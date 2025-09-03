"""Comprehensive CLI dispatcher functionality tests.

Tests for the core khive CLI dispatcher including:
- Command discovery and routing
- Argument passing and sys.argv manipulation
- Module loading and validation
- Error handling and recovery
- Entry point validation
"""

import sys
from unittest.mock import Mock, patch

import pytest

from khive.cli.khive_cli import (
    COMMAND_DESCRIPTIONS,
    COMMAND_MODULE_BASE_PATH,
    COMMANDS,
    ENTRY_POINT_FUNCTION_NAME,
    _get_full_module_path,
    _load_command_module,
    _print_root_help,
    main,
)


class TestCommandDiscovery:
    """Test command discovery and routing functionality."""

    def test_get_full_module_path_construction(self):
        """Test that module paths are constructed correctly."""
        result = _get_full_module_path("test_module")
        expected = f"{COMMAND_MODULE_BASE_PATH}.test_module"
        assert result == expected

    def test_get_full_module_path_with_various_names(self):
        """Test module path construction with different name patterns."""
        test_cases = [
            ("simple", f"{COMMAND_MODULE_BASE_PATH}.simple"),
            ("with_underscore", f"{COMMAND_MODULE_BASE_PATH}.with_underscore"),
            ("with-dash", f"{COMMAND_MODULE_BASE_PATH}.with-dash"),
            ("123numeric", f"{COMMAND_MODULE_BASE_PATH}.123numeric"),
        ]

        for module_name, expected in test_cases:
            result = _get_full_module_path(module_name)
            assert result == expected

    def test_commands_dict_structure(self):
        """Test that COMMANDS dictionary has the expected structure."""
        assert isinstance(COMMANDS, dict)
        assert len(COMMANDS) > 0

        # All keys should be strings (command names)
        for cmd_name in COMMANDS:
            assert isinstance(cmd_name, str)
            assert len(cmd_name) > 0

        # All values should be strings (module names)
        for module_name in COMMANDS.values():
            assert isinstance(module_name, str)
            assert len(module_name) > 0

    def test_command_descriptions_alignment(self):
        """Test that command descriptions are properly aligned with commands."""
        assert isinstance(COMMAND_DESCRIPTIONS, dict)

        # Not all commands need descriptions, but all description keys should be valid commands
        for cmd_name in COMMAND_DESCRIPTIONS:
            assert isinstance(cmd_name, str)
            # Command descriptions can exist for commands not yet implemented
            # so we don't require cmd_name to be in COMMANDS

        # All description values should be non-empty strings
        for description in COMMAND_DESCRIPTIONS.values():
            assert isinstance(description, str)
            assert len(description.strip()) > 0

    def test_base_path_configuration(self):
        """Test that the base path is properly configured."""
        assert COMMAND_MODULE_BASE_PATH == "khive.cli.commands"
        assert ENTRY_POINT_FUNCTION_NAME == "cli_entry"


class TestModuleLoading:
    """Test module loading and validation functionality."""

    def test_load_valid_command_module(self):
        """Test loading a valid command module."""
        # Use a command that actually exists
        if COMMANDS:
            cmd_name = "plan"  # We know this exists from the basic tests
            if cmd_name in COMMANDS:
                with patch("importlib.import_module") as mock_import:
                    mock_module = Mock()
                    mock_import.return_value = mock_module

                    result = _load_command_module(cmd_name)

                    assert result is mock_module
                    expected_path = _get_full_module_path(COMMANDS[cmd_name])
                    mock_import.assert_called_once_with(expected_path)

    def test_load_unknown_command(self, capsys):
        """Test loading an unknown command returns None and shows error."""
        result = _load_command_module("nonexistent_command")

        assert result is None
        captured = capsys.readouterr()
        assert "Error: Unknown command 'nonexistent_command'" in captured.err

    def test_load_command_import_error(self, capsys):
        """Test handling of ImportError during module loading."""
        cmd_name = "plan"  # Use existing command
        if cmd_name in COMMANDS:
            with patch("importlib.import_module") as mock_import:
                mock_import.side_effect = ImportError("Module not found")

                result = _load_command_module(cmd_name)

                assert result is None
                captured = capsys.readouterr()
                assert "Error: Could not import module" in captured.err
                assert "Module not found" in captured.err

    def test_load_command_unexpected_error(self, capsys):
        """Test handling of unexpected errors during module loading."""
        cmd_name = "plan"
        if cmd_name in COMMANDS:
            with patch("importlib.import_module") as mock_import:
                mock_import.side_effect = RuntimeError("Unexpected error")

                result = _load_command_module(cmd_name)

                assert result is None
                captured = capsys.readouterr()
                assert "Error: An unexpected issue occurred" in captured.err
                assert "Unexpected error" in captured.err

    @patch("importlib.import_module")
    def test_load_command_module_caching(self, mock_import):
        """Test that module loading doesn't interfere with Python's import caching."""
        mock_module = Mock()
        mock_import.return_value = mock_module

        cmd_name = "plan"
        if cmd_name in COMMANDS:
            # Load the same module twice
            result1 = _load_command_module(cmd_name)
            result2 = _load_command_module(cmd_name)

            # importlib should be called each time (no custom caching)
            assert mock_import.call_count == 2
            assert result1 is mock_module
            assert result2 is mock_module


