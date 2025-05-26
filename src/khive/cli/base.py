# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Base classes and patterns for khive CLI commands.

This module provides:
- Base CLI command class with common functionality
- Standard argument parsing patterns
- Configuration management base classes
- Common workflow patterns
- Error handling and exit code management
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from khive.utils import (
    BaseConfig,
    die,
    get_project_root,
    info_msg,
    load_toml_config,
    print_json_result,
    validate_directory,
)

# Type variables
ConfigType = TypeVar("ConfigType", bound=BaseConfig)
ResultType = TypeVar("ResultType")


# --- Base Configuration Classes ---
@dataclass
class CLIResult:
    """Standard result structure for CLI commands."""

    status: str  # success, failure, error, skipped, dry_run
    message: str
    data: dict[str, Any] | None = None
    exit_code: int = 0

    def is_success(self) -> bool:
        """Check if the result represents success."""
        return self.status in ["success", "skipped", "dry_run"]

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for JSON output."""
        result = {
            "status": self.status,
            "message": self.message,
        }
        if self.data:
            result.update(self.data)
        return result


# --- Base CLI Command Class ---
class BaseCLICommand(ABC):
    """
    Abstract base class for khive CLI commands.

    Provides common functionality:
    - Argument parsing with standard options
    - Configuration loading
    - Error handling and exit code management
    - JSON output formatting
    - Dry-run support
    """

    def __init__(self, command_name: str, description: str):
        self.command_name = command_name
        self.description = description
        self.parser = self._create_parser()
        self.config: BaseConfig | None = None

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser with standard options."""
        parser = argparse.ArgumentParser(description=self.description)

        # Add standard options that most commands need
        parser.add_argument(
            "--project-root",
            type=Path,
            default=get_project_root(),
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

        # Allow subclasses to add their own arguments
        self._add_arguments(parser)
        return parser

    @abstractmethod
    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add command-specific arguments to the parser."""

    @abstractmethod
    def _create_config(self, args: argparse.Namespace) -> BaseConfig:
        """Create and return the configuration object for this command."""

    @abstractmethod
    def _execute(self, args: argparse.Namespace, config: BaseConfig) -> CLIResult:
        """Execute the main command logic. Can be sync or async."""

    def _validate_args(self, args: argparse.Namespace) -> None:
        """Validate command-line arguments. Override in subclasses if needed."""
        # Validate project root
        validate_directory(args.project_root, "project root")

    def _load_config_file(self, config_path: Path) -> dict[str, Any]:
        """Load configuration from TOML file."""
        return load_toml_config(config_path)

    def _handle_result(self, result: CLIResult, json_output: bool) -> None:
        """Handle the command result and exit appropriately."""
        if json_output:
            print_json_result(result.status, result.message, result.data)
        else:
            if result.is_success():
                if result.status != "skipped":  # Don't show success for skipped
                    info_msg(f"{self.command_name} finished: {result.message}")
            else:
                die(result.message, result.data, json_output, result.exit_code)

        if not result.is_success():
            sys.exit(result.exit_code)

    def run(self, argv: list[str] | None = None) -> int:
        """
        Main entry point for the command.

        Args:
            argv: Command line arguments (defaults to sys.argv)

        Returns:
            Exit code
        """
        try:
            # Parse arguments
            args = self.parser.parse_args(argv)

            # Set global verbose mode
            global verbose_mode
            verbose_mode = args.verbose

            # Validate arguments
            self._validate_args(args)

            # Create configuration
            self.config = self._create_config(args)

            # Execute command (handle both sync and async)
            result = self._run_execute(args, self.config)

            # Handle result and exit
            self._handle_result(result, args.json_output)

            return result.exit_code

        except KeyboardInterrupt:
            if hasattr(args, "json_output") and args.json_output:
                print_json_result("interrupted", "Command interrupted by user")
            else:
                print("\nCommand interrupted by user", file=sys.stderr)
            return 130

        except Exception as e:
            error_msg = f"Unexpected error in {self.command_name}: {e}"
            if hasattr(args, "json_output") and args.json_output:
                print_json_result("error", error_msg)
            else:
                die(error_msg)
            return 1

    def _run_execute(self, args: argparse.Namespace, config: BaseConfig) -> CLIResult:
        """Run the _execute method, handling both sync and async implementations."""
        # Check if _execute is a coroutine function (async)
        if inspect.iscoroutinefunction(self._execute):
            # Run async method
            try:
                # Try to get existing event loop
                loop = asyncio.get_running_loop()
                # If we're already in an event loop, we need to handle this differently
                import concurrent.futures
                import threading

                result_container = {}
                exception_container = {}

                def run_in_thread():
                    try:
                        # Create new event loop for this thread
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            result = new_loop.run_until_complete(
                                self._execute(args, config)
                            )
                            result_container["result"] = result
                        finally:
                            # Ensure proper cleanup
                            try:
                                new_loop.close()
                            except Exception:
                                pass
                            asyncio.set_event_loop(None)
                    except Exception as e:
                        exception_container["exception"] = e

                # Run in thread
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()

                if "exception" in exception_container:
                    raise exception_container["exception"]

                return result_container["result"]

            except RuntimeError as e:
                # No event loop running, safe to use asyncio.run()
                if "no running event loop" in str(e).lower():
                    # For MCP command, suppress asyncio warnings during shutdown
                    if hasattr(self, "command_name") and self.command_name == "mcp":
                        import warnings
                        import sys
                        import os

                        # Capture stderr to suppress FastMCP/anyio error messages
                        original_stderr = sys.stderr

                        # Create a filter for stderr that suppresses specific error patterns
                        class ErrorFilter:
                            def __init__(self, original_stderr):
                                self.original_stderr = original_stderr
                                self.buffer = ""

                            def write(self, text):
                                # Filter out FastMCP/anyio error patterns
                                if any(
                                    pattern in text
                                    for pattern in [
                                        "cancel scope",
                                        "fastmcp",
                                        "anyio",
                                        "ExceptionGroup",
                                        "BaseExceptionGroup",
                                        "unhandled exception during asyncio.run() shutdown",
                                        "CancelledError",
                                        "RuntimeError: Attempted to exit cancel scope",
                                    ]
                                ):
                                    return  # Suppress these errors

                                # Allow other errors through
                                self.original_stderr.write(text)

                            def flush(self):
                                self.original_stderr.flush()

                        try:
                            # Redirect stderr to filter
                            sys.stderr = ErrorFilter(original_stderr)

                            # Also suppress warnings
                            with warnings.catch_warnings():
                                warnings.filterwarnings(
                                    "ignore", category=RuntimeWarning
                                )
                                warnings.filterwarnings("ignore", category=UserWarning)
                                return asyncio.run(self._execute(args, config))
                        finally:
                            # Always restore stderr
                            sys.stderr = original_stderr
                    else:
                        return asyncio.run(self._execute(args, config))
                else:
                    # Some other RuntimeError, re-raise
                    raise
        else:
            # Run sync method
            return self._execute(args, config)


# --- Specialized Base Classes ---
class FileBasedCLICommand(BaseCLICommand):
    """
    Base class for commands that work with specific files or file patterns.

    Adds common file-related arguments and validation.
    """

    def _add_file_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add common file-related arguments."""
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing files without confirmation",
        )


