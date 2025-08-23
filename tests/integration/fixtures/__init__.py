"""Integration test fixtures for external services and complex scenarios."""

import pytest

# Import fixtures from external_services module to make them available
from .external_services import (
    integration_env,
    mock_openai_client,
    mock_redis_cache,
    mock_redis_connected,
    mock_redis_server,
    real_redis_available,
    real_redis_cache,
    redis_cache_config,
    slow_openai_client,
    unreliable_openai_client,
)


@pytest.fixture(scope="session")
def integration_test_session():
    """Session-scoped fixture for integration test setup."""
    yield "integration_test_session"


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace for integration testing."""
    workspace = tmp_path / "khive_integration_workspace"
    workspace.mkdir(exist_ok=True)

    # Create expected directory structure
    (workspace / "sessions").mkdir(exist_ok=True)
    (workspace / "artifacts").mkdir(exist_ok=True)
    (workspace / "cache").mkdir(exist_ok=True)

    return workspace
