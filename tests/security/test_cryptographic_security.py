"""Cryptographic Security Tests for khive services.

This module provides comprehensive security testing for cryptographic functions
and security mechanisms including:
- Hash function security and collision resistance
- UUID generation security and uniqueness
- Secure random number generation
- Key derivation and management security
- Digital signature validation
- Encryption/decryption security
- Timing attack prevention
- Cryptographic protocol security
"""

import hashlib
import secrets
import time
import uuid
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import UUID

import pytest

from khive.utils import sha256_of_dict, validate_uuid


class TestHashFunctionSecurity:
    """Test hash function security."""

    def test_sha256_of_dict_deterministic(self):
        """Test that sha256_of_dict produces consistent output."""
        # Test data
        test_dict = {
            "key1": "value1",
            "key2": "value2",
            "nested": {"inner_key": "inner_value"},
            "list": [1, 2, 3],
        }

        # Should produce same hash for same input
        hash1 = sha256_of_dict(test_dict)
        hash2 = sha256_of_dict(test_dict)

        assert hash1 == hash2, "Hash function should be deterministic"
        assert len(hash1) == 64, "SHA-256 hash should be 64 characters (hex)"
        assert all(
            c in "0123456789abcdef" for c in hash1.lower()
        ), "Hash should be valid hex"

    def test_sha256_of_dict_key_order_independence(self):
        """Test that key order doesn't affect hash output."""
        dict1 = {"a": 1, "b": 2, "c": 3}
        dict2 = {"c": 3, "a": 1, "b": 2}
        dict3 = {"b": 2, "c": 3, "a": 1}

        hash1 = sha256_of_dict(dict1)
        hash2 = sha256_of_dict(dict2)
        hash3 = sha256_of_dict(dict3)

        assert hash1 == hash2 == hash3, "Hash should be independent of key order"

    def test_sha256_of_dict_collision_resistance(self):
        """Test collision resistance of hash function."""
        # Generate many different dictionaries and check for collisions
        hashes = set()

        for i in range(1000):
            test_dict = {
                f"key_{i}": f"value_{i}",
                "counter": i,
                "data": list(range(i % 10)),
            }

            hash_value = sha256_of_dict(test_dict)

            # Should not have collisions for different inputs
            assert hash_value not in hashes, f"Hash collision detected for input {i}"
            hashes.add(hash_value)

    def test_sha256_of_dict_sensitivity(self):
        """Test sensitivity of hash to small changes."""
        base_dict = {"key": "value", "number": 42}

        # Small changes should produce very different hashes
        variations = [
            {"key": "value", "number": 43},  # Small number change
            {"key": "Value", "number": 42},  # Case change
            {"key": "value ", "number": 42},  # Trailing space
            {"key": "value", "number": 42, "extra": None},  # Extra key
            {"Key": "value", "number": 42},  # Key case change
        ]

        base_hash = sha256_of_dict(base_dict)

        for i, variant in enumerate(variations):
            variant_hash = sha256_of_dict(variant)

            assert (
                variant_hash != base_hash
            ), f"Variation {i} should produce different hash"

            # Check Hamming distance (different bits) is significant
            base_bits = bin(int(base_hash, 16))[2:].zfill(256)
            variant_bits = bin(int(variant_hash, 16))[2:].zfill(256)

            differences = sum(b1 != b2 for b1, b2 in zip(base_bits, variant_bits))
            # Should have roughly 50% different bits (avalanche effect)
            assert (
                differences > 100
            ), f"Insufficient avalanche effect: {differences} different bits"

    def test_hash_function_timing_attack_resistance(self):
        """Test that hash function timing is consistent."""
        # Test with different input sizes
        inputs = [
            {"small": "data"},
            {"medium": "x" * 1000},
            {"large": "y" * 10000},
            {"nested": {str(i): {"data": "z" * 100} for i in range(100)}},
        ]

        timings = []

        for test_input in inputs:
            start_time = time.perf_counter()
            for _ in range(100):  # Multiple iterations for better timing
                sha256_of_dict(test_input)
            end_time = time.perf_counter()

            avg_time = (end_time - start_time) / 100
            timings.append(avg_time)

        # Timing should not vary dramatically (basic timing attack resistance)
        max_time = max(timings)
        min_time = min(timings)

        # Should not have extreme timing variations
        timing_ratio = max_time / min_time if min_time > 0 else float("inf")
        assert timing_ratio < 100, f"Excessive timing variation: {timing_ratio}"

    @pytest.mark.parametrize(
        "malicious_input",
        [
            {"__proto__": {"malicious": True}},  # Prototype pollution attempt
            {b"binary_key": "value"},  # Binary key
            {"key": {"nested": {"deep": {"very_deep": "value"}}}},  # Deep nesting
            {"key\x00null": "value"},  # Null byte in key
            {"key\n\r\t": "value"},  # Control characters in key
            {" " * 1000: "value"},  # Very long key
            {"key": "value\x00\x01\x02"},  # Binary data in value
        ],
    )
    def test_hash_function_malicious_input_handling(self, malicious_input):
        """Test hash function handles malicious inputs safely."""
        try:
            hash_value = sha256_of_dict(malicious_input)

            # If successful, should produce valid hash
            assert isinstance(hash_value, str)
            assert len(hash_value) == 64
            assert all(c in "0123456789abcdef" for c in hash_value.lower())

        except (TypeError, ValueError, UnicodeError) as e:
            # Expected for some malicious inputs - should fail gracefully
            assert "malicious" not in str(e).lower()  # Should not expose intent


