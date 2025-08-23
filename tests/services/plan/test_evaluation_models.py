"""Pydantic model validation tests for planning service models.

This module provides comprehensive validation of all Pydantic models used in the
planning service including:
- OrchestrationEvaluation model constraint validation
- PlannerRequest/Response model validation
- AgentRecommendation model validation
- Enum validation for complexity levels and workflow patterns
- Data type validation and constraint enforcement
- Serialization/deserialization validation
- Edge case handling for model validation

Ensures models maintain data integrity and validation constraints.
"""

import json
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from khive.services.plan.models import OrchestrationEvaluation
from khive.services.plan.parts import (AgentRecommendation, ComplexityLevel,
                                       PlannerRequest, PlannerResponse,
                                       QualityGate, WorkflowPattern)
from khive.services.plan.planner_service import ComplexityTier


@pytest.mark.unit
class TestOrchestrationEvaluationModel:
    """Test OrchestrationEvaluation model validation."""

    @pytest.fixture
    def valid_evaluation_data(self):
        """Valid data for OrchestrationEvaluation."""
        return {
            "complexity_tier": ComplexityTier.MEDIUM,
            "agent_count": 4,
            "recommended_roles": ["researcher", "architect", "implementer", "reviewer"],
            "workflow_pattern": WorkflowPattern.PARALLEL,
            "confidence_score": 0.85,
            "reasoning": "OAuth2 implementation requires multiple specialized agents",
            "estimated_duration": 120,
            "quality_gate": QualityGate.THOROUGH,
        }

    def test_valid_model_creation(self, valid_evaluation_data):
        """Test creating valid OrchestrationEvaluation."""
        evaluation = OrchestrationEvaluation(**valid_evaluation_data)

        assert evaluation.complexity_tier == ComplexityTier.MEDIUM
        assert evaluation.agent_count == 4
        assert len(evaluation.recommended_roles) == 4
        assert evaluation.workflow_pattern == WorkflowPattern.PARALLEL
        assert evaluation.confidence_score == 0.85
        assert evaluation.reasoning == valid_evaluation_data["reasoning"]
        assert evaluation.estimated_duration == 120
        assert evaluation.quality_gate == QualityGate.THOROUGH

    def test_confidence_score_constraints(self, valid_evaluation_data):
        """Test confidence score validation constraints."""
        # Test valid range
        for score in [0.0, 0.5, 1.0]:
            data = {**valid_evaluation_data, "confidence_score": score}
            evaluation = OrchestrationEvaluation(**data)
            assert evaluation.confidence_score == score

        # Test invalid ranges
        for invalid_score in [-0.1, 1.1, 2.0]:
            data = {**valid_evaluation_data, "confidence_score": invalid_score}
            with pytest.raises(ValidationError) as exc_info:
                OrchestrationEvaluation(**data)
            assert "confidence_score" in str(exc_info.value)

    def test_agent_count_constraints(self, valid_evaluation_data):
        """Test agent count validation constraints."""
        # Test valid ranges
        for count in [1, 6, 12]:
            data = {**valid_evaluation_data, "agent_count": count}
            evaluation = OrchestrationEvaluation(**data)
            assert evaluation.agent_count == count

        # Test invalid ranges
        for invalid_count in [0, -1, 13, 20]:
            data = {**valid_evaluation_data, "agent_count": invalid_count}
            with pytest.raises(ValidationError) as exc_info:
                OrchestrationEvaluation(**data)
            assert "agent_count" in str(exc_info.value)

    def test_recommended_roles_validation(self, valid_evaluation_data):
        """Test recommended roles list validation."""
        # Test valid role lists
        valid_roles = [
            ["researcher"],
            ["researcher", "implementer"],
            ["researcher", "architect", "implementer", "reviewer", "tester"],
        ]

        for roles in valid_roles:
            data = {**valid_evaluation_data, "recommended_roles": roles}
            evaluation = OrchestrationEvaluation(**data)
            assert evaluation.recommended_roles == roles

        # Test empty list (should be invalid)
        data = {**valid_evaluation_data, "recommended_roles": []}
        with pytest.raises(ValidationError):
            OrchestrationEvaluation(**data)

    def test_enum_validation(self, valid_evaluation_data):
        """Test enum field validation."""
        # Test invalid complexity tier
        data = {**valid_evaluation_data, "complexity_tier": "invalid_tier"}
        with pytest.raises(ValidationError):
            OrchestrationEvaluation(**data)

        # Test invalid workflow pattern
        data = {**valid_evaluation_data, "workflow_pattern": "invalid_pattern"}
        with pytest.raises(ValidationError):
            OrchestrationEvaluation(**data)

        # Test invalid quality gate
        data = {**valid_evaluation_data, "quality_gate": "invalid_gate"}
        with pytest.raises(ValidationError):
            OrchestrationEvaluation(**data)


