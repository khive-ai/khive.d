# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_mcp.py - MCP (Model Context Protocol) server management using FastMCP.

Features
========
* MCP server configuration management via .khive/mcps/config.json
* Server lifecycle management using FastMCP client
* Tool discovery and execution
* Support for stdio and HTTP transports

CLI
---
    khive mcp list                           # List configured servers
    khive mcp status [server]                # Show server status
    khive mcp tools <server>                 # List available tools
    khive mcp call <server> <tool> [args]    # Call a tool

Exit codes: 0 success · 1 failure.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport, SSETransport

from khive.utils import BaseConfig, die, error_msg, info_msg, log_msg, warn_msg

from .base import BaseCLICommand, CLIResult, cli_command


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
    # New field for transport type
    transport: str = "stdio"  # stdio or sse
    url: str | None = None  # For SSE transport


@dataclass
class MCPConfig(BaseConfig):
    """Configuration for MCP command."""

    servers: dict[str, MCPServerConfig] = field(default_factory=dict)

    @property
    def mcps_config_file(self) -> Path:
        return self.khive_config_dir / "mcps" / "config.json"


@cli_command("mcp")
class MCPCommand(BaseCLICommand):
    """Manage MCP servers using FastMCP."""

    def __init__(self):
        super().__init__(
            command_name="mcp",
            description="MCP (Model Context Protocol) server management",
        )
        self._check_fastmcp()
        # Store active clients
        self._clients: dict[str, Client] = {}

    def _check_fastmcp(self):
        """Check if FastMCP is installed."""
        if Client is None:
            die(
                "FastMCP is not installed. Install it with: pip install fastmcp",
                {"suggestion": "Run: pip install fastmcp"},
            )

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add MCP-specific arguments."""
        subparsers = parser.add_subparsers(dest="subcommand", help="MCP commands")

        # List command
        subparsers.add_parser("list", help="List configured MCP servers")

        # Status command
        status_parser = subparsers.add_parser("status", help="Show server status")
        status_parser.add_argument("server", nargs="?", help="Specific server name")

        # Tools command
        tools_parser = subparsers.add_parser("tools", help="List available tools")
        tools_parser.add_argument("server", help="Server name")

        # Call command
        call_parser = subparsers.add_parser("call", help="Call a tool")
        call_parser.add_argument("server", help="Server name")
        call_parser.add_argument("tool", help="Tool name")
        call_parser.add_argument(
            "--var",
            action="append",
            help="Tool argument as key=value (can be repeated)",
        )
        call_parser.add_argument(
            "--json", dest="json_args", help="Tool arguments as JSON string"
        )

    def _create_config(self, args: argparse.Namespace) -> MCPConfig:
        """Create MCPConfig from arguments and configuration files."""
        config = MCPConfig(project_root=args.project_root)
        config.update_from_cli_args(args)

        # Load MCP server configurations
        if config.mcps_config_file.exists():
            log_msg(f"Loading MCP config from {config.mcps_config_file}")
            try:
                config_data = json.loads(config.mcps_config_file.read_text())
                mcp_servers = config_data.get("mcpServers", {})

                for server_name, server_config in mcp_servers.items():
                    # Determine transport type
                    transport = "stdio"
                    url = None

                    if "url" in server_config:
                        transport = "sse"
                        url = server_config["url"]

                    config.servers[server_name] = MCPServerConfig(
                        name=server_name,
                        command=server_config.get("command", ""),
                        args=server_config.get("args", []),
                        env=server_config.get("env", {}),
                        always_allow=server_config.get("alwaysAllow", []),
                        disabled=server_config.get("disabled", False),
                        timeout=server_config.get("timeout", 30),
                        transport=transport,
                        url=url,
                    )
            except (json.JSONDecodeError, KeyError) as e:
                warn_msg(f"Could not parse MCP config: {e}")

        return config

    def _execute(self, args: argparse.Namespace, config: MCPConfig) -> CLIResult:
        """Execute the MCP command."""
        if not args.subcommand:
            return CLIResult(
                status="failure",
                message="No subcommand specified. Use --help for usage.",
                exit_code=1,
            )

        # Run async command
        try:
            result = asyncio.run(self._execute_async(args, config))
            return result
        except Exception as e:
            return CLIResult(
                status="failure", message=f"Unexpected error: {e}", exit_code=1
            )
        finally:
            # Clean up any active clients
            asyncio.run(self._cleanup_clients())

    async def _execute_async(
        self, args: argparse.Namespace, config: MCPConfig
    ) -> CLIResult:
        """Execute async MCP operations."""
        if args.subcommand == "list":
            return await self._cmd_list_servers(config)

        elif args.subcommand == "status":
            server_name = getattr(args, "server", None)
            return await self._cmd_server_status(config, server_name)

        elif args.subcommand == "tools":
            return await self._cmd_list_tools(config, args.server)

        elif args.subcommand == "call":
            # Parse tool arguments
            try:
                arguments = self._parse_tool_arguments(args)
            except ValueError as e:
                return CLIResult(
                    status="failure",
                    message=f"Argument parsing error: {e}",
                    exit_code=1,
                )

            return await self._cmd_call_tool(config, args.server, args.tool, arguments)

        else:
            return CLIResult(
                status="failure",
                message=f"Unknown subcommand: {args.subcommand}",
                exit_code=1,
            )

    async def _get_client(self, server_config: MCPServerConfig) -> Client:
        """Get or create a FastMCP client for a server."""
        if server_config.name in self._clients:
            return self._clients[server_config.name]

        # Create appropriate transport
        if server_config.transport == "sse" and server_config.url:
            transport = SSETransport(server_config.url)
        else:
            # Default to stdio transport
            transport = PythonStdioTransport(
                script_path=server_config.command,
                args=server_config.args,
                env=server_config.env,
            )

        # Create client
        client = Client(transport)
        self._clients[server_config.name] = client

        return client

    async def _cleanup_clients(self):
        """Clean up all active clients."""
        for client in self._clients.values():
            try:
                if hasattr(client, "_context_manager") and client._context_manager:
                    await client.__aexit__(None, None, None)
            except Exception:
                pass
        self._clients.clear()

    async def _cmd_list_servers(self, config: MCPConfig) -> CLIResult:
        """List all configured MCP servers."""
        servers_info = []

        for server_name, server_config in config.servers.items():
            server_info = {
                "name": server_name,
                "command": server_config.command,
                "transport": server_config.transport,
                "disabled": server_config.disabled,
                "operations_count": len(server_config.always_allow),
            }

            if server_config.transport == "sse":
                server_info["url"] = server_config.url

            servers_info.append(server_info)

        return CLIResult(
            status="success",
            message=f"Found {len(servers_info)} configured MCP servers",
            data={"servers": servers_info, "total_count": len(servers_info)},
        )

    async def _cmd_server_status(
        self, config: MCPConfig, server_name: str | None = None
    ) -> CLIResult:
        """Get status of one or all MCP servers."""
        if server_name:
            if server_name not in config.servers:
                return CLIResult(
                    status="failure",
                    message=f"Server '{server_name}' not found",
                    data={"available_servers": list(config.servers.keys())},
                    exit_code=1,
                )

            server_config = config.servers[server_name]
            server_info = {
                "name": server_name,
                "command": server_config.command,
                "args": server_config.args,
                "transport": server_config.transport,
                "disabled": server_config.disabled,
                "timeout": server_config.timeout,
                "allowed_operations": server_config.always_allow,
            }

            # Try to connect and get server info
            if not server_config.disabled:
                try:
                    client = await self._get_client(server_config)
                    async with client:
                        # Get server capabilities
                        tools = await client.list_tools()
                        server_info["status"] = "connected"
                        server_info["tools_count"] = len(tools)
                        server_info["tools"] = [
                            {"name": tool.name, "description": tool.description}
                            for tool in tools
                        ]
                except Exception as e:
                    server_info["status"] = "error"
                    server_info["error"] = str(e)
            else:
                server_info["status"] = "disabled"

            return CLIResult(
                status="success",
                message=f"Status for server '{server_name}'",
                data={"server": server_info},
            )
        else:
            # Return status for all servers
            return await self._cmd_list_servers(config)

    async def _cmd_list_tools(self, config: MCPConfig, server_name: str) -> CLIResult:
        """List tools available on a specific server."""
        if server_name not in config.servers:
            return CLIResult(
                status="failure",
                message=f"Server '{server_name}' not found",
                data={"available_servers": list(config.servers.keys())},
                exit_code=1,
            )

        server_config = config.servers[server_name]

        if server_config.disabled:
            return CLIResult(
                status="failure",
                message=f"Server '{server_name}' is disabled",
                exit_code=1,
            )

        if config.dry_run:
            return CLIResult(
                status="success",
                message=f"Would list tools for server '{server_name}' (dry run)",
                data={"server": server_name},
            )

        try:
            client = await self._get_client(server_config)
            async with client:
                tools = await client.list_tools()

                tools_info = []
                for tool in tools:
                    tool_info = {"name": tool.name, "description": tool.description}

                    # Add parameter info if available
                    if hasattr(tool, "inputSchema") and tool.inputSchema:
                        if "properties" in tool.inputSchema:
                            tool_info["parameters"] = list(
                                tool.inputSchema["properties"].keys()
                            )

                    tools_info.append(tool_info)

                return CLIResult(
                    status="success",
                    message=f"Found {len(tools_info)} tools on server '{server_name}'",
                    data={"server": server_name, "tools": tools_info},
                )

        except Exception as e:
            return CLIResult(
                status="failure",
                message=f"Failed to list tools: {e}",
                data={"server": server_name},
                exit_code=1,
            )

    async def _cmd_call_tool(
        self,
        config: MCPConfig,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> CLIResult:
        """Call a tool on a specific server."""
        if server_name not in config.servers:
            return CLIResult(
                status="failure",
                message=f"Server '{server_name}' not found",
                data={"available_servers": list(config.servers.keys())},
                exit_code=1,
            )

        server_config = config.servers[server_name]

        if server_config.disabled:
            return CLIResult(
                status="failure",
                message=f"Server '{server_name}' is disabled",
                exit_code=1,
            )

        # Check if tool is allowed
        if server_config.always_allow and tool_name not in server_config.always_allow:
            return CLIResult(
                status="failure",
                message=f"Tool '{tool_name}' not in allowlist",
                data={
                    "allowed_tools": server_config.always_allow,
                    "server": server_name,
                    "tool": tool_name,
                },
                exit_code=1,
            )

        if config.dry_run:
            return CLIResult(
                status="success",
                message=f"Would call tool '{tool_name}' on server '{server_name}' (dry run)",
                data={"server": server_name, "tool": tool_name, "arguments": arguments},
            )

        try:
            client = await self._get_client(server_config)
            async with client:
                # Call the tool
                result = await client.call_tool(tool_name, arguments)

                # Format result based on content type
                formatted_result = self._format_tool_result(result)

                return CLIResult(
                    status="success",
                    message=f"Tool '{tool_name}' executed successfully",
                    data={
                        "server": server_name,
                        "tool": tool_name,
                        "arguments": arguments,
                        "result": formatted_result,
                    },
                )

        except Exception as e:
            return CLIResult(
                status="failure",
                message=f"Failed to call tool: {e}",
                data={"server": server_name, "tool": tool_name, "arguments": arguments},
                exit_code=1,
            )

    def _parse_tool_arguments(self, args: argparse.Namespace) -> dict[str, Any]:
        """Parse tool arguments from CLI flags."""
        arguments = {}

        # Parse --var key=value arguments
        if hasattr(args, "var") and args.var:
            for var_arg in args.var:
                if "=" not in var_arg:
                    raise ValueError(
                        f"Invalid --var format: '{var_arg}'. Expected: key=value"
                    )
                key, value = var_arg.split("=", 1)

                # Try to parse as JSON for complex types
                try:
                    parsed_value = json.loads(value)
                    arguments[key] = parsed_value
                except json.JSONDecodeError:
                    # Treat as string
                    arguments[key] = value

        # Parse JSON arguments if provided
        if hasattr(args, "json_args") and args.json_args:
            try:
                json_arguments = json.loads(args.json_args)
                arguments.update(json_arguments)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}")

        return arguments

    def _format_tool_result(self, result: Any) -> Any:
        """Format tool result for display."""
        # Handle different result types
        if isinstance(result, list):
            # Check for MCP content format
            formatted = []
            for item in result:
                if isinstance(item, dict) and item.get("type") == "text":
                    formatted.append(item.get("text", ""))
                else:
                    formatted.append(item)
            return formatted

        elif hasattr(result, "content"):
            # Handle result objects with content attribute
            return self._format_tool_result(result.content)

        else:
            # Return as-is
            return result

    def _handle_result(self, result: CLIResult, json_output: bool) -> None:
        """Override to provide custom formatting for MCP results."""
        if json_output:
            super()._handle_result(result, json_output)
            return

        # Custom human-readable output
        if result.status == "success":
            info_msg(result.message)

            # Special formatting for different commands
            if result.data:
                if "servers" in result.data:
                    # List command
                    print("\nConfigured MCP Servers:")
                    for server in result.data["servers"]:
                        status = "✓" if not server["disabled"] else "✗"
                        print(
                            f"  {status} {server['name']}: {server['command']} ({server['transport']})"
                        )
                        if server["transport"] == "sse" and "url" in server:
                            print(f"    URL: {server['url']}")
                        print(f"    Operations: {server['operations_count']}")

                elif "tools" in result.data:
                    # Tools command
                    print(f"\nAvailable Tools on {result.data['server']}:")
                    for tool in result.data["tools"]:
                        print(f"  • {tool['name']}")
                        if tool.get("description"):
                            print(f"    {tool['description']}")
                        if tool.get("parameters"):
                            print(f"    Parameters: {', '.join(tool['parameters'])}")

                elif "result" in result.data:
                    # Call command
                    print("\nTool Result:")
                    formatted_result = result.data["result"]
                    if isinstance(formatted_result, list):
                        for item in formatted_result:
                            print(item)
                    else:
                        print(json.dumps(formatted_result, indent=2))
        else:
            error_msg(result.message)


def main(argv: list[str] | None = None) -> None:
    """Entry point for khive CLI integration."""
    cmd = MCPCommand()
    cmd.run(argv)


if __name__ == "__main__":
    main()
