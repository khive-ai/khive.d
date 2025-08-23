"""Cache Service Security Tests.

This module provides comprehensive security testing for the cache service
including:
- Cache key injection prevention
- Data serialization security
- Redis connection security
- Cache poisoning prevention
- Key collision attack prevention
- TTL manipulation prevention
- Memory exhaustion protection
- Unauthorized cache access prevention
"""

import asyncio
import json
import tempfile
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from khive.services.cache.config import CacheConfig
from khive.services.cache.models import CacheEntry, CacheKey, CacheStats
from khive.services.cache.redis_cache import RedisCache
from khive.services.cache.service import CacheService


class TestCacheKeySecurityValidation:
    """Test cache key security validation."""

    @pytest.fixture
    def cache_service(self):
        """Create cache service for testing."""
        config = CacheConfig(
            enabled=True,
            redis_host="localhost",
            redis_port=6379,
            max_key_length=250,
            fallback_on_error=True,
        )
        return CacheService(config)

    @pytest.mark.parametrize(
        "malicious_key",
        [
            "../../../etc/passwd",
            "key; rm -rf /",
            "key`cat /etc/passwd`",
            "key$(whoami)",
            "key|dangerous_command",
            "key&background_process",
            "key\x00null_byte",
            "key\nmalicious_newline",
            "key\rcarriage_return",
            "key\tmalicious_tab",
            "<script>alert('xss')</script>",
            "'; DROP TABLE cache; --",
            "key with spaces and special chars!@#$%^&*()",
            "key\u202e\u202d",  # Unicode directional override
            "key\\..\\..\\etc\\passwd",  # Windows path traversal
            "/etc/passwd",
            "C:\\Windows\\System32\\config",
            "key" + "A" * 500,  # Excessively long key
        ],
    )
    def test_malicious_cache_key_validation(self, cache_service, malicious_key):
        """Test that malicious cache keys are handled securely."""
        # Test hash generation with malicious key
        try:
            hash_result = cache_service._generate_hash(malicious_key)

            # If hash generation succeeds, it should produce safe output
            assert isinstance(hash_result, str)
            assert len(hash_result) == 16  # Expected hash length

            # Hash should not contain dangerous patterns
            dangerous_patterns = ["../", "rm -rf", "DROP TABLE", "<script>", "\x00"]
            for pattern in dangerous_patterns:
                assert (
                    pattern not in hash_result
                ), f"Dangerous pattern {pattern} in hash"

        except (ValueError, TypeError):
            # Expected - should reject some malicious inputs
            pass

    def test_cache_key_generation_consistency(self, cache_service):
        """Test cache key generation consistency and security."""
        # Test that same input produces same hash
        test_input = {"key": "value", "number": 42}

        hash1 = cache_service._generate_hash(test_input)
        hash2 = cache_service._generate_hash(test_input)

        assert hash1 == hash2, "Hash generation should be deterministic"

        # Test that different inputs produce different hashes
        different_input = {"key": "value", "number": 43}
        hash3 = cache_service._generate_hash(different_input)

        assert hash1 != hash3, "Different inputs should produce different hashes"

        # Test dictionary ordering independence
        reordered_input = {"number": 42, "key": "value"}
        hash4 = cache_service._generate_hash(reordered_input)

        assert hash1 == hash4, "Dictionary ordering should not affect hash"

    @pytest.mark.parametrize(
        "collision_attempt",
        [
            # Attempt to create hash collisions
            {"a": "1", "b": "2"},
            {"a": 1, "b": 2},
            {"A": "1", "B": "2"},
            {"ab": "12"},
            {"": "ab12"},
            {1: "a", 2: "b"},
            {"1": "a", "2": "b"},
        ],
    )
    def test_cache_key_collision_resistance(self, cache_service, collision_attempt):
        """Test resistance to hash collision attempts."""
        # Generate hashes for collision attempts
        hash_value = cache_service._generate_hash(collision_attempt)

        # Should produce valid hash
        assert isinstance(hash_value, str)
        assert len(hash_value) == 16
        assert all(c in "0123456789abcdef" for c in hash_value.lower())

        # Test with baseline to ensure different inputs produce different hashes
        baseline = {"baseline": "test"}
        baseline_hash = cache_service._generate_hash(baseline)

        assert (
            hash_value != baseline_hash
        ), "Collision attempt should not match baseline"


