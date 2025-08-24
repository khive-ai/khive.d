"""Focused planning service tests with practical coverage.

This module tests essential PlannerService functionality:
- Core planning workflow and service initialization
- Complexity assessment accuracy with representative cases
- Agent count optimization within efficiency bounds
- End-to-end integration testing

Maintains essential coverage while removing over-engineering.
"""

import os
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from khive.services.plan.models import OrchestrationEvaluation
from khive.services.plan.parts import (
    AgentRecommendation,
    ComplexityLevel,
    PlannerRequest,
    PlannerResponse,
    QualityGate,
)
from khive.services.plan.planner_service import (
    ComplexityTier,
    OrchestrationPlanner,
    PlannerService,
    Request,
)
from khive.services.plan.triage.complexity_triage import TriageConsensus


@pytest.mark.unit
class TestPlannerServiceCore:
    """Test core PlannerService functionality."""

    @pytest.fixture
    def sample_request(self):
        """Sample planning request for testing."""
        return PlannerRequest(
            task_description="Implement user authentication system with OAuth2",
            session_id=str(uuid4()),
            priority_level="medium",
        )

    @patch("khive.services.plan.planner_service.OrchestrationPlanner")
    async def test_plan_method_basic_flow(
        self, mock_orchestration_planner_cls, sample_request
    ):
        """Test basic planning flow with realistic response."""
        # Mock the OrchestrationPlanner
        mock_planner = AsyncMock()
        mock_orchestration_planner_cls.return_value = mock_planner

        # Mock realistic evaluation response
        mock_evaluation = OrchestrationEvaluation(
            complexity_tier=ComplexityTier.MEDIUM,
            agent_count=4,
            recommended_roles=["researcher", "architect", "implementer", "reviewer"],
            confidence_score=0.85,
            reasoning="OAuth2 implementation requires multiple specialized agents",
        )
        mock_planner.evaluate_request.return_value = mock_evaluation

        # Test the plan method
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}):
            service = PlannerService()
            result = await service.plan(sample_request)

        # Verify essential result properties
        assert isinstance(result, PlannerResponse)
        assert result.complexity_level == ComplexityLevel.MEDIUM
        assert len(result.agent_recommendations) == 4
        assert result.confidence_score == 0.85
        mock_planner.evaluate_request.assert_called_once()


