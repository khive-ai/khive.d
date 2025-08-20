"""Integration tests for LionOrchestrator workflow patterns."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.orchestration.parts import (
    FanoutResponse,
    FanoutWithGatedRefinementResponse,
)


class TestFanoutPattern:
    """Test fanout orchestration pattern."""

    @pytest.mark.asyncio
    async def test_fanout_complete_workflow(self, orchestrator_with_mocks):
        """Test complete fanout workflow."""
        orchestrator = orchestrator_with_mocks

        # Mock all dependencies
        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc

            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch_id"
            mock_branch_cls.return_value = mock_branch

            # Setup operation IDs
            root_id = "planning_operation"
            initial_nodes = ["agent1", "agent2", "agent3"]
            synth_node = "synthesis_operation"

            orchestrator.builder.add_operation.side_effect = [
                root_id,
                *initial_nodes,
                synth_node,
            ]
            orchestrator.builder.last_operation_id = None

            # Mock flow execution results
            flow_results = {
                "operation_results": {
                    root_id: MagicMock(flow_plans=MagicMock(initial=MagicMock())),
                    synth_node: "Synthesis result",
                }
            }
            orchestrator.session.flow.return_value = flow_results

            # Mock expand_with_plan
            orchestrator.expand_with_plan = AsyncMock(return_value=initial_nodes)

            # Mock opres_ctx
            orchestrator.opres_ctx = MagicMock(return_value=[{"context": "test"}])

            result = await orchestrator.fanout(
                initial_desc="Test initial phase",
                planning_instruction="Plan the work",
                synth_instruction="Synthesize results",
                context="Test context",
                max_agents=5,
            )

            # Verify result structure
            assert isinstance(result, FanoutResponse)
            assert result.synth_node == synth_node
            assert result.synth_result == "Synthesis result"
            assert result.flow_results == flow_results
            assert result.initial_nodes == initial_nodes

            # Verify expand_with_plan was called correctly
            orchestrator.expand_with_plan.assert_called_once()
            call_kwargs = orchestrator.expand_with_plan.call_args.kwargs
            assert call_kwargs["root"] == root_id
            assert call_kwargs["max_agents"] == 5
            assert call_kwargs["auto_context"] is True
            assert call_kwargs["skip_root_context"] is True

    @pytest.mark.asyncio
    async def test_fanout_with_visualization(self, orchestrator_with_mocks):
        """Test fanout with step-by-step visualization."""
        orchestrator = orchestrator_with_mocks

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc
            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch_id"
            mock_branch_cls.return_value = mock_branch

            orchestrator.builder.add_operation.side_effect = ["root", "agent1", "synth"]
            orchestrator.session.flow.return_value = {
                "operation_results": {
                    "root": MagicMock(flow_plans=MagicMock(initial=MagicMock())),
                    "synth": "result",
                }
            }
            orchestrator.expand_with_plan = AsyncMock(return_value=["agent1"])
            orchestrator.opres_ctx = MagicMock(return_value=[])

            await orchestrator.fanout(
                initial_desc="Test",
                planning_instruction="Plan",
                synth_instruction="Synthesize",
                visualize="step",
            )

            # Should call run_flow multiple times with visualize=True for steps
            assert orchestrator.session.flow.call_count >= 2
            # Final call should have visualization
            orchestrator.builder.visualize.assert_called()

    @pytest.mark.asyncio
    async def test_fanout_with_dependencies(self, orchestrator_with_mocks):
        """Test fanout with existing dependencies."""
        orchestrator = orchestrator_with_mocks

        # Set existing operation
        existing_op = "existing_operation"
        orchestrator.builder.last_operation_id = existing_op

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc
            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch_id"
            mock_branch_cls.return_value = mock_branch

            root_id = "planning_operation"
            orchestrator.builder.add_operation.side_effect = [
                root_id,
                "agent1",
                "synth",
            ]
            orchestrator.session.flow.return_value = {
                "operation_results": {
                    root_id: MagicMock(flow_plans=MagicMock(initial=MagicMock())),
                    "synth": "result",
                }
            }
            orchestrator.expand_with_plan = AsyncMock(return_value=["agent1"])
            orchestrator.opres_ctx = MagicMock(return_value=[])

            await orchestrator.fanout(
                initial_desc="Test",
                planning_instruction="Plan",
                synth_instruction="Synthesize",
            )

            # Verify root operation depends on existing operation
            first_call = orchestrator.builder.add_operation.call_args_list[0]
            assert first_call.kwargs["depends_on"] == [existing_op]


class TestFanoutWithGatedRefinement:
    """Test fanout with gated refinement pattern."""

    @pytest.mark.asyncio
    async def test_gated_refinement_gates_pass(self, orchestrator_with_mocks):
        """Test gated refinement when quality gates pass."""
        orchestrator = orchestrator_with_mocks

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc
            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch_id"
            mock_branch_cls.return_value = mock_branch

            # Setup operation IDs
            root_id = "planning_operation"
            initial_nodes = ["agent1", "agent2"]
            qa_branch_id = "qa_branch_id"
            gate1_id = "gate1_operation"
            synth_node = "synthesis_operation"

            orchestrator.builder.add_operation.side_effect = [
                root_id,
                *initial_nodes,
                gate1_id,
                synth_node,
            ]

            # Mock quality gate that passes
            mock_gate = MagicMock()
            mock_gate.threshold_met = True

            flow_results = {
                "operation_results": {
                    root_id: MagicMock(
                        flow_plans=MagicMock(
                            initial=MagicMock(),
                            refinement=MagicMock(),
                        )
                    ),
                    gate1_id: MagicMock(quality_gate=mock_gate),
                    synth_node: "Final synthesis result",
                }
            }
            orchestrator.session.flow.return_value = flow_results

            # Mock dependencies
            orchestrator.expand_with_plan = AsyncMock(return_value=initial_nodes)
            orchestrator.create_cc_branch = AsyncMock(return_value=qa_branch_id)
            orchestrator.opres_ctx = MagicMock(return_value=[{"context": "test"}])

            result = await orchestrator.fanout_w_gated_refinement(
                initial_desc="Initial work",
                refinement_desc="Refinement work",
                gate_instruction="Evaluate quality",
                synth_instruction="Final synthesis",
                planning_instruction="Create plan",
                gates={"design": True, "security": "Custom security check"},
            )

            # Verify result
            assert isinstance(result, FanoutWithGatedRefinementResponse)
            assert result.gate_passed is True
            assert result.refinement_executed is False
            assert result.synth_result == "Final synthesis result"
            assert result.final_gate == gate1_id

            # Should not have expanded refinement plan since gate passed
            assert orchestrator.expand_with_plan.call_count == 1

    @pytest.mark.asyncio
    async def test_gated_refinement_with_refinement(self, orchestrator_with_mocks):
        """Test gated refinement when initial quality fails but refinement passes."""
        orchestrator = orchestrator_with_mocks

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc
            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch_id"
            mock_branch_cls.return_value = mock_branch

            # Setup operation IDs
            root_id = "planning_operation"
            initial_nodes = ["agent1", "agent2"]
            refinement_nodes = ["refine1", "refine2"]
            qa_branch_id = "qa_branch_id"
            gate1_id = "gate1_operation"
            gate2_id = "gate2_operation"
            synth_node = "synthesis_operation"

            orchestrator.builder.add_operation.side_effect = [
                root_id,
                *initial_nodes,
                gate1_id,
                *refinement_nodes,
                gate2_id,
                synth_node,
            ]

            # First gate fails, second passes
            mock_gate1 = MagicMock()
            mock_gate1.threshold_met = False
            mock_gate2 = MagicMock()
            mock_gate2.threshold_met = True

            # Mock concurrent execution plan
            mock_refinement_plan = MagicMock()
            mock_refinement_plan.execution_strategy = "concurrent"

            flow_results_calls = [
                # First flow result (planning + initial + first gate)
                {
                    "operation_results": {
                        root_id: MagicMock(
                            flow_plans=MagicMock(
                                initial=MagicMock(),
                                refinement=mock_refinement_plan,
                            )
                        ),
                        gate1_id: MagicMock(quality_gate=mock_gate1),
                    }
                },
                # Second flow result (refinement + second gate)
                {
                    "operation_results": {
                        gate2_id: MagicMock(quality_gate=mock_gate2),
                    }
                },
                # Final flow result (synthesis)
                {
                    "operation_results": {
                        synth_node: "Refined synthesis result",
                    }
                },
            ]
            orchestrator.session.flow.side_effect = flow_results_calls

            # Mock dependencies
            orchestrator.expand_with_plan = AsyncMock(
                side_effect=[initial_nodes, refinement_nodes]
            )
            orchestrator.create_cc_branch = AsyncMock(return_value=qa_branch_id)
            orchestrator.opres_ctx = MagicMock(return_value=[{"context": "test"}])

            result = await orchestrator.fanout_w_gated_refinement(
                initial_desc="Initial work",
                refinement_desc="Refinement work",
                gate_instruction="Evaluate quality",
                synth_instruction="Final synthesis",
                planning_instruction="Create plan",
                gates={"design": True},
            )

            # Verify result
            assert isinstance(result, FanoutWithGatedRefinementResponse)
            assert result.gate_passed is True
            assert result.refinement_executed is True
            assert result.final_gate == gate2_id

            # Should have expanded both initial and refinement plans
            assert orchestrator.expand_with_plan.call_count == 2

    @pytest.mark.asyncio
    async def test_gated_refinement_context_aware(self, orchestrator_with_mocks):
        """Test gated refinement with context-aware gate configuration."""
        orchestrator = orchestrator_with_mocks

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc
            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch_id"
            mock_branch_cls.return_value = mock_branch

            orchestrator.builder.add_operation.side_effect = [
                "root",
                "agent1",
                "gate",
                "synth",
            ]

            mock_gate = MagicMock()
            mock_gate.threshold_met = True

            orchestrator.session.flow.return_value = {
                "operation_results": {
                    "root": MagicMock(
                        flow_plans=MagicMock(
                            initial=MagicMock(),
                            refinement=MagicMock(),
                        )
                    ),
                    "gate": MagicMock(quality_gate=mock_gate),
                    "synth": "result",
                }
            }
            orchestrator.expand_with_plan = AsyncMock(return_value=["agent1"])
            orchestrator.create_cc_branch = AsyncMock(return_value="qa_branch")
            orchestrator.opres_ctx = MagicMock(return_value=[])

            result = await orchestrator.fanout_w_gated_refinement(
                initial_desc="Initial work",
                refinement_desc="Refinement work",
                gate_instruction="Evaluate quality",
                synth_instruction="Final synthesis",
                planning_instruction="Create plan",
                project_phase="development",
                is_critical_path=True,
                is_experimental=False,
                gates={"performance": True, "security": "Custom security validation"},
            )

            assert isinstance(result, FanoutWithGatedRefinementResponse)

    @pytest.mark.asyncio
    async def test_gated_refinement_invalid_gates(self, orchestrator_with_mocks):
        """Test gated refinement with invalid gate configuration."""
        orchestrator = orchestrator_with_mocks

        with pytest.raises(ValueError, match="Invalid gate component"):
            await orchestrator.fanout_w_gated_refinement(
                initial_desc="Initial work",
                refinement_desc="Refinement work",
                gate_instruction="Evaluate quality",
                synth_instruction="Final synthesis",
                planning_instruction="Create plan",
                gates={"design": 123},  # Invalid type
            )

    @pytest.mark.asyncio
    async def test_gated_refinement_custom_critic(self, orchestrator_with_mocks):
        """Test gated refinement with custom critic configuration."""
        orchestrator = orchestrator_with_mocks

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc
            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch_id"
            mock_branch_cls.return_value = mock_branch

            orchestrator.builder.add_operation.side_effect = [
                "root",
                "agent1",
                "gate",
                "synth",
            ]

            mock_gate = MagicMock()
            mock_gate.threshold_met = True

            orchestrator.session.flow.return_value = {
                "operation_results": {
                    "root": MagicMock(
                        flow_plans=MagicMock(
                            initial=MagicMock(),
                            refinement=MagicMock(),
                        )
                    ),
                    "gate": MagicMock(quality_gate=mock_gate),
                    "synth": "result",
                }
            }
            orchestrator.expand_with_plan = AsyncMock(return_value=["agent1"])
            orchestrator.create_cc_branch = AsyncMock(return_value="qa_branch")
            orchestrator.opres_ctx = MagicMock(return_value=[])

            await orchestrator.fanout_w_gated_refinement(
                initial_desc="Initial work",
                refinement_desc="Refinement work",
                gate_instruction="Evaluate quality",
                synth_instruction="Final synthesis",
                planning_instruction="Create plan",
                critic_domain="security-architecture",
                critic_role="auditor",
                gates=["security", "performance"],
            )

            # Verify custom critic was used in branch creation
            orchestrator.create_cc_branch.assert_called_once()
            call_args = orchestrator.create_cc_branch.call_args
            compose_request = (
                call_args[0][0] if call_args[0] else call_args.kwargs["compose_request"]
            )
            assert compose_request.role == "auditor"
            assert compose_request.domains == "security-architecture"


class TestSessionManagement:
    """Test session management and persistence."""

    @pytest.mark.asyncio
    async def test_save_json(
        self, orchestrator_with_mocks, mock_aiofiles, mock_file_system
    ):
        """Test session state saving."""
        orchestrator = orchestrator_with_mocks

        # Setup session data
        orchestrator.session.id = "test_session_id"
        orchestrator.session.name = "test_session"
        orchestrator.session.created_at = "2025-08-20T12:00:00Z"

        # Mock branches
        mock_branch1 = MagicMock()
        mock_branch1.to_dict = MagicMock(
            return_value={"id": "branch1", "name": "branch1"}
        )
        mock_branch2 = MagicMock()
        mock_branch2.to_dict = MagicMock(
            return_value={"id": "branch2", "name": "branch2"}
        )

        orchestrator.session.branches = [mock_branch1, mock_branch2]
        orchestrator.session.default_branch.to_dict = MagicMock(
            return_value={"id": "default", "name": "default"}
        )

        # Mock graph
        mock_graph = MagicMock()
        mock_graph.to_dict = MagicMock(return_value={"nodes": [], "edges": []})
        orchestrator.builder.get_graph.return_value = mock_graph

        await orchestrator.save_json()

        # Verify file was written
        mock_aiofiles.open.assert_called_once()
        file_path = mock_aiofiles.open.call_args[0][0]
        assert "test_flow_session" in str(file_path)

        # Verify JSON content was written
        mock_aiofiles.open.return_value.__aenter__.return_value.write.assert_called_once()
        written_content = (
            mock_aiofiles.open.return_value.__aenter__.return_value.write.call_args[0][
                0
            ]
        )
        data = json.loads(written_content)

        assert "branches" in data
        assert "session_default_branch" in data
        assert "metadata" in data
        assert "graph" in data

    @pytest.mark.asyncio
    async def test_load_json(self, mock_aiofiles, tmp_path):
        """Test session state loading."""
        # Create test file
        test_file = tmp_path / "test_session.json"

        session_data = {
            "branches": [{"id": "branch1", "name": "branch1"}],
            "session_default_branch": {"id": "default", "name": "default"},
            "metadata": {
                "id": "session_id",
                "name": "test_flow",
                "created_at": "2025-08-20",
            },
            "graph": {"internal_nodes": {"nodes": []}, "internal_edges": {"edges": []}},
        }

        with (
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
            patch(
                "khive.services.orchestration.orchestrator.Session"
            ) as mock_session_cls,
            patch(
                "khive.services.orchestration.orchestrator.Builder"
            ) as mock_builder_cls,
            patch("khive.services.orchestration.orchestrator.Graph") as mock_graph_cls,
            patch("khive.services.orchestration.orchestrator.Pile") as mock_pile_cls,
        ):
            # Mock all the from_dict methods
            mock_branch = MagicMock()
            mock_branch_cls.from_dict = MagicMock(return_value=mock_branch)

            mock_session = MagicMock()
            mock_session.name = "test_flow"
            mock_session_cls.return_value = mock_session

            mock_builder = MagicMock()
            mock_builder_cls.return_value = mock_builder

            mock_graph = MagicMock()
            mock_graph_cls.return_value = mock_graph

            mock_pile = MagicMock()
            mock_pile_cls.from_dict = MagicMock(return_value=mock_pile)

            # Mock aiofiles to return test data
            mock_aiofiles.open.return_value.__aenter__.return_value.read.return_value = json.dumps(
                session_data
            )

            orchestrator = await LionOrchestrator.load_json(test_file)

            assert isinstance(orchestrator, LionOrchestrator)
            assert orchestrator.flow_name == "test_flow"
            assert orchestrator.session is mock_session
            assert orchestrator.builder is mock_builder

    @pytest.mark.asyncio
    async def test_load_json_file_not_found(self, tmp_path):
        """Test loading from non-existent file."""
        non_existent_file = tmp_path / "non_existent.json"

        with pytest.raises(FileNotFoundError):
            await LionOrchestrator.load_json(non_existent_file)


class TestErrorRecovery:
    """Test error recovery and resilience."""

    @pytest.mark.asyncio
    async def test_fanout_planning_failure(self, orchestrator_with_mocks):
        """Test fanout handles planning stage failure."""
        orchestrator = orchestrator_with_mocks

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc
            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch_id"
            mock_branch_cls.return_value = mock_branch

            orchestrator.builder.add_operation.return_value = "root_id"
            orchestrator.session.flow.side_effect = Exception("Planning failed")

            with pytest.raises(Exception, match="Planning failed"):
                await orchestrator.fanout(
                    initial_desc="Test",
                    planning_instruction="Plan",
                    synth_instruction="Synthesize",
                )

    @pytest.mark.asyncio
    async def test_fanout_expansion_failure(self, orchestrator_with_mocks):
        """Test fanout handles expansion stage failure."""
        orchestrator = orchestrator_with_mocks

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc
            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch_id"
            mock_branch_cls.return_value = mock_branch

            orchestrator.builder.add_operation.return_value = "root_id"

            # Planning succeeds
            orchestrator.session.flow.return_value = {
                "operation_results": {
                    "root_id": MagicMock(flow_plans=MagicMock(initial=MagicMock()))
                }
            }

            # But expansion fails
            orchestrator.expand_with_plan = AsyncMock(
                side_effect=Exception("Expansion failed")
            )

            with pytest.raises(Exception, match="Expansion failed"):
                await orchestrator.fanout(
                    initial_desc="Test",
                    planning_instruction="Plan",
                    synth_instruction="Synthesize",
                )

    @pytest.mark.asyncio
    async def test_gated_refinement_qa_branch_failure(self, orchestrator_with_mocks):
        """Test gated refinement handles QA branch creation failure."""
        orchestrator = orchestrator_with_mocks

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc
            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch_id"
            mock_branch_cls.return_value = mock_branch

            orchestrator.builder.add_operation.side_effect = ["root", "agent1"]
            orchestrator.session.flow.return_value = {
                "operation_results": {
                    "root": MagicMock(
                        flow_plans=MagicMock(
                            initial=MagicMock(),
                            refinement=MagicMock(),
                        )
                    ),
                }
            }
            orchestrator.expand_with_plan = AsyncMock(return_value=["agent1"])

            # QA branch creation fails
            orchestrator.create_cc_branch = AsyncMock(
                side_effect=Exception("QA branch failed")
            )

            with pytest.raises(Exception, match="QA branch failed"):
                await orchestrator.fanout_w_gated_refinement(
                    initial_desc="Test",
                    refinement_desc="Refine",
                    gate_instruction="Evaluate",
                    synth_instruction="Synthesize",
                    planning_instruction="Plan",
                )

    @pytest.mark.asyncio
    async def test_concurrent_operation_timeout(self, orchestrator_with_mocks):
        """Test handling of concurrent operation timeout."""
        orchestrator = orchestrator_with_mocks

        # Mock session flow to timeout
        orchestrator.session.flow = AsyncMock(
            side_effect=asyncio.TimeoutError("Flow timeout")
        )

        with pytest.raises(asyncio.TimeoutError):
            await orchestrator.run_flow()

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_failure(self, orchestrator_with_mocks):
        """Test that resources are properly cleaned up on failure."""
        orchestrator = orchestrator_with_mocks

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc
            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch_id"
            mock_branch_cls.return_value = mock_branch

            orchestrator.builder.add_operation.return_value = "root_id"

            # Simulate failure during flow execution
            orchestrator.session.flow.side_effect = Exception("Flow execution failed")

            try:
                await orchestrator.fanout(
                    initial_desc="Test",
                    planning_instruction="Plan",
                    synth_instruction="Synthesize",
                )
            except Exception:
                pass  # Expected failure

            # Verify branch was still added to session (proper state)
            orchestrator.session.branches.include.assert_called_once_with(mock_branch)
