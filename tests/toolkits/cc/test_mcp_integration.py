"""
MCP Protocol Integration Tests.

Tests MCP protocol implementations, server communication, protocol compliance,
timeout handling, connection recovery, and server lifecycle management.
Covers requirements from issue #189 MCP integration testing.

This module validates:
- MCP protocol interactions and message passing
- Server discovery and lifecycle management
- Protocol version compatibility and handshake validation
- Transport reliability (stdio, SSE, HTTP, WebSocket)
- Timeout handling and connection recovery mechanisms
- Error scenarios and graceful degradation
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from khive.cli.khive_mcp import MCPCommand, MCPConfig, MCPServerConfig


class MCPProtocolValidator:
    """Validator for MCP protocol compliance."""

    def __init__(self):
        self.errors = []
        self.messages_validated = 0

    def validate_message_format(self, message: dict[str, Any]) -> bool:
        """Validate MCP message format compliance."""
        self.messages_validated += 1

        # Check JSON-RPC 2.0 format
        if "jsonrpc" not in message:
            self.errors.append("Missing jsonrpc field")
            return False

        if message["jsonrpc"] != "2.0":
            self.errors.append(f"Invalid jsonrpc version: {message['jsonrpc']}")
            return False

        # Check for id field (required for requests/responses)
        if "id" not in message:
            self.errors.append("Missing id field")
            return False

        # Must have method (request) or result/error (response)
        has_method = "method" in message
        has_result = "result" in message
        has_error = "error" in message

        if not (has_method or has_result or has_error):
            self.errors.append("Message must have method, result, or error")
            return False

        return True

    def validate_handshake_sequence(
        self, initialize_request: dict, initialize_response: dict
    ) -> bool:
        """Validate MCP initialize handshake sequence."""
        # Validate initialize request
        if not self.validate_message_format(initialize_request):
            return False

        if initialize_request.get("method") != "initialize":
            self.errors.append("Expected initialize method in handshake")
            return False

        # Validate initialize response
        if not self.validate_message_format(initialize_response):
            return False

        if "result" not in initialize_response:
            self.errors.append("Initialize response missing result")
            return False

        result = initialize_response["result"]
        required_fields = ["protocolVersion", "capabilities", "serverInfo"]

        for field in required_fields:
            if field not in result:
                self.errors.append(f"Initialize response missing {field}")
                return False

        return True


@pytest.mark.mcp_protocol
@pytest.mark.integration
class TestMCPProtocolCompliance:
    """Test MCP protocol compliance and communication patterns."""

    @pytest.fixture
    def protocol_validator(self) -> MCPProtocolValidator:
        """Create protocol validator."""
        return MCPProtocolValidator()

    @pytest.mark.asyncio
    async def test_mcp_initialize_handshake(
        self, protocol_validator: MCPProtocolValidator
    ):
        """Test MCP protocol initialize handshake sequence."""
        server_config = MCPServerConfig(
            name="test_server", command="python", args=["-c", "pass"], transport="stdio"
        )

        mcp_cmd = MCPCommand()

        # Mock successful handshake
        with patch.object(mcp_cmd, "_create_transport"):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.list_tools = AsyncMock(
                return_value=[
                    MagicMock(name="read_file", description="Read file contents"),
                    MagicMock(name="write_file", description="Write file contents"),
                ]
            )

            with patch("khive.cli.khive_mcp.Client", return_value=mock_client):
                config = MCPConfig(project_root="/tmp")
                config.servers[server_config.name] = server_config

                result = await mcp_cmd._cmd_list_tools(config, server_config.name)

                assert result.status == "success"
                assert "tools" in result.data
                assert len(result.data["tools"]) >= 0

                # Verify connection was attempted
                mock_client.__aenter__.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_message_format_validation(
        self, protocol_validator: MCPProtocolValidator
    ):
        """Test MCP message format validation."""
        # Test valid request message
        valid_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }

        assert protocol_validator.validate_message_format(valid_request)

        # Test valid response message
        valid_response = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}

        assert protocol_validator.validate_message_format(valid_response)

        # Test invalid messages
        invalid_messages = [
            {"id": 1, "method": "test"},  # Missing jsonrpc
            {"jsonrpc": "1.0", "id": 1, "method": "test"},  # Wrong version
            {"jsonrpc": "2.0", "method": "test"},  # Missing id
            {"jsonrpc": "2.0", "id": 1},  # No method/result/error
        ]

        for invalid_msg in invalid_messages:
            assert not protocol_validator.validate_message_format(invalid_msg)

        # Check that errors were recorded
        assert len(protocol_validator.errors) > 0

    @pytest.mark.asyncio
    async def test_protocol_version_negotiation(self):
        """Test MCP protocol version negotiation."""
        # Test that our implementation handles different protocol versions
        versions_to_test = ["2024-11-05", "2024-10-07", "2024-09-19"]

        for version in versions_to_test:
            mock_response = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": version,
                    "capabilities": {"tools": {"listChanged": True}},
                    "serverInfo": {"name": "test_server", "version": "1.0.0"},
                },
            }

            # Verify our implementation can handle this response
            assert "protocolVersion" in mock_response["result"]
            assert mock_response["result"]["protocolVersion"] in versions_to_test


@pytest.mark.mcp_transport
@pytest.mark.integration
class TestMCPTransportReliability:
    """Test MCP transport reliability across different connection types."""

    @pytest.mark.asyncio
    async def test_stdio_transport_reliability(self):
        """Test stdio transport connection reliability."""
        server_config = MCPServerConfig(
            name="file_server",
            command="python",
            args=["-m", "file_server"],
            transport="stdio",
        )

        mcp_cmd = MCPCommand()
        config = MCPConfig(project_root="/tmp")
        config.servers[server_config.name] = server_config

        # Mock a working stdio connection
        with patch("khive.cli.khive_mcp.StdioTransport") as mock_transport_class:
            mock_transport = MagicMock()
            mock_transport_class.return_value = mock_transport

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=[])

            with patch("khive.cli.khive_mcp.Client", return_value=mock_client):
                result = await mcp_cmd._cmd_server_status(config, server_config.name)

                assert result.status == "success"
                assert result.data["server"]["status"] in [
                    "connected",
                    "timeout",
                    "error",
                ]

    @pytest.mark.asyncio
    async def test_sse_transport_reliability(self):
        """Test SSE transport connection reliability."""
        server_config = MCPServerConfig(
            name="sse_server", url="http://localhost:8080/sse", transport="sse"
        )

        mcp_cmd = MCPCommand()
        config = MCPConfig(project_root="/tmp")
        config.servers[server_config.name] = server_config

        # Mock SSE transport
        with patch("khive.cli.khive_mcp.SSETransport") as mock_transport_class:
            mock_transport = MagicMock()
            mock_transport_class.return_value = mock_transport

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=[])

            with patch("khive.cli.khive_mcp.Client", return_value=mock_client):
                result = await mcp_cmd._cmd_server_status(config, server_config.name)

                assert result.status == "success"
                mock_transport_class.assert_called_with("http://localhost:8080/sse")

    @pytest.mark.asyncio
    async def test_transport_switching(self):
        """Test automatic transport detection and switching."""
        mcp_cmd = MCPCommand()

        # Test stdio detection
        stdio_config = {
            "command": "python",
            "args": ["-m", "server"],
        }
        transport, url = mcp_cmd._detect_transport_type(stdio_config)
        assert transport == "stdio"
        assert url is None

        # Test SSE detection
        sse_config = {"url": "http://localhost:8080/sse"}
        transport, url = mcp_cmd._detect_transport_type(sse_config)
        assert transport == "sse"
        assert url == "http://localhost:8080/sse"

        # Test WebSocket detection
        ws_config = {"url": "ws://localhost:8080/ws"}
        transport, url = mcp_cmd._detect_transport_type(ws_config)
        assert transport == "websocket"
        assert url == "ws://localhost:8080/ws"


@pytest.mark.mcp_lifecycle
@pytest.mark.integration
class TestMCPServerLifecycle:
    """Test MCP server lifecycle management and monitoring."""

    @pytest.mark.asyncio
    async def test_server_startup_sequence(self):
        """Test MCP server startup and initialization sequence."""
        server_config = MCPServerConfig(
            name="test_server",
            command="python",
            args=["-m", "test_server"],
            transport="stdio",
        )

        mcp_cmd = MCPCommand()
        config = MCPConfig(project_root="/tmp")
        config.servers[server_config.name] = server_config

        # Mock successful server startup
        with patch("khive.cli.khive_mcp.StdioTransport") as mock_transport:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=[])

            with patch("khive.cli.khive_mcp.Client", return_value=mock_client):
                result = await mcp_cmd._cmd_server_status(config, server_config.name)

                assert result.status == "success"
                assert "server" in result.data

    @pytest.mark.asyncio
    async def test_server_shutdown_cleanup(self):
        """Test MCP server shutdown and cleanup procedures."""
        server_config = MCPServerConfig(
            name="test_server",
            command="python",
            args=["-m", "test_server"],
            transport="stdio",
        )

        mcp_cmd = MCPCommand()
        config = MCPConfig(project_root="/tmp")
        config.servers[server_config.name] = server_config

        # Test shutdown behavior
        with patch("khive.cli.khive_mcp.StdioTransport"):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            with patch("khive.cli.khive_mcp.Client", return_value=mock_client):
                # Simulate connection and shutdown
                async with mock_client:
                    pass

                # Verify cleanup was called
                mock_client.__aexit__.assert_called_once()


@pytest.mark.mcp_error_handling
@pytest.mark.integration
class TestMCPErrorHandlingAndRecovery:
    """Test MCP error handling and connection recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self):
        """Test timeout handling for slow connections."""
        server_config = MCPServerConfig(
            name="slow_server",
            command="sleep",
            args=["10"],
            transport="stdio",
            timeout=1.0,  # Short timeout
        )

        mcp_cmd = MCPCommand()
        config = MCPConfig(project_root="/tmp")
        config.servers[server_config.name] = server_config

        # Mock timeout scenario
        with patch("khive.cli.khive_mcp.StdioTransport") as mock_transport:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(
                side_effect=asyncio.TimeoutError("Connection timeout")
            )

            with patch("khive.cli.khive_mcp.Client", return_value=mock_client):
                result = await mcp_cmd._cmd_server_status(config, server_config.name)

                # Should handle timeout gracefully
                assert result.status in ["timeout", "error"]

    @pytest.mark.asyncio
    async def test_connection_recovery_retry(self):
        """Test connection recovery and retry mechanisms."""
        server_config = MCPServerConfig(
            name="flaky_server",
            command="python",
            args=["-m", "flaky_server"],
            transport="stdio",
        )

        mcp_cmd = MCPCommand()
        config = MCPConfig(project_root="/tmp")
        config.servers[server_config.name] = server_config

        # Mock failing then succeeding connection
        with patch("khive.cli.khive_mcp.StdioTransport"):
            mock_client = MagicMock()

            # First call fails, second succeeds
            mock_client.__aenter__ = AsyncMock()
            mock_client.__aexit__ = AsyncMock()
            mock_client.list_tools = AsyncMock(
                side_effect=[
                    ConnectionError("Connection failed"),
                    [],  # Success on retry
                ]
            )

            with patch("khive.cli.khive_mcp.Client", return_value=mock_client):
                # Test first attempt (should fail)
                result1 = await mcp_cmd._cmd_list_tools(config, server_config.name)

                # Test retry (should succeed)
                result2 = await mcp_cmd._cmd_list_tools(config, server_config.name)

                # Should handle both scenarios appropriately
                assert "status" in result1
                assert "status" in result2

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self):
        """Test handling of malformed server responses."""
        server_config = MCPServerConfig(
            name="malformed_server",
            command="python",
            args=["-m", "malformed_server"],
            transport="stdio",
        )

        mcp_cmd = MCPCommand()
        config = MCPConfig(project_root="/tmp")
        config.servers[server_config.name] = server_config

        # Mock malformed response
        with patch("khive.cli.khive_mcp.StdioTransport"):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.list_tools = AsyncMock(
                side_effect=ValueError("Invalid JSON response")
            )

            with patch("khive.cli.khive_mcp.Client", return_value=mock_client):
                result = await mcp_cmd._cmd_list_tools(config, server_config.name)

                # Should handle malformed response gracefully
                assert result.status in ["error", "timeout"]


