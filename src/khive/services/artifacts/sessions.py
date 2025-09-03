"""
Session manager for the Artifacts Service.

Handles session lifecycle, validation, and secure path resolution.
Based on Gemini Deep Think V2 architecture.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles

from .exceptions import (
    SessionAlreadyExists,
    SessionNotFound,
    StorageError,
    ValidationError,
)
from .models import DocumentType, Session, SessionStatus

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages the lifecycle and security of development sessions.

    Responsibilities:
    - Session creation and validation
    - Secure path resolution (prevents path traversal attacks)
    - Directory structure management
    - Session metadata persistence
    """

    # Strict validation for session IDs (prevents path traversal and injection)
    SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")

    def __init__(self, workspace_root: Path):
        """
        Initialize the session manager.

        Args:
            workspace_root: Root directory for all session workspaces
        """
        self._root = workspace_root
        self._root.mkdir(parents=True, exist_ok=True)
        # Create metadata directory for session persistence
        self._metadata_root = self._root / ".metadata"
        self._metadata_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"Session manager initialized with workspace: {self._root}")

    def _validate_id_format(self, session_id: str) -> None:
        """
        Ensures the session ID is safe for directory names.

        This is a critical security function that prevents:
        - Path traversal attacks (../, ../../etc/passwd)
        - Shell injection attempts
        - Unicode normalization attacks
        - Filesystem-specific invalid characters

        Args:
            session_id: Session ID to validate

        Raises:
            ValidationError: If the session ID format is invalid
        """
        if not session_id:
            raise ValidationError("Session ID cannot be empty")

        if not self.SESSION_ID_PATTERN.match(session_id):
            raise ValidationError(
                f"Invalid session ID format: {session_id}. "
                f"Must match pattern: {self.SESSION_ID_PATTERN.pattern}"
            )

        # Additional security checks
        if ".." in session_id or "/" in session_id or "\\" in session_id:
            raise ValidationError(
                f"Session ID contains invalid path characters: {session_id}"
            )

    def _get_metadata_path(self, session_id: str) -> Path:
        """Get the metadata file path for a session."""
        return self._metadata_root / f"{session_id}.json"

    async def _save_session_metadata(self, session: Session) -> None:
        """
        Atomically persist session metadata to filesystem.

        Args:
            session: Session object to persist

        Raises:
            StorageError: If metadata persistence fails
        """
        metadata_path = self._get_metadata_path(session.id)
        temp_path = metadata_path.with_suffix(".tmp")

        try:
            # Prepare metadata dictionary
            metadata = {
                "id": session.id,
                "workspace_path": str(session.workspace_path),
                "created_at": (
                    session.created_at.isoformat()
                    if isinstance(session.created_at, datetime)
                    else session.created_at
                ),
                "status": session.status.value,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "version": 1,
            }

            # Atomic write: write to temp file first, then rename
            async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(metadata, indent=2, ensure_ascii=False))
                await f.flush()

            # Atomic rename operation
            temp_path.rename(metadata_path)
            logger.debug(f"Session metadata saved for {session.id}")

        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            logger.error(f"Failed to save session metadata for {session.id}: {e}")
            raise StorageError(f"Failed to persist session metadata: {e}") from e

    async def _load_session_metadata(self, session_id: str) -> dict[str, Any] | None:
        """
        Load session metadata from filesystem.

        Args:
            session_id: Session identifier

        Returns:
            Metadata dictionary or None if not found

        Raises:
            StorageError: If metadata loading fails
        """
        metadata_path = self._get_metadata_path(session_id)

        if not metadata_path.exists():
            return None

        try:
            async with aiofiles.open(metadata_path, "r", encoding="utf-8") as f:
                content = await f.read()
                metadata = json.loads(content)
                logger.debug(f"Session metadata loaded for {session_id}")
                return metadata

        except Exception as e:
            logger.error(f"Failed to load session metadata for {session_id}: {e}")
            raise StorageError(f"Failed to load session metadata: {e}") from e

    async def _update_session_status(
        self, session_id: str, new_status: SessionStatus, **additional_fields
    ) -> None:
        """
        Atomically update session status and additional fields.

        Args:
            session_id: Session identifier
            new_status: New session status
            **additional_fields: Additional metadata fields to update

        Raises:
            SessionNotFound: If session metadata doesn't exist
            StorageError: If update fails
        """
        metadata = await self._load_session_metadata(session_id)
        if not metadata:
            raise SessionNotFound(f"Session metadata not found for {session_id}")

        # Update fields
        metadata["status"] = new_status.value
        metadata["last_updated"] = datetime.now(timezone.utc).isoformat()
        metadata["version"] = metadata.get("version", 1) + 1

        # Add any additional fields
        for key, value in additional_fields.items():
            metadata[key] = value

        # Atomic update using temp file
        metadata_path = self._get_metadata_path(session_id)
        temp_path = metadata_path.with_suffix(".tmp")

        try:
            async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(metadata, indent=2, ensure_ascii=False))
                await f.flush()

            temp_path.rename(metadata_path)
            logger.info(f"Session {session_id} status updated to {new_status.value}")

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            logger.error(f"Failed to update session status for {session_id}: {e}")
            raise StorageError(f"Failed to update session status: {e}") from e

    async def create_session(self, session_id: str | None = None) -> Session:
        """
        Creates a new development session.

        Args:
            session_id: Optional session ID (UUID generated if None)

        Returns:
            Created session

        Raises:
            SessionAlreadyExists: If session already exists
            ValidationError: If session ID format is invalid
            StorageError: If filesystem operations fail
        """
        # Create session object (validates ID format)
        session = Session.create_new(session_id, self._root)

        # Check if session already exists
        if session.workspace_path.exists():
            raise SessionAlreadyExists(f"Session {session.id} already exists")

        try:
            # Create the directory structure
            session.workspace_path.mkdir(exist_ok=False)

            # Create subdirectories for each document type
            for doc_type in DocumentType:
                (session.workspace_path / doc_type.value).mkdir()

            logger.info(f"Created session {session.id} at {session.workspace_path}")

            # Persist session metadata atomically
            await self._save_session_metadata(session)

            return session

        except OSError as e:
            logger.exception(
                f"Failed to create session workspace for {session.id}: {e}"
            )
            raise StorageError(f"Failed to create session workspace: {e}") from e

    async def get_session(self, session_id: str) -> Session:
        """
        Retrieves an existing session.

        Args:
            session_id: Session identifier

        Returns:
            Session object

        Raises:
            SessionNotFound: If session doesn't exist
            ValidationError: If session ID format is invalid
        """
        self._validate_id_format(session_id)

        session_path = self._root / session_id
        if not session_path.is_dir():
            raise SessionNotFound(f"Session {session_id} not found")

        # Load session metadata from filesystem
        metadata = await self._load_session_metadata(session_id)

        if metadata:
            # Parse datetime from ISO format
            try:
                created_at = datetime.fromisoformat(
                    metadata["created_at"].replace("Z", "+00:00")
                )
            except (ValueError, KeyError):
                created_at = datetime.fromtimestamp(
                    session_path.stat().st_ctime, tz=timezone.utc
                )

            return Session(
                id=session_id,
                workspace_path=session_path,
                created_at=created_at,
                status=SessionStatus(
                    metadata.get("status", SessionStatus.ACTIVE.value)
                ),
            )
        else:
            # Fallback: create session object from filesystem info
            # This handles sessions created before metadata persistence was implemented
            session = Session(
                id=session_id,
                workspace_path=session_path,
                created_at=datetime.fromtimestamp(
                    session_path.stat().st_ctime, tz=timezone.utc
                ),
                status=SessionStatus.ACTIVE,
            )

            # Persist metadata for future use
            try:
                await self._save_session_metadata(session)
                logger.info(f"Migrated session {session_id} to metadata persistence")
            except Exception as e:
                logger.warning(f"Failed to migrate session {session_id} metadata: {e}")

            return session

    async def validate_session(self, session_id: str) -> None:
        """
        Validates that a session exists and is active.

        Args:
            session_id: Session identifier to validate

        Raises:
            SessionNotFound: If session doesn't exist
            ValidationError: If session ID format is invalid or session is inactive
        """
        session = await self.get_session(session_id)

        if session.status != SessionStatus.ACTIVE:
            raise ValidationError(
                f"Session {session_id} is not active (status: {session.status})"
            )

    def resolve_document_path(
        self, session_id: str, doc_name: str, doc_type: DocumentType
    ) -> Path:
        """
        Safely resolves a document path, preventing path traversal attacks.

        This is a CRITICAL SECURITY FUNCTION that ensures:
        - All paths are within the session workspace
        - Path traversal attempts are blocked (../../etc/passwd)
        - Symlink attacks are prevented
        - Unicode normalization attacks are handled

        Args:
            session_id: Session identifier
            doc_name: Document name
            doc_type: Document type

        Returns:
            Resolved absolute path within the session workspace

        Raises:
            ValidationError: If path resolution fails or path traversal is detected
        """
        self._validate_id_format(session_id)

        # Resolve the base path to its absolute, real path (handling symlinks)
        base_path = (self._root / session_id / doc_type.value).resolve()

        # Validate document name format
        if not doc_name or ".." in doc_name or "/" in doc_name or "\\" in doc_name:
            raise ValidationError(f"Invalid document name: {doc_name}")

        try:
            # Construct the potential path and resolve it (handling normalization like '..')
            # Use strict=False to allow non-existent files
            resolved_path = (base_path / doc_name).resolve(strict=False)
        except (FileNotFoundError, RuntimeError, OSError) as e:
            # Handle potential resolution issues (e.g., excessive symlinks)
            logger.warning(
                f"Path resolution failed for {doc_name} in session {session_id}: {e}"
            )
            raise ValidationError(
                f"Invalid document name resolution: {doc_name}"
            ) from e

        # CRITICAL SECURITY CHECK: Ensure the resolved path is strictly within the base path
        # is_relative_to() requires Python 3.9+
        try:
            if not resolved_path.is_relative_to(base_path):
                # This indicates a path traversal attempt
                logger.warning(
                    f"Path traversal attempt detected: {doc_name} in session {session_id}. "
                    f"Resolved path {resolved_path} is outside base {base_path}"
                )
                raise ValidationError(f"Invalid document path: {doc_name}")
        except ValueError:
            # Fallback for edge cases in path comparison
            logger.warning(
                f"Path comparison failed for {doc_name} in session {session_id}"
            )
            raise ValidationError(f"Invalid document path: {doc_name}")

        return resolved_path

    async def list_sessions(self) -> list[str]:
        """
        Lists all available sessions.

        Returns:
            List of session IDs
        """
        try:
            sessions = []
            for path in self._root.iterdir():
                if (
                    path.is_dir()
                    and self.SESSION_ID_PATTERN.match(path.name)
                    and path.name != ".metadata"
                ):
                    sessions.append(path.name)
            return sorted(sessions)
        except OSError as e:
            logger.exception(f"Failed to list sessions: {e}")
            return []

    async def archive_session(self, session_id: str) -> None:
        """
        Archives a session (marks as inactive).

        Args:
            session_id: Session to archive
        """
        # Validate session exists and update status to archived
        await self.get_session(session_id)  # Validates existence
        await self._update_session_status(
            session_id,
            SessionStatus.ARCHIVED,
            archived_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info(f"Session {session_id} archived")

    async def delete_session(self, session_id: str, force: bool = False) -> None:
        """
        Deletes a session workspace.

        Args:
            session_id: Session to delete
            force: If True, delete even if session is active

        Raises:
            ValidationError: If session is active and force=False
        """
        session = await self.get_session(session_id)

        if session.status == SessionStatus.ACTIVE and not force:
            raise ValidationError(
                f"Cannot delete active session {session_id} (use force=True)"
            )

        try:
            import shutil

            # Delete workspace directory
            shutil.rmtree(session.workspace_path)

            # Delete metadata file
            metadata_path = self._get_metadata_path(session_id)
            if metadata_path.exists():
                metadata_path.unlink()

            logger.info(f"Deleted session {session_id} and its metadata")

        except OSError as e:
            raise StorageError(f"Failed to delete session {session_id}: {e}") from e

    async def recover_sessions(self) -> dict[str, str]:
        """
        Recover session state after process restart.

        Returns:
            Dictionary mapping session IDs to their recovery status
        """
        recovery_status = {}

        try:
            # Get all workspace directories
            workspace_sessions = set()
            for path in self._root.iterdir():
                if (
                    path.is_dir()
                    and self.SESSION_ID_PATTERN.match(path.name)
                    and path.name != ".metadata"
                ):
                    workspace_sessions.add(path.name)

            # Get all metadata files
            metadata_sessions = set()
            if self._metadata_root.exists():
                for path in self._metadata_root.iterdir():
                    if path.suffix == ".json" and path.stem:
                        metadata_sessions.add(path.stem)

            # Process sessions with both workspace and metadata
            for session_id in workspace_sessions & metadata_sessions:
                try:
                    session = await self.get_session(session_id)
                    recovery_status[session_id] = f"recovered: {session.status.value}"
                except Exception as e:
                    recovery_status[session_id] = f"error: {str(e)}"

            # Process orphaned workspaces (workspace but no metadata)
            for session_id in workspace_sessions - metadata_sessions:
                try:
                    session = await self.get_session(
                        session_id
                    )  # This will create metadata
                    recovery_status[session_id] = "migrated: workspace to metadata"
                except Exception as e:
                    recovery_status[session_id] = f"migration_error: {str(e)}"

            # Process orphaned metadata (metadata but no workspace)
            for session_id in metadata_sessions - workspace_sessions:
                recovery_status[session_id] = "orphaned: metadata without workspace"

            logger.info(
                f"Session recovery completed: {len(recovery_status)} sessions processed"
            )
            return recovery_status

        except Exception as e:
            logger.error(f"Session recovery failed: {e}")
            return {"error": str(e)}

    async def get_session_stats(self) -> dict[str, Any]:
        """
        Get statistics about all sessions.

        Returns:
            Dictionary with session statistics
        """
        try:
            sessions = await self.list_sessions()
            stats = {
                "total_sessions": len(sessions),
                "active_sessions": 0,
                "archived_sessions": 0,
                "session_details": [],
            }

            for session_id in sessions:
                try:
                    session = await self.get_session(session_id)
                    if session.status == SessionStatus.ACTIVE:
                        stats["active_sessions"] += 1
                    else:
                        stats["archived_sessions"] += 1

                    stats["session_details"].append(
                        {
                            "id": session_id,
                            "status": session.status.value,
                            "created_at": (
                                session.created_at.isoformat()
                                if isinstance(session.created_at, datetime)
                                else str(session.created_at)
                            ),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to get stats for session {session_id}: {e}")

            return stats

        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            return {"error": str(e)}
