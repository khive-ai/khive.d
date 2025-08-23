"""Tests for artifacts storage functionality."""

import json
import tempfile
from pathlib import Path

import pytest

from khive.services.artifacts.models import Document, DocumentType
from khive.services.artifacts.storage import FileSystemStorageRepository


class TestFileSystemStorageRepository:
    """Test the FileSystemStorageRepository storage implementation."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary storage directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def fs_repository(self, temp_storage_dir):
        """Create a FileSystemStorageRepository instance."""
        from khive.services.artifacts.sessions import SessionManager

        session_manager = SessionManager(workspace_root=temp_storage_dir)
        return FileSystemStorageRepository(session_manager=session_manager)

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return Document(
            name="test_doc",
            session_id="test_session",
            document_type=DocumentType.SCRATCHPAD,
            content="Test content",
            description="Test document",
            version=1,
            metadata={"author": "test"},
        )

    @pytest.mark.unit
    def test_repository_initialization(self, fs_repository, temp_storage_dir):
        """Test that repository initializes correctly."""
        assert fs_repository is not None
        assert Path(fs_repository.workspace_path) == temp_storage_dir

    @pytest.mark.unit
    def test_save_document(self, fs_repository, sample_document):
        """Test saving a document to storage."""
        # Save document
        fs_repository.save_document(sample_document)

        # Verify file exists
        expected_path = (
            Path(fs_repository.workspace_path)
            / sample_document.session_id
            / f"{sample_document.name}.md"
        )
        assert expected_path.exists()

        # Verify content
        with open(expected_path) as f:
            content = f.read()
            assert "Test content" in content
            assert sample_document.name in content

    @pytest.mark.unit
    def test_load_document(self, fs_repository, sample_document):
        """Test loading a document from storage."""
        # Save first
        fs_repository.save_document(sample_document)

        # Load document
        loaded_doc = fs_repository.load_document(
            sample_document.name, sample_document.session_id
        )

        assert loaded_doc is not None
        assert loaded_doc.name == sample_document.name
        assert loaded_doc.session_id == sample_document.session_id
        assert loaded_doc.content == sample_document.content

    @pytest.mark.unit
    def test_document_exists(self, fs_repository, sample_document):
        """Test checking if a document exists."""
        # Initially should not exist
        assert not fs_repository.document_exists(
            sample_document.name, sample_document.session_id
        )

        # Save document
        fs_repository.save_document(sample_document)

        # Now should exist
        assert fs_repository.document_exists(
            sample_document.name, sample_document.session_id
        )

    @pytest.mark.unit
    def test_list_session_documents(self, fs_repository):
        """Test listing documents in a session."""
        session_id = "test_session"

        # Create multiple documents
        documents = []
        for i in range(3):
            doc = Document(
                name=f"doc_{i}",
                session_id=session_id,
                document_type=DocumentType.SCRATCHPAD,
                content=f"Content {i}",
                description=f"Document {i}",
                version=1,
            )
            documents.append(doc)
            fs_repository.save_document(doc)

        # List documents
        listed_docs = fs_repository.list_session_documents(session_id)

        assert len(listed_docs) == 3
        doc_names = {doc.name for doc in listed_docs}
        expected_names = {f"doc_{i}" for i in range(3)}
        assert doc_names == expected_names

    @pytest.mark.unit
    def test_delete_document(self, fs_repository, sample_document):
        """Test deleting a document."""
        # Save document first
        fs_repository.save_document(sample_document)
        assert fs_repository.document_exists(
            sample_document.name, sample_document.session_id
        )

        # Delete document
        fs_repository.delete_document(sample_document.name, sample_document.session_id)

        # Verify deletion
        assert not fs_repository.document_exists(
            sample_document.name, sample_document.session_id
        )

    @pytest.mark.unit
    def test_session_directory_creation(self, fs_repository):
        """Test that session directories are created automatically."""
        session_id = "new_session"
        doc = Document(
            name="test_doc",
            session_id=session_id,
            document_type=DocumentType.DELIVERABLE,
            content="Content",
            description="Test",
            version=1,
        )

        # Session directory should not exist initially
        session_path = Path(fs_repository.workspace_path) / session_id
        assert not session_path.exists()

        # Save document
        fs_repository.save_document(doc)

        # Session directory should now exist
        assert session_path.exists()
        assert session_path.is_dir()

    @pytest.mark.integration
    def test_registry_file_management(self, fs_repository, sample_document):
        """Test that registry files are properly managed."""
        # Save document
        fs_repository.save_document(sample_document)

        # Check that registry file is created
        registry_path = (
            Path(fs_repository.workspace_path)
            / sample_document.session_id
            / "artifact_registry.json"
        )
        assert registry_path.exists()

        # Verify registry content
        with open(registry_path) as f:
            registry_data = json.load(f)
            assert sample_document.name in registry_data.get("artifacts", {})

    @pytest.mark.unit
    def test_invalid_document_name_handling(self, fs_repository):
        """Test handling of invalid document names."""
        # Test with invalid characters
        invalid_doc = Document(
            name="../../../etc/passwd",  # Path traversal attempt
            session_id="test_session",
            document_type=DocumentType.SCRATCHPAD,
            content="Malicious content",
            description="Bad document",
            version=1,
        )

        # Should either sanitize the name or raise an error
        with pytest.raises((ValueError, OSError)):
            fs_repository.save_document(invalid_doc)

    @pytest.mark.performance
    def test_large_document_handling(self, fs_repository):
        """Test handling of large documents."""
        # Create a large document (1MB content)
        large_content = "x" * (1024 * 1024)
        large_doc = Document(
            name="large_doc",
            session_id="test_session",
            document_type=DocumentType.SCRATCHPAD,
            content=large_content,
            description="Large document test",
            version=1,
        )

        # Should handle large documents gracefully
        fs_repository.save_document(large_doc)

        # Verify it can be loaded back
        loaded_doc = fs_repository.load_document("large_doc", "test_session")
        assert len(loaded_doc.content) == len(large_content)
        assert loaded_doc.content == large_content
