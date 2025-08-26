"""Async testing fixtures for concurrent and asynchronous operations."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture
def async_test_env() -> dict[str, Any]:
    """Provide a comprehensive async testing environment."""
    env = {
        "loop": asyncio.get_event_loop(),
        "timeout": 30.0,
        "concurrent_limit": 10,
        "retry_attempts": 3,
    }

    return env


@pytest.fixture
def mock_async_service() -> AsyncMock:
    """Create a mock async service with realistic behavior patterns."""
    mock = AsyncMock()

    # Configure common async patterns
    mock.startup = AsyncMock()
    mock.shutdown = AsyncMock()
    mock.health_check = AsyncMock(return_value={"status": "healthy"})
    mock.process = AsyncMock(return_value={"result": "success"})

    # Add realistic delays
    async def delayed_startup():
        await asyncio.sleep(0.01)
        return True

    async def delayed_process(data):
        await asyncio.sleep(0.005)
        return {"processed": data, "status": "complete"}

    mock.startup.side_effect = delayed_startup
    mock.process.side_effect = delayed_process

    return mock


@pytest.fixture
async def async_timeout_manager():
    """Provide timeout management for async tests."""

    class TimeoutManager:
        def __init__(self):
            self.default_timeout = 10.0
            self.long_timeout = 30.0
            self.short_timeout = 1.0

        async def with_timeout(self, coro, timeout=None):
            timeout = timeout or self.default_timeout
            return await asyncio.wait_for(coro, timeout=timeout)

        def timeout_after(self, seconds):
            return asyncio.timeout(seconds)

    return TimeoutManager()


@pytest.fixture
def concurrent_executor():
    """Provide utilities for concurrent test execution."""

    class ConcurrentExecutor:
        def __init__(self):
            self.max_workers = 10

        async def run_concurrent(self, tasks, max_concurrent=None):
            """Run tasks concurrently with optional concurrency limit."""
            max_concurrent = max_concurrent or self.max_workers
            semaphore = asyncio.Semaphore(max_concurrent)

            async def limited_task(task):
                async with semaphore:
                    return await task

            return await asyncio.gather(*[limited_task(task) for task in tasks])

        async def run_with_backpressure(self, producer, consumer, buffer_size=100):
            """Run producer/consumer with backpressure control."""
            queue = asyncio.Queue(maxsize=buffer_size)

            async def produce():
                async for item in producer():
                    await queue.put(item)
                await queue.put(None)  # Signal completion

            async def consume():
                results = []
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    result = await consumer(item)
                    results.append(result)
                return results

            producer_task = asyncio.create_task(produce())
            consumer_task = asyncio.create_task(consume())

            await producer_task
            results = await consumer_task
            return results

    return ConcurrentExecutor()


@pytest.fixture
async def async_resource_manager():
    """Manage async resources with proper cleanup."""

    class AsyncResourceManager:
        def __init__(self):
            self.resources = []
            self.connections = []

        async def create_resource(self, factory, *args, **kwargs):
            """Create and track an async resource."""
            resource = await factory(*args, **kwargs)
            self.resources.append(resource)
            return resource

        async def create_connection(self, connector, *args, **kwargs):
            """Create and track an async connection."""
            connection = await connector(*args, **kwargs)
            self.connections.append(connection)
            return connection

        async def cleanup_all(self):
            """Cleanup all managed resources."""
            # Close connections first
            for connection in reversed(self.connections):
                if hasattr(connection, "close"):
                    try:
                        await connection.close()
                    except Exception:
                        pass

            # Then cleanup resources
            for resource in reversed(self.resources):
                if hasattr(resource, "cleanup"):
                    try:
                        await resource.cleanup()
                    except Exception:
                        pass
                elif hasattr(resource, "close"):
                    try:
                        await resource.close()
                    except Exception:
                        pass

    manager = AsyncResourceManager()

    try:
        yield manager
    finally:
        # Ensure cleanup happens
        loop = asyncio.get_event_loop()
        if loop.is_running():
            await manager.cleanup_all()


@pytest.fixture
def async_error_simulator():
    """Simulate various async error conditions."""

    class AsyncErrorSimulator:
        @staticmethod
        async def timeout_error(delay=1.0):
            """Simulate a timeout error."""
            await asyncio.sleep(delay)
            raise asyncio.TimeoutError("Simulated timeout")

        @staticmethod
        async def connection_error():
            """Simulate a connection error."""
            await asyncio.sleep(0.01)
            raise ConnectionError("Simulated connection failure")

        @staticmethod
        async def intermittent_failure(success_rate=0.7):
            """Simulate intermittent failures."""
            await asyncio.sleep(0.005)
            if asyncio.get_event_loop().time() % 1.0 > success_rate:
                raise Exception("Intermittent failure")
            return True

        @staticmethod
        async def gradual_slowdown(base_delay=0.01, multiplier=1.5):
            """Simulate gradually increasing response times."""
            call_count = getattr(AsyncErrorSimulator.gradual_slowdown, "_calls", 0)
            AsyncErrorSimulator.gradual_slowdown._calls = call_count + 1

            delay = base_delay * (multiplier**call_count)
            await asyncio.sleep(min(delay, 5.0))  # Cap at 5 seconds
            return f"Response after {delay:.3f}s"

    return AsyncErrorSimulator()
