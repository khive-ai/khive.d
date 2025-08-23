"""Simple CLI testing fixtures."""

import io
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch

import pytest


class CLIResult:
    """Simulate Click's Result object for regular function testing."""

    def __init__(self, exit_code: int, output: str):
        self.exit_code = exit_code
        self.output = output


class CLIRunner:
    """CLI runner for testing the khive CLI dispatch system."""

    def invoke(self, func, args=None):
        """Invoke a CLI function and capture output."""
        if args is None:
            args = []

        # Capture stdout and stderr
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        exit_code = 0

        try:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                # For khive CLI, we call the main function with argv
                # Handle both sync and async scenarios by avoiding asyncio.run conflicts
                import asyncio

                # Check if we're already in an event loop
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an async context, so we need to handle this carefully
                    # For now, just call the function and handle SystemExit
                    func(args)
                except RuntimeError:
                    # No event loop running, safe to proceed normally
                    func(args)
        except SystemExit as e:
            exit_code = e.code if e.code is not None else 0
        except Exception as e:
            exit_code = 1
            import traceback

            traceback.print_exc(file=stderr_buffer)
            # Also capture the exception info
            stderr_buffer.write(f"\nException: {e!s}")

        # Combine stdout and stderr for output
        combined_output = stdout_buffer.getvalue() + stderr_buffer.getvalue()

        return CLIResult(exit_code, combined_output)


@pytest.fixture
def cli_runner():
    """CLI runner for testing Python functions."""
    return CLIRunner()


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for CLI command testing."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="mock output", stderr="")
        yield mock_run


@pytest.fixture
def mock_external_apis():
    """Mock all external API calls to prevent hanging in tests."""
    with (
        patch("openai.OpenAI") as mock_openai,
        patch("subprocess.run") as mock_subprocess,
    ):
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock subprocess calls (for gh CLI)
        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        yield {"openai": mock_openai, "subprocess": mock_subprocess}


@pytest.fixture
def baseline_manager():
    """Mock baseline manager for performance testing."""

    class MockBaselineManager:
        def __init__(self):
            self.results = {}

        def record_result(self, test_name, metric_name, value):
            """Record a performance test result."""
            key = f"{test_name}:{metric_name}"
            self.results[key] = value

        def compare_with_baseline(self, test_name, metric_name, current_value):
            """Compare current value with baseline."""
            key = f"{test_name}:{metric_name}"
            baseline = self.results.get(key, current_value)

            # Simple comparison logic - allow 20% variance
            variance = abs(current_value - baseline) / baseline if baseline > 0 else 0

            if variance > 0.2:
                return {
                    "status": "regression",
                    "message": f"Performance regression: {variance:.2%} slower than baseline",
                }
            if variance < -0.1:
                return {
                    "status": "improvement",
                    "message": f"Performance improvement: {abs(variance):.2%} faster than baseline",
                }
            return {
                "status": "pass",
                "message": "Within acceptable performance range",
            }

    return MockBaselineManager()


@pytest.fixture
def no_external_calls():
    """Fixture to ensure no external API calls are made during tests."""
    import os

    original_env = dict(os.environ)

    # Set environment variables to disable external calls
    os.environ.update(
        {
            "KHIVE_TEST_MODE": "true",
            "KHIVE_DISABLE_EXTERNAL_APIS": "true",
            "OPENAI_API_KEY": "test-key-mock",
        }
    )

    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original_env)


@pytest.fixture
def mock_khive_commands():
    """Mock khive commands for CLI testing."""
    # Stack all the necessary patches to prevent real API calls
    with (
        patch("importlib.import_module") as mock_import,
        patch(
            "khive.services.plan.planner_service.OrchestrationPlanner"
        ) as mock_planner,
        patch("khive.services.plan.planner_service.PlannerService") as mock_service,
        patch(
            "khive.services.composition.agent_composer.AgentComposer"
        ) as mock_composer,
    ):
        # Create mock command modules
        mock_plan_module = Mock()
        mock_plan_module.cli_entry = Mock()

        mock_compose_module = Mock()
        mock_compose_module.cli_entry = Mock()

        # Map module names to mock modules
        module_map = {
            "khive.cli.commands.plan": mock_plan_module,
            "khive.cli.commands.compose": mock_compose_module,
        }

        mock_import.side_effect = lambda name: module_map.get(name, Mock())

        # Configure mock services to avoid real API calls
        mock_service_instance = Mock()
        mock_service.return_value = mock_service_instance

        mock_response = Mock()
        mock_response.success = True
        mock_response.summary = "Mock planning complete"
        mock_response.complexity = "simple"
        mock_response.recommended_agents = 3
        mock_response.session_id = "test-session-123"
        mock_response.confidence = 0.85
        mock_response.phases = []
        mock_response.model_dump.return_value = {"success": True}

        async def mock_handle_request(request):
            return mock_response

        mock_service_instance.handle_request = mock_handle_request
        mock_service_instance.close = Mock()

        mock_composer_instance = Mock()
        mock_composer.return_value = mock_composer_instance
        mock_composer_instance.compose_agent.return_value = "Mock agent composition"

        yield {
            "plan": mock_plan_module,
            "compose": mock_compose_module,
            "import_module": mock_import,
            "planner_service": mock_service,
            "agent_composer": mock_composer,
        }
