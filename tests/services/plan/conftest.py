"""Configuration and fixtures for complexity assessment testing.

This module provides:
- Test configuration settings
- Shared fixtures for test modules
- Test data generators and utilities
- Coverage reporting configuration
- Performance benchmarking utilities
"""

import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from khive.services.plan.planner_service import OrchestrationPlanner
from khive.services.plan.triage.complexity_triage import ComplexityTriageService
from tests.fixtures.planning_fixtures import MockDecisionMatrix


class TestConfiguration:
    """Central configuration for complexity assessment tests."""

    # Test markers and categories
    MARKERS = {
        "unit": "Unit tests for individual components",
        "integration": "Integration tests across components",
        "performance": "Performance and load testing",
        "stress": "Stress testing with extreme conditions",
        "regression": "Regression testing for algorithm changes",
        "parametric": "Parametric testing with various inputs",
    }

    # Performance thresholds
    PERFORMANCE_LIMITS = {
        "single_assessment_max_time": 0.1,  # 100ms
        "batch_assessment_max_time": 2.0,  # 2 seconds
        "memory_increase_limit_mb": 10,  # 10MB
        "concurrent_requests": 50,
        "stress_test_iterations": 10000,
    }

    # Test data configuration
    TEST_DATA_CONFIG = {
        "sample_size": 100,
        "edge_case_count": 50,
        "unicode_test_cases": 20,
        "performance_test_sizes": [10, 50, 100, 500, 1000],
        "concurrency_levels": [1, 5, 10, 20, 50],
    }

    # Coverage requirements
    COVERAGE_REQUIREMENTS = {
        "line_coverage_minimum": 90,
        "branch_coverage_minimum": 85,
        "function_coverage_minimum": 95,
    }


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration for all test modules."""
    return TestConfiguration()


@pytest.fixture
def temp_khive_config():
    """Create temporary KHIVE configuration directory with test data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create directory structure
        (temp_path / "prompts" / "roles").mkdir(parents=True)
        (temp_path / "prompts" / "domains" / "backend").mkdir(parents=True)
        (temp_path / "prompts" / "domains" / "frontend").mkdir(parents=True)

        # Create role files
        roles = [
            "researcher",
            "analyst",
            "architect",
            "implementer",
            "tester",
            "critic",
            "reviewer",
            "strategist",
            "auditor",
        ]

        for role in roles:
            role_content = f"""# {role.title()}

## Role Description
A {role} agent specialized in {role} tasks.

## Responsibilities
- Primary {role} duties
- Collaborative planning
- Quality assurance

## Tools
- Standard development tools
- Analysis frameworks
- Communication protocols
"""
            (temp_path / "prompts" / "roles" / f"{role}.md").write_text(role_content)

        # Create domain files
        domains = {
            "backend": [
                "api-design",
                "database-design",
                "microservices",
                "async-programming",
            ],
            "frontend": ["ui-design", "state-management", "component-architecture"],
        }

        for category, domain_list in domains.items():
            for domain in domain_list:
                domain_content = {
                    "name": domain.replace("-", " ").title(),
                    "description": f"Specialized knowledge in {domain}",
                    "patterns": [f"{domain}-pattern-1", f"{domain}-pattern-2"],
                    "tools": [f"{domain}-tool-1", f"{domain}-tool-2"],
                }

                domain_file = (
                    temp_path / "prompts" / "domains" / category / f"{domain}.yaml"
                )
                with open(domain_file, "w") as f:
                    yaml.dump(domain_content, f)

        # Create comprehensive decision matrix
        decision_matrix = {
            "complexity_assessment": {
                "simple": {
                    "indicators": [
                        "simple",
                        "basic",
                        "quick",
                        "easy",
                        "straightforward",
                        "single_objective",
                        "well_defined_scope",
                        "minimal",
                    ],
                    "threshold": 2,
                    "description": "Simple, single-step tasks",
                },
                "medium": {
                    "indicators": [
                        "standard",
                        "typical",
                        "normal",
                        "routine",
                        "multiple_steps",
                        "some_coordination",
                    ],
                    "threshold": 2,
                    "description": "Standard multi-step tasks",
                },
                "complex": {
                    "indicators": [
                        "complex",
                        "sophisticated",
                        "advanced",
                        "distributed",
                        "enterprise",
                        "multiple_objectives",
                        "coordination_needed",
                    ],
                    "threshold": 2,
                    "description": "Complex tasks requiring coordination",
                },
                "very_complex": {
                    "indicators": [
                        "research",
                        "novel",
                        "innovative",
                        "cutting-edge",
                        "entire",
                        "complete",
                        "platform",
                        "ecosystem",
                        "research_frontier",
                        "multiple_disciplines",
                    ],
                    "threshold": 1,
                    "description": "Research and innovation tasks",
                },
            },
            "agent_role_selection": {
                "discovery_phase": {
                    "roles": ["researcher", "analyst"],
                    "triggers": [
                        "research",
                        "analyze",
                        "understand",
                        "investigate",
                        "explore",
                    ],
                },
                "design_phase": {
                    "roles": ["architect", "strategist"],
                    "triggers": [
                        "design",
                        "architect",
                        "plan",
                        "structure",
                        "blueprint",
                    ],
                },
                "implementation_phase": {
                    "roles": ["implementer"],
                    "triggers": ["implement", "build", "create", "develop", "code"],
                },
                "validation_phase": {
                    "roles": ["tester", "critic"],
                    "triggers": ["test", "verify", "validate", "check", "ensure"],
                },
                "refinement_phase": {
                    "roles": ["reviewer", "auditor"],
                    "triggers": ["review", "improve", "refine", "optimize", "document"],
                },
            },
            "workflow_patterns": {
                "sequential": {
                    "description": "Linear progression through phases",
                    "use_cases": ["simple", "well-defined"],
                },
                "parallel": {
                    "description": "Concurrent execution of independent tasks",
                    "use_cases": ["complex", "time-sensitive"],
                },
                "iterative": {
                    "description": "Repeated cycles with refinement",
                    "use_cases": ["research", "optimization"],
                },
            },
        }

        with open(temp_path / "prompts" / "decision_matrix.yaml", "w") as f:
            yaml.dump(decision_matrix, f, default_flow_style=False)

        # Create agent prompts
        agent_prompts = {
            "agents": {role: f"You are a {role} agent." for role in roles},
            "base_context_template": """
You are working within the KHIVE planning system.
Your role: {role}
Domain expertise: {domain}
Task context: {context}
""",
            "user_prompt_template": """
Task: {task}
Requirements: {requirements}
Constraints: {constraints}
""",
        }

        with open(temp_path / "prompts" / "agent_prompts.yaml", "w") as f:
            yaml.dump(agent_prompts, f, default_flow_style=False)

        yield temp_path


