"""Comprehensive tests for khive clean CLI functionality.

Tests cover:
- Configuration loading and protected branch patterns
- Git branch cleanup operations with proper mocking
- Error scenarios (permission failures, network issues)
- Dry-run mode validation
- Branch existence checking (local/remote)
- Destructive operation safeguards
- Default branch detection
- All-merged functionality
- CLI argument parsing
- JSON output modes
"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from khive.cli.khive_clean import (
    CleanConfig,
    _clean_single_branch,
    _main_clean_flow,
    cli_entry_clean,
    detect_default_branch_clean,
    get_current_git_branch_clean,
    get_merged_branches,
    is_branch_protected,
    load_clean_config,
    main,
)


class TestCleanConfig:
    """Test CleanConfig dataclass and configuration loading."""

    def test_clean_config_defaults(self, temp_dir):
        """Test CleanConfig default values."""
        config = CleanConfig(project_root=temp_dir)
        
        assert config.project_root == temp_dir
        assert config.protected_branch_patterns == ["release/*", "develop"]
        assert config.default_remote == "origin"
        assert config.strict_pull_on_default is False
        assert config.all_merged_default_base == ""
        assert config.json_output is False
        assert config.dry_run is False
        assert config.verbose is False

    def test_khive_config_dir_property(self, temp_dir):
        """Test khive_config_dir property."""
        config = CleanConfig(project_root=temp_dir)
        assert config.khive_config_dir == temp_dir / ".khive"

    def test_load_clean_config_no_file(self, temp_dir):
        """Test loading config when no config file exists."""
        config = load_clean_config(temp_dir)
        
        assert config.project_root == temp_dir
        assert config.protected_branch_patterns == ["release/*", "develop"]
        assert config.default_remote == "origin"

    def test_load_clean_config_with_file(self, temp_dir):
        """Test loading config from TOML file."""
        khive_dir = temp_dir / ".khive"
        khive_dir.mkdir()
        
        config_content = """
