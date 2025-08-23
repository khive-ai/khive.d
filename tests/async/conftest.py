"""
Configuration and shared fixtures for async and concurrency tests.
"""

import asyncio
import gc

import pytest


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for all async tests."""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
async def clean_async_environment():
    """Ensure clean async environment for each test."""
    # Cancel any existing tasks
    tasks = [task for task in asyncio.all_tasks() if not task.done()]
    for task in tasks:
        task.cancel()

    # Wait for cancellation to complete
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    # Force garbage collection
    gc.collect()

    yield

    # Cleanup after test
    tasks = [task for task in asyncio.all_tasks() if not task.done()]
    for task in tasks:
        task.cancel()

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


@pytest.fixture
def async_test_markers():
    """Configure test execution markers for async tests."""
    return {
        "timeout": 30,  # Default timeout for async tests
        "strict_memory": True,  # Enable strict memory checking
        "concurrency_level": "medium",  # Default concurrency level
    }
