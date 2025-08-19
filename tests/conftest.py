"""Global test configuration and fixtures for khive testing."""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test isolation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="Test response"))]
        )
    )
    return client


@pytest.fixture
def sample_project_dir(temp_dir: Path) -> Path:
    """Create a sample project directory structure."""
    project = temp_dir / "test_project"
    project.mkdir()
    (project / "src").mkdir()
    (project / "tests").mkdir()
    (project / "pyproject.toml").write_text("[project]\nname = 'test-project'")
    return project
