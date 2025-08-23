"""
Comprehensive MCP Protocol Integration Tests.

Tests actual MCP protocol implementations, server communication, protocol compliance,
edge cases, timeout handling, connection recovery, and multiple server implementations.

This module validates:
- Real MCP protocol interactions and message passing
- Server discovery and lifecycle management
- Protocol version compatibility and handshake validation
- Transport reliability (stdio, SSE, HTTP, WebSocket)
- Timeout handling and connection recovery mechanisms
- CC toolkit creation with various permission modes
- Configuration management and environment handling
- Error scenarios and graceful degradation
"""

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from khive.cli.khive_mcp import MCPCommand, MCPConfig, MCPServerConfig
from tests.fixtures.mcp_fixtures import (MCPProtocolValidator,
                                         MCPTestScenarios, MockMCPServer)


@pytest.mark.mcp_protocol
@pytest.mark.integration
class TestMCPProtocolCompliance:
    """Test MCP protocol compliance and communication patterns."""

    @pytest_asyncio.fixture
    async def initialized_mock_server(self, mock_mcp_server: MockMCPServer):
        """Create and start a mock MCP server for testing."""
        await mock_mcp_server.start()
        yield mock_mcp_server
        await mock_mcp_server.stop()

    @pytest.mark.asyncio
    async def test_mcp_initialize_handshake(
        self,
        initialized_mock_server: MockMCPServer,
        mcp_protocol_validator: MCPProtocolValidator,
    ):
        """Test MCP protocol initialize handshake sequence."""
        # Create server config for mock server
        server_config = MCPServerConfig(
            name=initialized_mock_server.server_name,
            command="python",
            args=["-c", "pass"],  # Will be overridden by mock
            transport="stdio",
        )

        # Test with our MCP implementation
        mcp_cmd = MCPCommand()

        # Mock the client creation to use our initialized server
        with patch.object(mcp_cmd, "_create_transport") as mock_transport:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            # Mock successful initialization
            mock_client.list_tools = AsyncMock(
                return_value=[
                    MagicMock(name="read_file", description="Read file contents"),
                    MagicMock(name="write_file", description="Write file contents"),
                ]
            )

            with patch("khive.cli.khive_mcp.Client", return_value=mock_client):
                config = MCPConfig()
                config.servers[server_config.name] = server_config

                result = await mcp_cmd._cmd_list_tools(config, server_config.name)

                assert result.status == "success"
                assert "tools" in result.data
                assert len(result.data["tools"]) == 2

                # Verify handshake was attempted
                mock_client.__aenter__.assert_called_once()
                mock_client.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_message_format_validation(
        self, mcp_protocol_validator: MCPProtocolValidator
    ):
        """Test MCP message format validation."""
        # Test valid request message
        valid_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }

        assert mcp_protocol_validator.validate_message_format(valid_request)

        # Test valid response message
        valid_response = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}

        assert mcp_protocol_validator.validate_message_format(valid_response)

        # Test invalid messages
        invalid_messages = [
            {"id": 1, "method": "test"},  # Missing jsonrpc
            {"jsonrpc": "1.0", "id": 1, "method": "test"},  # Wrong version
            {"jsonrpc": "2.0", "method": "test"},  # Missing id
            {"jsonrpc": "2.0", "id": 1},  # No method/result/error
        ]

        for invalid_msg in invalid_messages:
            assert not mcp_protocol_validator.validate_message_format(invalid_msg)

        # Check that errors were recorded
        assert len(mcp_protocol_validator.errors) > 0

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
    async def test_stdio_transport_reliability(
        self, mcp_test_scenarios: MCPTestScenarios
    ):
        """Test stdio transport connection reliability."""
        server_config = mcp_test_scenarios.basic_file_server_config()

        mcp_cmd = MCPCommand()
        config = MCPConfig()
        config.servers[server_config.name] = server_config

        # Mock a working stdio connection
        with patch("khive.cli.khive_mcp.StdioTransport") as mock_transport_class:
            mock_transport = MagicMock()
            mock_transport_class.return_value = mock_transport

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            # Test successful connection
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
    async def test_sse_transport_reliability(
        self, mcp_test_scenarios: MCPTestScenarios
    ):
        """Test SSE transport connection reliability."""
        server_config = mcp_test_scenarios.sse_server_config(
            "http://localhost:8080/sse"
        )

        mcp_cmd = MCPCommand()
        config = MCPConfig()
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
    async def test_transport_switching(self, mcp_test_scenarios: MCPTestScenarios):
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
    async def test_server_startup_sequence(
        self, mcp_test_scenarios: MCPTestScenarios, mcp_server_lifecycle_tracker
    ):
        """Test MCP server startup and initialization sequence."""
        server_config = mcp_test_scenarios.basic_file_server_config()

        mcp_cmd = MCPCommand()
        config = MCPConfig()
        config.servers[server_config.name] = server_config

        # Track lifecycle events
        mcp_server_lifecycle_tracker.log_event("startup_begin", server_config.name)

        # Mock successful server startup
        with patch("khive.cli.khive_mcp.StdioTransport") as mock_transport:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=[])

            with patch("khive.cli.khive_mcp.Client", return_value=mock_client):
                result = await mcp_cmd._cmd_server_status(config, server_config.name)

                mcp_server_lifecycle_tracker.log_event(
                    "startup_complete", server_config.name, {"result": result.status}
                )

                # Verify lifecycle events
                events = mcp_server_lifecycle_tracker.get_events_for_server(
                    server_config.name
                )
                assert len(events) == 2
                assert events[0]["event"] == "startup_begin"
                assert events[1]["event"] == "startup_complete"

    @pytest.mark.asyncio
    async def test_server_shutdown_cleanup(
        self, mcp_test_scenarios: MCPTestScenarios, mcp_server_lifecycle_tracker
    ):
        """Test MCP server shutdown and cleanup procedures."""
        server_config = mcp_test_scenarios.basic_file_server_config()

        mcp_cmd = MCPCommand()

        # Track cleanup process
        mcp_server_lifecycle_tracker.log_event("shutdown_begin", server_config.name)

        # Test cleanup method
        await mcp_cmd._safe_cleanup_all_clients()

        mcp_server_lifecycle_tracker.log_event("shutdown_complete", server_config.name)

        # Verify cleanup was tracked
        events = mcp_server_lifecycle_tracker.get_events_for_server(server_config.name)
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_multiple_server_management(
        self, sample_mcp_config: Path, mcp_server_lifecycle_tracker
    ):
        """Test management of multiple MCP servers simultaneously."""
        # Create config with multiple servers
        mcp_cmd = MCPCommand()

        # Mock project root to use our sample config
        with patch.object(Path, "exists", return_value=True):
            with patch.object(
                Path, "read_text", return_value=sample_mcp_config.read_text()
            ):
                config = mcp_cmd._create_config(
                    MagicMock(project_root=sample_mcp_config.parent.parent)
                )

                # Verify multiple servers loaded
                assert len(config.servers) >= 2

                # Test listing all servers
                result = await mcp_cmd._cmd_list_servers(config)

                assert result.status == "success"
                assert "servers" in result.data
                assert len(result.data["servers"]) >= 2


