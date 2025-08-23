"""External service fixtures for integration testing.

Provides fixtures for Redis, PostgreSQL, and OpenAI API integration testing
with both real and mocked implementations.
"""

import asyncio
import os
from typing import Any
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from khive.services.cache.config import CacheConfig
from khive.services.cache.redis_cache import RedisCache


class MockRedisServer:
    """Mock Redis server for testing Redis integration without real Redis."""

    def __init__(self):
        self._data: dict[str, Any] = {}
        self._connected = True  # Start connected for testing

    async def connect(self):
        """Simulate Redis connection."""
        await asyncio.sleep(0.01)  # Simulate connection delay
        self._connected = True

    async def disconnect(self):
        """Simulate Redis disconnection."""
        self._connected = False

    async def set(self, key: str, value: str, ex: int | None = None):
        """Mock Redis SET operation."""
        if not self._connected:
            raise RedisConnectionError("Not connected to Redis")
        self._data[key] = {"value": value, "expire": ex}
        return True

    async def setex(self, key: str, time: int, value: str):
        """Mock Redis SETEX operation."""
        if not self._connected:
            raise RedisConnectionError("Not connected to Redis")
        self._data[key] = {"value": value, "expire": time}
        return True

    async def get(self, key: str):
        """Mock Redis GET operation."""
        if not self._connected:
            raise RedisConnectionError("Not connected to Redis")
        data = self._data.get(key)
        return data["value"] if data else None

    async def delete(self, *keys: str):
        """Mock Redis DELETE operation."""
        if not self._connected:
            raise RedisConnectionError("Not connected to Redis")
        deleted_count = 0
        for key in keys:
            if self._data.pop(key, None) is not None:
                deleted_count += 1
        return deleted_count

    async def exists(self, *keys: str):
        """Mock Redis EXISTS operation."""
        if not self._connected:
            raise RedisConnectionError("Not connected to Redis")
        count = 0
        for key in keys:
            if key in self._data:
                count += 1
        return count

    async def keys(self, pattern: str = "*"):
        """Mock Redis KEYS operation."""
        if not self._connected:
            raise RedisConnectionError("Not connected to Redis")
        # Simple pattern matching (just support * wildcard)
        if pattern == "*":
            return list(self._data.keys())
        # For more complex patterns, you'd implement proper pattern matching
        return [key for key in self._data if pattern.replace("*", "") in key]

    async def flushdb(self):
        """Mock Redis FLUSHDB operation."""
        if not self._connected:
            raise RedisConnectionError("Not connected to Redis")
        self._data.clear()
        return True

    async def info(self, section: str | None = None):
        """Mock Redis INFO operation."""
        if not self._connected:
            raise RedisConnectionError("Not connected to Redis")
        return {
            "db0": {"keys": len(self._data)},
            "used_memory": len(str(self._data)) * 8,  # Rough memory estimation
        }

    async def ping(self):
        """Mock Redis PING operation."""
        if not self._connected:
            raise RedisConnectionError("Not connected to Redis")
        return b"PONG"

    async def close(self):
        """Mock Redis close operation."""
        self._connected = False

    # Add context manager support
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class MockOpenAIClient:
    """Mock OpenAI client for testing API integration."""

    def __init__(self, response_delay: float = 0.1, success_rate: float = 1.0):
        self.response_delay = response_delay
        self.success_rate = success_rate
        self.call_count = 0

    def create_completion_response(self, prompt: str) -> dict[str, Any]:
        """Create a mock completion response."""
        return {
            "id": f"mock-completion-{self.call_count}",
            "object": "text_completion",
            "model": "gpt-3.5-turbo",
            "choices": [
                {
                    "text": f"Mock response for: {prompt[:50]}...",
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt) // 4,  # Rough approximation
                "completion_tokens": 50,
                "total_tokens": len(prompt) // 4 + 50,
            },
        }

    async def create_completion(self, **kwargs) -> dict[str, Any]:
        """Mock completion creation."""
        await asyncio.sleep(self.response_delay)
        self.call_count += 1

        if self.call_count % (1 / self.success_rate) == 0:
            raise Exception("Mock API failure")

        prompt = kwargs.get("prompt", "")
        return self.create_completion_response(prompt)


@pytest.fixture
def mock_redis_server():
    """Fixture providing a mock Redis server."""
    return MockRedisServer()


@pytest.fixture
async def mock_redis_connected(mock_redis_server):
    """Fixture providing a connected mock Redis server."""
    await mock_redis_server.connect()
    yield mock_redis_server
    await mock_redis_server.disconnect()


@pytest.fixture
def redis_cache_config():
    """Fixture providing Redis cache configuration for testing."""
    return CacheConfig(
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        redis_ssl=False,  # Explicitly disable SSL for testing
        max_connections=10,
        compression_enabled=False,
    )


@pytest.fixture
async def mock_redis_cache(redis_cache_config, mock_redis_server):
    """Fixture providing a Redis cache with mock backend."""
    cache = RedisCache(redis_cache_config)
    # Patch the Redis connection to use our mock
    cache._redis = mock_redis_server
    cache._connect = AsyncMock()  # Mock connection method
    yield cache


@pytest.fixture
def mock_openai_client():
    """Fixture providing a mock OpenAI client."""
    return MockOpenAIClient()


@pytest.fixture
def unreliable_openai_client():
    """Fixture providing an unreliable mock OpenAI client for error testing."""
    return MockOpenAIClient(response_delay=0.5, success_rate=0.7)


@pytest.fixture
def slow_openai_client():
    """Fixture providing a slow mock OpenAI client for timeout testing."""
    return MockOpenAIClient(response_delay=2.0, success_rate=1.0)


@pytest.fixture
def integration_env():
    """Fixture providing environment variables for integration testing."""
    env_vars = {
        "KHIVE_TEST_MODE": "true",
        "KHIVE_DISABLE_EXTERNAL_APIS": "false",  # Enable for integration tests
        "OPENAI_API_KEY": "test-api-key",
        "REDIS_URL": "redis://localhost:6379/0",
        "POSTGRES_URL": "postgresql://test:test@localhost:5432/khive_test",
    }

    original_env = {}
    for key, value in env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield env_vars

    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture(scope="session")
def real_redis_available():
    """Check if a real Redis instance is available for testing."""
    try:
        import redis

        r = redis.Redis(host="localhost", port=6379, db=0)
        r.ping()
        return True
    except Exception:
        return False


@pytest.fixture
async def real_redis_cache(redis_cache_config, real_redis_available):
    """Fixture providing a real Redis cache if available, skip if not."""
    if not real_redis_available:
        pytest.skip("Redis not available for integration testing")

    cache = RedisCache(redis_cache_config)
    await cache._connect()
    yield cache

    # Cleanup
    try:
        redis_client = await cache._get_redis()
        await redis_client.flushdb()  # Clear test data
        await cache.close()
    except Exception:
        pass  # Ignore cleanup errors
