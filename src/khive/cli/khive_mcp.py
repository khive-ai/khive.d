# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_mcp.py - MCP (Model Context Protocol) server management and interaction.

Features
========
* MCP server configuration management via .khive/mcps/config.json
* Uses FastMCP v2 library for high-level MCP abstractions
* Seamless integration with Pydapter for data transformation
* Tool discovery and execution with smart argument parsing
* Persistent server connections with automatic reconnection
* Rich terminal output with color support

CLI Examples
============
    # List all configured MCP servers
    khive mcp list

    # Check status of a specific server
    khive mcp status filesystem

    # List available tools on a server
    khive mcp tools filesystem

    # Call a tool with arguments
    khive mcp call filesystem read_file --path /etc/hosts
    khive mcp call github create_issue --title "Bug report" --body "Details..."

    # Use JSON for complex arguments
    khive mcp call api request --json '{"method": "POST", "data": {...}}'

Exit codes: 0 success · 1 failure · 2 timeout/forbidden.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Import pydapter integration
from khive.adapters import MCPServerAdapter, MCPToolRequest, create_mcp_server_adapter

# Import from our FastMCP v2 implementation
from khive.adapters.fastmcp_client import MCPClient, MCPConfig, load_mcp_config

# --- Project Root and Config Path ---
try:
    PROJECT_ROOT = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.PIPE
        ).strip()
    )
except (subprocess.CalledProcessError, FileNotFoundError):
    PROJECT_ROOT = Path.cwd()

KHIVE_CONFIG_DIR = PROJECT_ROOT / ".khive"

# --- ANSI Colors and Logging ---
ANSI = {
    "G": "\033[32m" if sys.stdout.isatty() else "",  # Green
    "R": "\033[31m" if sys.stdout.isatty() else "",  # Red
    "Y": "\033[33m" if sys.stdout.isatty() else "",  # Yellow
    "B": "\033[34m" if sys.stdout.isatty() else "",  # Blue
    "C": "\033[36m" if sys.stdout.isatty() else "",  # Cyan
    "M": "\033[35m" if sys.stdout.isatty() else "",  # Magenta
    "N": "\033[0m" if sys.stdout.isatty() else "",  # Normal/Reset
    "DIM": "\033[2m" if sys.stdout.isatty() else "",  # Dim
}
verbose_mode = False


def log_msg_mcp(msg: str, *, kind: str = "B") -> None:
    if verbose_mode:
        print(f"{ANSI[kind]}▶{ANSI['N']} {msg}")


def format_message_mcp(prefix: str, msg: str, color_code: str) -> str:
    return f"{color_code}{prefix}{ANSI['N']} {msg}"


def info_msg_mcp(msg: str, *, console: bool = True) -> str:
    output = format_message_mcp("✔", msg, ANSI["G"])
    if console:
        print(output)
    return output


def warn_msg_mcp(msg: str, *, console: bool = True) -> str:
    output = format_message_mcp("⚠", msg, ANSI["Y"])
    if console:
        print(output, file=sys.stderr)
    return output


def error_msg_mcp(msg: str, *, console: bool = True) -> str:
    output = format_message_mcp("✖", msg, ANSI["R"])
    if console:
        print(output, file=sys.stderr)
    return output


def die_mcp(
    msg: str, json_data: dict[str, Any] | None = None, json_output_flag: bool = False
) -> None:
    error_msg_mcp(msg, console=not json_output_flag)
    if json_output_flag:
        base_data = {"status": "failure", "message": msg}
        if json_data:
            base_data.update(json_data)
        print(json.dumps(base_data, indent=2))
    sys.exit(1)


def print_example_configs():
    """Print example MCP server configurations."""
    print(
        f"\n{ANSI['B']}Example MCP Configuration{ANSI['N']} (.khive/mcps/config.json):"
    )
    example_config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", str(Path.home() / "Documents")],
                "alwaysAllow": ["read_file", "write_file", "list_directory"],
            },
            "github": {
                "command": "docker",
                "args": ["run", "-i", "--rm", "mcp/github-server"],
                "env": {"GITHUB_TOKEN": "$GITHUB_TOKEN"},
                "alwaysAllow": ["create_issue", "list_issues", "create_pr"],
            },
        }
    }
    print(f"{ANSI['DIM']}{json.dumps(example_config, indent=2)}{ANSI['N']}")


# --- Global MCP client registry ---
_mcp_clients: dict[str, MCPClient] = {}
_mcp_adapters: dict[str, MCPServerAdapter] = {}


