from __future__ import annotations

import asyncio
import contextlib
import functools
import json
import logging
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar
from uuid import UUID

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Callable

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

# --- Type Variables ---
T = TypeVar("T")


Import = TypeVar("I")

HasLen = TypeVar("HasLen")
Bin = list[int]
T = TypeVar("T")

# --- Global State ---
verbose_mode = False


__all__ = (
    "as_async_fn",
    "convert_to_datetime",
    "get_bins",
    "get_logger",
    "import_module",
    "is_coroutine_function",
    "is_package_installed",
    "sha256_of_dict",
    "validate_model_to_dict",
    "validate_uuid",
)


def get_logger(name: str, prefix: str = "") -> logging.Logger:
    """Set up Claude Code hook event logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            f"{prefix} %(asctime)s - %(levelname)s - %(message)s".strip()
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def import_module(
    package_name: str,
    module_name: str | None = None,
    import_name: str | list | None = None,
) -> Import | list[Import]:
    """Import a module by its path."""
    try:
        full_import_path = (
            f"{package_name}.{module_name}" if module_name else package_name
        )

        if import_name:
            import_name = (
                [import_name] if not isinstance(import_name, list) else import_name
            )
            a = __import__(
                full_import_path,
                fromlist=import_name,
            )
            if len(import_name) == 1:
                return getattr(a, import_name[0])
            return [getattr(a, name) for name in import_name]
        return __import__(full_import_path)

    except ImportError as e:
        error_msg = f"Failed to import module {full_import_path}: {e}"
        raise ImportError(error_msg) from e


def is_package_installed(package_name: str):
    from importlib.util import find_spec

    return find_spec(package_name) is not None


def get_bins(input_: list[HasLen], /, upper: int) -> list[Bin]:
    """Organizes indices of items into bins based on a cumulative upper limit length.

    Args:
        input_ (list[str]): The list of strings to be binned.
        upper (int): The cumulative length upper limit for each bin.

    Returns:
        list[list[int]]: A list of bins, each bin is a list of indices from the input list.
    """
    current = 0
    bins = []
    current_bin = []
    for idx, item in enumerate(input_):
        if current + len(item) < upper:
            current_bin.append(idx)
            current += len(item)
        else:
            bins.append(current_bin)
            current_bin = [idx]
            current = len(item)
    if current_bin:
        bins.append(current_bin)
    return bins


def sha256_of_dict(obj: dict) -> str:
    """Deterministic SHA-256 of an arbitrary mapping."""
    import hashlib

    import orjson

    payload: bytes = orjson.dumps(
        obj,
        option=(
            orjson.OPT_SORT_KEYS  # canonical ordering
            | orjson.OPT_NON_STR_KEYS  # allow int / enum keys if you need them
        ),
    )
    return hashlib.sha256(memoryview(payload)).hexdigest()


def convert_to_datetime(v):
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        with contextlib.suppress(ValueError):
            return datetime.fromisoformat(v)

    error_msg = "Input value for field <created_at> should be a `datetime.datetime` object or `isoformat` string"
    raise ValueError(error_msg)


def validate_uuid(v: str | UUID) -> UUID:
    if isinstance(v, UUID):
        return v
    try:
        return UUID(str(v))
    except Exception as e:
        error_msg = "Input value for field <id> should be a `uuid.UUID` object or a valid `uuid` representation"
        raise ValueError(error_msg) from e


def validate_model_to_dict(v):
    """Serialize a Pydantic model to a dictionary. kwargs are passed to model_dump."""

    if isinstance(v, BaseModel):
        return v.model_dump()
    if v is None:
        return {}
    if isinstance(v, dict):
        return v

    error_msg = "Input value for field <model> should be a `pydantic.BaseModel` object or a `dict`"
    raise ValueError(error_msg)


@cache
def is_coroutine_function(fn, /) -> bool:
    """Check if a function is a coroutine function."""
    return asyncio.iscoroutinefunction(fn)


def force_async(fn: Callable[..., T], /) -> Callable[..., Callable[..., T]]:
    """force a function to be async."""
    pool = ThreadPoolExecutor()

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        future = pool.submit(fn, *args, **kwargs)
        return asyncio.wrap_future(future)  # Make it awaitable

    return wrapper


@cache
def as_async_fn(fn, /):
    """forcefully get the async call of a function"""
    if is_coroutine_function(fn):
        return fn
    return force_async(fn)


# --- ANSI Colors ---
ANSI = {
    "G": "\033[32m" if sys.stdout.isatty() else "",  # Green
    "R": "\033[31m" if sys.stdout.isatty() else "",  # Red
    "Y": "\033[33m" if sys.stdout.isatty() else "",  # Yellow
    "B": "\033[34m" if sys.stdout.isatty() else "",  # Blue
    "M": "\033[35m" if sys.stdout.isatty() else "",  # Magenta
    "C": "\033[36m" if sys.stdout.isatty() else "",  # Cyan
    "N": "\033[0m" if sys.stdout.isatty() else "",  # Reset
    "BOLD": "\033[1m" if sys.stdout.isatty() else "",  # Bold
}


# --- Project Root Detection ---
def get_project_root() -> Path:
    """
    Detect the project root directory by finding the Git repository root.
    Falls back to current working directory if not in a Git repository.
    """
    try:
        result = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.PIPE
        ).strip()
        return Path(result)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


# --- Logging and Message Functions ---
def log_msg(msg: str, *, kind: str = "B") -> None:
    """Log a verbose message with color coding."""
    if verbose_mode:
        print(f"{ANSI[kind]}▶{ANSI['N']} {msg}")


def format_message(prefix: str, msg: str, color_code: str) -> str:
    """Format a message with colored prefix and reset."""
    return f"{color_code}{prefix}{ANSI['N']} {msg}"


def info_msg(msg: str, *, console: bool = True) -> str:
    """Display/return a success message with green checkmark."""
    output = format_message("✔", msg, ANSI["G"])
    if console:
        print(output)
    return output


def warn_msg(msg: str, *, console: bool = True) -> str:
    """Display/return a warning message with yellow warning symbol."""
    output = format_message("⚠", msg, ANSI["Y"])
    if console:
        print(output, file=sys.stderr)
    return output


def error_msg(msg: str, *, console: bool = True) -> str:
    """Display/return an error message with red X symbol."""
    output = format_message("✖", msg, ANSI["R"])
    if console:
        print(output, file=sys.stderr)
    return output


def die(
    msg: str,
    json_data: dict[str, Any] | None = None,
    json_output_flag: bool = False,
    exit_code: int = 1,
) -> None:
    """
    Display error message and exit with specified code.

    Args:
        msg: Error message to display
        json_data: Additional data to include in JSON output
        json_output_flag: Whether to output JSON format
        exit_code: Exit code (default: 1)
    """
    error_msg(msg, console=not json_output_flag)
    if json_output_flag:
        base_data = {"status": "failure", "message": msg}
        if json_data:
            base_data.update(json_data)
        print(json.dumps(base_data, indent=2))
    sys.exit(exit_code)


# --- Configuration Base Classes ---
@dataclass
class BaseConfig:
    """Base configuration class with common CLI options."""

    project_root: Path
    json_output: bool = False
    dry_run: bool = False
    verbose: bool = False

    @property
    def khive_config_dir(self) -> Path:
        """Path to the .khive configuration directory."""
        return self.project_root / ".khive"

    def update_from_cli_args(self, args: Any) -> None:
        """Update configuration from CLI arguments."""
        if hasattr(args, "json_output"):
            self.json_output = args.json_output
        if hasattr(args, "dry_run"):
            self.dry_run = args.dry_run
        if hasattr(args, "verbose"):
            self.verbose = args.verbose

        # Update global verbose mode
        global verbose_mode
        verbose_mode = self.verbose


@dataclass
class StackConfig:
    """Configuration for stack-based operations (legacy compatibility)."""

    name: str
    cmd: str
    check_cmd: str
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    enabled: bool = True


# --- Configuration Loading Helpers ---
def load_toml_config(
    config_path: Path, default_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Load TOML configuration from file with error handling.

    Args:
        config_path: Path to the TOML configuration file
        default_config: Default configuration to use if file doesn't exist

    Returns:
        Parsed configuration dictionary
    """
    if not config_path.exists():
        return default_config or {}

    try:
        log_msg(f"Loading config from {config_path}")
        return tomllib.loads(config_path.read_text())
    except Exception as e:
        warn_msg(f"Could not parse {config_path}: {e}. Using default values.")
        return default_config or {}


