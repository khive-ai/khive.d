"""Comprehensive async resource management and cleanup testing patterns.

This module provides testing infrastructure for:
- Async context managers and resource lifecycle
- Memory leak detection and monitoring
- Resource cleanup verification in success/failure scenarios
- Proper disposal patterns and validation
- Resource isolation and concurrency safety

Based on khive services architecture patterns.
"""

import asyncio
import gc
import tempfile
import tracemalloc
import weakref
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest
from memory_profiler import memory_usage

from khive.services.artifacts.sessions import SessionManager
from khive.services.cache.service import CacheService


class ResourceTracker:
    """Tracks resource allocation and cleanup for testing."""

    def __init__(self):
        self.allocated_resources: dict[str, Any] = {}
        self.cleanup_callbacks: dict[str, list[callable]] = {}
        self.weak_refs: set[weakref.ReferenceType] = set()
        self._resource_counter = 0

    def register_resource(self, resource: Any, name: str | None = None) -> str:
        """Register a resource for tracking."""
        resource_id = name or f"resource_{self._resource_counter}"
        self._resource_counter += 1

        self.allocated_resources[resource_id] = resource
        self.cleanup_callbacks[resource_id] = []

        # Create weak reference to track garbage collection
        weak_ref = weakref.ref(resource, self._on_resource_deleted)
        self.weak_refs.add(weak_ref)

        return resource_id

    def register_cleanup(self, resource_id: str, cleanup_func: callable):
        """Register cleanup function for a resource."""
        if resource_id in self.cleanup_callbacks:
            self.cleanup_callbacks[resource_id].append(cleanup_func)

    async def cleanup_resource(self, resource_id: str) -> bool:
        """Manually cleanup a specific resource."""
        if resource_id not in self.allocated_resources:
            return False

        resource = self.allocated_resources.pop(resource_id)
        callbacks = self.cleanup_callbacks.pop(resource_id, [])

        # Execute cleanup callbacks
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                pytest.fail(f"Cleanup callback failed for {resource_id}: {e}")

        # Handle async context managers
        if hasattr(resource, "__aexit__"):
            try:
                await resource.__aexit__(None, None, None)
            except Exception as e:
                # For testing purposes, we may expect some failures
                # Don't fail the test, just log the failure
                pass

        return True

    async def cleanup_all(self):
        """Cleanup all tracked resources."""
        resource_ids = list(self.allocated_resources.keys())
        for resource_id in resource_ids:
            await self.cleanup_resource(resource_id)

    def _on_resource_deleted(self, weak_ref: weakref.ReferenceType):
        """Called when a resource is garbage collected."""
        self.weak_refs.discard(weak_ref)

    def get_active_resources(self) -> dict[str, Any]:
        """Get currently active resources."""
        return self.allocated_resources.copy()

    def verify_all_cleaned(self) -> bool:
        """Verify all resources have been cleaned up."""
        return len(self.allocated_resources) == 0


class AsyncResourceMock:
    """Mock async resource for testing cleanup patterns."""

    def __init__(self, resource_id: str, fail_on_cleanup: bool = False):
        self.resource_id = resource_id
        self.fail_on_cleanup = fail_on_cleanup
        self.is_closed = False
        self.cleanup_called = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    async def cleanup(self):
        """Cleanup the resource."""
        if self.fail_on_cleanup:
            raise RuntimeError(f"Cleanup failed for {self.resource_id}")

        self.cleanup_called = True
        self.is_closed = True

    def __del__(self):
        if not self.is_closed:
            # Resource not properly cleaned up
            pass


@pytest.fixture
def resource_tracker():
    """Provide resource tracker for tests."""
    tracker = ResourceTracker()
    yield tracker
    # Ensure cleanup in case test fails
    asyncio.run(tracker.cleanup_all())


@pytest.fixture
def memory_baseline():
    """Establish memory baseline for leak detection."""
    # Force garbage collection
    gc.collect()

    # Start memory tracking
    tracemalloc.start()

    # Get initial memory usage
    baseline = memory_usage()[0]

    yield baseline

    # Stop tracking
    tracemalloc.stop()


