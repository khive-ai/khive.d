"""Security testing fixtures for vulnerability testing and input validation."""

from typing import Any

import pytest


@pytest.fixture
def security_test_config():
    """Configuration for security testing scenarios."""
    return {
        "max_input_length": 10000,
        "max_file_size_mb": 100,
        "allowed_file_extensions": [".py", ".md", ".txt", ".yaml", ".json"],
        "sensitive_env_vars": [
            "OPENAI_API_KEY",
            "API_KEY",
            "SECRET_KEY",
            "PASSWORD",
            "TOKEN",
        ],
        "max_path_depth": 10,
        "allowed_hosts": ["localhost", "127.0.0.1", "api.openai.com"],
    }


@pytest.fixture
def security_scanner():
    """Security scanning utilities for automated testing."""

    class SecurityScanner:
        def validate_input(
            self, input_data: str, max_length: int = 1000
        ) -> dict[str, Any]:
            """Validate input for security issues."""
            issues = []

            if len(input_data) > max_length:
                issues.append(
                    f"Input length {len(input_data)} exceeds maximum {max_length}"
                )

            return {
                "is_valid": len(issues) == 0,
                "issues": issues,
                "input_length": len(input_data),
            }

    return SecurityScanner()