class ConfigurableCLICommand(BaseCLICommand):
    """
    Base class for commands that use TOML configuration files.

    Provides standardized configuration loading and merging.
    """

    @property
    @abstractmethod
    def config_filename(self) -> str:
        """Return the name of the configuration file (e.g., 'commit.toml')."""

    @property
    @abstractmethod
    def default_config(self) -> dict[str, Any]:
        """Return the default configuration dictionary."""

    def _load_command_config(self, project_root: Path) -> dict[str, Any]:
        """Load command-specific configuration from .khive/{config_filename}."""
        config_path = project_root / ".khive" / self.config_filename
        file_config = self._load_config_file(config_path)

        # Merge with defaults
        config = self.default_config.copy()
        config.update(file_config)
        return config


class GitBasedCLICommand(ConfigurableCLICommand):
    """
    Base class for commands that work with Git repositories.

    Adds Git-specific validation and helper methods.
    """

    def _validate_args(self, args: argparse.Namespace) -> None:
        """Validate that we're in a Git repository."""
        super()._validate_args(args)

        # Check if we're in a Git repository
        git_dir = args.project_root / ".git"
        if not git_dir.exists():
            die(f"Not a Git repository: {args.project_root}")

    def _get_current_branch(self, project_root: Path) -> str:
        """Get the current Git branch name."""
        from khive.utils import git_run

        result = git_run(
            ["branch", "--show-current"], capture=True, check=False, cwd=project_root
        )

        if hasattr(result, "success") and result.success and result.stdout.strip():
            return result.stdout.strip()

        # Fallback for detached HEAD
        result = git_run(
            ["rev-parse", "--short", "HEAD"], capture=True, check=True, cwd=project_root
        )

        if hasattr(result, "stdout"):
            return f"detached-HEAD-{result.stdout.strip()}"

        return "HEAD"


