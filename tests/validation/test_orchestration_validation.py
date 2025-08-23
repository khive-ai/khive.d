"""Comprehensive validation tests for Orchestration Service models.

This module provides systematic validation testing for:
- AgentRequest model validation and instruction consistency
- OrchestrationPlan model validation and execution strategy
- ComplexityAssessment model validation and scoring logic
- BaseGate model validation and quality gate logic
- GateComponent model validation and component assessment
- Cross-model orchestration workflow validation
"""

from typing import Any, Literal

import pytest
from lionagi.fields import Instruct
from pydantic import ValidationError

from khive.services.composition.parts import ComposerRequest
from khive.services.orchestration.parts import (
    AgentRequest,
    BaseGate,
    ComplexityAssessment,
    DeliverableType,
    GateComponent,
    OrchestrationPlan,
)
from tests.validation.pydantic_validators import BaseValidationPattern

# ============================================================================
# AgentRequest Model Validation
# ============================================================================


class AgentRequestValidator(BaseValidationPattern):
    """Validation patterns for AgentRequest model."""

    VALID_DELIVERABLE_TYPES = [
        "RequirementsAnalysis",
        "CodeContextAnalysis",
        "IntegrationStrategy",
        "FeatureImplementation",
        "RequirementValidation",
        "DocumentationPackage",
        "TestStrategy",
        "WorkSynthesis",
    ]

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid AgentRequest data."""
        data = {
            "instruct": {
                "instruction": "Analyze the distributed system architecture and identify scalability bottlenecks",
                "context": "Working on high-throughput data processing system",
                "output_fields": ["analysis", "recommendations", "risks"],
            },
            "compose_request": {
                "role": "researcher",
                "domains": "distributed-systems,performance-optimization",
                "context": "System architecture analysis for scalability improvements",
            },
            "analysis_type": "RequirementsAnalysis",
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        required_fields = ["instruct", "compose_request", "analysis_type"]

        for field in required_fields:
            incomplete_data = cls.create_valid_data()
            del incomplete_data[field]
            cls.assert_invalid_model(AgentRequest, incomplete_data, field)

    @classmethod
    def test_instruct_validation(cls):
        """Test Instruct field validation."""
        # Valid Instruct structures
        valid_instructs = [
            {
                "instruction": "Simple instruction",
                "context": "Basic context",
                "output_fields": ["result"],
            },
            {
                "instruction": "Complex instruction with detailed requirements",
                "context": "Comprehensive context with background information",
                "output_fields": ["analysis", "design", "implementation", "testing"],
            },
            {
                "instruction": "Instruction with minimal context",
                "output_fields": ["output"],
            },
        ]

        for instruct_data in valid_instructs:
            data = cls.create_valid_data(instruct=instruct_data)
            cls.assert_valid_model(AgentRequest, data)

    @classmethod
    def test_compose_request_validation(cls):
        """Test ComposerRequest field validation."""
        # Valid ComposerRequest structures
        valid_compose_requests = [
            {
                "role": "researcher",
                "domains": "distributed-systems",
                "context": "Research context",
            },
            {
                "role": "architect",
                "domains": "software-architecture,microservices",
                "context": "System design context",
            },
            {
                "role": "implementer",
                # domains and context are optional
            },
        ]

        for compose_request in valid_compose_requests:
            data = cls.create_valid_data(compose_request=compose_request)
            cls.assert_valid_model(AgentRequest, data)

        # Invalid ComposerRequest (missing role)
        invalid_compose_request = {"domains": "test-domain", "context": "test context"}
        data = cls.create_valid_data(compose_request=invalid_compose_request)
        cls.assert_invalid_model(AgentRequest, data)

    @classmethod
    def test_analysis_type_validation(cls):
        """Test analysis_type field validation."""
        # Valid deliverable types
        for analysis_type in cls.VALID_DELIVERABLE_TYPES:
            data = cls.create_valid_data(analysis_type=analysis_type)
            cls.assert_valid_model(AgentRequest, data)

        # Invalid analysis type
        cls.assert_invalid_model(
            AgentRequest,
            cls.create_valid_data(analysis_type="InvalidAnalysisType"),
            "analysis_type",
        )

    @classmethod
    def test_agent_request_consistency(cls):
        """Test internal consistency of AgentRequest."""
        # Instruction and compose request should be aligned
        aligned_data = cls.create_valid_data(
            instruct={
                "instruction": "Research distributed system consensus algorithms",
                "context": "Building fault-tolerant system",
                "output_fields": ["algorithms", "tradeoffs", "recommendations"],
            },
            compose_request={
                "role": "researcher",
                "domains": "distributed-systems,consensus-algorithms",
                "context": "Consensus algorithm research for fault tolerance",
            },
            analysis_type="RequirementsAnalysis",
        )

        cls.assert_valid_model(AgentRequest, aligned_data)


# ============================================================================
# OrchestrationPlan Model Validation
# ============================================================================


class OrchestrationPlanValidator(BaseValidationPattern):
    """Validation patterns for OrchestrationPlan model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid OrchestrationPlan data."""
        data = {
            "common_background": "Building a distributed data processing system with high throughput requirements",
            "agent_requests": [
                {
                    "instruct": {
                        "instruction": "Analyze system requirements",
                        "context": "Initial analysis phase",
                        "output_fields": ["requirements", "constraints"],
                    },
                    "compose_request": {
                        "role": "researcher",
                        "domains": "distributed-systems",
                        "context": "Requirements analysis",
                    },
                    "analysis_type": "RequirementsAnalysis",
                },
                {
                    "instruct": {
                        "instruction": "Design system architecture",
                        "context": "Architecture design phase",
                        "output_fields": ["architecture", "components"],
                    },
                    "compose_request": {
                        "role": "architect",
                        "domains": "software-architecture",
                        "context": "System architecture design",
                    },
                    "analysis_type": "IntegrationStrategy",
                },
            ],
            "execution_strategy": "concurrent",
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        required_fields = ["common_background", "agent_requests"]

        for field in required_fields:
            incomplete_data = cls.create_valid_data()
            del incomplete_data[field]
            cls.assert_invalid_model(OrchestrationPlan, incomplete_data, field)

    @classmethod
    def test_field_defaults(cls):
        """Test field default values."""
        minimal_plan = OrchestrationPlan(
            common_background="Test background",
            agent_requests=[
                AgentRequest(
                    instruct=Instruct(
                        instruction="Test message", output_fields=["result"]
                    ),
                    compose_request=ComposerRequest(role="researcher"),
                    analysis_type="RequirementsAnalysis",
                )
            ],
        )

        assert minimal_plan.execution_strategy == "concurrent"

    @classmethod
    def test_common_background_validation(cls):
        """Test common_background field validation."""
        # Valid backgrounds
        valid_backgrounds = [
            "Simple background",
            "Detailed background with comprehensive context and requirements",
            "Multi-line\nbackground\nwith\ndetailed\ninformation",
            "Background with special chars: @#$%^&*()",
        ]

        for background in valid_backgrounds:
            data = cls.create_valid_data(common_background=background)
            cls.assert_valid_model(OrchestrationPlan, data)

        # Empty background should be invalid
        cls.assert_invalid_model(
            OrchestrationPlan,
            cls.create_valid_data(common_background=""),
            "common_background",
        )

    @classmethod
    def test_agent_requests_validation(cls):
        """Test agent_requests field validation."""
        # Valid agent request lists
        single_request = [
            {
                "instruct": {
                    "instruction": "Test instruction",
                    "output_fields": ["result"],
                },
                "compose_request": {"role": "researcher"},
                "analysis_type": "RequirementsAnalysis",
            }
        ]

        data = cls.create_valid_data(agent_requests=single_request)
        cls.assert_valid_model(OrchestrationPlan, data)

        # Empty agent requests should be invalid
        cls.assert_invalid_model(
            OrchestrationPlan,
            cls.create_valid_data(agent_requests=[]),
            "agent_requests",
        )

    @classmethod
    def test_execution_strategy_validation(cls):
        """Test execution_strategy field validation."""
        # Valid execution strategies
        valid_strategies = ["concurrent", "sequential"]

        for strategy in valid_strategies:
            data = cls.create_valid_data(execution_strategy=strategy)
            cls.assert_valid_model(OrchestrationPlan, data)

        # Invalid execution strategy
        cls.assert_invalid_model(
            OrchestrationPlan,
            cls.create_valid_data(execution_strategy="invalid_strategy"),
            "execution_strategy",
        )

    @classmethod
    def test_orchestration_plan_consistency(cls):
        """Test internal consistency of OrchestrationPlan."""
        # Agent requests should be diverse for concurrent execution
        concurrent_plan = cls.create_valid_data(
            execution_strategy="concurrent",
            agent_requests=[
                {
                    "instruct": {
                        "instruction": "Analyze requirements",
                        "output_fields": ["requirements"],
                    },
                    "compose_request": {"role": "researcher"},
                    "analysis_type": "RequirementsAnalysis",
                },
                {
                    "instruct": {
                        "instruction": "Design architecture",
                        "output_fields": ["architecture"],
                    },
                    "compose_request": {"role": "architect"},
                    "analysis_type": "IntegrationStrategy",
                },
            ],
        )

        cls.assert_valid_model(OrchestrationPlan, concurrent_plan)

        # Sequential execution might have dependent tasks
        sequential_plan = cls.create_valid_data(
            execution_strategy="sequential",
            agent_requests=[
                {
                    "instruct": {
                        "instruction": "First analyze requirements",
                        "output_fields": ["requirements"],
                    },
                    "compose_request": {"role": "researcher"},
                    "analysis_type": "RequirementsAnalysis",
                },
                {
                    "instruct": {
                        "instruction": "Then implement based on requirements",
                        "output_fields": ["implementation"],
                    },
                    "compose_request": {"role": "implementer"},
                    "analysis_type": "FeatureImplementation",
                },
            ],
        )

        cls.assert_valid_model(OrchestrationPlan, sequential_plan)


# ============================================================================
# ComplexityAssessment Model Validation
# ============================================================================


class ComplexityAssessmentValidator(BaseValidationPattern):
    """Validation patterns for ComplexityAssessment model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid ComplexityAssessment data."""
        data = {
            "overall_complexity_score": 0.6,
            "explanation": "Moderate complexity due to distributed system coordination requirements",
            "comment": "Consider using proven consensus algorithms to mitigate coordination complexity",
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        required_fields = ["overall_complexity_score", "explanation"]

        for field in required_fields:
            incomplete_data = cls.create_valid_data()
            del incomplete_data[field]
            cls.assert_invalid_model(ComplexityAssessment, incomplete_data, field)

    @classmethod
    def test_field_defaults(cls):
        """Test field default values."""
        minimal_assessment = ComplexityAssessment(
            overall_complexity_score=0.5, explanation="Test explanation"
        )

        assert minimal_assessment.comment is None

    @classmethod
    def test_complexity_score_constraints(cls):
        """Test complexity score field constraints."""
        # Valid complexity scores (0.0 to 1.0)
        valid_scores = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]

        for score in valid_scores:
            data = cls.create_valid_data(overall_complexity_score=score)
            cls.assert_valid_model(ComplexityAssessment, data)

        # Invalid complexity scores (outside range)
        invalid_scores = [-0.1, -1.0, 1.1, 2.0]

        for score in invalid_scores:
            data = cls.create_valid_data(overall_complexity_score=score)
            cls.assert_invalid_model(
                ComplexityAssessment, data, "overall_complexity_score"
            )

    @classmethod
    def test_explanation_validation(cls):
        """Test explanation field validation."""
        # Valid explanations
        valid_explanations = [
            "Simple explanation",
            "Detailed explanation with comprehensive analysis of complexity factors",
            "Multi-line\nexplanation\nwith\nbreaks",
            "Explanation with technical terms and rationale",
        ]

        for explanation in valid_explanations:
            data = cls.create_valid_data(explanation=explanation)
            cls.assert_valid_model(ComplexityAssessment, data)

        # Empty explanation should be invalid
        cls.assert_invalid_model(
            ComplexityAssessment, cls.create_valid_data(explanation=""), "explanation"
        )

    @classmethod
    def test_comment_validation(cls):
        """Test comment field validation."""
        # Valid comments (optional)
        valid_comments = [
            None,  # optional field
            "",  # empty comment
            "Short comment",
            "Detailed comment with additional context and recommendations",
            "Multi-line\ncomment\nwith\nadditional\ninsights",
        ]

        for comment in valid_comments:
            data = cls.create_valid_data(comment=comment)
            cls.assert_valid_model(ComplexityAssessment, data)

    @classmethod
    def test_complexity_consistency(cls):
        """Test internal consistency of complexity assessment."""
        # Low complexity should have appropriate explanation
        low_complexity = cls.create_valid_data(
            overall_complexity_score=0.2,
            explanation="Simple task with well-defined requirements and proven solutions",
        )
        cls.assert_valid_model(ComplexityAssessment, low_complexity)

        # High complexity should have appropriate explanation
        high_complexity = cls.create_valid_data(
            overall_complexity_score=0.9,
            explanation="Very complex task requiring novel approaches and significant coordination",
        )
        cls.assert_valid_model(ComplexityAssessment, high_complexity)

        # Medium complexity
        medium_complexity = cls.create_valid_data(
            overall_complexity_score=0.5,
            explanation="Moderate complexity with some known challenges",
        )
        cls.assert_valid_model(ComplexityAssessment, medium_complexity)


# ============================================================================
# BaseGate Model Validation
# ============================================================================


class BaseGateValidator(BaseValidationPattern):
    """Validation patterns for BaseGate model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid BaseGate data."""
        data = {
            "threshold_met": True,
            "feedback": "Work meets requirements with good quality and appropriate scope",
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        # Only threshold_met is required
        minimal_gate = {"threshold_met": True}
        cls.assert_valid_model(BaseGate, minimal_gate)

        # Missing threshold_met should fail
        cls.assert_invalid_model(BaseGate, {}, "threshold_met")

    @classmethod
    def test_field_defaults(cls):
        """Test field default values."""
        minimal_gate = BaseGate(threshold_met=True)

        assert minimal_gate.threshold_met is True
        assert minimal_gate.feedback is None

    @classmethod
    def test_threshold_met_validation(cls):
        """Test threshold_met field validation."""
        # Valid boolean values
        for threshold_met in [True, False]:
            data = cls.create_valid_data(threshold_met=threshold_met)
            cls.assert_valid_model(BaseGate, data)

    @classmethod
    def test_feedback_validation(cls):
        """Test feedback field validation."""
        # Valid feedback values
        valid_feedbacks = [
            None,  # optional field
            "",  # empty feedback
            "Short feedback",
            "Detailed feedback with specific observations and recommendations",
            "Multi-line\nfeedback\nwith\ndetailed\nanalysis",
            "Feedback with technical details and actionable suggestions",
        ]

        for feedback in valid_feedbacks:
            data = cls.create_valid_data(feedback=feedback)
            cls.assert_valid_model(BaseGate, data)

    @classmethod
    def test_gate_logic_consistency(cls):
        """Test gate logic consistency."""
        # Passing gate with positive feedback
        passing_gate = cls.create_valid_data(
            threshold_met=True, feedback="Excellent work that exceeds expectations"
        )
        cls.assert_valid_model(BaseGate, passing_gate)

        # Failing gate with constructive feedback
        failing_gate = cls.create_valid_data(
            threshold_met=False,
            feedback="Work needs improvement in error handling and documentation",
        )
        cls.assert_valid_model(BaseGate, failing_gate)

        # Gate without feedback (valid but less informative)
        no_feedback_gate = cls.create_valid_data(threshold_met=True, feedback=None)
        cls.assert_valid_model(BaseGate, no_feedback_gate)


# ============================================================================
# GateComponent Model Validation
# ============================================================================


class GateComponentValidator(BaseValidationPattern):
    """Validation patterns for GateComponent model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid GateComponent data."""
        data = {
            "is_acceptable": True,
            "problems": [],
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        # Only is_acceptable is required
        minimal_component = {"is_acceptable": True}
        cls.assert_valid_model(GateComponent, minimal_component)

        # Missing is_acceptable should fail
        cls.assert_invalid_model(GateComponent, {}, "is_acceptable")

    @classmethod
    def test_field_defaults(cls):
        """Test field default values."""
        minimal_component = GateComponent(is_acceptable=True)

        assert minimal_component.is_acceptable is True
        assert minimal_component.problems == []

    @classmethod
    def test_is_acceptable_validation(cls):
        """Test is_acceptable field validation."""
        # Valid boolean values
        for is_acceptable in [True, False]:
            data = cls.create_valid_data(is_acceptable=is_acceptable)
            cls.assert_valid_model(GateComponent, data)

    @classmethod
    def test_problems_validation(cls):
        """Test problems field validation."""
        # Valid problem lists
        valid_problem_lists = [
            [],  # no problems
            ["Single problem"],
            ["Multiple", "problems", "identified"],
            [
                "Detailed problem description with context",
                "Another problem with specific technical details",
                "Third problem requiring immediate attention",
            ],
        ]

        for problems in valid_problem_lists:
            data = cls.create_valid_data(problems=problems)
            cls.assert_valid_model(GateComponent, data)

    @classmethod
    def test_component_logic_consistency(cls):
        """Test component logic consistency."""
        # Acceptable component with no problems
        acceptable_component = cls.create_valid_data(is_acceptable=True, problems=[])
        cls.assert_valid_model(GateComponent, acceptable_component)

        # Unacceptable component with problems
        unacceptable_component = cls.create_valid_data(
            is_acceptable=False,
            problems=[
                "Security vulnerability in authentication",
                "Performance bottleneck in data processing",
                "Missing error handling for edge cases",
            ],
        )
        cls.assert_valid_model(GateComponent, unacceptable_component)

        # Edge case: acceptable component with minor problems (warnings)
        acceptable_with_warnings = cls.create_valid_data(
            is_acceptable=True, problems=["Minor: Consider adding more comments"]
        )
        cls.assert_valid_model(GateComponent, acceptable_with_warnings)


# ============================================================================
# Cross-Model Orchestration Validation Patterns
# ============================================================================


class OrchestrationServiceCrossValidator:
    """Cross-model validation patterns for Orchestration Service."""

    @staticmethod
    def validate_plan_complexity_consistency(
        plan: OrchestrationPlan, assessment: ComplexityAssessment
    ) -> list[str]:
        """Validate consistency between OrchestrationPlan and ComplexityAssessment."""
        issues = []

        # Number of agents vs complexity
        agent_count = len(plan.agent_requests)
        complexity_score = assessment.overall_complexity_score

        # Low complexity should not require many agents
        if complexity_score < 0.3 and agent_count > 5:
            issues.append(
                f"Low complexity ({complexity_score:.2f}) but many agents ({agent_count})"
            )

        # High complexity might require more agents
        if complexity_score > 0.8 and agent_count < 3:
            issues.append(
                f"High complexity ({complexity_score:.2f}) but few agents ({agent_count})"
            )

        # Execution strategy vs complexity
        if complexity_score > 0.7 and plan.execution_strategy == "concurrent":
            # High complexity might benefit from sequential approach
            pass  # This is a recommendation, not a hard rule

        return issues

    @staticmethod
    def validate_gate_assessment_consistency(
        base_gate: BaseGate, components: list[GateComponent]
    ) -> list[str]:
        """Validate consistency between BaseGate and GateComponents."""
        issues = []

        if not components:
            return issues  # No components to validate

        # Overall gate vs component assessments
        acceptable_components = [c for c in components if c.is_acceptable]
        unacceptable_components = [c for c in components if not c.is_acceptable]

        # If all components are acceptable, gate should probably pass
        if len(unacceptable_components) == 0 and not base_gate.threshold_met:
            issues.append("All components acceptable but overall gate fails")

        # If many components fail, gate should probably fail
        if (
            len(unacceptable_components) > len(acceptable_components)
            and base_gate.threshold_met
        ):
            issues.append(
                "More components unacceptable than acceptable but gate passes"
            )

        # Feedback should reflect component problems
        all_problems = []
        for component in components:
            all_problems.extend(component.problems)

        if all_problems and base_gate.threshold_met and not base_gate.feedback:
            issues.append("Components have problems but no gate feedback provided")

        return issues

    @staticmethod
    def validate_agent_request_diversity(plan: OrchestrationPlan) -> list[str]:
        """Validate diversity and balance of agent requests in plan."""
        issues = []

        if len(plan.agent_requests) < 2:
            return issues  # Single agent plans don't need diversity

        # Check role diversity
        roles = []
        for request in plan.agent_requests:
            if hasattr(request.compose_request.role, "value"):
                roles.append(request.compose_request.role.value)
            else:
                roles.append(str(request.compose_request.role))

        unique_roles = set(roles)

        # For concurrent execution, diversity is beneficial
        if plan.execution_strategy == "concurrent" and len(unique_roles) < 2:
            issues.append("Concurrent execution with limited role diversity")

        # Check analysis type diversity
        analysis_types = [req.analysis_type for req in plan.agent_requests]
        unique_analysis_types = set(analysis_types)

        if len(analysis_types) > 3 and len(unique_analysis_types) < 2:
            issues.append("Many agents but limited analysis type diversity")

        # Check for potential conflicts
        if (
            "RequirementsAnalysis" in analysis_types
            and "FeatureImplementation" in analysis_types
        ):
            if plan.execution_strategy == "concurrent":
                issues.append(
                    "Requirements analysis and implementation running concurrently"
                )

        return issues

    @staticmethod
    def validate_orchestration_workflow_consistency(
        plans: list[OrchestrationPlan],
        assessments: list[ComplexityAssessment],
        gates: list[BaseGate],
    ) -> list[str]:
        """Validate consistency across orchestration workflow."""
        issues = []

        # Ensure equal lengths
        if not (len(plans) == len(assessments) == len(gates)):
            issues.append(
                f"Mismatched workflow lengths: plans={len(plans)}, "
                f"assessments={len(assessments)}, gates={len(gates)}"
            )
            return issues

        for i, (plan, assessment, gate) in enumerate(zip(plans, assessments, gates)):
            # Plan-assessment consistency
            plan_issues = (
                OrchestrationServiceCrossValidator.validate_plan_complexity_consistency(
                    plan, assessment
                )
            )
            for issue in plan_issues:
                issues.append(f"Workflow step {i + 1}: {issue}")

            # Assessment-gate consistency
            if assessment.overall_complexity_score > 0.8 and gate.threshold_met:
                if not gate.feedback or len(gate.feedback) < 50:
                    issues.append(
                        f"Workflow step {i + 1}: High complexity passed gate without detailed feedback"
                    )

        return issues


# ============================================================================
# Comprehensive Test Suite
# ============================================================================


class TestOrchestrationValidation:
    """Test class to run all Orchestration Service validation tests."""

    def test_agent_request_validation(self):
        """Test AgentRequest model validation."""
        AgentRequestValidator.test_required_fields()
        AgentRequestValidator.test_instruct_validation()
        AgentRequestValidator.test_compose_request_validation()
        AgentRequestValidator.test_analysis_type_validation()
        AgentRequestValidator.test_agent_request_consistency()

    def test_orchestration_plan_validation(self):
        """Test OrchestrationPlan model validation."""
        OrchestrationPlanValidator.test_required_fields()
        OrchestrationPlanValidator.test_field_defaults()
        OrchestrationPlanValidator.test_common_background_validation()
        OrchestrationPlanValidator.test_agent_requests_validation()
        OrchestrationPlanValidator.test_execution_strategy_validation()
        OrchestrationPlanValidator.test_orchestration_plan_consistency()

    def test_complexity_assessment_validation(self):
        """Test ComplexityAssessment model validation."""
        ComplexityAssessmentValidator.test_required_fields()
        ComplexityAssessmentValidator.test_field_defaults()
        ComplexityAssessmentValidator.test_complexity_score_constraints()
        ComplexityAssessmentValidator.test_explanation_validation()
        ComplexityAssessmentValidator.test_comment_validation()
        ComplexityAssessmentValidator.test_complexity_consistency()

    def test_base_gate_validation(self):
        """Test BaseGate model validation."""
        BaseGateValidator.test_required_fields()
        BaseGateValidator.test_field_defaults()
        BaseGateValidator.test_threshold_met_validation()
        BaseGateValidator.test_feedback_validation()
        BaseGateValidator.test_gate_logic_consistency()

    def test_gate_component_validation(self):
        """Test GateComponent model validation."""
        GateComponentValidator.test_required_fields()
        GateComponentValidator.test_field_defaults()
        GateComponentValidator.test_is_acceptable_validation()
        GateComponentValidator.test_problems_validation()
        GateComponentValidator.test_component_logic_consistency()

    def test_cross_model_validation(self):
        """Test cross-model validation patterns."""
        # Create test models
        plan = OrchestrationPlan(
            common_background="Test distributed system implementation",
            agent_requests=[
                AgentRequest(
                    instruct=Instruct(
                        instruction="Analyze requirements",
                        output_fields=["requirements"],
                    ),
                    compose_request=ComposerRequest(role="researcher"),
                    analysis_type="RequirementsAnalysis",
                ),
                AgentRequest(
                    instruct=Instruct(
                        instruction="Design architecture",
                        output_fields=["architecture"],
                    ),
                    compose_request=ComposerRequest(role="architect"),
                    analysis_type="IntegrationStrategy",
                ),
            ],
            execution_strategy="concurrent",
        )

        assessment = ComplexityAssessment(
            overall_complexity_score=0.6,
            explanation="Moderate complexity due to distributed system requirements",
        )

        gate = BaseGate(
            threshold_met=True,
            feedback="Work meets standards with good analysis and design",
        )

        components = [
            GateComponent(is_acceptable=True, problems=[]),
            GateComponent(is_acceptable=True, problems=["Minor: Add more tests"]),
        ]

        # Run cross-model validations
        plan_complexity_issues = (
            OrchestrationServiceCrossValidator.validate_plan_complexity_consistency(
                plan, assessment
            )
        )

        gate_component_issues = (
            OrchestrationServiceCrossValidator.validate_gate_assessment_consistency(
                gate, components
            )
        )

        diversity_issues = (
            OrchestrationServiceCrossValidator.validate_agent_request_diversity(plan)
        )

        workflow_issues = OrchestrationServiceCrossValidator.validate_orchestration_workflow_consistency(
            [plan], [assessment], [gate]
        )

        # Should have no issues for valid models
        assert len(plan_complexity_issues) == 0
        assert len(gate_component_issues) == 0
        assert len(diversity_issues) == 0
        assert len(workflow_issues) == 0


if __name__ == "__main__":
    # Manual test runner
    test_suite = TestOrchestrationValidation()

    try:
        test_suite.test_agent_request_validation()
        test_suite.test_orchestration_plan_validation()
        test_suite.test_complexity_assessment_validation()
        test_suite.test_base_gate_validation()
        test_suite.test_gate_component_validation()
        test_suite.test_cross_model_validation()

        print("✅ All Orchestration Service validation tests passed!")

    except Exception as e:
        print(f"❌ Orchestration validation test failed: {e}")
        raise
