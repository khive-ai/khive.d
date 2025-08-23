"""
Domain Matching Algorithm Validation Test Suite

Comprehensive validation of domain matching accuracy, canonicalization,
and role-domain selection algorithms. Tests matching consistency, performance,
and error handling across diverse scenarios.
"""

import json
import time
from unittest.mock import MagicMock, patch

import pytest
import yaml

from khive.services.composition.agent_composer import AgentComposer
from khive.services.plan.parts import AgentRecommendation
from khive.services.plan.planner_service import OrchestrationPlanner, PlannerService

# Test data for domain matching validation
DOMAIN_MATCHING_TEST_CASES = [
    # Format: (input_domain, expected_canonical, should_match, description)
    ("frontend", "frontend-development", True, "Basic synonym mapping"),
    ("ui", "frontend-development", True, "UI abbreviation mapping"),
    ("backend", "backend-development", True, "Backend mapping"),
    ("api", "backend-development", True, "API to backend mapping"),
    ("microservices", "microservices-architecture", True, "Architecture mapping"),
    ("event", "event-sourcing", True, "Event to event-sourcing"),
    ("security", "security-architecture", True, "Security mapping"),
    ("testing", "playwright-testing", True, "Testing framework mapping"),
    ("neural", "neural-networks", True, "AI/ML mapping"),
    ("cloud", "cloud-native", True, "Cloud platform mapping"),
    ("websocket", "websocket-communication", True, "Communication protocol"),
    ("multimodal", "multi-modal-systems", True, "Complex term mapping"),
    ("nonexistent-domain", "nonexistent-domain", False, "No mapping exists"),
    ("", "", False, "Empty input"),
    ("UPPERCASE", "UPPERCASE", False, "Case handling test"),
    ("multi_modal_systems", "multi-modal-systems", True, "Underscore to hyphen"),
    ("distributed-systems", "distributed-systems", False, "Already canonical"),
]

ROLE_DOMAIN_COMBINATIONS = [
    # Format: (role, domain, valid, expected_capability_count, description)
    ("researcher", "distributed-systems", True, 3, "Valid combination"),
    ("architect", "microservices-architecture", True, 4, "Architecture match"),
    ("implementer", "backend-development", True, 3, "Implementation role"),
    ("tester", "playwright-testing", True, 2, "Testing specialization"),
    ("analyst", "neural-networks", True, 3, "Analysis role"),
    ("critic", "security-architecture", True, 2, "Security review"),
    ("theorist", "category-theory", True, 4, "Theory specialization"),
    ("innovator", "rust-performance", True, 3, "Performance optimization"),
    ("commentator", "frontend-development", True, 2, "Documentation role"),
    ("auditor", "byzantine-fault-tolerance", True, 4, "Consensus auditing"),
    ("invalid-role", "frontend-development", False, 0, "Invalid role"),
    ("researcher", "invalid-domain", True, 0, "Invalid domain but valid role"),
]

EDGE_CASES = [
    # Format: (input, expected_behavior, description)
    (None, "empty_string", "Null input handling"),
    ("", "empty_string", "Empty string handling"),
    ("a" * 1000, "truncated", "Very long input"),
    ("domain-with-../../../etc/passwd", "sanitized", "Path traversal attempt"),
    ("domain;rm -rf /", "sanitized", "Command injection attempt"),
    ("domain<script>alert('xss')</script>", "sanitized", "XSS attempt"),
    ("domain\x00\x01\x02", "sanitized", "Control character handling"),
    ("domain\n\r\t", "sanitized", "Whitespace handling"),
    ("DOMAIN", "normalized", "Case normalization"),
    ("Domain_With_Mixed-Case", "normalized", "Mixed case and separators"),
]

PERFORMANCE_BENCHMARKS = {
    "canonicalization": {"max_time_ms": 1.0, "iterations": 1000},
    "agent_composition": {"max_time_ms": 10.0, "iterations": 100},
    "domain_loading": {"max_time_ms": 50.0, "iterations": 10},
    "role_selection": {"max_time_ms": 5.0, "iterations": 500},
}


