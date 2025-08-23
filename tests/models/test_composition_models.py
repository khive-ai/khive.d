"""Comprehensive tests for composition Pydantic models."""

import pytest
from pydantic import ValidationError

from khive.prompts import AgentRole
from khive.services.composition.parts import (
    AgentCompositionRequest,
    ComposerRequest,
    ComposerResponse,
    DomainExpertise,
)


class TestComposerRequest:
    """Test ComposerRequest model validation and behavior."""

    def test_valid_composer_request_creation(self):
        """Test creating valid ComposerRequest instances."""
        request = ComposerRequest(
            role=AgentRole.RESEARCHER,
            domains="async-programming,software-architecture",
            context="Testing task for async processing",
        )

        assert request.role == AgentRole.RESEARCHER
        assert request.domains == "async-programming,software-architecture"
        assert request.context == "Testing task for async processing"

    def test_composer_request_minimal(self):
        """Test ComposerRequest with only required field."""
        request = ComposerRequest(role=AgentRole.ARCHITECT)

        assert request.role == AgentRole.ARCHITECT
        assert request.domains is None
        assert request.context is None

    @pytest.mark.parametrize(
        "role",
        [
            AgentRole.ANALYST,
            AgentRole.ARCHITECT,
            AgentRole.AUDITOR,
            AgentRole.COMMENTATOR,
            AgentRole.CRITIC,
            AgentRole.IMPLEMENTER,
            AgentRole.INNOVATOR,
            AgentRole.RESEARCHER,
            AgentRole.REVIEWER,
            AgentRole.STRATEGIST,
            AgentRole.TESTER,
            AgentRole.THEORIST,
        ],
    )
    def test_all_valid_agent_roles(self, role):
        """Test all valid AgentRole enum values."""
        request = ComposerRequest(role=role)
        assert request.role == role

    def test_composer_request_validation_errors(self):
        """Test validation errors for ComposerRequest."""
        # Missing required role field
        with pytest.raises(ValidationError) as exc_info:
            ComposerRequest()

        error_msg = str(exc_info.value)
        assert "role" in error_msg
        assert "Field required" in error_msg

    def test_composer_request_serialization(self):
        """Test ComposerRequest serialization and deserialization."""
        original = ComposerRequest(
            role=AgentRole.RESEARCHER,
            domains="async-programming,distributed-systems",
            context="Complex multi-domain analysis task",
        )

        # Test serialization
        data = original.model_dump()
        assert data["role"] == "researcher"  # Should use enum value
        assert data["domains"] == "async-programming,distributed-systems"
        assert data["context"] == "Complex multi-domain analysis task"

        # Test deserialization
        restored = ComposerRequest.model_validate(data)
        assert restored == original

    def test_composer_request_optional_fields(self):
        """Test ComposerRequest with various optional field combinations."""
        # Only domains provided
        request1 = ComposerRequest(
            role=AgentRole.RESEARCHER, domains="async-programming"
        )
        assert request1.context is None

        # Only context provided
        request2 = ComposerRequest(
            role=AgentRole.RESEARCHER, context="Research task context"
        )
        assert request2.domains is None


