# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for MCP adapters."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from khive.adapters import (
    MCPServerAdapter,
    MCPServerAdapterConfig,
    MCPDiscoveryAdapter,
    MCPToolRequest,
    MCPToolResponse,
    MCPDiscoveryRequest,
    MCPDiscoveryResponse,
    MCPServerInfo,
    MCPToolInfo,
    CapabilityContext,
)


class TestMCPServerAdapter:
    """Test the MCPServerAdapter class."""

    def test_obj_key_generation(self):
        """Test that obj_key is generated correctly."""
        config = MCPServerAdapterConfig(server_name="test_server")
        adapter = MCPServerAdapter(config)
        
        assert adapter.obj_key == "khive:mcp:server:test_server"

    def test_config_initialization(self):
        """Test adapter configuration initialization."""
        capability_context = CapabilityContext(
            principal_id="test_agent",
            capability_token="test_token"
        )
        
        config = MCPServerAdapterConfig(
            server_name="test_server",
            capability_context=capability_context,
            connection_timeout=45,
            call_timeout=90,
            enable_audit_logging=False
        )
        
        adapter = MCPServerAdapter(config)
        
        assert adapter.config.server_name == "test_server"
        assert adapter.config.capability_context.principal_id == "test_agent"
        assert adapter.config.connection_timeout == 45
        assert adapter.config.call_timeout == 90
        assert adapter.config.enable_audit_logging is False

    @pytest.mark.asyncio
    async def test_from_obj_success(self):
        """Test successful tool execution via from_obj."""
        config = MCPServerAdapterConfig(
            server_name="test_server",
            enable_audit_logging=False
        )
        
        # Mock the MCP client
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"content": [{"type": "text", "text": "success"}]}
        
        with patch('khive.adapters.mcp_client.MCPClient') as mock_client_class:
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = True
            
            with patch('khive.adapters.mcp_client.load_mcp_config') as mock_load_config:
                mock_mcp_config = MagicMock()
                mock_mcp_config.servers = {
                    "test_server": MagicMock(name="test_server", command="test", args=[])
                }
                mock_load_config.return_value = mock_mcp_config
                
                adapter = MCPServerAdapter(config)
                
                request = MCPToolRequest(
                    server_name="test_server",
                    tool_name="test_tool",
                    arguments={"param1": "value1"}
                )
                
                response = await adapter.from_obj(request)
                
                assert isinstance(response, MCPToolResponse)
                assert response.success is True
                assert response.result == {"content": [{"type": "text", "text": "success"}]}
                assert response.server_name == "test_server"
                assert response.tool_name == "test_tool"
                assert response.execution_time_ms is not None

    @pytest.mark.asyncio
    async def test_from_obj_with_capability_validation(self):
        """Test tool execution with capability context."""
        capability_context = CapabilityContext(
            principal_id="test_agent",
            capability_token="test_token"
        )
        
        config = MCPServerAdapterConfig(
            server_name="test_server",
            capability_context=capability_context,
            enable_audit_logging=True
        )
        
        # Mock the MCP client
        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {"result": "success"}
        
        with patch('khive.adapters.mcp_client.MCPClient') as mock_client_class:
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = True
            
            with patch('khive.adapters.mcp_client.load_mcp_config') as mock_load_config:
                mock_mcp_config = MagicMock()
                mock_mcp_config.servers = {
                    "test_server": MagicMock(name="test_server", command="test", args=[])
                }
                mock_load_config.return_value = mock_mcp_config
                
                adapter = MCPServerAdapter(config)
                
                request = MCPToolRequest(
                    server_name="test_server",
                    tool_name="test_tool",
                    arguments={"param1": "value1"}
                )
                
                # Should not raise an exception (capability validation is placeholder)
                response = await adapter.from_obj(request)
                
                assert response.success is True