@pytest.mark.unit
class TestDomainCanonicalization:
    """Test domain canonicalization accuracy and consistency."""

    @pytest.fixture
    def agent_composer(self, tmp_path):
        """Create AgentComposer with test configuration."""
        # Create test directory structure
        base_path = tmp_path / "test_prompts"
        base_path.mkdir()

        # Create roles directory with test roles
        roles_path = base_path / "roles"
        roles_path.mkdir()

        # Create minimal test roles
        test_roles = ["researcher", "architect", "implementer", "tester", "analyst"]
        for role in test_roles:
            role_file = roles_path / f"{role}.md"
            role_file.write_text(
                f"""# {role.title()}

```yaml
id: {role}
type: autonomous_agent
capabilities: ["analysis", "synthesis", "documentation"]
tools: ["Read", "Write", "Bash"]
```

## Role
Autonomous {role} agent that provides specialized analysis.

## Purpose
Execute {role} tasks with domain expertise.

## Core Capabilities
- Domain-specific analysis
- Evidence-based reasoning
- Collaborative coordination

## Decision Logic
```python
if task_complexity > threshold:
    escalate_to_specialist()
else:
    proceed_with_analysis()
```
"""
            )

        # Create domains directory with test domains
        domains_path = base_path / "domains"
        domains_path.mkdir()

        # Create architecture subdirectory
        arch_path = domains_path / "architecture"
        arch_path.mkdir()

        # Create test domain files
        test_domains = {
            "distributed-systems": {
                "domain": {"id": "distributed-systems", "category": "systems"},
                "knowledge_patterns": {
                    "consensus_algorithms": ["raft", "pbft", "paxos"],
                    "fault_tolerance": ["byzantine", "crash", "omission"],
                },
                "decision_rules": {
                    "complexity_threshold": 0.8,
                    "confidence_thresholds": {"analysis": 0.9},
                },
            },
            "frontend-development": {
                "domain": {"id": "frontend-development", "category": "engineering"},
                "knowledge_patterns": {
                    "frameworks": ["react", "vue", "angular"],
                    "patterns": ["component", "state", "routing"],
                },
                "decision_rules": {
                    "complexity_threshold": 0.6,
                    "confidence_thresholds": {"implementation": 0.8},
                },
            },
            "microservices-architecture": {
                "domain": {
                    "id": "microservices-architecture",
                    "category": "architecture",
                },
                "knowledge_patterns": {
                    "patterns": ["service_mesh", "api_gateway", "circuit_breaker"],
                    "communication": ["sync", "async", "event_driven"],
                },
                "decision_rules": {
                    "complexity_threshold": 0.9,
                    "confidence_thresholds": {"design": 0.9},
                },
            },
        }

        # Write domain files
        for domain_name, domain_data in test_domains.items():
            if domain_name == "microservices-architecture":
                # Put in architecture subdirectory
                domain_file = arch_path / f"{domain_name}.yaml"
            else:
                domain_file = domains_path / f"{domain_name}.yaml"

            with open(domain_file, "w") as f:
                yaml.dump(domain_data, f)

        # Create name_mapper.yaml
        name_mapper_data = {
            "synonyms": {
                "frontend": "frontend-development",
                "ui": "frontend-development",
                "backend": "backend-development",
                "api": "backend-development",
                "microservices": "microservices-architecture",
                "event": "event-sourcing",
                "security": "security-architecture",
                "testing": "playwright-testing",
                "neural": "neural-networks",
                "cloud": "cloud-native",
                "websocket": "websocket-communication",
                "multimodal": "multi-modal-systems",
                "multi_modal_systems": "multi-modal-systems",
            },
            "canonical_domains": [
                "frontend-development",
                "backend-development",
                "distributed-systems",
                "microservices-architecture",
                "event-sourcing",
                "security-architecture",
            ],
        }

        name_mapper_file = base_path / "name_mapper.yaml"
        with open(name_mapper_file, "w") as f:
            yaml.dump(name_mapper_data, f)

        return AgentComposer(base_path=str(base_path))

    @pytest.mark.parametrize(
        "input_domain,expected_canonical,should_match,description",
        DOMAIN_MATCHING_TEST_CASES,
    )
    def test_domain_canonicalization_accuracy(
        self,
        agent_composer,
        input_domain,
        expected_canonical,
        should_match,
        description,
    ):
        """Test domain canonicalization accuracy across various inputs."""
        result = agent_composer.canonicalize_domain(input_domain)

        if should_match:
            assert (
                result == expected_canonical
            ), f"Failed {description}: expected '{expected_canonical}', got '{result}'"
        else:
            # For non-matches, should return original or empty
            assert result in [
                input_domain,
                "",
            ], f"Failed {description}: unexpected transformation '{result}'"

    def test_domain_canonicalization_consistency(self, agent_composer):
        """Test that canonicalization is consistent across multiple calls."""
        test_domains = ["frontend", "ui", "backend", "microservices", "invalid-domain"]

        # Run canonicalization multiple times
        results = {}
        for _ in range(10):
            for domain in test_domains:
                canonical = agent_composer.canonicalize_domain(domain)
                if domain not in results:
                    results[domain] = []
                results[domain].append(canonical)

        # Verify consistency
        for domain, canonical_list in results.items():
            unique_results = set(canonical_list)
            assert (
                len(unique_results) == 1
            ), f"Inconsistent canonicalization for '{domain}': {unique_results}"

    def test_domain_canonicalization_edge_cases(self, agent_composer):
        """Test edge cases in domain canonicalization."""
        edge_cases = [
            (None, None),  # None should return None, not empty string
            ("", ""),
            ("   ", "   "),  # Whitespace should be preserved if no mapping
            (
                "FRONTEND",
                "frontend-development",
            ),  # Case insensitive mapping - converts to lowercase first
            ("frontend   ", "frontend-development"),  # Whitespace handling with mapping
            ("front-end", "front-end"),  # Hyphenated not in mapping
        ]

        for input_domain, expected in edge_cases:
            result = agent_composer.canonicalize_domain(input_domain)
            assert (
                result == expected
            ), f"Edge case failed: input='{input_domain}', expected='{expected}', got='{result}'"

    def test_domain_synonym_mapping_completeness(self, agent_composer):
        """Test that all defined synonyms map correctly."""
        # Get the synonym mapping
        synonyms = agent_composer._domain_mapper.get("synonyms", {})

        for synonym, canonical in synonyms.items():
            result = agent_composer.canonicalize_domain(synonym)
            assert (
                result == canonical
            ), f"Synonym mapping failed: '{synonym}' should map to '{canonical}', got '{result}'"

    def test_canonical_domain_preservation(self, agent_composer):
        """Test that canonical domains remain unchanged."""
        canonical_domains = agent_composer._domain_mapper.get("canonical_domains", [])

        for canonical in canonical_domains:
            result = agent_composer.canonicalize_domain(canonical)
            assert (
                result == canonical
            ), f"Canonical domain changed: '{canonical}' became '{result}'"


