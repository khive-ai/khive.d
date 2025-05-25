"""Tests for khive_ci CLI command."""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

from khive.cli.khive_ci import main, detect_project_types, CIConfig, load_ci_config


class TestKhiveCIFunctions:
    """Test individual functions from khive_ci module."""

    def test_detect_project_types_python_project(self):
        """Test detecting Python project with pyproject.toml."""
        test_root = Path("/test/project")
        
        with patch.object(Path, 'exists') as mock_exists:
            # Mock pyproject.toml exists
            mock_exists.side_effect = lambda: True if 'pyproject.toml' in str(self) else False
            
            projects = detect_project_types(test_root)
            
            assert 'python' in projects
            assert projects['python']['test_command'] == 'pytest'
            assert projects['python']['config_file'] == 'pyproject.toml'

    def test_detect_project_types_rust_project(self):
        """Test detecting Rust project with Cargo.toml."""
        test_root = Path("/test/project")
        
        with patch.object(Path, 'exists') as mock_exists:
            # Mock Cargo.toml exists
            mock_exists.side_effect = lambda: True if 'Cargo.toml' in str(self) else False
            
            projects = detect_project_types(test_root)
            
            assert 'rust' in projects
            assert projects['rust']['test_command'] == 'cargo test'
            assert projects['rust']['config_file'] == 'Cargo.toml'

    def test_detect_project_types_no_projects(self):
        """Test detecting no projects when no config files exist."""
        test_root = Path("/test/project")
        
        with patch.object(Path, 'exists', return_value=False):
            projects = detect_project_types(test_root)
            
            assert projects == {}

    def test_ci_config_creation(self):
        """Test CIConfig creation and properties."""
        test_root = Path("/test/project")
        config = CIConfig(project_root=test_root, timeout=600, verbose=True)
        
        assert config.project_root == test_root
        assert config.timeout == 600
        assert config.verbose is True
        assert config.khive_config_dir == test_root / ".khive"

    def test_load_ci_config_default(self):
        """Test loading CI config with defaults."""
        test_root = Path("/test/project")
        
        with patch.object(Path, 'exists', return_value=False):
            config = load_ci_config(test_root)
            
            assert config.project_root == test_root
            assert config.timeout == 300  # default
            assert config.json_output is False
            assert config.dry_run is False
            assert config.verbose is False

    def test_load_ci_config_with_file(self):
        """Test loading CI config from TOML file."""
        test_root = Path("/test/project")
        
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'read_text', return_value='timeout = 600'):
                config = load_ci_config(test_root)
                
                assert config.timeout == 600

    @pytest.mark.asyncio
    async def test_run_ci_async_no_projects(self):
        """Test run_ci_async when no projects are detected."""
        from khive.cli.khive_ci import run_ci_async
        
        test_root = Path("/test/project")
        
        with patch('khive.cli.khive_ci.detect_project_types', return_value={}):
            with patch('khive.cli.khive_ci.check_and_run_custom_ci_script', return_value=None):
                exit_code = await run_ci_async(test_root, json_output=True)
                
                assert exit_code == 0  # No projects is not an error

    @pytest.mark.asyncio
    async def test_run_ci_async_with_custom_script(self):
        """Test run_ci_async with custom script."""
        from khive.cli.khive_ci import run_ci_async, CIResult
        
        test_root = Path("/test/project")
        mock_result = CIResult(project_root=test_root)
        mock_result.overall_success = True
        
        with patch('khive.cli.khive_ci.check_and_run_custom_ci_script', return_value=mock_result):
            exit_code = await run_ci_async(test_root)
            
            assert exit_code == 0

    def test_main_with_keyboard_interrupt(self):
        """Test main function handles KeyboardInterrupt."""
        test_args = ['khive-ci', '--json-output']
        
        with patch.object(sys, 'argv', test_args):
            with patch('khive.cli.khive_ci.asyncio.run', side_effect=KeyboardInterrupt()):
                with patch('khive.cli.khive_ci.sys.exit') as mock_exit:
                    main()
                    
                    mock_exit.assert_called_once_with(130)

    def test_main_with_exception(self):
        """Test main function handles general exceptions."""
        test_args = ['khive-ci', '--json-output']
        
        with patch.object(sys, 'argv', test_args):
            with patch('khive.cli.khive_ci.asyncio.run', side_effect=Exception("Test error")):
                with patch('khive.cli.khive_ci.sys.exit') as mock_exit:
                    main()
                    
                    mock_exit.assert_called_once_with(1)

    def test_main_with_invalid_project_root(self):
        """Test main function with invalid project root."""
        test_args = ['khive-ci', '--project-root', '/nonexistent/path', '--json-output']
        
        with patch.object(sys, 'argv', test_args):
            with patch('khive.cli.khive_ci.sys.exit') as mock_exit:
                main()
                
                mock_exit.assert_called_once_with(1)