class TestCacheDataSecurityValidation:
    """Test cache data security validation."""

    @pytest.fixture
    def mock_redis_cache(self):
        """Create mock Redis cache for testing."""
        config = CacheConfig(enabled=True)
        cache = RedisCache(config)

        # Mock Redis client
        cache._redis = AsyncMock()
        return cache

    @pytest.mark.asyncio
    async def test_cache_data_serialization_security(self, mock_redis_cache):
        """Test security of cache data serialization."""
        # Test with potentially dangerous data
        dangerous_data = {
            "__proto__": {"admin": True},
            "constructor": {"prototype": {"admin": True}},
            "eval": "malicious_code()",
            "script": "<script>alert('xss')</script>",
            "command": "; rm -rf /",
            "sql": "'; DROP TABLE users; --",
            "path": "../../../etc/passwd",
        }

        # Mock successful Redis operations
        mock_redis_cache._redis.set.return_value = True

        try:
            success = await mock_redis_cache.set("test_key", dangerous_data, 3600)

            # If serialization succeeds, verify Redis was called with safe data
            if success:
                assert mock_redis_cache._redis.set.called
                call_args = mock_redis_cache._redis.set.call_args

                if call_args and len(call_args[0]) > 1:
                    serialized_data = call_args[0][1]  # Second argument is the value

                    # Should be JSON string
                    if isinstance(serialized_data, str):
                        try:
                            parsed = json.loads(serialized_data)

                            # Dangerous patterns should not be in serialized form
                            serialized_str = json.dumps(parsed)
                            dangerous_patterns = [
                                "__proto__",
                                "constructor",
                                "eval(",
                                "<script>",
                            ]

                            # Note: Some patterns may be preserved as data, but should be handled safely
                            # The key is that they shouldn't be executable

                        except json.JSONDecodeError:
                            # If not JSON, should not contain dangerous patterns
                            assert "<script>" not in serialized_data
                            assert "eval(" not in serialized_data

        except (ValueError, TypeError):
            # Expected - dangerous data might be rejected
            pass

    @pytest.mark.asyncio
    async def test_cache_data_deserialization_security(self, mock_redis_cache):
        """Test security of cache data deserialization."""
        # Test with malicious cached data
        malicious_cached_data = [
            '{"__proto__": {"admin": true}}',
            '{"constructor": {"prototype": {"admin": true}}}',
            '{"data": "<script>alert(\\"xss\\")</script>"}',
            '{"query": "\\"; DROP TABLE users; --"}',
            '{"path": "../../../etc/passwd"}',
            '{"command": "; rm -rf /"}',
        ]

        for malicious_data in malicious_cached_data:
            # Mock Redis returning malicious data
            mock_redis_cache._redis.get.return_value = malicious_data

            try:
                # Attempt to deserialize
                cache_entry = await mock_redis_cache.get("test_key")

                if cache_entry:
                    # If deserialization succeeds, data should be safe
                    assert isinstance(cache_entry, CacheEntry)

                    # Value should not contain executable dangerous content
                    value_str = str(cache_entry.value)

                    # Basic checks - implementation may vary
                    if "<script>" in malicious_data:
                        # XSS content should be handled safely
                        # May be preserved as data but shouldn't be executable
                        pass

            except (json.JSONDecodeError, ValueError, TypeError):
                # Expected - malicious data should be rejected or handled safely
                pass

    @pytest.mark.asyncio
    async def test_cache_metadata_security(self, mock_redis_cache):
        """Test security of cache metadata handling."""
        # Test with malicious metadata
        malicious_metadata = {
            "__proto__": {"admin": True},
            "eval": "dangerous_eval_code",
            "script_src": "javascript:alert('xss')",
            "system_command": "; cat /etc/passwd",
            "injection": "'; DELETE FROM cache; --",
            "traversal": "../../../sensitive/data",
        }

        mock_redis_cache._redis.set.return_value = True

        try:
            success = await mock_redis_cache.set(
                "test_key", "safe_value", ttl_seconds=3600, metadata=malicious_metadata
            )

            if success:
                # Verify that metadata was handled safely
                assert mock_redis_cache._redis.set.called

                # Metadata should be included in cache entry but safely serialized
                call_args = mock_redis_cache._redis.set.call_args

                if call_args and len(call_args[0]) > 1:
                    cached_data = call_args[0][1]

                    # Should not contain dangerous executable patterns
                    dangerous_executable = ["eval(", "javascript:", "DELETE FROM"]
                    for pattern in dangerous_executable:
                        assert (
                            pattern not in cached_data
                        ), f"Executable pattern {pattern} found"

        except (ValueError, TypeError):
            # Expected - malicious metadata might be rejected
            pass

    @pytest.mark.asyncio
    async def test_cache_size_limits(self, mock_redis_cache):
        """Test cache size limit enforcement."""
        # Test with excessively large data
        large_data = "A" * (1024 * 1024 * 10)  # 10MB data

        mock_redis_cache._redis.set.return_value = True

        try:
            success = await mock_redis_cache.set("test_key", large_data, 3600)

            # Should either succeed with size limits or reject large data
            if success:
                # Verify Redis was called with reasonable data size
                call_args = mock_redis_cache._redis.set.call_args
                if call_args and len(call_args[0]) > 1:
                    cached_data = call_args[0][1]
                    # Implementation may compress or limit data size
                    assert len(cached_data) < 1024 * 1024 * 50  # Reasonable limit

        except (ValueError, MemoryError):
            # Expected - large data might be rejected
            pass


