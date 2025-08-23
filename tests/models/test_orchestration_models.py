"""Comprehensive tests for orchestration Pydantic models."""


import pytest
from lionagi.fields import Instruct
from pydantic import ValidationError

from khive.prompts import AgentRole
from khive.services.composition.parts import ComposerRequest
from khive.services.orchestration.parts import AgentRequest, OrchestrationPlan
from khive.services.plan.parts import (AgentRecommendation, ComplexityLevel,
                                       PlannerRequest, PlannerResponse,
                                       QualityGate, TaskPhase, WorkflowPattern)


class TestAgentRequest:
    """Test AgentRequest model validation and behavior."""

    def test_valid_agent_request_creation(self):
        """Test creating valid AgentRequest instances."""
        instruct = Instruct(instruction="Test instruction")
        composer_request = ComposerRequest(role=AgentRole.RESEARCHER)

        agent_request = AgentRequest(
            instruct=instruct,
            compose_request=composer_request,
            analysis_type="RequirementsAnalysis",
        )

        assert agent_request.instruct == instruct
        assert agent_request.compose_request == composer_request
        assert agent_request.analysis_type == "RequirementsAnalysis"

    def test_agent_request_optional_analysis_type(self):
        """Test AgentRequest with optional analysis_type."""
        instruct = Instruct(instruction="Test instruction")
        composer_request = ComposerRequest(role=AgentRole.RESEARCHER)

        agent_request = AgentRequest(
            instruct=instruct, compose_request=composer_request
        )

        assert agent_request.analysis_type is None

    @pytest.mark.parametrize(
        "analysis_type",
        [
            "RequirementsAnalysis",
            "CodeContextAnalysis",
            "IntegrationStrategy",
            "FeatureImplementation",
            "RequirementValidation",
            "DocumentationPackage",
            "TestStrategy",
            "WorkSynthesis",
        ],
    )
    def test_valid_deliverable_types(self, analysis_type):
        """Test all valid DeliverableType values."""
        instruct = Instruct(instruction="Test instruction")
        composer_request = ComposerRequest(role=AgentRole.RESEARCHER)

        agent_request = AgentRequest(
            instruct=instruct,
            compose_request=composer_request,
            analysis_type=analysis_type,
        )

        assert agent_request.analysis_type == analysis_type

    def test_agent_request_validation_errors(self):
        """Test validation errors for AgentRequest."""
        composer_request = ComposerRequest(role=AgentRole.RESEARCHER)

        # Missing required instruct field
        with pytest.raises(ValidationError) as exc_info:
            AgentRequest(compose_request=composer_request)

        error_msg = str(exc_info.value)
        assert "instruct" in error_msg
        assert "Field required" in error_msg

    def test_agent_request_serialization(self):
        """Test AgentRequest serialization and deserialization."""
        instruct = Instruct(instruction="Test instruction", guidance="Test guidance")
        composer_request = ComposerRequest(
            role=AgentRole.RESEARCHER,
            domains="async-programming",
            context="Test context",
        )

        original = AgentRequest(
            instruct=instruct,
            compose_request=composer_request,
            analysis_type="RequirementsAnalysis",
        )

        # Test serialization
        data = original.model_dump()
        assert "instruct" in data
        assert "compose_request" in data
        assert "analysis_type" in data

        # Test deserialization
        restored = AgentRequest.model_validate(data)
        assert restored == original


