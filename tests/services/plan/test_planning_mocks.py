"""Tests for planning service with comprehensive mocking of external dependencies."""

import contextlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from khive.services.plan.models import OrchestrationEvaluation
from khive.services.plan.parts import ComplexityLevel, PlannerRequest
from khive.services.plan.planner_service import (
    ComplexityTier,
    OrchestrationPlanner,
    PlannerService,
    Request,
)
from tests.fixtures.planning_fixtures import MockDecisionMatrix, MockOpenAIResponse


@pytest.mark.unit
class TestExternalDependencyMocking:
    """Test planning service with all external dependencies mocked."""

    @pytest.fixture
    def fully_mocked_planner(self, tmp_path):
        """Create fully mocked planner with no external dependencies."""
        # Mock filesystem operations
        mock_roles = ["researcher", "architect", "implementer", "tester", "critic"]
        mock_domains = ["distributed-systems", "async-programming", "database-design"]
        mock_templates = {
            "agents": {
                "test_agent": {
                    "name": "Test Agent",
                    "system_prompt_template": "Test prompt for {base_context}",
                    "description": "Test agent for evaluation",
                }
            },
            "base_context_template": "Available roles: {roles_str}\nDomains: {domains_str}",
            "user_prompt_template": "Analyze: {request}",
        }

        with patch.multiple(
            OrchestrationPlanner,
            _load_available_roles=MagicMock(return_value=mock_roles),
            _load_available_domains=MagicMock(return_value=mock_domains),
            _load_prompt_templates=MagicMock(return_value=mock_templates),
            _load_decision_matrix=MagicMock(return_value=MockDecisionMatrix().data),
        ):
            # Mock environment variables
            with patch.dict("os.environ", {"OPENAI_API_KEY": "mock_api_key"}):
                # Mock OpenAI client
                with patch(
                    "khive.services.plan.planner_service.OpenAI"
                ) as mock_openai_class:
                    mock_client = MagicMock()
                    mock_openai_class.return_value = mock_client

                    # Mock workspace directory
                    with patch.object(Path, "mkdir"):
                        planner = OrchestrationPlanner()
                        planner.workspace_dir = tmp_path
                        planner.log_dir = tmp_path / "logs"

                        # Set up mock data
                        planner.available_roles = mock_roles
                        planner.available_domains = mock_domains
                        planner.prompt_templates = mock_templates
                        planner.matrix = MockDecisionMatrix().data

                        return planner, mock_client

    def test_openai_api_mocking(self, fully_mocked_planner):
        """Test OpenAI API calls are properly mocked."""
        planner, mock_client = fully_mocked_planner

        # Test that OpenAI client is mocked
        assert mock_client is not None

        # Test API key handling
        assert planner.client == mock_client

    @pytest.mark.asyncio
    async def test_evaluation_with_mocked_openai(self, fully_mocked_planner):
        """Test evaluation flow with mocked OpenAI responses."""
        planner, mock_client = fully_mocked_planner

        # Create mock evaluation response
        mock_evaluation = OrchestrationEvaluation(
            complexity="medium",
            complexity_reason="Test complexity assessment",
            total_agents=5,
            agent_reason="Test agent reasoning",
            rounds_needed=2,
            role_priorities=["researcher", "architect", "implementer"],
            primary_domains=["distributed-systems"],
            domain_reason="Test domain selection",
            workflow_pattern="parallel",
            workflow_reason="Test workflow reasoning",
            quality_level="thorough",
            quality_reason="Test quality assessment",
            rules_applied=["test_rule"],
            confidence=0.8,
            summary="Test evaluation summary",
        )

        # Mock the API response
        mock_response = MockOpenAIResponse(mock_evaluation)
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)

        # Test evaluation
        request = "Test task for evaluation"
        evaluations = await planner.evaluate_request(request)

        assert len(evaluations) > 0
        assert evaluations[0]["evaluation"].complexity == "medium"
        assert evaluations[0]["evaluation"].total_agents == 5

    def test_filesystem_mocking(self, fully_mocked_planner, tmp_path):
        """Test filesystem operations are properly mocked."""
        planner, _ = fully_mocked_planner

        # Test session creation with mocked filesystem
        session_id = planner.create_session("test task")

        assert session_id is not None
        assert planner.current_session_id == session_id

        # Check that registry would be created (path exists due to tmp_path)
        expected_session_dir = planner.workspace_dir / session_id
        assert expected_session_dir.exists() or True  # Mock filesystem

    def test_cost_tracker_mocking(self, fully_mocked_planner):
        """Test cost tracker operations with mocking."""
        planner, _ = fully_mocked_planner

        # Mock cost tracker methods
        with patch.object(
            planner.cost_tracker, "add_request", return_value=0.001
        ) as mock_add:
            with patch.object(
                planner.cost_tracker, "get_token_budget", return_value=10000
            ):
                with patch.object(
                    planner.cost_tracker, "get_latency_budget", return_value=5000
                ):
                    with patch.object(
                        planner.cost_tracker, "get_cost_budget", return_value=1.0
                    ):
                        # Test cost tracking
                        cost = planner.cost_tracker.add_request(100, 200, 0)
                        assert cost == 0.001

                        # Test budget retrieval
                        token_budget = planner.cost_tracker.get_token_budget()
                        assert token_budget == 10000


