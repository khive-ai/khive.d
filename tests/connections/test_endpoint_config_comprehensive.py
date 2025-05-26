"""
Comprehensive tests for endpoint configuration (khive.connections.endpoint_config).

This module tests endpoint configuration loading, validation, and management
which is fundamental for the connection system.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import os

from khive.connections.endpoint_config import EndpointConfig


class TestEndpointConfig:
    """Test the EndpointConfig class functionality."""

    def test_endpoint_config_initialization(self):
        """Test EndpointConfig initialization with basic parameters."""
        config = EndpointConfig(
            name="test_endpoint",
            provider="openai", 
            endpoint="v1/chat/completions",
            base_url="https://api.openai.com"
        )

        assert config.name == "test_endpoint"
        assert config.provider == "openai"
        assert config.endpoint == "v1/chat/completions"
        assert config.base_url == "https://api.openai.com"
        assert config.method == "POST"  # default value

    def test_endpoint_config_with_headers(self):
        """Test EndpointConfig with custom headers."""
        headers = {"X-Custom": "value", "Content-Type": "application/json"}

        config = EndpointConfig(
            name="auth_endpoint",
            provider="custom",
            endpoint="v1/auth",
            base_url="https://api.example.com",
            default_headers=headers,
        )

        assert config.default_headers == headers
        assert config.default_headers["X-Custom"] == "value"

    def test_endpoint_config_with_timeout(self):
        """Test EndpointConfig with custom timeout."""
        config = EndpointConfig(
            name="slow_endpoint",
            provider="custom",
            endpoint="v1/slow",
            base_url="https://api.example.com",
            timeout=60,
        )

        assert config.timeout == 60

    def test_endpoint_config_with_retries(self):
        """Test EndpointConfig with retry configuration."""
        config = EndpointConfig(
            name="retry_endpoint",
            provider="custom",
            endpoint="v1/flaky",
            base_url="https://api.example.com",
            max_retries=5,
        )

        assert config.max_retries == 5

    def test_endpoint_config_validation_invalid_transport(self):
        """Test EndpointConfig validation with invalid transport type."""
        with pytest.raises(ValueError):
            EndpointConfig(
                name="invalid",
                provider="custom",
                endpoint="v1/test",
                transport_type="invalid_transport"  # Should only accept "http" or "sdk"
            )

    def test_endpoint_config_default_values(self):
        """Test default values for optional parameters."""
        config = EndpointConfig(
            name="defaults",
            provider="custom",
            endpoint="v1/test",
            base_url="https://api.example.com"
        )

        # Check default values
        assert config.transport_type == "http"
        assert config.method == "POST"
        assert config.content_type == "application/json"
        assert config.auth_type == "bearer"
        assert config.timeout == 300
        assert config.max_retries == 3
        assert config.openai_compatible is False

    def test_endpoint_config_full_url_property(self):
        """Test full_url property generation."""
        config = EndpointConfig(
            name="test",
            provider="openai",
            endpoint="v1/chat/completions",
            base_url="https://api.openai.com"
        )

        assert config.full_url == "https://api.openai.com/v1/chat/completions"

    def test_endpoint_config_full_url_with_params(self):
        """Test full_url property with endpoint parameters."""
        config = EndpointConfig(
            name="test",
            provider="custom",
            endpoint="v1/models/{model_id}",
            base_url="https://api.example.com",
            endpoint_params=["model_id"],
            params={"model_id": "gpt-4"}
        )

        assert config.full_url == "https://api.example.com/v1/models/gpt-4"

    def test_endpoint_config_update_method(self):
        """Test the update method."""
        config = EndpointConfig(
            name="test",
            provider="custom",
            endpoint="v1/test",
            base_url="https://api.example.com"
        )

        config.update(timeout=120, custom_param="value")
        
        assert config.timeout == 120
        assert config.kwargs["custom_param"] == "value"

    def test_endpoint_config_api_key_handling_env_var(self):
        """Test API key handling with environment variable."""
        with patch.dict(os.environ, {"TEST_API_KEY": "secret123"}):
            config = EndpointConfig(
                name="test",
                provider="custom",
                endpoint="v1/test",
                base_url="https://api.example.com",
                api_key="TEST_API_KEY"
            )
            
            assert config._api_key == "secret123"

    def test_endpoint_config_api_key_handling_direct_value(self):
        """Test API key handling with direct value."""
        config = EndpointConfig(
            name="test",
            provider="custom", 
            endpoint="v1/test",
            base_url="https://api.example.com",
            api_key="direct_key_value"
        )
        
        # Should use the direct value if not found in env
        assert config._api_key == "direct_key_value"

    def test_endpoint_config_sdk_transport_requires_api_key(self):
        """Test that SDK transport requires API key for non-ollama providers."""
        with pytest.raises(ValueError, match="API key is required"):
            EndpointConfig(
                name="test",
                provider="openai",
                endpoint="v1/chat/completions",
                transport_type="sdk",
                api_key=None
            )

    def test_endpoint_config_ollama_exception(self):
        """Test that Ollama provider doesn't require API key for SDK transport."""
        config = EndpointConfig(
            name="test",
            provider="ollama",
            endpoint="v1/chat/completions", 
            transport_type="sdk",
            api_key=None
        )
        
        assert config._api_key == "ollama_key"

    def test_endpoint_config_validate_payload_no_options(self):
        """Test payload validation when no request_options are set."""
        config = EndpointConfig(
            name="test",
            provider="custom",
            endpoint="v1/test",
            base_url="https://api.example.com"
        )
        
        test_data = {"message": "hello", "temperature": 0.7}
        result = config.validate_payload(test_data)
        
        assert result == test_data

    def test_endpoint_config_kwargs_handling(self):
        """Test that unknown fields go into kwargs."""
        config = EndpointConfig(
            name="test",
            provider="custom",
            endpoint="v1/test",
            base_url="https://api.example.com",
            unknown_field="value",
            another_unknown=123
        )
        
        assert config.kwargs["unknown_field"] == "value"
        assert config.kwargs["another_unknown"] == 123

    def test_endpoint_config_client_kwargs(self):
        """Test client_kwargs field."""
        client_kwargs = {"verify_ssl": False, "connect_timeout": 30}
        
        config = EndpointConfig(
            name="test",
            provider="custom",
            endpoint="v1/test",
            base_url="https://api.example.com",
            client_kwargs=client_kwargs
        )
        
        assert config.client_kwargs == client_kwargs

    def test_endpoint_config_serialization(self):
        """Test model serialization."""
        config = EndpointConfig(
            name="serialize_test",
            provider="openai",
            endpoint="v1/chat/completions",
            base_url="https://api.openai.com",
            timeout=30,
            max_retries=5
        )

        config_dict = config.model_dump()

        assert isinstance(config_dict, dict)
        assert config_dict["name"] == "serialize_test"
        assert config_dict["provider"] == "openai"
        assert config_dict["endpoint"] == "v1/chat/completions"
        assert config_dict["timeout"] == 30
        assert config_dict["max_retries"] == 5


