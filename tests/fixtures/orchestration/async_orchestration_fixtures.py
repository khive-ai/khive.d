"""
Comprehensive async fixtures for orchestration testing.

This module provides reusable fixtures for testing LionOrchestrator functionality,
including mock services, test data, and async context management.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from lionagi import Branch, Builder, Session
from lionagi.fields import Instruct
from lionagi.service.imodel import iModel

from khive.services.artifacts.factory import ArtifactsConfig
from khive.services.artifacts.models import Author, DocumentType
from khive.services.artifacts.service import ArtifactsService
from khive.services.composition.parts import ComposerRequest
from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.orchestration.parts import (AgentRequest, GateOptions,
                                                OrchestrationPlan)
from khive.services.plan.parts import ComplexityLevel, TaskPhase
from khive.services.plan.planner_service import PlannerService


class MockAsyncContextManager:
    """Mock async context manager for testing."""

    def __init__(self, return_value=None):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async testing."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)
        # Create common subdirectories
        (workspace_path / "scratchpad").mkdir(exist_ok=True)
        (workspace_path / "deliverable").mkdir(exist_ok=True)
        (workspace_path / "sessions").mkdir(exist_ok=True)
        yield workspace_path


@pytest.fixture
def mock_cc_model():
    """Create a mock Claude Code model for testing."""
    model = MagicMock(spec=iModel)
    model.invoke = AsyncMock(return_value=MagicMock(content="Mock LLM response"))
    model.model_name = "claude-3-5-sonnet"
    return model


@pytest.fixture
def mock_session():
    """Create a mock lionagi Session for testing."""
    session = MagicMock(spec=Session)
    session.id = str(uuid4())
    session.name = "test_session"

    # Mock default branch
    session.default_branch = MagicMock(spec=Branch)
    session.default_branch.id = str(uuid4())
    session.default_branch.name = "default_branch"
    session.default_branch.operate = AsyncMock(return_value=MagicMock())

    # Mock branch management
    session._lookup_branch_by_name = MagicMock(return_value=None)
    session.create_branch = AsyncMock(return_value=str(uuid4()))
    session.get_branch = MagicMock(return_value=session.default_branch)
    session.list_branches = MagicMock(return_value=[session.default_branch])

    return session


@pytest.fixture
def mock_builder():
    """Create a mock lionagi Builder for testing."""
    builder = MagicMock(spec=Builder)
    builder.name = "test_builder"

    # Mock graph operations
    builder.get_graph = MagicMock(return_value=MagicMock())
    builder.add_operation = MagicMock(return_value=str(uuid4()))
    builder.execute = AsyncMock(return_value=MagicMock())

    return builder


@pytest.fixture
async def mock_artifacts_service(temp_workspace):
    """Create a mock artifacts service for testing."""
    config = ArtifactsConfig(
        storage_path=temp_workspace, enable_compression=False, max_file_size_mb=10
    )

    mock_service = MagicMock(spec=ArtifactsService)

    # Mock document operations
    mock_service.create_document = AsyncMock(return_value=str(uuid4()))
    mock_service.get_document = AsyncMock(
        return_value={
            "id": str(uuid4()),
            "title": "Test Document",
            "content": "Test document content for orchestration testing",
            "document_type": DocumentType.ANALYSIS,
            "author": Author(name="Test Agent", email="agent@khive.ai"),
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }
    )
    mock_service.list_documents = AsyncMock(return_value=[])
    mock_service.update_document = AsyncMock(return_value=True)
    mock_service.delete_document = AsyncMock(return_value=True)

    # Mock session operations
    mock_service.create_session = AsyncMock(return_value="test_session_id")
    mock_service.get_session_artifacts = AsyncMock(return_value=[])

    return mock_service


@pytest.fixture
async def mock_planner_service():
    """Create a mock planner service for testing."""
    mock_planner = MagicMock(spec=PlannerService)

    # Mock planning operations
    mock_planner.handle_request = AsyncMock(
        return_value=MagicMock(
            success=True,
            complexity=ComplexityLevel.MEDIUM,
            recommended_agents=3,
            phases=[
                TaskPhase(
                    name="analysis_phase",
                    description="Analysis and research phase",
                    agents=[],
                ),
                TaskPhase(
                    name="implementation_phase",
                    description="Implementation phase",
                    agents=[],
                ),
            ],
            spawn_commands=["Task('researcher: analyze requirements')"],
            session_id="test_planning_session",
        )
    )

    mock_planner.plan = AsyncMock(return_value=mock_planner.handle_request.return_value)
    mock_planner.get_metrics = MagicMock(
        return_value={
            "total_requests": 5,
            "avg_complexity": "medium",
            "success_rate": 0.95,
        }
    )

    return mock_planner


@pytest.fixture
async def initialized_orchestrator(mock_cc_model, mock_session, mock_builder):
    """Create a fully initialized orchestrator for testing."""
    orchestrator = LionOrchestrator("test_orchestration_flow")

    with (
        pytest.MonkeyPatch().context() as mp,
    ):
        # Patch all the dependencies
        mp.setattr(
            "khive.services.orchestration.orchestrator.create_cc",
            AsyncMock(return_value=mock_cc_model),
        )
        mp.setattr(
            "khive.services.orchestration.orchestrator.Session",
            lambda **kwargs: mock_session,
        )
        mp.setattr(
            "khive.services.orchestration.orchestrator.Branch",
            lambda **kwargs: mock_session.default_branch,
        )
        mp.setattr(
            "khive.services.orchestration.orchestrator.Builder",
            lambda name: mock_builder,
        )

        # Initialize the orchestrator
        await orchestrator.initialize()

        # Set up the mock objects
        orchestrator.session = mock_session
        orchestrator.builder = mock_builder

    return orchestrator


@pytest.fixture
def sample_agent_requests():
    """Create sample agent requests for testing."""
    return [
        AgentRequest(
            instruct=Instruct(instruction="Research distributed systems patterns"),
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
        AgentRequest(
            instruct=Instruct(instruction="Implement core services"),
            compose_request=ComposerRequest(
                role="implementer", domains="backend-development"
            ),
        ),
        AgentRequest(
            instruct=Instruct(instruction="Test system components"),
            compose_request=ComposerRequest(role="tester", domains="code-quality"),
        ),
        AgentRequest(
            instruct=Instruct(instruction="Review implementation"),
            compose_request=ComposerRequest(role="reviewer", domains="code-quality"),
        ),
    ]


@pytest.fixture
def sample_orchestration_plans(sample_agent_requests):
    """Create sample orchestration plans for testing."""
    return {
        "concurrent_plan": OrchestrationPlan(
            common_background="Concurrent execution test plan",
            agent_requests=sample_agent_requests[:3],
            execution_strategy="concurrent",
        ),
        "sequential_plan": OrchestrationPlan(
            common_background="Sequential execution test plan",
            agent_requests=sample_agent_requests[:2],
            execution_strategy="sequential",
        ),
        "complex_plan": OrchestrationPlan(
            common_background="Complex multi-agent orchestration plan",
            agent_requests=sample_agent_requests,
            execution_strategy="concurrent",
        ),
        "single_agent_plan": OrchestrationPlan(
            common_background="Single agent test plan",
            agent_requests=[sample_agent_requests[0]],
            execution_strategy="concurrent",
        ),
    }


@pytest.fixture
def quality_gate_configurations():
    """Create various quality gate configurations for testing."""
    return {
        "basic_gate": GateOptions(
            threshold=0.6,
            max_refinement_cycles=2,
            escalation_enabled=False,
            gate_type="basic",
        ),
        "thorough_gate": GateOptions(
            threshold=0.75,
            max_refinement_cycles=3,
            escalation_enabled=True,
            gate_type="thorough",
        ),
        "critical_gate": GateOptions(
            threshold=0.9,
            max_refinement_cycles=5,
            escalation_enabled=True,
            gate_type="critical",
        ),
        "emergency_gate": GateOptions(
            threshold=0.5,
            max_refinement_cycles=1,
            escalation_enabled=False,
            gate_type="basic",
        ),
    }


@pytest.fixture
def mock_composer_service():
    """Create a mock composer service for testing."""
    mock_service = MagicMock()
    mock_service.compose = AsyncMock(
        return_value=MagicMock(
            role="researcher",
            domains="distributed-systems",
            capabilities=["research", "analysis", "documentation"],
            tools=["search", "analyze", "document"],
        )
    )
    return mock_service


@pytest.fixture
async def async_test_timeout():
    """Provide configurable timeout for async tests."""
    return 30.0  # 30 seconds default timeout


@pytest.fixture
def performance_benchmarks():
    """Provide performance benchmarks for testing."""
    return {
        "max_initialization_time": 5.0,  # seconds
        "max_branch_creation_time": 2.0,  # seconds
        "max_workflow_execution_time": 30.0,  # seconds
        "max_memory_usage_mb": 100,  # MB
        "max_concurrent_agents": 10,
    }


@pytest.fixture
async def orchestration_test_session(
    initialized_orchestrator, mock_artifacts_service, temp_workspace
):
    """Create a complete orchestration test session with all dependencies."""

    class OrchestrationTestSession:
        def __init__(self, orchestrator, artifacts_service, workspace):
            self.orchestrator = orchestrator
            self.artifacts_service = artifacts_service
            self.workspace = workspace
            self.session_id = str(uuid4())
            self.created_branches = []
            self.executed_operations = []

        async def create_test_branch(
            self, role="researcher", domains="software-architecture"
        ):
            """Helper to create test branches."""
            compose_request = ComposerRequest(role=role, domains=domains)
            branch_id = await self.orchestrator.create_cc_branch(compose_request)
            self.created_branches.append(branch_id)
            return branch_id

        async def execute_test_workflow(self, plan):
            """Helper to execute test workflows."""
            result = await self.orchestrator.fanout(plan)
            self.executed_operations.append(result)
            return result

        def get_test_artifacts(self):
            """Get artifacts created during testing."""
            return {
                "session_id": self.session_id,
                "branches": self.created_branches,
                "operations": self.executed_operations,
                "workspace_path": self.workspace,
            }

        async def cleanup(self):
            """Clean up test resources."""
            self.created_branches.clear()
            self.executed_operations.clear()

    session = OrchestrationTestSession(
        initialized_orchestrator, mock_artifacts_service, temp_workspace
    )

    yield session

    # Cleanup after test
    await session.cleanup()


@pytest.fixture
def error_injection_helpers():
    """Provide helpers for error injection testing."""

    class ErrorInjectionHelpers:
        @staticmethod
        def mock_network_error():
            """Create a mock network error."""
            return ConnectionError("Network connection failed")

        @staticmethod
        def mock_timeout_error():
            """Create a mock timeout error."""
            return TimeoutError("Operation timed out")

        @staticmethod
        def mock_validation_error():
            """Create a mock validation error."""
            return ValueError("Invalid input parameters")

        @staticmethod
        def mock_resource_exhaustion():
            """Create a mock resource exhaustion error."""
            return MemoryError("Insufficient memory")

        @staticmethod
        async def inject_random_failure(probability=0.3):
            """Randomly inject failures for chaos testing."""
            import random

            if random.random() < probability:
                errors = [
                    ConnectionError("Random network failure"),
                    TimeoutError("Random timeout"),
                    ValueError("Random validation error"),
                ]
                raise random.choice(errors)

    return ErrorInjectionHelpers()


@pytest.fixture
def orchestration_metrics_collector():
    """Collect metrics during orchestration testing."""

    class MetricsCollector:
        def __init__(self):
            self.reset()

        def reset(self):
            self.metrics = {
                "branch_creation_times": [],
                "operation_execution_times": [],
                "memory_usage_samples": [],
                "error_counts": {"total": 0, "types": {}},
                "success_rates": {"total": 0, "successful": 0},
            }

        def record_branch_creation(self, duration):
            self.metrics["branch_creation_times"].append(duration)

        def record_operation_execution(self, duration):
            self.metrics["operation_execution_times"].append(duration)

        def record_memory_usage(self, usage_mb):
            self.metrics["memory_usage_samples"].append(usage_mb)

        def record_error(self, error_type):
            self.metrics["error_counts"]["total"] += 1
            error_name = type(error_type).__name__
            self.metrics["error_counts"]["types"][error_name] = (
                self.metrics["error_counts"]["types"].get(error_name, 0) + 1
            )

        def record_operation_result(self, success):
            self.metrics["success_rates"]["total"] += 1
            if success:
                self.metrics["success_rates"]["successful"] += 1

        def get_summary(self):
            return {
                "avg_branch_creation_time": (
                    sum(self.metrics["branch_creation_times"])
                    / len(self.metrics["branch_creation_times"])
                    if self.metrics["branch_creation_times"]
                    else 0
                ),
                "avg_operation_time": (
                    sum(self.metrics["operation_execution_times"])
                    / len(self.metrics["operation_execution_times"])
                    if self.metrics["operation_execution_times"]
                    else 0
                ),
                "peak_memory_usage": (
                    max(self.metrics["memory_usage_samples"])
                    if self.metrics["memory_usage_samples"]
                    else 0
                ),
                "error_rate": (
                    self.metrics["error_counts"]["total"]
                    / max(self.metrics["success_rates"]["total"], 1)
                ),
                "success_rate": (
                    self.metrics["success_rates"]["successful"]
                    / max(self.metrics["success_rates"]["total"], 1)
                ),
            }

    return MetricsCollector()
