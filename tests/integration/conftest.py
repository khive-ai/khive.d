"""
Integration test fixtures and configuration.

Provides fixtures for cross-service testing, database setup, and external API mocking.
"""

import asyncio
import json
import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from khive.services.artifacts.factory import (ArtifactsConfig,
                                              create_artifacts_service)
from khive.services.artifacts.models import Author
from khive.services.artifacts.service import ArtifactsService
from khive.services.cache.config import CacheConfig
from khive.services.cache.redis_cache import RedisCache
from khive.services.session.session_service import SessionService

# Import fixtures to make them available to integration tests
from .fixtures import *


@pytest.fixture(scope="session")
def integration_event_loop():
    """Create event loop for integration tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def integration_temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for integration tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def temp_workspace(integration_temp_dir: Path) -> Path:
    """Create temporary workspace for artifacts integration tests."""
    workspace = integration_temp_dir / "artifacts_workspace"
    workspace.mkdir(exist_ok=True)
    return workspace


@pytest.fixture
def integration_env() -> Generator[dict[str, Any], None, None]:
    """Set environment variables for integration testing."""
    original_env = dict(os.environ)

    test_env = {
        "KHIVE_TEST_MODE": "true",
        "KHIVE_DISABLE_EXTERNAL_APIS": "true",
        "KHIVE_INTEGRATION_TEST": "true",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "OPENAI_API_KEY": "test_key_for_integration_testing",
    }

    os.environ.update(test_env)

    try:
        yield test_env
    finally:
        os.environ.clear()
        os.environ.update(original_env)


@pytest.fixture
def artifacts_service_config(integration_temp_dir: Path) -> ArtifactsConfig:
    """Create artifacts service configuration for integration testing."""
    workspace_root = integration_temp_dir / "artifacts_workspace"
    workspace_root.mkdir(exist_ok=True)

    return ArtifactsConfig(workspace_root=workspace_root)


@pytest.fixture
def artifacts_service(artifacts_service_config: ArtifactsConfig) -> ArtifactsService:
    """Create artifacts service instance for integration testing."""
    return create_artifacts_service(artifacts_service_config)


@pytest.fixture
def cache_config() -> CacheConfig:
    """Create cache configuration for integration testing."""
    return CacheConfig(
        redis_host="localhost",
        redis_port=6379,
        redis_db=15,  # Use separate DB for testing
        redis_ssl=False,  # Explicitly disable SSL for testing
    )


@pytest_asyncio.fixture
async def redis_cache(cache_config: CacheConfig) -> Generator[RedisCache, None, None]:
    """Create Redis cache instance for integration testing."""
    cache = RedisCache(cache_config)

    try:
        # Test connection - skip if Redis is not available
        await cache._connect()
        yield cache
    except Exception as e:
        pytest.skip(f"Redis not available for integration testing: {e}")
    finally:
        if cache._redis:
            await cache._redis.flushdb()  # Clean test data
            await cache._redis.aclose()


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for integration testing."""
    mock_client = AsyncMock()

    # Mock successful completion response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps({
                    "complexity": "medium",
                    "confidence": 0.85,
                    "reasoning": "Integration testing scenario with moderate complexity",
                    "recommended_agents": 3,
                    "roles": ["researcher", "implementer", "tester"],
                })
            )
        )
    ]

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    return mock_client


@pytest.fixture
def mock_external_apis(mock_openai_client):
    """Patch all external APIs for integration testing."""
    with patch("openai.AsyncOpenAI", return_value=mock_openai_client):
        yield {
            "openai": mock_openai_client,
        }


@pytest.fixture
def session_service(artifacts_service: ArtifactsService) -> SessionService:
    """Create session service instance for integration testing."""
    # SessionService constructor takes no parameters
    return SessionService()


@pytest.fixture
def integration_session_id() -> str:
    """Provide a consistent session ID for integration tests."""
    return "integration_test_session_20250822"


@pytest.fixture
async def populated_session(
    artifacts_service: ArtifactsService, integration_session_id: str
) -> str:
    """Create and populate a test session with sample documents."""
    # Create session
    session = artifacts_service.create_session(integration_session_id)

    # Create sample documents
    artifacts_service.create_document(
        "research_findings",
        integration_session_id,
        content="# Research Findings\n\nThis is a test research document.",
        description="Test research document for integration testing",
    )

    artifacts_service.create_document(
        "implementation_plan",
        integration_session_id,
        content="# Implementation Plan\n\n1. Phase 1: Setup\n2. Phase 2: Implementation",
        description="Test implementation plan for integration testing",
    )

    return integration_session_id


@pytest.fixture
def error_injection_config():
    """Configuration for error injection testing."""
    return {
        "redis_connection_failure_rate": 0.1,
        "file_system_failure_rate": 0.05,
        "api_timeout_rate": 0.15,
        "concurrent_access_conflicts": 0.2,
    }


@pytest.fixture
def performance_test_config():
    """Configuration for performance integration testing."""
    return {
        "concurrent_operations": 10,
        "operation_timeout": 30.0,
        "expected_throughput": 100,  # operations per second
        "memory_limit_mb": 256,
    }


class IntegrationTestData:
    """Test data factory for integration tests."""

    @staticmethod
    def sample_planning_request() -> str:
        """Sample planning request for integration testing."""
        return "Implement comprehensive authentication system with JWT tokens and role-based access control"

    @staticmethod
    def sample_document_content() -> str:
        """Sample document content for integration testing."""
        return """# Integration Test Document

This is a sample document created during integration testing.

## Contents
- Test data for validation
- Integration scenarios
- Cross-service workflows

## Metadata
- Created by: integration test suite
- Purpose: validation of cross-service functionality
"""

    @staticmethod
    def sample_session_metadata() -> dict[str, Any]:
        """Sample session metadata for integration testing."""
        return {
            "project": "integration_testing",
            "phase": "validation",
            "participants": ["researcher", "implementer", "tester"],
            "priority": "high",
        }


@pytest.fixture
def integration_test_data() -> IntegrationTestData:
    """Provide integration test data factory."""
    return IntegrationTestData()


@pytest_asyncio.fixture
async def integration_artifacts_service(temp_workspace: Path) -> ArtifactsService:
    """Create artifacts service for integration testing."""
    config = ArtifactsConfig(workspace_root=temp_workspace)
    return create_artifacts_service(config)


@pytest.fixture
def test_author() -> Author:
    """Create a test author for document operations."""
    return Author(id="test_author", role="tester")
