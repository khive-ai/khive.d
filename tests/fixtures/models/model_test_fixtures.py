"""Comprehensive model test fixtures for Pydantic model validation testing."""

from datetime import datetime, timezone

import pytest
from lionagi.fields import Instruct

from khive.prompts import AgentRole
from khive.services.artifacts.models import Author, Document, DocumentType
from khive.services.composition.parts import (
    ComposerRequest,
    ComposerResponse,
    DomainExpertise,
)
from khive.services.orchestration.parts import AgentRequest, OrchestrationPlan
from khive.services.plan.parts import (
    AgentRecommendation,
    ComplexityLevel,
    PlannerRequest,
    PlannerResponse,
    QualityGate,
    TaskPhase,
    WorkflowPattern,
)


class ModelTestData:
    """Container for test data categories."""

    # Valid test data
    VALID_AUTHOR_DATA = {"id": "test_author_001", "role": "researcher"}

    VALID_DOCUMENT_DATA = {
        "session_id": "session_123",
        "name": "test_document",
        "type": DocumentType.DELIVERABLE,
        "content": "Test document content",
        "last_modified": datetime.now(timezone.utc),
    }

    VALID_COMPOSER_REQUEST_DATA = {
        "role": AgentRole.RESEARCHER,
        "domains": "async-programming,software-architecture",
        "context": "Testing task for async processing",
    }

    VALID_COMPOSER_RESPONSE_DATA = {
        "success": True,
        "summary": "Composed researcher agent with async programming expertise",
        "agent_id": "researcher_001",
        "role": "researcher",
        "system_prompt": "You are a researcher specializing in async programming",
        "confidence": 0.95,
    }

    VALID_PLANNER_REQUEST_DATA = {
        "task_description": "Implement async queue processing system",
        "context": "High-throughput task processing with Redis backend",
        "time_budget_seconds": 60.0,
    }

    # Invalid test data for boundary testing
    INVALID_AUTHOR_DATA = [
        {"id": "", "role": "researcher"},  # Empty id
        {"id": "test", "role": ""},  # Empty role
        {"role": "researcher"},  # Missing id
        {"id": "test"},  # Missing role
    ]

    INVALID_DOCUMENT_DATA = [
        {
            "name": "test",
            "type": DocumentType.DELIVERABLE,
            "content": "content",
        },  # Missing session_id
        {
            "session_id": "",
            "name": "test",
            "type": DocumentType.DELIVERABLE,
            "content": "content",
        },  # Empty session_id
        {
            "session_id": "session",
            "name": "",
            "type": DocumentType.DELIVERABLE,
            "content": "content",
        },  # Empty name
    ]

    INVALID_COMPOSER_RESPONSE_DATA = [
        {
            "success": True,
            "summary": "",
            "agent_id": "agent",
            "role": "role",
            "system_prompt": "prompt",
            "confidence": 0.5,
        },  # Empty summary
        {
            "success": True,
            "summary": "summary",
            "agent_id": "",
            "role": "role",
            "system_prompt": "prompt",
            "confidence": 0.5,
        },  # Empty agent_id
        {
            "success": True,
            "summary": "summary",
            "agent_id": "agent",
            "role": "",
            "system_prompt": "prompt",
            "confidence": 0.5,
        },  # Empty role
        {
            "success": True,
            "summary": "summary",
            "agent_id": "agent",
            "role": "role",
            "system_prompt": "",
            "confidence": 0.5,
        },  # Empty system_prompt
        {
            "success": True,
            "summary": "summary",
            "agent_id": "agent",
            "role": "role",
            "system_prompt": "prompt",
            "confidence": 1.5,
        },  # Invalid confidence
        {
            "success": True,
            "summary": "summary",
            "agent_id": "agent",
            "role": "role",
            "system_prompt": "prompt",
            "confidence": -0.1,
        },  # Invalid confidence
    ]

    # Boundary value test data
    BOUNDARY_TEST_DATA = {
        "confidence_values": [0.0, 0.1, 0.5, 0.9, 1.0],
        "invalid_confidence_values": [-0.1, 1.1, 2.0, -1.0],
        "string_lengths": {
            "min": "a",
            "normal": "test_string",
            "max_100": "a" * 100,
            "max_500": "a" * 500,
            "max_10000": "a" * 10000,
            "overflow_101": "a" * 101,
            "overflow_501": "a" * 501,
            "overflow_10001": "a" * 10001,
        },
    }

    # Enum test data
    ENUM_TEST_DATA = {
        "valid_document_types": [DocumentType.DELIVERABLE, DocumentType.SCRATCHPAD],
        "valid_complexity_levels": [
            ComplexityLevel.SIMPLE,
            ComplexityLevel.MEDIUM,
            ComplexityLevel.COMPLEX,
            ComplexityLevel.VERY_COMPLEX,
        ],
        "valid_workflow_patterns": [
            WorkflowPattern.PARALLEL,
            WorkflowPattern.SEQUENTIAL,
            WorkflowPattern.HYBRID,
        ],
        "valid_quality_gates": [
            QualityGate.BASIC,
            QualityGate.THOROUGH,
            QualityGate.CRITICAL,
        ],
        "valid_agent_roles": [role for role in AgentRole],
    }


@pytest.fixture
def valid_author():
    """Valid Author model instance."""
    return Author(**ModelTestData.VALID_AUTHOR_DATA)


@pytest.fixture
def valid_document():
    """Valid Document model instance."""
    return Document(**ModelTestData.VALID_DOCUMENT_DATA)


