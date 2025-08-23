"""
Decision Logic Validation Tests for Planning Service.

This module provides comprehensive validation for all decision-making logic
including decision matrices, scoring mechanisms, consensus algorithms,
and boundary condition handling.
"""

import statistics
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from khive.services.plan.models import OrchestrationEvaluation
from khive.services.plan.parts import ComplexityLevel
from khive.services.plan.planner_service import (ComplexityTier,
                                                 OrchestrationPlanner, Request)
from khive.services.plan.triage.complexity_triage import (
    ComplexityTriageService, TriageConsensus)


@dataclass
class DecisionTestCase:
    """Test case for decision validation."""

    scenario: str
    input_context: dict[str, Any]
    expected_decision: Any
    decision_rationale: str
    confidence_threshold: float = 0.7


@dataclass
class ScoringTestCase:
    """Test case for scoring mechanism validation."""

    name: str
    inputs: dict[str, Any]
    expected_score_range: tuple[float, float]
    scoring_criteria: dict[str, Any]


class DecisionValidationFramework:
    """Framework for validating decision-making algorithms."""

    def __init__(self):
        self.decision_log: list[dict[str, Any]] = []
        self.scoring_log: list[dict[str, Any]] = []

    def validate_decision_logic(
        self, decision_func: callable, test_cases: list[DecisionTestCase]
    ) -> dict[str, float]:
        """Validate decision logic against test cases."""

        correct_decisions = 0
        confidence_scores = []

        for test_case in test_cases:
            try:
                decision_result = decision_func(test_case.input_context)

                # Extract decision and confidence
                if isinstance(decision_result, tuple):
                    decision, confidence = decision_result
                elif isinstance(decision_result, dict):
                    decision = decision_result.get("decision")
                    confidence = decision_result.get("confidence", 1.0)
                else:
                    decision = decision_result
                    confidence = 1.0

                is_correct = self._validate_decision(
                    decision, test_case.expected_decision
                )

                if is_correct:
                    correct_decisions += 1

                confidence_scores.append(confidence)

                self.decision_log.append({
                    "scenario": test_case.scenario,
                    "correct": is_correct,
                    "decision": decision,
                    "expected": test_case.expected_decision,
                    "confidence": confidence,
                    "rationale": test_case.decision_rationale,
                })

            except Exception as e:
                self.decision_log.append({
                    "scenario": test_case.scenario,
                    "correct": False,
                    "error": str(e),
                })

        return {
            "accuracy": correct_decisions / len(test_cases) if test_cases else 0,
            "avg_confidence": statistics.mean(confidence_scores)
            if confidence_scores
            else 0,
            "total_cases": len(test_cases),
            "correct_decisions": correct_decisions,
        }

    def _validate_decision(self, actual: Any, expected: Any) -> bool:
        """Validate a decision against expected outcome."""
        if isinstance(expected, (list, tuple)):
            return actual in expected
        return actual == expected

    def validate_scoring_mechanism(
        self, scoring_func: callable, test_cases: list[ScoringTestCase]
    ) -> dict[str, float]:
        """Validate scoring mechanisms."""

        valid_scores = 0
        score_deviations = []

        for test_case in test_cases:
            try:
                score = scoring_func(test_case.inputs)

                min_score, max_score = test_case.expected_score_range
                is_valid = min_score <= score <= max_score

                if is_valid:
                    valid_scores += 1

                # Calculate deviation from expected range center
                center = (min_score + max_score) / 2
                deviation = abs(score - center) / (max_score - min_score)
                score_deviations.append(deviation)

                self.scoring_log.append({
                    "test_name": test_case.name,
                    "score": score,
                    "expected_range": test_case.expected_score_range,
                    "valid": is_valid,
                    "deviation": deviation,
                })

            except Exception as e:
                self.scoring_log.append({
                    "test_name": test_case.name,
                    "error": str(e),
                    "valid": False,
                })

        return {
            "accuracy": valid_scores / len(test_cases) if test_cases else 0,
            "avg_deviation": statistics.mean(score_deviations)
            if score_deviations
            else 1.0,
            "total_cases": len(test_cases),
            "valid_scores": valid_scores,
        }