class TestDomainExpertise:
    """Test DomainExpertise model validation and behavior."""

    def test_valid_domain_expertise_creation(self):
        """Test creating valid DomainExpertise instances."""
        expertise = DomainExpertise(
            domain_id="async-programming",
            knowledge_patterns={
                "patterns": ["event_loop", "coroutines", "async_context_managers"]
            },
            decision_rules={"rules": ["prefer_async_await", "use_asyncio_gather"]},
            specialized_tools=["asyncio", "aiohttp", "pytest-asyncio"],
            confidence_thresholds={"min": 0.7, "target": 0.9},
        )

        assert expertise.domain_id == "async-programming"
        assert "patterns" in expertise.knowledge_patterns
        assert "rules" in expertise.decision_rules
        assert len(expertise.specialized_tools) == 3
        assert expertise.confidence_thresholds["min"] == 0.7

    def test_domain_expertise_defaults(self):
        """Test DomainExpertise with default values."""
        expertise = DomainExpertise(domain_id="test-domain")

        assert expertise.domain_id == "test-domain"
        assert expertise.knowledge_patterns == {}
        assert expertise.decision_rules == {}
        assert expertise.specialized_tools == []
        assert expertise.confidence_thresholds == {}

    def test_domain_expertise_validation_errors(self):
        """Test validation errors for DomainExpertise."""
        # Missing required domain_id
        with pytest.raises(ValidationError) as exc_info:
            DomainExpertise()

        error_msg = str(exc_info.value)
        assert "domain_id" in error_msg
        assert "Field required" in error_msg

    def test_domain_id_constraints(self):
        """Test domain_id field constraints."""
        # Valid non-empty domain_id
        expertise = DomainExpertise(domain_id="valid-domain")
        assert expertise.domain_id == "valid-domain"

        # Empty domain_id should fail
        with pytest.raises(ValidationError) as exc_info:
            DomainExpertise(domain_id="")

        error_msg = str(exc_info.value)
        assert "domain_id" in error_msg
        assert "String should have at least 1 character" in error_msg

    def test_complex_knowledge_patterns(self):
        """Test DomainExpertise with complex knowledge patterns."""
        complex_patterns = {
            "async_patterns": ["coroutines", "tasks", "futures"],
            "design_patterns": ["producer_consumer", "pipeline", "fan_out_fan_in"],
            "performance_patterns": ["connection_pooling", "batch_processing"],
            "error_handling": ["exponential_backoff", "circuit_breaker"],
        }

        expertise = DomainExpertise(
            domain_id="advanced-async", knowledge_patterns=complex_patterns
        )

        assert len(expertise.knowledge_patterns) == 4
        assert "async_patterns" in expertise.knowledge_patterns
        assert len(expertise.knowledge_patterns["async_patterns"]) == 3

    def test_specialized_tools_list(self):
        """Test specialized_tools list handling."""
        tools = ["asyncio", "aiohttp", "fastapi", "celery", "redis"]

        expertise = DomainExpertise(domain_id="async-web", specialized_tools=tools)

        assert len(expertise.specialized_tools) == 5
        assert "asyncio" in expertise.specialized_tools
        assert "fastapi" in expertise.specialized_tools


class TestComposerResponse:
    """Test ComposerResponse model validation and behavior."""

    def test_valid_composer_response_creation(self):
        """Test creating valid ComposerResponse instances."""
        domain_expertise = DomainExpertise(
            domain_id="async-programming", specialized_tools=["asyncio", "aiohttp"]
        )

        response = ComposerResponse(
            success=True,
            summary="Composed researcher agent with async programming expertise",
            agent_id="researcher_001",
            role="researcher",
            domains=["async-programming", "software-architecture"],
            system_prompt="You are a researcher specializing in async programming",
            capabilities=["analysis", "research", "documentation"],
            tools=["search", "analyze", "document"],
            domain_expertise=[domain_expertise],
            confidence=0.95,
            error=None,
        )

        assert response.success is True
        assert (
            response.summary
            == "Composed researcher agent with async programming expertise"
        )
        assert response.agent_id == "researcher_001"
        assert response.role == "researcher"
        assert len(response.domains) == 2
        assert len(response.capabilities) == 3
        assert len(response.tools) == 3
        assert len(response.domain_expertise) == 1
        assert response.confidence == 0.95
        assert response.error is None

    def test_composer_response_minimal_required(self):
        """Test ComposerResponse with only required fields."""
        response = ComposerResponse(
            success=True,
            summary="Minimal agent composition",
            agent_id="agent_001",
            role="researcher",
            system_prompt="Basic system prompt",
            confidence=0.8,
        )

        assert response.domains == []
        assert response.capabilities == []
        assert response.tools == []
        assert response.domain_expertise == []

    def test_composer_response_failure_case(self):
        """Test ComposerResponse for failure scenarios."""
        response = ComposerResponse(
            success=False,
            summary="Failed to compose agent",
            agent_id="failed_agent",
            role="researcher",
            system_prompt="Fallback prompt",
            confidence=0.1,
            error="Invalid domain specification",
        )

        assert response.success is False
        assert response.error == "Invalid domain specification"
        assert response.confidence == 0.1

    def test_composer_response_validation_errors(self):
        """Test validation errors for ComposerResponse."""
        # Test missing required fields
        required_fields = [
            "success",
            "summary",
            "agent_id",
            "role",
            "system_prompt",
            "confidence",
        ]

        for field in required_fields:
            incomplete_data = {
                "success": True,
                "summary": "Test summary",
                "agent_id": "test_agent",
                "role": "researcher",
                "system_prompt": "Test prompt",
                "confidence": 0.8,
            }
            del incomplete_data[field]

            with pytest.raises(ValidationError) as exc_info:
                ComposerResponse(**incomplete_data)

            error_msg = str(exc_info.value)
            assert field in error_msg
            assert "Field required" in error_msg

    def test_composer_response_string_field_constraints(self):
        """Test string field constraints for ComposerResponse."""
        base_data = {
            "success": True,
            "agent_id": "test_agent",
            "role": "researcher",
            "system_prompt": "Test prompt",
            "confidence": 0.8,
        }

        # Test empty summary (should fail)
        with pytest.raises(ValidationError) as exc_info:
            ComposerResponse(summary="", **base_data)

        error_msg = str(exc_info.value)
        assert "summary" in error_msg
        assert "String should have at least 1 character" in error_msg

        # Test empty agent_id (should fail)
        with pytest.raises(ValidationError) as exc_info:
            ComposerResponse(
                summary="Test",
                agent_id="",
                **{k: v for k, v in base_data.items() if k != "agent_id"},
            )

        error_msg = str(exc_info.value)
        assert "agent_id" in error_msg

    def test_confidence_boundary_validation(self):
        """Test confidence field boundary validation."""
        base_data = {
            "success": True,
            "summary": "Test summary",
            "agent_id": "test_agent",
            "role": "researcher",
            "system_prompt": "Test prompt",
        }

        # Valid confidence values
        valid_confidences = [0.0, 0.1, 0.5, 0.9, 1.0]
        for confidence in valid_confidences:
            response = ComposerResponse(confidence=confidence, **base_data)
            assert response.confidence == confidence

        # Invalid confidence values
        invalid_confidences = [-0.1, 1.1, 2.0, -1.0]
        for confidence in invalid_confidences:
            with pytest.raises(ValidationError) as exc_info:
                ComposerResponse(confidence=confidence, **base_data)

            error_msg = str(exc_info.value)
            assert "confidence" in error_msg

    def test_composer_response_extra_fields_allowed(self):
        """Test ComposerResponse allows extra fields."""
        response = ComposerResponse(
            success=True,
            summary="Test summary",
            agent_id="test_agent",
            role="researcher",
            system_prompt="Test prompt",
            confidence=0.8,
            custom_field="allowed",  # Should be allowed
            metadata={"key": "value"},  # Should be allowed
        )

        assert hasattr(response, "custom_field")
        assert response.custom_field == "allowed"
        assert hasattr(response, "metadata")
        assert response.metadata == {"key": "value"}


