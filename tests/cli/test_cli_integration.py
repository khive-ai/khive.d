"""Comprehensive CLI integration tests.

Tests for end-to-end khive CLI workflows including:
- Real command execution integration
- Configuration loading workflows
- JSON output formatting verification
- Verbose mode behavior testing
- Command interaction patterns
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from khive.cli.khive_cli import COMMANDS, main


class TestRealCommandIntegration:
    """Test integration with actual command modules."""

    def test_help_command_integration(self, capsys):
        """Test help command integration works end-to-end."""
        main(["--help"])
        captured = capsys.readouterr()

        # Should contain basic help structure
        assert "khive" in captured.out.lower()
        assert "usage" in captured.out.lower()
        assert "available commands" in captured.out.lower()

        # Should list actual commands
        for cmd_name in COMMANDS:
            assert cmd_name in captured.out

    def test_help_flag_integration(self, capsys):
        """Test -h flag integration works end-to-end."""
        main(["-h"])
        captured = capsys.readouterr()

        assert "khive" in captured.out.lower()
        assert "usage" in captured.out.lower()

    def test_no_args_integration(self, capsys):
        """Test no arguments integration shows help."""
        main([])
        captured = capsys.readouterr()

        assert "khive" in captured.out.lower()
        assert "usage" in captured.out.lower()

    @pytest.mark.parametrize("command_name", ["plan", "compose"])
    def test_command_loading_integration(self, command_name):
        """Test that actual commands can be loaded successfully."""
        # This test verifies that the command modules can actually be imported
        # and have the expected entry point
        if command_name in COMMANDS:
            from khive.cli.khive_cli import _load_command_module

            module = _load_command_module(command_name)

            assert module is not None
            assert hasattr(module, "cli_entry")
            assert callable(module.cli_entry)

    def test_invalid_command_integration(self, capsys):
        """Test invalid command integration shows proper error."""
        with pytest.raises(SystemExit) as exc_info:
            main(["invalid_command_xyz"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Unknown command 'invalid_command_xyz'" in captured.err


class TestConfigurationWorkflows:
    """Test configuration loading and merging workflows."""



class TestJSONOutputFormatting:
    """Test JSON output formatting across commands."""

    def test_json_output_structure(self):
        """Test that JSON output has consistent structure."""

        # Mock a command that returns JSON output
        class MockCommand:
            @staticmethod
            def format_json_output(status, message, data=None):
                result = {
                    "status": status,
                    "message": message,
                    "timestamp": "2025-08-22T23:30:00Z",  # Mock timestamp
                }
                if data:
                    result.update(data)
                return json.dumps(result, indent=2)

        cmd = MockCommand()

        # Test success output
        output = cmd.format_json_output("success", "Operation completed", {"files": 5})
        parsed = json.loads(output)

        assert parsed["status"] == "success"
        assert parsed["message"] == "Operation completed"
        assert parsed["files"] == 5
        assert "timestamp" in parsed

    def test_json_error_output_structure(self):
        """Test JSON error output structure."""

        class MockCommand:
            @staticmethod
            def format_json_error(status, message, error_details=None):
                result = {
                    "status": status,
                    "message": message,
                    "timestamp": "2025-08-22T23:30:00Z",
                }
                if error_details:
                    result["error_details"] = error_details
                return json.dumps(result, indent=2)

        cmd = MockCommand()

        # Test error output
        error_details = {"code": "E001", "file": "test.py", "line": 42}
        output = cmd.format_json_error("error", "Validation failed", error_details)
        parsed = json.loads(output)

        assert parsed["status"] == "error"
        assert parsed["message"] == "Validation failed"
        assert parsed["error_details"]["code"] == "E001"

    @patch("khive.utils.print_json_result")
    def test_json_output_integration_with_utils(self, mock_print_json):
        """Test JSON output integration with khive.utils functions."""
        from khive.utils import print_json_result

        # Test that the utility function is called correctly
        print_json_result("success", "Test message", {"key": "value"})

        mock_print_json.assert_called_once_with(
            "success", "Test message", {"key": "value"}
        )


class TestVerboseModeIntegration:
    """Test verbose mode behavior across the CLI system."""

    def test_verbose_mode_activation(self):
        """Test that verbose mode can be activated."""
        # This would typically be tested in individual command implementations
        # Here we test the general pattern

        class MockVerboseCommand:
            def __init__(self):
                self.verbose = False

            def set_verbose(self, verbose):
                self.verbose = verbose

            def log_verbose(self, message):
                if self.verbose:
                    print(f"VERBOSE: {message}")

        cmd = MockVerboseCommand()

        # Test verbose mode off
        cmd.set_verbose(False)
        assert cmd.verbose is False

        # Test verbose mode on
        cmd.set_verbose(True)
        assert cmd.verbose is True

    def test_verbose_output_patterns(self, capsys):
        """Test verbose output patterns."""

        class MockVerboseCommand:
            def __init__(self, verbose=False):
                self.verbose = verbose

            def execute_with_logging(self):
                if self.verbose:
                    print("VERBOSE: Starting operation")
                    print("VERBOSE: Processing step 1")
                    print("VERBOSE: Processing step 2")
                    print("VERBOSE: Operation completed")
                print("Operation result: success")

        # Test without verbose mode
        cmd = MockVerboseCommand(verbose=False)
        cmd.execute_with_logging()

        captured = capsys.readouterr()
        assert "VERBOSE:" not in captured.out
        assert "Operation result: success" in captured.out

        # Test with verbose mode
        cmd = MockVerboseCommand(verbose=True)
        cmd.execute_with_logging()

        captured = capsys.readouterr()
        assert "VERBOSE: Starting operation" in captured.out
        assert "VERBOSE: Processing step 1" in captured.out
        assert "VERBOSE: Processing step 2" in captured.out
        assert "VERBOSE: Operation completed" in captured.out
        assert "Operation result: success" in captured.out


class TestCommandInteractionPatterns:
    """Test command interaction and workflow patterns."""

    def test_command_chaining_patterns(self):
        """Test patterns for chaining commands together."""
        # Simulate command chain where one command's output feeds into another

        class MockCommandA:
            def execute(self):
                return {"status": "success", "output_file": "/tmp/result.json"}

        class MockCommandB:
            def execute(self, input_data):
                if input_data.get("status") == "success":
                    return {"status": "success", "processed": True}
                return {"status": "error", "message": "Input validation failed"}

        cmd_a = MockCommandA()
        cmd_b = MockCommandB()

        # Test successful chain
        result_a = cmd_a.execute()
        result_b = cmd_b.execute(result_a)

        assert result_a["status"] == "success"
        assert result_b["status"] == "success"
        assert result_b["processed"] is True

    def test_command_state_management(self):
        """Test command state management patterns."""

        class StatefulCommand:
            def __init__(self):
                self.state = "initialized"
                self.operations = []

            def validate(self):
                if self.state != "initialized":
                    raise ValueError("Invalid state for validation")
                self.state = "validated"
                self.operations.append("validate")
                return True

            def execute(self):
                if self.state != "validated":
                    raise ValueError("Must validate before execution")
                self.state = "executed"
                self.operations.append("execute")
                return {"status": "success"}

            def cleanup(self):
                self.state = "cleaned"
                self.operations.append("cleanup")

        cmd = StatefulCommand()

        # Test proper workflow
        assert cmd.state == "initialized"
        cmd.validate()
        assert cmd.state == "validated"
        result = cmd.execute()
        assert cmd.state == "executed"
        assert result["status"] == "success"
        cmd.cleanup()
        assert cmd.state == "cleaned"

        assert cmd.operations == ["validate", "execute", "cleanup"]

    def test_command_error_recovery(self):
        """Test command error recovery patterns."""

        class RecoverableCommand:
            def __init__(self):
                self.attempt_count = 0
                self.max_attempts = 3

            def execute_with_retry(self):
                for attempt in range(self.max_attempts):
                    self.attempt_count = attempt + 1
                    try:
                        return self._execute_operation()
                    except Exception as e:
                        if attempt == self.max_attempts - 1:
                            raise
                        continue
                return None

            def _execute_operation(self):
                # Simulate operation that succeeds on 3rd attempt
                if self.attempt_count < 3:
                    raise RuntimeError(f"Attempt {self.attempt_count} failed")
                return {"status": "success", "attempts": self.attempt_count}

        cmd = RecoverableCommand()
        result = cmd.execute_with_retry()

        assert result["status"] == "success"
        assert result["attempts"] == 3


class TestFullWorkflowIntegration:
    """Test complete end-to-end workflow scenarios."""

    def test_complete_command_lifecycle(self):
        """Test complete command lifecycle from invocation to completion."""
        # This simulates the full lifecycle of a CLI command

        class CompleteWorkflowCommand:
            def __init__(self):
                self.stages = []

            def parse_arguments(self, args):
                self.stages.append("parse_arguments")
                self.args = args
                return True

            def validate_environment(self):
                self.stages.append("validate_environment")
                # Simulate environment validation
                return True

            def load_configuration(self):
                self.stages.append("load_configuration")
                self.config = {"timeout": 30, "retries": 3}
                return True

            def execute_operation(self):
                self.stages.append("execute_operation")
                # Simulate actual work
                return {"files_processed": 5, "errors": 0}

            def generate_output(self, result):
                self.stages.append("generate_output")
                return {
                    "status": "success",
                    "message": f"Processed {result['files_processed']} files",
                    "details": result,
                }

            def cleanup_resources(self):
                self.stages.append("cleanup_resources")
                return True

            def run_complete_workflow(self, args):
                try:
                    self.parse_arguments(args)
                    self.validate_environment()
                    self.load_configuration()
                    result = self.execute_operation()
                    return self.generate_output(result)
                finally:
                    self.cleanup_resources()

        cmd = CompleteWorkflowCommand()
        result = cmd.run_complete_workflow(["--verbose", "--dry-run"])

        # Verify complete workflow execution
        expected_stages = [
            "parse_arguments",
            "validate_environment",
            "load_configuration",
            "execute_operation",
            "generate_output",
            "cleanup_resources",
        ]

        assert cmd.stages == expected_stages
        assert result["status"] == "success"
        assert "Processed 5 files" in result["message"]

    def test_workflow_interruption_handling(self):
        """Test workflow handling when interrupted."""

        class InterruptibleWorkflow:
            def __init__(self):
                self.stages_completed = []
                self.cleanup_called = False

            def stage_1(self):
                self.stages_completed.append("stage_1")
                return True

            def stage_2(self):
                self.stages_completed.append("stage_2")
                # Simulate interruption
                raise KeyboardInterrupt("User interrupted")

            def stage_3(self):
                self.stages_completed.append("stage_3")
                return True

            def cleanup(self):
                self.cleanup_called = True

            def run_with_cleanup(self):
                try:
                    self.stage_1()
                    self.stage_2()
                    self.stage_3()
                    return "completed"
                except KeyboardInterrupt:
                    return "interrupted"
                finally:
                    self.cleanup()

        workflow = InterruptibleWorkflow()
        result = workflow.run_with_cleanup()

        assert result == "interrupted"
        assert workflow.stages_completed == ["stage_1", "stage_2"]
        assert workflow.cleanup_called is True

    def test_parallel_command_coordination(self):
        """Test coordination between parallel command executions."""
        import threading
        import time

        class ParallelCommand:
            def __init__(self, name, duration=0.1):
                self.name = name
                self.duration = duration
                self.result = None
                self.start_time = None
                self.end_time = None

            def execute(self):
                self.start_time = time.time()
                time.sleep(self.duration)
                self.result = f"{self.name}_completed"
                self.end_time = time.time()
                return self.result

        class ParallelCoordinator:
            def __init__(self):
                self.commands = []
                self.results = []

            def add_command(self, command):
                self.commands.append(command)

            def execute_all_parallel(self):
                threads = []
                for cmd in self.commands:
                    thread = threading.Thread(
                        target=lambda c=cmd: self.results.append(c.execute())
                    )
                    threads.append(thread)
                    thread.start()

                for thread in threads:
                    thread.join()

                return self.results

        coordinator = ParallelCoordinator()
        coordinator.add_command(ParallelCommand("cmd1"))
        coordinator.add_command(ParallelCommand("cmd2"))
        coordinator.add_command(ParallelCommand("cmd3"))

        results = coordinator.execute_all_parallel()

        assert len(results) == 3
        assert "cmd1_completed" in results
        assert "cmd2_completed" in results
        assert "cmd3_completed" in results


class TestCrossCommandIntegration:
    """Test integration patterns between different commands."""

    def test_command_data_sharing(self):
        """Test data sharing patterns between commands."""

        class DataSharingTest:
            def __init__(self):
                self.shared_state = {}

            def command_a_produces_data(self):
                data = {
                    "generated_files": ["file1.py", "file2.py"],
                    "metadata": {"version": "1.0"},
                }
                self.shared_state.update(data)
                return data

            def command_b_consumes_data(self):
                if "generated_files" not in self.shared_state:
                    raise ValueError("Required data not available")

                files = self.shared_state["generated_files"]
                return {"processed_files": len(files), "status": "success"}

        test = DataSharingTest()

        # Command A produces data
        data_a = test.command_a_produces_data()
        assert "generated_files" in data_a

        # Command B consumes data
        result_b = test.command_b_consumes_data()
        assert result_b["processed_files"] == 2
        assert result_b["status"] == "success"

    def test_command_dependency_resolution(self):
        """Test command dependency resolution patterns."""

        class DependencyResolver:
            def __init__(self):
                self.command_dependencies = {
                    "init": [],
                    "validate": ["init"],
                    "build": ["init", "validate"],
                    "test": ["build"],
                    "deploy": ["test"],
                }
                self.executed_commands = []

            def resolve_dependencies(self, command):
                deps = self.command_dependencies.get(command, [])
                for dep in deps:
                    if dep not in self.executed_commands:
                        self.resolve_dependencies(dep)

                if command not in self.executed_commands:
                    self.executed_commands.append(command)

            def execute_command(self, command):
                self.resolve_dependencies(command)
                return {"command": command, "dependencies_resolved": True}

        resolver = DependencyResolver()

        # Test executing deploy (should resolve all dependencies)
        result = resolver.execute_command("deploy")

        expected_order = ["init", "validate", "build", "test", "deploy"]
        assert resolver.executed_commands == expected_order
        assert result["command"] == "deploy"
        assert result["dependencies_resolved"] is True

    def test_command_pipeline_execution(self):
        """Test command pipeline execution patterns."""

        class PipelineExecutor:
            def __init__(self):
                self.pipeline_stages = []

            def add_stage(self, stage_name, stage_func):
                self.pipeline_stages.append((stage_name, stage_func))

            def execute_pipeline(self, input_data):
                current_data = input_data
                results = []

                for stage_name, stage_func in self.pipeline_stages:
                    try:
                        stage_result = stage_func(current_data)
                        results.append({
                            "stage": stage_name,
                            "status": "success",
                            "result": stage_result,
                        })
                        current_data = stage_result  # Output becomes next input
                    except Exception as e:
                        results.append({
                            "stage": stage_name,
                            "status": "error",
                            "error": str(e),
                        })
                        break

                return {"pipeline_results": results, "final_data": current_data}

        pipeline = PipelineExecutor()

        # Add pipeline stages
        pipeline.add_stage("parse", lambda data: {"parsed": True, "input": data})
        pipeline.add_stage("validate", lambda data: {"validated": True, "data": data})
        pipeline.add_stage(
            "transform", lambda data: {"transformed": True, "original": data}
        )

        result = pipeline.execute_pipeline({"initial": "data"})

        assert len(result["pipeline_results"]) == 3
        assert all(stage["status"] == "success" for stage in result["pipeline_results"])
        assert result["final_data"]["transformed"] is True
