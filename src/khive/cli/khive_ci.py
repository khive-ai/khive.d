# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_ci.py - Enhanced CI command with nested configuration support.

Features
========
* Multi-stack test execution (Python, Rust)
* Nested configuration support for monorepos
* Custom CI script support via .khive/scripts/khive_ci.sh
* Proper async execution with timeout handling
* JSON output support
* Configurable via TOML at multiple levels
* Respects pytest.ini and pyproject.toml configurations

CLI
---
    khive ci [--test-type python|rust|all] [--timeout 300] [--dry-run] [--verbose] [--json-output]

Exit codes: 0 success · 1 failure.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

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
    "M": "\033[35m" if sys.stdout.isatty() else "",
    "C": "\033[36m" if sys.stdout.isatty() else "",
    "N": "\033[0m" if sys.stdout.isatty() else "",
    "BOLD": "\033[1m" if sys.stdout.isatty() else "",
}
verbose_mode = False


def log_msg_ci(msg: str, *, kind: str = "B") -> None:
    if verbose_mode:
        print(f"{ANSI[kind]}▶{ANSI['N']} {msg}")


def format_message_ci(prefix: str, msg: str, color_code: str) -> str:
    return f"{color_code}{prefix}{ANSI['N']} {msg}"


def info_msg_ci(msg: str, *, console: bool = True) -> str:
    output = format_message_ci("✔", msg, ANSI["G"])
    if console:
        print(output)
    return output


def warn_msg_ci(msg: str, *, console: bool = True) -> str:
    output = format_message_ci("⚠", msg, ANSI["Y"])
    if console:
        print(output, file=sys.stderr)
    return output


def error_msg_ci(msg: str, *, console: bool = True) -> str:
    output = format_message_ci("✖", msg, ANSI["R"])
    if console:
        print(output, file=sys.stderr)
    return output


def die_ci(
    msg: str, json_data: dict[str, Any] | None = None, json_output_flag: bool = False
) -> None:
    error_msg_ci(msg, console=not json_output_flag)
    if json_output_flag:
        base_data = {"status": "failure", "message": msg, "test_results": []}
        if json_data:
            base_data.update(json_data)
        print(json.dumps(base_data, indent=2))
    sys.exit(1)


# --- Test Output Parsing ---
@dataclass
class PytestSummary:
    """Parsed pytest output summary."""

    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    warnings: int = 0
    duration: float = 0.0
    coverage_percent: float | None = None
    test_files: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped + self.errors

    @property
    def success(self) -> bool:
        return self.failed == 0 and self.errors == 0


def parse_pytest_output(output: str) -> PytestSummary:
    """Parse pytest output to extract key metrics."""
    summary = PytestSummary()

    # Parse test results line (e.g., "369 passed, 4 skipped, 9 warnings in 5.95s")
    results_pattern = r"(\d+)\s+passed|(\d+)\s+failed|(\d+)\s+skipped|(\d+)\s+error|(\d+)\s+warnings?\s+in\s+([\d.]+)s"
    for match in re.finditer(results_pattern, output):
        if match.group(1):
            summary.passed = int(match.group(1))
        elif match.group(2):
            summary.failed = int(match.group(2))
        elif match.group(3):
            summary.skipped = int(match.group(3))
        elif match.group(4):
            summary.errors = int(match.group(4))
        elif match.group(5):
            summary.warnings = int(match.group(5))
        elif match.group(6):
            summary.duration = float(match.group(6))

    # Parse coverage if present
    coverage_pattern = r"TOTAL\s+\d+\s+\d+\s+(\d+)%"
    coverage_match = re.search(coverage_pattern, output)
    if coverage_match:
        summary.coverage_percent = float(coverage_match.group(1))

    # Parse test file names
    file_pattern = r"^(tests/[^\s]+\.py)\s+"
    for match in re.finditer(file_pattern, output, re.MULTILINE):
        summary.test_files.append(match.group(1))

    # Parse failures
    failure_section = re.search(r"=+ FAILURES =+(.+?)(?:=+ |$)", output, re.DOTALL)
    if failure_section:
        summary.failures = [
            line.strip()
            for line in failure_section.group(1).split("\n")
            if line.strip()
        ]

    return summary


# --- Configuration ---
@dataclass
class TestConfig:
    """Configuration for a specific test type."""

    test_command: str
    test_tool: str
    config_file: str | None = None
    test_paths: list[str] = field(default_factory=list)
    timeout: int | None = None
    coverage: bool = False
    coverage_threshold: float = 80.0
    extra_args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    use_native_discovery: bool = True  # New: respect tool's native discovery
    show_output: str = "smart"  # New: always/never/smart/on-failure


@dataclass
class CIConfig:
    project_root: Path
    timeout: int = 300
    json_output: bool = False
    dry_run: bool = False
    verbose: bool = False
    test_configs: dict[str, TestConfig] = field(default_factory=dict)
    enabled_tests: list[str] = field(default_factory=list)

    @property
    def khive_config_dir(self) -> Path:
        return self.project_root / ".khive"


