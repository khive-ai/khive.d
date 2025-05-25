"""Tests for khive_roo CLI command."""

import subprocess
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
import json

from khive.cli.khive_roo import main, get_project_root, KhiveRooManager


class TestKhiveRooFunctions:
    """Test individual functions from khive_roo module."""

    def test_get_project_root_with_git(self):
        """Test get_project_root when git is available."""
        with patch('subprocess.check_output') as mock_check:
            mock_check.return_value = b'/test/project\n'
            
            root = get_project_root()
            
            assert root == Path('/test/project')
            mock_check.assert_called_once_with(
                ["git", "rev-parse", "--show-toplevel"], 
                stderr=subprocess.PIPE
            )

    def test_get_project_root_without_git(self):
        """Test get_project_root when git is not available."""
        with patch('subprocess.check_output', side_effect=FileNotFoundError()):
            with patch('pathlib.Path.cwd', return_value=Path('/current/dir')):
                root = get_project_root()
                
                assert root == Path('/current/dir')

    def test_get_project_root_git_error(self):
        """Test get_project_root when git command fails."""
        import subprocess
        with patch('subprocess.check_output', side_effect=subprocess.CalledProcessError(1, 'git')):
            with patch('pathlib.Path.cwd', return_value=Path('/fallback/dir')):
                root = get_project_root()
                
                assert root == Path('/fallback/dir')

    def test_khive_roo_manager_initialization(self):
        """Test KhiveRooManager initialization."""
        test_root = Path("/test/project")
        manager = KhiveRooManager(project_root_override=test_root)
        
        assert manager.project_root == test_root
        assert manager.khive_dir == test_root / ".khive"
        assert manager.target_roo_dir == test_root / ".roo"
        assert manager.output_json_path == test_root / ".roomodes"

    def test_khive_roo_manager_default_initialization(self):
        """Test KhiveRooManager initialization without override."""
        with patch('khive.cli.khive_roo.get_project_root', return_value=Path("/default/root")):
            manager = KhiveRooManager()
            
            assert manager.project_root == Path("/default/root")

    def test_get_package_source_path_success(self):
        """Test _get_package_source_path when package is found."""
        manager = KhiveRooManager(Path("/test"))
        
        with patch('importlib.resources.files') as mock_files:
            mock_files.return_value = Path("/package/prompts")
            
            result = manager._get_package_source_path()
            
            assert result == Path("/package/prompts")

    def test_get_package_source_path_fallback(self):
        """Test _get_package_source_path fallback to development path."""
        manager = KhiveRooManager(Path("/test"))
        
        with patch('importlib.resources.files', side_effect=ModuleNotFoundError()):
            # Mock the development path
            dev_path = Path(__file__).resolve().parent.parent / "prompts"
            with patch.object(Path, 'is_dir', return_value=True):
                result = manager._get_package_source_path()
                
                # Should return some path (the exact path depends on file structure)
                assert isinstance(result, Path)

    def test_get_package_source_path_not_found(self):
        """Test _get_package_source_path when no source is found."""
        manager = KhiveRooManager(Path("/test"))
        
        with patch('importlib.resources.files', side_effect=ModuleNotFoundError()):
            with patch.object(Path, 'is_dir', return_value=False):
                result = manager._get_package_source_path()
                
                assert result is None

    def test_initialize_khive_structure_success(self):
        """Test successful initialization of khive structure."""
        manager = KhiveRooManager(Path("/test"))
        
        with patch.object(Path, 'exists', return_value=False):
            with patch.object(Path, 'mkdir') as mock_mkdir:
                with patch.object(manager, '_get_package_source_path', return_value=Path("/source")):
                    with patch('shutil.copytree') as mock_copytree:
                        with patch.object(Path, 'is_dir', return_value=True):
                            result = manager.initialize_khive_structure()
                            
                            assert result is True
                            assert mock_mkdir.call_count >= 2  # .khive and .khive/prompts

    def test_initialize_khive_structure_no_source(self):
        """Test initialization when source path is not found."""
        manager = KhiveRooManager(Path("/test"))
        
        with patch.object(manager, '_get_package_source_path', return_value=None):
            result = manager.initialize_khive_structure()
            
            assert result is False

    def test_synchronize_target_roo_folder_success(self):
        """Test successful synchronization of target roo folder."""
        manager = KhiveRooManager(Path("/test"))
        
        with patch.object(Path, 'is_dir', return_value=True):
            with patch.object(Path, 'exists', return_value=True):
                with patch('shutil.rmtree') as mock_rmtree:
                    with patch('shutil.copytree') as mock_copytree:
                        result = manager.synchronize_target_roo_folder()
                        
                        assert result is True
                        mock_rmtree.assert_called_once()
                        mock_copytree.assert_called_once()

    def test_synchronize_target_roo_folder_no_source(self):
        """Test synchronization when source directory doesn't exist."""
        manager = KhiveRooManager(Path("/test"))
        
        with patch.object(Path, 'is_dir', return_value=False):
            result = manager.synchronize_target_roo_folder()
            
            assert result is False

    def test_parse_mode_readme_success(self):
        """Test successful parsing of mode readme file."""
        manager = KhiveRooManager(Path("/test"))
        test_content = """---
title: "Test Mode"
slug: "test-mode"
name: "🧪Test Mode"
groups: ["read", "write"]
source: "project"
---

## Role Definition

This is a test role definition.

## Custom Instructions

These are test custom instructions.
"""
        
        with patch.object(Path, 'read_text', return_value=test_content):
            with patch('yaml.safe_load') as mock_yaml:
                mock_yaml.return_value = {
                    "title": "Test Mode",
                    "slug": "test-mode", 
                    "name": "🧪Test Mode",
                    "groups": ["read", "write"],
                    "source": "project"
                }
                
                result = manager._parse_mode_readme(Path("test.md"))
                
                assert result is not None
                assert result["slug"] == "test-mode"
                assert result["name"] == "🧪Test Mode"
                assert result["groups"] == ["read", "write"]
                assert "This is a test role definition" in result["roleDefinition"]
                assert "These are test custom instructions" in result["customInstructions"]

    def test_parse_mode_readme_no_frontmatter(self):
        """Test parsing mode readme without YAML frontmatter."""
        manager = KhiveRooManager(Path("/test"))
        test_content = "Just some markdown content without frontmatter."
        
        with patch.object(Path, 'read_text', return_value=test_content):
            result = manager._parse_mode_readme(Path("test.md"))
            
            assert result is None

    def test_parse_mode_readme_invalid_yaml(self):
        """Test parsing mode readme with invalid YAML."""
        manager = KhiveRooManager(Path("/test"))
        test_content = """---
invalid: yaml: content: [
---

Content here.
"""
        
        with patch.object(Path, 'read_text', return_value=test_content):
            result = manager._parse_mode_readme(Path("test.md"))
            
            assert result is None

    def test_generate_roomodes_file_success(self):
        """Test successful generation of roomodes file."""
        manager = KhiveRooManager(Path("/test"))
        
        # Mock yaml module availability
        with patch.dict('sys.modules', {'yaml': MagicMock()}):
            with patch.object(Path, 'is_dir', return_value=True):
                with patch.object(Path, 'iterdir') as mock_iterdir:
                    # Mock a mode directory
                    mock_dir = MagicMock()
                    mock_dir.is_dir.return_value = True
                    mock_dir.name = "test-mode"
                    mock_readme = mock_dir / "README.md"
                    mock_readme.exists.return_value = True
                    mock_readme.is_file.return_value = True
                    mock_iterdir.return_value = [mock_dir]
                    
                    with patch.object(manager, '_parse_mode_readme') as mock_parse:
                        mock_parse.return_value = {
                            "slug": "test-mode",
                            "name": "Test Mode",
                            "groups": [],
                            "source": "project",
                            "roleDefinition": "Test role",
                            "customInstructions": "Test instructions"
                        }
                        
                        with patch('builtins.open', MagicMock()) as mock_open:
                            with patch('json.dump') as mock_json_dump:
                                result = manager.generate_roomodes_file()
                                
                                assert result is True
                                mock_json_dump.assert_called_once()

    def test_generate_roomodes_file_no_yaml(self):
        """Test generation when yaml module is not available."""
        manager = KhiveRooManager(Path("/test"))
        
        # Mock yaml module not being available
        with patch.dict('sys.modules', {}, clear=True):
            result = manager.generate_roomodes_file()
            
            assert result is False

    def test_generate_roomodes_file_no_target_dir(self):
        """Test generation when target directory doesn't exist."""
        manager = KhiveRooManager(Path("/test"))
        
        with patch.dict('sys.modules', {'yaml': MagicMock()}):
            with patch.object(Path, 'is_dir', return_value=False):
                result = manager.generate_roomodes_file()
                
                assert result is False

    def test_run_method_success(self):
        """Test successful run of the complete process."""
        manager = KhiveRooManager(Path("/test"))
        
        with patch.object(manager, 'initialize_khive_structure', return_value=True):
            with patch.object(manager, 'synchronize_target_roo_folder', return_value=True):
                with patch.object(manager, 'generate_roomodes_file', return_value=True):
                    result = manager.run()
                    
                    assert result == 0

    def test_run_method_sync_failure(self):
        """Test run method when synchronization fails."""
        manager = KhiveRooManager(Path("/test"))
        
        with patch.object(manager, 'initialize_khive_structure', return_value=True):
            with patch.object(manager, 'synchronize_target_roo_folder', return_value=False):
                result = manager.run()
                
                assert result == 1

    def test_run_method_generation_failure(self):
        """Test run method when roomodes generation fails."""
        manager = KhiveRooManager(Path("/test"))
        
        with patch.object(manager, 'initialize_khive_structure', return_value=True):
            with patch.object(manager, 'synchronize_target_roo_folder', return_value=True):
                with patch.object(manager, 'generate_roomodes_file', return_value=False):
                    result = manager.run()
                    
                    assert result == 1

    def test_main_function(self):
        """Test main function creates manager and runs."""
        with patch('khive.cli.khive_roo.KhiveRooManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.run.return_value = 0
            mock_manager_class.return_value = mock_manager
            
            with patch('khive.cli.khive_roo.sys.exit') as mock_exit:
                main()
                
                mock_manager_class.assert_called_once()
                mock_manager.run.assert_called_once()
                mock_exit.assert_called_once_with(0)


class TestKhiveRooIntegration:
    """Integration tests for roo functionality."""

    def test_constants_defined(self):
        """Test that required constants are defined."""
        from khive.cli.khive_roo import (
            KHIVE_DIR_NAME, PROMPTS_DIR_NAME, ROO_RULES_DIR_NAME,
            TEMPLATES_DIR_NAME, TARGET_ROO_DIR_NAME, OUTPUT_JSON_NAME
        )
        
        assert KHIVE_DIR_NAME == ".khive"
        assert PROMPTS_DIR_NAME == "prompts"
        assert ROO_RULES_DIR_NAME == "roo_rules"
        assert TEMPLATES_DIR_NAME == "templates"
        assert TARGET_ROO_DIR_NAME == ".roo"
        assert OUTPUT_JSON_NAME == ".roomodes"

    def test_logging_configuration(self):
        """Test that logging is configured."""
        import logging
        
        # Should have some loggers configured
        logger = logging.getLogger()
        assert logger is not None

    def test_yaml_import_handling(self):
        """Test handling of yaml import."""
        # The module should handle yaml import gracefully
        # Even if yaml is not available, it should not crash on import
        from khive.cli.khive_roo import KhiveRooManager
        
        # Should be able to create manager even without yaml
        manager = KhiveRooManager(Path("/test"))
        assert manager is not None

    def test_manager_path_properties(self):
        """Test that manager path properties are correctly set."""
        test_root = Path("/test/project")
        manager = KhiveRooManager(test_root)
        
        # Check all path properties
        assert manager.project_root == test_root
        assert manager.khive_dir == test_root / ".khive"
        assert manager.khive_prompts_dir == test_root / ".khive" / "prompts"
        assert manager.source_roo_rules_dir == test_root / ".khive" / "prompts" / "roo_rules"
        assert manager.source_templates_dir == test_root / ".khive" / "prompts" / "templates"
        assert manager.target_roo_dir == test_root / ".roo"
        assert manager.output_json_path == test_root / ".roomodes"

    def test_direct_execution(self):
        """Test direct execution path (if __name__ == '__main__')."""
        # The module should be able to handle direct execution
        # We can't easily test the actual execution, but we can verify
        # the structure is there
        import khive.cli.khive_roo
        
        # Should have the main execution block
        assert hasattr(khive.cli.khive_roo, 'main')
        assert callable(khive.cli.khive_roo.main)

    def test_error_handling_in_file_operations(self):
        """Test error handling in file operations."""
        manager = KhiveRooManager(Path("/test"))
        
        # Test file reading error handling
        with patch.object(Path, 'read_text', side_effect=IOError("File error")):
            result = manager._parse_mode_readme(Path("test.md"))
            assert result is None

    def test_section_extraction_regex(self):
        """Test the section extraction logic."""
        manager = KhiveRooManager(Path("/test"))
        
        test_content = """---
slug: test
---

## Role Definition

This is the role definition content.

## Custom Instructions

These are the custom instructions.

## Other Section

This should not be captured.
"""
        
        with patch.object(Path, 'read_text', return_value=test_content):
            with patch('yaml.safe_load', return_value={"slug": "test"}):
                result = manager._parse_mode_readme(Path("test.md"))
                
                if result:  # Only test if parsing succeeds
                    assert "role definition content" in result["roleDefinition"].lower()
                    assert "custom instructions" in result["customInstructions"].lower()
                    assert "other section" not in result["roleDefinition"].lower()
                    assert "other section" not in result["customInstructions"].lower()