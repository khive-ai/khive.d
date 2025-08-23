"""Test configuration and patterns for orchestration evaluation system.

This module provides:
- Test configuration constants and thresholds
- Reusable test patterns and utilities
- Test data validation helpers
- Performance and reliability testing standards
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock

import pytest

from khive.services.plan.models import OrchestrationEvaluation
from khive.services.plan.planner_service import ComplexityTier

# ============================================================================
# Test Configuration Constants
# ============================================================================


class TestConfig:
    """Central configuration for orchestration evaluation tests."""

    # Performance thresholds
    MAX_EVALUATION_TIME_MS = 5000
    MAX_CONCURRENT_EVALUATIONS = 20
    TARGET_COST_PER_EVALUATION = 0.0035
    MEMORY_LIMIT_MB = 512

    # Validation thresholds
    MIN_CONFIDENCE_SCORE = 0.0
    MAX_CONFIDENCE_SCORE = 1.0
    MIN_AGENT_COUNT = 1
    MAX_AGENT_COUNT = 20
    MIN_ROUNDS = 1
    MAX_ROUNDS = 6

    # Complexity assessment
    COMPLEXITY_TIERS = ["simple", "medium", "complex", "very_complex"]
    WORKFLOW_PATTERNS = ["parallel", "sequential", "hybrid"]
    QUALITY_LEVELS = ["basic", "thorough", "critical"]

    # Test timeouts (seconds)
    UNIT_TEST_TIMEOUT = 5.0
    INTEGRATION_TEST_TIMEOUT = 30.0
    PERFORMANCE_TEST_TIMEOUT = 60.0

    # Error tolerance
    CONFIDENCE_VARIANCE_THRESHOLD = 0.3
    COST_VARIANCE_THRESHOLD = 0.5
    TIME_VARIANCE_THRESHOLD = 0.2


# ============================================================================
# Test Data Validation Helpers
# ============================================================================


class TestDataValidator:
    """Validation utilities for test data integrity."""

    @staticmethod
    def validate_orchestration_evaluation(
        evaluation: OrchestrationEvaluation,
    ) -> list[str]:
        """Validate OrchestrationEvaluation for test integrity.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Complexity validation
        if evaluation.complexity not in TestConfig.COMPLEXITY_TIERS:
            errors.append(f"Invalid complexity: {evaluation.complexity}")

        # Agent count validation
        if not (
            TestConfig.MIN_AGENT_COUNT
            <= evaluation.total_agents
            <= TestConfig.MAX_AGENT_COUNT
        ):
            errors.append(f"Agent count out of range: {evaluation.total_agents}")

        # Confidence validation
        if not (
            TestConfig.MIN_CONFIDENCE_SCORE
            <= evaluation.confidence
            <= TestConfig.MAX_CONFIDENCE_SCORE
        ):
            errors.append(f"Confidence out of range: {evaluation.confidence}")

        # Rounds validation
        if not (
            TestConfig.MIN_ROUNDS <= evaluation.rounds_needed <= TestConfig.MAX_ROUNDS
        ):
            errors.append(f"Rounds out of range: {evaluation.rounds_needed}")

        # Role priorities validation
        if len(evaluation.role_priorities) == 0:
            errors.append("Empty role priorities list")

        if len(evaluation.role_priorities) > evaluation.total_agents:
            errors.append("More roles than agents")

        # String length validation
        if len(evaluation.complexity_reason) > 250:
            errors.append("Complexity reason too long")

        if len(evaluation.agent_reason) > 250:
            errors.append("Agent reason too long")

        if len(evaluation.summary) > 300:
            errors.append("Summary too long")

        return errors

    @staticmethod
    def validate_consistency(
        evaluations: list[OrchestrationEvaluation],
    ) -> dict[str, Any]:
        """Validate consistency across multiple evaluations.

        Returns:
            Dictionary with consistency metrics and warnings
        """
        if not evaluations:
            return {"valid": False, "error": "Empty evaluations list"}

        complexities = [e.complexity for e in evaluations]
        agent_counts = [e.total_agents for e in evaluations]
        confidences = [e.confidence for e in evaluations]

        # Calculate variance
        complexity_variance = len(set(complexities)) / len(complexities)
        agent_variance = max(agent_counts) - min(agent_counts) if agent_counts else 0
        confidence_variance = max(confidences) - min(confidences) if confidences else 0

        warnings = []

        if confidence_variance > TestConfig.CONFIDENCE_VARIANCE_THRESHOLD:
            warnings.append(f"High confidence variance: {confidence_variance:.2f}")

        if complexity_variance > 0.5:
            warnings.append(f"High complexity disagreement: {complexity_variance:.2f}")

        if agent_variance > 10:
            warnings.append(f"High agent count variance: {agent_variance}")

        return {
            "valid": True,
            "complexity_variance": complexity_variance,
            "agent_variance": agent_variance,
            "confidence_variance": confidence_variance,
            "warnings": warnings,
            "evaluations_count": len(evaluations),
        }


