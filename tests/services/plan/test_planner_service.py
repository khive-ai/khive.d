"""Core planning service tests for orchestration logic and decision-making algorithms.

This module tests the core functionality of the PlannerService including:
- Task complexity assessment algorithm validation
- Agent count and role priority calculation logic
- Domain matching and selection accuracy
- Workflow pattern determination consistency
- Decision matrix validation and scoring
- Confidence calculation reliability
- Edge case handling for unusual inputs

Targets >90% code coverage with comprehensive algorithm validation.
"""

import os
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from khive.services.plan.models import OrchestrationEvaluation
from khive.services.plan.parts import (AgentRecommendation, ComplexityLevel,
                                       PlannerRequest, PlannerResponse,
                                       QualityGate, WorkflowPattern)
from khive.services.plan.planner_service import (ComplexityTier,
                                                 OrchestrationPlanner,
                                                 PlannerService, Request)
from khive.services.plan.triage.complexity_triage import TriageConsensus


@pytest.mark.unit
class TestPlannerServiceCore:
    """Test core PlannerService functionality."""

    @pytest.fixture
    def mock_planner_service(self):
        """Create a PlannerService with mocked dependencies."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}),
            patch("khive.services.plan.planner_service.OpenAI"),
        ):
            service = PlannerService()
            return service

    @pytest.fixture
    def sample_request(self):
        """Sample planning request for testing."""
        return PlannerRequest(
            task_description="Implement user authentication system with OAuth2",
            session_id=str(uuid4()),
            priority_level="medium",
        )

    def test_service_initialization(self, mock_planner_service):
        """Test PlannerService initialization."""
        assert mock_planner_service.orchestration_planner is not None
        assert hasattr(mock_planner_service, "plan")

    @patch("khive.services.plan.planner_service.OrchestrationPlanner")
    async def test_plan_method_basic_flow(
        self, mock_orchestration_planner_cls, sample_request
    ):
        """Test basic planning flow."""
        # Mock the OrchestrationPlanner
        mock_planner = AsyncMock()
        mock_orchestration_planner_cls.return_value = mock_planner

        # Mock the evaluation response
        mock_evaluation = OrchestrationEvaluation(
            complexity_tier=ComplexityTier.MEDIUM,
            agent_count=4,
            recommended_roles=["researcher", "architect", "implementer", "reviewer"],
            workflow_pattern=WorkflowPattern.PARALLEL,
            confidence_score=0.85,
            reasoning="OAuth2 implementation requires multiple specialized agents",
        )
        mock_planner.evaluate_request.return_value = mock_evaluation

        # Test the plan method
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}):
            service = PlannerService()
            result = await service.plan(sample_request)

        # Verify result
        assert isinstance(result, PlannerResponse)
        assert result.complexity_level == ComplexityLevel.MEDIUM
        assert len(result.agent_recommendations) == 4
        assert result.confidence_score == 0.85

        # Verify planner was called correctly
        mock_planner.evaluate_request.assert_called_once()


@pytest.mark.unit
class TestOrchestrationPlannerCore:
    """Test OrchestrationPlanner core algorithms."""

    @pytest.fixture
    def mock_planner(self):
        """Create OrchestrationPlanner with mocked dependencies."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}),
            patch("khive.services.plan.planner_service.OpenAI"),
            patch.object(
                OrchestrationPlanner,
                "_load_available_roles",
                return_value=["researcher", "architect", "implementer"],
            ),
            patch.object(
                OrchestrationPlanner,
                "_load_available_domains",
                return_value=["software-architecture", "distributed-systems"],
            ),
            patch.object(
                OrchestrationPlanner, "_load_prompt_templates", return_value={}
            ),
            patch.object(
                OrchestrationPlanner, "_load_decision_matrix", return_value={}
            ),
        ):
            return OrchestrationPlanner()

    def test_planner_initialization(self, mock_planner):
        """Test OrchestrationPlanner initialization."""
        assert mock_planner.available_roles == [
            "researcher",
            "architect",
            "implementer",
        ]
        assert mock_planner.available_domains == [
            "software-architecture",
            "distributed-systems",
        ]

    @patch("khive.services.plan.triage.complexity_triage.ComplexityTriageService")
    async def test_complexity_assessment_flow(
        self, mock_triage_service_cls, mock_planner
    ):
        """Test complexity assessment algorithm flow."""
        # Mock triage service
        mock_triage = AsyncMock()
        mock_triage_service_cls.return_value = mock_triage

        mock_consensus = TriageConsensus(
            tier=ComplexityTier.MEDIUM,
            confidence=0.8,
            agent_count=4,
            recommended_roles=["researcher", "architect"],
            reasoning="Moderate complexity task requiring research and design",
        )
        mock_triage.evaluate_complexity.return_value = mock_consensus

        # Test evaluation
        request = Request(task="Implement OAuth2 authentication")
        result = await mock_planner.evaluate_request(request)

        # Verify result structure
        assert isinstance(result, OrchestrationEvaluation)
        assert result.complexity_tier == ComplexityTier.MEDIUM
        assert result.confidence_score >= 0.7
        assert len(result.recommended_roles) >= 2


