"""
MCP Performance Testing Fixtures.

Provides performance monitoring and benchmarking utilities for MCP operations.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import psutil
import pytest


@dataclass
class PerformanceMetrics:
    """Performance metrics for MCP operations."""

    operation_name: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    memory_before: int = 0
    memory_after: int = 0
    cpu_percent: float = 0.0
    success: bool = True
    error_message: str | None = None

    @property
    def duration(self) -> float:
        """Get operation duration in seconds."""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @property
    def memory_delta(self) -> int:
        """Get memory usage change in bytes."""
        return self.memory_after - self.memory_before

    def finish(self, success: bool = True, error_message: str | None = None):
        """Mark operation as finished."""
        self.end_time = time.time()
        self.success = success
        self.error_message = error_message


class MCPPerformanceMonitor:
    """Monitors performance metrics for MCP operations."""

    def __init__(self):
        self.metrics: list[PerformanceMetrics] = []
        self.process = psutil.Process()

    def start_operation(self, operation_name: str) -> PerformanceMetrics:
        """Start monitoring an operation."""
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            memory_before=self.process.memory_info().rss,
            cpu_percent=self.process.cpu_percent(),
        )
        self.metrics.append(metrics)
        return metrics

    def finish_operation(
        self,
        metrics: PerformanceMetrics,
        success: bool = True,
        error_message: str | None = None,
    ):
        """Finish monitoring an operation."""
        metrics.memory_after = self.process.memory_info().rss
        metrics.finish(success, error_message)

    def get_operation_metrics(self, operation_name: str) -> list[PerformanceMetrics]:
        """Get metrics for a specific operation."""
        return [m for m in self.metrics if m.operation_name == operation_name]

    def get_average_duration(self, operation_name: str) -> float:
        """Get average duration for an operation."""
        metrics = self.get_operation_metrics(operation_name)
        if not metrics:
            return 0.0
        return sum(m.duration for m in metrics) / len(metrics)

    def get_memory_usage_stats(self) -> dict[str, Any]:
        """Get memory usage statistics."""
        if not self.metrics:
            return {"total_operations": 0}

        memory_deltas = [m.memory_delta for m in self.metrics if m.success]

        return {
            "total_operations": len(self.metrics),
            "successful_operations": len([m for m in self.metrics if m.success]),
            "max_memory_increase": max(memory_deltas) if memory_deltas else 0,
            "min_memory_increase": min(memory_deltas) if memory_deltas else 0,
            "average_memory_increase": (
                sum(memory_deltas) / len(memory_deltas) if memory_deltas else 0
            ),
            "total_memory_increase": sum(memory_deltas) if memory_deltas else 0,
        }

    def get_performance_report(self) -> dict[str, Any]:
        """Get comprehensive performance report."""
        operations = set(m.operation_name for m in self.metrics)

        report = {
            "total_operations": len(self.metrics),
            "operation_types": len(operations),
            "memory_stats": self.get_memory_usage_stats(),
            "operation_summaries": {},
        }

        for op_name in operations:
            op_metrics = self.get_operation_metrics(op_name)
            successful = [m for m in op_metrics if m.success]
            failed = [m for m in op_metrics if not m.success]

            report["operation_summaries"][op_name] = {
                "total_count": len(op_metrics),
                "successful_count": len(successful),
                "failed_count": len(failed),
                "average_duration": (
                    sum(m.duration for m in successful) / len(successful)
                    if successful
                    else 0
                ),
                "max_duration": (
                    max(m.duration for m in successful) if successful else 0
                ),
                "min_duration": (
                    min(m.duration for m in successful) if successful else 0
                ),
            }

        return report

    def clear_metrics(self):
        """Clear all collected metrics."""
        self.metrics.clear()

    def assert_performance_thresholds(
        self,
        operation_name: str,
        max_duration: float | None = None,
        max_memory_mb: float | None = None,
        min_success_rate: float | None = None,
    ):
        """Assert that performance thresholds are met."""
        metrics = self.get_operation_metrics(operation_name)

        if not metrics:
            raise AssertionError(f"No metrics found for operation: {operation_name}")

        successful = [m for m in metrics if m.success]

        # Check success rate
        if min_success_rate is not None:
            success_rate = len(successful) / len(metrics)
            assert (
                success_rate >= min_success_rate
            ), f"Success rate {success_rate:.2%} below threshold {min_success_rate:.2%}"

        # Check duration (only for successful operations)
        if max_duration is not None and successful:
            avg_duration = sum(m.duration for m in successful) / len(successful)
            assert (
                avg_duration <= max_duration
            ), f"Average duration {avg_duration:.3f}s exceeds threshold {max_duration:.3f}s"

        # Check memory usage
        if max_memory_mb is not None and successful:
            max_memory_bytes = max_memory_mb * 1024 * 1024
            avg_memory_delta = sum(m.memory_delta for m in successful) / len(successful)
            assert (
                avg_memory_delta <= max_memory_bytes
            ), f"Average memory increase {avg_memory_delta / 1024 / 1024:.1f}MB exceeds threshold {max_memory_mb}MB"


class MCPConcurrencyTester:
    """Tests MCP operations under concurrent load."""

    def __init__(self, performance_monitor: MCPPerformanceMonitor):
        self.performance_monitor = performance_monitor

    async def run_concurrent_operations(
        self,
        operation_func,
        operation_args: list[Any],
        concurrency_level: int = 5,
        operation_name: str = "concurrent_operation",
    ) -> list[Any]:
        """Run operations concurrently and measure performance."""

        async def monitored_operation(args):
            metrics = self.performance_monitor.start_operation(
                f"{operation_name}_concurrent"
            )
            try:
                result = await operation_func(*args)
                self.performance_monitor.finish_operation(metrics, success=True)
                return result
            except Exception as e:
                self.performance_monitor.finish_operation(
                    metrics, success=False, error_message=str(e)
                )
                raise

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency_level)

        async def bounded_operation(args):
            async with semaphore:
                return await monitored_operation(args)

        # Run all operations concurrently
        tasks = [bounded_operation(args) for args in operation_args]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return results

    async def stress_test_operation(
        self,
        operation_func,
        operation_args: Any,
        duration_seconds: float = 10.0,
        max_concurrent: int = 10,
        operation_name: str = "stress_test",
    ) -> dict[str, Any]:
        """Stress test an operation over a period of time."""
        start_time = time.time()
        operations_completed = 0
        errors = []

        semaphore = asyncio.Semaphore(max_concurrent)

        async def stress_operation():
            nonlocal operations_completed
            async with semaphore:
                metrics = self.performance_monitor.start_operation(
                    f"{operation_name}_stress"
                )
                try:
                    await operation_func(*operation_args)
                    self.performance_monitor.finish_operation(metrics, success=True)
                    operations_completed += 1
                except Exception as e:
                    self.performance_monitor.finish_operation(
                        metrics, success=False, error_message=str(e)
                    )
                    errors.append(str(e))

        tasks = []
        while time.time() - start_time < duration_seconds:
            # Add new tasks periodically
            if len([t for t in tasks if not t.done()]) < max_concurrent:
                task = asyncio.create_task(stress_operation())
                tasks.append(task)

            # Small delay to prevent overwhelming
            await asyncio.sleep(0.01)

        # Wait for remaining tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        total_duration = time.time() - start_time

        return {
            "total_duration": total_duration,
            "operations_completed": operations_completed,
            "operations_per_second": operations_completed / total_duration,
            "error_count": len(errors),
            "error_rate": len(errors) / max(operations_completed + len(errors), 1),
            "errors": errors[:10],  # First 10 errors
        }


# Pytest fixtures
@pytest.fixture
def mcp_performance_monitor() -> MCPPerformanceMonitor:
    """Create MCP performance monitor."""
    monitor = MCPPerformanceMonitor()
    yield monitor
    monitor.clear_metrics()


@pytest.fixture
def mcp_concurrency_tester(
    mcp_performance_monitor: MCPPerformanceMonitor,
) -> MCPConcurrencyTester:
    """Create MCP concurrency tester."""
    return MCPConcurrencyTester(mcp_performance_monitor)


@pytest.fixture
def performance_thresholds() -> dict[str, Any]:
    """Default performance thresholds for MCP operations."""
    return {
        "mcp_server_startup": {
            "max_duration": 5.0,  # 5 seconds
            "max_memory_mb": 50.0,  # 50MB
            "min_success_rate": 0.95,  # 95%
        },
        "mcp_tool_call": {
            "max_duration": 2.0,  # 2 seconds
            "max_memory_mb": 10.0,  # 10MB
            "min_success_rate": 0.98,  # 98%
        },
        "mcp_server_shutdown": {
            "max_duration": 3.0,  # 3 seconds
            "max_memory_mb": 5.0,  # 5MB (should free memory)
            "min_success_rate": 0.99,  # 99%
        },
    }