protected_branch_patterns = ["main", "staging/*", "hotfix/*"]
default_remote = "upstream"
strict_pull_on_default = true
all_merged_default_base = "develop"
"""
        (khive_dir / "clean.toml").write_text(config_content)
        
        config = load_clean_config(temp_dir)
        
        assert config.protected_branch_patterns == ["main", "staging/*", "hotfix/*"]
        assert config.default_remote == "upstream"
        assert config.strict_pull_on_default is True
        assert config.all_merged_default_base == "develop"

    def test_load_clean_config_invalid_toml(self, temp_dir):
        """Test loading config with invalid TOML content."""
        khive_dir = temp_dir / ".khive"
        khive_dir.mkdir()
        
        # Invalid TOML content
        (khive_dir / "clean.toml").write_text("invalid toml content [[[")
        
        with patch("khive.cli.khive_clean.warn_msg_clean") as mock_warn:
            config = load_clean_config(temp_dir)
            
            # Should fall back to defaults
            assert config.protected_branch_patterns == ["release/*", "develop"]
            mock_warn.assert_called()

    def test_load_clean_config_with_cli_args(self, temp_dir):
        """Test loading config with CLI arguments override."""
        from argparse import Namespace
        
        cli_args = Namespace(
            json_output=True,
            dry_run=True,
            verbose=True
        )
        
        config = load_clean_config(temp_dir, cli_args)
        
        assert config.json_output is True
        assert config.dry_run is True
        assert config.verbose is True


class TestBranchProtection:
    """Test branch protection logic."""

    def test_is_branch_protected_default_branch(self, temp_dir):
        """Test that default branch is always protected."""
        config = CleanConfig(project_root=temp_dir)
        
        assert is_branch_protected("main", "main", config) is True
        assert is_branch_protected("develop", "develop", config) is True

    def test_is_branch_protected_pattern_matching(self, temp_dir):
        """Test branch protection pattern matching."""
        config = CleanConfig(
            project_root=temp_dir,
            protected_branch_patterns=["release/*", "develop", "hotfix/*"]
        )
        
        # Should be protected
        assert is_branch_protected("release/1.0.0", "main", config) is True
        assert is_branch_protected("develop", "main", config) is True
        assert is_branch_protected("hotfix/critical-bug", "main", config) is True
        
        # Should not be protected
        assert is_branch_protected("feature/new-thing", "main", config) is False
        assert is_branch_protected("bugfix/simple-fix", "main", config) is False

    def test_is_branch_protected_case_sensitive(self, temp_dir):
        """Test that pattern matching is case-sensitive."""
        config = CleanConfig(
            project_root=temp_dir,
            protected_branch_patterns=["Release/*"]
        )
        
        # Case-sensitive matching
        assert is_branch_protected("Release/1.0.0", "main", config) is True
        assert is_branch_protected("release/1.0.0", "main", config) is False


class TestGitOperations:
    """Test Git operation helpers with mocking."""

    @patch('khive.cli.khive_clean.git_run_clean')
    def test_get_current_git_branch_clean_success(self, mock_git_run, temp_dir):
        """Test getting current branch successfully."""
        config = CleanConfig(project_root=temp_dir)
        
        # Mock successful git branch --show-current
        mock_process = subprocess.CompletedProcess(
            ["git", "branch", "--show-current"], 0, stdout="feature/test-branch", stderr=""
        )
        mock_git_run.return_value = mock_process
        
        result = get_current_git_branch_clean(config)
        
        assert result == "feature/test-branch"
        mock_git_run.assert_called_once_with(
            ["branch", "--show-current"],
            capture=True,
            check=False,
            cwd=temp_dir,
            dry_run=False
        )

    @patch('khive.cli.khive_clean.git_run_clean')
    def test_get_current_git_branch_clean_failure(self, mock_git_run, temp_dir):
        """Test getting current branch when command fails."""
        config = CleanConfig(project_root=temp_dir)
        
        # Mock failed git command
        mock_process = subprocess.CompletedProcess(
            ["git", "branch", "--show-current"], 1, stdout="", stderr=""
        )
        mock_git_run.return_value = mock_process
        
        result = get_current_git_branch_clean(config)
        
        assert result == "HEAD"

    @patch('khive.cli.khive_clean.git_run_clean')
    def test_get_current_git_branch_clean_dry_run(self, mock_git_run, temp_dir):
        """Test getting current branch in dry run mode."""
        config = CleanConfig(project_root=temp_dir, dry_run=True)
        
        result = get_current_git_branch_clean(config)
        
        assert result == "main"
        mock_git_run.assert_not_called()

    @patch('khive.cli.khive_clean.shutil.which')
    @patch('khive.cli.khive_clean.cli_run_clean')
    @patch('khive.cli.khive_clean.git_run_clean')
    def test_detect_default_branch_clean_gh_success(self, mock_git_run, mock_cli_run, mock_which, temp_dir):
        """Test detecting default branch using gh CLI."""
        config = CleanConfig(project_root=temp_dir)
        
        # Mock gh CLI available
        mock_which.return_value = "/usr/bin/gh"
        
        # Mock successful gh repo view
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.stdout = "main"
        mock_cli_run.return_value = mock_process
        
        result = detect_default_branch_clean(config)
        
        assert result == "main"
        mock_cli_run.assert_called_once()

    @patch('khive.cli.khive_clean.shutil.which')
    @patch('khive.cli.khive_clean.git_run_clean')
    def test_detect_default_branch_clean_symbolic_ref(self, mock_git_run, mock_which, temp_dir):
        """Test detecting default branch using git symbolic-ref."""
        config = CleanConfig(project_root=temp_dir)
        
        # Mock gh CLI not available
        mock_which.return_value = None
        
        # Mock successful git symbolic-ref
        mock_process = subprocess.CompletedProcess(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"], 
            0, stdout="refs/remotes/origin/develop", stderr=""
        )
        mock_git_run.return_value = mock_process
        
        result = detect_default_branch_clean(config)
        
        assert result == "develop"

    @patch('khive.cli.khive_clean.shutil.which')
    @patch('khive.cli.khive_clean.git_run_clean')
    def test_detect_default_branch_clean_fallback(self, mock_git_run, mock_which, temp_dir):
        """Test detecting default branch using fallback logic."""
        config = CleanConfig(project_root=temp_dir)
        
        # Mock gh CLI not available
        mock_which.return_value = None
        
        # Mock git symbolic-ref failure, then success for show-ref main
        mock_git_run.side_effect = [
            subprocess.CompletedProcess(["git", "symbolic-ref"], 1, "", ""),  # symbolic-ref fails
            0,  # show-ref main succeeds (returns int for non-capture commands)
        ]
        
        result = detect_default_branch_clean(config)
        
        assert result == "main"

    @patch('khive.cli.khive_clean.git_run_clean')
    def test_get_merged_branches_success(self, mock_git_run, temp_dir):
        """Test getting merged branches successfully."""
        config = CleanConfig(project_root=temp_dir)
        
        # Mock git branch --merged command
        mock_git_run.side_effect = [
            0,  # checkout
            0,  # pull
            subprocess.CompletedProcess(
                ["git", "branch", "--merged"], 0, 
                stdout="feature/branch1\nfeature/branch2\n  main\n", stderr=""
            )  # branch --merged
        ]
        
        result = get_merged_branches("main", config)
        
        assert result == ["feature/branch1", "feature/branch2", "main"]

    @patch('khive.cli.khive_clean.git_run_clean')
    def test_get_merged_branches_dry_run(self, mock_git_run, temp_dir):
        """Test getting merged branches in dry run mode."""
        config = CleanConfig(project_root=temp_dir, dry_run=True)
        
        result = get_merged_branches("main", config)
        
        assert result == ["feature/dry-merged-1", "feature/dry-merged-2"]
        mock_git_run.assert_not_called()


class TestSingleBranchClean:
    """Test single branch cleaning logic."""

    @patch('khive.cli.khive_clean.git_run_clean')
    def test_clean_single_branch_protected(self, mock_git_run, temp_dir):
        """Test cleaning a protected branch."""
        config = CleanConfig(project_root=temp_dir)
        db_info = {"name": "main"}
        
        result = _clean_single_branch("main", "main", config, db_info)
        
        assert result["branch_name"] == "main"
        assert result["local_delete_status"] == "PROTECTED"
        assert result["remote_delete_status"] == "PROTECTED"
        assert "protected" in result["message"].lower()

    @patch('khive.cli.khive_clean.git_run_clean')
    def test_clean_single_branch_success(self, mock_git_run, temp_dir):
        """Test successfully cleaning a branch."""
        config = CleanConfig(project_root=temp_dir)
        db_info = {"name": "main"}
        
        # Mock successful branch operations
        mock_git_run.side_effect = [
            0,  # local branch exists (show-ref)
            0,  # delete local branch
            subprocess.CompletedProcess(
                ["git", "ls-remote"], 0, stdout="refs/heads/feature/test", stderr=""
            ),  # remote branch exists
            0,  # delete remote branch
        ]
        
        result = _clean_single_branch("feature/test", "main", config, db_info)
        
        assert result["branch_name"] == "feature/test"
        assert result["local_delete_status"] == "OK"
        assert result["remote_delete_status"] == "OK"
        assert "cleaned successfully" in result["message"]

    @patch('khive.cli.khive_clean.git_run_clean')
    def test_clean_single_branch_local_not_found(self, mock_git_run, temp_dir):
        """Test cleaning when local branch doesn't exist."""
        config = CleanConfig(project_root=temp_dir)
        db_info = {"name": "main"}
        
        # Mock branch operations
        mock_git_run.side_effect = [
            1,  # local branch doesn't exist (show-ref)
            subprocess.CompletedProcess(
                ["git", "ls-remote"], 1, stdout="", stderr=""
            ),  # remote branch doesn't exist
        ]
        
        result = _clean_single_branch("feature/test", "main", config, db_info)
        
        assert result["branch_name"] == "feature/test"
        assert result["local_delete_status"] == "NOT_FOUND"
        assert result["remote_delete_status"] == "NOT_FOUND"

    @patch('khive.cli.khive_clean.git_run_clean')
    def test_clean_single_branch_delete_failure(self, mock_git_run, temp_dir):
        """Test cleaning when deletion fails."""
        config = CleanConfig(project_root=temp_dir)
        db_info = {"name": "main"}
        
        # Mock failed deletion
        mock_git_run.side_effect = [
            0,  # local branch exists (show-ref)
            subprocess.CompletedProcess(
                ["git", "branch", "-D"], 1, stdout="", stderr="Permission denied"
            ),  # delete local fails
            subprocess.CompletedProcess(
                ["git", "ls-remote"], 0, stdout="refs/heads/feature/test", stderr=""
            ),  # remote exists
            subprocess.CompletedProcess(
                ["git", "push"], 1, stdout="", stderr="Permission denied"
            ),  # delete remote fails
            subprocess.CompletedProcess(
                ["git", "ls-remote"], 0, stdout="refs/heads/feature/test", stderr=""
            ),  # still exists check
        ]
        
        result = _clean_single_branch("feature/test", "main", config, db_info)
        
        assert result["branch_name"] == "feature/test"
        assert result["local_delete_status"] == "FAILED"
        assert result["remote_delete_status"] == "FAILED"

    @patch('khive.cli.khive_clean.git_run_clean')
    def test_clean_single_branch_dry_run(self, mock_git_run, temp_dir):
        """Test cleaning in dry run mode."""
        config = CleanConfig(project_root=temp_dir, dry_run=True)
        db_info = {"name": "main"}
        
        # Mock dry run operations - git_run_clean returns CompletedProcess for capture=True, int for others
        mock_git_run.side_effect = [
            subprocess.CompletedProcess(
                ["git", "show-ref"], 0, stdout="DRY_RUN_OUTPUT", stderr=""
            ),  # local exists check (capture=True)
            0,  # local delete (capture=False)
            subprocess.CompletedProcess(
                ["git", "ls-remote"], 0, stdout="DRY_RUN_OUTPUT", stderr=""
            ),  # remote exists (capture=True)
            0,  # remote delete (capture=False)
        ]
        
        result = _clean_single_branch("feature/test", "main", config, db_info)
        
        assert result["branch_name"] == "feature/test"
        assert result["local_delete_status"] == "OK_DRY_RUN"
        assert result["remote_delete_status"] == "OK_DRY_RUN"