def merge_config(
    base_config: dict[str, Any], override_config: dict[str, Any]
) -> dict[str, Any]:
    """
    Merge two configuration dictionaries, with override taking precedence.

    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary

    Returns:
        Merged configuration dictionary
    """
    merged = base_config.copy()
    for key, value in override_config.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = merge_config(merged[key], value)
        else:
            merged[key] = value
    return merged


# --- Command Execution Helpers ---
@dataclass
class CommandResult:
    """Result of a command execution."""

    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    success: bool
    duration: float = 0.0


def run_command(
    cmd_args: list[str],
    *,
    capture: bool = False,
    check: bool = True,
    dry_run: bool = False,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
    tool_name: str | None = None,
) -> CommandResult | int:
    """
    Execute a command with comprehensive options and error handling.

    Args:
        cmd_args: Command and arguments to execute
        capture: Whether to capture stdout/stderr
        check: Whether to raise exception on non-zero exit
        dry_run: Whether to simulate execution
        cwd: Working directory for command
        env: Environment variables
        timeout: Timeout in seconds
        tool_name: Name of tool for logging (defaults to cmd_args[0])

    Returns:
        CommandResult object if capture=True, exit code if capture=False
    """
    import time

    tool_name = tool_name or cmd_args[0]
    log_msg(f"{tool_name} " + " ".join(cmd_args[1:]))

    if dry_run:
        info_msg(f"[DRY-RUN] Would run: {' '.join(cmd_args)}", console=True)
        if capture:
            return CommandResult(
                command=cmd_args,
                exit_code=0,
                stdout="DRY_RUN_OUTPUT",
                stderr="",
                success=True,
                duration=0.0,
            )
        return 0

    start_time = time.time()

    try:
        # Prepare environment
        final_env = os.environ.copy()
        if env:
            final_env.update(env)

        process = subprocess.run(
            cmd_args,
            text=True,
            capture_output=capture,
            check=check,
            cwd=cwd,
            env=final_env,
            timeout=timeout,
        )

        duration = time.time() - start_time

        if capture:
            return CommandResult(
                command=cmd_args,
                exit_code=process.returncode,
                stdout=process.stdout or "",
                stderr=process.stderr or "",
                success=process.returncode == 0,
                duration=duration,
            )
        return process.returncode

    except FileNotFoundError:
        error_msg(
            f"{tool_name} command not found. Is {tool_name} installed and in PATH?"
        )
        if capture:
            return CommandResult(
                command=cmd_args,
                exit_code=127,
                stdout="",
                stderr=f"{tool_name} not found",
                success=False,
                duration=time.time() - start_time,
            )
        if check:
            sys.exit(127)
        return 127

    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        if capture:
            return CommandResult(
                command=cmd_args,
                exit_code=e.returncode,
                stdout=e.stdout or "",
                stderr=e.stderr or "",
                success=False,
                duration=duration,
            )
        if check:
            error_msg(
                f"{tool_name} command failed: {' '.join(cmd_args)}\nStderr: {e.stderr}"
            )
            raise
        return e.returncode

    except subprocess.TimeoutExpired as e:
        duration = time.time() - start_time
        error_msg(f"{tool_name} command timed out after {timeout} seconds")
        if capture:
            return CommandResult(
                command=cmd_args,
                exit_code=124,
                stdout=e.stdout.decode() if e.stdout else "",
                stderr=e.stderr.decode() if e.stderr else "",
                success=False,
                duration=duration,
            )
        if check:
            raise
        return 124


