# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
FastMCP Client - Simplified MCP client using FastMCP library.

This module replaces the custom 262-line MCP implementation with FastMCP,
demonstrating Khive's principle: "tools should unify, not multiply."
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from fastmcp import FastMCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


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
                print(f"Warning: Could not parse MCP config: {e}. Using empty configuration.")

    # Apply CLI arguments
    if cli_args:
        cfg.json_output = getattr(cli_args, 'json_output', False)
        cfg.dry_run = getattr(cli_args, 'dry_run', False)
        cfg.verbose = getattr(cli_args, 'verbose', False)

    return cfg


class FastMCPClient:
    """FastMCP-based MCP client that replaces our custom 262-line implementation."""

    def __init__(self, server_config: MCPServerConfig):
        self.server_config = server_config
        self.session: Optional[ClientSession] = None
        self.connected = False
        self.server_info: dict[str, Any] = {}
        self.tools: list[dict[str, Any]] = []

    async def connect(self) -> bool:
        """Connect to the MCP server using FastMCP."""
        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(self.server_config.env)

            # Create server parameters
            server_params = StdioServerParameters(
                command=self.server_config.command,
                args=self.server_config.args,
                env=env
            )

            # Connect using FastMCP's stdio client
            self.session = await stdio_client(server_params)
            
            # Initialize the session
            init_result = await self.session.initialize()
            self.server_info = init_result.model_dump()

            # List available tools
            tools_result = await self.session.list_tools()
            self.tools = [tool.model_dump() for tool in tools_result.tools]

            self.connected = True
            return True

        except Exception as e:
            if self.session:
                await self.session.close()
                self.session = None
            return False

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a specific tool on the MCP server."""
        if not self.connected or not self.session:
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

        # Call the tool using FastMCP
        result = await self.session.call_tool(tool_name, arguments)
        
        # Convert result to our expected format
        return {
            "content": [
                {
                    "type": content.type,
                    "text": getattr(content, 'text', str(content))
                }
                for content in result.content
            ]
        }

    async def list_tools(self) -> list[dict[str, Any]]:
        """Get list of available tools."""
        return self.tools

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.session:
            await self.session.close()
            self.session = None
            self.connected = False


# Backward compatibility alias
MCPClient = FastMCPClient