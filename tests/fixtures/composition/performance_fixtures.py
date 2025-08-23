"""Performance testing fixtures for AgentComposer.

Provides fixtures for testing performance, scalability, and resource usage
under various load conditions and edge cases.
"""

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
import yaml


@pytest.fixture
def large_composition_data(temp_dir):
    """Create large-scale composition test data for performance testing."""

    # Create many roles
    roles_dir = temp_dir / "roles"
    roles_dir.mkdir()

    # Generate 100 different roles
    for i in range(100):
        role_data = {
            "identity": {
                "id": f"role_{i:03d}",
                "type": "specialized",
                "capabilities": [f"skill_{j}" for j in range(10)],
                "tools": ["Read", "Write", "Bash", "Edit"],
            },
            "role": f"Specialized role number {i} for testing performance",
            "purpose": f"Execute tasks of type {i % 10} with high efficiency",
            "capabilities": "\n".join([f"- Capability {j}" for j in range(20)]),
            "decision_logic": f"Follow pattern {i % 5} for decision making",
        }

        role_file = roles_dir / f"role_{i:03d}.yaml"
        role_file.write_text(yaml.dump(role_data))

    # Create many domains with complex hierarchies
    domains_dir = temp_dir / "domains"
    domains_dir.mkdir()

    # Create 50 categories with 10 domains each
    for cat_i in range(50):
        category_dir = domains_dir / f"category_{cat_i:02d}"
        category_dir.mkdir()

        for dom_i in range(10):
            domain_data = {
                "domain": {
                    "id": f"domain_{cat_i:02d}_{dom_i:02d}",
                    "name": f"Domain {cat_i}-{dom_i}",
                    "description": f"Specialized domain for category {cat_i}, subdomain {dom_i}",
                },
                "knowledge_patterns": {
                    f"pattern_type_{j}": [f"pattern_{j}_{k}" for k in range(20)]
                    for j in range(10)
                },
                "decision_rules": {
                    f"rule_category_{j}": [
                        f"Rule {j}-{k}: Apply pattern {k} when condition {j} is met"
                        for k in range(15)
                    ]
                    for j in range(8)
                },
                "specialized_tools": {
                    f"tool_category_{j}": [f"tool_{j}_{k}" for k in range(25)]
                    for j in range(12)
                },
                "confidence_thresholds": {
                    f"threshold_{j}": 0.5 + (j * 0.05) for j in range(10)
                },
            }

            domain_file = category_dir / f"domain_{cat_i:02d}_{dom_i:02d}.yaml"
            domain_file.write_text(yaml.dump(domain_data))

    return {
        "role_count": 100,
        "domain_count": 500,
        "category_count": 50,
        "base_path": temp_dir,
    }


@pytest.fixture
def performance_test_scenarios():
    """Provide various performance test scenarios."""
    return {
        "composition_scales": [
            {"roles": 1, "domains": 0, "name": "minimal"},
            {"roles": 1, "domains": 1, "name": "simple"},
            {"roles": 1, "domains": 5, "name": "moderate"},
            {"roles": 1, "domains": 10, "name": "complex"},
            {"roles": 1, "domains": 25, "name": "heavy"},
            {"roles": 1, "domains": 50, "name": "extreme"},
        ],
        "concurrent_loads": [
            {"threads": 1, "operations": 100, "name": "sequential"},
            {"threads": 2, "operations": 50, "name": "light_concurrent"},
            {"threads": 4, "operations": 25, "name": "moderate_concurrent"},
            {"threads": 8, "operations": 15, "name": "heavy_concurrent"},
            {"threads": 16, "operations": 10, "name": "extreme_concurrent"},
            {"threads": 32, "operations": 5, "name": "stress_test"},
        ],
        "memory_pressure": [
            {"context_size": 100, "iterations": 1000, "name": "small_contexts"},
            {"context_size": 1000, "iterations": 500, "name": "medium_contexts"},
            {"context_size": 10000, "iterations": 100, "name": "large_contexts"},
            {"context_size": 100000, "iterations": 10, "name": "huge_contexts"},
            {"context_size": 1000000, "iterations": 1, "name": "massive_context"},
        ],
        "file_io_patterns": [
            {"file_count": 10, "file_size": 1024, "name": "many_small"},
            {"file_count": 5, "file_size": 10240, "name": "few_medium"},
            {"file_count": 2, "file_size": 102400, "name": "large_files"},
            {"file_count": 1, "file_size": 1048576, "name": "single_huge"},
        ],
    }


