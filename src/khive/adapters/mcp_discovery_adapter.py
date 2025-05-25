# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
MCP Discovery Adapter - Pydapter-based adapter for MCP server and tool discovery.

This adapter provides comprehensive discovery of MCP servers and their available
tools, including parameter schemas and metadata for dynamic CLI generation.
"""

from __future__ import annotations

import fnmatch
import time
from datetime import datetime
from typing import Any

from .fastmcp_client import MCPClient, MCPConfig, load_mcp_config
from .mcp_models import (
    MCPDiscoveryRequest,
    MCPDiscoveryResponse,
    MCPServerInfo,
    MCPToolInfo,
)


class MCPDiscoveryAdapter:
    """
    Pydapter-compatible adapter for discovering MCP servers and tools.

    This adapter connects to all configured MCP servers, discovers their
    available tools, and extracts parameter schemas for dynamic validation.
    """

    def __init__(self, mcp_config: MCPConfig | None = None):
        """
        Initialize the MCP discovery adapter.

        Args:
            mcp_config: Optional MCP configuration (will be loaded if not provided)
        """
        self._mcp_config = mcp_config
        self._discovery_cache: MCPDiscoveryResponse | None = None
        self._cache_timestamp: datetime | None = None
        self._cache_ttl_seconds = 300  # 5 minutes cache TTL

    @property
    def obj_key(self) -> str:
        """Return the pydapter registry key for this adapter."""
        return "khive:mcp:discovery"

    async def from_obj(
        self, data: MCPDiscoveryRequest, **kwargs
    ) -> MCPDiscoveryResponse:
        """
        Discover MCP servers and tools (pydapter AsyncAdapter interface).

        Args:
            data: Discovery request with optional filters
            **kwargs: Additional keyword arguments

        Returns:
            MCPDiscoveryResponse with discovered servers and tools
        """
        start_time = time.time()

        try:
            # Check cache first
            if self._is_cache_valid():
                cached_response = self._apply_filters(self._discovery_cache, data)
                cached_response.discovery_time_ms = (time.time() - start_time) * 1000
                return cached_response

            # Load MCP configuration if not provided
            if self._mcp_config is None:
                self._mcp_config = await self._load_mcp_config()

            # Discover servers and tools
            servers = await self._discover_servers(data)
            tools = await self._discover_tools(data, servers)

            # Create response
            response = MCPDiscoveryResponse(
                servers=servers,
                tools=tools,
                total_servers=len(servers),
                total_tools=len(tools),
                discovery_time_ms=(time.time() - start_time) * 1000,
            )

            # Update cache
            self._discovery_cache = response
            self._cache_timestamp = datetime.utcnow()

            return response

        except Exception:
            # Return error response
            return MCPDiscoveryResponse(
                servers=[],
                tools=[],
                total_servers=0,
                total_tools=0,
                discovery_time_ms=(time.time() - start_time) * 1000,
            )

    async def to_obj(self, data: MCPDiscoveryResponse, **kwargs) -> Any:
        """
        Convert response back to object (not typically used for discovery).

        Args:
            data: Discovery response to convert
            **kwargs: Additional keyword arguments

        Returns:
            The response data as a dictionary
        """
        return data.model_dump()

    async def _load_mcp_config(self) -> MCPConfig:
        """Load MCP configuration from the project."""
        import subprocess
        from pathlib import Path

        try:
            project_root = Path(
                subprocess.check_output(
                    ["git", "rev-parse", "--show-toplevel"],
                    text=True,
                    stderr=subprocess.PIPE,
                ).strip()
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            project_root = Path.cwd()

        return load_mcp_config(project_root)

    async def _discover_servers(
        self, request: MCPDiscoveryRequest
    ) -> list[MCPServerInfo]:
        """
        Discover available MCP servers.

        Args:
            request: Discovery request with filters

        Returns:
            List of discovered server information
        """
        servers = []

        for server_name, server_config in self._mcp_config.servers.items():
            # Apply server filter
            if request.server_filter and not fnmatch.fnmatch(
                server_name, request.server_filter
            ):
                continue

            # Skip disabled servers unless requested
            if server_config.disabled and not request.include_disabled:
                continue

            # Try to connect and get server info
            try:
                client = MCPClient(server_config)
                connected = await client.connect()

                if connected:
                    server_info = MCPServerInfo(
                        name=server_name,
                        status="connected",
                        command=server_config.command,
                        tool_count=len(client.tools),
                        capabilities=client.server_info.get("capabilities", {}),
                        server_info=client.server_info,
                        disabled=server_config.disabled,
                        last_connected=datetime.utcnow(),
                    )
                    await client.disconnect()
                else:
                    server_info = MCPServerInfo(
                        name=server_name,
                        status="disconnected",
                        command=server_config.command,
                        tool_count=0,
                        capabilities={},
                        server_info=None,
                        disabled=server_config.disabled,
                        last_connected=None,
                    )

            except Exception:
                server_info = MCPServerInfo(
                    name=server_name,
                    status="error",
                    command=server_config.command,
                    tool_count=0,
                    capabilities={},
                    server_info=None,
                    disabled=server_config.disabled,
                    last_connected=None,
                )

            servers.append(server_info)

        return servers

    async def _discover_tools(
        self, request: MCPDiscoveryRequest, servers: list[MCPServerInfo]
    ) -> list[MCPToolInfo]:
        """
        Discover available tools from connected servers.

        Args:
            request: Discovery request with filters
            servers: List of discovered servers

        Returns:
            List of discovered tool information
        """
        tools = []

        for server_info in servers:
            if server_info.status != "connected":
                continue

            try:
                # Get server config
                server_config = self._mcp_config.servers[server_info.name]

                # Connect to server
                client = MCPClient(server_config)
                await client.connect()

                # Get tools from server
                server_tools = await client.list_tools()

                for tool in server_tools:
                    tool_name = tool.get("name", "")

                    # Apply tool filter
                    if request.tool_filter and not fnmatch.fnmatch(
                        tool_name, request.tool_filter
                    ):
                        continue

                    # Extract parameter schema
                    input_schema = tool.get("inputSchema", {})
                    parameters = input_schema if request.include_schemas else {}

                    # Extract required parameters
                    required_params = input_schema.get("required", [])

                    tool_info = MCPToolInfo(
                        server_name=server_info.name,
                        tool_name=tool_name,
                        description=tool.get("description"),
                        parameters=parameters,
                        required_params=required_params,
                    )

                    tools.append(tool_info)

                await client.disconnect()

            except Exception:
                # Skip servers that fail to connect
                continue

        return tools

    def _is_cache_valid(self) -> bool:
        """Check if the discovery cache is still valid."""
        if self._discovery_cache is None or self._cache_timestamp is None:
            return False

        cache_age = (datetime.utcnow() - self._cache_timestamp).total_seconds()
        return cache_age < self._cache_ttl_seconds

    def _apply_filters(
        self, cached_response: MCPDiscoveryResponse, request: MCPDiscoveryRequest
    ) -> MCPDiscoveryResponse:
        """
        Apply filters to cached discovery response.

        Args:
            cached_response: Cached discovery response
            request: Discovery request with filters

        Returns:
            Filtered discovery response
        """
        filtered_servers = []
        filtered_tools = []

        # Filter servers
        for server in cached_response.servers:
            if request.server_filter and not fnmatch.fnmatch(
                server.name, request.server_filter
            ):
                continue

            if server.disabled and not request.include_disabled:
                continue

            filtered_servers.append(server)

        # Filter tools
        for tool in cached_response.tools:
            if request.server_filter and not fnmatch.fnmatch(
                tool.server_name, request.server_filter
            ):
                continue

            if request.tool_filter and not fnmatch.fnmatch(
                tool.tool_name, request.tool_filter
            ):
                continue

            # Only include tools from servers that passed the server filter
            if any(s.name == tool.server_name for s in filtered_servers):
                filtered_tools.append(tool)

        return MCPDiscoveryResponse(
            servers=filtered_servers,
            tools=filtered_tools,
            total_servers=len(filtered_servers),
            total_tools=len(filtered_tools),
            discovery_time_ms=0,  # Will be updated by caller
        )

    async def invalidate_cache(self) -> None:
        """Invalidate the discovery cache to force fresh discovery."""
        self._discovery_cache = None
        self._cache_timestamp = None

    async def aclose(self) -> None:
        """Close the adapter and clean up resources."""
        # Clear cache
        await self.invalidate_cache()


# Factory function for creating discovery adapters
async def create_mcp_discovery_adapter(**kwargs) -> MCPDiscoveryAdapter:
    """
    Factory function for creating MCP discovery adapters.

    Args:
        **kwargs: Additional configuration options

    Returns:
        Configured MCPDiscoveryAdapter instance
    """
    return MCPDiscoveryAdapter(**kwargs)