class TestUUIDSecurity:
    """Test UUID generation and validation security."""

    def test_uuid_validation_security(self):
        """Test UUID validation function security."""
        # Test valid UUIDs
        valid_uuids = [
            uuid.uuid4(),
            UUID("12345678-1234-5678-1234-567812345678"),
            "12345678-1234-5678-1234-567812345678",
            "{12345678-1234-5678-1234-567812345678}",
        ]

        for valid_uuid in valid_uuids:
            result = validate_uuid(valid_uuid)
            assert isinstance(result, UUID)

    @pytest.mark.parametrize(
        "invalid_uuid",
        [
            "not-a-uuid",
            "12345678-1234-5678-1234-56781234567g",  # Invalid character
            "12345678-1234-5678-1234-56781234567",  # Too short
            "12345678-1234-5678-1234-567812345678a",  # Too long
            "../../../etc/passwd",  # Path traversal
            "<script>alert('xss')</script>",  # XSS attempt
            "'; DROP TABLE users; --",  # SQL injection
            "\x00malicious",  # Null byte
            "",  # Empty string
            None,  # None value
            123,  # Integer
            [],  # List
            {},  # Dictionary
        ],
    )
    def test_uuid_validation_malicious_inputs(self, invalid_uuid):
        """Test UUID validation rejects malicious inputs."""
        with pytest.raises((ValueError, TypeError, AttributeError)):
            validate_uuid(invalid_uuid)

    def test_uuid_uniqueness(self):
        """Test UUID generation uniqueness."""
        # Generate many UUIDs and ensure uniqueness
        generated_uuids = set()

        for _ in range(10000):
            new_uuid = uuid.uuid4()

            # Should not have duplicates
            assert new_uuid not in generated_uuids, "UUID collision detected"
            generated_uuids.add(new_uuid)

    def test_uuid_randomness_quality(self):
        """Test quality of UUID randomness."""
        uuids = [uuid.uuid4() for _ in range(1000)]

        # Test that UUIDs have good distribution of bytes
        byte_counts = [0] * 256

        for test_uuid in uuids:
            uuid_bytes = test_uuid.bytes
            for byte_val in uuid_bytes:
                byte_counts[byte_val] += 1

        # Check that byte distribution is reasonably uniform
        total_bytes = len(uuids) * 16
        expected_per_byte = total_bytes / 256

        for i, count in enumerate(byte_counts):
            # Allow for some statistical variation
            assert (
                count > expected_per_byte * 0.5
            ), f"Byte {i} appears too rarely: {count}"
            assert (
                count < expected_per_byte * 2.0
            ), f"Byte {i} appears too frequently: {count}"

    def test_uuid_timing_attack_resistance(self):
        """Test UUID operations are resistant to timing attacks."""
        # Test UUID validation timing consistency
        valid_uuid_str = "12345678-1234-5678-1234-567812345678"
        invalid_uuid_str = "invalid-uuid-string-here-test"

        # Time valid UUID validation
        start_time = time.perf_counter()
        for _ in range(1000):
            try:
                validate_uuid(valid_uuid_str)
            except:
                pass
        valid_time = time.perf_counter() - start_time

        # Time invalid UUID validation
        start_time = time.perf_counter()
        for _ in range(1000):
            try:
                validate_uuid(invalid_uuid_str)
            except:
                pass
        invalid_time = time.perf_counter() - start_time

        # Timing should not reveal validity (basic timing attack resistance)
        if valid_time > 0 and invalid_time > 0:
            timing_ratio = max(valid_time, invalid_time) / min(valid_time, invalid_time)
            assert timing_ratio < 10, f"Timing attack vulnerability: {timing_ratio}"