def load_pytest_config(project_root: Path) -> dict[str, Any]:
    """Load pytest configuration from pytest.ini or pyproject.toml."""
    config = {}

    # Check pyproject.toml first (higher priority)
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        try:
            pyproject_data = tomllib.loads(pyproject_path.read_text())
            tool_pytest = pyproject_data.get("tool", {}).get("pytest", {})
            if tool_pytest:
                config.update(tool_pytest)
                log_msg_ci(f"Loaded pytest config from {pyproject_path}")
        except Exception as e:
            warn_msg_ci(f"Could not parse pytest config from pyproject.toml: {e}")

    # Check pytest.ini
    pytest_ini = project_root / "pytest.ini"
    if pytest_ini.exists():
        try:
            import configparser

            parser = configparser.ConfigParser()
            parser.read(pytest_ini)
            if "pytest" in parser:
                for key, value in parser["pytest"].items():
                    if key not in config:  # pyproject.toml takes precedence
                        config[key] = value
                log_msg_ci(f"Loaded pytest config from {pytest_ini}")
        except Exception as e:
            warn_msg_ci(f"Could not parse pytest.ini: {e}")

    return config


def load_ci_config(
    project_r: Path, cli_args: argparse.Namespace | None = None
) -> CIConfig:
    cfg = CIConfig(project_root=project_r)

    # Default test configurations
    default_python_config = TestConfig(
        test_command="pytest",
        test_tool="pytest",
        test_paths=[],
        extra_args=[],
        use_native_discovery=True,
        show_output="smart",
    )

    default_rust_config = TestConfig(
        test_command="cargo test",
        test_tool="cargo",
        test_paths=[],
        extra_args=[],
        show_output="smart",
    )

    # Load configuration from .khive/ci.toml if it exists
    config_file = cfg.khive_config_dir / "ci.toml"
    if config_file.exists():
        log_msg_ci(f"Loading CI config from {config_file}")
        try:
            raw_toml = tomllib.loads(config_file.read_text())

            # Load general settings
            cfg.timeout = raw_toml.get("timeout", cfg.timeout)
            cfg.enabled_tests = raw_toml.get("enable", ["python", "rust"])

            # Load test-specific configurations
            test_configs = raw_toml.get("tests", {})

            for test_type, test_config in test_configs.items():
                if test_type == "python":
                    cfg.test_configs["python"] = TestConfig(
                        test_command=test_config.get(
                            "command", default_python_config.test_command
                        ),
                        test_tool=test_config.get(
                            "tool", default_python_config.test_tool
                        ),
                        test_paths=test_config.get("paths", []),
                        timeout=test_config.get("timeout"),
                        coverage=test_config.get("coverage", False),
                        coverage_threshold=test_config.get("coverage_threshold", 80.0),
                        extra_args=test_config.get("extra_args", []),
                        env=test_config.get("env", {}),
                        use_native_discovery=test_config.get(
                            "use_native_discovery", True
                        ),
                        show_output=test_config.get("show_output", "smart"),
                    )
                elif test_type == "rust":
                    cfg.test_configs["rust"] = TestConfig(
                        test_command=test_config.get(
                            "command", default_rust_config.test_command
                        ),
                        test_tool=test_config.get(
                            "tool", default_rust_config.test_tool
                        ),
                        test_paths=test_config.get("paths", []),
                        timeout=test_config.get("timeout"),
                        extra_args=test_config.get("extra_args", []),
                        env=test_config.get("env", {}),
                        show_output=test_config.get("show_output", "smart"),
                    )
                else:
                    # Custom test type
                    cfg.test_configs[test_type] = TestConfig(
                        test_command=test_config.get("command", ""),
                        test_tool=test_config.get("tool", ""),
                        test_paths=test_config.get("paths", []),
                        timeout=test_config.get("timeout"),
                        extra_args=test_config.get("extra_args", []),
                        env=test_config.get("env", {}),
                        show_output=test_config.get("show_output", "smart"),
                    )

        except Exception as e:
            warn_msg_ci(f"Could not parse {config_file}: {e}. Using default values.")
    else:
        # No config file, use defaults
        cfg.test_configs["python"] = default_python_config
        cfg.test_configs["rust"] = default_rust_config

    # Apply CLI arguments
    if cli_args:
        cfg.json_output = cli_args.json_output
        cfg.dry_run = cli_args.dry_run
        cfg.verbose = cli_args.verbose
        if hasattr(cli_args, "timeout") and cli_args.timeout:
            cfg.timeout = cli_args.timeout

        global verbose_mode
        verbose_mode = cli_args.verbose

    return cfg


# --- Data Classes ---
@dataclass
class CITestResult:
    """Represents the result of a test execution."""

    test_type: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    success: bool
    project_path: str | None = None
    summary: PytestSummary | None = None  # New: parsed test summary


@dataclass
class CIResult:
    """Represents the overall result of CI execution."""

    project_root: Path
    test_results: list[CITestResult] = field(default_factory=list)
    discovered_projects: dict[str, dict[str, Any]] = field(default_factory=dict)
    nested_results: list[dict[str, Any]] = field(default_factory=list)
    overall_success: bool = True
    total_duration: float = 0.0

    def add_test_result(self, result: CITestResult) -> None:
        """Add a test result and update overall status."""
        self.test_results.append(result)
        self.total_duration += result.duration
        if not result.success:
            self.overall_success = False