async def get_mcp_client(server_config) -> MCPClient:
    """Get or create an MCP client for a server."""
    if server_config.name not in _mcp_clients:
        client = MCPClient(server_config)
        log_msg_mcp(f"Connecting to {server_config.name}...")
        if await client.connect():
            _mcp_clients[server_config.name] = client
            info_msg_mcp(f"Connected to {server_config.name}")
        else:
            raise Exception(f"Failed to connect to MCP server '{server_config.name}'")

    return _mcp_clients[server_config.name]


async def get_mcp_adapter(server_name: str) -> MCPServerAdapter:
    """Get or create a pydapter-based MCP server adapter."""
    if server_name not in _mcp_adapters:
        adapter = await create_mcp_server_adapter(server_name)
        _mcp_adapters[server_name] = adapter
    return _mcp_adapters[server_name]


async def disconnect_all_clients():
    """Disconnect all MCP clients and adapters."""
    for client in _mcp_clients.values():
        await client.disconnect()
    for adapter in _mcp_adapters.values():
        await adapter.aclose()
    _mcp_clients.clear()
    _mcp_adapters.clear()


# --- Command Implementations ---
async def cmd_list_servers(config: MCPConfig) -> dict[str, Any]:
    """List all configured MCP servers."""
    if not config.servers:
        if not config.json_output:
            warn_msg_mcp("No MCP servers configured")
            print_example_configs()
        return {
            "status": "success",
            "message": "No MCP servers configured",
            "servers": [],
            "total_count": 0,
        }

    servers_info = []

    for server_name, server_config in config.servers.items():
        server_info = {
            "name": server_name,
            "command": server_config.command,
            "disabled": server_config.disabled,
            "operations_count": len(server_config.always_allow),
            "status": "disconnected",
        }

        # Check if we have an active connection
        if server_name in _mcp_clients:
            client = _mcp_clients[server_name]
            if client.connected:
                server_info["status"] = "connected"
                server_info["tools_count"] = len(client.tools)

        servers_info.append(server_info)

    return {
        "status": "success",
        "message": f"Found {len(servers_info)} configured MCP servers",
        "servers": servers_info,
        "total_count": len(servers_info),
    }


async def cmd_server_status(
    config: MCPConfig, server_name: str | None = None
) -> dict[str, Any]:
    """Get status of one or all MCP servers."""
    if server_name:
        if server_name not in config.servers:
            available = list(config.servers.keys())
            if available:
                error_msg = f"Server '{server_name}' not found. Available servers: {', '.join(available)}"
            else:
                error_msg = f"Server '{server_name}' not found. No servers configured."
            return {
                "status": "failure",
                "message": error_msg,
                "available_servers": available,
            }

        server_config = config.servers[server_name]
        server_info = {
            "name": server_name,
            "command": server_config.command,
            "args": server_config.args,
            "disabled": server_config.disabled,
            "timeout": server_config.timeout,
            "allowed_operations": server_config.always_allow,
            "status": "disconnected",
        }

        # Try to connect if not already connected
        try:
            client = await get_mcp_client(server_config)
            server_info["status"] = "connected"
            server_info["server_info"] = client.server_info
            server_info["tools"] = client.tools
        except Exception as e:
            server_info["status"] = "error"
            server_info["error"] = str(e)

        return {
            "status": "success",
            "message": f"Status for server '{server_name}'",
            "server": server_info,
        }
    else:
        # Return status for all servers
        return await cmd_list_servers(config)


async def cmd_list_tools(config: MCPConfig, server_name: str) -> dict[str, Any]:
    """List tools available on a specific server."""
    if server_name not in config.servers:
        available = list(config.servers.keys())
        if available:
            error_msg = f"Server '{server_name}' not found. Available servers: {', '.join(available)}"
        else:
            error_msg = f"Server '{server_name}' not found. No servers configured."
        return {
            "status": "failure",
            "message": error_msg,
            "available_servers": available,
        }

    if config.dry_run:
        return {
            "status": "dry_run",
            "message": f"Would list tools for server '{server_name}'",
            "server": server_name,
        }

    try:
        server_config = config.servers[server_name]
        client = await get_mcp_client(server_config)
        tools = await client.list_tools()

        return {
            "status": "success",
            "message": f"Found {len(tools)} tools on server '{server_name}'",
            "server": server_name,
            "tools": tools,
        }
    except Exception as e:
        return {
            "status": "failure",
            "message": f"Failed to list tools: {e}",
            "server": server_name,
            "hint": "Make sure the server is running and accessible",
        }


