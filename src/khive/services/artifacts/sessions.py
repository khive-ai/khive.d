"""
Session manager for the Artifacts Service.

Handles session lifecycle, validation, and secure path resolution.
Based on Gemini Deep Think V2 architecture.
"""

import logging
import re
from pathlib import Path

from .exceptions import (SessionAlreadyExists, SessionNotFound, StorageError,
                         ValidationError)
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

            # TODO: Persist session metadata (atomic operation)
            # await self._save_session_metadata(session)

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

        # TODO: Load session metadata from filesystem
        # For now, create a basic session object
        return Session(
            id=session_id,
            workspace_path=session_path,
            created_at=session_path.stat().st_ctime,  # Use filesystem creation time
            status=SessionStatus.ACTIVE,
        )

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
                if path.is_dir() and self.SESSION_ID_PATTERN.match(path.name):
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
        await self.get_session(session_id)
        # TODO: Update session metadata to mark as archived
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

            shutil.rmtree(session.workspace_path)
            logger.info(f"Deleted session {session_id}")
        except OSError as e:
            raise StorageError(f"Failed to delete session {session_id}: {e}") from e
