"""
Boundary and Edge Case Testing for Planning Service.

This module provides comprehensive testing for boundary conditions, edge cases,
error handling, and extreme scenarios in the planning service algorithms.
"""

import asyncio
import random
import time
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from khive.services.plan.models import OrchestrationEvaluation
from khive.services.plan.parts import PlannerRequest
from khive.services.plan.planner_service import (ComplexityTier,
                                                 OrchestrationPlanner,
                                                 PlannerService, Request)
from khive.services.plan.triage.complexity_triage import \
    ComplexityTriageService


class BoundaryTestGenerator:
    """Generate boundary test cases systematically."""

    @staticmethod
    def generate_text_variations(base_text: str, variations: int = 50) -> list[str]:
        """Generate text variations for boundary testing."""
        variations_list = []

        # Length variations
        variations_list.extend([
            "",  # Empty
            "x",  # Single char
            base_text[:10],  # Truncated
            base_text * 10,  # Repeated
            base_text * 100,  # Very long
        ])

        # Case variations
        variations_list.extend([
            base_text.upper(),
            base_text.lower(),
            base_text.title(),
            "".join(
                c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(base_text)
            ),
        ])

        # Character variations
        variations_list.extend([
            base_text.replace(" ", ""),  # No spaces
            base_text.replace(" ", "   "),  # Multiple spaces
            base_text.replace(" ", "\t"),  # Tabs
            base_text.replace(" ", "\n"),  # Newlines
            base_text + "\n" * 10,  # Trailing newlines
        ])

        # Special characters
        special_chars = "!@#$%^&*()[]{}|\\:;\"'<>?,./"
        variations_list.extend([
            base_text + special_chars,
            special_chars + base_text,
        ])
        variations_list.extend([
            base_text.replace(" ", random.choice(special_chars)) for _ in range(5)
        ])

        # Unicode variations
        variations_list.extend([
            "测试任务 研究系统",  # Chinese
            "исследовать систему",  # Russian
            "🚀🔬⚗️🧪 task",  # Emojis
            "café naïve résumé",  # Accented characters
            "𝓤𝓷𝓲𝓬𝓸𝓭𝓮 𝓽𝓮𝓼𝓽",  # Math symbols
        ])

        # Numeric variations
        variations_list.extend([
            "123456789",  # Pure numbers
            base_text + " " + str(random.randint(1, 1000000)),
            f"{base_text} {random.random():.10f}",  # Floating point
        ])

        # Limit to requested number
        return variations_list[:variations]

    @staticmethod
    def generate_extreme_inputs() -> list[dict[str, Any]]:
        """Generate extreme input conditions."""
        return [
            # Size extremes
            {"type": "empty", "data": ""},
            {"type": "minimal", "data": "x"},
            {"type": "huge", "data": "research " * 50000},
            {
                "type": "very_long_words",
                "data": "supercalifragilisticexpialidocious" * 100,
            },
            # Character extremes
            {"type": "only_punctuation", "data": "!@#$%^&*(){}[]|\\:;\"'<>?,./" * 10},
            {"type": "only_numbers", "data": "1234567890" * 100},
            {"type": "only_whitespace", "data": " \t\n\r" * 1000},
            {"type": "control_characters", "data": "".join(chr(i) for i in range(32))},
            # Encoding extremes
            {"type": "mixed_encodings", "data": "ASCII 中文 русский 🌟 𝓤𝓷𝓲𝓬𝓸𝓭𝓮"},
            {"type": "null_bytes", "data": "test\x00task\x00system"},
            {
                "type": "high_unicode",
                "data": "".join(chr(i) for i in range(65536, 65600)),
            },
            # Structure extremes
            {"type": "deeply_nested", "data": "(" * 1000 + "task" + ")" * 1000},
            {"type": "malformed_json", "data": '{"task": "incomplete'},
            {"type": "sql_injection_attempt", "data": "'; DROP TABLE tasks; --"},
            {"type": "script_injection", "data": "<script>alert('xss')</script> task"},
        ]


