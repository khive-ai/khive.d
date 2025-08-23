"""Pytest configuration and fixtures for orchestration tests.

This module provides common fixtures and configuration for all orchestration tests,
including mock setups, test data, and performance thresholds.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from lionagi.fields import Instruct
from lionagi.protocols.types import AssistantResponse
from lionagi.service.imodel import iModel

from khive.services.composition.parts import ComposerRequest
from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.orchestration.parts import (
    AgentRequest,
    BaseGate,
    GateComponent,
    OrchestrationPlan,
)


@pytest.fixture(scope="function")
def orchestrator_with_mocks():
    """Create orchestrator with comprehensive mocking for testing."""
    orchestrator = LionOrchestrator("test_flow")

    # Mock session
    orchestrator.session = MagicMock()
    orchestrator.session.id = str(uuid4())
    orchestrator.session.name = "test_flow"
    orchestrator.session.default_branch = MagicMock()
    orchestrator.session.branches = MagicMock()
    orchestrator.session._lookup_branch_by_name = MagicMock(return_value=None)
    orchestrator.session.get_branch = MagicMock()
    orchestrator.session.flow = AsyncMock(
        return_value={"operation_results": {"mock_op": "mock_result"}}
    )

    # Mock builder
    orchestrator.builder = MagicMock()
    orchestrator.builder.add_operation = MagicMock(
        side_effect=lambda *args, **kwargs: f"op_{uuid4().hex[:8]}"
    )
    orchestrator.builder.get_graph = MagicMock()
    orchestrator.builder.get_graph.return_value.internal_nodes = {}
    orchestrator.builder.last_operation_id = None
    orchestrator.builder.visualize = MagicMock()

    return orchestrator


@pytest.fixture
def mock_create_cc():
    """Mock create_cc function for orchestrator tests."""
    with patch("khive.services.orchestration.orchestrator.create_cc") as mock_cc:
        mock_imodel = MagicMock(spec=iModel)
        mock_imodel.endpoint = MagicMock()
        mock_imodel.endpoint.endpoint = "anthropic/claude-3-5-sonnet-20241022"
        mock_cc.return_value = mock_imodel
        yield mock_cc


@pytest.fixture
def sample_composer_request():
    """Sample composer request for testing."""
    return ComposerRequest(role="researcher", domains="software-architecture")


@pytest.fixture
def sample_orchestration_plan(sample_composer_request):
    """Sample orchestration plan for testing."""
    return OrchestrationPlan(
        common_background="Test orchestration background",
        agent_requests=[
            AgentRequest(
                instruct=Instruct(
                    instruction="Analyze requirements",
                    context="Requirements analysis context",
                    guidance="Follow best practices for analysis",
                ),
                compose_request=sample_composer_request,
                analysis_type="RequirementsAnalysis",
            ),
            AgentRequest(
                instruct=Instruct(
                    instruction="Design system architecture",
                    context="System design context",
                    guidance="Focus on scalability and maintainability",
                ),
                compose_request=ComposerRequest(
                    role="architect", domains="distributed-systems"
                ),
                analysis_type="CodeContextAnalysis",
            ),
        ],
        execution_strategy="concurrent",
    )


@pytest.fixture
def mock_assistant_response():
    """Mock AssistantResponse for testing."""
    mock_response = MagicMock(spec=AssistantResponse)
    mock_response.model_response = {
        "result": "Test result",
        "summary": "Test summary",
        "analysis": "Test analysis",
    }
    return mock_response


@pytest.fixture
def mock_file_system():
    """Mock file system operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create mock directories
        khive_config_dir = temp_path / ".khive" / "config"
        claude_roles_dir = khive_config_dir / "claude_roles"

        # Setup directory structure
        for role in [
            "researcher",
            "analyst",
            "architect",
            "implementer",
            "tester",
            "reviewer",
        ]:
            role_dir = claude_roles_dir / role / ".claude"
            role_dir.mkdir(parents=True, exist_ok=True)

            # Create mock configuration files
            (role_dir / "settings.json").write_text('{"test": "config"}')
            (role_dir / "CLAUDE.md").write_text(f"# Claude configuration for {role}")
            (role_dir / ".mcp.json").write_text('{"test": "mcp_config"}')

        yield temp_path


@pytest.fixture
def mock_shutil():
    """Mock shutil operations for file system tests."""
    with patch("shutil.copytree") as mock_copytree, patch("shutil.copy") as mock_copy:
        mock_copytree.return_value = None
        mock_copy.return_value = None
        yield {"copytree": mock_copytree, "copy": mock_copy}


@pytest.fixture
def performance_thresholds():
    """Performance thresholds for testing."""
    return {
        "initialize_max_time": 2.0,  # 2 seconds max for initialization
        "create_branch_max_time": 1.0,  # 1 second max for branch creation
        "run_flow_max_time": 5.0,  # 5 seconds max for basic flow
        "fanout_max_time": 10.0,  # 10 seconds max for fanout operation
        "gate_evaluation_max_time": 3.0,  # 3 seconds max for gate evaluation
        "max_memory_growth_mb": 50,  # 50MB max memory growth
        "max_concurrent_operations": 20,  # Max 20 concurrent operations
    }


