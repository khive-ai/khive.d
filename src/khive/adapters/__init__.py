# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Khive Adapters - Pydapter-based adapter implementations.

This module contains adapter implementations that follow the pydapter pattern
for composable, secure, and discoverable service interactions.
"""

from .mcp_discovery_adapter import MCPDiscoveryAdapter, create_mcp_discovery_adapter
from .mcp_models import (
    CapabilityContext,
    MCPDiscoveryRequest,
    MCPDiscoveryResponse,
    MCPServerAdapterConfig,
    MCPServerInfo,
    MCPToolInfo,
    MCPToolRequest,
    MCPToolResponse,
)
from .mcp_server_adapter import (
    MCPServerAdapter,
    create_mcp_server_adapter,
    disconnect_all_adapter_clients,
)

__all__ = [
    # Data models
    "MCPToolRequest",
    "MCPToolResponse",
    "MCPDiscoveryRequest",
    "MCPDiscoveryResponse",
    "MCPServerInfo",
    "MCPToolInfo",
    "CapabilityContext",
    "MCPServerAdapterConfig",
    # Adapters
    "MCPServerAdapter",
    "MCPDiscoveryAdapter",
    # Factory functions
    "create_mcp_server_adapter",
    "create_mcp_discovery_adapter",
    # Utilities
    "disconnect_all_adapter_clients",
]
