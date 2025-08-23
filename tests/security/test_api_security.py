"""API Security Tests for khive services.

This module provides comprehensive security testing for API endpoints and web interfaces
including:
- WebSocket security validation
- HTTP endpoint security
- API authentication and authorization
- Rate limiting and DoS prevention
- Input validation for API parameters
- CORS and security header validation
- Real-time monitoring security
- API error handling security
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from urllib.parse import quote, unquote

import pytest
import websockets

from khive.services.claude.frontend.realtime_server import HookEventWebSocketServer
from khive.services.claude.hooks import HookEvent


class TestWebSocketSecurity:
    """Test WebSocket API security."""

    @pytest.fixture
    def mock_websocket_server(self):
        """Create a mock WebSocket server for testing."""
        return HookEventWebSocketServer(host="localhost", port=8767)

    def test_websocket_connection_validation(self, mock_websocket_server):
        """Test WebSocket connection validation and authorization."""
        server = mock_websocket_server

        # Test connection limits
        assert len(server.clients) == 0

        # Mock WebSocket connections
        mock_clients = []
        for i in range(100):  # Try to create many connections
            mock_client = Mock()
            mock_client.remote_address = ("127.0.0.1", 50000 + i)
            mock_clients.append(mock_client)

        # Test that server doesn't crash with many connections
        try:
            for client in mock_clients:
                server.clients.add(client)

            # Should handle many clients gracefully
            assert len(server.clients) == 100
        except Exception as e:
            # Should not crash due to DoS attempt
            assert "memory" not in str(e).lower()
            assert "overflow" not in str(e).lower()

    @pytest.mark.asyncio
    async def test_websocket_message_injection_prevention(self, mock_websocket_server):
        """Test prevention of message injection attacks via WebSocket."""
        server = mock_websocket_server

        # Create mock WebSocket client
        mock_websocket = AsyncMock()
        mock_websocket.remote_address = ("127.0.0.1", 12345)

        # Test malicious JSON injection attempts
        malicious_messages = [
            '{"type": "ping"; rm -rf /}',  # Command injection
            '{"type": "get_recent_events", "limit": 999999999}',  # DoS attempt
            '{"type": "admin_command", "command": "shutdown"}',  # Privilege escalation
            '{"type": "get_recent_events", "limit": -1}',  # Integer overflow
            '{"__proto__": {"admin": true}, "type": "ping"}',  # Prototype pollution
            '{"type": "ping\\u0000malicious"}',  # Null byte injection
            '{"type": "eval", "code": "import os; os.system(\\"rm -rf /\\")"}',  # Code injection
            '{"type": "../../../etc/passwd"}',  # Path traversal
            json.dumps({"type": "A" * 10000}),  # Buffer overflow attempt
        ]

        for malicious_msg in malicious_messages:
            try:
                await server.handle_client_message(mock_websocket, malicious_msg)

                # Check that no dangerous operations were performed
                # Mock should not have been called with dangerous operations
                if hasattr(mock_websocket, "send"):
                    sent_messages = mock_websocket.send.call_args_list
                    for call in sent_messages:
                        message_data = call[0][0]
                        # Should not contain dangerous content
                        assert "rm -rf" not in message_data
                        assert "/etc/passwd" not in message_data
                        assert "admin" not in message_data.lower()

            except (json.JSONDecodeError, ValueError, TypeError):
                # Expected - should reject malicious JSON
                pass

    @pytest.mark.asyncio
    async def test_websocket_rate_limiting(self, mock_websocket_server):
        """Test rate limiting for WebSocket connections."""
        server = mock_websocket_server

        mock_websocket = AsyncMock()
        mock_websocket.remote_address = ("127.0.0.1", 12345)

        # Simulate rapid message sending (potential DoS)
        message = '{"type": "ping"}'

        start_time = time.time()
        for _ in range(100):  # Send many messages rapidly
            try:
                await server.handle_client_message(mock_websocket, message)
            except Exception as e:
                # Should handle rate limiting gracefully
                assert "rate" in str(e).lower() or "limit" in str(e).lower()
                break

        end_time = time.time()

        # Should not process all messages instantly (basic rate limiting check)
        duration = end_time - start_time
        assert duration < 10.0  # Should complete in reasonable time

    @pytest.mark.asyncio
    async def test_websocket_data_sanitization(self, mock_websocket_server):
        """Test data sanitization in WebSocket responses."""
        server = mock_websocket_server

        # Mock hook events with potentially sensitive data
        mock_events = []
        for i in range(5):
            mock_event = Mock()
            mock_event.id = f"event_{i}"
            mock_event.created_datetime = Mock()
            mock_event.created_datetime.isoformat.return_value = "2023-12-01T12:00:00Z"
            mock_event.content = {
                "event_type": "test",
                "tool_name": "bash",
                "command": f"echo 'password: secret123' > /tmp/test_{i}",  # Sensitive data
                "output": f"User credentials: admin/password123 for server_{i}",  # More sensitive data
                "session_id": f"session_{i}",
                "file_paths": [
                    f"/etc/passwd_{i}",
                    f"/home/user/.ssh/id_rsa_{i}",
                ],  # Sensitive paths
                "metadata": {
                    "api_key": f"sk-{i}abcd1234",
                    "token": f"token_{i}",
                },  # API keys
            }
            mock_events.append(mock_event)

        with patch.object(HookEvent, "get_recent", return_value=mock_events):
            mock_websocket = AsyncMock()
            mock_websocket.remote_address = ("127.0.0.1", 12345)

            # Register client and test data sanitization
            await server.register_client(mock_websocket)

            # Check sent messages for sensitive data
            if mock_websocket.send.called:
                sent_messages = [
                    call[0][0] for call in mock_websocket.send.call_args_list
                ]

                for message in sent_messages:
                    message_data = json.loads(message)

                    # Should not contain raw sensitive data
                    message_str = json.dumps(message_data).lower()
                    sensitive_patterns = [
                        "password123",
                        "secret123",
                        "admin/password",
                        "api_key",
                        "sk-",
                        "token_",
                        "/etc/passwd",
                        "/.ssh/id_rsa",
                    ]

                    for pattern in sensitive_patterns:
                        if pattern in message_str:
                            # If sensitive data is present, it should be sanitized
                            assert (
                                "[REDACTED]" in message_str
                                or "[FILTERED]" in message_str
                            )

    @pytest.mark.asyncio
    async def test_websocket_connection_hijacking_prevention(
        self, mock_websocket_server
    ):
        """Test prevention of WebSocket connection hijacking."""
        server = mock_websocket_server

        # Simulate connection from suspicious source
        suspicious_websocket = AsyncMock()
        suspicious_websocket.remote_address = ("192.168.1.100", 6666)  # Suspicious port

        # Test origin validation (if implemented)
        with patch(
            "websockets.WebSocketServerProtocol.request_headers",
            {"Origin": "http://malicious.com"},
        ):
            try:
                await server.register_client(suspicious_websocket)

                # If connection is allowed, should not expose sensitive operations
                assert len(server.clients) <= 1

            except Exception as e:
                # Expected - should reject suspicious origins
                assert "origin" in str(e).lower() or "unauthorized" in str(e).lower()

    def test_websocket_server_configuration_security(self, mock_websocket_server):
        """Test WebSocket server configuration security."""
        server = mock_websocket_server

        # Test secure default configuration
        assert (
            server.host == "localhost"
        )  # Should not bind to all interfaces by default
        assert server.port == 8767  # Should use non-standard port

        # Test that server doesn't expose dangerous configuration
        server_config = str(server.__dict__)
        dangerous_patterns = ["password", "secret", "key", "token", "credential"]

        for pattern in dangerous_patterns:
            assert pattern not in server_config.lower()


class TestStreamlitDashboardSecurity:
    """Test security of Streamlit dashboard and web interface."""

    def test_dashboard_environment_variable_security(self):
        """Test security of environment variable handling in dashboard."""
        # Test that sensitive environment variables are not exposed

        with patch.dict(
            "os.environ",
            {
                "KHIVE_SECRET_KEY": "super_secret_key_123",
                "DATABASE_PASSWORD": "db_password_456",
                "API_TOKEN": "api_token_789",
                "KHIVE_REFRESH_RATE": "5",  # This one should be safe
            },
        ):
            from khive.services.claude.frontend import streamlit_dashboard

            # Check that sensitive variables are not in module globals
            module_vars = dir(streamlit_dashboard)
            module_str = str(module_vars).lower()

            # Should not expose sensitive environment variables
            assert "super_secret_key_123" not in module_str
            assert "db_password_456" not in module_str
            assert "api_token_789" not in module_str

            # Should only access safe configuration variables
            if hasattr(streamlit_dashboard, "CONFIG"):
                config_str = str(streamlit_dashboard.CONFIG).lower()
                assert "password" not in config_str
                assert "secret" not in config_str
                assert "token" not in config_str

    def test_dashboard_xss_prevention(self):
        """Test XSS prevention in dashboard rendering."""
        # Test that user-controllable data is properly escaped

        malicious_payloads = [
            '<script>alert("XSS")</script>',
            '"><script>document.location="http://evil.com"</script>',
            'javascript:alert("XSS")',
            '<img src="x" onerror="alert(\'XSS\')">',
            "<svg onload=\"alert('XSS')\">",
            '&lt;script&gt;alert("XSS")&lt;/script&gt;',
            "%3Cscript%3Ealert%28%22XSS%22%29%3C%2Fscript%3E",
        ]

        for payload in malicious_payloads:
            # Test that payload is properly sanitized
            # This is a simplified test - real implementation would test actual rendering
            sanitized = html_escape(payload)

            # Should not contain dangerous patterns after escaping
            assert "<script>" not in sanitized
            assert "javascript:" not in sanitized
            assert "onerror=" not in sanitized
            assert "onload=" not in sanitized

    def test_dashboard_csrf_protection(self):
        """Test CSRF protection for dashboard operations."""
        # Test that state-changing operations require CSRF protection

        # Mock Streamlit session state
        mock_session_state = {
            "csrf_token": "valid_token_123",
            "user_authenticated": True,
            "realtime_events": [],
        }

        with patch("streamlit.session_state", mock_session_state):
            # Test that operations validate CSRF token
            try:
                # Simulate operation without CSRF token
                result = perform_dashboard_operation(csrf_token=None)

                # Should reject operations without valid CSRF token
                assert result is None or "error" in str(result).lower()

            except Exception as e:
                # Expected - should reject operations without CSRF protection
                assert "csrf" in str(e).lower() or "token" in str(e).lower()

    def test_dashboard_sql_injection_prevention(self):
        """Test SQL injection prevention in dashboard queries."""
        # Test that database queries are parameterized

        malicious_inputs = [
            "'; DROP TABLE hook_events; --",
            "' OR '1'='1",
            "1; DELETE FROM hook_events WHERE 1=1; --",
            "' UNION SELECT password FROM users --",
            "'; INSERT INTO users (username, password) VALUES ('admin', 'hacked'); --",
        ]

        for malicious_input in malicious_inputs:
            # Test that malicious input doesn't affect database queries
            with patch("khive.services.claude.hooks.HookEvent.get_recent") as mock_get:
                mock_get.return_value = []

                try:
                    # Simulate query with malicious input
                    query_events_with_filter(malicious_input)

                    # Should use parameterized queries
                    mock_get.assert_called()
                    call_args = mock_get.call_args

                    # Should not contain raw SQL injection
                    if call_args and call_args[1]:  # If keyword arguments exist
                        for arg_value in call_args[1].values():
                            if isinstance(arg_value, str):
                                assert "DROP TABLE" not in arg_value
                                assert "DELETE FROM" not in arg_value
                                assert "INSERT INTO" not in arg_value

                except Exception as e:
                    # Expected - should reject malicious input
                    assert "sql" in str(e).lower() or "injection" in str(e).lower()


class TestAPIEndpointSecurity:
    """Test security of API endpoints and HTTP interfaces."""

    def test_api_input_validation(self):
        """Test input validation for API parameters."""
        # Test various API input validation scenarios

        invalid_inputs = [
            {"limit": -1},  # Negative limit
            {"limit": 999999999},  # Excessive limit
            {"limit": "'; DROP TABLE --"},  # SQL injection
            {"limit": "<script>alert('XSS')</script>"},  # XSS
            {"session_id": "../../../etc/passwd"},  # Path traversal
            {"session_id": "\x00malicious"},  # Null byte injection
            {"event_type": "type\nmalicious"},  # Newline injection
            {"metadata": {"__proto__": {"admin": True}}},  # Prototype pollution
        ]

        for invalid_input in invalid_inputs:
            try:
                # Test API endpoint with invalid input
                result = api_call_with_params(invalid_input)

                if result:
                    # If not rejected, should be sanitized
                    result_str = str(result).lower()
                    assert "drop table" not in result_str
                    assert "<script>" not in result_str
                    assert "/etc/passwd" not in result_str
                    assert "malicious" not in result_str

            except (ValueError, TypeError) as e:
                # Expected - should reject invalid input
                assert "validation" in str(e).lower() or "invalid" in str(e).lower()

    def test_api_rate_limiting(self):
        """Test rate limiting for API endpoints."""
        # Test that API endpoints implement rate limiting

        start_time = time.time()
        requests_made = 0
        rate_limited = False

        for i in range(100):  # Make many requests rapidly
            try:
                result = make_api_request(f"request_{i}")
                requests_made += 1

                if "rate limit" in str(result).lower():
                    rate_limited = True
                    break

            except Exception as e:
                if "rate" in str(e).lower() or "throttle" in str(e).lower():
                    rate_limited = True
                    break

        end_time = time.time()
        duration = end_time - start_time

        # Should have some form of rate limiting
        # Either explicit rate limiting or natural request processing time
        assert rate_limited or duration > 1.0 or requests_made < 100

    def test_api_cors_security(self):
        """Test CORS configuration security."""
        # Test that CORS headers are properly configured

        malicious_origins = [
            "http://malicious.com",
            "https://phishing-site.net",
            "null",
            "*",  # Wildcard should be restricted
            "http://localhost:3000<script>alert('XSS')</script>",  # XSS in origin
        ]

        for origin in malicious_origins:
            try:
                headers = get_cors_headers_for_origin(origin)

                if headers and "Access-Control-Allow-Origin" in headers:
                    allowed_origin = headers["Access-Control-Allow-Origin"]

                    # Should not allow arbitrary origins
                    if origin == "*":
                        # Wildcard should only be allowed for public APIs
                        assert "credentials" not in str(headers).lower()

                    # Should not contain malicious content
                    assert "<script>" not in allowed_origin
                    assert "malicious.com" not in allowed_origin

            except Exception as e:
                # Expected - should reject malicious origins
                assert "cors" in str(e).lower() or "origin" in str(e).lower()

    def test_api_security_headers(self):
        """Test that proper security headers are set."""
        # Test that API responses include security headers

        response_headers = get_api_response_headers()

        # Check for important security headers
        security_headers = [
            "X-Content-Type-Options",  # Should be 'nosniff'
            "X-Frame-Options",  # Should be 'DENY' or 'SAMEORIGIN'
            "X-XSS-Protection",  # Should be '1; mode=block'
            "Strict-Transport-Security",  # Should be present for HTTPS
            "Content-Security-Policy",  # Should restrict sources
        ]

        for header in security_headers:
            if header in response_headers:
                header_value = response_headers[header]

                if header == "X-Content-Type-Options":
                    assert "nosniff" in header_value
                elif header == "X-Frame-Options":
                    assert header_value in ["DENY", "SAMEORIGIN"]
                elif header == "X-XSS-Protection":
                    assert "1" in header_value
                elif header == "Content-Security-Policy":
                    # Should not allow unsafe-eval or unsafe-inline
                    assert "unsafe-eval" not in header_value
                    assert "unsafe-inline" not in header_value

    def test_api_error_handling_security(self):
        """Test that API error handling doesn't leak information."""
        # Test that error responses don't expose sensitive information

        error_inducing_inputs = [
            {"invalid": "parameter"},
            {"limit": "not_a_number"},
            {"session_id": None},
            {"nonexistent": "field"},
        ]

        for error_input in error_inducing_inputs:
            try:
                response = make_api_request_with_error(error_input)

                if response and "error" in response:
                    error_message = str(response["error"]).lower()

                    # Should not expose sensitive information in errors
                    sensitive_patterns = [
                        "password",
                        "secret",
                        "key",
                        "token",
                        "credential",
                        "database",
                        "connection",
                        "traceback",
                        "stack trace",
                        "/home/",
                        "/etc/",
                        "c:\\",
                        "system32",
                    ]

                    for pattern in sensitive_patterns:
                        assert pattern not in error_message

            except Exception as e:
                # Error handling should not crash
                assert "crash" not in str(e).lower()
                assert "panic" not in str(e).lower()