class TestOrchestrationPlan:
    """Test OrchestrationPlan model validation and behavior."""

    def test_valid_orchestration_plan_creation(self):
        """Test creating valid OrchestrationPlan instances."""
        instruct = Instruct(instruction="Research async patterns")
        composer_request = ComposerRequest(
            role=AgentRole.RESEARCHER, domains="async-programming"
        )
        agent_request = AgentRequest(
            instruct=instruct, compose_request=composer_request
        )

        plan = OrchestrationPlan(
            common_background="Async system development project",
            agent_requests=[agent_request],
            execution_strategy="concurrent",
        )

        assert plan.common_background == "Async system development project"
        assert len(plan.agent_requests) == 1
        assert plan.execution_strategy == "concurrent"

    def test_orchestration_plan_default_execution_strategy(self):
        """Test default execution strategy is concurrent."""
        instruct = Instruct(instruction="Test instruction")
        composer_request = ComposerRequest(role=AgentRole.RESEARCHER)
        agent_request = AgentRequest(
            instruct=instruct, compose_request=composer_request
        )

        plan = OrchestrationPlan(
            common_background="Test background", agent_requests=[agent_request]
        )

        assert plan.execution_strategy == "concurrent"

    @pytest.mark.parametrize("execution_strategy", ["sequential", "concurrent"])
    def test_valid_execution_strategies(self, execution_strategy):
        """Test valid execution strategy values."""
        instruct = Instruct(instruction="Test instruction")
        composer_request = ComposerRequest(role=AgentRole.RESEARCHER)
        agent_request = AgentRequest(
            instruct=instruct, compose_request=composer_request
        )

        plan = OrchestrationPlan(
            common_background="Test background",
            agent_requests=[agent_request],
            execution_strategy=execution_strategy,
        )

        assert plan.execution_strategy == execution_strategy

    def test_invalid_execution_strategy(self):
        """Test invalid execution strategy values."""
        instruct = Instruct(instruction="Test instruction")
        composer_request = ComposerRequest(role=AgentRole.RESEARCHER)
        agent_request = AgentRequest(
            instruct=instruct, compose_request=composer_request
        )

        with pytest.raises(ValidationError) as exc_info:
            OrchestrationPlan(
                common_background="Test background",
                agent_requests=[agent_request],
                execution_strategy="invalid_strategy",
            )

        error_msg = str(exc_info.value)
        assert "execution_strategy" in error_msg

    def test_multiple_agent_requests(self):
        """Test OrchestrationPlan with multiple agent requests."""
        agent_requests = []
        for role in [AgentRole.RESEARCHER, AgentRole.ARCHITECT, AgentRole.IMPLEMENTER]:
            instruct = Instruct(instruction=f"Task for {role.value}")
            composer_request = ComposerRequest(role=role)
            agent_request = AgentRequest(
                instruct=instruct, compose_request=composer_request
            )
            agent_requests.append(agent_request)

        plan = OrchestrationPlan(
            common_background="Multi-agent project", agent_requests=agent_requests
        )

        assert len(plan.agent_requests) == 3
        assert all(isinstance(req, AgentRequest) for req in plan.agent_requests)

    def test_empty_agent_requests_list(self):
        """Test OrchestrationPlan with empty agent requests."""
        plan = OrchestrationPlan(common_background="Test background", agent_requests=[])

        assert len(plan.agent_requests) == 0

    def test_orchestration_plan_validation_errors(self):
        """Test validation errors for OrchestrationPlan."""
        instruct = Instruct(instruction="Test instruction")
        composer_request = ComposerRequest(role=AgentRole.RESEARCHER)
        agent_request = AgentRequest(
            instruct=instruct, compose_request=composer_request
        )

        # Missing required common_background
        with pytest.raises(ValidationError) as exc_info:
            OrchestrationPlan(agent_requests=[agent_request])

        error_msg = str(exc_info.value)
        assert "common_background" in error_msg
        assert "Field required" in error_msg


