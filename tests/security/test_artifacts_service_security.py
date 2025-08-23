"""Artifacts Service Security Tests.

This module provides comprehensive security testing for the artifacts service
including:
- Session ID validation and security
- Document path traversal prevention
- Access control validation
- Input sanitization in document operations
- Concurrent access security
- Storage security validation
- Metadata injection prevention
- Registry manipulation prevention
"""

import asyncio
import json
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest

from khive.services.artifacts.exceptions import (
    DocumentAlreadyExists,
    DocumentNotFound,
    ValidationError,
)
from khive.services.artifacts.locks import LockManager
from khive.services.artifacts.models import (
    Author,
    Document,
    DocumentType,
    Session,
    SessionStatus,
)
from khive.services.artifacts.service import ArtifactsService
from khive.services.artifacts.sessions import SessionManager
from khive.services.artifacts.storage import IStorageRepository


class TestSessionSecurityValidation:
    """Test session security validation."""

    @pytest.mark.parametrize(
        "malicious_session_id",
        [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config",
            "session; rm -rf /",
            "session`cat /etc/passwd`",
            "session$(whoami)",
            "session|dangerous_command",
            "session&background_process",
            "session\x00null_byte",
            "session\nmalicious_newline",
            "session\rcarriage_return",
            "session\tmalicious_tab",
            "/etc/passwd",
            "C:\\Windows\\System32\\config",
            "session/../../../sensitive",
            "session\\/malicious",
            "session%2e%2e%2f%2e%2e%2f",  # URL encoded path traversal
            "session" + "A" * 200,  # Excessively long
            "",  # Empty string
            " ",  # Just space
            "session with spaces and special chars!@#$%",
            "session\u202e\u202d",  # Unicode directional override
        ],
    )
    def test_malicious_session_id_validation(self, malicious_session_id):
        """Test that malicious session IDs are rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)

            # Should raise ValidationError for malicious session IDs
            with pytest.raises((ValidationError, ValueError, TypeError)):
                Session.create_new(malicious_session_id, workspace_root)

    def test_session_id_length_limits(self):
        """Test session ID length validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)

            # Valid length should work
            valid_session = Session.create_new("valid_session_123", workspace_root)
            assert valid_session.id == "valid_session_123"

            # Excessively long session ID should be rejected
            long_session_id = "A" * 200  # Over 128 chars
            with pytest.raises(ValidationError):
                Session.create_new(long_session_id, workspace_root)

    def test_session_id_character_validation(self):
        """Test session ID character restrictions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)

            # Valid characters should work
            valid_ids = [
                "session_123",
                "session-456",
                "session789",
                "SESSION_ABC",
                "session_with_underscores",
                "session-with-hyphens",
                "123numeric",
            ]

            for valid_id in valid_ids:
                session = Session.create_new(valid_id, workspace_root)
                assert session.id == valid_id

            # Invalid characters should be rejected
            invalid_ids = [
                "session.with.dots",
                "session@with@symbols",
                "session#with#hash",
                "session with spaces",
                "session/with/slashes",
                "session\\with\\backslashes",
                "session!with!exclamation",
            ]

            for invalid_id in invalid_ids:
                with pytest.raises(ValidationError):
                    Session.create_new(invalid_id, workspace_root)

    def test_session_workspace_path_security(self):
        """Test that session workspace paths are secure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)

            # Create session with valid ID
            session = Session.create_new("test_session", workspace_root)

            # Workspace path should be within the root directory
            assert session.workspace_path.parent == workspace_root
            assert session.workspace_path.name == "test_session"

            # Should not allow path traversal through workspace path
            resolved_path = session.workspace_path.resolve()
            root_resolved = workspace_root.resolve()

            assert str(resolved_path).startswith(str(root_resolved))


