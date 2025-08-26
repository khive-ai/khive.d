"""Service layer fixtures for testing business logic and integrations."""

from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def service_test_stack():
    """Complete service testing stack."""

    class ServiceTestStack:
        def __init__(self):
            self.planner_service = MagicMock()
            self.composer_service = MagicMock()
            self.orchestrator_service = MagicMock()
            self.session_service = MagicMock()

        def reset_all_mocks(self):
            """Reset all service mocks."""
            for service in [
                self.planner_service,
                self.composer_service,
                self.orchestrator_service,
                self.session_service,
            ]:
                service.reset_mock()

    return ServiceTestStack()


@pytest.fixture
def microservice_mocks():
    """Mock microservice dependencies."""
    return {
        "planning": MagicMock(),
        "composition": MagicMock(),
        "orchestration": MagicMock(),
        "session": MagicMock(),
        "artifacts": MagicMock(),
    }


@pytest.fixture
def api_test_client():
    """Mock API client for testing."""

    class MockAPIClient:
        def __init__(self):
            self.base_url = "http://test-api.example.com"
            self.timeout = 30
            self.retries = 3

        async def get(self, endpoint: str, **kwargs) -> dict[str, Any]:
            """Mock GET request."""
            return {"status": "success", "endpoint": endpoint, "method": "GET"}

        async def post(
            self, endpoint: str, data: dict = None, **kwargs
        ) -> dict[str, Any]:
            """Mock POST request."""
            return {
                "status": "success",
                "endpoint": endpoint,
                "method": "POST",
                "data": data,
            }

        async def put(
            self, endpoint: str, data: dict = None, **kwargs
        ) -> dict[str, Any]:
            """Mock PUT request."""
            return {
                "status": "success",
                "endpoint": endpoint,
                "method": "PUT",
                "data": data,
            }

        async def delete(self, endpoint: str, **kwargs) -> dict[str, Any]:
            """Mock DELETE request."""
            return {"status": "success", "endpoint": endpoint, "method": "DELETE"}

    return MockAPIClient()
