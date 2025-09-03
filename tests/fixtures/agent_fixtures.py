"""Agent composition and orchestration test fixtures."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from khive.services.composition.models import ComposerRequest


@pytest.fixture
def agent_composer_fixture():
    """Mock agent composer for testing agent creation and configuration."""
    from khive.services.composition.agent_composer import AgentComposer

    composer = MagicMock(spec=AgentComposer)
    composer.compose_agent = AsyncMock(
        return_value={
            "persona": "Mock agent persona",
            "capabilities": ["analysis", "implementation"],
            "domain_knowledge": {"patterns": [], "tools": []},
            "decision_rules": [],
        }
    )
    return composer


@pytest.fixture
def mock_agent_request():
    """Create mock agent composition request with realistic data."""
    return ComposerRequest(
        role="researcher",
        domain="software-architecture",
        context="Test context for agent composition",
        task_requirements=["analyze", "document"],
        capabilities_needed=["research", "analysis"],
    )


@pytest.fixture
def agent_composition_scenarios():
    """Comprehensive test scenarios for agent composition."""
    return [
        {
            "name": "simple_researcher",
            "role": "researcher",
            "domain": "api-design",
            "context": "Research REST API best practices",
            "expected_capabilities": ["research", "analysis", "documentation"],
            "expected_tools": ["web_search", "document_analysis"],
        },
        {
            "name": "security_architect",
            "role": "architect",
            "domain": "security",
            "context": "Design secure authentication system",
            "expected_capabilities": ["security_analysis", "system_design"],
            "expected_tools": ["threat_modeling", "security_review"],
        },
        {
            "name": "performance_tester",
            "role": "tester",
            "domain": "performance",
            "context": "Load test distributed system",
            "expected_capabilities": ["performance_testing", "monitoring"],
            "expected_tools": ["load_generation", "metrics_collection"],
        },
        {
            "name": "multi_domain_implementer",
            "role": "implementer",
            "domain": ["backend-development", "database-design"],
            "context": "Implement microservice with database",
            "expected_capabilities": ["coding", "database_design", "testing"],
            "expected_tools": ["code_generation", "database_migration", "unit_testing"],
        },
    ]


@pytest.fixture
def role_domain_combinations():
    """Valid role and domain combinations for testing."""
    return {
        "researcher": [
            "software-architecture",
            "api-design",
            "database-design",
            "security",
            "performance",
            "ai-governance",
        ],
        "architect": [
            "microservices-architecture",
            "software-architecture",
            "database-design",
            "security",
            "devops-automation",
        ],
        "implementer": [
            "backend-development",
            "frontend-development",
            "database-design",
            "api-design",
            "async-programming",
        ],
        "tester": ["code-quality", "performance", "security", "ci-cd-pipelines"],
        "analyst": [
            "software-architecture",
            "performance",
            "security",
            "agile-methodology",
            "ai-governance",
        ],
        "reviewer": [
            "code-quality",
            "security",
            "software-architecture",
            "api-design",
            "database-design",
        ],
    }


@pytest.fixture
def orchestration_request_scenarios():
    """Test scenarios for orchestration requests."""
    return [
        {
            "name": "simple_feature",
            "description": "Add user authentication endpoint",
            "complexity": "simple",
            "expected_agents": 2,
            "expected_roles": ["implementer", "tester"],
        },
        {
            "name": "complex_system",
            "description": "Design and implement distributed consensus protocol",
            "complexity": "complex",
            "expected_agents": 5,
            "expected_roles": [
                "researcher",
                "architect",
                "implementer",
                "tester",
                "reviewer",
            ],
        },
        {
            "name": "security_critical",
            "description": "Implement OAuth2 with PKCE and secure token storage",
            "complexity": "moderate",
            "expected_agents": 4,
            "expected_roles": ["researcher", "architect", "implementer", "auditor"],
        },
    ]


@pytest.fixture
def mock_agent_workspace(tmp_path: Path):
    """Create isolated workspace for agent testing."""
    workspace = tmp_path / "agent_workspace"
    workspace.mkdir()

    # Create standard agent directories
    (workspace / "artifacts").mkdir()
    (workspace / "logs").mkdir()
    (workspace / "context").mkdir()

    # Create mock configuration
    config_file = workspace / "agent_config.json"
    config_file.write_text('{"role": "test", "domain": "testing"}')

    return workspace


@pytest.fixture
def agent_performance_metrics():
    """Performance metrics for agent testing."""
    return {
        "composition_time_ms": 500,
        "memory_usage_mb": 50,
        "context_processing_time_ms": 200,
        "decision_making_time_ms": 100,
        "max_concurrent_agents": 10,
        "throughput_requests_per_second": 20,
    }


@pytest.fixture
def agent_error_scenarios():
    """Error scenarios for robust agent testing."""
    return [
        {
            "error_type": "invalid_role",
            "input": {"role": "invalid_role", "domain": "valid-domain"},
            "expected_error": "ValidationError",
        },
        {
            "error_type": "invalid_domain",
            "input": {"role": "researcher", "domain": "nonexistent-domain"},
            "expected_error": "DomainNotFoundError",
        },
        {
            "error_type": "insufficient_context",
            "input": {"role": "implementer", "domain": "backend", "context": ""},
            "expected_error": "InsufficientContextError",
        },
        {
            "error_type": "resource_exhaustion",
            "input": {"concurrent_requests": 100},
            "expected_error": "ResourceExhaustionError",
        },
    ]


@pytest.fixture
def agent_security_test_cases():
    """Security test cases for agent composition."""
    return [
        {
            "name": "context_injection",
            "malicious_input": {
                "context": "Normal context; DELETE FROM users; --",
                "role": "researcher",
            },
            "expected_behavior": "sanitized_and_rejected",
        },
        {
            "name": "role_escalation",
            "malicious_input": {
                "role": "admin; DROP TABLE agents; --",
                "domain": "security",
            },
            "expected_behavior": "validation_error",
        },
        {
            "name": "path_traversal",
            "malicious_input": {
                "context": "../../../etc/passwd",
                "domain": "filesystem",
            },
            "expected_behavior": "path_sanitized",
        },
    ]


__all__ = [
    "agent_composer_fixture",
    "mock_agent_request",
    "agent_composition_scenarios",
    "role_domain_combinations",
    "orchestration_request_scenarios",
    "mock_agent_workspace",
    "agent_performance_metrics",
    "agent_error_scenarios",
    "agent_security_test_cases",
]