class TestEndpointConfigIntegration:
    """Integration tests for endpoint configuration."""

    def test_config_roundtrip_serialization(self):
        """Test complete serialization roundtrip."""
        original_config = EndpointConfig(
            name="roundtrip_test",
            provider="anthropic",
            endpoint="v1/messages",
            base_url="https://api.anthropic.com",
            timeout=30,
            max_retries=3,
            default_headers={"X-Test": "value"}
        )

        # Serialize to dict
        config_dict = original_config.model_dump()

        # Recreate from dict
        recreated_config = EndpointConfig(**config_dict)

        # Compare key attributes
        assert recreated_config.name == original_config.name
        assert recreated_config.provider == original_config.provider
        assert recreated_config.endpoint == original_config.endpoint
        assert recreated_config.base_url == original_config.base_url
        assert recreated_config.timeout == original_config.timeout
        assert recreated_config.max_retries == original_config.max_retries

    def test_config_with_all_fields(self):
        """Test configuration with all possible fields set."""
        config = EndpointConfig(
            name="comprehensive_test",
            provider="custom",
            transport_type="http",
            base_url="https://api.example.com",
            endpoint="v1/test/{model}",
            endpoint_params=["model"],
            method="PUT",
            params={"model": "test-model"},
            content_type="application/json",
            auth_type="bearer",
            default_headers={"X-Custom": "header"},
            api_key="test_key",
            timeout=120,
            max_retries=5,
            openai_compatible=True,
            client_kwargs={"verify": False},
            custom_field="custom_value"
        )

        # Verify all fields are set correctly
        assert config.name == "comprehensive_test"
        assert config.provider == "custom"
        assert config.transport_type == "http"
        assert config.base_url == "https://api.example.com"
        assert config.endpoint == "v1/test/{model}"
        assert config.endpoint_params == ["model"]
        assert config.method == "PUT"
        assert config.params == {"model": "test-model"}
        assert config.content_type == "application/json"
        assert config.auth_type == "bearer"
        assert config.default_headers == {"X-Custom": "header"}
        assert config._api_key == "test_key"
        assert config.timeout == 120
        assert config.max_retries == 5
        assert config.openai_compatible is True
        assert config.client_kwargs == {"verify": False}
        assert config.kwargs["custom_field"] == "custom_value"

    def test_config_model_validation_errors(self):
        """Test various model validation error cases."""
        # Missing required fields
        with pytest.raises(ValueError):
            EndpointConfig()  # Missing name, provider, endpoint

        # Invalid transport_type
        with pytest.raises(ValueError):
            EndpointConfig(
                name="test",
                provider="custom",
                endpoint="v1/test",
                transport_type="invalid"
            )
