"""Tests for the ArtifactsService."""

import tempfile
from pathlib import Path

import pytest

from khive.services.artifacts.exceptions import (DocumentAlreadyExists,
                                                 DocumentNotFound)
from khive.services.artifacts.factory import (ArtifactsConfig,
                                              create_artifacts_service)
from khive.services.artifacts.models import Author, DocumentType
from khive.services.artifacts.service import ArtifactsService


class TestArtifactsService:
    """Test the main ArtifactsService class."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def artifacts_service(self, temp_workspace):
        """Create an ArtifactsService instance."""
        config = ArtifactsConfig(workspace_root=temp_workspace)
        return create_artifacts_service(config)

    @pytest.fixture
    def test_session_id(self):
        """Return a test session ID."""
        return "test_session_123"

    @pytest.mark.unit
    def test_service_initialization(self, artifacts_service):
        """Test that ArtifactsService initializes correctly."""
        assert artifacts_service is not None
        assert hasattr(artifacts_service, "create_session")
        assert hasattr(artifacts_service, "create_document")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_session(self, artifacts_service, test_session_id):
        """Test creating a new session."""
        session = await artifacts_service.create_session(test_session_id)
        assert session is not None
        assert session.id == test_session_id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_document_in_session(self, artifacts_service, test_session_id):
        """Test creating a document within a session."""
        # First create a session
        await artifacts_service.create_session(test_session_id)

        # Create a document
        document_name = "test_document"
        content = "Test document for validation"

        document = await artifacts_service.create_document(
            session_id=test_session_id,
            doc_name=document_name,
            doc_type=DocumentType.SCRATCHPAD,
            content=content,
        )

        assert document is not None
        assert document.name == document_name
        assert document.session_id == test_session_id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_document_not_found_error(self, artifacts_service, test_session_id):
        """Test that DocumentNotFound is raised for non-existent documents."""
        await artifacts_service.create_session(test_session_id)

        with pytest.raises(DocumentNotFound):
            await artifacts_service.get_document(
                session_id=test_session_id,
                doc_name="nonexistent_doc",
                doc_type=DocumentType.SCRATCHPAD,
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_duplicate_document_error(self, artifacts_service, test_session_id):
        """Test that DocumentAlreadyExists is raised for duplicate documents."""
        await artifacts_service.create_session(test_session_id)

        # Create first document
        document_name = "duplicate_test"
        await artifacts_service.create_document(
            session_id=test_session_id,
            doc_name=document_name,
            doc_type=DocumentType.SCRATCHPAD,
            content="Test content",
        )

        # Attempt to create duplicate should raise error
        with pytest.raises(DocumentAlreadyExists):
            await artifacts_service.create_document(
                session_id=test_session_id,
                doc_name=document_name,
                doc_type=DocumentType.SCRATCHPAD,
                content="Duplicate content",
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_session_documents(self, artifacts_service, test_session_id):
        """Test listing documents in a session."""
        await artifacts_service.create_session(test_session_id)

        # Create multiple documents
        doc_names = ["doc1", "doc2", "doc3"]
        for name in doc_names:
            await artifacts_service.create_document(
                session_id=test_session_id,
                doc_name=name,
                doc_type=DocumentType.SCRATCHPAD,
                content=f"Content for {name}",
            )

        # List documents
        document_names = await artifacts_service.list_documents(
            session_id=test_session_id, doc_type=DocumentType.SCRATCHPAD
        )
        # Get actual document objects
        documents = []
        for name in document_names:
            doc = await artifacts_service.get_document(
                session_id=test_session_id,
                doc_name=name,
                doc_type=DocumentType.SCRATCHPAD,
            )
            documents.append(doc)

        assert len(documents) == len(doc_names)
        retrieved_names = [doc.name for doc in documents]
        for name in doc_names:
            assert name in retrieved_names

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_session_isolation(self, artifacts_service):
        """Test that documents are properly isolated between sessions."""
        session1_id = "session_1"
        session2_id = "session_2"

        # Create two sessions
        await artifacts_service.create_session(session1_id)
        await artifacts_service.create_session(session2_id)

        # Create documents in each session
        await artifacts_service.create_document(
            session_id=session1_id,
            doc_name="doc1",
            doc_type=DocumentType.SCRATCHPAD,
            content="Content 1",
        )
        await artifacts_service.create_document(
            session_id=session2_id,
            doc_name="doc2",
            doc_type=DocumentType.SCRATCHPAD,
            content="Content 2",
        )

        # Check isolation
        session1_names = await artifacts_service.list_documents(
            session_id=session1_id, doc_type=DocumentType.SCRATCHPAD
        )
        session2_names = await artifacts_service.list_documents(
            session_id=session2_id, doc_type=DocumentType.SCRATCHPAD
        )

        # Get actual documents
        session1_docs = []
        for name in session1_names:
            doc = await artifacts_service.get_document(
                session_id=session1_id, doc_name=name, doc_type=DocumentType.SCRATCHPAD
            )
            session1_docs.append(doc)

        session2_docs = []
        for name in session2_names:
            doc = await artifacts_service.get_document(
                session_id=session2_id, doc_name=name, doc_type=DocumentType.SCRATCHPAD
            )
            session2_docs.append(doc)

        assert len(session1_docs) == 1
        assert len(session2_docs) == 1
        assert session1_docs[0].name == "doc1"
        assert session2_docs[0].name == "doc2"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_document_content(self, artifacts_service, test_session_id):
        """Test updating document content."""
        await artifacts_service.create_session(test_session_id)

        # Create document
        doc_name = "updateable_doc"
        original_content = "Original content"
        document = await artifacts_service.create_document(
            session_id=test_session_id,
            doc_name=doc_name,
            doc_type=DocumentType.SCRATCHPAD,
            content=original_content,
        )

        # Update content
        new_content = "Updated content"
        test_author = Author(id="test_updater", role="tester")
        updated_doc = await artifacts_service.update_document(
            session_id=test_session_id,
            doc_name=doc_name,
            doc_type=DocumentType.SCRATCHPAD,
            new_content=new_content,
            author=test_author,
        )

        assert updated_doc.content == new_content
        assert updated_doc.version > document.version

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_document_metadata_validation(
        self, artifacts_service, test_session_id
    ):
        """Test that document metadata is properly validated."""
        await artifacts_service.create_session(test_session_id)

        # Test with valid metadata and author
        test_author = Author(id="test_user", role="tester")
        document = await artifacts_service.create_document(
            session_id=test_session_id,
            doc_name="metadata_doc",
            doc_type=DocumentType.SCRATCHPAD,
            content="Test content with metadata",
            author=test_author,
        )

        # Check that document has contributions with the author
        assert len(document.contributions) > 0
        assert document.contributions[0].author == test_author
        assert document.name == "metadata_doc"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_document_operations(
        self, artifacts_service, test_session_id
    ):
        """Test handling of concurrent document operations."""
        import asyncio

        await artifacts_service.create_session(test_session_id)

        # Create base document
        await artifacts_service.create_document(
            session_id=test_session_id,
            doc_name="concurrent_doc",
            doc_type=DocumentType.SCRATCHPAD,
            content="Base content",
        )

        results = []
        errors = []

        async def update_document(content_suffix):
            try:
                test_author = Author(id=f"test_author_{content_suffix}", role="tester")
                updated_doc = await artifacts_service.update_document(
                    session_id=test_session_id,
                    doc_name="concurrent_doc",
                    doc_type=DocumentType.SCRATCHPAD,
                    new_content=f"Content {content_suffix}",
                    author=test_author,
                )
                results.append(updated_doc.version)
            except Exception as e:
                errors.append(e)

        # Run concurrent updates
        tasks = [update_document(i) for i in range(3)]
        await asyncio.gather(*tasks)

        # Verify results
        assert len(errors) == 0  # No errors should occur
        assert len(results) == 3  # All updates should succeed
        assert len(set(results)) == 3  # All versions should be unique


class TestArtifactsServiceFactory:
    """Test the artifacts service factory function."""

    @pytest.mark.unit
    def test_factory_creates_service(self):
        """Test that factory creates a valid service instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ArtifactsConfig(workspace_root=Path(temp_dir))
            service = create_artifacts_service(config)

            assert isinstance(service, ArtifactsService)

    @pytest.mark.unit
    def test_factory_with_invalid_workspace(self):
        """Test factory behavior with invalid workspace path."""
        config = ArtifactsConfig(workspace_root=Path("/invalid/nonexistent/path"))

        # Should handle invalid path gracefully
        with pytest.raises((ValueError, OSError)):
            create_artifacts_service(config)