def parse_tool_arguments(args: argparse.Namespace) -> dict[str, Any]:
    """Parse tool arguments from CLI flags into a dictionary."""
    arguments = {}

    # Parse --var key=value arguments
    if hasattr(args, "var") and args.var:
        for var_arg in args.var:
            if "=" not in var_arg:
                raise ValueError(
                    f"Invalid --var format: '{var_arg}'. Expected format: key=value"
                )
            key, value = var_arg.split("=", 1)

            # Try to parse as JSON value for complex types
            try:
                parsed_value = json.loads(value)
                arguments[key] = parsed_value
            except json.JSONDecodeError:
                # If not valid JSON, treat as string
                arguments[key] = value

    # Parse individual flag arguments (--key value)
    # We'll collect these from unknown args that follow the pattern
    if hasattr(args, "tool_args") and args.tool_args:
        i = 0
        while i < len(args.tool_args):
            arg = args.tool_args[i]
            if arg.startswith("--"):
                key = arg[2:]  # Remove '--' prefix
                if i + 1 < len(args.tool_args) and not args.tool_args[i + 1].startswith(
                    "--"
                ):
                    value = args.tool_args[i + 1]
                    # Try to parse as JSON for complex types
                    try:
                        parsed_value = json.loads(value)
                        arguments[key] = parsed_value
                    except json.JSONDecodeError:
                        arguments[key] = value
                    i += 2
                else:
                    # Boolean flag (no value)
                    arguments[key] = True
                    i += 1
            else:
                i += 1

    # Fallback to JSON if provided
    if hasattr(args, "json_args") and args.json_args:
        try:
            json_arguments = json.loads(args.json_args)
            arguments.update(json_arguments)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in --json argument: {args.json_args}")

    return arguments


async def cmd_call_tool(
    config: MCPConfig,
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any],
    use_adapter: bool = False,
) -> dict[str, Any]:
    """Call a tool on a specific server."""
    if server_name not in config.servers:
        available = list(config.servers.keys())
        if available:
            error_msg = f"Server '{server_name}' not found. Available servers: {', '.join(available)}"
        else:
            error_msg = f"Server '{server_name}' not found. No servers configured."
        return {
            "status": "failure",
            "message": error_msg,
            "available_servers": available,
        }

    if config.dry_run:
        return {
            "status": "dry_run",
            "message": f"Would call tool '{tool_name}' on server '{server_name}'",
            "server": server_name,
            "tool": tool_name,
            "arguments": arguments,
        }

    try:
        if use_adapter:
            # Use pydapter-based MCP server adapter for enhanced features
            adapter = await get_mcp_adapter(server_name)
            request = MCPToolRequest(
                server_name=server_name, tool_name=tool_name, arguments=arguments
            )
            response = await adapter.from_obj(request)

            if response.success:
                return {
                    "status": "success",
                    "message": f"Tool '{tool_name}' executed successfully",
                    "server": server_name,
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": response.result,
                    "execution_time_ms": response.execution_time_ms,
                }
            else:
                return {
                    "status": "failure",
                    "message": f"Tool execution failed: {response.error}",
                    "server": server_name,
                    "tool": tool_name,
                    "arguments": arguments,
                    "error": response.error,
                }
        else:
            # Use direct MCP client
            server_config = config.servers[server_name]
            client = await get_mcp_client(server_config)
            result = await client.call_tool(tool_name, arguments)

            return {
                "status": "success",
                "message": f"Tool '{tool_name}' executed successfully",
                "server": server_name,
                "tool": tool_name,
                "arguments": arguments,
                "result": result,
            }
    except Exception as e:
        error_details = str(e)
        hint = None

        # Provide helpful hints based on common errors
        if "not found" in error_details.lower():
            hint = f"Use 'khive mcp tools {server_name}' to see available tools"
        elif "not in allowlist" in error_details.lower():
            hint = "Update 'alwaysAllow' in .khive/mcps/config.json to allow this tool"
        elif "connection" in error_details.lower():
            hint = "Check if the MCP server is running and accessible"

        return {
            "status": "failure",
            "message": f"Failed to call tool: {error_details}",
            "server": server_name,
            "tool": tool_name,
            "arguments": arguments,
            "error": error_details,
            "hint": hint,
        }


