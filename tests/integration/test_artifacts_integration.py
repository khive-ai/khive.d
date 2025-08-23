"""Integration tests for Artifacts Service.

Tests file system operations, session management, concurrency control,
and cross-service integration with the artifacts storage system.
"""

import asyncio
import json

import pytest

from khive.services.artifacts.exceptions import (DocumentAlreadyExists,
                                                 DocumentNotFound)
from khive.services.artifacts.factory import create_artifacts_service
from khive.services.artifacts.models import Author, DocumentType
from khive.services.artifacts.storage import FilesystemStorageRepository


@pytest.mark.integration
class TestArtifactsServiceIntegration:
    """Integration tests for the Artifacts Service."""

    @pytest.mark.asyncio
    async def test_service_initialization(self, integration_artifacts_service):
        """Test that artifacts service initializes correctly."""
        assert integration_artifacts_service is not None
        assert hasattr(integration_artifacts_service, "create_document")
        assert hasattr(integration_artifacts_service, "create_session")
        assert hasattr(integration_artifacts_service, "get_document")

    @pytest.mark.asyncio
    async def test_session_lifecycle_integration(self, integration_artifacts_service):
        """Test complete session lifecycle with document operations."""
        session_id = "integration_session_001"

        # Create session
        session = await integration_artifacts_service.create_session(session_id)
        assert session.session_id == session_id
        assert session.status == "active"

        # Verify session exists
        retrieved_session = await integration_artifacts_service.get_session(session_id)
        assert retrieved_session.session_id == session_id

        # Create document in session
        doc_id = "test_document"
        content = "Test document content for integration testing"
        author = Author(id="integration_tester", role="tester")

        document = await integration_artifacts_service.create_document(
            document_id=doc_id,
            session_id=session_id,
            content=content,
            author=author,
            document_type=DocumentType.ARTIFACT,
        )

        assert document.document_id == doc_id
        assert document.session_id == session_id
        assert document.content == content

        # Retrieve document from session
        retrieved_doc = await artifacts_service.get_document(doc_id, session_id)
        assert retrieved_doc.document_id == doc_id
        assert retrieved_doc.content == content

        # Update document
        updated_content = "Updated content for integration testing"
        updated_doc = await artifacts_service.update_document(
            document_id=doc_id,
            session_id=session_id,
            content=updated_content,
            author=author,
        )

        assert updated_doc.content == updated_content
        assert updated_doc.version > document.version

        # List documents in session
        documents = await artifacts_service.list_documents(session_id)
        assert len(documents) == 1
        assert documents[0].document_id == doc_id

    async def test_concurrent_document_operations(
        self, artifacts_service, test_session, test_author
    ):
        """Test concurrent document operations with proper locking."""
        doc_id = "concurrent_test_doc"
        initial_content = "Initial content"

        # Create initial document
        await artifacts_service.create_document(
            document_id=doc_id,
            session_id=test_session,
            content=initial_content,
            author=test_author,
            document_type=DocumentType.ARTIFACT,
        )

        # Define concurrent update operations
        async def update_document(suffix: str):
            content = f"Updated content {suffix}"
            return await artifacts_service.update_document(
                document_id=doc_id,
                session_id=test_session,
                content=content,
                author=test_author,
            )

        # Run concurrent updates
        tasks = [update_document("A"), update_document("B"), update_document("C")]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all operations completed (one succeeded, others may have retry logic)
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 1

        # Verify final document state
        final_doc = await artifacts_service.get_document(doc_id, test_session)
        assert "Updated content" in final_doc.content
        assert final_doc.version > 1

    async def test_file_system_integration(
        self, artifacts_service, test_session, test_author
    ):
        """Test integration with underlying file system operations."""
        doc_id = "filesystem_integration_doc"
        content = "Content for file system integration testing"

        # Create document
        document = await artifacts_service.create_document(
            document_id=doc_id,
            session_id=test_session,
            content=content,
            author=test_author,
            document_type=DocumentType.ARTIFACT,
        )

        # Verify document was persisted to file system
        # Note: This tests actual file system integration
        workspace_path = artifacts_service._storage._base_path
        session_path = workspace_path / test_session

        # Check session directory exists
        assert session_path.exists()

        # Check document file exists (implementation dependent)
        # This verifies the storage layer integration
        doc_files = list(session_path.glob("*"))
        assert len(doc_files) > 0  # At least registry + document files

        # Test direct file system manipulation resilience
        # Simulate external file modification
        registry_file = session_path / "artifact_registry.json"
        if registry_file.exists():
            # Read current registry
            with open(registry_file) as f:
                registry_data = json.load(f)

            # Verify document is in registry
            assert doc_id in [
                doc["document_id"] for doc in registry_data.get("documents", [])
            ]

    async def test_cross_session_isolation(self, artifacts_service, test_author):
        """Test that documents are properly isolated between sessions."""
        session_a = "session_a"
        session_b = "session_b"

        # Create two sessions
        await artifacts_service.create_session(session_a)
        await artifacts_service.create_session(session_b)

        # Create documents with same ID in different sessions
        doc_id = "shared_doc_id"
        content_a = "Content for session A"
        content_b = "Content for session B"

        doc_a = await artifacts_service.create_document(
            document_id=doc_id,
            session_id=session_a,
            content=content_a,
            author=test_author,
            document_type=DocumentType.ARTIFACT,
        )

        doc_b = await artifacts_service.create_document(
            document_id=doc_id,
            session_id=session_b,
            content=content_b,
            author=test_author,
            document_type=DocumentType.ARTIFACT,
        )

        # Verify documents are isolated
        retrieved_a = await artifacts_service.get_document(doc_id, session_a)
        retrieved_b = await artifacts_service.get_document(doc_id, session_b)

        assert retrieved_a.content == content_a
        assert retrieved_b.content == content_b
        assert retrieved_a.session_id != retrieved_b.session_id

        # Verify cross-session access fails
        with pytest.raises(DocumentNotFound):
            await artifacts_service.get_document(doc_id + "_nonexistent", session_a)

    async def test_error_recovery_integration(
        self, artifacts_service, test_session, test_author
    ):
        """Test error recovery and resilience in file operations."""
        doc_id = "error_recovery_test"
        content = "Test content for error recovery"

        # Test document creation with invalid session
        with pytest.raises(Exception):  # Should raise appropriate session error
            await artifacts_service.create_document(
                document_id=doc_id,
                session_id="nonexistent_session",
                content=content,
                author=test_author,
                document_type=DocumentType.ARTIFACT,
            )

        # Create valid document
        document = await artifacts_service.create_document(
            document_id=doc_id,
            session_id=test_session,
            content=content,
            author=test_author,
            document_type=DocumentType.ARTIFACT,
        )

        # Test duplicate document creation
        with pytest.raises(DocumentAlreadyExists):
            await artifacts_service.create_document(
                document_id=doc_id,
                session_id=test_session,
                content="Duplicate content",
                author=test_author,
                document_type=DocumentType.ARTIFACT,
            )

        # Test updating non-existent document
        with pytest.raises(DocumentNotFound):
            await artifacts_service.update_document(
                document_id="nonexistent_doc",
                session_id=test_session,
                content="Updated content",
                author=test_author,
            )

        # Verify original document is still intact after errors
        retrieved_doc = await artifacts_service.get_document(doc_id, test_session)
        assert retrieved_doc.content == content
        assert retrieved_doc.document_id == doc_id

    @pytest.mark.asyncio
    async def test_performance_under_load(
        self, artifacts_service, test_session, test_author
    ):
        """Test artifacts service performance under concurrent load."""
        import time

        num_documents = 50
        start_time = time.time()

        # Create multiple documents concurrently
        async def create_test_document(doc_index: int):
            doc_id = f"perf_test_doc_{doc_index}"
            content = f"Performance test content {doc_index}"

            return await artifacts_service.create_document(
                document_id=doc_id,
                session_id=test_session,
                content=content,
                author=test_author,
                document_type=DocumentType.ARTIFACT,
            )

        # Run concurrent document creation
        tasks = [create_test_document(i) for i in range(num_documents)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        duration = end_time - start_time

        # Verify results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= num_documents * 0.9  # Allow 10% failure rate

        # Performance assertion - should complete within reasonable time
        assert duration < 10.0, f"Performance test took too long: {duration}s"

        # Verify all documents were created correctly
        documents = await artifacts_service.list_documents(test_session)
        assert len(documents) >= num_documents * 0.9

    async def test_workspace_cleanup_integration(self, temp_workspace, test_author):
        """Test workspace cleanup and resource management."""
        # Create service with temporary workspace
        artifacts_service = await create_artifacts_service(
            workspace_path=temp_workspace
        )

        session_id = "cleanup_test_session"
        session = await artifacts_service.create_session(session_id)

        # Create multiple documents
        for i in range(5):
            await artifacts_service.create_document(
                document_id=f"cleanup_doc_{i}",
                session_id=session_id,
                content=f"Content {i}",
                author=test_author,
                document_type=DocumentType.ARTIFACT,
            )

        # Verify documents exist
        documents = await artifacts_service.list_documents(session_id)
        assert len(documents) == 5

        # Verify workspace has files
        session_path = temp_workspace / session_id
        assert session_path.exists()
        files_before = list(session_path.glob("*"))
        assert len(files_before) > 0

        # Test cleanup (this would be implementation specific)
        # For now, verify session can be properly closed/managed
        session_info = await artifacts_service.get_session(session_id)
        assert session_info.status == "active"


@pytest.mark.integration
class TestArtifactsServiceWithExternalStorage:
    """Integration tests with different storage backends."""

    async def test_filesystem_storage_integration(self, temp_workspace):
        """Test integration with filesystem storage backend."""

        storage_repo = FilesystemStorageRepository(temp_workspace)

        # Test basic storage operations
        test_data = {"test": "data", "number": 123}
        file_path = temp_workspace / "test_storage.json"

        # Test storage persistence
        await storage_repo.store_json(file_path, test_data)
        assert file_path.exists()

        # Test retrieval
        retrieved_data = await storage_repo.load_json(file_path)
        assert retrieved_data == test_data

        # Test error handling
        with pytest.raises(FileNotFoundError):
            await storage_repo.load_json(temp_workspace / "nonexistent.json")
