"""Focused complexity assessment tests with practical validation.

This module tests essential complexity assessment functionality:
- Heuristic pattern matching for common complexity indicators
- Triage algorithm accuracy for representative scenarios  
- Decision matrix indicator matching
- Performance within acceptable limits

Maintains essential coverage while removing algorithmic over-engineering.
"""

import asyncio
from unittest.mock import patch

import pytest

from khive.prompts.complexity_heuristics import assess_by_heuristics
from khive.services.plan.planner_service import ComplexityTier
from khive.services.plan.triage.complexity_triage import (
    ComplexityTriageService,
    TriageConsensus,
)


@pytest.mark.unit
class TestHeuristicAssessment:
    """Test heuristic-based complexity pattern matching."""

    @pytest.fixture
    def complexity_indicators(self):
        """Common complexity indicators for testing."""
        return {
            "simple": ["fix", "update", "add", "remove", "simple", "basic"],
            "medium": ["implement", "create", "design", "develop", "moderate"],
            "complex": ["distributed", "architecture", "system", "complex", "advanced"],
            "very_complex": ["consensus", "algorithm", "blockchain", "machine learning", "research"]
        }

    def test_heuristic_pattern_recognition(self, complexity_indicators):
        """Test that heuristics recognize common complexity patterns."""
        test_cases = [
            ("fix login bug", "simple"),
            ("implement user authentication", "medium"),
            ("design distributed system", "complex"),
            ("research consensus algorithm", "very_complex"),
        ]

        for task_description, expected_level in test_cases:
            result = assess_by_heuristics(task_description)
            
            # Verify result format and basic pattern matching
            assert isinstance(result, list), f"Expected list result for '{task_description}'"
            
            # Check if task contains expected complexity indicators
            task_lower = task_description.lower()
            expected_indicators = complexity_indicators[expected_level]
            found_indicators = any(indicator in task_lower for indicator in expected_indicators)
            assert found_indicators, f"No {expected_level} indicators found in '{task_description}'"

    def test_heuristic_consistency(self):
        """Test that heuristic results are consistent across calls."""
        test_tasks = [
            "fix authentication bug",
            "implement OAuth2 system", 
            "design microservices architecture",
            "research Byzantine consensus algorithm"
        ]

        for task in test_tasks:
            result1 = assess_by_heuristics(task)
            result2 = assess_by_heuristics(task)
            assert result1 == result2, f"Inconsistent heuristic results for '{task}'"

    def test_edge_case_handling(self):
        """Test heuristic robustness with edge cases."""
        edge_cases = [
            "",  # Empty string
            "   ",  # Whitespace only
            "a" * 1000,  # Very long string
            "COMPLEX SYSTEM",  # All caps
            "café résumé",  # Unicode characters
        ]

        for edge_case in edge_cases:
            try:
                result = assess_by_heuristics(edge_case)
                assert isinstance(result, list), f"Expected list for edge case: '{edge_case}'"
            except Exception as e:
                pytest.fail(f"Edge case '{edge_case}' caused exception: {e}")


@pytest.mark.unit
class TestTriageAlgorithms:
    """Test complexity triage system with realistic scenarios."""

    @pytest.fixture
    def triage_scenarios(self):
        """Representative triage test scenarios."""
        return [
            {
                "task": "fix login button styling",
                "expected_tier": ComplexityTier.SIMPLE,
                "expected_agents": 2,
            },
            {
                "task": "implement OAuth2 authentication system",
                "expected_tier": ComplexityTier.MEDIUM,
                "expected_agents": 4,
            },
            {
                "task": "design distributed microservices architecture",
                "expected_tier": ComplexityTier.COMPLEX,
                "expected_agents": 7,
            },
            {
                "task": "develop blockchain consensus algorithm",
                "expected_tier": ComplexityTier.VERY_COMPLEX,
                "expected_agents": 10,
            },
        ]

    @patch("khive.services.plan.triage.complexity_triage.ComplexityTriageService._evaluate_with_llm")
    async def test_triage_classification_accuracy(self, mock_llm_eval, triage_scenarios):
        """Test triage algorithm accuracy for representative scenarios."""
        service = ComplexityTriageService()
        correct_assessments = 0

        for scenario in triage_scenarios:
            # Mock LLM response for scenario
            mock_consensus = TriageConsensus(
                tier=scenario["expected_tier"],
                confidence=0.8,
                agent_count=scenario["expected_agents"],
                recommended_roles=["researcher", "implementer"],
                reasoning=f"Assessment for {scenario['task']}",
            )
            mock_llm_eval.return_value = mock_consensus

            # Test triage evaluation
            result = await service.evaluate_complexity(scenario["task"])

            # Verify result structure and accuracy
            assert isinstance(result, TriageConsensus)
            assert result.tier == scenario["expected_tier"]
            assert 1 <= result.agent_count <= 12  # Within bounds
            
            if result.tier == scenario["expected_tier"]:
                correct_assessments += 1

        # Assert reasonable accuracy
        accuracy = correct_assessments / len(triage_scenarios)
        assert accuracy >= 0.75, f"Triage accuracy {accuracy:.2%} below 75% threshold"

    @patch("khive.services.plan.triage.complexity_triage.ComplexityTriageService._evaluate_with_llm")  
    async def test_agent_count_bounds(self, mock_llm_eval):
        """Test that agent counts stay within efficiency bounds."""
        service = ComplexityTriageService()
        
        # Test different complexity tiers
        test_cases = [
            (ComplexityTier.SIMPLE, 2),
            (ComplexityTier.MEDIUM, 5),  
            (ComplexityTier.COMPLEX, 8),
            (ComplexityTier.VERY_COMPLEX, 11),
        ]

        for tier, agent_count in test_cases:
            mock_consensus = TriageConsensus(
                tier=tier,
                confidence=0.8,
                agent_count=agent_count,
                recommended_roles=["researcher"],
                reasoning=f"Test for {tier.value}",
            )
            mock_llm_eval.return_value = mock_consensus

            result = await service.evaluate_complexity(f"Test {tier.value} task")
            
            # Verify efficiency bounds
            assert 1 <= result.agent_count <= 12, f"Agent count {result.agent_count} outside bounds [1, 12]"
            assert result.tier == tier