# --- Command Factory ---
class CLICommandFactory:
    """Factory for creating and registering CLI commands."""

    _commands: dict[str, type[BaseCLICommand]] = {}

    @classmethod
    def register(cls, name: str, command_class: type[BaseCLICommand]) -> None:
        """Register a command class with a name."""
        cls._commands[name] = command_class

    @classmethod
    def create(cls, name: str, *args, **kwargs) -> BaseCLICommand:
        """Create a command instance by name."""
        if name not in cls._commands:
            raise ValueError(f"Unknown command: {name}")
        return cls._commands[name](*args, **kwargs)

    @classmethod
    def list_commands(cls) -> list[str]:
        """List all registered command names."""
        return list(cls._commands.keys())


# --- Decorators ---
def cli_command(name: str):
    """Decorator to register a CLI command class."""

    def decorator(cls: type[BaseCLICommand]) -> type[BaseCLICommand]:
        CLICommandFactory.register(name, cls)
        return cls

    return decorator


# --- Common Workflow Patterns ---
class WorkflowStep:
    """Represents a single step in a command workflow."""

    def __init__(self, name: str, description: str, required: bool = True):
        self.name = name
        self.description = description
        self.required = required
        self.completed = False
        self.error: str | None = None


class CommandWorkflow:
    """Manages a sequence of steps for complex commands."""

    def __init__(self, name: str):
        self.name = name
        self.steps: list[WorkflowStep] = []
        self.current_step = 0

    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow."""
        self.steps.append(step)

    def execute_step(self, step_index: int, executor: callable) -> bool:
        """
        Execute a specific step.

        Args:
            step_index: Index of the step to execute
            executor: Function to execute the step

        Returns:
            True if step succeeded, False otherwise
        """
        if step_index >= len(self.steps):
            return False

        step = self.steps[step_index]

        try:
            from khive.utils import print_step

            print_step(step.description, "running")

            success = executor(step)

            if success:
                step.completed = True
                print_step(step.description, "success")
            else:
                print_step(step.description, "failure")
                if step.required:
                    return False

            return True

        except Exception as e:
            step.error = str(e)
            print_step(f"{step.description}: {e}", "failure")
            return not step.required

    def execute_all(self, executor: callable) -> bool:
        """
        Execute all steps in sequence.

        Args:
            executor: Function that takes a WorkflowStep and returns success boolean

        Returns:
            True if all required steps succeeded
        """
        for i, step in enumerate(self.steps):
            if not self.execute_step(i, executor):
                return False
        return True

    def get_status(self) -> dict[str, Any]:
        """Get the current workflow status."""
        return {
            "name": self.name,
            "total_steps": len(self.steps),
            "completed_steps": sum(1 for step in self.steps if step.completed),
            "failed_steps": sum(1 for step in self.steps if step.error),
            "steps": [
                {
                    "name": step.name,
                    "description": step.description,
                    "required": step.required,
                    "completed": step.completed,
                    "error": step.error,
                }
                for step in self.steps
            ],
        }
