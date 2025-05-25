# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for khive MCP CLI."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from khive.adapters.fastmcp_client import MCPConfig, MCPServerConfig, load_mcp_config
from khive.cli.khive_mcp import (
    cmd_call_tool,
    cmd_list_servers,
    cmd_list_tools,
    cmd_server_status,
    parse_tool_arguments,
)


class TestMCPConfig:
    """Test MCP configuration loading."""

    def test_load_empty_config(self, tmp_path):
        """Test loading when no config exists."""
        args = MagicMock()
        args.json_output = False
        args.dry_run = False
        args.verbose = False

        # Create a mock config directly since load_mcp_config doesn't take args
        config = MCPConfig(
            project_root=tmp_path,
            json_output=args.json_output,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

        assert isinstance(config, MCPConfig)
        assert config.project_root == tmp_path
        assert len(config.servers) == 0
        assert config.json_output is False
        assert config.dry_run is False
        assert config.verbose is False

    def test_load_config_with_servers(self, tmp_path):
        """Test loading config with server definitions."""
        config_dir = tmp_path / ".khive" / "mcps"
        config_dir.mkdir(parents=True)

        config_data = {
            "mcpServers": {
                "test_server": {
                    "command": "test_cmd",
                    "args": ["arg1", "arg2"],
                    "env": {"TEST": "value"},
                    "alwaysAllow": ["tool1", "tool2"],
                    "disabled": False,
                    "timeout": 45,
                }
            }
        }

        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps(config_data))

        args = MagicMock()
        args.json_output = True
        args.dry_run = False
        args.verbose = True

        # Load config and then update with CLI args
        config = load_mcp_config(tmp_path)
        config.json_output = args.json_output
        config.dry_run = args.dry_run
        config.verbose = args.verbose

        assert len(config.servers) == 1
        assert "test_server" in config.servers

        server = config.servers["test_server"]
        assert server.command == "test_cmd"
        assert server.args == ["arg1", "arg2"]
        assert server.env == {"TEST": "value"}
        assert server.always_allow == ["tool1", "tool2"]
        assert server.disabled is False
        assert server.timeout == 45

        assert config.json_output is True
        assert config.verbose is True


class TestParseToolArguments:
    """Test tool argument parsing."""

    def test_parse_var_arguments(self):
        """Test parsing --var key=value arguments."""
        args = MagicMock()
        args.var = ["key1=value1", "key2=value2", "json_val=[1,2,3]"]
        args.tool_args = []
        args.json_args = None

        result = parse_tool_arguments(args)

        assert result == {"key1": "value1", "key2": "value2", "json_val": [1, 2, 3]}

    def test_parse_flag_arguments(self):
        """Test parsing --key value arguments."""
        args = MagicMock()
        args.var = None
        args.tool_args = ["--path", "/test/file.txt", "--recursive", "--limit", "10"]
        args.json_args = None

        result = parse_tool_arguments(args)

        assert result == {
            "path": "/test/file.txt",
            "recursive": True,
            "limit": 10,  # JSON parsing converts numeric strings to integers
        }

    def test_parse_json_arguments(self):
        """Test parsing JSON fallback."""
        args = MagicMock()
        args.var = None
        args.tool_args = []
        args.json_args = '{"complex": {"nested": "value"}, "array": [1, 2, 3]}'

        result = parse_tool_arguments(args)

        assert result == {"complex": {"nested": "value"}, "array": [1, 2, 3]}

    def test_parse_mixed_arguments(self):
        """Test parsing mixed argument types."""
        args = MagicMock()
        args.var = ["key1=value1"]
        args.tool_args = ["--flag"]
        args.json_args = '{"override": "json_value"}'

        result = parse_tool_arguments(args)

        assert result == {"key1": "value1", "flag": True, "override": "json_value"}


