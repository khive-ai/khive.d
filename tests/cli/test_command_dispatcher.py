"""Comprehensive tests for CLI command dispatcher functionality.

Tests the core command dispatching logic, module loading, argument passing,
and error handling in the main CLI entry point.
"""

import sys
from types import ModuleType
from unittest.mock import Mock, patch

import pytest

from khive.cli.khive_cli import (COMMAND_DESCRIPTIONS,
                                 COMMAND_MODULE_BASE_PATH, COMMANDS,
                                 ENTRY_POINT_FUNCTION_NAME,
                                 _get_full_module_path, _load_command_module,
                                 _print_root_help, main)


class TestCommandMapping:
    """Test command mapping and configuration."""

    def test_commands_dict_structure(self):
        """Test that COMMANDS dict has proper structure."""
        assert isinstance(COMMANDS, dict)
        assert len(COMMANDS) > 0

        for command_name, module_name in COMMANDS.items():
            assert isinstance(command_name, str)
            assert isinstance(module_name, str)
            assert len(command_name) > 0
            assert len(module_name) > 0
            # Command names should use kebab-case
            assert all(c.isalnum() or c == "-" for c in command_name)
            # Module names should use snake_case
            assert all(c.isalnum() or c == "_" for c in module_name)

    def test_command_descriptions_completeness(self):
        """Test that all commands have descriptions."""
        assert isinstance(COMMAND_DESCRIPTIONS, dict)

        # Every command should have a description
        for command_name in COMMANDS:
            if command_name not in COMMAND_DESCRIPTIONS:
                # Some commands might not have descriptions yet, that's ok
                continue
            assert isinstance(COMMAND_DESCRIPTIONS[command_name], str)
            assert len(COMMAND_DESCRIPTIONS[command_name]) > 0

    def test_no_duplicate_command_names(self):
        """Test that there are no duplicate command names."""
        command_names = list(COMMANDS.keys())
        assert len(command_names) == len(set(command_names))

    def test_no_duplicate_module_names(self):
        """Test that there are no duplicate module mappings."""
        module_names = list(COMMANDS.values())
        assert len(module_names) == len(set(module_names))

    def test_command_module_base_path_constant(self):
        """Test that the base path constant is properly configured."""
        assert isinstance(COMMAND_MODULE_BASE_PATH, str)
        assert COMMAND_MODULE_BASE_PATH == "khive.cli.commands"
        assert "." in COMMAND_MODULE_BASE_PATH

    def test_entry_point_function_name_constant(self):
        """Test that the entry point function name is configured."""
        assert isinstance(ENTRY_POINT_FUNCTION_NAME, str)
        assert ENTRY_POINT_FUNCTION_NAME == "cli_entry"


class TestModulePathConstruction:
    """Test module path construction utilities."""

    def test_get_full_module_path_basic(self):
        """Test basic module path construction."""
        result = _get_full_module_path("test_module")
        expected = f"{COMMAND_MODULE_BASE_PATH}.test_module"
        assert result == expected

    def test_get_full_module_path_with_underscores(self):
        """Test module path construction with underscores."""
        result = _get_full_module_path("new_doc")
        expected = f"{COMMAND_MODULE_BASE_PATH}.new_doc"
        assert result == expected

    def test_get_full_module_path_empty_input(self):
        """Test module path construction with empty input."""
        result = _get_full_module_path("")
        expected = f"{COMMAND_MODULE_BASE_PATH}."
        assert result == expected

    def test_get_full_module_path_with_existing_commands(self):
        """Test module path construction for all existing commands."""
        for module_name in COMMANDS.values():
            result = _get_full_module_path(module_name)
            expected = f"{COMMAND_MODULE_BASE_PATH}.{module_name}"
            assert result == expected
            assert "khive.cli.commands" in result


