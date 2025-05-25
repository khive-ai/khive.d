# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
MCP Client - Shared MCP client implementation.

This module contains the core MCP client functionality that can be shared
between the CLI and adapter implementations without circular imports.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    always_allow: list[str] = field(default_factory=list)
    disabled: bool = False
    timeout: int = 30


@dataclass
class MCPConfig:
    """Configuration for MCP servers."""
    project_root: Path
    servers: dict[str, MCPServerConfig] = field(default_factory=dict)

    # CLI args / internal state
    json_output: bool = False
    dry_run: bool = False
    verbose: bool = False

    @property
    def khive_config_dir(self) -> Path:
        return self.project_root / ".khive"

    @property
    def mcps_config_file(self) -> Path:
        return self.khive_config_dir / "mcps" / "config.json"

    @property
    def mcps_state_file(self) -> Path:
        return self.khive_config_dir / "mcps" / "state.json"


def load_mcp_config(project_r: Path, cli_args: Optional[Any] = None) -> MCPConfig:
    """Load MCP configuration from project."""
    cfg = MCPConfig(project_root=project_r)

    # Load MCP server configurations
    if cfg.mcps_config_file.exists():
        try:
            config_data = json.loads(cfg.mcps_config_file.read_text())
            mcp_servers = config_data.get("mcpServers", {})

            for server_name, server_config in mcp_servers.items():
                cfg.servers[server_name] = MCPServerConfig(
                    name=server_name,
                    command=server_config.get("command", ""),
                    args=server_config.get("args", []),
                    env=server_config.get("env", {}),
                    always_allow=server_config.get("alwaysAllow", []),
                    disabled=server_config.get("disabled", False),
                    timeout=server_config.get("timeout", 30),
                )
        except (json.JSONDecodeError, KeyError) as e:
            # Can't use log_msg_mcp here due to circular import
            if cfg.verbose:
                print(f"Warning: Could not parse MCP config: {e}. Using empty configuration.", file=sys.stderr)

    # Apply CLI arguments
    if cli_args:
        cfg.json_output = getattr(cli_args, 'json_output', False)
        cfg.dry_run = getattr(cli_args, 'dry_run', False)
        cfg.verbose = getattr(cli_args, 'verbose', False)

    return cfg


class MCPClient:
    """Proper MCP client that handles the full JSON-RPC 2.0 protocol."""

    def __init__(self, server_config: MCPServerConfig):
        self.server_config = server_config
        self.process: asyncio.subprocess.Process | None = None
        self.message_id = 0
        self.connected = False
        self.server_info: dict[str, Any] = {}
        self.tools: list[dict[str, Any]] = []

    async def connect(self) -> bool:
        """Connect to the MCP server and perform initialization handshake."""
        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(self.server_config.env)

            # Start the MCP server process
            cmd = [self.server_config.command] + self.server_config.args

            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            # Perform MCP initialization handshake
            await self._initialize()

            # List available tools
            await self._list_tools()

            self.connected = True
            return True

        except Exception as e:
            if self.process:
                self.process.terminate()
                await self.process.wait()
            return False

    async def _initialize(self):
        """Perform the MCP initialization handshake."""
        # Step 1: Send initialize request
        init_response = await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                "clientInfo": {"name": "khive", "version": "1.0.0"},
            },
        )

        if "error" in init_response:
            raise Exception(f"Initialization failed: {init_response['error']}")

        # Store server info
        if "result" in init_response:
            self.server_info = init_response["result"]

        # Step 3: Send initialized notification
        await self._send_notification("notifications/initialized")

    async def _list_tools(self):
        """List available tools from the server."""
        tools_response = await self._send_request("tools/list")
        if "result" in tools_response and "tools" in tools_response["result"]:
            self.tools = tools_response["result"]["tools"]

    async def _send_request(self, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC request and wait for response."""
        if not self.process or not self.process.stdin:
            raise Exception("Not connected to MCP server")

        self.message_id += 1
        message = {"jsonrpc": "2.0", "id": self.message_id, "method": method}
        if params:
            message["params"] = params

        # Send message
        message_str = json.dumps(message) + "\n"
        self.process.stdin.write(message_str.encode())
        await self.process.stdin.drain()

        # Read response
        try:
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(), timeout=self.server_config.timeout
            )

            if not response_line:
                raise Exception("Server closed connection")

            response = json.loads(response_line.decode().strip())
            return response

        except asyncio.TimeoutError:
            raise Exception(f"Timeout waiting for response to {method}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {e}")

    async def _send_notification(self, method: str, params: dict | None = None):
        """Send a JSON-RPC notification (no response expected)."""
        if not self.process or not self.process.stdin:
            raise Exception("Not connected to MCP server")

        message = {"jsonrpc": "2.0", "method": method}
        if params:
            message["params"] = params

        message_str = json.dumps(message) + "\n"
        self.process.stdin.write(message_str.encode())
        await self.process.stdin.drain()

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a specific tool on the MCP server."""
        if not self.connected:
            raise Exception("Not connected to MCP server")

        # Check if tool is allowed
        if (
            self.server_config.always_allow
            and tool_name not in self.server_config.always_allow
        ):
            raise Exception(f"Tool '{tool_name}' not in allowlist")

        # Check if tool exists
        tool_names = [tool.get("name") for tool in self.tools]
        if tool_name not in tool_names:
            raise Exception(f"Tool '{tool_name}' not found. Available: {tool_names}")

        response = await self._send_request(
            "tools/call", {"name": tool_name, "arguments": arguments}
        )

        if "error" in response:
            raise Exception(f"Tool call failed: {response['error']}")

        return response.get("result", {})

    async def list_tools(self) -> list[dict[str, Any]]:
        """Get list of available tools."""
        return self.tools

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.process:
            try:
                # Send a graceful shutdown if possible
                if self.connected:
                    await self._send_notification("notifications/cancelled")
            except:
                pass  # Ignore errors during shutdown

            # Terminate the process
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()

            self.process = None
            self.connected = False