# ============================================================================
# Test Pattern Utilities
# ============================================================================


class TestPatterns:
    """Reusable test patterns for orchestration evaluation testing."""

    @staticmethod
    async def measure_async_performance(
        async_func: Callable,
        *args,
        expected_max_time: float = TestConfig.MAX_EVALUATION_TIME_MS / 1000,
        **kwargs,
    ) -> tuple[Any, float]:
        """Measure performance of async function.

        Returns:
            Tuple of (result, execution_time_seconds)
        """
        start_time = time.time()
        result = await async_func(*args, **kwargs)
        end_time = time.time()

        execution_time = end_time - start_time

        if execution_time > expected_max_time:
            pytest.fail(
                f"Performance test failed: {execution_time:.3f}s > {expected_max_time:.3f}s"
            )

        return result, execution_time

    @staticmethod
    def assert_complexity_progression(evaluations: list[OrchestrationEvaluation]):
        """Assert that evaluations show logical complexity progression."""
        complexity_order = {"simple": 1, "medium": 2, "complex": 3, "very_complex": 4}

        for evaluation in evaluations:
            complexity_level = complexity_order[evaluation.complexity]
            agent_count = evaluation.total_agents

            # Basic progression checks
            if complexity_level == 1:  # simple
                assert agent_count <= 4, (
                    f"Simple tasks should have ≤4 agents, got {agent_count}"
                )
            elif complexity_level == 2:  # medium
                assert 3 <= agent_count <= 7, (
                    f"Medium tasks should have 3-7 agents, got {agent_count}"
                )
            elif complexity_level == 3:  # complex
                assert 5 <= agent_count <= 12, (
                    f"Complex tasks should have 5-12 agents, got {agent_count}"
                )
            elif complexity_level == 4:  # very_complex
                assert agent_count >= 8, (
                    f"Very complex tasks should have ≥8 agents, got {agent_count}"
                )

    @staticmethod
    def assert_role_consistency(evaluations: list[OrchestrationEvaluation]):
        """Assert role assignments are consistent with complexity and requirements."""
        critical_roles = ["researcher", "implementer"]
        validation_roles = ["tester", "critic", "auditor"]

        for evaluation in evaluations:
            roles = evaluation.role_priorities

            # Critical roles should always be present
            has_critical = any(role in roles for role in critical_roles)
            assert has_critical, f"Missing critical roles in: {roles}"

            # Complex tasks should have validation roles
            if evaluation.complexity in ["complex", "very_complex"]:
                has_validation = any(role in roles for role in validation_roles)
                assert has_validation, f"Complex task missing validation roles: {roles}"

            # Role count should not exceed agent count
            assert len(roles) <= evaluation.total_agents, (
                f"More roles ({len(roles)}) than agents ({evaluation.total_agents})"
            )

    @staticmethod
    def create_mock_evaluation(
        complexity: str = "medium",
        agents: int = 5,
        confidence: float = 0.8,
        **overrides,
    ) -> OrchestrationEvaluation:
        """Create a mock evaluation with sensible defaults."""
        defaults = {
            "complexity": complexity,
            "complexity_reason": f"Task assessed as {complexity} complexity",
            "total_agents": agents,
            "agent_reason": f"Requires {agents} agents for proper coverage",
            "rounds_needed": 2,
            "role_priorities": ["researcher", "architect", "implementer"][
                : agents // 2 + 1
            ],
            "primary_domains": ["distributed-systems"],
            "domain_reason": "Core domain for the task",
            "workflow_pattern": "parallel",
            "workflow_reason": "Tasks can be executed concurrently",
            "quality_level": "thorough",
            "quality_reason": "Standard quality requirements",
            "rules_applied": ["complexity_assessment"],
            "confidence": confidence,
            "summary": f"Mock {complexity} complexity evaluation",
        }

        # Apply overrides
        defaults.update(overrides)

        return OrchestrationEvaluation(**defaults)