# --- Project Detection ---
def detect_project_types(
    project_root: Path, config: CIConfig | None = None
) -> dict[str, dict[str, Any]]:
    """
    Detect project types and their test configurations within a specific directory.

    Args:
        project_root: Path to the project root directory
        config: CIConfig with test configurations

    Returns:
        Dictionary mapping project types to their configurations
    """
    projects = {}

    # Check if we should skip directories with their own configs
    skip_nested = project_root == (config.project_root if config else project_root)

    # Check for Python project
    if (project_root / "pyproject.toml").exists() or (
        project_root / "setup.py"
    ).exists():
        python_config = config.test_configs.get("python") if config else None
        if python_config:
            # If native discovery is enabled and no paths specified, let pytest handle it
            test_paths = python_config.test_paths
            if python_config.use_native_discovery and not test_paths:
                test_paths = []  # Empty list means pytest will use its own discovery
            elif not test_paths:
                test_paths = _discover_python_test_paths(project_root, skip_nested)

            projects["python"] = {
                "test_command": python_config.test_command,
                "test_tool": python_config.test_tool,
                "config_file": "pyproject.toml"
                if (project_root / "pyproject.toml").exists()
                else None,
                "test_paths": test_paths,
                "timeout": python_config.timeout,
                "coverage": python_config.coverage,
                "coverage_threshold": python_config.coverage_threshold,
                "extra_args": python_config.extra_args,
                "env": python_config.env,
                "use_native_discovery": python_config.use_native_discovery,
                "show_output": python_config.show_output,
            }
        else:
            projects["python"] = {
                "test_command": "pytest",
                "test_tool": "pytest",
                "config_file": "pyproject.toml"
                if (project_root / "pyproject.toml").exists()
                else None,
                "test_paths": [],  # Let pytest discover
                "use_native_discovery": True,
                "show_output": "smart",
            }

    # Check for Rust project
    if (project_root / "Cargo.toml").exists():
        rust_config = config.test_configs.get("rust") if config else None
        if rust_config:
            projects["rust"] = {
                "test_command": rust_config.test_command,
                "test_tool": rust_config.test_tool,
                "config_file": "Cargo.toml",
                "test_paths": rust_config.test_paths
                or _discover_rust_test_paths(project_root),
                "timeout": rust_config.timeout,
                "extra_args": rust_config.extra_args,
                "env": rust_config.env,
                "show_output": rust_config.show_output,
            }
        else:
            projects["rust"] = {
                "test_command": "cargo test",
                "test_tool": "cargo",
                "config_file": "Cargo.toml",
                "test_paths": _discover_rust_test_paths(project_root),
                "show_output": "smart",
            }

    # Check for custom test types from config
    if config:
        for test_type, test_config in config.test_configs.items():
            if test_type not in ["python", "rust"] and test_config.test_command:
                projects[test_type] = {
                    "test_command": test_config.test_command,
                    "test_tool": test_config.test_tool,
                    "config_file": test_config.config_file,
                    "test_paths": test_config.test_paths,
                    "timeout": test_config.timeout,
                    "extra_args": test_config.extra_args,
                    "env": test_config.env,
                    "show_output": test_config.show_output,
                }

    # Filter by enabled tests
    if config and config.enabled_tests:
        projects = {k: v for k, v in projects.items() if k in config.enabled_tests}

    return projects


def _discover_python_test_paths(
    project_root: Path, skip_nested: bool = True
) -> list[str]:
    """Discover Python test paths, optionally skipping nested projects."""
    test_paths = []

    # Collect directories to skip if they have their own CI config
    dirs_to_skip = set()
    if skip_nested:
        for ci_config in project_root.rglob(".khive/ci.toml"):
            if ci_config.parent.parent != project_root:
                dirs_to_skip.add(ci_config.parent.parent)

    # Common test directories
    common_test_dirs = ["tests", "test", "src/tests"]
    for test_dir in common_test_dirs:
        test_path = project_root / test_dir
        if test_path.exists() and test_path.is_dir():
            # Check if this path is inside a nested project
            skip = False
            for skip_dir in dirs_to_skip:
                try:
                    test_path.relative_to(skip_dir)
                    skip = True
                    break
                except ValueError:
                    continue

            if not skip:
                test_paths.append(str(test_path.relative_to(project_root)))

    # If we found common test directories, don't look for individual files
    if test_paths:
        return test_paths

    # Look for test files in common patterns
    test_patterns = ["test_*.py", "*_test.py"]
    for pattern in test_patterns:
        for test_file in project_root.rglob(pattern):
            # Skip virtual environment and other common non-project directories
            if any(
                part in [".venv", "venv", "env", ".env", "node_modules", ".git"]
                for part in test_file.parts
            ):
                continue

            # Skip if in a nested project
            skip = False
            for skip_dir in dirs_to_skip:
                try:
                    test_file.relative_to(skip_dir)
                    skip = True
                    break
                except ValueError:
                    continue

            if not skip and test_file.is_file():
                test_dir = str(test_file.parent.relative_to(project_root))
                if test_dir not in test_paths and test_dir != ".":
                    test_paths.append(test_dir)

    return test_paths if test_paths else ["."]


def _discover_rust_test_paths(project_root: Path) -> list[str]:
    """Discover Rust test paths."""
    test_paths = []

    # Check for tests directory
    tests_dir = project_root / "tests"
    if tests_dir.exists() and tests_dir.is_dir():
        test_paths.append("tests")

    # Check for src directory (unit tests)
    src_dir = project_root / "src"
    if src_dir.exists() and src_dir.is_dir():
        test_paths.append("src")

    return test_paths if test_paths else ["."]


def validate_test_tools(projects: dict[str, dict[str, Any]]) -> dict[str, bool]:
    """
    Validate that required test tools are available.

    Args:
        projects: Dictionary of detected projects

    Returns:
        Dictionary mapping project types to tool availability
    """
    tool_availability = {}

    for project_type, config in projects.items():
        tool = config["test_tool"]
        tool_availability[project_type] = shutil.which(tool) is not None

    return tool_availability