def git_run(
    cmd_args: list[str],
    *,
    capture: bool = False,
    check: bool = True,
    dry_run: bool = False,
    cwd: Path | None = None,
    timeout: int | None = None,
) -> CommandResult | int:
    """
    Execute a git command with standard options.

    Args:
        cmd_args: Git subcommand and arguments
        capture: Whether to capture stdout/stderr
        check: Whether to raise exception on non-zero exit
        dry_run: Whether to simulate execution
        cwd: Working directory for command
        timeout: Timeout in seconds

    Returns:
        CommandResult object if capture=True, exit code if capture=False
    """
    return run_command(
        ["git", *cmd_args],
        capture=capture,
        check=check,
        dry_run=dry_run,
        cwd=cwd,
        timeout=timeout,
        tool_name="git",
    )


def check_tool_available(tool_name: str) -> bool:
    """Check if a command-line tool is available in PATH."""
    return shutil.which(tool_name) is not None


def ensure_tools_available(tools: list[str], json_output: bool = False) -> None:
    """
    Ensure required tools are available, exit if any are missing.

    Args:
        tools: List of required tool names
        json_output: Whether to format error as JSON
    """
    missing_tools = [tool for tool in tools if not check_tool_available(tool)]
    if missing_tools:
        error_msg = f"Missing required tools: {', '.join(missing_tools)}"
        die(error_msg, json_output_flag=json_output)


# --- JSON Output Helpers ---
def format_json_output(
    status: str,
    message: str | None = None,
    data: dict[str, Any] | None = None,
    **kwargs: Any,
) -> str:
    """
    Format standardized JSON output.

    Args:
        status: Status string (success, failure, error, etc.)
        message: Optional message
        data: Additional data to include
        **kwargs: Additional key-value pairs to include

    Returns:
        JSON formatted string
    """
    output = {"status": status}
    if message:
        output["message"] = message
    if data:
        output.update(data)
    output.update(kwargs)
    return json.dumps(output, indent=2)