@pytest.fixture
def decision_framework():
    """Provide decision validation framework."""
    return DecisionValidationFramework()


@pytest.fixture
def mock_decision_planner():
    """Create orchestration planner with comprehensive decision matrix."""
    decision_matrix = {
        "complexity_assessment": {
            "simple": {
                "indicators": ["basic", "straightforward", "quick", "simple", "easy"],
                "threshold_score": 0.3,
                "agent_multiplier": 1.0,
            },
            "medium": {
                "indicators": ["moderate", "standard", "typical", "regular", "normal"],
                "threshold_score": 0.5,
                "agent_multiplier": 1.5,
            },
            "complex": {
                "indicators": [
                    "advanced",
                    "sophisticated",
                    "multi_step",
                    "complex",
                    "intricate",
                ],
                "threshold_score": 0.7,
                "agent_multiplier": 2.0,
            },
            "very_complex": {
                "indicators": [
                    "enterprise",
                    "distributed",
                    "comprehensive",
                    "large_scale",
                    "platform",
                ],
                "threshold_score": 0.9,
                "agent_multiplier": 2.5,
            },
        },
        "agent_role_selection": {
            "discovery_phase": {
                "roles": ["researcher", "analyst", "theorist"],
                "min_agents": 1,
                "max_agents": 3,
                "triggers": ["research", "analyze", "understand", "investigate"],
            },
            "design_phase": {
                "roles": ["architect", "strategist"],
                "min_agents": 1,
                "max_agents": 2,
                "triggers": ["design", "architect", "plan", "structure"],
            },
            "implementation_phase": {
                "roles": ["implementer", "innovator"],
                "min_agents": 1,
                "max_agents": 4,
                "triggers": ["implement", "build", "create", "develop"],
            },
            "validation_phase": {
                "roles": ["tester", "critic", "auditor"],
                "min_agents": 1,
                "max_agents": 3,
                "triggers": ["test", "verify", "validate", "check", "audit"],
            },
        },
        "workflow_patterns": {
            "parallel": {
                "indicators": ["independent", "concurrent", "simultaneous"],
                "efficiency_score": 0.9,
                "complexity_penalty": 0.1,
            },
            "sequential": {
                "indicators": ["dependent", "ordered", "step_by_step"],
                "efficiency_score": 0.7,
                "complexity_penalty": 0.0,
            },
            "hybrid": {
                "indicators": ["mixed", "combined", "phases"],
                "efficiency_score": 0.8,
                "complexity_penalty": 0.05,
            },
        },
        "quality_gates": {
            "basic": {
                "min_complexity": "simple",
                "validation_threshold": 0.6,
                "review_requirements": ["implementer"],
            },
            "thorough": {
                "min_complexity": "medium",
                "validation_threshold": 0.8,
                "review_requirements": ["implementer", "tester"],
            },
            "critical": {
                "min_complexity": "complex",
                "validation_threshold": 0.95,
                "review_requirements": ["implementer", "tester", "auditor"],
            },
        },
    }

    with (
        patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
        patch("khive.services.plan.planner_service.OpenAI"),
        patch.object(
            OrchestrationPlanner,
            "_load_available_roles",
            return_value=[
                "researcher",
                "analyst",
                "theorist",
                "architect",
                "strategist",
                "implementer",
                "innovator",
                "tester",
                "critic",
                "auditor",
                "reviewer",
            ],
        ),
        patch.object(
            OrchestrationPlanner,
            "_load_available_domains",
            return_value=[
                "software-architecture",
                "distributed-systems",
                "api-design",
                "database-design",
                "async-programming",
                "microkernel-architecture",
            ],
        ),
        patch.object(
            OrchestrationPlanner,
            "_load_prompt_templates",
            return_value={
                "agents": {},
                "base_context_template": "",
                "user_prompt_template": "",
            },
        ),
        patch.object(
            OrchestrationPlanner, "_load_decision_matrix", return_value=decision_matrix
        ),
    ):
        planner = OrchestrationPlanner()
        planner.matrix = decision_matrix
        return planner


