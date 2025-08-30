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
import os
import platform
import shutil
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastmcp.client import Client
from fastmcp.client.transports import (
    PythonStdioTransport,
    SSETransport,
    StdioTransport,
    StreamableHttpTransport,
)

from khive.utils import BaseConfig, die, error_msg, info_msg, log_msg, warn_msg

from .base import BaseCLICommand, CLIResult, cli_command

# Timeouts based on community recommendations
DEFAULT_TIMEOUT = 120.0  # Increased for memory server
INIT_TIMEOUT = 30.0  # Initial connection timeout - increased
CLEANUP_TIMEOUT = 2.0  # Faster cleanup


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    always_allow: list[str] = field(default_factory=list)
    disabled: bool = False
    timeout: int = DEFAULT_TIMEOUT
    transport: str = "stdio"
    url: str | None = None
    # New fields for better subprocess handling
    buffer_size: int = 65536  # 64KB buffer
    use_shell: bool = False  # Whether to use shell execution


@dataclass
class MCPConfig(BaseConfig):
    """Configuration for MCP command."""

    servers: dict[str, MCPServerConfig] = field(default_factory=dict)

    @property
    def mcps_config_file(self) -> Path:
        return self.khive_config_dir / "mcps" / "config.json"


class StdioTransportFixed(StdioTransport):
    """Fixed StdioTransport that handles buffering properly."""

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        buffer_size: int = 65536,
    ):
        super().__init__(command, args or [], env or {})
        self.buffer_size = buffer_size
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()

    async def start(self):
        """Start the subprocess with proper buffering."""
        # Prepare environment
        env = os.environ.copy()
        env.update(self.env)

        # Add Python unbuffered mode for Python scripts
        env["PYTHONUNBUFFERED"] = "1"

        # Platform-specific handling
        if platform.system() == "Windows":
            # Windows needs CREATE_NO_WINDOW flag
            import subprocess

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self._process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                startupinfo=startupinfo,
                limit=self.buffer_size,  # Increase buffer limit
            )
        else:
            # Unix/Linux/Mac
            self._process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                limit=self.buffer_size,  # Increase buffer limit
            )

        # Start background tasks for reading with proper error handling
        self._read_task = asyncio.create_task(self._read_output())
        self._error_task = asyncio.create_task(self._read_errors())


