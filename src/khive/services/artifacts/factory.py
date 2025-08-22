"""
Factory and configuration for the Artifacts Service.

Provides dependency injection and configuration management.
Based on Gemini Deep Think V2 architecture.
"""

import logging
from pathlib import Path

from pydantic import BaseModel, Field

from .exceptions import ConfigurationError
from .locks import LockManager
from .service import ArtifactsService
from .sessions import SessionManager
from .storage import FileSystemStorageRepository

logger = logging.getLogger(__name__)


class ArtifactsConfig(BaseModel):
    """
    Configuration for the Artifacts Service.

    Uses Pydantic for validation and environment variable support.
    """

    workspace_root: Path = Field(
        default=Path("./.khive/workspace"),
        description="Root directory for all session workspaces",
    )

    lock_timeout_seconds: float = Field(
        default=10.0,
        ge=0.1,
        le=300.0,
        description="Default timeout for lock acquisition in seconds",
    )

    max_locks: int = Field(
        default=1000,
        ge=10,
        le=10000,
        description="Maximum number of locks to keep in memory",
    )

    enable_lock_cleanup: bool = Field(
        default=True, description="Whether to automatically cleanup unused locks"
    )

    log_level: str = Field(
        default="INFO", description="Logging level for the artifacts service"
    )

    def model_post_init(self, __context):
        """Post-initialization validation and setup."""
        # Ensure workspace root is absolute for security
        if not self.workspace_root.is_absolute():
            self.workspace_root = self.workspace_root.resolve()

        # Set up logging
        logging.getLogger("khive.services.artifacts").setLevel(self.log_level)


def create_artifacts_service(config: ArtifactsConfig) -> ArtifactsService:
    """
    Factory function (Composition Root) to initialize the ArtifactsService stack.

    This function wires up all dependencies and ensures proper initialization order.

    Args:
        config: Configuration object

    Returns:
        Fully initialized ArtifactsService

    Raises:
        ConfigurationError: If initialization fails
    """
    logger.info(
        f"Initializing ArtifactsService with workspace: {config.workspace_root}"
    )

    try:
        # 1. Initialize SessionManager (validates workspace access)
        session_manager = SessionManager(workspace_root=config.workspace_root)
        logger.debug("SessionManager initialized")

        # 2. Initialize Storage Repository
        storage_repository = FileSystemStorageRepository(
            session_manager=session_manager
        )
        logger.debug("FileSystemStorageRepository initialized")

        # 3. Initialize Lock Manager
        lock_manager = LockManager(default_timeout=config.lock_timeout_seconds)
        logger.debug("LockManager initialized")

        # 4. Wire up the ArtifactsService (Constructor Injection)
        service = ArtifactsService(
            storage_repo=storage_repository,
            session_manager=session_manager,
            lock_manager=lock_manager,
        )

        logger.info("ArtifactsService successfully initialized")
        return service

    except Exception as e:
        logger.error(f"Failed to initialize ArtifactsService: {e}", exc_info=True)
        raise ConfigurationError(f"Failed to initialize ArtifactsService: {e}") from e


def create_artifacts_service_from_env() -> ArtifactsService:
    """
    Convenience function to create service from environment variables.

    Environment variables:
    - ARTIFACTS_WORKSPACE_ROOT: Workspace root directory
    - ARTIFACTS_LOCK_TIMEOUT_SECONDS: Lock timeout
    - ARTIFACTS_MAX_LOCKS: Maximum locks to keep
    - ARTIFACTS_LOG_LEVEL: Logging level

    Returns:
        Configured ArtifactsService
    """
    try:
        # Try to use pydantic-settings if available for env var support
        from pydantic_settings import BaseSettings, SettingsConfigDict

        class ArtifactsEnvConfig(BaseSettings, ArtifactsConfig):
            model_config = SettingsConfigDict(env_prefix="ARTIFACTS_")

        config = ArtifactsEnvConfig()

    except ImportError:
        # Fallback to manual environment variable reading
        import os

        config = ArtifactsConfig(
            workspace_root=Path(
                os.getenv("ARTIFACTS_WORKSPACE_ROOT", "./.khive/workspace")
            ),
            lock_timeout_seconds=float(
                os.getenv("ARTIFACTS_LOCK_TIMEOUT_SECONDS", "10.0")
            ),
            max_locks=int(os.getenv("ARTIFACTS_MAX_LOCKS", "1000")),
            log_level=os.getenv("ARTIFACTS_LOG_LEVEL", "INFO"),
        )

    return create_artifacts_service(config)


def validate_dependencies() -> list[str]:
    """
    Validates that all required dependencies are available.

    Returns:
        List of missing dependencies (empty if all available)
    """
    missing = []

    # Check aiofiles
    try:
        import aiofiles
    except ImportError:
        missing.append("aiofiles")

    # Check pydantic
    try:
        import pydantic
    except ImportError:
        missing.append("pydantic")

    # Check asyncio (should be available in Python 3.11+)
    try:
        import asyncio

        # Check for Python 3.11+ features
        asyncio.timeout
    except (ImportError, AttributeError):
        missing.append("asyncio with timeout support (Python 3.11+)")

    return missing


def get_default_config() -> ArtifactsConfig:
    """
    Returns the default configuration.

    Useful for testing and documentation.
    """
    return ArtifactsConfig()


# Health check function for monitoring
async def health_check(service: ArtifactsService) -> dict:
    """
    Performs a basic health check on the artifacts service.

    Args:
        service: ArtifactsService instance to check

    Returns:
        Health status dictionary
    """
    try:
        # Test basic functionality
        sessions = await service.list_sessions()
        lock_stats = await service.get_lock_stats()

        return {
            "status": "healthy",
            "session_count": len(sessions),
            "lock_stats": lock_stats,
            "timestamp": "2024-01-01T00:00:00Z",  # Would use real timestamp
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z",  # Would use real timestamp
        }