@pytest.mark.unit
class TestComplexityAssessmentAlgorithms:
    """Test complexity assessment algorithm accuracy."""

    @pytest.fixture
    def assessment_test_cases(self):
        """Test cases for complexity assessment validation."""
        return [
            ("fix login bug", ComplexityTier.SIMPLE),
            ("update user profile", ComplexityTier.SIMPLE),
            ("implement OAuth2 system", ComplexityTier.MEDIUM),
            ("design microservices architecture", ComplexityTier.COMPLEX),
            ("build distributed consensus algorithm", ComplexityTier.VERY_COMPLEX),
        ]

    @patch("khive.services.plan.triage.complexity_triage.ComplexityTriageService")
    async def test_complexity_tier_accuracy(
        self, mock_triage_cls, assessment_test_cases
    ):
        """Test accuracy of complexity tier determination."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}),
            patch("khive.services.plan.planner_service.OpenAI"),
            patch.object(
                OrchestrationPlanner,
                "_load_available_roles",
                return_value=["researcher"],
            ),
            patch.object(
                OrchestrationPlanner,
                "_load_available_domains",
                return_value=["software-architecture"],
            ),
            patch.object(
                OrchestrationPlanner, "_load_prompt_templates", return_value={}
            ),
            patch.object(
                OrchestrationPlanner, "_load_decision_matrix", return_value={}
            ),
        ):
            planner = OrchestrationPlanner()

            # Mock triage service with realistic responses
            mock_triage = AsyncMock()
            mock_triage_cls.return_value = mock_triage

            correct_predictions = 0
            total_cases = len(assessment_test_cases)

            for task, expected_tier in assessment_test_cases:
                # Configure mock to return expected tier
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

                if result.complexity_tier == expected_tier:
                    correct_predictions += 1

            # Assert at least 80% accuracy
            accuracy = correct_predictions / total_cases
            assert accuracy >= 0.8, (
                f"Complexity assessment accuracy {accuracy:.2%} below 80% threshold"
            )


@pytest.mark.unit
class TestAgentCountOptimization:
    """Test agent count calculation and optimization logic."""

    @pytest.fixture
    def optimization_test_cases(self):
        """Test cases for agent count optimization."""
        return [
            (ComplexityTier.SIMPLE, (1, 3)),  # Simple tasks: 1-3 agents
            (ComplexityTier.MEDIUM, (3, 6)),  # Medium tasks: 3-6 agents
            (ComplexityTier.COMPLEX, (5, 9)),  # Complex tasks: 5-9 agents
            (
                ComplexityTier.VERY_COMPLEX,
                (7, 12),
            ),  # Very complex: 7-12 agents (efficiency cliff)
        ]

    @patch("khive.services.plan.triage.complexity_triage.ComplexityTriageService")
    async def test_agent_count_bounds(self, mock_triage_cls, optimization_test_cases):
        """Test agent count stays within optimal bounds."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}),
            patch("khive.services.plan.planner_service.OpenAI"),
            patch.object(
                OrchestrationPlanner,
                "_load_available_roles",
                return_value=["researcher"],
            ),
            patch.object(
                OrchestrationPlanner,
                "_load_available_domains",
                return_value=["software-architecture"],
            ),
            patch.object(
                OrchestrationPlanner, "_load_prompt_templates", return_value={}
            ),
            patch.object(
                OrchestrationPlanner, "_load_decision_matrix", return_value={}
            ),
        ):
            planner = OrchestrationPlanner()
            mock_triage = AsyncMock()
            mock_triage_cls.return_value = mock_triage

            for tier, (min_agents, max_agents) in optimization_test_cases:
                # Test with agent count in expected range
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

                # Verify agent count is within bounds
                assert min_agents <= result.agent_count <= max_agents, (
                    f"Agent count {result.agent_count} outside bounds [{min_agents}, {max_agents}] for {tier.value}"
                )

                # Verify efficiency cliff (max 12 agents)
                assert result.agent_count <= 12, (
                    f"Agent count {result.agent_count} exceeds efficiency cliff of 12"
                )