class TestMCPDiscoveryAdapter:
    """Test the MCPDiscoveryAdapter class."""

    def test_obj_key(self):
        """Test that obj_key is correct."""
        adapter = MCPDiscoveryAdapter()
        assert adapter.obj_key == "khive:mcp:discovery"

    @pytest.mark.asyncio
    async def test_from_obj_basic_discovery(self):
        """Test basic discovery functionality."""
        # Mock the MCP config loading
        with patch('khive.adapters.mcp_client.load_mcp_config') as mock_load_config:
            mock_mcp_config = MagicMock()
            mock_mcp_config.servers = {
                "test_server": MagicMock(
                    name="test_server",
                    command="test_command",
                    disabled=False
                )
            }
            mock_load_config.return_value = mock_mcp_config
            
            # Mock the MCP client
            with patch('khive.adapters.mcp_client.MCPClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.connect.return_value = True
                mock_client.tools = [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"param1": {"type": "string"}},
                            "required": ["param1"]
                        }
                    }
                ]
                mock_client.server_info = {"capabilities": {"tools": {}}}
                mock_client_class.return_value = mock_client
                
                adapter = MCPDiscoveryAdapter()
                
                request = MCPDiscoveryRequest(
                    server_filter=None,
                    tool_filter=None,
                    include_disabled=False,
                    include_schemas=True
                )
                
                response = await adapter.from_obj(request)
                
                assert isinstance(response, MCPDiscoveryResponse)
                assert response.total_servers == 1
                assert response.total_tools == 1
                assert len(response.servers) == 1
                assert len(response.tools) == 1
                
                server = response.servers[0]
                assert server.name == "test_server"
                assert server.status == "connected"
                assert server.tool_count == 1
                
                tool = response.tools[0]
                assert tool.server_name == "test_server"
                assert tool.tool_name == "test_tool"
                assert tool.description == "A test tool"
                assert "param1" in tool.required_params

    @pytest.mark.asyncio
    async def test_cache_functionality(self):
        """Test that caching works correctly."""
        adapter = MCPDiscoveryAdapter()
        
        # Verify cache is initially empty
        assert adapter._discovery_cache is None
        assert not adapter._is_cache_valid()
        
        # After setting cache, it should be valid
        adapter._discovery_cache = MCPDiscoveryResponse(
            servers=[],
            tools=[],
            total_servers=0,
            total_tools=0
        )
        from datetime import datetime
        adapter._cache_timestamp = datetime.utcnow()
        
        assert adapter._is_cache_valid()
        
        # Test cache invalidation
        await adapter.invalidate_cache()
        assert adapter._discovery_cache is None
        assert adapter._cache_timestamp is None


class TestDataModels:
    """Test the Pydantic data models."""

    def test_capability_context_model(self):
        """Test CapabilityContext model validation."""
        context = CapabilityContext(
            principal_id="test_agent",
            capability_token="jwt_token_here",
            request_id="req_123",
            source_ip="192.168.1.1"
        )
        
        assert context.principal_id == "test_agent"
        assert context.capability_token == "jwt_token_here"
        assert context.request_id == "req_123"
        assert context.source_ip == "192.168.1.1"

    def test_mcp_tool_request_model(self):
        """Test MCPToolRequest model validation."""
        request = MCPToolRequest(
            server_name="filesystem",
            tool_name="read_file",
            arguments={"path": "/test/file.txt"},
            timeout=30
        )
        
        assert request.server_name == "filesystem"
        assert request.tool_name == "read_file"
        assert request.arguments == {"path": "/test/file.txt"}
        assert request.timeout == 30

    def test_mcp_tool_response_model(self):
        """Test MCPToolResponse model validation."""
        response = MCPToolResponse(
            success=True,
            result={"content": [{"type": "text", "text": "file contents"}]},
            error=None,
            execution_time_ms=150.5,
            server_name="filesystem",
            tool_name="read_file"
        )
        
        assert response.success is True
        assert response.result["content"][0]["text"] == "file contents"
        assert response.error is None
        assert response.execution_time_ms == 150.5
        assert response.server_name == "filesystem"
        assert response.tool_name == "read_file"

    def test_mcp_discovery_request_model(self):
        """Test MCPDiscoveryRequest model validation."""
        request = MCPDiscoveryRequest(
            server_filter="filesystem*",
            tool_filter="*file*",
            include_disabled=True,
            include_schemas=False
        )
        
        assert request.server_filter == "filesystem*"
        assert request.tool_filter == "*file*"
        assert request.include_disabled is True
        assert request.include_schemas is False

    def test_mcp_server_info_model(self):
        """Test MCPServerInfo model validation."""
        from datetime import datetime
        
        server_info = MCPServerInfo(
            name="filesystem",
            status="connected",
            command="npx",
            tool_count=5,
            capabilities={"tools": {}, "resources": {}},
            disabled=False,
            last_connected=datetime.utcnow()
        )
        
        assert server_info.name == "filesystem"
        assert server_info.status == "connected"
        assert server_info.command == "npx"
        assert server_info.tool_count == 5
        assert "tools" in server_info.capabilities
        assert server_info.disabled is False
        assert server_info.last_connected is not None

    def test_mcp_tool_info_model(self):
        """Test MCPToolInfo model validation."""
        tool_info = MCPToolInfo(
            server_name="filesystem",
            tool_name="read_file",
            description="Read a file",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            },
            required_params=["path"]
        )
        
        assert tool_info.server_name == "filesystem"
        assert tool_info.tool_name == "read_file"
        assert tool_info.description == "Read a file"
        assert "path" in tool_info.parameters["properties"]
        assert "path" in tool_info.required_params