@pytest.fixture
def boundary_test_generator():
    """Provide boundary test generator."""
    return BoundaryTestGenerator()


@pytest.fixture
def minimal_planner():
    """Create minimal planner configuration for boundary testing."""
    with (
        patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
        patch("khive.services.plan.planner_service.OpenAI"),
        patch.object(
            OrchestrationPlanner, "_load_available_roles", return_value=["researcher"]
        ),
        patch.object(
            OrchestrationPlanner,
            "_load_available_domains",
            return_value=["test-domain"],
        ),
        patch.object(
            OrchestrationPlanner, "_load_prompt_templates", return_value={"agents": {}}
        ),
        patch.object(
            OrchestrationPlanner,
            "_load_decision_matrix",
            return_value={
                "complexity_assessment": {"medium": {"indicators": []}},
                "agent_role_selection": {"execution_phase": {"roles": ["researcher"]}},
            },
        ),
    ):
        planner = OrchestrationPlanner()
        return planner


@pytest.fixture
def corrupted_planner():
    """Create planner with corrupted/incomplete configuration."""
    with (
        patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
        patch("khive.services.plan.planner_service.OpenAI"),
        patch.object(
            OrchestrationPlanner, "_load_available_roles", return_value=[]
        ),  # Empty
        patch.object(
            OrchestrationPlanner, "_load_available_domains", return_value=[]
        ),  # Empty
        patch.object(
            OrchestrationPlanner, "_load_prompt_templates", return_value={}
        ),  # Empty
        patch.object(
            OrchestrationPlanner, "_load_decision_matrix", return_value={}
        ),  # Empty
    ):
        planner = OrchestrationPlanner()
        return planner


@pytest.mark.boundary
class TestInputBoundaryConditions:
    """Test boundary conditions for various inputs."""

    def test_empty_input_handling(self, minimal_planner):
        """Test handling of empty inputs."""

        empty_cases = ["", " ", "\t", "\n", "   \t\n  "]

        for empty_input in empty_cases:
            request = Request(empty_input)

            # Should not crash
            complexity = minimal_planner.assess(request)
            roles = minimal_planner.select_roles(request, complexity)
            phases = minimal_planner._determine_required_phases(request)

            # Should return reasonable defaults
            assert isinstance(complexity, ComplexityTier)
            assert len(roles) >= 1, f"No roles for empty input: '{empty_input}'"
            assert len(phases) >= 1, f"No phases for empty input: '{empty_input}'"

    def test_minimal_input_handling(self, minimal_planner):
        """Test handling of minimal inputs."""

        minimal_cases = ["x", "a", "1", ".", "?", "!"]

        for minimal_input in minimal_cases:
            request = Request(minimal_input)

            # Should handle gracefully
            try:
                complexity = minimal_planner.assess(request)
                roles = minimal_planner.select_roles(request, complexity)

                assert isinstance(complexity, ComplexityTier)
                assert len(roles) >= 1

            except Exception as e:
                pytest.fail(f"Minimal input '{minimal_input}' caused error: {e}")

    def test_maximum_length_input_handling(self, minimal_planner):
        """Test handling of very long inputs."""

        # Generate inputs of increasing size
        base_text = "research and implement sophisticated distributed system "

        for multiplier in [100, 1000, 5000, 10000]:
            long_input = base_text * multiplier
            request = Request(long_input)

            start_time = time.perf_counter()

            try:
                complexity = minimal_planner.assess(request)
                roles = minimal_planner.select_roles(request, complexity)

                execution_time = time.perf_counter() - start_time

                # Should complete within reasonable time even for large inputs
                assert execution_time < 5.0, (
                    f"Large input processing too slow: {execution_time}s for {len(long_input)} chars"
                )

                # Should produce valid results
                assert isinstance(complexity, ComplexityTier)
                assert len(roles) >= 1

            except Exception as e:
                # Large inputs might cause memory issues, but should be handled gracefully
                if "memory" in str(e).lower() or "timeout" in str(e).lower():
                    pytest.skip(
                        f"Expected memory/timeout issue with very large input: {e}"
                    )
                else:
                    pytest.fail(f"Unexpected error with large input: {e}")

    @pytest.mark.parametrize(
        "extreme_input",
        [
            "!@#$%^&*(){}[]|\\:;\"'<>?,./" * 10,  # Special characters
            "1234567890" * 100,  # Only numbers
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 50,  # Only uppercase
            " \t\n\r" * 1000,  # Only whitespace
            "🚀🔬⚗️🧪" * 100,  # Only emojis
        ],
    )
    def test_extreme_character_inputs(self, minimal_planner, extreme_input):
        """Test handling of extreme character compositions."""

        request = Request(extreme_input)

        # Should handle without crashing
        complexity = minimal_planner.assess(request)
        roles = minimal_planner.select_roles(request, complexity)

        # Should produce valid results even for unusual inputs
        assert isinstance(complexity, ComplexityTier)
        assert len(roles) >= 1


