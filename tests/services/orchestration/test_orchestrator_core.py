"""
Core unit tests for LionOrchestrator functionality.

This module consolidates comprehensive testing of LionOrchestrator initialization,
session management, branch creation patterns, and core orchestration operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from lionagi import Branch, Builder, Session
from lionagi.fields import Instruct
from lionagi.protocols.types import Graph
from lionagi.service.imodel import iModel

from khive.services.composition.parts import ComposerRequest
from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.orchestration.parts import (
    AgentRequest,
    FanoutResponse,
    OrchestrationPlan,
)


@pytest.fixture
def mock_cc_model():
    """Create a mock Claude Code model for testing."""
    model = MagicMock(spec=iModel)
    model.invoke = AsyncMock(return_value=MagicMock(content="Test response"))
    return model


@pytest.fixture
def mock_session():
    """Create a mock lionagi Session for testing."""
    session = MagicMock(spec=Session)
    session.default_branch = MagicMock(spec=Branch)
    session.default_branch.id = str(uuid4())
    session._lookup_branch_by_name = MagicMock(return_value=None)
    session.create_branch = AsyncMock(return_value=str(uuid4()))
    session.get_branch = MagicMock(return_value=session.default_branch)
    return session


@pytest.fixture
def mock_builder():
    """Create a mock lionagi Builder for testing."""
    builder = MagicMock(spec=Builder)
    builder.get_graph = MagicMock(return_value=MagicMock(spec=Graph))
    return builder


@pytest.fixture
async def initialized_orchestrator(mock_cc_model, mock_session, mock_builder):
    """Create an initialized orchestrator for testing."""
    orchestrator = LionOrchestrator("test_flow")

    with (
        patch("khive.services.orchestration.orchestrator.create_cc") as mock_create_cc,
        patch("khive.services.orchestration.orchestrator.Session") as mock_session_cls,
        patch("khive.services.orchestration.orchestrator.Branch") as mock_branch_cls,
        patch("khive.services.orchestration.orchestrator.Builder") as mock_builder_cls,
    ):
        mock_create_cc.return_value = mock_cc_model
        mock_session_cls.return_value = mock_session
        mock_builder_cls.return_value = mock_builder

        mock_branch = MagicMock(spec=Branch)
        mock_branch.id = str(uuid4())
        mock_branch_cls.return_value = mock_branch

        await orchestrator.initialize()

        # Set up the mocked objects
        orchestrator.session = mock_session
        orchestrator.builder = mock_builder

    return orchestrator


@pytest.mark.unit
class TestLionOrchestratorCore:
    """Core tests for LionOrchestrator functionality."""

    def test_orchestrator_initialization(self):
        """Test basic orchestrator initialization."""
        flow_name = "test_orchestration_flow"
        orchestrator = LionOrchestrator(flow_name)

        assert orchestrator.flow_name == flow_name
        assert orchestrator.session is None
        assert orchestrator.builder is None

    @pytest.mark.asyncio
    async def test_initialize_with_defaults(self, mock_cc_model):
        """Test initialization with default parameters."""
        orchestrator = LionOrchestrator("test_flow")

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Session"
            ) as mock_session_cls,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
            patch(
                "khive.services.orchestration.orchestrator.Builder"
            ) as mock_builder_cls,
        ):
            mock_create_cc.return_value = mock_cc_model

            mock_branch = MagicMock(spec=Branch)
            mock_branch.id = str(uuid4())
            mock_branch_cls.return_value = mock_branch

            mock_session = MagicMock(spec=Session)
            mock_session_cls.return_value = mock_session

            mock_builder = MagicMock(spec=Builder)
            mock_builder_cls.return_value = mock_builder

            await orchestrator.initialize()

            # Verify initialization calls
            mock_create_cc.assert_called_once()
            mock_session_cls.assert_called_once()
            mock_builder_cls.assert_called_once_with("test_flow")

    @pytest.mark.asyncio
    async def test_initialize_with_custom_parameters(self, mock_cc_model):
        """Test initialization with custom model and system prompt."""
        orchestrator = LionOrchestrator("custom_flow")
        custom_model = "claude-3-5-sonnet"
        custom_system = "Custom system prompt"

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Session"
            ) as mock_session_cls,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
            patch(
                "khive.services.orchestration.orchestrator.Builder"
            ) as mock_builder_cls,
        ):
            mock_create_cc.return_value = mock_cc_model

            mock_branch = MagicMock(spec=Branch)
            mock_branch_cls.return_value = mock_branch

            mock_session = MagicMock(spec=Session)
            mock_session_cls.return_value = mock_session

            mock_builder = MagicMock(spec=Builder)
            mock_builder_cls.return_value = mock_builder

            await orchestrator.initialize(model=custom_model, system=custom_system)

            # Verify custom parameters were passed
            mock_create_cc.assert_called_once_with(
                as_orchestrator=True,
                verbose_output=True,
                model=custom_model,
                auto_finish=True,
            )

            # Verify branch was created with custom system
            mock_branch_cls.assert_called_once()
            branch_call_args = mock_branch_cls.call_args[1]
            assert branch_call_args["system"] == custom_system

    def test_orc_branch_property(self, initialized_orchestrator):
        """Test orc_branch property access."""
        orchestrator = initialized_orchestrator

        # The property should return the default branch
        orc_branch = orchestrator.orc_branch
        assert orc_branch == orchestrator.session.default_branch

    @pytest.mark.asyncio
    async def test_create_cc_branch_basic(self, initialized_orchestrator):
        """Test basic CC branch creation."""
        orchestrator = initialized_orchestrator
        compose_request = ComposerRequest(
            role="researcher", domains="software-architecture"
        )

        with patch(
            "khive.services.orchestration.orchestrator.composer_service.compose"
        ) as mock_compose:
            mock_compose.return_value = AsyncMock()
            mock_orchestrator_cc_model = AsyncMock()

            with patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_model:
                mock_create_model.return_value = mock_orchestrator_cc_model

                branch_id = await orchestrator.create_cc_branch(compose_request)

                # Verify branch was created and returned
                assert branch_id is not None
                assert isinstance(branch_id, (str, UUID))

    @pytest.mark.asyncio
    async def test_create_cc_branch_duplicate_handling(self, initialized_orchestrator):
        """Test handling of duplicate branch names."""
        orchestrator = initialized_orchestrator
        compose_request = ComposerRequest(
            role="researcher", domains="software-architecture"
        )

        # Mock session to return existing branches for name collision
        existing_branch_mock = MagicMock()
        orchestrator.session._lookup_branch_by_name.side_effect = [
            existing_branch_mock,  # First call finds existing
            existing_branch_mock,  # Second call finds existing
            None,  # Third call finds available name
        ]

        with patch(
            "khive.services.orchestration.orchestrator.composer_service.compose"
        ) as mock_compose:
            mock_compose.return_value = AsyncMock()
            mock_orchestrator_cc_model = AsyncMock()

            with patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_model:
                mock_create_model.return_value = mock_orchestrator_cc_model

                branch_id = await orchestrator.create_cc_branch(compose_request)

                # Verify name collision handling worked
                assert orchestrator.session._lookup_branch_by_name.call_count == 3


@pytest.mark.unit
class TestOrchestrationWorkflowExecution:
    """Test orchestration workflow execution patterns."""

    @pytest.mark.asyncio
    async def test_fanout_execution(self, initialized_orchestrator):
        """Test fanout execution pattern."""
        orchestrator = initialized_orchestrator

        # Create mock orchestration plan
        agent_requests = [
            AgentRequest(
                instruct=Instruct(instruction="Research distributed systems"),
                compose_request=ComposerRequest(
                    role="researcher", domains="distributed-systems"
                ),
            ),
            AgentRequest(
                instruct=Instruct(instruction="Design system architecture"),
                compose_request=ComposerRequest(
                    role="architect", domains="software-architecture"
                ),
            ),
        ]

        plan = OrchestrationPlan(
            common_background="Test orchestration background",
            agent_requests=agent_requests,
            execution_strategy="concurrent",
        )

        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
        ):
            # Mock branch creation to return branch IDs
            mock_create_branch.side_effect = [str(uuid4()) for _ in agent_requests]

            # Mock operate to return successful operations
            mock_operate.return_value = AsyncMock()

            result = await orchestrator.fanout(plan)

            # Verify fanout execution
            assert isinstance(result, FanoutResponse)
            assert mock_create_branch.call_count == len(agent_requests)

    @pytest.mark.asyncio
    async def test_sequential_execution(self, initialized_orchestrator):
        """Test sequential execution pattern."""
        orchestrator = initialized_orchestrator

        agent_requests = [
            AgentRequest(
                instruct=Instruct(instruction="First sequential task"),
                compose_request=ComposerRequest(
                    role="researcher", domains="distributed-systems"
                ),
            ),
            AgentRequest(
                instruct=Instruct(instruction="Second sequential task"),
                compose_request=ComposerRequest(
                    role="implementer", domains="backend-development"
                ),
            ),
        ]

        plan = OrchestrationPlan(
            common_background="Sequential execution test",
            agent_requests=agent_requests,
            execution_strategy="sequential",
        )

        with (
            patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
            patch.object(orchestrator.orc_branch, "operate") as mock_operate,
        ):
            mock_create_branch.side_effect = [str(uuid4()) for _ in agent_requests]
            mock_operate.return_value = AsyncMock()

            result = await orchestrator.fanout(plan)

            assert isinstance(result, FanoutResponse)
            assert mock_create_branch.call_count == len(agent_requests)


@pytest.mark.unit
class TestOrchestrationErrorHandling:
    """Test error handling in orchestration operations."""

    @pytest.mark.asyncio
    async def test_branch_creation_failure(self, initialized_orchestrator):
        """Test handling of branch creation failures."""
        orchestrator = initialized_orchestrator
        compose_request = ComposerRequest(
            role="researcher", domains="software-architecture"
        )

        with (
            patch(
                "khive.services.orchestration.orchestrator.composer_service.compose"
            ) as mock_compose,
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_model,
        ):
            # Mock composer service to raise an exception
            mock_compose.side_effect = Exception("Composer service failed")

            with pytest.raises(Exception, match="Composer service failed"):
                await orchestrator.create_cc_branch(compose_request)

    @pytest.mark.asyncio
    async def test_operation_failure_handling(self, initialized_orchestrator):
        """Test handling of operation failures during execution."""
        orchestrator = initialized_orchestrator

        agent_requests = [
            AgentRequest(
                instruct=Instruct(instruction="Task that will fail"),
                compose_request=ComposerRequest(
                    role="researcher", domains="distributed-systems"
                ),
            ),
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
            # Mock operate to raise an exception
            mock_operate.side_effect = Exception("Operation failed")

            # Should handle the exception gracefully
            result = await orchestrator.fanout(plan)

            # Verify that the orchestrator handled the error appropriately
            assert isinstance(result, FanoutResponse)


@pytest.mark.unit
class TestOrchestrationResourceManagement:
    """Test resource management and cleanup in orchestration."""

    @pytest.mark.asyncio
    async def test_session_state_persistence(self, initialized_orchestrator):
        """Test session state is properly maintained."""
        orchestrator = initialized_orchestrator

        # Verify initial state
        assert orchestrator.session is not None
        assert orchestrator.builder is not None

        # Create some branches
        compose_request = ComposerRequest(
            role="researcher", domains="software-architecture"
        )

        with (
            patch(
                "khive.services.orchestration.orchestrator.composer_service.compose"
            ) as mock_compose,
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_model,
        ):
            mock_compose.return_value = AsyncMock()
            mock_create_model.return_value = AsyncMock()

            branch_id = await orchestrator.create_cc_branch(compose_request)

            # Verify session state is maintained
            assert orchestrator.session is not None
            assert branch_id is not None

    def test_memory_cleanup_on_completion(self, initialized_orchestrator):
        """Test that resources are cleaned up properly."""
        orchestrator = initialized_orchestrator

        # For this test, we mainly verify that the orchestrator
        # maintains proper references and doesn't create memory leaks
        initial_session = orchestrator.session
        initial_builder = orchestrator.builder

        # After operations, session and builder should still be valid
        assert orchestrator.session is initial_session
        assert orchestrator.builder is initial_builder
