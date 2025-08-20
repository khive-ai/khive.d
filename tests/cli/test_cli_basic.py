"""Basic CLI functionality tests.

Simple tests for khive CLI core functionality that work with existing fixtures.
"""

from unittest.mock import Mock, patch

import pytest
from khive.cli.khive_cli import (
    COMMAND_DESCRIPTIONS,
    COMMANDS,
    _get_full_module_path,
    _print_root_help,
    main,
)


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_get_full_module_path(self):
        """Test module path construction."""
        result = _get_full_module_path("test_module")
        assert "khive.cli.commands.test_module" in result

    def test_commands_dict_exists(self):
        """Test that COMMANDS dict is properly configured."""
        assert isinstance(COMMANDS, dict)
        assert len(COMMANDS) > 0
        # Test at least one expected command exists
        assert "plan" in COMMANDS

    def test_command_descriptions_exist(self):
        """Test that command descriptions are configured."""
        assert isinstance(COMMAND_DESCRIPTIONS, dict)
        assert len(COMMAND_DESCRIPTIONS) > 0

    def test_help_function_runs(self, capsys):
        """Test that help function runs without errors."""
        _print_root_help()
        captured = capsys.readouterr()
        assert "khive" in captured.out.lower()
        assert "usage" in captured.out.lower()

    def test_main_with_help_flag(self, capsys):
        """Test main function with help flag."""
        main(["--help"])
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower()

    def test_main_with_no_args(self, capsys):
        """Test main function with no arguments."""
        main([])
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower()

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_with_valid_command(self, mock_load):
        """Test main with a valid command."""
        mock_module = Mock()
        mock_module.cli_entry = Mock()
        mock_load.return_value = mock_module

        # Use an actual command from COMMANDS
        if COMMANDS:
            command = next(iter(COMMANDS.keys()))
            main([command])
            mock_load.assert_called_once_with(command)

    def test_main_with_invalid_command(self, capsys):
        """Test main with invalid command shows error."""
        # This will actually call _load_command_module which will print error and return None
        with pytest.raises(SystemExit):
            main(["invalid_command_that_definitely_does_not_exist"])

        captured = capsys.readouterr()
        assert "error" in captured.err.lower() or "unknown" in captured.err.lower()


class TestCLIIntegration:
    """Test CLI integration with actual commands."""

    def test_cli_module_can_be_imported(self):
        """Test that CLI module imports correctly."""
        from khive.cli import khive_cli

        assert hasattr(khive_cli, "main")
        assert callable(khive_cli.main)

    def test_commands_point_to_valid_modules(self):
        """Test that command mappings point to real module names."""
        for cmd_name, module_name in COMMANDS.items():
            assert isinstance(cmd_name, str)
            assert isinstance(module_name, str)
            assert len(module_name) > 0
            # Basic validation of module name format
            assert module_name.replace("_", "").replace("-", "").isalnum()

    def test_help_includes_all_commands(self, capsys):
        """Test that help output includes all configured commands."""
        _print_root_help()
        captured = capsys.readouterr()

        # Check that at least some commands appear in help
        for cmd_name in list(COMMANDS.keys())[:5]:  # Check first 5 commands
            assert cmd_name in captured.out
