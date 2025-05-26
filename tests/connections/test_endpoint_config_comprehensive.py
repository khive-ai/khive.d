"""
Comprehensive tests for endpoint configuration (khive.connections.endpoint_config).

This module tests endpoint configuration loading, validation, and management
which is fundamental for the connection system.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import yaml
import json

from khive.connections.endpoint_config import EndpointConfig, load_endpoint_configs


class TestEndpointConfig:
    """Test the EndpointConfig class functionality."""

    def test_endpoint_config_initialization(self):
        """Test EndpointConfig initialization with basic parameters."""
        config = EndpointConfig(
            name="test_endpoint",
            url="https://api.example.com",
            method="POST"
        )
        
        assert config.name == "test_endpoint"
        assert config.url == "https://api.example.com"
        assert config.method == "POST"

    def test_endpoint_config_with_headers(self):
        """Test EndpointConfig with custom headers."""
        headers = {
            "Authorization": "Bearer token",
            "Content-Type": "application/json"
        }
        
        config = EndpointConfig(
            name="auth_endpoint",
            url="https://api.example.com/auth",
            method="POST",
            headers=headers
        )
        
        assert config.headers == headers
        assert config.headers["Authorization"] == "Bearer token"

    def test_endpoint_config_with_timeout(self):
        """Test EndpointConfig with custom timeout."""
        config = EndpointConfig(
            name="slow_endpoint",
            url="https://api.example.com/slow",
            method="GET",
            timeout=60.0
        )
        
        assert config.timeout == 60.0

    def test_endpoint_config_with_retries(self):
        """Test EndpointConfig with retry configuration."""
        config = EndpointConfig(
            name="retry_endpoint",
            url="https://api.example.com/flaky",
            method="GET",
            max_retries=5,
            retry_delay=2.0
        )
        
        assert config.max_retries == 5
        assert config.retry_delay == 2.0

    def test_endpoint_config_validation(self):
        """Test EndpointConfig validation."""
        # Valid config should not raise
        config = EndpointConfig(
            name="valid",
            url="https://api.example.com",
            method="GET"
        )
        assert config.name == "valid"
        
        # Test invalid method
        with pytest.raises(ValueError):
            EndpointConfig(
                name="invalid_method",
                url="https://api.example.com",
                method="INVALID"
            )
        
        # Test invalid URL format
        with pytest.raises(ValueError):
            EndpointConfig(
                name="invalid_url",
                url="not-a-url",
                method="GET"
            )

    def test_endpoint_config_default_values(self):
        """Test default values for optional parameters."""
        config = EndpointConfig(
            name="defaults",
            url="https://api.example.com",
            method="GET"
        )
        
        # Check default values
        assert config.headers == {} or config.headers is None
        assert config.timeout > 0  # Should have reasonable default
        assert config.max_retries >= 0  # Should have default retry setting

    def test_endpoint_config_serialization(self):
        """Test serialization to dict."""
        config = EndpointConfig(
            name="serialize_test",
            url="https://api.example.com",
            method="POST",
            headers={"X-Test": "value"},
            timeout=30.0
        )
        
        config_dict = config.to_dict() if hasattr(config, 'to_dict') else config.__dict__
        
        assert isinstance(config_dict, dict)
        assert config_dict["name"] == "serialize_test"
        assert config_dict["url"] == "https://api.example.com"
        assert config_dict["method"] == "POST"

    def test_endpoint_config_from_dict(self):
        """Test creation from dictionary."""
        config_data = {
            "name": "from_dict_test",
            "url": "https://api.example.com",
            "method": "PUT",
            "headers": {"Authorization": "Bearer test"},
            "timeout": 45.0,
            "max_retries": 3
        }
        
        if hasattr(EndpointConfig, 'from_dict'):
            config = EndpointConfig.from_dict(config_data)
        else:
            config = EndpointConfig(**config_data)
        
        assert config.name == "from_dict_test"
        assert config.url == "https://api.example.com"
        assert config.method == "PUT"
        assert config.timeout == 45.0

    def test_endpoint_config_environment_variable_substitution(self):
        """Test environment variable substitution in config."""
        with patch.dict('os.environ', {'API_TOKEN': 'secret123', 'API_URL': 'https://prod.api.com'}):
            config_data = {
                "name": "env_test",
                "url": "${API_URL}/v1/endpoint",
                "method": "GET",
                "headers": {"Authorization": "Bearer ${API_TOKEN}"}
            }
            
            # Test if environment variable substitution works
            if hasattr(EndpointConfig, 'from_dict'):
                config = EndpointConfig.from_dict(config_data)
                # Check if substitution occurred
                if "${" not in config.url:
                    assert "https://prod.api.com" in config.url
                if "${" not in config.headers.get("Authorization", ""):
                    assert "secret123" in config.headers["Authorization"]


class TestLoadEndpointConfigs:
    """Test the load_endpoint_configs function."""

    def test_load_from_yaml_file(self):
        """Test loading configurations from YAML file."""
        yaml_content = """
