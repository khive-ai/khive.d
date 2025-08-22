"""
Storage repository for the Artifacts Service.

Implements atomic file operations with proper concurrency control.
Based on Gemini Deep Think V2 architecture.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Protocol

import aiofiles
import yaml

from .exceptions import DocumentNotFound, StorageError
from .models import Author, ContributionMetadata, Document, DocumentType
from .sessions import SessionManager

logger = logging.getLogger(__name__)


class IStorageRepository(Protocol):
    """
    Defines the contract for persistent storage.
    Focuses on atomic operations for individual documents.
    """

    async def save(self, document: Document) -> None:
        """
        Persists the document. This operation MUST be atomic (all-or-nothing).
        If the document exists, it is overwritten.
        Raises: StorageError on I/O failure.
        """
        ...

    async def read(
        self, session_id: str, doc_name: str, doc_type: DocumentType
    ) -> Document:
        """
        Retrieves a document.
        Raises: DocumentNotFound if the document does not exist.
        """
        ...

    async def exists(
        self, session_id: str, doc_name: str, doc_type: DocumentType
    ) -> bool:
        """Checks if a document exists."""
        ...


class FileSystemStorageRepository(IStorageRepository):
    """
    File system implementation of the storage repository.

    Documents are stored as markdown files with YAML front matter to preserve metadata.
    Uses atomic write-to-temp-and-rename for consistency.
    """

    def __init__(self, session_manager: SessionManager):
        """
        Initialize the repository.

        Args:
            session_manager: Used for secure path resolution
        """
        # We rely on the SessionManager to resolve paths securely
        self._sessions = session_manager

    async def _resolve_path(
        self, session_id: str, doc_name: str, doc_type: DocumentType
    ) -> Path:
        """
        Securely resolves the file path for a document.

        Returns path with .md extension for markdown storage.
        """
        return self._sessions.resolve_document_path(
            session_id, doc_name, doc_type
        ).with_suffix(".md")

    def _document_to_markdown(self, document: Document) -> str:
        """
        Converts a Document to markdown format with YAML front matter.
        """
        # Create front matter with essential metadata
        front_matter = {
            "session_id": document.session_id,
            "name": document.name,
            "type": document.type.value,
            "version": document.version,
            "last_modified": document.last_modified.isoformat(),
            "contributions": [
                {
                    "author_id": contrib.author.id,
                    "author_role": contrib.author.role,
                    "timestamp": contrib.timestamp.isoformat(),
                    "content_length": contrib.content_length,
                }
                for contrib in document.contributions
            ],
        }

        # Generate markdown with YAML front matter
        yaml_header = yaml.dump(front_matter, default_flow_style=False, sort_keys=False)
        return f"---\n{yaml_header}---\n\n{document.content}"

    async def save(self, document: Document) -> None:
        """
        Implements atomic save using write-to-temp-and-rename.
        Saves as markdown with YAML front matter instead of JSON.

        This ensures that readers never see partially written files
        and the filesystem state remains consistent even if the process crashes.
        """
        target_path = await self._resolve_path(
            document.session_id, document.name, document.type
        )
        parent_dir = target_path.parent

        # Ensure the directory exists (blocking operation run in thread)
        await asyncio.to_thread(parent_dir.mkdir, parents=True, exist_ok=True)

        # 1. Serialize the document to markdown with YAML front matter
        try:
            data_to_write = self._document_to_markdown(document)
        except Exception as e:
            raise StorageError(
                f"Failed to serialize document {document.name}: {e}"
            ) from e

        # 2. Create a unique temporary file path in the same directory.
        #    Crucial: Must be on the same filesystem for os.replace() to be atomic.
        temp_path = parent_dir / f".tmp.{document.name}.{uuid.uuid4().hex}.md"

        try:
            # 3. Write content to the temporary file asynchronously.
            async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
                await f.write(data_to_write)
                await f.flush()
                # 4. Ensure durability: fsync is a blocking OS call.
                await asyncio.to_thread(os.fsync, f.fileno())

            # 5. Atomically replace the target file. os.replace() is blocking.
            await asyncio.to_thread(os.replace, temp_path, target_path)

            logger.debug(
                f"Successfully saved document {document.name} to {target_path}"
            )

        except OSError as e:
            logger.error(f"Atomic save failed for {document.name}: {e}", exc_info=True)
            # Cleanup: If writing or renaming fails, remove the temp file.
            if temp_path.exists():
                try:
                    await asyncio.to_thread(os.remove, temp_path)
                except OSError:
                    # If cleanup fails, log but don't raise (original error is more important)
                    logger.warning(f"Failed to cleanup temp file {temp_path}")
            raise StorageError(f"Atomic save failed for {document.name}: {e}") from e

    def _markdown_to_document(self, content: str) -> Document:
        """
        Converts markdown with YAML front matter back to a Document object.
        """
        # Split front matter and content
        if not content.startswith("---\n"):
            raise ValueError("Invalid markdown format: missing YAML front matter")

        parts = content.split("---\n", 2)
        if len(parts) != 3:
            raise ValueError("Invalid markdown format: malformed YAML front matter")

        yaml_content = parts[1]
        markdown_content = parts[2].lstrip("\n")

        # Parse YAML front matter
        try:
            metadata = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML front matter: {e}")

        # Reconstruct contributions
        contributions = []
        for contrib_data in metadata.get("contributions", []):
            author = Author(
                id=contrib_data["author_id"], role=contrib_data["author_role"]
            )
            contribution = ContributionMetadata(
                author=author,
                timestamp=datetime.fromisoformat(contrib_data["timestamp"]),
                content_length=contrib_data["content_length"],
            )
            contributions.append(contribution)

        # Create Document object
        return Document(
            session_id=metadata["session_id"],
            name=metadata["name"],
            type=DocumentType(metadata["type"]),
            content=markdown_content,
            version=metadata["version"],
            last_modified=datetime.fromisoformat(metadata["last_modified"]),
            contributions=contributions,
        )

    async def read(
        self, session_id: str, doc_name: str, doc_type: DocumentType
    ) -> Document:
        """
        Reads a document from storage.
        Now handles markdown format with YAML front matter instead of JSON.

        Args:
            session_id: Session identifier
            doc_name: Document name
            doc_type: Document type

        Returns:
            The loaded document

        Raises:
            DocumentNotFound: If the document doesn't exist
            StorageError: If there's an I/O or parsing error
        """
        path = await self._resolve_path(session_id, doc_name, doc_type)

        try:
            async with aiofiles.open(path, encoding="utf-8") as f:
                data = await f.read()
        except FileNotFoundError:
            raise DocumentNotFound(f"Document {doc_name} not found in {doc_type.value}")
        except OSError as e:
            raise StorageError(f"Failed to read document {doc_name}: {e}") from e

        try:
            # Parse markdown with YAML front matter
            return self._markdown_to_document(data)
        except (ValueError, yaml.YAMLError) as e:
            raise StorageError(f"Failed to parse document {doc_name}: {e}") from e

    async def exists(
        self, session_id: str, doc_name: str, doc_type: DocumentType
    ) -> bool:
        """
        Checks if a document exists.

        Args:
            session_id: Session identifier
            doc_name: Document name
            doc_type: Document type

        Returns:
            True if the document exists, False otherwise
        """
        try:
            path = await self._resolve_path(session_id, doc_name, doc_type)
            return await asyncio.to_thread(path.exists)
        except Exception:
            # If path resolution fails, consider the document as not existing
            return False

    async def list_documents(
        self, session_id: str, doc_type: DocumentType
    ) -> list[str]:
        """
        Lists all documents of a given type in a session.

        Args:
            session_id: Session identifier
            doc_type: Document type to list

        Returns:
            List of document names (without .json extension)
        """
        try:
            session = await self._sessions.get_session(session_id)
            doc_dir = session.get_document_type_path(doc_type)

            if not await asyncio.to_thread(doc_dir.exists):
                return []

            # List all .json files in the directory
            def _list_files():
                return [f.stem for f in doc_dir.glob("*.json") if f.is_file()]

            return await asyncio.to_thread(_list_files)

        except Exception as e:
            logger.error(
                f"Failed to list documents for {session_id}/{doc_type.value}: {e}"
            )
            return []