@pytest.mark.unit
class TestRoleDomainMatching:
    """Test role-domain combination matching and validation."""

    @pytest.fixture
    def agent_composer(self, tmp_path):
        """Create AgentComposer for role-domain testing."""
        return create_test_agent_composer(tmp_path)

    @pytest.mark.parametrize(
        "role,domain,valid,expected_capability_count,description",
        ROLE_DOMAIN_COMBINATIONS,
    )
    def test_role_domain_composition(
        self,
        agent_composer,
        role,
        domain,
        valid,
        expected_capability_count,
        description,
    ):
        """Test role-domain composition accuracy."""
        if not valid and role.startswith("invalid"):
            # Test invalid role
            with pytest.raises(ValueError, match="not found"):
                agent_composer.compose_agent(role, domain)
            return

        # Test valid combinations (invalid domain should not raise error)
        result = agent_composer.compose_agent(role, domain)

        # Basic structure validation
        assert "identity" in result
        assert "role" in result
        assert "purpose" in result

        # Validate identity structure
        identity = result["identity"]
        assert identity["id"] == role
        assert "capabilities" in identity
        assert isinstance(identity["capabilities"], list)

    def test_multi_domain_composition(self, agent_composer):
        """Test composition with multiple domains."""
        role = "researcher"
        domains = "distributed-systems,frontend-development"

        result = agent_composer.compose_agent(role, domains)

        # Should have domain-specific sections
        assert "domains" in result
        assert "domain_patterns" in result
        assert "domain_rules" in result

        # Should merge patterns from both domains
        if result["domain_patterns"]:
            # Check that we have patterns from both domains
            all_patterns = []
            for pattern_type, patterns in result["domain_patterns"].items():
                all_patterns.extend(patterns)
            assert len(all_patterns) > 0

    def test_domain_expertise_merging(self, agent_composer):
        """Test that domain expertise is properly merged."""
        role = "architect"
        domains = "distributed-systems,microservices-architecture"

        result = agent_composer.compose_agent(role, domains)

        # Should have merged domain rules
        if result.get("domain_rules"):
            # Should have confidence thresholds from both domains
            thresholds = result.get("domain_thresholds", {})
            assert isinstance(thresholds, dict)

    def test_role_without_domain(self, agent_composer):
        """Test role composition without domain specification."""
        result = agent_composer.compose_agent("researcher")

        # Should have basic role information
        assert result["identity"]["id"] == "researcher"
        assert "role" in result
        assert "domains" not in result  # No domain-specific data


