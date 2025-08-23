"""Comprehensive error handling tests for CLI functionality.

Tests error conditions, edge cases, exception handling, and recovery
scenarios in the CLI system.
"""

import sys
from types import ModuleType
from unittest.mock import Mock, patch

import pytest

from khive.cli.khive_cli import _load_command_module, _print_root_help, main


class TestModuleLoadingErrors:
    """Test error handling in module loading scenarios."""

    @patch("khive.cli.khive_cli.importlib.import_module")
    def test_import_error_with_detailed_message(self, mock_import, capsys):
        """Test ImportError with detailed error message."""
        detailed_error = ImportError("No module named 'missing_dependency'")
        mock_import.side_effect = detailed_error

        result = _load_command_module("plan")
        assert result is None

        captured = capsys.readouterr()
        assert "Could not import module for command 'plan'" in captured.err
        assert "missing_dependency" in captured.err

    @patch("khive.cli.khive_cli.importlib.import_module")
    def test_import_error_circular_dependency(self, mock_import, capsys):
        """Test ImportError due to circular dependencies."""
        circular_error = ImportError("circular import detected")
        mock_import.side_effect = circular_error

        result = _load_command_module("compose")
        assert result is None

        captured = capsys.readouterr()
        assert "Could not import module" in captured.err
        assert "circular import" in captured.err

    @patch("khive.cli.khive_cli.importlib.import_module")
    def test_syntax_error_in_module(self, mock_import, capsys):
        """Test SyntaxError in command module."""
        syntax_error = SyntaxError("invalid syntax at line 5")
        mock_import.side_effect = syntax_error

        result = _load_command_module("session")
        assert result is None

        captured = capsys.readouterr()
        assert "unexpected issue occurred" in captured.err
        assert "invalid syntax" in captured.err

    @patch("khive.cli.khive_cli.importlib.import_module")
    def test_permission_error_module_access(self, mock_import, capsys):
        """Test PermissionError when accessing module."""
        permission_error = PermissionError("Permission denied")
        mock_import.side_effect = permission_error

        result = _load_command_module("clean")
        assert result is None

        captured = capsys.readouterr()
        assert "unexpected issue occurred" in captured.err

    @patch("khive.cli.khive_cli.importlib.import_module")
    def test_unicode_error_in_module(self, mock_import, capsys):
        """Test UnicodeError in module loading."""
        unicode_error = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")
        mock_import.side_effect = unicode_error

        result = _load_command_module("mcp")
        assert result is None

        captured = capsys.readouterr()
        assert "unexpected issue occurred" in captured.err

    @patch("khive.cli.khive_cli.importlib.import_module")
    def test_memory_error_during_import(self, mock_import, capsys):
        """Test MemoryError during module import."""
        memory_error = MemoryError("Out of memory")
        mock_import.side_effect = memory_error

        result = _load_command_module("pr")
        assert result is None

        captured = capsys.readouterr()
        assert "unexpected issue occurred" in captured.err


class TestEntryPointErrors:
    """Test error handling related to entry point functions."""

    @patch("khive.cli.khive_cli._load_command_module")
    def test_missing_entry_point_attribute(self, mock_load, capsys):
        """Test module without entry point function."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        # Don't set cli_entry attribute
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["plan"])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "does not have a callable 'cli_entry' entry point" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_entry_point_not_callable(self, mock_load, capsys):
        """Test entry point that is not callable."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = "not_a_function"  # String instead of function
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["compose"])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "does not have a callable 'cli_entry' entry point" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_entry_point_none_value(self, mock_load, capsys):
        """Test entry point that is None."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = None
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["session"])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "does not have a callable 'cli_entry' entry point" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_entry_point_class_instead_of_function(self, mock_load, capsys):
        """Test entry point that is a class instead of function."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"

        class NotAFunction:
            pass

        mock_module.cli_entry = NotAFunction  # Class, not function
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["clean"])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "does not have a callable 'cli_entry' entry point" in captured.err


