"""
Comprehensive async operation test patterns for core reliability, timeouts, and cancellation.

This module consolidates essential async testing patterns for the khive system,
focusing on practical failures that could occur in production environments.
"""

import asyncio
import time

import pytest


class TestAsyncReliabilityPatterns:
    """Core async reliability patterns for production scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_operation_isolation(self):
        """Test that concurrent operations remain isolated from each other's failures."""

        # Track operation states
        operation_states = {}

        async def isolated_operation(
            op_id: str, should_fail: bool = False, duration: float = 0.1
        ):
            """Simulate an isolated async operation."""
            operation_states[op_id] = {"status": "running", "start_time": time.time()}

            try:
                await asyncio.sleep(duration)
                if should_fail:
                    raise ValueError(f"Operation {op_id} failed intentionally")

                operation_states[op_id]["status"] = "completed"
                return f"{op_id}_success"

            except Exception as e:
                operation_states[op_id]["status"] = "failed"
                operation_states[op_id]["error"] = str(e)
                raise

        # Run mixed success/failure operations concurrently
        operations = [
            isolated_operation("op1", should_fail=False, duration=0.1),
            isolated_operation("op2", should_fail=True, duration=0.05),
            isolated_operation("op3", should_fail=False, duration=0.15),
            isolated_operation("op4", should_fail=True, duration=0.08),
            isolated_operation("op5", should_fail=False, duration=0.12),
        ]

        # Use return_exceptions to prevent failure propagation
        results = await asyncio.gather(*operations, return_exceptions=True)

        # Verify isolation: successful operations completed despite failures
        successful_results = [
            r for r in results if isinstance(r, str) and "_success" in r
        ]
        failed_results = [r for r in results if isinstance(r, Exception)]

        assert len(successful_results) == 3  # op1, op3, op5 succeeded
        assert len(failed_results) == 2  # op2, op4 failed

        # Verify successful operations completed fully
        for op_id in ["op1", "op3", "op5"]:
            assert operation_states[op_id]["status"] == "completed"

        # Verify failed operations recorded failures
        for op_id in ["op2", "op4"]:
            assert operation_states[op_id]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_timeout_cascade_prevention(self):
        """Test preventing timeout cascades in dependent operations."""

        timeout_events = []

        async def timeout_prone_operation(
            name: str, timeout: float, actual_duration: float
        ):
            """Operation that may timeout."""
            try:
                timeout_events.append(f"{name}_started")
                await asyncio.wait_for(asyncio.sleep(actual_duration), timeout=timeout)
                timeout_events.append(f"{name}_completed")
                return f"{name}_result"
            except asyncio.TimeoutError:
                timeout_events.append(f"{name}_timeout")
                raise

        # Chain of operations where first may timeout but others should continue
        async def resilient_workflow():
            """Workflow that handles timeouts gracefully."""
            results = {}

            # Phase 1: May timeout, but don't let it block everything
            try:
                results["phase1"] = await timeout_prone_operation("phase1", 0.1, 0.2)
            except asyncio.TimeoutError:
                results["phase1"] = "phase1_timeout_fallback"

            # Phase 2: Independent operations that should still run
            phase2_ops = [
                timeout_prone_operation("op2a", 0.2, 0.05),
                timeout_prone_operation("op2b", 0.2, 0.08),
                timeout_prone_operation("op2c", 0.2, 0.06),
            ]

            try:
                phase2_results = await asyncio.gather(
                    *phase2_ops, return_exceptions=True
                )
                results["phase2"] = [
                    r if isinstance(r, str) else "fallback" for r in phase2_results
                ]
            except Exception:
                results["phase2"] = ["fallback", "fallback", "fallback"]

            # Phase 3: Final operation that should always attempt
            try:
                results["phase3"] = await timeout_prone_operation("phase3", 0.15, 0.1)
            except asyncio.TimeoutError:
                results["phase3"] = "phase3_timeout_fallback"

            return results

        # Execute workflow
        start_time = time.time()
        results = await resilient_workflow()
        end_time = time.time()

        # Verify timeout didn't cascade
        assert results["phase1"] == "phase1_timeout_fallback"  # Timed out as expected
        assert len(results["phase2"]) == 3  # All phase 2 ops attempted
        assert results["phase3"].endswith("_result")  # Phase 3 completed successfully

        # Verify reasonable total execution time (no excessive blocking)
        assert end_time - start_time < 0.5  # Should complete quickly despite timeout

        # Verify timeout events
        assert "phase1_timeout" in timeout_events
        assert "phase3_completed" in timeout_events

    @pytest.mark.asyncio
    async def test_graceful_cancellation_with_cleanup(self):
        """Test graceful cancellation with proper resource cleanup."""

        cleanup_log = []
        resource_states = {}

        class AsyncResource:
            """Mock async resource that tracks acquisition and cleanup."""

            def __init__(self, name: str):
                self.name = name
                self.acquired = False
                self.cleaned = False

            async def acquire(self):
                """Acquire the resource."""
                await asyncio.sleep(0.05)  # Simulate acquisition time
                self.acquired = True
                resource_states[self.name] = self
                cleanup_log.append(f"{self.name}_acquired")

            async def cleanup(self):
                """Clean up the resource."""
                if self.acquired and not self.cleaned:
                    await asyncio.sleep(0.02)  # Simulate cleanup time
                    self.cleaned = True
                    cleanup_log.append(f"{self.name}_cleaned")

        async def resource_using_operation(
            resource_name: str, work_duration: float = 1.0
        ):
            """Operation that uses resources and handles cancellation."""
            resource = AsyncResource(resource_name)

            try:
                # Acquire resource
                await resource.acquire()

                # Simulate long-running work that might be cancelled
                await asyncio.sleep(work_duration)

                return f"{resource_name}_completed"

            except asyncio.CancelledError:
                cleanup_log.append(f"{resource_name}_cancelled")
                raise
            finally:
                # Always attempt cleanup
                if resource.acquired:
                    await resource.cleanup()

        # Start multiple resource-using operations
        operations = [
            asyncio.create_task(resource_using_operation(f"resource_{i}", 2.0))
            for i in range(3)
        ]

        # Let operations start and acquire resources
        await asyncio.sleep(0.2)

        # Cancel all operations
        for task in operations:
            task.cancel()

        # Wait for cancellation and cleanup
        results = await asyncio.gather(*operations, return_exceptions=True)

        # Verify all operations were cancelled
        assert all(isinstance(r, asyncio.CancelledError) for r in results)

        # Verify resources were properly cleaned up
        for i in range(3):
            resource_name = f"resource_{i}"
            assert f"{resource_name}_acquired" in cleanup_log
            assert f"{resource_name}_cancelled" in cleanup_log
            assert f"{resource_name}_cleaned" in cleanup_log

            # Verify resource state
            resource = resource_states[resource_name]
            assert resource.acquired is True
            assert resource.cleaned is True

    @pytest.mark.asyncio
    async def test_backpressure_handling_patterns(self):
        """Test backpressure handling in async operations."""

        semaphore = asyncio.Semaphore(2)  # Limit to 2 concurrent operations
        execution_log = []

        async def rate_limited_operation(op_id: str, duration: float = 0.1):
            """Operation that respects backpressure limits."""

            async with semaphore:
                execution_log.append(f"{op_id}_started")
                await asyncio.sleep(duration)
                execution_log.append(f"{op_id}_completed")
                return f"{op_id}_result"

        # Start many operations that should be throttled
        operations = [rate_limited_operation(f"op_{i}", 0.1) for i in range(8)]

        start_time = time.time()
        results = await asyncio.gather(*operations)
        end_time = time.time()

        # Verify all operations completed
        assert len(results) == 8
        assert all(r.endswith("_result") for r in results)

        # Verify backpressure was applied - should take longer than pure parallel
        expected_min_time = (8 / 2) * 0.1  # 8 ops / 2 concurrent * 0.1s = 0.4s
        assert end_time - start_time >= expected_min_time * 0.8  # Allow some variance

        # Verify execution was properly throttled
        start_events = [log for log in execution_log if log.endswith("_started")]
        completed_events = [log for log in execution_log if log.endswith("_completed")]

        assert len(start_events) == 8
        assert len(completed_events) == 8