@pytest.fixture
def mock_orchestration_planner():
    """Create mock OrchestrationPlanner with test configuration."""
    with patch.multiple(
        OrchestrationPlanner,
        _load_available_roles=MagicMock(
            return_value=[
                "researcher",
                "analyst",
                "architect",
                "implementer",
                "tester",
                "critic",
                "reviewer",
                "strategist",
                "auditor",
            ]
        ),
        _load_available_domains=MagicMock(
            return_value=[
                "api-design",
                "database-design",
                "microservices",
                "ui-design",
                "state-management",
                "async-programming",
            ]
        ),
        _load_prompt_templates=MagicMock(
            return_value={
                "agents": {},
                "base_context_template": "Base context",
                "user_prompt_template": "User prompt",
            }
        ),
        _load_decision_matrix=MagicMock(return_value=MockDecisionMatrix().data),
    ):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
            planner = OrchestrationPlanner()
            planner.matrix = MockDecisionMatrix().data
            return planner


@pytest.fixture
def mock_triage_service():
    """Create mock ComplexityTriageService for testing."""
    with patch("os.getenv") as mock_getenv:
        mock_getenv.return_value = "test_api_key"
        service = ComplexityTriageService()
        service.client = MagicMock()
        return service


@pytest.fixture
def sample_test_inputs():
    """Provide diverse sample inputs for testing."""
    return {
        "simple": [
            "fix login bug",
            "update user profile",
            "add basic validation",
            "simple database query",
            "straightforward implementation",
        ],
        "medium": [
            "implement user authentication",
            "create reporting dashboard",
            "integrate third-party API",
            "standard system refactoring",
            "typical feature development",
        ],
        "complex": [
            "distributed caching system",
            "microservices orchestration",
            "sophisticated analytics platform",
            "enterprise security framework",
            "advanced workflow engine",
        ],
        "very_complex": [
            "research novel algorithms",
            "complete platform migration",
            "innovative distributed system",
            "cutting-edge neural architecture",
            "entire ecosystem transformation",
        ],
    }