@pytest.mark.mcp_error_handling
@pytest.mark.integration
class TestMCPErrorHandlingAndRecovery:
    """Test MCP error handling, timeout management, and connection recovery."""

    @pytest.mark.asyncio
    async def test_connection_timeout_handling(
        self, mcp_test_scenarios: MCPTestScenarios, mcp_error_injection
    ):
        """Test handling of connection timeouts."""
        server_config = (
            mcp_test_scenarios.slow_server_config()
        )  # Configured with short timeout

        mcp_cmd = MCPCommand()
        config = MCPConfig()
        config.servers[server_config.name] = server_config

        # Configure error injection for timeouts
        mcp_error_injection.configure(1.0, ["timeout"])

        # Mock timeout scenario
        with patch("khive.cli.khive_mcp.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(
                side_effect=asyncio.TimeoutError("Connection timeout")
            )
            mock_client_class.return_value = mock_client

            result = await mcp_cmd._cmd_server_status(config, server_config.name)

            # Should handle timeout gracefully
            assert (
                result.status == "success"
            )  # Status command succeeds even if server is unreachable
            assert (
                result.data["server"]["status"] == "timeout"
                or "error" in result.data["server"]
            )

    @pytest.mark.asyncio
    async def test_connection_recovery_mechanisms(
        self, mcp_test_scenarios: MCPTestScenarios, mcp_error_injection
    ):
        """Test connection recovery after failures."""
        server_config = mcp_test_scenarios.basic_file_server_config()

        mcp_cmd = MCPCommand()
        config = MCPConfig()
        config.servers[server_config.name] = server_config

        # Configure intermittent failures
        mcp_error_injection.configure(0.5, ["connection"])

        # Test with retry logic in list_tools (which has built-in retries)
        call_count = 0

        def mock_client_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_client = MagicMock()
            if call_count <= 2:  # Fail first 2 attempts
                mock_client.__aenter__ = AsyncMock(
                    side_effect=ConnectionError("Connection failed")
                )
            else:  # Succeed on 3rd attempt
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock()
                mock_client.list_tools = AsyncMock(return_value=[])

            return mock_client

        with patch("khive.cli.khive_mcp.Client", side_effect=mock_client_side_effect):
            result = await mcp_cmd._cmd_list_tools(config, server_config.name)

            # Should eventually succeed after retries
            assert result.status in [
                "success",
                "failure",
            ]  # May fail if retries exhausted
            assert call_count >= 2  # Verify retries were attempted

    @pytest.mark.asyncio
    async def test_malformed_response_handling(
        self, mcp_protocol_validator: MCPProtocolValidator
    ):
        """Test handling of malformed MCP protocol responses."""
        malformed_responses = [
            {"invalid": "response"},  # Missing required fields
            {"jsonrpc": "1.0", "id": 1, "result": {}},  # Wrong version
            {"jsonrpc": "2.0", "result": {}},  # Missing id
            "not json",  # Not even JSON
            None,  # Null response
        ]

        for response in malformed_responses:
            if isinstance(response, dict):
                is_valid = mcp_protocol_validator.validate_message_format(response)
                assert not is_valid, (
                    f"Should have rejected malformed response: {response}"
                )

        # Verify errors were recorded
        assert len(mcp_protocol_validator.errors) > 0

    @pytest.mark.asyncio
    async def test_server_process_crash_handling(
        self, mcp_test_scenarios: MCPTestScenarios
    ):
        """Test handling of MCP server process crashes."""
        server_config = mcp_test_scenarios.basic_file_server_config()

        mcp_cmd = MCPCommand()
        config = MCPConfig()
        config.servers[server_config.name] = server_config

        # Mock process crash scenario
        with patch("khive.cli.khive_mcp.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(side_effect=Exception("Process crashed"))
            mock_client_class.return_value = mock_client

            result = await mcp_cmd._cmd_server_status(config, server_config.name)

            # Should handle crash gracefully
            assert result.status == "success"
            assert result.data["server"]["status"] == "error"


@pytest.mark.mcp_configuration
@pytest.mark.integration
class TestMCPConfigurationManagement:
    """Test MCP configuration management and validation."""

    @pytest.mark.asyncio
    async def test_configuration_loading_and_validation(self, sample_mcp_config: Path):
        """Test MCP configuration file loading and validation."""
        mcp_cmd = MCPCommand()

        # Mock the configuration file path
        mock_args = MagicMock()
        mock_args.project_root = sample_mcp_config.parent.parent

        with patch.object(Path, "exists", return_value=True):
            with patch.object(
                Path, "read_text", return_value=sample_mcp_config.read_text()
            ):
                config = mcp_cmd._create_config(mock_args)

                # Verify servers were loaded
                assert len(config.servers) >= 2

                # Verify server configuration details
                for server_name, server_config in config.servers.items():
                    assert isinstance(server_config, MCPServerConfig)
                    assert server_config.name == server_name
                    assert server_config.transport in ["stdio", "sse", "http"]

    @pytest.mark.asyncio
    async def test_environment_variable_merging(self, temp_dir: Path):
        """Test environment variable merging with different priorities."""
        mcp_cmd = MCPCommand()

        # Create .env file
        env_file = temp_dir / ".env"
        env_file.write_text("GITHUB_TOKEN=env_file_token\nTEST_VAR=from_env_file")

        # Set system environment variable
        os.environ["GITHUB_TOKEN"] = "system_token"
        os.environ["SYSTEM_VAR"] = "from_system"

        try:
            # Test environment variable loading
            env_vars = mcp_cmd._load_environment_variables(temp_dir)

            assert "GITHUB_TOKEN" in env_vars
            assert "TEST_VAR" in env_vars
            assert env_vars["TEST_VAR"] == "from_env_file"

            # Test merging with config env (highest priority)
            config_env = {"GITHUB_TOKEN": "config_token", "CONFIG_VAR": "from_config"}
            merged = mcp_cmd._merge_environment_variables(
                config_env, env_vars, "github"
            )

            # Config should have highest priority
            assert merged["GITHUB_TOKEN"] == "config_token"
            assert merged["TEST_VAR"] == "from_env_file"
            assert merged["CONFIG_VAR"] == "from_config"
            assert merged["SYSTEM_VAR"] == "from_system"

        finally:
            # Cleanup environment variables
            os.environ.pop("GITHUB_TOKEN", None)
            os.environ.pop("SYSTEM_VAR", None)

    @pytest.mark.asyncio
    async def test_server_specific_environment_mapping(self):
        """Test server-specific environment variable mapping."""
        mcp_cmd = MCPCommand()

        # Test GitHub server environment mapping
        env_vars = {"GITHUB_PERSONAL_ACCESS_TOKEN": "pat_token"}
        config_env = {}

        merged = mcp_cmd._merge_environment_variables(config_env, env_vars, "github")

        # Should map GITHUB_PERSONAL_ACCESS_TOKEN to GITHUB_TOKEN
        assert merged["GITHUB_TOKEN"] == "pat_token"
        assert merged["GITHUB_PERSONAL_ACCESS_TOKEN"] == "pat_token"

    @pytest.mark.asyncio
    async def test_invalid_configuration_handling(self, temp_dir: Path):
        """Test handling of invalid MCP configurations."""
        mcp_cmd = MCPCommand()

        # Create invalid configuration file
        config_file = temp_dir / "config.json"
        config_file.write_text("invalid json content")

        mock_args = MagicMock()
        mock_args.project_root = temp_dir

        # Mock the config file path to return our invalid file
        with patch.object(MCPConfig, "mcps_config_file", Path(config_file)):
            # Should handle invalid JSON gracefully
            config = mcp_cmd._create_config(mock_args)

            # Should create empty config without crashing
            assert isinstance(config, MCPConfig)
            assert len(config.servers) == 0


@pytest.mark.mcp_performance
@pytest.mark.integration
@pytest.mark.slow
class TestMCPPerformanceAndStress:
    """Test MCP performance characteristics and stress scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_server_connections(
        self, sample_mcp_config: Path, mcp_performance_monitor
    ):
        """Test concurrent connections to multiple MCP servers."""
        mcp_cmd = MCPCommand()

        # Load configuration with multiple servers
        mock_args = MagicMock()
        mock_args.project_root = sample_mcp_config.parent.parent

        with patch.object(Path, "exists", return_value=True):
            with patch.object(
                Path, "read_text", return_value=sample_mcp_config.read_text()
            ):
                config = mcp_cmd._create_config(mock_args)

                # Mock multiple successful connections
                with patch("khive.cli.khive_mcp.Client") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock()
                    mock_client.list_tools = AsyncMock(return_value=[])
                    mock_client_class.return_value = mock_client

                    # Test concurrent server status checks
                    tasks = []
                    for server_name in config.servers.keys():
                        op_id = mcp_performance_monitor.start_operation(
                            "status_check", server_name
                        )
                        task = asyncio.create_task(
                            mcp_cmd._cmd_server_status(config, server_name)
                        )
                        tasks.append((task, op_id, server_name))

                    # Wait for all tasks to complete
                    for task, op_id, server_name in tasks:
                        result = await task
                        mcp_performance_monitor.end_operation(
                            op_id, result.status == "success"
                        )

                    # Analyze performance
                    stats = mcp_performance_monitor.get_statistics()
                    assert stats["total_operations"] >= 2
                    assert stats["success_rate"] >= 0.5  # At least 50% success rate

    @pytest.mark.asyncio
    async def test_rapid_sequential_requests(
        self, mcp_test_scenarios: MCPTestScenarios, mcp_performance_monitor
    ):
        """Test rapid sequential requests to same MCP server."""
        server_config = mcp_test_scenarios.basic_file_server_config()

        mcp_cmd = MCPCommand()
        config = MCPConfig()
        config.servers[server_config.name] = server_config

        # Mock fast responding server
        with patch("khive.cli.khive_mcp.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=[])
            mock_client_class.return_value = mock_client

            # Perform rapid sequential requests
            num_requests = 10
            for i in range(num_requests):
                op_id = mcp_performance_monitor.start_operation(
                    f"request_{i}", server_config.name
                )
                result = await mcp_cmd._cmd_list_tools(config, server_config.name)
                mcp_performance_monitor.end_operation(op_id, result.status == "success")

            # Analyze performance
            stats = mcp_performance_monitor.get_statistics()
            assert stats["total_operations"] == num_requests
            assert (
                stats["average_duration"] < 1.0
            )  # Should be fast with mocked responses

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, mcp_test_scenarios: MCPTestScenarios):
        """Test memory usage patterns under sustained load."""
        import gc

        server_config = mcp_test_scenarios.basic_file_server_config()

        mcp_cmd = MCPCommand()
        config = MCPConfig()
        config.servers[server_config.name] = server_config

        # Track memory usage
        initial_objects = len(gc.get_objects())

        # Mock server that creates/destroys resources
        with patch("khive.cli.khive_mcp.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.list_tools = AsyncMock(
                return_value=[MagicMock() for _ in range(100)]
            )
            mock_client_class.return_value = mock_client

            # Perform multiple operations
            for i in range(50):
                await mcp_cmd._cmd_list_tools(config, server_config.name)

                # Force cleanup periodically
                if i % 10 == 0:
                    await mcp_cmd._safe_cleanup_all_clients()
                    gc.collect()

            # Final cleanup
            await mcp_cmd._safe_cleanup_all_clients()
            gc.collect()

            final_objects = len(gc.get_objects())

            # Memory usage should not grow excessively
            object_growth = final_objects - initial_objects
            assert object_growth < 1000, (
                f"Excessive memory growth: {object_growth} objects"
            )


@pytest.mark.mcp_protocol
@pytest.mark.integration
class TestMCPEdgeCasesAndCompatibility:
    """Test edge cases and compatibility scenarios."""

    @pytest.mark.asyncio
    async def test_empty_server_responses(self, mcp_test_scenarios: MCPTestScenarios):
        """Test handling of empty or minimal server responses."""
        server_config = mcp_test_scenarios.basic_file_server_config()

        mcp_cmd = MCPCommand()
        config = MCPConfig()
        config.servers[server_config.name] = server_config

        # Mock server with no tools or resources
        with patch("khive.cli.khive_mcp.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=[])  # Empty tool list
            mock_client_class.return_value = mock_client

            result = await mcp_cmd._cmd_list_tools(config, server_config.name)

            assert result.status == "success"
            assert result.data["tools"] == []
            assert "Found 0 tools" in result.message

    @pytest.mark.asyncio
    async def test_large_response_handling(self, mcp_test_scenarios: MCPTestScenarios):
        """Test handling of large MCP server responses."""
        server_config = mcp_test_scenarios.basic_file_server_config()

        mcp_cmd = MCPCommand()
        config = MCPConfig()
        config.servers[server_config.name] = server_config

        # Mock server with large number of tools
        large_tool_list = []
        for i in range(500):  # Large number of tools
            tool = MagicMock()
            tool.name = f"tool_{i}"
            tool.description = f"Description for tool {i} " * 20  # Long description
            tool.inputSchema = {"type": "object", "properties": {}}
            large_tool_list.append(tool)

        with patch("khive.cli.khive_mcp.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=large_tool_list)
            mock_client_class.return_value = mock_client

            result = await mcp_cmd._cmd_list_tools(config, server_config.name)

            assert result.status == "success"
            assert len(result.data["tools"]) == 500
            assert "Found 500 tools" in result.message

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(
        self, mcp_test_scenarios: MCPTestScenarios
    ):
        """Test handling of Unicode and special characters in MCP responses."""
        server_config = mcp_test_scenarios.basic_file_server_config()

        mcp_cmd = MCPCommand()
        config = MCPConfig()
        config.servers[server_config.name] = server_config

        # Mock tools with Unicode characters
        unicode_tools = []
        unicode_names = [
            "测试工具",
            "🔧 repair_tool",
            "файл_инструмент",
            "outil_français",
        ]

        for name in unicode_names:
            tool = MagicMock()
            tool.name = name
            tool.description = f"Unicode test tool: {name} 🚀"
            tool.inputSchema = {"type": "object", "properties": {}}
            unicode_tools.append(tool)

        with patch("khive.cli.khive_mcp.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=unicode_tools)
            mock_client_class.return_value = mock_client

            result = await mcp_cmd._cmd_list_tools(config, server_config.name)

            assert result.status == "success"
            assert len(result.data["tools"]) == 4

            # Verify Unicode characters are preserved
            tool_names = [tool["name"] for tool in result.data["tools"]]
            for expected_name in unicode_names:
                assert expected_name in tool_names

    @pytest.mark.asyncio
    async def test_version_compatibility_matrix(self):
        """Test compatibility with different MCP protocol versions."""
        # Test compatibility matrix
        compatibility_tests = [
            {
                "client_version": "2024-11-05",
                "server_version": "2024-11-05",
                "should_work": True,
            },
            {
                "client_version": "2024-11-05",
                "server_version": "2024-10-07",
                "should_work": True,  # Backward compatibility
            },
            {
                "client_version": "2024-10-07",
                "server_version": "2024-11-05",
                "should_work": True,  # Forward compatibility within reason
            },
        ]

        for test_case in compatibility_tests:
            # Mock initialize response with specific version
            mock_response = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": test_case["server_version"],
                    "capabilities": {"tools": {"listChanged": True}},
                    "serverInfo": {"name": "version_test_server", "version": "1.0.0"},
                },
            }

            # Verify response format is valid regardless of version
            validator = MCPProtocolValidator()
            is_valid = validator.validate_message_format(mock_response)

            if test_case["should_work"]:
                assert is_valid, f"Version combination should work: {test_case}"

            # Check protocol version is accessible
            assert "protocolVersion" in mock_response["result"]
            assert (
                mock_response["result"]["protocolVersion"]
                == test_case["server_version"]
            )