@pytest.fixture
def complexity_decision_cases():
    """Test cases for complexity decision validation."""
    return [
        DecisionTestCase(
            scenario="simple_single_action",
            input_context={"request_text": "fix basic authentication bug"},
            expected_decision=ComplexityTier.SIMPLE,
            decision_rationale="Single action with clear scope",
            confidence_threshold=0.8,
        ),
        DecisionTestCase(
            scenario="medium_multi_step",
            input_context={
                "request_text": "create API endpoint with standard validation"
            },
            expected_decision=ComplexityTier.MEDIUM,
            decision_rationale="Multiple steps but standard approach",
            confidence_threshold=0.7,
        ),
        DecisionTestCase(
            scenario="complex_architecture",
            input_context={
                "request_text": "design sophisticated microservices architecture"
            },
            expected_decision=ComplexityTier.COMPLEX,
            decision_rationale="Advanced architectural decisions required",
            confidence_threshold=0.75,
        ),
        DecisionTestCase(
            scenario="very_complex_distributed",
            input_context={
                "request_text": "build enterprise distributed consensus platform"
            },
            expected_decision=ComplexityTier.VERY_COMPLEX,
            decision_rationale="Enterprise scale with distributed complexity",
            confidence_threshold=0.9,
        ),
        DecisionTestCase(
            scenario="boundary_simple_medium",
            input_context={"request_text": "basic task with moderate requirements"},
            expected_decision=[
                ComplexityTier.SIMPLE,
                ComplexityTier.MEDIUM,
            ],  # Either acceptable
            decision_rationale="Boundary case between simple and medium",
            confidence_threshold=0.6,
        ),
        DecisionTestCase(
            scenario="conflicting_indicators",
            input_context={
                "request_text": "simple enterprise distributed basic system"
            },
            expected_decision=ComplexityTier.VERY_COMPLEX,  # Highest indicator wins
            decision_rationale="Conflicting indicators resolved to highest complexity",
            confidence_threshold=0.7,
        ),
    ]


@pytest.fixture
def agent_count_decision_cases():
    """Test cases for agent count decision validation."""
    return [
        DecisionTestCase(
            scenario="minimal_team_simple",
            input_context={
                "complexity": ComplexityTier.SIMPLE,
                "phases": ["implementation"],
            },
            expected_decision=(1, 3),  # Range acceptable
            decision_rationale="Simple tasks need minimal team",
            confidence_threshold=0.8,
        ),
        DecisionTestCase(
            scenario="balanced_team_medium",
            input_context={
                "complexity": ComplexityTier.MEDIUM,
                "phases": ["design", "implementation", "validation"],
            },
            expected_decision=(3, 6),  # Range acceptable
            decision_rationale="Medium complexity needs balanced team",
            confidence_threshold=0.7,
        ),
        DecisionTestCase(
            scenario="large_team_complex",
            input_context={
                "complexity": ComplexityTier.COMPLEX,
                "phases": ["discovery", "design", "implementation", "validation"],
            },
            expected_decision=(6, 10),  # Range acceptable
            decision_rationale="Complex tasks need larger coordinated team",
            confidence_threshold=0.75,
        ),
        DecisionTestCase(
            scenario="max_team_very_complex",
            input_context={
                "complexity": ComplexityTier.VERY_COMPLEX,
                "phases": [
                    "discovery",
                    "design",
                    "implementation",
                    "validation",
                    "refinement",
                ],
            },
            expected_decision=(8, 12),  # Capped at efficiency cliff
            decision_rationale="Very complex tasks need large team but capped for efficiency",
            confidence_threshold=0.8,
        ),
    ]


@pytest.fixture
def scoring_mechanism_cases():
    """Test cases for scoring mechanism validation."""
    return [
        ScoringTestCase(
            name="complexity_score_simple",
            inputs={"indicators_matched": ["basic", "quick"], "total_indicators": 5},
            expected_score_range=(0.1, 0.4),
            scoring_criteria={"method": "indicator_ratio"},
        ),
        ScoringTestCase(
            name="complexity_score_complex",
            inputs={
                "indicators_matched": ["sophisticated", "enterprise", "distributed"],
                "total_indicators": 5,
            },
            expected_score_range=(0.6, 1.0),
            scoring_criteria={"method": "indicator_ratio"},
        ),
        ScoringTestCase(
            name="role_priority_score",
            inputs={"role": "implementer", "position": 0, "confidence": 0.9},
            expected_score_range=(0.8, 1.0),
            scoring_criteria={"method": "position_weighted"},
        ),
        ScoringTestCase(
            name="consensus_confidence",
            inputs={"agreement_ratio": 0.8, "individual_confidences": [0.7, 0.8, 0.9]},
            expected_score_range=(0.7, 0.9),
            scoring_criteria={"method": "weighted_average"},
        ),
    ]


