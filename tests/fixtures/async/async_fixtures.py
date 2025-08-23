"""
Comprehensive async testing fixtures for khive system.

Provides fixtures for:
- Async resource management testing
- Concurrency pattern validation
- Memory leak detection
- Timeout and cancellation scenarios
- Performance benchmarking
"""

import asyncio
import gc
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from memory_profiler import memory_usage


class AsyncTestHarness:
    """Comprehensive test harness for async operations and concurrency testing."""

    def __init__(self):
        self.operations_log: list[dict[str, Any]] = []
        self.resource_tracker: dict[str, Any] = {}
        self.timing_data: dict[str, list[float]] = {}
        self.error_log: list[dict[str, Any]] = []
        self._operation_counter = 0

    def log_operation(self, operation_type: str, details: dict[str, Any]):
        """Log an async operation for analysis."""
        self._operation_counter += 1
        self.operations_log.append(
            {
                "id": self._operation_counter,
                "type": operation_type,
                "timestamp": time.time(),
                "details": details,
            }
        )

    def log_timing(self, operation_name: str, duration: float):
        """Log operation timing data."""
        if operation_name not in self.timing_data:
            self.timing_data[operation_name] = []
        self.timing_data[operation_name].append(duration)

    def log_error(self, operation_id: str, error: Exception):
        """Log an error that occurred during testing."""
        self.error_log.append(
            {
                "operation_id": operation_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "timestamp": time.time(),
            }
        )

    def get_performance_summary(self) -> dict[str, Any]:
        """Get performance summary of logged operations."""
        summary = {}
        for op_name, durations in self.timing_data.items():
            summary[op_name] = {
                "count": len(durations),
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "total_duration": sum(durations),
            }
        return summary

    def reset(self):
        """Reset all tracked data."""
        self.operations_log.clear()
        self.resource_tracker.clear()
        self.timing_data.clear()
        self.error_log.clear()
        self._operation_counter = 0


class MockAsyncResource:
    """Mock async resource with configurable behavior for testing."""

    def __init__(
        self,
        resource_id: str,
        setup_delay: float = 0.01,
        cleanup_delay: float = 0.01,
        fail_setup: bool = False,
        fail_cleanup: bool = False,
    ):
        self.resource_id = resource_id
        self.setup_delay = setup_delay
        self.cleanup_delay = cleanup_delay
        self.fail_setup = fail_setup
        self.fail_cleanup = fail_cleanup
        self.is_active = False
        self.setup_called = False
        self.cleanup_called = False

    async def __aenter__(self):
        if self.fail_setup:
            raise RuntimeError(f"Setup failed for {self.resource_id}")

        await asyncio.sleep(self.setup_delay)
        self.is_active = True
        self.setup_called = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.fail_cleanup:
            raise RuntimeError(f"Cleanup failed for {self.resource_id}")

        await asyncio.sleep(self.cleanup_delay)
        self.is_active = False
        self.cleanup_called = True
        return False


@asynccontextmanager
async def async_timeout_context(timeout: float) -> AsyncGenerator[None, None]:
    """Context manager for testing timeout scenarios."""
    try:
        yield
    except asyncio.TimeoutError:
        # Re-raise timeout errors for test verification
        raise
    except Exception as e:
        # Log other exceptions but don't suppress them
        raise


@asynccontextmanager
async def memory_monitor_context(
    max_increase_mb: float = 15.0,
) -> AsyncGenerator[None, None]:
    """Context manager for monitoring memory usage during async operations."""
    gc.collect()
    initial_memory = memory_usage()[0]

    try:
        yield
    finally:
        gc.collect()
        final_memory = memory_usage()[0]
        increase = final_memory - initial_memory

        if increase > max_increase_mb:
            pytest.fail(
                f"Memory usage increased by {increase:.2f}MB (max: {max_increase_mb}MB)"
            )


class AsyncOperationPool:
    """Pool of async operations for concurrent testing."""

    def __init__(self, pool_size: int = 10):
        self.pool_size = pool_size
        self.active_operations: set[asyncio.Task] = set()
        self.completed_operations: list[Any] = []
        self.failed_operations: list[Exception] = []
        self._semaphore = asyncio.Semaphore(pool_size)

    async def execute_operation(self, coro):
        """Execute an async operation within the pool constraints."""
        async with self._semaphore:
            task = asyncio.create_task(coro)
            self.active_operations.add(task)

            try:
                result = await task
                self.completed_operations.append(result)
                return result
            except Exception as e:
                self.failed_operations.append(e)
                raise
            finally:
                self.active_operations.discard(task)

    async def execute_batch(self, operations: list):
        """Execute a batch of operations concurrently."""
        tasks = [self.execute_operation(op) for op in operations]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def get_stats(self) -> dict[str, Any]:
        """Get execution statistics."""
        return {
            "active_count": len(self.active_operations),
            "completed_count": len(self.completed_operations),
            "failed_count": len(self.failed_operations),
            "pool_size": self.pool_size,
        }


# Pytest Fixtures


@pytest.fixture
def async_test_harness():
    """Provide async test harness for operation tracking."""
    harness = AsyncTestHarness()
    yield harness
    # Cleanup is automatic