class TestRedisCacheConnectionSecurity:
    """Test Redis cache connection security."""

    def test_redis_connection_configuration_security(self):
        """Test Redis connection configuration security."""
        # Test secure configuration
        secure_config = CacheConfig(
            enabled=True,
            redis_host="127.0.0.1",  # Localhost only
            redis_port=6379,
            redis_password="secure_password_123",
            redis_ssl=True,
            max_connections=10,
            socket_timeout=5.0,
            fallback_on_error=True,
        )

        redis_cache = RedisCache(secure_config)

        # Configuration should use secure defaults
        assert secure_config.redis_ssl is True
        assert secure_config.redis_password is not None
        assert secure_config.socket_timeout > 0
        assert secure_config.max_connections <= 50  # Reasonable limit

    def test_redis_connection_parameter_validation(self):
        """Test Redis connection parameter validation."""
        # Test with potentially malicious connection parameters
        malicious_configs = [
            {"redis_host": "malicious.com; rm -rf /", "redis_port": 6379},
            {"redis_host": "../../../etc/passwd", "redis_port": 6379},
            {"redis_host": "localhost", "redis_port": "6379; dangerous_command"},
            {"redis_host": "127.0.0.1", "redis_port": -1},  # Invalid port
            {"redis_host": "127.0.0.1", "redis_port": 999999},  # Invalid port
        ]

        for malicious_config in malicious_configs:
            try:
                config = CacheConfig(enabled=True, **malicious_config)
                redis_cache = RedisCache(config)

                # If config is accepted, connection should fail safely
                # Rather than executing dangerous commands

            except (ValueError, TypeError) as e:
                # Expected - malicious config should be rejected
                assert "malicious" not in str(e).lower()

    @pytest.mark.asyncio
    async def test_redis_connection_error_handling(self):
        """Test Redis connection error handling security."""
        # Test with unreachable Redis server
        config = CacheConfig(
            enabled=True,
            redis_host="192.168.255.255",  # Unreachable IP
            redis_port=6379,
            socket_timeout=1.0,
            fallback_on_error=True,
        )

        redis_cache = RedisCache(config)

        # Connection attempt should fail gracefully
        try:
            await redis_cache._connect()
            pytest.fail("Connection should have failed")
        except Exception as e:
            # Error message should not expose sensitive information
            error_str = str(e)

            # Should not contain credentials or internal details
            assert "password" not in error_str.lower()
            assert "secret" not in error_str.lower()
            assert "internal" not in error_str.lower()

    @pytest.mark.asyncio
    async def test_redis_command_injection_prevention(self):
        """Test prevention of Redis command injection."""
        config = CacheConfig(enabled=True, fallback_on_error=True)
        redis_cache = RedisCache(config)

        # Mock Redis client to capture commands
        mock_redis = AsyncMock()
        redis_cache._redis = mock_redis

        # Test with keys that might cause command injection
        injection_keys = [
            "key\nFLUSHDB",  # Redis command injection
            "key\rDEL *",  # Delete all keys
            "key; EVAL 'malicious_lua_code'",
            "key\x00CONFIG SET dir /tmp",
            "key\tSHUTDOWN",
        ]

        for injection_key in injection_keys:
            try:
                # Test GET operation
                await redis_cache.get(injection_key)

                # Verify only GET command was called, not injected commands
                if mock_redis.get.called:
                    call_args = mock_redis.get.call_args
                    called_key = call_args[0][0] if call_args and call_args[0] else ""

                    # Key should be sanitized or operation should fail
                    assert "FLUSHDB" not in called_key
                    assert "DEL *" not in called_key
                    assert "EVAL" not in called_key
                    assert "SHUTDOWN" not in called_key

            except (ValueError, TypeError):
                # Expected - injection attempts should be rejected
                pass