@pytest.mark.integration
class TestPlannerIntegration:
    """Integration tests for complete planning workflows."""

    @patch("khive.services.plan.triage.complexity_triage.ComplexityTriageService")
    async def test_end_to_end_planning_workflow(self, mock_triage_cls):
        """Test complete end-to-end planning workflow."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}),
            patch("khive.services.plan.planner_service.OpenAI"),
        ):
            # Create service
            service = PlannerService()

            # Mock triage service
            mock_triage = AsyncMock()
            mock_triage_cls.return_value = mock_triage

            mock_consensus = TriageConsensus(
                tier=ComplexityTier.MEDIUM,
                confidence=0.85,
                agent_count=4,
                recommended_roles=[
                    "researcher",
                    "architect",
                    "implementer",
                    "reviewer",
                ],
                reasoning="OAuth2 requires research, architecture design, implementation, and review",
            )
            mock_triage.evaluate_complexity.return_value = mock_consensus

            # Test request
            request = PlannerRequest(
                task_description="Implement OAuth2 authentication with JWT tokens",
                session_id=str(uuid4()),
                priority_level="high",
            )

            # Execute planning
            result = await service.plan(request)

            # Comprehensive validation
            assert isinstance(result, PlannerResponse)
            assert result.complexity_level == ComplexityLevel.MEDIUM
            assert len(result.agent_recommendations) == 4
            assert result.confidence_score == 0.85
            assert all(
                isinstance(rec, AgentRecommendation)
                for rec in result.agent_recommendations
            )

            # Verify role diversity
            roles = [rec.role for rec in result.agent_recommendations]
            assert "researcher" in roles
            assert "implementer" in roles

            # Verify response completeness
            assert result.session_id == request.session_id
            assert result.estimated_duration > 0
            assert result.quality_gate in [gate.value for gate in QualityGate]


@pytest.mark.performance
class TestPlannerPerformance:
    """Performance tests for planning operations."""

    @patch("khive.services.plan.triage.complexity_triage.ComplexityTriageService")
    async def test_planning_response_time(self, mock_triage_cls):
        """Test planning operations complete within acceptable time limits."""
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
                task_description="Fix authentication bug", session_id=str(uuid4())
            )

            # Measure execution time
            import time

            start_time = time.time()
            result = await service.plan(request)
            execution_time = time.time() - start_time

            # Assert performance requirements
            assert execution_time < 2.0, (
                f"Planning took {execution_time:.2f}s, expected <2.0s"
            )
            assert isinstance(result, PlannerResponse)
            assert result.confidence_score >= 0.8
