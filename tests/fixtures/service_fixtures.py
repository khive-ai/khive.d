"""Service layer testing fixtures."""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_orchestration_service():
    """Mock orchestration service for testing."""
    service = AsyncMock()
    service.execute_issue = AsyncMock()
    service.create_workflow = AsyncMock()
    service.get_workflow_status = AsyncMock()
    return service


@pytest.fixture
def mock_composition_service():
    """Mock agent composition service for testing."""
    service = AsyncMock()
    service.compose_agent = AsyncMock()
    service.get_agent_config = AsyncMock()
    service.validate_composition = AsyncMock()
    return service


@pytest.fixture
def mock_plan_service():
    """Mock planning service for testing."""
    service = AsyncMock()
    service.create_plan = AsyncMock()
    service.estimate_costs = AsyncMock()
    service.validate_plan = AsyncMock()
    return service


@pytest.fixture
def mock_claude_service():
    """Mock Claude service for testing."""
    service = AsyncMock()
    service.send_message = AsyncMock()
    service.create_session = AsyncMock()
    service.get_response = AsyncMock()
    return service


@pytest.fixture
def mock_mcp_service():
    """Mock MCP service for testing."""
    service = AsyncMock()
    service.connect = AsyncMock()
    service.disconnect = AsyncMock()
    service.list_tools = AsyncMock()
    service.call_tool = AsyncMock()
    return service


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing."""
    return {
        "id": "workflow_001",
        "name": "test_workflow",
        "steps": [
            {"id": "step_1", "type": "analyze", "params": {}},
            {"id": "step_2", "type": "implement", "params": {}},
            {"id": "step_3", "type": "test", "params": {}},
        ],
        "status": "pending",
        "created_at": "2023-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_agent_config():
    """Sample agent configuration for testing."""
    return {
        "role": "architect",
        "domain": "software-architecture",
        "capabilities": ["analysis", "design", "documentation"],
        "tools": ["read", "write", "bash"],
        "context": "Design system architecture for testing infrastructure",
    }


@pytest.fixture
def sample_issue_data():
    """Sample issue data for testing."""
    return {
        "issue_num": 195,
        "flow_name": "test_infrastructure_setup",
        "pattern": "W_REFINEMENT",
        "project_phase": "development",
        "is_critical_path": True,
        "workspace_path": ".khive/workspaces/test_workspace",
        "description": "Test issue for infrastructure setup",
    }