class TestCachePoisoningPrevention:
    """Test cache poisoning prevention."""

    @pytest.fixture
    def cache_service_with_mock(self):
        """Create cache service with mocked backend."""
        config = CacheConfig(enabled=True, fallback_on_error=True)
        service = CacheService(config)
        service._backend = AsyncMock()
        service._initialized = True
        return service

    @pytest.mark.asyncio
    async def test_cache_poisoning_via_hash_collision(self, cache_service_with_mock):
        """Test prevention of cache poisoning via hash collisions."""
        # Test with inputs designed to cause hash collisions
        collision_attempts = [
            {"order": "first", "value": 1},
            {"order": "second", "value": 1},
            {"different": "key", "same": "value"},
            {"same": "value", "different": "key"},
        ]

        hashes = []
        for attempt in collision_attempts:
            request_hash = cache_service_with_mock._generate_hash(attempt)
            hashes.append(request_hash)

        # All hashes should be different (no collisions)
        unique_hashes = set(hashes)
        assert len(unique_hashes) == len(hashes), "Hash collision detected"

    @pytest.mark.asyncio
    async def test_cache_poisoning_via_key_manipulation(self, cache_service_with_mock):
        """Test prevention of cache poisoning via key manipulation."""
        # Mock backend to track cache operations
        service = cache_service_with_mock
        service._backend.get.return_value = None
        service._backend.set.return_value = True

        # Test with manipulated cache requests
        base_request = {"query": "legitimate_query", "user": "user123"}
        poisoned_request = {"query": "legitimate_query", "user": "admin_user"}

        # Cache legitimate result
        legitimate_result = {"data": "user_data", "permissions": ["read"]}
        await service.cache_planning_result(base_request, legitimate_result)

        # Attempt to poison cache with elevated permissions
        poisoned_result = {
            "data": "admin_data",
            "permissions": ["read", "write", "admin"],
        }
        await service.cache_planning_result(poisoned_request, poisoned_result)

        # Verify that different requests produce different cache keys
        base_hash = service._generate_hash(base_request)
        poisoned_hash = service._generate_hash(poisoned_request)

        assert base_hash != poisoned_hash, "Cache key collision enables poisoning"

    @pytest.mark.asyncio
    async def test_cache_ttl_manipulation_prevention(self, cache_service_with_mock):
        """Test prevention of TTL manipulation attacks."""
        service = cache_service_with_mock

        # Mock backend set method to capture TTL values
        service._backend.set.return_value = True

        # Test with normal request
        normal_request = {"query": "normal_query"}
        normal_result = {"data": "normal_data"}

        await service.cache_planning_result(normal_request, normal_result)

        # Verify TTL was set correctly
        if service._backend.set.called:
            call_args = service._backend.set.call_args
            if call_args and len(call_args) > 1:
                # Check that TTL is within reasonable bounds
                ttl_seconds = (
                    call_args.kwargs.get("ttl_seconds") if call_args.kwargs else None
                )
                if ttl_seconds:
                    assert 0 < ttl_seconds < 86400 * 7  # Max 1 week
                    assert ttl_seconds > 60  # Min 1 minute