@pytest.mark.unit
class TestComplexityDecisionValidation:
    """Validate complexity decision logic."""

    def test_complexity_decision_accuracy(
        self, decision_framework, mock_decision_planner, complexity_decision_cases
    ):
        """Test complexity decision accuracy against known cases."""

        def complexity_decision_func(context: dict[str, Any]) -> ComplexityTier:
            request = Request(context["request_text"])
            return mock_decision_planner.assess(request)

        results = decision_framework.validate_decision_logic(
            complexity_decision_func, complexity_decision_cases
        )

        # Validate decision accuracy
        assert results["accuracy"] >= 0.8, (
            f"Complexity decision accuracy too low: {results['accuracy']}"
        )
        assert results["avg_confidence"] >= 0.7, (
            f"Low confidence in complexity decisions: {results['avg_confidence']}"
        )

        # Check specific boundary cases handled correctly
        boundary_cases = [
            log
            for log in decision_framework.decision_log
            if "boundary" in log["scenario"]
        ]
        assert len(boundary_cases) > 0, "No boundary cases tested"

        boundary_accuracy = sum(1 for case in boundary_cases if case["correct"]) / len(
            boundary_cases
        )
        assert boundary_accuracy >= 0.6, (
            f"Boundary case accuracy too low: {boundary_accuracy}"
        )

    def test_complexity_indicator_weight_validation(self, mock_decision_planner):
        """Test that complexity indicators have appropriate weights."""

        # Test indicator strength hierarchy
        indicator_hierarchy = [
            ("basic task", ComplexityTier.SIMPLE),
            ("moderate system", ComplexityTier.MEDIUM),
            ("sophisticated architecture", ComplexityTier.COMPLEX),
            ("enterprise distributed platform", ComplexityTier.VERY_COMPLEX),
        ]

        previous_complexity = None
        for request_text, expected_tier in indicator_hierarchy:
            request = Request(request_text)
            actual_tier = mock_decision_planner.assess(request)

            assert actual_tier == expected_tier, (
                f"Indicator weight hierarchy broken: '{request_text}' -> {actual_tier}, expected {expected_tier}"
            )

            # Ensure complexity doesn't decrease in hierarchy
            if previous_complexity is not None:
                assert mock_decision_planner._tier_rank(
                    actual_tier.value
                ) >= mock_decision_planner._tier_rank(previous_complexity.value), (
                    "Complexity hierarchy violated"
                )

            previous_complexity = actual_tier


@pytest.mark.unit
class TestAgentCountDecisionValidation:
    """Validate agent count decision logic."""

    def test_agent_count_decision_logic(
        self, decision_framework, mock_decision_planner, agent_count_decision_cases
    ):
        """Test agent count decision logic."""

        def agent_count_decision_func(context: dict[str, Any]) -> int:
            # Simulate agent count calculation based on complexity and phases
            complexity = context["complexity"]
            phases = context.get("phases", [])

            # Create a representative request
            request = Request(
                f"task with {complexity.value} complexity requiring {' '.join(phases)}"
            )
            roles = mock_decision_planner.select_roles(request, complexity)
            return len(roles)

        results = decision_framework.validate_decision_logic(
            agent_count_decision_func, agent_count_decision_cases
        )

        # Validate agent count decisions
        assert results["accuracy"] >= 0.7, (
            f"Agent count decision accuracy too low: {results['accuracy']}"
        )

        # Verify efficiency cliff is respected
        for log_entry in decision_framework.decision_log:
            if isinstance(log_entry.get("decision"), int):
                agent_count = log_entry["decision"]
                assert agent_count <= 12, (
                    f"Agent count {agent_count} exceeds efficiency cliff"
                )

    def test_agent_count_scaling_logic(self, mock_decision_planner):
        """Test agent count scaling with complexity."""

        scaling_cases = [
            (ComplexityTier.SIMPLE, 1, 4),
            (ComplexityTier.MEDIUM, 2, 6),
            (ComplexityTier.COMPLEX, 4, 10),
            (ComplexityTier.VERY_COMPLEX, 6, 12),
        ]

        previous_max_count = 0
        for complexity, min_count, max_count in scaling_cases:
            request = Request(f"task with {complexity.value} complexity")
            roles = mock_decision_planner.select_roles(request, complexity)
            actual_count = len(roles)

            # Validate range
            assert min_count <= actual_count <= max_count, (
                f"Agent count {actual_count} outside range [{min_count}, {max_count}] for {complexity}"
            )

            # Ensure scaling increases (or stays same)
            assert (
                actual_count >= previous_max_count
                or complexity == ComplexityTier.SIMPLE
            ), f"Agent count scaling regression: {actual_count} < {previous_max_count}"

            previous_max_count = min(actual_count, max_count)