class TestRandomNumberGeneration:
    """Test secure random number generation."""

    def test_secrets_module_availability(self):
        """Test that secure random module is available."""
        # Should be able to generate cryptographically secure random values
        random_bytes = secrets.token_bytes(32)
        random_hex = secrets.token_hex(32)
        random_url = secrets.token_urlsafe(32)

        assert len(random_bytes) == 32
        assert len(random_hex) == 64  # 32 bytes = 64 hex chars
        assert len(random_url) >= 32  # URL-safe can be slightly longer

    def test_random_quality(self):
        """Test quality of random number generation."""
        # Generate random values and test distribution
        random_values = [secrets.randbelow(256) for _ in range(10000)]

        # Count frequency of each value
        counts = [0] * 256
        for value in random_values:
            counts[value] += 1

        # Check reasonable distribution
        expected_per_value = len(random_values) / 256

        for i, count in enumerate(counts):
            # Allow for statistical variation
            assert (
                count > expected_per_value * 0.5
            ), f"Value {i} appears too rarely: {count}"
            assert (
                count < expected_per_value * 2.0
            ), f"Value {i} appears too frequently: {count}"

    def test_random_unpredictability(self):
        """Test unpredictability of random generation."""
        # Generate sequences and check for patterns
        sequences = []
        for _ in range(100):
            sequence = [secrets.randbelow(10) for _ in range(10)]
            sequences.append(tuple(sequence))

        # Should have very few or no duplicate sequences
        unique_sequences = set(sequences)
        duplicate_ratio = 1 - (len(unique_sequences) / len(sequences))

        assert duplicate_ratio < 0.1, f"Too many duplicate sequences: {duplicate_ratio}"

    def test_random_seed_independence(self):
        """Test that random generation is properly seeded."""
        # Multiple processes/calls should produce different values
        values1 = [secrets.randbelow(1000000) for _ in range(100)]
        values2 = [secrets.randbelow(1000000) for _ in range(100)]

        # Should have very few overlapping values
        overlaps = set(values1) & set(values2)
        overlap_ratio = len(overlaps) / len(values1)

        assert overlap_ratio < 0.1, f"Too many overlapping values: {overlap_ratio}"