class TestMainCleanFlow:
    """Test main clean workflow."""

    @patch('khive.cli.khive_clean.shutil.which')
    @patch('khive.cli.khive_clean.os.chdir')
    @patch('khive.cli.khive_clean.detect_default_branch_clean')
    @patch('khive.cli.khive_clean.get_current_git_branch_clean')
    @patch('khive.cli.khive_clean.git_run_clean')
    @patch('khive.cli.khive_clean._clean_single_branch')
    def test_main_clean_flow_single_branch(self, mock_clean_branch, mock_git_run, 
                                          mock_current_branch, mock_default_branch,
                                          mock_chdir, mock_which, temp_dir):
        """Test main clean flow for single branch."""
        from argparse import Namespace
        
        config = CleanConfig(project_root=temp_dir)
        args = Namespace(
            all_merged=False,
            branch_name="feature/test",
            yes=False
        )
        
        # Setup mocks
        mock_which.return_value = "/usr/bin/git"
        mock_default_branch.return_value = "main"
        mock_current_branch.return_value = "feature/test"
        mock_git_run.side_effect = [0, 0]  # checkout and pull success
        
        mock_clean_result = {
            "branch_name": "feature/test",
            "local_delete_status": "OK",
            "remote_delete_status": "OK",
            "message": "Branch cleaned successfully"
        }
        mock_clean_branch.return_value = mock_clean_result
        
        result = _main_clean_flow(args, config)
        
        assert result["status"] == "success"
        assert len(result["branches_processed"]) == 1
        assert result["branches_processed"][0] == mock_clean_result

    @patch('khive.cli.khive_clean.shutil.which')
    def test_main_clean_flow_no_git(self, mock_which, temp_dir):
        """Test main clean flow when Git is not available."""
        from argparse import Namespace
        
        config = CleanConfig(project_root=temp_dir)
        args = Namespace(all_merged=False, branch_name="feature/test")
        
        mock_which.return_value = None
        
        result = _main_clean_flow(args, config)
        
        assert "Git command not found" in result["message"]

    @patch('khive.cli.khive_clean.shutil.which')
    @patch('khive.cli.khive_clean.os.chdir')
    @patch('khive.cli.khive_clean.detect_default_branch_clean')
    @patch('khive.cli.khive_clean.get_current_git_branch_clean')
    @patch('khive.cli.khive_clean.git_run_clean')
    @patch('khive.cli.khive_clean.get_merged_branches')
    def test_main_clean_flow_all_merged(self, mock_merged_branches, mock_git_run,
                                       mock_current_branch, mock_default_branch,
                                       mock_chdir, mock_which, temp_dir):
        """Test main clean flow for all merged branches."""
        from argparse import Namespace
        
        config = CleanConfig(project_root=temp_dir)
        args = Namespace(
            all_merged=True,
            branch_name=None,
            into=None,
            yes=True
        )
        
        # Setup mocks
        mock_which.return_value = "/usr/bin/git"
        mock_default_branch.return_value = "main"
        mock_current_branch.return_value = "main"
        mock_git_run.side_effect = [0]  # pull success
        mock_merged_branches.return_value = ["feature/merged1", "feature/merged2", "main"]
        
        with patch('khive.cli.khive_clean._clean_single_branch') as mock_clean_branch:
            mock_clean_branch.return_value = {
                "branch_name": "test",
                "local_delete_status": "OK",
                "remote_delete_status": "OK",
                "message": "Cleaned"
            }
            
            result = _main_clean_flow(args, config)
            
            assert result["status"] == "success"
            # Should clean 2 branches (excluding main which is default)
            assert len(result["branches_processed"]) == 2

    @patch('khive.cli.khive_clean.shutil.which')
    @patch('khive.cli.khive_clean.os.chdir')
    @patch('khive.cli.khive_clean.detect_default_branch_clean')
    @patch('khive.cli.khive_clean.get_current_git_branch_clean')
    @patch('khive.cli.khive_clean.git_run_clean')
    def test_main_clean_flow_checkout_failure(self, mock_git_run, mock_current_branch,
                                             mock_default_branch, mock_chdir, mock_which, temp_dir):
        """Test main clean flow when checkout fails."""
        from argparse import Namespace
        
        config = CleanConfig(project_root=temp_dir)
        args = Namespace(
            all_merged=False,
            branch_name="feature/test"
        )
        
        # Setup mocks
        mock_which.return_value = "/usr/bin/git"
        mock_default_branch.return_value = "main"
        mock_current_branch.return_value = "feature/test"
        
        # Mock failed checkout
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.stderr = "error: pathspec 'main' did not match"
        mock_git_run.return_value = mock_process
        
        result = _main_clean_flow(args, config)
        
        assert result["status"] == "failure"
        assert "Failed to checkout default branch" in result["message"]


