"""Performance testing fixtures and utilities."""

import asyncio
import gc
import time
from collections.abc import Callable
from typing import Any

import psutil
import pytest

from khive.services.artifacts import ArtifactsService
from khive.services.cache.service import CacheService
from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.plan.planner_service import PlannerService
from khive.services.session.session_service import SessionService


class PerformanceProfiler:
    """Enhanced performance profiler for khive services."""

    def __init__(self):
        self.reset()
        self.process = psutil.Process()

    def reset(self):
        """Reset all measurements."""
        self.start_time = None
        self.end_time = None
        self.operation_times = []
        self.memory_snapshots = []
        self.cpu_snapshots = []
        self.error_count = 0
        self.success_count = 0
        self.custom_metrics = {}

    def start_measurement(self):
        """Start performance measurement with initial system state."""
        self.start_time = time.perf_counter()
        self.record_system_state()

    def end_measurement(self):
        """End performance measurement with final system state."""
        self.end_time = time.perf_counter()
        self.record_system_state()

    def record_system_state(self):
        """Record current system state."""
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent()

            self.memory_snapshots.append({
                "timestamp": time.perf_counter(),
                "rss_mb": memory_info.rss / (1024 * 1024),
                "vms_mb": memory_info.vms / (1024 * 1024),
            })

            self.cpu_snapshots.append({
                "timestamp": time.perf_counter(),
                "cpu_percent": cpu_percent,
            })
        except Exception:
            # Handle cases where process monitoring fails
            pass

    def record_operation(
        self,
        duration: float,
        success: bool = True,
        operation_type: str = "general",
        metadata: dict | None = None,
    ):
        """Record an individual operation with metadata."""
        self.operation_times.append({
            "duration": duration,
            "success": success,
            "operation_type": operation_type,
            "timestamp": time.perf_counter(),
            "metadata": metadata or {},
        })

        if success:
            self.success_count += 1
        else:
            self.error_count += 1

    def add_custom_metric(self, name: str, value: Any):
        """Add a custom performance metric."""
        if name not in self.custom_metrics:
            self.custom_metrics[name] = []
        self.custom_metrics[name].append({
            "value": value,
            "timestamp": time.perf_counter(),
        })

    def get_comprehensive_metrics(self) -> dict[str, Any]:
        """Get comprehensive performance metrics."""
        total_time = (
            self.end_time - self.start_time if self.start_time and self.end_time else 0
        )
        total_operations = self.success_count + self.error_count

        # Basic metrics
        metrics = {
            "total_time": total_time,
            "total_operations": total_operations,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(total_operations, 1),
            "error_rate": self.error_count / max(total_operations, 1),
            "throughput": total_operations / max(total_time, 0.001),
        }

        # Operation timing metrics
        if self.operation_times:
            durations = [op["duration"] for op in self.operation_times]
            metrics.update({
                "avg_operation_time": sum(durations) / len(durations),
                "min_operation_time": min(durations),
                "max_operation_time": max(durations),
                "operation_count": len(durations),
                "p50_operation_time": sorted(durations)[len(durations) // 2],
                "p95_operation_time": sorted(durations)[int(len(durations) * 0.95)],
                "p99_operation_time": sorted(durations)[int(len(durations) * 0.99)],
            })

            # Operation type breakdown
            op_types = {}
            for op in self.operation_times:
                op_type = op["operation_type"]
                if op_type not in op_types:
                    op_types[op_type] = []
                op_types[op_type].append(op["duration"])

            metrics["operation_types"] = {
                op_type: {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                }
                for op_type, times in op_types.items()
            }

        # Memory metrics
        if len(self.memory_snapshots) >= 2:
            initial_memory = self.memory_snapshots[0]["rss_mb"]
            peak_memory = max(snap["rss_mb"] for snap in self.memory_snapshots)
            final_memory = self.memory_snapshots[-1]["rss_mb"]

            metrics.update({
                "initial_memory_mb": initial_memory,
                "peak_memory_mb": peak_memory,
                "final_memory_mb": final_memory,
                "memory_growth_mb": final_memory - initial_memory,
                "peak_memory_delta_mb": peak_memory - initial_memory,
            })

        # CPU metrics
        if self.cpu_snapshots:
            cpu_values = [
                snap["cpu_percent"]
                for snap in self.cpu_snapshots
                if snap["cpu_percent"] > 0
            ]
            if cpu_values:
                metrics.update({
                    "avg_cpu_percent": sum(cpu_values) / len(cpu_values),
                    "max_cpu_percent": max(cpu_values),
                    "min_cpu_percent": min(cpu_values),
                })

        # Custom metrics
        if self.custom_metrics:
            metrics["custom_metrics"] = {}
            for name, values in self.custom_metrics.items():
                if values:
                    numeric_values = [
                        v["value"]
                        for v in values
                        if isinstance(v["value"], int | float)
                    ]
                    if numeric_values:
                        metrics["custom_metrics"][name] = {
                            "count": len(values),
                            "avg": sum(numeric_values) / len(numeric_values),
                            "min": min(numeric_values),
                            "max": max(numeric_values),
                        }
                    else:
                        metrics["custom_metrics"][name] = {
                            "count": len(values),
                            "values": [
                                v["value"] for v in values[-5:]
                            ],  # Last 5 values
                        }

        return metrics


class LoadTestRunner:
    """Advanced load testing runner for khive services."""

    def __init__(self, profiler: PerformanceProfiler | None = None):
        self.profiler = profiler or PerformanceProfiler()

    async def run_async_load_test(
        self,
        async_operation: Callable,
        concurrent_tasks: int = 10,
        operations_per_task: int = 10,
        ramp_up_seconds: float = 1.0,
    ) -> dict[str, Any]:
        """Run asynchronous load test with controlled ramp-up."""
        results = {"tasks": [], "errors": [], "start_time": None, "end_time": None}

        async def task_worker(task_id: int, delay: float = 0):
            """Worker coroutine for load testing."""
            if delay > 0:
                await asyncio.sleep(delay)

            task_results = {"operations": 0, "errors": 0, "times": []}

            for op_id in range(operations_per_task):
                start_time = time.perf_counter()
                try:
                    await async_operation()
                    task_results["operations"] += 1
                    success = True
                except Exception as e:
                    task_results["errors"] += 1
                    results["errors"].append(f"Task {task_id}, Op {op_id}: {e!s}")
                    success = False

                end_time = time.perf_counter()
                operation_time = end_time - start_time
                task_results["times"].append(operation_time)

                self.profiler.record_operation(
                    operation_time, success, f"async_task_{task_id}"
                )

            results["tasks"].append(task_results)

        # Start profiling
        self.profiler.start_measurement()
        results["start_time"] = time.perf_counter()

        # Create tasks with staggered start times for ramp-up
        tasks = []
        ramp_delay = ramp_up_seconds / concurrent_tasks if concurrent_tasks > 1 else 0

        for task_id in range(concurrent_tasks):
            delay = task_id * ramp_delay
            task = asyncio.create_task(task_worker(task_id, delay))
            tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # End profiling
        results["end_time"] = time.perf_counter()
        self.profiler.end_measurement()

        # Calculate aggregate metrics
        total_operations = sum(t["operations"] for t in results["tasks"])
        total_errors = sum(t["errors"] for t in results["tasks"])
        all_times = [t for task in results["tasks"] for t in task["times"]]

        results.update({
            "total_operations": total_operations,
            "total_errors": total_errors,
            "success_rate": total_operations / max(total_operations + total_errors, 1),
            "total_time": results["end_time"] - results["start_time"],
            "throughput": total_operations
            / (results["end_time"] - results["start_time"]),
            "avg_response_time": (sum(all_times) / len(all_times) if all_times else 0),
            "performance_metrics": self.profiler.get_comprehensive_metrics(),
        })

        return results


@pytest.fixture
def performance_profiler():
    """Provide a performance profiler instance."""
    profiler = PerformanceProfiler()
    yield profiler
    # Cleanup
    profiler.reset()


@pytest.fixture
def load_test_runner(performance_profiler):
    """Provide a load test runner."""
    return LoadTestRunner(performance_profiler)


@pytest.fixture
def memory_monitor():
    """Provide memory usage monitoring functionality."""

    def measure_memory_usage(func: Callable, *args, **kwargs) -> dict[str, Any]:
        """Measure memory usage of a function call."""
        process = psutil.Process()

        # Force garbage collection before measurement
        gc.collect()
        memory_before = process.memory_info().rss

        # Execute function
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        end_time = time.perf_counter()

        # Measure memory after
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

    return measure_memory_usage


@pytest.fixture
async def orchestration_service():
    """Provide orchestration service for performance testing."""
    # Initialize with test configuration
    orchestrator = LionOrchestrator("test_flow")
    yield orchestrator
    # Cleanup if needed


@pytest.fixture
async def planning_service():
    """Provide planning service for performance testing."""
    planner = PlannerService()
    yield planner
    # Cleanup if needed


@pytest.fixture
async def session_service():
    """Provide session service for performance testing."""
    session_svc = SessionService()
    yield session_svc
    # Cleanup if needed


@pytest.fixture
async def artifacts_service(tmp_path):
    """Provide artifacts service for performance testing."""
    artifacts_svc = ArtifactsService(workspace_path=str(tmp_path))
    yield artifacts_svc
    # Cleanup if needed


@pytest.fixture
async def cache_service():
    """Provide cache service for performance testing."""
    cache_svc = CacheService()
    yield cache_svc
    # Cleanup if needed


@pytest.fixture
def large_dataset_generator():
    """Generate large datasets for stress testing."""

    def generate_dataset(
        size_mb: int = 1, complexity: str = "medium"
    ) -> dict[str, Any]:
        """Generate a large dataset for testing."""
        if complexity == "simple":
            # Simple repetitive data
            data = {"items": ["item_" + str(i) for i in range(size_mb * 1000)]}
        elif complexity == "medium":
            # Medium complexity with nested structures
            data = {
                "categories": [
                    {
                        "id": f"cat_{i}",
                        "items": [
                            {
                                "id": f"item_{i}_{j}",
                                "data": "x" * 100,  # 100 byte payload
                                "metadata": {
                                    "created": time.time(),
                                    "tags": [f"tag_{k}" for k in range(10)],
                                },
                            }
                            for j in range(100)  # 100 items per category
                        ],
                    }
                    for i in range(size_mb * 10)  # Scale categories by MB
                ]
            }
        else:  # complex
            # Complex nested data with deep hierarchies
            data = {"root": _generate_recursive_data(depth=10, breadth=size_mb)}

        return data

    def _generate_recursive_data(depth: int, breadth: int) -> dict:
        """Generate recursive nested data structure."""
        if depth <= 0:
            return {"value": "leaf_data_" + "x" * 50}

        return {
            f"branch_{i}": _generate_recursive_data(depth - 1, max(1, breadth // 2))
            for i in range(breadth)
        }

    return generate_dataset


@pytest.fixture
def stress_test_scenarios():
    """Provide stress test scenario configurations."""
    return {
        "memory_stress": {
            "description": "High memory usage scenarios",
            "dataset_sizes": [1, 5, 10, 25, 50],  # MB
            "concurrent_operations": [1, 5, 10, 20],
            "expected_max_memory_mb": 500,
        },
        "cpu_stress": {
            "description": "CPU intensive operations",
            "operation_counts": [100, 500, 1000, 5000],
            "complexity_levels": ["simple", "medium", "complex"],
            "max_duration_seconds": 30,
        },
        "io_stress": {
            "description": "File I/O intensive operations",
            "file_counts": [10, 50, 100, 500],
            "file_sizes": [1024, 10240, 102400],  # bytes
            "concurrent_files": [5, 10, 25],
        },
        "concurrent_stress": {
            "description": "High concurrency scenarios",
            "thread_counts": [10, 25, 50, 100],
            "duration_seconds": [5, 10, 30, 60],
            "operation_rates": [10, 50, 100, 200],  # ops/sec target
        },
    }


@pytest.fixture
def performance_thresholds():
    """Define performance thresholds for different operations."""
    return {
        "orchestration": {
            "simple_operation_ms": 100,
            "complex_operation_ms": 1000,
            "memory_limit_mb": 50,
            "throughput_ops_per_sec": 10,
        },
        "planning": {
            "simple_plan_ms": 200,
            "complex_plan_ms": 2000,
            "memory_limit_mb": 100,
            "throughput_ops_per_sec": 5,
        },
        "session": {
            "session_create_ms": 50,
            "session_load_ms": 25,
            "memory_per_session_mb": 5,
            "concurrent_sessions": 100,
        },
        "artifacts": {
            "file_read_ms": 10,
            "file_write_ms": 25,
            "memory_limit_mb": 25,
            "throughput_ops_per_sec": 50,
        },
        "cache": {
            "cache_get_ms": 5,
            "cache_set_ms": 10,
            "memory_limit_mb": 200,
            "throughput_ops_per_sec": 1000,
        },
    }


@pytest.fixture(autouse=True)
def performance_test_cleanup():
    """Ensure proper cleanup after performance tests."""
    yield
    # Force garbage collection after each test
    gc.collect()

    # Additional cleanup can be added here
    # e.g., clear caches, close connections, etc.
