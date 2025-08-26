"""CLI testing fixtures for command-line interface testing."""

import os
import subprocess
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Enhanced CLI runner with isolated filesystem."""
    return CliRunner(mix_stderr=False)


@pytest.fixture
def cli_test_environment(tmp_path: Path) -> Generator[dict[str, Any], None, None]:
    """Provide a complete CLI testing environment."""
    # Create test project structure
    test_project = tmp_path / "test_project"
    test_project.mkdir()

    # Create minimal project files
    (test_project / "pyproject.toml").write_text(
        """
[project]
name = "test-project"
version = "0.1.0"
description = "Test project"
requires-python = ">=3.10"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
    """.strip()
    )

    (test_project / "src").mkdir()
    (test_project / "src" / "test_project").mkdir()
    (test_project / "src" / "test_project" / "__init__.py").write_text("")

    (test_project / "tests").mkdir()
    (test_project / "tests" / "__init__.py").write_text("")

    # Create test environment
    env = {
        "project_root": test_project,
        "src_dir": test_project / "src",
        "tests_dir": test_project / "tests",
        "temp_dir": tmp_path / "temp",
        "config_dir": tmp_path / "config",
        "cache_dir": tmp_path / "cache",
        "log_dir": tmp_path / "logs",
    }

    # Create additional directories
    for dir_path in [
        env["temp_dir"],
        env["config_dir"],
        env["cache_dir"],
        env["log_dir"],
    ]:
        dir_path.mkdir(exist_ok=True)

    # Set up environment variables
    test_env = {
        "KHIVE_TEST_MODE": "true",
        "KHIVE_DISABLE_EXTERNAL_APIS": "true",
        "KHIVE_PROJECT_ROOT": str(test_project),
        "KHIVE_CONFIG_DIR": str(env["config_dir"]),
        "KHIVE_CACHE_DIR": str(env["cache_dir"]),
        "KHIVE_LOG_DIR": str(env["log_dir"]),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(test_project / "src"),
    }

    with patch.dict(os.environ, test_env):
        yield env


@pytest.fixture
def mock_subprocess():
    """Mock subprocess operations for CLI testing."""
    with (
        patch("subprocess.run") as mock_run,
        patch("subprocess.Popen") as mock_popen,
        patch("subprocess.check_output") as mock_output,
    ):
        # Configure default successful responses
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        mock_output.return_value = b"Success"

        # Configure Popen mock
        mock_process = MagicMock()
        mock_process.poll.return_value = 0
        mock_process.communicate.return_value = (b"Success", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        yield {
            "run": mock_run,
            "popen": mock_popen,
            "check_output": mock_output,
            "result": mock_result,
            "process": mock_process,
        }


@pytest.fixture
def git_repo_fixture(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary git repository for testing."""
    repo_path = tmp_path / "git_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo_path, check=True
    )

    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repository")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True)

    yield repo_path


@pytest.fixture
def cli_command_builder():
    """Build CLI commands with proper argument handling."""

    class CommandBuilder:
        def __init__(self):
            self.base_command = ["uv", "run", "khive"]

        def build(self, subcommand: str, *args, **kwargs) -> list[str]:
            """Build a complete CLI command."""
            cmd = self.base_command + [subcommand]

            # Add positional arguments
            cmd.extend(str(arg) for arg in args)

            # Add keyword arguments
            for key, value in kwargs.items():
                key = key.replace("_", "-")
                if value is True:
                    cmd.append(f"--{key}")
                elif value is not False and value is not None:
                    cmd.extend([f"--{key}", str(value)])

            return cmd

        def plan(self, task: str, **kwargs) -> list[str]:
            """Build a plan command."""
            return self.build("plan", task, **kwargs)

        def compose(
            self, role: str, domain: str = None, context: str = None, **kwargs
        ) -> list[str]:
            """Build a compose command."""
            cmd = self.build("compose", role, **kwargs)
            if domain:
                cmd.extend(["-d", domain])
            if context:
                cmd.extend(["-c", context])
            return cmd

        def session(self, action: str, **kwargs) -> list[str]:
            """Build a session command."""
            return self.build("session", action, **kwargs)

    return CommandBuilder()


@pytest.fixture
def cli_output_parser():
    """Parse and validate CLI output."""

    class OutputParser:
        @staticmethod
        def parse_json_output(output: str) -> dict[str, Any]:
            """Parse JSON output from CLI commands."""
            import json

            # Find JSON content in output
            lines = output.strip().split("\n")
            json_lines = []
            in_json = False

            for line in lines:
                if line.strip().startswith("{") or line.strip().startswith("["):
                    in_json = True
                if in_json:
                    json_lines.append(line)
                if in_json and (
                    line.strip().endswith("}") or line.strip().endswith("]")
                ):
                    break

            if json_lines:
                json_text = "\\n".join(json_lines)
                return json.loads(json_text)

            return {}

        @staticmethod
        def extract_sections(output: str) -> dict[str, str]:
            """Extract sections from structured CLI output."""
            sections = {}
            current_section = None
            current_content = []

            for line in output.split("\n"):
                if line.startswith("## ") or line.startswith("# "):
                    # Save previous section
                    if current_section:
                        sections[current_section] = "\\n".join(current_content).strip()

                    # Start new section
                    current_section = line.lstrip("# ").strip()
                    current_content = []
                else:
                    current_content.append(line)

            # Save last section
            if current_section:
                sections[current_section] = "\\n".join(current_content).strip()

            return sections

        @staticmethod
        def validate_success_output(
            output: str, expected_indicators: list[str] = None
        ) -> bool:
            """Validate that output indicates successful execution."""
            if expected_indicators is None:
                expected_indicators = ["✓", "Success", "Complete", "Done"]

            return any(indicator in output for indicator in expected_indicators)

        @staticmethod
        def extract_error_messages(output: str) -> list[str]:
            """Extract error messages from CLI output."""
            errors = []
            lines = output.split("\n")

            for line in lines:
                line = line.strip()
                if any(
                    indicator in line.lower()
                    for indicator in ["error", "failed", "exception"]
                ):
                    errors.append(line)

            return errors

    return OutputParser()


@pytest.fixture
def cli_interaction_simulator():
    """Simulate interactive CLI sessions."""

    class InteractionSimulator:
        def __init__(self):
            self.responses = {}

        def set_response(self, prompt_pattern: str, response: str):
            """Set a response for a prompt pattern."""
            self.responses[prompt_pattern] = response

        def simulate_input(self, prompts: list[str]) -> list[str]:
            """Simulate user input for a series of prompts."""
            responses = []
            for prompt in prompts:
                response = self.find_response(prompt)
                responses.append(response)
            return responses

        def find_response(self, prompt: str) -> str:
            """Find the appropriate response for a prompt."""
            for pattern, response in self.responses.items():
                if pattern in prompt.lower():
                    return response
            return "y"  # Default response

    return InteractionSimulator()