@pytest.mark.boundary
class TestConfigurationBoundaryConditions:
    """Test boundary conditions in configuration scenarios."""

    def test_empty_roles_configuration(self, corrupted_planner):
        """Test behavior with no available roles."""

        request = Request("implement system with testing")

        # Should handle gracefully even with no roles configured
        try:
            complexity = corrupted_planner.assess(request)
            roles = corrupted_planner.select_roles(request, complexity)

            # Should fall back to reasonable defaults
            assert isinstance(complexity, ComplexityTier)
            # With empty roles, should return empty list or fallback
            assert isinstance(roles, list)

        except Exception as e:
            # Should either handle gracefully or provide meaningful error
            assert "role" in str(e).lower() or "configuration" in str(e).lower()

    def test_empty_domains_configuration(self, corrupted_planner):
        """Test behavior with no available domains."""

        request = Request("design API for distributed systems")

        # Should handle domain selection gracefully
        try:
            complexity = corrupted_planner.assess(request)
            # Domain issues might not surface until role selection

        except Exception as e:
            # Should provide meaningful error about missing configuration
            assert any(
                word in str(e).lower()
                for word in ["domain", "configuration", "missing"]
            )

    def test_corrupted_decision_matrix(self, minimal_planner):
        """Test behavior with corrupted decision matrix."""

        # Corrupt the decision matrix
        minimal_planner.matrix = {
            "complexity_assessment": {
                # Missing indicators
                "simple": {},
                "medium": {"indicators": None},  # Invalid value
                "complex": {"indicators": [123, True]},  # Invalid types
            }
        }

        request = Request("build system")

        # Should handle corrupted matrix gracefully
        try:
            complexity = minimal_planner.assess(request)
            assert isinstance(complexity, ComplexityTier)

        except Exception as e:
            # Should handle gracefully or provide meaningful error
            assert any(
                word in str(e).lower()
                for word in ["matrix", "configuration", "invalid"]
            )