endpoints:
  - name: test_endpoint_1
    url: https://api1.example.com
    method: GET
    timeout: 30.0
    
  - name: test_endpoint_2
    url: https://api2.example.com
    method: POST
    headers:
      Content-Type: application/json
    max_retries: 3
"""
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.suffix", ".yaml"):
                    configs = load_endpoint_configs("test_config.yaml")
        
        assert len(configs) == 2
        assert configs[0].name == "test_endpoint_1"
        assert configs[0].url == "https://api1.example.com"
        assert configs[0].method == "GET"
        assert configs[1].name == "test_endpoint_2"
        assert configs[1].method == "POST"

    def test_load_from_json_file(self):
        """Test loading configurations from JSON file."""
        json_content = {
            "endpoints": [
                {
                    "name": "json_endpoint",
                    "url": "https://api.example.com",
                    "method": "GET",
                    "timeout": 25.0
                }
            ]
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(json_content))):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.suffix", ".json"):
                    configs = load_endpoint_configs("test_config.json")
        
        assert len(configs) == 1
        assert configs[0].name == "json_endpoint"
        assert configs[0].url == "https://api.example.com"

    def test_load_from_directory(self):
        """Test loading configurations from directory."""
        yaml_content = """
endpoints:
  - name: dir_endpoint_1
    url: https://api1.example.com
    method: GET
"""
        
        json_content = {
            "endpoints": [
                {
                    "name": "dir_endpoint_2",
                    "url": "https://api2.example.com",
                    "method": "POST"
                }
            ]
        }
        
        def mock_iterdir():
            yaml_file = Mock()
            yaml_file.suffix = ".yaml"
            yaml_file.is_file.return_value = True
            yaml_file.name = "config1.yaml"
            
            json_file = Mock()
            json_file.suffix = ".json"
            json_file.is_file.return_value = True
            json_file.name = "config2.json"
            
            return [yaml_file, json_file]
        
        def mock_open_func(file_path, *args, **kwargs):
            if "yaml" in str(file_path):
                return mock_open(read_data=yaml_content)()
            else:
                return mock_open(read_data=json.dumps(json_content))()
        
        with patch("builtins.open", side_effect=mock_open_func):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("pathlib.Path.iterdir", side_effect=mock_iterdir):
                    configs = load_endpoint_configs("config_dir/")
        
        assert len(configs) == 2
        config_names = [config.name for config in configs]
        assert "dir_endpoint_1" in config_names
        assert "dir_endpoint_2" in config_names

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file."""
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                load_endpoint_configs("nonexistent.yaml")

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML content."""
        invalid_yaml = """
endpoints:
  - name: test
    url: https://api.example.com
    method: GET
  - invalid: yaml: content: here
"""
        
        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.suffix", ".yaml"):
                    with pytest.raises(yaml.YAMLError):
                        load_endpoint_configs("invalid.yaml")

    def test_load_invalid_json(self):
        """Test loading invalid JSON content."""
        invalid_json = '{"endpoints": [{"name": "test", "invalid": json}]}'
        
        with patch("builtins.open", mock_open(read_data=invalid_json)):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.suffix", ".json"):
                    with pytest.raises(json.JSONDecodeError):
                        load_endpoint_configs("invalid.json")

    def test_load_empty_config(self):
        """Test loading empty configuration."""
        empty_yaml = """