@pytest.fixture
def edge_case_inputs():
    """Provide edge case inputs for robustness testing."""
    return [
        "",  # Empty string
        " ",  # Whitespace only
        "\n\t\r",  # Only control characters
        "a" * 10000,  # Very long string
        "研究分布式系统",  # Chinese characters
        "система исследований",  # Cyrillic
        "🔬🧪⚗️ research project",  # Emojis
        "café naïve résumé",  # Accented characters
        "simple\x00complex",  # Null character
        "test\u200btask",  # Zero-width space
        "UPPERCASE lowercase MiXeD",  # Mixed case
        "complex;;sophisticated!!advanced",  # Special punctuation
        "   extra    spaces   between   words   ",  # Extra whitespace
    ]


@pytest.fixture
def performance_test_data():
    """Generate test data for performance testing."""
    return {
        "sizes": [10, 50, 100, 500, 1000, 5000],
        "patterns": {
            "simple": ["simple", "basic", "quick", "easy"],
            "complex": ["complex", "sophisticated", "distributed", "advanced"],
            "very_complex": ["research", "novel", "innovative", "cutting-edge"],
        },
        "load_test_count": 10000,
        "concurrent_users": [1, 5, 10, 20, 50],
        "stress_multipliers": [100, 500, 1000, 5000],
    }


class TestMetrics:
    """Utility class for collecting and analyzing test metrics."""

    def __init__(self):
        self.metrics = {
            "execution_times": [],
            "memory_usage": [],
            "assessment_accuracy": [],
            "error_rates": [],
            "coverage_stats": {},
        }

    def record_execution_time(self, test_name: str, execution_time: float):
        """Record execution time for a test."""
        self.metrics["execution_times"].append(
            {
                "test": test_name,
                "time": execution_time,
            }
        )

    def record_memory_usage(self, test_name: str, memory_mb: float):
        """Record memory usage for a test."""
        self.metrics["memory_usage"].append({"test": test_name, "memory": memory_mb})

    def record_assessment_accuracy(self, expected: str, actual: str, test_input: str):
        """Record assessment accuracy."""
        self.metrics["assessment_accuracy"].append(
            {
                "expected": expected,
                "actual": actual,
                "input": test_input,
                "correct": expected == actual,
            }
        )

    def get_accuracy_rate(self) -> float:
        """Calculate overall accuracy rate."""
        if not self.metrics["assessment_accuracy"]:
            return 0.0

        correct = sum(
            1 for item in self.metrics["assessment_accuracy"] if item["correct"]
        )
        total = len(self.metrics["assessment_accuracy"])
        return correct / total

    def get_average_execution_time(self) -> float:
        """Calculate average execution time."""
        if not self.metrics["execution_times"]:
            return 0.0

        times = [item["time"] for item in self.metrics["execution_times"]]
        return sum(times) / len(times)

    def generate_report(self) -> dict[str, Any]:
        """Generate comprehensive metrics report."""
        return {
            "accuracy_rate": self.get_accuracy_rate(),
            "average_execution_time": self.get_average_execution_time(),
            "total_tests_run": len(self.metrics["execution_times"]),
            "memory_stats": {
                "max_usage": max(
                    [m["memory"] for m in self.metrics["memory_usage"]], default=0
                ),
                "average_usage": sum(
                    [m["memory"] for m in self.metrics["memory_usage"]]
                )
                / max(len(self.metrics["memory_usage"]), 1),
            },
            "performance_summary": {
                "fastest_test": min(
                    self.metrics["execution_times"],
                    key=lambda x: x["time"],
                    default={"test": "N/A", "time": 0},
                ),
                "slowest_test": max(
                    self.metrics["execution_times"],
                    key=lambda x: x["time"],
                    default={"test": "N/A", "time": 0},
                ),
            },
        }


@pytest.fixture
def test_metrics():
    """Provide test metrics collector."""
    return TestMetrics()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    for marker, description in TestConfiguration.MARKERS.items():
        config.addinivalue_line("markers", f"{marker}: {description}")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add automatic markers."""
    for item in items:
        # Add performance marker to performance tests
        if "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)

        # Add integration marker to integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # Add stress marker to stress tests
        if "stress" in item.nodeid:
            item.add_marker(pytest.mark.stress)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before running tests."""
    # Set up test logging
    import logging

    logging.basicConfig(level=logging.DEBUG)

    # Create test data directories if needed
    test_dir = Path(__file__).parent
    (test_dir / "test_artifacts").mkdir(exist_ok=True)
    (test_dir / "test_reports").mkdir(exist_ok=True)

    yield

    # Cleanup after all tests
    # Note: Cleanup is handled by temp directories automatically


@pytest.fixture(autouse=True)
def reset_environment_vars():
    """Reset environment variables before each test."""
    original_env = os.environ.copy()
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