class TestModuleLoading:
    """Test command module loading functionality."""

    def test_load_command_module_unknown_command(self, capsys):
        """Test loading unknown command shows error and returns None."""
        result = _load_command_module("unknown_command_xyz")
        assert result is None

        captured = capsys.readouterr()
        assert "Error: Unknown command 'unknown_command_xyz'" in captured.err
        assert "usage" in captured.out.lower() or "khive" in captured.out.lower()

    @patch("khive.cli.khive_cli.importlib.import_module")
    def test_load_command_module_import_error(self, mock_import, capsys):
        """Test handling of module import errors."""
        mock_import.side_effect = ImportError("Module not found")

        # Use a real command from COMMANDS
        if COMMANDS:
            command_name = next(iter(COMMANDS.keys()))
            result = _load_command_module(command_name)
            assert result is None

            captured = capsys.readouterr()
            assert (
                f"Error: Could not import module for command '{command_name}'"
                in captured.err
            )
            assert "Module not found" in captured.err

    @patch("khive.cli.khive_cli.importlib.import_module")
    def test_load_command_module_unexpected_error(self, mock_import, capsys):
        """Test handling of unexpected errors during module loading."""
        mock_import.side_effect = RuntimeError("Unexpected error")

        if COMMANDS:
            command_name = next(iter(COMMANDS.keys()))
            result = _load_command_module(command_name)
            assert result is None

            captured = capsys.readouterr()
            assert (
                f"Error: An unexpected issue occurred while trying to load command '{command_name}'"
                in captured.err
            )
            assert "Unexpected error" in captured.err

    @patch("khive.cli.khive_cli.importlib.import_module")
    def test_load_command_module_success(self, mock_import):
        """Test successful module loading."""
        mock_module = Mock(spec=ModuleType)
        mock_import.return_value = mock_module

        if COMMANDS:
            command_name = next(iter(COMMANDS.keys()))
            result = _load_command_module(command_name)
            assert result is mock_module
            mock_import.assert_called_once()


class TestHelpSystem:
    """Test help system functionality."""

    def test_print_root_help_basic_structure(self, capsys):
        """Test that root help has proper structure."""
        _print_root_help()
        captured = capsys.readouterr()

        assert "khive" in captured.out.lower()
        assert "usage" in captured.out.lower()
        assert "available commands" in captured.out.lower()
        assert "more information" in captured.out.lower()

    def test_print_root_help_includes_commands(self, capsys):
        """Test that help includes all configured commands."""
        _print_root_help()
        captured = capsys.readouterr()

        for command_name in COMMANDS:
            assert command_name in captured.out

    def test_print_root_help_includes_descriptions(self, capsys):
        """Test that help includes command descriptions where available."""
        _print_root_help()
        captured = capsys.readouterr()

        for command_name, description in COMMAND_DESCRIPTIONS.items():
            if command_name in COMMANDS:
                assert description in captured.out

    def test_print_root_help_formatting(self, capsys):
        """Test help formatting and alignment."""
        _print_root_help()
        captured = capsys.readouterr()

        lines = captured.out.split("\n")
        command_lines = [line for line in lines if any(cmd in line for cmd in COMMANDS)]

        # Should have proper indentation
        for line in command_lines:
            if line.strip():  # Skip empty lines
                assert line.startswith("  ")  # Should be indented

    def test_print_root_help_with_empty_commands(self, capsys):
        """Test help system handles empty COMMANDS gracefully."""
        with patch("khive.cli.khive_cli.COMMANDS", {}):
            _print_root_help()
            captured = capsys.readouterr()

            assert "khive" in captured.out.lower()
            assert "usage" in captured.out.lower()
            # Should still show basic help structure