@pytest.mark.unit
class TestPlannerRequestModel:
    """Test PlannerRequest model validation."""

    @pytest.fixture
    def valid_request_data(self):
        """Valid data for PlannerRequest."""
        return {
            "task_description": "Implement user authentication with OAuth2",
            "session_id": str(uuid4()),
            "priority_level": "high",
            "context": {"project": "web-app", "framework": "FastAPI"},
            "constraints": ["security-first", "scalable"],
            "deadline": datetime.now() + timedelta(days=7),
        }

    def test_valid_request_creation(self, valid_request_data):
        """Test creating valid PlannerRequest."""
        request = PlannerRequest(**valid_request_data)

        assert request.task_description == valid_request_data["task_description"]
        assert request.session_id == valid_request_data["session_id"]
        assert request.priority_level == "high"
        assert request.context == valid_request_data["context"]
        assert request.constraints == valid_request_data["constraints"]
        assert isinstance(request.deadline, datetime)

    def test_required_fields_validation(self):
        """Test required field validation."""
        # Test missing task_description
        with pytest.raises(ValidationError) as exc_info:
            PlannerRequest(session_id=str(uuid4()))
        assert "task_description" in str(exc_info.value)

        # Test missing session_id
        with pytest.raises(ValidationError) as exc_info:
            PlannerRequest(task_description="Test task")
        assert "session_id" in str(exc_info.value)

    def test_task_description_constraints(self, valid_request_data):
        """Test task description validation constraints."""
        # Test minimum length
        short_task = "fix"
        data = {**valid_request_data, "task_description": short_task}
        with pytest.raises(ValidationError) as exc_info:
            PlannerRequest(**data)
        assert "task_description" in str(exc_info.value)

        # Test maximum length
        long_task = "x" * 10001  # Over 10k characters
        data = {**valid_request_data, "task_description": long_task}
        with pytest.raises(ValidationError) as exc_info:
            PlannerRequest(**data)
        assert "task_description" in str(exc_info.value)

        # Test valid length
        valid_task = "Implement a comprehensive user authentication system"
        data = {**valid_request_data, "task_description": valid_task}
        request = PlannerRequest(**data)
        assert request.task_description == valid_task

    def test_session_id_format(self, valid_request_data):
        """Test session ID format validation."""
        # Test valid UUID format
        valid_uuid = str(uuid4())
        data = {**valid_request_data, "session_id": valid_uuid}
        request = PlannerRequest(**data)
        assert request.session_id == valid_uuid

        # Test invalid formats
        invalid_ids = ["not-a-uuid", "12345", ""]
        for invalid_id in invalid_ids:
            data = {**valid_request_data, "session_id": invalid_id}
            with pytest.raises(ValidationError):
                PlannerRequest(**data)

    def test_priority_level_validation(self, valid_request_data):
        """Test priority level validation."""
        valid_priorities = ["low", "medium", "high", "critical"]
        for priority in valid_priorities:
            data = {**valid_request_data, "priority_level": priority}
            request = PlannerRequest(**data)
            assert request.priority_level == priority

        # Test invalid priority
        data = {**valid_request_data, "priority_level": "invalid"}
        with pytest.raises(ValidationError):
            PlannerRequest(**data)


@pytest.mark.unit
class TestPlannerResponseModel:
    """Test PlannerResponse model validation."""

    @pytest.fixture
    def valid_response_data(self):
        """Valid data for PlannerResponse."""
        return {
            "session_id": str(uuid4()),
            "complexity_level": ComplexityLevel.MEDIUM,
            "agent_recommendations": [
                {
                    "role": "researcher",
                    "domain": "software-architecture",
                    "priority": 1,
                    "reasoning": "Research OAuth2 specifications",
                },
                {
                    "role": "implementer",
                    "domain": "backend-development",
                    "priority": 2,
                    "reasoning": "Implement authentication logic",
                },
            ],
            "workflow_pattern": WorkflowPattern.SEQUENTIAL,
            "estimated_duration": 240,
            "confidence_score": 0.85,
            "quality_gate": QualityGate.THOROUGH,
            "task_phases": [
                {
                    "phase_name": "research",
                    "description": "Research OAuth2 standards",
                    "estimated_hours": 8,
                },
                {
                    "phase_name": "implementation",
                    "description": "Implement authentication system",
                    "estimated_hours": 32,
                },
            ],
        }

    def test_valid_response_creation(self, valid_response_data):
        """Test creating valid PlannerResponse."""
        response = PlannerResponse(**valid_response_data)

        assert response.complexity_level == ComplexityLevel.MEDIUM
        assert len(response.agent_recommendations) == 2
        assert response.workflow_pattern == WorkflowPattern.SEQUENTIAL
        assert response.estimated_duration == 240
        assert response.confidence_score == 0.85
        assert len(response.task_phases) == 2

    def test_agent_recommendations_validation(self, valid_response_data):
        """Test agent recommendations validation."""
        # Test empty recommendations (should be invalid)
        data = {**valid_response_data, "agent_recommendations": []}
        with pytest.raises(ValidationError):
            PlannerResponse(**data)

        # Test maximum recommendations
        max_recommendations = []
        for i in range(13):  # Over efficiency cliff of 12
            max_recommendations.append({
                "role": "researcher",
                "domain": "software-architecture",
                "priority": i + 1,
                "reasoning": f"Agent {i + 1}",
            })

        data = {**valid_response_data, "agent_recommendations": max_recommendations}
        with pytest.raises(ValidationError):
            PlannerResponse(**data)