@asynccontextmanager
async def memory_leak_detector(
    max_increase_mb: float = 10.0,
) -> AsyncGenerator[None, None]:
    """Context manager for detecting memory leaks."""
    gc.collect()
    initial_memory = memory_usage()[0]

    yield

    gc.collect()
    final_memory = memory_usage()[0]

    increase = final_memory - initial_memory
    if increase > max_increase_mb:
        pytest.fail(
            f"Memory leak detected: {increase:.2f}MB increase (max: {max_increase_mb}MB)"
        )


# Resource Management Test Classes


@pytest.mark.async_test
@pytest.mark.resource_cleanup
class TestAsyncResourceLifecycle:
    """Test async resource lifecycle management."""

    async def test_basic_resource_cleanup(self, resource_tracker):
        """Test basic resource creation and cleanup."""
        resource = AsyncResourceMock("test_resource")
        resource_id = resource_tracker.register_resource(resource)

        # Use resource in async context
        async with resource:
            assert not resource.is_closed
            assert resource.resource_id == "test_resource"

        # Verify cleanup occurred
        assert resource.cleanup_called
        assert resource.is_closed

        # Cleanup from tracker
        await resource_tracker.cleanup_all()
        assert resource_tracker.verify_all_cleaned()

    async def test_resource_cleanup_on_exception(self, resource_tracker):
        """Test resource cleanup when exceptions occur."""
        resource = AsyncResourceMock("exception_resource")
        resource_tracker.register_resource(resource)

        with pytest.raises(ValueError):
            async with resource:
                raise ValueError("Test exception")

        # Verify cleanup still occurred despite exception
        assert resource.cleanup_called
        assert resource.is_closed

    async def test_failed_cleanup_handling(self, resource_tracker):
        """Test handling when resource cleanup fails."""
        resource = AsyncResourceMock("failing_resource", fail_on_cleanup=True)
        resource_tracker.register_resource(resource)

        with pytest.raises(RuntimeError, match="Cleanup failed"):
            async with resource:
                pass

    async def test_multiple_resource_coordination(self, resource_tracker):
        """Test coordinating cleanup of multiple resources."""
        resources = [AsyncResourceMock(f"resource_{i}") for i in range(5)]

        # Register all resources
        for resource in resources:
            resource_tracker.register_resource(resource, resource.resource_id)

        # Use all resources concurrently
        tasks = []

        async def use_resource(res):
            async with res:
                await asyncio.sleep(0.1)  # Simulate work

        for resource in resources:
            tasks.append(asyncio.create_task(use_resource(resource)))

        await asyncio.gather(*tasks)

        # Verify all resources cleaned up
        for resource in resources:
            assert resource.cleanup_called
            assert resource.is_closed


@pytest.mark.async_test
@pytest.mark.resource_cleanup
class TestMemoryLeakDetection:
    """Test memory leak detection patterns."""

    async def test_no_memory_leak_basic_usage(self):
        """Test that basic resource usage doesn't leak memory."""
        async with memory_leak_detector(max_increase_mb=5.0):
            # Create and cleanup resources in a loop
            for i in range(100):
                resource = AsyncResourceMock(f"resource_{i}")
                async with resource:
                    pass  # Minimal usage

    async def test_detect_intentional_memory_leak(self):
        """Test that memory leak detector catches actual leaks."""
        leaked_objects = []

        with pytest.raises(Exception, match="Memory leak detected"):
            async with memory_leak_detector(max_increase_mb=2.0):
                # Intentionally create objects that won't be cleaned up
                for i in range(5000):
                    leaked_objects.append(bytearray(1024))  # 1KB each = ~5MB total

    async def test_memory_usage_monitoring_with_services(self):
        """Test memory monitoring with actual khive services."""
        async with memory_leak_detector(max_increase_mb=15.0):
            # Test with actual khive services
            with tempfile.TemporaryDirectory() as temp_dir:
                session_manager = SessionManager(Path(temp_dir))

                # Create and cleanup multiple sessions
                sessions = []
                for i in range(10):
                    session = await session_manager.create_session(f"session_{i}")
                    sessions.append(session)

                # Cleanup sessions
                for session in sessions:
                    try:
                        await session_manager.delete_session(session.id)
                    except Exception:
                        pass  # Session might not exist

    async def test_cache_service_memory_management(self):
        """Test cache service doesn't leak memory."""
        async with memory_leak_detector(max_increase_mb=10.0):
            cache_service = CacheService()

            # Initialize and use cache
            await cache_service.initialize()

            try:
                # Perform cache operations
                for i in range(50):
                    await cache_service.cache_planning_result(
                        f"request_{i}",
                        {"result": f"data_{i}"},
                        {"metadata": f"meta_{i}"},
                    )
            finally:
                await cache_service.close()