class TestCLIIntegration:
    """Test CLI entry points and argument parsing."""

    def test_main_function_with_args(self):
        """Test main function with command line arguments."""
        with patch('khive.cli.khive_clean.cli_entry_clean') as mock_cli:
            main(["--dry-run", "feature/test"])
            mock_cli.assert_called_once()

    @patch('khive.cli.khive_clean.sys.argv', ['khive-clean', '--help'])
    def test_cli_entry_help(self):
        """Test CLI entry with help argument."""
        with pytest.raises(SystemExit) as exc_info:
            cli_entry_clean()
        assert exc_info.value.code == 0

    @patch('khive.cli.khive_clean.sys.argv', ['khive-clean'])
    def test_cli_entry_no_branch(self):
        """Test CLI entry without specifying branch or --all-merged."""
        with pytest.raises(SystemExit) as exc_info:
            cli_entry_clean()
        assert exc_info.value.code != 0

    @patch('khive.cli.khive_clean._main_clean_flow')
    @patch('khive.cli.khive_clean.sys.argv', ['khive-clean', 'feature/test'])
    def test_cli_entry_single_branch(self, mock_main_flow, temp_dir):
        """Test CLI entry for single branch cleaning."""
        mock_main_flow.return_value = {
            "status": "success",
            "message": "Branch cleaned successfully",
            "branches_processed": []
        }
        
        with patch('khive.cli.khive_clean.PROJECT_ROOT', temp_dir):
            cli_entry_clean()
            mock_main_flow.assert_called_once()

    @patch('khive.cli.khive_clean._main_clean_flow')
    @patch('khive.cli.khive_clean.sys.argv', ['khive-clean', '--all-merged', '--yes'])
    def test_cli_entry_all_merged(self, mock_main_flow, temp_dir):
        """Test CLI entry for all merged branches."""
        mock_main_flow.return_value = {
            "status": "success",
            "message": "All branches cleaned",
            "branches_processed": []
        }
        
        with patch('khive.cli.khive_clean.PROJECT_ROOT', temp_dir):
            cli_entry_clean()
            mock_main_flow.assert_called_once()

    @patch('khive.cli.khive_clean._main_clean_flow')
    @patch('khive.cli.khive_clean.sys.argv', ['khive-clean', '--json-output', 'feature/test'])
    def test_cli_entry_json_output(self, mock_main_flow, temp_dir, capsys):
        """Test CLI entry with JSON output."""
        result_data = {
            "status": "success",
            "message": "Branch cleaned successfully",
            "branches_processed": [
                {
                    "branch_name": "feature/test",
                    "local_delete_status": "OK",
                    "remote_delete_status": "OK",
                    "message": "Cleaned successfully"
                }
            ]
        }
        mock_main_flow.return_value = result_data
        
        with patch('khive.cli.khive_clean.PROJECT_ROOT', temp_dir):
            cli_entry_clean()
            
        captured = capsys.readouterr()
        output_json = json.loads(captured.out)
        assert output_json["status"] == "success"
        assert len(output_json["branches_processed"]) == 1

    @patch('khive.cli.khive_clean._main_clean_flow')
    @patch('khive.cli.khive_clean.sys.argv', ['khive-clean', '--dry-run', 'feature/test'])
    def test_cli_entry_dry_run(self, mock_main_flow, temp_dir):
        """Test CLI entry with dry run mode."""
        mock_main_flow.return_value = {
            "status": "success",
            "message": "Dry run completed",
            "branches_processed": []
        }
        
        with patch('khive.cli.khive_clean.PROJECT_ROOT', temp_dir):
            cli_entry_clean()
            
        # Verify config was set to dry_run=True
        call_args = mock_main_flow.call_args
        config = call_args[0][1]
        assert config.dry_run is True

    @patch('khive.cli.khive_clean._main_clean_flow')
    @patch('khive.cli.khive_clean.sys.argv', ['khive-clean', 'feature/test'])
    def test_cli_entry_failure_exit_code(self, mock_main_flow, temp_dir):
        """Test CLI entry exits with error code on failure."""
        mock_main_flow.return_value = {
            "status": "failure",
            "message": "Something went wrong",
            "branches_processed": []
        }
        
        with patch('khive.cli.khive_clean.PROJECT_ROOT', temp_dir):
            with pytest.raises(SystemExit) as exc_info:
                cli_entry_clean()
            assert exc_info.value.code == 1