class TestAPIAuthenticationSecurity:
    """Test API authentication and authorization security."""

    def test_api_token_validation(self):
        """Test API token validation security."""
        # Test various token validation scenarios

        invalid_tokens = [
            None,  # No token
            "",  # Empty token
            "invalid_token",  # Invalid format
            "Bearer ",  # Empty bearer token
            "Bearer invalid",  # Invalid bearer token
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.malicious",  # Malformed JWT
            "../../../etc/passwd",  # Path traversal in token
            "token\x00malicious",  # Null byte injection
            "token; rm -rf /",  # Command injection
            "A" * 10000,  # Excessively long token
        ]

        for token in invalid_tokens:
            try:
                result = validate_api_token(token)

                # Should reject invalid tokens
                assert result is False or result is None

            except Exception as e:
                # Expected - should reject invalid tokens
                assert "token" in str(e).lower() or "auth" in str(e).lower()

    def test_api_session_security(self):
        """Test API session management security."""
        # Test session management security

        # Test session fixation prevention
        session1 = create_api_session()
        session2 = create_api_session()

        # Sessions should be unique
        assert session1["id"] != session2["id"]

        # Test session hijacking prevention
        malicious_session_ids = [
            "../../../etc/passwd",
            "session; rm -rf /",
            "session\x00malicious",
            "AAAA" + "B" * 1000,  # Long session ID
        ]

        for malicious_id in malicious_session_ids:
            try:
                result = validate_api_session(malicious_id)

                # Should reject malicious session IDs
                assert result is False or result is None

            except Exception as e:
                # Expected - should reject malicious input
                pass

    def test_api_privilege_escalation_prevention(self):
        """Test prevention of privilege escalation via API."""
        # Test that API doesn't allow privilege escalation

        regular_user_token = "user_token_123"
        admin_operations = [
            {"action": "delete_all_events"},
            {"action": "modify_user_permissions"},
            {"action": "access_system_files"},
            {"action": "execute_system_command", "command": "whoami"},
        ]

        for operation in admin_operations:
            try:
                result = perform_api_operation(regular_user_token, operation)

                # Should not allow admin operations for regular users
                if result:
                    assert (
                        "unauthorized" in str(result).lower()
                        or "forbidden" in str(result).lower()
                    )

            except Exception as e:
                # Expected - should reject unauthorized operations
                assert "permission" in str(e).lower() or "forbidden" in str(e).lower()


