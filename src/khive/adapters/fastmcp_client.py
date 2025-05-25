# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
FastMCP Client - TRUE FastMCP v2 implementation using high-level abstractions.

This module properly uses FastMCP v2's decorators and high-level features,
demonstrating Khive's principle: "tools should unify, not multiply."
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.client import Client


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


def load_mcp_config(project_r: Path, cli_args: Any | None = None) -> MCPConfig:
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
                print(
                    f"Warning: Could not parse MCP config: {e}. Using empty configuration."
                )

    # Apply CLI arguments
    if cli_args:
        cfg.json_output = getattr(cli_args, "json_output", False)
        cfg.dry_run = getattr(cli_args, "dry_run", False)
        cfg.verbose = getattr(cli_args, "verbose", False)

    return cfg


class FastMCPClient:
    """TRUE FastMCP v2 client using high-level abstractions."""

    def __init__(self, server_config: MCPServerConfig):
        self.server_config = server_config
        self.client: Client | None = None
        self.connected = False
        self.server_info: dict[str, Any] = {}
        self.tools: list[dict[str, Any]] = []

        # Create FastMCP app for client operations
        self.app = FastMCP(name=f"khive-client-{server_config.name}")

    async def connect(self) -> bool:
        """Connect to the MCP server using FastMCP v2 high-level client."""
        try:
            # Build the command
            cmd = [self.server_config.command] + self.server_config.args

            # Create a FastMCP client connection
            self.client = await self.app.create_client(
                command=cmd,
                env=self.server_config.env,
                timeout=self.server_config.timeout,
            )

            # Get server information
            self.server_info = await self.client.get_server_info()

            # Get available tools
            tools_response = await self.client.list_tools()
            self.tools = tools_response if isinstance(tools_response, list) else []

            self.connected = True
            return True

        except Exception:
            if self.client:
                await self.client.close()
                self.client = None
            self.connected = False
            return False

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a tool using FastMCP v2 high-level client."""
        if not self.connected or not self.client:
            raise Exception("Not connected to MCP server")

        # Check if tool is allowed
        if (
            self.server_config.always_allow
            and tool_name not in self.server_config.always_allow
        ):
            raise Exception(f"Tool '{tool_name}' not in allowlist")

        # Check if tool exists
        tool_names = [tool.get("name", "") for tool in self.tools]
        if tool_name not in tool_names:
            raise Exception(f"Tool '{tool_name}' not found. Available: {tool_names}")

        # Call the tool using FastMCP v2 client
        result = await self.client.call_tool(tool_name, **arguments)

        # Convert result to expected format
        if isinstance(result, dict):
            return result
        else:
            # Wrap simple results in our expected format
            return {"content": [{"type": "text", "text": str(result)}]}

    async def list_tools(self) -> list[dict[str, Any]]:
        """Get list of available tools."""
        return self.tools

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.client:
            await self.client.close()
            self.client = None
            self.connected = False


# Backward compatibility alias
MCPClient = FastMCPClient