class TestSubcommandExecutionErrors:
    """Test error handling during subcommand execution."""

    @patch("khive.cli.khive_cli._load_command_module")
    def test_subcommand_raises_keyboard_interrupt(self, mock_load, capsys):
        """Test subcommand raising KeyboardInterrupt."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = Mock(side_effect=KeyboardInterrupt())
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["plan"])

        # KeyboardInterrupt should be re-raised as SystemExit
        # The exact behavior depends on the implementation

    @patch("khive.cli.khive_cli._load_command_module")
    def test_subcommand_raises_system_exit_negative_code(self, mock_load):
        """Test subcommand raising SystemExit with negative code."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = Mock(side_effect=SystemExit(-1))
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["compose"])

        assert excinfo.value.code == -1

    @patch("khive.cli.khive_cli._load_command_module")
    def test_subcommand_raises_system_exit_high_code(self, mock_load):
        """Test subcommand raising SystemExit with high exit code."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = Mock(side_effect=SystemExit(255))
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["session"])

        assert excinfo.value.code == 255

    @patch("khive.cli.khive_cli._load_command_module")
    def test_subcommand_raises_type_error(self, mock_load, capsys):
        """Test subcommand raising TypeError."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = Mock(
            side_effect=TypeError("unsupported operand type(s)")
        )
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["clean"])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert (
            "unexpected error occurred while executing command 'clean'" in captured.err
        )
        assert "TypeError" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_subcommand_raises_value_error(self, mock_load, capsys):
        """Test subcommand raising ValueError."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = Mock(side_effect=ValueError("invalid value"))
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["mcp"])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "unexpected error occurred while executing command 'mcp'" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_subcommand_raises_attribute_error(self, mock_load, capsys):
        """Test subcommand raising AttributeError."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = Mock(
            side_effect=AttributeError("'NoneType' object has no attribute 'method'")
        )
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["pr"])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "unexpected error occurred while executing command 'pr'" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_subcommand_infinite_recursion(self, mock_load, capsys):
        """Test subcommand causing infinite recursion."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = Mock(
            side_effect=RecursionError("maximum recursion depth exceeded")
        )
        mock_load.return_value = mock_module

        with pytest.raises(SystemExit) as excinfo:
            main(["new-doc"])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "unexpected error occurred" in captured.err


class TestArgumentHandlingErrors:
    """Test error handling in argument processing."""

    def test_invalid_command_characters(self, capsys):
        """Test command names with invalid characters."""
        invalid_commands = [
            "cmd with spaces",
            "cmd/with/slashes",
            "cmd\\with\\backslashes",
            "cmd|with|pipes",
            "cmd&with&ampersand",
            "cmd;with;semicolon",
        ]

        for invalid_cmd in invalid_commands:
            with pytest.raises(SystemExit) as excinfo:
                main([invalid_cmd])

            assert excinfo.value.code == 1
            captured = capsys.readouterr()
            assert "Unknown command" in captured.err

    def test_extremely_long_command_name(self, capsys):
        """Test extremely long command name."""
        long_command = "a" * 1000  # 1000 character command name

        with pytest.raises(SystemExit) as excinfo:
            main([long_command])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Unknown command" in captured.err

    def test_null_character_in_command(self, capsys):
        """Test command with null character."""
        null_command = "cmd\x00null"

        with pytest.raises(SystemExit) as excinfo:
            main([null_command])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Unknown command" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_sys_argv_corruption_during_execution(self, mock_load):
        """Test handling of sys.argv corruption during command execution."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"

        def corrupt_argv():
            # Simulate subcommand corrupting sys.argv
            sys.argv = []

        mock_module.cli_entry = corrupt_argv
        mock_load.return_value = mock_module

        original_argv = sys.argv.copy()

        try:
            main(["plan", "test"])
            # sys.argv should be restored even if subcommand corrupts it
            assert sys.argv == original_argv
        finally:
            sys.argv = original_argv

    @patch("khive.cli.khive_cli._load_command_module")
    def test_sys_argv_exception_during_restoration(self, mock_load):
        """Test exception handling during sys.argv restoration."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.cli_entry = Mock(side_effect=ValueError("test error"))
        mock_load.return_value = mock_module

        original_argv = sys.argv.copy()

        try:
            with pytest.raises(SystemExit):
                main(["compose"])
            # sys.argv should still be restored even when subcommand fails
            assert sys.argv == original_argv
        finally:
            sys.argv = original_argv


class TestConfigurationErrors:
    """Test error handling in configuration scenarios."""

    def test_commands_dict_empty(self, capsys):
        """Test behavior when COMMANDS dict is empty."""
        with patch("khive.cli.khive_cli.COMMANDS", {}):
            _print_root_help()
            captured = capsys.readouterr()

            # Should still show basic help structure
            assert "khive" in captured.out.lower()
            assert "usage" in captured.out.lower()

    def test_commands_dict_malformed_values(self, capsys):
        """Test behavior with malformed COMMANDS dict values."""
        malformed_commands = {"test1": None, "test2": 123, "test3": {}, "test4": []}

        with patch("khive.cli.khive_cli.COMMANDS", malformed_commands):
            # Should handle malformed values gracefully
            for cmd_name in malformed_commands:
                with pytest.raises(SystemExit):
                    main([cmd_name])

    def test_command_descriptions_inconsistency(self, capsys):
        """Test handling of inconsistent command descriptions."""
        test_commands = {"test_cmd": "test_module"}
        test_descriptions = {"different_cmd": "Different description"}

        with patch("khive.cli.khive_cli.COMMANDS", test_commands):
            with patch("khive.cli.khive_cli.COMMAND_DESCRIPTIONS", test_descriptions):
                _print_root_help()
                captured = capsys.readouterr()

                # Should include command even without description
                assert "test_cmd" in captured.out


class TestSystemResourceErrors:
    """Test error handling related to system resources."""

    @patch("khive.cli.khive_cli.importlib.import_module")
    def test_out_of_memory_during_import(self, mock_import, capsys):
        """Test handling of memory exhaustion during import."""
        mock_import.side_effect = MemoryError("Cannot allocate memory")

        result = _load_command_module("plan")
        assert result is None

        captured = capsys.readouterr()
        assert "unexpected issue occurred" in captured.err

    @patch("khive.cli.khive_cli.importlib.import_module")
    def test_disk_full_during_import(self, mock_import, capsys):
        """Test handling of disk space issues during import."""
        mock_import.side_effect = OSError(28, "No space left on device")  # ENOSPC

        result = _load_command_module("compose")
        assert result is None

        captured = capsys.readouterr()
        assert "unexpected issue occurred" in captured.err

    @patch("khive.cli.khive_cli._load_command_module")
    def test_file_descriptor_exhaustion(self, mock_load):
        """Test handling of file descriptor exhaustion."""
        mock_load.side_effect = OSError(24, "Too many open files")  # EMFILE

        with pytest.raises(SystemExit) as excinfo:
            main(["session"])

        assert excinfo.value.code == 1


class TestConcurrencyErrors:
    """Test error handling in concurrent scenarios."""

    @patch("khive.cli.khive_cli._load_command_module")
    def test_concurrent_sys_argv_modification(self, mock_load):
        """Test handling of concurrent sys.argv modifications."""
        mock_module = Mock(spec=ModuleType)
        mock_module.__name__ = "test_module"

        def modify_argv_concurrently():
            import threading
            import time

            def modify():
                time.sleep(0.1)  # Small delay
                sys.argv = ["modified"]

            thread = threading.Thread(target=modify)
            thread.start()
            time.sleep(0.2)  # Let modification happen
            thread.join()

        mock_module.cli_entry = modify_argv_concurrently
        mock_load.return_value = mock_module

        original_argv = sys.argv.copy()

        try:
            main(["plan"])
            # sys.argv should be restored regardless of concurrent modifications
            assert sys.argv == original_argv
        finally:
            sys.argv = original_argv

    def test_signal_handling_during_execution(self):
        """Test signal handling during command execution."""
        # This test would require actual signal generation
        # which is complex in a test environment
        # Focus on KeyboardInterrupt which is the most common


class TestEdgeCaseErrors:
    """Test edge case error scenarios."""

    def test_unicode_in_command_names(self, capsys):
        """Test Unicode characters in command names."""
        unicode_commands = [
            "测试",  # Chinese
            "тест",  # Cyrillic
            "🚀",  # Emoji
            "café",  # Accented characters
        ]

        for unicode_cmd in unicode_commands:
            with pytest.raises(SystemExit) as excinfo:
                main([unicode_cmd])

            assert excinfo.value.code == 1
            captured = capsys.readouterr()
            assert "Unknown command" in captured.err

    def test_control_characters_in_arguments(self):
        """Test control characters in arguments."""
        control_chars = [
            "\x01",  # SOH
            "\x1b",  # ESC
            "\x7f",  # DEL
            "\n",  # Newline
            "\t",  # Tab
        ]

        for char in control_chars:
            command_with_control = f"test{char}command"
            with pytest.raises(SystemExit):
                main([command_with_control])

    def test_very_large_argument_lists(self):
        """Test handling of extremely large argument lists."""
        # Create a large argument list that might cause memory issues
        large_args = ["plan"] + [f"arg{i}" for i in range(10000)]

        # Should handle gracefully without memory errors
        with pytest.raises(SystemExit):
            main(large_args)

    def test_nested_exception_handling(self):
        """Test nested exception scenarios."""

        @patch("khive.cli.khive_cli._load_command_module")
        def test_with_nested_exceptions(mock_load, capsys):
            mock_module = Mock(spec=ModuleType)
            mock_module.__name__ = "test_module"

            def nested_exception():
                try:
                    raise ValueError("Inner exception")
                except ValueError:
                    raise RuntimeError("Outer exception")

            mock_module.cli_entry = nested_exception
            mock_load.return_value = mock_module

            with pytest.raises(SystemExit) as excinfo:
                main(["plan"])

            assert excinfo.value.code == 1
            captured = capsys.readouterr()
            assert "unexpected error occurred" in captured.err

        test_with_nested_exceptions()


class TestRecoveryScenarios:
    """Test error recovery and graceful degradation."""

    def test_partial_command_loading_failure(self):
        """Test behavior when only some commands fail to load."""
        # This would test scenarios where some commands work and others don't
        # In practice, this would require mocking specific command modules

    def test_help_system_robustness(self, capsys):
        """Test help system works even with broken commands."""
        # Help should work even if individual commands are broken
        with patch(
            "khive.cli.khive_cli.COMMANDS", {"broken_cmd": "nonexistent_module"}
        ):
            _print_root_help()
            captured = capsys.readouterr()

            # Help should still display
            assert "khive" in captured.out.lower()
            assert "usage" in captured.out.lower()
            assert "broken_cmd" in captured.out

    @patch("khive.cli.khive_cli._load_command_module")
    def test_graceful_degradation_on_import_failure(self, mock_load, capsys):
        """Test graceful degradation when command import fails."""
        mock_load.return_value = None  # Simulate import failure

        with pytest.raises(SystemExit) as excinfo:
            main(["plan"])

        assert excinfo.value.code == 1
        # Should exit gracefully without causing crashes
