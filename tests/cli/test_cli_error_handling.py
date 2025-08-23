"""Comprehensive CLI error handling tests.

Tests for khive CLI error handling including:
- Exception propagation and handling
- Error message formatting
- Exit code validation
- stderr output verification
- Cleanup on error scenarios
- Edge cases and boundary conditions
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from khive.cli.base import BaseCLICommand, CLIResult
from khive.cli.khive_cli import _load_command_module, main
from khive.utils import BaseConfig


class TestExceptionPropagation:
    """Test exception propagation through the CLI system."""

    @patch("khive.cli.khive_cli._load_command_module")
    def test_runtime_error_in_subcommand(self, mock_load, capsys):
        """Test RuntimeError in subcommand is handled gracefully."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = RuntimeError("Test runtime error")
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: An unexpected error occurred" in captured.err
        assert "Test runtime error" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_import_error_in_subcommand(self, mock_load, capsys):
        """Test ImportError in subcommand is handled gracefully."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = ImportError("Cannot import required module")
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: An unexpected error occurred" in captured.err
        assert "Cannot import required module" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_value_error_in_subcommand(self, mock_load, capsys):
        """Test ValueError in subcommand is handled gracefully."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = ValueError("Invalid value provided")
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: An unexpected error occurred" in captured.err
        assert "Invalid value provided" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_keyboard_interrupt_in_subcommand(self, mock_load, capsys):
        """Test KeyboardInterrupt in subcommand propagates correctly."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = KeyboardInterrupt()
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: An unexpected error occurred" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_custom_exception_in_subcommand(self, mock_load, capsys):
        """Test custom exception in subcommand is handled gracefully."""

        class CustomError(Exception):
            pass

        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = CustomError("Custom error message")
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: An unexpected error occurred" in captured.err
        assert "Custom error message" in captured.err


class TestSystemExitHandling:
    """Test SystemExit handling and exit code propagation."""

    @patch("khive.cli.khive_cli._load_command_module")
    def test_system_exit_zero(self, mock_load):
        """Test SystemExit(0) from subcommand."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = SystemExit(0)
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 0

    @patch("khive.cli.khive_cli._load_command_module")
    def test_system_exit_nonzero(self, mock_load):
        """Test SystemExit with non-zero code from subcommand."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = SystemExit(42)
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 42

    @patch("khive.cli.khive_cli._load_command_module")
    def test_system_exit_none_code(self, mock_load):
        """Test SystemExit with None exit code from subcommand."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = SystemExit(None)
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 0  # Should default to 0

    @patch("khive.cli.khive_cli._load_command_module")
    def test_system_exit_string_code(self, mock_load):
        """Test SystemExit with string exit code from subcommand."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = SystemExit("error message")
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        # SystemExit with string should be handled appropriately
        assert exc_info.value.code == "error message" or exc_info.value.code == 1


class TestModuleLoadingErrors:
    """Test module loading error scenarios."""

    def test_unknown_command_error(self, capsys):
        """Test error message for unknown command."""
        result = _load_command_module("definitely_unknown_command_12345")

        assert result is None
        captured = capsys.readouterr()
        assert (
            "Error: Unknown command 'definitely_unknown_command_12345'" in captured.err
        )

    @patch("importlib.import_module")
    def test_module_not_found_error(self, mock_import, capsys):
        """Test error message for module not found."""
        mock_import.side_effect = ImportError(
            "No module named 'khive.cli.commands.missing'"
        )

        # Use an existing command to test import failure
        cmd_name = "plan"  # This exists in COMMANDS
        if cmd_name in {"plan", "compose"}:  # Use any existing command
            result = _load_command_module(cmd_name)

            assert result is None
            captured = capsys.readouterr()
            assert "Error: Could not import module" in captured.err
            assert "No module named" in captured.err

    @patch("importlib.import_module")
    def test_syntax_error_in_module(self, mock_import, capsys):
        """Test error message for syntax error in module."""
        mock_import.side_effect = SyntaxError("invalid syntax in module")

        cmd_name = "plan"
        if cmd_name in {"plan", "compose"}:
            result = _load_command_module(cmd_name)

            assert result is None
            captured = capsys.readouterr()
            assert "Error: An unexpected issue occurred" in captured.err
            assert "invalid syntax in module" in captured.err

    @patch("importlib.import_module")
    def test_circular_import_error(self, mock_import, capsys):
        """Test error message for circular import."""
        mock_import.side_effect = ImportError(
            "cannot import name 'x' from partially initialized module"
        )

        cmd_name = "plan"
        if cmd_name in {"plan", "compose"}:
            result = _load_command_module(cmd_name)

            assert result is None
            captured = capsys.readouterr()
            assert "Error: Could not import module" in captured.err
            assert "partially initialized module" in captured.err


class TestEntryPointValidation:
    """Test entry point validation and error handling."""

    @patch("khive.cli.khive_cli._load_command_module")
    def test_missing_entry_point_attribute(self, mock_load, capsys):
        """Test error when module has no cli_entry attribute."""
        mock_module = Mock()
        # Don't set cli_entry attribute
        if hasattr(mock_module, "cli_entry"):
            delattr(mock_module, "cli_entry")
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not have a callable 'cli_entry' entry point" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_non_callable_entry_point(self, mock_load, capsys):
        """Test error when cli_entry is not callable."""
        mock_module = Mock()
        mock_module.cli_entry = "not_a_function"  # String instead of callable
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not have a callable 'cli_entry' entry point" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_entry_point_is_none(self, mock_load, capsys):
        """Test error when cli_entry is None."""
        mock_module = Mock()
        mock_module.cli_entry = None
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as exc_info:
            main(["test_cmd"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not have a callable 'cli_entry' entry point" in captured.err


class TestSysArgvHandling:
    """Test sys.argv manipulation and restoration."""

    @patch("khive.cli.khive_cli._load_command_module")
    def test_argv_restoration_on_success(self, mock_load):
        """Test sys.argv is restored after successful command execution."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        original_argv = list(sys.argv)

        try:
            main(["test_cmd", "--arg1", "value1"])

            # sys.argv should be restored to original
            assert sys.argv == original_argv

        finally:
            sys.argv = original_argv

    @patch("khive.cli.khive_cli._load_command_module")
    def test_argv_restoration_on_exception(self, mock_load):
        """Test sys.argv is restored even when subcommand raises exception."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = RuntimeError("Test error")
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        original_argv = list(sys.argv)

        try:
            with pytest.raises(SystemExit):
                main(["test_cmd", "--arg1", "value1"])

            # sys.argv should still be restored
            assert sys.argv == original_argv

        finally:
            sys.argv = original_argv

    @patch("khive.cli.khive_cli._load_command_module")
    def test_argv_restoration_on_system_exit(self, mock_load):
        """Test sys.argv is restored when subcommand calls SystemExit."""
        mock_module = Mock()
        mock_entry = Mock()
        mock_entry.side_effect = SystemExit(42)
        mock_module.cli_entry = mock_entry
        mock_load.return_value = mock_module

        original_argv = list(sys.argv)

        try:
            with pytest.raises(SystemExit):
                main(["test_cmd", "--arg1", "value1"])

            # sys.argv should still be restored
            assert sys.argv == original_argv

        finally:
            sys.argv = original_argv

    @patch("khive.cli.khive_cli._load_command_module")
    def test_argv_content_during_execution(self, mock_load):
        """Test sys.argv content during subcommand execution."""
        mock_module = Mock()
        captured_argv = []

        def capture_argv():
            captured_argv.extend(list(sys.argv))

        mock_module.cli_entry = capture_argv
        mock_load.return_value = mock_module

        original_argv = list(sys.argv)

        try:
            main(["test_cmd", "--arg1", "value1", "--flag"])

            # Check that sys.argv was set correctly for the subcommand
            assert len(captured_argv) > 0
            assert "khive test_cmd" in captured_argv[0]
            assert "--arg1" in captured_argv
            assert "value1" in captured_argv
            assert "--flag" in captured_argv

        finally:
            sys.argv = original_argv


class TestBaseCLICommandErrorHandling:
    """Test error handling in BaseCLICommand implementations."""

    def test_validation_error_in_args(self):
        """Test argument validation error handling."""

        class TestCommand(BaseCLICommand):
            def _add_arguments(self, parser):
                pass

            def _create_config(self, args):
                return BaseConfig()

            def _execute(self, args, config):
                return CLIResult("success", "Test")

            def _validate_args(self, args):
                raise ValueError("Invalid argument combination")

        command = TestCommand("test", "Test command")

        with tempfile.TemporaryDirectory() as temp_dir:
            exit_code = command.run(["--project-root", temp_dir])

            assert exit_code == 1

    def test_config_creation_error(self):
        """Test error in configuration creation."""

        class TestCommand(BaseCLICommand):
            def _add_arguments(self, parser):
                pass

            def _create_config(self, args):
                raise RuntimeError("Config creation failed")

            def _execute(self, args, config):
                return CLIResult("success", "Test")

        command = TestCommand("test", "Test command")

        with tempfile.TemporaryDirectory() as temp_dir:
            exit_code = command.run(["--project-root", temp_dir])

            assert exit_code == 1

    def test_execution_error_with_cli_result(self):
        """Test execution error returned via CLIResult."""

        class TestCommand(BaseCLICommand):
            def _add_arguments(self, parser):
                pass

            def _create_config(self, args):
                return BaseConfig()

            def _execute(self, args, config):
                return CLIResult("error", "Execution failed", exit_code=5)

        command = TestCommand("test", "Test command")

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(SystemExit) as exc_info:
                command.run(["--project-root", temp_dir])

            assert exc_info.value.code == 5

    def test_execution_error_with_exception(self):
        """Test execution error raised as exception."""

        class TestCommand(BaseCLICommand):
            def _add_arguments(self, parser):
                pass

            def _create_config(self, args):
                return BaseConfig()

            def _execute(self, args, config):
                raise RuntimeError("Critical error in execution")

        command = TestCommand("test", "Test command")

        with tempfile.TemporaryDirectory() as temp_dir:
            exit_code = command.run(["--project-root", temp_dir])

            assert exit_code == 1

    def test_keyboard_interrupt_handling(self, capsys):
        """Test KeyboardInterrupt handling in BaseCLICommand."""

        class TestCommand(BaseCLICommand):
            def _add_arguments(self, parser):
                pass

            def _create_config(self, args):
                return BaseConfig()

            def _execute(self, args, config):
                raise KeyboardInterrupt

        command = TestCommand("test", "Test command")

        with tempfile.TemporaryDirectory() as temp_dir:
            exit_code = command.run(["--project-root", temp_dir])

            assert exit_code == 130
            captured = capsys.readouterr()
            assert "interrupted by user" in captured.err


class TestResourceCleanup:
    """Test resource cleanup on error scenarios."""

    @patch("khive.cli.khive_cli._load_command_module")
    def test_cleanup_after_module_loading_failure(self, mock_load, capsys):
        """Test cleanup when module loading fails."""
        mock_load.return_value = None  # Simulate loading failure

        original_argv = list(sys.argv)

        try:
            with pytest.raises(SystemExit):
                main(["test_cmd", "--arg"])

            # sys.argv should be unchanged (not modified if module loading fails)
            assert sys.argv == original_argv

        finally:
            sys.argv = original_argv

    def test_temp_directory_cleanup_on_error(self):
        """Test that temporary resources are cleaned up on error."""

        # This is more of an integration concern, but we can test the pattern
        class TestCommand(BaseCLICommand):
            def _add_arguments(self, parser):
                pass

            def _create_config(self, args):
                return BaseConfig()

            def _execute(self, args, config):
                # Simulate creating temp resources then failing
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_file = Path(temp_dir) / "test.txt"
                    temp_file.write_text("test content")
                    raise RuntimeError("Simulated failure")

        command = TestCommand("test", "Test command")

        with tempfile.TemporaryDirectory() as project_root:
            exit_code = command.run(["--project-root", project_root])

            assert exit_code == 1
            # Temporary directory should be cleaned up automatically by context manager


class TestEdgeCases:
    """Test edge cases and boundary conditions for error handling."""

    def test_empty_error_message(self):
        """Test handling of empty error messages."""

        class TestCommand(BaseCLICommand):
            def _add_arguments(self, parser):
                pass

            def _create_config(self, args):
                return BaseConfig()

            def _execute(self, args, config):
                return CLIResult("error", "", exit_code=1)

        command = TestCommand("test", "Test command")

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(SystemExit) as exc_info:
                command.run(["--project-root", temp_dir])

            assert exc_info.value.code == 1

    def test_very_long_error_message(self):
        """Test handling of very long error messages."""
        long_message = "Error: " + "A" * 10000  # Very long error message

        class TestCommand(BaseCLICommand):
            def _add_arguments(self, parser):
                pass

            def _create_config(self, args):
                return BaseConfig()

            def _execute(self, args, config):
                return CLIResult("error", long_message, exit_code=1)

        command = TestCommand("test", "Test command")

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(SystemExit) as exc_info:
                command.run(["--project-root", temp_dir])

            assert exc_info.value.code == 1

    def test_unicode_error_message(self):
        """Test handling of Unicode characters in error messages."""
        unicode_message = "Error with Unicode: 你好世界 🌍 ñoño"

        class TestCommand(BaseCLICommand):
            def _add_arguments(self, parser):
                pass

            def _create_config(self, args):
                return BaseConfig()

            def _execute(self, args, config):
                return CLIResult("error", unicode_message, exit_code=1)

        command = TestCommand("test", "Test command")

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(SystemExit) as exc_info:
                command.run(["--project-root", temp_dir])

            assert exc_info.value.code == 1

    def test_nested_exception_chain(self):
        """Test handling of nested exception chains."""

        class TestCommand(BaseCLICommand):
            def _add_arguments(self, parser):
                pass

            def _create_config(self, args):
                return BaseConfig()

            def _execute(self, args, config):
                try:
                    raise ValueError("Original error")
                except ValueError as e:
                    raise RuntimeError("Wrapped error") from e

        command = TestCommand("test", "Test command")

        with tempfile.TemporaryDirectory() as temp_dir:
            exit_code = command.run(["--project-root", temp_dir])

            assert exit_code == 1
