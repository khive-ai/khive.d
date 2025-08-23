"""Comprehensive tests for CLI base framework functionality.

Tests the base CLI command classes, argument parsing, configuration management,
workflow systems, and factory patterns.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from khive.cli.base import (BaseCLICommand, CLICommandFactory, CLIResult,
                            CommandWorkflow, ConfigurableCLICommand,
                            FileBasedCLICommand, GitBasedCLICommand,
                            WorkflowStep, cli_command)
from khive.utils import BaseConfig


class TestCLIResult:
    """Test CLIResult data class functionality."""

    def test_cli_result_creation(self):
        """Test basic CLIResult creation."""
        result = CLIResult(status="success", message="Test message")

        assert result.status == "success"
        assert result.message == "Test message"
        assert result.data is None
        assert result.exit_code == 0

    def test_cli_result_with_data(self):
        """Test CLIResult with data."""
        data = {"key": "value", "count": 42}
        result = CLIResult(
            status="success", message="Test message", data=data, exit_code=0
        )

        assert result.data == data
        assert result.data["key"] == "value"
        assert result.data["count"] == 42

    def test_cli_result_is_success(self):
        """Test is_success method for different statuses."""
        success_statuses = ["success", "skipped", "dry_run"]
        failure_statuses = ["failure", "error", "invalid"]

        for status in success_statuses:
            result = CLIResult(status=status, message="test")
            assert result.is_success() is True

        for status in failure_statuses:
            result = CLIResult(status=status, message="test")
            assert result.is_success() is False

    def test_cli_result_to_dict(self):
        """Test to_dict method."""
        # Without data
        result = CLIResult(status="success", message="Test message")
        dict_result = result.to_dict()

        expected = {"status": "success", "message": "Test message"}
        assert dict_result == expected

        # With data
        data = {"extra": "info"}
        result = CLIResult(status="success", message="Test message", data=data)
        dict_result = result.to_dict()

        expected = {"status": "success", "message": "Test message", "extra": "info"}
        assert dict_result == expected

    def test_cli_result_exit_codes(self):
        """Test various exit codes."""
        result = CLIResult(status="success", message="test", exit_code=0)
        assert result.exit_code == 0

        result = CLIResult(status="error", message="test", exit_code=1)
        assert result.exit_code == 1

        result = CLIResult(status="failure", message="test", exit_code=2)
        assert result.exit_code == 2


class MockCLICommand(BaseCLICommand):
    """Mock CLI command for testing abstract base class."""

    def __init__(self, command_name="test", description="Test command"):
        super().__init__(command_name, description)
        self.config_created = False
        self.executed = False

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--test-arg", help="Test argument")

    def _create_config(self, args: argparse.Namespace) -> BaseConfig:
        self.config_created = True
        return BaseConfig()  # Assuming BaseConfig exists

    def _execute(self, args: argparse.Namespace, config: BaseConfig) -> CLIResult:
        self.executed = True
        return CLIResult(status="success", message="Test executed")


class AsyncMockCLICommand(BaseCLICommand):
    """Mock async CLI command for testing async execution."""

    def __init__(self, command_name="async_test", description="Async test command"):
        super().__init__(command_name, description)
        self.executed = False

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--async-arg", help="Async test argument")

    def _create_config(self, args: argparse.Namespace) -> BaseConfig:
        return BaseConfig()

    async def _execute(self, args: argparse.Namespace, config: BaseConfig) -> CLIResult:
        self.executed = True
        return CLIResult(status="success", message="Async test executed")


class TestBaseCLICommand:
    """Test BaseCLICommand abstract base class."""

    def test_base_command_initialization(self):
        """Test basic command initialization."""
        cmd = MockCLICommand("test_cmd", "Test description")

        assert cmd.command_name == "test_cmd"
        assert cmd.description == "Test description"
        assert isinstance(cmd.parser, argparse.ArgumentParser)
        assert cmd.config is None

    def test_parser_creation_standard_arguments(self):
        """Test that parser includes standard arguments."""
        cmd = MockCLICommand()
        parser = cmd.parser

        # Get all argument names
        arg_names = []
        for action in parser._actions:
            if action.dest != "help":
                arg_names.append(action.dest)

        expected_args = [
            "project_root",
            "json_output",
            "dry_run",
            "verbose",
            "test_arg",
        ]
        for arg in expected_args:
            assert arg in arg_names

    def test_custom_arguments_added(self):
        """Test that custom arguments are added."""
        cmd = MockCLICommand()

        # Check that test_arg was added by _add_arguments
        arg_names = [action.dest for action in cmd.parser._actions]
        assert "test_arg" in arg_names

    @patch("khive.cli.base.get_project_root")
    def test_argument_parsing(self, mock_get_root):
        """Test argument parsing functionality."""
        mock_get_root.return_value = Path("/test/root")

        cmd = MockCLICommand()

        # Test basic parsing
        args = cmd.parser.parse_args(["--test-arg", "value"])
        assert args.test_arg == "value"
        assert args.json_output is False
        assert args.dry_run is False
        assert args.verbose is False

    @patch("khive.cli.base.get_project_root")
    def test_argument_parsing_with_flags(self, mock_get_root):
        """Test argument parsing with flags."""
        mock_get_root.return_value = Path("/test/root")

        cmd = MockCLICommand()

        # Test flag parsing
        args = cmd.parser.parse_args(["--json-output", "--dry-run", "--verbose"])
        assert args.json_output is True
        assert args.dry_run is True
        assert args.verbose is True

    @patch("khive.cli.base.validate_directory")
    @patch("khive.cli.base.get_project_root")
    def test_argument_validation(self, mock_get_root, mock_validate):
        """Test argument validation."""
        mock_get_root.return_value = Path("/test/root")

        cmd = MockCLICommand()
        args = argparse.Namespace(project_root=Path("/test/root"))

        cmd._validate_args(args)
        mock_validate.assert_called_once_with(Path("/test/root"), "project root")

    @patch("khive.cli.base.validate_directory")
    @patch("khive.cli.base.get_project_root")
    def test_run_method_success(self, mock_get_root, mock_validate):
        """Test successful run method execution."""
        mock_get_root.return_value = Path("/test/root")

        cmd = MockCLICommand()

        # Mock sys.argv to avoid interference
        with patch.object(sys, "argv", ["test_cmd"]):
            exit_code = cmd.run([])

        assert exit_code == 0
        assert cmd.config_created is True
        assert cmd.executed is True

    @patch("khive.cli.base.get_project_root")
    def test_run_method_keyboard_interrupt(self, mock_get_root, capsys):
        """Test run method handles KeyboardInterrupt."""
        mock_get_root.return_value = Path("/test/root")

        cmd = MockCLICommand()
        # Mock _execute to raise KeyboardInterrupt
        cmd._execute = Mock(side_effect=KeyboardInterrupt())

        exit_code = cmd.run([])

        assert exit_code == 130
        captured = capsys.readouterr()
        assert "interrupted" in captured.err

    @patch("khive.cli.base.get_project_root")
    def test_run_method_unexpected_exception(self, mock_get_root, capsys):
        """Test run method handles unexpected exceptions."""
        mock_get_root.return_value = Path("/test/root")

        cmd = MockCLICommand()
        cmd._execute = Mock(side_effect=ValueError("Test error"))

        exit_code = cmd.run([])

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Unexpected error" in captured.err

    @patch("khive.cli.base.get_project_root")
    def test_json_output_handling(self, mock_get_root, capsys):
        """Test JSON output formatting."""
        mock_get_root.return_value = Path("/test/root")

        cmd = MockCLICommand()

        with patch.object(sys, "argv", ["test_cmd"]):
            exit_code = cmd.run(["--json-output"])

        assert exit_code == 0
        captured = capsys.readouterr()

        # Should output JSON
        try:
            json.loads(captured.out)
        except json.JSONDecodeError:
            pytest.fail("Output should be valid JSON")

    @patch("khive.cli.base.get_project_root")
    def test_verbose_mode_setting(self, mock_get_root):
        """Test that verbose mode is set globally."""
        mock_get_root.return_value = Path("/test/root")

        cmd = MockCLICommand()

        with patch.object(sys, "argv", ["test_cmd"]):
            # Mock the global verbose_mode setting
            with patch("khive.cli.base.verbose_mode", None) as mock_verbose:
                cmd.run(["--verbose"])
                # The verbose flag should be processed


class TestAsyncCLICommand:
    """Test async CLI command execution."""

    @patch("khive.cli.base.get_project_root")
    @patch("khive.cli.base.validate_directory")
    def test_async_command_execution(self, mock_validate, mock_get_root):
        """Test async command execution."""
        mock_get_root.return_value = Path("/test/root")

        cmd = AsyncMockCLICommand()

        with patch.object(sys, "argv", ["async_test"]):
            exit_code = cmd.run([])

        assert exit_code == 0
        assert cmd.executed is True

    @patch("khive.cli.base.get_project_root")
    @patch("khive.cli.base.validate_directory")
    def test_async_command_with_existing_loop(self, mock_validate, mock_get_root):
        """Test async command execution when event loop already exists."""
        mock_get_root.return_value = Path("/test/root")

        cmd = AsyncMockCLICommand()

        # Mock get_running_loop to simulate existing loop
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop

            with patch.object(sys, "argv", ["async_test"]):
                exit_code = cmd.run([])

            assert exit_code == 0


class MockConfigurableCommand(ConfigurableCLICommand):
    """Mock configurable command for testing."""

    @property
    def config_filename(self) -> str:
        return "test.toml"

    @property
    def default_config(self) -> dict[str, Any]:
        return {"key": "default_value", "number": 42}

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--config-arg", help="Config test argument")

    def _create_config(self, args: argparse.Namespace) -> BaseConfig:
        return BaseConfig()

    def _execute(self, args: argparse.Namespace, config: BaseConfig) -> CLIResult:
        return CLIResult(status="success", message="Config test executed")


class TestConfigurableCLICommand:
    """Test ConfigurableCLICommand functionality."""

    def test_config_filename_property(self):
        """Test config_filename abstract property."""
        cmd = MockConfigurableCommand("config_test", "Config test")
        assert cmd.config_filename == "test.toml"

    def test_default_config_property(self):
        """Test default_config abstract property."""
        cmd = MockConfigurableCommand("config_test", "Config test")
        expected = {"key": "default_value", "number": 42}
        assert cmd.default_config == expected

    @patch("khive.cli.base.load_toml_config")
    def test_load_command_config(self, mock_load_toml):
        """Test loading command configuration."""
        mock_load_toml.return_value = {"key": "file_value", "extra": "from_file"}

        cmd = MockConfigurableCommand("config_test", "Config test")
        project_root = Path("/test/project")

        config = cmd._load_command_config(project_root)

        # Should merge default config with file config
        expected = {
            "key": "file_value",  # File value overrides default
            "number": 42,  # Default value preserved
            "extra": "from_file",  # New value from file
        }
        assert config == expected

        # Verify the config file path
        expected_path = project_root / ".khive" / "test.toml"
        mock_load_toml.assert_called_once_with(expected_path)


class MockGitCommand(GitBasedCLICommand):
    """Mock git-based command for testing."""

    @property
    def config_filename(self) -> str:
        return "git_test.toml"

    @property
    def default_config(self) -> dict[str, Any]:
        return {"git_setting": "default"}

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--git-arg", help="Git test argument")

    def _create_config(self, args: argparse.Namespace) -> BaseConfig:
        return BaseConfig()

    def _execute(self, args: argparse.Namespace, config: BaseConfig) -> CLIResult:
        return CLIResult(status="success", message="Git test executed")


class TestGitBasedCLICommand:
    """Test GitBasedCLICommand functionality."""

    @patch("khive.cli.base.validate_directory")
    def test_git_validation_success(self, mock_validate):
        """Test successful Git repository validation."""
        cmd = MockGitCommand("git_test", "Git test")

        # Mock a Git repository
        project_root = Path("/test/git/repo")
        git_dir = project_root / ".git"

        with patch.object(git_dir, "exists", return_value=True):
            args = argparse.Namespace(project_root=project_root)
            cmd._validate_args(args)

        mock_validate.assert_called_once()

    def test_git_validation_failure(self):
        """Test Git repository validation failure."""
        cmd = MockGitCommand("git_test", "Git test")

        project_root = Path("/test/not/git/repo")
        git_dir = project_root / ".git"

        with patch.object(git_dir, "exists", return_value=False):
            with patch("khive.cli.base.validate_directory"):
                args = argparse.Namespace(project_root=project_root)

                with pytest.raises(SystemExit):
                    with patch("khive.cli.base.die") as mock_die:
                        cmd._validate_args(args)
                        mock_die.assert_called_once()

    @patch("khive.cli.base.git_run")
    def test_get_current_branch_success(self, mock_git_run):
        """Test successful current branch retrieval."""
        cmd = MockGitCommand("git_test", "Git test")

        # Mock successful git branch --show-current
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = "main\n"
        mock_git_run.return_value = mock_result

        project_root = Path("/test/repo")
        branch = cmd._get_current_branch(project_root)

        assert branch == "main"
        mock_git_run.assert_called_once_with(
            ["branch", "--show-current"], capture=True, check=False, cwd=project_root
        )

    @patch("khive.cli.base.git_run")
    def test_get_current_branch_detached_head(self, mock_git_run):
        """Test current branch retrieval for detached HEAD."""
        cmd = MockGitCommand("git_test", "Git test")

        # First call fails (no current branch)
        mock_result_fail = Mock()
        mock_result_fail.success = False
        mock_result_fail.stdout = ""

        # Second call succeeds (get HEAD hash)
        mock_result_success = Mock()
        mock_result_success.stdout = "abc1234\n"

        mock_git_run.side_effect = [mock_result_fail, mock_result_success]

        project_root = Path("/test/repo")
        branch = cmd._get_current_branch(project_root)

        assert branch == "detached-HEAD-abc1234"
        assert mock_git_run.call_count == 2


class TestFileBasedCLICommand:
    """Test FileBasedCLICommand functionality."""

    class MockFileCommand(FileBasedCLICommand):
        def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
            self._add_file_arguments(parser)

        def _create_config(self, args: argparse.Namespace) -> BaseConfig:
            return BaseConfig()

        def _execute(self, args: argparse.Namespace, config: BaseConfig) -> CLIResult:
            return CLIResult(status="success", message="File test executed")

    def test_file_arguments_added(self):
        """Test that file-related arguments are added."""
        cmd = self.MockFileCommand("file_test", "File test")

        arg_names = [action.dest for action in cmd.parser._actions]
        assert "force" in arg_names


class TestCLICommandFactory:
    """Test CLI command factory functionality."""

    def test_factory_registration(self):
        """Test command registration."""

        class TestCommand(BaseCLICommand):
            def _add_arguments(self, parser):
                pass

            def _create_config(self, args):
                return BaseConfig()

            def _execute(self, args, config):
                return CLIResult("success", "test")

        CLICommandFactory.register("test_factory", TestCommand)

        assert "test_factory" in CLICommandFactory._commands
        assert CLICommandFactory._commands["test_factory"] is TestCommand

    def test_factory_creation(self):
        """Test command creation from factory."""

        class TestCommand(BaseCLICommand):
            def _add_arguments(self, parser):
                pass

            def _create_config(self, args):
                return BaseConfig()

            def _execute(self, args, config):
                return CLIResult("success", "test")

        CLICommandFactory.register("test_create", TestCommand)

        cmd = CLICommandFactory.create("test_create", "test_name", "test_desc")
        assert isinstance(cmd, TestCommand)
        assert cmd.command_name == "test_name"
        assert cmd.description == "test_desc"

    def test_factory_unknown_command(self):
        """Test creating unknown command raises error."""
        with pytest.raises(ValueError, match="Unknown command"):
            CLICommandFactory.create("unknown_command")

    def test_factory_list_commands(self):
        """Test listing registered commands."""
        # Clear any existing commands for clean test
        original_commands = CLICommandFactory._commands.copy()
        CLICommandFactory._commands.clear()

        try:

            class TestCommand1(BaseCLICommand):
                def _add_arguments(self, parser):
                    pass

                def _create_config(self, args):
                    return BaseConfig()

                def _execute(self, args, config):
                    return CLIResult("success", "test")

            class TestCommand2(BaseCLICommand):
                def _add_arguments(self, parser):
                    pass

                def _create_config(self, args):
                    return BaseConfig()

                def _execute(self, args, config):
                    return CLIResult("success", "test")

            CLICommandFactory.register("cmd1", TestCommand1)
            CLICommandFactory.register("cmd2", TestCommand2)

            commands = CLICommandFactory.list_commands()
            assert "cmd1" in commands
            assert "cmd2" in commands
            assert len(commands) == 2

        finally:
            # Restore original commands
            CLICommandFactory._commands = original_commands

    def test_cli_command_decorator(self):
        """Test cli_command decorator."""

        @cli_command("decorated_test")
        class DecoratedCommand(BaseCLICommand):
            def _add_arguments(self, parser):
                pass

            def _create_config(self, args):
                return BaseConfig()

            def _execute(self, args, config):
                return CLIResult("success", "test")

        assert "decorated_test" in CLICommandFactory._commands
        assert CLICommandFactory._commands["decorated_test"] is DecoratedCommand


class TestWorkflowSystem:
    """Test workflow management system."""

    def test_workflow_step_creation(self):
        """Test WorkflowStep creation."""
        step = WorkflowStep("test_step", "Test step description")

        assert step.name == "test_step"
        assert step.description == "Test step description"
        assert step.required is True
        assert step.completed is False
        assert step.error is None

    def test_workflow_step_optional(self):
        """Test optional WorkflowStep creation."""
        step = WorkflowStep("optional_step", "Optional step", required=False)

        assert step.required is False

    def test_command_workflow_creation(self):
        """Test CommandWorkflow creation."""
        workflow = CommandWorkflow("test_workflow")

        assert workflow.name == "test_workflow"
        assert workflow.steps == []
        assert workflow.current_step == 0

    def test_workflow_add_step(self):
        """Test adding steps to workflow."""
        workflow = CommandWorkflow("test_workflow")
        step1 = WorkflowStep("step1", "First step")
        step2 = WorkflowStep("step2", "Second step")

        workflow.add_step(step1)
        workflow.add_step(step2)

        assert len(workflow.steps) == 2
        assert workflow.steps[0] is step1
        assert workflow.steps[1] is step2

    @patch("khive.cli.base.print_step")
    def test_workflow_execute_step_success(self, mock_print_step):
        """Test successful step execution."""
        workflow = CommandWorkflow("test_workflow")
        step = WorkflowStep("test_step", "Test step")
        workflow.add_step(step)

        # Mock executor that returns True (success)
        executor = Mock(return_value=True)

        result = workflow.execute_step(0, executor)

        assert result is True
        assert step.completed is True
        executor.assert_called_once_with(step)
        assert mock_print_step.call_count == 2  # running and success

    @patch("khive.cli.base.print_step")
    def test_workflow_execute_step_failure_required(self, mock_print_step):
        """Test failed step execution for required step."""
        workflow = CommandWorkflow("test_workflow")
        step = WorkflowStep("test_step", "Test step", required=True)
        workflow.add_step(step)

        # Mock executor that returns False (failure)
        executor = Mock(return_value=False)

        result = workflow.execute_step(0, executor)

        assert result is False
        assert step.completed is False

    @patch("khive.cli.base.print_step")
    def test_workflow_execute_step_failure_optional(self, mock_print_step):
        """Test failed step execution for optional step."""
        workflow = CommandWorkflow("test_workflow")
        step = WorkflowStep("test_step", "Test step", required=False)
        workflow.add_step(step)

        # Mock executor that returns False (failure)
        executor = Mock(return_value=False)

        result = workflow.execute_step(0, executor)

        assert result is True  # Should continue for optional steps
        assert step.completed is False

    @patch("khive.cli.base.print_step")
    def test_workflow_execute_step_exception_required(self, mock_print_step):
        """Test step execution with exception for required step."""
        workflow = CommandWorkflow("test_workflow")
        step = WorkflowStep("test_step", "Test step", required=True)
        workflow.add_step(step)

        # Mock executor that raises exception
        executor = Mock(side_effect=ValueError("Test error"))

        result = workflow.execute_step(0, executor)

        assert result is False
        assert step.error == "Test error"

    @patch("khive.cli.base.print_step")
    def test_workflow_execute_step_exception_optional(self, mock_print_step):
        """Test step execution with exception for optional step."""
        workflow = CommandWorkflow("test_workflow")
        step = WorkflowStep("test_step", "Test step", required=False)
        workflow.add_step(step)

        # Mock executor that raises exception
        executor = Mock(side_effect=ValueError("Test error"))

        result = workflow.execute_step(0, executor)

        assert result is True  # Should continue for optional steps
        assert step.error == "Test error"

    def test_workflow_execute_step_invalid_index(self):
        """Test executing step with invalid index."""
        workflow = CommandWorkflow("test_workflow")
        executor = Mock()

        result = workflow.execute_step(5, executor)

        assert result is False
        executor.assert_not_called()

    def test_workflow_execute_all_success(self):
        """Test executing all steps successfully."""
        workflow = CommandWorkflow("test_workflow")
        step1 = WorkflowStep("step1", "First step")
        step2 = WorkflowStep("step2", "Second step")
        workflow.add_step(step1)
        workflow.add_step(step2)

        # Mock executor that always succeeds
        executor = Mock(return_value=True)

        with patch("khive.cli.base.print_step"):
            result = workflow.execute_all(executor)

        assert result is True
        assert step1.completed is True
        assert step2.completed is True
        assert executor.call_count == 2

    def test_workflow_execute_all_with_failure(self):
        """Test executing all steps with one failure."""
        workflow = CommandWorkflow("test_workflow")
        step1 = WorkflowStep("step1", "First step")
        step2 = WorkflowStep("step2", "Second step", required=True)
        workflow.add_step(step1)
        workflow.add_step(step2)

        # Mock executor: first succeeds, second fails
        executor = Mock(side_effect=[True, False])

        with patch("khive.cli.base.print_step"):
            result = workflow.execute_all(executor)

        assert result is False
        assert step1.completed is True
        assert step2.completed is False

    def test_workflow_get_status(self):
        """Test workflow status reporting."""
        workflow = CommandWorkflow("test_workflow")
        step1 = WorkflowStep("step1", "First step")
        step2 = WorkflowStep("step2", "Second step")
        step1.completed = True
        step2.error = "Test error"

        workflow.add_step(step1)
        workflow.add_step(step2)

        status = workflow.get_status()

        assert status["name"] == "test_workflow"
        assert status["total_steps"] == 2
        assert status["completed_steps"] == 1
        assert status["failed_steps"] == 1
        assert len(status["steps"]) == 2

        step1_status = status["steps"][0]
        assert step1_status["name"] == "step1"
        assert step1_status["completed"] is True
        assert step1_status["error"] is None

        step2_status = status["steps"][1]
        assert step2_status["name"] == "step2"
        assert step2_status["completed"] is False
        assert step2_status["error"] == "Test error"