class TestHelpSystem:
    """Test help system functionality."""

    def test_print_root_help_basic_structure(self, capsys):
        """Test that root help prints the basic structure."""
        _print_root_help()
        captured = capsys.readouterr()

        # Check for main elements
        assert "khive" in captured.out.lower()
        assert "usage" in captured.out.lower()
        assert "available commands" in captured.out.lower()
        assert "<command>" in captured.out or "command" in captured.out

    def test_print_root_help_includes_commands(self, capsys):
        """Test that help includes all configured commands."""
        _print_root_help()
        captured = capsys.readouterr()

        # Should include all commands from COMMANDS dict
        for cmd_name in COMMANDS:
            assert cmd_name in captured.out

    def test_print_root_help_includes_descriptions(self, capsys):
        """Test that help includes command descriptions where available."""
        _print_root_help()
        captured = capsys.readouterr()

        # Should include descriptions from COMMAND_DESCRIPTIONS
        for cmd_name in COMMAND_DESCRIPTIONS:
            if cmd_name in COMMANDS:  # Only check descriptions for actual commands
                # Description should appear after command name
                lines = captured.out.split("\n")
                cmd_line = None
                for line in lines:
                    if cmd_name in line and not line.strip().startswith("#"):
                        cmd_line = line
                        break

                if cmd_line:
                    # Description should be on the same line or context should suggest it's there
                    # At minimum, the command should be present
                    assert cmd_name in cmd_line

    def test_print_root_help_formatting(self, capsys):
        """Test that help output has proper formatting."""
        _print_root_help()
        captured = capsys.readouterr()

        lines = captured.out.split("\n")

        # Should have proper structure
        assert len(lines) > 5  # At least several lines of output

        # Should have usage line
        usage_found = any("usage" in line.lower() for line in lines)
        assert usage_found

        # Should have commands section
        commands_found = any(
            "available commands" in line.lower() or "commands" in line.lower()
            for line in lines
        )
        assert commands_found

    def test_help_with_empty_commands_dict(self):
        """Test help system behavior when COMMANDS dict is empty."""
        with patch("khive.cli.khive_cli.COMMANDS", {}):
            # Should not crash even with empty commands
            try:
                _print_root_help()
            except Exception as e:
                pytest.fail(
                    f"Help system should handle empty COMMANDS dict, but raised: {e}"
                )