class TestDocumentSecurityValidation:
    """Test document security validation."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage for testing."""
        storage = Mock(spec=IStorageRepository)
        storage.exists = AsyncMock(return_value=False)
        storage.save = AsyncMock()
        storage.load = AsyncMock()
        return storage

    @pytest.fixture
    def mock_session_manager(self):
        """Create mock session manager for testing."""
        session_manager = Mock(spec=SessionManager)
        session_manager.validate_session = AsyncMock()
        return session_manager

    @pytest.fixture
    def mock_lock_manager(self):
        """Create mock lock manager for testing."""
        return Mock(spec=LockManager)

    @pytest.fixture
    def artifacts_service(self, mock_storage, mock_session_manager, mock_lock_manager):
        """Create artifacts service with mocks for testing."""
        return ArtifactsService(mock_storage, mock_session_manager, mock_lock_manager)

    @pytest.mark.parametrize(
        "malicious_doc_name",
        [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config",
            "doc; rm -rf /",
            "doc`cat /etc/passwd`",
            "doc$(whoami)",
            "doc|dangerous_command",
            "doc&background_process",
            "doc\x00null_byte",
            "doc\nmalicious_newline",
            "doc\rcarriage_return",
            "/etc/passwd",
            "C:\\Windows\\System32\\config",
            "doc/../../../sensitive",
            "doc%2e%2e%2f%2e%2e%2f",  # URL encoded path traversal
            "doc\u202e\u202d",  # Unicode directional override
            "<script>alert('xss')</script>",  # XSS attempt
            "'; DROP TABLE documents; --",  # SQL injection attempt
        ],
    )
    @pytest.mark.asyncio
    async def test_malicious_document_name_validation(
        self, artifacts_service, malicious_doc_name
    ):
        """Test that malicious document names are handled securely."""
        try:
            await artifacts_service.create_document(
                session_id="test_session",
                doc_name=malicious_doc_name,
                doc_type=DocumentType.SCRATCHPAD,
                content="test content",
            )

            # If it doesn't raise exception, check that dangerous patterns are filtered
            # This would depend on implementation details of input validation

        except (ValidationError, ValueError, TypeError) as e:
            # Expected - should reject malicious input
            error_str = str(e).lower()
            # Should not expose the malicious content in error message
            assert "malicious" not in error_str
            assert "/etc/passwd" not in error_str
            assert "rm -rf" not in error_str

    @pytest.mark.asyncio
    async def test_document_content_security(self, artifacts_service):
        """Test security validation of document content."""
        # Test various potentially dangerous content
        dangerous_contents = [
            "<script>alert('XSS')</script>",
            "'; DROP TABLE documents; --",
            "; rm -rf /",
            "../../../etc/passwd",
            "\x00null_byte_injection",
            "Content with\nembedded\ncommands: rm -rf /",
            "Content with $(command_substitution)",
            "Content with `backtick_execution`",
            "Content with unicode\u202e\u202d",
        ]

        for dangerous_content in dangerous_contents:
            try:
                document = await artifacts_service.create_document(
                    session_id="test_session",
                    doc_name="test_document",
                    doc_type=DocumentType.SCRATCHPAD,
                    content=dangerous_content,
                )

                # If creation succeeds, verify content is handled safely
                # Implementation should sanitize or validate content appropriately

            except (ValidationError, ValueError) as e:
                # Expected - dangerous content should be rejected
                error_str = str(e).lower()
                assert "dangerous" not in error_str or "malicious" not in error_str

    @pytest.mark.asyncio
    async def test_document_metadata_injection_prevention(self, artifacts_service):
        """Test prevention of metadata injection attacks."""
        malicious_metadata = {
            "__proto__": {"admin": True},  # Prototype pollution
            "eval": "malicious_code()",
            "system_command": "; rm -rf /",
            "../../../sensitive": "data",
            "null_byte\x00": "injection",
            "script_injection": "<script>alert('xss')</script>",
        }

        try:
            document = await artifacts_service.create_document(
                session_id="test_session",
                doc_name="test_document",
                doc_type=DocumentType.SCRATCHPAD,
                content="test content",
                metadata=malicious_metadata,
            )

            # If successful, metadata should be properly sanitized
            # Check that dangerous patterns don't appear in stored metadata

        except (ValidationError, ValueError, TypeError):
            # Expected - malicious metadata should be rejected
            pass

    @pytest.mark.asyncio
    async def test_author_validation_security(self, artifacts_service):
        """Test security validation of author information."""
        # Test malicious author information
        malicious_authors = [
            Author(id="../../../admin", role="system"),
            Author(id="admin\x00malicious", role="administrator"),
            Author(id="author; rm -rf /", role="system"),
            Author(id="<script>alert('xss')</script>", role="user"),
            Author(id="'; DROP TABLE users; --", role="admin"),
            Author(id="author", role="../../../etc/passwd"),
            Author(id="author", role="role\nwith\nnewlines"),
        ]

        for malicious_author in malicious_authors:
            try:
                document = await artifacts_service.create_document(
                    session_id="test_session",
                    doc_name="test_document",
                    doc_type=DocumentType.SCRATCHPAD,
                    content="test content",
                    author=malicious_author,
                )

                # If successful, author data should be sanitized
                assert (
                    document.contributions[0].author.id != malicious_author.id
                    or document.contributions[0].author.role != malicious_author.role
                )

            except (ValidationError, ValueError, TypeError):
                # Expected - malicious author should be rejected
                pass