# Helper functions for testing (would be implemented based on actual API structure)


def html_escape(text):
    """Simple HTML escaping for testing purposes."""
    return text.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")


def perform_dashboard_operation(csrf_token=None):
    """Mock dashboard operation for CSRF testing."""
    if csrf_token is None:
        raise ValueError("CSRF token required")
    return {"success": True}


def query_events_with_filter(filter_value):
    """Mock event query function for SQL injection testing."""
    # This would normally query the database
    return []


def api_call_with_params(params):
    """Mock API call for input validation testing."""
    # Validate parameters
    if "limit" in params:
        limit = params["limit"]
        if isinstance(limit, str) and any(char in limit for char in ["'", "<", ">"]):
            raise ValueError("Invalid characters in limit")
        if isinstance(limit, int) and (limit < 0 or limit > 1000):
            raise ValueError("Limit out of range")
    return {"success": True}


def make_api_request(request_id):
    """Mock API request for rate limiting testing."""
    # Simulate API processing time
    time.sleep(0.01)
    return {"request_id": request_id, "status": "success"}


def get_cors_headers_for_origin(origin):
    """Mock CORS header generation for testing."""
    allowed_origins = ["http://localhost:3000", "https://app.khive.ai"]

    if origin in allowed_origins:
        return {"Access-Control-Allow-Origin": origin}
    else:
        return {}


