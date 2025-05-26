"""
Comprehensive tests for the configuration module (khive.config).

This module tests configuration loading, validation, and environment handling
which affects the entire system.
"""

import pytest
from unittest.mock import Mock, patch
import os
from pathlib import Path
from pydantic import SecretStr

from khive.config import AppSettings, settings, CacheConfig


class TestCacheConfig:
    """Test the CacheConfig class functionality."""

    def test_cache_config_initialization_defaults(self):
        """Test CacheConfig initialization with default values."""
        config = CacheConfig()

        assert config.ttl == 300
        assert config.key is None
        assert config.namespace is None
        assert callable(config.skip_cache_func)
        assert callable(config.noself)

    def test_cache_config_initialization_with_values(self):
        """Test CacheConfig initialization with custom values."""
        config = CacheConfig(
            ttl=600, key="test_key", namespace="test_namespace", alias="test_alias"
        )

        assert config.ttl == 600
        assert config.key == "test_key"
        assert config.namespace == "test_namespace"
        assert config.alias == "test_alias"

    def test_cache_config_as_kwargs(self):
        """Test CacheConfig as_kwargs method."""
        config = CacheConfig(ttl=600, key="test_key", namespace="test_namespace")

        kwargs = config.as_kwargs()

        assert isinstance(kwargs, dict)
        assert kwargs["ttl"] == 600
        assert kwargs["key"] == "test_key"
        assert kwargs["namespace"] == "test_namespace"

        # Should exclude unserialisable callables
        assert "key_builder" not in kwargs
        assert "skip_cache_func" not in kwargs
        assert "noself" not in kwargs
        assert "serializer" not in kwargs
        assert "plugins" not in kwargs


