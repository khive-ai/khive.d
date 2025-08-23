"""
MCP (Model Context Protocol) test fixtures for comprehensive integration testing.

Provides mock servers, transport implementations, and protocol compliance testing utilities
for validating MCP protocol implementations across various scenarios.
"""

import asyncio
import json
import subprocess
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from fastmcp.client import Client
from fastmcp.client.transports import SSETransport, StdioTransport

from khive.cli.khive_mcp import MCPServerConfig


class MockMCPServer:
    """Mock MCP server for testing protocol compliance and communication."""

    def __init__(
        self, server_name: str, transport: str = "stdio", port: int | None = None
    ):
        self.server_name = server_name
        self.transport = transport
        self.port = port
        self.process: subprocess.Popen | None = None
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
        if self.is_running:
            return True

        try:
            if self.transport == "stdio":
                await self._start_stdio_server()
            elif self.transport == "sse":
                await self._start_sse_server()
            else:
                raise ValueError(f"Unsupported transport: {self.transport}")

            self.is_running = True
            return True
        except Exception as e:
            print(f"Failed to start mock MCP server {self.server_name}: {e}")
            return False

    async def stop(self):
        """Stop the mock MCP server."""
        if not self.is_running:
            return

        try:
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
                self.process = None

            self.is_running = False
        except Exception as e:
            print(f"Error stopping mock MCP server {self.server_name}: {e}")

    async def _start_stdio_server(self):
        """Start stdio-based mock server."""
        # Create a simple Python script that implements MCP protocol
        server_script = self._generate_stdio_server_script()

        # Write script to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(server_script)
            script_path = f.name

        # Start the server process
        self.process = subprocess.Popen(
            ["python", script_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Give it a moment to start
        await asyncio.sleep(0.1)

    async def _start_sse_server(self):
        """Start SSE-based mock server."""
        # For SSE, we'd typically start a web server
        # For testing purposes, we'll simulate this
        self.port = self.port or 8080
        # In real implementation, would start actual SSE server

    def _generate_stdio_server_script(self) -> str:
        """Generate Python script for stdio-based mock MCP server."""
        tools_json = json.dumps(self.tools, indent=2)
        resources_json = json.dumps(self.resources, indent=2)

        return f'''#!/usr/bin/env python3
"""Mock MCP server for testing - {self.server_name}."""

import json
import sys
import asyncio
from typing import Any, Dict, List

class MockMCPStdioServer:
    def __init__(self):
        self.tools = {tools_json}
        self.resources = {resources_json}
        self.request_id = 0
        
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP messages."""
        method = message.get("method")
        params = message.get("params", {{}})
        msg_id = message.get("id")
        
        if method == "initialize":
            return {{
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {{
                    "protocolVersion": "2024-11-05",
                    "capabilities": {{
                        "tools": {{"listChanged": True}},
                        "resources": {{"subscribe": True, "listChanged": True}}
                    }},
                    "serverInfo": {{
                        "name": "{self.server_name}",
                        "version": "1.0.0"
                    }}
                }}
            }}
            
        elif method == "tools/list":
            return {{
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {{
                    "tools": self.tools
                }}
            }}
            
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {{}})
            return {{
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {{
                    "content": [
                        {{
                            "type": "text",
                            "text": f"Mock tool {{tool_name}} called with args: {{arguments}}"
                        }}
                    ]
                }}
            }}
            
        elif method == "resources/list":
            return {{
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {{
                    "resources": self.resources
                }}
            }}
            
        else:
            return {{
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {{
                    "code": -32601,
                    "message": f"Method not found: {{method}}"
                }}
            }}
    
    async def run(self):
        """Main server loop."""
        while True:
            try:
                line = await asyncio.to_thread(sys.stdin.readline)
                if not line:
                    break
                    
                message = json.loads(line.strip())
                response = await self.handle_message(message)
                
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                error_response = {{
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {{
                        "code": -32603,
                        "message": f"Internal error: {{str(e)}}"
                    }}
                }}
                print(json.dumps(error_response), flush=True)

if __name__ == "__main__":
    server = MockMCPStdioServer()
    asyncio.run(server.run())
'''


class MCPProtocolValidator:
    """Validates MCP protocol compliance during tests."""

    def __init__(self):
        self.messages = []
        self.errors = []

    def log_message(self, message: dict[str, Any], direction: str):
        """Log a protocol message for validation."""
        self.messages.append({
            "direction": direction,  # "sent" or "received"
            "message": message,
            "timestamp": asyncio.get_event_loop().time(),
        })

    def validate_initialize_handshake(self) -> bool:
        """Validate the MCP initialize handshake sequence."""
        init_messages = [
            msg
            for msg in self.messages
            if msg["message"].get("method") == "initialize"
            or (msg["message"].get("result", {}).get("protocolVersion"))
        ]

        if len(init_messages) < 2:
            self.errors.append("Incomplete initialize handshake")
            return False

        # Validate protocol version
        init_response = next(
            (msg for msg in init_messages if msg["message"].get("result")), None
        )
        if not init_response:
            self.errors.append("No initialize response found")
            return False

        protocol_version = init_response["message"]["result"].get("protocolVersion")
        if not protocol_version:
            self.errors.append("No protocol version in initialize response")
            return False

        return True

    def validate_message_format(self, message: dict[str, Any]) -> bool:
        """Validate that a message follows MCP protocol format."""
        # Check required fields
        if "jsonrpc" not in message:
            self.errors.append("Missing jsonrpc field")
            return False

        if message["jsonrpc"] != "2.0":
            self.errors.append(f"Invalid jsonrpc version: {message['jsonrpc']}")
            return False

        # Check message type
        if "method" in message:
            # Request message
            if "id" not in message:
                self.errors.append("Request missing id field")
                return False
        elif "result" in message or "error" in message:
            # Response message
            if "id" not in message:
                self.errors.append("Response missing id field")
                return False
        else:
            self.errors.append("Invalid message type")
            return False

        return True

    def get_validation_report(self) -> dict[str, Any]:
        """Get a comprehensive validation report."""
        return {
            "message_count": len(self.messages),
            "error_count": len(self.errors),
            "errors": self.errors,
            "handshake_valid": self.validate_initialize_handshake(),
            "messages": self.messages[-10:],  # Last 10 messages for debugging
        }


class MCPTestScenarios:
    """Common test scenarios for MCP protocol testing."""

    @staticmethod
    def basic_file_server_config() -> MCPServerConfig:
        """Configuration for a basic file system MCP server."""
        return MCPServerConfig(
            name="test_file_server",
            command="python",
            args=["-m", "mcp_file_server", "--root", "/tmp"],
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
        """Configuration for SSE-based MCP server."""
        return MCPServerConfig(
            name="test_sse_server",
            command="",  # Not used for SSE
            transport="sse",
            url=url,
            timeout=10.0,
        )

    @staticmethod
    def slow_server_config() -> MCPServerConfig:
        """Configuration for a server that responds slowly (for timeout testing)."""
        return MCPServerConfig(
            name="slow_server",
            command="python",
            args=["-c", "import time; time.sleep(5)"],  # Simulates slow startup
            transport="stdio",
            timeout=2.0,  # Short timeout to trigger timeout scenarios
        )


@pytest.fixture
def mock_mcp_server() -> Generator[MockMCPServer, None, None]:
    """Create a mock MCP server for testing."""
    server = MockMCPServer("test_server")

    # Add some sample tools
    server.add_tool("read_file", "Read contents of a file", {"path": "string"})
    server.add_tool(
        "write_file", "Write content to a file", {"path": "string", "content": "string"}
    )
    server.add_tool("list_files", "List files in a directory", {"directory": "string"})

    # Add some sample resources
    server.add_resource("file://test.txt", "test.txt", "Test file")
    server.add_resource("file://config.json", "config.json", "Configuration file")

    yield server

    # Cleanup
    asyncio.create_task(server.stop())


@pytest.fixture
def mcp_protocol_validator() -> MCPProtocolValidator:
    """Create an MCP protocol validator for testing."""
    return MCPProtocolValidator()


@pytest.fixture
def mcp_test_scenarios() -> MCPTestScenarios:
    """Provide MCP test scenarios factory."""
    return MCPTestScenarios()


@pytest.fixture
def temp_mcp_config(temp_dir: Path) -> Path:
    """Create temporary MCP configuration directory."""
    mcp_dir = temp_dir / ".khive" / "mcps"
    mcp_dir.mkdir(parents=True, exist_ok=True)
    return mcp_dir


@pytest.fixture
def sample_mcp_config(
    temp_mcp_config: Path, mcp_test_scenarios: MCPTestScenarios
) -> Path:
    """Create a sample MCP configuration file for testing."""
    config_file = temp_mcp_config / "config.json"

    config_data = {
        "mcpServers": {
            "file_server": {
                "command": "python",
                "args": ["-m", "test_file_server"],
                "transport": "stdio",
            },
            "github_server": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_TOKEN": "test_token"},
                "transport": "stdio",
                "disabled": False,
            },
            "sse_server": {"url": "http://localhost:8080/sse", "transport": "sse"},
        }
    }

    config_file.write_text(json.dumps(config_data, indent=2))
    return config_file


@pytest_asyncio.fixture
async def mcp_client_factory():
    """Factory for creating MCP clients with different transports."""
    created_clients = []

    async def create_client(server_config: MCPServerConfig) -> Client:
        """Create an MCP client for the given server configuration."""
        if server_config.transport == "stdio":
            transport = StdioTransport(
                command=server_config.command,
                args=server_config.args,
                env=server_config.env,
            )
        elif server_config.transport == "sse":
            if not server_config.url:
                raise ValueError("SSE transport requires URL")
            transport = SSETransport(server_config.url)
        else:
            raise ValueError(f"Unsupported transport: {server_config.transport}")

        client = Client(transport)
        created_clients.append(client)
        return client

    yield create_client

    # Cleanup all created clients
    for client in created_clients:
        try:
            if hasattr(client, "transport") and hasattr(client.transport, "close"):
                await client.transport.close()
        except Exception:
            pass  # Ignore cleanup errors


@pytest.fixture
def mock_fastmcp_imports():
    """Mock FastMCP imports for testing when library is not available."""
    with patch.dict(
        "sys.modules",
        {
            "fastmcp": MagicMock(),
            "fastmcp.client": MagicMock(),
            "fastmcp.client.transports": MagicMock(),
        },
    ):
        yield


@pytest.fixture
def mcp_server_lifecycle_tracker():
    """Track MCP server lifecycle events for testing."""

    class LifecycleTracker:
        def __init__(self):
            self.events = []

        def log_event(
            self, event: str, server_name: str, details: dict | None = None
        ):
            self.events.append({
                "event": event,
                "server_name": server_name,
                "details": details or {},
                "timestamp": asyncio.get_event_loop().time(),
            })

        def get_events_for_server(self, server_name: str) -> list[dict]:
            return [
                event for event in self.events if event["server_name"] == server_name
            ]

        def clear(self):
            self.events.clear()

    return LifecycleTracker()


@pytest.fixture
def mcp_error_injection():
    """Inject errors into MCP operations for testing error handling."""

    class ErrorInjector:
        def __init__(self):
            self.injection_rate = 0.0
            self.error_types = []
            self.injected_count = 0

        def configure(self, injection_rate: float, error_types: list[str]):
            self.injection_rate = injection_rate
            self.error_types = error_types

        def should_inject_error(self) -> bool:
            import random

            return random.random() < self.injection_rate

        def get_error_to_inject(self) -> Exception:
            import random

            error_type = random.choice(self.error_types)

            if error_type == "timeout":
                return asyncio.TimeoutError("Injected timeout error")
            if error_type == "connection":
                return ConnectionError("Injected connection error")
            if error_type == "protocol":
                return ValueError("Injected protocol error")
            return Exception(f"Injected {error_type} error")

        def record_injection(self):
            self.injected_count += 1

    return ErrorInjector()


@pytest.fixture
def mcp_performance_monitor():
    """Monitor MCP operation performance for testing."""

    class PerformanceMonitor:
        def __init__(self):
            self.operations = []

        def start_operation(self, operation: str, server_name: str) -> str:
            import uuid

            operation_id = str(uuid.uuid4())

            self.operations.append({
                "id": operation_id,
                "operation": operation,
                "server_name": server_name,
                "start_time": asyncio.get_event_loop().time(),
                "end_time": None,
                "duration": None,
                "success": None,
            })

            return operation_id

        def end_operation(self, operation_id: str, success: bool):
            operation = next(
                (op for op in self.operations if op["id"] == operation_id), None
            )
            if operation:
                end_time = asyncio.get_event_loop().time()
                operation["end_time"] = end_time
                operation["duration"] = end_time - operation["start_time"]
                operation["success"] = success

        def get_statistics(self) -> dict[str, Any]:
            if not self.operations:
                return {"total": 0}

            completed_ops = [op for op in self.operations if op["duration"] is not None]
            successful_ops = [op for op in completed_ops if op["success"]]

            durations = [op["duration"] for op in completed_ops]

            return {
                "total_operations": len(self.operations),
                "completed_operations": len(completed_ops),
                "successful_operations": len(successful_ops),
                "success_rate": len(successful_ops) / len(completed_ops)
                if completed_ops
                else 0,
                "average_duration": sum(durations) / len(durations) if durations else 0,
                "min_duration": min(durations) if durations else 0,
                "max_duration": max(durations) if durations else 0,
            }

    return PerformanceMonitor()
