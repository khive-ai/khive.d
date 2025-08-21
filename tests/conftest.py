"""Simple test configuration and fixtures for khive testing."""

import asyncio
import os
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

# Import all fixture modules so pytest can discover them
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "fixtures"))

# Import CLI fixtures
from tests.fixtures.cli_fixtures import *  # noqa: F401,F403

# Import service fixtures
from tests.fixtures.service_fixtures import *  # noqa: F401,F403

# Import orchestration fixtures
from tests.fixtures.orchestration.orchestration_fixtures import *  # noqa: F401,F403

# Import planning fixtures
from tests.fixtures.planning_fixtures import *  # noqa: F401,F403

# Import composition fixtures
from tests.fixtures.composition.composition_fixtures import *  # noqa: F401,F403
from tests.fixtures.composition.performance_fixtures import *  # noqa: F401,F403
from tests.fixtures.composition.security_fixtures import *  # noqa: F401,F403

# Import filesystem fixtures
from tests.fixtures.filesystem_fixtures import *  # noqa: F401,F403

# Import gated refinement fixtures
from tests.fixtures.gated_refinement_fixtures import *  # noqa: F401,F403


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