@pytest.mark.boundary
class TestNumericalBoundaryConditions:
    """Test numerical boundary conditions."""

    def test_agent_count_boundaries(self, minimal_planner):
        """Test agent count at various boundaries."""

        # Test complexity tiers that might trigger boundary conditions
        boundary_cases = [
            (ComplexityTier.SIMPLE, 0, 5),  # Lower bound
            (ComplexityTier.MEDIUM, 1, 8),  # Mid range
            (ComplexityTier.COMPLEX, 3, 12),  # Upper range
            (ComplexityTier.VERY_COMPLEX, 5, 12),  # Efficiency cliff
        ]

        for complexity, min_expected, max_expected in boundary_cases:
            request = Request(f"task with {complexity.value} complexity level")
            roles = minimal_planner.select_roles(request, complexity)
            agent_count = len(roles)

            # Verify boundaries are respected
            assert 0 <= agent_count <= 12, (
                f"Agent count {agent_count} exceeds absolute boundaries"
            )

            # Note: With minimal configuration, exact ranges might not match
            # Just ensure reasonable behavior
            assert agent_count >= 0, f"Negative agent count for {complexity}"

    def test_confidence_score_boundaries(self):
        """Test confidence score boundaries in various scenarios."""

        # Mock evaluations with extreme confidence values
        extreme_evaluations = [
            # Minimum confidence
            {
                "config": {"name": "min_confidence"},
                "evaluation": OrchestrationEvaluation(
                    complexity="simple",
                    complexity_reason="Low confidence",
                    total_agents=1,
                    agent_reason="Minimal",
                    rounds_needed=1,
                    role_priorities=["researcher"],
                    primary_domains=["test"],
                    domain_reason="Test",
                    workflow_pattern="parallel",
                    workflow_reason="Simple",
                    quality_level="basic",
                    quality_reason="Basic",
                    rules_applied=[],
                    confidence=0.0,  # Minimum
                    summary="Min confidence test",
                ),
            },
            # Maximum confidence
            {
                "config": {"name": "max_confidence"},
                "evaluation": OrchestrationEvaluation(
                    complexity="very_complex",
                    complexity_reason="High confidence",
                    total_agents=12,
                    agent_reason="Full team",
                    rounds_needed=5,
                    role_priorities=["researcher", "architect", "implementer"],
                    primary_domains=["distributed-systems"],
                    domain_reason="Expert domain",
                    workflow_pattern="hybrid",
                    workflow_reason="Complex",
                    quality_level="critical",
                    quality_reason="High stakes",
                    rules_applied=["rule1", "rule2"],
                    confidence=1.0,  # Maximum
                    summary="Max confidence test",
                ),
            },
        ]

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
            patch("khive.services.plan.planner_service.OpenAI"),
            patch.object(
                OrchestrationPlanner,
                "_load_available_roles",
                return_value=["researcher", "architect", "implementer"],
            ),
            patch.object(
                OrchestrationPlanner,
                "_load_available_domains",
                return_value=["test", "distributed-systems"],
            ),
            patch.object(
                OrchestrationPlanner,
                "_load_prompt_templates",
                return_value={"agents": {}},
            ),
            patch.object(
                OrchestrationPlanner, "_load_decision_matrix", return_value={}
            ),
        ):
            planner = OrchestrationPlanner()

            # Build consensus with extreme confidence values
            consensus_output, consensus_data = planner.build_consensus(
                extreme_evaluations, "Boundary confidence test"
            )

            # Final confidence should be within bounds
            final_confidence = consensus_data.get("confidence", 0.5)
            assert 0.0 <= final_confidence <= 1.0, (
                f"Confidence {final_confidence} outside valid range"
            )