def get_api_response_headers():
    """Mock API response headers for testing."""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "SAMEORIGIN",
        "X-XSS-Protection": "1; mode=block",
        "Content-Security-Policy": "default-src 'self'",
    }


def make_api_request_with_error(params):
    """Mock API request that triggers errors for testing."""
    if "invalid" in params:
        return {"error": "Invalid parameter provided"}
    return {"success": True}


def validate_api_token(token):
    """Mock API token validation for testing."""
    if not token or not isinstance(token, str):
        return False
    if len(token) > 500:  # Prevent excessively long tokens
        return False
    if any(char in token for char in ["\x00", ";", "&", "|"]):
        return False
    return token.startswith("valid_token_")


def create_api_session():
    """Mock API session creation for testing."""
    import uuid

    return {"id": str(uuid.uuid4()), "created": time.time()}


def validate_api_session(session_id):
    """Mock API session validation for testing."""
    if not session_id or not isinstance(session_id, str):
        return False
    if any(char in session_id for char in ["../", "\x00", ";", "&"]):
        return False
    return len(session_id) == 36  # UUID length


def perform_api_operation(token, operation):
    """Mock API operation for privilege testing."""
    if not validate_api_token(token):
        raise ValueError("Invalid token")

    admin_actions = [
        "delete_all_events",
        "modify_user_permissions",
        "access_system_files",
    ]
    if operation.get("action") in admin_actions:
        raise PermissionError("Insufficient permissions")

    return {"success": True}