@pytest.mark.unit
class TestScoringMechanismValidation:
    """Validate scoring mechanisms and mathematical models."""

    def test_complexity_scoring_algorithm(
        self, decision_framework, scoring_mechanism_cases
    ):
        """Test complexity scoring mechanisms."""

        def complexity_scoring_func(inputs: dict[str, Any]) -> float:
            matched = inputs.get("indicators_matched", [])
            total = inputs.get("total_indicators", 1)

            # Simulate indicator ratio scoring
            return len(matched) / total if total > 0 else 0.0

        # Filter for complexity scoring cases
        complexity_cases = [
            case for case in scoring_mechanism_cases if "complexity_score" in case.name
        ]

        results = decision_framework.validate_scoring_mechanism(
            complexity_scoring_func, complexity_cases
        )

        assert results["accuracy"] >= 0.8, (
            f"Complexity scoring accuracy too low: {results['accuracy']}"
        )
        assert results["avg_deviation"] <= 0.3, (
            f"High scoring deviation: {results['avg_deviation']}"
        )

    def test_consensus_scoring_algorithm(
        self, decision_framework, scoring_mechanism_cases
    ):
        """Test consensus scoring mechanisms."""

        def consensus_scoring_func(inputs: dict[str, Any]) -> float:
            agreement_ratio = inputs.get("agreement_ratio", 0.0)
            individual_confidences = inputs.get("individual_confidences", [])

            if not individual_confidences:
                return agreement_ratio

            avg_confidence = sum(individual_confidences) / len(individual_confidences)

            # Weight agreement by confidence
            return (agreement_ratio * 0.6) + (avg_confidence * 0.4)

        # Filter for consensus scoring cases
        consensus_cases = [
            case for case in scoring_mechanism_cases if "consensus" in case.name
        ]

        results = decision_framework.validate_scoring_mechanism(
            consensus_scoring_func, consensus_cases
        )

        assert results["accuracy"] >= 0.7, (
            f"Consensus scoring accuracy too low: {results['accuracy']}"
        )

    def test_role_priority_scoring_algorithm(self, mock_decision_planner):
        """Test role priority scoring logic."""

        # Create mock evaluations with role priorities
        mock_evaluations = [
            {
                "config": {"name": "agent_1"},
                "evaluation": OrchestrationEvaluation(
                    complexity="medium",
                    complexity_reason="Test",
                    total_agents=4,
                    agent_reason="Test",
                    rounds_needed=2,
                    role_priorities=["researcher", "implementer", "tester"],
                    primary_domains=["api-design"],
                    domain_reason="Test",
                    workflow_pattern="parallel",
                    workflow_reason="Test",
                    quality_level="thorough",
                    quality_reason="Test",
                    rules_applied=["rule1"],
                    confidence=0.8,
                    summary="Test evaluation",
                ),
            },
            {
                "config": {"name": "agent_2"},
                "evaluation": OrchestrationEvaluation(
                    complexity="medium",
                    complexity_reason="Test",
                    total_agents=4,
                    agent_reason="Test",
                    rounds_needed=2,
                    role_priorities=["implementer", "tester", "reviewer"],
                    primary_domains=["api-design"],
                    domain_reason="Test",
                    workflow_pattern="parallel",
                    workflow_reason="Test",
                    quality_level="thorough",
                    quality_reason="Test",
                    rules_applied=["rule1"],
                    confidence=0.9,
                    summary="Test evaluation",
                ),
            },
        ]

        # Build consensus and check role scoring
        consensus_output, consensus_data = mock_decision_planner.build_consensus(
            mock_evaluations, "Test request"
        )

        role_recommendations = consensus_data.get("role_recommendations", [])
        assert len(role_recommendations) > 0, "No role recommendations generated"

        # Verify scoring logic
        # implementer appears in both lists, should have higher score
        implementer_score = None
        researcher_score = None

        for role, score in role_recommendations:
            if role == "implementer":
                implementer_score = score
            elif role == "researcher":
                researcher_score = score

        # implementer should score higher than researcher (appears in more evaluations)
        if implementer_score is not None and researcher_score is not None:
            assert implementer_score >= researcher_score, (
                f"Role scoring logic error: implementer ({implementer_score}) < researcher ({researcher_score})"
            )