@pytest.fixture
def sample_gate_evaluations():
    """Sample gate evaluations for testing."""
    return {
        "passing_all": BaseGate(
            threshold_met=True, feedback="All quality criteria successfully met"
        ),
        "failing_security": BaseGate(
            threshold_met=False,
            feedback="Security vulnerabilities detected requiring immediate attention",
        ),
        "failing_design": BaseGate(
            threshold_met=False,
            feedback="Architectural design needs significant improvements",
        ),
        "failing_multiple": BaseGate(
            threshold_met=False,
            feedback="Multiple issues: security, design, and performance problems",
        ),
    }


@pytest.fixture
def sample_gate_components():
    """Sample gate components for testing."""
    return {
        "security_passing": GateComponent(is_acceptable=True, problems=[]),
        "security_failing": GateComponent(
            is_acceptable=False,
            problems=[
                "SQL injection vulnerability in user input validation",
                "Cross-site scripting (XSS) potential in comment rendering",
                "Inadequate authentication token management",
            ],
        ),
        "design_passing": GateComponent(is_acceptable=True, problems=[]),
        "design_failing": GateComponent(
            is_acceptable=False,
            problems=[
                "Tight coupling between business logic and data access layers",
                "Missing abstraction for external service dependencies",
                "Inconsistent error handling patterns across modules",
            ],
        ),
        "performance_failing": GateComponent(
            is_acceptable=False,
            problems=[
                "Database queries not optimized for large datasets",
                "Memory leaks in long-running operations",
                "Inefficient algorithms in critical performance paths",
            ],
        ),
    }


@pytest.fixture
def timeout_scenarios():
    """Timeout scenarios for testing."""
    return {
        "immediate": 0.001,  # 1ms - should timeout immediately
        "very_short": 0.1,  # 100ms - short timeout for testing
        "short": 0.5,  # 500ms - reasonable for quick operations
        "medium": 2.0,  # 2 seconds - medium timeout
        "long": 10.0,  # 10 seconds - long timeout for complex operations
    }


@pytest.fixture
def error_scenarios():
    """Common error scenarios for testing."""
    return {
        "network_errors": [
            ConnectionError("Network connection failed"),
            TimeoutError("Network request timed out"),
            OSError("Network interface unavailable"),
        ],
        "resource_errors": [
            MemoryError("Insufficient memory available"),
            OSError("Too many open files"),
            RuntimeError("Thread pool executor exhausted"),
        ],
        "validation_errors": [
            ValueError("Invalid parameter value provided"),
            TypeError("Incorrect parameter type"),
            AttributeError("Required attribute missing"),
        ],
        "external_service_errors": [
            Exception("External API service unavailable"),
            Exception("Authentication failed for external service"),
            Exception("External service rate limit exceeded"),
        ],
    }


@pytest.fixture
def large_scale_test_data():
    """Large scale test data for performance and boundary testing."""
    return {
        "large_agent_count": 100,
        "huge_context_size": 100000,  # 100K characters
        "massive_context_size": 1000000,  # 1M characters
        "many_operations": 1000,
        "deep_dependency_chain": 50,
        "concurrent_orchestrations": 10,
    }


@pytest.fixture
def mock_external_services():
    """Mock external services for integration testing."""
    return {
        "git_service": MagicMock(),
        "claude_service": MagicMock(),
        "database_service": MagicMock(),
        "file_service": MagicMock(),
        "network_service": MagicMock(),
    }


@pytest.fixture
def workflow_state_tracker():
    """Workflow state tracking fixture for testing state management."""
    return {
        "states": [],
        "transitions": [],
        "errors": [],
        "performance_metrics": {},
    }


@pytest.fixture(autouse=True)
def patch_imports():
    """Auto-patch imports that might not be available in test environment."""
    with (
        patch("khive.utils.KHIVE_CONFIG_DIR", new=Path("/tmp/khive_test_config")),
        patch("khive.utils.PROJECT_ROOT", new=Path("/tmp/khive_test_project")),
        patch("khive.services.orchestration.orchestrator.get_logger") as mock_logger,
    ):
        mock_logger.return_value = MagicMock()
        yield


@pytest.fixture
def async_timeout():
    """Async timeout context manager for tests."""

    def _timeout(seconds=5.0):
        return asyncio.wait_for

    return _timeout


# Pytest configuration
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add appropriate markers."""
    # Add timeout marker to all async tests
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)

        # Add slow marker to performance tests
        if "performance" in item.name.lower():
            item.add_marker(pytest.mark.slow)

        # Add integration marker to integration tests
        if "integration" in item.name.lower() or "e2e" in item.name.lower():
            item.add_marker(pytest.mark.integration)


# Import patch at module level for use in fixtures
from unittest.mock import patch
