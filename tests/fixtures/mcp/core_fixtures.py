"""
Core MCP (Model Context Protocol) test fixtures.

Provides essential mock servers, validators, and test utilities for MCP integration testing.
Consolidated from the comprehensive MCP test implementation.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from khive.cli.khive_mcp import MCPServerConfig


class MockMCPServer:
    """Lightweight mock MCP server for testing."""

    def __init__(self, server_name: str = "test_server", transport: str = "stdio"):
        self.server_name = server_name
        self.transport = transport
        self.is_running = False
        self.tools = []
        self.resources = []
        self._message_log = []

    def add_tool(self, name: str, description: str, parameters: dict | None = None):
        """Add a tool to this mock server."""
        tool = {
            "name": name,
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": parameters or {},
                "required": list(parameters.keys()) if parameters else [],
            },
        }
        self.tools.append(tool)

    def add_resource(self, uri: str, name: str, description: str):
        """Add a resource to this mock server."""
        resource = {"uri": uri, "name": name, "description": description}
        self.resources.append(resource)

    async def start(self) -> bool:
        """Start the mock MCP server."""
        if not self.is_running:
            # Add default tools
            self.add_tool(
                "read_file", "Read file contents", {"path": {"type": "string"}}
            )
            self.add_tool(
                "write_file",
                "Write file contents",
                {"path": {"type": "string"}, "content": {"type": "string"}},
            )

            # Add default resources
            self.add_resource("file://", "file_system", "File system access")

            self.is_running = True
        return True

    async def stop(self):
        """Stop the mock MCP server."""
        self.is_running = False

    def create_initialize_response(self, msg_id: Any) -> dict[str, Any]:
        """Create a standard initialize response."""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"subscribe": True, "listChanged": True},
                },
                "serverInfo": {"name": self.server_name, "version": "1.0.0"},
            },
        }

    def create_tools_list_response(self, msg_id: Any) -> dict[str, Any]:
        """Create a tools/list response."""
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": self.tools}}


class MCPProtocolValidator:
    """Validates MCP protocol compliance."""

    def __init__(self):
        self.messages = []
        self.errors = []

    def validate_message_format(self, message: dict[str, Any]) -> bool:
        """Validate MCP message format compliance."""
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

    def get_validation_report(self) -> dict[str, Any]:
        """Get validation report."""
        return {
            "message_count": len(self.messages),
            "error_count": len(self.errors),
            "errors": self.errors,
            "valid": len(self.errors) == 0,
        }


class MCPTestScenarios:
    """Common test scenarios for MCP testing."""

    @staticmethod
    def basic_file_server_config() -> MCPServerConfig:
        """Configuration for a basic file system MCP server."""
        return MCPServerConfig(
            name="test_file_server",
            command="python",
            args=["-m", "file_server"],
            transport="stdio",
            timeout=10.0,
        )

    @staticmethod
    def github_server_config(token: str | None = None) -> MCPServerConfig:
        """Configuration for GitHub MCP server."""
        env = {"GITHUB_TOKEN": token or "test_token"}
        return MCPServerConfig(
            name="test_github_server",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env=env,
            transport="stdio",
            timeout=15.0,
        )

    @staticmethod
    def sse_server_config(url: str) -> MCPServerConfig:
        """Configuration for SSE transport server."""
        return MCPServerConfig(
            name="test_sse_server", url=url, transport="sse", timeout=10.0
        )

    @staticmethod
    def websocket_server_config(url: str) -> MCPServerConfig:
        """Configuration for WebSocket transport server."""
        return MCPServerConfig(
            name="test_ws_server", url=url, transport="websocket", timeout=10.0
        )

    @staticmethod
    def create_sample_mcp_config(project_root: Path) -> dict[str, Any]:
        """Create a sample MCP configuration for testing."""
        return {
            "mcpServers": {
                "file_server": {
                    "command": "python",
                    "args": ["-m", "file_server"],
                    "transport": "stdio",
                    "env": {"FILE_ROOT": "/tmp"},
                },
                "github_server": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "transport": "stdio",
                    "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
                },
            }
        }


class MCPLifecycleTracker:
    """Tracks MCP server lifecycle events for testing."""

    def __init__(self):
        self.events = []

    def log_event(self, event: str, server_name: str, data: dict | None = None):
        """Log a lifecycle event."""
        self.events.append({
            "event": event,
            "server_name": server_name,
            "data": data or {},
            "timestamp": asyncio.get_event_loop().time(),
        })

    def get_events_for_server(self, server_name: str) -> list[dict]:
        """Get all events for a specific server."""
        return [event for event in self.events if event["server_name"] == server_name]

    def clear_events(self):
        """Clear all logged events."""
        self.events.clear()


# Pytest fixtures
@pytest.fixture
def mock_mcp_server() -> MockMCPServer:
    """Create a mock MCP server for testing."""
    server = MockMCPServer("test_server", "stdio")
    yield server


@pytest_asyncio.fixture
async def initialized_mock_server() -> MockMCPServer:
    """Create and start a mock MCP server."""
    server = MockMCPServer("test_server", "stdio")
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
def mcp_protocol_validator() -> MCPProtocolValidator:
    """Create an MCP protocol validator."""
    return MCPProtocolValidator()


@pytest.fixture
def mcp_test_scenarios() -> MCPTestScenarios:
    """Create MCP test scenarios."""
    return MCPTestScenarios()


@pytest.fixture
def mcp_lifecycle_tracker() -> MCPLifecycleTracker:
    """Create MCP lifecycle tracker."""
    tracker = MCPLifecycleTracker()
    yield tracker
    tracker.clear_events()


@pytest.fixture
def sample_mcp_config() -> dict[str, Any]:
    """Create a sample MCP configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        return MCPTestScenarios.create_sample_mcp_config(project_root)


@pytest.fixture
def temp_project_with_mcp() -> Path:
    """Create a temporary project with MCP configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir)

        # Create project structure
        (project_dir / ".khive").mkdir()
        (project_dir / ".khive" / "mcps").mkdir()

        # Create MCP config
        mcp_config = MCPTestScenarios.create_sample_mcp_config(project_dir)
        config_file = project_dir / ".khive" / "mcps" / "config.json"
        config_file.write_text(json.dumps(mcp_config, indent=2))

        yield project_dir