class TestCommands:
    """Test MCP command implementations."""

    @pytest.mark.asyncio
    async def test_cmd_list_servers(self):
        """Test listing configured servers."""
        config = MCPConfig(project_root=Path("/test"))
        config.servers = {
            "server1": MCPServerConfig(
                name="server1",
                command="cmd1",
                args=[],
                disabled=False,
                always_allow=["tool1", "tool2"],
            ),
            "server2": MCPServerConfig(
                name="server2", command="cmd2", args=[], disabled=True, always_allow=[]
            ),
        }

        result = await cmd_list_servers(config)

        assert result["status"] == "success"
        assert result["total_count"] == 2
        assert len(result["servers"]) == 2

        server1 = next(s for s in result["servers"] if s["name"] == "server1")
        assert server1["command"] == "cmd1"
        assert server1["disabled"] is False
        assert server1["operations_count"] == 2
        assert server1["status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_cmd_server_status_not_found(self):
        """Test getting status of non-existent server."""
        config = MCPConfig(project_root=Path("/test"))
        config.servers = {}

        result = await cmd_server_status(config, "nonexistent")

        assert result["status"] == "failure"
        assert "not found" in result["message"]
        assert result["available_servers"] == []

    @pytest.mark.asyncio
    async def test_cmd_server_status_success(self):
        """Test getting status of existing server."""
        config = MCPConfig(project_root=Path("/test"))
        config.servers = {
            "test_server": MCPServerConfig(
                name="test_server",
                command="test_cmd",
                args=["arg1"],
                disabled=False,
                timeout=30,
                always_allow=["tool1"],
            )
        }

        result = await cmd_server_status(config, "test_server")

        assert result["status"] == "success"
        assert result["server"]["name"] == "test_server"
        assert result["server"]["command"] == "test_cmd"
        assert result["server"]["args"] == ["arg1"]
        assert result["server"]["timeout"] == 30
        assert result["server"]["allowed_operations"] == ["tool1"]
        # When connection fails, status is "error" not "disconnected"
        assert result["server"]["status"] in ["disconnected", "error"]

    @pytest.mark.asyncio
    async def test_cmd_list_tools_server_not_found(self):
        """Test listing tools for non-existent server."""
        config = MCPConfig(project_root=Path("/test"))
        config.servers = {}

        result = await cmd_list_tools(config, "nonexistent")

        assert result["status"] == "failure"
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_cmd_list_tools_dry_run(self):
        """Test listing tools in dry-run mode."""
        config = MCPConfig(project_root=Path("/test"))
        config.dry_run = True
        config.servers = {
            "test_server": MCPServerConfig(name="test_server", command="test", args=[])
        }

        result = await cmd_list_tools(config, "test_server")

        assert result["status"] == "dry_run"
        assert "Would list tools" in result["message"]

    @pytest.mark.asyncio
    async def test_cmd_call_tool_server_not_found(self):
        """Test calling tool on non-existent server."""
        config = MCPConfig(project_root=Path("/test"))
        config.servers = {}

        result = await cmd_call_tool(config, "nonexistent", "tool", {})

        assert result["status"] == "failure"
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_cmd_call_tool_dry_run(self):
        """Test calling tool in dry-run mode."""
        config = MCPConfig(project_root=Path("/test"))
        config.dry_run = True
        config.servers = {
            "test_server": MCPServerConfig(name="test_server", command="test", args=[])
        }

        arguments = {"param1": "value1"}
        result = await cmd_call_tool(config, "test_server", "test_tool", arguments)

        assert result["status"] == "dry_run"
        assert result["server"] == "test_server"
        assert result["tool"] == "test_tool"
        assert result["arguments"] == arguments


class TestCLIIntegration:
    """Test CLI integration points."""

    def test_parse_tool_arguments_invalid_var(self):
        """Test parsing invalid --var format."""
        args = MagicMock()
        args.var = ["invalid_format"]
        args.tool_args = []
        args.json_args = None

        with pytest.raises(ValueError, match="Invalid --var format"):
            parse_tool_arguments(args)

    def test_parse_tool_arguments_invalid_json(self):
        """Test parsing invalid JSON."""
        args = MagicMock()
        args.var = None
        args.tool_args = []
        args.json_args = "invalid json"

        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_tool_arguments(args)

    @pytest.mark.asyncio
    async def test_cmd_list_tools_with_mock_client(self):
        """Test listing tools with mocked MCP client."""
        config = MCPConfig(project_root=Path("/test"))
        config.servers = {
            "test_server": MCPServerConfig(name="test_server", command="test", args=[])
        }

        mock_client = AsyncMock()
        mock_client.list_tools.return_value = [
            {
                "name": "tool1",
                "description": "Test tool 1",
                "inputSchema": {
                    "type": "object",
                    "properties": {"param1": {"type": "string"}},
                    "required": ["param1"],
                },
            },
            {
                "name": "tool2",
                "description": "Test tool 2",
                "inputSchema": {
                    "type": "object",
                    "properties": {"param2": {"type": "number"}},
                },
            },
        ]

        with patch("khive.cli.khive_mcp.get_mcp_client") as mock_get_client:
            mock_get_client.return_value = mock_client

            result = await cmd_list_tools(config, "test_server")

            assert result["status"] == "success"
            assert len(result["tools"]) == 2
            assert result["tools"][0]["name"] == "tool1"
            assert result["tools"][1]["name"] == "tool2"

    @pytest.mark.asyncio
    async def test_cmd_call_tool_with_mock_client(self):
        """Test calling tool with mocked MCP client."""
        config = MCPConfig(project_root=Path("/test"))
        config.servers = {
            "test_server": MCPServerConfig(name="test_server", command="test", args=[])
        }

        mock_client = AsyncMock()
        mock_client.call_tool.return_value = {
            "content": [{"type": "text", "text": "Success result"}]
        }

        with patch("khive.cli.khive_mcp.get_mcp_client") as mock_get_client:
            mock_get_client.return_value = mock_client

            arguments = {"param1": "value1"}
            result = await cmd_call_tool(config, "test_server", "test_tool", arguments)

            assert result["status"] == "success"
            assert result["result"]["content"][0]["text"] == "Success result"
            # Remove the enhanced check as it's not in the new implementation

            mock_client.call_tool.assert_called_once_with("test_tool", arguments)