class TestTimeoutScenarios:
    """Timeout handling test scenarios for different operation types."""

    @pytest.fixture
    def timeout_configs(self):
        """Provide various timeout configurations."""
        return {"fast": 0.1, "medium": 0.5, "slow": 2.0, "very_slow": 5.0}

    @pytest.mark.asyncio
    async def test_operation_timeout_with_fallback(self, timeout_configs):
        """Test operations with timeout and fallback mechanisms."""

        fallback_usage = []

        async def operation_with_fallback(name: str, work_time: float, timeout: float):
            """Operation that uses fallback on timeout."""

            async def primary_operation():
                await asyncio.sleep(work_time)
                return f"{name}_primary_result"

            async def fallback_operation():
                fallback_usage.append(name)
                await asyncio.sleep(0.01)  # Fast fallback
                return f"{name}_fallback_result"

            try:
                return await asyncio.wait_for(primary_operation(), timeout=timeout)
            except asyncio.TimeoutError:
                return await fallback_operation()

        # Test various timeout scenarios
        operations = [
            operation_with_fallback(
                "fast_op", 0.05, timeout_configs["fast"]
            ),  # Should succeed
            operation_with_fallback(
                "slow_op", 1.0, timeout_configs["fast"]
            ),  # Should timeout
            operation_with_fallback(
                "medium_op", 0.3, timeout_configs["medium"]
            ),  # Should succeed
            operation_with_fallback(
                "very_slow_op", 3.0, timeout_configs["medium"]
            ),  # Should timeout
        ]

        results = await asyncio.gather(*operations)

        # Verify results
        assert results[0] == "fast_op_primary_result"  # No timeout
        assert results[1] == "slow_op_fallback_result"  # Used fallback
        assert results[2] == "medium_op_primary_result"  # No timeout
        assert results[3] == "very_slow_op_fallback_result"  # Used fallback

        # Verify fallbacks were used appropriately
        assert "slow_op" in fallback_usage
        assert "very_slow_op" in fallback_usage
        assert "fast_op" not in fallback_usage
        assert "medium_op" not in fallback_usage

    @pytest.mark.asyncio
    async def test_timeout_inheritance_in_nested_calls(self):
        """Test timeout behavior in nested async calls."""

        timeout_events = []

        async def nested_operation(
            name: str, levels: int, delay_per_level: float = 0.1
        ):
            """Recursively nested operation for testing timeout inheritance."""

            timeout_events.append(f"{name}_level_{levels}_start")

            # Add delay at each level to ensure timeout occurs
            await asyncio.sleep(delay_per_level)

            if levels <= 0:
                timeout_events.append(f"{name}_level_{levels}_complete")
                return f"{name}_base_result"

            # Recursive call
            try:
                result = await nested_operation(name, levels - 1, delay_per_level)
                timeout_events.append(f"{name}_level_{levels}_complete")
                return f"{name}_level_{levels}_" + result
            except asyncio.CancelledError:
                timeout_events.append(f"{name}_level_{levels}_cancelled")
                raise

        # Test with timeout that should interrupt nested execution
        # 10 levels * 0.1s = 1.0s total, but timeout after 0.3s
        nested_task = asyncio.create_task(nested_operation("deep", 10, 0.1))

        try:
            # This should timeout before completing all 10 levels (would take 1.0s total)
            result = await asyncio.wait_for(nested_task, timeout=0.3)
            pytest.fail("Should have timed out")
        except asyncio.TimeoutError:
            # Expected timeout
            pass

        # Verify nested levels were interrupted
        start_events = [e for e in timeout_events if "start" in e]
        complete_events = [e for e in timeout_events if "complete" in e]

        # Should have started several levels but not completed all
        assert len(start_events) > 0
        assert len(complete_events) < len(start_events)  # Interrupted execution

    @pytest.mark.asyncio
    async def test_timeout_with_partial_results(self):
        """Test collecting partial results when operations timeout."""

        async def batch_operation_with_timeout(
            items: list[str], timeout_per_item: float
        ):
            """Process items with individual timeouts, collecting partial results."""

            async def process_item(item: str, processing_time: float):
                await asyncio.sleep(processing_time)
                return f"processed_{item}"

            # Processing times vary - some will timeout, others won't
            processing_times = {
                "item1": 0.05,  # Fast
                "item2": 0.5,  # Slow - will timeout
                "item3": 0.08,  # Fast
                "item4": 1.0,  # Very slow - will timeout
                "item5": 0.06,  # Fast
            }

            # Process with individual timeouts
            tasks = []
            for item in items:
                task = asyncio.create_task(
                    process_item(item, processing_times.get(item, 0.1))
                )
                tasks.append((item, task))

            results = {}
            for item, task in tasks:
                try:
                    result = await asyncio.wait_for(task, timeout=timeout_per_item)
                    results[item] = result
                except asyncio.TimeoutError:
                    results[item] = f"timeout_{item}"

            return results

        # Process items with short timeout
        items = ["item1", "item2", "item3", "item4", "item5"]
        results = await batch_operation_with_timeout(items, timeout_per_item=0.2)

        # Verify partial results
        assert results["item1"] == "processed_item1"  # Fast, completed
        assert results["item2"] == "timeout_item2"  # Slow, timed out
        assert results["item3"] == "processed_item3"  # Fast, completed
        assert results["item4"] == "timeout_item4"  # Very slow, timed out
        assert results["item5"] == "processed_item5"  # Fast, completed

        # Verify we got mix of successes and timeouts
        successful = [v for v in results.values() if v.startswith("processed_")]
        timeouts = [v for v in results.values() if v.startswith("timeout_")]

        assert len(successful) == 3
        assert len(timeouts) == 2


