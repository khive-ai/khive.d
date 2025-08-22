"""Comprehensive fixtures for LionOrchestrator testing."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from lionagi import Branch, Builder, Operation, Session
from lionagi.fields import Instruct
from lionagi.protocols.types import AssistantResponse, Graph

from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.orchestration.parts import (
    AgentRequest,
    MultiPhaseOrchestrationResponse,
    GatedMultiPhaseOrchestrationResponse,
    OrchestrationPlan,
)
from khive.services.composition.parts import ComposerRequest


@pytest.fixture
def mock_lionagi_session():
    """Mock LionAGI Session for testing."""
    session = MagicMock(spec=Session)
    session.id = str(uuid4())
    session.name = "test_session"
    session.created_at = "2025-08-20T12:00:00Z"

    # Mock branches
    session.branches = MagicMock()
    session.branches.include = MagicMock()
    session._lookup_branch_by_name = MagicMock(return_value=None)

    # Mock default branch
    default_branch = MagicMock(spec=Branch)
    default_branch.id = str(uuid4())
    default_branch.name = "test_orchestrator"
    default_branch.messages = MagicMock()
    default_branch.messages.progression = []
    session.default_branch = default_branch

    # Mock flow method
    session.flow = AsyncMock(
        return_value={
            "operation_results": {},
            "graph_metadata": {},
        }
    )

    # Mock get_branch method
    session.get_branch = MagicMock(return_value=default_branch)

    return session


@pytest.fixture
def mock_lionagi_branch():
    """Mock LionAGI Branch for testing."""
    branch = MagicMock(spec=Branch)
    branch.id = str(uuid4())
    branch.name = "test_branch"
    branch.messages = MagicMock()
    branch.messages.progression = []
    branch.chat_model = MagicMock()
    branch.parse_model = MagicMock()
    branch.clone = MagicMock(return_value=branch)
    branch.to_dict = MagicMock(return_value={"id": str(branch.id), "name": branch.name})
    return branch


@pytest.fixture
def mock_lionagi_builder():
    """Mock LionAGI Builder for testing."""
    builder = MagicMock(spec=Builder)
    builder.name = "test_flow"
    builder.last_operation_id = None

    # Mock operations - return different UUIDs on each call
    def mock_add_operation(*args, **kwargs):
        return str(uuid4())

    builder.add_operation = MagicMock(side_effect=mock_add_operation)

    # Mock graph
    mock_graph = MagicMock(spec=Graph)
    mock_operation = MagicMock(spec=Operation)
    mock_operation.branch_id = str(uuid4())
    # Use a placeholder UUID for the mock graph
    placeholder_operation_id = str(uuid4())
    mock_graph.internal_nodes = {placeholder_operation_id: mock_operation}
    builder.get_graph = MagicMock(return_value=mock_graph)
    builder.visualize = MagicMock()

    return builder


@pytest.fixture
def mock_claude_code():
    """Mock Claude Code model for testing."""
    cc = MagicMock()
    cc.model = "claude-3-5-sonnet-20241022"
    cc.provider = "anthropic"
    return cc


@pytest.fixture
def mock_create_cc():
    """Mock the create_cc function."""
    with patch("khive.services.orchestration.orchestrator.create_cc") as mock:
        mock_cc = MagicMock()
        mock.return_value = mock_cc
        yield mock


@pytest.fixture
def mock_composer_service():
    """Mock composer service for testing."""
    with patch("khive.services.orchestration.orchestrator.composer_service") as mock:
        mock_response = MagicMock()
        mock_response.system_prompt = "Test system prompt"
        mock.handle_request = AsyncMock(return_value=mock_response)
        yield mock


@pytest.fixture
def sample_composer_request():
    """Sample ComposerRequest for testing."""
    return ComposerRequest(
        role="researcher",
        domains="software-architecture",
    )


@pytest.fixture
def sample_agent_request(sample_composer_request):
    """Sample AgentRequest for testing."""
    return AgentRequest(
        instruct=Instruct(
            instruction="Test instruction",
            context="Test context",
        ),
        compose_request=sample_composer_request,
        analysis_type="RequirementsAnalysis",
    )


@pytest.fixture
def sample_orchestration_plan(sample_agent_request):
    """Sample OrchestrationPlan for testing."""
    return OrchestrationPlan(
        common_background="Test background",
        agent_requests=[sample_agent_request],
        execution_strategy="concurrent",
    )


@pytest.fixture
def sample_fanout_response():
    """Sample MultiPhaseOrchestrationResponse for testing."""
    return MultiPhaseOrchestrationResponse(
        synth_result="Test synthesis result",
        initial_nodes=["node1", "node2"],
    )


@pytest.fixture
def sample_gated_response():
    """Sample GatedMultiPhaseOrchestrationResponse for testing."""
    return GatedMultiPhaseOrchestrationResponse(
        synth_result="Test synthesis result",
        initial_nodes=["node1", "node2"],
        gate_passed=True,
        refinement_executed=False,
    )


@pytest.fixture
def mock_assistant_response():
    """Mock AssistantResponse for testing."""
    response = MagicMock(spec=AssistantResponse)
    response.model_response = {
        "result": "Test result",
        "summary": "Test summary",
    }
    return response


@pytest.fixture
def mock_quality_gate():
    """Mock quality gate component."""
    gate = MagicMock()
    gate.threshold_met = True
    gate.feedback = "All requirements met"
    return gate


@pytest.fixture
def orchestrator_with_mocks(
    mock_lionagi_session,
    mock_lionagi_builder,
    mock_create_cc,
    mock_composer_service,
):
    """LionOrchestrator instance with all dependencies mocked."""
    orchestrator = LionOrchestrator("test_flow")
    orchestrator.session = mock_lionagi_session
    orchestrator.builder = mock_lionagi_builder
    return orchestrator


@pytest.fixture
def async_timeout():
    """Default timeout for async tests."""
    return 5.0


@pytest.fixture
def mock_file_system(tmp_path):
    """Mock file system operations."""
    with patch("khive.services.orchestration.orchestrator.KHIVE_CONFIG_DIR", tmp_path):
        # Create necessary directories
        (tmp_path / "claude_roles").mkdir(parents=True)
        (tmp_path / "workspaces").mkdir(parents=True)
        yield tmp_path


@pytest.fixture
def mock_aiofiles():
    """Mock aiofiles operations."""
    with patch("khive.services.orchestration.orchestrator.aiofiles") as mock:
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value='{"test": "data"}')
        mock_file.write = AsyncMock()
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        mock.open = MagicMock(return_value=mock_file)
        yield mock


@pytest.fixture
def mock_shutil():
    """Mock shutil operations for file copying."""
    with patch("shutil.copytree") as mock_copytree, patch("shutil.copy") as mock_copy:
        yield {"copytree": mock_copytree, "copy": mock_copy}


@pytest.fixture
def error_scenarios():
    """Common error scenarios for testing."""
    return {
        "timeout_error": asyncio.TimeoutError("Operation timed out"),
        "connection_error": ConnectionError("Failed to connect"),
        "value_error": ValueError("Invalid input"),
        "runtime_error": RuntimeError("Unexpected error"),
    }


@pytest.fixture
def performance_thresholds():
    """Performance thresholds for testing."""
    return {
        "initialize_max_time": 2.0,
        "create_branch_max_time": 1.0,
        "fanout_max_time": 10.0,
        "run_flow_max_time": 5.0,
    }
