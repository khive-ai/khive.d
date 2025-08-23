"""Comprehensive tests for artifacts Pydantic models."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from khive.services.artifacts.models import (Author, ContributionMetadata,
                                             Document, DocumentType,
                                             SessionStatus)


class TestDocumentType:
    """Test DocumentType enum validation and behavior."""

    def test_valid_document_types(self):
        """Test all valid DocumentType enum values."""
        assert DocumentType.DELIVERABLE == "deliverable"
        assert DocumentType.SCRATCHPAD == "scratchpad"

    def test_document_type_string_comparison(self):
        """Test DocumentType can be compared with strings."""
        assert DocumentType.DELIVERABLE == "deliverable"
        assert DocumentType.SCRATCHPAD == "scratchpad"

        # Test inequality
        assert DocumentType.DELIVERABLE != "scratchpad"
        assert DocumentType.SCRATCHPAD != "deliverable"

    def test_document_type_in_list(self):
        """Test DocumentType membership in lists."""
        doc_types = [DocumentType.DELIVERABLE, DocumentType.SCRATCHPAD]

        assert DocumentType.DELIVERABLE in doc_types
        assert DocumentType.SCRATCHPAD in doc_types
        assert "invalid_type" not in [dt.value for dt in doc_types]


class TestSessionStatus:
    """Test SessionStatus enum validation and behavior."""

    def test_valid_session_statuses(self):
        """Test all valid SessionStatus enum values."""
        assert SessionStatus.ACTIVE == "ACTIVE"
        assert SessionStatus.ARCHIVED == "ARCHIVED"

    def test_session_status_string_comparison(self):
        """Test SessionStatus can be compared with strings."""
        assert SessionStatus.ACTIVE == "ACTIVE"
        assert SessionStatus.ARCHIVED == "ARCHIVED"


class TestAuthor:
    """Test Author model validation and behavior."""

    def test_valid_author_creation(self):
        """Test creating valid Author instances."""
        author = Author(id="researcher_001", role="researcher")

        assert author.id == "researcher_001"
        assert author.role == "researcher"

    def test_author_validation_errors(self):
        """Test validation errors for Author model."""
        # Missing required id field
        with pytest.raises(ValidationError) as exc_info:
            Author(role="researcher")

        error_msg = str(exc_info.value)
        assert "id" in error_msg
        assert "Field required" in error_msg

        # Missing required role field
        with pytest.raises(ValidationError) as exc_info:
            Author(id="test_id")

        error_msg = str(exc_info.value)
        assert "role" in error_msg
        assert "Field required" in error_msg

    def test_author_field_constraints(self):
        """Test Author field constraints."""
        # Empty id should fail (min_length=1)
        with pytest.raises(ValidationError) as exc_info:
            Author(id="", role="researcher")

        error_msg = str(exc_info.value)
        assert "id" in error_msg
        assert "String should have at least 1 character" in error_msg

        # Empty role should fail (min_length=1)
        with pytest.raises(ValidationError) as exc_info:
            Author(id="test_id", role="")

        error_msg = str(exc_info.value)
        assert "role" in error_msg
        assert "String should have at least 1 character" in error_msg

    def test_author_system_factory_method(self):
        """Test Author.system() factory method."""
        system_author = Author.system()

        assert system_author.id == "system"
        assert system_author.role == "system"
        assert isinstance(system_author, Author)

    def test_author_equality(self):
        """Test Author equality comparison."""
        author1 = Author(id="test_001", role="researcher")
        author2 = Author(id="test_001", role="researcher")
        author3 = Author(id="test_002", role="researcher")
        author4 = Author(id="test_001", role="architect")

        # Same data should be equal
        assert author1 == author2

        # Different id should not be equal
        assert author1 != author3

        # Different role should not be equal
        assert author1 != author4

    def test_author_serialization(self):
        """Test Author serialization and deserialization."""
        original = Author(id="architect_001", role="architect")

        # Test serialization
        data = original.model_dump()
        expected = {"id": "architect_001", "role": "architect"}
        assert data == expected

        # Test deserialization
        restored = Author.model_validate(data)
        assert restored == original

    @pytest.mark.parametrize(
        "author_id,role",
        [
            ("researcher_001", "researcher"),
            ("architect_main", "architect"),
            ("system", "system"),
            ("user_session_123", "user"),
            ("ai_agent_v2", "ai_assistant"),
        ],
    )
    def test_author_parametrized_creation(self, author_id, role):
        """Test Author creation with various valid combinations."""
        author = Author(id=author_id, role=role)
        assert author.id == author_id
        assert author.role == role


class TestContributionMetadata:
    """Test ContributionMetadata model validation and behavior."""

    def test_valid_contribution_metadata_creation(self):
        """Test creating valid ContributionMetadata instances."""
        author = Author(id="contributor_001", role="researcher")
        timestamp = datetime.now(timezone.utc)

        contribution = ContributionMetadata(
            author=author, timestamp=timestamp, content_length=1500
        )

        assert contribution.author == author
        assert contribution.timestamp == timestamp
        assert contribution.content_length == 1500

    def test_contribution_metadata_validation_errors(self):
        """Test validation errors for ContributionMetadata."""
        author = Author(id="test", role="test")
        timestamp = datetime.now(timezone.utc)

        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            ContributionMetadata(timestamp=timestamp, content_length=100)

        error_msg = str(exc_info.value)
        assert "author" in error_msg
        assert "Field required" in error_msg

    def test_content_length_constraints(self):
        """Test content_length field constraints."""
        author = Author(id="test", role="test")
        timestamp = datetime.now(timezone.utc)

        # Valid content lengths (ge=0)
        valid_lengths = [0, 1, 100, 10000, 50000]
        for length in valid_lengths:
            contribution = ContributionMetadata(
                author=author, timestamp=timestamp, content_length=length
            )
            assert contribution.content_length == length

        # Invalid negative content length
        with pytest.raises(ValidationError) as exc_info:
            ContributionMetadata(author=author, timestamp=timestamp, content_length=-1)

        error_msg = str(exc_info.value)
        assert "content_length" in error_msg
        assert "Input should be greater than or equal to 0" in error_msg

    def test_timestamp_handling(self):
        """Test timestamp field handling with different timezone scenarios."""
        author = Author(id="test", role="test")

        # UTC timestamp
        utc_time = datetime.now(timezone.utc)
        contribution1 = ContributionMetadata(
            author=author, timestamp=utc_time, content_length=100
        )
        assert contribution1.timestamp == utc_time

        # Local timestamp (should be handled correctly)
        local_time = datetime.now()
        contribution2 = ContributionMetadata(
            author=author, timestamp=local_time, content_length=100
        )
        assert contribution2.timestamp == local_time

    def test_contribution_metadata_serialization(self):
        """Test ContributionMetadata serialization and deserialization."""
        author = Author(id="serialization_test", role="tester")
        timestamp = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)

        original = ContributionMetadata(
            author=author, timestamp=timestamp, content_length=2500
        )

        # Test serialization
        data = original.model_dump()
        assert "author" in data
        assert "timestamp" in data
        assert "content_length" in data
        assert data["content_length"] == 2500

        # Test deserialization
        restored = ContributionMetadata.model_validate(data)
        assert restored == original


class TestDocument:
    """Test Document model validation and behavior."""

    def test_valid_document_creation(self):
        """Test creating valid Document instances."""
        timestamp = datetime.now(timezone.utc)

        document = Document(
            session_id="session_123",
            name="test_document",
            type=DocumentType.DELIVERABLE,
            content="This is test document content",
            last_modified=timestamp,
        )

        assert document.session_id == "session_123"
        assert document.name == "test_document"
        assert document.type == DocumentType.DELIVERABLE
        assert document.content == "This is test document content"
        assert document.last_modified == timestamp
        assert document.contributions == []
        assert document.version == 0

    def test_document_validation_errors(self):
        """Test validation errors for Document model."""
        timestamp = datetime.now(timezone.utc)
        base_data = {
            "name": "test_doc",
            "type": DocumentType.DELIVERABLE,
            "content": "content",
            "last_modified": timestamp,
        }

        # Missing session_id
        with pytest.raises(ValidationError) as exc_info:
            Document(**base_data)

        error_msg = str(exc_info.value)
        assert "session_id" in error_msg
        assert "Field required" in error_msg

    def test_document_field_constraints(self):
        """Test Document field constraints."""
        timestamp = datetime.now(timezone.utc)

        # Empty session_id should fail
        with pytest.raises(ValidationError) as exc_info:
            Document(
                session_id="",
                name="test",
                type=DocumentType.DELIVERABLE,
                content="content",
                last_modified=timestamp,
            )

        error_msg = str(exc_info.value)
        assert "session_id" in error_msg
        assert "String should have at least 1 character" in error_msg

        # Empty name should fail
        with pytest.raises(ValidationError) as exc_info:
            Document(
                session_id="session",
                name="",
                type=DocumentType.DELIVERABLE,
                content="content",
                last_modified=timestamp,
            )

        error_msg = str(exc_info.value)
        assert "name" in error_msg
        assert "String should have at least 1 character" in error_msg

    def test_document_version_constraints(self):
        """Test version field constraints."""
        timestamp = datetime.now(timezone.utc)

        # Valid version values (ge=0)
        valid_versions = [0, 1, 5, 100]
        for version in valid_versions:
            document = Document(
                session_id="session",
                name="test",
                type=DocumentType.DELIVERABLE,
                content="content",
                version=version,
                last_modified=timestamp,
            )
            assert document.version == version

        # Invalid negative version
        with pytest.raises(ValidationError) as exc_info:
            Document(
                session_id="session",
                name="test",
                type=DocumentType.DELIVERABLE,
                content="content",
                version=-1,
                last_modified=timestamp,
            )

        error_msg = str(exc_info.value)
        assert "version" in error_msg
        assert "Input should be greater than or equal to 0" in error_msg

    def test_document_with_contributions(self):
        """Test Document with contributions list."""
        author = Author(id="contributor", role="researcher")
        timestamp = datetime.now(timezone.utc)

        contribution = ContributionMetadata(
            author=author, timestamp=timestamp, content_length=500
        )

        document = Document(
            session_id="session_with_contributions",
            name="collaborative_doc",
            type=DocumentType.SCRATCHPAD,
            content="Collaborative document content",
            contributions=[contribution],
            last_modified=timestamp,
        )

        assert len(document.contributions) == 1
        assert document.contributions[0] == contribution

    def test_document_create_new_factory_method(self):
        """Test Document.create_new factory method."""
        author = Author(id="creator", role="architect")
        content = "New document content"

        with patch("khive.services.artifacts.models.datetime") as mock_datetime:
            fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = fixed_time

            document = Document.create_new(
                session_id="new_session",
                name="new_document",
                doc_type=DocumentType.DELIVERABLE,
                content=content,
                author=author,
            )

            assert document.session_id == "new_session"
            assert document.name == "new_document"
            assert document.type == DocumentType.DELIVERABLE
            assert document.content == content
            assert document.last_modified == fixed_time
            assert document.version == 0
            assert len(document.contributions) == 1
            assert document.contributions[0].author == author
            assert document.contributions[0].content_length == len(content)

    def test_document_create_new_with_system_author(self):
        """Test Document.create_new with default system author."""
        content = "System-created document"

        with patch("khive.services.artifacts.models.datetime") as mock_datetime:
            fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = fixed_time

            document = Document.create_new(
                session_id="system_session",
                name="system_document",
                doc_type=DocumentType.SCRATCHPAD,
                content=content,
            )

            assert len(document.contributions) == 1
            assert document.contributions[0].author.id == "system"
            assert document.contributions[0].author.role == "system"

    @pytest.mark.parametrize(
        "doc_type", [DocumentType.DELIVERABLE, DocumentType.SCRATCHPAD]
    )
    def test_document_types_parametrized(self, doc_type):
        """Test Document creation with different DocumentType values."""
        timestamp = datetime.now(timezone.utc)

        document = Document(
            session_id="type_test_session",
            name="type_test_document",
            type=doc_type,
            content="Content for type testing",
            last_modified=timestamp,
        )

        assert document.type == doc_type

    def test_document_large_content(self):
        """Test Document with large content."""
        timestamp = datetime.now(timezone.utc)
        large_content = "x" * 100000  # 100KB content

        document = Document(
            session_id="large_content_session",
            name="large_document",
            type=DocumentType.DELIVERABLE,
            content=large_content,
            last_modified=timestamp,
        )

        assert len(document.content) == 100000
        assert document.content == large_content

    def test_document_serialization_roundtrip(self):
        """Test Document complete serialization and deserialization."""
        author = Author(id="serialization_author", role="researcher")
        timestamp = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)

        contribution = ContributionMetadata(
            author=author, timestamp=timestamp, content_length=1000
        )

        original = Document(
            session_id="serialization_session",
            name="serialization_test_document",
            type=DocumentType.DELIVERABLE,
            content="This is content for serialization testing",
            contributions=[contribution],
            version=2,
            last_modified=timestamp,
        )

        # JSON serialization roundtrip
        json_data = original.model_dump_json()
        restored = Document.model_validate_json(json_data)

        assert restored == original
        assert restored.session_id == original.session_id
        assert restored.name == original.name
        assert restored.type == original.type
        assert restored.content == original.content
        assert restored.version == original.version
        assert len(restored.contributions) == len(original.contributions)
        assert (
            restored.contributions[0].author.id == original.contributions[0].author.id
        )

    def test_document_equality_and_hashing(self):
        """Test Document equality and hashing behavior."""
        timestamp = datetime.now(timezone.utc)

        doc1 = Document(
            session_id="test_session",
            name="test_doc",
            type=DocumentType.DELIVERABLE,
            content="test content",
            last_modified=timestamp,
        )

        doc2 = Document(
            session_id="test_session",
            name="test_doc",
            type=DocumentType.DELIVERABLE,
            content="test content",
            last_modified=timestamp,
        )

        doc3 = Document(
            session_id="different_session",
            name="test_doc",
            type=DocumentType.DELIVERABLE,
            content="test content",
            last_modified=timestamp,
        )

        # Same data should be equal
        assert doc1 == doc2

        # Different session_id should not be equal
        assert doc1 != doc3

        # Should be hashable (inherits from HashableModel)
        hash1 = hash(doc1)
        hash2 = hash(doc2)
        hash3 = hash(doc3)

        assert hash1 == hash2  # Same content
        assert hash1 != hash3  # Different content

    def test_document_performance_with_many_contributions(self):
        """Test Document performance with many contributions."""
        import time

        timestamp = datetime.now(timezone.utc)

        # Create many contributions
        contributions = []
        for i in range(100):
            author = Author(id=f"contributor_{i}", role="contributor")
            contribution = ContributionMetadata(
                author=author,
                timestamp=timestamp + timedelta(minutes=i),
                content_length=100 + i,
            )
            contributions.append(contribution)

        start_time = time.time()
        document = Document(
            session_id="performance_test_session",
            name="performance_test_document",
            type=DocumentType.SCRATCHPAD,
            content="Performance test content with many contributions",
            contributions=contributions,
            last_modified=timestamp,
        )
        creation_time = time.time() - start_time

        # Should create reasonably quickly
        assert creation_time < 1.0
        assert len(document.contributions) == 100

        # Test serialization performance
        start_time = time.time()
        serialized_data = document.model_dump()
        serialization_time = time.time() - start_time

        assert serialization_time < 0.5
        assert len(serialized_data["contributions"]) == 100