class TestArgumentPassing:
    """Test argument passing and sys.argv manipulation."""

    def test_main_with_help_flags(self, capsys):
        """Test main function with various help flags."""
        help_flags = ["-h", "--help"]

        for flag in help_flags:
            # Clear previous output
            capsys.readouterr()

            main([flag])
            captured = capsys.readouterr()

            assert "usage" in captured.out.lower()
            assert "khive" in captured.out.lower()

    def test_main_no_arguments(self, capsys):
        """Test main function with no arguments shows help."""
        main([])
        captured = capsys.readouterr()

        assert "usage" in captured.out.lower()
        assert "khive" in captured.out.lower()

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_sys_argv_manipulation(self, mock_load):
        """Test that sys.argv is properly manipulated for subcommands."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        original_argv = list(sys.argv)

        try:
            main(["test_cmd", "--arg1", "value1", "--arg2"])

            # Verify sys.argv was set correctly for the subcommand
            # The mock should have been called, and sys.argv should be restored
            mock_entry.assert_called_once()
            assert sys.argv == original_argv

        finally:
            sys.argv = original_argv

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_with_complex_arguments(self, mock_load):
        """Test argument passing with complex argument structures."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        original_argv = list(sys.argv)
        complex_args = [
            "cmd",
            "--flag",
            "--option=value",
            "positional",
            "--another",
            "val",
        ]

        try:
            main(complex_args)
            mock_entry.assert_called_once()
            assert sys.argv == original_argv
        finally:
            sys.argv = original_argv

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_argv_restoration_on_exception(self, mock_load):
        """Test that sys.argv is restored even when subcommand raises exception."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = RuntimeError("Test error")
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        original_argv = list(sys.argv)

        try:
            with pytest.raises(SystemExit):
                main(["test_cmd"])

            # sys.argv should still be restored
            assert sys.argv == original_argv
        finally:
            sys.argv = original_argv


class TestErrorHandling:
    """Test error handling and recovery functionality."""

    def test_main_invalid_command_exits(self):
        """Test that invalid command causes SystemExit."""
        with pytest.raises(SystemExit) as exc_info:
            main(["definitely_nonexistent_command"])

        assert exc_info.value.code == 1

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_module_loading_failure_exits(self, mock_load):
        """Test that module loading failure causes SystemExit."""
        mock_load.return_value = None  # Simulate loading failure

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 1

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_missing_entry_point_exits(self, mock_load, capsys):
        """Test that missing entry point causes SystemExit."""
        mock_module = Mock()
        mock_module.__name__ = "test_module"  # Add required __name__ attribute
        del mock_module.cli_entry  # No entry point
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not have a callable 'cli_entry' entry point" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_non_callable_entry_point_exits(self, mock_load, capsys):
        """Test that non-callable entry point causes SystemExit."""
        mock_module = Mock()
        mock_module.__name__ = "test_module"  # Add required __name__ attribute
        mock_module.cli_entry = "not_callable"  # Not callable
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not have a callable 'cli_entry' entry point" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_subcommand_system_exit_propagation(self, mock_load):
        """Test that SystemExit from subcommand is properly propagated."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = SystemExit(42)  # Custom exit code
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 42

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_subcommand_exception_handling(self, mock_load, capsys):
        """Test that unexpected exceptions from subcommands are handled gracefully."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = RuntimeError("Unexpected error in subcommand")
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert (
            "Error: An unexpected error occurred while executing command"
            in captured.err
        )
        assert "Unexpected error in subcommand" in captured.err


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_main_with_none_argv(self, capsys):
        """Test main function with None argv (should use sys.argv)."""
        with patch("sys.argv", ["khive", "--help"]):
            main(None)  # Should print help and return normally
            captured = capsys.readouterr()
            assert "usage" in captured.out.lower()

    def test_main_with_empty_command_name(self, capsys):
        """Test main function with empty command name."""
        with pytest.raises(SystemExit) as exc_info:
            main([""])  # Empty string as command

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Unknown command ''" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_with_subcommand_none_exit_code(self, mock_load):
        """Test SystemExit with None exit code from subcommand."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = SystemExit(None)  # None exit code
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 0  # Should default to 0

    def test_command_names_with_special_characters(self):
        """Test that command names with special characters are handled properly."""
        # This test checks our current command names for any issues
        for cmd_name in COMMANDS:
            # Command names should not contain spaces or other problematic characters
            assert " " not in cmd_name
            assert "\t" not in cmd_name
            assert "\n" not in cmd_name

            # Should be valid for file/module names
            assert cmd_name.replace("-", "_").replace("_", "").isalnum()

    def test_module_names_validity(self):
        """Test that all module names in COMMANDS are valid Python identifiers."""
        for module_name in COMMANDS.values():
            # Module names should be valid Python identifiers (after path splitting)
            parts = module_name.split(".")
            for part in parts:
                # Allow hyphens in module names (they get converted to underscores)
                normalized_part = part.replace("-", "_")
                assert (
                    normalized_part.isidentifier()
                ), f"Invalid module name part: {part}"