class TestErrorScenarios:
    """Test various error scenarios and edge cases."""

    @patch('khive.cli.khive_clean.sys.argv', ['khive-clean', '--project-root', '/nonexistent', 'feature/test'])
    def test_invalid_project_root(self):
        """Test handling of invalid project root directory."""
        with pytest.raises(SystemExit):
            cli_entry_clean()

    @patch('khive.cli.khive_clean.os.chdir')
    @patch('khive.cli.khive_clean.shutil.which')
    def test_chdir_failure(self, mock_which, mock_chdir, temp_dir):
        """Test handling when changing to project directory fails."""
        from argparse import Namespace
        
        config = CleanConfig(project_root=temp_dir)
        args = Namespace(all_merged=False, branch_name="feature/test")
        
        mock_which.return_value = "/usr/bin/git"
        mock_chdir.side_effect = FileNotFoundError("Directory not found")
        
        result = _main_clean_flow(args, config)
        
        # In non-dry-run mode, should fail
        assert "Project root directory not found" in result["message"]

    @patch('khive.cli.khive_clean.shutil.which')
    @patch('khive.cli.khive_clean.os.chdir')
    @patch('khive.cli.khive_clean.detect_default_branch_clean')
    @patch('khive.cli.khive_clean.get_current_git_branch_clean')
    @patch('khive.cli.khive_clean.git_run_clean')
    def test_strict_pull_failure(self, mock_git_run, mock_current_branch, 
                                mock_default_branch, mock_chdir, mock_which, temp_dir):
        """Test strict pull failure handling."""
        from argparse import Namespace
        
        config = CleanConfig(project_root=temp_dir, strict_pull_on_default=True)
        args = Namespace(all_merged=False, branch_name="feature/test")
        
        # Setup mocks
        mock_which.return_value = "/usr/bin/git"
        mock_default_branch.return_value = "main"
        mock_current_branch.return_value = "main"
        
        # Mock successful checkout but failed pull
        mock_git_run.side_effect = [
            Mock(returncode=1, stderr="Pull failed")  # pull fails
        ]
        
        result = _main_clean_flow(args, config)
        
        assert result["status"] == "failure"
        assert "Strict pull enabled and failed" in result["message"]

    def test_load_config_file_not_readable(self, temp_dir):
        """Test handling when config file exists but can't be read."""
        khive_dir = temp_dir / ".khive"
        khive_dir.mkdir()
        config_file = khive_dir / "clean.toml"
        config_file.write_text("valid config")
        
        # Mock file read failure
        with patch('pathlib.Path.read_text', side_effect=PermissionError("Permission denied")):
            with patch('khive.cli.khive_clean.warn_msg_clean') as mock_warn:
                config = load_clean_config(temp_dir)
                
                # Should fall back to defaults
                assert config.protected_branch_patterns == ["release/*", "develop"]
                mock_warn.assert_called()