class TestCryptographicProtocols:
    """Test cryptographic protocol security."""

    def test_hash_based_authentication(self):
        """Test hash-based authentication security."""

        # Simulate hash-based authentication
        def hash_password(password: str, salt: bytes) -> str:
            """Simulate secure password hashing."""
            return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000).hex()

        def verify_password(password: str, salt: bytes, expected_hash: str) -> bool:
            """Simulate password verification."""
            computed_hash = hash_password(password, salt)
            return computed_hash == expected_hash

        # Test secure password handling
        password = "secure_password_123"
        salt = secrets.token_bytes(32)

        password_hash = hash_password(password, salt)

        # Correct password should verify
        assert verify_password(password, salt, password_hash)

        # Wrong password should not verify
        assert not verify_password("wrong_password", salt, password_hash)

        # Different salt should not verify
        different_salt = secrets.token_bytes(32)
        assert not verify_password(password, different_salt, password_hash)

    def test_timing_attack_resistance_auth(self):
        """Test timing attack resistance in authentication."""

        def constant_time_compare(a: str, b: str) -> bool:
            """Simulate constant-time comparison."""
            if len(a) != len(b):
                return False
            result = 0
            for x, y in zip(a, b):
                result |= ord(x) ^ ord(y)
            return result == 0

        # Test with same length strings
        correct_hash = "a" * 64  # Simulate 64-char hash

        # Time correct comparison
        start_time = time.perf_counter()
        for _ in range(1000):
            constant_time_compare(correct_hash, correct_hash)
        correct_time = time.perf_counter() - start_time

        # Time incorrect comparison (same length)
        incorrect_hash = "b" * 64
        start_time = time.perf_counter()
        for _ in range(1000):
            constant_time_compare(correct_hash, incorrect_hash)
        incorrect_time = time.perf_counter() - start_time

        # Timing should be similar (constant-time)
        if correct_time > 0 and incorrect_time > 0:
            timing_ratio = max(correct_time, incorrect_time) / min(
                correct_time, incorrect_time
            )
            assert (
                timing_ratio < 2
            ), f"Potential timing attack vulnerability: {timing_ratio}"

    def test_secure_token_generation(self):
        """Test secure token generation patterns."""

        def generate_session_token() -> str:
            """Generate secure session token."""
            return secrets.token_urlsafe(32)

        def generate_api_key() -> str:
            """Generate secure API key."""
            return secrets.token_hex(32)

        def generate_csrf_token() -> str:
            """Generate CSRF token."""
            return secrets.token_urlsafe(24)

        # Test token generation
        session_token = generate_session_token()
        api_key = generate_api_key()
        csrf_token = generate_csrf_token()

        # Tokens should be different
        assert session_token != api_key
        assert session_token != csrf_token
        assert api_key != csrf_token

        # Tokens should have expected properties
        assert len(session_token) >= 32
        assert len(api_key) == 64  # 32 bytes = 64 hex chars
        assert len(csrf_token) >= 24

        # Tokens should be URL-safe where expected
        import string

        url_safe_chars = set(string.ascii_letters + string.digits + "-_")
        assert all(c in url_safe_chars for c in session_token)
        assert all(c in url_safe_chars for c in csrf_token)

    def test_key_derivation_security(self):
        """Test key derivation function security."""

        def derive_key(password: str, salt: bytes, info: bytes = b"") -> bytes:
            """Simulate key derivation."""
            # Use PBKDF2 for key derivation
            return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000, 32)

        password = "master_password"
        salt = secrets.token_bytes(16)

        # Same inputs should produce same key
        key1 = derive_key(password, salt)
        key2 = derive_key(password, salt)
        assert key1 == key2

        # Different passwords should produce different keys
        key3 = derive_key("different_password", salt)
        assert key1 != key3

        # Different salts should produce different keys
        different_salt = secrets.token_bytes(16)
        key4 = derive_key(password, different_salt)
        assert key1 != key4

        # Keys should be proper length
        assert len(key1) == 32


class TestCryptographicAttackPrevention:
    """Test prevention of cryptographic attacks."""

    def test_hash_collision_attack_prevention(self):
        """Test prevention of hash collision attacks."""
        # Test with inputs designed to find collisions (simplified)
        collision_attempts = [
            {"a": 1, "b": 2},
            {"a": "1", "b": "2"},  # Different types
            {"a": 1.0, "b": 2.0},  # Different types
            {1: "a", 2: "b"},  # Integer keys
            {"1": "a", "2": "b"},  # String keys
        ]

        hashes = []
        for attempt in collision_attempts:
            try:
                hash_value = sha256_of_dict(attempt)
                hashes.append(hash_value)
            except Exception:
                # Some attempts might fail due to type issues
                pass

        # Should not have collisions
        unique_hashes = set(hashes)
        assert len(unique_hashes) == len(hashes), "Hash collision detected"

    def test_length_extension_attack_prevention(self):
        """Test prevention of length extension attacks."""
        # Using SHA-256 should be resistant to length extension
        # Test that hash function doesn't expose internal state
        original_data = {"message": "original_message"}
        extended_data = {"message": "original_message", "extension": "malicious"}

        original_hash = sha256_of_dict(original_data)
        extended_hash = sha256_of_dict(extended_data)

        # Should not be able to predict extended hash from original
        assert original_hash != extended_hash
        assert not extended_hash.startswith(original_hash[:32])

    def test_rainbow_table_resistance(self):
        """Test resistance to rainbow table attacks."""
        # Test with common passwords that might be in rainbow tables
        common_passwords = [
            "password",
            "123456",
            "password123",
            "admin",
            "letmein",
            "welcome",
            "monkey",
            "1234567890",
            "qwerty",
            "abc123",
        ]

        # Hash with salt (simulated)
        for password in common_passwords:
            salt = secrets.token_bytes(16)
            # Simulate salted hashing
            salted_input = {"password": password, "salt": salt.hex()}
            hash_value = sha256_of_dict(salted_input)

            # Hash should be unique even for common passwords
            assert len(hash_value) == 64
            # Should not be predictable from password alone
            password_only_hash = sha256_of_dict({"password": password})
            assert hash_value != password_only_hash

    def test_birthday_attack_resistance(self):
        """Test resistance to birthday attacks."""
        # Generate many hashes and check collision probability
        hash_values = set()

        # For birthday attack, we need roughly sqrt(2^n) samples
        # For testing, use smaller sample size
        for i in range(1000):
            test_data = {"counter": i, "random": secrets.token_hex(16)}
            hash_value = sha256_of_dict(test_data)

            # Should not have collisions
            assert hash_value not in hash_values, f"Birthday collision at iteration {i}"
            hash_values.add(hash_value)

    @pytest.mark.parametrize(
        "weak_input",
        [
            {"": ""},  # Empty strings
            {"0": "0"},  # Simple values
            {"a": "a"},  # Identical key-value
            {str(i): str(i) for i in range(10)},  # Pattern
            {"null": None},  # Null values
            {"true": True, "false": False},  # Boolean values
        ],
    )
    def test_weak_input_handling(self, weak_input):
        """Test handling of weak inputs that might be vulnerable."""
        hash_value = sha256_of_dict(weak_input)

        # Should still produce valid hash
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value.lower())

        # Should not produce obviously weak hashes
        weak_patterns = ["0" * 64, "1" * 64, "f" * 64, "a" * 64]
        assert hash_value not in weak_patterns