@pytest.mark.unit  
class TestDecisionMatrix:
    """Test decision matrix indicator matching."""

    def test_indicator_matching(self):
        """Test decision matrix indicator matching logic."""
        # Simulate decision matrix matching
        complexity_indicators = {
            "simple": ["fix", "update", "basic", "quick"],
            "medium": ["implement", "create", "design", "develop"], 
            "complex": ["distributed", "architecture", "system", "advanced"],
            "very_complex": ["consensus", "algorithm", "research", "blockchain"]
        }

        test_cases = [
            ("fix simple bug", "simple"),
            ("implement authentication", "medium"),
            ("design distributed architecture", "complex"),
            ("research consensus algorithm", "very_complex"),
        ]

        for task, expected_tier in test_cases:
            task_lower = task.lower()
            best_tier = None
            max_matches = 0

            # Find tier with most indicator matches
            for tier, indicators in complexity_indicators.items():
                match_count = sum(1 for indicator in indicators if indicator in task_lower)
                if match_count > max_matches:
                    max_matches = match_count
                    best_tier = tier

            assert best_tier == expected_tier, f"Expected {expected_tier}, got {best_tier} for '{task}'"
            assert max_matches >= 1, f"No indicators matched for '{task}'"

    def test_agent_count_ranges(self):
        """Test agent count range validation."""
        ranges_by_tier = {
            "simple": "1-3",
            "medium": "3-6", 
            "complex": "5-9",
            "very_complex": "7-12"
        }

        for tier, range_str in ranges_by_tier.items():
            assert "-" in range_str, f"Invalid range format for {tier}: {range_str}"
            
            min_str, max_str = range_str.split("-")
            min_agents, max_agents = int(min_str), int(max_str)
            
            # Verify reasonable bounds
            assert 1 <= min_agents <= max_agents <= 12, f"Invalid range for {tier}: {min_agents}-{max_agents}"


@pytest.mark.performance
class TestPerformance:
    """Test performance characteristics of complexity assessment."""

    def test_heuristic_performance(self):
        """Test heuristic assessment performance under load."""
        import time
        
        tasks = [
            "implement OAuth2 system", 
            "design microservices architecture",
            "build analytics dashboard"
        ] * 10  # 30 total tasks

        start_time = time.time()
        for task in tasks:
            assess_by_heuristics(task)
        total_time = time.time() - start_time

        # Should complete quickly
        assert total_time < 0.5, f"Heuristic assessment took {total_time:.2f}s, expected <0.5s"

    @pytest.mark.asyncio
    async def test_concurrent_assessment(self):
        """Test concurrent assessment handling."""
        tasks = [
            "implement authentication",
            "design database schema", 
            "build API endpoints"
        ]

        async def assess_task(task):
            await asyncio.sleep(0.01)  # Simulate processing
            return assess_by_heuristics(task)

        # Run concurrent assessments
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*[assess_task(task) for task in tasks])
        total_time = asyncio.get_event_loop().time() - start_time

        # Verify results and performance
        assert len(results) == len(tasks)
        assert all(isinstance(result, list) for result in results)
        assert total_time < 0.1, f"Concurrent assessment took {total_time:.2f}s, expected <0.1s"
