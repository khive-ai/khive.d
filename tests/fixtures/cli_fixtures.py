"""CLI testing fixtures and utilities."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner():
    """CLI runner for testing Click-based commands."""
    return CliRunner()


@pytest.fixture
def mock_git_commands():
    """Mock git command execution."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "mock output"
        mock_run.return_value.stderr = ""
        yield mock_run


@pytest.fixture
def sample_khive_config():
    """Sample khive configuration for CLI testing."""
    return {
        "version": "0.4.0",
        "cli": {"default_branch": "main", "auto_commit": True, "verbose": False},
        "services": {"mcp_timeout": 30, "max_retries": 3},
    }


@pytest.fixture
def cli_temp_project(tmp_path: Path):
    """Create temporary project structure for CLI testing."""
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Create basic project structure
    src_dir = project_root / "src"
    src_dir.mkdir()

    tests_dir = project_root / "tests"
    tests_dir.mkdir()

    # Create pyproject.toml
    pyproject = project_root / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "test-project"
version = "0.1.0"
"""
    )

    return project_root