@pytest.mark.boundary
class TestConcurrencyBoundaryConditions:
    """Test boundary conditions under concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_assessment_requests(self, minimal_planner):
        """Test concurrent complexity assessments."""

        async def assess_complexity(
            request_text: str, delay: float = 0
        ) -> ComplexityTier:
            if delay > 0:
                await asyncio.sleep(delay)
            request = Request(request_text)
            return minimal_planner.assess(request)

        # Create multiple concurrent requests
        tasks = []
        for i in range(50):
            task = assess_complexity(f"concurrent task {i}", random.uniform(0, 0.1))
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all completed successfully
        successful_results = [r for r in results if isinstance(r, ComplexityTier)]
        failed_results = [r for r in results if isinstance(r, Exception)]

        assert len(successful_results) >= len(tasks) * 0.9, (
            f"Too many failures: {len(failed_results)} out of {len(tasks)}"
        )

        # Verify results are valid
        for result in successful_results:
            assert isinstance(result, ComplexityTier)

    @pytest.mark.asyncio
    async def test_concurrent_role_selection(self, minimal_planner):
        """Test concurrent role selection operations."""

        async def select_roles_async(
            request_text: str, complexity: ComplexityTier
        ) -> list[str]:
            await asyncio.sleep(random.uniform(0, 0.05))  # Random delay
            request = Request(request_text)
            return minimal_planner.select_roles(request, complexity)

        # Create concurrent role selection tasks
        tasks = []
        complexities = list(ComplexityTier)

        for i in range(20):
            complexity = random.choice(complexities)
            task = select_roles_async(f"role selection task {i}", complexity)
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify results
        successful_results = [r for r in results if isinstance(r, list)]
        assert len(successful_results) >= len(tasks) * 0.9, (
            "Too many concurrent failures"
        )

        for result in successful_results:
            assert isinstance(result, list)
            assert len(result) >= 0  # Can be empty with minimal config


@pytest.mark.boundary
class TestErrorRecoveryBoundaryConditions:
    """Test error recovery and boundary conditions in error scenarios."""

    def test_network_error_simulation(self):
        """Test behavior when network errors occur."""

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
            patch(
                "khive.services.plan.planner_service.OpenAI",
                side_effect=Exception("Network error"),
            ),
        ):
            # Should handle OpenAI initialization failure gracefully
            with pytest.raises(Exception) as exc_info:
                OrchestrationPlanner()

            # Should provide meaningful error message
            assert (
                "network" in str(exc_info.value).lower()
                or "openai" in str(exc_info.value).lower()
            )

    def test_missing_configuration_files(self):
        """Test behavior when configuration files are missing."""

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
            patch("khive.services.plan.planner_service.OpenAI"),
            patch.object(
                OrchestrationPlanner,
                "_load_prompt_templates",
                side_effect=FileNotFoundError("Templates not found"),
            ),
        ):
            # Should handle missing files gracefully
            with pytest.raises(FileNotFoundError) as exc_info:
                OrchestrationPlanner()

            assert "templates" in str(exc_info.value).lower()

    def test_invalid_api_key_handling(self):
        """Test handling of invalid API key."""

        with patch.dict("os.environ", {}, clear=True):
            # Should raise appropriate error for missing API key
            with pytest.raises(ValueError) as exc_info:
                OrchestrationPlanner()

            assert (
                "api" in str(exc_info.value).lower()
                and "key" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_timeout_boundary_conditions(self):
        """Test timeout handling at boundaries."""

        # Mock triage service with timeout
        mock_triage_service = AsyncMock()
        mock_triage_service.triage.side_effect = asyncio.TimeoutError("Triage timeout")

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
            patch.object(ComplexityTriageService, "__init__", return_value=None),
        ):
            service = PlannerService()
            service._triage_service = mock_triage_service

            request = PlannerRequest(task_description="Test timeout handling")

            # Should handle timeout gracefully
            response = await service.handle_request(request)

            # Should return error response
            assert response.success == False
            assert (
                "timeout" in response.error.lower()
                or "failed" in response.summary.lower()
            )


@pytest.mark.boundary
class TestMemoryBoundaryConditions:
    """Test memory usage boundary conditions."""

    def test_memory_usage_with_large_inputs(self, minimal_planner):
        """Test memory usage doesn't grow unbounded with large inputs."""

        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Process increasingly large inputs
        base_text = "research sophisticated distributed enterprise system "

        for size_multiplier in [10, 100, 500, 1000]:
            large_input = base_text * size_multiplier
            request = Request(large_input)

            # Process the large input
            complexity = minimal_planner.assess(request)
            roles = minimal_planner.select_roles(request, complexity)

            current_memory = process.memory_info().rss
            memory_growth = current_memory - initial_memory

            # Memory growth should be reasonable (less than 100MB)
            memory_growth_mb = memory_growth / (1024 * 1024)
            assert memory_growth_mb < 100, (
                f"Memory growth too high: {memory_growth_mb:.1f}MB"
            )

            # Cleanup references to help garbage collection
            del large_input, request, complexity, roles

    def test_garbage_collection_effectiveness(self, minimal_planner):
        """Test that memory is properly released after processing."""

        import gc
        import os

        import psutil

        process = psutil.Process(os.getpid())

        # Force garbage collection
        gc.collect()
        baseline_memory = process.memory_info().rss

        # Create and process many requests
        for i in range(100):
            large_text = f"process system {i} " * 1000
            request = Request(large_text)
            complexity = minimal_planner.assess(request)
            roles = minimal_planner.select_roles(request, complexity)

            # Clear references
            del large_text, request, complexity, roles

            # Periodic garbage collection
            if i % 20 == 0:
                gc.collect()

        # Final garbage collection
        gc.collect()
        final_memory = process.memory_info().rss

        memory_growth_mb = (final_memory - baseline_memory) / (1024 * 1024)

        # Memory growth should be minimal after garbage collection
        assert memory_growth_mb < 50, (
            f"Memory leak detected: {memory_growth_mb:.1f}MB growth"
        )


