"""
Domain models for the Artifacts Service.

Represents the core entities: Document, Session, and their relationships.
Based on Gemini Deep Think V2 architecture.
"""

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Type of document in the artifacts system."""

    DELIVERABLE = "deliverable"  # Official collaborative documents (CRR, TDS, etc.)
    SCRATCHPAD = "scratchpad"  # Working documents and agent notes shared in session


class SessionStatus(str, Enum):
    """Status of a development session."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class Author(BaseModel):
    """Represents an author/contributor to a document."""

    id: str
    role: str  # e.g., "PlannerAgent", "Researcher", "Architect"

    @classmethod
    def system(cls) -> "Author":
        """System author for automated operations."""
        return cls(id="system", role="system")


class ContributionMetadata(BaseModel):
    """Metadata about a contribution to a document."""

    author: Author
    timestamp: datetime
    content_length: int


class Document(BaseModel):
    """
    Represents an artifact managed by the service.

    Documents are stored as JSON files containing both content and metadata.
    This enables rich querying and version tracking without complex storage.
    """

    session_id: str
    name: str
    type: DocumentType
    content: str
    contributions: list[ContributionMetadata] = Field(default_factory=list)
    version: int = 0
    last_modified: datetime

    @classmethod
    def create_new(
        cls,
        session_id: str,
        name: str,
        doc_type: DocumentType,
        content: str,
        author: Author | None = None,
    ) -> "Document":
        """Factory method to create a new document."""
        now = datetime.now(timezone.utc)
        effective_author = author or Author.system()

        contribution = ContributionMetadata(
            author=effective_author, timestamp=now, content_length=len(content)
        )

        return cls(
            session_id=session_id,
            name=name,
            type=doc_type,
            content=content,
            contributions=[contribution],
            version=1,
            last_modified=now,
        )

    def append_contribution(self, content: str, author: Author) -> None:
        """Append content with proper metadata tracking."""
        now = datetime.now(timezone.utc)

        # Format the contribution with clear separation
        separator = f"\n\n--- [Contribution by {author.id} ({author.role}) @ {now.isoformat()}] ---\n\n"
        self.content = f"{self.content}{separator}{content}"

        # Update metadata
        contribution = ContributionMetadata(
            author=author, timestamp=now, content_length=len(content)
        )
        self.contributions.append(contribution)
        self.version += 1
        self.last_modified = now


class Session(BaseModel):
    """Represents a development session workspace."""

    id: str
    workspace_path: Path
    created_at: datetime
    status: SessionStatus

    @classmethod
    def create_new(cls, session_id: str | None, workspace_root: Path) -> "Session":
        """Factory method to create a new session."""
        if session_id is None:
            session_id = str(uuid.uuid4())

        # Validate session ID format for security
        if not re.match(r"^[a-zA-Z0-9_-]{1,128}$", session_id):
            from .exceptions import ValidationError

            raise ValidationError(f"Invalid session ID format: {session_id}")

        workspace_path = workspace_root / session_id

        return cls(
            id=session_id,
            workspace_path=workspace_path,
            created_at=datetime.now(timezone.utc),
            status=SessionStatus.ACTIVE,
        )

    def get_document_type_path(self, doc_type: DocumentType) -> Path:
        """Get the path for a specific document type."""
        return self.workspace_path / doc_type.value


# --- Artifact Registry Models ---


class ArtifactRegistryEntry(BaseModel):
    """Represents an entry in the artifact registry."""

    id: str
    type: str  # Document type/template used (e.g., "CRR", "TDS", "artifact")
    name: str  # Human-readable name/component name
    description: str | None = None
    file_path: str  # Relative path from workspace root
    status: str = "active"  # active, archived, deprecated
    created_at: datetime
    agent_role: str | None = None  # Agent that created it
    agent_domain: str | None = None  # Agent domain
    metadata: dict[str, Any] = Field(default_factory=dict)  # Additional metadata


class ArtifactRegistry(BaseModel):
    """Session-level artifact registry for tracking all documents."""

    session_id: str
    created_at: datetime
    task_description: str | None = None
    artifacts: list[ArtifactRegistryEntry] = Field(default_factory=list)
    status: str = "active"  # active, completed, archived

    @classmethod
    def create_new(
        cls, session_id: str, task_description: str | None = None
    ) -> "ArtifactRegistry":
        """Create a new artifact registry for a session."""
        return cls(
            session_id=session_id,
            created_at=datetime.now(timezone.utc),
            task_description=task_description,
            artifacts=[],
            status="active",
        )

    def add_artifact(
        self,
        artifact_id: str,
        doc_type: str,
        name: str,
        file_path: str,
        description: str | None = None,
        agent_role: str | None = None,
        agent_domain: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a new artifact to the registry."""
        entry = ArtifactRegistryEntry(
            id=artifact_id,
            type=doc_type,
            name=name,
            description=description,
            file_path=file_path,
            created_at=datetime.now(timezone.utc),
            agent_role=agent_role,
            agent_domain=agent_domain,
            metadata=metadata or {},
        )
        self.artifacts.append(entry)

    def get_artifact(self, artifact_id: str) -> ArtifactRegistryEntry | None:
        """Get an artifact by ID."""
        for artifact in self.artifacts:
            if artifact.id == artifact_id:
                return artifact
        return None

    def list_artifacts_by_type(self, doc_type: str) -> list[ArtifactRegistryEntry]:
        """List all artifacts of a specific type."""
        return [artifact for artifact in self.artifacts if artifact.type == doc_type]