def print_json_result(
    status: str,
    message: str | None = None,
    data: dict[str, Any] | None = None,
    **kwargs: Any,
) -> None:
    """Print standardized JSON result and exit appropriately."""
    print(format_json_output(status, message, data, **kwargs))
    if status in ["failure", "error"]:
        sys.exit(1)


# --- File and Directory Helpers ---
def ensure_directory(path: Path) -> None:
    """Ensure a directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)


def safe_read_file(path: Path, default: str = "") -> str:
    """Safely read a file, returning default if file doesn't exist or can't be read."""
    try:
        return path.read_text()
    except (FileNotFoundError, PermissionError, OSError):
        return default


def safe_write_file(path: Path, content: str) -> bool:
    """
    Safely write content to a file, creating directories as needed.

    Returns:
        True if successful, False otherwise
    """
    try:
        ensure_directory(path.parent)
        path.write_text(content)
        return True
    except (PermissionError, OSError) as e:
        error_msg(f"Failed to write {path}: {e}")
        return False


# --- Validation Helpers ---
def validate_path_exists(path: Path, path_type: str = "path") -> None:
    """Validate that a path exists, exit with error if not."""
    if not path.exists():
        die(f"{path_type.title()} does not exist: {path}")


def validate_directory(path: Path, path_type: str = "directory") -> None:
    """Validate that a path is a directory, exit with error if not."""
    validate_path_exists(path, path_type)
    if not path.is_dir():
        die(f"{path_type.title()} is not a directory: {path}")


def validate_file(path: Path, path_type: str = "file") -> None:
    """Validate that a path is a file, exit with error if not."""
    validate_path_exists(path, path_type)
    if not path.is_file():
        die(f"{path_type.title()} is not a file: {path}")


# --- Progress and Status Helpers ---
def print_section_header(title: str, width: int = 50) -> None:
    """Print a formatted section header."""
    if not verbose_mode:
        return
    print(f"\n{ANSI['BOLD']}{title}{ANSI['N']}")
    print("=" * min(len(title), width))


def print_step(step: str, status: str = "running") -> None:
    """Print a step with status indicator."""
    if status == "running":
        print(f"{ANSI['B']}▶{ANSI['N']} {step}...")
    elif status == "success":
        print(f"{ANSI['G']}✔{ANSI['N']} {step}")
    elif status == "failure":
        print(f"{ANSI['R']}✖{ANSI['N']} {step}")
    elif status == "warning":
        print(f"{ANSI['Y']}⚠{ANSI['N']} {step}")


# --- Module Initialization ---
# Set up project root as module-level constant
PROJECT_ROOT = get_project_root()
KHIVE_CONFIG_DIR = PROJECT_ROOT / ".khive"
SQLITE_DSN = f"sqlite+aiosqlite:///{KHIVE_CONFIG_DIR}/claude_hooks.db"


class EventBroadcaster:
    """Real-time event broadcasting system for hook events."""

    _instance: ClassVar[EventBroadcaster | None] = None
    _subscribers: ClassVar[list[Callable[[Any], None]]] = []
    _async_subscribers: ClassVar[list[Callable[[Any], Any]]] = []
    _event_type: ClassVar[type]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def subscribe(cls, callback: Callable[[Any], None]) -> None:
        """Subscribe to hook events with sync callback."""
        if callback not in cls._subscribers:
            cls._subscribers.append(callback)

    @classmethod
    def subscribe_async(cls, callback: Callable[[Any], Any]) -> None:
        """Subscribe to hook events with async callback."""
        if callback not in cls._async_subscribers:
            cls._async_subscribers.append(callback)

    @classmethod
    def unsubscribe(cls, callback: Callable[[Any], None]) -> None:
        """Unsubscribe from hook events."""
        if callback in cls._subscribers:
            cls._subscribers.remove(callback)
        if callback in cls._async_subscribers:
            cls._async_subscribers.remove(callback)

    @classmethod
    async def broadcast(cls, event) -> None:
        """Broadcast event to all subscribers."""
        # Sync callbacks
        for callback in cls._subscribers:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in sync subscriber callback: {e}")

        # Async callbacks
        for callback in cls._async_subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                print(f"Error in async subscriber callback: {e}")

    @classmethod
    def get_subscriber_count(cls) -> int:
        """Get total number of subscribers."""
        return len(cls._subscribers) + len(cls._async_subscribers)