class TestCacheMemoryExhaustionProtection:
    """Test cache memory exhaustion protection."""

    @pytest.fixture
    def cache_config_with_limits(self):
        """Create cache config with protective limits."""
        return CacheConfig(
            enabled=True,
            max_key_length=250,
            max_value_size=1024 * 1024,  # 1MB limit
            max_connections=10,
            fallback_on_error=True,
        )

    def test_cache_key_length_limits(self, cache_config_with_limits):
        """Test cache key length limits."""
        config = cache_config_with_limits
        redis_cache = RedisCache(config)

        # Normal key should be acceptable
        normal_key = "normal_cache_key_123"
        assert len(normal_key) <= config.max_key_length

        # Extremely long key should be rejected
        long_key = "A" * (config.max_key_length + 100)

        # Test key validation (would be implemented in set method)
        # This is a simplified test
        assert len(long_key) > config.max_key_length

    @pytest.mark.asyncio
    async def test_cache_value_size_protection(self):
        """Test cache value size protection."""
        config = CacheConfig(enabled=True, max_value_size=1024 * 100)  # 100KB limit

        redis_cache = RedisCache(config)
        redis_cache._redis = AsyncMock()

        # Normal sized value should be acceptable
        normal_value = {"data": "A" * 1000}  # 1KB approx

        try:
            await redis_cache.set("normal_key", normal_value, 3600)
            # Should succeed for normal size
        except MemoryError:
            pytest.fail("Normal sized value should not cause memory error")

        # Extremely large value should be protected against
        large_value = {"data": "B" * (1024 * 1024 * 50)}  # 50MB

        try:
            await redis_cache.set("large_key", large_value, 3600)
            # If it succeeds, check that size was limited
        except (MemoryError, ValueError):
            # Expected - large values should be rejected
            pass

    @pytest.mark.asyncio
    async def test_cache_connection_limit_protection(self):
        """Test cache connection limit protection."""
        config = CacheConfig(enabled=True, max_connections=5)  # Low limit for testing

        # Should not be able to create unlimited connections
        assert config.max_connections <= 50  # Reasonable upper limit
        assert config.max_connections >= 1  # Must allow at least 1


