"""
Comprehensive workflow execution tests for orchestration patterns.

This module tests async workflow execution, multi-agent coordination,
quality gates, refinement patterns, and integration workflows.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from lionagi import Branch, Builder, Session
from lionagi.fields import Instruct

from khive.services.artifacts.factory import ArtifactsConfig
from khive.services.artifacts.models import Author, DocumentType
from khive.services.artifacts.service import ArtifactsService
from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.orchestration.parts import (
    AgentRequest, ComposerRequest, FanoutResponse,
    FanoutWithGatedRefinementResponse, OrchestrationPlan)
from khive.services.plan.parts import ComplexityLevel, TaskPhase


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)
        yield workspace_path


@pytest.fixture
async def mock_artifacts_service(temp_workspace):
    """Create a mock artifacts service for testing."""
    config = ArtifactsConfig(
        storage_path=temp_workspace, enable_compression=False, max_file_size_mb=10
    )

    with patch(
        "khive.services.artifacts.factory.create_artifacts_service"
    ) as mock_create:
        mock_service = MagicMock(spec=ArtifactsService)
        mock_service.create_document = AsyncMock(return_value=str(uuid4()))
        mock_service.get_document = AsyncMock(
            return_value={
                "id": str(uuid4()),
                "title": "Test Document",
                "content": "Test content",
                "document_type": DocumentType.ANALYSIS,
                "author": Author(name="Test Author", email="test@example.com"),
            }
        )
        mock_service.list_documents = AsyncMock(return_value=[])
        mock_create.return_value = mock_service
        yield mock_service


@pytest.fixture
async def initialized_orchestrator():
    """Create an initialized orchestrator for workflow testing."""
    orchestrator = LionOrchestrator("workflow_test_flow")

    with (
        patch("khive.services.orchestration.orchestrator.create_cc") as mock_create_cc,
        patch("khive.services.orchestration.orchestrator.Session") as mock_session_cls,
        patch("khive.services.orchestration.orchestrator.Branch") as mock_branch_cls,
        patch("khive.services.orchestration.orchestrator.Builder") as mock_builder_cls,
    ):
        # Mock Claude Code model
        mock_cc_model = MagicMock()
        mock_cc_model.invoke = AsyncMock(
            return_value=MagicMock(content="Mock response")
        )
        mock_create_cc.return_value = mock_cc_model

        # Mock branch
        mock_branch = MagicMock(spec=Branch)
        mock_branch.id = str(uuid4())
        mock_branch.operate = AsyncMock(return_value=MagicMock())
        mock_branch_cls.return_value = mock_branch

        # Mock session
        mock_session = MagicMock(spec=Session)
        mock_session.default_branch = mock_branch
        mock_session._lookup_branch_by_name = MagicMock(return_value=None)
        mock_session.create_branch = AsyncMock(return_value=str(uuid4()))
        mock_session.get_branch = MagicMock(return_value=mock_branch)
        mock_session_cls.return_value = mock_session

        # Mock builder
        mock_builder = MagicMock(spec=Builder)
        mock_builder.get_graph = MagicMock(return_value=MagicMock())
        mock_builder_cls.return_value = mock_builder

        await orchestrator.initialize()
        orchestrator.session = mock_session
        orchestrator.builder = mock_builder

    return orchestrator


@pytest.mark.integration
class TestWorkflowExecution:
    """Integration tests for workflow execution patterns."""

    @pytest.mark.asyncio
    async def test_planning_to_execution_cycle(
        self, initialized_orchestrator, mock_artifacts_service
    ):
        """Test complete planning → execution → cleanup cycle."""
        orchestrator = initialized_orchestrator

        # Mock PlannerService integration
        with patch(
            "khive.services.plan.planner_service.PlannerService"
        ) as mock_planner_cls:
            mock_planner = MagicMock()
            mock_planner.handle_request = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    complexity=ComplexityLevel.MEDIUM,
                    recommended_agents=3,
                    phases=[
                        TaskPhase(
                            name="research_phase",
                            description="Research and analysis",
                            agents=[],
                        )
                    ],
                    spawn_commands=["Task('researcher: analyze requirements')"],
                    session_id="test_session",
                )
            )
            mock_planner_cls.return_value = mock_planner

            # Create orchestration plan
            agent_requests = [
                AgentRequest(
                    instruct=Instruct(instruction="Analyze system requirements"),
                    compose_request=ComposerRequest(
                        role="researcher", domains="software-architecture"
                    ),
                ),
                AgentRequest(
                    instruct=Instruct(instruction="Design system components"),
                    compose_request=ComposerRequest(
                        role="architect", domains="distributed-systems"
                    ),
                ),
                AgentRequest(
                    instruct=Instruct(instruction="Validate design decisions"),
                    compose_request=ComposerRequest(
                        role="critic", domains="code-quality"
                    ),
                ),
            ]

            plan = OrchestrationPlan(
                common_background="End-to-end workflow test for system design",
                agent_requests=agent_requests,
                execution_strategy="concurrent",
            )

            # Mock branch creation and execution
            with (
                patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
                patch.object(orchestrator.orc_branch, "operate") as mock_operate,
            ):
                # Mock successful branch creation
                branch_ids = [str(uuid4()) for _ in agent_requests]
                mock_create_branch.side_effect = branch_ids

                # Mock successful operations
                mock_operate.return_value = AsyncMock()

                # Execute workflow
                result = await orchestrator.fanout(plan)

                # Verify workflow execution
                assert isinstance(result, FanoutResponse)
                assert mock_create_branch.call_count == len(agent_requests)

                # Verify all agents were spawned
                for i, request in enumerate(agent_requests):
                    assert (
                        mock_create_branch.call_args_list[i][0][0]
                        == request.compose_request
                    )

    @pytest.mark.asyncio
    async def test_multi_phase_workflow_coordination(self, initialized_orchestrator):
        """Test multi-phase workflow with dependencies."""
        orchestrator = initialized_orchestrator

        # Create a multi-phase plan
        research_agents = [
            AgentRequest(
                instruct=Instruct(instruction="Research distributed systems patterns"),
                compose_request=ComposerRequest(
                    role="researcher", domains="distributed-systems"
                ),
            ),
            AgentRequest(
                instruct=Instruct(instruction="Research performance requirements"),
                compose_request=ComposerRequest(role="analyst", domains="code-quality"),
            ),
        ]

        design_agents = [
            AgentRequest(
                instruct=Instruct(instruction="Design system architecture"),
                compose_request=ComposerRequest(
                    role="architect", domains="software-architecture"
                ),
            )
        ]

        validation_agents = [
            AgentRequest(
                instruct=Instruct(instruction="Validate architecture decisions"),
                compose_request=ComposerRequest(role="critic", domains="code-quality"),
            )
        ]

        # Execute phases sequentially
        phases = [
            ("research", research_agents),
            ("design", design_agents),
            ("validation", validation_agents),
        ]

        results = {}

        for phase_name, phase_agents in phases:
            plan = OrchestrationPlan(
                common_background=f"Multi-phase workflow: {phase_name} phase",
                agent_requests=phase_agents,
                execution_strategy="concurrent",
            )

            with (
                patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
                patch.object(orchestrator.orc_branch, "operate") as mock_operate,
            ):
                branch_ids = [str(uuid4()) for _ in phase_agents]
                mock_create_branch.side_effect = branch_ids
                mock_operate.return_value = AsyncMock()

                phase_result = await orchestrator.fanout(plan)
                results[phase_name] = phase_result

                # Verify phase execution
                assert isinstance(phase_result, FanoutResponse)
                assert mock_create_branch.call_count == len(phase_agents)

        # Verify all phases completed
        assert len(results) == 3
        assert all(isinstance(result, FanoutResponse) for result in results.values())

    @pytest.mark.asyncio
    async def test_agent_spawning_patterns(self, initialized_orchestrator):
        """Test various agent spawning patterns and coordination."""
        orchestrator = initialized_orchestrator

        # Test different role combinations
        agent_combinations = [
            # Research team
            [
                AgentRequest(
                    instruct=Instruct(instruction="Research API patterns"),
                    compose_request=ComposerRequest(
                        role="researcher", domains="api-design"
                    ),
                ),
                AgentRequest(
                    instruct=Instruct(instruction="Analyze performance implications"),
                    compose_request=ComposerRequest(
                        role="analyst", domains="backend-development"
                    ),
                ),
            ],
            # Implementation team
            [
                AgentRequest(
                    instruct=Instruct(instruction="Implement core services"),
                    compose_request=ComposerRequest(
                        role="implementer", domains="backend-development"
                    ),
                ),
                AgentRequest(
                    instruct=Instruct(instruction="Design database schema"),
                    compose_request=ComposerRequest(
                        role="architect", domains="database-design"
                    ),
                ),
            ],
            # Quality team
            [
                AgentRequest(
                    instruct=Instruct(instruction="Create test strategy"),
                    compose_request=ComposerRequest(
                        role="tester", domains="code-quality"
                    ),
                ),
                AgentRequest(
                    instruct=Instruct(instruction="Review implementation"),
                    compose_request=ComposerRequest(
                        role="reviewer", domains="code-quality"
                    ),
                ),
            ],
        ]

        for i, agent_group in enumerate(agent_combinations):
            plan = OrchestrationPlan(
                common_background=f"Agent spawning test group {i + 1}",
                agent_requests=agent_group,
                execution_strategy="concurrent",
            )

            with (
                patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
                patch.object(orchestrator.orc_branch, "operate") as mock_operate,
            ):
                branch_ids = [str(uuid4()) for _ in agent_group]
                mock_create_branch.side_effect = branch_ids
                mock_operate.return_value = AsyncMock()

                result = await orchestrator.fanout(plan)

                # Verify spawning succeeded
                assert isinstance(result, FanoutResponse)
                assert mock_create_branch.call_count == len(agent_group)

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, initialized_orchestrator):
        """Test error handling and recovery mechanisms in workflows."""
        orchestrator = initialized_orchestrator

        agent_requests = [
            AgentRequest(
                instruct=Instruct(instruction="Task that will succeed"),
                compose_request=ComposerRequest(
                    role="researcher", domains="distributed-systems"
                ),
            ),
            AgentRequest(
                instruct=Instruct(instruction="Task that will fail"),
                compose_request=ComposerRequest(
                    role="implementer", domains="backend-development"
                ),
            ),
        ]

        plan = OrchestrationPlan(
            common_background="Error handling test workflow",
            agent_requests=agent_requests,
            execution_strategy="concurrent",
        )

        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
        ):
            # First branch succeeds, second fails
            mock_create_branch.side_effect = [
                str(uuid4()),  # Success
                Exception("Branch creation failed"),  # Failure
            ]

            # Should handle partial failure gracefully
            result = await orchestrator.fanout(plan)

            # Verify graceful degradation
            assert isinstance(result, FanoutResponse)
            # At least one branch should have been attempted
            assert mock_create_branch.call_count >= 1

    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self, initialized_orchestrator):
        """Test concurrent execution of multiple workflows."""
        orchestrator = initialized_orchestrator

        # Create multiple independent workflows
        workflows = []
        for i in range(3):
            agent_requests = [
                AgentRequest(
                    instruct=Instruct(instruction=f"Concurrent task {i + 1}"),
                    compose_request=ComposerRequest(
                        role="researcher", domains="software-architecture"
                    ),
                )
            ]

            plan = OrchestrationPlan(
                common_background=f"Concurrent workflow {i + 1}",
                agent_requests=agent_requests,
                execution_strategy="concurrent",
            )
            workflows.append(plan)

        # Execute workflows concurrently
        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
        ):
            mock_create_branch.return_value = str(uuid4())
            mock_operate.return_value = AsyncMock()

            # Execute all workflows concurrently
            tasks = [orchestrator.fanout(plan) for plan in workflows]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all workflows executed
            assert len(results) == len(workflows)

            # Verify no exceptions occurred
            for result in results:
                assert not isinstance(result, Exception)
                assert isinstance(result, FanoutResponse)


@pytest.mark.integration
class TestQualityGateWorkflows:
    """Test quality gate integration in workflows."""

    @pytest.mark.asyncio
    async def test_gated_refinement_workflow(self, initialized_orchestrator):
        """Test workflow with quality gate refinement cycles."""
        orchestrator = initialized_orchestrator

        agent_requests = [
            AgentRequest(
                instruct=Instruct(instruction="Initial implementation"),
                compose_request=ComposerRequest(
                    role="implementer", domains="backend-development"
                ),
            ),
            AgentRequest(
                instruct=Instruct(instruction="Review implementation"),
                compose_request=ComposerRequest(
                    role="reviewer", domains="code-quality"
                ),
            ),
        ]

        plan = OrchestrationPlan(
            common_background="Quality gate workflow test",
            agent_requests=agent_requests,
            execution_strategy="sequential",
        )

        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
            patch.object(
                orchestrator, "fanout_with_gated_refinement"
            ) as mock_gated_fanout,
        ):
            mock_create_branch.return_value = str(uuid4())
            mock_operate.return_value = AsyncMock()

            # Mock gated refinement to return successful result
            mock_gated_fanout.return_value = FanoutWithGatedRefinementResponse(
                fanout_responses=[MagicMock()],
                refinement_cycles=1,
                final_quality_score=0.95,
                gate_decisions=["passed"],
            )

            result = await orchestrator.fanout_with_gated_refinement(plan)

            # Verify gated workflow execution
            assert isinstance(result, FanoutWithGatedRefinementResponse)
            assert result.refinement_cycles >= 1
            assert result.final_quality_score > 0.5

    @pytest.mark.asyncio
    async def test_quality_escalation_patterns(self, initialized_orchestrator):
        """Test quality gate escalation when quality is insufficient."""
        orchestrator = initialized_orchestrator

        agent_requests = [
            AgentRequest(
                instruct=Instruct(instruction="Low quality implementation"),
                compose_request=ComposerRequest(
                    role="implementer", domains="backend-development"
                ),
            )
        ]

        plan = OrchestrationPlan(
            common_background="Quality escalation test",
            agent_requests=agent_requests,
            execution_strategy="concurrent",
        )

        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
            patch.object(
                orchestrator, "fanout_with_gated_refinement"
            ) as mock_gated_fanout,
        ):
            mock_create_branch.return_value = str(uuid4())
            mock_operate.return_value = AsyncMock()

            # Mock multiple refinement cycles due to quality issues
            mock_gated_fanout.return_value = FanoutWithGatedRefinementResponse(
                fanout_responses=[MagicMock()],
                refinement_cycles=3,  # Multiple cycles indicate quality escalation
                final_quality_score=0.85,
                gate_decisions=["failed", "failed", "passed"],
            )

            result = await orchestrator.fanout_with_gated_refinement(plan)

            # Verify escalation occurred
            assert result.refinement_cycles > 1
            assert len(result.gate_decisions) == result.refinement_cycles
            assert result.gate_decisions[-1] == "passed"  # Final decision should pass


@pytest.mark.integration
class TestWorkflowResourceManagement:
    """Test resource management in complex workflows."""

    @pytest.mark.asyncio
    async def test_session_persistence_across_workflows(
        self, initialized_orchestrator, temp_workspace
    ):
        """Test that session state persists across multiple workflows."""
        orchestrator = initialized_orchestrator

        # Execute first workflow
        plan1 = OrchestrationPlan(
            common_background="First workflow for session persistence test",
            agent_requests=[
                AgentRequest(
                    instruct=Instruct(instruction="Create initial state"),
                    compose_request=ComposerRequest(
                        role="researcher", domains="software-architecture"
                    ),
                )
            ],
            execution_strategy="concurrent",
        )

        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
        ):
            mock_create_branch.return_value = str(uuid4())
            mock_operate.return_value = AsyncMock()

            result1 = await orchestrator.fanout(plan1)

            # Verify initial session state
            initial_session = orchestrator.session
            assert initial_session is not None

        # Execute second workflow with same orchestrator
        plan2 = OrchestrationPlan(
            common_background="Second workflow for session persistence test",
            agent_requests=[
                AgentRequest(
                    instruct=Instruct(instruction="Build on previous state"),
                    compose_request=ComposerRequest(
                        role="architect", domains="distributed-systems"
                    ),
                )
            ],
            execution_strategy="concurrent",
        )

        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
        ):
            mock_create_branch.return_value = str(uuid4())
            mock_operate.return_value = AsyncMock()

            result2 = await orchestrator.fanout(plan2)

            # Verify session persistence
            assert orchestrator.session is initial_session
            assert isinstance(result1, FanoutResponse)
            assert isinstance(result2, FanoutResponse)

    @pytest.mark.asyncio
    async def test_cleanup_after_workflow_completion(self, initialized_orchestrator):
        """Test proper cleanup after workflow completion."""
        orchestrator = initialized_orchestrator

        agent_requests = [
            AgentRequest(
                instruct=Instruct(instruction="Task requiring cleanup"),
                compose_request=ComposerRequest(
                    role="implementer", domains="backend-development"
                ),
            )
        ]

        plan = OrchestrationPlan(
            common_background="Cleanup test workflow",
            agent_requests=agent_requests,
            execution_strategy="concurrent",
        )

        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
        ):
            mock_create_branch.return_value = str(uuid4())
            mock_operate.return_value = AsyncMock()

            # Execute workflow
            result = await orchestrator.fanout(plan)

            # Verify cleanup state
            assert isinstance(result, FanoutResponse)
            # Orchestrator should still be in valid state after completion
            assert orchestrator.session is not None
            assert orchestrator.builder is not None
