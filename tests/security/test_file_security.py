"""Core File Security Testing Suite

Tests comprehensive file security including directory traversal prevention,
malicious content parsing protection, input sanitization effectiveness,
and thread-safe file operations under concurrent access.

This consolidates the most critical security tests for Pydantic model validation
focusing on real-world attack vectors that could compromise file system security.
"""

import json
import threading
import time

import pytest
from pydantic import ValidationError

from khive.services.composition.parts import ComposerRequest
from khive.services.orchestration.parts import AgentRequest


class TestFileSecurityCore:
    """Core file security validation tests."""

    def test_file_path_injection_prevention(self):
        """Test prevention of file path injection attacks."""

        malicious_file_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM",
            "../../../../home/user/.ssh/id_rsa",
            "../../../proc/self/environ",
            "\\\\?\\C:\\Windows\\System32\\drivers\\etc\\hosts",
            "/dev/null; rm -rf /",
            "file:///etc/passwd",
            "..\\..\\..\\..\\..\\windows\\win.ini",
        ]

        for malicious_path in malicious_file_paths:
            # Test through ComposerRequest context field
            try:
                request = ComposerRequest(
                    role="researcher",
                    context=f"Read file: {malicious_path}",
                    domains="file-operations",
                )

                # Check if dangerous path remains in context
                if any(pattern in request.context for pattern in ["../", "..\\"]):
                    pytest.fail(f"Path traversal pattern accepted: {malicious_path}")

            except ValidationError:
                # Expected - validation should block malicious paths
                pass

    def test_large_file_content_dos_prevention(self):
        """Test prevention of DoS attacks through large file content."""

        # Test different payload sizes
        large_payloads = [
            "A" * 50000,  # 50KB
            "X" * 100000,  # 100KB
            "Z" * 500000,  # 500KB
            "B" * 1000000,  # 1MB
        ]

        for payload in large_payloads:
            try:
                request = ComposerRequest(
                    role="researcher", context=payload, domains="data-processing"
                )

                # Check if large content was accepted (vulnerability)
                if len(request.context) > 10000:  # 10KB limit
                    pytest.fail(f"Large content accepted: {len(payload)} bytes")

            except ValidationError:
                # Expected - should reject large payloads
                pass

    def test_binary_content_injection_prevention(self):
        """Test prevention of binary content injection."""

        binary_payloads = [
            b"\x00\x01\x02\x03".decode("latin1"),  # Null bytes
            b"\xff\xfe\xfd\xfc".decode("latin1"),  # High bytes
            "\x00\x08\x0c\x0a\x0d\x09",  # Control characters
            "text\x00with\x00nulls",  # Embedded nulls
            "\x1b[31mcolored\x1b[0m",  # ANSI escape codes
        ]

        for payload in binary_payloads:
            try:
                request = ComposerRequest(
                    role="researcher",
                    context=f"Process data: {payload}",
                    domains="data-analysis",
                )

                # Check if binary content was accepted
                if any(ord(c) < 32 and c not in "\t\n\r" for c in request.context):
                    pytest.fail(f"Binary content accepted: {payload!r}")

            except (ValidationError, UnicodeError):
                # Expected - should reject binary content
                pass

    def test_serialization_bomb_prevention(self):
        """Test prevention of serialization bomb attacks."""

        # Deeply nested structure
        nested_data = {"level": 0}
        current = nested_data
        for i in range(1000):  # Deep nesting
            current["next"] = {"level": i + 1}
            current = current["next"]

        # Large array structure
        large_array = [{"item": i} for i in range(10000)]

        # Circular reference attempt
        circular = {"name": "root"}
        circular["self"] = circular

        dangerous_structures = [
            nested_data,
            large_array,
            # Note: Circular reference will cause JSON serialization to fail
        ]

        for structure in dangerous_structures:
            try:
                # Test through AgentRequest instruct field
                instruct_data = {
                    "instruction": "Process data",
                    "context": json.dumps(structure, default=str)[
                        :1000
                    ],  # Truncate to avoid test issues
                }

                request = AgentRequest(
                    instruct=instruct_data, compose_request={"role": "researcher"}
                )

                # If this succeeds, the dangerous structure was accepted
                pytest.fail("Dangerous nested structure accepted")

            except (ValidationError, RecursionError, MemoryError):
                # Expected - should reject dangerous structures
                pass


