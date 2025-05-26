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
        return AsyncExecutor(max_workers=2, timeout=5.0)

    @pytest.fixture
    def custom_executor(self):
        """Create an AsyncExecutor with custom thread pool."""
        thread_pool = ThreadPoolExecutor(max_workers=3)
        return AsyncExecutor(executor=thread_pool, timeout=10.0)

    async def test_initialization_default(self):
        """Test AsyncExecutor initialization with default parameters."""
        executor = AsyncExecutor()
        
        assert executor.max_workers == 4
        assert executor.timeout == 30.0
        assert executor._executor is None
        assert executor._closed is False

    async def test_initialization_custom(self, executor):
        """Test AsyncExecutor initialization with custom parameters."""
        assert executor.max_workers == 2
        assert executor.timeout == 5.0
        assert executor._executor is None
        assert executor._closed is False

    async def test_initialization_with_custom_executor(self, custom_executor):
        """Test AsyncExecutor initialization with custom thread pool."""
        assert custom_executor.max_workers == 3  # From custom thread pool
        assert custom_executor.timeout == 10.0
        assert custom_executor._executor is not None

    async def test_get_executor_creates_new(self, executor):
        """Test that _get_executor creates a new thread pool when needed."""
        thread_pool = executor._get_executor()
        
        assert thread_pool is not None
        assert thread_pool._max_workers == 2
        assert executor._executor is thread_pool

    async def test_get_executor_reuses_existing(self, custom_executor):
        """Test that _get_executor reuses existing thread pool."""
        original_executor = custom_executor._executor
        thread_pool = custom_executor._get_executor()
        
        assert thread_pool is original_executor

    async def test_get_executor_when_closed(self, executor):
        """Test that _get_executor raises error when closed."""
        executor._closed = True
        
        with pytest.raises(RuntimeError, match="Executor is closed"):
            executor._get_executor()

    async def test_execute_sync_function(self, executor):
        """Test executing a synchronous function."""
        def sync_function(x, y):
            return x + y

        result = await executor.execute(sync_function, 5, 10)
        assert result == 15

    async def test_execute_sync_function_with_kwargs(self, executor):
        """Test executing a synchronous function with keyword arguments."""
        def sync_function(x, y, multiplier=1):
            return (x + y) * multiplier

        result = await executor.execute(sync_function, 5, 10, multiplier=2)
        assert result == 30

    async def test_execute_sync_function_exception(self, executor):
        """Test executing a synchronous function that raises an exception."""
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await executor.execute(failing_function)

    async def test_execute_with_timeout(self, executor):
        """Test executing a function that times out."""
        def slow_function():
            import time
            time.sleep(10)  # Longer than executor timeout
            return "completed"

        with pytest.raises(asyncio.TimeoutError):
            await executor.execute(slow_function)

    async def test_execute_async_function_error(self, executor):
        """Test that executing an async function raises TypeError."""
        async def async_function():
            return "async result"

        with pytest.raises(TypeError, match="Cannot execute coroutine"):
            await executor.execute(async_function)

    async def test_execute_lambda(self, executor):
        """Test executing a lambda function."""
        result = await executor.execute(lambda x: x * 2, 21)
        assert result == 42

    async def test_execute_builtin_function(self, executor):
        """Test executing a built-in function."""
        result = await executor.execute(len, [1, 2, 3, 4, 5])
        assert result == 5

    async def test_execute_method_call(self, executor):
        """Test executing a method call."""
        test_list = [3, 1, 4, 1, 5]
        
        # Execute the sort method
        await executor.execute(test_list.sort)
        assert test_list == [1, 1, 3, 4, 5]

    async def test_execute_complex_computation(self, executor):
        """Test executing a complex computation."""
        def fibonacci(n):
            if n <= 1:
                return n
            return fibonacci(n-1) + fibonacci(n-2)

        result = await executor.execute(fibonacci, 10)
        assert result == 55

    async def test_concurrent_executions(self, executor):
        """Test multiple concurrent executions."""
        def slow_computation(n, delay=0.1):
            import time
            time.sleep(delay)
            return n * n

        # Start multiple tasks concurrently
        tasks = [
            executor.execute(slow_computation, i, 0.1)
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)
        expected = [i * i for i in range(5)]
        assert results == expected

    async def test_execute_with_side_effects(self, executor):
        """Test executing a function with side effects."""
        results = []

        def append_result(value):
            results.append(value)
            return len(results)

        count1 = await executor.execute(append_result, "first")
        count2 = await executor.execute(append_result, "second")

        assert count1 == 1
        assert count2 == 2
        assert results == ["first", "second"]

    async def test_close_executor(self, executor):
        """Test closing the executor."""
        # First, create the thread pool by executing something
        await executor.execute(lambda: 42)
        
        # Verify executor exists
        assert executor._executor is not None
        assert not executor._closed

        # Close the executor
        await executor.close()

        # Verify it's closed
        assert executor._closed
        assert executor._executor is None

    async def test_close_executor_idempotent(self, executor):
        """Test that closing executor multiple times is safe."""
        await executor.execute(lambda: 42)
        
        # Close multiple times
        await executor.close()
        await executor.close()
        await executor.close()

        # Should still be closed
        assert executor._closed

    async def test_close_executor_without_creation(self, executor):
        """Test closing executor that was never created."""
        # Close without ever creating the thread pool
        await executor.close()
        
        assert executor._closed
        assert executor._executor is None

    async def test_execute_after_close(self, executor):
        """Test that execution after close raises error."""
        await executor.close()

        with pytest.raises(RuntimeError, match="Executor is closed"):
            await executor.execute(lambda: 42)

    async def test_context_manager_success(self):
        """Test using AsyncExecutor as context manager successfully."""
        async with AsyncExecutor(max_workers=2) as executor:
            result = await executor.execute(lambda x: x * 2, 21)
            assert result == 42
            assert not executor._closed

        # Should be closed after exiting context
        assert executor._closed

    async def test_context_manager_with_exception(self):
        """Test using AsyncExecutor as context manager with exception."""
        executor = None
        
        try:
            async with AsyncExecutor(max_workers=2) as exec_instance:
                executor = exec_instance
                result = await executor.execute(lambda x: x * 2, 21)
                assert result == 42
                
                # Raise an exception
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # Should still be closed after exception
        assert executor._closed

    async def test_resource_cleanup_on_cancellation(self, executor):
        """Test that resources are cleaned up properly on task cancellation."""
        def long_running_task():
            import time
            time.sleep(2)
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
        result = await executor.execute(lambda: "quick task")
        assert result == "quick task"

    async def test_multiple_executors_independence(self):
        """Test that multiple executor instances are independent."""
        executor1 = AsyncExecutor(max_workers=2, timeout=5.0)
        executor2 = AsyncExecutor(max_workers=3, timeout=10.0)

        # Execute tasks on both
        result1 = await executor1.execute(lambda: "executor1")
        result2 = await executor2.execute(lambda: "executor2")

        assert result1 == "executor1"
        assert result2 == "executor2"

        # Close one, other should still work
        await executor1.close()
        assert executor1._closed
        assert not executor2._closed

        result3 = await executor2.execute(lambda: "still working")
        assert result3 == "still working"

        await executor2.close()

    async def test_execute_with_complex_return_types(self, executor):
        """Test executing functions that return complex types."""
        def return_dict():
            return {"key": "value", "number": 42, "list": [1, 2, 3]}

        def return_object():
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
        def modify_list(lst):
            lst.append("modified")
            return lst

        original_list = [1, 2, 3]
        result = await executor.execute(modify_list, original_list)

        # The function should have modified the list
        assert result == [1, 2, 3, "modified"]
        assert original_list == [1, 2, 3, "modified"]

    async def test_execute_with_none_return(self, executor):
        """Test executing functions that return None."""
        def return_none():
            return None

        def no_explicit_return():
            x = 1 + 1  # No return statement

        result1 = await executor.execute(return_none)
        result2 = await executor.execute(no_explicit_return)

        assert result1 is None
        assert result2 is None

    async def test_thread_safety(self, executor):
        """Test thread safety with shared state."""
        import threading
        
        counter = {"value": 0}
        lock = threading.Lock()

        def increment_counter():
            with lock:
                current = counter["value"]
                # Simulate some work
                import time
                time.sleep(0.01)
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
        return AsyncExecutor(max_workers=2, timeout=1.0)

    async def test_execute_with_import_error(self, executor):
        """Test executing function that has import error."""
        def import_nonexistent():
            import nonexistent_module  # This will fail
            return "should not reach here"

        with pytest.raises(ImportError):
            await executor.execute(import_nonexistent)

    async def test_execute_with_attribute_error(self, executor):
        """Test executing function that has attribute error."""
        def attribute_error():
            obj = object()
            return obj.nonexistent_attribute

        with pytest.raises(AttributeError):
            await executor.execute(attribute_error)

    async def test_execute_with_type_error(self, executor):
        """Test executing function that has type error."""
        def type_error():
            return "string" + 42

        with pytest.raises(TypeError):
            await executor.execute(type_error)

    async def test_execute_with_custom_exception(self, executor):
        """Test executing function that raises custom exception."""
        class CustomError(Exception):
            pass

        def raise_custom():
            raise CustomError("Custom error message")

        with pytest.raises(CustomError, match="Custom error message"):
            await executor.execute(raise_custom)

    async def test_execute_with_system_exit(self, executor):
        """Test executing function that calls sys.exit."""
        def call_exit():
            import sys
            sys.exit(1)

        with pytest.raises(SystemExit):
            await executor.execute(call_exit)

    async def test_execute_with_keyboard_interrupt(self, executor):
        """Test executing function that raises KeyboardInterrupt."""
        def raise_keyboard_interrupt():
            raise KeyboardInterrupt("Simulated interrupt")

        with pytest.raises(KeyboardInterrupt):
            await executor.execute(raise_keyboard_interrupt)