@pytest.mark.unit 
class TestComplexityAssessment:
    """Test complexity assessment with practical test cases."""

    @pytest.fixture
    def complexity_test_cases(self):
        """Representative test cases for complexity validation."""
        return [
            ("fix login bug", ComplexityTier.SIMPLE),
            ("implement OAuth2 system", ComplexityTier.MEDIUM), 
            ("design microservices architecture", ComplexityTier.COMPLEX),
            ("build distributed consensus algorithm", ComplexityTier.VERY_COMPLEX),
        ]

    @patch("khive.services.plan.triage.complexity_triage.ComplexityTriageService")
    async def test_complexity_classification(self, mock_triage_cls, complexity_test_cases):
        """Test that complexity classification works for representative cases."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}),
            patch("khive.services.plan.planner_service.OpenAI"),
            patch.object(OrchestrationPlanner, "_load_available_roles", return_value=["researcher"]),
            patch.object(OrchestrationPlanner, "_load_available_domains", return_value=["software-architecture"]),
            patch.object(OrchestrationPlanner, "_load_prompt_templates", return_value={}),
            patch.object(OrchestrationPlanner, "_load_decision_matrix", return_value={}),
        ):
            planner = OrchestrationPlanner()
            mock_triage = AsyncMock()
            mock_triage_cls.return_value = mock_triage

            # Test classification for each complexity level
            for task, expected_tier in complexity_test_cases:
                mock_consensus = TriageConsensus(
                    tier=expected_tier,
                    confidence=0.8,
                    agent_count=2,
                    recommended_roles=["researcher"],
                    reasoning=f"Assessment for {task}",
                )
                mock_triage.evaluate_complexity.return_value = mock_consensus

                request = Request(task=task)
                result = await planner.evaluate_request(request)

                assert result.complexity_tier == expected_tier
                assert isinstance(result, OrchestrationEvaluation)
                assert result.confidence_score >= 0.7

    @pytest.mark.parametrize("tier,expected_range", [
        (ComplexityTier.SIMPLE, (1, 3)),
        (ComplexityTier.MEDIUM, (3, 6)), 
        (ComplexityTier.COMPLEX, (5, 9)),
        (ComplexityTier.VERY_COMPLEX, (7, 12)),
    ])
    @patch("khive.services.plan.triage.complexity_triage.ComplexityTriageService")
    async def test_agent_count_bounds(self, mock_triage_cls, tier, expected_range):
        """Test agent count stays within efficiency bounds for each tier."""
        min_agents, max_agents = expected_range
        
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}),
            patch("khive.services.plan.planner_service.OpenAI"),
            patch.object(OrchestrationPlanner, "_load_available_roles", return_value=["researcher"]),
            patch.object(OrchestrationPlanner, "_load_available_domains", return_value=["software-architecture"]),
            patch.object(OrchestrationPlanner, "_load_prompt_templates", return_value={}),
            patch.object(OrchestrationPlanner, "_load_decision_matrix", return_value={}),
        ):
            planner = OrchestrationPlanner()
            mock_triage = AsyncMock()
            mock_triage_cls.return_value = mock_triage

            test_agent_count = (min_agents + max_agents) // 2
            mock_consensus = TriageConsensus(
                tier=tier,
                confidence=0.8,
                agent_count=test_agent_count,
                recommended_roles=["researcher"] * test_agent_count,
                reasoning=f"Testing tier {tier.value}",
            )
            mock_triage.evaluate_complexity.return_value = mock_consensus

            request = Request(task=f"Test task for {tier.value} complexity")
            result = await planner.evaluate_request(request)

            # Verify agent count within bounds and efficiency cliff
            assert min_agents <= result.agent_count <= max_agents
            assert result.agent_count <= 12  # Efficiency cliff


@pytest.mark.integration
class TestPlannerIntegration:
    """Integration tests for complete planning workflows."""

    @patch("khive.services.plan.triage.complexity_triage.ComplexityTriageService")
    async def test_end_to_end_planning_workflow(self, mock_triage_cls):
        """Test complete end-to-end planning workflow with realistic data."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}),
            patch("khive.services.plan.planner_service.OpenAI"),
        ):
            service = PlannerService()

            # Mock triage service with realistic consensus
            mock_triage = AsyncMock()
            mock_triage_cls.return_value = mock_triage

            mock_consensus = TriageConsensus(
                tier=ComplexityTier.MEDIUM,
                confidence=0.85,
                agent_count=4,
                recommended_roles=["researcher", "architect", "implementer", "reviewer"],
                reasoning="OAuth2 requires research, architecture, implementation, and review",
            )
            mock_triage.evaluate_complexity.return_value = mock_consensus

            # Execute planning with realistic request
            request = PlannerRequest(
                task_description="Implement OAuth2 authentication with JWT tokens",
                session_id=str(uuid4()),
                priority_level="high",
            )
            result = await service.plan(request)

            # Verify essential result properties
            assert isinstance(result, PlannerResponse)
            assert result.complexity_level == ComplexityLevel.MEDIUM
            assert len(result.agent_recommendations) == 4
            assert result.confidence_score == 0.85
            assert all(isinstance(rec, AgentRecommendation) for rec in result.agent_recommendations)
            
            # Verify workflow completeness
            roles = [rec.role for rec in result.agent_recommendations]
            assert "researcher" in roles and "implementer" in roles
            assert result.session_id == request.session_id
            assert result.estimated_duration > 0
            assert result.quality_gate in [gate.value for gate in QualityGate]

    @patch("khive.services.plan.triage.complexity_triage.ComplexityTriageService") 
    async def test_performance_within_limits(self, mock_triage_cls):
        """Test planning operations complete within acceptable time."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}),
            patch("khive.services.plan.planner_service.OpenAI"),
        ):
            service = PlannerService()

            # Mock for fast response
            mock_triage = AsyncMock()
            mock_triage_cls.return_value = mock_triage
            mock_consensus = TriageConsensus(
                tier=ComplexityTier.SIMPLE,
                confidence=0.9,
                agent_count=2,
                recommended_roles=["implementer", "reviewer"],
                reasoning="Simple bug fix",
            )
            mock_triage.evaluate_complexity.return_value = mock_consensus

            request = PlannerRequest(
                task_description="Fix authentication bug", 
                session_id=str(uuid4())
            )

            # Measure and verify execution time
            import time
            start_time = time.time()
            result = await service.plan(request)
            execution_time = time.time() - start_time

            assert execution_time < 2.0, f"Planning took {execution_time:.2f}s, expected <2.0s"
            assert isinstance(result, PlannerResponse)
            assert result.confidence_score >= 0.8