# ============================================================================
# Test Scenarios and Data
# ============================================================================


@dataclass
class ComplexityTestCase:
    """Test case for complexity assessment."""

    request_text: str
    expected_complexity: ComplexityTier
    expected_agents_range: tuple[int, int]
    description: str
    should_trigger_ragrs: bool = False
    expected_modifiers: list[str] = None

    def __post_init__(self):
        if self.expected_modifiers is None:
            self.expected_modifiers = []


@dataclass
class PerformanceTestCase:
    """Test case for performance validation."""

    scenario_name: str
    concurrent_operations: int
    max_time_seconds: float
    expected_success_rate: float
    memory_limit_mb: int | None = None

    def __post_init__(self):
        if self.memory_limit_mb is None:
            self.memory_limit_mb = TestConfig.MEMORY_LIMIT_MB


class TestDataSets:
    """Predefined test data sets for consistent testing."""

    COMPLEXITY_CASES = [
        ComplexityTestCase(
            request_text="Create a simple REST API endpoint",
            expected_complexity=ComplexityTier.SIMPLE,
            expected_agents_range=(1, 3),
            description="Basic single-service implementation",
        ),
        ComplexityTestCase(
            request_text="Build microservices architecture with event sourcing",
            expected_complexity=ComplexityTier.COMPLEX,
            expected_agents_range=(6, 10),
            description="Multi-service architecture with advanced patterns",
        ),
        ComplexityTestCase(
            request_text="Research novel Byzantine fault tolerance algorithms for distributed consensus",
            expected_complexity=ComplexityTier.VERY_COMPLEX,
            expected_agents_range=(10, 15),
            description="Research-level distributed systems work",
            should_trigger_ragrs=True,
            expected_modifiers=["distributed_consensus"],
        ),
        ComplexityTestCase(
            request_text="Optimize performance for microsecond latency requirements",
            expected_complexity=ComplexityTier.COMPLEX,
            expected_agents_range=(5, 8),
            description="Performance optimization with tight constraints",
            should_trigger_ragrs=True,
            expected_modifiers=["energy_constraints"],
        ),
    ]

    PERFORMANCE_CASES = [
        PerformanceTestCase(
            scenario_name="single_evaluation",
            concurrent_operations=1,
            max_time_seconds=2.0,
            expected_success_rate=1.0,
        ),
        PerformanceTestCase(
            scenario_name="moderate_concurrency",
            concurrent_operations=5,
            max_time_seconds=5.0,
            expected_success_rate=1.0,
        ),
        PerformanceTestCase(
            scenario_name="high_concurrency",
            concurrent_operations=20,
            max_time_seconds=10.0,
            expected_success_rate=0.95,
        ),
        PerformanceTestCase(
            scenario_name="stress_test",
            concurrent_operations=50,
            max_time_seconds=30.0,
            expected_success_rate=0.8,
            memory_limit_mb=1024,
        ),
    ]

    EDGE_CASES = [
        ("", "Empty request handling"),
        ("a", "Single character request"),
        ("x" * 10000, "Extremely long request"),
        ("🔬🧪🎯", "Unicode-only request"),
        ("UPPERCASE REQUEST", "Case handling"),
        ("request with\nnewlines\nand\ttabs", "Whitespace handling"),
    ]

    RAGRS_TRIGGERS = [
        {
            "keywords": ["consensus", "byzantine", "distributed"],
            "expected_roles": ["theorist", "critic"],
            "complexity_modifier": "+1 level",
            "description": "Distributed consensus system triggers",
        },
        {
            "keywords": ["performance", "optimization", "microsecond"],
            "expected_roles": ["theorist", "implementer"],
            "complexity_modifier": "+1 level if microsecond_timing",
            "description": "Performance optimization triggers",
        },
        {
            "keywords": ["knowledge", "memory", "learning"],
            "expected_roles": ["researcher", "analyst"],
            "complexity_modifier": "none",
            "description": "Knowledge management triggers",
        },
    ]