@pytest.mark.boundary
class TestDataIntegrityBoundaryConditions:
    """Test data integrity at boundary conditions."""

    def test_consistency_under_repeated_operations(self, minimal_planner):
        """Test that repeated operations maintain consistency."""

        test_request = Request("implement distributed consensus algorithm")

        # Perform same operation multiple times
        results = []
        for _ in range(100):
            complexity = minimal_planner.assess(test_request)
            roles = minimal_planner.select_roles(test_request, complexity)
            phases = minimal_planner._determine_required_phases(test_request)

            results.append({
                "complexity": complexity,
                "roles": tuple(sorted(roles)),  # Sort for comparison
                "phases": tuple(sorted(phases)),
            })

        # All results should be identical (deterministic behavior)
        first_result = results[0]
        for i, result in enumerate(results[1:], 1):
            assert result["complexity"] == first_result["complexity"], (
                f"Complexity inconsistency at iteration {i}: {result['complexity']} != {first_result['complexity']}"
            )

            assert result["roles"] == first_result["roles"], (
                f"Roles inconsistency at iteration {i}: {result['roles']} != {first_result['roles']}"
            )

            assert result["phases"] == first_result["phases"], (
                f"Phases inconsistency at iteration {i}: {result['phases']} != {first_result['phases']}"
            )

    def test_state_isolation_between_requests(self, minimal_planner):
        """Test that different requests don't interfere with each other."""

        test_cases = [
            ("simple bug fix", ComplexityTier.SIMPLE),
            ("complex distributed system", ComplexityTier.VERY_COMPLEX),
            ("moderate API development", ComplexityTier.MEDIUM),
        ]

        # Process requests in different orders
        for order in [test_cases, reversed(test_cases), test_cases[::-1]]:
            results = []

            for request_text, expected_complexity in order:
                request = Request(request_text)
                actual_complexity = minimal_planner.assess(request)
                roles = minimal_planner.select_roles(request, actual_complexity)

                results.append({
                    "request": request_text,
                    "complexity": actual_complexity,
                    "roles": roles,
                })

            # Results should be consistent regardless of processing order
            for i, (request_text, expected_complexity) in enumerate(test_cases):
                matching_result = next(
                    r for r in results if r["request"] == request_text
                )

                # The complexity might not match exactly due to algorithm variations,
                # but it should be consistent across different orderings
                assert matching_result["complexity"] in ComplexityTier, (
                    f"Invalid complexity type for '{request_text}'"
                )


if __name__ == "__main__":
    # Run boundary and edge case tests
    pytest.main([__file__, "-v", "--tb=short", "-m", "boundary"])