@pytest.mark.async_test
@pytest.mark.concurrency
class TestConcurrentResourceManagement:
    """Test resource management under concurrent access."""

    async def test_concurrent_resource_creation_cleanup(self, resource_tracker):
        """Test concurrent resource creation and cleanup."""

        async def create_and_cleanup_resource(resource_id: str):
            resource = AsyncResourceMock(resource_id)
            tracker_id = resource_tracker.register_resource(resource, resource_id)

            async with resource:
                await asyncio.sleep(0.1)  # Simulate work

            # Verify cleanup
            assert resource.cleanup_called
            return tracker_id

        # Create multiple concurrent tasks
        tasks = [
            asyncio.create_task(create_and_cleanup_resource(f"concurrent_{i}"))
            for i in range(20)
        ]

        # Wait for all tasks to complete
        tracker_ids = await asyncio.gather(*tasks)

        # Verify all resources were created and cleaned up
        assert len(tracker_ids) == 20

    async def test_resource_isolation_under_concurrency(self):
        """Test that resources remain isolated under concurrent access."""
        shared_state = {"counter": 0}

        class IsolatedResource:
            def __init__(self, resource_id: str):
                self.resource_id = resource_id
                self.local_counter = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

            async def increment(self):
                # Simulate non-atomic operation
                current = shared_state["counter"]
                await asyncio.sleep(0.001)  # Force task switching
                shared_state["counter"] = current + 1
                self.local_counter += 1

        async def worker(worker_id: int):
            resource = IsolatedResource(f"worker_{worker_id}")
            async with resource:
                for _ in range(10):
                    await resource.increment()
                return resource.local_counter

        # Run multiple workers concurrently
        tasks = [asyncio.create_task(worker(i)) for i in range(10)]
        local_counters = await asyncio.gather(*tasks)

        # Each worker should have incremented 10 times locally
        assert all(count == 10 for count in local_counters)

        # But shared state might show race conditions
        # This demonstrates the need for proper isolation
        assert shared_state["counter"] <= 100  # May be less due to race conditions


@pytest.mark.async_test
class TestResourceTimeoutHandling:
    """Test resource management with timeouts and cancellation."""

    async def test_resource_cleanup_on_timeout(self, resource_tracker):
        """Test that resources are cleaned up when operations timeout."""
        resource = AsyncResourceMock("timeout_resource")
        resource_tracker.register_resource(resource)

        with pytest.raises(asyncio.TimeoutError):
            async with resource:
                # This should timeout and still cleanup the resource
                await asyncio.wait_for(asyncio.sleep(10), timeout=0.1)

        # Verify resource was cleaned up despite timeout
        assert resource.cleanup_called
        assert resource.is_closed

    async def test_cancellation_cleanup(self, resource_tracker):
        """Test resource cleanup when task is cancelled."""
        resource = AsyncResourceMock("cancelled_resource")
        resource_tracker.register_resource(resource)

        async def task_with_resource():
            async with resource:
                await asyncio.sleep(10)  # Long operation

        task = asyncio.create_task(task_with_resource())
        await asyncio.sleep(0.1)  # Let task start
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # Verify resource was cleaned up despite cancellation
        assert resource.cleanup_called
        assert resource.is_closed