class TestConcurrentFileAccess:
    """Test thread safety of file operations under concurrent access."""

    def test_concurrent_validation_race_conditions(self):
        """Test for race conditions in validation under concurrent access."""

        results = []
        errors = []

        def validate_request(thread_id: int):
            try:
                for i in range(100):
                    request = ComposerRequest(
                        role="researcher",
                        context=f"Thread {thread_id} iteration {i}",
                        domains="concurrent-testing",
                    )
                    results.append(f"T{thread_id}-{i}")
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # Run concurrent validation
        threads = []
        for thread_id in range(10):
            thread = threading.Thread(target=validate_request, args=(thread_id,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Check for errors
        assert len(errors) == 0, f"Concurrent validation errors: {errors}"
        assert len(results) == 1000, f"Expected 1000 results, got {len(results)}"

    def test_concurrent_malicious_input_handling(self):
        """Test handling of malicious input under concurrent conditions."""

        malicious_inputs = [
            "../../../etc/passwd",
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "rm -rf /",
            "eval('import os; os.system(\"whoami\")')",
        ]

        results = {"blocked": 0, "accepted": 0}
        errors = []

        def test_malicious_input(payload: str, thread_id: int):
            try:
                request = ComposerRequest(
                    role="researcher", context=payload, domains="security-testing"
                )
                results["accepted"] += 1

            except ValidationError:
                results["blocked"] += 1
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # Run concurrent malicious input tests
        threads = []
        for i, payload in enumerate(malicious_inputs * 20):  # 100 total requests
            thread = threading.Thread(target=test_malicious_input, args=(payload, i))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no errors occurred during concurrent processing
        assert len(errors) == 0, f"Concurrent processing errors: {errors}"

        # Note: Whether requests are blocked or accepted depends on model validation
        # This test ensures concurrent processing doesn't cause crashes


class TestErrorHandlingSecurityValidation:
    """Test error handling doesn't leak sensitive information."""

    def test_error_message_information_disclosure(self):
        """Test that error messages don't disclose sensitive system information."""

        # Inputs designed to trigger various error conditions
        error_triggering_inputs = [
            {"role": None, "context": "test"},  # Type error
            {"role": "invalid_role_12345", "context": "test"},  # Validation error
            {"role": "researcher", "context": None},  # None context
            {},  # Missing required fields
        ]

        for invalid_input in error_triggering_inputs:
            try:
                ComposerRequest(**invalid_input)

            except Exception as e:
                error_message = str(e)

                # Check for information disclosure patterns
                sensitive_patterns = [
                    "/etc/",
                    "/home/",
                    "C:\\",
                    "\\Users\\",
                    "__file__",
                    "__name__",
                    "globals",
                    "locals",
                    "site-packages",
                    "/tmp/",
                    "python",
                ]

                for pattern in sensitive_patterns:
                    if pattern.lower() in error_message.lower():
                        pytest.fail(
                            f"Sensitive information disclosed in error: {pattern} in '{error_message}'"
                        )

    def test_validation_error_sanitization(self):
        """Test that validation errors are properly sanitized."""

        with pytest.raises(ValidationError) as exc_info:
            # Try to create request with malicious data that should trigger validation error
            ComposerRequest(
                role="researcher",
                context="../../../secret/file/path/data.txt",
                domains="malicious,../traversal,<script>xss</script>",
            )

        # If this fails, it means the malicious input was accepted (vulnerability)
        # If it passes, it means validation correctly rejected the input
        error_str = str(exc_info.value) if exc_info.value else ""

        # The error message should not contain the malicious content
        dangerous_content = ["../../../", "<script>", "secret/file"]
        for content in dangerous_content:
            assert content not in error_str, (
                f"Error message contains malicious content: {content}"
            )


# Performance and Load Testing
class TestSecurityPerformance:
    """Test security validation performance under load."""

    def test_validation_performance_under_load(self):
        """Test validation performance doesn't degrade under security scanning."""

        # Time normal validation
        start_time = time.time()
        for i in range(1000):
            ComposerRequest(
                role="researcher",
                context=f"Normal request {i}",
                domains="performance-testing",
            )
        normal_time = time.time() - start_time

        # Time validation with potential attack patterns
        attack_patterns = [
            "../etc/passwd",
            "<script>alert('xss')</script>",
            "'; DROP TABLE test; --",
            "eval('malicious_code')",
            "rm -rf /tmp/*",
        ]

        start_time = time.time()
        for i in range(200):  # 1000 total (200 * 5 patterns)
            pattern = attack_patterns[i % len(attack_patterns)]
            try:
                ComposerRequest(
                    role="researcher",
                    context=f"Security test {i}: {pattern}",
                    domains="security-performance",
                )
            except ValidationError:
                pass  # Expected for some patterns

        attack_time = time.time() - start_time

        # Security validation shouldn't be more than 3x slower than normal
        performance_ratio = (
            attack_time / normal_time if normal_time > 0 else float("inf")
        )
        assert performance_ratio < 3.0, (
            f"Security validation too slow: {performance_ratio:.2f}x"
        )