# --- Nested Directory Support ---
async def run_ci_for_nested_directory(
    dir_path: Path, parent_config: CIConfig, cli_args: argparse.Namespace
) -> dict[str, Any] | None:
    """
    Run CI for a directory with its own .khive/ci.toml configuration.

    Returns the result dict if CI was run, None otherwise.
    """
    nested_config_path = dir_path / ".khive" / "ci.toml"

    if not nested_config_path.exists():
        return None

    info_msg_ci(
        f"Processing nested project: {dir_path.relative_to(parent_config.project_root)}",
        console=not parent_config.json_output,
    )

    # Create a new config for this subdirectory
    nested_config = load_ci_config(dir_path, cli_args)

    # Check for custom CI script in nested directory
    custom_result = await check_and_run_custom_ci_script(nested_config)
    if custom_result:
        return {
            "directory": str(dir_path.relative_to(parent_config.project_root)),
            "status": "success" if custom_result.overall_success else "failure",
            "test_results": [
                {
                    "test_type": tr.test_type,
                    "command": tr.command,
                    "exit_code": tr.exit_code,
                    "success": tr.success,
                    "duration": tr.duration,
                    "stdout": tr.stdout if parent_config.verbose else "",
                    "stderr": tr.stderr if parent_config.verbose else "",
                }
                for tr in custom_result.test_results
            ],
            "duration": custom_result.total_duration,
        }

    # Otherwise, run standard CI for this directory
    result = CIResult(project_root=dir_path)

    # Discover projects in this directory
    discovered_projects = detect_project_types(dir_path, nested_config)
    result.discovered_projects = discovered_projects

    if not discovered_projects:
        return {
            "directory": str(dir_path.relative_to(parent_config.project_root)),
            "status": "skipped",
            "message": f"No test projects discovered in {dir_path.name}",
            "test_results": [],
            "duration": 0.0,
        }

    # Validate tools
    tool_availability = validate_test_tools(discovered_projects)
    missing_tools = [
        project_type
        for project_type, available in tool_availability.items()
        if not available
    ]

    if missing_tools:
        return {
            "directory": str(dir_path.relative_to(parent_config.project_root)),
            "status": "error",
            "message": f"Missing required tools for {dir_path.name}: {', '.join(missing_tools)}",
            "test_results": [],
            "duration": 0.0,
        }

    if nested_config.dry_run:
        return {
            "directory": str(dir_path.relative_to(parent_config.project_root)),
            "status": "dry_run",
            "would_execute": [
                f"{config['test_command']} for {project_type}"
                for project_type, config in discovered_projects.items()
            ],
            "test_results": [],
            "duration": 0.0,
        }

    # Execute tests
    for project_type, proj_config in discovered_projects.items():
        if not parent_config.verbose and not parent_config.json_output:
            print(f"Running {project_type} tests in {dir_path.name}...")

        test_result = await execute_tests_async(
            project_root=dir_path,
            project_type=project_type,
            config=proj_config,
            timeout=proj_config.get("timeout", nested_config.timeout),
            verbose=parent_config.verbose,
        )
        test_result.project_path = str(dir_path.relative_to(parent_config.project_root))

        result.add_test_result(test_result)

        # Show test output based on configuration
        show_output = proj_config.get("show_output", "smart")
        should_show = should_show_output(show_output, test_result, parent_config)

        if should_show and not parent_config.json_output:
            display_test_output(test_result, project_type, dir_path.name)

    return {
        "directory": str(dir_path.relative_to(parent_config.project_root)),
        "status": "success" if result.overall_success else "failure",
        "test_results": [
            {
                "test_type": tr.test_type,
                "command": tr.command,
                "exit_code": tr.exit_code,
                "success": tr.success,
                "duration": tr.duration,
                "stdout": tr.stdout if parent_config.verbose else "",
                "stderr": tr.stderr if parent_config.verbose else "",
                "summary": tr.summary.__dict__ if tr.summary else None,
            }
            for tr in result.test_results
        ],
        "duration": result.total_duration,
    }