class TestDryRunMode:
    """Test dry run mode functionality."""

    @patch('khive.cli.khive_clean.shutil.which')
    @patch('khive.cli.khive_clean.os.chdir')
    @patch('khive.cli.khive_clean.detect_default_branch_clean')
    @patch('khive.cli.khive_clean.get_current_git_branch_clean')
    def test_dry_run_messages(self, mock_current_branch, mock_default_branch, 
                             mock_chdir, mock_which, temp_dir, capsys):
        """Test that dry run mode shows appropriate messages."""
        from argparse import Namespace
        
        config = CleanConfig(project_root=temp_dir, dry_run=True)
        args = Namespace(
            all_merged=True,
            branch_name=None,
            into=None,
            yes=True
        )
        
        # Setup mocks
        mock_which.return_value = "/usr/bin/git"
        mock_default_branch.return_value = "main"
        mock_current_branch.return_value = "main"
        
        with patch('khive.cli.khive_clean.get_merged_branches') as mock_merged:
            mock_merged.return_value = ["feature/test1", "feature/test2"]
            
            result = _main_clean_flow(args, config)
            
            assert result["status"] == "success"
            # Check that dry run message is shown
            assert "Dry run completed" in result["message"]

    def test_dry_run_no_actual_operations(self, temp_dir):
        """Test that dry run mode doesn't perform actual Git operations."""
        config = CleanConfig(project_root=temp_dir, dry_run=True)
        
        # These should return mock values without calling git
        current_branch = get_current_git_branch_clean(config)
        assert current_branch == "main"
        
        merged_branches = get_merged_branches("main", config)
        assert merged_branches == ["feature/dry-merged-1", "feature/dry-merged-2"]