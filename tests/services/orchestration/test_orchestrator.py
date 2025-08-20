"""Comprehensive unit tests for LionOrchestrator."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from lionagi.fields import Instruct

from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.orchestration.parts import (
    AgentRequest,
    ComposerRequest,
    OrchestrationPlan,
)


class TestLionOrchestratorInitialization:
    """Test orchestrator initialization and setup."""

    def test_init_basic(self):
        """Test basic initialization."""
        orchestrator = LionOrchestrator("test_flow")
        assert orchestrator.flow_name == "test_flow"
        assert orchestrator.session is None
        assert orchestrator.builder is None

    @pytest.mark.asyncio
    async def test_initialize_default_parameters(self, mock_create_cc):
        """Test initialize method with default parameters."""
        orchestrator = LionOrchestrator("test_flow")

        with (
            patch(
                "khive.services.orchestration.orchestrator.Session"
            ) as mock_session_cls,
            patch(
                "khive.services.orchestration.orchestrator.Builder"
            ) as mock_builder_cls,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_branch = MagicMock()
            mock_branch_cls.return_value = mock_branch

            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session

            mock_builder = MagicMock()
            mock_builder_cls.return_value = mock_builder

            await orchestrator.initialize()

            # Verify create_cc was called correctly
            mock_create_cc.assert_called_once_with(
                as_orchestrator=True,
                verbose_output=True,
                model=None,
                auto_finish=True,
            )

            # Verify branch creation
            mock_branch_cls.assert_called_once()
            call_kwargs = mock_branch_cls.call_args.kwargs
            assert call_kwargs["name"] == "test_flow_orchestrator"
            assert (
                "You are an orchestrator for the test_flow flow"
                in call_kwargs["system"]
            )
            assert call_kwargs["use_lion_system_message"] is True
            assert call_kwargs["system_datetime"] is True
            assert call_kwargs["chat_model"] is mock_create_cc.return_value
            assert call_kwargs["parse_model"] is mock_create_cc.return_value

            # Verify session creation
            mock_session_cls.assert_called_once_with(
                default_branch=mock_branch, name="test_flow"
            )

            # Verify builder creation
            mock_builder_cls.assert_called_once_with("test_flow")

            assert orchestrator.session is mock_session
            assert orchestrator.builder is mock_builder

    @pytest.mark.asyncio
    async def test_initialize_custom_parameters(self, mock_create_cc):
        """Test initialize method with custom parameters."""
        orchestrator = LionOrchestrator("test_flow")
        custom_model = "claude-3-opus-20240229"
        custom_system = "Custom system prompt"

        with (
            patch(
                "khive.services.orchestration.orchestrator.Session"
            ) as mock_session_cls,
            patch(
                "khive.services.orchestration.orchestrator.Builder"
            ) as mock_builder_cls,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            await orchestrator.initialize(model=custom_model, system=custom_system)

            mock_create_cc.assert_called_once_with(
                as_orchestrator=True,
                verbose_output=True,
                model=custom_model,
                auto_finish=True,
            )

            call_kwargs = mock_branch_cls.call_args.kwargs
            assert call_kwargs["system"] == custom_system

    def test_orc_branch_property(self, orchestrator_with_mocks):
        """Test orc_branch property."""
        assert (
            orchestrator_with_mocks.orc_branch
            == orchestrator_with_mocks.session.default_branch
        )


class TestBranchCreation:
    """Test branch creation functionality."""

    @pytest.mark.asyncio
    async def test_create_cc_branch_basic(
        self,
        orchestrator_with_mocks,
        sample_composer_request,
        mock_file_system,
        mock_shutil,
    ):
        """Test basic CC branch creation."""
        orchestrator = orchestrator_with_mocks

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc

            mock_response = MagicMock()
            mock_response.system_prompt = "Test system prompt"
            mock_composer.handle_request = AsyncMock(return_value=mock_response)

            # Setup file system
            role_dir = mock_file_system / "claude_roles" / "researcher" / ".claude"
            role_dir.mkdir(parents=True)
            (role_dir / "settings.json").write_text('{"test": "config"}')
            (role_dir / "CLAUDE.md").write_text("# Test CLAUDE.md")

            source_dir = (
                Path(__file__).parent.parent
                / "src"
                / "khive"
                / "toolkits"
                / "cc"
                / "claude_roles"
                / "researcher"
                / ".claude"
            )

            branch_id = await orchestrator.create_cc_branch(sample_composer_request)

            # Verify branch was created and added
            assert isinstance(branch_id, str)
            orchestrator.session.branches.include.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_cc_branch_name_collision(
        self,
        orchestrator_with_mocks,
        sample_composer_request,
        mock_file_system,
        mock_shutil,
    ):
        """Test branch creation with name collision."""
        orchestrator = orchestrator_with_mocks

        # Mock lookup to return existing branch for first few attempts
        orchestrator.session._lookup_branch_by_name = MagicMock(
            side_effect=[MagicMock(), MagicMock(), None]  # Two collisions, then success
        )

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc

            mock_response = MagicMock()
            mock_response.system_prompt = "Test system prompt"
            mock_composer.handle_request = AsyncMock(return_value=mock_response)

            mock_branch = MagicMock()
            mock_branch.id = "test_id"
            mock_branch_cls.return_value = mock_branch

            branch_id = await orchestrator.create_cc_branch(sample_composer_request)

            # Should try original name, then _0, _1, then succeed with _2
            expected_calls = [
                "test_flow_researcher_software-architecture",
                "test_flow_researcher_software-architecture_0",
                "test_flow_researcher_software-architecture_1",
            ]
            actual_calls = [
                call[0][0]
                for call in orchestrator.session._lookup_branch_by_name.call_args_list
            ]
            assert actual_calls == expected_calls

    @pytest.mark.asyncio
    async def test_create_cc_branch_too_many_collisions(
        self,
        orchestrator_with_mocks,
        sample_composer_request,
        mock_file_system,
    ):
        """Test branch creation fails after too many collisions."""
        orchestrator = orchestrator_with_mocks

        # Always return existing branch
        orchestrator.session._lookup_branch_by_name = MagicMock(
            return_value=MagicMock()
        )

        with pytest.raises(ValueError, match="Too many branches with name"):
            await orchestrator.create_cc_branch(sample_composer_request)

    @pytest.mark.asyncio
    async def test_create_cc_branch_with_clone(
        self,
        orchestrator_with_mocks,
        sample_composer_request,
        mock_file_system,
    ):
        """Test branch creation with cloning."""
        orchestrator = orchestrator_with_mocks
        clone_from_id = "source_branch_id"

        # Setup source branch
        source_branch = MagicMock()
        source_branch.clone = MagicMock()
        cloned_branch = MagicMock()
        cloned_branch.id = "cloned_branch_id"
        source_branch.clone.return_value = cloned_branch
        orchestrator.session.get_branch = MagicMock(return_value=source_branch)

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc

            mock_response = MagicMock()
            mock_composer.handle_request = AsyncMock(return_value=mock_response)

            branch_id = await orchestrator.create_cc_branch(
                sample_composer_request, clone_from=clone_from_id
            )

            assert branch_id == "cloned_branch_id"
            source_branch.clone.assert_called_once_with(sender=orchestrator.session)
            assert cloned_branch.chat_model is mock_cc
            assert cloned_branch.parse_model is mock_cc

    @pytest.mark.asyncio
    async def test_create_cc_branch_root_roles(
        self,
        orchestrator_with_mocks,
        mock_file_system,
    ):
        """Test branch creation for root-requiring roles."""
        orchestrator = orchestrator_with_mocks

        root_roles = ["implementer", "tester", "architect", "reviewer"]

        for role in root_roles:
            request = ComposerRequest(role=role, domains="software-architecture")

            with (
                patch(
                    "khive.services.orchestration.orchestrator.create_cc"
                ) as mock_create_cc,
                patch(
                    "khive.services.orchestration.orchestrator.composer_service"
                ) as mock_composer,
            ):
                mock_cc = MagicMock()
                mock_create_cc.return_value = mock_cc

                mock_response = MagicMock()
                mock_composer.handle_request = AsyncMock(return_value=mock_response)

                await orchestrator.create_cc_branch(request)

                # Verify create_cc called with requires_root=True
                call_kwargs = mock_create_cc.call_args.kwargs
                assert call_kwargs["requires_root"] is True
                assert call_kwargs["copy_mcp_config_from"] is None
                assert call_kwargs["copy_settings_from"] is None
                assert call_kwargs["copy_claude_md_from"] is None
                assert call_kwargs["overwrite_config"] is False


class TestFieldGeneration:
    """Test field generation methods."""

    def test_generate_flow_plans_field(self):
        """Test flow plans field generation."""
        plans_description = {
            "initial": "Initial phase description",
            "refinement": "Refinement phase description",
        }

        field_model = LionOrchestrator.generate_flow_plans_field(**plans_description)

        assert field_model.name == "flow_plans"
        assert field_model.base_type.__name__ == "FlowOrchestrationPlans"

    def test_generate_quality_gate_field_basic(self):
        """Test basic quality gate field generation."""
        field_model = LionOrchestrator.generate_quality_gate_field(
            design="Test design validation",
            security=True,
        )

        assert field_model.name == "quality_gate"
        assert field_model.base_type.__name__ == "QualityGate"

    def test_generate_quality_gate_field_with_context(self):
        """Test quality gate field generation with context."""
        field_model = LionOrchestrator.generate_quality_gate_field(
            project_phase="development",
            is_critical_path=True,
            is_experimental=False,
            design="Custom design validation",
            security="Custom security validation",
        )

        assert field_model.name == "quality_gate"

    def test_generate_quality_gate_field_invalid_gate(self):
        """Test quality gate field generation with invalid gate."""
        with pytest.raises(ValueError, match="Unknown gate component"):
            LionOrchestrator.generate_quality_gate_field(
                invalid_gate=True,
            )


class TestPlanExpansion:
    """Test orchestration plan expansion."""

    @pytest.mark.asyncio
    async def test_expand_with_plan_concurrent(
        self,
        orchestrator_with_mocks,
        sample_orchestration_plan,
        mock_create_cc,
    ):
        """Test plan expansion with concurrent execution."""
        orchestrator = orchestrator_with_mocks
        root_id = "root_operation_id"

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc_patch,
            patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer,
        ):
            mock_cc = MagicMock()
            mock_create_cc_patch.return_value = mock_cc

            mock_response = MagicMock()
            mock_composer.handle_request = AsyncMock(return_value=mock_response)

            # Mock builder operations
            operation_ids = [
                str(uuid4())
                for _ in range(len(sample_orchestration_plan.agent_requests))
            ]
            orchestrator.builder.add_operation.side_effect = operation_ids

            nodes = await orchestrator.expand_with_plan(
                root=root_id,
                plan=sample_orchestration_plan,
                max_agents=8,
                auto_context=True,
                skip_root_context=True,
            )

            assert len(nodes) == len(sample_orchestration_plan.agent_requests)
            assert nodes == operation_ids

            # Verify all operations depend on root
            for call in orchestrator.builder.add_operation.call_args_list:
                assert call.kwargs["depends_on"] == [root_id]

    @pytest.mark.asyncio
    async def test_expand_with_plan_sequential(
        self,
        orchestrator_with_mocks,
        sample_orchestration_plan,
    ):
        """Test plan expansion with sequential execution."""
        orchestrator = orchestrator_with_mocks
        sample_orchestration_plan.execution_strategy = "sequential"
        root_id = "root_operation_id"

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc

            mock_response = MagicMock()
            mock_composer.handle_request = AsyncMock(return_value=mock_response)

            # Mock run_flow to avoid actual execution
            orchestrator.run_flow = AsyncMock()

            operation_ids = [
                str(uuid4())
                for _ in range(len(sample_orchestration_plan.agent_requests))
            ]
            orchestrator.builder.add_operation.side_effect = operation_ids

            nodes = await orchestrator.expand_with_plan(
                root=root_id,
                plan=sample_orchestration_plan,
                auto_context=True,
            )

            assert len(nodes) == len(sample_orchestration_plan.agent_requests)

            # Verify sequential dependencies
            calls = orchestrator.builder.add_operation.call_args_list
            assert calls[0].kwargs["depends_on"] == [root_id]  # First depends on root
            # Subsequent ones should depend on previous (would be tested in integration)

    @pytest.mark.asyncio
    async def test_expand_with_plan_max_agents_limit(
        self,
        orchestrator_with_mocks,
        sample_composer_request,
    ):
        """Test plan expansion respects max_agents limit."""
        orchestrator = orchestrator_with_mocks

        # Create plan with more agents than max_agents
        agent_requests = [
            AgentRequest(
                instruct=Instruct(instruction=f"Task {i}"),
                compose_request=sample_composer_request,
                analysis_type="RequirementsAnalysis",
            )
            for i in range(10)  # 10 agents
        ]

        plan = OrchestrationPlan(
            common_background="Test background",
            agent_requests=agent_requests,
        )

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc

            mock_response = MagicMock()
            mock_composer.handle_request = AsyncMock(return_value=mock_response)

            operation_ids = [str(uuid4()) for _ in range(5)]  # Only 5 will be processed
            orchestrator.builder.add_operation.side_effect = operation_ids

            nodes = await orchestrator.expand_with_plan(
                root="root_id",
                plan=plan,
                max_agents=5,  # Limit to 5 agents
            )

            assert len(nodes) == 5  # Should only process 5 agents


class TestContextOperations:
    """Test context extraction and management."""

    def test_opres_ctx_single_operation(
        self, orchestrator_with_mocks, mock_assistant_response
    ):
        """Test operation result context extraction for single operation."""
        orchestrator = orchestrator_with_mocks
        op_id = "test_operation_id"

        # Setup mock operation and branch
        mock_operation = MagicMock()
        mock_operation.branch_id = "test_branch_id"
        orchestrator.builder.get_graph.return_value.internal_nodes = {
            op_id: mock_operation
        }

        mock_branch = MagicMock()
        mock_branch.id = "test_branch_id"
        mock_branch.name = "test_branch"
        mock_branch.messages = MagicMock()
        mock_branch.messages.progression = [0]
        mock_branch.messages.__getitem__ = MagicMock(
            return_value=mock_assistant_response
        )
        orchestrator.session.get_branch = MagicMock(return_value=mock_branch)

        result = orchestrator.opres_ctx(op_id)

        expected = [
            {
                "branch_id": "test_branch_id",
                "branch_name": "test_branch",
                "result": "Test result",
                "summary": "Test summary",
            }
        ]

        assert result == expected

    def test_opres_ctx_multiple_operations(
        self, orchestrator_with_mocks, mock_assistant_response
    ):
        """Test operation result context extraction for multiple operations."""
        orchestrator = orchestrator_with_mocks
        op_ids = ["op1", "op2"]

        # Setup mock operations
        for i, op_id in enumerate(op_ids):
            mock_operation = MagicMock()
            mock_operation.branch_id = f"branch_{i}"
            orchestrator.builder.get_graph.return_value.internal_nodes = {
                **orchestrator.builder.get_graph.return_value.internal_nodes,
                op_id: mock_operation,
            }

        def mock_get_branch(branch_id, default=None):
            mock_branch = MagicMock()
            mock_branch.id = branch_id
            mock_branch.name = f"branch_{branch_id.split('_')[1]}"
            mock_branch.messages = MagicMock()
            mock_branch.messages.progression = [0]
            mock_branch.messages.__getitem__ = MagicMock(
                return_value=mock_assistant_response
            )
            return mock_branch

        orchestrator.session.get_branch = mock_get_branch

        result = orchestrator.opres_ctx(op_ids)

        assert len(result) == 2
        assert all("branch_id" in ctx for ctx in result)

    def test_opres_ctx_no_branch(self, orchestrator_with_mocks):
        """Test context extraction when operation has no branch."""
        orchestrator = orchestrator_with_mocks
        op_id = "test_operation_id"

        mock_operation = MagicMock()
        mock_operation.branch_id = None
        orchestrator.builder.get_graph.return_value.internal_nodes = {
            op_id: mock_operation
        }

        result = orchestrator.opres_ctx(op_id)

        assert result == [{"error": f"Operation {op_id} has no branch_id"}]

    def test_opres_ctx_exception_handling(self, orchestrator_with_mocks):
        """Test context extraction handles exceptions gracefully."""
        orchestrator = orchestrator_with_mocks
        op_id = "test_operation_id"

        # Make get_graph raise an exception
        orchestrator.builder.get_graph.side_effect = Exception("Test error")

        result = orchestrator.opres_ctx(op_id)

        assert result == [{"error": "Failed to extract summary: Test error"}]


class TestFlowExecution:
    """Test flow execution functionality."""

    @pytest.mark.asyncio
    async def test_run_flow_basic(self, orchestrator_with_mocks):
        """Test basic flow execution."""
        orchestrator = orchestrator_with_mocks
        expected_result = {"test": "result"}
        orchestrator.session.flow = AsyncMock(return_value=expected_result)

        result = await orchestrator.run_flow()

        assert result == expected_result
        orchestrator.session.flow.assert_called_once_with(
            orchestrator.builder.get_graph.return_value
        )

    @pytest.mark.asyncio
    async def test_run_flow_with_visualization(self, orchestrator_with_mocks):
        """Test flow execution with visualization."""
        orchestrator = orchestrator_with_mocks
        expected_result = {"test": "result"}
        orchestrator.session.flow = AsyncMock(return_value=expected_result)

        result = await orchestrator.run_flow(visualize=True)

        assert result == expected_result
        orchestrator.builder.visualize.assert_called_once_with("test_flow")

    @pytest.mark.asyncio
    async def test_run_flow_timeout(self, orchestrator_with_mocks):
        """Test flow execution with timeout."""
        orchestrator = orchestrator_with_mocks
        orchestrator.session.flow = AsyncMock(
            side_effect=asyncio.TimeoutError("Flow timed out")
        )

        with pytest.raises(asyncio.TimeoutError):
            await orchestrator.run_flow()

    def test_new_orc_branch(self, orchestrator_with_mocks):
        """Test new orchestrator branch creation."""
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
            mock_branch_cls.return_value = mock_branch

            result = orchestrator.new_orc_branch()

            assert result is mock_branch
            mock_create_cc.assert_called_once_with(permission_mode="bypassPermissions")
            mock_branch_cls.assert_called_once()
            orchestrator.session.branches.include.assert_called_once_with(mock_branch)


class TestAsyncErrorHandling:
    """Test async error handling scenarios."""

    @pytest.mark.asyncio
    async def test_initialize_create_cc_failure(self):
        """Test initialization handles create_cc failure."""
        orchestrator = LionOrchestrator("test_flow")

        with patch(
            "khive.services.orchestration.orchestrator.create_cc"
        ) as mock_create_cc:
            mock_create_cc.side_effect = Exception("Failed to create CC")

            with pytest.raises(Exception, match="Failed to create CC"):
                await orchestrator.initialize()

    @pytest.mark.asyncio
    async def test_create_cc_branch_composer_failure(
        self,
        orchestrator_with_mocks,
        sample_composer_request,
        mock_file_system,
    ):
        """Test branch creation handles composer service failure."""
        orchestrator = orchestrator_with_mocks

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc

            mock_composer.handle_request = AsyncMock(
                side_effect=Exception("Composer failed")
            )

            with pytest.raises(Exception, match="Composer failed"):
                await orchestrator.create_cc_branch(sample_composer_request)

    @pytest.mark.asyncio
    async def test_expand_with_plan_create_branch_failure(
        self,
        orchestrator_with_mocks,
        sample_orchestration_plan,
    ):
        """Test plan expansion handles branch creation failure."""
        orchestrator = orchestrator_with_mocks
        orchestrator.create_cc_branch = AsyncMock(
            side_effect=Exception("Branch creation failed")
        )

        with pytest.raises(Exception, match="Branch creation failed"):
            await orchestrator.expand_with_plan(
                root="root_id",
                plan=sample_orchestration_plan,
            )


class TestPerformanceAndLimits:
    """Test performance characteristics and limits."""

    @pytest.mark.asyncio
    async def test_initialize_performance(self, performance_thresholds):
        """Test initialization performance."""
        import time

        orchestrator = LionOrchestrator("test_flow")

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Session"
            ) as mock_session_cls,
            patch(
                "khive.services.orchestration.orchestrator.Builder"
            ) as mock_builder_cls,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_create_cc.return_value = MagicMock()
            mock_branch_cls.return_value = MagicMock()
            mock_session_cls.return_value = MagicMock()
            mock_builder_cls.return_value = MagicMock()

            start_time = time.time()
            await orchestrator.initialize()
            end_time = time.time()

            execution_time = end_time - start_time
            assert execution_time < performance_thresholds["initialize_max_time"]

    @pytest.mark.asyncio
    async def test_create_cc_branch_performance(
        self,
        orchestrator_with_mocks,
        sample_composer_request,
        mock_file_system,
        performance_thresholds,
    ):
        """Test branch creation performance."""
        import time

        orchestrator = orchestrator_with_mocks

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc

            mock_response = MagicMock()
            mock_composer.handle_request = AsyncMock(return_value=mock_response)

            start_time = time.time()
            await orchestrator.create_cc_branch(sample_composer_request)
            end_time = time.time()

            execution_time = end_time - start_time
            assert execution_time < performance_thresholds["create_branch_max_time"]

    def test_memory_usage_large_plans(
        self, orchestrator_with_mocks, sample_composer_request
    ):
        """Test memory usage with large orchestration plans."""
        import sys

        orchestrator = orchestrator_with_mocks

        # Create large plan
        large_plan = OrchestrationPlan(
            common_background="Large test background",
            agent_requests=[
                AgentRequest(
                    instruct=Instruct(instruction=f"Task {i}"),
                    compose_request=sample_composer_request,
                    analysis_type="RequirementsAnalysis",
                )
                for i in range(100)  # 100 agents
            ],
        )

        # Measure memory usage (basic check)
        initial_size = sys.getsizeof(orchestrator)
        plan_size = sys.getsizeof(large_plan)

        # Should be reasonable memory usage
        assert plan_size < 10 * 1024 * 1024  # Less than 10MB