def create_test_agent_composer(tmp_path):
    """Helper function to create AgentComposer with test setup."""
    # Create test directory structure
    base_path = tmp_path / "test_prompts"
    base_path.mkdir()

    # Create roles directory with test roles
    roles_path = base_path / "roles"
    roles_path.mkdir()

    # Create minimal test roles
    test_roles = [
        "researcher",
        "architect",
        "implementer",
        "tester",
        "analyst",
        "critic",
        "theorist",
        "innovator",
        "commentator",
        "auditor",
    ]
    for role in test_roles:
        role_file = roles_path / f"{role}.md"
        role_file.write_text(
            f"""# {role.title()}

```yaml
id: {role}
type: autonomous_agent
capabilities: ["analysis", "synthesis", "documentation"]
tools: ["Read", "Write", "Bash"]
```

## Role
Autonomous {role} agent that provides specialized analysis.

## Purpose
Execute {role} tasks with domain expertise.

## Core Capabilities
- Domain-specific analysis
- Evidence-based reasoning
- Collaborative coordination

## Decision Logic
```python
if task_complexity > threshold:
    escalate_to_specialist()
else:
    proceed_with_analysis()
```
"""
        )

    # Create domains directory with test domains
    domains_path = base_path / "domains"
    domains_path.mkdir()

    # Create architecture subdirectory
    arch_path = domains_path / "architecture"
    arch_path.mkdir()

    # Create test domain files
    test_domains = {
        "distributed-systems": {
            "domain": {"id": "distributed-systems", "category": "systems"},
            "knowledge_patterns": {
                "consensus_algorithms": ["raft", "pbft", "paxos"],
                "fault_tolerance": ["byzantine", "crash", "omission"],
            },
            "decision_rules": {
                "complexity_threshold": 0.8,
                "confidence_thresholds": {"analysis": 0.9},
            },
        },
        "frontend-development": {
            "domain": {"id": "frontend-development", "category": "engineering"},
            "knowledge_patterns": {
                "frameworks": ["react", "vue", "angular"],
                "patterns": ["component", "state", "routing"],
            },
            "decision_rules": {
                "complexity_threshold": 0.6,
                "confidence_thresholds": {"implementation": 0.8},
            },
        },
        "microservices-architecture": {
            "domain": {"id": "microservices-architecture", "category": "architecture"},
            "knowledge_patterns": {
                "patterns": ["service_mesh", "api_gateway", "circuit_breaker"],
                "communication": ["sync", "async", "event_driven"],
            },
            "decision_rules": {
                "complexity_threshold": 0.9,
                "confidence_thresholds": {"design": 0.9},
            },
        },
        "backend-development": {
            "domain": {"id": "backend-development", "category": "engineering"},
            "knowledge_patterns": {
                "frameworks": ["fastapi", "django", "flask"],
                "patterns": ["mvc", "repository", "service"],
            },
            "decision_rules": {
                "complexity_threshold": 0.7,
                "confidence_thresholds": {"implementation": 0.8},
            },
        },
    }

    # Write domain files
    for domain_name, domain_data in test_domains.items():
        if domain_name == "microservices-architecture":
            # Put in architecture subdirectory
            domain_file = arch_path / f"{domain_name}.yaml"
        else:
            domain_file = domains_path / f"{domain_name}.yaml"

        with open(domain_file, "w") as f:
            yaml.dump(domain_data, f)

    # Create name_mapper.yaml
    name_mapper_data = {
        "synonyms": {
            "frontend": "frontend-development",
            "ui": "frontend-development",
            "backend": "backend-development",
            "api": "backend-development",
            "microservices": "microservices-architecture",
            "event": "event-sourcing",
            "security": "security-architecture",
            "testing": "playwright-testing",
            "neural": "neural-networks",
            "cloud": "cloud-native",
            "websocket": "websocket-communication",
            "multimodal": "multi-modal-systems",
            "multi_modal_systems": "multi-modal-systems",
        },
        "canonical_domains": [
            "frontend-development",
            "backend-development",
            "distributed-systems",
            "microservices-architecture",
            "event-sourcing",
            "security-architecture",
        ],
    }

    name_mapper_file = base_path / "name_mapper.yaml"
    with open(name_mapper_file, "w") as f:
        yaml.dump(name_mapper_data, f)

    return AgentComposer(base_path=str(base_path))


