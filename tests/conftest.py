"""Simple test configuration and fixtures for khive testing."""

import asyncio
import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Minimal fixture imports - only keep what's actually needed


@pytest.fixture
def cli_runner():
    """Basic CLI runner fixture."""
    from click.testing import CliRunner

    return CliRunner()


# ============================================================================
# CRITICAL: PREVENT ALL REAL API CALLS IN TESTS
# ============================================================================


def create_mock_openai_response(content: str = None):
    """Create a mock OpenAI API response."""
    if content is None:
        # Default mock response for triage service
        content = '{"complexity": "simple", "confidence": 0.8, "reasoning": "Mock response", "recommended_agents": 2, "suggested_roles": ["researcher", "implementer"], "suggested_domains": ["api-design"]}'

    mock_choice = MagicMock()
    mock_choice.message.content = content

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


@pytest.fixture(autouse=True)
def mock_openai_globally():
    """Mock all OpenAI clients globally to prevent any real API calls."""
    # Create mock response for OpenAI
    mock_response = create_mock_openai_response()

    # Create mock async client
    mock_async_client = AsyncMock()
    mock_async_client.chat.completions.create.return_value = mock_response

    # Create mock sync client
    mock_sync_client = MagicMock()
    mock_sync_client.chat.completions.create.return_value = mock_response

    # Patch all OpenAI imports
    patches = [
        patch("openai.OpenAI", return_value=mock_sync_client),
        patch("openai.AsyncOpenAI", return_value=mock_async_client),
        # Patch where AsyncOpenAI is imported in the triage module
        patch(
            "khive.services.plan.triage.complexity_triage.AsyncOpenAI",
            return_value=mock_async_client,
        ),
        # Patch where OpenAI is imported in the planner service
        patch(
            "khive.services.plan.planner_service.OpenAI", return_value=mock_sync_client
        ),
    ]

    # Apply all patches
    for p in patches:
        p.start()

    yield {"async_client": mock_async_client, "sync_client": mock_sync_client}

    # Clean up patches
    for p in patches:
        try:
            p.stop()
        except RuntimeError:
            pass


@pytest.fixture(autouse=True)
def ensure_no_real_api_calls():
    """Ensure environment variables disable real API calls."""
    with patch.dict(
        os.environ,
        {
            "KHIVE_DISABLE_EXTERNAL_APIS": "true",
            "KHIVE_TEST_MODE": "true",
            "OPENAI_API_KEY": "test-key-should-never-be-used",
        },
    ):
        yield


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_env() -> Generator[dict[str, Any], None, None]:
    """Mock environment variables for testing."""
    original_env = dict(os.environ)
    test_env = {
        "KHIVE_TEST_MODE": "true",
        "KHIVE_DISABLE_EXTERNAL_APIS": "true",
    }
    os.environ.update(test_env)
    yield test_env
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_project_dir(temp_dir: Path) -> Path:
    """Create a sample project directory for CLI testing."""
    project = temp_dir / "test_project"
    project.mkdir()
    (project / "src").mkdir()
    (project / "pyproject.toml").write_text("[project]\nname = 'test-project'")
    return project
