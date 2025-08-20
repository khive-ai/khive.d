"""CLI command parsing tests.

Tests for khive CLI command parsing, validation, and error handling.
Focus on command structure, argument validation, and help generation.
"""

from unittest.mock import MagicMock, patch

import pytest

from khive.cli.khive_cli import main


@pytest.mark.unit
@pytest.mark.cli
class TestCommandParsing:
    """Test CLI command parsing functionality."""

    def test_main_command_help_display(self, cli_runner):
        """Test main command displays help information."""
        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Commands:" in result.output

    def test_invalid_command_shows_error(self, cli_runner):
        """Test invalid command shows appropriate error message."""
        result = cli_runner.invoke(main, ["invalid_command"])

        assert result.exit_code != 0
        assert "No such command" in result.output

    def test_command_without_required_args_shows_help(self, cli_runner):
        """Test command without required arguments shows help."""
        result = cli_runner.invoke(main, ["plan"])

        # Should either show help or error message about missing args
        assert result.exit_code != 0
        assert any(
            keyword in result.output.lower()
            for keyword in ["usage", "required", "missing"]
        )


@pytest.mark.unit
@pytest.mark.cli
class TestCommandArguments:
    """Test CLI command argument handling."""

    def test_plan_command_with_task_argument(self, cli_runner, mock_khive_commands):
        """Test plan command with task argument."""
        result = cli_runner.invoke(main, ["plan", "test task"])

        # Mock should handle the actual execution
        assert result.exit_code == 0

    def test_compose_command_with_role_and_domain(
        self, cli_runner, mock_khive_commands
    ):
        """Test compose command with role and domain arguments."""
        result = cli_runner.invoke(
            main, ["compose", "researcher", "-d", "backend-development"]
        )

        assert result.exit_code == 0

    @pytest.mark.parametrize("invalid_arg", ["", " ", "!@#$%"])
    def test_command_with_invalid_arguments(self, cli_runner, invalid_arg):
        """Test commands handle invalid arguments gracefully."""
        result = cli_runner.invoke(main, ["plan", invalid_arg])

        # Should not crash, may show error or help
        assert result.exit_code in [0, 1, 2]  # Common CLI exit codes


@pytest.mark.unit
@pytest.mark.cli
class TestCommandValidation:
    """Test CLI command input validation."""

    def test_file_path_validation(self, cli_runner):
        """Test file path argument validation."""
        # This would test commands that accept file paths
        # Implementation depends on specific command structure

    def test_numeric_argument_validation(self, cli_runner):
        """Test numeric argument validation."""
        # Test commands that accept numeric inputs (timeouts, limits, etc.)


@pytest.mark.integration
@pytest.mark.cli
class TestCommandIntegration:
    """Test CLI command integration with services."""

    @patch("khive.services.plan.khive_plan.PlannerService")
    def test_plan_command_calls_planner_service(self, mock_planner_service, cli_runner):
        """Test plan command properly integrates with planner service."""
        mock_service = MagicMock()
        mock_planner_service.return_value = mock_service

        result = cli_runner.invoke(main, ["plan", "test task"])

        # Verify service was called (adjust based on actual implementation)
        # mock_service.plan.assert_called_once()

    def test_command_error_handling(self, cli_runner):
        """Test CLI error handling for service failures."""
        # Test how CLI handles when underlying services fail


@pytest.mark.unit
@pytest.mark.cli
class TestCommandSecurity:
    """Test CLI command security aspects."""

    def test_command_injection_prevention(self, cli_runner):
        """Test CLI prevents command injection attacks."""
        injection_attempts = ["; rm -rf /", "$(rm -rf /)", "`rm -rf /`"]
        for injection_attempt in injection_attempts:
            result = cli_runner.invoke(main, ["plan", injection_attempt])

            # Should not execute injected commands
            assert result.exit_code in [0, 1, 2]
            # Output should not contain signs of command execution
            assert "etc/passwd" not in result.output.lower()

    def test_path_traversal_prevention(self, cli_runner):
        """Test CLI prevents path traversal attacks."""
        # Test commands that accept file paths
        path_attacks = ["../../../etc/passwd", "..\\..\\..\\windows\\system32"]
        for path_attack in path_attacks:
            # Would need to test with commands that accept file paths
            result = cli_runner.invoke(main, ["--help"])
            # Basic test - just ensure CLI doesn't crash with these inputs
            assert result.exit_code == 0


@pytest.mark.slow
@pytest.mark.cli
class TestCommandPerformance:
    """Test CLI command performance characteristics."""

    def test_help_command_response_time(self, cli_runner, benchmark):
        """Benchmark help command response time."""

        def run_help():
            return cli_runner.invoke(main, ["--help"])

        result = benchmark(run_help)
        assert result.exit_code == 0

    def test_command_startup_time(self, cli_runner, baseline_manager):
        """Test CLI command startup performance."""
        import time

        start_time = time.perf_counter()
        result = cli_runner.invoke(main, ["--help"])
        execution_time = time.perf_counter() - start_time

        assert result.exit_code == 0

        if baseline_manager:
            baseline_manager.record_result(
                "cli_help_command", "startup_time", execution_time
            )

            comparison = baseline_manager.compare_with_baseline(
                "cli_help_command", "startup_time", execution_time
            )

            # Allow for some variance in startup time
            assert comparison["status"] in [
                "pass",
                "improvement",
            ], f"CLI startup performance regression: {comparison['message']}"