# --- Custom Script Support ---
async def check_and_run_custom_ci_script(config: CIConfig) -> CIResult | None:
    """Check for custom CI script and execute it if found."""
    custom_script_path = config.khive_config_dir / "scripts" / "khive_ci.sh"

    if not custom_script_path.exists():
        return None

    # Verify the script is executable
    if not os.access(custom_script_path, os.X_OK):
        warn_msg_ci(
            f"Custom CI script {custom_script_path} exists but is not executable. "
            f"Run: chmod +x {custom_script_path}",
            console=not config.json_output,
        )
        return None

    # Security check
    script_stat = custom_script_path.stat()
    if not stat.S_ISREG(script_stat.st_mode):
        error_msg_ci(
            f"Custom CI script {custom_script_path} is not a regular file",
            console=not config.json_output,
        )
        result = CIResult(project_root=config.project_root)
        result.overall_success = False
        return result

    info_msg_ci(
        f"Using custom CI script: {custom_script_path}", console=not config.json_output
    )

    # Prepare environment variables
    env = os.environ.copy()
    env.update({
        "KHIVE_PROJECT_ROOT": str(config.project_root),
        "KHIVE_CONFIG_DIR": str(config.khive_config_dir),
        "KHIVE_DRY_RUN": "1" if config.dry_run else "0",
        "KHIVE_VERBOSE": "1" if config.verbose else "0",
        "KHIVE_JSON_OUTPUT": "1" if config.json_output else "0",
        "KHIVE_TIMEOUT": str(config.timeout),
    })

    # Build command
    cmd = [str(custom_script_path)]
    if config.dry_run:
        cmd.append("--dry-run")
    if config.verbose:
        cmd.append("--verbose")
    if config.json_output:
        cmd.append("--json-output")
    cmd.extend(["--timeout", str(config.timeout)])

    log_msg_ci(f"Executing custom CI script: {' '.join(cmd)}")

    if config.dry_run:
        info_msg_ci(f"[DRY-RUN] Would execute: {' '.join(cmd)}", console=True)
        result = CIResult(project_root=config.project_root)
        result.test_results.append(
            CITestResult(
                test_type="custom_script",
                command=" ".join(cmd),
                exit_code=0,
                stdout="DRY RUN",
                stderr="",
                duration=0.0,
                success=True,
            )
        )
        return result

    try:
        start_time = time.time()
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=config.project_root,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=config.timeout
        )
        duration = time.time() - start_time

        stdout = stdout_bytes.decode(errors="replace").strip()
        stderr = stderr_bytes.decode(errors="replace").strip()

        # Try to parse JSON output if in JSON mode
        if config.json_output and stdout.strip():
            try:
                custom_result_data = json.loads(stdout.strip())
                if (
                    isinstance(custom_result_data, dict)
                    and "test_results" in custom_result_data
                ):
                    result = CIResult(project_root=config.project_root)
                    result.overall_success = (
                        custom_result_data.get("status") == "success"
                    )

                    for test_data in custom_result_data["test_results"]:
                        test_result = CITestResult(
                            test_type=test_data.get("test_type", "custom"),
                            command=test_data.get("command", ""),
                            exit_code=test_data.get("exit_code", proc.returncode),
                            stdout=test_data.get("stdout", ""),
                            stderr=test_data.get("stderr", ""),
                            duration=test_data.get("duration", duration),
                            success=test_data.get("success", proc.returncode == 0),
                        )
                        result.add_test_result(test_result)

                    return result
            except json.JSONDecodeError:
                pass  # Fall through to handle as plain text

        # Handle as single test result
        result = CIResult(project_root=config.project_root)
        test_result = CITestResult(
            test_type="custom_script",
            command=" ".join(cmd),
            exit_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            duration=duration,
            success=proc.returncode == 0,
        )
        result.add_test_result(test_result)

        if proc.returncode != 0:
            if not config.json_output:
                error_msg_ci(
                    f"Custom CI script failed with exit code {proc.returncode}"
                )
                print(f"Command: {' '.join(cmd)}", file=sys.stderr)
                print(f"Working directory: {config.project_root}", file=sys.stderr)
                if stdout:
                    print(f"\n--- Script Output ---\n{stdout}")
                if stderr:
                    print(f"\n--- Error Output ---\n{stderr}", file=sys.stderr)
        elif not config.json_output and stdout:
            print(stdout)

        return result

    except asyncio.TimeoutError:
        duration = time.time() - start_time
        error_msg_ci("Custom CI script timed out", console=not config.json_output)
        result = CIResult(project_root=config.project_root)
        result.overall_success = False
        test_result = CITestResult(
            test_type="custom_script",
            command=" ".join(cmd),
            exit_code=124,
            stdout="",
            stderr=f"Timeout after {config.timeout} seconds",
            duration=duration,
            success=False,
        )
        result.add_test_result(test_result)
        return result
    except Exception as e:
        error_msg_ci(
            f"Failed to execute custom CI script: {e}", console=not config.json_output
        )
        result = CIResult(project_root=config.project_root)
        result.overall_success = False
        test_result = CITestResult(
            test_type="custom_script",
            command=" ".join(cmd),
            exit_code=1,
            stdout="",
            stderr=str(e),
            duration=0.0,
            success=False,
        )
        result.add_test_result(test_result)
        return result


# --- Enhanced Test Execution ---
async def execute_tests_async(
    project_root: Path,
    project_type: str,
    config: dict[str, Any],
    timeout: int = 300,
    verbose: bool = False,
) -> CITestResult:
    """
    Execute tests for a specific project type using async subprocess.

    Args:
        project_root: Path to the project root
        project_type: Type of project (python, rust)
        config: Project configuration
        timeout: Timeout in seconds
        verbose: Enable verbose output

    Returns:
        CITestResult object with execution details
    """
    start_time = time.time()

    # Build command based on configuration
    cmd_parts = config["test_command"].split()
    cmd = []

    # Add environment variables
    env = os.environ.copy()
    if config.get("env"):
        env.update(config["env"])

    # Build the command
    for part in cmd_parts:
        cmd.append(part)

    # For Python, respect pytest configuration
    if project_type == "python" and config["test_tool"] == "pytest":
        # Load pytest configuration
        pytest_config = load_pytest_config(project_root)

        # Don't add verbose flag if it's already in pytest config
        if verbose and "-v" not in cmd and "--verbose" not in cmd:
            if not pytest_config.get("verbose"):
                cmd.append("-v")

        # Add coverage if requested
        if config.get("coverage"):
            # Check if coverage is already configured
            if "--cov" not in cmd:
                cmd.extend(["--cov", "--cov-report=term-missing"])
                if config.get("coverage_threshold"):
                    cmd.extend(["--cov-fail-under", str(config["coverage_threshold"])])

    elif project_type == "rust" and verbose:
        cmd.append("--verbose")

    # Add extra arguments
    if config.get("extra_args"):
        cmd.extend(config["extra_args"])

    # Add test paths only if specified and not using native discovery
    if config.get("test_paths") and not config.get("use_native_discovery", False):
        cmd.extend(config["test_paths"])

    try:
        # Use async subprocess for better control
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=project_root,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        exit_code = proc.returncode
        stdout = stdout_bytes.decode(errors="replace").strip()
        stderr = stderr_bytes.decode(errors="replace").strip()

        duration = time.time() - start_time

        # Parse pytest output if applicable
        summary = None
        if project_type == "python" and "pytest" in config["test_tool"]:
            summary = parse_pytest_output(stdout + "\n" + stderr)

        return CITestResult(
            test_type=project_type,
            command=" ".join(cmd),
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=duration,
            success=exit_code == 0,
            summary=summary,
        )

    except asyncio.TimeoutError:
        duration = time.time() - start_time
        return CITestResult(
            test_type=project_type,
            command=" ".join(cmd),
            exit_code=124,  # Standard timeout exit code
            stdout="",
            stderr=f"Test execution timed out after {timeout} seconds",
            duration=duration,
            success=False,
        )
    except Exception as e:
        duration = time.time() - start_time
        return CITestResult(
            test_type=project_type,
            command=" ".join(cmd),
            exit_code=1,
            stdout="",
            stderr=f"Error executing tests: {e}",
            duration=duration,
            success=False,
        )