@pytest.fixture
def concurrent_test_setup():
    """Setup for comprehensive concurrent testing."""
    return {
        "thread_configs": [
            {"count": 2, "duration": 5.0, "name": "light_load"},
            {"count": 4, "duration": 10.0, "name": "moderate_load"},
            {"count": 8, "duration": 15.0, "name": "heavy_load"},
            {"count": 16, "duration": 20.0, "name": "stress_load"},
        ],
        "operation_mixes": [
            {
                "name": "read_heavy",
                "load_role": 60,
                "load_domain": 30,
                "compose_agent": 10,
            },
            {
                "name": "balanced",
                "load_role": 40,
                "load_domain": 40,
                "compose_agent": 20,
            },
            {
                "name": "composition_heavy",
                "load_role": 20,
                "load_domain": 20,
                "compose_agent": 60,
            },
        ],
        "contention_scenarios": [
            {
                "name": "same_file_access",
                "description": "Many threads accessing same files",
                "file_overlap": 1.0,  # 100% overlap
            },
            {
                "name": "partial_overlap",
                "description": "Some file access overlap",
                "file_overlap": 0.5,  # 50% overlap
            },
            {
                "name": "no_contention",
                "description": "No file access overlap",
                "file_overlap": 0.0,  # No overlap
            },
        ],
    }


@pytest.fixture
def stress_test_environment():
    """Create environment for stress testing."""
    return {
        "resource_limits": {
            "max_memory_mb": 512,
            "max_file_handles": 1000,
            "max_threads": 100,
            "timeout_seconds": 300,
        },
        "stress_patterns": [
            {
                "name": "memory_stress",
                "description": "Create many large objects in memory",
                "large_compositions": 100,
                "context_size": 50000,
                "domain_count": 25,
            },
            {
                "name": "io_stress",
                "description": "Perform intensive file I/O operations",
                "file_operations": 10000,
                "concurrent_files": 50,
                "file_size_range": (1024, 102400),
            },
            {
                "name": "cpu_stress",
                "description": "Perform CPU-intensive operations",
                "complex_compositions": 1000,
                "deep_nesting": 100,
                "pattern_matching": 10000,
            },
            {
                "name": "mixed_stress",
                "description": "Combined memory, I/O, and CPU stress",
                "duration": 60,  # seconds
                "concurrent_operations": 50,
                "resource_variety": True,
            },
        ],
        "degradation_thresholds": {
            "response_time_increase": 2.0,  # 2x slower acceptable
            "memory_usage_increase": 3.0,  # 3x more memory acceptable
            "error_rate_threshold": 0.05,  # 5% error rate max
            "throughput_decrease": 0.5,  # 50% throughput decrease max
        },
    }


@pytest.fixture
def benchmark_configurations():
    """Provide benchmark configuration scenarios."""
    return {
        "baseline_operations": [
            {
                "name": "single_role_load",
                "operation": "load_agent_role",
                "args": ["researcher"],
                "iterations": 1000,
                "expected_time_per_op": 0.001,  # 1ms
            },
            {
                "name": "single_domain_load",
                "operation": "load_domain_expertise",
                "args": ["software-architecture"],
                "iterations": 1000,
                "expected_time_per_op": 0.001,
            },
            {
                "name": "simple_composition",
                "operation": "compose_agent",
                "args": ["researcher", "software-architecture"],
                "iterations": 500,
                "expected_time_per_op": 0.010,  # 10ms
            },
            {
                "name": "complex_composition",
                "operation": "compose_agent",
                "args": [
                    "implementer",
                    "software-architecture,code-quality,backend-development",
                ],
                "iterations": 100,
                "expected_time_per_op": 0.050,  # 50ms
            },
        ],
        "scalability_tests": [
            {
                "name": "domain_count_scaling",
                "base_operation": "compose_agent",
                "variable": "domain_count",
                "values": [1, 2, 5, 10, 20, 50],
                "expected_scaling": "linear",
            },
            {
                "name": "context_size_scaling",
                "base_operation": "compose_agent",
                "variable": "context_size",
                "values": [100, 500, 1000, 5000, 10000],
                "expected_scaling": "linear",
            },
            {
                "name": "file_size_scaling",
                "base_operation": "load_yaml",
                "variable": "file_size",
                "values": [1024, 5120, 25600, 128000, 640000],  # Up to ~640KB
                "expected_scaling": "linear",
            },
        ],
        "regression_benchmarks": [
            {
                "name": "performance_regression",
                "description": "Detect performance regressions",
                "operations": ["load_role", "load_domain", "compose_agent"],
                "acceptable_degradation": 0.1,  # 10% slower acceptable
                "sample_size": 100,
            }
        ],
    }