class TestPlannerRequest:
    """Test PlannerRequest model validation and behavior."""

    def test_valid_planner_request_creation(self):
        """Test creating valid PlannerRequest instances."""
        request = PlannerRequest(
            task_description="Implement async queue processing",
            context="High-throughput system with Redis backend",
            time_budget_seconds=60.0,
        )

        assert request.task_description == "Implement async queue processing"
        assert request.context == "High-throughput system with Redis backend"
        assert request.time_budget_seconds == 60.0

    def test_planner_request_defaults(self):
        """Test PlannerRequest default values."""
        request = PlannerRequest(task_description="Test task")

        assert request.task_description == "Test task"
        assert request.context is None
        assert request.time_budget_seconds == 30.0

    def test_planner_request_extra_fields_forbidden(self):
        """Test extra fields are forbidden in PlannerRequest."""
        with pytest.raises(ValidationError) as exc_info:
            PlannerRequest(task_description="Test task", extra_field="not_allowed")

        error_msg = str(exc_info.value)
        assert "extra_field" in error_msg
        assert "Extra inputs are not permitted" in error_msg

    def test_planner_request_validation_errors(self):
        """Test validation errors for PlannerRequest."""
        # Missing required task_description
        with pytest.raises(ValidationError) as exc_info:
            PlannerRequest()

        error_msg = str(exc_info.value)
        assert "task_description" in error_msg
        assert "Field required" in error_msg

    def test_time_budget_type_validation(self):
        """Test time_budget_seconds type validation."""
        # Valid float
        request1 = PlannerRequest(task_description="Test", time_budget_seconds=45.5)
        assert request1.time_budget_seconds == 45.5

        # Valid int (should coerce to float)
        request2 = PlannerRequest(task_description="Test", time_budget_seconds=60)
        assert request2.time_budget_seconds == 60.0

        # Invalid string
        with pytest.raises(ValidationError):
            PlannerRequest(task_description="Test", time_budget_seconds="invalid")


class TestAgentRecommendation:
    """Test AgentRecommendation model validation and behavior."""

    def test_valid_agent_recommendation_creation(self):
        """Test creating valid AgentRecommendation instances."""
        recommendation = AgentRecommendation(
            role="researcher",
            domain="async-programming",
            priority=0.9,
            reasoning="Expert in async patterns and concurrency",
        )

        assert recommendation.role == "researcher"
        assert recommendation.domain == "async-programming"
        assert recommendation.priority == 0.9
        assert recommendation.reasoning == "Expert in async patterns and concurrency"

    def test_agent_recommendation_validation_errors(self):
        """Test validation errors for AgentRecommendation."""
        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            AgentRecommendation()

        error_msg = str(exc_info.value)
        assert "Field required" in error_msg

    def test_priority_boundary_values(self):
        """Test priority field boundary values."""
        # Test valid priority values
        valid_priorities = [
            0.0,
            0.1,
            0.5,
            0.9,
            1.0,
            1.5,
        ]  # Assuming no upper bound constraint

        for priority in valid_priorities:
            recommendation = AgentRecommendation(
                role="researcher",
                domain="async-programming",
                priority=priority,
                reasoning="Test reasoning",
            )
            assert recommendation.priority == priority