# ============================================================================
# Test Execution Patterns
# ============================================================================


class TestExecutionPatterns:
    """Patterns for organizing and executing test suites."""

    @staticmethod
    def parametric_complexity_test(test_cases: list[ComplexityTestCase]):
        """Generate parametric test for complexity assessment."""
        return pytest.mark.parametrize(
            "test_case", test_cases, ids=[case.description for case in test_cases]
        )

    @staticmethod
    def parametric_performance_test(test_cases: list[PerformanceTestCase]):
        """Generate parametric test for performance validation."""
        return pytest.mark.parametrize(
            "test_case", test_cases, ids=[case.scenario_name for case in test_cases]
        )

    @staticmethod
    async def run_concurrent_evaluations(
        evaluator_func: Callable,
        request_data: list[Any],
        max_concurrent: int = TestConfig.MAX_CONCURRENT_EVALUATIONS,
    ) -> list[Any]:
        """Run evaluations concurrently with limits."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def limited_evaluation(data):
            async with semaphore:
                return await evaluator_func(data)

        tasks = [limited_evaluation(data) for data in request_data]
        return await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def validate_test_results(
        results: list[Any], expected_count: int, success_threshold: float = 0.95
    ) -> dict[str, Any]:
        """Validate test execution results."""
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful
        success_rate = successful / len(results) if results else 0.0

        validation = {
            "total_tests": len(results),
            "successful": successful,
            "failed": failed,
            "success_rate": success_rate,
            "meets_threshold": success_rate >= success_threshold,
            "expected_count": expected_count,
            "count_matches": len(results) == expected_count,
        }

        if not validation["meets_threshold"]:
            pytest.fail(
                f"Test success rate {success_rate:.2%} below threshold {success_threshold:.2%}"
            )

        if not validation["count_matches"]:
            pytest.fail(f"Expected {expected_count} results, got {len(results)}")

        return validation


# ============================================================================
# Mock Configuration Helpers
# ============================================================================


class MockConfigurationHelper:
    """Helper for creating consistent mock configurations."""

    @staticmethod
    def create_mock_openai_response(evaluation: OrchestrationEvaluation):
        """Create standardized mock OpenAI response."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = evaluation
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 400
        mock_response.usage.completion_tokens = 200
        mock_response.usage.total_tokens = 600
        return mock_response

    @staticmethod
    def create_mock_cost_tracker(budget: float = 1.0):
        """Create standardized mock cost tracker."""
        tracker = Mock()
        tracker.get_token_budget.return_value = 10000
        tracker.get_latency_budget.return_value = 60
        tracker.get_cost_budget.return_value = budget
        tracker.add_request.return_value = 0.001
        tracker.total_cost = 0.05
        tracker.is_over_budget.return_value = False
        return tracker

    @staticmethod
    def create_mock_timeout_config():
        """Create standardized mock timeout configuration."""
        config = Mock()
        config.agent_execution_timeout = 300.0
        config.phase_completion_timeout = 1800.0
        config.total_orchestration_timeout = 3600.0
        config.max_retries = 3
        config.retry_delay = 5.0
        config.escalation_enabled = True
        config.performance_threshold = 0.9
        config.timeout_reduction_factor = 0.3
        return config
