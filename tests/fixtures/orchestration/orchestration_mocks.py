"""Comprehensive mock infrastructure for orchestration testing."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from lionagi import Branch, Builder, Operation, Session
from lionagi.fields import Instruct
from lionagi.protocols.types import AssistantResponse, Graph
from lionagi.service.imodel import iModel

from khive.services.composition.parts import ComposerRequest, ComposerResponse
from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.orchestration.parts import AgentRequest, OrchestrationPlan


class MockLionAGIComponents:
    """Comprehensive mocks for LionAGI components."""

    @staticmethod
    def create_mock_session(name: str = "test_session") -> MagicMock:
        """Create mock LionAGI Session."""
        session = MagicMock(spec=Session)
        session.id = str(uuid4())
        session.name = name
        session.created_at = "2025-08-22T12:00:00Z"

        # Mock branches collection
        session.branches = MagicMock()
        session.branches.include = MagicMock()
        session.branches.to_dict = MagicMock(return_value=[])
        session._lookup_branch_by_name = MagicMock(return_value=None)

        # Mock default branch
        default_branch = MockLionAGIComponents.create_mock_branch(
            f"{name}_orchestrator"
        )
        session.default_branch = default_branch

        # Mock flow method
        session.flow = AsyncMock(
            return_value={
                "operation_results": {},
                "graph_metadata": {},
            }
        )

        # Mock get_branch method
        session.get_branch = MagicMock()

        return session

    @staticmethod
    def create_mock_branch(name: str = "test_branch") -> MagicMock:
        """Create mock LionAGI Branch."""
        branch = MagicMock(spec=Branch)
        branch.id = str(uuid4())
        branch.name = name

        # Mock messages
        branch.messages = MagicMock()
        branch.messages.progression = []
        branch.messages.__getitem__ = MagicMock()
        branch.messages.__len__ = MagicMock(return_value=0)

        # Mock clone method
        branch.clone = MagicMock(
            return_value=MockLionAGIComponents.create_mock_branch(f"{name}_clone")
        )

        return branch

    @staticmethod
    def create_mock_builder(name: str = "test_builder") -> MagicMock:
        """Create mock LionAGI Builder."""
        builder = MagicMock(spec=Builder)
        builder.name = name

        # Mock operations
        builder.add_operation = MagicMock(side_effect=lambda **kwargs: str(uuid4()))
        builder.get_graph = MagicMock(
            return_value=MockLionAGIComponents.create_mock_graph()
        )
        builder.visualize = MagicMock()
        builder.last_operation_id = None

        return builder

    @staticmethod
    def create_mock_graph() -> MagicMock:
        """Create mock LionAGI Graph."""
        graph = MagicMock(spec=Graph)
        graph.internal_nodes = {}
        graph.internal_edges = {}
        graph.to_dict = MagicMock(return_value={"nodes": [], "edges": []})
        return graph

    @staticmethod
    def create_mock_operation(branch_id: str | None = None) -> MagicMock:
        """Create mock LionAGI Operation."""
        operation = MagicMock(spec=Operation)
        operation.id = str(uuid4())
        operation.branch_id = branch_id or str(uuid4())
        operation.status = "completed"
        return operation

    @staticmethod
    def create_mock_assistant_response(result: dict[str, Any] = None) -> MagicMock:
        """Create mock AssistantResponse."""
        response = MagicMock(spec=AssistantResponse)
        response.model_response = result or {
            "result": "Mock result",
            "summary": "Mock summary",
        }
        return response

    @staticmethod
    def create_mock_imodel() -> MagicMock:
        """Create mock iModel."""
        model = MagicMock(spec=iModel)
        model.model_name = "mock-model"
        model.temperature = 0.3
        return model


class MockExternalServices:
    """Mocks for external services and dependencies."""

    @staticmethod
    def create_mock_claude_code_model() -> MagicMock:
        """Create mock Claude Code model."""
        mock_cc = MagicMock()
        mock_cc.model_name = "claude-3-5-sonnet-20241022"
        mock_cc.temperature = 0.3
        mock_cc.max_tokens = 4000
        return mock_cc

    @staticmethod
    def create_mock_composer_service() -> MagicMock:
        """Create mock composer service."""
        mock_service = MagicMock()
        mock_service.handle_request = AsyncMock()
        mock_service.handle_request.return_value = ComposerResponse(
            system_prompt="Mock system prompt for test role",
            capabilities=["analysis", "research"],
            domain_expertise=["software-architecture"],
        )
        return mock_service

    @staticmethod
    def create_mock_openai_client() -> MagicMock:
        """Create mock OpenAI client."""
        mock_client = MagicMock()

        # Mock chat completions
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.parsed = MagicMock()
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

        mock_client.beta.chat.completions.parse.return_value = mock_response

        return mock_client


class MockOrchestrationScenarios:
    """Pre-configured scenarios for common orchestration patterns."""

    @staticmethod
    def create_fanout_scenario() -> dict[str, Any]:
        """Create mock scenario for fanout pattern."""
        return {
            "plan": OrchestrationPlan(
                execution_strategy="concurrent",
                agent_requests=[
                    AgentRequest(
                        compose_request=ComposerRequest(
                            role="researcher", domains="software-architecture"
                        ),
                        instruct=Instruct(instruction="Research the topic"),
                        analysis_type="RequirementsAnalysis",
                    ),
                    AgentRequest(
                        compose_request=ComposerRequest(
                            role="analyst", domains="distributed-systems"
                        ),
                        instruct=Instruct(instruction="Analyze requirements"),
                        analysis_type="CodeContextAnalysis",
                    ),
                ],
                common_background="Test background context",
            ),
            "expected_agents": 2,
            "expected_strategy": "concurrent",
        }

    @staticmethod
    def create_sequential_scenario() -> dict[str, Any]:
        """Create mock scenario for sequential pattern."""
        return {
            "plan": OrchestrationPlan(
                execution_strategy="sequential",
                agent_requests=[
                    AgentRequest(
                        compose_request=ComposerRequest(
                            role="architect", domains="software-architecture"
                        ),
                        instruct=Instruct(instruction="Design architecture"),
                        analysis_type="IntegrationStrategy",
                    ),
                    AgentRequest(
                        compose_request=ComposerRequest(
                            role="implementer", domains="software-architecture"
                        ),
                        instruct=Instruct(instruction="Implement design"),
                        analysis_type="FeatureImplementation",
                    ),
                ],
                common_background="Sequential implementation context",
            ),
            "expected_agents": 2,
            "expected_strategy": "sequential",
        }

    @staticmethod
    def create_gated_refinement_scenario() -> dict[str, Any]:
        """Create mock scenario for gated refinement pattern."""
        return {
            "initial_plan": OrchestrationPlan(
                execution_strategy="concurrent",
                agent_requests=[
                    AgentRequest(
                        compose_request=ComposerRequest(
                            role="researcher", domains="software-architecture"
                        ),
                        instruct=Instruct(instruction="Initial research"),
                        analysis_type="RequirementsAnalysis",
                    ),
                ],
                common_background="Initial phase context",
            ),
            "refinement_plan": OrchestrationPlan(
                execution_strategy="concurrent",
                agent_requests=[
                    AgentRequest(
                        compose_request=ComposerRequest(
                            role="critic", domains="software-architecture"
                        ),
                        instruct=Instruct(instruction="Critique and refine"),
                        analysis_type="RequirementValidation",
                    ),
                ],
                common_background="Refinement phase context",
            ),
            "quality_gate_passed": True,
        }


@pytest.fixture
def mock_lionagi_components():
    """Pytest fixture for LionAGI component mocks."""
    return MockLionAGIComponents()


@pytest.fixture
def mock_external_services():
    """Pytest fixture for external service mocks."""
    return MockExternalServices()


@pytest.fixture
def mock_orchestration_scenarios():
    """Pytest fixture for orchestration scenario mocks."""
    return MockOrchestrationScenarios()


@pytest.fixture
def mock_initialized_orchestrator(mock_lionagi_components):
    """Pytest fixture for fully initialized orchestrator."""
    orchestrator = LionOrchestrator("test_flow")
    orchestrator.session = mock_lionagi_components.create_mock_session()
    orchestrator.builder = mock_lionagi_components.create_mock_builder()
    return orchestrator


class AsyncMockContext:
    """Helper class for managing async mocks in tests."""

    def __init__(self):
        self.patches = []
        self.mocks = {}

    def add_mock(self, target: str, mock_value: Any) -> Any:
        """Add a mock and track it for cleanup."""
        patcher = patch(target, mock_value)
        mock = patcher.start()
        self.patches.append(patcher)
        self.mocks[target] = mock
        return mock

    def get_mock(self, target: str) -> Any:
        """Get a previously registered mock."""
        return self.mocks.get(target)

    def cleanup(self):
        """Clean up all patches."""
        for patcher in self.patches:
            patcher.stop()
        self.patches.clear()
        self.mocks.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


@pytest.fixture
def async_mock_context():
    """Pytest fixture for async mock context manager."""
    return AsyncMockContext()


class MockTimeoutManager:
    """Mock timeout manager for testing timeout scenarios."""

    def __init__(self, config):
        self.config = config
        self.session_id = "test_session"
        self.active_tasks = {}
        self.timeout_count = 0

    async def execute_with_timeout(
        self, agent_id: str, timeout_type, task_func, *args, **kwargs
    ):
        """Mock timeout execution."""
        # Simulate timeout after certain number of calls
        if self.timeout_count >= 3:
            raise asyncio.TimeoutError("Mock timeout")

        self.timeout_count += 1

        # Mock successful execution
        result = MagicMock()
        result.status = "completed"
        result.duration = 1.5
        result.retry_count = 0
        result.error = None
        result.end_time = MagicMock()
        result.end_time.isoformat.return_value = "2025-08-22T12:01:30Z"

        return result

    async def get_performance_metrics(self):
        """Mock performance metrics."""
        return {
            "total_operations": 5,
            "successful_operations": 4,
            "timeout_rate": 0.2,
            "performance_improvement": 0.15,
        }

    async def cleanup(self):
        """Mock cleanup."""
        self.active_tasks.clear()


@pytest.fixture
def mock_timeout_manager():
    """Pytest fixture for mock timeout manager."""

    def _create_timeout_manager(config):
        return MockTimeoutManager(config)

    return _create_timeout_manager


class MockFileSystemOperations:
    """Mock file system operations for testing."""

    def __init__(self):
        self.files = {}
        self.directories = set()

    def create_file(self, path: str, content: str):
        """Mock file creation."""
        self.files[path] = content

    def create_directory(self, path: str):
        """Mock directory creation."""
        self.directories.add(path)

    def file_exists(self, path: str) -> bool:
        """Mock file existence check."""
        return path in self.files

    def directory_exists(self, path: str) -> bool:
        """Mock directory existence check."""
        return path in self.directories

    def read_file(self, path: str) -> str:
        """Mock file reading."""
        return self.files.get(path, "")

    def clear(self):
        """Clear all mock files and directories."""
        self.files.clear()
        self.directories.clear()


@pytest.fixture
def mock_filesystem():
    """Pytest fixture for mock file system operations."""
    return MockFileSystemOperations()


def create_comprehensive_orchestrator_mocks():
    """Create comprehensive mocks for orchestrator testing."""
    with AsyncMockContext() as ctx:
        # Mock LionAGI components
        ctx.add_mock(
            "khive.services.orchestration.orchestrator.create_cc",
            AsyncMock(
                return_value=MockExternalServices.create_mock_claude_code_model()
            ),
        )
        ctx.add_mock(
            "khive.services.orchestration.orchestrator.Session",
            MagicMock(side_effect=MockLionAGIComponents.create_mock_session),
        )
        ctx.add_mock(
            "khive.services.orchestration.orchestrator.Builder",
            MagicMock(side_effect=MockLionAGIComponents.create_mock_builder),
        )
        ctx.add_mock(
            "khive.services.orchestration.orchestrator.Branch",
            MagicMock(side_effect=MockLionAGIComponents.create_mock_branch),
        )

        # Mock external services
        ctx.add_mock(
            "khive.services.orchestration.orchestrator.composer_service",
            MockExternalServices.create_mock_composer_service(),
        )

        # Mock file system operations
        ctx.add_mock("pathlib.Path.exists", MagicMock(return_value=True))
        ctx.add_mock("pathlib.Path.mkdir", MagicMock())
        ctx.add_mock("aiofiles.open", AsyncMock())

        return ctx


@pytest.fixture
def comprehensive_orchestrator_mocks():
    """Pytest fixture for comprehensive orchestrator mocks."""
    return create_comprehensive_orchestrator_mocks()
