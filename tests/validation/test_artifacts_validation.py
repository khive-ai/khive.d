"""Comprehensive validation tests for Artifacts Service models.

This module provides systematic validation testing for:
- Document model validation and lifecycle
- Session model validation and security
- Author model validation
- ContributionMetadata validation
- ArtifactRegistryEntry validation
- ArtifactRegistry validation and consistency
"""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from khive.services.artifacts.models import (
    ArtifactRegistry,
    ArtifactRegistryEntry,
    Author,
    ContributionMetadata,
    Document,
    DocumentType,
    Session,
    SessionStatus,
)
from tests.validation.pydantic_validators import BaseValidationPattern

# ============================================================================
# Author Model Validation
# ============================================================================


class AuthorValidator(BaseValidationPattern):
    """Validation patterns for Author model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid Author data."""
        data = {
            "id": "test_agent_001",
            "role": "researcher",
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        # Missing id
        cls.assert_invalid_model(Author, {"role": "researcher"}, "id")

        # Missing role
        cls.assert_invalid_model(Author, {"id": "test_agent"}, "role")

    @classmethod
    def test_field_constraints(cls):
        """Test field constraint validation."""
        # Empty strings should be invalid
        cls.assert_invalid_model(Author, cls.create_valid_data(id=""), "id")

        cls.assert_invalid_model(Author, cls.create_valid_data(role=""), "role")

        # Very long strings
        long_id = "x" * 1000
        long_role = "x" * 1000

        # Should handle reasonable lengths
        cls.assert_valid_model(Author, cls.create_valid_data(id=long_id[:100]))
        cls.assert_valid_model(Author, cls.create_valid_data(role=long_role[:100]))

    @classmethod
    def test_system_author(cls):
        """Test system author factory method."""
        system_author = Author.system()
        assert system_author.id == "system"
        assert system_author.role == "system"

        # Verify it's a valid model
        cls.assert_valid_model(
            Author, {"id": system_author.id, "role": system_author.role}
        )


# ============================================================================
# ContributionMetadata Model Validation
# ============================================================================


class ContributionMetadataValidator(BaseValidationPattern):
    """Validation patterns for ContributionMetadata model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid ContributionMetadata data."""
        data = {
            "author": {"id": "test_agent_001", "role": "researcher"},
            "timestamp": datetime.now(timezone.utc),
            "content_length": 1500,
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        required_fields = ["author", "timestamp", "content_length"]

        for field in required_fields:
            incomplete_data = cls.create_valid_data()
            del incomplete_data[field]
            cls.assert_invalid_model(ContributionMetadata, incomplete_data, field)

    @classmethod
    def test_content_length_constraints(cls):
        """Test content length constraints."""
        # Valid lengths
        valid_lengths = [0, 1, 100, 10000, 1000000]
        for length in valid_lengths:
            data = cls.create_valid_data(content_length=length)
            cls.assert_valid_model(ContributionMetadata, data)

        # Invalid lengths (negative)
        invalid_lengths = [-1, -100]
        for length in invalid_lengths:
            data = cls.create_valid_data(content_length=length)
            cls.assert_invalid_model(ContributionMetadata, data, "content_length")

    @classmethod
    def test_timestamp_validation(cls):
        """Test timestamp field validation."""
        # Valid timestamps
        valid_timestamps = [
            datetime.now(timezone.utc),
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime.now(timezone.utc) + timedelta(days=365),
        ]

        for timestamp in valid_timestamps:
            data = cls.create_valid_data(timestamp=timestamp)
            cls.assert_valid_model(ContributionMetadata, data)

    @classmethod
    def test_author_validation(cls):
        """Test nested author validation."""
        # Valid author
        valid_author = {"id": "agent_researcher_001", "role": "researcher"}
        data = cls.create_valid_data(author=valid_author)
        cls.assert_valid_model(ContributionMetadata, data)

        # Invalid author (missing fields)
        invalid_authors = [
            {"id": "test"},  # missing role
            {"role": "test"},  # missing id
            {},  # missing both
        ]

        for invalid_author in invalid_authors:
            data = cls.create_valid_data(author=invalid_author)
            cls.assert_invalid_model(ContributionMetadata, data)


# ============================================================================
# Document Model Validation
# ============================================================================


class DocumentValidator(BaseValidationPattern):
    """Validation patterns for Document model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid Document data."""
        data = {
            "session_id": "test_session_123",
            "name": "test_document",
            "type": "scratchpad",
            "content": "This is test content for the document.",
            "contributions": [],
            "version": 1,
            "last_modified": datetime.now(timezone.utc),
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        required_fields = ["session_id", "name", "type", "content", "last_modified"]

        for field in required_fields:
            incomplete_data = cls.create_valid_data()
            del incomplete_data[field]
            cls.assert_invalid_model(Document, incomplete_data, field)

    @classmethod
    def test_document_type_enum(cls):
        """Test DocumentType enum validation."""
        valid_types = ["deliverable", "scratchpad"]
        for doc_type in valid_types:
            data = cls.create_valid_data(type=doc_type)
            cls.assert_valid_model(Document, data)

        # Invalid type
        cls.assert_invalid_model(
            Document, cls.create_valid_data(type="invalid_type"), "type"
        )

    @classmethod
    def test_version_constraints(cls):
        """Test version field constraints."""
        # Valid versions
        valid_versions = [0, 1, 10, 100]
        for version in valid_versions:
            data = cls.create_valid_data(version=version)
            cls.assert_valid_model(Document, data)

        # Invalid versions
        invalid_versions = [-1, -10]
        for version in invalid_versions:
            data = cls.create_valid_data(version=version)
            cls.assert_invalid_model(Document, data, "version")

    @classmethod
    def test_session_id_format(cls):
        """Test session ID format validation."""
        # Valid session IDs
        valid_session_ids = [
            "session_123",
            "20250101_120000_test_session",
            "a1b2c3d4",
            "test-session_001",
        ]

        for session_id in valid_session_ids:
            data = cls.create_valid_data(session_id=session_id)
            cls.assert_valid_model(Document, data)

        # Empty session ID should be invalid
        cls.assert_invalid_model(
            Document, cls.create_valid_data(session_id=""), "session_id"
        )

    @classmethod
    def test_contributions_list_validation(cls):
        """Test contributions list validation."""
        # Valid contributions
        valid_contribution = {
            "author": {"id": "agent_001", "role": "researcher"},
            "timestamp": datetime.now(timezone.utc),
            "content_length": 100,
        }

        data = cls.create_valid_data(contributions=[valid_contribution])
        cls.assert_valid_model(Document, data)

        # Multiple contributions
        multiple_contributions = [
            valid_contribution,
            {
                "author": {"id": "agent_002", "role": "architect"},
                "timestamp": datetime.now(timezone.utc),
                "content_length": 200,
            },
        ]

        data = cls.create_valid_data(contributions=multiple_contributions)
        cls.assert_valid_model(Document, data)

    @classmethod
    def test_create_new_factory(cls):
        """Test Document.create_new factory method."""
        # Basic creation
        doc = Document.create_new(
            session_id="test_session",
            name="test_doc",
            doc_type=DocumentType.SCRATCHPAD,
            content="Test content",
        )

        assert doc.session_id == "test_session"
        assert doc.name == "test_doc"
        assert doc.type == DocumentType.SCRATCHPAD
        assert doc.content == "Test content"
        assert doc.version == 1
        assert len(doc.contributions) == 1
        assert doc.contributions[0].content_length == len("Test content")

        # With custom author
        custom_author = Author(id="custom_agent", role="tester")
        doc_with_author = Document.create_new(
            session_id="test_session",
            name="test_doc",
            doc_type=DocumentType.DELIVERABLE,
            content="Test content",
            author=custom_author,
        )

        assert doc_with_author.contributions[0].author == custom_author

    @classmethod
    def test_append_contribution(cls):
        """Test append_contribution method."""
        # Create initial document
        doc = Document.create_new(
            session_id="test_session",
            name="test_doc",
            doc_type=DocumentType.SCRATCHPAD,
            content="Initial content",
        )

        original_version = doc.version
        original_content_length = len(doc.content)

        # Append contribution
        new_author = Author(id="new_agent", role="reviewer")
        new_content = "Additional content"
        doc.append_contribution(new_content, new_author)

        # Verify updates
        assert doc.version == original_version + 1
        assert len(doc.contributions) == 2
        assert doc.contributions[-1].author == new_author
        assert doc.contributions[-1].content_length == len(new_content)
        assert new_content in doc.content
        assert len(doc.content) > original_content_length


# ============================================================================
# Session Model Validation
# ============================================================================


class SessionValidator(BaseValidationPattern):
    """Validation patterns for Session model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid Session data."""
        data = {
            "id": "test_session_123",
            "workspace_path": "/tmp/test_workspace",
            "created_at": datetime.now(timezone.utc),
            "status": "ACTIVE",
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        required_fields = ["id", "workspace_path", "created_at", "status"]

        for field in required_fields:
            incomplete_data = cls.create_valid_data()
            del incomplete_data[field]
            cls.assert_invalid_model(Session, incomplete_data, field)

    @classmethod
    def test_session_status_enum(cls):
        """Test SessionStatus enum validation."""
        valid_statuses = ["ACTIVE", "ARCHIVED"]
        for status in valid_statuses:
            data = cls.create_valid_data(status=status)
            cls.assert_valid_model(Session, data)

        # Invalid status
        cls.assert_invalid_model(
            Session, cls.create_valid_data(status="INVALID"), "status"
        )

    @classmethod
    def test_create_new_factory(cls):
        """Test Session.create_new factory method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)

            # Create with explicit session ID
            session = Session.create_new("test_session_123", workspace_root)

            assert session.id == "test_session_123"
            assert session.workspace_path == workspace_root / "test_session_123"
            assert session.status == SessionStatus.ACTIVE
            assert session.created_at is not None

            # Create with auto-generated ID
            auto_session = Session.create_new(None, workspace_root)

            assert auto_session.id is not None
            assert len(auto_session.id) > 0
            assert auto_session.status == SessionStatus.ACTIVE

    @classmethod
    def test_session_id_security_validation(cls):
        """Test session ID security validation in create_new."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)

            # Valid session IDs
            valid_ids = [
                "test_session_123",
                "20250101_120000_session",
                "a1b2c3d4-e5f6-7890",
                "session_001",
            ]

            for session_id in valid_ids:
                session = Session.create_new(session_id, workspace_root)
                assert session.id == session_id

            # Invalid session IDs (should raise ValidationError)
            invalid_ids = [
                "../../../etc/passwd",
                "session;rm -rf /",
                "session`cat /etc/passwd`",
                "session\x00malicious",
                "session/../../../sensitive",
                "/etc/passwd",
                "session" * 50,  # too long
            ]

            for invalid_id in invalid_ids:
                with pytest.raises(Exception):  # ValidationError or similar
                    Session.create_new(invalid_id, workspace_root)

    @classmethod
    def test_get_document_type_path(cls):
        """Test get_document_type_path method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            session = Session.create_new("test_session", workspace_root)

            # Test document type paths
            deliverable_path = session.get_document_type_path(DocumentType.DELIVERABLE)
            scratchpad_path = session.get_document_type_path(DocumentType.SCRATCHPAD)

            expected_deliverable = session.workspace_path / "deliverable"
            expected_scratchpad = session.workspace_path / "scratchpad"

            assert deliverable_path == expected_deliverable
            assert scratchpad_path == expected_scratchpad


# ============================================================================
# ArtifactRegistryEntry Model Validation
# ============================================================================


class ArtifactRegistryEntryValidator(BaseValidationPattern):
    """Validation patterns for ArtifactRegistryEntry model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid ArtifactRegistryEntry data."""
        data = {
            "id": "artifact_001",
            "type": "CRR",
            "name": "Code Review Report",
            "description": "Comprehensive code review findings",
            "file_path": "deliverable/code_review_report.md",
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "agent_role": "reviewer",
            "agent_domain": "software-architecture",
            "metadata": {"priority": "high", "estimated_hours": 4},
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        required_fields = ["id", "type", "name", "file_path", "created_at"]

        for field in required_fields:
            incomplete_data = cls.create_valid_data()
            del incomplete_data[field]
            cls.assert_invalid_model(ArtifactRegistryEntry, incomplete_data, field)

    @classmethod
    def test_optional_fields(cls):
        """Test optional field behavior."""
        # Minimal valid data
        minimal_data = {
            "id": "artifact_001",
            "type": "TDS",
            "name": "Technical Design Spec",
            "file_path": "deliverable/tech_design.md",
            "created_at": datetime.now(timezone.utc),
        }

        entry = cls.assert_valid_model(ArtifactRegistryEntry, minimal_data)

        # Check defaults
        assert entry.description is None
        assert entry.status == "active"
        assert entry.agent_role is None
        assert entry.agent_domain is None
        assert entry.metadata == {}

    @classmethod
    def test_metadata_validation(cls):
        """Test metadata field validation."""
        # Various metadata types
        metadata_examples = [
            {},  # empty
            {"key": "value"},  # simple string
            {"priority": "high", "estimated_hours": 4},  # mixed types
            {"tags": ["review", "security"], "complex": {"nested": "data"}},  # complex
        ]

        for metadata in metadata_examples:
            data = cls.create_valid_data(metadata=metadata)
            cls.assert_valid_model(ArtifactRegistryEntry, data)

    @classmethod
    def test_status_values(cls):
        """Test status field values."""
        valid_statuses = ["active", "archived", "deprecated"]
        for status in valid_statuses:
            data = cls.create_valid_data(status=status)
            cls.assert_valid_model(ArtifactRegistryEntry, data)

    @classmethod
    def test_file_path_security(cls):
        """Test file path security validation."""
        # Valid paths
        valid_paths = [
            "deliverable/report.md",
            "scratchpad/notes.md",
            "artifacts/analysis.json",
            "deep/nested/path/file.txt",
        ]

        for path in valid_paths:
            data = cls.create_valid_data(file_path=path)
            cls.assert_valid_model(ArtifactRegistryEntry, data)

        # Potentially problematic paths (should still validate at model level)
        # Security validation should happen at service level
        problematic_paths = [
            "../../../etc/passwd",
            "/absolute/path/file.txt",
            "file\x00malicious.txt",
        ]

        # These should validate at model level (path traversal prevention is service responsibility)
        for path in problematic_paths:
            data = cls.create_valid_data(file_path=path)
            # Model validation should pass, but service should reject
            cls.assert_valid_model(ArtifactRegistryEntry, data)


# ============================================================================
# ArtifactRegistry Model Validation
# ============================================================================


class ArtifactRegistryValidator(BaseValidationPattern):
    """Validation patterns for ArtifactRegistry model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid ArtifactRegistry data."""
        data = {
            "session_id": "test_session_123",
            "created_at": datetime.now(timezone.utc),
            "task_description": "Implement comprehensive validation testing for khive services",
            "artifacts": [],
            "status": "active",
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        required_fields = ["session_id", "created_at"]

        for field in required_fields:
            incomplete_data = cls.create_valid_data()
            del incomplete_data[field]
            cls.assert_invalid_model(ArtifactRegistry, incomplete_data, field)

    @classmethod
    def test_optional_fields(cls):
        """Test optional field defaults."""
        minimal_data = {
            "session_id": "test_session_123",
            "created_at": datetime.now(timezone.utc),
        }

        registry = cls.assert_valid_model(ArtifactRegistry, minimal_data)

        # Check defaults
        assert registry.task_description is None
        assert registry.artifacts == []
        assert registry.status == "active"

    @classmethod
    def test_create_new_factory(cls):
        """Test ArtifactRegistry.create_new factory method."""
        # With task description
        registry = ArtifactRegistry.create_new(
            "test_session_123", "Test task description"
        )

        assert registry.session_id == "test_session_123"
        assert registry.task_description == "Test task description"
        assert registry.status == "active"
        assert registry.artifacts == []
        assert registry.created_at is not None

        # Without task description
        minimal_registry = ArtifactRegistry.create_new("test_session_456")

        assert minimal_registry.session_id == "test_session_456"
        assert minimal_registry.task_description is None
        assert minimal_registry.status == "active"

    @classmethod
    def test_add_artifact(cls):
        """Test add_artifact method."""
        registry = ArtifactRegistry.create_new("test_session_123")

        # Add first artifact
        registry.add_artifact(
            artifact_id="artifact_001",
            doc_type="CRR",
            name="Code Review Report",
            file_path="deliverable/crr.md",
            description="Comprehensive code review",
            agent_role="reviewer",
            agent_domain="software-architecture",
            metadata={"priority": "high"},
        )

        assert len(registry.artifacts) == 1
        artifact = registry.artifacts[0]

        assert artifact.id == "artifact_001"
        assert artifact.type == "CRR"
        assert artifact.name == "Code Review Report"
        assert artifact.description == "Comprehensive code review"
        assert artifact.agent_role == "reviewer"
        assert artifact.agent_domain == "software-architecture"
        assert artifact.metadata["priority"] == "high"

        # Add second artifact
        registry.add_artifact(
            artifact_id="artifact_002",
            doc_type="TDS",
            name="Technical Design",
            file_path="deliverable/tds.md",
        )

        assert len(registry.artifacts) == 2

    @classmethod
    def test_get_artifact(cls):
        """Test get_artifact method."""
        registry = ArtifactRegistry.create_new("test_session_123")

        # Add test artifact
        registry.add_artifact(
            artifact_id="test_artifact",
            doc_type="CRR",
            name="Test Artifact",
            file_path="test/path.md",
        )

        # Test retrieval
        found_artifact = registry.get_artifact("test_artifact")
        assert found_artifact is not None
        assert found_artifact.id == "test_artifact"

        # Test non-existent artifact
        missing_artifact = registry.get_artifact("non_existent")
        assert missing_artifact is None

    @classmethod
    def test_list_artifacts_by_type(cls):
        """Test list_artifacts_by_type method."""
        registry = ArtifactRegistry.create_new("test_session_123")

        # Add artifacts of different types
        registry.add_artifact("crr_001", "CRR", "Review 1", "path1.md")
        registry.add_artifact("crr_002", "CRR", "Review 2", "path2.md")
        registry.add_artifact("tds_001", "TDS", "Design 1", "path3.md")

        # Test filtering by type
        crr_artifacts = registry.list_artifacts_by_type("CRR")
        tds_artifacts = registry.list_artifacts_by_type("TDS")
        missing_artifacts = registry.list_artifacts_by_type("NonExistent")

        assert len(crr_artifacts) == 2
        assert len(tds_artifacts) == 1
        assert len(missing_artifacts) == 0

        # Verify correct artifacts returned
        crr_ids = [artifact.id for artifact in crr_artifacts]
        assert "crr_001" in crr_ids
        assert "crr_002" in crr_ids


# ============================================================================
# Cross-Model Validation Patterns
# ============================================================================


class ArtifactsServiceCrossValidator:
    """Cross-model validation patterns for Artifacts Service."""

    @staticmethod
    def validate_document_session_consistency(
        document: Document, session: Session
    ) -> list[str]:
        """Validate consistency between Document and Session."""
        issues = []

        # Document session_id should match Session id
        if document.session_id != session.id:
            issues.append(
                f"Document session_id '{document.session_id}' doesn't match "
                f"Session id '{session.id}'"
            )

        # Document should be newer than session
        if document.last_modified < session.created_at:
            issues.append("Document last_modified is older than session creation")

        return issues

    @staticmethod
    def validate_registry_artifact_consistency(
        registry: ArtifactRegistry, entry: ArtifactRegistryEntry
    ) -> list[str]:
        """Validate consistency between Registry and its entries."""
        issues = []

        # Entry should exist in registry
        found_entry = registry.get_artifact(entry.id)
        if found_entry is None:
            issues.append(f"Artifact entry '{entry.id}' not found in registry")

        # Entry creation should be after registry creation
        if entry.created_at < registry.created_at:
            issues.append("Artifact entry created before registry creation")

        return issues

    @staticmethod
    def validate_contribution_document_consistency(document: Document) -> list[str]:
        """Validate consistency within Document contributions."""
        issues = []

        if not document.contributions:
            issues.append("Document has no contributions but has content")
            return issues

        # Contributions should be chronologically ordered
        timestamps = [contrib.timestamp for contrib in document.contributions]
        if timestamps != sorted(timestamps):
            issues.append("Document contributions not in chronological order")

        # Version should match contribution count
        if document.version != len(document.contributions):
            issues.append(
                f"Document version {document.version} doesn't match "
                f"contribution count {len(document.contributions)}"
            )

        # Total content length should be reasonable vs contributions
        total_contrib_length = sum(
            contrib.content_length for contrib in document.contributions
        )
        content_length = len(document.content)

        # Allow for separators and formatting in content
        if total_contrib_length > content_length * 2:
            issues.append(
                "Contribution lengths significantly exceed actual content length"
            )

        return issues


# ============================================================================
# Comprehensive Test Suite
# ============================================================================


class TestArtifactsValidation:
    """Test class to run all Artifacts Service validation tests."""

    def test_author_validation(self):
        """Test Author model validation."""
        AuthorValidator.test_required_fields()
        AuthorValidator.test_field_constraints()
        AuthorValidator.test_system_author()

    def test_contribution_metadata_validation(self):
        """Test ContributionMetadata model validation."""
        ContributionMetadataValidator.test_required_fields()
        ContributionMetadataValidator.test_content_length_constraints()
        ContributionMetadataValidator.test_timestamp_validation()
        ContributionMetadataValidator.test_author_validation()

    def test_document_validation(self):
        """Test Document model validation."""
        DocumentValidator.test_required_fields()
        DocumentValidator.test_document_type_enum()
        DocumentValidator.test_version_constraints()
        DocumentValidator.test_session_id_format()
        DocumentValidator.test_contributions_list_validation()
        DocumentValidator.test_create_new_factory()
        DocumentValidator.test_append_contribution()

    def test_session_validation(self):
        """Test Session model validation."""
        SessionValidator.test_required_fields()
        SessionValidator.test_session_status_enum()
        SessionValidator.test_create_new_factory()
        SessionValidator.test_session_id_security_validation()
        SessionValidator.test_get_document_type_path()

    def test_artifact_registry_entry_validation(self):
        """Test ArtifactRegistryEntry model validation."""
        ArtifactRegistryEntryValidator.test_required_fields()
        ArtifactRegistryEntryValidator.test_optional_fields()
        ArtifactRegistryEntryValidator.test_metadata_validation()
        ArtifactRegistryEntryValidator.test_status_values()
        ArtifactRegistryEntryValidator.test_file_path_security()

    def test_artifact_registry_validation(self):
        """Test ArtifactRegistry model validation."""
        ArtifactRegistryValidator.test_required_fields()
        ArtifactRegistryValidator.test_optional_fields()
        ArtifactRegistryValidator.test_create_new_factory()
        ArtifactRegistryValidator.test_add_artifact()
        ArtifactRegistryValidator.test_get_artifact()
        ArtifactRegistryValidator.test_list_artifacts_by_type()

    def test_cross_model_validation(self):
        """Test cross-model validation patterns."""
        # Create test models
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            session = Session.create_new("test_session", workspace_root)

            document = Document.create_new(
                session_id=session.id,
                name="test_doc",
                doc_type=DocumentType.SCRATCHPAD,
                content="Test content",
            )

            registry = ArtifactRegistry.create_new(session.id, "Test task")
            registry.add_artifact(
                "test_artifact", "CRR", "Test Artifact", "test/path.md"
            )

            entry = registry.get_artifact("test_artifact")

            # Run cross-model validations
            doc_session_issues = (
                ArtifactsServiceCrossValidator.validate_document_session_consistency(
                    document, session
                )
            )

            registry_entry_issues = (
                ArtifactsServiceCrossValidator.validate_registry_artifact_consistency(
                    registry, entry
                )
            )

            contrib_issues = ArtifactsServiceCrossValidator.validate_contribution_document_consistency(
                document
            )

            # Should have no issues for valid models
            assert len(doc_session_issues) == 0
            assert len(registry_entry_issues) == 0
            assert len(contrib_issues) == 0


if __name__ == "__main__":
    # Manual test runner
    test_suite = TestArtifactsValidation()

    try:
        test_suite.test_author_validation()
        test_suite.test_contribution_metadata_validation()
        test_suite.test_document_validation()
        test_suite.test_session_validation()
        test_suite.test_artifact_registry_entry_validation()
        test_suite.test_artifact_registry_validation()
        test_suite.test_cross_model_validation()

        print("✅ All Artifacts Service validation tests passed!")

    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        raise
