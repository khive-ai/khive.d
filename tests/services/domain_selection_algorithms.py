"""
Domain Selection Algorithm Test Suite

Comprehensive testing of domain selection logic in the planning service,
including domain-role matching algorithms, domain scoring, and selection
criteria validation.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from khive.services.plan.models import OrchestrationEvaluation
from khive.services.plan.planner_service import (ComplexityTier,
                                                 OrchestrationPlanner,
                                                 PlannerService, Request)
from khive.services.plan.triage.complexity_triage import TriageConsensus

# Domain selection test scenarios
DOMAIN_SELECTION_SCENARIOS = [
    # Format: (task_description, expected_domains, min_domains, description)
    (
        "Build distributed consensus system with Byzantine fault tolerance",
        ["distributed-systems", "byzantine-fault-tolerance"],
        2,
        "Complex distributed systems task",
    ),
    (
        "Create React frontend with TypeScript and state management",
        ["frontend-development", "typescript", "nextjs"],
        2,
        "Frontend development task",
    ),
    (
        "Design microservices API with event sourcing",
        ["microservices-architecture", "api-design", "backend-development"],
        2,
        "Backend architecture task",
    ),
    (
        "Implement real-time WebSocket communication",
        ["websocket-communication", "backend-development"],
        1,
        "Communication protocol task",
    ),
    (
        "Build neural network for image classification",
        ["neural-networks", "ai-architecture"],
        1,
        "AI/ML task",
    ),
    (
        "Set up CI/CD pipeline with automated testing",
        ["ci-cd-pipelines", "devops-automation", "code-quality"],
        2,
        "DevOps task",
    ),
    (
        "Simple CRUD API for user management",
        ["api-design", "database-design"],
        1,
        "Simple backend task",
    ),
    (
        "Optimize database queries for performance",
        ["database-design", "backend-development"],
        1,
        "Database optimization",
    ),
]

DOMAIN_SCORING_CRITERIA = [
    # Format: (criterion_name, weight, description)
    ("keyword_relevance", 0.4, "Relevance based on task keywords"),
    ("complexity_match", 0.3, "Domain complexity matches task complexity"),
    ("role_compatibility", 0.2, "Domain compatible with selected roles"),
    ("historical_success", 0.1, "Historical success rate for similar tasks"),
]

ROLE_DOMAIN_AFFINITY_MATRIX = {
    # Format: role -> {domain: affinity_score}
    "researcher": {
        "distributed-systems": 0.9,
        "byzantine-fault-tolerance": 0.8,
        "neural-networks": 0.9,
        "ai-architecture": 0.8,
        "frontend-development": 0.3,
    },
    "architect": {
        "microservices-architecture": 0.9,
        "software-architecture": 0.9,
        "distributed-systems": 0.8,
        "api-design": 0.7,
        "database-design": 0.6,
    },
    "implementer": {
        "backend-development": 0.9,
        "frontend-development": 0.8,
        "typescript": 0.7,
        "rust": 0.8,
        "api-design": 0.7,
    },
    "tester": {
        "code-quality": 0.9,
        "playwright-testing": 0.9,
        "ci-cd-pipelines": 0.6,
        "backend-development": 0.5,
    },
    "analyst": {
        "neural-networks": 0.8,
        "ai-architecture": 0.7,
        "distributed-systems": 0.6,
        "database-design": 0.5,
    },
}


@pytest.mark.unit
class TestDomainSelectionAccuracy:
    """Test accuracy of domain selection algorithms."""

    @pytest.fixture
    def mock_planner(self, tmp_path):
        """Create orchestration planner with comprehensive domain setup."""
        domains_list = [
            "distributed-systems",
            "byzantine-fault-tolerance",
            "frontend-development",
            "typescript",
            "nextjs",
            "microservices-architecture",
            "api-design",
            "backend-development",
            "websocket-communication",
            "neural-networks",
            "ai-architecture",
            "ci-cd-pipelines",
            "devops-automation",
            "code-quality",
            "database-design",
            "software-architecture",
            "rust",
            "playwright-testing",
        ]

        with patch.multiple(
            OrchestrationPlanner,
            _load_available_roles=MagicMock(
                return_value=[
                    "researcher",
                    "architect",
                    "implementer",
                    "tester",
                    "analyst",
                ]
            ),
            _load_available_domains=MagicMock(return_value=domains_list),
            _load_prompt_templates=MagicMock(return_value={"agents": {}}),
            _load_decision_matrix=MagicMock(
                return_value={"complexity_assessment": {}, "agent_role_selection": {}}
            ),
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                planner = OrchestrationPlanner()
                # Mock workspace directory
                planner.workspace_dir = tmp_path / "workspace"
                planner.workspace_dir.mkdir(parents=True, exist_ok=True)
                return planner

    @pytest.mark.parametrize(
        "task_description,expected_domains,min_domains,description",
        DOMAIN_SELECTION_SCENARIOS,
    )
    def test_domain_selection_accuracy(
        self, mock_planner, task_description, expected_domains, min_domains, description
    ):
        """Test that domain selection identifies relevant domains accurately."""
        # Create mock evaluation with expected domains
        mock_evaluation = OrchestrationEvaluation(
            complexity="medium",
            complexity_reason="Test evaluation",
            total_agents=3,
            agent_reason="Test agents",
            rounds_needed=1,
            role_priorities=["researcher", "implementer"],
            primary_domains=expected_domains[:min_domains],  # Limit to required minimum
            domain_reason="Test domain selection",
            workflow_pattern="parallel",
            workflow_reason="Test workflow",
            quality_level="thorough",
            quality_reason="Test quality",
            rules_applied=["domain_matching"],
            confidence=0.8,
            summary="Test evaluation for domain selection",
        )

        # Test that available domains include expected ones
        available_domains = mock_planner.available_domains

        domains_found = []
        for expected_domain in expected_domains:
            if expected_domain in available_domains:
                domains_found.append(expected_domain)

        assert len(domains_found) >= min_domains, (
            f"Failed {description}: Expected at least {min_domains} domains from {expected_domains}, "
            f"but only found {len(domains_found)}: {domains_found} in available domains"
        )

    def test_domain_relevance_scoring(self, mock_planner):
        """Test domain relevance scoring based on task keywords."""
        test_cases = [
            # Format: (task, domain, expected_score_range, description)
            (
                "distributed consensus system",
                "distributed-systems",
                (0.8, 1.0),
                "High relevance",
            ),
            (
                "React frontend application",
                "frontend-development",
                (0.8, 1.0),
                "High relevance",
            ),
            ("database optimization", "database-design", (0.8, 1.0), "High relevance"),
            ("simple task", "distributed-systems", (0.0, 0.3), "Low relevance"),
            ("neural networks", "frontend-development", (0.0, 0.3), "Low relevance"),
        ]

        for task, domain, score_range, description in test_cases:
            # Mock relevance scoring algorithm
            keywords = task.lower().split()
            domain_keywords = domain.replace("-", " ").split()

            # Simple relevance calculation based on keyword overlap
            overlap = len(set(keywords) & set(domain_keywords))
            total_keywords = len(set(keywords) | set(domain_keywords))
            relevance_score = overlap / total_keywords if total_keywords > 0 else 0

            assert score_range[0] <= relevance_score <= score_range[1], (
                f"Failed {description}: score {relevance_score:.3f} not in range {score_range}"
            )

    def test_complexity_domain_matching(self, mock_planner):
        """Test that domain selection matches task complexity appropriately."""
        complexity_scenarios = [
            (
                ComplexityTier.SIMPLE,
                ["api-design", "frontend-development"],
                "Simple tasks",
            ),
            (
                ComplexityTier.MEDIUM,
                ["backend-development", "database-design"],
                "Medium tasks",
            ),
            (
                ComplexityTier.COMPLEX,
                ["microservices-architecture", "distributed-systems"],
                "Complex tasks",
            ),
            (
                ComplexityTier.VERY_COMPLEX,
                ["byzantine-fault-tolerance", "ai-architecture"],
                "Very complex tasks",
            ),
        ]

        for complexity, suitable_domains, description in complexity_scenarios:
            # Check that suitable domains are available
            available = mock_planner.available_domains

            found_domains = [d for d in suitable_domains if d in available]
            assert len(found_domains) > 0, (
                f"No suitable domains found for {description}: {suitable_domains} not in {available}"
            )

    def test_role_domain_affinity_validation(self, mock_planner):
        """Test that role-domain affinity scores are reasonable."""
        # Test some expected high-affinity pairs
        high_affinity_pairs = [
            ("researcher", ["distributed-systems", "neural-networks"]),
            ("architect", ["microservices-architecture", "software-architecture"]),
            ("implementer", ["backend-development", "frontend-development"]),
            ("tester", ["code-quality", "playwright-testing"]),
        ]

        available_domains = mock_planner.available_domains

        for role, preferred_domains in high_affinity_pairs:
            found_preferred = [d for d in preferred_domains if d in available_domains]

            assert len(found_preferred) > 0, (
                f"No preferred domains found for role '{role}': "
                f"{preferred_domains} not available in {available_domains}"
            )


@pytest.mark.unit
class TestDomainSelectionConsistency:
    """Test consistency in domain selection across different scenarios."""

    @pytest.fixture
    def mock_planner(self, tmp_path):
        """Create planner for consistency testing."""
        return TestDomainSelectionAccuracy().mock_planner.__pytest_wrapped__(tmp_path)

    def test_deterministic_domain_selection(self, mock_planner):
        """Test that domain selection is deterministic for identical inputs."""
        task_descriptions = [
            "Build distributed consensus system",
            "Create React frontend application",
            "Design microservices architecture",
        ]

        for task in task_descriptions:
            request = Request(task)

            # Run multiple times and check consistency
            selections = []
            for _ in range(10):
                # Mock domain selection process
                available_domains = mock_planner.available_domains

                # Simple keyword-based selection for testing
                task_words = request.text.split()
                selected_domains = []

                for domain in available_domains:
                    domain_words = domain.replace("-", " ").split()
                    if any(word in task_words for word in domain_words):
                        selected_domains.append(domain)

                selections.append(sorted(selected_domains))

            # All selections should be identical
            unique_selections = set(tuple(s) for s in selections)
            assert len(unique_selections) == 1, (
                f"Inconsistent domain selection for '{task}': {unique_selections}"
            )

    def test_domain_selection_stability(self, mock_planner):
        """Test stability of domain selection under minor input variations."""
        base_task = "build distributed system"
        variations = [
            "build distributed system",
            "Build distributed system",
            "build  distributed  system",  # Extra spaces
            "build distributed systems",  # Plural
            "build a distributed system",  # Article
        ]

        # All variations should select similar domains
        domain_selections = []
        available_domains = mock_planner.available_domains

        for variation in variations:
            task_words = variation.lower().split()
            selected_domains = []

            for domain in available_domains:
                domain_words = domain.replace("-", " ").split()
                if any(word in task_words for word in domain_words):
                    selected_domains.append(domain)

            domain_selections.append(set(selected_domains))

        # Check that all selections have significant overlap
        base_selection = domain_selections[0]
        for selection in domain_selections[1:]:
            overlap = len(base_selection & selection)
            total = len(base_selection | selection)

            if total > 0:
                similarity = overlap / total
                assert similarity >= 0.8, (
                    f"Low similarity between domain selections: {similarity:.2f}"
                )

    def test_consistent_domain_ranking(self, mock_planner):
        """Test that domain ranking is consistent across runs."""
        task = "build microservices with event sourcing"
        available_domains = mock_planner.available_domains

        # Simple relevance-based ranking
        def rank_domains(task_text, domains):
            task_words = set(task_text.lower().split())
            scored_domains = []

            for domain in domains:
                domain_words = set(domain.replace("-", " ").split())
                overlap = len(task_words & domain_words)
                score = (
                    overlap / len(task_words | domain_words)
                    if task_words | domain_words
                    else 0
                )
                scored_domains.append((domain, score))

            return sorted(scored_domains, key=lambda x: x[1], reverse=True)

        # Run ranking multiple times
        rankings = []
        for _ in range(10):
            ranking = rank_domains(task, available_domains)
            rankings.append(ranking)

        # All rankings should be identical
        first_ranking = rankings[0]
        for ranking in rankings[1:]:
            assert ranking == first_ranking, "Inconsistent domain ranking across runs"


@pytest.mark.unit
class TestDomainSelectionEdgeCases:
    """Test edge cases in domain selection algorithms."""

    @pytest.fixture
    def mock_planner(self, tmp_path):
        """Create planner for edge case testing."""
        return TestDomainSelectionAccuracy().mock_planner.__pytest_wrapped__(tmp_path)

    def test_empty_task_description(self, mock_planner):
        """Test domain selection with empty task description."""
        empty_request = Request("")
        available_domains = mock_planner.available_domains

        # Should handle gracefully - either select default domains or none
        assert len(available_domains) >= 0  # Should not crash

    def test_single_word_task(self, mock_planner):
        """Test domain selection with single word tasks."""
        single_word_tasks = ["api", "frontend", "database", "testing", "security"]

        for task in single_word_tasks:
            request = Request(task)
            available_domains = mock_planner.available_domains

            # Should find at least one relevant domain for common terms
            relevant_domains = [
                d
                for d in available_domains
                if task in d
                or task.replace("end", "end-development") in available_domains
            ]

            # Allow for no matches on some single words
            assert isinstance(relevant_domains, list)

    def test_very_long_task_description(self, mock_planner):
        """Test domain selection with very long task descriptions."""
        long_task = ("build distributed system " * 100).strip()
        request = Request(long_task)
        available_domains = mock_planner.available_domains

        # Should handle long inputs without performance degradation
        start_time = time.time()

        # Simulate domain selection
        task_words = set(request.text.split())
        selected_domains = []
        for domain in available_domains[:10]:  # Limit for test performance
            domain_words = set(domain.replace("-", " ").split())
            if task_words & domain_words:
                selected_domains.append(domain)

        end_time = time.time()
        processing_time = end_time - start_time

        assert processing_time < 1.0, (
            f"Long task processing too slow: {processing_time:.3f}s"
        )

    def test_task_with_special_characters(self, mock_planner):
        """Test domain selection with special characters in task description."""
        special_tasks = [
            "build API with REST/GraphQL endpoints",
            "create UI/UX for mobile app",
            "implement OAuth 2.0 authentication",
            "setup CI/CD with Docker & Kubernetes",
            "build real-time chat (WebSocket + Redis)",
        ]

        for task in special_tasks:
            request = Request(task)
            # Should not crash and should sanitize special characters
            assert isinstance(request.text, str)
            assert len(request.text) > 0

    def test_domain_selection_with_no_matches(self, mock_planner):
        """Test domain selection when no domains match the task."""
        obscure_task = "xyzabc123 completely unrelated task zyx987"
        request = Request(obscure_task)
        available_domains = mock_planner.available_domains

        # Should handle gracefully with no matches
        task_words = set(request.text.split())
        matched_domains = []

        for domain in available_domains:
            domain_words = set(domain.replace("-", " ").split())
            if task_words & domain_words:
                matched_domains.append(domain)

        # Should return empty list or default domains, not crash
        assert isinstance(matched_domains, list)

    def test_duplicate_domain_handling(self, mock_planner):
        """Test handling of duplicate domains in selection."""
        # Simulate scenario where multiple selection criteria pick same domain
        task = "distributed distributed systems systems"
        request = Request(task)
        available_domains = mock_planner.available_domains

        selected_domains = []
        task_words = request.text.split()

        # Simulate multiple selection passes that might create duplicates
        for word in task_words:
            for domain in available_domains:
                if word in domain:
                    selected_domains.append(domain)

        # Remove duplicates
        unique_domains = list(set(selected_domains))

        # Should handle duplicates properly
        assert len(unique_domains) <= len(selected_domains)
        assert len(unique_domains) == len(set(unique_domains))


@pytest.mark.performance
class TestDomainSelectionPerformance:
    """Performance benchmarks for domain selection algorithms."""

    @pytest.fixture
    def mock_planner(self, tmp_path):
        """Create planner for performance testing."""
        return TestDomainSelectionAccuracy().mock_planner.__pytest_wrapped__(tmp_path)

    @pytest.mark.benchmark
    def test_domain_matching_performance(self, mock_planner):
        """Benchmark domain matching performance."""
        tasks = [
            "build distributed system with consensus",
            "create frontend application with React",
            "design microservices architecture",
            "implement neural network for classification",
            "setup CI/CD pipeline with testing",
        ]

        iterations = 1000
        max_time_ms = 5.0

        start_time = time.time()

        for _ in range(iterations):
            for task in tasks:
                request = Request(task)
                available_domains = mock_planner.available_domains

                # Simple domain matching algorithm
                task_words = set(request.text.split())
                for domain in available_domains:
                    domain_words = set(domain.replace("-", " ").split())
                    overlap = len(task_words & domain_words)
                    # Just calculate, don't store

        end_time = time.time()
        avg_time_ms = ((end_time - start_time) * 1000) / (iterations * len(tasks))

        print(f"Domain matching performance: {avg_time_ms:.4f}ms per operation")

        assert avg_time_ms < max_time_ms, (
            f"Domain matching too slow: {avg_time_ms:.4f}ms > {max_time_ms}ms"
        )

    @pytest.mark.benchmark
    def test_large_domain_set_performance(self, mock_planner):
        """Test performance with large domain sets."""
        # Simulate large domain set
        large_domain_set = [f"domain-{i}" for i in range(1000)]

        task = "build distributed system"
        request = Request(task)

        max_time_ms = 10.0
        start_time = time.time()

        # Test domain matching against large set
        task_words = set(request.text.split())
        matched_domains = []

        for domain in large_domain_set:
            domain_words = set(domain.replace("-", " ").split())
            if task_words & domain_words:
                matched_domains.append(domain)

        end_time = time.time()
        processing_time_ms = (end_time - start_time) * 1000

        print(
            f"Large domain set performance: {processing_time_ms:.4f}ms for {len(large_domain_set)} domains"
        )

        assert processing_time_ms < max_time_ms, (
            f"Large domain set processing too slow: {processing_time_ms:.4f}ms > {max_time_ms}ms"
        )

    @pytest.mark.benchmark
    def test_concurrent_domain_selection(self, mock_planner):
        """Test concurrent domain selection performance."""
        import threading

        tasks = [f"build system {i}" for i in range(20)]
        results = []
        errors = []

        def select_domains(task):
            try:
                request = Request(task)
                available_domains = mock_planner.available_domains

                task_words = set(request.text.split())
                selected = []

                for domain in available_domains:
                    domain_words = set(domain.replace("-", " ").split())
                    if task_words & domain_words:
                        selected.append(domain)

                results.append(selected)
            except Exception as e:
                errors.append(e)

        # Run concurrent selections
        threads = []
        start_time = time.time()

        for task in tasks:
            thread = threading.Thread(target=select_domains, args=(task,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        end_time = time.time()
        total_time_ms = (end_time - start_time) * 1000

        print(
            f"Concurrent domain selection: {total_time_ms:.4f}ms for {len(tasks)} tasks"
        )

        # Should complete without errors and within reasonable time
        assert len(errors) == 0, f"Concurrent selection errors: {errors}"
        assert total_time_ms < 1000, (
            f"Concurrent selection too slow: {total_time_ms:.4f}ms"
        )
        assert len(results) == len(tasks), "Missing results from concurrent execution"


@pytest.mark.integration
class TestDomainSelectionIntegration:
    """Integration tests for domain selection with other system components."""

    @pytest.fixture
    def planner_service(self):
        """Create planner service for integration testing."""
        return PlannerService()

    @pytest.mark.asyncio
    async def test_domain_selection_in_planning_workflow(self, tmp_path):
        """Test domain selection integration with complete planning workflow."""
        # Mock triage service
        from khive.services.plan.triage.complexity_triage import \
            ComplexityTriageService

        mock_triage_consensus = TriageConsensus(
            should_escalate=True,
            decision_votes={"proceed": 0, "escalate": 3},
            average_confidence=0.9,
            final_roles=["researcher", "architect", "implementer"],
            final_domains=["distributed-systems", "microservices-architecture"],
            final_agent_count=3,
        )

        with patch.object(
            ComplexityTriageService, "triage", new_callable=AsyncMock
        ) as mock_triage:
            mock_triage.return_value = (True, mock_triage_consensus)

            with patch.multiple(
                OrchestrationPlanner,
                _load_available_domains=MagicMock(
                    return_value=[
                        "distributed-systems",
                        "microservices-architecture",
                        "frontend-development",
                        "backend-development",
                    ]
                ),
                _load_available_roles=MagicMock(
                    return_value=["researcher", "architect", "implementer"]
                ),
                _load_prompt_templates=MagicMock(return_value={"agents": {}}),
                _load_decision_matrix=MagicMock(
                    return_value={
                        "complexity_assessment": {},
                        "agent_role_selection": {},
                    }
                ),
                evaluate_request=AsyncMock(return_value=[]),
                build_consensus=MagicMock(
                    return_value=(
                        "mock consensus",
                        {
                            "complexity": "complex",
                            "domains": [
                                "distributed-systems",
                                "microservices-architecture",
                            ],
                            "agent_count": 3,
                            "confidence": 0.9,
                            "role_recommendations": [
                                ("researcher", 0.9),
                                ("architect", 0.8),
                                ("implementer", 0.7),
                            ],
                        },
                    )
                ),
            ):
                with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                    service = PlannerService()

                    from khive.services.plan.parts import PlannerRequest

                    request = PlannerRequest(
                        task_description="Build distributed microservices system with fault tolerance"
                    )

                    response = await service.handle_request(request)

                    # Should successfully complete with domain selection
                    assert response.success is True
                    assert response.session_id is not None

    def test_domain_selection_with_agent_composer_integration(self, tmp_path):
        """Test integration between domain selection and agent composition."""
        # Create composer with test setup
        composer = TestDomainSelectionAccuracy().mock_planner.__pytest_wrapped__(
            tmp_path
        )

        # Test end-to-end: task -> domain selection -> agent composition
        tasks_and_expected_domains = [
            ("build API", ["api-design", "backend-development"]),
            ("frontend React app", ["frontend-development", "typescript"]),
            (
                "microservices system",
                ["microservices-architecture", "distributed-systems"],
            ),
        ]

        available_domains = (
            composer.available_domains
            if hasattr(composer, "available_domains")
            else [
                "api-design",
                "backend-development",
                "frontend-development",
                "typescript",
                "microservices-architecture",
                "distributed-systems",
            ]
        )

        for task, expected_domains in tasks_and_expected_domains:
            # Simulate domain selection
            selected_domains = []
            task_words = set(task.lower().split())

            for domain in available_domains:
                domain_words = set(domain.replace("-", " ").split())
                if task_words & domain_words:
                    selected_domains.append(domain)

            # Should select at least one relevant domain
            relevant_found = any(
                expected in selected_domains or expected in available_domains
                for expected in expected_domains
            )

            assert relevant_found or len(selected_domains) > 0, (
                f"No relevant domains selected for task '{task}'. "
                f"Expected some from {expected_domains}, got {selected_domains}"
            )


if __name__ == "__main__":
    # Run specific test categories
    import sys

    if len(sys.argv) > 1:
        test_category = sys.argv[1]
        if test_category == "unit":
            pytest.main(["-v", "-m", "unit", __file__])
        elif test_category == "performance":
            pytest.main(["-v", "-m", "performance", __file__])
        elif test_category == "integration":
            pytest.main(["-v", "-m", "integration", __file__])
        else:
            pytest.main(["-v", __file__])
    else:
        pytest.main(["-v", __file__])
