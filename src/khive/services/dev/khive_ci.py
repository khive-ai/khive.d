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

CLI
---
    khive ci [--test-type python|rust|all] [--timeout 300] [--dry-run] [--verbose] [--json-output]

Exit codes: 0 success · 1 failure.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from khive.cli.base import (
    CLIResult,
    CommandWorkflow,
    ConfigurableCLICommand,
    WorkflowStep,
    cli_command,
)
from khive.utils import (
    ANSI,
    BaseConfig,
    check_tool_available,
    info_msg,
    print_step,
    warn_msg,
)


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

    # Parse test results line
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


# --- Configuration Classes ---
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
    use_native_discovery: bool = True
    show_output: str = "smart"  # always/never/smart/on-failure


@dataclass
class CIConfig(BaseConfig):
    """CI-specific configuration."""

    timeout: int = 300
    test_configs: dict[str, TestConfig] = field(default_factory=dict)
    enabled_tests: list[str] = field(default_factory=list)
    test_type: str = "all"  # CLI argument


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
    summary: PytestSummary | None = None


@dataclass
class CIExecutionResult:
    """Overall CI execution result."""

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


# --- CI Command Implementation ---
@cli_command("ci")
class CICommand(ConfigurableCLICommand):
    """Run continuous integration checks with nested configuration support."""

    def __init__(self):
        super().__init__(
            command_name="ci",
            description="Run continuous integration checks with nested configuration support",
        )
        self._execution_result: Optional[CIExecutionResult] = None

    @property
    def config_filename(self) -> str:
        return "ci.toml"

    @property
    def default_config(self) -> Dict[str, Any]:
        return {
            "timeout": 300,
            "enable": ["python", "rust"],
            "tests": {
                "python": {
                    "command": "pytest",
                    "tool": "pytest",
                    "use_native_discovery": True,
                    "show_output": "smart",
                },
                "rust": {
                    "command": "cargo test",
                    "tool": "cargo",
                    "show_output": "smart",
                },
            },
        }

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add CI-specific arguments."""
        parser.add_argument(
            "--test-type",
            choices=["python", "rust", "all"],
            default="all",
            help="Specify which test types to run (default: all)",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            help="Timeout for test execution in seconds (default: from config or 300)",
        )

    def _create_config(self, args: argparse.Namespace) -> CIConfig:
        """Create CI configuration from arguments and config files."""
        # Load configuration from file
        config_data = self._load_command_config(args.project_root)

        # Create base config
        config = CIConfig(
            project_root=args.project_root,
            timeout=args.timeout or config_data.get("timeout", 300),
            enabled_tests=config_data.get("enable", ["python", "rust"]),
            test_type=args.test_type,
        )

        # Load test configurations
        test_configs = config_data.get("tests", {})
        for test_type, test_data in test_configs.items():
            config.test_configs[test_type] = TestConfig(
                test_command=test_data.get("command", ""),
                test_tool=test_data.get("tool", ""),
                test_paths=test_data.get("paths", []),
                timeout=test_data.get("timeout"),
                coverage=test_data.get("coverage", False),
                coverage_threshold=test_data.get("coverage_threshold", 80.0),
                extra_args=test_data.get("extra_args", []),
                env=test_data.get("env", {}),
                use_native_discovery=test_data.get("use_native_discovery", True),
                show_output=test_data.get("show_output", "smart"),
            )

        # Update from CLI args
        config.update_from_cli_args(args)

        return config

    def _execute(self, args: argparse.Namespace, config: CIConfig) -> CLIResult:
        """Execute the CI command using async runner."""
        # Run async CI logic
        try:
            self._execution_result = asyncio.run(self._run_ci_async(config))

            # Convert to CLIResult
            if self._execution_result.overall_success:
                return CLIResult(
                    status="success",
                    message=self._format_summary_message(),
                    data=self._format_result_data(),
                )
            else:
                return CLIResult(
                    status="failure",
                    message=self._format_failure_message(),
                    data=self._format_result_data(),
                    exit_code=1,
                )

        except Exception as e:
            return CLIResult(
                status="error",
                message=f"CI execution failed: {e}",
                exit_code=1,
            )

    async def _run_ci_async(self, config: CIConfig) -> CIExecutionResult:
        """Run CI checks asynchronously."""
        result = CIExecutionResult(project_root=config.project_root)

        # Create workflow
        workflow = CommandWorkflow("CI Pipeline")
        workflow.add_step(
            WorkflowStep("check_custom_script", "Checking for custom CI script")
        )
        workflow.add_step(
            WorkflowStep("discover_projects", "Discovering test projects")
        )
        workflow.add_step(WorkflowStep("validate_tools", "Validating required tools"))
        workflow.add_step(WorkflowStep("execute_tests", "Executing tests"))
        workflow.add_step(
            WorkflowStep("process_nested", "Processing nested projects", required=False)
        )

        # Step 1: Check for custom CI script
        custom_result = await self._check_custom_script(config)
        if custom_result:
            return custom_result

        # Step 2: Discover projects
        discovered_projects = self._discover_projects(config.project_root, config)
        result.discovered_projects = discovered_projects

        # Filter by test type
        if config.test_type != "all":
            discovered_projects = {
                k: v for k, v in discovered_projects.items() if k == config.test_type
            }

        if not discovered_projects and not config.dry_run:
            # Check for nested projects before giving up
            nested_results = await self._process_nested_projects(config)
            if nested_results:
                result.nested_results = nested_results
                result.overall_success = all(
                    r["status"] in ["success", "skipped", "dry_run"]
                    for r in nested_results
                )
                return result

        # Step 3: Validate tools
        if discovered_projects:
            missing_tools = self._validate_tools(discovered_projects)
            if missing_tools:
                raise Exception(f"Missing required tools: {', '.join(missing_tools)}")

        # Step 4: Execute tests (if not dry run)
        if config.dry_run:
            info_msg("[DRY-RUN] Would execute tests")
        else:
            # Execute root-level tests
            for proj_type, proj_config in discovered_projects.items():
                print_step(f"Running {proj_type} tests", "running")

                test_result = await self._execute_test_async(
                    config.project_root,
                    proj_type,
                    proj_config,
                    proj_config.get("timeout", config.timeout),
                    config.verbose,
                )

                result.add_test_result(test_result)

                # Show output based on configuration
                if self._should_show_output(
                    proj_config.get("show_output", "smart"), test_result, config
                ):
                    self._display_test_output(test_result, proj_type)

                print_step(
                    f"{proj_type} tests",
                    "success" if test_result.success else "failure",
                )

        # Step 5: Process nested projects
        nested_results = await self._process_nested_projects(config)
        if nested_results:
            result.nested_results = nested_results
            # Update overall success
            for nested in nested_results:
                if nested["status"] not in ["success", "skipped", "dry_run"]:
                    result.overall_success = False

        return result

    async def _check_custom_script(
        self, config: CIConfig
    ) -> Optional[CIExecutionResult]:
        """Check for and execute custom CI script."""
        script_path = config.khive_config_dir / "scripts" / "khive_ci.sh"

        if not script_path.exists():
            return None

        # Verify executable
        if not os.access(script_path, os.X_OK):
            warn_msg(
                f"Custom CI script exists but is not executable. Run: chmod +x {script_path}"
            )
            return None

        info_msg(f"Using custom CI script: {script_path}")

        # Prepare environment
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
        cmd = [str(script_path)]
        if config.dry_run:
            cmd.append("--dry-run")
        if config.verbose:
            cmd.append("--verbose")
        if config.json_output:
            cmd.append("--json-output")
        cmd.extend(["--timeout", str(config.timeout)])

        if config.dry_run:
            info_msg(f"[DRY-RUN] Would execute: {' '.join(cmd)}")
            result = CIExecutionResult(project_root=config.project_root)
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

        # Execute script
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

            # Create result
            result = CIExecutionResult(project_root=config.project_root)
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

            return result

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            result = CIExecutionResult(project_root=config.project_root)
            result.overall_success = False
            result.test_results.append(
                CITestResult(
                    test_type="custom_script",
                    command=" ".join(cmd),
                    exit_code=124,
                    stdout="",
                    stderr=f"Timeout after {config.timeout} seconds",
                    duration=duration,
                    success=False,
                )
            )
            return result

    def _discover_projects(
        self, project_root: Path, config: CIConfig
    ) -> Dict[str, Dict[str, Any]]:
        """Discover test projects in the given directory."""
        projects = {}

        # Check for Python project
        if (project_root / "pyproject.toml").exists() or (
            project_root / "setup.py"
        ).exists():
            python_config = config.test_configs.get("python")
            if python_config:
                projects["python"] = {
                    "test_command": python_config.test_command,
                    "test_tool": python_config.test_tool,
                    "test_paths": python_config.test_paths or [],
                    "timeout": python_config.timeout,
                    "coverage": python_config.coverage,
                    "coverage_threshold": python_config.coverage_threshold,
                    "extra_args": python_config.extra_args,
                    "env": python_config.env,
                    "use_native_discovery": python_config.use_native_discovery,
                    "show_output": python_config.show_output,
                }

        # Check for Rust project
        if (project_root / "Cargo.toml").exists():
            rust_config = config.test_configs.get("rust")
            if rust_config:
                projects["rust"] = {
                    "test_command": rust_config.test_command,
                    "test_tool": rust_config.test_tool,
                    "test_paths": rust_config.test_paths or [],
                    "timeout": rust_config.timeout,
                    "extra_args": rust_config.extra_args,
                    "env": rust_config.env,
                    "show_output": rust_config.show_output,
                }

        # Filter by enabled tests
        if config.enabled_tests:
            projects = {k: v for k, v in projects.items() if k in config.enabled_tests}

        return projects

    def _validate_tools(self, projects: Dict[str, Dict[str, Any]]) -> List[str]:
        """Validate that required tools are available."""
        missing_tools = []
        for project_type, config in projects.items():
            tool = config["test_tool"]
            if not check_tool_available(tool):
                missing_tools.append(tool)
        return missing_tools

    async def _execute_test_async(
        self,
        project_root: Path,
        project_type: str,
        config: Dict[str, Any],
        timeout: int,
        verbose: bool,
    ) -> CITestResult:
        """Execute tests asynchronously."""
        start_time = time.time()

        # Build command
        cmd_parts = config["test_command"].split()
        cmd = []

        # Add environment variables
        env = os.environ.copy()
        if config.get("env"):
            env.update(config["env"])

        # Build the command
        for part in cmd_parts:
            cmd.append(part)

        # Add verbose flag if needed
        if verbose and project_type == "python" and "-v" not in cmd:
            cmd.append("-v")
        elif verbose and project_type == "rust":
            cmd.append("--verbose")

        # Add coverage for Python
        if project_type == "python" and config.get("coverage"):
            if "--cov" not in cmd:
                cmd.extend(["--cov", "--cov-report=term-missing"])
                if config.get("coverage_threshold"):
                    cmd.extend(["--cov-fail-under", str(config["coverage_threshold"])])

        # Add extra arguments
        if config.get("extra_args"):
            cmd.extend(config["extra_args"])

        # Add test paths
        if config.get("test_paths") and not config.get("use_native_discovery", False):
            cmd.extend(config["test_paths"])

        try:
            # Execute tests
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

            # Parse pytest output
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
                exit_code=124,
                stdout="",
                stderr=f"Test execution timed out after {timeout} seconds",
                duration=duration,
                success=False,
            )

    async def _process_nested_projects(self, config: CIConfig) -> List[Dict[str, Any]]:
        """Process nested projects with their own CI configurations."""
        nested_results = []

        # Find nested CI configs
        nested_dirs = []
        for ci_config in config.project_root.rglob(".khive/ci.toml"):
            if ci_config.parent.parent != config.project_root:
                nested_dirs.append(ci_config.parent.parent)

        # Sort by depth
        nested_dirs.sort(key=lambda p: len(p.parts))

        # Process each nested directory
        processed_dirs = set()
        for nested_dir in nested_dirs:
            # Skip if inside already processed directory
            skip = False
            for processed in processed_dirs:
                try:
                    nested_dir.relative_to(processed)
                    skip = True
                    break
                except ValueError:
                    continue

            if not skip:
                info_msg(
                    f"Processing nested project: {nested_dir.relative_to(config.project_root)}"
                )

                # Create new config for nested directory
                nested_config = CIConfig(
                    project_root=nested_dir,
                    timeout=config.timeout,
                    json_output=config.json_output,
                    dry_run=config.dry_run,
                    verbose=config.verbose,
                    test_type=config.test_type,
                )

                # Run CI for nested directory
                nested_result = await self._run_ci_async(nested_config)

                # Convert to result dict
                nested_results.append({
                    "directory": str(nested_dir.relative_to(config.project_root)),
                    "status": (
                        "success" if nested_result.overall_success else "failure"
                    ),
                    "test_results": [
                        {
                            "test_type": tr.test_type,
                            "command": tr.command,
                            "exit_code": tr.exit_code,
                            "success": tr.success,
                            "duration": tr.duration,
                        }
                        for tr in nested_result.test_results
                    ],
                    "duration": nested_result.total_duration,
                })

                processed_dirs.add(nested_dir)

        return nested_results

    def _should_show_output(
        self, show_output: str, test_result: CITestResult, config: CIConfig
    ) -> bool:
        """Determine if test output should be shown."""
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
                if test_result.summary.warnings > 0 or test_result.summary.skipped > 0:
                    return True
                if (
                    test_result.summary.coverage_percent is not None
                    and test_result.summary.coverage_percent < 80
                ):
                    return True
            return config.verbose

        return False

    def _display_test_output(
        self, test_result: CITestResult, project_type: str, project_name: str = ""
    ) -> None:
        """Display test output in a user-friendly format."""
        project_info = f" in {project_name}" if project_name else ""

        if test_result.success and test_result.summary:
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
        elif not test_result.success:
            print(
                f"\n{ANSI['R']}✗ {project_type} tests failed{project_info}:{ANSI['N']}"
            )
            if test_result.stdout:
                print(test_result.stdout)
            if test_result.stderr:
                print(f"\n{ANSI['R']}Errors:{ANSI['N']}\n{test_result.stderr}")

    def _format_summary_message(self) -> str:
        """Format success summary message."""
        if not self._execution_result:
            return "CI completed"

        # Calculate totals
        total_tests = sum(
            tr.summary.total if tr.summary else 0
            for tr in self._execution_result.test_results
        )

        if total_tests > 0:
            return f"All tests passed ({total_tests} tests in {self._execution_result.total_duration:.2f}s)"
        else:
            return "CI completed successfully"

    def _format_failure_message(self) -> str:
        """Format failure summary message."""
        if not self._execution_result:
            return "CI failed"

        failed_types = [
            tr.test_type for tr in self._execution_result.test_results if not tr.success
        ]

        if failed_types:
            return f"CI failed: {', '.join(failed_types)} tests failed"
        else:
            return "CI failed"

    def _format_result_data(self) -> Dict[str, Any]:
        """Format execution result as data dictionary."""
        if not self._execution_result:
            return {}

        return {
            "total_duration": self._execution_result.total_duration,
            "discovered_projects": self._execution_result.discovered_projects,
            "test_results": [
                {
                    "test_type": tr.test_type,
                    "command": tr.command,
                    "exit_code": tr.exit_code,
                    "success": tr.success,
                    "duration": tr.duration,
                    "summary": tr.summary.__dict__ if tr.summary else None,
                }
                for tr in self._execution_result.test_results
            ],
            "nested_results": self._execution_result.nested_results,
        }


# --- CLI Entry Point ---
def cli_entry() -> None:
    """Entry point for khive CLI integration."""
    command = CICommand()
    sys.exit(command.run())


if __name__ == "__main__":
    cli_entry()