class TestAppSettings:
    """Test the AppSettings class functionality."""

    def test_app_settings_initialization_defaults(self):
        """Test AppSettings initialization with default values."""
        app_settings = AppSettings()

        # Check cache config
        assert isinstance(app_settings.aiocache_config, CacheConfig)

        # Check default model settings
        assert app_settings.KHIVE_EMBEDDING_PROVIDER == "openai"
        assert app_settings.KHIVE_EMBEDDING_MODEL == "text-embedding-3-small"
        assert app_settings.KHIVE_CHAT_PROVIDER == "anthropic"
        assert app_settings.KHIVE_CHAT_MODEL == "claude-3-7-sonnet-20250219"

        # Check storage settings
        assert app_settings.KHIVE_AUTO_STORE_EVENT is False
        assert app_settings.KHIVE_STORAGE_PROVIDER == "async_qdrant"
        assert app_settings.KHIVE_AUTO_EMBED_LOG is False
        assert app_settings.KHIVE_QDRANT_URL == "http://localhost:6333"
        assert app_settings.KHIVE_DEFAULT_QDRANT_COLLECTION == "event_logs"

    def test_app_settings_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            "KHIVE_EMBEDDING_PROVIDER": "custom_provider",
            "KHIVE_CHAT_MODEL": "custom-model",
            "KHIVE_AUTO_STORE_EVENT": "true",
            "KHIVE_QDRANT_URL": "http://custom.qdrant.com:6333",
            "OPENAI_API_KEY": "test_openai_key",
            "ANTHROPIC_API_KEY": "test_anthropic_key",
        }

        with patch.dict(os.environ, env_vars):
            app_settings = AppSettings()

            assert app_settings.KHIVE_EMBEDDING_PROVIDER == "custom_provider"
            assert app_settings.KHIVE_CHAT_MODEL == "custom-model"
            assert app_settings.KHIVE_AUTO_STORE_EVENT is True
            assert app_settings.KHIVE_QDRANT_URL == "http://custom.qdrant.com:6333"

            # Check that API keys are loaded as SecretStr
            assert isinstance(app_settings.OPENAI_API_KEY, SecretStr)
            assert isinstance(app_settings.ANTHROPIC_API_KEY, SecretStr)

    def test_app_settings_get_secret_success(self):
        """Test successful secret retrieval."""
        env_vars = {
            "OPENAI_API_KEY": "test_openai_secret",
            "ANTHROPIC_API_KEY": "test_anthropic_secret",
        }

        with patch.dict(os.environ, env_vars):
            app_settings = AppSettings()

            openai_secret = app_settings.get_secret("OPENAI_API_KEY")
            anthropic_secret = app_settings.get_secret("ANTHROPIC_API_KEY")

            assert openai_secret == "test_openai_secret"
            assert anthropic_secret == "test_anthropic_secret"

    def test_app_settings_get_secret_ollama_special_case(self):
        """Test special case for Ollama API key."""
        app_settings = AppSettings()

        # Should return "ollama" for any key containing "ollama"
        ollama_secret = app_settings.get_secret("OLLAMA_API_KEY")
        assert ollama_secret == "ollama"

    def test_app_settings_get_secret_not_found(self):
        """Test get_secret with non-existent key."""
        app_settings = AppSettings()

        with pytest.raises(
            AttributeError, match="Secret key 'NON_EXISTENT_KEY' not found"
        ):
            app_settings.get_secret("NON_EXISTENT_KEY")

    def test_app_settings_get_secret_none_value(self):
        """Test get_secret with None value."""
        # Create environment without API keys to test None behavior
        clean_env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}

        with patch.dict(os.environ, clean_env, clear=True):
            # Create AppSettings without env_file loading to test None behavior
            class TestAppSettings(AppSettings):
                model_config = AppSettings.model_config.copy()
                model_config.update({"env_file": None})

            app_settings = TestAppSettings()

            # All API keys default to None
            with pytest.raises(
                ValueError, match="Secret key 'OPENAI_API_KEY' is not set"
            ):
                app_settings.get_secret("OPENAI_API_KEY")

    def test_app_settings_frozen(self):
        """Test that AppSettings is frozen (immutable)."""
        app_settings = AppSettings()

        # Should not be able to modify settings after creation
        with pytest.raises(Exception):  # ValidationError or similar
            app_settings.KHIVE_EMBEDDING_PROVIDER = "modified_provider"

    def test_app_settings_model_config(self):
        """Test AppSettings model configuration."""
        app_settings = AppSettings()

        # Check that model config is properly set
        assert hasattr(app_settings, "model_config")
        config = app_settings.model_config

        # Should be case insensitive
        assert config.get("case_sensitive") is False
        # Should ignore extra fields
        assert config.get("extra") == "ignore"

    def test_app_settings_with_custom_cache_config(self):
        """Test AppSettings with custom cache configuration."""
        env_vars = {"AIOCACHE_CONFIG__TTL": "600"}

        with patch.dict(os.environ, env_vars):
            app_settings = AppSettings()

            # Cache config should still be a CacheConfig instance
            assert isinstance(app_settings.aiocache_config, CacheConfig)

    def test_app_settings_api_key_types(self):
        """Test that API keys are properly typed as SecretStr when set."""
        env_vars = {
            "OPENAI_API_KEY": "secret123",
            "GROQ_API_KEY": "groq_secret",
            "EXA_API_KEY": "exa_secret",
        }

        with patch.dict(os.environ, env_vars):
            app_settings = AppSettings()

            assert isinstance(app_settings.OPENAI_API_KEY, SecretStr)
            assert isinstance(app_settings.GROQ_API_KEY, SecretStr)
            assert isinstance(app_settings.EXA_API_KEY, SecretStr)

            # Verify the actual secret values
            assert app_settings.OPENAI_API_KEY.get_secret_value() == "secret123"
            assert app_settings.GROQ_API_KEY.get_secret_value() == "groq_secret"
            assert app_settings.EXA_API_KEY.get_secret_value() == "exa_secret"