class TestAgentCompositionRequest:
    """Test AgentCompositionRequest model validation and behavior."""

    def test_valid_agent_composition_request_creation(self):
        """Test creating valid AgentCompositionRequest instances."""
        request = AgentCompositionRequest(
            role="researcher",
            domains="async-programming,software-architecture",
            context="Complex analysis task requiring multi-domain expertise",
        )

        assert request.role == "researcher"
        assert request.domains == "async-programming,software-architecture"
        assert (
            request.context == "Complex analysis task requiring multi-domain expertise"
        )

    def test_agent_composition_request_minimal(self):
        """Test AgentCompositionRequest with only required field."""
        request = AgentCompositionRequest(role="architect")

        assert request.role == "architect"
        assert request.domains is None
        assert request.context is None

    def test_agent_composition_request_extra_fields_forbidden(self):
        """Test AgentCompositionRequest forbids extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            AgentCompositionRequest(role="researcher", extra_field="not_allowed")

        error_msg = str(exc_info.value)
        assert "extra_field" in error_msg
        assert "Extra inputs are not permitted" in error_msg

    def test_role_field_constraints(self):
        """Test role field constraints."""
        # Valid role length
        request = AgentCompositionRequest(role="researcher")
        assert request.role == "researcher"

        # Empty role should fail (min_length=1)
        with pytest.raises(ValidationError) as exc_info:
            AgentCompositionRequest(role="")

        error_msg = str(exc_info.value)
        assert "role" in error_msg
        assert "String should have at least 1 character" in error_msg

        # Role too long should fail (max_length=100)
        long_role = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            AgentCompositionRequest(role=long_role)

        error_msg = str(exc_info.value)
        assert "role" in error_msg
        assert "String should have at most 100 characters" in error_msg

    def test_domains_field_constraints(self):
        """Test domains field constraints."""
        # Valid domains length
        domains = "async-programming,software-architecture,database-design"
        request = AgentCompositionRequest(role="researcher", domains=domains)
        assert request.domains == domains

        # Domains too long should fail (max_length=500)
        long_domains = "a" * 501
        with pytest.raises(ValidationError) as exc_info:
            AgentCompositionRequest(role="researcher", domains=long_domains)

        error_msg = str(exc_info.value)
        assert "domains" in error_msg
        assert "String should have at most 500 characters" in error_msg

    def test_context_field_constraints(self):
        """Test context field constraints."""
        # Valid context length
        context = "This is a complex task requiring careful analysis" * 10  # ~500 chars
        request = AgentCompositionRequest(role="researcher", context=context)
        assert request.context == context

        # Context too long should fail (max_length=10000)
        long_context = "a" * 10001
        with pytest.raises(ValidationError) as exc_info:
            AgentCompositionRequest(role="researcher", context=long_context)

        error_msg = str(exc_info.value)
        assert "context" in error_msg
        assert "String should have at most 10000 characters" in error_msg

    def test_role_field_validator(self):
        """Test custom role field validator (if implemented)."""
        # This test would check if there's a custom validator for the role field
        # For now, we test basic string validation
        request = AgentCompositionRequest(role="valid_role_123")
        assert request.role == "valid_role_123"


class TestCompositionModelsIntegration:
    """Test integration between composition models."""

    def test_composer_request_to_response_flow(self):
        """Test typical flow from ComposerRequest to ComposerResponse."""
        # Create request
        request = ComposerRequest(
            role=AgentRole.RESEARCHER,
            domains="async-programming,performance-optimization",
            context="High-performance async system development",
        )

        # Create corresponding response
        domain_expertise = DomainExpertise(
            domain_id="async-programming",
            knowledge_patterns={"patterns": ["coroutines", "event_loops"]},
            specialized_tools=["asyncio", "uvloop"],
        )

        response = ComposerResponse(
            success=True,
            summary=f"Composed {request.role.value} agent with expertise in {request.domains}",
            agent_id=f"{request.role.value}_001",
            role=request.role.value,
            domains=request.domains.split(",") if request.domains else [],
            system_prompt=f"You are a {request.role.value} with context: {request.context}",
            domain_expertise=[domain_expertise],
            confidence=0.9,
        )

        # Verify correspondence
        assert response.role == request.role.value
        assert set(response.domains) == set(request.domains.split(","))
        assert request.context in response.system_prompt

    def test_complex_multi_domain_composition(self):
        """Test composition with multiple complex domains."""
        domains = "async-programming,distributed-systems,microservices-architecture,database-design"

        request = AgentCompositionRequest(
            role="architect",
            domains=domains,
            context="Design scalable microservices platform with async processing",
        )

        # Create expertise for each domain
        domain_expertises = []
        for domain in domains.split(","):
            expertise = DomainExpertise(
                domain_id=domain,
                knowledge_patterns={f"{domain}_patterns": ["pattern1", "pattern2"]},
                specialized_tools=[f"{domain}_tool1", f"{domain}_tool2"],
            )
            domain_expertises.append(expertise)

        response = ComposerResponse(
            success=True,
            summary="Multi-domain architect agent",
            agent_id="architect_multi_001",
            role=request.role,
            domains=request.domains.split(","),
            system_prompt="Advanced multi-domain architect",
            domain_expertise=domain_expertises,
            confidence=0.85,
        )

        assert len(response.domain_expertise) == 4
        assert all(exp.domain_id in domains for exp in response.domain_expertise)

    def test_composition_models_serialization_roundtrip(self):
        """Test complete serialization roundtrip for composition models."""
        # Create complex composition data
        domain_expertise = DomainExpertise(
            domain_id="async-programming",
            knowledge_patterns={"async_patterns": ["coroutines", "tasks"]},
            decision_rules={"rules": ["prefer_async_await"]},
            specialized_tools=["asyncio", "aiohttp"],
            confidence_thresholds={"min": 0.8, "target": 0.95},
        )

        original_response = ComposerResponse(
            success=True,
            summary="Comprehensive async programming researcher",
            agent_id="researcher_async_001",
            role="researcher",
            domains=["async-programming", "performance-optimization"],
            system_prompt="Expert async programming researcher with performance focus",
            capabilities=["research", "analysis", "benchmarking"],
            tools=["profiler", "analyzer", "documenter"],
            domain_expertise=[domain_expertise],
            confidence=0.92,
            error=None,
        )

        # JSON serialization roundtrip
        json_data = original_response.model_dump_json()
        restored_response = ComposerResponse.model_validate_json(json_data)

        assert restored_response == original_response
        assert len(restored_response.domain_expertise) == 1
        assert restored_response.domain_expertise[0].domain_id == "async-programming"
        assert restored_response.domain_expertise[0].specialized_tools == [
            "asyncio",
            "aiohttp",
        ]

    def test_error_handling_in_composition_models(self):
        """Test error handling scenarios in composition models."""
        # Test ComposerResponse with error
        error_response = ComposerResponse(
            success=False,
            summary="Composition failed due to invalid domain",
            agent_id="failed_001",
            role="researcher",
            system_prompt="Fallback prompt",
            confidence=0.0,
            error="Domain 'invalid-domain' not recognized in expertise catalog",
        )

        assert error_response.success is False
        assert error_response.confidence == 0.0
        assert "invalid-domain" in error_response.error

        # Test serialization of error response
        serialized = error_response.model_dump()
        assert serialized["success"] is False
        assert serialized["error"] is not None

        restored = ComposerResponse.model_validate(serialized)
        assert restored.success is False
        assert restored.error == error_response.error