# --- Output Display Helpers ---
def should_show_output(
    show_output: str, test_result: CITestResult, config: CIConfig
) -> bool:
    """Determine if test output should be shown based on configuration."""
    if config.json_output:
        return False

    if show_output == "always":
        return True
    elif show_output == "never":
        return False
    elif show_output == "on-failure":
        return not test_result.success
    elif show_output == "smart":
        # Show on failure or if there's important information
        if not test_result.success:
            return True
        if test_result.summary:
            # Show if there are warnings, skipped tests, or low coverage
            if test_result.summary.warnings > 0 or test_result.summary.skipped > 0:
                return True
            if (
                test_result.summary.coverage_percent is not None
                and test_result.summary.coverage_percent < 80
            ):
                return True
        return config.verbose

    return False


def display_test_output(
    test_result: CITestResult, project_type: str, project_name: str = ""
) -> None:
    """Display test output in a user-friendly format."""
    project_info = f" in {project_name}" if project_name else ""

    if test_result.success:
        # For successful tests, show a summary if we have pytest data
        if test_result.summary and test_result.summary.total > 0:
            print(
                f"\n{ANSI['G']}✓ {project_type} tests passed{project_info}:{ANSI['N']}"
            )

            # Show test counts
            parts = []
            if test_result.summary.passed > 0:
                parts.append(
                    f"{ANSI['G']}{test_result.summary.passed} passed{ANSI['N']}"
                )
            if test_result.summary.skipped > 0:
                parts.append(
                    f"{ANSI['Y']}{test_result.summary.skipped} skipped{ANSI['N']}"
                )
            if test_result.summary.warnings > 0:
                parts.append(
                    f"{ANSI['Y']}{test_result.summary.warnings} warnings{ANSI['N']}"
                )

            print(f"  {' · '.join(parts)} in {test_result.summary.duration:.2f}s")

            # Show coverage if available
            if test_result.summary.coverage_percent is not None:
                coverage_color = (
                    ANSI["G"]
                    if test_result.summary.coverage_percent >= 80
                    else ANSI["Y"]
                )
                print(
                    f"  Coverage: {coverage_color}{test_result.summary.coverage_percent:.1f}%{ANSI['N']}"
                )

            # Show warnings or important info from output
            if test_result.summary.warnings > 0 and test_result.stdout:
                # Extract warning section
                warning_section = re.search(
                    r"=+ warnings summary =+(.+?)(?:=+ |$)",
                    test_result.stdout,
                    re.DOTALL,
                )
                if warning_section:
                    print(f"\n{ANSI['Y']}Warnings:{ANSI['N']}")
                    warning_lines = (
                        warning_section.group(1).strip().split("\n")[:5]
                    )  # Show first 5
                    for line in warning_lines:
                        print(f"  {line}")
                    if len(warning_lines) < test_result.summary.warnings:
                        print(
                            f"  ... and {test_result.summary.warnings - len(warning_lines)} more"
                        )
        else:
            # Fallback to simple output
            print(test_result.stdout)
    else:
        # For failed tests, show full output
        print(f"\n{ANSI['R']}✗ {project_type} tests failed{project_info}:{ANSI['N']}")
        print(f"Command: {test_result.command}")

        if test_result.summary and test_result.summary.total > 0:
            # Show failure summary
            parts = []
            if test_result.summary.failed > 0:
                parts.append(
                    f"{ANSI['R']}{test_result.summary.failed} failed{ANSI['N']}"
                )
            if test_result.summary.errors > 0:
                parts.append(
                    f"{ANSI['R']}{test_result.summary.errors} errors{ANSI['N']}"
                )
            if test_result.summary.passed > 0:
                parts.append(
                    f"{ANSI['G']}{test_result.summary.passed} passed{ANSI['N']}"
                )

            print(f"  {' · '.join(parts)}")

        # Show output
        if test_result.stdout:
            print(f"\n{test_result.stdout}")
        if test_result.stderr:
            print(f"\n{ANSI['R']}Errors:{ANSI['N']}\n{test_result.stderr}")


