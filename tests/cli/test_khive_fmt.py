"""Tests for khive_fmt CLI command."""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

from khive.cli.khive_fmt import main, load_fmt_config, FmtConfig, StackConfig, format_stack, find_files


class TestKhiveFmtFunctions:
    """Test individual functions from khive_fmt module."""

    def test_stack_config_creation(self):
        """Test StackConfig creation."""
        stack = StackConfig(
            name="python",
            cmd="ruff format {files}",
            check_cmd="ruff format --check {files}",
            include=["*.py"],
            exclude=["*.pyc"]
        )
        
        assert stack.name == "python"
        assert stack.cmd == "ruff format {files}"
        assert stack.check_cmd == "ruff format --check {files}"
        assert stack.include == ["*.py"]
        assert stack.exclude == ["*.pyc"]
        assert stack.enabled is True

    def test_fmt_config_creation(self):
        """Test FmtConfig creation and properties."""
        test_root = Path("/test/project")
        config = FmtConfig(project_root=test_root, verbose=True, dry_run=True)
        
        assert config.project_root == test_root
        assert config.verbose is True
        assert config.dry_run is True
        assert config.khive_config_dir == test_root / ".khive"

    def test_load_fmt_config_default(self):
        """Test loading fmt config with defaults."""
        test_root = Path("/test/project")
        
        with patch.object(Path, 'exists', return_value=False):
            config = load_fmt_config(test_root)
            
            assert config.project_root == test_root
            assert "python" in config.stacks
            assert "rust" in config.stacks
            assert "docs" in config.stacks
            assert "deno" in config.stacks

    def test_load_fmt_config_with_pyproject(self):
        """Test loading fmt config from pyproject.toml."""
        test_root = Path("/test/project")
        
        with patch.object(Path, 'exists') as mock_exists:
            mock_exists.side_effect = lambda: True if 'pyproject.toml' in str(self) else False
            
            with patch.object(Path, 'read_text', return_value='[tool."khive fmt"]\nenable = ["python"]'):
                config = load_fmt_config(test_root)
                
                assert config.enable == ["python"]

    def test_find_files_with_patterns(self):
        """Test find_files function with include/exclude patterns."""
        test_root = Path("/test/project")
        
        with patch.object(Path, 'glob') as mock_glob:
            # Mock glob to return some test files
            mock_glob.return_value = [
                Path("test1.py"),
                Path("test2.py"),
                Path("generated.py")
            ]
            
            files = find_files(test_root, ["*.py"], ["*generated*"])
            
            # Should include .py files but exclude generated ones
            file_names = [f.name for f in files]
            assert "test1.py" in file_names
            assert "test2.py" in file_names
            assert "generated.py" not in file_names

    def test_find_files_no_matches(self):
        """Test find_files when no files match patterns."""
        test_root = Path("/test/project")
        
        with patch.object(Path, 'glob', return_value=[]):
            files = find_files(test_root, ["*.py"], [])
            
            assert files == []

    def test_format_stack_disabled(self):
        """Test format_stack with disabled stack."""
        stack = StackConfig(
            name="test",
            cmd="echo {files}",
            check_cmd="echo --check {files}",
            enabled=False
        )
        config = FmtConfig(project_root=Path("/test"))
        
        result = format_stack(stack, config)
        
        assert result["status"] == "skipped"
        assert result["stack_name"] == "test"

    def test_format_stack_no_files(self):
        """Test format_stack when no files are found."""
        stack = StackConfig(
            name="test",
            cmd="echo {files}",
            check_cmd="echo --check {files}",
            include=["*.test"],
            enabled=True
        )
        config = FmtConfig(project_root=Path("/test"))
        
        with patch('khive.cli.khive_fmt.find_files', return_value=[]):
            with patch('khive.cli.khive_fmt.shutil.which', return_value="/usr/bin/echo"):
                result = format_stack(stack, config)
                
                assert result["status"] == "success"
                assert "No files found" in result["message"]

    def test_format_stack_tool_not_found(self):
        """Test format_stack when formatter tool is not found."""
        stack = StackConfig(
            name="test",
            cmd="nonexistent_tool {files}",
            check_cmd="nonexistent_tool --check {files}",
            enabled=True
        )
        config = FmtConfig(project_root=Path("/test"))
        
        with patch('khive.cli.khive_fmt.shutil.which', return_value=None):
            result = format_stack(stack, config)
            
            assert result["status"] == "error"
            assert "not found" in result["message"]

    def test_main_with_invalid_project_root(self):
        """Test main function with invalid project root."""
        test_args = ['--project-root', '/nonexistent/path', '--json-output']
        
        with patch.object(sys, 'argv', ['khive-fmt'] + test_args):
            with patch('khive.cli.khive_fmt.sys.exit') as mock_exit:
                main()
                
                mock_exit.assert_called_once_with(1)

    def test_main_with_dry_run(self):
        """Test main function with dry run mode."""
        test_args = ['--dry-run', '--json-output']
        
        with patch.object(sys, 'argv', ['khive-fmt'] + test_args):
            with patch('khive.cli.khive_fmt._main_fmt_flow') as mock_flow:
                mock_flow.return_value = {"status": "success", "message": "Dry run completed"}
                
                with patch('khive.cli.khive_fmt.sys.exit') as mock_exit:
                    main()
                    
                    # Should not exit with error for dry run
                    mock_exit.assert_not_called()

    def test_main_with_check_mode(self):
        """Test main function with check mode."""
        test_args = ['--check', '--json-output']
        
        with patch.object(sys, 'argv', ['khive-fmt'] + test_args):
            with patch('khive.cli.khive_fmt._main_fmt_flow') as mock_flow:
                mock_flow.return_value = {"status": "check_failed", "message": "Check failed"}
                
                with patch('khive.cli.khive_fmt.sys.exit') as mock_exit:
                    main()
                    
                    mock_exit.assert_called_once_with(1)


