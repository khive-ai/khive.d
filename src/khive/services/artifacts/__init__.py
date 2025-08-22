"""
Artifacts Service Package.

Provides session-based document management with multi-agent collaboration support.
Based on Gemini Deep Think V2 architecture.

This package implements:
- Atomic document operations with concurrency control
- Secure session management with path traversal protection
- Collaborative document editing for deliverables
- File-system based storage with JSON serialization

Example usage:
    from khive.services.artifacts import create_artifacts_service, ArtifactsConfig
    from khive.services.artifacts.models import DocumentType, Author

    # Create service
    config = ArtifactsConfig(workspace_root=Path("./workspace"))
    service = create_artifacts_service(config)

    # Create session and document
    session = await service.create_session("my_session")
    author = Author(id="agent_1", role="researcher")

    doc = await service.create_document(
        session.id,
        "research_notes",
        DocumentType.SCRATCHPAD,
        "Initial findings...",
        author
    )

    # Collaborate on deliverable
    await service.append_to_deliverable(
        session.id,
        "final_report",
        "## Analysis Results\n\nKey insights discovered...",
        author
    )
"""

from .exceptions import (
    AlreadyExistsError,
    ArtifactsError,
    ConcurrencyError,
    ConfigurationError,
    DocumentAlreadyExists,
    DocumentNotFound,
    NotFoundError,
    SessionAlreadyExists,
    SessionNotFound,
    StorageError,
    TemplateError,
    TemplateNotFound,
    ValidationError,
)
from .factory import (
    ArtifactsConfig,
    create_artifacts_service,
    create_artifacts_service_from_env,
)
from .locks import LockManager
from .models import (
    ArtifactRegistry,
    ArtifactRegistryEntry,
    Author,
    ContributionMetadata,
    Document,
    DocumentType,
    Session,
    SessionStatus,
)
from .service import ArtifactsService
from .sessions import SessionManager
from .storage import FileSystemStorageRepository, IStorageRepository

__all__ = [
    # Main service
    "ArtifactsService",
    "create_artifacts_service",
    "create_artifacts_service_from_env",
    "ArtifactsConfig",
    # Domain models
    "Document",
    "DocumentType",
    "Author",
    "Session",
    "SessionStatus",
    "ContributionMetadata",
    "ArtifactRegistry",
    "ArtifactRegistryEntry",
    # Components (for advanced usage)
    "FileSystemStorageRepository",
    "IStorageRepository",
    "SessionManager",
    "LockManager",
    # Exceptions
    "ArtifactsError",
    "NotFoundError",
    "DocumentNotFound",
    "SessionNotFound",
    "TemplateNotFound",
    "AlreadyExistsError",
    "DocumentAlreadyExists",
    "SessionAlreadyExists",
    "ValidationError",
    "StorageError",
    "TemplateError",
    "ConfigurationError",
    "ConcurrencyError",
]