# --- Output Formatting ---
def format_output(
    result: CIResult, json_output: bool = False, verbose: bool = False
) -> str:
    """
    Format the CI result for output.

    Args:
        result: CIResult object
        json_output: Whether to format as JSON
        verbose: Whether to include verbose details

    Returns:
        Formatted output string
    """
    if json_output:
        output_data = {
            "status": "success" if result.overall_success else "failure",
            "project_root": str(result.project_root),
            "total_duration": result.total_duration,
            "discovered_projects": result.discovered_projects,
            "test_results": [
                {
                    "test_type": tr.test_type,
                    "command": tr.command,
                    "exit_code": tr.exit_code,
                    "success": tr.success,
                    "duration": tr.duration,
                    "project_path": tr.project_path,
                    "stdout": tr.stdout if verbose else "",
                    "stderr": tr.stderr if verbose else "",
                    "summary": tr.summary.__dict__ if tr.summary else None,
                }
                for tr in result.test_results
            ],
            "nested_results": result.nested_results,
        }
        return json.dumps(output_data, indent=2)

    # Human-readable format
    lines = []

    # Header
    header = f"{ANSI['BOLD']}khive ci{ANSI['N']} - Test Results"
    lines.append(f"\n{header}")
    lines.append("=" * 50)

    # Summary statistics
    total_tests = sum(
        tr.summary.total if tr.summary else 0 for tr in result.test_results
    )
    total_passed = sum(
        tr.summary.passed if tr.summary else (1 if tr.success else 0)
        for tr in result.test_results
    )
    total_failed = sum(
        tr.summary.failed if tr.summary else (0 if tr.success else 1)
        for tr in result.test_results
    )
    total_skipped = sum(
        tr.summary.skipped if tr.summary else 0 for tr in result.test_results
    )

    if total_tests > 0:
        status_color = ANSI["G"] if result.overall_success else ANSI["R"]
        status_icon = "✓" if result.overall_success else "✗"
        lines.append(
            f"\n{status_color}{status_icon} Overall Status: {'SUCCESS' if result.overall_success else 'FAILURE'}{ANSI['N']}"
        )

        # Test summary
        summary_parts = []
        if total_passed > 0:
            summary_parts.append(f"{ANSI['G']}{total_passed} passed{ANSI['N']}")
        if total_failed > 0:
            summary_parts.append(f"{ANSI['R']}{total_failed} failed{ANSI['N']}")
        if total_skipped > 0:
            summary_parts.append(f"{ANSI['Y']}{total_skipped} skipped{ANSI['N']}")

        lines.append(f"   {' · '.join(summary_parts)} in {result.total_duration:.2f}s")

        # Coverage summary if available
        coverage_results = [
            tr.summary.coverage_percent
            for tr in result.test_results
            if tr.summary and tr.summary.coverage_percent is not None
        ]
        if coverage_results:
            avg_coverage = sum(coverage_results) / len(coverage_results)
            coverage_color = ANSI["G"] if avg_coverage >= 80 else ANSI["Y"]
            lines.append(f"   Coverage: {coverage_color}{avg_coverage:.1f}%{ANSI['N']}")

    # Discovered projects (only in verbose mode)
    if verbose and result.discovered_projects:
        lines.append("\nDiscovered Projects:")
        for project_type, config in result.discovered_projects.items():
            lines.append(f"  • {project_type.title()}: {config['test_command']}")
            if config.get("test_paths"):
                lines.append(f"    Test paths: {', '.join(config['test_paths'])}")

    # Test results details (only show failures in non-verbose mode)
    if not verbose and result.test_results:
        failed_tests = [tr for tr in result.test_results if not tr.success]
        if failed_tests:
            lines.append("\nFailed Tests:")
            for test_result in failed_tests:
                project_info = (
                    f" [{test_result.project_path}]" if test_result.project_path else ""
                )
                lines.append(
                    f"  {ANSI['R']}✗{ANSI['N']} {test_result.test_type}{project_info}"
                )
                if test_result.summary and test_result.summary.failures:
                    for failure in test_result.summary.failures[
                        :3
                    ]:  # Show first 3 failures
                        lines.append(f"    - {failure}")

    # Nested results
    if result.nested_results:
        lines.append("\nNested Projects:")
        for nested in result.nested_results:
            status = "✓" if nested["status"] == "success" else "✗"
            color = ANSI["G"] if nested["status"] == "success" else ANSI["R"]
            lines.append(f"  {color}{status}{ANSI['N']} {nested['directory']}")

    lines.append("")  # Empty line at end
    return "\n".join(lines)