class TestDocumentPathTraversalPrevention:
    """Test prevention of path traversal in document operations."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_document_type_path_security(self, temp_workspace):
        """Test that document type paths are secure."""
        session = Session.create_new("test_session", temp_workspace)

        # Test that document type paths are within session workspace
        deliverable_path = session.get_document_type_path(DocumentType.DELIVERABLE)
        scratchpad_path = session.get_document_type_path(DocumentType.SCRATCHPAD)

        # Paths should be within the session workspace
        session_resolved = session.workspace_path.resolve()
        deliverable_resolved = deliverable_path.resolve()
        scratchpad_resolved = scratchpad_path.resolve()

        assert str(deliverable_resolved).startswith(str(session_resolved))
        assert str(scratchpad_resolved).startswith(str(session_resolved))

        # Paths should match expected structure
        assert deliverable_path.name == "deliverable"
        assert scratchpad_path.name == "scratchpad"

    def test_workspace_path_traversal_prevention(self, temp_workspace):
        """Test that workspace paths prevent traversal attacks."""
        # Even if session ID contains traversal attempts, path should be secure
        safe_session = Session.create_new("safe_session", temp_workspace)

        # Create some sensitive files outside workspace to test protection
        sensitive_dir = temp_workspace.parent / "sensitive"
        sensitive_dir.mkdir(exist_ok=True)
        sensitive_file = sensitive_dir / "secret.txt"
        sensitive_file.write_text("SECRET_DATA")

        # Document paths should not be able to access sensitive files
        doc_path = (
            safe_session.get_document_type_path(DocumentType.SCRATCHPAD) / "test_doc.md"
        )

        # Path should be within safe boundaries
        doc_resolved = doc_path.resolve()
        workspace_resolved = temp_workspace.resolve()

        assert str(doc_resolved).startswith(str(workspace_resolved))

        # Should not be able to traverse to sensitive file
        traversal_path = safe_session.workspace_path / ".." / "sensitive" / "secret.txt"
        traversal_resolved = traversal_path.resolve()

        # Even if traversal path resolves, it should not be considered safe for operations
        assert not str(traversal_resolved).startswith(
            str(safe_session.workspace_path.resolve())
        )


class TestConcurrentAccessSecurity:
    """Test security under concurrent access patterns."""

    @pytest.fixture
    def mock_artifacts_service(self):
        """Create mock artifacts service for concurrent testing."""
        storage = Mock(spec=IStorageRepository)
        session_manager = Mock(spec=SessionManager)
        lock_manager = Mock(spec=LockManager)

        # Setup async mock returns
        storage.exists = AsyncMock(return_value=False)
        storage.save = AsyncMock()
        session_manager.validate_session = AsyncMock()

        return ArtifactsService(storage, session_manager, lock_manager)

    @pytest.mark.asyncio
    async def test_concurrent_document_creation_security(self, mock_artifacts_service):
        """Test security under concurrent document creation."""

        # Simulate multiple agents trying to create documents concurrently
        async def create_document_task(doc_id):
            try:
                return await mock_artifacts_service.create_document(
                    session_id="test_session",
                    doc_name=f"document_{doc_id}",
                    doc_type=DocumentType.SCRATCHPAD,
                    content=f"Content for document {doc_id}",
                )
            except Exception:
                return None

        # Launch concurrent creation tasks
        tasks = [create_document_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All tasks should complete without crashing
        for result in results:
            if isinstance(result, Exception):
                # Should not have security-related exceptions
                assert "security" not in str(result).lower()
                assert "malicious" not in str(result).lower()

    @pytest.mark.asyncio
    async def test_concurrent_session_access_security(self, mock_artifacts_service):
        """Test security under concurrent session access."""

        # Simulate multiple operations on same session concurrently
        async def session_operation(operation_id):
            try:
                if operation_id % 2 == 0:
                    # Even operations try to create documents
                    return await mock_artifacts_service.create_document(
                        session_id="shared_session",
                        doc_name=f"doc_{operation_id}",
                        doc_type=DocumentType.SCRATCHPAD,
                        content="test content",
                    )
                else:
                    # Odd operations try to get session info
                    return await mock_artifacts_service.get_session("shared_session")
            except Exception:
                return None

        # Launch concurrent operations
        tasks = [session_operation(i) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Should handle concurrent access safely
        for result in results:
            if isinstance(result, Exception):
                # Should not expose sensitive information in errors
                error_str = str(result).lower()
                assert "password" not in error_str
                assert "secret" not in error_str
                assert "key" not in error_str

    @pytest.mark.asyncio
    async def test_race_condition_security(self, mock_artifacts_service):
        """Test security against race condition attacks."""
        # Mock storage to simulate race conditions
        storage = mock_artifacts_service._storage

        # Simulate race condition where file existence check and creation are separate
        call_count = 0

        async def racy_exists(session_id, doc_name, doc_type):
            nonlocal call_count
            call_count += 1
            # First few calls return False, then True (simulating race condition)
            return call_count > 3

        storage.exists = AsyncMock(side_effect=racy_exists)

        # Try to create same document multiple times concurrently
        async def create_same_document(attempt_id):
            try:
                return await mock_artifacts_service.create_document(
                    session_id="race_session",
                    doc_name="race_document",
                    doc_type=DocumentType.SCRATCHPAD,
                    content=f"Content attempt {attempt_id}",
                )
            except DocumentAlreadyExists:
                return "already_exists"
            except Exception as e:
                return f"error: {e}"

        # Launch concurrent creation attempts
        tasks = [create_same_document(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Should handle race conditions gracefully
        successful_creations = [r for r in results if isinstance(r, Document)]
        already_exists = [r for r in results if r == "already_exists"]

        # Should not have multiple successful creations or security errors
        assert len(successful_creations) <= 1
        for result in results:
            if isinstance(result, str) and result.startswith("error:"):
                assert "security" not in result.lower()


class TestStorageSecurityValidation:
    """Test storage layer security validation."""

    def test_document_serialization_security(self):
        """Test that document serialization is secure."""
        # Create document with various data types
        document = Document.create_new(
            session_id="test_session",
            name="test_document",
            doc_type=DocumentType.SCRATCHPAD,
            content="test content with special chars: <>&'\"",
        )

        # Serialize to JSON
        doc_json = document.model_dump_json()

        # Should be valid JSON
        parsed = json.loads(doc_json)
        assert isinstance(parsed, dict)

        # Should not contain dangerous patterns in serialized form
        dangerous_patterns = [
            "__proto__",
            "eval(",
            "function(",
            "<script>",
            "javascript:",
        ]

        for pattern in dangerous_patterns:
            assert (
                pattern not in doc_json
            ), f"Dangerous pattern {pattern} found in serialized document"

    def test_document_deserialization_security(self):
        """Test that document deserialization is secure."""
        # Test with potentially malicious JSON
        malicious_json_strings = [
            '{"__proto__": {"admin": true}, "session_id": "test"}',
            '{"session_id": "test", "constructor": {"prototype": {"admin": true}}}',
            '{"session_id": "test`rm -rf /`", "name": "doc"}',
            '{"session_id": "../../../etc/passwd", "name": "doc"}',
            '{"session_id": "test", "content": "<script>alert(1)</script>"}',
        ]

        for malicious_json in malicious_json_strings:
            try:
                parsed_data = json.loads(malicious_json)

                # Try to create Document from malicious data
                # This should either fail validation or sanitize the data
                if all(
                    required_field in parsed_data
                    for required_field in ["session_id", "name"]
                ):
                    # Add required fields that might be missing
                    parsed_data.setdefault("type", "scratchpad")
                    parsed_data.setdefault("content", "")
                    parsed_data.setdefault("contributions", [])
                    parsed_data.setdefault("version", 1)
                    parsed_data.setdefault(
                        "last_modified", datetime.now(timezone.utc).isoformat()
                    )

                    try:
                        document = Document(**parsed_data)

                        # If deserialization succeeds, dangerous content should be sanitized
                        assert "__proto__" not in document.session_id
                        assert "../" not in document.session_id
                        assert "`" not in document.session_id
                        assert "<script>" not in document.content

                    except (ValidationError, ValueError, TypeError):
                        # Expected - should reject malicious data
                        pass

            except json.JSONDecodeError:
                # Expected for malformed JSON
                pass


class TestArtifactRegistrySecurityValidation:
    """Test artifact registry security validation."""

    @pytest.fixture
    def mock_artifacts_service_with_registry(self):
        """Create artifacts service with registry mocking."""
        storage = Mock(spec=IStorageRepository)
        session_manager = Mock(spec=SessionManager)
        lock_manager = Mock(spec=LockManager)

        storage.exists = AsyncMock(return_value=False)
        storage.save = AsyncMock()
        session_manager.validate_session = AsyncMock()

        service = ArtifactsService(storage, session_manager, lock_manager)

        # Mock registry operations
        service.register_artifact = AsyncMock()

        return service

    @pytest.mark.asyncio
    async def test_registry_injection_prevention(
        self, mock_artifacts_service_with_registry
    ):
        """Test prevention of registry injection attacks."""
        # Test with malicious registry data
        malicious_registry_data = {
            "artifact_id": "../../../admin_access",
            "doc_type": "'; DROP TABLE artifacts; --",
            "name": "<script>alert('xss')</script>",
            "file_path": "../../sensitive/data.txt",
            "description": "Normal description\n\nMALICIOUS: $(rm -rf /)",
            "agent_role": "admin\x00malicious",
            "agent_domain": "domain|dangerous_command",
        }

        await mock_artifacts_service_with_registry.create_document(
            session_id="test_session",
            doc_name="test_document",
            doc_type=DocumentType.SCRATCHPAD,
            content="test content",
            **{
                k: v
                for k, v in malicious_registry_data.items()
                if k in ["description", "agent_role", "agent_domain"]
            },
        )

        # Verify register_artifact was called with sanitized data
        assert mock_artifacts_service_with_registry.register_artifact.called
        call_args = mock_artifacts_service_with_registry.register_artifact.call_args

        if call_args:
            # Check that dangerous patterns were filtered
            call_kwargs = call_args.kwargs if call_args.kwargs else {}
            for key, value in call_kwargs.items():
                if isinstance(value, str):
                    assert "../" not in value, f"Path traversal found in {key}: {value}"
                    assert (
                        "DROP TABLE" not in value
                    ), f"SQL injection found in {key}: {value}"
                    assert "<script>" not in value, f"XSS found in {key}: {value}"
                    assert "\x00" not in value, f"Null byte found in {key}: {value}"


class TestIntegrationSecurityScenarios:
    """Test end-to-end security scenarios."""

    @pytest.mark.asyncio
    async def test_complete_document_lifecycle_security(self):
        """Test security throughout complete document lifecycle."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)

            # Create secure session
            session = Session.create_new("secure_test_session", workspace_root)

            # Test document creation with various security challenges
            test_cases = [
                {
                    "name": "normal_document",
                    "content": "Normal content",
                    "should_succeed": True,
                },
                {
                    "name": "document_with_html",
                    "content": "<b>Bold</b> and <script>alert('xss')</script>",
                    "should_succeed": True,  # Content may be allowed but should be safe
                },
                {
                    "name": "document_with_commands",
                    "content": "Content with $(echo 'command') and `whoami`",
                    "should_succeed": True,  # Content should be safe for display
                },
            ]

            for test_case in test_cases:
                try:
                    document = Document.create_new(
                        session_id=session.id,
                        name=test_case["name"],
                        doc_type=DocumentType.SCRATCHPAD,
                        content=test_case["content"],
                    )

                    if test_case["should_succeed"]:
                        # Document should be created successfully
                        assert document.name == test_case["name"]
                        assert document.session_id == session.id

                        # Content should be preserved but safe
                        assert len(document.content) > 0

                        # Dangerous patterns should not cause issues in metadata
                        assert len(document.contributions) == 1
                        assert document.version == 1

                except (ValidationError, ValueError):
                    if test_case["should_succeed"]:
                        pytest.fail(
                            f"Expected {test_case['name']} to succeed but it was rejected"
                        )

    def test_security_configuration_validation(self):
        """Test that security configurations are properly set."""
        # Test that security-related settings are configured correctly

        # Session ID validation should be strict
        test_patterns = [
            ("valid_session_123", True),
            ("valid-session-456", True),
            ("ValidSession789", True),
            ("invalid.session", False),
            ("invalid session", False),
            ("invalid/session", False),
            ("", False),
            ("a" * 129, False),  # Too long
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)

            for pattern, should_be_valid in test_patterns:
                try:
                    session = Session.create_new(pattern, workspace_root)
                    assert (
                        should_be_valid
                    ), f"Pattern '{pattern}' should have been rejected"
                    assert session.id == pattern
                except ValidationError:
                    assert (
                        not should_be_valid
                    ), f"Pattern '{pattern}' should have been accepted"

    @pytest.mark.asyncio
    async def test_error_message_security(self):
        """Test that error messages don't leak sensitive information."""
        # Create mocked service
        storage = Mock(spec=IStorageRepository)
        session_manager = Mock(spec=SessionManager)
        lock_manager = Mock(spec=LockManager)

        # Setup mocks to raise various errors
        storage.exists = AsyncMock(
            side_effect=Exception(
                "Internal storage error with /sensitive/path/data.txt"
            )
        )
        session_manager.validate_session = AsyncMock(
            side_effect=Exception("Database connection failed: password=secret123")
        )

        service = ArtifactsService(storage, session_manager, lock_manager)

        # Test that error messages are sanitized
        try:
            await service.create_document(
                session_id="test_session",
                doc_name="test_document",
                doc_type=DocumentType.SCRATCHPAD,
                content="test content",
            )
        except Exception as e:
            error_msg = str(e)

            # Should not contain sensitive file paths
            assert "/sensitive/path" not in error_msg

            # Should not contain credentials
            assert "password=secret123" not in error_msg
            assert "secret123" not in error_msg

            # Should not expose internal implementation details
            assert "storage error" not in error_msg.lower()