@pytest.fixture
def mock_async_resource_factory():
    """Factory for creating mock async resources with different configurations."""

    def create_resource(resource_id: str, **kwargs):
        return MockAsyncResource(resource_id, **kwargs)

    return create_resource


@pytest.fixture
def async_operation_pool():
    """Provide async operation pool for concurrent testing."""
    pool = AsyncOperationPool()
    yield pool
    # Cancel any remaining operations
    for task in pool.active_operations:
        if not task.done():
            task.cancel()


@pytest.fixture
async def timeout_scenarios():
    """Provide various timeout test scenarios."""
    return {"fast": 0.1, "medium": 0.5, "slow": 2.0, "very_slow": 5.0}


@pytest.fixture
async def concurrency_scenarios():
    """Provide concurrency test scenarios."""
    return {
        "low_contention": {"agents": 5, "operations_per_agent": 10},
        "medium_contention": {"agents": 10, "operations_per_agent": 20},
        "high_contention": {"agents": 20, "operations_per_agent": 30},
        "stress_test": {"agents": 50, "operations_per_agent": 100},
    }


@pytest.fixture
def resource_lifecycle_scenarios():
    """Provide resource lifecycle test scenarios."""
    return {
        "normal_operation": {
            "setup_delay": 0.01,
            "cleanup_delay": 0.01,
            "fail_setup": False,
            "fail_cleanup": False,
        },
        "slow_setup": {
            "setup_delay": 0.1,
            "cleanup_delay": 0.01,
            "fail_setup": False,
            "fail_cleanup": False,
        },
        "slow_cleanup": {
            "setup_delay": 0.01,
            "cleanup_delay": 0.1,
            "fail_setup": False,
            "fail_cleanup": False,
        },
        "setup_failure": {
            "setup_delay": 0.01,
            "cleanup_delay": 0.01,
            "fail_setup": True,
            "fail_cleanup": False,
        },
        "cleanup_failure": {
            "setup_delay": 0.01,
            "cleanup_delay": 0.01,
            "fail_setup": False,
            "fail_cleanup": True,
        },
    }


@pytest.fixture
def performance_benchmarks():
    """Provide performance benchmark thresholds."""
    return {
        "max_operation_duration": 1.0,  # seconds
        "max_concurrent_operations": 100,
        "max_memory_increase_mb": 20.0,
        "min_operations_per_second": 50,
        "max_error_rate": 0.05,  # 5%
    }


@pytest.fixture
async def orchestrator_with_mocks():
    """Provide orchestrator with comprehensive mocking for async testing."""

    # Create mock orchestrator
    mock_orchestrator = MagicMock()
    mock_orchestrator.session = MagicMock()
    mock_orchestrator.session.branches = MagicMock()
    mock_orchestrator.session.default_branch = MagicMock()

    # Mock async methods
    mock_orchestrator.create_cc_branch = AsyncMock()
    mock_orchestrator.session._lookup_branch_by_name = MagicMock(return_value=None)
    mock_orchestrator.session.get_branch = MagicMock(return_value=None)

    return mock_orchestrator


# Utility functions for async testing


async def create_async_operation_batch(
    operation_count: int, operation_duration: float = 0.01, failure_rate: float = 0.0
):
    """Create a batch of async operations for testing."""
    import random

    async def test_operation(op_id: int):
        if random.random() < failure_rate:
            raise ValueError(f"Operation {op_id} failed")

        await asyncio.sleep(operation_duration)
        return f"result_{op_id}"

    return [test_operation(i) for i in range(operation_count)]


async def simulate_concurrent_resource_access(
    resource_count: int, accessor_count: int, access_duration: float = 0.1
):
    """Simulate concurrent access to shared resources."""
    resources = {f"resource_{i}": asyncio.Lock() for i in range(resource_count)}
    results = []

    async def access_resource(accessor_id: int):
        # Randomly select resources to access
        import random

        selected_resources = random.sample(
            list(resources.items()), min(3, resource_count)
        )

        # Sort by name for consistent ordering (deadlock prevention)
        selected_resources.sort(key=lambda x: x[0])

        acquired_locks = []
        try:
            for resource_name, lock in selected_resources:
                await lock.acquire()
                acquired_locks.append(lock)

            # Simulate work with resources
            await asyncio.sleep(access_duration)
            return f"accessor_{accessor_id}_success"

        finally:
            # Release in reverse order
            for lock in reversed(acquired_locks):
                lock.release()

    # Create concurrent accessors
    tasks = [access_resource(i) for i in range(accessor_count)]
    return await asyncio.gather(*tasks, return_exceptions=True)


def analyze_async_performance(timing_data: dict[str, list[float]]) -> dict[str, Any]:
    """Analyze async operation performance metrics."""
    analysis = {}

    for operation, durations in timing_data.items():
        if not durations:
            continue

        analysis[operation] = {
            "count": len(durations),
            "mean": sum(durations) / len(durations),
            "min": min(durations),
            "max": max(durations),
            "p95": sorted(durations)[int(len(durations) * 0.95)] if durations else 0,
            "total": sum(durations),
            "ops_per_second": (
                len(durations) / sum(durations) if sum(durations) > 0 else 0
            ),
        }

    return analysis
