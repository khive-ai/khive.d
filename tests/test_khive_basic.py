"""
Basic unit tests for the khive package.
"""

import importlib
import sys
from pathlib import Path


def test_khive_package_imports():
    """Test that the khive package can be imported."""
    import khive

    assert khive is not None


def test_khive_cli_imports():
    """Test that CLI modules can be imported."""
    from khive.cli import khive_cli

    assert khive_cli is not None


def test_project_structure():
    """Test that the project has expected structure."""
    project_root = Path(__file__).parent.parent

    # Check key files exist
    assert (project_root / "pyproject.toml").exists()
    assert (project_root / "src" / "khive").exists()
    assert (project_root / "src" / "khive" / "cli").exists()


def test_github_workflows():
    """Test that GitHub workflows exist."""
    project_root = Path(__file__).parent.parent
    workflows_dir = project_root / ".github" / "workflows"

    assert workflows_dir.exists()
    assert (workflows_dir / "ci.yml").exists()


def test_tests_directory():
    """Test that tests directory has expected structure."""
    project_root = Path(__file__).parent.parent
    tests_dir = project_root / "tests"

    assert tests_dir.exists()
    assert (tests_dir / "unit").exists()
    assert (tests_dir / "integration").exists()
    assert (tests_dir / "performance").exists()
    assert (tests_dir / "conftest.py").exists()
    assert (tests_dir / "README.md").exists()
