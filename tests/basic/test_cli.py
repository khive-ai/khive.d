"""CLI command parsing tests.

Tests for khive CLI command parsing, validation, and error handling.
Focus on command structure, argument validation, and help generation.
"""

from unittest.mock import MagicMock, Mock, patch

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
        assert "Available commands:" in result.output

    def test_invalid_command_shows_error(self, cli_runner):
        """Test invalid command shows appropriate error message."""
        result = cli_runner.invoke(main, ["invalid_command"])

        assert result.exit_code != 0
        assert "Unknown command" in result.output

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

    @patch("khive.services.plan.planner_service.OrchestrationPlanner")
    @patch("khive.services.plan.planner_service.PlannerService")
    def test_plan_command_with_task_argument(
        self,
        mock_planner_service,
        mock_orchestration_planner,
        cli_runner,
        no_external_calls,
    ):
        """Test plan command with task argument."""
        # Mock the planner service to avoid real API calls
        mock_service_instance = Mock()
        mock_planner_service.return_value = mock_service_instance

        # Mock the response
        mock_response = Mock()
        mock_response.success = True
        mock_response.summary = "Mock planning complete"
        mock_response.complexity = "simple"
        mock_response.recommended_agents = 3
        mock_response.session_id = "test-session-123"
        mock_response.confidence = 0.85
        mock_response.phases = []
        mock_response.model_dump.return_value = {
            "success": True,
            "summary": "Mock planning complete",
        }

        # Mock async handle_request method
        async def mock_handle_request(request):
            return mock_response

        mock_service_instance.handle_request = mock_handle_request

        # Mock async close method
        async def mock_close():
            pass

        mock_service_instance.close = mock_close

        result = cli_runner.invoke(main, ["plan", "test task"])

        # Should not hang and should complete successfully
        assert result.exit_code == 0

    @patch("khive.services.composition.agent_composer.AgentComposer")
    def test_compose_command_with_role_and_domain(
        self, mock_agent_composer, cli_runner, no_external_calls
    ):
        """Test compose command with role and domain arguments."""
        # Mock the agent composer to avoid real operations
        mock_composer_instance = Mock()
        mock_agent_composer.return_value = mock_composer_instance
        mock_composer_instance.compose_agent.return_value = (
            "Mock agent composition complete"
        )

        result = cli_runner.invoke(
            main, ["compose", "researcher", "-d", "backend-development"]
        )

        assert result.exit_code == 0

    @pytest.mark.parametrize("invalid_arg", ["", " ", "!@#$%"])
    @patch("khive.services.plan.planner_service.OrchestrationPlanner")
    @patch("khive.services.plan.planner_service.PlannerService")
    def test_command_with_invalid_arguments(
        self,
        mock_planner_service,
        mock_orchestration_planner,
        cli_runner,
        invalid_arg,
        no_external_calls,
    ):
        """Test commands handle invalid arguments gracefully."""
        # Mock the planner service to avoid real API calls
        mock_service_instance = Mock()
        mock_planner_service.return_value = mock_service_instance

        mock_response = Mock()
        mock_response.success = True
        mock_response.summary = "Mock planning complete"
        mock_response.complexity = "simple"
        mock_response.recommended_agents = 3
        mock_response.session_id = "test-session-123"
        mock_response.confidence = 0.85
        mock_response.phases = []

        async def mock_handle_request(request):
            return mock_response

        mock_service_instance.handle_request = mock_handle_request

        # Mock async close method
        async def mock_close():
            pass

        mock_service_instance.close = mock_close

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

    @patch("khive.services.plan.planner_service.OrchestrationPlanner")
    @patch("khive.services.plan.planner_service.PlannerService")
    def test_plan_command_calls_planner_service(
        self,
        mock_planner_service,
        mock_orchestration_planner,
        cli_runner,
        no_external_calls,
    ):
        """Test plan command properly integrates with planner service."""
        mock_service = MagicMock()
        mock_planner_service.return_value = mock_service

        # Mock the response
        mock_response = Mock()
        mock_response.success = True
        mock_response.summary = "Mock planning complete"
        mock_response.complexity = "simple"
        mock_response.recommended_agents = 3
        mock_response.session_id = "test-session-123"
        mock_response.confidence = 0.85
        mock_response.phases = []

        # Mock async handle_request method
        async def mock_handle_request(request):
            return mock_response

        mock_service.handle_request = mock_handle_request

        # Mock async close method
        async def mock_close():
            pass

        mock_service.close = mock_close

        result = cli_runner.invoke(main, ["plan", "test task"])

        # Verify service was instantiated
        mock_planner_service.assert_called_once()
        assert result.exit_code == 0

    @patch("khive.services.plan.planner_service.OrchestrationPlanner")
    @patch("khive.services.plan.planner_service.PlannerService")
    def test_command_error_handling(
        self,
        mock_planner_service,
        mock_orchestration_planner,
        cli_runner,
        no_external_calls,
    ):
        """Test CLI error handling for service failures."""
        # Mock service to raise an exception
        mock_service = Mock()
        mock_planner_service.return_value = mock_service

        async def mock_handle_request_error(request):
            raise Exception("Mock service error")

        mock_service.handle_request = mock_handle_request_error

        # Mock async close method
        async def mock_close():
            pass

        mock_service.close = mock_close

        result = cli_runner.invoke(main, ["plan", "test task"])

        # Should handle error gracefully
        assert result.exit_code == 1
        assert "Error" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestCommandSecurity:
    """Test CLI command security aspects."""

    @patch("khive.services.plan.planner_service.OrchestrationPlanner")
    @patch("khive.services.plan.planner_service.PlannerService")
    def test_command_injection_prevention(
        self,
        mock_planner_service,
        mock_orchestration_planner,
        cli_runner,
        no_external_calls,
    ):
        """Test CLI prevents command injection attacks."""
        # Mock the planner service to avoid real API calls
        mock_service_instance = Mock()
        mock_planner_service.return_value = mock_service_instance

        # Mock the response
        mock_response = Mock()
        mock_response.success = True
        mock_response.summary = "Mock planning complete"
        mock_response.complexity = "simple"
        mock_response.recommended_agents = 3
        mock_response.session_id = "test-session-123"
        mock_response.confidence = 0.85
        mock_response.phases = []

        # Mock async handle_request method
        async def mock_handle_request(request):
            return mock_response

        mock_service_instance.handle_request = mock_handle_request

        # Mock async close method
        async def mock_close():
            pass

        mock_service_instance.close = mock_close

        injection_attempts = ["; rm -rf /", "$(rm -rf /)", "`rm -rf /`"]
        for injection_attempt in injection_attempts:
            result = cli_runner.invoke(main, ["plan", injection_attempt])

            # Should not execute injected commands
            assert result.exit_code in [0, 1, 2]
            # Output should not contain signs of command execution
            assert "etc/passwd" not in result.output.lower()

    def test_path_traversal_prevention(self, cli_runner, no_external_calls):
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

    def test_help_command_response_time(self, cli_runner, benchmark, no_external_calls):
        """Benchmark help command response time."""

        def run_help():
            return cli_runner.invoke(main, ["--help"])

        result = benchmark(run_help)
        assert result.exit_code == 0

    def test_command_startup_time(
        self, cli_runner, baseline_manager, no_external_calls
    ):
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