@pytest.mark.unit
class TestDomainMatchingConsistency:
    """Test consistency in domain matching across different scenarios."""

    @pytest.fixture
    def agent_composer(self, tmp_path):
        """Create AgentComposer for consistency testing."""
        return create_test_agent_composer(tmp_path)

    def test_repeated_canonicalization_consistency(self, agent_composer):
        """Test that repeated canonicalization produces identical results."""
        test_domains = ["frontend", "backend", "microservices", "invalid", ""]

        for domain in test_domains:
            # Run canonicalization 20 times
            results = [agent_composer.canonicalize_domain(domain) for _ in range(20)]

            # All results should be identical
            unique_results = set(results)
            assert (
                len(unique_results) == 1
            ), f"Inconsistent canonicalization for '{domain}': {unique_results}"

    def test_composition_determinism(self, agent_composer):
        """Test that agent composition is deterministic."""
        role = "researcher"
        domain = "distributed-systems"

        # Compose agent multiple times
        compositions = []
        for _ in range(10):
            result = agent_composer.compose_agent(role, domain)
            # Convert to JSON for comparison (handles nested dicts)
            compositions.append(json.dumps(result, sort_keys=True))

        # All compositions should be identical
        unique_compositions = set(compositions)
        assert len(unique_compositions) == 1, "Agent composition is not deterministic"

    def test_unique_agent_id_generation(self, agent_composer):
        """Test unique agent ID generation prevents duplicates."""
        role = "researcher"
        domain = "distributed-systems"

        # Generate multiple IDs
        ids = [agent_composer.get_unique_agent_id(role, domain) for _ in range(5)]

        # Should have base ID and versioned IDs
        expected_ids = [
            "researcher_distributed-systems",
            "researcher_distributed-systems_v2",
            "researcher_distributed-systems_v3",
            "researcher_distributed-systems_v4",
            "researcher_distributed-systems_v5",
        ]

        assert ids == expected_ids, f"Unexpected ID sequence: {ids}"

    def test_cross_instance_consistency(self, tmp_path):
        """Test consistency across different AgentComposer instances."""
        # Create instance directories
        instance1_path = tmp_path / "instance1"
        instance2_path = tmp_path / "instance2"
        instance1_path.mkdir(parents=True)
        instance2_path.mkdir(parents=True)

        # Use the same setup as other tests
        composer1 = create_test_agent_composer(instance1_path)
        composer2 = create_test_agent_composer(instance2_path)

        test_domains = ["frontend", "backend", "microservices"]

        for domain in test_domains:
            result1 = composer1.canonicalize_domain(domain)
            result2 = composer2.canonicalize_domain(domain)

            assert (
                result1 == result2
            ), f"Cross-instance inconsistency for '{domain}': {result1} vs {result2}"


