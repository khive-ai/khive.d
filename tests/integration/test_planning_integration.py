"""Integration tests for Planning Service.

Tests OpenAI API integration, cost tracking, complexity assessment,
decision workflows, and multi-agent evaluation scenarios.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from khive.services.plan.cost_tracker import CostTracker
from khive.services.plan.models import OrchestrationEvaluation
from khive.services.plan.parts import (
    AgentRecommendation,
    ComplexityLevel,
    PlannerRequest,
    PlannerResponse,
    TaskPhase,
    WorkflowPattern,
)
from khive.services.plan.planner_service import PlannerService
from khive.services.plan.triage.complexity_triage import ComplexityTriageService
from tests.integration.fixtures.external_services import (
    MockOpenAIClient,
    mock_openai_client,
    slow_openai_client,
    unreliable_openai_client,
)


@pytest.mark.integration
class TestPlanningServiceIntegration:
    """Integration tests for the Planning Service."""

    @pytest.fixture
    def decision_matrix_path(self, tmp_path):
        """Create a test decision matrix YAML file."""
        decision_matrix = {
            "complexity_thresholds": {
                "simple": {"max_agents": 3, "max_phases": 1},
                "medium": {"max_agents": 8, "max_phases": 3},
                "complex": {"max_agents": 15, "max_phases": 5},
                "very_complex": {"max_agents": 25, "max_phases": 8},
            },
            "role_selection": {
                "analysis_tasks": ["researcher", "analyst"],
                "implementation_tasks": ["architect", "implementer"],
                "quality_tasks": ["reviewer", "tester"],
                "creative_tasks": ["innovator", "strategist"],
            },
            "workflow_patterns": {
                "simple": "direct",
                "medium": "fanout",
                "complex": "gated_refinement",
                "very_complex": "hierarchical",
            },
        }

        matrix_file = tmp_path / "test_decision_matrix.yaml"
        with open(matrix_file, "w") as f:
            yaml.dump(decision_matrix, f)

        return matrix_file

    @pytest.fixture
    async def planner_service(self, decision_matrix_path, mock_openai_client):
        """Create a configured planner service for testing."""
        with patch("khive.services.plan.planner_service.OpenAI") as mock_openai:
            mock_openai.return_value = mock_openai_client

            service = PlannerService(
                decision_matrix_path=str(decision_matrix_path),
                openai_client=mock_openai_client,
                enable_cost_tracking=True,
            )

            return service

    @pytest.fixture
    def sample_requests(self):
        """Sample planning requests of varying complexity."""
        return [
            PlannerRequest(
                request_text="Create a simple README file for the project",
                context="Basic documentation task",
                priority="medium",
            ),
            PlannerRequest(
                request_text="Implement a complete microservices architecture with API gateway, service discovery, distributed logging, and monitoring",
                context="Complex system architecture implementation",
                priority="high",
            ),
            PlannerRequest(
                request_text="Fix a typo in the configuration file",
                context="Minor bug fix",
                priority="low",
            ),
            PlannerRequest(
                request_text="Design and implement a distributed consensus algorithm with Byzantine fault tolerance for a blockchain network",
                context="Advanced distributed systems research and implementation",
                priority="high",
            ),
        ]

    def test_planner_service_initialization(self, planner_service):
        """Test that planner service initializes correctly."""
        assert planner_service is not None
        assert hasattr(planner_service, "plan_request")
        assert hasattr(planner_service, "assess_complexity")
        assert planner_service._cost_tracker is not None

    async def test_complexity_assessment_integration(
        self, planner_service, sample_requests
    ):
        """Test complexity assessment across different request types."""

        for request in sample_requests:
            complexity = await planner_service.assess_complexity(request.request_text)

            # Verify complexity is valid
            assert complexity in [
                ComplexityLevel.SIMPLE,
                ComplexityLevel.MEDIUM,
                ComplexityLevel.COMPLEX,
                ComplexityLevel.VERY_COMPLEX,
            ]

            # Verify consistency - same request should get same complexity
            complexity_2 = await planner_service.assess_complexity(request.request_text)
            assert complexity == complexity_2

    async def test_agent_recommendation_integration(
        self, planner_service, sample_requests
    ):
        """Test agent recommendation based on complexity and task type."""

        for request in sample_requests:
            complexity = await planner_service.assess_complexity(request.request_text)
            recommendations = await planner_service.recommend_agents(
                request, complexity
            )

            # Verify recommendations structure
            assert isinstance(recommendations, list)
            assert len(recommendations) > 0

            for rec in recommendations:
                assert isinstance(rec, AgentRecommendation)
                assert rec.role is not None
                assert rec.domain is not None
                assert rec.priority in ["high", "medium", "low"]

    async def test_full_planning_workflow_integration(
        self, planner_service, sample_requests
    ):
        """Test complete planning workflow from request to response."""

        for request in sample_requests:
            # Execute full planning workflow
            response = await planner_service.plan_request(request)

            # Verify response structure
            assert isinstance(response, PlannerResponse)
            assert response.complexity is not None
            assert response.agent_recommendations is not None
            assert response.estimated_phases is not None
            assert response.workflow_pattern is not None
            assert response.total_estimated_cost > 0

            # Verify recommendations align with complexity
            num_agents = len(response.agent_recommendations)
            if response.complexity == ComplexityLevel.SIMPLE:
                assert num_agents <= 5
            elif response.complexity == ComplexityLevel.MEDIUM:
                assert num_agents <= 10
            elif response.complexity == ComplexityLevel.COMPLEX:
                assert num_agents <= 20
            else:  # VERY_COMPLEX
                assert num_agents <= 30

    async def test_cost_tracking_integration(self, planner_service, sample_requests):
        """Test cost tracking throughout planning operations."""
        initial_cost = planner_service._cost_tracker.get_total_cost()

        # Execute multiple planning operations
        responses = []
        for request in sample_requests:
            response = await planner_service.plan_request(request)
            responses.append(response)

        # Verify cost tracking
        final_cost = planner_service._cost_tracker.get_total_cost()
        assert final_cost > initial_cost

        # Verify individual response costs
        total_response_costs = sum(r.total_estimated_cost for r in responses)
        assert total_response_costs > 0

        # Get cost breakdown
        cost_breakdown = planner_service._cost_tracker.get_cost_breakdown()
        assert "total_requests" in cost_breakdown
        assert cost_breakdown["total_requests"] >= len(sample_requests)

    async def test_concurrent_planning_requests(self, planner_service):
        """Test concurrent planning request handling."""
        num_concurrent = 10

        # Create concurrent requests
        requests = [
            PlannerRequest(
                request_text=f"Implement feature {i} with database integration",
                context=f"Feature development task {i}",
                priority="medium",
            )
            for i in range(num_concurrent)
        ]

        # Execute concurrent planning
        start_time = time.time()
        tasks = [planner_service.plan_request(req) for req in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Verify results
        successful_responses = [r for r in responses if isinstance(r, PlannerResponse)]
        assert len(successful_responses) >= num_concurrent * 0.8  # Allow 20% failure

        # Verify performance
        duration = end_time - start_time
        assert duration < 30.0, f"Concurrent planning took too long: {duration}s"

        # Verify response consistency
        for response in successful_responses:
            assert response.complexity is not None
            assert len(response.agent_recommendations) > 0

    async def test_decision_matrix_integration(
        self, planner_service, decision_matrix_path
    ):
        """Test integration with decision matrix configuration."""

        # Verify decision matrix was loaded
        assert planner_service._decision_matrix is not None

        # Test with different complexity levels
        test_cases = [
            ("Simple task", ComplexityLevel.SIMPLE),
            (
                "Medium complexity implementation with multiple components",
                ComplexityLevel.MEDIUM,
            ),
            (
                "Complex distributed system with microservices, databases, APIs, monitoring, and security",
                ComplexityLevel.COMPLEX,
            ),
        ]

        for request_text, expected_min_complexity in test_cases:
            request = PlannerRequest(
                request_text=request_text,
                context="Decision matrix test",
                priority="medium",
            )

            response = await planner_service.plan_request(request)

            # Verify decision matrix influences were applied
            assert response.workflow_pattern is not None
            assert response.estimated_phases > 0
            assert len(response.agent_recommendations) > 0

    @pytest.mark.asyncio
    async def test_error_handling_with_openai_failures(
        self, planner_service, unreliable_openai_client
    ):
        """Test error handling when OpenAI API fails."""

        # Replace client with unreliable one
        planner_service._openai_client = unreliable_openai_client

        request = PlannerRequest(
            request_text="Test request for error handling",
            context="Error handling test",
            priority="medium",
        )

        # Multiple attempts - some should succeed, some fail
        results = []
        for _ in range(10):
            try:
                response = await planner_service.plan_request(request)
                results.append(response)
            except Exception as e:
                results.append(e)

        # Should have some successes and some failures
        successful = [r for r in results if isinstance(r, PlannerResponse)]
        failed = [r for r in results if isinstance(r, Exception)]

        assert len(successful) > 0, "Should have some successful requests"
        assert len(failed) > 0, "Should have some failed requests"

    async def test_timeout_handling(self, planner_service, slow_openai_client):
        """Test timeout handling with slow API responses."""

        # Replace with slow client
        planner_service._openai_client = slow_openai_client

        request = PlannerRequest(
            request_text="Test request for timeout handling",
            context="Timeout test",
            priority="medium",
        )

        # Set short timeout for testing
        start_time = time.time()

        try:
            # This should either succeed or timeout
            response = await asyncio.wait_for(
                planner_service.plan_request(request), timeout=3.0
            )
            # If it succeeds, verify it's valid
            assert isinstance(response, PlannerResponse)
        except asyncio.TimeoutError:
            # Timeout is acceptable behavior
            pass

        end_time = time.time()
        duration = end_time - start_time

        # Should not take much longer than timeout
        assert duration < 5.0, f"Operation took too long even with timeout: {duration}s"

    async def test_phase_determination_integration(
        self, planner_service, sample_requests
    ):
        """Test phase determination logic integration."""

        for request in sample_requests:
            response = await planner_service.plan_request(request)

            # Verify phase structure
            phases = response.estimated_phases
            assert isinstance(phases, list)
            assert len(phases) > 0

            for phase in phases:
                assert isinstance(phase, TaskPhase)
                assert phase.phase_name is not None
                assert phase.estimated_duration > 0
                assert isinstance(phase.required_agents, list)

    async def test_workflow_pattern_selection(self, planner_service, sample_requests):
        """Test workflow pattern selection based on complexity."""

        pattern_counts = {}

        for request in sample_requests:
            response = await planner_service.plan_request(request)
            pattern = response.workflow_pattern

            assert isinstance(pattern, WorkflowPattern)

            # Track pattern usage
            pattern_key = f"{pattern.name}_{response.complexity.value}"
            pattern_counts[pattern_key] = pattern_counts.get(pattern_key, 0) + 1

        # Should have variety in patterns based on complexity
        assert len(pattern_counts) > 1, "Should use different workflow patterns"

    async def test_budget_constraints_integration(self, planner_service):
        """Test planning with budget constraints."""

        # Set budget constraint
        max_budget = 100.0

        request = PlannerRequest(
            request_text="Large scale implementation project with multiple services",
            context="Budget constrained project",
            priority="high",
            max_budget=max_budget,
        )

        response = await planner_service.plan_request(request)

        # Verify budget constraint was considered
        # (Implementation dependent - may reduce agents or phases)
        assert response.total_estimated_cost <= max_budget * 1.1  # Allow 10% margin


@pytest.mark.integration
class TestComplexityTriageIntegration:
    """Integration tests for complexity triage service."""

    @pytest.fixture
    async def triage_service(self, mock_openai_client):
        """Create complexity triage service for testing."""
        with patch(
            "khive.services.plan.triage.complexity_triage.OpenAI"
        ) as mock_openai:
            mock_openai.return_value = mock_openai_client

            service = ComplexityTriageService(openai_client=mock_openai_client)

            return service

    async def test_multi_agent_consensus_triage(self, triage_service):
        """Test multi-agent complexity consensus."""

        request_text = "Implement a distributed caching system with Redis clustering"

        # Get consensus assessment
        consensus = await triage_service.get_complexity_consensus(request_text)

        # Verify consensus structure
        assert hasattr(consensus, "final_complexity")
        assert hasattr(consensus, "confidence_score")
        assert hasattr(consensus, "agent_assessments")

        # Verify individual assessments
        assert len(consensus.agent_assessments) > 1

        for assessment in consensus.agent_assessments:
            assert assessment.complexity is not None
            assert 0.0 <= assessment.confidence <= 1.0

    async def test_triage_consistency(self, triage_service):
        """Test consistency of triage assessments."""

        request_text = "Simple file processing utility"

        # Multiple assessments of same request
        assessments = []
        for _ in range(3):
            consensus = await triage_service.get_complexity_consensus(request_text)
            assessments.append(consensus.final_complexity)

        # Should have consistent results (allowing for some variation)
        unique_assessments = set(assessments)
        assert len(unique_assessments) <= 2, "Assessments should be mostly consistent"


@pytest.mark.integration
@pytest.mark.performance
class TestPlanningServicePerformance:
    """Performance integration tests for planning service."""

    async def test_planning_throughput(self, planner_service):
        """Test planning service throughput under load."""

        num_requests = 50
        batch_size = 10

        async def batch_planning(start_index: int):
            requests = [
                PlannerRequest(
                    request_text=f"Implement feature {start_index + i}",
                    context=f"Performance test {start_index + i}",
                    priority="medium",
                )
                for i in range(batch_size)
            ]

            tasks = [planner_service.plan_request(req) for req in requests]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful = [r for r in results if isinstance(r, PlannerResponse)]
            return len(successful)

        # Execute batched planning
        start_time = time.time()
        batches = [
            batch_planning(i * batch_size) for i in range(num_requests // batch_size)
        ]

        batch_results = await asyncio.gather(*batches, return_exceptions=True)
        end_time = time.time()

        # Calculate performance metrics
        duration = end_time - start_time
        successful_batches = [r for r in batch_results if isinstance(r, int)]
        total_successful = sum(successful_batches)

        requests_per_second = total_successful / duration if duration > 0 else 0

        # Performance assertions
        assert (
            requests_per_second > 5
        ), f"Throughput too low: {requests_per_second} req/sec"
        assert duration < 60.0, f"Batch planning took too long: {duration}s"
        assert total_successful >= num_requests * 0.8  # Allow 20% failure rate

    async def test_memory_usage_under_load(self, planner_service):
        """Test memory usage during high-load planning."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create many planning requests
        num_requests = 100
        requests = [
            PlannerRequest(
                request_text=f"Complex implementation task {i} with multiple components",
                context=f"Memory test {i}",
                priority="high",
            )
            for i in range(num_requests)
        ]

        # Execute all requests
        tasks = [planner_service.plan_request(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Verify memory usage is reasonable
        memory_increase_mb = memory_increase / (1024 * 1024)
        assert (
            memory_increase_mb < 500
        ), f"Memory usage too high: {memory_increase_mb}MB"

        # Verify successful completions
        successful_results = [r for r in results if isinstance(r, PlannerResponse)]
        assert len(successful_results) >= num_requests * 0.8