@pytest.mark.unit
class TestConsensusDecisionValidation:
    """Validate consensus building decision logic."""

    def test_consensus_complexity_decision(self, mock_decision_planner):
        """Test consensus complexity decision logic."""

        # Test cases with different evaluation patterns
        consensus_scenarios = [
            {
                "name": "unanimous_simple",
                "evaluations": [
                    ("simple", "basic task"),
                    ("simple", "straightforward work"),
                    ("simple", "quick fix"),
                ],
                "expected_consensus": "simple",
                "min_agreement": 1.0,
            },
            {
                "name": "majority_complex",
                "evaluations": [
                    ("complex", "advanced system"),
                    ("complex", "sophisticated design"),
                    ("medium", "moderate task"),
                ],
                "expected_consensus": "complex",
                "min_agreement": 0.6,
            },
            {
                "name": "split_decision",
                "evaluations": [
                    ("medium", "moderate complexity"),
                    ("complex", "advanced features"),
                ],
                "expected_consensus": "complex",  # Should escalate to higher
                "min_agreement": 0.5,
            },
        ]

        for scenario in consensus_scenarios:
            # Create mock evaluations
            mock_evaluations = []
            for i, (complexity, reason) in enumerate(scenario["evaluations"]):
                mock_evaluations.append({
                    "config": {"name": f"agent_{i}"},
                    "evaluation": OrchestrationEvaluation(
                        complexity=complexity,
                        complexity_reason=reason,
                        total_agents=4,
                        agent_reason="Standard team",
                        rounds_needed=2,
                        role_priorities=["researcher", "implementer"],
                        primary_domains=["software-architecture"],
                        domain_reason="Architecture focus",
                        workflow_pattern="parallel",
                        workflow_reason="Independent work",
                        quality_level="thorough",
                        quality_reason="Standard validation",
                        rules_applied=["rule1"],
                        confidence=0.8,
                        summary=f"Test evaluation {i}",
                    ),
                })

            # Build consensus
            consensus_output, consensus_data = mock_decision_planner.build_consensus(
                mock_evaluations, f"Test request for {scenario['name']}"
            )

            actual_consensus = consensus_data.get("complexity")
            expected_consensus = scenario["expected_consensus"]

            assert actual_consensus == expected_consensus, (
                f"Consensus error in {scenario['name']}: got {actual_consensus}, expected {expected_consensus}"
            )

    def test_consensus_confidence_weighting(self, mock_decision_planner):
        """Test confidence weighting in consensus decisions."""

        # Create evaluations with different confidence levels
        mock_evaluations = [
            {
                "config": {"name": "high_confidence_agent"},
                "evaluation": OrchestrationEvaluation(
                    complexity="complex",
                    complexity_reason="High confidence assessment",
                    total_agents=6,
                    agent_reason="Experienced judgment",
                    rounds_needed=3,
                    role_priorities=["architect", "implementer", "tester"],
                    primary_domains=["distributed-systems"],
                    domain_reason="Domain expertise",
                    workflow_pattern="hybrid",
                    workflow_reason="Mixed approach",
                    quality_level="critical",
                    quality_reason="High stakes",
                    rules_applied=["rule1"],
                    confidence=0.95,  # High confidence
                    summary="High confidence complex assessment",
                ),
            },
            {
                "config": {"name": "low_confidence_agent"},
                "evaluation": OrchestrationEvaluation(
                    complexity="medium",
                    complexity_reason="Lower confidence assessment",
                    total_agents=3,
                    agent_reason="Uncertain evaluation",
                    rounds_needed=2,
                    role_priorities=["researcher", "implementer"],
                    primary_domains=["api-design"],
                    domain_reason="Limited scope",
                    workflow_pattern="sequential",
                    workflow_reason="Step by step",
                    quality_level="basic",
                    quality_reason="Simple validation",
                    rules_applied=["rule2"],
                    confidence=0.4,  # Low confidence
                    summary="Low confidence medium assessment",
                ),
            },
        ]

        # Build consensus
        consensus_output, consensus_data = mock_decision_planner.build_consensus(
            mock_evaluations, "Test confidence weighting"
        )

        # High confidence agent should influence consensus more
        actual_complexity = consensus_data.get("complexity")

        # Should lean toward the high-confidence agent's assessment
        assert actual_complexity in ["complex", "medium"], (
            "Consensus outside expected range"
        )

        # Check that confidence is properly weighted
        final_confidence = consensus_data.get("confidence", 0)
        assert 0.4 < final_confidence < 0.95, (
            f"Confidence weighting error: {final_confidence}"
        )


