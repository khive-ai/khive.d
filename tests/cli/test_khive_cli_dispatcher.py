"""
Tests for the main khive CLI dispatcher (khive.cli.khive_cli).

This module tests the core CLI functionality including command discovery,
module loading, argument passing, and error handling.
"""

import sys
from unittest.mock import Mock, patch, MagicMock
import pytest

from khive.cli.khive_cli import (
    main,
    _load_command_module,
    _get_full_module_path,
    _print_root_help,
    COMMANDS,
    COMMAND_DESCRIPTIONS,
    COMMAND_MODULE_BASE_PATH,
    ENTRY_POINT_FUNCTION_NAME,
)


class TestCLIDispatcher:
    """Test the main CLI dispatcher functionality."""

    def test_get_full_module_path(self):
        """Test module path construction."""
        result = _get_full_module_path("init")
        assert result == "khive.commands.init"
        
        result = _get_full_module_path("new_doc")
        assert result == "khive.commands.new_doc"

    def test_commands_dict_completeness(self):
        """Test that COMMANDS dict has entries for expected commands."""
        expected_commands = {
            "init", "new-doc", "fmt", "roo", "info", 
            "file", "ci", "mcp", "dev", "git"
        }
        assert set(COMMANDS.keys()) == expected_commands

    def test_command_descriptions_completeness(self):
        """Test that all commands have descriptions."""
        for cmd in COMMANDS.keys():
            assert cmd in COMMAND_DESCRIPTIONS
            assert len(COMMAND_DESCRIPTIONS[cmd]) > 0

    @patch('khive.cli.khive_cli.importlib.import_module')
    def test_load_command_module_success(self, mock_import):
        """Test successful module loading."""
        mock_module = Mock()
        mock_import.return_value = mock_module
        
        result = _load_command_module("init")
        assert result == mock_module
        mock_import.assert_called_once_with("khive.commands.init")

    @patch('khive.cli.khive_cli.importlib.import_module')
    @patch('khive.cli.khive_cli._print_root_help')
    @patch('builtins.print')
    def test_load_command_module_unknown_command(self, mock_print, mock_help, mock_import):
        """Test loading unknown command."""
        result = _load_command_module("unknown")
        assert result is None
        mock_help.assert_called_once()
        mock_print.assert_called_once()

    @patch('khive.cli.khive_cli.importlib.import_module')
    @patch('builtins.print')
    def test_load_command_module_import_error(self, mock_print, mock_import):
        """Test handling of import errors."""
        mock_import.side_effect = ImportError("Module not found")
        
        result = _load_command_module("init")
        assert result is None
        mock_print.assert_called_once()

    @patch('builtins.print')
    def test_print_root_help(self, mock_print):
        """Test root help message printing."""
        _print_root_help()
        
        # Verify print was called multiple times (for different parts of help)
        assert mock_print.call_count >= len(COMMANDS) + 3  # Header + commands + footer

    @patch('khive.cli.khive_cli._print_root_help')
    def test_main_no_args(self, mock_help):
        """Test main function with no arguments."""
        main([])
        mock_help.assert_called_once()

    @patch('khive.cli.khive_cli._print_root_help')
    def test_main_help_flag(self, mock_help):
        """Test main function with help flag."""
        main(["--help"])
        mock_help.assert_called_once()
        
        main(["-h"])
        assert mock_help.call_count == 2

    @patch('khive.cli.khive_cli._load_command_module')
    def test_main_module_load_failure(self, mock_load):
        """Test main function when module loading fails."""
        mock_load.return_value = None
        
        with pytest.raises(SystemExit) as exc_info:
            main(["init"])
        
        assert exc_info.value.code == 1

    @patch('khive.cli.khive_cli._load_command_module')
    @patch('builtins.print')
    def test_main_missing_entry_point(self, mock_print, mock_load):
        """Test main function when module lacks entry point."""
        mock_module = Mock()
        mock_module.__name__ = "test_module"  # Add required __name__ attribute
        del mock_module.cli_entry  # Ensure attribute doesn't exist
        mock_load.return_value = mock_module
        
        with pytest.raises(SystemExit) as exc_info:
            main(["init"])
        
        assert exc_info.value.code == 1
        mock_print.assert_called_once()

    @patch('khive.cli.khive_cli._load_command_module')
    def test_main_successful_command_execution(self, mock_load):
        """Test successful command execution."""
        mock_entry_point = Mock()
        mock_module = Mock()
        mock_module.cli_entry = mock_entry_point
        mock_load.return_value = mock_module
        
        original_argv = sys.argv.copy()
        try:
            main(["init", "--arg1", "value1"])
            
            # Verify entry point was called
            mock_entry_point.assert_called_once()
            
            # Verify sys.argv was properly set for the subcommand
            # (This happens during execution, so we can't directly test it here,
            # but we can verify the entry point was called)
            
        finally:
            sys.argv = original_argv

    @patch('khive.cli.khive_cli._load_command_module')
    def test_main_command_system_exit(self, mock_load):
        """Test handling of SystemExit from command."""
        mock_entry_point = Mock(side_effect=SystemExit(42))
        mock_module = Mock()
        mock_module.cli_entry = mock_entry_point
        mock_load.return_value = mock_module
        
        with pytest.raises(SystemExit) as exc_info:
            main(["init"])
        
        assert exc_info.value.code == 42

    @patch('khive.cli.khive_cli._load_command_module')
    @patch('builtins.print')
    @patch('traceback.print_exc')
    def test_main_command_unexpected_error(self, mock_traceback, mock_print, mock_load):
        """Test handling of unexpected errors from command."""
        mock_entry_point = Mock(side_effect=RuntimeError("Unexpected error"))
        mock_module = Mock()
        mock_module.cli_entry = mock_entry_point
        mock_load.return_value = mock_module
        
        with pytest.raises(SystemExit) as exc_info:
            main(["init"])
        
        assert exc_info.value.code == 1
        mock_traceback.assert_called_once()

    def test_argv_handling_preserves_original(self):
        """Test that original sys.argv is preserved after command execution."""
        original_argv = sys.argv.copy()
        
        with patch('khive.cli.khive_cli._load_command_module') as mock_load:
            mock_entry_point = Mock()
            mock_module = Mock()
            mock_module.cli_entry = mock_entry_point
            mock_load.return_value = mock_module
            
            main(["init", "--test"])
            
            # sys.argv should be restored
            assert sys.argv == original_argv


class TestCLIIntegration:
    """Integration tests for CLI dispatcher with real command modules."""

    def test_commands_exist_and_have_entry_points(self):
        """Test that all configured commands can be imported and have entry points."""
        for cmd_name, module_name in COMMANDS.items():
            full_path = f"{COMMAND_MODULE_BASE_PATH}.{module_name}"
            
            try:
                import importlib
                module = importlib.import_module(full_path)
                
                # Check that entry point exists and is callable
                assert hasattr(module, ENTRY_POINT_FUNCTION_NAME), f"Module {full_path} missing {ENTRY_POINT_FUNCTION_NAME}"
                entry_point = getattr(module, ENTRY_POINT_FUNCTION_NAME)
                assert callable(entry_point), f"Entry point {ENTRY_POINT_FUNCTION_NAME} in {full_path} is not callable"
                
            except ImportError as e:
                pytest.fail(f"Could not import command module {full_path}: {e}")


# Fixtures for CLI testing
@pytest.fixture
def mock_sys_argv():
    """Fixture to safely mock sys.argv."""
    original = sys.argv.copy()
    yield
    sys.argv = original