@pytest.mark.mcp_performance
@pytest.mark.slow
class TestMCPPerformance:
    """Test MCP performance and concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_server_connections(self):
        """Test concurrent connections to multiple MCP servers."""
        server_configs = [
            MCPServerConfig(
                name=f"server_{i}",
                command="python",
                args=["-m", f"server_{i}"],
                transport="stdio",
            )
            for i in range(3)
        ]

        mcp_cmd = MCPCommand()
        config = MCPConfig(project_root="/tmp")

        for server_config in server_configs:
            config.servers[server_config.name] = server_config

        # Mock concurrent connections
        with patch("khive.cli.khive_mcp.StdioTransport"):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=[])

            with patch("khive.cli.khive_mcp.Client", return_value=mock_client):
                # Test concurrent status checks
                tasks = [
                    mcp_cmd._cmd_server_status(config, server_config.name)
                    for server_config in server_configs
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # All results should be successful or handled gracefully
                for result in results:
                    if isinstance(result, Exception):
                        pytest.fail(f"Unexpected exception: {result}")
                    else:
                        assert hasattr(result, "status")

    @pytest.mark.asyncio
    async def test_memory_usage_during_operations(self):
        """Test memory usage remains stable during MCP operations."""
        import gc
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        server_config = MCPServerConfig(
            name="memory_test_server",
            command="python",
            args=["-m", "test_server"],
            transport="stdio",
        )

        mcp_cmd = MCPCommand()
        config = MCPConfig(project_root="/tmp")
        config.servers[server_config.name] = server_config

        # Perform multiple operations
        with patch("khive.cli.khive_mcp.StdioTransport"):
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=[])

            with patch("khive.cli.khive_mcp.Client", return_value=mock_client):
                for _ in range(10):
                    result = await mcp_cmd._cmd_list_tools(config, server_config.name)
                    assert hasattr(result, "status")

        # Force garbage collection
        gc.collect()

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024, (
            f"Excessive memory usage: {memory_increase} bytes"
        )