class TestTaskPhase:
    """Test TaskPhase model validation and behavior."""

    def test_valid_task_phase_creation(self):
        """Test creating valid TaskPhase instances."""
        agent_rec = AgentRecommendation(
            role="researcher",
            domain="async-programming",
            priority=0.9,
            reasoning="Expert in async patterns",
        )

        phase = TaskPhase(
            name="Research Phase",
            description="Research async programming patterns",
            agents=[agent_rec],
            dependencies=["initialization"],
            quality_gate=QualityGate.THOROUGH,
            coordination_pattern=WorkflowPattern.PARALLEL,
        )

        assert phase.name == "Research Phase"
        assert phase.description == "Research async programming patterns"
        assert len(phase.agents) == 1
        assert phase.dependencies == ["initialization"]
        assert phase.quality_gate == QualityGate.THOROUGH
        assert phase.coordination_pattern == WorkflowPattern.PARALLEL

    def test_task_phase_default_dependencies(self):
        """Test TaskPhase with default empty dependencies."""
        agent_rec = AgentRecommendation(
            role="researcher",
            domain="async-programming",
            priority=0.9,
            reasoning="Expert in async patterns",
        )

        phase = TaskPhase(
            name="Research Phase",
            description="Research async programming patterns",
            agents=[agent_rec],
            quality_gate=QualityGate.BASIC,
            coordination_pattern=WorkflowPattern.SEQUENTIAL,
        )

        assert phase.dependencies == []

    @pytest.mark.parametrize(
        "quality_gate", [QualityGate.BASIC, QualityGate.THOROUGH, QualityGate.CRITICAL]
    )
    def test_valid_quality_gates(self, quality_gate):
        """Test all valid QualityGate values."""
        agent_rec = AgentRecommendation(
            role="researcher",
            domain="async-programming",
            priority=0.9,
            reasoning="Test",
        )

        phase = TaskPhase(
            name="Test Phase",
            description="Test phase",
            agents=[agent_rec],
            quality_gate=quality_gate,
            coordination_pattern=WorkflowPattern.PARALLEL,
        )

        assert phase.quality_gate == quality_gate

    @pytest.mark.parametrize(
        "coordination_pattern",
        [WorkflowPattern.PARALLEL, WorkflowPattern.SEQUENTIAL, WorkflowPattern.HYBRID],
    )
    def test_valid_coordination_patterns(self, coordination_pattern):
        """Test all valid WorkflowPattern values."""
        agent_rec = AgentRecommendation(
            role="researcher",
            domain="async-programming",
            priority=0.9,
            reasoning="Test",
        )

        phase = TaskPhase(
            name="Test Phase",
            description="Test phase",
            agents=[agent_rec],
            quality_gate=QualityGate.BASIC,
            coordination_pattern=coordination_pattern,
        )

        assert phase.coordination_pattern == coordination_pattern


class TestPlannerResponse:
    """Test PlannerResponse model validation and behavior."""

    def test_valid_planner_response_creation(self):
        """Test creating valid PlannerResponse instances."""
        agent_rec = AgentRecommendation(
            role="researcher",
            domain="async-programming",
            priority=0.9,
            reasoning="Expert",
        )
        phase = TaskPhase(
            name="Research",
            description="Research phase",
            agents=[agent_rec],
            quality_gate=QualityGate.BASIC,
            coordination_pattern=WorkflowPattern.PARALLEL,
        )

        response = PlannerResponse(
            success=True,
            summary="Comprehensive async processing plan",
            complexity=ComplexityLevel.MEDIUM,
            recommended_agents=3,
            phases=[phase],
            spawn_commands=["khive compose researcher -d async-programming"],
            session_id="session_123",
            confidence=0.9,
        )

        assert response.success is True
        assert response.summary == "Comprehensive async processing plan"
        assert response.complexity == ComplexityLevel.MEDIUM
        assert response.recommended_agents == 3
        assert len(response.phases) == 1
        assert len(response.spawn_commands) == 1
        assert response.session_id == "session_123"
        assert response.confidence == 0.9

    def test_planner_response_defaults(self):
        """Test PlannerResponse default values."""
        response = PlannerResponse(
            success=True,
            summary="Test summary",
            complexity=ComplexityLevel.SIMPLE,
            recommended_agents=1,
            confidence=0.8,
        )

        assert response.phases == []
        assert response.spawn_commands == []
        assert response.session_id is None
        assert response.error is None

    @pytest.mark.parametrize(
        "complexity",
        [
            ComplexityLevel.SIMPLE,
            ComplexityLevel.MEDIUM,
            ComplexityLevel.COMPLEX,
            ComplexityLevel.VERY_COMPLEX,
        ],
    )
    def test_valid_complexity_levels(self, complexity):
        """Test all valid ComplexityLevel values."""
        response = PlannerResponse(
            success=True,
            summary="Test summary",
            complexity=complexity,
            recommended_agents=1,
            confidence=0.8,
        )

        assert response.complexity == complexity

    def test_confidence_boundary_validation(self):
        """Test confidence field boundary validation."""
        # Valid confidence values
        valid_confidences = [0.0, 0.1, 0.5, 0.9, 1.0]

        for confidence in valid_confidences:
            response = PlannerResponse(
                success=True,
                summary="Test summary",
                complexity=ComplexityLevel.SIMPLE,
                recommended_agents=1,
                confidence=confidence,
            )
            assert response.confidence == confidence

        # Invalid confidence values
        invalid_confidences = [-0.1, 1.1, 2.0, -1.0]

        for confidence in invalid_confidences:
            with pytest.raises(ValidationError) as exc_info:
                PlannerResponse(
                    success=True,
                    summary="Test summary",
                    complexity=ComplexityLevel.SIMPLE,
                    recommended_agents=1,
                    confidence=confidence,
                )

            error_msg = str(exc_info.value)
            assert "confidence" in error_msg

    def test_planner_response_extra_fields_allowed(self):
        """Test PlannerResponse allows extra fields."""
        response = PlannerResponse(
            success=True,
            summary="Test summary",
            complexity=ComplexityLevel.SIMPLE,
            recommended_agents=1,
            confidence=0.8,
            extra_field="allowed",  # Should be allowed due to Config extra="allow"
        )

        # Extra field should be accessible
        assert hasattr(response, "extra_field")
        assert response.extra_field == "allowed"