@pytest.fixture
def valid_composer_request():
    """Valid ComposerRequest model instance."""
    return ComposerRequest(**ModelTestData.VALID_COMPOSER_REQUEST_DATA)


@pytest.fixture
def valid_composer_response():
    """Valid ComposerResponse model instance."""
    return ComposerResponse(**ModelTestData.VALID_COMPOSER_RESPONSE_DATA)


@pytest.fixture
def valid_planner_request():
    """Valid PlannerRequest model instance."""
    return PlannerRequest(**ModelTestData.VALID_PLANNER_REQUEST_DATA)


@pytest.fixture
def valid_agent_recommendation():
    """Valid AgentRecommendation model instance."""
    return AgentRecommendation(
        role="researcher",
        domain="async-programming",
        priority=0.9,
        reasoning="Expert in async patterns and concurrency",
    )


@pytest.fixture
def valid_task_phase(valid_agent_recommendation):
    """Valid TaskPhase model instance."""
    return TaskPhase(
        name="Research Phase",
        description="Research async programming patterns",
        agents=[valid_agent_recommendation],
        quality_gate=QualityGate.THOROUGH,
        coordination_pattern=WorkflowPattern.PARALLEL,
    )


@pytest.fixture
def valid_planner_response(valid_task_phase):
    """Valid PlannerResponse model instance."""
    return PlannerResponse(
        success=True,
        summary="Comprehensive async processing plan",
        complexity=ComplexityLevel.MEDIUM,
        recommended_agents=3,
        phases=[valid_task_phase],
        spawn_commands=["khive compose researcher -d async-programming"],
        confidence=0.9,
    )


@pytest.fixture
def valid_domain_expertise():
    """Valid DomainExpertise model instance."""
    return DomainExpertise(
        domain_id="async-programming",
        knowledge_patterns={
            "patterns": ["event_loop", "coroutines", "async_context_managers"]
        },
        decision_rules={
            "rules": ["prefer_async_await", "use_asyncio_gather_for_concurrency"]
        },
        specialized_tools=["asyncio", "aiohttp", "pytest-asyncio"],
        confidence_thresholds={"min": 0.7, "target": 0.9},
    )


@pytest.fixture
def valid_orchestration_plan():
    """Valid OrchestrationPlan model instance."""
    instruct = Instruct(
        instruction="Research async programming patterns",
        guidance="Focus on modern Python async/await patterns",
        context="Building high-performance async system",
    )
    composer_request = ComposerRequest(
        role=AgentRole.RESEARCHER,
        domains="async-programming",
        context="Async research task",
    )
    agent_request = AgentRequest(
        instruct=instruct,
        compose_request=composer_request,
        analysis_type="RequirementsAnalysis",
    )

    return OrchestrationPlan(
        common_background="Async system development project",
        agent_requests=[agent_request],
    )


@pytest.fixture
def model_test_data():
    """Access to all test data categories."""
    return ModelTestData


@pytest.fixture
def large_data_models():
    """Models with large data for performance testing."""
    large_content = "x" * 10000  # 10KB content
    large_document = Document(
        session_id="large_session",
        name="large_document",
        type=DocumentType.DELIVERABLE,
        content=large_content,
        last_modified=datetime.now(timezone.utc),
    )

    many_agents = []
    for i in range(100):
        instruct = Instruct(instruction=f"Task {i}")
        composer_request = ComposerRequest(role=AgentRole.RESEARCHER)
        agent_request = AgentRequest(
            instruct=instruct, compose_request=composer_request
        )
        many_agents.append(agent_request)

    large_orchestration = OrchestrationPlan(
        common_background="Large orchestration test", agent_requests=many_agents
    )

    return {
        "large_document": large_document,
        "large_orchestration": large_orchestration,
    }


@pytest.fixture(
    params=["valid_minimal", "valid_complete", "boundary_values", "empty_optionals"]
)
def parametrized_composer_request(request):
    """Parametrized ComposerRequest for comprehensive testing."""
    test_cases = {
        "valid_minimal": ComposerRequest(role=AgentRole.RESEARCHER),
        "valid_complete": ComposerRequest(
            role=AgentRole.RESEARCHER,
            domains="async-programming,software-architecture",
            context="Complete test case with all fields",
        ),
        "boundary_values": ComposerRequest(
            role=AgentRole.RESEARCHER,
            domains="a" * 500,  # Max length
            context="a" * 10000,  # Max length
        ),
        "empty_optionals": ComposerRequest(
            role=AgentRole.RESEARCHER, domains=None, context=None
        ),
    }
    return test_cases[request.param]


@pytest.fixture
def error_injection_data():
    """Data for testing error conditions and edge cases."""
    return {
        "type_errors": [
            {
                "field": "confidence",
                "value": "not_a_float",
                "expected_error": "Input should be a valid number",
            },
            {
                "field": "success",
                "value": "not_a_bool",
                "expected_error": "Input should be a valid boolean",
            },
            {
                "field": "recommended_agents",
                "value": "not_an_int",
                "expected_error": "Input should be a valid integer",
            },
        ],
        "constraint_violations": [
            {
                "field": "confidence",
                "value": -0.5,
                "expected_error": "Input should be greater than or equal to 0",
            },
            {
                "field": "confidence",
                "value": 1.5,
                "expected_error": "Input should be less than or equal to 1",
            },
            {
                "field": "agent_id",
                "value": "",
                "expected_error": "String should have at least 1 character",
            },
        ],
        "missing_required": [
            {"missing_field": "success", "expected_error": "Field required"},
            {"missing_field": "summary", "expected_error": "Field required"},
            {"missing_field": "agent_id", "expected_error": "Field required"},
        ],
    }
