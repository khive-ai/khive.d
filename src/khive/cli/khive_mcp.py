# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_mcp.py - MCP (Model Context Protocol) server management and interaction.

Features
========
* MCP server configuration management via .khive/mcps/config.json
* Proper MCP initialization handshake and communication
* JSON-RPC 2.0 over stdin/stdout transport
* Server lifecycle management (start, stop, status)
* Tool discovery and execution
* Persistent server connections

# CLI
# ---
#     khive mcp list                           # List configured servers
#     khive mcp status [server]                # Show server status
#     khive mcp discover [--server] [--tool]   # Discover servers and tools with schemas
#     khive mcp tools <server>                 # List available tools
#     khive mcp call <server> <tool> [args]    # Call a tool (enhanced with schema validation)

Exit codes: 0 success · 1 failure · 2 warnings.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Import shared MCP client
from ..adapters.mcp_client import (
    MCPClient,
    MCPConfig,
    MCPServerConfig,
    load_mcp_config,
)

# Import pydapter adapters for enhanced functionality
PYDAPTER_AVAILABLE = False
try:
    from ..adapters import (
        MCPDiscoveryAdapter,
        MCPDiscoveryRequest,
        MCPServerAdapter,
        MCPServerAdapterConfig,
        MCPToolRequest,
        CapabilityContext,
    )
    PYDAPTER_AVAILABLE = True
except ImportError:
    pass  # Will be handled later when verbose_mode is available

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
    "G": "\033[32m" if sys.stdout.isatty() else "",
    "R": "\033[31m" if sys.stdout.isatty() else "",
    "Y": "\033[33m" if sys.stdout.isatty() else "",
    "B": "\033[34m" if sys.stdout.isatty() else "",
    "C": "\033[36m" if sys.stdout.isatty() else "",
    "M": "\033[35m" if sys.stdout.isatty() else "",
    "N": "\033[0m" if sys.stdout.isatty() else "",
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


# Configuration loading wrapper that adds CLI-specific functionality
def load_mcp_config_with_cli(
    project_r: Path, cli_args: argparse.Namespace | None = None
) -> MCPConfig:
    """Load MCP config and apply CLI arguments."""
    cfg = load_mcp_config(project_r, cli_args)
    
    # Apply CLI arguments for logging
    if cli_args:
        cfg.json_output = cli_args.json_output
        cfg.dry_run = cli_args.dry_run
        cfg.verbose = cli_args.verbose

        global verbose_mode
        verbose_mode = cli_args.verbose
        
        # Log config loading if verbose
        if cfg.verbose and cfg.mcps_config_file.exists():
            log_msg_mcp(f"Loading MCP config from {cfg.mcps_config_file}")

    return cfg


def save_mcp_state(config: MCPConfig, server_states: dict[str, dict[str, Any]]) -> None:
    """Save MCP server runtime state."""
    try:
        config.mcps_state_file.parent.mkdir(parents=True, exist_ok=True)
        config.mcps_state_file.write_text(json.dumps(server_states, indent=2))
    except OSError as e:
        warn_msg_mcp(f"Could not save MCP state: {e}")