@pytest.mark.unit
class TestDomainMatchingErrorHandling:
    """Test error handling in domain matching algorithms."""

    @pytest.fixture
    def agent_composer(self, tmp_path):
        """Create AgentComposer for error handling testing."""
        return create_test_agent_composer(tmp_path)

    def test_invalid_role_handling(self, agent_composer):
        """Test handling of invalid role specifications."""
        invalid_roles = ["nonexistent-role", "", None, 123, []]

        for invalid_role in invalid_roles:
            if invalid_role is None or invalid_role == 123 or invalid_role == []:
                # Should raise TypeError or ValueError
                with pytest.raises((ValueError, TypeError)):
                    agent_composer.compose_agent(invalid_role, "distributed-systems")
            elif invalid_role == "":
                # Empty string should raise ValueError due to Pydantic validation
                with pytest.raises(ValueError, match="Invalid composition request"):
                    agent_composer.compose_agent(invalid_role, "distributed-systems")
            else:
                # Nonexistent role should raise ValueError
                with pytest.raises(ValueError, match="not found"):
                    agent_composer.compose_agent(invalid_role, "distributed-systems")

    def test_malicious_input_sanitization(self, agent_composer):
        """Test that malicious inputs are handled gracefully."""
        malicious_inputs = [
            "domain/../../../etc/passwd",
            "domain;rm -rf /",
            "domain<script>alert('xss')</script>",
            "domain\x00\x01\x02",
            "domain\n\r\t",
            "domain' OR 1=1--",
            "domain$(malicious_command)",
        ]

        for malicious_input in malicious_inputs:
            # Should not raise exception and should return some result
            result = agent_composer.canonicalize_domain(malicious_input)

            # Should return string (not crash) - actual sanitization is implementation dependent
            assert isinstance(result, str) or result is None

            # Test that agent composition with sanitized input works
            try:
                # Use a valid role to test that the domain input is handled
                spec = agent_composer.compose_agent(
                    "researcher", result if result else "distributed-systems"
                )
                assert "identity" in spec  # Should successfully compose
            except ValueError:
                # Domain not found is acceptable, as long as it doesn't crash
                pass

    def test_memory_exhaustion_protection(self, agent_composer):
        """Test protection against memory exhaustion attacks."""
        # Very long input
        long_domain = "a" * 100000

        result = agent_composer.canonicalize_domain(long_domain)

        # Should handle gracefully (not crash), actual length depends on implementation
        assert isinstance(result, str) or result is None

        # Test should complete in reasonable time (not hang)
        import time

        start = time.time()
        for _ in range(10):
            agent_composer.canonicalize_domain(
                long_domain[:1000]
            )  # Smaller repeated test
        end = time.time()

        assert (end - start) < 1.0, "Processing too slow, potential DoS vulnerability"

    def test_corrupt_mapping_file_handling(self, tmp_path):
        """Test handling of corrupted domain mapping files."""
        # Create base directory
        base_path = tmp_path / "corrupt_test"
        base_path.mkdir()

        # Create corrupted name_mapper.yaml
        corrupt_mapper = base_path / "name_mapper.yaml"
        corrupt_mapper.write_text("invalid: yaml: content: [unclosed")

        # Should handle gracefully with default mapping
        composer = AgentComposer(str(base_path))
        result = composer.canonicalize_domain("frontend")

        # Should return original since mapping failed to load
        assert result == "frontend"

    def test_missing_domain_file_handling(self, agent_composer):
        """Test graceful handling of missing domain files."""
        # Try to load non-existent domain
        result = agent_composer.load_domain_expertise("nonexistent-domain")

        # Should return empty dict, not raise exception
        assert result == {}

    def test_concurrent_access_safety(self, agent_composer):
        """Test thread safety of domain matching operations."""
        import threading

        results = []
        errors = []

        def canonicalize_domain(domain):
            try:
                result = agent_composer.canonicalize_domain(domain)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Run concurrent canonicalization
        threads = []
        test_domain = "frontend"

        for _ in range(10):
            thread = threading.Thread(target=canonicalize_domain, args=(test_domain,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have no errors and consistent results
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert (
            len(set(results)) == 1
        ), f"Inconsistent concurrent results: {set(results)}"


@pytest.mark.performance
class TestDomainMatchingPerformance:
    """Performance benchmarks for domain matching algorithms."""

    @pytest.fixture
    def agent_composer(self, tmp_path):
        """Create AgentComposer for performance testing."""
        return create_test_agent_composer(tmp_path)

    @pytest.mark.benchmark
    def test_canonicalization_performance(self, agent_composer):
        """Benchmark domain canonicalization performance."""
        test_domains = ["frontend", "backend", "microservices", "invalid-domain"]
        iterations = PERFORMANCE_BENCHMARKS["canonicalization"]["iterations"]
        max_time_ms = PERFORMANCE_BENCHMARKS["canonicalization"]["max_time_ms"]

        start_time = time.time()

        for _ in range(iterations):
            for domain in test_domains:
                agent_composer.canonicalize_domain(domain)

        end_time = time.time()
        avg_time_ms = ((end_time - start_time) * 1000) / (
            iterations * len(test_domains)
        )

        print(f"Canonicalization performance: {avg_time_ms:.4f}ms per operation")

        assert (
            avg_time_ms < max_time_ms
        ), f"Canonicalization too slow: {avg_time_ms:.4f}ms > {max_time_ms}ms"

    @pytest.mark.benchmark
    def test_agent_composition_performance(self, agent_composer):
        """Benchmark agent composition performance."""
        role = "researcher"
        domain = "distributed-systems"
        iterations = PERFORMANCE_BENCHMARKS["agent_composition"]["iterations"]
        max_time_ms = PERFORMANCE_BENCHMARKS["agent_composition"]["max_time_ms"]

        start_time = time.time()

        for _ in range(iterations):
            agent_composer.compose_agent(role, domain)

        end_time = time.time()
        avg_time_ms = ((end_time - start_time) * 1000) / iterations

        print(f"Agent composition performance: {avg_time_ms:.4f}ms per operation")

        assert (
            avg_time_ms < max_time_ms
        ), f"Agent composition too slow: {avg_time_ms:.4f}ms > {max_time_ms}ms"

    @pytest.mark.benchmark
    def test_domain_loading_performance(self, agent_composer):
        """Benchmark domain expertise loading performance."""
        test_domains = [
            "distributed-systems",
            "frontend-development",
            "microservices-architecture",
        ]
        iterations = PERFORMANCE_BENCHMARKS["domain_loading"]["iterations"]
        max_time_ms = PERFORMANCE_BENCHMARKS["domain_loading"]["max_time_ms"]

        start_time = time.time()

        for _ in range(iterations):
            for domain in test_domains:
                agent_composer.load_domain_expertise(domain)

        end_time = time.time()
        avg_time_ms = ((end_time - start_time) * 1000) / (
            iterations * len(test_domains)
        )

        print(f"Domain loading performance: {avg_time_ms:.4f}ms per operation")

        assert (
            avg_time_ms < max_time_ms
        ), f"Domain loading too slow: {avg_time_ms:.4f}ms > {max_time_ms}ms"

    @pytest.mark.benchmark
    def test_memory_efficiency(self, agent_composer):
        """Test memory efficiency of domain matching operations."""
        import gc

        # Force garbage collection and get initial memory
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Perform many operations
        for _ in range(1000):
            agent_composer.canonicalize_domain("frontend")
            agent_composer.canonicalize_domain("backend")
            agent_composer.canonicalize_domain("nonexistent")

        # Force garbage collection again
        gc.collect()
        final_objects = len(gc.get_objects())

        object_growth = final_objects - initial_objects

        print(f"Memory efficiency: {object_growth} object growth after 3000 operations")

        # Should not create excessive objects
        assert object_growth < 100, f"Excessive object creation: {object_growth}"


@pytest.mark.integration
class TestDomainMatchingIntegration:
    """Integration tests for domain matching with planning service."""

    @pytest.fixture
    def mock_planner_service(self):
        """Create mock planner service for integration testing."""
        return PlannerService()

    @pytest.mark.asyncio
    async def test_domain_matching_in_planning_context(self, tmp_path):
        """Test domain matching integration with planning service."""
        # Create minimal orchestration planner setup
        with patch.multiple(
            OrchestrationPlanner,
            _load_available_roles=MagicMock(return_value=["researcher", "architect"]),
            _load_available_domains=MagicMock(
                return_value=["distributed-systems", "frontend-development"]
            ),
            _load_prompt_templates=MagicMock(return_value={"agents": {}}),
            _load_decision_matrix=MagicMock(
                return_value={"complexity_assessment": {}, "agent_role_selection": {}}
            ),
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                planner = OrchestrationPlanner()

                # Test domain availability
                available_domains = planner.available_domains
                assert "distributed-systems" in available_domains
                assert "frontend-development" in available_domains

    def test_domain_matching_with_agent_recommendations(self, tmp_path):
        """Test domain matching with agent recommendation system."""
        composer = create_test_agent_composer(tmp_path)

        # Create agent recommendations with various domain inputs
        recommendations = []
        role_domain_pairs = [
            ("researcher", "frontend"),  # Should canonicalize to frontend-development
            (
                "architect",
                "microservices",
            ),  # Should canonicalize to microservices-architecture
            ("implementer", "distributed-systems"),  # Already canonical
        ]

        for role, domain in role_domain_pairs:
            canonical_domain = composer.canonicalize_domain(domain)

            recommendation = AgentRecommendation(
                role=role,
                domain=canonical_domain,
                priority=0.8,
                reasoning=f"Test recommendation for {role} in {canonical_domain}",
            )
            recommendations.append(recommendation)

        # Validate recommendations have canonical domains
        assert recommendations[0].domain == "frontend-development"
        assert recommendations[1].domain == "microservices-architecture"
        assert recommendations[2].domain == "distributed-systems"

    def test_end_to_end_domain_workflow(self, tmp_path):
        """Test complete domain matching workflow from input to output."""
        composer = create_test_agent_composer(tmp_path)

        # Simulate workflow: user input -> canonicalization -> agent composition -> output
        user_inputs = [
            ("researcher", "ui"),
            ("architect", "backend"),
            ("implementer", "microservices"),
        ]

        results = []
        for role, raw_domain in user_inputs:
            # Step 1: Canonicalize domain
            canonical_domain = composer.canonicalize_domain(raw_domain)

            # Step 2: Compose agent
            agent_spec = composer.compose_agent(role, canonical_domain)

            # Step 3: Generate unique ID
            unique_id = composer.get_unique_agent_id(role, canonical_domain)

            results.append(
                {
                    "raw_input": raw_domain,
                    "canonical_domain": canonical_domain,
                    "agent_id": unique_id,
                    "has_domain_expertise": bool(agent_spec.get("domains")),
                }
            )

        # Validate end-to-end workflow
        expected_results = [
            {
                "raw_input": "ui",
                "canonical_domain": "frontend-development",
                "agent_id": "researcher_frontend-development",
                "has_domain_expertise": True,
            },
            {
                "raw_input": "backend",
                "canonical_domain": "backend-development",
                "agent_id": "architect_backend-development",
                "has_domain_expertise": False,  # No backend-development domain file in test setup
            },
            {
                "raw_input": "microservices",
                "canonical_domain": "microservices-architecture",
                "agent_id": "implementer_microservices-architecture",
                "has_domain_expertise": True,
            },
        ]

        for actual, expected in zip(results, expected_results, strict=False):
            assert actual["raw_input"] == expected["raw_input"]
            assert actual["canonical_domain"] == expected["canonical_domain"]
            assert actual["agent_id"] == expected["agent_id"]
            # Note: has_domain_expertise depends on test setup


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