class TestOrchestrationModelsSerialization:
    """Test serialization and deserialization of orchestration models."""

    def test_orchestration_models_json_roundtrip(self):
        """Test complete JSON serialization roundtrip for orchestration models."""
        # Create a complete orchestration plan
        instruct = Instruct(
            instruction="Research async patterns",
            guidance="Focus on modern patterns",
            context="Building high-performance system",
        )
        composer_request = ComposerRequest(
            role=AgentRole.RESEARCHER,
            domains="async-programming,software-architecture",
            context="Complex async research task",
        )
        agent_request = AgentRequest(
            instruct=instruct,
            compose_request=composer_request,
            analysis_type="RequirementsAnalysis",
        )

        original_plan = OrchestrationPlan(
            common_background="Comprehensive async system development",
            agent_requests=[agent_request],
            execution_strategy="concurrent",
        )

        # JSON serialization roundtrip
        json_data = original_plan.model_dump_json()
        restored_plan = OrchestrationPlan.model_validate_json(json_data)

        assert restored_plan == original_plan
        assert restored_plan.common_background == original_plan.common_background
        assert len(restored_plan.agent_requests) == len(original_plan.agent_requests)
        assert restored_plan.execution_strategy == original_plan.execution_strategy

    def test_complex_planner_response_serialization(self):
        """Test serialization of complex PlannerResponse with nested data."""
        agent_rec = AgentRecommendation(
            role="researcher",
            domain="async-programming",
            priority=0.95,
            reasoning="Deep expertise in async patterns and performance",
        )

        phase = TaskPhase(
            name="Analysis Phase",
            description="Comprehensive analysis of async requirements",
            agents=[agent_rec],
            dependencies=["initialization", "setup"],
            quality_gate=QualityGate.CRITICAL,
            coordination_pattern=WorkflowPattern.HYBRID,
        )

        original_response = PlannerResponse(
            success=True,
            summary="Multi-phase async system development plan",
            complexity=ComplexityLevel.VERY_COMPLEX,
            recommended_agents=5,
            phases=[phase],
            spawn_commands=[
                "khive compose researcher -d async-programming -c 'performance analysis'",
                "khive compose architect -d software-architecture -c 'system design'",
            ],
            session_id="complex_session_456",
            confidence=0.92,
            error=None,
        )

        # Test serialization
        serialized_data = original_response.model_dump()
        assert "phases" in serialized_data
        assert len(serialized_data["phases"]) == 1
        assert serialized_data["phases"][0]["name"] == "Analysis Phase"

        # Test deserialization
        restored_response = PlannerResponse.model_validate(serialized_data)
        assert restored_response == original_response
        assert len(restored_response.phases) == 1
        assert restored_response.phases[0].name == "Analysis Phase"