def load_mcp_state(config: MCPConfig) -> dict[str, dict[str, Any]]:
    """Load MCP server runtime state."""
    if not config.mcps_state_file.exists():
        return {}

    try:
        return json.loads(config.mcps_state_file.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


# --- Global MCP client registry ---
_mcp_clients: dict[str, MCPClient] = {}


async def get_mcp_client(server_config: MCPServerConfig) -> MCPClient:
    """Get or create an MCP client for a server."""
    if server_config.name not in _mcp_clients:
        client = MCPClient(server_config)
        if await client.connect():
            _mcp_clients[server_config.name] = client
        else:
            raise Exception(f"Failed to connect to MCP server '{server_config.name}'")

    return _mcp_clients[server_config.name]


async def disconnect_all_clients():
    """Disconnect all MCP clients."""
    for client in _mcp_clients.values():
        await client.disconnect()
    _mcp_clients.clear()


# --- Command Implementations ---
async def cmd_list_servers(config: MCPConfig) -> dict[str, Any]:
    """List all configured MCP servers."""
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
            return {
                "status": "failure",
                "message": f"Server '{server_name}' not found in configuration",
                "available_servers": list(config.servers.keys()),
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

        # Check if we have an active connection
        if server_name in _mcp_clients:
            client = _mcp_clients[server_name]
            if client.connected:
                server_info["status"] = "connected"
                server_info["server_info"] = client.server_info
                server_info["tools"] = client.tools

        return {
            "status": "success",
            "message": f"Status for server '{server_name}'",
            "server": server_info,
        }
    # Return status for all servers
    return await cmd_list_servers(config)


async def cmd_list_tools(config: MCPConfig, server_name: str) -> dict[str, Any]:
    """List tools available on a specific server."""
    if server_name not in config.servers:
        return {
            "status": "failure",
            "message": f"Server '{server_name}' not found in configuration",
            "available_servers": list(config.servers.keys()),
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
        }


async def cmd_discover(
    config: MCPConfig,
    server_filter: Optional[str] = None,
    tool_filter: Optional[str] = None,
    include_disabled: bool = False
) -> dict[str, Any]:
    """
    Discover available MCP servers and tools with their schemas.
    
    This command uses the pydapter MCPDiscoveryAdapter if available,
    otherwise falls back to legacy discovery.
    """
    if config.dry_run:
        return {
            "status": "dry_run",
            "message": "Would discover MCP servers and tools",
            "filters": {
                "server_filter": server_filter,
                "tool_filter": tool_filter,
                "include_disabled": include_disabled
            }
        }

    try:
        if PYDAPTER_AVAILABLE:
            # Use enhanced pydapter discovery
            discovery_adapter = MCPDiscoveryAdapter(config)
            
            discovery_request = MCPDiscoveryRequest(
                server_filter=server_filter,
                tool_filter=tool_filter,
                include_disabled=include_disabled,
                include_schemas=True
            )
            
            discovery_response = await discovery_adapter.from_obj(discovery_request)
            
            return {
                "status": "success",
                "message": f"Discovered {discovery_response.total_servers} servers and {discovery_response.total_tools} tools",
                "discovery_time_ms": discovery_response.discovery_time_ms,
                "servers": [server.model_dump() for server in discovery_response.servers],
                "tools": [tool.model_dump() for tool in discovery_response.tools],
                "total_servers": discovery_response.total_servers,
                "total_tools": discovery_response.total_tools,
                "enhanced": True  # Flag to indicate enhanced discovery was used
            }
        else:
            # Fallback to legacy discovery
            return await _legacy_discover(config, server_filter, tool_filter, include_disabled)
            
    except Exception as e:
        return {
            "status": "failure",
            "message": f"Discovery failed: {e}",
            "error": str(e)
        }


async def _legacy_discover(
    config: MCPConfig,
    server_filter: Optional[str] = None,
    tool_filter: Optional[str] = None,
    include_disabled: bool = False
) -> dict[str, Any]:
    """Legacy discovery implementation without pydapter."""
    import fnmatch
    
    servers = []
    tools = []
    
    for server_name, server_config in config.servers.items():
        # Apply server filter
        if server_filter and not fnmatch.fnmatch(server_name, server_filter):
            continue
            
        # Skip disabled servers unless requested
        if server_config.disabled and not include_disabled:
            continue
        
        try:
            client = MCPClient(server_config)
            connected = await client.connect()
            
            server_info = {
                "name": server_name,
                "status": "connected" if connected else "disconnected",
                "command": server_config.command,
                "tool_count": len(client.tools) if connected else 0,
                "capabilities": client.server_info.get("capabilities", {}) if connected else {},
                "disabled": server_config.disabled
            }
            
            if connected:
                # Get tools from this server
                server_tools = await client.list_tools()
                
                for tool in server_tools:
                    tool_name = tool.get("name", "")
                    
                    # Apply tool filter
                    if tool_filter and not fnmatch.fnmatch(tool_name, tool_filter):
                        continue
                    
                    tool_info = {
                        "server_name": server_name,
                        "tool_name": tool_name,
                        "description": tool.get("description"),
                        "parameters": tool.get("inputSchema", {}),
                        "required_params": tool.get("inputSchema", {}).get("required", [])
                    }
                    
                    tools.append(tool_info)
                
                await client.disconnect()
            
            servers.append(server_info)
            
        except Exception as e:
            # Add server with error status
            server_info = {
                "name": server_name,
                "status": "error",
                "command": server_config.command,
                "tool_count": 0,
                "capabilities": {},
                "disabled": server_config.disabled,
                "error": str(e)
            }
            servers.append(server_info)
    
    return {
        "status": "success",
        "message": f"Discovered {len(servers)} servers and {len(tools)} tools",
        "servers": servers,
        "tools": tools,
        "total_servers": len(servers),
        "total_tools": len(tools),
        "enhanced": False  # Flag to indicate legacy discovery was used
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
    config: MCPConfig, server_name: str, tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Call a tool on a specific server with enhanced validation."""
    if server_name not in config.servers:
        return {
            "status": "failure",
            "message": f"Server '{server_name}' not found in configuration",
            "available_servers": list(config.servers.keys()),
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
        if PYDAPTER_AVAILABLE:
            # Use enhanced pydapter adapter
            adapter_config = MCPServerAdapterConfig(
                server_name=server_name,
                capability_context=None,  # TODO: Add capability context when security is implemented
                enable_audit_logging=config.verbose
            )
            
            adapter = MCPServerAdapter(adapter_config, config)
            
            tool_request = MCPToolRequest(
                server_name=server_name,
                tool_name=tool_name,
                arguments=arguments
            )
            
            tool_response = await adapter.from_obj(tool_request)
            
            return {
                "status": "success" if tool_response.success else "failure",
                "message": f"Tool '{tool_name}' executed successfully" if tool_response.success else f"Tool execution failed: {tool_response.error}",
                "server": server_name,
                "tool": tool_name,
                "arguments": arguments,
                "result": tool_response.result,
                "error": tool_response.error,
                "execution_time_ms": tool_response.execution_time_ms,
                "enhanced": True  # Flag to indicate enhanced execution was used
            }
        else:
            # Fallback to legacy implementation
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
                "enhanced": False
            }
            
    except Exception as e:
        return {
            "status": "failure",
            "message": f"Failed to call tool: {e}",
            "server": server_name,
            "tool": tool_name,
            "arguments": arguments,
            "error": str(e),
        }


def validate_tool_arguments_with_schema(
    arguments: dict[str, Any],
    tool_schema: dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """
    Validate tool arguments against JSON schema.
    
    Args:
        arguments: The arguments to validate
        tool_schema: JSON schema for the tool parameters
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Basic validation - check required parameters
        required_params = tool_schema.get("required", [])
        properties = tool_schema.get("properties", {})
        
        # Check for missing required parameters
        missing_params = [param for param in required_params if param not in arguments]
        if missing_params:
            return False, f"Missing required parameters: {', '.join(missing_params)}"
        
        # Check for unexpected parameters
        allowed_params = set(properties.keys())
        provided_params = set(arguments.keys())
        unexpected_params = provided_params - allowed_params
        
        if unexpected_params:
            return False, f"Unexpected parameters: {', '.join(unexpected_params)}"
        
        # TODO: Add more detailed type validation using jsonschema library
        # For now, just basic presence validation
        
        return True, None
        
    except Exception as e:
        return False, f"Schema validation error: {e}"


async def parse_tool_arguments_with_schema(
    args: argparse.Namespace,
    server_name: str,
    tool_name: str,
    config: MCPConfig
) -> tuple[dict[str, Any], Optional[str]]:
    """
    Enhanced argument parsing with schema validation.
    
    Args:
        args: Parsed CLI arguments
        server_name: Name of the MCP server
        tool_name: Name of the tool
        config: MCP configuration
        
    Returns:
        Tuple of (parsed_arguments, error_message)
    """
    try:
        # Parse arguments using existing logic
        arguments = parse_tool_arguments(args)
        
        # Try to get tool schema for validation
        if PYDAPTER_AVAILABLE:
            try:
                discovery_adapter = MCPDiscoveryAdapter(config)
                discovery_request = MCPDiscoveryRequest(
                    server_filter=server_name,
                    tool_filter=tool_name,
                    include_schemas=True
                )
                
                discovery_response = await discovery_adapter.from_obj(discovery_request)
                
                # Find the specific tool
                tool_info = None
                for tool in discovery_response.tools:
                    if tool.server_name == server_name and tool.tool_name == tool_name:
                        tool_info = tool
                        break
                
                if tool_info and tool_info.parameters:
                    # Validate arguments against schema
                    is_valid, error_msg = validate_tool_arguments_with_schema(
                        arguments, tool_info.parameters
                    )
                    
                    if not is_valid:
                        return {}, f"Argument validation failed: {error_msg}"
                
            except Exception as e:
                # If schema validation fails, log but continue
                if config.verbose:
                    log_msg_mcp(f"Schema validation skipped due to error: {e}", kind="Y")
        
        return arguments, None
        
    except Exception as e:
        return {}, str(e)


async def main_mcp_flow(args: argparse.Namespace, config: MCPConfig) -> dict[str, Any]:
    """Main MCP command flow."""
    try:
        # Dispatch to specific command handlers
        if args.command == "list":
            return await cmd_list_servers(config)

        if args.command == "status":
            server_name = getattr(args, "server", None)
            return await cmd_server_status(config, server_name)

        if args.command == "discover":
            server_filter = getattr(args, "server", None)
            tool_filter = getattr(args, "tool", None)
            include_disabled = getattr(args, "include_disabled", False)
            return await cmd_discover(config, server_filter, tool_filter, include_disabled)

        if args.command == "tools":
            server_name = args.server
            return await cmd_list_tools(config, server_name)

        if args.command == "call":
            server_name = args.server
            tool_name = args.tool

            # Enhanced argument parsing with schema validation
            try:
                if PYDAPTER_AVAILABLE:
                    arguments, error_msg = await parse_tool_arguments_with_schema(
                        args, server_name, tool_name, config
                    )
                    if error_msg:
                        return {
                            "status": "failure",
                            "message": f"Argument validation error: {error_msg}",
                        }
                else:
                    arguments = parse_tool_arguments(args)
            except ValueError as e:
                return {
                    "status": "failure",
                    "message": f"Argument parsing error: {e}",
                }

            return await cmd_call_tool(config, server_name, tool_name, arguments)

        return {
            "status": "failure",
            "message": f"Unknown command: {args.command}",
            "available_commands": ["list", "status", "discover", "tools", "call"],
        }

    finally:
        # Clean up connections on exit
        if not config.dry_run:
            await disconnect_all_clients()
            # Also clean up pydapter adapter clients if available
            if PYDAPTER_AVAILABLE:
                try:
                    from ..adapters import disconnect_all_adapter_clients
                    await disconnect_all_adapter_clients()
                except ImportError:
                    pass


# --- CLI Entry Point ---
def cli_entry_mcp() -> None:
    parser = argparse.ArgumentParser(description="khive MCP server management.")

    # Global arguments
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root directory.",
    )
    parser.add_argument(
        "--json-output", action="store_true", help="Output results in JSON format."
    )
    parser.add_argument(
        "--dry-run", "-n", action="store_true", help="Show what would be done."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging."
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="MCP commands")

    # List command
    subparsers.add_parser("list", help="List configured MCP servers")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show server status")
    status_parser.add_argument("server", nargs="?", help="Specific server name")

    # Discover command - NEW enhanced discovery
    discover_parser = subparsers.add_parser("discover", help="Discover servers and tools with schemas")
    discover_parser.add_argument("--server", help="Filter by server name pattern (e.g., 'filesystem*')")
    discover_parser.add_argument("--tool", help="Filter by tool name pattern (e.g., '*file*')")
    discover_parser.add_argument("--include-disabled", action="store_true", help="Include disabled servers")

    # Tools command
    tools_parser = subparsers.add_parser("tools", help="List available tools")
    tools_parser.add_argument("server", help="Server name")

    # Call command - Enhanced with natural argument parsing
    call_parser = subparsers.add_parser("call", help="Call a tool")
    call_parser.add_argument("server", help="Server name")
    call_parser.add_argument("tool", help="Tool name")

    # Support for --var key=value arguments
    call_parser.add_argument(
        "--var",
        action="append",
        help="Tool argument as key=value pair (can be repeated)",
    )

    # Support for JSON fallback
    call_parser.add_argument(
        "--json",
        dest="json_args",
        help="Tool arguments as JSON string (fallback for complex arguments)",
    )

    # Parse known args to allow unknown flags for tool arguments
    args, unknown = parser.parse_known_args()

    # If we're in call command, process unknown args as tool arguments
    if args.command == "call":
        args.tool_args = unknown

    if not args.command:
        parser.print_help()
        sys.exit(1)

    global verbose_mode
    verbose_mode = args.verbose

    if not args.project_root.is_dir():
        die_mcp(
            f"Project root not a directory: {args.project_root}",
            json_output_flag=args.json_output,
        )

    config = load_mcp_config_with_cli(args.project_root, args)

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

        # Show additional details for specific commands
        if args.command == "list" and "servers" in result:
            print("\nConfigured MCP Servers:")
            for server in result["servers"]:
                status_color = {
                    "connected": ANSI["G"],
                    "disconnected": ANSI["Y"],
                }.get(server["status"], ANSI["R"])

                disabled_indicator = " (disabled)" if server["disabled"] else ""
                print(
                    f"  • {server['name']}: {status_color}{server['status']}{ANSI['N']}{disabled_indicator}"
                )
                print(f"    Command: {server['command']}")
                print(f"    Operations: {server['operations_count']}")
                if "tools_count" in server:
                    print(f"    Tools: {server['tools_count']}")

        elif args.command == "discover" and "servers" in result:
            print(f"\nDiscovered Servers ({result.get('total_servers', 0)}):")
            for server in result["servers"]:
                status_color = {
                    "connected": ANSI["G"],
                    "disconnected": ANSI["Y"],
                    "error": ANSI["R"],
                }.get(server["status"], ANSI["R"])

                disabled_indicator = " (disabled)" if server.get("disabled", False) else ""
                enhanced_indicator = " [Enhanced]" if result.get("enhanced", False) else ""
                print(
                    f"  • {server['name']}: {status_color}{server['status']}{ANSI['N']}{disabled_indicator}{enhanced_indicator}"
                )
                print(f"    Command: {server['command']}")
                print(f"    Tools: {server.get('tool_count', 0)}")
                if server.get("capabilities"):
                    caps = list(server["capabilities"].keys())
                    print(f"    Capabilities: {', '.join(caps)}")

            if result.get("tools"):
                print(f"\nDiscovered Tools ({result.get('total_tools', 0)}):")
                for tool in result["tools"]:
                    print(f"  • {tool['server_name']}.{tool['tool_name']}")
                    if tool.get("description"):
                        print(f"    {tool['description']}")
                    if tool.get("required_params"):
                        print(f"    Required: {', '.join(tool['required_params'])}")
                    if tool.get("parameters", {}).get("properties"):
                        params = list(tool["parameters"]["properties"].keys())
                        optional_params = [p for p in params if p not in tool.get("required_params", [])]
                        if optional_params:
                            print(f"    Optional: {', '.join(optional_params)}")

            # Show discovery performance info
            if result.get("discovery_time_ms"):
                print(f"\nDiscovery completed in {result['discovery_time_ms']:.1f}ms")

        elif args.command == "tools" and "tools" in result:
            print(f"\nAvailable Tools on {args.server}:")
            for tool in result["tools"]:
                print(f"  • {tool.get('name', 'unnamed')}")
                if "description" in tool:
                    print(f"    {tool['description']}")
                if "inputSchema" in tool and "properties" in tool["inputSchema"]:
                    params = list(tool["inputSchema"]["properties"].keys())
                    print(f"    Parameters: {', '.join(params)}")

        elif args.command == "call" and "result" in result:
            print("\nTool Result:")
            if "content" in result["result"]:
                for content in result["result"]["content"]:
                    if content.get("type") == "text":
                        print(content.get("text", ""))
            else:
                print(json.dumps(result["result"], indent=2))

            # Show the parsed arguments if verbose
            if verbose_mode and "arguments" in result:
                print("\nParsed Arguments:")
                print(json.dumps(result["arguments"], indent=2))

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
    finally:
        # Restore original args
        sys.argv = original_argv


if __name__ == "__main__":
    cli_entry_mcp()
