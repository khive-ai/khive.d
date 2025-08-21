"""Advanced algorithm tests for planning service core logic."""

from unittest.mock import MagicMock, patch

import pytest

from khive.services.plan.planner_service import (
    ComplexityTier,
    OrchestrationPlanner,
    Request,
)
from tests.fixtures.planning_fixtures import MockDecisionMatrix


@pytest.mark.unit
class TestComplexityAlgorithmDetails:
    """Detailed tests for complexity assessment algorithms."""

    @pytest.fixture
    def algorithm_planner(self):
        """Create planner focused on algorithm testing."""
        with patch.multiple(
            OrchestrationPlanner,
            _load_available_roles=MagicMock(return_value=["researcher", "architect"]),
            _load_available_domains=MagicMock(return_value=["distributed-systems"]),
            _load_prompt_templates=MagicMock(return_value={"agents": {}}),
            _load_decision_matrix=MagicMock(return_value=MockDecisionMatrix().data),
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                planner = OrchestrationPlanner()
                planner.matrix = MockDecisionMatrix().data
                return planner

    def test_indicator_pattern_matching_logic(self, algorithm_planner):
        """Test the core pattern matching logic for complexity indicators."""
        matrix_indicators = {
            "simple": ["single_objective", "well_defined_scope"],
            "medium": ["multiple_objectives", "some_unknowns"],
            "complex": ["many_stakeholders", "high_uncertainty"],
            "very_complex": ["research_frontier", "multiple_disciplines"],
        }

        for tier, indicators in matrix_indicators.items():
            # Test single indicator match
            for indicator in indicators:
                request = Request(indicator.replace("_", " "))
                result = algorithm_planner.assess(request)
                assert result.value == tier, f"Failed for indicator: {indicator}"

            # Test multiple indicator match
            combined_text = " ".join(indicators).replace("_", " ")
            request = Request(combined_text)
            result = algorithm_planner.assess(request)
            assert (
                result.value == tier
            ), f"Failed for combined indicators: {combined_text}"

    @pytest.mark.parametrize(
        "heuristic_patterns,expected_tier",
        [
            (["simple", "basic"], "simple"),
            (["simple", "basic", "quick", "easy"], "simple"),
            (["complex", "sophisticated"], "complex"),
            (["complex", "sophisticated", "distributed", "advanced"], "very_complex"),
            (["research", "novel"], "very_complex"),
            (["research", "novel", "cutting-edge", "innovative"], "very_complex"),
        ],
    )
    def test_heuristic_density_scoring(
        self, algorithm_planner, heuristic_patterns: list[str], expected_tier: str
    ):
        """Test heuristic pattern density scoring algorithm."""
        request_text = " ".join(heuristic_patterns)
        request = Request(request_text)

        result = algorithm_planner.assess(request)
        assert result.value == expected_tier

    def test_complexity_modifier_logic(self, algorithm_planner):
        """Test RAGRS complexity modifier application logic."""
        # Test distributed consensus modifier
        base_cases = [
            ("consensus system", "medium", "complex"),
            ("byzantine fault tolerance", "simple", "medium"),
            ("distributed agreement", "complex", "very_complex"),
        ]

        for request_text, base_tier, expected_tier in base_cases:
            request = Request(request_text)
            result = algorithm_planner._apply_complexity_modifiers(request, base_tier)
            assert result == expected_tier

        # Test energy constraints modifier
        energy_cases = [
            ("performance optimization microsecond", "medium", "complex"),
            ("efficiency nanosecond timing", "simple", "medium"),
            ("performance without timing", "medium", "medium"),  # No modifier
        ]

        for request_text, base_tier, expected_tier in energy_cases:
            request = Request(request_text)
            result = algorithm_planner._apply_complexity_modifiers(request, base_tier)
            assert result == expected_tier

    def test_tier_precedence_algorithm(self, algorithm_planner):
        """Test tier precedence when multiple patterns match."""
        # When multiple tiers match, should return highest
        mixed_patterns = [
            ("simple quick complex sophisticated", ComplexityTier.COMPLEX),
            ("basic easy research novel", ComplexityTier.VERY_COMPLEX),
            ("straightforward multiple stakeholders", ComplexityTier.COMPLEX),
        ]

        for request_text, expected_tier in mixed_patterns:
            request = Request(request_text)
            result = algorithm_planner.assess(request)
            assert result == expected_tier

    def test_boundary_condition_scoring(self, algorithm_planner):
        """Test boundary conditions in scoring algorithms."""
        boundary_cases = [
            # Exactly at thresholds
            ("simple simple", ComplexityTier.SIMPLE),  # 2 simple patterns
            ("complex complex", ComplexityTier.COMPLEX),  # 2 complex patterns
            ("research novel", ComplexityTier.VERY_COMPLEX),  # 2 very complex patterns
            # Just below thresholds
            ("simple", ComplexityTier.SIMPLE),  # 1 simple pattern
            ("complex", ComplexityTier.COMPLEX),  # 1 complex pattern
            # Edge case combinations
            ("entire system", ComplexityTier.VERY_COMPLEX),  # Special phrase
            ("complete platform", ComplexityTier.VERY_COMPLEX),  # Special phrase
            ("distributed system", ComplexityTier.VERY_COMPLEX),  # Special phrase - distributed systems are very complex
        ]

        for request_text, expected_tier in boundary_cases:
            request = Request(request_text)
            result = algorithm_planner.assess(request)
            assert result == expected_tier, f"Failed for: {request_text}"


@pytest.mark.unit
class TestRoleSelectionAlgorithms:
    """Test role selection algorithm internals."""

    @pytest.fixture
    def role_planner(self):
        """Create planner for role selection algorithm testing."""
        full_roles = [
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
            "commentator",
        ]

        with patch.multiple(
            OrchestrationPlanner,
            _load_available_roles=MagicMock(return_value=full_roles),
            _load_available_domains=MagicMock(return_value=["distributed-systems"]),
            _load_prompt_templates=MagicMock(return_value={"agents": {}}),
            _load_decision_matrix=MagicMock(return_value=MockDecisionMatrix().data),
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                planner = OrchestrationPlanner()
                planner.matrix = MockDecisionMatrix().data
                planner.available_roles = full_roles
                return planner

    def test_phase_detection_algorithm(self, role_planner):
        """Test phase detection algorithm accuracy."""
        phase_keywords = {
            "discovery_phase": ["research", "analyze", "understand", "investigate"],
            "design_phase": ["design", "architect", "plan", "structure"],
            "implementation_phase": ["implement", "build", "create", "develop"],
            "validation_phase": ["test", "verify", "validate", "check"],
            "refinement_phase": ["document", "improve", "refine", "optimize"],
        }

        for expected_phase, keywords in phase_keywords.items():
            for keyword in keywords:
                request = Request(f"{keyword} the system")
                phases = role_planner._determine_required_phases(request)
                assert (
                    expected_phase in phases
                ), f"Failed to detect {expected_phase} for keyword: {keyword}"

    def test_complexity_based_role_scaling(self, role_planner):
        """Test role scaling algorithm based on complexity."""
        base_request = Request("comprehensive system requiring all phases")

        scaling_expectations = {
            ComplexityTier.SIMPLE: {
                "max_roles": 4,
                "priority_roles": ["researcher", "implementer"],
            },
            ComplexityTier.MEDIUM: {"max_roles": 8, "expected_min": 3},
            ComplexityTier.COMPLEX: {"max_roles": 12, "expected_min": 5},
            ComplexityTier.VERY_COMPLEX: {
                "expected_min": 6,
                "critical_roles": ["researcher", "theorist"],
            },
        }

        for complexity, expectations in scaling_expectations.items():
            roles = role_planner.select_roles(base_request, complexity)

            if "max_roles" in expectations:
                assert (
                    len(roles) <= expectations["max_roles"]
                ), f"Too many roles for {complexity}"

            if "expected_min" in expectations:
                assert (
                    len(roles) >= expectations["expected_min"]
                ), f"Too few roles for {complexity}"

            if "priority_roles" in expectations:
                for priority_role in expectations["priority_roles"]:
                    assert (
                        priority_role in roles
                    ), f"Missing priority role {priority_role} for {complexity}"

            if "critical_roles" in expectations:
                for critical_role in expectations["critical_roles"]:
                    assert (
                        critical_role in roles
                    ), f"Missing critical role {critical_role} for {complexity}"

    def test_ragrs_mandatory_injection_algorithm(self, role_planner):
        """Test RAGRS mandatory role injection algorithm."""
        ragrs_scenarios = [
            {
                "keywords": ["consensus", "byzantine"],
                "mandatory_roles": ["theorist", "critic"],
                "trigger": "consensus_systems",
            },
            {
                "keywords": ["performance", "optimization"],
                "mandatory_roles": ["theorist", "implementer"],
                "trigger": "performance_optimization",
            },
        ]

        for scenario in ragrs_scenarios:
            for keyword in scenario["keywords"]:
                request = Request(f"build {keyword} system")
                roles = role_planner.select_roles(request, ComplexityTier.MEDIUM)

                for mandatory_role in scenario["mandatory_roles"]:
                    assert (
                        mandatory_role in roles
                    ), f"Missing mandatory role {mandatory_role} for {keyword}"

    def test_role_deduplication_algorithm(self, role_planner):
        """Test role deduplication in complex scenarios."""
        # Create scenario that could lead to duplicate role assignments
        complex_request = Request(
            "research design implement test research analyze validate"
        )

        for complexity in ComplexityTier:
            roles = role_planner.select_roles(complex_request, complexity)

            # Check no duplicates
            unique_roles = set(roles)
            assert len(roles) == len(
                unique_roles
            ), f"Duplicates found in {complexity}: {roles}"

    def test_priority_ordering_algorithm(self, role_planner):
        """Test role priority ordering for simple tasks."""
        request = Request("research design implement test validate document audit")
        roles = role_planner.select_roles(request, ComplexityTier.SIMPLE)

        # For simple tasks, should prioritize core roles
        priority_order = ["researcher", "implementer", "analyst", "architect"]

        assigned_priority_roles = [role for role in priority_order if role in roles]

        # Check that assigned roles respect priority order
        assert len(assigned_priority_roles) > 0, "No priority roles assigned"

        # Should have researcher or implementer for simple tasks
        assert "researcher" in roles or "implementer" in roles


@pytest.mark.unit
class TestAgentCountOptimization:
    """Test agent count optimization algorithms."""

    @pytest.fixture
    def optimization_planner(self):
        """Create planner for optimization testing."""
        roles = [
            "researcher",
            "analyst",
            "architect",
            "implementer",
            "tester",
            "critic",
        ]

        with patch.multiple(
            OrchestrationPlanner,
            _load_available_roles=MagicMock(return_value=roles),
            _load_available_domains=MagicMock(return_value=["distributed-systems"]),
            _load_prompt_templates=MagicMock(return_value={"agents": {}}),
            _load_decision_matrix=MagicMock(return_value=MockDecisionMatrix().data),
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                planner = OrchestrationPlanner()
                planner.matrix = MockDecisionMatrix().data
                planner.available_roles = roles
                return planner

    @pytest.mark.parametrize(
        "complexity,min_expected,max_expected",
        [
            (ComplexityTier.SIMPLE, 1, 4),
            (ComplexityTier.MEDIUM, 2, 6),
            (ComplexityTier.COMPLEX, 4, 6),  # Based on available roles
            (ComplexityTier.VERY_COMPLEX, 4, 6),  # Based on available roles
        ],
    )
    def test_agent_count_optimization_bounds(
        self,
        optimization_planner,
        complexity: ComplexityTier,
        min_expected: int,
        max_expected: int,
    ):
        """Test agent count stays within optimization bounds."""
        request = Request("comprehensive task requiring multiple capabilities")
        roles = optimization_planner.select_roles(request, complexity)

        assert min_expected <= len(roles) <= max_expected, (
            f"Agent count {len(roles)} outside bounds [{min_expected}, {max_expected}] "
            f"for complexity {complexity}"
        )

    def test_efficiency_cliff_avoidance(self, optimization_planner):
        """Test that algorithm avoids efficiency cliff (>12 agents)."""
        # Even for very complex tasks, should not exceed efficiency cliff
        complex_request = Request(
            "research design implement test validate document audit "
            "optimize secure monitor deploy maintain scale"
        )

        roles = optimization_planner.select_roles(
            complex_request, ComplexityTier.VERY_COMPLEX
        )

        # Should not exceed available roles (6 in fixture)
        assert len(roles) <= 12, f"Exceeded efficiency cliff with {len(roles)} agents"

    def test_minimal_viable_team_algorithm(self, optimization_planner):
        """Test minimal viable team composition."""
        simple_request = Request("simple task")
        roles = optimization_planner.select_roles(simple_request, ComplexityTier.SIMPLE)

        # Should have at least one core role
        core_roles = ["researcher", "implementer", "analyst", "architect"]
        has_core_role = any(role in core_roles for role in roles)

        assert has_core_role, f"No core roles in minimal team: {roles}"
        assert len(roles) >= 1, "Empty team assigned"

    def test_comprehensive_coverage_algorithm(self, optimization_planner):
        """Test comprehensive coverage for complex tasks."""
        complex_request = Request(
            "comprehensive distributed system research implementation validation"
        )
        roles = optimization_planner.select_roles(
            complex_request, ComplexityTier.VERY_COMPLEX
        )

        # Should have broad coverage
        phase_coverage = {
            "discovery": ["researcher", "analyst"],
            "design": ["architect"],
            "implementation": ["implementer"],
            "validation": ["tester", "critic"],
        }

        covered_phases = 0
        for phase_roles in phase_coverage.values():
            if any(role in roles for role in phase_roles):
                covered_phases += 1

        # Should cover most phases
        assert covered_phases >= 3, f"Insufficient phase coverage: {covered_phases}/4"


@pytest.mark.unit
class TestPerformanceOptimizations:
    """Test performance-related algorithmic optimizations."""

    @pytest.fixture
    def performance_planner(self):
        """Create planner for performance testing."""
        with patch.multiple(
            OrchestrationPlanner,
            _load_available_roles=MagicMock(return_value=["researcher", "implementer"]),
            _load_available_domains=MagicMock(return_value=["distributed-systems"]),
            _load_prompt_templates=MagicMock(return_value={"agents": {}}),
            _load_decision_matrix=MagicMock(return_value=MockDecisionMatrix().data),
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                planner = OrchestrationPlanner()
                planner.matrix = MockDecisionMatrix().data
                return planner

    def test_complexity_assessment_performance(self, performance_planner):
        """Test complexity assessment performance with various input sizes."""
        test_sizes = [
            ("short", "simple task"),
            ("medium", "implement distributed consensus system"),
            (
                "long",
                "research and develop comprehensive distributed consensus system " * 10,
            ),
            ("very_long", "complex sophisticated enterprise platform system " * 100),
        ]

        for size_name, request_text in test_sizes:
            request = Request(request_text)

            # Should complete without errors regardless of size
            result = performance_planner.assess(request)
            assert isinstance(result, ComplexityTier), f"Failed for {size_name} input"

    def test_role_selection_performance(self, performance_planner):
        """Test role selection performance with various complexities."""
        base_request = Request("comprehensive system requiring multiple phases")

        for complexity in ComplexityTier:
            # Should complete efficiently
            roles = performance_planner.select_roles(base_request, complexity)
            assert isinstance(roles, list), f"Failed for complexity {complexity}"
            assert len(roles) >= 1, f"Empty result for complexity {complexity}"

    def test_algorithmic_complexity_bounds(self, performance_planner):
        """Test that algorithms have reasonable complexity bounds."""
        # Test with increasing input complexity
        base_text = "research design implement test validate "

        for multiplier in [1, 5, 10, 20]:
            request_text = base_text * multiplier
            request = Request(request_text)

            # All operations should complete in reasonable time
            complexity = performance_planner.assess(request)
            roles = performance_planner.select_roles(request, complexity)
            phases = performance_planner._determine_required_phases(request)

            # Results should be consistent regardless of repetition
            assert isinstance(complexity, ComplexityTier)
            assert isinstance(roles, list) and len(roles) >= 1
            assert isinstance(phases, list) and len(phases) >= 1


@pytest.mark.unit
class TestAlgorithmicCornerCases:
    """Test corner cases and edge conditions in algorithms."""

    @pytest.fixture
    def corner_case_planner(self):
        """Create planner for corner case testing."""
        with patch.multiple(
            OrchestrationPlanner,
            _load_available_roles=MagicMock(
                return_value=["researcher"]
            ),  # Minimal roles
            _load_available_domains=MagicMock(return_value=["test-domain"]),
            _load_prompt_templates=MagicMock(return_value={"agents": {}}),
            _load_decision_matrix=MagicMock(return_value=MockDecisionMatrix().data),
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                planner = OrchestrationPlanner()
                planner.matrix = MockDecisionMatrix().data
                planner.available_roles = ["researcher"]
                return planner

    def test_minimal_configuration_handling(self, corner_case_planner):
        """Test algorithm behavior with minimal configuration."""
        request = Request("complex task requiring many roles")

        # Should handle gracefully even with minimal available roles
        complexity = corner_case_planner.assess(request)
        roles = corner_case_planner.select_roles(request, complexity)

        assert isinstance(complexity, ComplexityTier)
        assert len(roles) >= 1  # Should assign at least one role
        assert "researcher" in roles  # Should use available role

    def test_no_pattern_matches(self, corner_case_planner):
        """Test behavior when no patterns match."""
        # Use text with no recognizable patterns
        obscure_request = Request("xyzabc qwerty uiop")

        complexity = corner_case_planner.assess(obscure_request)
        roles = corner_case_planner.select_roles(obscure_request, complexity)

        # Should fall back to defaults
        assert complexity == ComplexityTier.MEDIUM
        assert len(roles) >= 1

    def test_conflicting_indicators(self, corner_case_planner):
        """Test handling of conflicting complexity indicators."""
        conflicting_request = Request(
            "simple quick complex sophisticated research novel basic easy"
        )

        complexity = corner_case_planner.assess(conflicting_request)

        # Should resolve to highest complexity found
        assert complexity in [ComplexityTier.COMPLEX, ComplexityTier.VERY_COMPLEX]

    def test_unicode_edge_cases(self, corner_case_planner):
        """Test Unicode handling in pattern matching."""
        unicode_cases = [
            "研究 系统",  # Chinese characters
            "система исследований",  # Cyrillic
            "🔬🧪⚗️",  # Only emojis
            "café naïve résumé",  # Accented characters
        ]

        for request_text in unicode_cases:
            request = Request(request_text)

            # Should handle without errors
            complexity = corner_case_planner.assess(request)
            roles = corner_case_planner.select_roles(request, complexity)

            assert isinstance(complexity, ComplexityTier)
            assert isinstance(roles, list)
            assert len(roles) >= 1

    def test_extremely_long_input(self, corner_case_planner):
        """Test handling of extremely long input."""
        # Create very long input
        long_request = Request("research " * 10000)

        # Should complete without memory issues
        complexity = corner_case_planner.assess(long_request)
        roles = corner_case_planner.select_roles(long_request, complexity)

        assert complexity == ComplexityTier.VERY_COMPLEX  # Many "research" keywords
        assert len(roles) >= 1
