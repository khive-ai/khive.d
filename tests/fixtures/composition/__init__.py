"""Composition test fixtures for AgentComposer testing.

This module provides comprehensive fixtures for testing agent composition functionality,
including security testing, file operations testing, and performance testing scenarios.
"""

from .composition_fixtures import (composer_with_test_data,
                                   mock_composition_file_system,
                                   temp_composition_env)
from .performance_fixtures import (concurrent_test_setup,
                                   large_composition_data,
                                   stress_test_environment)
from .security_fixtures import path_traversal_attempts

__all__ = [
    # Core fixtures
    "composer_with_test_data",
    # Performance fixtures
    "concurrent_test_setup",
    "large_composition_data",
    "mock_composition_file_system",
    # Security fixtures
    "path_traversal_attempts",
    "stress_test_environment",
    "temp_composition_env",
]