class PerformanceMonitor:
    """Monitor and measure performance during tests."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all measurements."""
        self.start_time = None
        self.end_time = None
        self.operation_times = []
        self.memory_usage = []
        self.error_count = 0
        self.success_count = 0

    def start_measurement(self):
        """Start performance measurement."""
        self.start_time = time.time()

    def end_measurement(self):
        """End performance measurement."""
        self.end_time = time.time()

    def record_operation(self, duration: float, success: bool = True):
        """Record an individual operation."""
        self.operation_times.append(duration)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get performance metrics."""
        total_time = (
            self.end_time - self.start_time if self.start_time and self.end_time else 0
        )
        total_operations = self.success_count + self.error_count

        return {
            "total_time": total_time,
            "total_operations": total_operations,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(total_operations, 1),
            "error_rate": self.error_count / max(total_operations, 1),
            "throughput": total_operations / max(total_time, 0.001),
            "avg_operation_time": sum(self.operation_times)
            / max(len(self.operation_times), 1),
            "min_operation_time": (
                min(self.operation_times) if self.operation_times else 0
            ),
            "max_operation_time": (
                max(self.operation_times) if self.operation_times else 0
            ),
            "operation_count": len(self.operation_times),
        }


@pytest.fixture
def performance_monitor():
    """Provide a performance monitor instance."""
    return PerformanceMonitor()


def run_concurrent_operations(
    operation_func: Callable,
    thread_count: int,
    operations_per_thread: int,
    monitor: PerformanceMonitor = None,
) -> dict[str, Any]:
    """Run operations concurrently and measure performance."""

    if monitor is None:
        monitor = PerformanceMonitor()

    results = {"threads": [], "errors": []}

    def worker():
        """Worker function for concurrent operations."""
        thread_results = {"operations": 0, "errors": 0, "times": []}

        for _ in range(operations_per_thread):
            start_time = time.time()
            try:
                operation_func()
                thread_results["operations"] += 1
                success = True
            except Exception as e:
                thread_results["errors"] += 1
                results["errors"].append(str(e))
                success = False

            end_time = time.time()
            operation_time = end_time - start_time
            thread_results["times"].append(operation_time)

            if monitor:
                monitor.record_operation(operation_time, success)

        results["threads"].append(thread_results)

    # Run concurrent operations
    monitor.start_measurement()

    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(worker) for _ in range(thread_count)]
        for future in futures:
            future.result()  # Wait for completion

    monitor.end_measurement()

    # Calculate aggregate results
    total_operations = sum(t["operations"] for t in results["threads"])
    total_errors = sum(t["errors"] for t in results["threads"])
    all_times = [t for thread in results["threads"] for t in thread["times"]]

    results.update(
        {
            "total_operations": total_operations,
            "total_errors": total_errors,
            "success_rate": total_operations / max(total_operations + total_errors, 1),
            "avg_time_per_operation": sum(all_times) / max(len(all_times), 1),
            "min_time": min(all_times) if all_times else 0,
            "max_time": max(all_times) if all_times else 0,
            "performance_metrics": monitor.get_metrics() if monitor else {},
        }
    )

    return results


@pytest.fixture
def concurrent_operation_runner():
    """Provide a runner for concurrent operations."""
    return run_concurrent_operations


def create_large_context(size_kb: int) -> str:
    """Create a large context string for testing."""
    base_text = """
This is a comprehensive context for testing large-scale agent composition.
The context includes detailed requirements, specifications, and background information
that would be typical in real-world scenarios where agents need substantial context
to perform their tasks effectively.

Requirements:
- Analyze the system architecture for scalability issues
- Identify potential performance bottlenecks
- Recommend optimization strategies
- Consider security implications of proposed changes
- Evaluate impact on existing functionality
- Provide cost-benefit analysis of recommendations

Background:
The system currently handles moderate load but needs to scale to support
10x more users while maintaining sub-100ms response times. The architecture
uses a microservices pattern with REST APIs and event-driven communication.
Database performance is becoming a concern with increasing data volume.

Technical Context:
"""

    # Repeat and expand the base text to reach the desired size
    target_size = size_kb * 1024
    current_text = base_text

    while len(current_text.encode("utf-8")) < target_size:
        current_text += base_text
        current_text += f"\n\nSection {len(current_text) // 1000}: Additional technical details and requirements.\n"

    return current_text[:target_size]  # Trim to exact size


@pytest.fixture
def large_context_generator():
    """Provide a generator for large context strings."""
    return create_large_context


def measure_memory_usage(func: Callable, *args, **kwargs) -> dict[str, Any]:
    """Measure memory usage of a function call."""
    import os

    import psutil

    process = psutil.Process(os.getpid())

    # Get memory before
    memory_before = process.memory_info().rss

    # Execute function
    start_time = time.time()
    try:
        result = func(*args, **kwargs)
        success = True
        error = None
    except Exception as e:
        result = None
        success = False
        error = str(e)
    end_time = time.time()

    # Get memory after
    memory_after = process.memory_info().rss

    return {
        "result": result,
        "success": success,
        "error": error,
        "execution_time": end_time - start_time,
        "memory_before_mb": memory_before / (1024 * 1024),
        "memory_after_mb": memory_after / (1024 * 1024),
        "memory_delta_mb": (memory_after - memory_before) / (1024 * 1024),
    }


@pytest.fixture
def memory_usage_monitor():
    """Provide a memory usage monitor."""
    return measure_memory_usage