class TestKhiveCIIntegration:
    """Integration tests for CI functionality."""

    def test_cli_entry_function_exists(self):
        """Test that cli_entry function exists and is callable."""
        from khive.cli.khive_ci import cli_entry
        
        # Should be callable without error (though we won't actually call it)
        assert callable(cli_entry)

    def test_project_root_detection(self):
        """Test PROJECT_ROOT is properly detected."""
        from khive.cli.khive_ci import PROJECT_ROOT
        
        # Should be a Path object
        assert isinstance(PROJECT_ROOT, Path)

    def test_ansi_colors_defined(self):
        """Test ANSI color constants are defined."""
        from khive.cli.khive_ci import ANSI
        
        assert 'G' in ANSI  # Green
        assert 'R' in ANSI  # Red
        assert 'Y' in ANSI  # Yellow
        assert 'B' in ANSI  # Blue
        assert 'N' in ANSI  # Normal/Reset

    def test_logging_functions_exist(self):
        """Test that logging functions exist and work."""
        from khive.cli.khive_ci import log_msg_ci, info_msg_ci, warn_msg_ci, error_msg_ci
        
        # Test functions exist and can be called
        with patch('builtins.print'):
            log_msg_ci("test message")
            info_msg_ci("test info", console=False)
            warn_msg_ci("test warning", console=False)
            error_msg_ci("test error", console=False)

    @pytest.mark.asyncio
    async def test_execute_tests_async_python(self):
        """Test execute_tests_async for Python projects."""
        from khive.cli.khive_ci import execute_tests_async
        
        test_root = Path("/test/project")
        config = {"test_paths": ["tests"]}
        
        with patch('khive.cli.khive_ci.asyncio.create_subprocess_exec') as mock_create:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"All tests passed", b"")
            mock_create.return_value = mock_proc
            
            with patch('khive.cli.khive_ci.asyncio.wait_for') as mock_wait:
                mock_wait.return_value = (b"All tests passed", b"")
                
                result = await execute_tests_async(
                    test_root, "python", config, timeout=300
                )
                
                assert result.test_type == "python"
                assert result.success is True
                assert result.exit_code == 0

    def test_format_output_json(self):
        """Test format_output with JSON format."""
        from khive.cli.khive_ci import format_output, CIResult
        
        result = CIResult(project_root=Path("/test"))
        result.overall_success = True
        result.total_duration = 5.5
        
        output = format_output(result, json_output=True)
        
        # Should be valid JSON
        import json
        data = json.loads(output)
        assert data["status"] == "success"
        assert data["total_duration"] == 5.5

    def test_format_output_human_readable(self):
        """Test format_output with human-readable format."""
        from khive.cli.khive_ci import format_output, CIResult
        
        result = CIResult(project_root=Path("/test"))
        result.overall_success = True
        
        output = format_output(result, json_output=False)
        
        # Should contain expected sections
        assert "khive ci - Continuous Integration Results" in output
        assert "Project Root:" in output
        assert "Overall Status: SUCCESS" in output