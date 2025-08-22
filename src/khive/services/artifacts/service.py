"""
Main Artifacts Service facade.

Provides the primary interface for document and session management.
Based on Gemini Deep Think V2 architecture.
"""

import json
import logging
from pathlib import Path
from typing import Any

from .exceptions import DocumentAlreadyExists, DocumentNotFound
from .locks import LockManager
from .models import ArtifactRegistry, Author, Document, DocumentType, Session
from .sessions import SessionManager
from .storage import IStorageRepository

logger = logging.getLogger(__name__)


class ArtifactsService:
    """
    Central facade for the Artifacts Service.

    This is the main entry point for all document and session operations.
    It coordinates between storage, session management, locking, and templates.

    The service ensures:
    - Atomic operations for document updates
    - Proper concurrency control for collaborative documents
    - Security validation for all operations
    - Consistent error handling and logging
    """

    def __init__(
        self,
        storage_repo: IStorageRepository,
        session_manager: SessionManager,
        lock_manager: LockManager,
    ):
        """
        Initialize the artifacts service.

        Args:
            storage_repo: Repository for document persistence
            session_manager: Manager for session lifecycle and security
            lock_manager: Manager for concurrency control
        """
        self._storage = storage_repo
        self._sessions = session_manager
        self._locks = lock_manager

        logger.info("ArtifactsService initialized")

    # --- Session Operations (Delegation) ---

    async def create_session(self, session_id: str | None = None) -> Session:
        """
        Creates a new development session.

        Args:
            session_id: Optional session ID (UUID generated if None)

        Returns:
            Created session
        """
        logger.info(f"Creating session: {session_id or 'auto-generated'}")
        return await self._sessions.create_session(session_id)

    async def get_session(self, session_id: str) -> Session:
        """
        Retrieves an existing session.

        Args:
            session_id: Session identifier

        Returns:
            Session object
        """
        return await self._sessions.get_session(session_id)

    async def list_sessions(self) -> list[str]:
        """
        Lists all available sessions.

        Returns:
            List of session IDs
        """
        return await self._sessions.list_sessions()

    # --- Document Operations ---

    async def create_document(
        self,
        session_id: str,
        doc_name: str,
        doc_type: DocumentType,
        content: str,
        author: Author | None = None,
        description: str | None = None,
        agent_role: str | None = None,
        agent_domain: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """
        Creates a new document, ensuring it does not already exist.

        Args:
            session_id: Session identifier
            doc_name: Name of the document
            doc_type: Type of document (DELIVERABLE, SCRATCHPAD)
            content: Initial content
            author: Author of the document (defaults to system)
            description: Optional description for artifact registry
            agent_role: Agent role that created the document
            agent_domain: Agent domain
            metadata: Additional metadata for artifact registry

        Returns:
            Created document

        Raises:
            DocumentAlreadyExists: If document already exists
            SessionNotFound: If session doesn't exist
            ValidationError: If inputs are invalid
        """
        logger.info(f"Creating document {doc_name} in session {session_id}")

        # Validate session exists and is active
        await self._sessions.validate_session(session_id)

        # Check for existence
        if await self._storage.exists(session_id, doc_name, doc_type):
            raise DocumentAlreadyExists(
                f"Document '{doc_name}' already exists in {doc_type.value}"
            )

        # Create the document
        document = Document.create_new(
            session_id=session_id,
            name=doc_name,
            doc_type=doc_type,
            content=content,
            author=author,
        )

        # Save atomically
        await self._storage.save(document)

        # Register in artifact registry
        file_path = f"{doc_type.value}/{doc_name}.md"
        artifact_id = f"{doc_name}_{session_id}"

        # Determine document type for registry (map DocumentType to template types)
        registry_doc_type = doc_type.value
        if doc_type == DocumentType.DELIVERABLE and doc_name.startswith(
            (
                "CRR_",
                "TDS_",
                "RR_",
                "IP_",
                "TI_",
            )
        ):
            registry_doc_type = doc_name.split("_")[0]  # Extract CRR, TDS, etc.
        elif doc_type == DocumentType.SCRATCHPAD:
            registry_doc_type = "artifact"

        await self.register_artifact(
            session_id=session_id,
            artifact_id=artifact_id,
            doc_type=registry_doc_type,
            name=doc_name,
            file_path=file_path,
            description=description,
            agent_role=agent_role,
            agent_domain=agent_domain,
            metadata=metadata,
        )

        logger.info(
            f"Successfully created document {doc_name} (version {document.version})"
        )
        return document

    async def get_document(
        self, session_id: str, doc_name: str, doc_type: DocumentType
    ) -> Document:
        """
        Retrieves a document.

        Args:
            session_id: Session identifier
            doc_name: Document name
            doc_type: Document type

        Returns:
            The requested document
        """
        await self._sessions.validate_session(session_id)
        return await self._storage.read(session_id, doc_name, doc_type)

    async def list_documents(
        self, session_id: str, doc_type: DocumentType
    ) -> list[str]:
        """
        Lists all documents of a given type in a session.

        Args:
            session_id: Session identifier
            doc_type: Document type to list

        Returns:
            List of document names
        """
        await self._sessions.validate_session(session_id)
        return await self._storage.list_documents(session_id, doc_type)

    async def append_to_deliverable(
        self, session_id: str, doc_name: str, content_to_append: str, author: Author
    ) -> Document:
        """
        Atomically appends content to a deliverable document.

        This method implements the collaborative workflow where multiple agents
        can contribute to the same document safely. It uses pessimistic locking
        to ensure atomic Read-Modify-Write cycles.

        Args:
            session_id: Session identifier
            doc_name: Name of the deliverable document
            content_to_append: Content to append
            author: Author making the contribution

        Returns:
            Updated document with the new contribution

        Raises:
            ConcurrencyError: If lock acquisition times out
            SessionNotFound: If session doesn't exist
            ValidationError: If inputs are invalid

        Example:
            # Multiple agents can safely append to the same document
            author = Author(id="agent_researcher", role="Researcher")
            doc = await service.append_to_deliverable(
                "session_123",
                "research_report",
                "## New findings\n\nDiscovered important insights...",
                author
            )
        """
        logger.info(
            f"Appending to deliverable {doc_name} in session {session_id} by {author.id}"
        )

        await self._sessions.validate_session(session_id)
        doc_type = DocumentType.DELIVERABLE

        # Generate a unique lock key for this specific document
        lock_key = self._locks.format_lock_key(session_id, doc_type.value, doc_name)

        # 1. Acquire the logical lock (Pessimistic Concurrency Control)
        # This will raise ConcurrencyError on timeout
        async with self._locks.acquire(lock_key):
            logger.debug(f"Acquired lock for {lock_key}")

            # 2. Read current content (Must happen AFTER acquiring the lock)
            try:
                document = await self._storage.read(session_id, doc_name, doc_type)
                logger.debug(
                    f"Read existing document {doc_name} (version {document.version})"
                )
            except DocumentNotFound:
                # Business decision: Allow creation on append if it doesn't exist
                logger.info(
                    f"Document {doc_name} not found, creating with initial content"
                )
                return await self.create_document(
                    session_id,
                    doc_name,
                    doc_type,
                    content=content_to_append,
                    author=author,
                )

            # 3. Append the contribution (this modifies the document in-place)
            old_version = document.version
            document.append_contribution(content_to_append, author)

            # 4. Atomic write (Handled by storage.save())
            try:
                await self._storage.save(document)
                logger.info(
                    f"Successfully appended to {doc_name} by {author.id} "
                    f"(version {old_version} -> {document.version})"
                )
            except Exception as e:
                # If the save fails (e.g., disk full), the lock is released by the context manager
                # The document on disk remains in its previous state due to atomic save
                logger.error(f"Failed to save document {doc_name}: {e}")
                raise

            return document

        # 6. Release lock (handled automatically by 'async with')

    async def update_document(
        self,
        session_id: str,
        doc_name: str,
        doc_type: DocumentType,
        new_content: str,
        author: Author,
    ) -> Document:
        """
        Updates a document with entirely new content.

        For deliverables, this replaces all content. For scratchpads and references,
        this is the normal update operation.

        Args:
            session_id: Session identifier
            doc_name: Document name
            doc_type: Document type
            new_content: New content to replace existing content
            author: Author making the update

        Returns:
            Updated document
        """
        logger.info(f"Updating document {doc_name} in session {session_id}")

        await self._sessions.validate_session(session_id)

        # For deliverables, use locking to ensure atomicity
        if doc_type == DocumentType.DELIVERABLE:
            lock_key = self._locks.format_lock_key(session_id, doc_type.value, doc_name)
            async with self._locks.acquire(lock_key):
                document = await self._storage.read(session_id, doc_name, doc_type)

                # Replace content entirely and add as a new contribution
                document.content = new_content
                document.append_contribution(
                    f"[FULL UPDATE] {len(new_content)} characters", author
                )

                await self._storage.save(document)
                return document
        else:
            # For non-deliverables, direct update is fine
            document = await self._storage.read(session_id, doc_name, doc_type)

            document.content = new_content
            document.append_contribution(
                f"[UPDATE] {len(new_content)} characters", author
            )

            await self._storage.save(document)
            return document

    async def document_exists(
        self, session_id: str, doc_name: str, doc_type: DocumentType
    ) -> bool:
        """
        Checks if a document exists.

        Args:
            session_id: Session identifier
            doc_name: Document name
            doc_type: Document type

        Returns:
            True if document exists, False otherwise
        """
        try:
            await self._sessions.validate_session(session_id)
            return await self._storage.exists(session_id, doc_name, doc_type)
        except Exception:
            return False

    # --- Utility Methods ---

    async def get_lock_stats(self) -> dict[str, Any]:
        """
        Get statistics about lock usage for monitoring.

        Returns:
            Dictionary with lock statistics
        """
        return self._locks.get_lock_stats()

    async def cleanup_locks(self, max_locks: int = 1000) -> int:
        """
        Cleanup unused locks to prevent memory leaks.

        Args:
            max_locks: Maximum number of locks to keep

        Returns:
            Number of locks cleaned up
        """
        return await self._locks.cleanup_unused_locks(max_locks)

    # --- Artifact Registry Methods ---

    async def _get_registry_path(self, session_id: str) -> Path:
        """Get the path to the artifact registry file for a session."""
        session = await self._sessions.get_session(session_id)
        return session.workspace_path / "artifact_registry.json"

    async def _load_artifact_registry(self, session_id: str) -> ArtifactRegistry:
        """Load artifact registry for a session, creating if it doesn't exist."""
        registry_path = await self._get_registry_path(session_id)

        if registry_path.exists():
            try:
                content = registry_path.read_text(encoding="utf-8")
                data = json.loads(content)
                return ArtifactRegistry(**data)
            except Exception as e:
                logger.warning(
                    f"Failed to load artifact registry for {session_id}: {e}"
                )
                # Fall through to create new registry

        # Create new registry
        return ArtifactRegistry.create_new(session_id)

    async def _save_artifact_registry(self, registry: ArtifactRegistry) -> None:
        """Save artifact registry to disk."""
        registry_path = await self._get_registry_path(registry.session_id)

        try:
            # Ensure parent directory exists
            registry_path.parent.mkdir(parents=True, exist_ok=True)

            # Save with pretty printing for human readability
            content = registry.model_dump_json(indent=2, exclude_defaults=True)
            registry_path.write_text(content, encoding="utf-8")

            logger.debug(f"Saved artifact registry for session {registry.session_id}")
        except Exception as e:
            logger.error(f"Failed to save artifact registry: {e}")
            raise

    async def register_artifact(
        self,
        session_id: str,
        artifact_id: str,
        doc_type: str,
        name: str,
        file_path: str,
        description: str | None = None,
        agent_role: str | None = None,
        agent_domain: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Register an artifact in the session's artifact registry.

        Args:
            session_id: Session identifier
            artifact_id: Unique identifier for the artifact
            doc_type: Document type (CRR, TDS, artifact, etc.)
            name: Human-readable name
            file_path: Relative path from session root
            description: Optional description
            agent_role: Agent role that created it
            agent_domain: Agent domain
            metadata: Additional metadata
        """
        await self._sessions.validate_session(session_id)

        registry = await self._load_artifact_registry(session_id)
        registry.add_artifact(
            artifact_id=artifact_id,
            doc_type=doc_type,
            name=name,
            file_path=file_path,
            description=description,
            agent_role=agent_role,
            agent_domain=agent_domain,
            metadata=metadata,
        )

        await self._save_artifact_registry(registry)
        logger.info(f"Registered artifact {artifact_id} in session {session_id}")

    async def get_artifact_registry(self, session_id: str) -> ArtifactRegistry:
        """Get the artifact registry for a session."""
        await self._sessions.validate_session(session_id)
        return await self._load_artifact_registry(session_id)

    async def list_artifacts_by_type(self, session_id: str, doc_type: str) -> list[str]:
        """List all artifacts of a specific type in a session."""
        registry = await self.get_artifact_registry(session_id)
        artifacts = registry.list_artifacts_by_type(doc_type)
        return [artifact.name for artifact in artifacts]