async def main_mcp_flow(args: argparse.Namespace, config: MCPConfig) -> dict[str, Any]:
    """Main MCP command flow."""
    try:
        # Dispatch to specific command handlers
        if args.command == "list":
            return await cmd_list_servers(config)

        elif args.command == "status":
            server_name = getattr(args, "server", None)
            return await cmd_server_status(config, server_name)

        elif args.command == "tools":
            server_name = args.server
            return await cmd_list_tools(config, server_name)

        elif args.command == "call":
            server_name = args.server
            tool_name = args.tool

            # Parse tool arguments from various CLI formats
            try:
                arguments = parse_tool_arguments(args)
            except ValueError as e:
                return {
                    "status": "failure",
                    "message": f"Argument parsing error: {e}",
                    "hint": "Use --var key=value or --json '{...}' for complex arguments",
                }

            # Use adapter if requested
            use_adapter = getattr(args, "use_adapter", False)
            return await cmd_call_tool(
                config, server_name, tool_name, arguments, use_adapter
            )

        else:
            return {
                "status": "failure",
                "message": f"Unknown command: {args.command}",
                "available_commands": ["list", "status", "tools", "call"],
            }

    finally:
        # Clean up connections on exit
        if not config.dry_run:
            await disconnect_all_clients()


# --- CLI Entry Point ---
def cli_entry_mcp() -> None:
    parser = argparse.ArgumentParser(
        description="khive MCP server management - interact with AI tools via Model Context Protocol.",
        epilog="""
Examples:
  khive mcp list                                    # List all configured servers
  khive mcp status filesystem                       # Check status of 'filesystem' server
  khive mcp tools github                            # List tools available on 'github' server
  khive mcp call filesystem read_file --path /tmp/test.txt
  khive mcp call github create_issue --title "Bug" --body "Description"

For more information, see: https://modelcontextprotocol.io
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global arguments
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root directory (default: git root or current directory)",
    )
    parser.add_argument(
        "--json-output", action="store_true", help="Output results in JSON format"
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be done without executing",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    # Subcommands
    subparsers = parser.add_subparsers(
        dest="command", help="MCP commands", required=True
    )

    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List configured MCP servers",
        description="Display all MCP servers configured in .khive/mcps/config.json",
    )

    # Status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show server status and connection info",
        description="Check the status of MCP servers and their available tools",
    )
    status_parser.add_argument(
        "server", nargs="?", help="Specific server name (shows all if omitted)"
    )

    # Tools command
    tools_parser = subparsers.add_parser(
        "tools",
        help="List available tools on a server",
        description="Discover what tools (functions) are available on an MCP server",
    )
    tools_parser.add_argument("server", help="Server name to query")

    # Call command - Enhanced with natural argument parsing
    call_parser = subparsers.add_parser(
        "call",
        help="Call a tool on an MCP server",
        description="Execute a tool (function) on an MCP server with arguments",
        epilog="""
Argument formats:
  --key value              : Simple key-value pairs
  --flag                   : Boolean flags (no value = true)
  --var key=value          : Alternative key=value syntax
  --json '{"key": "val"}'  : JSON for complex arguments

Examples:
  khive mcp call fs read_file --path /etc/hosts
  khive mcp call api request --method POST --var data='{"name": "test"}'
  khive mcp call github create_issue --json '{"title": "Bug", "labels": ["bug", "urgent"]}'
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    call_parser.add_argument("server", help="Server name")
    call_parser.add_argument("tool", help="Tool name to call")

    # Support for --var key=value arguments
    call_parser.add_argument(
        "--var",
        action="append",
        help="Tool argument as key=value pair (can be repeated)",
        metavar="KEY=VALUE",
    )

    # Support for JSON fallback
    call_parser.add_argument(
        "--json",
        dest="json_args",
        help="Tool arguments as JSON string (for complex arguments)",
        metavar="JSON",
    )

    # Use pydapter integration
    call_parser.add_argument(
        "--use-adapter",
        action="store_true",
        help="Use pydapter-based adapter for enhanced features (audit logging, etc.)",
    )

    # Parse known args to allow unknown flags for tool arguments
    args, unknown = parser.parse_known_args()

    # If we're in call command, process unknown args as tool arguments
    if args.command == "call":
        args.tool_args = unknown

    global verbose_mode
    verbose_mode = args.verbose

    if not args.project_root.is_dir():
        die_mcp(
            f"Project root not a directory: {args.project_root}",
            json_output_flag=args.json_output,
        )

    config = load_mcp_config(args.project_root, args)

    # Show helpful message if no servers configured
    if not config.servers and args.command != "list":
        if not args.json_output:
            warn_msg_mcp("No MCP servers configured")
            print_example_configs()
            print(
                f"\n{ANSI['C']}Create the config file at:{ANSI['N']} {config.mcps_config_file}"
            )
        die_mcp("No MCP servers configured", json_output_flag=args.json_output)

    result = asyncio.run(main_mcp_flow(args, config))

    if config.json_output:
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output
        status_icon = {
            "success": f"{ANSI['G']}✓{ANSI['N']}",
            "failure": f"{ANSI['R']}✗{ANSI['N']}",
            "dry_run": f"{ANSI['Y']}◦{ANSI['N']}",
            "skipped": f"{ANSI['Y']}-{ANSI['N']}",
        }.get(result.get("status", "unknown"), "?")

        print(f"{status_icon} {result.get('message', 'Operation completed')}")

        # Show hint if available
        if "hint" in result:
            print(f"{ANSI['DIM']}💡 Hint: {result['hint']}{ANSI['N']}")

        # Show additional details for specific commands
        if args.command == "list" and "servers" in result:
            if result["servers"]:
                print(f"\n{ANSI['B']}Configured MCP Servers:{ANSI['N']}")
                for server in result["servers"]:
                    status_color = {
                        "connected": ANSI["G"],
                        "disconnected": ANSI["Y"],
                        "error": ANSI["R"],
                    }.get(server["status"], ANSI["R"])

                    disabled_indicator = (
                        f" {ANSI['DIM']}(disabled){ANSI['N']}"
                        if server["disabled"]
                        else ""
                    )
                    print(
                        f"  {ANSI['C']}•{ANSI['N']} {server['name']}: {status_color}{server['status']}{ANSI['N']}{disabled_indicator}"
                    )
                    print(f"    {ANSI['DIM']}Command: {server['command']}")
                    if server.get("operations_count", 0) > 0:
                        print(f"    Allowed operations: {server['operations_count']}")
                    if "tools_count" in server:
                        print(
                            f"    Available tools: {server['tools_count']}{ANSI['N']}"
                        )

        elif args.command == "tools" and "tools" in result:
            if result["tools"]:
                print(f"\n{ANSI['B']}Available Tools on {args.server}:{ANSI['N']}")
                for tool in result["tools"]:
                    print(
                        f"  {ANSI['C']}•{ANSI['N']} {ANSI['M']}{tool.get('name', 'unnamed')}{ANSI['N']}"
                    )
                    if "description" in tool:
                        print(f"    {tool['description']}")
                    if "inputSchema" in tool and "properties" in tool["inputSchema"]:
                        params = list(tool["inputSchema"]["properties"].keys())
                        required = tool["inputSchema"].get("required", [])
                        param_strs = []
                        for p in params:
                            if p in required:
                                param_strs.append(
                                    f"{ANSI['Y']}{p}{ANSI['N']} (required)"
                                )
                            else:
                                param_strs.append(f"{ANSI['DIM']}{p}{ANSI['N']}")
                        print(f"    Parameters: {', '.join(param_strs)}")
            else:
                print(f"\n{ANSI['DIM']}No tools available on this server{ANSI['N']}")

        elif args.command == "call" and "result" in result:
            print(f"\n{ANSI['B']}Tool Result:{ANSI['N']}")
            if isinstance(result["result"], dict) and "content" in result["result"]:
                for content in result["result"]["content"]:
                    if content.get("type") == "text":
                        print(content.get("text", ""))
            else:
                # Pretty print JSON result
                print(json.dumps(result["result"], indent=2))

            # Show execution time if available
            if "execution_time_ms" in result:
                print(
                    f"\n{ANSI['DIM']}Execution time: {result['execution_time_ms']:.2f}ms{ANSI['N']}"
                )

            # Show the parsed arguments if verbose
            if verbose_mode and "arguments" in result:
                print(f"\n{ANSI['DIM']}Parsed Arguments:")
                print(json.dumps(result["arguments"], indent=2))
                print(ANSI["N"])

    # Exit with appropriate code
    if result.get("status") == "failure":
        sys.exit(1)
    elif result.get("status") in ["timeout", "forbidden"]:
        sys.exit(2)


def main(argv: list[str] | None = None) -> None:
    """Entry point for khive CLI integration."""
    # Save original args
    original_argv = sys.argv

    # Set new args if provided
    if argv is not None:
        sys.argv = [sys.argv[0], *argv]

    try:
        cli_entry_mcp()
    except KeyboardInterrupt:
        error_msg_mcp("\nOperation cancelled by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        if verbose_mode:
            import traceback

            traceback.print_exc()
        error_msg_mcp(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Restore original args
        sys.argv = original_argv


if __name__ == "__main__":
    cli_entry_mcp()