class TestKeyManagementSecurity:
    """Test key management security."""

    def test_key_generation_security(self):
        """Test secure key generation."""
        # Generate encryption keys
        aes_key = secrets.token_bytes(32)  # 256-bit AES key
        hmac_key = secrets.token_bytes(32)  # HMAC key

        # Keys should be different
        assert aes_key != hmac_key

        # Keys should be proper length
        assert len(aes_key) == 32
        assert len(hmac_key) == 32

        # Keys should have good entropy
        # Check for all zeros or all same byte
        assert not all(b == 0 for b in aes_key)
        assert not all(b == aes_key[0] for b in aes_key)
        assert not all(b == 0 for b in hmac_key)
        assert not all(b == hmac_key[0] for b in hmac_key)

    def test_key_derivation_parameters(self):
        """Test key derivation parameters are secure."""
        # Test PBKDF2 parameters
        password = "test_password"
        salt = secrets.token_bytes(16)

        # Test iteration count is sufficient
        iterations = 100000  # Should be high enough for security
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations, 32)

        assert len(key) == 32

        # Different iteration counts should produce different keys
        key_low_iter = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 1000, 32)
        assert key != key_low_iter

        # Test that salt is properly used
        key_no_salt = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), b"", iterations, 32
        )
        assert key != key_no_salt

    def test_key_storage_security(self):
        """Test secure key storage patterns."""

        # Simulate secure key storage
        def store_key_securely(key: bytes) -> str:
            """Simulate secure key storage (base64 for transport)."""
            import base64

            return base64.b64encode(key).decode("ascii")

        def retrieve_key_securely(stored_key: str) -> bytes:
            """Simulate secure key retrieval."""
            import base64

            return base64.b64decode(stored_key.encode("ascii"))

        original_key = secrets.token_bytes(32)
        stored_key = store_key_securely(original_key)
        retrieved_key = retrieve_key_securely(stored_key)

        assert original_key == retrieved_key

        # Stored format should be base64
        import base64

        try:
            base64.b64decode(stored_key)
        except Exception:
            pytest.fail("Stored key is not valid base64")

    def test_key_rotation_security(self):
        """Test key rotation patterns."""
        # Simulate key rotation
        current_key = secrets.token_bytes(32)
        old_keys = []

        # Rotate keys
        for _ in range(5):
            old_keys.append(current_key)
            current_key = secrets.token_bytes(32)

        # All keys should be different
        all_keys = old_keys + [current_key]
        unique_keys = set(all_keys)

        assert len(unique_keys) == len(all_keys), "Key rotation produced duplicate keys"


