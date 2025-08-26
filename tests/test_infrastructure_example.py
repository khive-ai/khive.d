"""Example test demonstrating the comprehensive testing infrastructure."""

import asyncio

import pytest

from tests.fixtures.async_fixtures import async_test_env
from tests.fixtures.cli_fixtures import cli_test_environment
from tests.fixtures.filesystem_fixtures import temp_workspace
from tests.fixtures.mock_fixtures import mock_api_clients
from tests.fixtures.performance_fixtures import performance_monitor
from tests.fixtures.security_fixtures import security_scanner


@pytest.mark.unit
def test_basic_functionality():
    """Basic unit test example."""
    assert True, "Infrastructure is working"


@pytest.mark.unit
def test_temp_workspace_fixture(temp_workspace):
    """Test the temp workspace fixture."""
    assert temp_workspace.exists()
    assert (temp_workspace / "src").exists()
    assert (temp_workspace / "tests").exists()
    assert (temp_workspace / "pyproject.toml").exists()

    # Verify workspace content
    pyproject_content = (temp_workspace / "pyproject.toml").read_text()
    assert "test-workspace" in pyproject_content


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_test_environment(async_test_env):
    """Test async testing environment."""
    assert "loop" in async_test_env
    assert "timeout" in async_test_env
    assert async_test_env["concurrent_limit"] == 10

    # Test async operation
    await asyncio.sleep(0.001)
    assert True


@pytest.mark.unit
def test_cli_test_environment(cli_test_environment):
    """Test CLI testing environment."""
    env = cli_test_environment
    assert env["project_root"].exists()
    assert env["src_dir"].exists()
    assert env["tests_dir"].exists()

    # Verify project structure
    assert (env["project_root"] / "pyproject.toml").exists()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_mock_api_clients(mock_api_clients):
    """Test API client mocking."""
    openai_client = mock_api_clients["openai"]
    assert openai_client is not None

    # Test mock behavior
    response = await openai_client.chat.completions.create(
        model="gpt-4", messages=[{"role": "user", "content": "test"}]
    )
    assert response.choices[0].message.content == "Mock response"


@pytest.mark.performance
def test_performance_monitoring(performance_monitor):
    """Test performance monitoring fixture."""
    monitor = performance_monitor

    # Start monitoring
    monitor.start_monitoring()

    # Simulate some work
    for i in range(100):
        monitor.record_operation(success=True)
        _ = sum(range(100))  # Simple CPU work

    # Stop monitoring and get metrics
    metrics = monitor.stop_monitoring()

    assert metrics.operation_count == 100
    assert metrics.duration > 0
    assert metrics.operations_per_second > 0
    assert metrics.error_rate == 0.0


@pytest.mark.security
def test_security_scanner(security_scanner):
    """Test security scanning fixture."""
    scanner = security_scanner

    # Test valid input
    result = scanner.validate_input("Hello world", max_length=100)
    assert result["is_valid"] is True
    assert len(result["issues"]) == 0

    # Test invalid input (too long)
    long_input = "A" * 2000
    result = scanner.validate_input(long_input, max_length=100)
    assert result["is_valid"] is False
    assert len(result["issues"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integrated_workflow(
    async_test_env, mock_api_clients, performance_monitor
):
    """Test integrated workflow using multiple fixtures."""
    # Start performance monitoring
    performance_monitor.start_monitoring()

    # Simulate async API calls
    openai_client = mock_api_clients["openai"]

    tasks = []
    for i in range(10):
        task = openai_client.chat.completions.create(
            model="gpt-4", messages=[{"role": "user", "content": f"Message {i}"}]
        )
        tasks.append(task)
        performance_monitor.record_operation(success=True)

    # Wait for completion
    results = await asyncio.gather(*tasks)

    # Stop monitoring
    metrics = performance_monitor.stop_monitoring()

    # Assertions
    assert len(results) == 10
    assert metrics.operation_count == 10
    assert metrics.error_rate == 0.0
    assert all("Mock response" in str(result) for result in results)


@pytest.mark.cli
def test_cli_command_execution(cli_test_environment):
    """Test CLI command execution in test environment."""
    import subprocess
    import sys

    # Test help command using subprocess to avoid Click issues
    result = subprocess.run(
        [sys.executable, "-m", "khive.cli.khive_cli", "--help"],
        capture_output=True,
        text=True,
        cwd=cli_test_environment["project_root"],
    )
    
    # Our CLI should exit with code 0 for help and contain khive in output
    assert result.returncode == 0
    assert "khive" in result.stdout.lower() or "help" in result.stdout.lower()


@pytest.mark.boundary
def test_edge_cases(temp_workspace, security_scanner):
    """Test boundary conditions and edge cases."""
    # Test empty input
    result = security_scanner.validate_input("", max_length=100)
    assert result["is_valid"] is True
    assert result["input_length"] == 0

    # Test exactly at limit
    limit_input = "A" * 100
    result = security_scanner.validate_input(limit_input, max_length=100)
    assert result["is_valid"] is True
    assert result["input_length"] == 100

    # Test one over limit
    over_limit = "A" * 101
    result = security_scanner.validate_input(over_limit, max_length=100)
    assert result["is_valid"] is False

    # Test workspace edge cases
    assert temp_workspace.exists()

    # Create deeply nested directory
    deep_dir = temp_workspace
    for i in range(5):
        deep_dir = deep_dir / f"level_{i}"
        deep_dir.mkdir()

    assert deep_dir.exists()


if __name__ == "__main__":
    # Run this specific test file
    pytest.main([__file__, "-v"])