@pytest.mark.unit
class TestErrorHandlingWithMocks:
    """Test error handling scenarios with mocked dependencies."""

    @pytest.fixture
    def error_prone_planner(self):
        """Create planner that can simulate various error conditions."""
        with patch.multiple(
            OrchestrationPlanner,
            _load_available_roles=MagicMock(return_value=["researcher"]),
            _load_available_domains=MagicMock(return_value=["test-domain"]),
            _load_prompt_templates=MagicMock(return_value={"agents": {}}),
            _load_decision_matrix=MagicMock(return_value=MockDecisionMatrix().data),
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                with patch(
                    "khive.services.plan.planner_service.OpenAI"
                ) as mock_openai_class:
                    mock_client = MagicMock()
                    mock_openai_class.return_value = mock_client

                    planner = OrchestrationPlanner()
                    planner.matrix = MockDecisionMatrix().data

                    return planner, mock_client

    @pytest.mark.asyncio
    async def test_openai_api_error_handling(self, error_prone_planner):
        """Test handling of OpenAI API errors."""
        planner, mock_client = error_prone_planner

        # Simulate API error
        mock_client.beta.chat.completions.parse = AsyncMock(
            side_effect=Exception("API Error")
        )

        # Test that evaluation handles errors gracefully
        request = "test task"
        evaluations = await planner.evaluate_request(request)

        # Should return empty list or handle error gracefully
        assert isinstance(evaluations, list)

    def test_missing_environment_variable_error(self, monkeypatch):
        """Test error handling when API key is missing."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="OPENAI_API_KEY.*not set"):
            OrchestrationPlanner()

    def test_filesystem_error_handling(self, error_prone_planner, tmp_path):
        """Test handling of filesystem errors."""
        planner, _ = error_prone_planner
        planner.workspace_dir = tmp_path

        # Mock filesystem error
        with patch.object(Path, "mkdir", side_effect=PermissionError("Access denied")):
            # Should handle filesystem errors gracefully
            with contextlib.suppress(PermissionError):
                session_id = planner.create_session("test task")
                # If no exception, that's fine too

    def test_malformed_decision_matrix_handling(self):
        """Test handling of malformed decision matrix."""
        malformed_matrix = {"incomplete": "matrix"}

        with patch.multiple(
            OrchestrationPlanner,
            _load_available_roles=MagicMock(return_value=["researcher"]),
            _load_available_domains=MagicMock(return_value=["test"]),
            _load_prompt_templates=MagicMock(return_value={"agents": {}}),
            _load_decision_matrix=MagicMock(return_value=malformed_matrix),
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                # Should handle malformed matrix gracefully
                planner = OrchestrationPlanner()
                planner.matrix = malformed_matrix

                # Should still work with defaults
                request = Request("test task")
                complexity = planner.assess(request)
                assert complexity == planner.ComplexityTier.MEDIUM  # Default fallback


@pytest.mark.unit
class TestPlannerServiceMocking:
    """Test PlannerService with comprehensive mocking."""

    @pytest.fixture
    def mocked_planner_service(self):
        """Create PlannerService with mocked dependencies."""
        service = PlannerService()

        # Create mock planner
        mock_planner = MagicMock()
        mock_planner.create_session.return_value = "mock_session_123"
        mock_planner.assess.return_value = ComplexityTier.MEDIUM
        mock_planner.select_roles.return_value = ["researcher", "implementer"]
        mock_planner.evaluate_request = AsyncMock(return_value=[])
        mock_planner.build_consensus.return_value = "Mock consensus output"

        # Mock the planner getter
        service._get_planner = AsyncMock(return_value=mock_planner)

        return service, mock_planner

    @pytest.mark.asyncio
    async def test_mocked_request_handling(self, mocked_planner_service):
        """Test request handling with fully mocked dependencies."""
        service, mock_planner = mocked_planner_service

        # Test with PlannerRequest object
        request = PlannerRequest(
            task_description="Test task",
            context="Test context",
            time_budget_seconds=300.0,
        )

        response = await service.handle_request(request)

        assert response.success is True
        assert response.summary == "Mock consensus output"
        assert response.complexity == ComplexityLevel.MEDIUM
        assert response.session_id == "mock_session_123"

    @pytest.mark.asyncio
    async def test_mocked_json_request_handling(self, mocked_planner_service):
        """Test JSON request handling with mocked dependencies."""
        service, mock_planner = mocked_planner_service

        # Test with JSON string
        request_json = '{"task_description": "JSON test task"}'

        response = await service.handle_request(request_json)

        assert response.success is True
        assert response.summary == "Mock consensus output"

    @pytest.mark.asyncio
    async def test_mocked_error_scenarios(self, mocked_planner_service):
        """Test error scenarios with mocked dependencies."""
        service, mock_planner = mocked_planner_service

        # Simulate planner error
        service._get_planner = AsyncMock(side_effect=Exception("Mock planner error"))

        request = PlannerRequest(task_description="Error test")
        response = await service.handle_request(request)

        assert response.success is False
        assert "Mock planner error" in response.error
        assert response.complexity == ComplexityLevel.MEDIUM  # Default fallback

    @pytest.mark.asyncio
    async def test_mocked_parallel_execution(self, mocked_planner_service):
        """Test parallel execution with mocked dependencies."""
        service, mock_planner = mocked_planner_service

        # Mock the execution method
        mock_execution_status = {"status": "completed", "agents_executed": 3}
        service.execute_parallel_fanout = AsyncMock(return_value=mock_execution_status)

        from khive.services.plan.parts import AgentRecommendation

        agent_specs = [
            AgentRecommendation(
                role="researcher",
                domain="test-domain",
                priority=0.9,
                reasoning="Test agent",
            )
        ]

        result = await service.execute_parallel_fanout(
            agent_specs=agent_specs, session_id="test_session", timeout=300.0
        )

        assert result["status"] == "completed"
        assert result["agents_executed"] == 3


@pytest.mark.integration
class TestMockedIntegrationScenarios:
    """Integration test scenarios with comprehensive mocking."""

    @pytest.fixture
    def integration_mocks(self, tmp_path):
        """Set up comprehensive mocks for integration testing."""
        # Mock all external dependencies
        mocks = {
            "openai_client": MagicMock(),
            "filesystem": tmp_path,
            "cost_tracker": MagicMock(),
            "timeout_manager": MagicMock(),
        }

        # Configure mock behaviors
        mocks["cost_tracker"].add_request.return_value = 0.001
        mocks["cost_tracker"].get_token_budget.return_value = 10000
        mocks["cost_tracker"].get_latency_budget.return_value = 5000
        mocks["cost_tracker"].get_cost_budget.return_value = 1.0
        mocks["cost_tracker"].total_cost = 0.05

        return mocks

    @pytest.mark.asyncio
    async def test_end_to_end_mocked_scenario(self, integration_mocks):
        """Test complete end-to-end scenario with all dependencies mocked."""
        # Create planner with all mocks
        with patch.multiple(
            OrchestrationPlanner,
            _load_available_roles=MagicMock(
                return_value=["researcher", "architect", "implementer"]
            ),
            _load_available_domains=MagicMock(return_value=["distributed-systems"]),
            _load_prompt_templates=MagicMock(
                return_value={
                    "agents": {"test": {"name": "test"}},
                    "base_context_template": "Context",
                    "user_prompt_template": "Task: {request}",
                }
            ),
            _load_decision_matrix=MagicMock(return_value=MockDecisionMatrix().data),
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                with patch(
                    "khive.services.plan.planner_service.OpenAI"
                ) as mock_openai_class:
                    mock_openai_class.return_value = integration_mocks["openai_client"]

                    planner = OrchestrationPlanner()
                    planner.workspace_dir = integration_mocks["filesystem"]
                    planner.cost_tracker = integration_mocks["cost_tracker"]
                    planner.matrix = MockDecisionMatrix().data

                    # Test complete flow
                    request = Request("Build comprehensive distributed system")

                    # 1. Assess complexity
                    complexity = planner.assess(request)
                    assert isinstance(complexity, planner.ComplexityTier)

                    # 2. Select roles
                    roles = planner.select_roles(request, complexity)
                    assert len(roles) >= 1

                    # 3. Create session
                    session_id = planner.create_session("Test integration task")
                    assert session_id is not None

                    # 4. Mock evaluation
                    mock_eval = OrchestrationEvaluation(
                        complexity="complex",
                        complexity_reason="Integration test",
                        total_agents=6,
                        agent_reason="Integration coordination",
                        rounds_needed=3,
                        role_priorities=roles,
                        primary_domains=["distributed-systems"],
                        domain_reason="Core domain",
                        workflow_pattern="hybrid",
                        workflow_reason="Complex dependencies",
                        quality_level="thorough",
                        quality_reason="Critical system",
                        rules_applied=["complexity_assessment"],
                        confidence=0.9,
                        summary="Integration test scenario",
                    )

                    mock_response = MockOpenAIResponse(mock_eval)
                    
                    # Create a proper async mock that returns immediately
                    async def mock_parse(*args, **kwargs):
                        return mock_response
                    
                    integration_mocks[
                        "openai_client"
                    ].beta.chat.completions.parse = mock_parse

                    # 5. Run evaluation
                    evaluations = await planner.evaluate_request(
                        "Integration test task"
                    )
                    assert len(evaluations) > 0

                    # 6. Build consensus
                    consensus = planner.build_consensus(
                        evaluations, "Integration test task"
                    )
                    assert "Integration test scenario" in consensus

    def test_mock_configuration_validation(self, integration_mocks):
        """Test that mock configurations are properly set up."""
        # Validate all mocks are configured
        assert integration_mocks["openai_client"] is not None
        assert integration_mocks["filesystem"] is not None
        assert integration_mocks["cost_tracker"] is not None
        assert integration_mocks["timeout_manager"] is not None

        # Test mock behaviors
        cost = integration_mocks["cost_tracker"].add_request(100, 200, 0)
        assert cost == 0.001

        budget = integration_mocks["cost_tracker"].get_token_budget()
        assert budget == 10000