class TestCryptographicIntegration:
    """Test integrated cryptographic scenarios."""

    def test_secure_session_management(self):
        """Test secure session management using cryptographic primitives."""

        def create_secure_session():
            return {
                "session_id": secrets.token_urlsafe(32),
                "csrf_token": secrets.token_urlsafe(24),
                "created_at": time.time(),
                "user_id": secrets.randbelow(1000000),
            }

        def validate_session(session):
            # Validate session structure and values
            required_fields = ["session_id", "csrf_token", "created_at", "user_id"]
            return all(field in session for field in required_fields)

        # Create multiple sessions
        sessions = [create_secure_session() for _ in range(10)]

        # All sessions should be valid
        assert all(validate_session(session) for session in sessions)

        # All session IDs should be unique
        session_ids = [s["session_id"] for s in sessions]
        assert len(set(session_ids)) == len(session_ids)

        # All CSRF tokens should be unique
        csrf_tokens = [s["csrf_token"] for s in sessions]
        assert len(set(csrf_tokens)) == len(csrf_tokens)

    def test_secure_data_integrity(self):
        """Test data integrity using cryptographic hashes."""
        test_data = {
            "sensitive_info": "confidential_data",
            "user_id": 12345,
            "timestamp": time.time(),
        }

        # Calculate integrity hash
        integrity_hash = sha256_of_dict(test_data)

        # Verify integrity
        verification_hash = sha256_of_dict(test_data)
        assert integrity_hash == verification_hash, "Data integrity verification failed"

        # Test that tampering is detected
        tampered_data = test_data.copy()
        tampered_data["sensitive_info"] = "modified_data"
        tampered_hash = sha256_of_dict(tampered_data)

        assert integrity_hash != tampered_hash, "Tampering not detected"

    def test_cryptographic_regression_prevention(self):
        """Test prevention of known cryptographic vulnerabilities."""
        # Test against known weak patterns
        regression_tests = [
            {
                "name": "weak_random",
                "test": lambda: secrets.randbelow(2**32) != secrets.randbelow(2**32),
                "description": "Random values should be different",
            },
            {
                "name": "hash_consistency",
                "test": lambda: sha256_of_dict({"test": "data"})
                == sha256_of_dict({"test": "data"}),
                "description": "Hash should be consistent",
            },
            {
                "name": "uuid_uniqueness",
                "test": lambda: uuid.uuid4() != uuid.uuid4(),
                "description": "UUIDs should be unique",
            },
        ]

        for test_case in regression_tests:
            try:
                assert test_case[
                    "test"
                ](), f"Regression test failed: {test_case['name']} - {test_case['description']}"
            except Exception as e:
                pytest.fail(
                    f"Cryptographic regression detected in {test_case['name']}: {e}"
                )


@pytest.fixture
def secure_random_seed():
    """Ensure tests use secure randomness."""
    # Note: secrets module uses OS random, no seeding needed
    yield


@pytest.fixture
def mock_weak_random():
    """Mock weak random for testing attack scenarios."""

    class WeakRandom:
        def __init__(self):
            self.counter = 0

        def randint(self, a, b):
            # Predictable sequence for testing
            self.counter += 1
            return (self.counter % (b - a + 1)) + a

        def random(self):
            self.counter += 1
            return (self.counter % 1000) / 1000.0

    return WeakRandom()


class TestCryptographicEdgeCases:
    """Test edge cases in cryptographic functions."""

    def test_empty_input_handling(self):
        """Test handling of empty inputs."""
        # Empty dictionary
        empty_hash = sha256_of_dict({})
        assert len(empty_hash) == 64
        assert all(c in "0123456789abcdef" for c in empty_hash.lower())

        # Should be consistent
        assert empty_hash == sha256_of_dict({})

    def test_large_input_handling(self):
        """Test handling of large inputs."""
        # Large dictionary
        large_dict = {f"key_{i}": f"value_{i}" * 1000 for i in range(100)}

        start_time = time.time()
        large_hash = sha256_of_dict(large_dict)
        end_time = time.time()

        # Should complete in reasonable time
        assert end_time - start_time < 5.0, "Large input processing too slow"

        # Should produce valid hash
        assert len(large_hash) == 64
        assert all(c in "0123456789abcdef" for c in large_hash.lower())

    def test_unicode_input_handling(self):
        """Test handling of Unicode inputs."""
        unicode_dict = {
            "english": "Hello World",
            "chinese": "你好世界",
            "arabic": "مرحبا بالعالم",
            "emoji": "🔐🔑🛡️",
            "mixed": "Hello 你好 🌍",
        }

        unicode_hash = sha256_of_dict(unicode_dict)

        # Should produce valid hash
        assert len(unicode_hash) == 64
        assert all(c in "0123456789abcdef" for c in unicode_hash.lower())

        # Should be consistent
        assert unicode_hash == sha256_of_dict(unicode_dict)


class SecurityError(Exception):
    """Custom security exception for testing."""

    pass