# --- Main CI Function ---
async def run_ci_async(
    project_root: Path,
    json_output: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    test_type: str = "all",
    timeout: int = 300,
) -> int:
    """
    Run continuous integration checks with async support and nested configurations.

    Args:
        project_root: Path to the project root
        json_output: Output results in JSON format
        dry_run: Show what would be done without executing
        verbose: Enable verbose output
        test_type: Type of tests to run (python, rust, all)
        timeout: Timeout for test execution

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Create args namespace for config loading
    args = argparse.Namespace(
        json_output=json_output,
        dry_run=dry_run,
        verbose=verbose,
        timeout=timeout,
    )

    config = load_ci_config(project_root, args)

    # Check for custom CI script first
    custom_result = await check_and_run_custom_ci_script(config)
    if custom_result is not None:
        output = format_output(custom_result, json_output=json_output, verbose=verbose)
        print(output)
        return 0 if custom_result.overall_success else 1

    result = CIResult(project_root=project_root)

    try:
        # First, find and process all nested directories with their own CI configs
        nested_dirs = []
        for ci_config in project_root.rglob(".khive/ci.toml"):
            if ci_config.parent.parent != project_root:  # Skip root .khive
                nested_dirs.append(ci_config.parent.parent)

        # Sort by depth to process parent directories before children
        nested_dirs.sort(key=lambda p: len(p.parts))

        # Process nested directories
        processed_dirs = set()
        for nested_dir in nested_dirs:
            # Skip if this directory is inside an already processed directory
            skip = False
            for processed in processed_dirs:
                try:
                    nested_dir.relative_to(processed)
                    skip = True
                    break
                except ValueError:
                    continue

            if not skip:
                nested_result = await run_ci_for_nested_directory(
                    nested_dir, config, args
                )
                if nested_result:
                    result.nested_results.append(nested_result)
                    processed_dirs.add(nested_dir)

                    # Update overall success based on nested results
                    if nested_result["status"] not in ["success", "skipped", "dry_run"]:
                        result.overall_success = False

                    # Add duration
                    result.total_duration += nested_result.get("duration", 0)

        # Discover projects in root (excluding nested directories)
        discovered_projects = detect_project_types(project_root, config)
        result.discovered_projects = discovered_projects

        # Execute tests for root-level projects
        if discovered_projects:
            # Filter projects based on test_type
            if test_type != "all":
                discovered_projects = {
                    k: v for k, v in discovered_projects.items() if k == test_type
                }

            # Validate tools
            tool_availability = validate_test_tools(discovered_projects)
            missing_tools = [
                project_type
                for project_type, available in tool_availability.items()
                if not available
            ]

            if missing_tools:
                error_msg = f"Missing required tools for: {', '.join(missing_tools)}"
                if json_output:
                    output_data = {
                        "status": "error",
                        "message": error_msg,
                        "missing_tools": missing_tools,
                        "nested_results": result.nested_results,
                    }
                    print(json.dumps(output_data, indent=2))
                else:
                    print(f"Error: {error_msg}", file=sys.stderr)
                return 1

            if dry_run:
                if json_output:
                    output_data = {
                        "status": "dry_run",
                        "discovered_projects": discovered_projects,
                        "would_execute": [
                            f"{proj_config['test_command']} for {proj_type}"
                            for proj_type, proj_config in discovered_projects.items()
                        ],
                        "nested_results": result.nested_results,
                    }
                    print(json.dumps(output_data, indent=2))
                else:
                    print("Dry run - would execute:")
                    for proj_type, proj_config in discovered_projects.items():
                        print(f"  • {proj_config['test_command']} for {proj_type}")
                    if result.nested_results:
                        print("\nNested projects:")
                        for nested in result.nested_results:
                            print(f"  • {nested['directory']}")
                return 0

            # Execute tests for root projects
            for proj_type, proj_config in discovered_projects.items():
                if not verbose and not json_output:
                    print(f"{ANSI['B']}Running {proj_type} tests...{ANSI['N']}")

                test_result = await execute_tests_async(
                    project_root=project_root,
                    project_type=proj_type,
                    config=proj_config,
                    timeout=proj_config.get("timeout", timeout),
                    verbose=verbose,
                )

                result.add_test_result(test_result)

                # Show test output based on configuration
                show_output = proj_config.get("show_output", "smart")
                should_show = should_show_output(show_output, test_result, config)

                if should_show and not json_output:
                    display_test_output(test_result, proj_type)

        # Handle case where no tests were found anywhere
        if not result.test_results and not result.nested_results:
            if json_output:
                output_data = {
                    "status": "no_tests",
                    "message": "No test projects discovered",
                    "project_root": str(project_root),
                }
                print(json.dumps(output_data, indent=2))
            else:
                print(
                    "No test projects discovered in the current directory or subdirectories."
                )
            return 0

        # Output results
        output = format_output(result, json_output=json_output, verbose=verbose)
        print(output)

        return 0 if result.overall_success else 1

    except Exception as e:
        error_msg = f"CI execution failed: {e}"
        if json_output:
            output_data = {"status": "error", "message": error_msg, "exit_code": 1}
            print(json.dumps(output_data, indent=2))
        else:
            print(f"Error: {error_msg}", file=sys.stderr)
        return 1


# --- CLI Entry Point ---
def main() -> None:
    """
    Main entry point for the khive ci command.
    """
    parser = argparse.ArgumentParser(
        description="Run continuous integration checks with nested configuration support."
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Path to the project root directory (default: current working directory).",
    )

    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output results in JSON format.",
    )

    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be done without actually running tests.",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging.",
    )

    parser.add_argument(
        "--test-type",
        choices=["python", "rust", "all"],
        default="all",
        help="Specify which test types to run (default: all).",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout for test execution in seconds (default: 300).",
    )

    args = parser.parse_args()
    global verbose_mode
    verbose_mode = args.verbose

    try:
        # Resolve project root path
        project_root = args.project_root.resolve()
        if not project_root.is_dir():
            error_msg = (
                f"Project root does not exist or is not a directory: {project_root}"
            )
            if args.json_output:
                result = {"status": "error", "message": error_msg, "exit_code": 1}
                print(json.dumps(result, indent=2))
            else:
                print(f"Error: {error_msg}", file=sys.stderr)
            sys.exit(1)

        # Run the CI command with async support
        exit_code = asyncio.run(
            run_ci_async(
                project_root=project_root,
                json_output=args.json_output,
                dry_run=args.dry_run,
                verbose=args.verbose,
                test_type=args.test_type,
                timeout=args.timeout,
            )
        )

        sys.exit(exit_code)

    except KeyboardInterrupt:
        if args.json_output:
            result = {
                "status": "interrupted",
                "message": "Command interrupted by user",
                "exit_code": 130,
            }
            print(json.dumps(result, indent=2))
        else:
            print("\nCommand interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        if args.json_output:
            result = {"status": "error", "message": error_msg, "exit_code": 1}
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {error_msg}", file=sys.stderr)
        sys.exit(1)


def cli_entry() -> None:
    """Entry point for khive CLI integration."""
    main()


if __name__ == "__main__":
    main()