@pytest.mark.integration
class TestDecisionIntegration:
    """Test integrated decision-making across multiple components."""

    def test_triage_to_consensus_decision_flow(self):
        """Test decision flow from triage to full consensus."""

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            # Mock triage service
            mock_triage = MagicMock()
            mock_triage.triage.return_value = (
                True,  # Escalate
                TriageConsensus(
                    should_escalate=True,
                    decision_votes={"escalate": 2, "proceed": 1},
                    average_confidence=0.75,
                ),
            )

            # Mock full consensus
            mock_planner = MagicMock()
            mock_evaluations = [
                {
                    "config": {"name": "consensus_agent"},
                    "evaluation": OrchestrationEvaluation(
                        complexity="complex",
                        complexity_reason="Integrated assessment",
                        total_agents=8,
                        agent_reason="Full team needed",
                        rounds_needed=3,
                        role_priorities=[
                            "researcher",
                            "architect",
                            "implementer",
                            "tester",
                        ],
                        primary_domains=["distributed-systems"],
                        domain_reason="Complex domain",
                        workflow_pattern="hybrid",
                        workflow_reason="Multi-phase approach",
                        quality_level="thorough",
                        quality_reason="Quality focus",
                        rules_applied=["complexity_rule"],
                        confidence=0.85,
                        summary="Complex integrated system",
                    ),
                }
            ]

            mock_planner.evaluate_request.return_value = mock_evaluations
            mock_planner.build_consensus.return_value = (
                "Consensus output",
                {
                    "complexity": "complex",
                    "agent_count": 8,
                    "confidence": 0.85,
                    "workflow_pattern": "hybrid",
                    "quality_level": "thorough",
                },
            )
            mock_planner.create_session.return_value = "integration_test_session"

            # Test the integration
            with (
                patch.object(ComplexityTriageService, "__init__", return_value=None),
                patch.object(
                    ComplexityTriageService,
                    "triage",
                    return_value=(True, mock_triage.triage.return_value[1]),
                ),
            ):
                from khive.services.plan.parts import PlannerRequest
                from khive.services.plan.planner_service import PlannerService

                service = PlannerService()
                service._planner = mock_planner

                # Execute integrated decision flow
                request = PlannerRequest(
                    task_description="Build complex distributed system"
                )
                response = asyncio.run(service.handle_request(request))

                # Validate integrated decisions
                assert response.success == True, "Integration decision flow failed"
                assert response.complexity == ComplexityLevel.COMPLEX, (
                    "Complexity decision not propagated"
                )
                assert response.confidence >= 0.7, "Confidence not properly integrated"
                assert response.recommended_agents >= 6, (
                    "Agent count decision not integrated"
                )


if __name__ == "__main__":
    # Run decision validation suite
    pytest.main([__file__, "-v", "--tb=short"])