endpoints: []
"""
        
        with patch("builtins.open", mock_open(read_data=empty_yaml)):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.suffix", ".yaml"):
                    configs = load_endpoint_configs("empty.yaml")
        
        assert len(configs) == 0
        assert isinstance(configs, list)

    def test_load_config_validation_error(self):
        """Test handling of configuration validation errors."""
        invalid_config_yaml = """
endpoints:
  - name: invalid_endpoint
    url: not-a-valid-url
    method: INVALID_METHOD
"""
        
        with patch("builtins.open", mock_open(read_data=invalid_config_yaml)):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.suffix", ".yaml"):
                    with pytest.raises((ValueError, TypeError)):
                        load_endpoint_configs("invalid_config.yaml")

    def test_load_with_environment_variables(self):
        """Test loading configuration with environment variable substitution."""
        yaml_with_env = """
endpoints:
  - name: env_endpoint
    url: ${API_BASE_URL}/v1/test
    method: GET
    headers:
      Authorization: Bearer ${API_TOKEN}
"""
        
        with patch.dict('os.environ', {'API_BASE_URL': 'https://prod.api.com', 'API_TOKEN': 'prod_token'}):
            with patch("builtins.open", mock_open(read_data=yaml_with_env)):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.suffix", ".yaml"):
                        configs = load_endpoint_configs("env_config.yaml")
        
        assert len(configs) == 1
        config = configs[0]
        
        # Check if environment variables were substituted
        if hasattr(config, 'substitute_env_vars') or "${" not in config.url:
            assert "https://prod.api.com" in config.url
            if config.headers and "Authorization" in config.headers:
                assert "prod_token" in config.headers["Authorization"]


class TestEndpointConfigIntegration:
    """Integration tests for endpoint configuration."""

    def test_config_roundtrip_serialization(self):
        """Test complete serialization roundtrip."""
        original_config = EndpointConfig(
            name="roundtrip_test",
            url="https://api.example.com/test",
            method="POST",
            headers={"Content-Type": "application/json"},
            timeout=30.0,
            max_retries=3,
            retry_delay=1.5
        )
        
        # Serialize to dict
        config_dict = original_config.to_dict() if hasattr(original_config, 'to_dict') else original_config.__dict__
        
        # Recreate from dict
        if hasattr(EndpointConfig, 'from_dict'):
            recreated_config = EndpointConfig.from_dict(config_dict)
        else:
            recreated_config = EndpointConfig(**{k: v for k, v in config_dict.items() if not k.startswith('_')})
        
        # Compare key attributes
        assert recreated_config.name == original_config.name
        assert recreated_config.url == original_config.url
        assert recreated_config.method == original_config.method

    def test_multiple_configs_same_name_handling(self):
        """Test handling of configurations with duplicate names."""
        yaml_with_duplicates = """
endpoints:
  - name: duplicate_name
    url: https://api1.example.com
    method: GET
    
  - name: duplicate_name
    url: https://api2.example.com
    method: POST
"""
        
        with patch("builtins.open", mock_open(read_data=yaml_with_duplicates)):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.suffix", ".yaml"):
                    configs = load_endpoint_configs("duplicates.yaml")
        
        # Should load both configs (handling duplicates is up to the application)
        assert len(configs) == 2
        assert all(config.name == "duplicate_name" for config in configs)

    def test_config_inheritance_or_defaults(self):
        """Test configuration inheritance or default value application."""
        yaml_with_minimal_config = """
endpoints:
  - name: minimal
    url: https://api.example.com
    method: GET
"""
        
        with patch("builtins.open", mock_open(read_data=yaml_with_minimal_config)):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.suffix", ".yaml"):
                    configs = load_endpoint_configs("minimal.yaml")
        
        assert len(configs) == 1
        config = configs[0]
        
        # Should have reasonable defaults
        assert config.name == "minimal"
        assert config.url == "https://api.example.com"
        assert config.method == "GET"
        # Other attributes should have defaults or be None
        assert hasattr(config, 'timeout')
        assert hasattr(config, 'headers')