class TestKhiveFmtIntegration:
    """Integration tests for fmt functionality."""

    def test_cli_entry_function_exists(self):
        """Test that cli_entry_fmt function exists and is callable."""
        from khive.cli.khive_fmt import cli_entry_fmt
        
        # Should be callable without error (though we won't actually call it)
        assert callable(cli_entry_fmt)

    def test_project_root_detection(self):
        """Test PROJECT_ROOT is properly detected."""
        from khive.cli.khive_fmt import PROJECT_ROOT
        
        # Should be a Path object
        assert isinstance(PROJECT_ROOT, Path)

    def test_ansi_colors_defined(self):
        """Test ANSI color constants are defined."""
        from khive.cli.khive_fmt import ANSI
        
        assert 'G' in ANSI  # Green
        assert 'R' in ANSI  # Red
        assert 'Y' in ANSI  # Yellow
        assert 'B' in ANSI  # Blue
        assert 'N' in ANSI  # Normal/Reset

    def test_logging_functions_exist(self):
        """Test that logging functions exist and work."""
        from khive.cli.khive_fmt import log_msg, info_msg, warn_msg, error_msg
        
        # Test functions exist and can be called
        with patch('builtins.print'):
            log_msg("test message")
            info_msg("test info", console=False)
            warn_msg("test warning", console=False)
            error_msg("test error", console=False)

    def test_max_files_per_batch_constant(self):
        """Test MAX_FILES_PER_BATCH constant is defined."""
        from khive.cli.khive_fmt import MAX_FILES_PER_BATCH
        
        assert isinstance(MAX_FILES_PER_BATCH, int)
        assert MAX_FILES_PER_BATCH > 0

    def test_run_command_function(self):
        """Test run_command function with mocked subprocess."""
        from khive.cli.khive_fmt import run_command
        
        with patch('khive.cli.khive_fmt.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")
            
            result = run_command(
                ["echo", "test"],
                capture=True,
                check=False,
                dry_run=False,
                cwd=Path("/test"),
                tool_name="echo"
            )
            
            assert hasattr(result, 'returncode')

    def test_run_command_dry_run(self):
        """Test run_command in dry run mode."""
        from khive.cli.khive_fmt import run_command
        
        result = run_command(
            ["echo", "test"],
            capture=True,
            check=False,
            dry_run=True,
            cwd=Path("/test"),
            tool_name="echo"
        )
        
        # Should return success result without actually running
        assert hasattr(result, 'returncode')
        assert result.returncode == 0

    def test_check_and_run_custom_script_not_found(self):
        """Test check_and_run_custom_script when script doesn't exist."""
        from khive.cli.khive_fmt import check_and_run_custom_script
        import argparse
        
        config = FmtConfig(project_root=Path("/test"))
        args = argparse.Namespace()
        
        with patch.object(Path, 'exists', return_value=False):
            result = check_and_run_custom_script(config, args)
            
            assert result is None

    def test_default_stack_configurations(self):
        """Test that default stack configurations are properly set up."""
        test_root = Path("/test/project")
        
        with patch.object(Path, 'exists', return_value=False):
            config = load_fmt_config(test_root)
            
            # Check Python stack
            python_stack = config.stacks["python"]
            assert python_stack.name == "python"
            assert "ruff format" in python_stack.cmd
            assert "*.py" in python_stack.include
            
            # Check Rust stack
            rust_stack = config.stacks["rust"]
            assert rust_stack.name == "rust"
            assert "cargo fmt" in rust_stack.cmd
            assert "*.rs" in rust_stack.include

    def test_main_flow_function(self):
        """Test _main_fmt_flow function."""
        from khive.cli.khive_fmt import _main_fmt_flow
        import argparse
        
        config = FmtConfig(project_root=Path("/test"))
        args = argparse.Namespace()
        
        with patch('khive.cli.khive_fmt.check_and_run_custom_script', return_value=None):
            with patch('khive.cli.khive_fmt.format_stack') as mock_format:
                mock_format.return_value = {
                    "status": "success",
                    "stack_name": "test",
                    "message": "Success",
                    "files_processed": 5
                }
                
                # Enable one stack for testing
                config.stacks["test"] = StackConfig(
                    name="test",
                    cmd="echo {files}",
                    check_cmd="echo --check {files}",
                    enabled=True
                )
                
                result = _main_fmt_flow(args, config)
                
                assert result["status"] == "success"
                assert len(result["stacks_processed"]) == 1

    def test_argv_handling_in_main(self):
        """Test that main function properly handles argv parameter."""
        test_argv = ['--help']
        
        # Should not raise an exception when setting custom argv
        with patch('khive.cli.khive_fmt.cli_entry_fmt') as mock_cli:
            main(test_argv)
            mock_cli.assert_called_once()