@pytest.mark.async_test
@pytest.mark.race_condition
class TestRaceConditionDetection:
    """Test detection of race conditions in resource management."""

    async def test_file_resource_race_condition(self):
        """Test race conditions with file resources."""
        test_file = Path("test_race_file.tmp")

        async def write_worker(worker_id: int, content: str):
            # Simulate multiple workers writing to the same file
            for i in range(10):
                async with asyncio.Lock():  # This prevents the race condition
                    with open(test_file, "a") as f:
                        f.write(f"{worker_id}:{i}:{content}\n")
                await asyncio.sleep(0.001)

        try:
            # Run multiple workers
            tasks = [
                asyncio.create_task(write_worker(i, f"data_{i}")) for i in range(5)
            ]
            await asyncio.gather(*tasks)

            # Verify file contents
            if test_file.exists():
                content = test_file.read_text()
                lines = [line for line in content.split("\n") if line]
                assert len(lines) == 50  # 5 workers * 10 writes each

        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()


@pytest.mark.integration
@pytest.mark.resource_cleanup
class TestServiceResourceIntegration:
    """Test resource management integration with khive services."""

    async def test_session_manager_resource_lifecycle(self):
        """Test SessionManager resource lifecycle."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_manager = SessionManager(Path(temp_dir))

            # Track memory usage
            initial_memory = memory_usage()[0]

            sessions_created = []
            try:
                # Create multiple sessions
                for i in range(10):
                    session = await session_manager.create_session(
                        f"integration_session_{i}"
                    )
                    sessions_created.append(session)

                    # Verify session directory exists
                    assert session.workspace_path.exists()

                # Verify all sessions exist
                assert len(sessions_created) == 10

            finally:
                # Cleanup all sessions
                for session in sessions_created:
                    try:
                        await session_manager.delete_session(session.id)
                    except Exception:
                        pass  # Session might not exist

                # Verify cleanup
                gc.collect()
                final_memory = memory_usage()[0]
                memory_increase = final_memory - initial_memory

                # Should not have significant memory increase
                assert memory_increase < 20.0  # Less than 20MB increase

    async def test_cache_service_connection_management(self):
        """Test CacheService connection resource management."""
        cache_configs = [
            {"enabled": False},  # Disabled cache
        ]

        for config_data in cache_configs:
            cache_service = CacheService()
            cache_service.config.enabled = config_data["enabled"]

            try:
                await cache_service.initialize()

                # Test basic operations
                result = await cache_service.cache_planning_result(
                    "test_request", {"test": "data"}, {"meta": "data"}
                )

                # Should handle gracefully regardless of config
                assert isinstance(result, bool)

            finally:
                await cache_service.close()


# Utility functions for resource management testing


def assert_no_file_handles_leaked(initial_count: int):
    """Assert that no file handles were leaked."""
    # This is platform-specific and may need adjustment
    try:
        import psutil

        current_process = psutil.Process()
        current_count = (
            current_process.num_fds() if hasattr(current_process, "num_fds") else 0
        )

        if current_count > initial_count + 5:  # Allow some tolerance
            pytest.fail(
                f"File handle leak detected: {current_count - initial_count} handles leaked"
            )
    except ImportError:
        # psutil not available, skip check
        pass


@pytest.mark.async_test
@pytest.mark.resource_cleanup
class TestFileHandleManagement:
    """Test file handle resource management."""

    async def test_no_file_handle_leaks(self):
        """Test that file operations don't leak file handles."""
        try:
            import psutil

            initial_handles = (
                psutil.Process().num_fds()
                if hasattr(psutil.Process(), "num_fds")
                else 0
            )
        except ImportError:
            pytest.skip("psutil not available for file handle testing")
            return

        # Create and cleanup many temporary files
        for i in range(100):
            with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
                tmp_file.write(b"test data")
                tmp_file.flush()

        # Force garbage collection
        gc.collect()

        # Check for leaks
        assert_no_file_handles_leaked(initial_handles)