@cli_command("mcp")
class MCPCommand(BaseCLICommand):
    """Manage MCP servers using FastMCP."""

    def __init__(self):
        super().__init__(
            command_name="mcp",
            description="MCP (Model Context Protocol) server management",
        )
        self._check_fastmcp()
        self._active_clients: dict[str, Client] = {}
        self._client_locks: dict[str, asyncio.Lock] = {}

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

        # Load environment variables from .env file
        env_vars = self._load_environment_variables(config.project_root)

        # Load MCP server configurations
        if config.mcps_config_file.exists():
            log_msg(f"Loading MCP config from {config.mcps_config_file}")
            try:
                config_data = json.loads(config.mcps_config_file.read_text())
                mcp_servers = config_data.get("mcpServers", {})

                for server_name, server_config in mcp_servers.items():
                    # Intelligently detect transport type
                    transport, url = self._detect_transport_type(server_config)

                    # Merge environment variables with priority: config env > .env file > system env
                    merged_env = self._merge_environment_variables(
                        server_config.get("env", {}), env_vars, server_name
                    )

                    config.servers[server_name] = MCPServerConfig(
                        name=server_name,
                        command=server_config.get("command", ""),
                        args=server_config.get("args", []),
                        env=merged_env,
                        always_allow=server_config.get("alwaysAllow", []),
                        disabled=server_config.get("disabled", False),
                        timeout=server_config.get(
                            "timeout", self._get_default_timeout(server_config)
                        ),
                        transport=transport,
                        url=url,
                        buffer_size=server_config.get("bufferSize", 65536),
                        use_shell=server_config.get("useShell", False),
                    )
            except (json.JSONDecodeError, KeyError) as e:
                warn_msg(f"Could not parse MCP config: {e}")

        return config

    def _load_environment_variables(self, project_root: Path) -> dict[str, str]:
        """Load environment variables from .env file and system environment."""
        env_vars = {}

        # Load from .env file if it exists
        env_file = project_root / ".env"
        if env_file.exists():
            try:
                log_msg(f"Loading environment variables from {env_file}")
                with open(env_file) as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        # Skip empty lines and comments
                        if not line or line.startswith("#"):
                            continue

                        if "=" in line:
                            key, value = line.split("=", 1)
                            env_vars[key.strip()] = value.strip()
                        else:
                            warn_msg(f"Invalid .env line {line_num}: {line}")

                log_msg(f"Loaded {len(env_vars)} environment variables from .env file")
            except Exception as e:
                warn_msg(f"Error reading .env file: {e}")

        return env_vars

    def _merge_environment_variables(
        self, config_env: dict[str, str], dotenv_vars: dict[str, str], server_name: str
    ) -> dict[str, str]:
        """
        Merge environment variables with proper priority and mapping.

        Priority order:
        1. Config file env section (highest priority)
        2. .env file variables
        3. System environment variables (lowest priority)

        Also handles common environment variable name mappings.
        """
        merged_env = {}

        # Define common environment variable mappings for different servers
        env_mappings = {
            "github": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": [
                    "GITHUB_TOKEN",
                    "GITHUB_PERSONAL_ACCESS_TOKEN",
                ],
                "GITHUB_TOKEN": ["GITHUB_TOKEN", "GITHUB_PERSONAL_ACCESS_TOKEN"],
            },
            # Add more server-specific mappings as needed
        }

        # Start with system environment
        merged_env.update(os.environ)

        # Apply .env file variables (overrides system env)
        merged_env.update(dotenv_vars)

        # Apply config env variables (highest priority)
        merged_env.update(config_env)

        # Handle environment variable mappings for this server
        if server_name in env_mappings:
            server_mappings = env_mappings[server_name]

            for target_var, source_vars in server_mappings.items():
                # If target variable is not set, try to find it from source variables
                if target_var not in merged_env or not merged_env[target_var]:
                    for source_var in source_vars:
                        if merged_env.get(source_var):
                            merged_env[target_var] = merged_env[source_var]
                            log_msg(
                                f"Mapped {source_var} -> {target_var} for server '{server_name}'"
                            )
                            break

        return merged_env

    def _get_default_timeout(self, server_config: dict) -> float:
        """Get appropriate default timeout based on server configuration."""
        command = server_config.get("command", "")

        # Docker containers often need shorter timeouts for faster failure detection
        if command == "docker" or command.startswith("docker "):
            return 10.0  # Shorter timeout for Docker

        return DEFAULT_TIMEOUT

    def _detect_transport_type(self, server_config: dict) -> tuple[str, str | None]:
        """Intelligently detect the transport type based on server configuration."""
        # 1. Explicit transport specification takes precedence
        if "transport" in server_config:
            transport = server_config["transport"].lower()
            if transport in ["sse", "http", "https"]:
                url = server_config.get("url")
                if not url:
                    warn_msg(f"Transport '{transport}' specified but no URL provided")
                return transport, url
            if transport in ["stdio", "pipe"]:
                return "stdio", None
            warn_msg(f"Unknown transport type '{transport}', defaulting to stdio")

        # 2. URL presence indicates SSE/HTTP transport
        if server_config.get("url"):
            url = server_config["url"]
            if url.startswith(("http://", "https://")):
                return "sse", url
            if url.startswith(("ws://", "wss://")):
                return "websocket", url
            warn_msg(f"Unrecognized URL scheme in '{url}', treating as SSE")
            return "sse", url

        # 3. Command-based detection for stdio transport
        command = server_config.get("command", "")
        if not command:
            warn_msg("No command specified, defaulting to stdio transport")
            return "stdio", None

        # 4. Analyze command to determine best transport
        # Check if it's a Docker command - many Docker MCP servers use HTTP internally
        if command == "docker" or command.startswith("docker "):
            # Check if this looks like a typical MCP server Docker image
            args = server_config.get("args", [])
            if any("mcp" in str(arg).lower() for arg in args):
                # This looks like an MCP server in Docker
                # Many MCP servers in Docker expose HTTP endpoints
                # But without explicit URL, we'll try stdio first with shorter timeout
                log_msg(
                    "Detected Docker MCP server, using stdio transport with shorter timeout"
                )
                return "stdio", None
            log_msg("Detected Docker command, using stdio transport")
            return "stdio", None

        # Check if it's a Python script or module
        if (
            command in ["python", "python3", "py"]
            or command.startswith(("python ", "python3 ", "py "))
            or command.endswith(".py")
        ):
            log_msg("Detected Python command, using stdio transport")
            return "stdio", None

        # Check if it's a Node.js command
        if (
            command in ["node", "npm", "npx", "yarn"]
            or command.startswith(("node ", "npm ", "npx ", "yarn "))
            or command.endswith(".js")
        ):
            log_msg("Detected Node.js command, using stdio transport")
            return "stdio", None

        # Check if it's an executable file
        resolved_command = self._resolve_command_path(command)
        if Path(resolved_command).exists() and os.access(resolved_command, os.X_OK):
            log_msg("Detected executable file, using stdio transport")
            return "stdio", None

        # Check if it's a system command
        if shutil.which(command.split()[0] if " " in command else command):
            log_msg("Detected system command, using stdio transport")
            return "stdio", None

        # Default to stdio with warning
        warn_msg(
            f"Could not determine transport type for command '{command}', defaulting to stdio"
        )
        return "stdio", None

    async def _execute(self, args: argparse.Namespace, config: MCPConfig) -> CLIResult:
        """Execute the MCP command asynchronously."""
        if not args.subcommand:
            return CLIResult(
                status="failure",
                message="No subcommand specified. Use --help for usage.",
                exit_code=1,
            )

        # Try to use nest_asyncio if available (solves many event loop issues)
        try:
            import nest_asyncio

            nest_asyncio.apply()
            log_msg("Using nest_asyncio for event loop compatibility")
        except ImportError:
            log_msg("nest_asyncio not available, using standard asyncio")

        # Execute commands with proper async handling
        result = None
        try:
            if args.subcommand == "list":
                result = await self._cmd_list_servers(config)
            elif args.subcommand == "status":
                server_name = getattr(args, "server", None)
                result = await self._cmd_server_status(config, server_name)
            elif args.subcommand == "tools":
                result = await self._cmd_list_tools(config, args.server)
            elif args.subcommand == "call":
                arguments = self._parse_tool_arguments(args)
                result = await self._cmd_call_tool(
                    config, args.server, args.tool, arguments
                )
            else:
                result = CLIResult(
                    status="failure",
                    message=f"Unknown subcommand: {args.subcommand}",
                    exit_code=1,
                )

        except asyncio.TimeoutError as e:
            # Cleanup resources
            try:
                await self._safe_cleanup_all_clients()
            except Exception as cleanup_error:
                log_msg(f"Cleanup error (ignoring): {cleanup_error}")

            result = CLIResult(
                status="failure",
                message=f"Operation timed out: {e}",
                exit_code=1,
            )
        except ConnectionError as e:
            # Cleanup resources
            try:
                await self._safe_cleanup_all_clients()
            except Exception as cleanup_error:
                log_msg(f"Cleanup error (ignoring): {cleanup_error}")

            result = CLIResult(
                status="failure",
                message=f"Connection failed: {e}",
                exit_code=1,
            )
        except Exception as e:
            # Cleanup resources
            try:
                await self._safe_cleanup_all_clients()
            except Exception as cleanup_error:
                log_msg(f"Cleanup error (ignoring): {cleanup_error}")

            result = CLIResult(
                status="failure",
                message=f"Operation failed: {e}",
                exit_code=1,
            )

        # Normal cleanup
        try:
            await self._safe_cleanup_all_clients()
        except Exception as cleanup_error:
            log_msg(f"Cleanup error (ignoring): {cleanup_error}")

        # Force garbage collection to clean up any remaining async resources
        import gc

        gc.collect()

        return result

    def _resolve_command_path(self, command: str) -> str:
        """Resolve command to full path if it's a system command."""
        # Handle python module execution
        if command == "python" or command.startswith("python"):
            # Don't resolve python, let the system handle it
            return command

        if Path(command).is_absolute():
            return command

        if Path(command).exists():
            return str(Path(command).resolve())

        resolved_path = shutil.which(command)
        if resolved_path:
            return resolved_path

        return command

    def _create_transport(self, server_config: MCPServerConfig):
        """Create appropriate transport based on detected configuration."""
        transport_type = server_config.transport.lower()

        # Handle HTTP/SSE transports
        if transport_type in ["http", "https"]:
            if not server_config.url:
                raise ValueError(f"URL required for {transport_type} transport")
            log_msg(f"Creating SSE transport for {server_config.url}")
            return StreamableHttpTransport(server_config.url)

        if transport_type == "sse":
            if not server_config.url:
                raise ValueError("URL required for SSE transport")
            log_msg(f"Creating SSE transport for {server_config.url}")
            return SSETransport(server_config.url)

        # Handle WebSocket transport (if supported by FastMCP)
        if transport_type in ["websocket", "ws", "wss"]:
            if not server_config.url:
                raise ValueError(f"URL required for {transport_type} transport")
            # Note: WebSocket transport may not be available in all FastMCP versions
            try:
                from fastmcp.client.transports import WSTransport

                log_msg(f"Creating WebSocket transport for {server_config.url}")
                return WSTransport(server_config.url)
            except ImportError:
                warn_msg("WebSocket transport not available, falling back to SSE")
                return SSETransport(server_config.url)

        # Handle stdio/pipe transports (default)
        elif transport_type in ["stdio", "pipe"]:
            return self._create_stdio_transport(server_config)

        else:
            warn_msg(f"Unknown transport type '{transport_type}', using stdio")
            return self._create_stdio_transport(server_config)

    def _create_stdio_transport(self, server_config: MCPServerConfig):
        """Create the appropriate stdio transport based on command type."""
        # Resolve command
        resolved_command = self._resolve_command_path(server_config.command)

        # Prepare environment - merge system env with server config env
        env = os.environ.copy()
        env.update(server_config.env)

        # Force unbuffered output for Python scripts
        env["PYTHONUNBUFFERED"] = "1"

        # Log environment variables being passed (for debugging auth issues)
        log_msg(f"Creating StdioTransport for {resolved_command}")
        log_msg(f"Environment variables: {', '.join(sorted(env.keys()))}")
        if "GITHUB_PERSONAL_ACCESS_TOKEN" in env:
            # Log token presence without revealing the value
            token_preview = (
                env["GITHUB_PERSONAL_ACCESS_TOKEN"][:8] + "..."
                if env["GITHUB_PERSONAL_ACCESS_TOKEN"]
                else "None"
            )
            log_msg(f"GITHUB_PERSONAL_ACCESS_TOKEN: {token_preview}")

        # Detect if this is a Python script for PythonStdioTransport
        if (
            self._is_python_command(server_config.command, server_config.args)
            and PythonStdioTransport is not None
        ):
            # Extract Python script path from command/args
            script_path = self._extract_python_script_path(
                server_config.command, server_config.args
            )
            if script_path:
                log_msg(f"Creating PythonStdioTransport for {script_path}")
                return PythonStdioTransport(
                    script_path=script_path,
                    args=self._extract_python_script_args(server_config.args),
                    env=env,
                )

        # Use standard StdioTransport (not our custom one) to avoid interference
        log_msg("Using standard StdioTransport")
        return StdioTransport(
            command=resolved_command,
            args=server_config.args,
            env=env,
        )

    def _is_python_command(self, command: str, args: list[str]) -> bool:
        """Check if this is a Python command that should use PythonStdioTransport."""
        # Direct Python interpreter calls
        if command in ["python", "python3", "py"]:
            return True

        # Python with flags (e.g., "python -m module")
        if command.startswith(("python ", "python3 ", "py ")):
            return True

        # Direct .py file execution
        if command.endswith(".py"):
            return True

        # Check if first arg is a .py file when using python interpreter
        if command in ["python", "python3", "py"] and args and args[0].endswith(".py"):
            return True

        return False

    def _extract_python_script_path(self, command: str, args: list[str]) -> str | None:
        """Extract the Python script path from command and args."""
        # Direct .py file execution
        if command.endswith(".py"):
            return self._resolve_command_path(command)

        # Python interpreter with script as first argument
        if command in ["python", "python3", "py"] and args:
            first_arg = args[0]
            # Skip flags like -m, -c, etc.
            if not first_arg.startswith("-") and first_arg.endswith(".py"):
                return self._resolve_command_path(first_arg)

        return None

    def _extract_python_script_args(self, args: list[str]) -> list[str]:
        """Extract arguments for the Python script (excluding the script path itself)."""
        if not args:
            return []

        # If first arg is a .py file, return the rest
        if args[0].endswith(".py"):
            return args[1:]

        # Otherwise return all args (for cases like python -m module)
        return args

    @asynccontextmanager
    async def _get_client(self, server_config: MCPServerConfig):
        """Create a fresh client for each operation with proper async handling."""
        transport = self._create_transport(server_config)
        client = Client(transport)

        connected = False
        try:
            # Initialize with timeout - use wait_for instead of asyncio.timeout to avoid cancellation issues
            try:
                await asyncio.wait_for(client.__aenter__(), timeout=INIT_TIMEOUT)
                connected = True
            except asyncio.TimeoutError:
                raise asyncio.TimeoutError(
                    f"Failed to connect to {server_config.name} within {INIT_TIMEOUT}s"
                )

            # Yield for use
            yield client

        except asyncio.CancelledError:
            # Handle cancellation - don't try to cleanup, just let it go
            log_msg(f"Client connection to {server_config.name} was cancelled")
            raise
        except Exception as e:
            # Handle other exceptions - try cleanup but don't block
            if connected:
                try:
                    # Simple cleanup without nested timeouts to avoid cancellation issues
                    await client.__aexit__(type(e), e, e.__traceback__)
                except Exception as cleanup_e:
                    # Expected cleanup failure during exception handling
                    import logging

                    logging.getLogger(__name__).debug(
                        f"MCP client cleanup exception (expected during error): {cleanup_e}"
                    )
            raise
        else:
            # Normal cleanup only when no exception occurred
            if connected:
                try:
                    # Simple cleanup without nested timeouts
                    await client.__aexit__(None, None, None)
                except Exception as cleanup_e:
                    # Expected cleanup failure during normal operation
                    import logging

                    logging.getLogger(__name__).debug(
                        f"MCP client cleanup exception (expected): {cleanup_e}"
                    )

    async def _cleanup_all_clients(self):
        """No-op cleanup since we don't store clients anymore."""
        # Clear any remaining references
        self._active_clients.clear()
        self._client_locks.clear()

    async def _safe_cleanup_all_clients(self):
        """No-op cleanup since we don't store clients anymore."""
        # Clear any remaining references
        self._active_clients.clear()
        self._client_locks.clear()

        # Force garbage collection to clean up any remaining resources
        import gc

        gc.collect()

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
                    async with self._get_client(server_config) as client:
                        tools = await asyncio.wait_for(
                            client.list_tools(), timeout=120.0
                        )
                        server_info["status"] = "connected"
                        server_info["tools_count"] = len(tools)
                        server_info["tools"] = [
                            {"name": tool.name, "description": tool.description}
                            for tool in tools
                        ]
                except asyncio.TimeoutError:
                    server_info["status"] = "timeout"
                    server_info["error"] = "Connection timeout (120s)"
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

        # Retry logic for flaky connections
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                async with self._get_client(server_config) as client:
                    # Test connection first
                    try:
                        # Some MCP servers need a moment to initialize
                        await asyncio.sleep(0.1)
                        tools = await asyncio.wait_for(
                            client.list_tools(), timeout=120.0
                        )
                    except Exception as tools_error:
                        log_msg(
                            f"Error listing tools on attempt {attempt + 1}: {tools_error}"
                        )
                        if attempt < max_retries - 1:
                            await asyncio.sleep(
                                0.5 * (attempt + 1)
                            )  # Exponential backoff
                            continue
                        raise

                    tools_info = []
                    for tool in tools:
                        try:
                            tool_info = {
                                "name": tool.name,
                                "description": tool.description,
                            }

                            # Add parameter info if available - handle different schema formats
                            if hasattr(tool, "inputSchema") and tool.inputSchema:
                                schema = tool.inputSchema
                                if isinstance(schema, dict) and "properties" in schema:
                                    tool_info["parameters"] = list(
                                        schema["properties"].keys()
                                    )
                                elif hasattr(schema, "properties"):
                                    tool_info["parameters"] = list(
                                        schema.properties.keys()
                                    )

                            # Add any available input schema info
                            if hasattr(tool, "inputSchema") and tool.inputSchema:
                                tool_info["has_schema"] = True

                            tools_info.append(tool_info)
                        except Exception as tool_error:
                            log_msg(
                                f"Error processing tool {getattr(tool, 'name', 'unknown')}: {tool_error}"
                            )
                            # Add minimal info for problematic tools
                            tools_info.append({
                                "name": getattr(tool, "name", "unknown"),
                                "description": f"Error: {tool_error}",
                                "error": True,
                            })

                    return CLIResult(
                        status="success",
                        message=f"Found {len(tools_info)} tools on server '{server_name}'",
                        data={"server": server_name, "tools": tools_info},
                    )

            except asyncio.TimeoutError as e:
                last_error = e
                log_msg(
                    f"Timeout on attempt {attempt + 1}/{max_retries} for server '{server_name}'"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))  # Progressive delay
                    continue
                break
            except asyncio.CancelledError:
                raise  # Don't retry cancellation
            except Exception as e:
                last_error = e
                log_msg(
                    f"Error on attempt {attempt + 1}/{max_retries} for server '{server_name}': {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                break

        # All retries failed
        if isinstance(last_error, asyncio.TimeoutError):
            return CLIResult(
                status="failure",
                message=f"Timeout connecting to server '{server_name}' after {max_retries} attempts (max {server_config.timeout}s each)",
                data={
                    "server": server_name,
                    "timeout": server_config.timeout,
                    "attempts": max_retries,
                },
                exit_code=1,
            )
        return CLIResult(
            status="failure",
            message=f"Failed to list tools after {max_retries} attempts: {last_error}",
            data={"server": server_name, "attempts": max_retries},
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

        # Enhanced timeout for tool calls (they may take longer than connection)
        call_timeout = max(
            server_config.timeout, 120.0
        )  # At least 120s for tool execution

        try:
            async with self._get_client(server_config) as client:
                # Validate tool exists first
                try:
                    tools = await asyncio.wait_for(
                        client.list_tools(), timeout=server_config.timeout
                    )
                    available_tools = [t.name for t in tools]
                    if tool_name not in available_tools:
                        return CLIResult(
                            status="failure",
                            message=f"Tool '{tool_name}' not found on server '{server_name}'",
                            data={
                                "server": server_name,
                                "tool": tool_name,
                                "available_tools": available_tools,
                            },
                            exit_code=1,
                        )
                except Exception as list_error:
                    log_msg(f"Warning: Could not verify tool existence: {list_error}")
                    # Continue anyway - some servers may not support tool listing during execution

                # Call the tool with proper error handling
                try:
                    log_msg(
                        f"Calling tool '{tool_name}' on server '{server_name}' with args: {arguments}"
                    )
                    result = await asyncio.wait_for(
                        client.call_tool(tool_name, arguments), timeout=call_timeout
                    )
                    log_msg("Tool call completed successfully")

                    # Extract the actual content like Claude Code does
                    if hasattr(result, "content") and result.content:
                        # If result has content attribute, use that
                        if isinstance(result.content, list):
                            formatted_result = []
                            for item in result.content:
                                if (
                                    hasattr(item, "text")
                                    and hasattr(item, "type")
                                    and item.type == "text"
                                ):
                                    try:
                                        import json

                                        parsed = json.loads(item.text)
                                        formatted_result.append(parsed)
                                    except:
                                        formatted_result.append(item.text)
                                else:
                                    formatted_result.append(item)
                        else:
                            formatted_result = result.content
                    elif (
                        hasattr(result, "text")
                        and hasattr(result, "type")
                        and result.type == "text"
                    ):
                        # Single text result
                        try:
                            import json

                            formatted_result = json.loads(result.text)
                        except:
                            formatted_result = result.text
                    else:
                        # Fallback to old formatting
                        formatted_result = self._format_tool_result(result)

                    return CLIResult(
                        status="success",
                        message=f"Tool '{tool_name}' executed successfully",
                        data={
                            "server": server_name,
                            "tool": tool_name,
                            "arguments": arguments,
                            "result": formatted_result,
                            "execution_time": f"< {call_timeout}s",
                        },
                    )
                except Exception as call_error:
                    log_msg(f"Tool call failed: {call_error}")
                    # Provide more specific error information
                    error_info = {
                        "server": server_name,
                        "tool": tool_name,
                        "arguments": arguments,
                        "error_type": type(call_error).__name__,
                        "error_details": str(call_error),
                    }

                    return CLIResult(
                        status="failure",
                        message=f"Tool execution failed: {call_error}",
                        data=error_info,
                        exit_code=1,
                    )

        except asyncio.TimeoutError:
            return CLIResult(
                status="failure",
                message=f"Timeout calling tool '{tool_name}' after {call_timeout}s",
                data={
                    "server": server_name,
                    "tool": tool_name,
                    "arguments": arguments,
                    "timeout": call_timeout,
                    "suggestion": "Tool may require more time - consider increasing timeout",
                },
                exit_code=1,
            )
        except asyncio.CancelledError:
            return CLIResult(
                status="failure",
                message=f"Tool call '{tool_name}' was cancelled",
                data={"server": server_name, "tool": tool_name, "arguments": arguments},
                exit_code=1,
            )
        except Exception as e:
            return CLIResult(
                status="failure",
                message=f"Failed to call tool: {e}",
                data={
                    "server": server_name,
                    "tool": tool_name,
                    "arguments": arguments,
                    "error_type": type(e).__name__,
                },
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
        """Format tool result for display to match Claude Code MCP behavior."""
        import json

        # Handle MCP result objects with text content (like Claude Code does)
        try:
            # Try to access .text attribute directly (for MCP response objects)
            if hasattr(result, "text") and hasattr(result, "type"):
                if result.type == "text":
                    try:
                        # Parse JSON from the text content
                        parsed_json = json.loads(result.text)
                        return parsed_json
                    except json.JSONDecodeError:
                        # Return as plain text if not valid JSON
                        return result.text
        except (AttributeError, TypeError):
            pass

        # Handle lists of MCP content format
        if isinstance(result, list):
            formatted = []
            for item in result:
                if isinstance(item, dict) and item.get("type") == "text":
                    try:
                        # Try to parse JSON from text content
                        parsed_json = json.loads(item.get("text", ""))
                        formatted.append(parsed_json)
                    except json.JSONDecodeError:
                        formatted.append(item.get("text", ""))
                else:
                    formatted.append(item)
            return formatted

        # Handle result objects with content attribute
        if hasattr(result, "content"):
            return self._format_tool_result(result.content)

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
