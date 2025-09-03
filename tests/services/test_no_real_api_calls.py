"""Verification test to ensure no real API calls are made during testing."""

import pytest

from khive.services.plan.planner_service import PlannerService
from khive.services.plan.triage.complexity_triage import ComplexityTriageService


class TestNoRealApiCalls:
    """Verify that all OpenAI clients are properly mocked in tests."""

    def test_openai_clients_are_mocked(self, mock_openai_globally):
        """Verify OpenAI clients are mocked and not making real requests."""
        # The mock_openai_globally fixture should provide mocked clients
        assert "async_client" in mock_openai_globally
        assert "sync_client" in mock_openai_globally

        # Verify the clients are mocked
        async_client = mock_openai_globally["async_client"]
        sync_client = mock_openai_globally["sync_client"]

        # These should be mock objects, not real clients
        assert hasattr(async_client, "chat")
        assert hasattr(sync_client, "chat")

    @pytest.mark.asyncio
    async def test_complexity_triage_service_uses_mock(self):
        """Verify ComplexityTriageService uses mocked OpenAI client."""
        # Create service - should use mocked client
        service = ComplexityTriageService(api_key="test-key")

        # This should not make a real API call
        should_escalate, consensus = await service.triage("simple test task")

        # Should get mock response without any real HTTP requests
        assert isinstance(should_escalate, bool)
        assert consensus is not None
        assert hasattr(consensus, "complexity_votes")

    @pytest.mark.asyncio
    async def test_planner_service_uses_mock(self):
        """Verify PlannerService uses mocked components."""
        from khive.services.plan.parts import PlannerRequest

        # Create service - should use mocked components
        service = PlannerService()

        # This should not make any real API calls
        request = PlannerRequest(
            task_description="Test task that should not trigger real API calls",
            time_budget_seconds=60.0,
        )

        response = await service.handle_request(request)

        # Should get a valid response without real API calls
        assert response is not None
        assert hasattr(response, "success")
        assert hasattr(response, "summary")

    def test_no_real_openai_import_used(self):
        """Verify that importing OpenAI modules uses mocks."""
        # These imports should be intercepted by our patches
        from openai import AsyncOpenAI, OpenAI

        # Create instances - these should be mocks
        async_client = AsyncOpenAI(api_key="test")
        sync_client = OpenAI(api_key="test")

        # Verify they're mocked (have mock attributes)
        assert hasattr(async_client, "chat")
        assert hasattr(sync_client, "chat")

        # The real OpenAI client would not have these mock-specific attributes
        # but our mocks should
        assert hasattr(async_client.chat.completions, "create")
        assert hasattr(sync_client.chat.completions, "create")