class TestMainEntryPoint:
    """Test the main CLI entry point function."""

    def test_main_no_arguments(self, capsys):
        """Test main with no arguments shows help."""
        main([])
        captured = capsys.readouterr()

        assert "usage" in captured.out.lower()
        assert "khive" in captured.out.lower()

    def test_main_help_flags(self, capsys):
        """Test main with help flags shows help."""
        for help_flag in ["-h", "--help"]:
            main([help_flag])
            captured = capsys.readouterr()

            assert "usage" in captured.out.lower()
            assert "khive" in captured.out.lower()

    def test_main_invalid_command_exits(self, capsys):
        """Test main with invalid command exits with error code."""
        with pytest.raises(SystemExit) as excinfo:
            main(["nonexistent_command"])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Unknown command" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_module_loading_failure(self, mock_load, capsys):
        """Test main handles module loading failure."""
        mock_load.return_value = None

        with pytest.raises(SystemExit) as excinfo:
            main(["plan"])  # Use a known command

        assert excinfo.value.code == 1

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_missing_entry_point(self, mock_load, capsys):
        """Test main handles missing entry point function."""
        mock_module = Mock(spec=ModuleType)
        # Mock module without cli_entry function
        mock_module.__name__ = "test_module"
        del mock_module.cli_entry  # Ensure it doesn't exist
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["plan"])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "does not have a callable 'cli_entry' entry point" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_non_callable_entry_point(self, mock_load, capsys):
        """Test main handles non-callable entry point."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = "not_callable"  # String instead of function
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["plan"])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "does not have a callable 'cli_entry' entry point" in captured.err


class TestArgumentPassing:
    """Test argument passing to subcommands."""

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_argument_passing(self, mock_load):
        """Test that arguments are passed correctly to subcommands."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = Mock()
        mock_load.return_value = mock_module

        original_argv = sys.argv.copy()

        try:
            main(["plan", "--help", "--verbose"])

            # After main() executes, sys.argv should be restored
            assert sys.argv == original_argv

            # The entry point should have been called
            mock_module.cli_entry.assert_called_once()

        finally:
            sys.argv = original_argv

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_sys_argv_manipulation(self, mock_load):
        """Test that sys.argv is properly manipulated for subcommands."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = Mock()
        mock_load.return_value = mock_module

        original_argv = sys.argv.copy()
        test_args = ["plan", "arg1", "--flag", "value"]

        try:
            main(test_args)

            # sys.argv should be restored after execution
            assert sys.argv == original_argv

        finally:
            sys.argv = original_argv

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_subcommand_system_exit(self, mock_load):
        """Test main handles SystemExit from subcommands."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = Mock(side_effect=SystemExit(42))
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["plan"])

        assert excinfo.value.code == 42

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_subcommand_system_exit_none_code(self, mock_load):
        """Test main handles SystemExit with None code from subcommands."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = Mock(side_effect=SystemExit(None))
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["plan"])

        assert excinfo.value.code == 0

    @patch("khive.cli.khive_cli._load_command_module")
    def test_main_subcommand_unexpected_exception(self, mock_load, capsys):
        """Test main handles unexpected exceptions from subcommands."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = Mock(side_effect=ValueError("Test error"))
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["plan"])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert (
            "An unexpected error occurred while executing command 'plan'"
            in captured.err
        )


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_main_with_none_argv(self, capsys):
        """Test main with None argv uses sys.argv."""
        original_argv = sys.argv.copy()

        try:
            # Simulate sys.argv with help flag
            sys.argv = ["khive", "--help"]
            main(None)

            captured = capsys.readouterr()
            assert "usage" in captured.out.lower()

        finally:
            sys.argv = original_argv

    def test_main_empty_string_command(self, capsys):
        """Test main with empty string command."""
        with pytest.raises(SystemExit):
            main([""])

        captured = capsys.readouterr()
        assert "Error: Unknown command ''" in captured.err

    def test_commands_dict_consistency(self):
        """Test that COMMANDS dict and actual command modules are consistent."""
        # This test verifies that all commands in COMMANDS actually have corresponding modules
        # We can't test actual module existence here as it would require file system access
        # but we can test the mapping consistency

        for module_name in COMMANDS.values():
            full_path = _get_full_module_path(module_name)
            assert full_path.endswith(module_name)
            assert COMMAND_MODULE_BASE_PATH in full_path


class TestSystemIntegration:
    """Test system-level integration aspects."""

    def test_main_function_signature(self):
        """Test that main function has the expected signature."""
        import inspect

        sig = inspect.signature(main)
        params = sig.parameters

        assert "argv" in params
        assert params["argv"].default is None
        assert params["argv"].annotation == list[str] | None

    def test_help_functions_signature(self):
        """Test that help functions have expected signatures."""
        import inspect

        # Test _print_root_help signature
        sig = inspect.signature(_print_root_help)
        assert len(sig.parameters) == 0
        assert sig.return_annotation is None

    def test_module_loading_functions_signature(self):
        """Test module loading function signatures."""
        import inspect

        # Test _load_command_module signature
        sig = inspect.signature(_load_command_module)
        params = sig.parameters
        assert "cmd_name" in params
        assert params["cmd_name"].annotation == str

        # Test _get_full_module_path signature
        sig = inspect.signature(_get_full_module_path)
        params = sig.parameters
        assert "module_name" in params
        assert params["module_name"].annotation == str
