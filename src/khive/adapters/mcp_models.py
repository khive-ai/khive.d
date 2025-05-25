# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
MCP Adapter Data Models - Pydantic models for MCP adapter interactions.

These models define the data structures used by MCP adapters following
the pydapter pattern for type-safe, validated data transformations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CapabilityContext(BaseModel):
    """Security capability context for adapter operations (TDS-149 integration)."""
    
    principal_id: str = Field(..., description="ID of the principal (agent/user) making the request")
    capability_token: Optional[str] = Field(None, description="JWT capability token for authorization")
    request_id: Optional[str] = Field(None, description="Unique request identifier for audit trail")
    source_ip: Optional[str] = Field(None, description="Source IP address if applicable")
    
    class Config:
        json_schema_extra = {
            "example": {
                "principal_id": "agent_research_001",
                "capability_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9...",
                "request_id": "req_12345",
                "source_ip": "192.168.1.100"
            }
        }


class MCPToolRequest(BaseModel):
    """Request model for MCP tool execution."""
    
    server_name: str = Field(..., description="Name of the MCP server to call")
    tool_name: str = Field(..., description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    timeout: Optional[int] = Field(None, description="Timeout in seconds for tool execution")
    
    class Config:
        json_schema_extra = {
            "example": {
                "server_name": "filesystem",
                "tool_name": "read_file",
                "arguments": {
                    "path": "/home/user/document.txt"
                },
                "timeout": 30
            }
        }


class MCPToolResponse(BaseModel):
    """Response model for MCP tool execution."""
    
    success: bool = Field(..., description="Whether the tool execution was successful")
    result: Optional[Dict[str, Any]] = Field(None, description="Tool execution result data")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    server_name: str = Field(..., description="Name of the server that executed the tool")
    tool_name: str = Field(..., description="Name of the executed tool")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": "File contents here..."
                        }
                    ]
                },
                "error": None,
                "execution_time_ms": 150.5,
                "server_name": "filesystem",
                "tool_name": "read_file"
            }
        }


class MCPDiscoveryRequest(BaseModel):
    """Request model for MCP server and tool discovery."""
    
    server_filter: Optional[str] = Field(None, description="Filter servers by name pattern")
    tool_filter: Optional[str] = Field(None, description="Filter tools by name pattern")
    include_disabled: bool = Field(False, description="Include disabled servers in discovery")
    include_schemas: bool = Field(True, description="Include parameter schemas in tool info")
    
    class Config:
        json_schema_extra = {
            "example": {
                "server_filter": "filesystem*",
                "tool_filter": "*file*",
                "include_disabled": False,
                "include_schemas": True
            }
        }


class MCPToolInfo(BaseModel):
    """Information about an available MCP tool."""
    
    server_name: str = Field(..., description="Name of the server providing this tool")
    tool_name: str = Field(..., description="Name of the tool")
    description: Optional[str] = Field(None, description="Tool description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema for tool parameters")
    required_params: List[str] = Field(default_factory=list, description="List of required parameter names")
    
    class Config:
        json_schema_extra = {
            "example": {
                "server_name": "filesystem",
                "tool_name": "read_file",
                "description": "Read the complete contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to read"
                        }
                    },
                    "required": ["path"]
                },
                "required_params": ["path"]
            }
        }


class MCPServerInfo(BaseModel):
    """Information about an MCP server."""
    
    name: str = Field(..., description="Server name")
    status: str = Field(..., description="Connection status (connected/disconnected/error)")
    command: str = Field(..., description="Command used to start the server")
    tool_count: int = Field(default=0, description="Number of available tools")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Server capabilities")
    server_info: Optional[Dict[str, Any]] = Field(None, description="Server-provided information")
    disabled: bool = Field(False, description="Whether the server is disabled")
    last_connected: Optional[datetime] = Field(None, description="Last successful connection time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "filesystem",
                "status": "connected",
                "command": "npx",
                "tool_count": 5,
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {}
                },
                "server_info": {
                    "name": "filesystem-server",
                    "version": "1.0.0"
                },
                "disabled": False,
                "last_connected": "2025-05-24T20:07:30Z"
            }
        }


class MCPDiscoveryResponse(BaseModel):
    """Response model for MCP discovery operations."""
    
    servers: List[MCPServerInfo] = Field(default_factory=list, description="Discovered servers")
    tools: List[MCPToolInfo] = Field(default_factory=list, description="Discovered tools")
    total_servers: int = Field(default=0, description="Total number of servers")
    total_tools: int = Field(default=0, description="Total number of tools")
    discovery_time_ms: Optional[float] = Field(None, description="Time taken for discovery in milliseconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "servers": [
                    {
                        "name": "filesystem",
                        "status": "connected",
                        "command": "npx",
                        "tool_count": 5,
                        "capabilities": {},
                        "disabled": False
                    }
                ],
                "tools": [
                    {
                        "server_name": "filesystem",
                        "tool_name": "read_file",
                        "description": "Read file contents",
                        "parameters": {},
                        "required_params": ["path"]
                    }
                ],
                "total_servers": 1,
                "total_tools": 5,
                "discovery_time_ms": 250.0
            }
        }


class MCPServerAdapterConfig(BaseModel):
    """Configuration for MCPServerAdapter instances."""
    
    server_name: str = Field(..., description="Name of the MCP server")
    capability_context: Optional[CapabilityContext] = Field(None, description="Security capability context")
    connection_timeout: int = Field(30, description="Connection timeout in seconds")
    call_timeout: int = Field(60, description="Tool call timeout in seconds")
    enable_audit_logging: bool = Field(True, description="Enable audit logging for tool calls")
    
    class Config:
        json_schema_extra = {
            "example": {
                "server_name": "filesystem",
                "capability_context": {
                    "principal_id": "agent_001",
                    "capability_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9..."
                },
                "connection_timeout": 30,
                "call_timeout": 60,
                "enable_audit_logging": True
            }
        }