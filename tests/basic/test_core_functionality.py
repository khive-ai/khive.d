"""Unit tests for core khive functionality."""

from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestKhiveCLI:
    """Test khive CLI functionality."""

    def test_cli_module_exists(self):
        """Test that CLI module exists and has expected attributes."""
        from khive.cli import khive_cli

        assert hasattr(khive_cli, "main")

    def test_cli_help_command(self):
        """Test CLI help functionality."""
        from khive.cli.khive_cli import main

        # Test that main function exists and is callable
        assert callable(main)

    @patch("sys.argv", ["khive", "--help"])
    def test_cli_help_output(self):
        """Test that help command works without crashing."""
        from khive.cli import khive_cli

        # This should not raise an exception
        try:
            khive_cli.main()
        except SystemExit as e:
            # Help command exits with code 0, which is expected
            assert e.code == 0


@pytest.mark.unit
class TestKhiveServices:
    """Test khive service components."""

    def test_service_imports(self):
        """Test that service modules can be imported."""
        # Test that services exist and are importable - let ImportError propagate naturally
        from khive import _types, utils

        # Test that imported modules have expected attributes
        assert hasattr(_types, "BaseModel")
        assert hasattr(utils, "KHIVE_CONFIG_DIR")

    def test_basic_types_import(self):
        """Test that basic types can be imported."""
        from khive._types import BaseModel

        assert BaseModel is not None


@pytest.mark.unit
class TestConfiguration:
    """Test configuration handling."""

    def test_project_structure(self, sample_project_dir):
        """Test basic project structure validation."""
        # Test that our sample project has expected structure
        assert sample_project_dir.exists()
        assert (sample_project_dir / "src").exists()
        assert (sample_project_dir / "pyproject.toml").exists()
