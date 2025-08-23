"""Integration tests for LionOrchestrator workflow patterns."""

import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from lionagi.service.imodel import iModel


class TestFanoutPattern:
    """Test fanout orchestration pattern."""

    def test_orchestrator_configuration(self, orchestrator_with_mocks):
        """Test orchestrator basic configuration and setup."""
        orchestrator = orchestrator_with_mocks

        # Test basic properties
        assert orchestrator.builder is not None
        assert orchestrator.session is not None
        assert hasattr(orchestrator, "flow_name")

        # Test builder has expected methods
        assert hasattr(orchestrator.builder, "add_operation")
        assert hasattr(orchestrator.builder, "get_graph")

        # Test session has expected methods
        assert hasattr(orchestrator.session, "default_branch")

    def test_add_operations_to_builder(self, orchestrator_with_mocks):
        """Test that operations can be added to the builder."""
        orchestrator = orchestrator_with_mocks

        # Test adding operations returns valid IDs
        op_id_1 = orchestrator.builder.add_operation("operate", instruction="Test 1")
        op_id_2 = orchestrator.builder.add_operation("operate", instruction="Test 2")

        assert op_id_1 is not None
        assert op_id_2 is not None
        assert op_id_1 != op_id_2  # Should be different UUIDs

    def test_orchestrator_helper_methods(self, orchestrator_with_mocks):
        """Test orchestrator helper methods work correctly."""
        orchestrator = orchestrator_with_mocks

        # Test opres_ctx method
        nodes = ["node1", "node2"]
        context = orchestrator.opres_ctx(nodes)
        assert isinstance(context, list)

        # Test flow plans field generation
        flow_field = orchestrator.generate_flow_plans_field(initial="test description")
        assert flow_field is not None

    def test_orchestrator_branch_creation(self, orchestrator_with_mocks):
        """Test orchestrator branch creation methods."""
        orchestrator = orchestrator_with_mocks

        # Test new orchestrator branch creation
        branch = orchestrator.new_orc_branch()
        assert branch is not None

    def test_builder_graph_access(self, orchestrator_with_mocks):
        """Test builder graph access and operations."""
        orchestrator = orchestrator_with_mocks

        # Test getting graph from builder
        graph = orchestrator.builder.get_graph()
        assert graph is not None

        # Test builder visualization method exists
        assert hasattr(orchestrator.builder, "visualize")

    def test_orchestrator_dependency_handling(self, orchestrator_with_mocks):
        """Test orchestrator dependency handling with builder operations."""
        orchestrator = orchestrator_with_mocks

        # Test setting and getting last operation ID
        orchestrator.builder.last_operation_id = "test_op_id"
        assert orchestrator.builder.last_operation_id == "test_op_id"

        # Test that operations can be added with dependencies
        op_id_1 = orchestrator.builder.add_operation(
            "operate", instruction="First operation"
        )
        orchestrator.builder.last_operation_id = op_id_1

        op_id_2 = orchestrator.builder.add_operation(
            "operate", instruction="Second operation"
        )

        # Verify both operations have different IDs
        assert op_id_1 != op_id_2
        assert op_id_1 is not None
        assert op_id_2 is not None


class TestFanoutWithGatedRefinement:
    """Test fanout with gated refinement pattern."""

    def test_gated_refinement_field_generation(self, orchestrator_with_mocks):
        """Test gated refinement field generation methods."""
        orchestrator = orchestrator_with_mocks

        # Test generating flow plans field with refinement
        flow_field = orchestrator.generate_flow_plans_field(
            initial="Initial description",
            refinement="Refinement description",
            context_aware="Context aware description",
        )
        assert flow_field is not None

    def test_gated_refinement_branch_creation(self, orchestrator_with_mocks):
        """Test branch creation for gated refinement."""
        orchestrator = orchestrator_with_mocks

        # Test creating branches for different roles
        branch1 = orchestrator.new_orc_branch()
        branch2 = orchestrator.new_orc_branch()

        assert branch1 is not None
        assert branch2 is not None
        # Branches should be different objects
        assert branch1 != branch2

    def test_gated_refinement_operations_setup(self, orchestrator_with_mocks):
        """Test setting up operations for gated refinement workflow."""
        orchestrator = orchestrator_with_mocks

        # Test adding multiple operations for gated workflow
        planning_op = orchestrator.builder.add_operation(
            "operate", instruction="Plan work"
        )
        initial_op = orchestrator.builder.add_operation(
            "operate", instruction="Initial work"
        )
        gate_op = orchestrator.builder.add_operation(
            "operate", instruction="Quality gate"
        )
        refinement_op = orchestrator.builder.add_operation(
            "operate", instruction="Refinement work"
        )

        # All operations should have unique IDs
        ops = [planning_op, initial_op, gate_op, refinement_op]
        assert len(set(ops)) == 4  # All unique
        assert all(op is not None for op in ops)

    def test_gated_refinement_context_operations(self, orchestrator_with_mocks):
        """Test context operations for gated refinement."""
        orchestrator = orchestrator_with_mocks

        # Test opres_ctx with multiple nodes (as in gated refinement)
        nodes = ["gate1", "gate2", "refinement1"]
        context = orchestrator.opres_ctx(nodes)
        assert isinstance(context, list)

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


class TestSessionManagement:
    """Test session management functionality."""

    async def test_session_management_placeholder(self, orchestrator_with_mocks):
        """Placeholder test for session management."""
        orchestrator = orchestrator_with_mocks
        assert orchestrator.session is not None


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
            mock_cc = MagicMock(spec=iModel)
            mock_cc.endpoint = MagicMock()
            mock_cc.endpoint.endpoint = "anthropic/claude-3-5-sonnet-20241022"
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
            mock_cc = MagicMock(spec=iModel)
            mock_cc.endpoint = MagicMock()
            mock_cc.endpoint.endpoint = "anthropic/claude-3-5-sonnet-20241022"
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
            mock_cc = MagicMock(spec=iModel)
            mock_cc.endpoint = MagicMock()
            mock_cc.endpoint.endpoint = "anthropic/claude-3-5-sonnet-20241022"
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
            mock_cc = MagicMock(spec=iModel)
            mock_cc.endpoint = MagicMock()
            mock_cc.endpoint.endpoint = "anthropic/claude-3-5-sonnet-20241022"
            mock_create_cc.return_value = mock_cc
            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch_id"
            mock_branch_cls.return_value = mock_branch

            orchestrator.builder.add_operation.return_value = "root_id"

            # Simulate failure during flow execution
            orchestrator.session.flow.side_effect = Exception("Flow execution failed")

            with contextlib.suppress(Exception):
                await orchestrator.fanout(
                    initial_desc="Test",
                    planning_instruction="Plan",
                    synth_instruction="Synthesize",
                )

            # Verify branch was still added to session (proper state)
            orchestrator.session.branches.include.assert_called_once_with(mock_branch)
