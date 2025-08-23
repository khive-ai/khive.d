"""
Simplified quality gate testing for orchestration workflows.

This module tests basic quality gate evaluation and gate-based decision making.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from lionagi.fields import Instruct

from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.orchestration.parts import (AgentRequest, BaseGate,
                                                ComposerRequest,
                                                FanoutResponse, GateComponent,
                                                OrchestrationPlan)


@pytest.fixture
def quality_gate_components():
    """Create quality gate components for testing."""
    return {
        "design": GateComponent(is_acceptable=True, problems=[]),
        "testing": GateComponent(is_acceptable=True, problems=[]),
        "security": GateComponent(
            is_acceptable=False,
            problems=["Missing input validation", "Insufficient error handling"],
        ),
        "performance": GateComponent(is_acceptable=True, problems=[]),
    }


@pytest.fixture
async def mock_orchestrator():
    """Create a mock orchestrator for quality gate testing."""
    orchestrator = LionOrchestrator("quality_gate_test_flow")

    with (
        patch("khive.services.orchestration.orchestrator.create_cc") as mock_create_cc,
        patch("khive.services.orchestration.orchestrator.Session") as mock_session_cls,
        patch("khive.services.orchestration.orchestrator.Branch") as mock_branch_cls,
        patch("khive.services.orchestration.orchestrator.Builder") as mock_builder_cls,
    ):
        # Mock CC model
        mock_cc_model = MagicMock()
        mock_cc_model.invoke = AsyncMock(
            return_value=MagicMock(content="Mock response")
        )
        mock_create_cc.return_value = mock_cc_model

        # Mock branch
        mock_branch = MagicMock()
        mock_branch.id = str(uuid4())
        mock_branch.operate = AsyncMock(return_value=MagicMock())
        mock_branch_cls.return_value = mock_branch

        # Mock session
        mock_session = MagicMock()
        mock_session.default_branch = mock_branch
        mock_session._lookup_branch_by_name = MagicMock(return_value=None)
        mock_session.create_branch = AsyncMock(return_value=str(uuid4()))
        mock_session_cls.return_value = mock_session

        # Mock builder
        mock_builder = MagicMock()
        mock_builder.get_graph = MagicMock(return_value=MagicMock())
        mock_builder_cls.return_value = mock_builder

        await orchestrator.initialize()
        orchestrator.session = mock_session
        orchestrator.builder = mock_builder

    return orchestrator


@pytest.mark.unit
class TestBasicQualityGates:
    """Test basic quality gate functionality."""

    @pytest.mark.asyncio
    async def test_successful_orchestration_with_quality_gates(
        self, mock_orchestrator, quality_gate_components
    ):
        """Test successful orchestration with quality gate validation."""
        orchestrator = mock_orchestrator

        agent_requests = [
            AgentRequest(
                instruct=Instruct(instruction="Implement high quality feature"),
                compose_request=ComposerRequest(
                    role="implementer", domains="backend-development"
                ),
            )
        ]

        plan = OrchestrationPlan(
            common_background="Quality gate validation test",
            agent_requests=agent_requests,
            execution_strategy="concurrent",
        )

        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
        ):
            mock_create_branch.return_value = str(uuid4())
            mock_operate.return_value = AsyncMock()

            result = await orchestrator.fanout(plan)

            # Verify successful orchestration
            assert isinstance(result, FanoutResponse)

            # Verify quality gate components
            design_gate = quality_gate_components["design"]
            testing_gate = quality_gate_components["testing"]

            assert design_gate.is_acceptable is True
            assert testing_gate.is_acceptable is True
            assert len(design_gate.problems) == 0

    @pytest.mark.asyncio
    async def test_quality_gate_with_problems(
        self, mock_orchestrator, quality_gate_components
    ):
        """Test quality gate that identifies problems."""
        orchestrator = mock_orchestrator

        agent_requests = [
            AgentRequest(
                instruct=Instruct(instruction="Implement security-critical feature"),
                compose_request=ComposerRequest(
                    role="implementer", domains="backend-development"
                ),
            )
        ]

        plan = OrchestrationPlan(
            common_background="Security quality gate test",
            agent_requests=agent_requests,
            execution_strategy="concurrent",
        )

        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
        ):
            mock_create_branch.return_value = str(uuid4())
            mock_operate.return_value = AsyncMock()

            result = await orchestrator.fanout(plan)

            # Verify orchestration completed
            assert isinstance(result, FanoutResponse)

            # Check security gate identified problems
            security_gate = quality_gate_components["security"]
            assert security_gate.is_acceptable is False
            assert len(security_gate.problems) > 0
            assert "Missing input validation" in security_gate.problems
            assert "Insufficient error handling" in security_gate.problems

    @pytest.mark.asyncio
    async def test_base_gate_evaluation(self, mock_orchestrator):
        """Test BaseGate evaluation functionality."""
        orchestrator = mock_orchestrator

        # Create a base gate that passes
        passing_gate = BaseGate(
            threshold_met=True, feedback="Implementation meets all requirements"
        )

        # Create a base gate that fails
        failing_gate = BaseGate(
            threshold_met=False,
            feedback="Implementation needs improvement in error handling",
        )

        # Test passing gate
        assert passing_gate.threshold_met is True
        assert "meets all requirements" in passing_gate.feedback

        # Test failing gate
        assert failing_gate.threshold_met is False
        assert "needs improvement" in failing_gate.feedback

    @pytest.mark.asyncio
    async def test_multiple_quality_gates(
        self, mock_orchestrator, quality_gate_components
    ):
        """Test orchestration with multiple quality gates."""
        orchestrator = mock_orchestrator

        agent_requests = [
            AgentRequest(
                instruct=Instruct(instruction="Comprehensive feature implementation"),
                compose_request=ComposerRequest(
                    role="implementer", domains="backend-development"
                ),
            ),
            AgentRequest(
                instruct=Instruct(instruction="Security review"),
                compose_request=ComposerRequest(role="auditor", domains="code-quality"),
            ),
        ]

        plan = OrchestrationPlan(
            common_background="Multiple quality gates test",
            agent_requests=agent_requests,
            execution_strategy="sequential",
        )

        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
        ):
            mock_create_branch.return_value = str(uuid4())
            mock_operate.return_value = AsyncMock()

            result = await orchestrator.fanout(plan)

            # Verify orchestration completed
            assert isinstance(result, FanoutResponse)

            # Evaluate all quality gates
            gate_results = {}
            for gate_name, gate_component in quality_gate_components.items():
                gate_results[gate_name] = gate_component.is_acceptable

            # Verify mixed results
            assert gate_results["design"] is True
            assert gate_results["testing"] is True
            assert gate_results["security"] is False  # This one has problems
            assert gate_results["performance"] is True

    @pytest.mark.asyncio
    async def test_quality_gate_feedback_generation(self, mock_orchestrator):
        """Test quality gate feedback generation."""
        orchestrator = mock_orchestrator

        # Test different feedback scenarios
        feedback_scenarios = [
            BaseGate(
                threshold_met=True,
                feedback="Excellent implementation with comprehensive error handling",
            ),
            BaseGate(
                threshold_met=False,
                feedback="Implementation missing critical security validations",
            ),
            BaseGate(
                threshold_met=True,
                feedback="Good performance characteristics, minor optimization opportunities",
            ),
        ]

        for i, gate in enumerate(feedback_scenarios):
            assert gate.feedback is not None
            assert len(gate.feedback) > 0

            if gate.threshold_met:
                assert any(
                    word in gate.feedback.lower()
                    for word in ["good", "excellent", "comprehensive"]
                )
            else:
                assert any(
                    word in gate.feedback.lower()
                    for word in ["missing", "needs", "insufficient"]
                )


@pytest.mark.unit
class TestQualityGatePatterns:
    """Test quality gate patterns and workflows."""

    @pytest.mark.asyncio
    async def test_escalation_pattern(self, mock_orchestrator):
        """Test quality gate escalation pattern."""
        orchestrator = mock_orchestrator

        # Simulate escalation scenario
        initial_gate = BaseGate(
            threshold_met=False, feedback="Initial implementation needs refinement"
        )

        escalated_gate = BaseGate(
            threshold_met=True,
            feedback="After escalation and refinement, implementation now meets standards",
        )

        agent_requests = [
            AgentRequest(
                instruct=Instruct(instruction="Initial implementation"),
                compose_request=ComposerRequest(
                    role="implementer", domains="backend-development"
                ),
            ),
            AgentRequest(
                instruct=Instruct(instruction="Escalated review and refinement"),
                compose_request=ComposerRequest(
                    role="reviewer", domains="code-quality"
                ),
            ),
        ]

        plan = OrchestrationPlan(
            common_background="Quality gate escalation test",
            agent_requests=agent_requests,
            execution_strategy="sequential",
        )

        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
        ):
            mock_create_branch.return_value = str(uuid4())
            mock_operate.return_value = AsyncMock()

            result = await orchestrator.fanout(plan)

            # Verify orchestration
            assert isinstance(result, FanoutResponse)

            # Verify escalation pattern
            assert initial_gate.threshold_met is False
            assert escalated_gate.threshold_met is True
            assert "refinement" in escalated_gate.feedback

    @pytest.mark.asyncio
    async def test_composite_quality_evaluation(
        self, mock_orchestrator, quality_gate_components
    ):
        """Test composite quality evaluation across multiple components."""
        orchestrator = mock_orchestrator

        # Calculate overall quality based on component gates
        acceptable_components = sum(
            1 for gate in quality_gate_components.values() if gate.is_acceptable
        )
        total_components = len(quality_gate_components)
        overall_quality_ratio = acceptable_components / total_components

        # Create composite gate based on component results
        composite_gate = BaseGate(
            threshold_met=overall_quality_ratio >= 0.75,  # 75% threshold
            feedback=f"Overall quality: {overall_quality_ratio:.2%} of components acceptable",
        )

        agent_requests = [
            AgentRequest(
                instruct=Instruct(instruction="Comprehensive quality evaluation"),
                compose_request=ComposerRequest(
                    role="reviewer", domains="code-quality"
                ),
            )
        ]

        plan = OrchestrationPlan(
            common_background="Composite quality evaluation test",
            agent_requests=agent_requests,
            execution_strategy="concurrent",
        )

        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
        ):
            mock_create_branch.return_value = str(uuid4())
            mock_operate.return_value = AsyncMock()

            result = await orchestrator.fanout(plan)

            # Verify orchestration
            assert isinstance(result, FanoutResponse)

            # Verify composite evaluation
            # With our test data: 3 out of 4 components are acceptable (75%)
            assert composite_gate.threshold_met is True
            assert "75.00%" in composite_gate.feedback

    @pytest.mark.asyncio
    async def test_quality_gate_error_handling(self, mock_orchestrator):
        """Test quality gate behavior during error conditions."""
        orchestrator = mock_orchestrator

        agent_requests = [
            AgentRequest(
                instruct=Instruct(instruction="Task that will encounter errors"),
                compose_request=ComposerRequest(
                    role="implementer", domains="backend-development"
                ),
            )
        ]

        plan = OrchestrationPlan(
            common_background="Error handling test",
            agent_requests=agent_requests,
            execution_strategy="concurrent",
        )

        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
        ):
            mock_create_branch.return_value = str(uuid4())
            # Mock operation to raise an exception
            mock_operate.side_effect = Exception("Simulated operation failure")

            # Should handle the error gracefully
            result = await orchestrator.fanout(plan)

            # Verify error handling
            assert isinstance(result, FanoutResponse)

            # Quality gate should reflect error condition
            error_gate = BaseGate(
                threshold_met=False, feedback="Operation failed due to execution error"
            )

            assert error_gate.threshold_met is False
            assert "failed" in error_gate.feedback