class TestSettingsSingleton:
    """Test the global settings singleton."""

    def test_settings_singleton_exists(self):
        """Test that the global settings singleton exists."""
        assert settings is not None
        assert isinstance(settings, AppSettings)

    def test_settings_singleton_consistency(self):
        """Test that the singleton is consistent."""
        # The settings should be the same instance
        assert AppSettings._instance is settings
        assert isinstance(settings, AppSettings)

    def test_settings_singleton_immutable(self):
        """Test that the singleton settings are immutable."""
        # Should not be able to modify the global settings
        with pytest.raises(Exception):  # ValidationError or similar
            settings.KHIVE_CHAT_PROVIDER = "modified"


class TestAppSettingsIntegration:
    """Integration tests for AppSettings."""

    def test_comprehensive_environment_loading(self):
        """Test loading a comprehensive set of environment variables."""
        env_vars = {
            # API Keys
            "OPENAI_API_KEY": "openai_test_key",
            "ANTHROPIC_API_KEY": "anthropic_test_key",
            "GROQ_API_KEY": "groq_test_key",
            "PERPLEXITY_API_KEY": "perplexity_test_key",
            # Model settings
            "KHIVE_EMBEDDING_PROVIDER": "test_embedding_provider",
            "KHIVE_EMBEDDING_MODEL": "test-embedding-model",
            "KHIVE_CHAT_PROVIDER": "test_chat_provider",
            "KHIVE_CHAT_MODEL": "test-chat-model",
            # Storage settings
            "KHIVE_AUTO_STORE_EVENT": "true",
            "KHIVE_STORAGE_PROVIDER": "test_storage",
            "KHIVE_AUTO_EMBED_LOG": "true",
            "KHIVE_QDRANT_URL": "http://test.qdrant.com:6333",
            "KHIVE_DEFAULT_QDRANT_COLLECTION": "test_collection",
        }

        with patch.dict(os.environ, env_vars):
            app_settings = AppSettings()

            # Verify API keys
            assert app_settings.get_secret("OPENAI_API_KEY") == "openai_test_key"
            assert app_settings.get_secret("ANTHROPIC_API_KEY") == "anthropic_test_key"
            assert app_settings.get_secret("GROQ_API_KEY") == "groq_test_key"
            assert (
                app_settings.get_secret("PERPLEXITY_API_KEY") == "perplexity_test_key"
            )

            # Verify model settings
            assert app_settings.KHIVE_EMBEDDING_PROVIDER == "test_embedding_provider"
            assert app_settings.KHIVE_EMBEDDING_MODEL == "test-embedding-model"
            assert app_settings.KHIVE_CHAT_PROVIDER == "test_chat_provider"
            assert app_settings.KHIVE_CHAT_MODEL == "test-chat-model"

            # Verify storage settings
            assert app_settings.KHIVE_AUTO_STORE_EVENT is True
            assert app_settings.KHIVE_STORAGE_PROVIDER == "test_storage"
            assert app_settings.KHIVE_AUTO_EMBED_LOG is True
            assert app_settings.KHIVE_QDRANT_URL == "http://test.qdrant.com:6333"
            assert app_settings.KHIVE_DEFAULT_QDRANT_COLLECTION == "test_collection"

    def test_boolean_environment_variable_parsing(self):
        """Test that boolean environment variables are parsed correctly."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"KHIVE_AUTO_STORE_EVENT": env_value}):
                app_settings = AppSettings()
                assert app_settings.KHIVE_AUTO_STORE_EVENT is expected

    def test_settings_with_env_file_support(self):
        """Test that settings support .env file loading."""
        # This tests the configuration for env file support
        app_settings = AppSettings()

        # Check that model_config includes env_file settings
        config = app_settings.model_config
        assert "env_file" in config
        env_files = config["env_file"]

        # Should support multiple env files
        assert isinstance(env_files, (list, tuple))
        assert ".env" in env_files
