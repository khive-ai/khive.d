"""Simple service testing fixtures."""

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_service():
    """Basic mock service for testing."""
    service = AsyncMock()
    service.execute = AsyncMock(return_value="mock result")
    service.status = "running"
    return service