@pytest.mark.unit
class TestAgentRecommendationModel:
    """Test AgentRecommendation model validation."""

    @pytest.fixture
    def valid_recommendation_data(self):
        """Valid data for AgentRecommendation."""
        return {
            "role": "architect",
            "domain": "distributed-systems",
            "priority": 1,
            "reasoning": "Design scalable architecture",
            "estimated_hours": 16,
            "dependencies": ["researcher"],
            "deliverables": ["architecture_diagram.md", "component_spec.md"],
        }

    def test_valid_recommendation_creation(self, valid_recommendation_data):
        """Test creating valid AgentRecommendation."""
        rec = AgentRecommendation(**valid_recommendation_data)

        assert rec.role == "architect"
        assert rec.domain == "distributed-systems"
        assert rec.priority == 1
        assert rec.reasoning == valid_recommendation_data["reasoning"]
        assert rec.estimated_hours == 16
        assert rec.dependencies == ["researcher"]
        assert len(rec.deliverables) == 2

    def test_priority_validation(self, valid_recommendation_data):
        """Test priority field validation."""
        # Test valid priorities
        for priority in [1, 2, 5, 12]:
            data = {**valid_recommendation_data, "priority": priority}
            rec = AgentRecommendation(**data)
            assert rec.priority == priority

        # Test invalid priorities
        for invalid_priority in [0, -1, 13, 20]:
            data = {**valid_recommendation_data, "priority": invalid_priority}
            with pytest.raises(ValidationError):
                AgentRecommendation(**data)

    def test_role_domain_validation(self, valid_recommendation_data):
        """Test role and domain validation."""
        # Valid roles
        valid_roles = ["researcher", "architect", "implementer", "reviewer", "tester"]
        for role in valid_roles:
            data = {**valid_recommendation_data, "role": role}
            rec = AgentRecommendation(**data)
            assert rec.role == role

        # Invalid role
        data = {**valid_recommendation_data, "role": "invalid_role"}
        with pytest.raises(ValidationError):
            AgentRecommendation(**data)

    def test_estimated_hours_validation(self, valid_recommendation_data):
        """Test estimated hours validation."""
        # Valid hours
        for hours in [1, 8, 40, 160]:
            data = {**valid_recommendation_data, "estimated_hours": hours}
            rec = AgentRecommendation(**data)
            assert rec.estimated_hours == hours

        # Invalid hours
        for invalid_hours in [0, -5, 200]:
            data = {**valid_recommendation_data, "estimated_hours": invalid_hours}
            with pytest.raises(ValidationError):
                AgentRecommendation(**data)


@pytest.mark.unit
class TestEnumValidation:
    """Test enum validation for all planning service enums."""

    def test_complexity_level_enum(self):
        """Test ComplexityLevel enum validation."""
        # Test all valid values
        valid_levels = [
            ComplexityLevel.SIMPLE,
            ComplexityLevel.MEDIUM,
            ComplexityLevel.COMPLEX,
            ComplexityLevel.VERY_COMPLEX,
        ]

        for level in valid_levels:
            assert level.value in ["simple", "medium", "complex", "very_complex"]

    def test_workflow_pattern_enum(self):
        """Test WorkflowPattern enum validation."""
        valid_patterns = [
            WorkflowPattern.SEQUENTIAL,
            WorkflowPattern.PARALLEL,
            WorkflowPattern.HYBRID,
        ]

        for pattern in valid_patterns:
            assert pattern.value in ["sequential", "parallel", "hybrid"]

    def test_quality_gate_enum(self):
        """Test QualityGate enum validation."""
        valid_gates = [QualityGate.BASIC, QualityGate.THOROUGH, QualityGate.CRITICAL]

        for gate in valid_gates:
            assert gate.value in ["basic", "thorough", "critical"]

    def test_complexity_tier_enum(self):
        """Test ComplexityTier enum validation."""
        valid_tiers = [
            ComplexityTier.SIMPLE,
            ComplexityTier.MEDIUM,
            ComplexityTier.COMPLEX,
            ComplexityTier.VERY_COMPLEX,
        ]

        for tier in valid_tiers:
            assert tier.value in ["simple", "medium", "complex", "very_complex"]


