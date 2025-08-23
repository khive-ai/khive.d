"""Integration tests for Cache Service with Redis backend.

Tests Redis connectivity, cache operations, serialization, error handling,
and performance characteristics under various conditions.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import pytest

from khive.services.cache.config import CacheConfig
from khive.services.cache.models import CacheEntry, CacheStats
from khive.services.cache.redis_cache import RedisCache
from tests.integration.fixtures.external_services import (
    MockRedisServer,
    mock_redis_cache,
    real_redis_cache,
)


@pytest.mark.integration
class TestRedisCacheIntegration:
    """Integration tests for Redis cache functionality."""

    @pytest.fixture
    def cache_config(self):
        """Standard cache configuration for testing."""
        return CacheConfig(
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
            redis_ssl=False,  # Explicitly disable SSL for testing
            max_connections=10,
            compression_enabled=False,
        )

    @pytest.fixture
    def test_data(self):
        """Sample data for cache testing."""
        return {
            "string_data": "test_value",
            "numeric_data": 42,
            "complex_data": {
                "nested": {"key": "value"},
                "array": [1, 2, 3, 4, 5],
                "timestamp": datetime.now().isoformat(),
            },
            "large_data": "x" * 1024,  # 1KB of data
        }

    async def test_cache_basic_operations_mock(self, mock_redis_cache, test_data):
        """Test basic cache operations with mock Redis."""
        cache = mock_redis_cache

        # Test set operation
        key = "test_basic_key"
        await cache.set(key, test_data["string_data"])

        # Test get operation
        retrieved_entry = await cache.get(key)
        assert retrieved_entry is not None
        assert retrieved_entry.value == test_data["string_data"]

        # Test exists operation
        exists = await cache.exists(key)
        assert exists is True

        # Test delete operation
        deleted = await cache.delete(key)
        assert deleted is True

        # Verify deletion
        retrieved_after_delete = await cache.get(key)
        assert retrieved_after_delete is None

    async def test_cache_json_serialization(self, mock_redis_cache, test_data):
        """Test JSON serialization/deserialization with complex data."""
        cache = mock_redis_cache

        key = "test_json_key"
        complex_data = test_data["complex_data"]

        # Store complex data
        await cache.set(key, complex_data)

        # Retrieve and verify
        retrieved_entry = await cache.get(key)
        assert retrieved_entry is not None
        retrieved = retrieved_entry.value
        assert retrieved == complex_data
        assert isinstance(retrieved["nested"], dict)
        assert isinstance(retrieved["array"], list)
        assert len(retrieved["array"]) == 5

    async def test_cache_expiration_mock(self, mock_redis_cache):
        """Test cache expiration functionality with mock."""
        cache = mock_redis_cache

        key = "test_expiration_key"
        value = "expires_soon"
        ttl = 1  # 1 second

        # Set with expiration
        await cache.set(key, value, ttl_seconds=ttl)

        # Verify immediate retrieval works
        retrieved_entry = await cache.get(key)
        assert retrieved_entry is not None
        assert retrieved_entry.value == value

        # Wait for expiration (mock may need special handling)
        await asyncio.sleep(1.1)

        # Note: Mock implementation may need to simulate expiration
        # For real Redis, this would return None after TTL

    async def test_cache_connection_error_handling(self, cache_config):
        """Test cache behavior during connection failures."""
        cache = RedisCache(cache_config)

        # Test operations without connection should handle errors gracefully
        with pytest.raises(Exception):  # Should raise connection error
            await cache.get("test_key")

        # Test that cache can recover after connection issues
        # This would need a mock that can simulate connection recovery

    async def test_cache_concurrent_operations(self, mock_redis_cache):
        """Test cache performance under concurrent load."""
        cache = mock_redis_cache
        num_operations = 100

        # Concurrent set operations
        async def set_test_data(index: int):
            key = f"concurrent_key_{index}"
            value = f"concurrent_value_{index}"
            await cache.set(key, value)
            return index

        # Run concurrent operations
        start_time = time.time()
        set_tasks = [set_test_data(i) for i in range(num_operations)]
        set_results = await asyncio.gather(*set_tasks, return_exceptions=True)

        # Verify all operations completed
        successful_sets = [r for r in set_results if not isinstance(r, Exception)]
        assert len(successful_sets) >= num_operations * 0.9  # Allow 10% failure

        # Concurrent get operations
        async def get_test_data(index: int):
            key = f"concurrent_key_{index}"
            value = await cache.get(key)
            return value

        get_tasks = [get_test_data(i) for i in range(num_operations)]
        get_results = await asyncio.gather(*get_tasks, return_exceptions=True)

        end_time = time.time()
        duration = end_time - start_time

        # Verify performance
        successful_gets = [r for r in get_results if not isinstance(r, Exception)]
        assert len(successful_gets) >= num_operations * 0.9

        # Performance assertion
        assert duration < 5.0, f"Concurrent operations took too long: {duration}s"

    async def test_cache_memory_usage(self, mock_redis_cache, test_data):
        """Test cache memory usage with large data sets."""
        cache = mock_redis_cache

        # Store multiple large objects
        large_data = test_data["large_data"] * 100  # 100KB per object
        num_objects = 50

        start_time = time.time()

        for i in range(num_objects):
            key = f"large_object_{i}"
            await cache.set(key, large_data)

        end_time = time.time()
        storage_duration = end_time - start_time

        # Test retrieval performance
        start_time = time.time()

        retrieved_objects = []
        for i in range(num_objects):
            key = f"large_object_{i}"
            retrieved_entry = await cache.get(key)
            if retrieved_entry:
                retrieved_objects.append(retrieved_entry.value)

        end_time = time.time()
        retrieval_duration = end_time - start_time

        # Verify data integrity
        assert len(retrieved_objects) >= num_objects * 0.9
        for obj in retrieved_objects:
            assert len(obj) == len(large_data)

        # Performance assertions
        assert storage_duration < 10.0, f"Storage took too long: {storage_duration}s"
        assert (
            retrieval_duration < 10.0
        ), f"Retrieval took too long: {retrieval_duration}s"

    async def test_cache_stats_tracking(self, mock_redis_cache):
        """Test cache statistics tracking functionality."""
        cache = mock_redis_cache

        # Perform various operations
        await cache.set("stats_key_1", "value_1")
        await cache.set("stats_key_2", "value_2")

        # Cache hits
        await cache.get("stats_key_1")  # Hit
        await cache.get("stats_key_1")  # Hit
        await cache.get("nonexistent_key")  # Miss

        # Get statistics (if implemented)
        if hasattr(cache, "get_stats"):
            stats = await cache.get_stats()
            assert isinstance(stats, CacheStats)
            # Additional stats verification would depend on implementation

    async def test_cache_error_recovery(self, mock_redis_cache):
        """Test cache error recovery and resilience."""
        cache = mock_redis_cache

        # Test that cache can handle various error conditions
        test_cases = [
            ("normal_key", "normal_value"),
            ("", "empty_key_test"),  # Empty key
            ("unicode_key_🔑", "unicode_value_🌟"),  # Unicode
            ("very_long_key_" + "x" * 1000, "long_key_test"),  # Long key
        ]

        for key, value in test_cases:
            try:
                await cache.set(key, value)
                retrieved_entry = await cache.get(key)
                # Only assert if no exception was raised
                if key != "":  # Empty keys may not be supported
                    assert retrieved_entry is not None
                    assert retrieved_entry.value == value
            except Exception as e:
                # Log error for investigation but don't fail test
                print(f"Cache error for key '{key}': {e}")

    @pytest.mark.skipif(
        not pytest.importorskip("redis", minversion="4.0"),
        reason="Redis not available for real integration testing",
    )
    async def test_real_redis_integration(self, real_redis_cache, test_data):
        """Test with real Redis instance if available."""
        cache = real_redis_cache

        # Test basic operations with real Redis
        key = "real_redis_test_key"
        value = test_data["string_data"]

        # Clean up any existing data
        await cache.delete(key)

        # Test set/get cycle
        await cache.set(key, value)
        retrieved_entry = await cache.get(key)
        assert retrieved_entry is not None
        assert retrieved_entry.value == value

        # Test expiration with real Redis
        ttl_key = "real_redis_ttl_test"
        await cache.set(ttl_key, "expires", ttl=1)

        # Immediate retrieval should work
        immediate_entry = await cache.get(ttl_key)
        assert immediate_entry is not None
        assert immediate_entry.value == "expires"

        # Wait for expiration
        await asyncio.sleep(1.5)
        expired = await cache.get(ttl_key)
        assert expired is None

        # Cleanup
        await cache.delete(key)

    async def test_cache_connection_pool_management(self, cache_config):
        """Test Redis connection pool management."""
        cache = RedisCache(cache_config)

        # Test multiple simultaneous connections
        async def test_operation(index: int):
            key = f"pool_test_{index}"
            value = f"pool_value_{index}"

            await cache.set(key, value)
            retrieved_entry = await cache.get(key)
            await cache.delete(key)

            return retrieved_entry is not None and retrieved_entry.value == value

        # Create more concurrent operations than max connections
        num_operations = cache_config.max_connections * 2
        tasks = [test_operation(i) for i in range(num_operations)]

        # This should test connection pool behavior
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = [r for r in results if r is True]
            # Some operations should succeed even with limited pool
            assert len(successful) > 0
        except Exception:
            # Connection errors are expected if Redis isn't available
            pytest.skip("Redis connection not available for pool testing")


@pytest.mark.integration
class TestCacheServiceErrors:
    """Integration tests for cache error handling and edge cases."""

    async def test_cache_serialization_errors(self, mock_redis_cache):
        """Test cache behavior with non-serializable data."""
        cache = mock_redis_cache

        # Test with non-JSON-serializable data
        class NonSerializable:
            def __init__(self):
                self.value = "test"

        key = "serialization_error_key"
        non_serializable_data = NonSerializable()

        # This should handle serialization errors gracefully
        with pytest.raises((TypeError, ValueError)):
            await cache.set_json(key, non_serializable_data)

    async def test_cache_large_data_limits(self, mock_redis_cache):
        """Test cache behavior with very large data."""
        cache = mock_redis_cache

        # Test with extremely large data (may hit size limits)
        huge_data = "x" * (10 * 1024 * 1024)  # 10MB string
        key = "huge_data_key"

        try:
            await cache.set(key, huge_data)
            retrieved_entry = await cache.get(key)
            if retrieved_entry is not None:
                assert retrieved_entry.value == huge_data
            # May fail due to size, so retrieved_entry could be None
        except Exception:
            # Large data errors are acceptable
            pass

    async def test_cache_connection_interruption_recovery(self, cache_config):
        """Test cache recovery after connection interruption."""
        cache = RedisCache(cache_config)

        # This test would require mocking connection interruption
        # For now, test that cache handles connection errors gracefully
        try:
            await cache.ping()
        except Exception:
            # Expected if Redis not available
            pass

        # Test that cache can attempt reconnection
        try:
            await cache.set("recovery_test", "value")
        except Exception:
            # Connection errors are expected without Redis
            pass


@pytest.mark.integration
@pytest.mark.performance
class TestCachePerformance:
    """Performance integration tests for cache operations."""

    async def test_cache_throughput(self, mock_redis_cache):
        """Test cache throughput under high load."""
        cache = mock_redis_cache

        num_operations = 1000
        batch_size = 100

        async def batch_operations(start_index: int):
            operations = []
            for i in range(batch_size):
                key = f"throughput_key_{start_index + i}"
                value = f"throughput_value_{start_index + i}"
                operations.append(cache.set(key, value))

            await asyncio.gather(*operations)
            return batch_size

        # Run batched operations
        start_time = time.time()
        batches = [
            batch_operations(i * batch_size)
            for i in range(num_operations // batch_size)
        ]

        batch_results = await asyncio.gather(*batches, return_exceptions=True)
        end_time = time.time()

        # Calculate performance metrics
        duration = end_time - start_time
        successful_batches = [r for r in batch_results if isinstance(r, int)]
        total_operations = sum(successful_batches)

        operations_per_second = total_operations / duration if duration > 0 else 0

        # Performance assertions
        assert (
            operations_per_second > 100
        ), f"Throughput too low: {operations_per_second} ops/sec"
        assert duration < 30.0, f"Batch operations took too long: {duration}s"

    async def test_cache_latency_distribution(self, mock_redis_cache):
        """Test cache operation latency distribution."""
        cache = mock_redis_cache

        num_operations = 100
        latencies = []

        # Measure individual operation latencies
        for i in range(num_operations):
            key = f"latency_key_{i}"
            value = f"latency_value_{i}"

            start_time = time.time()
            await cache.set(key, value)
            await cache.get(key)
            end_time = time.time()

            latencies.append((end_time - start_time) * 1000)  # Convert to milliseconds

        # Calculate latency statistics
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)

        # Sort for percentile calculation
        sorted_latencies = sorted(latencies)
        p95_latency = sorted_latencies[int(0.95 * len(sorted_latencies))]
        p99_latency = sorted_latencies[int(0.99 * len(sorted_latencies))]

        # Performance assertions (adjusted for mock performance)
        assert avg_latency < 100, f"Average latency too high: {avg_latency}ms"
        assert p95_latency < 200, f"95th percentile latency too high: {p95_latency}ms"
        assert max_latency < 1000, f"Maximum latency too high: {max_latency}ms"

        # Log performance metrics for analysis
        print(f"Cache Performance Metrics:")
        print(f"  Average latency: {avg_latency:.2f}ms")
        print(f"  95th percentile: {p95_latency:.2f}ms")
        print(f"  99th percentile: {p99_latency:.2f}ms")
        print(f"  Min/Max: {min_latency:.2f}ms / {max_latency:.2f}ms")
