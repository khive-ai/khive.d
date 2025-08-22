"""Validation patterns and utilities for Pydantic models in orchestration system.

This module provides:
- Comprehensive validation patterns for all orchestration Pydantic models
- Constraint testing utilities
- Model relationship validation
- Data integrity checking patterns
- Custom validators for domain-specific rules
"""

from typing import Any

import pytest
from khive.services.plan.models import OrchestrationEvaluation
from khive.services.plan.parts import (
    AgentRecommendation,
    PlannerRequest,
    PlannerResponse,
    TaskPhase,
)
from pydantic import BaseModel, ValidationError

# ============================================================================
# Base Validation Patterns
# ============================================================================


class BaseValidationPattern:
    """Base class for model validation patterns."""

    @staticmethod
    def assert_valid_model(model_class: type, data: dict[str, Any]) -> BaseModel:
        """Assert that data creates a valid model instance."""
        try:
            return model_class.model_validate(data)
        except ValidationError as e:
            pytest.fail(f"Model validation failed for {model_class.__name__}: {e}")

    @staticmethod
    def assert_invalid_model(
        model_class: type, data: dict[str, Any], expected_field: str | None = None
    ):
        """Assert that data creates an invalid model instance."""
        with pytest.raises(ValidationError) as exc_info:
            model_class.model_validate(data)

        if expected_field:
            error_fields = [error["loc"][0] for error in exc_info.value.errors()]
            assert expected_field in error_fields, (
                f"Expected validation error for field '{expected_field}', "
                f"but got errors for: {error_fields}"
            )

    @staticmethod
    def get_validation_errors(
        model_class: type, data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get validation errors without raising exception."""
        try:
            model_class.model_validate(data)
            return []
        except ValidationError as e:
            return e.errors()


# ============================================================================
# OrchestrationEvaluation Validation
# ============================================================================


class OrchestrationEvaluationValidator(BaseValidationPattern):
    """Validation patterns for OrchestrationEvaluation model."""

    VALID_COMPLEXITIES = ["simple", "medium", "complex", "very_complex"]
    VALID_WORKFLOW_PATTERNS = ["parallel", "sequential", "hybrid"]
    VALID_QUALITY_LEVELS = ["basic", "thorough", "critical"]

    MIN_AGENTS = 1
    MAX_AGENTS = 20
    MIN_ROUNDS = 1
    MAX_ROUNDS = 6
    MIN_CONFIDENCE = 0.0
    MAX_CONFIDENCE = 1.0

    # String length limits
    MAX_REASON_LENGTH = 200
    MAX_SUMMARY_LENGTH = 300
    MAX_ROLE_PRIORITIES = 10
    MAX_DOMAINS = 3
    MAX_RULES_APPLIED = 3

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid OrchestrationEvaluation data."""
        data = {
            "complexity": "medium",
            "complexity_reason": "Task involves multiple objectives",
            "total_agents": 5,
            "agent_reason": "Balanced team for comprehensive coverage",
            "rounds_needed": 2,
            "role_priorities": ["researcher", "analyst", "architect"],
            "primary_domains": ["distributed-systems"],
            "domain_reason": "Core technical domain",
            "workflow_pattern": "parallel",
            "workflow_reason": "Tasks can be executed concurrently",
            "quality_level": "thorough",
            "quality_reason": "Important system requiring validation",
            "rules_applied": ["complexity_assessment"],
            "confidence": 0.8,
            "summary": "Standard orchestration evaluation",
        }
        data.update(overrides)
        return data

    @classmethod
    def test_field_constraints(cls):
        """Test all field constraints for OrchestrationEvaluation."""

        # Test complexity field
        valid_data = cls.create_valid_data()

        for complexity in cls.VALID_COMPLEXITIES:
            data = cls.create_valid_data(complexity=complexity)
            cls.assert_valid_model(OrchestrationEvaluation, data)

        # Invalid complexity
        invalid_data = cls.create_valid_data(complexity="invalid")
        cls.assert_invalid_model(OrchestrationEvaluation, invalid_data, "complexity")

        # Test agent count bounds
        cls.assert_invalid_model(
            OrchestrationEvaluation,
            cls.create_valid_data(total_agents=0),
            "total_agents",
        )

        cls.assert_invalid_model(
            OrchestrationEvaluation,
            cls.create_valid_data(total_agents=25),
            "total_agents",
        )

        # Test confidence bounds
        cls.assert_invalid_model(
            OrchestrationEvaluation,
            cls.create_valid_data(confidence=-0.1),
            "confidence",
        )

        cls.assert_invalid_model(
            OrchestrationEvaluation, cls.create_valid_data(confidence=1.5), "confidence"
        )

        # Test rounds bounds
        cls.assert_invalid_model(
            OrchestrationEvaluation,
            cls.create_valid_data(rounds_needed=0),
            "rounds_needed",
        )

        cls.assert_invalid_model(
            OrchestrationEvaluation,
            cls.create_valid_data(rounds_needed=10),
            "rounds_needed",
        )

    @classmethod
    def test_string_length_constraints(cls):
        """Test string length constraints."""

        # Test complexity_reason length
        long_reason = "x" * (cls.MAX_REASON_LENGTH + 1)
        cls.assert_invalid_model(
            OrchestrationEvaluation,
            cls.create_valid_data(complexity_reason=long_reason),
            "complexity_reason",
        )

        # Test summary length
        long_summary = "x" * (cls.MAX_SUMMARY_LENGTH + 1)
        cls.assert_invalid_model(
            OrchestrationEvaluation,
            cls.create_valid_data(summary=long_summary),
            "summary",
        )

    @classmethod
    def test_list_constraints(cls):
        """Test list field constraints."""

        # Test role_priorities max length
        too_many_roles = ["role" + str(i) for i in range(cls.MAX_ROLE_PRIORITIES + 1)]
        cls.assert_invalid_model(
            OrchestrationEvaluation,
            cls.create_valid_data(role_priorities=too_many_roles),
            "role_priorities",
        )

        # Test primary_domains max length
        too_many_domains = ["domain" + str(i) for i in range(cls.MAX_DOMAINS + 1)]
        cls.assert_invalid_model(
            OrchestrationEvaluation,
            cls.create_valid_data(primary_domains=too_many_domains),
            "primary_domains",
        )

        # Test rules_applied max length
        too_many_rules = ["rule" + str(i) for i in range(cls.MAX_RULES_APPLIED + 1)]
        cls.assert_invalid_model(
            OrchestrationEvaluation,
            cls.create_valid_data(rules_applied=too_many_rules),
            "rules_applied",
        )

    @classmethod
    def test_workflow_pattern_constraints(cls):
        """Test workflow pattern constraints."""
        for pattern in cls.VALID_WORKFLOW_PATTERNS:
            data = cls.create_valid_data(workflow_pattern=pattern)
            cls.assert_valid_model(OrchestrationEvaluation, data)

        # Invalid pattern
        cls.assert_invalid_model(
            OrchestrationEvaluation,
            cls.create_valid_data(workflow_pattern="invalid"),
            "workflow_pattern",
        )

    @classmethod
    def test_quality_level_constraints(cls):
        """Test quality level constraints."""
        for level in cls.VALID_QUALITY_LEVELS:
            data = cls.create_valid_data(quality_level=level)
            cls.assert_valid_model(OrchestrationEvaluation, data)

        # Invalid level
        cls.assert_invalid_model(
            OrchestrationEvaluation,
            cls.create_valid_data(quality_level="invalid"),
            "quality_level",
        )


# ============================================================================
# PlannerRequest Validation
# ============================================================================


class PlannerRequestValidator(BaseValidationPattern):
    """Validation patterns for PlannerRequest model."""

    MIN_TIME_BUDGET = 0.1
    MAX_TIME_BUDGET = 3600.0

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid PlannerRequest data."""
        data = {
            "task_description": "Build a distributed system",
            "context": "High availability requirements",
            "time_budget_seconds": 300.0,
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        # Missing task_description
        cls.assert_invalid_model(
            PlannerRequest,
            {"context": "test", "time_budget_seconds": 300.0},
            "task_description",
        )

        # Valid minimal request
        cls.assert_valid_model(PlannerRequest, {"task_description": "test task"})

    @classmethod
    def test_time_budget_constraints(cls):
        """Test time budget constraints."""
        # Valid time budgets
        valid_budgets = [30.0, 300.0, 1800.0]
        for budget in valid_budgets:
            data = cls.create_valid_data(time_budget_seconds=budget)
            cls.assert_valid_model(PlannerRequest, data)

        # Test default value
        data = {"task_description": "test"}
        request = cls.assert_valid_model(PlannerRequest, data)
        assert request.time_budget_seconds == 30.0

    @classmethod
    def test_string_constraints(cls):
        """Test string field constraints."""
        # Empty task description should be invalid
        cls.assert_invalid_model(
            PlannerRequest,
            cls.create_valid_data(task_description=""),
            "task_description",
        )

        # Very long descriptions should be handled gracefully
        long_description = "x" * 10000
        data = cls.create_valid_data(task_description=long_description)
        # Should not fail validation but may be truncated by system
        cls.assert_valid_model(PlannerRequest, data)


# ============================================================================
# AgentRecommendation Validation
# ============================================================================


class AgentRecommendationValidator(BaseValidationPattern):
    """Validation patterns for AgentRecommendation model."""

    MIN_PRIORITY = 0.0
    MAX_PRIORITY = 1.0

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid AgentRecommendation data."""
        data = {
            "role": "researcher",
            "domain": "distributed-systems",
            "priority": 0.8,
            "reasoning": "Essential for understanding the problem domain",
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        required_fields = ["role", "domain", "priority", "reasoning"]

        for field in required_fields:
            incomplete_data = cls.create_valid_data()
            del incomplete_data[field]
            cls.assert_invalid_model(AgentRecommendation, incomplete_data, field)

    @classmethod
    def test_priority_constraints(cls):
        """Test priority field constraints."""
        # Valid priorities
        valid_priorities = [0.0, 0.5, 1.0]
        for priority in valid_priorities:
            data = cls.create_valid_data(priority=priority)
            cls.assert_valid_model(AgentRecommendation, data)

        # Invalid priorities
        invalid_priorities = [-0.1, 1.5, -1.0, 2.0]
        for priority in invalid_priorities:
            data = cls.create_valid_data(priority=priority)
            cls.assert_invalid_model(AgentRecommendation, data, "priority")

    @classmethod
    def test_role_domain_validation(cls):
        """Test role and domain string validation."""
        # Empty strings should be invalid
        cls.assert_invalid_model(
            AgentRecommendation, cls.create_valid_data(role=""), "role"
        )

        cls.assert_invalid_model(
            AgentRecommendation, cls.create_valid_data(domain=""), "domain"
        )

        # Valid role/domain combinations
        valid_combinations = [
            ("researcher", "distributed-systems"),
            ("architect", "software-architecture"),
            ("implementer", "frontend-development"),
            ("tester", "async-programming"),
        ]

        for role, domain in valid_combinations:
            data = cls.create_valid_data(role=role, domain=domain)
            cls.assert_valid_model(AgentRecommendation, data)


# ============================================================================
# TaskPhase Validation
# ============================================================================


class TaskPhaseValidator(BaseValidationPattern):
    """Validation patterns for TaskPhase model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid TaskPhase data."""
        data = {
            "name": "discovery_phase",
            "description": "Research and analyze requirements",
            "agents": [
                {
                    "role": "researcher",
                    "domain": "distributed-systems",
                    "priority": 1.0,
                    "reasoning": "Primary research role",
                }
            ],
            "dependencies": [],
            "quality_gate": "thorough",
            "coordination_pattern": "parallel",
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        required_fields = [
            "name",
            "description",
            "agents",
            "quality_gate",
            "coordination_pattern",
        ]

        for field in required_fields:
            incomplete_data = cls.create_valid_data()
            del incomplete_data[field]
            cls.assert_invalid_model(TaskPhase, incomplete_data, field)

    @classmethod
    def test_enum_constraints(cls):
        """Test enum field constraints."""
        # Valid quality gates
        valid_gates = ["basic", "thorough", "critical"]
        for gate in valid_gates:
            data = cls.create_valid_data(quality_gate=gate)
            cls.assert_valid_model(TaskPhase, data)

        # Invalid quality gate
        cls.assert_invalid_model(
            TaskPhase, cls.create_valid_data(quality_gate="invalid"), "quality_gate"
        )

        # Valid coordination patterns
        valid_patterns = ["parallel", "sequential", "hybrid"]
        for pattern in valid_patterns:
            data = cls.create_valid_data(coordination_pattern=pattern)
            cls.assert_valid_model(TaskPhase, data)

        # Invalid coordination pattern
        cls.assert_invalid_model(
            TaskPhase,
            cls.create_valid_data(coordination_pattern="invalid"),
            "coordination_pattern",
        )

    @classmethod
    def test_agents_list_validation(cls):
        """Test agents list validation."""
        # Empty agents list should be invalid
        cls.assert_invalid_model(TaskPhase, cls.create_valid_data(agents=[]), "agents")

        # Valid multiple agents
        multiple_agents = [
            {
                "role": "researcher",
                "domain": "distributed-systems",
                "priority": 1.0,
                "reasoning": "Primary research",
            },
            {
                "role": "architect",
                "domain": "software-architecture",
                "priority": 0.9,
                "reasoning": "System design",
            },
        ]
        data = cls.create_valid_data(agents=multiple_agents)
        cls.assert_valid_model(TaskPhase, data)

    @classmethod
    def test_dependencies_validation(cls):
        """Test dependencies list validation."""
        # Valid dependencies
        valid_dependencies = ["phase1", "phase2"]
        data = cls.create_valid_data(dependencies=valid_dependencies)
        cls.assert_valid_model(TaskPhase, data)

        # Empty dependencies (default)
        data = cls.create_valid_data()
        phase = cls.assert_valid_model(TaskPhase, data)
        assert phase.dependencies == []


# ============================================================================
# PlannerResponse Validation
# ============================================================================


class PlannerResponseValidator(BaseValidationPattern):
    """Validation patterns for PlannerResponse model."""

    MIN_CONFIDENCE = 0.0
    MAX_CONFIDENCE = 1.0
    MIN_RECOMMENDED_AGENTS = 0

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid PlannerResponse data."""
        data = {
            "success": True,
            "summary": "Orchestration plan for the task",
            "complexity": "medium",
            "recommended_agents": 5,
            "phases": [],
            "spawn_commands": [],
            "session_id": "test_session_123",
            "confidence": 0.85,
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        required_fields = [
            "success",
            "summary",
            "complexity",
            "recommended_agents",
            "confidence",
        ]

        for field in required_fields:
            incomplete_data = cls.create_valid_data()
            del incomplete_data[field]
            cls.assert_invalid_model(PlannerResponse, incomplete_data, field)

    @classmethod
    def test_complexity_enum(cls):
        """Test complexity enum validation."""
        valid_complexities = ["simple", "medium", "complex", "very_complex"]
        for complexity in valid_complexities:
            data = cls.create_valid_data(complexity=complexity)
            cls.assert_valid_model(PlannerResponse, data)

        # Invalid complexity
        cls.assert_invalid_model(
            PlannerResponse, cls.create_valid_data(complexity="invalid"), "complexity"
        )

    @classmethod
    def test_confidence_constraints(cls):
        """Test confidence field constraints."""
        # Valid confidence values
        valid_confidences = [0.0, 0.5, 1.0]
        for confidence in valid_confidences:
            data = cls.create_valid_data(confidence=confidence)
            cls.assert_valid_model(PlannerResponse, data)

        # Invalid confidence values
        invalid_confidences = [-0.1, 1.5]
        for confidence in invalid_confidences:
            data = cls.create_valid_data(confidence=confidence)
            cls.assert_invalid_model(PlannerResponse, data, "confidence")

    @classmethod
    def test_recommended_agents_constraints(cls):
        """Test recommended agents constraints."""
        # Valid agent counts
        valid_counts = [0, 1, 5, 20]
        for count in valid_counts:
            data = cls.create_valid_data(recommended_agents=count)
            cls.assert_valid_model(PlannerResponse, data)

        # Invalid agent counts
        invalid_counts = [-1, -5]
        for count in invalid_counts:
            data = cls.create_valid_data(recommended_agents=count)
            cls.assert_invalid_model(PlannerResponse, data, "recommended_agents")

    @classmethod
    def test_optional_fields(cls):
        """Test optional field behavior."""
        # Test with minimal required fields
        minimal_data = {
            "success": True,
            "summary": "Test summary",
            "complexity": "medium",
            "recommended_agents": 3,
            "confidence": 0.8,
        }
        response = cls.assert_valid_model(PlannerResponse, minimal_data)

        # Check defaults
        assert response.phases == []
        assert response.spawn_commands == []
        assert response.session_id is None
        assert response.error is None


# ============================================================================
# Cross-Model Validation Patterns
# ============================================================================


class CrossModelValidator:
    """Validation patterns for relationships between models."""

    @staticmethod
    def validate_evaluation_consistency(
        evaluation: OrchestrationEvaluation,
    ) -> list[str]:
        """Validate internal consistency of OrchestrationEvaluation."""
        issues = []

        # Agent count vs complexity consistency
        complexity_agent_ranges = {
            "simple": (1, 4),
            "medium": (3, 7),
            "complex": (5, 12),
            "very_complex": (8, 20),
        }

        min_agents, max_agents = complexity_agent_ranges.get(
            evaluation.complexity, (1, 20)
        )
        if not (min_agents <= evaluation.total_agents <= max_agents):
            issues.append(
                f"Agent count {evaluation.total_agents} inconsistent with "
                f"{evaluation.complexity} complexity (expected {min_agents}-{max_agents})"
            )

        # Role count vs agent count consistency
        if len(evaluation.role_priorities) > evaluation.total_agents:
            issues.append(
                f"More roles ({len(evaluation.role_priorities)}) than agents "
                f"({evaluation.total_agents})"
            )

        # Quality level vs complexity consistency
        if (
            evaluation.complexity in ["complex", "very_complex"]
            and evaluation.quality_level == "basic"
        ):
            issues.append("Complex tasks should not have basic quality level")

        # Confidence vs clarity consistency
        reason_lengths = [
            len(evaluation.complexity_reason),
            len(evaluation.agent_reason),
            len(evaluation.domain_reason),
        ]
        avg_reason_length = sum(reason_lengths) / len(reason_lengths)

        if evaluation.confidence > 0.9 and avg_reason_length < 50:
            issues.append("High confidence should have detailed reasoning")

        return issues

    @staticmethod
    def validate_phase_consistency(phases: list[TaskPhase]) -> list[str]:
        """Validate consistency across multiple phases."""
        issues = []
        phase_names = [phase.name for phase in phases]

        # Check for duplicate phase names
        if len(phase_names) != len(set(phase_names)):
            issues.append("Duplicate phase names found")

        # Check dependency references
        for phase in phases:
            issues.extend(
                f"Phase {phase.name} depends on non-existent phase {dep}"
                for dep in phase.dependencies
                if dep not in phase_names
            )

        # Check for circular dependencies
        if CrossModelValidator._has_circular_dependencies(phases):
            issues.append("Circular dependencies detected in phases")

        # Check agent distribution
        all_agents = []
        for phase in phases:
            all_agents.extend(phase.agents)

        role_counts = {}
        for agent in all_agents:
            role_counts[agent.role] = role_counts.get(agent.role, 0) + 1

        # Warn about role imbalances
        if max(role_counts.values()) > 3 * min(role_counts.values(), default=1):
            issues.append("Significant role imbalance across phases")

        return issues

    @staticmethod
    def _has_circular_dependencies(phases: list[TaskPhase]) -> bool:
        """Check for circular dependencies in phases."""
        # Build dependency graph
        deps = {phase.name: phase.dependencies for phase in phases}

        # Use DFS to detect cycles
        visiting = set()
        visited = set()

        def has_cycle(node):
            if node in visiting:
                return True
            if node in visited:
                return False

            visiting.add(node)
            for neighbor in deps.get(node, []):
                if has_cycle(neighbor):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        return any(has_cycle(phase_name) for phase_name in deps)

    @staticmethod
    def validate_response_consistency(response: PlannerResponse) -> list[str]:
        """Validate internal consistency of PlannerResponse."""
        issues = []

        # Success vs error consistency
        if not response.success and not response.error:
            issues.append("Failed response should have error message")

        if response.success and response.error:
            issues.append("Successful response should not have error message")

        # Agent count vs phases consistency
        if response.phases:
            total_phase_agents = sum(len(phase.agents) for phase in response.phases)
            if abs(total_phase_agents - response.recommended_agents) > 2:
                issues.append(
                    f"Recommended agents ({response.recommended_agents}) doesn't match "
                    f"phase agents ({total_phase_agents})"
                )

        # Spawn commands vs phases consistency
        if response.phases and not response.spawn_commands:
            issues.append("Phases defined but no spawn commands provided")

        return issues


# ============================================================================
# Comprehensive Validation Test Suite
# ============================================================================


class ComprehensiveModelValidator:
    """Comprehensive validation test suite for all models."""

    @staticmethod
    def run_all_validations() -> dict[str, list[str]]:
        """Run all validation tests and return results."""
        results = {}

        try:
            # OrchestrationEvaluation tests
            OrchestrationEvaluationValidator.test_field_constraints()
            OrchestrationEvaluationValidator.test_string_length_constraints()
            OrchestrationEvaluationValidator.test_list_constraints()
            OrchestrationEvaluationValidator.test_workflow_pattern_constraints()
            OrchestrationEvaluationValidator.test_quality_level_constraints()
            results["OrchestrationEvaluation"] = ["All tests passed"]
        except Exception as e:
            results["OrchestrationEvaluation"] = [str(e)]

        try:
            # PlannerRequest tests
            PlannerRequestValidator.test_required_fields()
            PlannerRequestValidator.test_time_budget_constraints()
            PlannerRequestValidator.test_string_constraints()
            results["PlannerRequest"] = ["All tests passed"]
        except Exception as e:
            results["PlannerRequest"] = [str(e)]

        try:
            # AgentRecommendation tests
            AgentRecommendationValidator.test_required_fields()
            AgentRecommendationValidator.test_priority_constraints()
            AgentRecommendationValidator.test_role_domain_validation()
            results["AgentRecommendation"] = ["All tests passed"]
        except Exception as e:
            results["AgentRecommendation"] = [str(e)]

        try:
            # TaskPhase tests
            TaskPhaseValidator.test_required_fields()
            TaskPhaseValidator.test_enum_constraints()
            TaskPhaseValidator.test_agents_list_validation()
            TaskPhaseValidator.test_dependencies_validation()
            results["TaskPhase"] = ["All tests passed"]
        except Exception as e:
            results["TaskPhase"] = [str(e)]

        try:
            # PlannerResponse tests
            PlannerResponseValidator.test_required_fields()
            PlannerResponseValidator.test_complexity_enum()
            PlannerResponseValidator.test_confidence_constraints()
            PlannerResponseValidator.test_recommended_agents_constraints()
            PlannerResponseValidator.test_optional_fields()
            results["PlannerResponse"] = ["All tests passed"]
        except Exception as e:
            results["PlannerResponse"] = [str(e)]

        return results

    @staticmethod
    def validate_full_orchestration_workflow() -> list[str]:
        """Validate a complete orchestration workflow."""
        issues = []

        try:
            # Create a complete workflow
            request_data = PlannerRequestValidator.create_valid_data()
            request = PlannerRequest.model_validate(request_data)

            evaluation_data = OrchestrationEvaluationValidator.create_valid_data()
            evaluation = OrchestrationEvaluation.model_validate(evaluation_data)

            agent_data = AgentRecommendationValidator.create_valid_data()
            agent = AgentRecommendation.model_validate(agent_data)

            phase_data = TaskPhaseValidator.create_valid_data(agents=[agent_data])
            phase = TaskPhase.model_validate(phase_data)

            response_data = PlannerResponseValidator.create_valid_data(
                phases=[phase_data]
            )
            response = PlannerResponse.model_validate(response_data)

            # Validate cross-model consistency
            eval_issues = CrossModelValidator.validate_evaluation_consistency(
                evaluation
            )
            phase_issues = CrossModelValidator.validate_phase_consistency([phase])
            response_issues = CrossModelValidator.validate_response_consistency(
                response
            )

            issues.extend(eval_issues)
            issues.extend(phase_issues)
            issues.extend(response_issues)

        except Exception as e:
            issues.append(f"Workflow validation failed: {e!s}")

        return issues
