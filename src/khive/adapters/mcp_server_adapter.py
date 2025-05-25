# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
MCP Server Adapter - Pydapter-based adapter for MCP server interactions.

This adapter wraps the existing MCPClient functionality in a pydapter-compatible
interface, providing obj_key-based registry integration and capability-based
security integration points.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import time
from datetime import datetime
from typing import Any

from .fastmcp_client import MCPClient, MCPConfig, load_mcp_config
from .mcp_models import (
    CapabilityContext,
    MCPServerAdapterConfig,
    MCPToolRequest,
    MCPToolResponse,
)

# Global registry for MCP clients (reuse existing pattern)
_adapter_clients: dict[str, MCPClient] = {}


class MCPServerAdapter:
    """
    Pydapter-compatible adapter for MCP server interactions.

    This adapter provides a clean interface for calling MCP tools while
    integrating with the pydapter registry system and security framework.
    """

    def __init__(
        self, config: MCPServerAdapterConfig, mcp_config: MCPConfig | None = None
    ):
        """
        Initialize the MCP server adapter.

        Args:
            config: Adapter configuration including server name and security context
            mcp_config: Optional MCP configuration (will be loaded if not provided)
        """
        self.config = config
        self._mcp_config = mcp_config
        self._client: MCPClient | None = None

    @property
    def obj_key(self) -> str:
        """Return the pydapter registry key for this adapter."""
        return f"khive:mcp:server:{self.config.server_name}"

    async def from_obj(self, data: MCPToolRequest, **kwargs) -> MCPToolResponse:
        """
        Execute an MCP tool call (pydapter AsyncAdapter interface).

        Args:
            data: Tool request containing server name, tool name, and arguments
            **kwargs: Additional keyword arguments

        Returns:
            MCPToolResponse with execution results
        """
        start_time = time.time()

        try:
            # Security integration point (TDS-149)
            if self.config.capability_context:
                await self._validate_capability(data)

            # Get or create MCP client connection
            client = await self._get_client()

            # Execute the tool call with timeout
            timeout = data.timeout or self.config.call_timeout
            result = await asyncio.wait_for(
                client.call_tool(data.tool_name, data.arguments), timeout=timeout
            )

            execution_time_ms = (time.time() - start_time) * 1000

            response = MCPToolResponse(
                success=True,
                result=result,
                error=None,
                execution_time_ms=execution_time_ms,
                server_name=data.server_name,
                tool_name=data.tool_name,
            )

            # Audit logging
            if self.config.enable_audit_logging:
                await self._audit_log_tool_call(data, response, execution_time_ms)

            return response

        except asyncio.TimeoutError:
            execution_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Tool call timed out after {timeout} seconds"

            response = MCPToolResponse(
                success=False,
                result=None,
                error=error_msg,
                execution_time_ms=execution_time_ms,
                server_name=data.server_name,
                tool_name=data.tool_name,
            )

            if self.config.enable_audit_logging:
                await self._audit_log_tool_call(data, response, execution_time_ms)

            return response

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)

            response = MCPToolResponse(
                success=False,
                result=None,
                error=error_msg,
                execution_time_ms=execution_time_ms,
                server_name=data.server_name,
                tool_name=data.tool_name,
            )

            if self.config.enable_audit_logging:
                await self._audit_log_tool_call(data, response, execution_time_ms)

            return response

    async def to_obj(self, data: MCPToolResponse, **kwargs) -> Any:
        """
        Convert response back to object (not typically used for MCP).

        Args:
            data: Tool response to convert
            **kwargs: Additional keyword arguments

        Returns:
            The response data
        """
        return data.result if data.success else {"error": data.error}

    async def _get_client(self) -> MCPClient:
        """Get or create an MCP client for this server."""
        client_key = f"{self.config.server_name}"

        if client_key not in _adapter_clients:
            # Load MCP configuration if not provided
            if self._mcp_config is None:
                import subprocess
                from pathlib import Path

                try:
                    # Use shutil.which to get full path to git executable for security
                    git_cmd = shutil.which("git")
                    if not git_cmd:
                        raise FileNotFoundError("git command not found in PATH")
                    
                    project_root = Path(
                        subprocess.check_output(  # noqa: S603 # git command with validated executable path
                            [git_cmd, "rev-parse", "--show-toplevel"],
                            text=True,
                            stderr=subprocess.PIPE,
                            shell=False,  # Explicitly disable shell for security
                        ).strip()
                    )
                except (subprocess.CalledProcessError, FileNotFoundError):
                    project_root = Path.cwd()

                self._mcp_config = load_mcp_config(project_root)

            # Get server configuration
            if self.config.server_name not in self._mcp_config.servers:
                raise ValueError(
                    f"Server '{self.config.server_name}' not found in MCP configuration"
                )

            server_config = self._mcp_config.servers[self.config.server_name]

            # Create and connect client
            client = MCPClient(server_config)
            if await client.connect():
                _adapter_clients[client_key] = client
            else:
                raise RuntimeError(
                    f"Failed to connect to MCP server '{self.config.server_name}'"
                )

        return _adapter_clients[client_key]

    async def _validate_capability(self, request: MCPToolRequest) -> None:
        """
        Validate capability for the requested operation (TDS-149 integration point).

        This is a placeholder implementation for future security integration.
        When the full TDS-149 security architecture is implemented, this method
        will perform actual capability validation.

        Args:
            request: The tool request to validate

        Raises:
            PermissionError: If capability validation fails
        """
        if not self.config.capability_context:
            return

        # Log the capability check for now
        print(
            f"CAPABILITY_CHECK: {self.config.capability_context.principal_id} -> "
            f"{request.server_name}:{request.tool_name}"
        )

        # TODO: Implement actual capability validation when TDS-149 is complete
        # This would involve:
        # 1. Validating capability token signature
        # 2. Checking token expiration
        # 3. Verifying action is allowed by capability
        # 4. Checking resource constraints

        # For now, just validate that we have a principal_id
        if not self.config.capability_context.principal_id:
            raise PermissionError("No principal_id provided in capability context")

    async def _audit_log_tool_call(
        self, request: MCPToolRequest, response: MCPToolResponse, duration_ms: float
    ) -> None:
        """
        Log tool call for security audit trail.

        Args:
            request: The original tool request
            response: The tool response
            duration_ms: Execution duration in milliseconds
        """
        audit_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "MCP_TOOL_CALL",
            "principal_id": (
                self.config.capability_context.principal_id
                if self.config.capability_context
                else "unknown"
            ),
            "server_name": request.server_name,
            "tool_name": request.tool_name,
            "success": response.success,
            "duration_ms": duration_ms,
            "argument_count": len(request.arguments),
            "error": response.error,
            "request_id": (
                self.config.capability_context.request_id
                if self.config.capability_context
                else None
            ),
        }

        # For now, just print the audit log
        # TODO: Send to centralized audit logging system
        print(f"AUDIT: {json.dumps(audit_data)}")

    async def aclose(self) -> None:
        """Close the adapter and clean up resources."""
        client_key = f"{self.config.server_name}"
        if client_key in _adapter_clients:
            client = _adapter_clients.pop(client_key)
            await client.disconnect()


# Factory function for creating adapters (pydapter registry pattern)
async def create_mcp_server_adapter(
    server_name: str, capability_context: CapabilityContext | None = None, **kwargs
) -> MCPServerAdapter:
    """
    Factory function for creating MCP server adapters.

    Args:
        server_name: Name of the MCP server
        capability_context: Optional security capability context
        **kwargs: Additional configuration options

    Returns:
        Configured MCPServerAdapter instance
    """
    config = MCPServerAdapterConfig(
        server_name=server_name, capability_context=capability_context, **kwargs
    )

    return MCPServerAdapter(config)


# Utility function for disconnecting all adapter clients
async def disconnect_all_adapter_clients() -> None:
    """Disconnect all MCP clients managed by adapters."""
    for client in _adapter_clients.values():
        await client.disconnect()
    _adapter_clients.clear()