class TestAsyncExecutorIntegration:
    """Integration tests for AsyncExecutor."""

    async def test_real_world_computation(self):
        """Test real-world computation scenario."""
        async with AsyncExecutor(max_workers=4, timeout=10.0) as executor:
            def compute_primes(limit):
                """Compute prime numbers up to limit."""
                primes = []
                for num in range(2, limit + 1):
                    is_prime = True
                    for i in range(2, int(num ** 0.5) + 1):
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
        async with AsyncExecutor(max_workers=3, timeout=5.0) as executor:
            def process_data(data_chunk):
                """Simulate processing a chunk of data."""
                import time
                time.sleep(0.1)  # Simulate processing time
                
                # Simple transformation
                processed = [x * 2 for x in data_chunk if x % 2 == 0]
                return {
                    "processed_count": len(processed),
                    "sum": sum(processed),
                    "chunk_size": len(data_chunk)
                }

            # Create data chunks
            data_chunks = [
                list(range(i, i + 10)) for i in range(0, 50, 10)
            ]

            # Process chunks concurrently
            tasks = [
                executor.execute(process_data, chunk) 
                for chunk in data_chunks
            ]

            results = await asyncio.gather(*tasks)

            # Verify results
            assert len(results) == 5
            total_processed = sum(r["processed_count"] for r in results)
            total_sum = sum(r["sum"] for r in results)
            
            assert total_processed > 0
            assert total_sum > 0
            assert all(r["chunk_size"] == 10 for r in results)