@pytest.mark.unit
class TestModelSerialization:
    """Test model serialization and deserialization."""

    @pytest.fixture
    def complex_evaluation(self):
        """Complex evaluation for serialization testing."""
        return OrchestrationEvaluation(
            complexity_tier=ComplexityTier.COMPLEX,
            agent_count=6,
            recommended_roles=[
                "researcher",
                "architect",
                "implementer",
                "reviewer",
                "tester",
                "auditor",
            ],
            workflow_pattern=WorkflowPattern.HYBRID,
            confidence_score=0.78,
            reasoning="Complex microservices architecture requiring multiple specialized roles",
            estimated_duration=480,
            quality_gate=QualityGate.CRITICAL,
        )

    def test_model_to_dict_serialization(self, complex_evaluation):
        """Test model conversion to dictionary."""
        data = complex_evaluation.model_dump()

        assert isinstance(data, dict)
        assert data["complexity_tier"] == "complex"
        assert data["agent_count"] == 6
        assert len(data["recommended_roles"]) == 6
        assert data["workflow_pattern"] == "hybrid"
        assert data["confidence_score"] == 0.78
        assert data["quality_gate"] == "critical"

    def test_model_to_json_serialization(self, complex_evaluation):
        """Test model conversion to JSON."""
        json_str = complex_evaluation.model_dump_json()

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["complexity_tier"] == "complex"
        assert data["agent_count"] == 6

    def test_model_from_dict_deserialization(self, complex_evaluation):
        """Test model creation from dictionary."""
        data = complex_evaluation.model_dump()
        restored = OrchestrationEvaluation(**data)

        assert restored.complexity_tier == complex_evaluation.complexity_tier
        assert restored.agent_count == complex_evaluation.agent_count
        assert restored.recommended_roles == complex_evaluation.recommended_roles
        assert restored.confidence_score == complex_evaluation.confidence_score

    def test_model_from_json_deserialization(self, complex_evaluation):
        """Test model creation from JSON."""
        json_str = complex_evaluation.model_dump_json()
        data = json.loads(json_str)
        restored = OrchestrationEvaluation(**data)

        assert restored.complexity_tier == complex_evaluation.complexity_tier
        assert restored.agent_count == complex_evaluation.agent_count


@pytest.mark.unit
class TestConstraintValidation:
    """Test comprehensive constraint validation across models."""

    def test_cross_model_consistency(self):
        """Test consistency between related models."""
        # Create a PlannerResponse with matching agent count
        recommendations = [
            AgentRecommendation(
                role="researcher",
                domain="software-architecture",
                priority=1,
                reasoning="Research requirements",
            ),
            AgentRecommendation(
                role="implementer",
                domain="backend-development",
                priority=2,
                reasoning="Implement solution",
            ),
        ]

        response = PlannerResponse(
            session_id=str(uuid4()),
            complexity_level=ComplexityLevel.MEDIUM,
            agent_recommendations=recommendations,
            workflow_pattern=WorkflowPattern.SEQUENTIAL,
            estimated_duration=120,
            confidence_score=0.85,
            quality_gate=QualityGate.THOROUGH,
        )

        # Verify consistency
        assert len(response.agent_recommendations) == 2
        assert all(rec.priority <= len(recommendations) for rec in recommendations)

    def test_business_rule_validation(self):
        """Test business rule validation across models."""
        # Test that high complexity requires more agents
        high_complexity_data = {
            "complexity_tier": ComplexityTier.VERY_COMPLEX,
            "agent_count": 1,  # Too few for very complex
            "recommended_roles": ["implementer"],
            "workflow_pattern": WorkflowPattern.SEQUENTIAL,
            "confidence_score": 0.5,
            "reasoning": "Very complex with minimal resources",
        }

        # This should be allowed by the model but caught by business logic
        evaluation = OrchestrationEvaluation(**high_complexity_data)
        assert evaluation.agent_count == 1  # Model allows it

        # Business logic should flag this as inconsistent
        assert evaluation.complexity_tier == ComplexityTier.VERY_COMPLEX
        assert evaluation.agent_count < 7  # Below recommended minimum for very complex