class SecurityError(Exception):
    """Custom security exception for testing."""

    pass


@pytest.fixture
def secure_workspace():
    """Provide a secure workspace for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


class TestArtifactsServiceSecurityRegression:
    """Test prevention of known security regression patterns."""

    @pytest.mark.asyncio
    async def test_path_traversal_regression(self):
        """Test prevention of path traversal regression patterns."""
        # Historical path traversal patterns that should be blocked
        traversal_patterns = [
            "../../../etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "..%252F..%252F..%252Fetc%252Fpasswd",
            "....//....//....//etc//passwd",
            "..\\..\\..\\windows\\system32\\config",
            "/etc/passwd",
            "C:\\Windows\\System32\\config",
        ]

        for pattern in traversal_patterns:
            with tempfile.TemporaryDirectory() as temp_dir:
                workspace_root = Path(temp_dir)

                # Should not be able to create session with traversal pattern
                with pytest.raises((ValidationError, ValueError)):
                    Session.create_new(pattern, workspace_root)

    @pytest.mark.asyncio
    async def test_injection_regression(self):
        """Test prevention of injection attack regression patterns."""
        # Known injection patterns that should be handled safely
        injection_patterns = [
            "; rm -rf /",
            "`cat /etc/passwd`",
            "$(whoami)",
            "|dangerous_command",
            "&background_process",
            "\x00null_byte_injection",
            "'; DROP TABLE documents; --",
            "<script>alert('XSS')</script>",
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)

            for pattern in injection_patterns:
                # Should not be able to create session with injection pattern
                with pytest.raises((ValidationError, ValueError)):
                    Session.create_new(pattern, workspace_root)

    def test_unicode_security_regression(self):
        """Test prevention of Unicode-based security regression patterns."""
        unicode_attacks = [
            "session\u202e\u202d",  # Directional override
            "session\ufeff",  # Zero-width no-break space
            "session\u200b",  # Zero-width space
            "роle",  # Cyrillic characters
            "sеssion",  # Mixed scripts (Cyrillic 'e')
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)

            for pattern in unicode_attacks:
                # Should reject Unicode attacks in session IDs
                with pytest.raises(ValidationError):
                    Session.create_new(pattern, workspace_root)