class TestCancellationPatterns:
    """Cancellation behavior patterns for different scenarios."""

    @pytest.mark.asyncio
    async def test_structured_cancellation_propagation(self):
        """Test proper cancellation propagation through structured async code."""

        cancellation_order = []

        async def cancellable_subtask(name: str, duration: float = 0.5):
            """Subtask that handles cancellation gracefully."""
            try:
                await asyncio.sleep(duration)
                return f"{name}_completed"
            except asyncio.CancelledError:
                cancellation_order.append(name)
                raise

        async def parent_task():
            """Parent task with multiple subtasks."""
            try:
                # Start subtasks
                subtask1 = asyncio.create_task(cancellable_subtask("subtask1", 1.0))
                subtask2 = asyncio.create_task(cancellable_subtask("subtask2", 1.5))
                subtask3 = asyncio.create_task(cancellable_subtask("subtask3", 2.0))

                # Wait for all subtasks
                results = await asyncio.gather(subtask1, subtask2, subtask3)
                return results

            except asyncio.CancelledError:
                cancellation_order.append("parent_task")
                # Cancel any running subtasks
                for task in [subtask1, subtask2, subtask3]:
                    if not task.done():
                        task.cancel()
                raise

        # Start parent task and cancel it
        parent = asyncio.create_task(parent_task())
        await asyncio.sleep(0.1)  # Let subtasks start
        parent.cancel()

        with pytest.raises(asyncio.CancelledError):
            await parent

        # Verify cancellation propagated correctly
        assert "parent_task" in cancellation_order
        # Subtasks should also be cancelled (order may vary)
        subtask_cancellations = [
            name for name in cancellation_order if "subtask" in name
        ]
        assert len(subtask_cancellations) >= 2  # At least 2 subtasks cancelled

    @pytest.mark.asyncio
    async def test_cancellation_with_async_context_managers(self):
        """Test cancellation behavior with async context managers."""

        context_events = []

        class TrackingAsyncContextManager:
            """Async context manager that tracks entry/exit."""

            def __init__(self, name: str):
                self.name = name

            async def __aenter__(self):
                context_events.append(f"{self.name}_enter")
                await asyncio.sleep(0.01)  # Simulate setup
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                # Only record exit once per context manager
                exit_event = f"{self.name}_exit"
                if exit_event not in context_events:
                    context_events.append(exit_event)
                    if isinstance(exc_val, asyncio.CancelledError):
                        context_events.append(f"{self.name}_cancelled_exit")
                await asyncio.sleep(0.01)  # Simulate cleanup
                return False  # Don't suppress exceptions

        async def context_using_operation():
            """Operation that uses multiple async context managers."""

            async with TrackingAsyncContextManager("ctx1"):
                async with TrackingAsyncContextManager("ctx2"):
                    async with TrackingAsyncContextManager("ctx3"):
                        # Long operation that will be cancelled
                        await asyncio.sleep(5.0)
                        return "operation_completed"

        # Start operation and cancel it
        task = asyncio.create_task(context_using_operation())
        await asyncio.sleep(0.1)  # Let context managers initialize
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # Verify all context managers were entered
        enter_events = [e for e in context_events if e.endswith("_enter")]
        assert len(enter_events) == 3

        # Verify all context managers were exited (in reverse order)
        exit_events = [
            e for e in context_events if e.endswith("_exit") and "cancelled" not in e
        ]
        assert len(exit_events) == 3

        # Verify cancellation was properly detected
        cancelled_exit_events = [e for e in context_events if "cancelled_exit" in e]
        assert len(cancelled_exit_events) == 3  # All should detect cancellation

    @pytest.mark.asyncio
    async def test_selective_cancellation_with_shielding(self):
        """Test selective cancellation using asyncio.shield."""

        critical_operations = []
        regular_operations = []

        async def critical_operation(name: str):
            """Critical operation that should complete even if parent is cancelled."""
            try:
                await asyncio.sleep(0.2)
                critical_operations.append(f"{name}_completed")
                return f"{name}_critical_result"
            except asyncio.CancelledError:
                critical_operations.append(f"{name}_cancelled")
                raise

        async def regular_operation(name: str):
            """Regular operation that can be cancelled."""
            try:
                await asyncio.sleep(0.5)
                regular_operations.append(f"{name}_completed")
                return f"{name}_regular_result"
            except asyncio.CancelledError:
                regular_operations.append(f"{name}_cancelled")
                raise

        async def mixed_workflow():
            """Workflow with both critical and regular operations."""

            # Shield critical operations from cancellation
            critical_task = asyncio.shield(
                asyncio.create_task(critical_operation("critical1"))
            )

            # Regular operations are not shielded
            regular_task1 = asyncio.create_task(regular_operation("regular1"))
            regular_task2 = asyncio.create_task(regular_operation("regular2"))

            # Gather all results
            try:
                results = await asyncio.gather(
                    critical_task, regular_task1, regular_task2, return_exceptions=True
                )
                return results
            except asyncio.CancelledError:
                # Even if workflow is cancelled, critical operation should complete
                try:
                    # Wait for critical operation to finish
                    critical_result = await critical_task
                    return [critical_result, "cancelled", "cancelled"]
                except Exception:
                    return ["error", "cancelled", "cancelled"]

        # Start workflow and cancel it partway through
        workflow_task = asyncio.create_task(mixed_workflow())
        await asyncio.sleep(0.1)  # Let operations start
        workflow_task.cancel()

        # Wait for cancellation handling
        try:
            results = await workflow_task
        except asyncio.CancelledError:
            # Wait a bit longer for shielded operation to complete
            await asyncio.sleep(0.3)

        # Verify critical operation completed despite cancellation
        assert "critical1_completed" in critical_operations

        # Verify regular operations were cancelled
        assert "regular1_cancelled" in regular_operations
        assert "regular2_cancelled" in regular_operations

        # Verify regular operations did not complete
        assert "regular1_completed" not in regular_operations
        assert "regular2_completed" not in regular_operations


