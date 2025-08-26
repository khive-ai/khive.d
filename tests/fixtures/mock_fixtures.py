"""Mock fixtures for external services and API calls."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_api_clients():
    """Mock external API clients."""
    mock_openai = AsyncMock()
    mock_openai.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Mock response"))]
    )

    return {
        "openai": mock_openai,
        "anthropic": AsyncMock(),
        "http_client": MagicMock(),
    }


@pytest.fixture
def mock_external_services():
    """Mock external services for testing."""

    class MockServiceManager:
        def __init__(self):
            self.services = {}
            self.call_logs = []

        def register_service(self, name: str, mock_service: Any):
            """Register a mock service."""
            self.services[name] = mock_service

        def get_service(self, name: str):
            """Get a mock service."""
            return self.services.get(name)

        def log_call(self, service: str, method: str, args: tuple, kwargs: dict):
            """Log service calls for verification."""
            self.call_logs.append(
                {
                    "service": service,
                    "method": method,
                    "args": args,
                    "kwargs": kwargs,
                }
            )

    return MockServiceManager()


@pytest.fixture
def mock_http_responses():
    """Mock HTTP responses for testing."""
    return {
        "success_200": {
            "status_code": 200,
            "json": {"status": "success", "data": {"result": "test"}},
            "headers": {"Content-Type": "application/json"},
        },
        "error_404": {
            "status_code": 404,
            "json": {"error": "Not found"},
            "headers": {"Content-Type": "application/json"},
        },
        "error_500": {
            "status_code": 500,
            "json": {"error": "Internal server error"},
            "headers": {"Content-Type": "application/json"},
        },
    }