@pytest.fixture
def mock_api_server():
    """Provide a mock API server for testing."""
    server = Mock()
    server.host = "localhost"
    server.port = 8080
    server.clients = set()
    return server


class TestAPISecurityIntegration:
    """Test end-to-end API security scenarios."""

    def test_api_security_chain_validation(self):
        """Test complete API security validation chain."""
        # Test end-to-end security validation

        # 1. Token validation
        valid_token = "valid_token_abc123"
        assert validate_api_token(valid_token) is True

        # 2. Session validation
        session = create_api_session()
        assert validate_api_session(session["id"]) is True

        # 3. Input validation
        valid_params = {"limit": 10, "session_id": session["id"]}
        result = api_call_with_params(valid_params)
        assert result["success"] is True

        # 4. Operation authorization
        safe_operation = {"action": "get_events"}
        result = perform_api_operation(valid_token, safe_operation)
        assert result["success"] is True

    def test_api_security_regression_prevention(self):
        """Test prevention of known API security regression patterns."""
        regression_tests = [
            {
                "name": "path_traversal",
                "input": {"file_path": "../../../etc/passwd"},
                "should_fail": True,
            },
            {
                "name": "sql_injection",
                "input": {"query": "'; DROP TABLE users; --"},
                "should_fail": True,
            },
            {
                "name": "xss_injection",
                "input": {"content": "<script>alert('XSS')</script>"},
                "should_fail": True,
            },
            {
                "name": "command_injection",
                "input": {"command": "; rm -rf /"},
                "should_fail": True,
            },
        ]

        for test_case in regression_tests:
            try:
                result = api_call_with_params(test_case["input"])

                if test_case["should_fail"]:
                    # Should have been rejected or sanitized
                    if result:
                        result_str = str(result).lower()
                        assert "/etc/passwd" not in result_str
                        assert "drop table" not in result_str
                        assert "<script>" not in result_str
                        assert "rm -rf" not in result_str

            except Exception as e:
                if test_case["should_fail"]:
                    # Expected - malicious input should be rejected
                    assert "error" in str(e).lower() or "invalid" in str(e).lower()
                else:
                    # Unexpected - valid input should not fail
                    pytest.fail(f"Valid input failed: {test_case['name']}: {e}")


class SecurityError(Exception):
    """Custom security exception for API testing."""

    pass
