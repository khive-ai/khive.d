"""Comprehensive validation tests for Cache Service models.

This module provides systematic validation testing for:
- CacheEntry model validation and Redis serialization
- CacheStats model validation and metrics consistency
- CacheKey utility validation and format consistency
- Cache expiration logic validation
- Cross-model cache consistency validation
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from khive.services.cache.models import CacheEntry, CacheKey, CacheStats
from tests.validation.pydantic_validators import BaseValidationPattern

# ============================================================================
# CacheEntry Model Validation
# ============================================================================


class CacheEntryValidator(BaseValidationPattern):
    """Validation patterns for CacheEntry model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid CacheEntry data."""
        data = {
            "key": "khive:plan:hash:abc123",
            "value": {"result": "success", "data": [1, 2, 3]},
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "metadata": {"source": "planning_service", "version": "1.0"},
            "version": "1.0",
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        required_fields = ["key", "value"]

        for field in required_fields:
            incomplete_data = cls.create_valid_data()
            del incomplete_data[field]
            cls.assert_invalid_model(CacheEntry, incomplete_data, field)

    @classmethod
    def test_optional_fields_defaults(cls):
        """Test optional field defaults."""
        minimal_data = {"key": "test:key:123", "value": {"test": "data"}}

        entry = cls.assert_valid_model(CacheEntry, minimal_data)

        # Check defaults
        assert entry.created_at is not None
        assert entry.expires_at is None
        assert entry.metadata == {}
        assert entry.version == "1.0"

    @classmethod
    def test_key_validation(cls):
        """Test cache key validation."""
        # Valid keys
        valid_keys = [
            "khive:plan:hash:abc123",
            "khive:triage:hash:def456",
            "khive:complexity:hash:ghi789",
            "khive:meta:stats",
            "custom:key:format",
            "simple_key",
            "key-with-dashes",
            "key_with_underscores",
        ]

        for key in valid_keys:
            data = cls.create_valid_data(key=key)
            cls.assert_valid_model(CacheEntry, data)

        # Empty key should be invalid
        cls.assert_invalid_model(CacheEntry, cls.create_valid_data(key=""), "key")

    @classmethod
    def test_value_validation(cls):
        """Test cache value validation."""
        # Various value types
        valid_values = [
            "string_value",
            123,
            123.45,
            True,
            False,
            None,
            [],
            {},
            [1, 2, 3],
            {"key": "value", "nested": {"data": True}},
            {"complex": [{"nested": "structure"}]},
        ]

        for value in valid_values:
            data = cls.create_valid_data(value=value)
            cls.assert_valid_model(CacheEntry, data)

    @classmethod
    def test_expiration_validation(cls):
        """Test expiration datetime validation."""
        now = datetime.now(timezone.utc)

        # Valid expiration times
        valid_expirations = [
            None,  # no expiration
            now + timedelta(seconds=30),  # 30 seconds
            now + timedelta(minutes=5),  # 5 minutes
            now + timedelta(hours=1),  # 1 hour
            now + timedelta(days=1),  # 1 day
            now + timedelta(days=365),  # 1 year
        ]

        for expires_at in valid_expirations:
            data = cls.create_valid_data(expires_at=expires_at)
            cls.assert_valid_model(CacheEntry, data)

    @classmethod
    def test_metadata_validation(cls):
        """Test metadata field validation."""
        # Various metadata formats
        valid_metadata = [
            {},
            {"source": "planning"},
            {"priority": "high", "retry_count": 3},
            {"tags": ["cache", "planning"], "nested": {"info": "value"}},
            {"timestamp": "2024-01-01T00:00:00Z"},
        ]

        for metadata in valid_metadata:
            data = cls.create_valid_data(metadata=metadata)
            cls.assert_valid_model(CacheEntry, data)

    @classmethod
    def test_version_validation(cls):
        """Test version field validation."""
        # Valid versions
        valid_versions = [
            "1.0",
            "2.1.0",
            "1.0-beta",
            "v1.2.3",
            "latest",
        ]

        for version in valid_versions:
            data = cls.create_valid_data(version=version)
            cls.assert_valid_model(CacheEntry, data)

        # Empty version should use default
        data_no_version = cls.create_valid_data()
        del data_no_version["version"]
        entry = cls.assert_valid_model(CacheEntry, data_no_version)
        assert entry.version == "1.0"

    @classmethod
    def test_is_expired_method(cls):
        """Test is_expired method logic."""
        now = datetime.now(timezone.utc)

        # Never expires (None)
        never_expires = CacheEntry(key="test:key", value="test", expires_at=None)
        assert not never_expires.is_expired()

        # Future expiration (not expired)
        future_expires = CacheEntry(
            key="test:key", value="test", expires_at=now + timedelta(hours=1)
        )
        assert not future_expires.is_expired()

        # Past expiration (expired)
        past_expires = CacheEntry(
            key="test:key", value="test", expires_at=now - timedelta(hours=1)
        )
        assert past_expires.is_expired()

    @classmethod
    def test_redis_serialization(cls):
        """Test Redis serialization/deserialization."""
        # Create test entry
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=1)

        original_entry = CacheEntry(
            key="test:serialization:key",
            value={"complex": "data", "numbers": [1, 2, 3]},
            created_at=now,
            expires_at=expires_at,
            metadata={"source": "test", "priority": "high"},
            version="2.0",
        )

        # Serialize to Redis format
        redis_value = original_entry.to_redis_value()
        assert isinstance(redis_value, str)

        # Should be valid JSON
        parsed_json = json.loads(redis_value)
        assert "key" in parsed_json
        assert "value" in parsed_json
        assert "created_at" in parsed_json

        # Deserialize back
        deserialized_entry = CacheEntry.from_redis_value(
            original_entry.key, redis_value
        )

        # Verify all fields match
        assert deserialized_entry.key == original_entry.key
        assert deserialized_entry.value == original_entry.value
        assert deserialized_entry.metadata == original_entry.metadata
        assert deserialized_entry.version == original_entry.version

        # Timestamps should be equal (within precision)
        assert (
            abs(
                (
                    deserialized_entry.created_at - original_entry.created_at
                ).total_seconds()
            )
            < 0.001
        )
        if expires_at:
            assert (
                abs(
                    (
                        deserialized_entry.expires_at - original_entry.expires_at
                    ).total_seconds()
                )
                < 0.001
            )

    @classmethod
    def test_redis_serialization_edge_cases(cls):
        """Test Redis serialization with edge cases."""
        # Entry without expiration
        no_expire_entry = CacheEntry(
            key="test:no_expire", value="simple_value", expires_at=None
        )

        redis_value = no_expire_entry.to_redis_value()
        deserialized = CacheEntry.from_redis_value(no_expire_entry.key, redis_value)

        assert deserialized.expires_at is None
        assert deserialized.value == "simple_value"

        # Entry with None value
        none_value_entry = CacheEntry(key="test:none_value", value=None)

        redis_value = none_value_entry.to_redis_value()
        deserialized = CacheEntry.from_redis_value(none_value_entry.key, redis_value)

        assert deserialized.value is None

        # Entry with empty metadata
        empty_meta_entry = CacheEntry(key="test:empty_meta", value="test", metadata={})

        redis_value = empty_meta_entry.to_redis_value()
        deserialized = CacheEntry.from_redis_value(empty_meta_entry.key, redis_value)

        assert deserialized.metadata == {}


# ============================================================================
# CacheStats Model Validation
# ============================================================================


class CacheStatsValidator(BaseValidationPattern):
    """Validation patterns for CacheStats model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid CacheStats data."""
        data = {
            "total_keys": 100,
            "hits": 75,
            "misses": 25,
            "evictions": 5,
            "memory_usage_bytes": 1048576,  # 1MB
            "hit_rate": 0.75,
        }
        data.update(overrides)
        return data

    @classmethod
    def test_field_defaults(cls):
        """Test field default values."""
        minimal_stats = CacheStats()

        assert minimal_stats.total_keys == 0
        assert minimal_stats.hits == 0
        assert minimal_stats.misses == 0
        assert minimal_stats.evictions == 0
        assert minimal_stats.memory_usage_bytes is None
        assert minimal_stats.hit_rate == 0.0

    @classmethod
    def test_integer_field_constraints(cls):
        """Test integer field constraints."""
        # Valid positive integers
        valid_values = [0, 1, 100, 10000, 1000000]
        integer_fields = ["total_keys", "hits", "misses", "evictions"]

        for field in integer_fields:
            for value in valid_values:
                data = cls.create_valid_data(**{field: value})
                cls.assert_valid_model(CacheStats, data)

        # Invalid negative integers
        invalid_values = [-1, -10, -100]
        for field in integer_fields:
            for value in invalid_values:
                data = cls.create_valid_data(**{field: value})
                cls.assert_invalid_model(CacheStats, data, field)

    @classmethod
    def test_memory_usage_validation(cls):
        """Test memory usage field validation."""
        # Valid memory values
        valid_memory = [None, 0, 1024, 1048576, 1073741824]  # None, 0, 1KB, 1MB, 1GB

        for memory in valid_memory:
            data = cls.create_valid_data(memory_usage_bytes=memory)
            cls.assert_valid_model(CacheStats, data)

        # Invalid negative memory
        invalid_memory = [-1, -1024]
        for memory in invalid_memory:
            data = cls.create_valid_data(memory_usage_bytes=memory)
            cls.assert_invalid_model(CacheStats, data, "memory_usage_bytes")

    @classmethod
    def test_hit_rate_constraints(cls):
        """Test hit rate field constraints."""
        # Valid hit rates (0.0 to 1.0)
        valid_rates = [0.0, 0.25, 0.5, 0.75, 1.0]

        for rate in valid_rates:
            data = cls.create_valid_data(hit_rate=rate)
            cls.assert_valid_model(CacheStats, data)

        # Invalid hit rates (outside 0.0-1.0 range)
        invalid_rates = [-0.1, -1.0, 1.1, 2.0]
        for rate in invalid_rates:
            data = cls.create_valid_data(hit_rate=rate)
            cls.assert_invalid_model(CacheStats, data, "hit_rate")

    @classmethod
    def test_calculate_hit_rate_method(cls):
        """Test calculate_hit_rate method logic."""
        # Normal case
        stats = CacheStats(hits=75, misses=25)
        calculated_rate = stats.calculate_hit_rate()

        assert calculated_rate == 0.75
        assert stats.hit_rate == 0.75

        # Perfect hit rate
        perfect_stats = CacheStats(hits=100, misses=0)
        perfect_rate = perfect_stats.calculate_hit_rate()

        assert perfect_rate == 1.0
        assert perfect_stats.hit_rate == 1.0

        # Zero hit rate
        zero_stats = CacheStats(hits=0, misses=100)
        zero_rate = zero_stats.calculate_hit_rate()

        assert zero_rate == 0.0
        assert zero_stats.hit_rate == 0.0

        # No requests (edge case)
        no_requests_stats = CacheStats(hits=0, misses=0)
        no_requests_rate = no_requests_stats.calculate_hit_rate()

        assert no_requests_rate == 0.0
        assert no_requests_stats.hit_rate == 0.0

    @classmethod
    def test_stats_consistency_validation(cls):
        """Test internal consistency of stats."""
        # Consistent stats
        consistent_stats = CacheStats(total_keys=50, hits=75, misses=25, hit_rate=0.75)

        # Should validate at model level
        cls.assert_valid_model(
            CacheStats, {"total_keys": 50, "hits": 75, "misses": 25, "hit_rate": 0.75}
        )

        # Verify calculated rate matches
        calculated_rate = consistent_stats.calculate_hit_rate()
        assert abs(calculated_rate - 0.75) < 0.001


# ============================================================================
# CacheKey Utility Validation
# ============================================================================


class CacheKeyValidator:
    """Validation patterns for CacheKey utility class."""

    @staticmethod
    def test_key_format_consistency():
        """Test cache key format consistency."""
        # Test all key generation methods
        request_hash = "abc123def456"

        planning_key = CacheKey.planning_result(request_hash)
        triage_key = CacheKey.triage_result(request_hash)
        complexity_key = CacheKey.complexity_assessment(request_hash)
        stats_key = CacheKey.stats()
        config_key = CacheKey.config()

        # Check format patterns
        assert planning_key == f"khive:plan:hash:{request_hash}"
        assert triage_key == f"khive:triage:hash:{request_hash}"
        assert complexity_key == f"khive:complexity:hash:{request_hash}"
        assert stats_key == "khive:meta:stats"
        assert config_key == "khive:meta:config"

        # All keys should start with khive:
        keys = [planning_key, triage_key, complexity_key, stats_key, config_key]
        for key in keys:
            assert key.startswith("khive:")
            assert len(key) > 6  # Minimum reasonable length
            assert ":" in key  # Should contain separators

    @staticmethod
    def test_key_uniqueness():
        """Test that different inputs generate unique keys."""
        hash1 = "hash1"
        hash2 = "hash2"

        planning_key1 = CacheKey.planning_result(hash1)
        planning_key2 = CacheKey.planning_result(hash2)
        triage_key1 = CacheKey.triage_result(hash1)

        # Different hashes should generate different keys
        assert planning_key1 != planning_key2

        # Different key types should be different even with same hash
        assert planning_key1 != triage_key1

        # Same input should generate same key
        assert planning_key1 == CacheKey.planning_result(hash1)

    @staticmethod
    def test_key_edge_cases():
        """Test cache key generation with edge cases."""
        # Empty hash
        empty_key = CacheKey.planning_result("")
        assert empty_key == "khive:plan:hash:"

        # Special characters in hash
        special_hash = "abc-123_def.456"
        special_key = CacheKey.complexity_assessment(special_hash)
        assert special_key == f"khive:complexity:hash:{special_hash}"

        # Long hash
        long_hash = "x" * 1000
        long_key = CacheKey.triage_result(long_hash)
        assert long_key == f"khive:triage:hash:{long_hash}"
        assert len(long_key) > 1000

    @staticmethod
    def test_meta_key_consistency():
        """Test meta keys are consistent."""
        # Meta keys should always be the same
        stats_key1 = CacheKey.stats()
        stats_key2 = CacheKey.stats()
        config_key1 = CacheKey.config()
        config_key2 = CacheKey.config()

        assert stats_key1 == stats_key2
        assert config_key1 == config_key2
        assert stats_key1 != config_key1


# ============================================================================
# Cross-Model Cache Validation Patterns
# ============================================================================


class CacheServiceCrossValidator:
    """Cross-model validation patterns for Cache Service."""

    @staticmethod
    def validate_entry_stats_consistency(
        entries: list[CacheEntry], stats: CacheStats
    ) -> list[str]:
        """Validate consistency between cache entries and stats."""
        issues = []

        # Count active (non-expired) entries
        now = datetime.now(timezone.utc)
        active_entries = [entry for entry in entries if not entry.is_expired()]

        # Total keys should match active entries
        if stats.total_keys != len(active_entries):
            issues.append(
                f"Stats total_keys ({stats.total_keys}) doesn't match "
                f"active entries count ({len(active_entries)})"
            )

        # Hit rate should be within valid range
        if not (0.0 <= stats.hit_rate <= 1.0):
            issues.append(f"Invalid hit rate: {stats.hit_rate}")

        # Calculated hit rate should match stored hit rate
        total_requests = stats.hits + stats.misses
        if total_requests > 0:
            expected_rate = stats.hits / total_requests
            if abs(stats.hit_rate - expected_rate) > 0.001:
                issues.append(
                    f"Hit rate {stats.hit_rate} doesn't match calculated "
                    f"rate {expected_rate}"
                )

        return issues

    @staticmethod
    def validate_cache_key_entry_consistency(
        cache_key: str, entry: CacheEntry
    ) -> list[str]:
        """Validate consistency between cache key and entry."""
        issues = []

        # Entry key should match provided key
        if entry.key != cache_key:
            issues.append(
                f"Entry key '{entry.key}' doesn't match cache key '{cache_key}'"
            )

        # Key should follow khive format for khive keys
        if cache_key.startswith("khive:"):
            if not entry.key.startswith("khive:"):
                issues.append("Khive key format inconsistent in entry")

            # Should have proper structure
            key_parts = entry.key.split(":")
            if len(key_parts) < 3:
                issues.append("Khive key doesn't have enough parts")

        return issues

    @staticmethod
    def validate_expiration_consistency(entries: list[CacheEntry]) -> list[str]:
        """Validate expiration logic consistency across entries."""
        issues = []

        now = datetime.now(timezone.utc)

        for entry in entries:
            # Expired entries should be identified correctly
            if entry.expires_at is not None:
                is_expired_method = entry.is_expired()
                is_expired_calc = now > entry.expires_at

                if is_expired_method != is_expired_calc:
                    issues.append(
                        f"Entry {entry.key}: is_expired() method inconsistent "
                        f"with manual calculation"
                    )

            # Creation time should be before expiration time
            if entry.expires_at is not None:
                if entry.created_at > entry.expires_at:
                    issues.append(f"Entry {entry.key}: created after expiration time")

        return issues


# ============================================================================
# Comprehensive Test Suite
# ============================================================================


class TestCacheValidation:
    """Test class to run all Cache Service validation tests."""

    def test_cache_entry_validation(self):
        """Test CacheEntry model validation."""
        CacheEntryValidator.test_required_fields()
        CacheEntryValidator.test_optional_fields_defaults()
        CacheEntryValidator.test_key_validation()
        CacheEntryValidator.test_value_validation()
        CacheEntryValidator.test_expiration_validation()
        CacheEntryValidator.test_metadata_validation()
        CacheEntryValidator.test_version_validation()
        CacheEntryValidator.test_is_expired_method()
        CacheEntryValidator.test_redis_serialization()
        CacheEntryValidator.test_redis_serialization_edge_cases()

    def test_cache_stats_validation(self):
        """Test CacheStats model validation."""
        CacheStatsValidator.test_field_defaults()
        CacheStatsValidator.test_integer_field_constraints()
        CacheStatsValidator.test_memory_usage_validation()
        CacheStatsValidator.test_hit_rate_constraints()
        CacheStatsValidator.test_calculate_hit_rate_method()
        CacheStatsValidator.test_stats_consistency_validation()

    def test_cache_key_validation(self):
        """Test CacheKey utility validation."""
        CacheKeyValidator.test_key_format_consistency()
        CacheKeyValidator.test_key_uniqueness()
        CacheKeyValidator.test_key_edge_cases()
        CacheKeyValidator.test_meta_key_consistency()

    def test_cross_model_validation(self):
        """Test cross-model validation patterns."""
        # Create test data
        now = datetime.now(timezone.utc)

        entries = [
            CacheEntry(
                key="khive:plan:hash:test1",
                value={"result": "success"},
                created_at=now,
                expires_at=now + timedelta(hours=1),
            ),
            CacheEntry(
                key="khive:triage:hash:test2",
                value={"result": "success"},
                created_at=now,
                expires_at=now - timedelta(hours=1),  # expired
            ),
        ]

        stats = CacheStats(
            total_keys=1,
            hits=80,
            misses=20,
            hit_rate=0.8,  # Only count non-expired
        )

        # Run cross-model validations
        entry_stats_issues = (
            CacheServiceCrossValidator.validate_entry_stats_consistency(entries, stats)
        )

        key_entry_issues = (
            CacheServiceCrossValidator.validate_cache_key_entry_consistency(
                "khive:plan:hash:test1", entries[0]
            )
        )

        expiration_issues = CacheServiceCrossValidator.validate_expiration_consistency(
            entries
        )

        # Should have no issues for valid models
        assert len(entry_stats_issues) == 0
        assert len(key_entry_issues) == 0
        assert len(expiration_issues) == 0


if __name__ == "__main__":
    # Manual test runner
    test_suite = TestCacheValidation()

    try:
        test_suite.test_cache_entry_validation()
        test_suite.test_cache_stats_validation()
        test_suite.test_cache_key_validation()
        test_suite.test_cross_model_validation()

        print("✅ All Cache Service validation tests passed!")

    except Exception as e:
        print(f"❌ Cache validation test failed: {e}")
        raise