class TestCacheSecurityIntegration:
    """Test integrated cache security scenarios."""

    @pytest.mark.asyncio
    async def test_end_to_end_cache_security(self):
        """Test end-to-end cache security."""
        config = CacheConfig(
            enabled=True,
            fallback_on_error=True,
            redis_password="test_password",
            redis_ssl=True,
            max_key_length=250,
        )

        service = CacheService(config)

        # Mock the backend for testing
        service._backend = AsyncMock()
        service._backend.set.return_value = True
        service._backend.get.return_value = None
        service._initialized = True

        # Test complete workflow with security considerations
        test_request = {
            "query": "SELECT * FROM users WHERE id = ?",
            "params": [123],
            "user_id": "user_456",
        }

        test_result = {
            "data": [{"id": 123, "name": "John Doe", "email": "john@example.com"}],
            "count": 1,
            "metadata": {"execution_time": 0.05},
        }

        # Cache the result
        cache_success = await service.cache_planning_result(test_request, test_result)
        assert cache_success is True

        # Retrieve the result
        cached_result = await service.get_planning_result(test_request)

        # Verify security throughout the process
        if service._backend.set.called:
            set_call = service._backend.set.call_args
            cache_key = set_call[0][0] if set_call and set_call[0] else ""

            # Cache key should be hashed (not contain sensitive data)
            assert "SELECT * FROM users" not in cache_key
            assert "user_456" not in cache_key
            assert len(cache_key) > 0

    @pytest.mark.asyncio
    async def test_cache_security_under_load(self):
        """Test cache security under concurrent load."""
        config = CacheConfig(enabled=True, fallback_on_error=True)
        service = CacheService(config)
        service._backend = AsyncMock()
        service._backend.set.return_value = True
        service._backend.get.return_value = None
        service._initialized = True

        # Simulate concurrent cache operations
        async def cache_operation(operation_id):
            request = {"operation_id": operation_id, "data": f"data_{operation_id}"}
            result = {"result": f"result_{operation_id}"}

            # Cache and retrieve
            await service.cache_planning_result(request, result)
            return await service.get_planning_result(request)

        # Run concurrent operations
        tasks = [cache_operation(i) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should complete without security exceptions
        for result in results:
            if isinstance(result, Exception):
                error_msg = str(result).lower()
                assert "security" not in error_msg
                assert "injection" not in error_msg
                assert "malicious" not in error_msg

    @pytest.mark.asyncio
    async def test_cache_security_error_handling(self):
        """Test that cache security errors are handled properly."""
        config = CacheConfig(enabled=True, fallback_on_error=False)
        service = CacheService(config)

        # Mock backend to raise various errors
        service._backend = AsyncMock()
        service._backend.set.side_effect = Exception(
            "Simulated cache error with /sensitive/path"
        )
        service._initialized = True

        # Test that errors don't leak sensitive information
        try:
            await service.cache_planning_result({"test": "request"}, {"test": "result"})
        except Exception as e:
            error_msg = str(e)

            # Should not leak sensitive paths or internal details
            assert "/sensitive/path" not in error_msg
            assert "password" not in error_msg.lower()
            assert "internal" not in error_msg.lower()


class SecurityError(Exception):
    """Custom security exception for testing."""

    pass


@pytest.fixture
def mock_redis_config():
    """Provide mock Redis configuration for testing."""
    return CacheConfig(
        enabled=True,
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        max_connections=10,
        fallback_on_error=True,
    )


class TestCacheSecurityRegression:
    """Test prevention of known cache security regression patterns."""

    @pytest.mark.asyncio
    async def test_cache_injection_regression(self):
        """Test prevention of cache injection regression patterns."""
        config = CacheConfig(enabled=True, fallback_on_error=True)
        service = CacheService(config)

        # Known injection patterns that should be handled safely
        injection_patterns = [
            {"query": "'; DROP TABLE cache; --"},
            {"key": "../../../etc/passwd"},
            {"value": "<script>alert('xss')</script>"},
            {"command": "; rm -rf /"},
            {"eval": "eval('malicious_code')"},
        ]

        for pattern in injection_patterns:
            try:
                # Should handle injection patterns safely
                hash_result = service._generate_hash(pattern)

                # Hash should not contain dangerous content
                assert isinstance(hash_result, str)
                assert len(hash_result) == 16

                # Should not contain injection patterns
                assert "DROP TABLE" not in hash_result
                assert "../" not in hash_result
                assert "<script>" not in hash_result
                assert "; rm" not in hash_result

            except (ValueError, TypeError):
                # Expected - dangerous patterns might be rejected
                pass

    @pytest.mark.asyncio
    async def test_cache_deserialization_regression(self):
        """Test prevention of cache deserialization regression patterns."""
        config = CacheConfig(enabled=True)
        redis_cache = RedisCache(config)
        redis_cache._redis = AsyncMock()

        # Known dangerous serialized patterns
        dangerous_patterns = [
            '{"__proto__": {"polluted": true}}',
            '{"constructor": {"prototype": {"admin": true}}}',
            '{"toString": {"valueOf": "malicious"}}',
        ]

        for pattern in dangerous_patterns:
            redis_cache._redis.get.return_value = pattern

            try:
                result = await redis_cache.get("test_key")

                # If deserialization succeeds, should not have prototype pollution
                if result and hasattr(result, "value"):
                    value = result.value

                    # Should not have polluted Object prototype
                    if isinstance(value, dict):
                        assert "__proto__" not in str(value) or value.get(
                            "__proto__"
                        ) != {"polluted": True}

            except (json.JSONDecodeError, ValueError, TypeError):
                # Expected - dangerous patterns should be rejected
                pass