class TestAsyncResourceManagement:
    """Async resource management and cleanup patterns."""

    @pytest.mark.asyncio
    async def test_resource_pool_with_async_lifecycle(self):
        """Test async resource pool with proper lifecycle management."""

        class AsyncResourcePool:
            """Mock async resource pool for testing."""

            def __init__(self, max_resources: int = 3):
                self.max_resources = max_resources
                self.available_resources = []
                self.in_use_resources = set()
                self.resource_counter = 0
                self.lifecycle_events = []

            async def _create_resource(self):
                """Create a new resource."""
                await asyncio.sleep(0.05)  # Simulate creation time
                resource_id = f"resource_{self.resource_counter}"
                self.resource_counter += 1
                self.lifecycle_events.append(f"{resource_id}_created")
                return resource_id

            async def acquire(self):
                """Acquire a resource from the pool."""
                # Check if we have available resources first
                if self.available_resources:
                    resource_id = self.available_resources.pop()
                    self.lifecycle_events.append(f"{resource_id}_reused")
                # Create new resource if under limit
                elif len(self.in_use_resources) < self.max_resources:
                    resource_id = await self._create_resource()
                else:
                    # Pool is at capacity, wait for a resource to be released
                    max_wait_attempts = 5
                    for attempt in range(max_wait_attempts):
                        await asyncio.sleep(0.05)  # Short wait
                        if self.available_resources:
                            resource_id = self.available_resources.pop()
                            self.lifecycle_events.append(f"{resource_id}_waited")
                            break
                    else:
                        raise RuntimeError("No resources available after waiting")

                self.in_use_resources.add(resource_id)
                self.lifecycle_events.append(f"{resource_id}_acquired")
                return resource_id

            async def release(self, resource_id: str):
                """Release a resource back to the pool."""
                if resource_id in self.in_use_resources:
                    self.in_use_resources.remove(resource_id)
                    self.available_resources.append(resource_id)
                    self.lifecycle_events.append(f"{resource_id}_released")
                    await asyncio.sleep(0.02)  # Simulate cleanup

            async def close(self):
                """Close all resources in the pool."""
                for resource_id in (
                    list(self.in_use_resources) + self.available_resources
                ):
                    self.lifecycle_events.append(f"{resource_id}_closed")
                self.in_use_resources.clear()
                self.available_resources.clear()

        pool = AsyncResourcePool(max_resources=2)

        async def resource_using_task(task_id: str, usage_duration: float = 0.15):
            """Task that uses a resource from the pool."""
            resource_id = await pool.acquire()

            try:
                await asyncio.sleep(usage_duration)
                return f"task_{task_id}_used_{resource_id}"
            finally:
                await pool.release(resource_id)

        # Run multiple tasks sequentially to ensure resource reuse
        # First batch: 2 concurrent tasks (should create 2 resources)
        batch1_tasks = [
            resource_using_task("0", 0.1),
            resource_using_task("1", 0.1),
        ]
        await asyncio.gather(*batch1_tasks)

        # Second batch: 3 more tasks (should reuse existing resources)
        batch2_tasks = [
            resource_using_task("2", 0.1),
            resource_using_task("3", 0.1),
            resource_using_task("4", 0.1),
        ]
        results_batch2 = await asyncio.gather(*batch2_tasks)

        # Verify all tasks completed successfully
        assert len(results_batch2) == 3
        assert all(
            r.startswith("task_") and "_used_resource_" in r for r in results_batch2
        )

        # Verify resource reuse occurred
        lifecycle_events = pool.lifecycle_events
        created_events = [e for e in lifecycle_events if "_created" in e]
        reused_events = [e for e in lifecycle_events if "_reused" in e]

        assert len(created_events) == 2  # Exactly 2 resources created
        assert len(reused_events) >= 2  # At least some resource reuse occurred

        # Clean up
        await pool.close()

        closed_events = [e for e in lifecycle_events if "_closed" in e]
        assert len(closed_events) >= len(created_events)  # All created resources closed

    @pytest.mark.asyncio
    async def test_async_lock_contention_patterns(self):
        """Test async lock contention and fairness patterns."""

        lock = asyncio.Lock()
        execution_order = []
        contention_times = {}

        async def contending_operation(op_id: str, work_duration: float = 0.1):
            """Operation that contends for a shared lock."""

            wait_start = time.time()

            async with lock:
                wait_end = time.time()
                contention_times[op_id] = wait_end - wait_start

                execution_order.append(f"{op_id}_start")
                await asyncio.sleep(work_duration)
                execution_order.append(f"{op_id}_end")

                return f"{op_id}_result"

        # Start operations that will contend for the lock
        operations = [
            asyncio.create_task(contending_operation(f"op_{i}", 0.05)) for i in range(5)
        ]

        start_time = time.time()
        results = await asyncio.gather(*operations)
        end_time = time.time()

        # Verify all operations completed
        assert len(results) == 5
        assert all(r.endswith("_result") for r in results)

        # Verify operations were properly serialized
        start_events = [e for e in execution_order if e.endswith("_start")]
        end_events = [e for e in execution_order if e.endswith("_end")]

        assert len(start_events) == 5
        assert len(end_events) == 5

        # Verify no overlap in critical sections
        for i in range(len(start_events) - 1):
            current_op = start_events[i].replace("_start", "")
            current_end_idx = execution_order.index(f"{current_op}_end")
            next_start_idx = execution_order.index(start_events[i + 1])

            # Current operation should end before next one starts (or at same time)
            assert current_end_idx <= next_start_idx

        # Verify total time shows serialization (should be roughly sequential)
        total_time = end_time - start_time
        expected_min_time = 5 * 0.05  # 5 operations * 0.05s each
        assert total_time >= expected_min_time * 0.8  # Allow some variance

    @pytest.mark.asyncio
    async def test_async_memory_management_patterns(self):
        """Test async patterns for memory management and cleanup."""

        memory_tracker = {
            "allocated": 0,
            "deallocated": 0,
            "peak_usage": 0,
            "current_usage": 0,
        }

        class AsyncMemoryResource:
            """Mock resource that tracks memory usage."""

            def __init__(self, name: str, size: int):
                self.name = name
                self.size = size
                self.allocated = False

            async def allocate(self):
                """Allocate the resource."""
                if not self.allocated:
                    await asyncio.sleep(0.01)  # Simulate allocation time
                    memory_tracker["allocated"] += self.size
                    memory_tracker["current_usage"] += self.size
                    memory_tracker["peak_usage"] = max(
                        memory_tracker["peak_usage"], memory_tracker["current_usage"]
                    )
                    self.allocated = True

            async def deallocate(self):
                """Deallocate the resource."""
                if self.allocated:
                    await asyncio.sleep(0.01)  # Simulate deallocation time
                    memory_tracker["deallocated"] += self.size
                    memory_tracker["current_usage"] -= self.size
                    self.allocated = False

        async def memory_intensive_operation(op_id: str, resource_sizes: list[int]):
            """Operation that allocates and manages multiple memory resources."""

            resources = []

            try:
                # Allocate resources
                for i, size in enumerate(resource_sizes):
                    resource = AsyncMemoryResource(f"{op_id}_res_{i}", size)
                    await resource.allocate()
                    resources.append(resource)

                # Simulate work with resources
                await asyncio.sleep(0.1)

                return f"{op_id}_completed"

            finally:
                # Always clean up resources
                for resource in resources:
                    if resource.allocated:
                        await resource.deallocate()

        # Run operations with varying memory requirements
        operations = [
            memory_intensive_operation("op1", [100, 200, 150]),  # 450 total
            memory_intensive_operation("op2", [300, 250]),  # 550 total
            memory_intensive_operation("op3", [500]),  # 500 total
            memory_intensive_operation("op4", [100, 100, 100, 100]),  # 400 total
        ]

        # Execute operations concurrently
        results = await asyncio.gather(*operations, return_exceptions=True)

        # Verify all operations completed successfully
        assert len(results) == 4
        assert all(isinstance(r, str) and r.endswith("_completed") for r in results)

        # Verify memory was properly managed
        total_allocated = memory_tracker["allocated"]
        total_deallocated = memory_tracker["deallocated"]
        current_usage = memory_tracker["current_usage"]
        peak_usage = memory_tracker["peak_usage"]

        # All allocated memory should be deallocated
        assert total_allocated == total_deallocated
        assert current_usage == 0  # No leaks

        # Peak usage should reflect concurrent operations
        expected_total = 450 + 550 + 500 + 400  # Sum of all resource sizes
        assert total_allocated == expected_total

        # Peak usage should be less than total (due to cleanup)
        assert 0 < peak_usage <= expected_total
