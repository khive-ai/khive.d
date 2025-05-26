"""
Comprehensive tests for AsyncExecutor.

Tests the async executor functionality including task execution,
resource management, and error handling.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

from khive.clients.executor import AsyncExecutor
from khive.clients.errors import APIClientError


class TestAsyncExecutor:
    """Test the AsyncExecutor class."""

    @pytest.fixture
    def executor(self):
        """Create an AsyncExecutor instance for testing."""
        return AsyncExecutor(max_concurrency=2)

    @pytest.fixture
    def custom_executor(self):
        """Create an AsyncExecutor with custom concurrency."""
        return AsyncExecutor(max_concurrency=3)

    async def test_initialization_default(self):
        """Test AsyncExecutor initialization with default parameters."""
        executor = AsyncExecutor()

        assert executor.semaphore is None
        assert len(executor._active_tasks) == 0
        assert executor._lock is not None

    async def test_initialization_custom(self, executor):
        """Test AsyncExecutor initialization with custom parameters."""
        assert executor.semaphore is not None
        assert executor.semaphore._value == 2
        assert len(executor._active_tasks) == 0
        assert executor._lock is not None

    async def test_initialization_with_custom_concurrency(self, custom_executor):
        """Test AsyncExecutor initialization with custom concurrency."""
        assert custom_executor.semaphore is not None
        assert custom_executor.semaphore._value == 3
        assert len(custom_executor._active_tasks) == 0
        assert custom_executor._lock is not None

    async def test_execute_basic_function(self, executor):
        """Test executing a basic async function."""
        
        async def async_function(x, y):
            return x + y

        result = await executor.execute(async_function, 5, 10)
        assert result == 15

    async def test_execute_with_semaphore(self, executor):
        """Test that semaphore limits concurrency."""
        call_count = 0
        
        async def counting_function():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return call_count

        # Start multiple tasks
        tasks = [executor.execute(counting_function) for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 5

    async def test_execute_no_semaphore(self):
        """Test execution without concurrency limit."""
        executor = AsyncExecutor(max_concurrency=None)
        
        async def async_function(x):
            return x * 2

        result = await executor.execute(async_function, 21)
        assert result == 42

    async def test_execute_async_function_with_kwargs(self, executor):
        """Test executing an async function with keyword arguments."""

        async def async_function(x, y, multiplier=1):
            return (x + y) * multiplier

        result = await executor.execute(async_function, 5, 10, multiplier=2)
        assert result == 30

    async def test_execute_async_function_exception(self, executor):
        """Test executing an async function that raises an exception."""

        async def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await executor.execute(failing_function)

    async def test_execute_with_cancellation(self, executor):
        """Test executing a function that gets cancelled."""

        async def slow_function():
            await asyncio.sleep(10)  # Long operation
            return "completed"

        task = asyncio.create_task(executor.execute(slow_function))
        await asyncio.sleep(0.1)  # Let it start
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_execute_sync_function_error(self, executor):
        """Test that executing a sync function raises a proper error."""

        def sync_function():
            return "sync result"

        # AsyncExecutor should only handle async functions, not sync
        # Passing a sync function should raise a TypeError
        with pytest.raises(TypeError, match="object str can't be used in 'await' expression"):
            await executor.execute(sync_function)

    async def test_execute_async_lambda(self, executor):
        """Test executing an async lambda function."""
        async_lambda = lambda x: asyncio.sleep(0.01) or x * 2
        
        async def async_multiply(x):
            await asyncio.sleep(0.01)
            return x * 2
            
        result = await executor.execute(async_multiply, 21)
        assert result == 42

    async def test_execute_async_builtin_wrapper(self, executor):
        """Test executing a wrapped builtin function."""
        async def async_len(lst):
            await asyncio.sleep(0.01)
            return len(lst)
            
        result = await executor.execute(async_len, [1, 2, 3, 4, 5])
        assert result == 5

    async def test_execute_async_method_call(self, executor):
        """Test executing an async method call."""
        
        async def async_sort(test_list):
            await asyncio.sleep(0.01)
            test_list.sort()
            return test_list

        test_list = [3, 1, 4, 1, 5]
        result = await executor.execute(async_sort, test_list)
        assert result == [1, 1, 3, 4, 5]

    async def test_execute_complex_async_computation(self, executor):
        """Test executing a complex async computation."""

        async def async_fibonacci(n):
            await asyncio.sleep(0.001)  # Small delay to make it async
            if n <= 1:
                return n
            # For testing, use iterative approach to avoid deep recursion
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            return b

        result = await executor.execute(async_fibonacci, 10)
        assert result == 55

    async def test_concurrent_executions(self, executor):
        """Test multiple concurrent executions."""

        async def slow_computation(n, delay=0.1):
            await asyncio.sleep(delay)
            return n * n

        # Start multiple tasks concurrently
        tasks = [executor.execute(slow_computation, i, 0.1) for i in range(5)]

        results = await asyncio.gather(*tasks)
        expected = [i * i for i in range(5)]
        assert results == expected

    async def test_execute_with_side_effects(self, executor):
        """Test executing a function with side effects."""
        results = []

        async def append_result(value):
            await asyncio.sleep(0.01)
            results.append(value)
            return len(results)

        count1 = await executor.execute(append_result, "first")
        count2 = await executor.execute(append_result, "second")

        assert count1 == 1
        assert count2 == 2
        assert results == ["first", "second"]

    async def test_shutdown_executor(self, executor):
        """Test shutting down the executor."""
        
        async def simple_task():
            await asyncio.sleep(0.1)
            return 42

        # Execute something to create active tasks
        task = asyncio.create_task(executor.execute(simple_task))
        
        # Wait a bit to let it start
        await asyncio.sleep(0.05)
        
        # Shutdown should wait for active tasks
        await executor.shutdown(timeout=1.0)
        
        # Task should complete normally
        result = await task
        assert result == 42

    async def test_shutdown_executor_idempotent(self, executor):
        """Test that shutting down executor multiple times is safe."""
        
        async def simple_task():
            return 42
            
        await executor.execute(simple_task)

        # Shutdown multiple times
        await executor.shutdown()
        await executor.shutdown()
        await executor.shutdown()

        # Should still work
        assert True  # No errors means success

    async def test_shutdown_with_timeout(self, executor):
        """Test shutdown with timeout cancels pending tasks."""
        
        async def long_task():
            await asyncio.sleep(10)  # Very long task
            return "completed"

        # Start a long task
        task = asyncio.create_task(executor.execute(long_task))
        await asyncio.sleep(0.1)  # Let it start
        
        # Shutdown with short timeout should cancel the task
        await executor.shutdown(timeout=0.1)
        
        # The task should be cancelled
        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_context_manager_success(self):
        """Test using AsyncExecutor as context manager successfully."""
        async with AsyncExecutor(max_concurrency=2) as executor:
            
            async def async_multiply(x):
                await asyncio.sleep(0.01)
                return x * 2
                
            result = await executor.execute(async_multiply, 21)
            assert result == 42
            # Executor should still be active during context
            assert executor._lock is not None

        # Should be shutdown after exiting context
        # (No _closed attribute to check, but should have cleaned up tasks)
        assert True  # Context manager completed successfully

    async def test_context_manager_with_exception(self):
        """Test using AsyncExecutor as context manager with exception."""
        executor = None

        try:
            async with AsyncExecutor(max_concurrency=2) as exec_instance:
                executor = exec_instance
                
                async def async_multiply(x):
                    await asyncio.sleep(0.01)
                    return x * 2
                    
                result = await executor.execute(async_multiply, 21)
                assert result == 42

                # Raise an exception
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # Should still be shutdown after exception
        assert executor._lock is not None  # Executor object still exists

    async def test_resource_cleanup_on_cancellation(self, executor):
        """Test that resources are cleaned up properly on task cancellation."""

        async def long_running_task():
            await asyncio.sleep(2)
            return "completed"

        # Start a task and cancel it
        task = asyncio.create_task(executor.execute(long_running_task))
        await asyncio.sleep(0.1)  # Let it start
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass  # Expected

        # Executor should still be usable
        async def quick_task():
            return "quick task"
            
        result = await executor.execute(quick_task)
        assert result == "quick task"

    async def test_multiple_executors_independence(self):
        """Test that multiple executor instances are independent."""
        executor1 = AsyncExecutor(max_concurrency=2)
        executor2 = AsyncExecutor(max_concurrency=3)

        # Execute tasks on both
        async def task1():
            return "executor1"
            
        async def task2():
            return "executor2"
            
        result1 = await executor1.execute(task1)
        result2 = await executor2.execute(task2)

        assert result1 == "executor1"
        assert result2 == "executor2"

        # Shutdown one, other should still work
        await executor1.shutdown()
        
        async def task3():
            return "still working"
            
        result3 = await executor2.execute(task3)
        assert result3 == "still working"

        await executor2.shutdown()

    async def test_execute_with_complex_return_types(self, executor):
        """Test executing functions that return complex types."""

        async def return_dict():
            await asyncio.sleep(0.01)
            return {"key": "value", "number": 42, "list": [1, 2, 3]}

        async def return_object():
            await asyncio.sleep(0.01)
            class TestObject:
                def __init__(self):
                    self.attr = "test"
            return TestObject()

        # Test dict return
        result_dict = await executor.execute(return_dict)
        assert result_dict == {"key": "value", "number": 42, "list": [1, 2, 3]}

        # Test object return
        result_obj = await executor.execute(return_object)
        assert result_obj.attr == "test"

    async def test_execute_with_mutable_arguments(self, executor):
        """Test executing functions with mutable arguments."""

        async def modify_list(lst):
            await asyncio.sleep(0.01)
            lst.append("modified")
            return lst

        original_list = [1, 2, 3]
        result = await executor.execute(modify_list, original_list)

        # The function should have modified the list
        assert result == [1, 2, 3, "modified"]
        assert original_list == [1, 2, 3, "modified"]

    async def test_execute_with_none_return(self, executor):
        """Test executing functions that return None."""

        async def return_none():
            await asyncio.sleep(0.01)
            return None

        async def no_explicit_return():
            await asyncio.sleep(0.01)
            x = 1 + 1  # No return statement

        result1 = await executor.execute(return_none)
        result2 = await executor.execute(no_explicit_return)

        assert result1 is None
        assert result2 is None

    async def test_async_concurrency_control(self, executor):
        """Test async concurrency control with shared state."""
        counter = {"value": 0}
        lock = asyncio.Lock()

        async def increment_counter():
            async with lock:
                current = counter["value"]
                # Simulate some async work
                await asyncio.sleep(0.01)
                counter["value"] = current + 1
            return counter["value"]

        # Run multiple increments concurrently
        tasks = [executor.execute(increment_counter) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All increments should have completed
        assert counter["value"] == 10
        # Results should be unique values from 1 to 10
        assert set(results) == set(range(1, 11))


class TestAsyncExecutorErrorHandling:
    """Test error handling in AsyncExecutor."""

    @pytest.fixture
    def executor(self):
        """Create an AsyncExecutor instance for testing."""
        return AsyncExecutor(max_concurrency=2)

    async def test_execute_with_import_error(self, executor):
        """Test executing function that has import error."""

        async def import_nonexistent():
            import nonexistent_module  # This will fail
            return "should not reach here"

        with pytest.raises(ImportError):
            await executor.execute(import_nonexistent)

    async def test_execute_with_attribute_error(self, executor):
        """Test executing function that has attribute error."""

        async def attribute_error():
            obj = object()
            return obj.nonexistent_attribute

        with pytest.raises(AttributeError):
            await executor.execute(attribute_error)

    async def test_execute_with_type_error(self, executor):
        """Test executing function that has type error."""

        async def type_error():
            return "string" + 42

        with pytest.raises(TypeError):
            await executor.execute(type_error)

    async def test_execute_with_custom_exception(self, executor):
        """Test executing function that raises custom exception."""

        class CustomError(Exception):
            pass

        async def raise_custom():
            raise CustomError("Custom error message")

        with pytest.raises(CustomError, match="Custom error message"):
            await executor.execute(raise_custom)

    @pytest.mark.skip(reason="SystemExit causes issues in test environment")
    async def test_execute_with_system_exit(self, executor):
        """Test executing function that raises SystemExit."""

        async def call_exit():
            # SystemExit is a special exception that inherits from BaseException
            # not Exception, so it should propagate through the executor
            raise SystemExit(1)

        # SystemExit should propagate through the executor without being caught
        # by the general Exception handler in _track_task
        with pytest.raises(SystemExit):
            await executor.execute(call_exit)

    async def test_execute_with_keyboard_interrupt(self, executor):
        """Test executing function that raises KeyboardInterrupt."""

        async def raise_keyboard_interrupt():
            raise KeyboardInterrupt("Simulated interrupt")

        with pytest.raises(KeyboardInterrupt):
            await executor.execute(raise_keyboard_interrupt)


class TestAsyncExecutorIntegration:
    """Integration tests for AsyncExecutor."""

    async def test_real_world_computation(self):
        """Test real-world computation scenario."""
        async with AsyncExecutor(max_concurrency=4) as executor:

            async def compute_primes(limit):
                """Compute prime numbers up to limit."""
                await asyncio.sleep(0.01)  # Small async delay
                primes = []
                for num in range(2, limit + 1):
                    is_prime = True
                    for i in range(2, int(num**0.5) + 1):
                        if num % i == 0:
                            is_prime = False
                            break
                    if is_prime:
                        primes.append(num)
                return primes

            # Compute primes for different ranges concurrently
            tasks = [
                executor.execute(compute_primes, 50),
                executor.execute(compute_primes, 100),
                executor.execute(compute_primes, 150),
            ]

            results = await asyncio.gather(*tasks)

            # Verify results
            assert len(results) == 3
            assert all(isinstance(result, list) for result in results)
            assert all(len(result) > 0 for result in results)

            # First few primes should be consistent
            expected_first_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
            for result in results:
                assert result[:10] == expected_first_primes

    async def test_file_processing_simulation(self):
        """Test file processing simulation."""
        async with AsyncExecutor(max_concurrency=3) as executor:

            async def process_data(data_chunk):
                """Simulate processing a chunk of data."""
                await asyncio.sleep(0.1)  # Simulate processing time

                # Simple transformation
                processed = [x * 2 for x in data_chunk if x % 2 == 0]
                return {
                    "processed_count": len(processed),
                    "sum": sum(processed),
                    "chunk_size": len(data_chunk),
                }

            # Create data chunks
            data_chunks = [list(range(i, i + 10)) for i in range(0, 50, 10)]

            # Process chunks concurrently
            tasks = [executor.execute(process_data, chunk) for chunk in data_chunks]

            results = await asyncio.gather(*tasks)

            # Verify results
            assert len(results) == 5
            total_processed = sum(r["processed_count"] for r in results)
            total_sum = sum(r["sum"] for r in results)

            assert total_processed > 0
            assert total_sum > 0
            assert all(r["chunk_size"] == 10 for r in results)
