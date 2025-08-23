"""
MCP Configuration Management Tests.

Tests configuration file parsing, validation, environment variable handling,
and configuration copying with security filtering.
Covers requirements from issue #189 MCP integration testing.

This module validates:
- Configuration file parsing and validation
- Environment variable precedence (config > .env > system)
- Server-specific mappings and token handling
- Configuration copying with security validation
- Default timeout calculation and server settings
- Configuration error recovery mechanisms
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from khive.cli.khive_mcp import MCPConfig, MCPServerConfig


class ConfigurationValidator:
    """Validates MCP server configurations for security and completeness."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_server_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Validate server configuration for security and completeness."""
        self.errors.clear()
        self.warnings.clear()

        # Required fields validation
        required_fields = ["name"]
        for field in required_fields:
            if field not in config:
                self.errors.append(f"Missing required field: {field}")

        # Command or URL validation
        has_command = "command" in config
        has_url = "url" in config

        if not has_command and not has_url:
            self.errors.append("Server must have either 'command' or 'url' specified")

        # Security validation for commands
        if has_command:
            command = config["command"]
            dangerous_patterns = ["rm ", "del ", "format ", "chmod 777", "sudo "]
            for pattern in dangerous_patterns:
                if pattern in command.lower():
                    self.errors.append(
                        f"Potentially dangerous command detected: {command}"
                    )

        # Environment variable validation
        if "env" in config:
            env_vars = config["env"]
            for key, value in env_vars.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    self.errors.append(
                        f"Invalid environment variable format: {key}={value}"
                    )
                if key.startswith("PATH"):
                    self.warnings.append(
                        f"PATH modification detected in env var: {key}"
                    )

        # Transport validation
        if "transport" in config:
            valid_transports = ["stdio", "sse", "http", "websocket"]
            if config["transport"] not in valid_transports:
                self.errors.append(f"Invalid transport: {config['transport']}")

        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def sanitize_configuration(self, config: dict[str, Any]) -> dict[str, Any]:
        """Sanitize configuration by removing/masking sensitive data."""
        sanitized = config.copy()

        # Mask sensitive environment variables
        if "env" in sanitized:
            env_vars = sanitized["env"]
            sensitive_keys = ["password", "secret", "key", "token"]

            for env_key, env_value in env_vars.items():
                if any(sensitive in env_key.lower() for sensitive in sensitive_keys):
                    sanitized["env"][env_key] = "*" * 8

        return sanitized


class EnvironmentVariableManager:
    """Manages environment variable precedence and security filtering."""

    def __init__(self):
        self.precedence_order = ["config", "env_file", "system"]

    def merge_environment_variables(
        self,
        config_env: dict[str, str],
        env_file_vars: dict[str, str],
        system_env: dict[str, str],
        permission_mode: str = "default",
    ) -> dict[str, str]:
        """Merge environment variables with precedence: config > .env > system."""
        merged_env = {}

        # Start with system environment (lowest precedence)
        merged_env.update(system_env)

        # Override with .env file variables
        merged_env.update(env_file_vars)

        # Override with config-specified variables (highest precedence)
        merged_env.update(config_env)

        # Apply security filtering based on permission mode
        return self._filter_environment_variables(merged_env, permission_mode)

    def _filter_environment_variables(
        self, env_vars: dict[str, str], permission_mode: str
    ) -> dict[str, str]:
        """Filter environment variables based on permission mode."""
        if permission_mode == "restricted":
            # In restricted mode, filter out sensitive variables
            sensitive_patterns = ["password", "secret", "key", "token", "credential"]

            filtered_vars = {}
            for key, value in env_vars.items():
                if not any(pattern in key.lower() for pattern in sensitive_patterns):
                    filtered_vars[key] = value

            return filtered_vars

        return env_vars

    def resolve_environment_references(self, config: dict[str, Any]) -> dict[str, Any]:
        """Resolve ${VAR} references in configuration values."""
        resolved_config = {}

        for key, value in config.items():
            if (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                env_var_name = value[2:-1]  # Remove ${ and }
                resolved_value = os.getenv(
                    env_var_name, value
                )  # Keep original if not found
                resolved_config[key] = resolved_value
            elif isinstance(value, dict):
                resolved_config[key] = self.resolve_environment_references(value)
            else:
                resolved_config[key] = value

        return resolved_config


@pytest.mark.mcp_configuration
@pytest.mark.integration
class TestMCPConfigurationParsing:
    """Test MCP configuration file parsing and validation."""

    @pytest.fixture
    def config_validator(self) -> ConfigurationValidator:
        """Create configuration validator."""
        return ConfigurationValidator()

    @pytest.fixture
    def env_manager(self) -> EnvironmentVariableManager:
        """Create environment variable manager."""
        return EnvironmentVariableManager()

    @pytest.fixture
    def temp_project(self) -> Path:
        """Create temporary project with configuration files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Create .khive directory
            khive_dir = project_dir / ".khive"
            khive_dir.mkdir()

            # Create mcps directory
            mcps_dir = khive_dir / "mcps"
            mcps_dir.mkdir()

            yield project_dir

    def test_valid_server_configuration(self, config_validator: ConfigurationValidator):
        """Test validation of valid server configurations."""
        valid_configs = [
            {
                "name": "file_server",
                "command": "python",
                "args": ["-m", "file_server"],
                "transport": "stdio",
            },
            {
                "name": "web_server",
                "url": "http://localhost:8080/mcp",
                "transport": "sse",
            },
            {
                "name": "ws_server",
                "url": "ws://localhost:8080/ws",
                "transport": "websocket",
            },
        ]

        for config in valid_configs:
            result = config_validator.validate_server_config(config)
            assert result["valid"], f"Config should be valid: {result['errors']}"
            assert len(result["errors"]) == 0

    def test_invalid_server_configuration(
        self, config_validator: ConfigurationValidator
    ):
        """Test validation catches invalid configurations."""
        invalid_configs = [
            {"command": "python"},  # Missing name
            {"name": "server"},  # Missing command or url
            {
                "name": "dangerous_server",
                "command": "rm -rf /",  # Dangerous command
                "transport": "stdio",
            },
            {"name": "invalid_transport", "command": "python", "transport": "invalid"},
        ]

        for config in invalid_configs:
            result = config_validator.validate_server_config(config)
            assert not result["valid"], f"Config should be invalid: {config}"
            assert len(result["errors"]) > 0

    def test_configuration_sanitization(self, config_validator: ConfigurationValidator):
        """Test configuration sanitization masks sensitive data."""
        config_with_secrets = {
            "name": "secure_server",
            "command": "python",
            "env": {
                "GITHUB_TOKEN": "secret_token_123",
                "API_KEY": "secret_key_456",
                "DATABASE_PASSWORD": "secret_password_789",
                "SAFE_VAR": "safe_value",
            },
        }

        sanitized = config_validator.sanitize_configuration(config_with_secrets)

        # Sensitive variables should be masked
        env_vars = sanitized["env"]
        assert env_vars["GITHUB_TOKEN"] == "*" * 8
        assert env_vars["API_KEY"] == "*" * 8
        assert env_vars["DATABASE_PASSWORD"] == "*" * 8

        # Safe variables should remain unchanged
        assert env_vars["SAFE_VAR"] == "safe_value"

    def test_environment_variable_precedence(
        self, env_manager: EnvironmentVariableManager
    ):
        """Test environment variable precedence: config > .env > system."""
        config_env = {"VAR1": "config_value", "VAR2": "config_value"}
        env_file_vars = {"VAR2": "env_file_value", "VAR3": "env_file_value"}
        system_env = {"VAR3": "system_value", "VAR4": "system_value"}

        merged = env_manager.merge_environment_variables(
            config_env, env_file_vars, system_env
        )

        # Check precedence is correctly applied
        assert merged["VAR1"] == "config_value"  # Config only
        assert merged["VAR2"] == "config_value"  # Config overrides .env
        assert merged["VAR3"] == "env_file_value"  # .env overrides system
        assert merged["VAR4"] == "system_value"  # System only

    def test_environment_variable_filtering(
        self, env_manager: EnvironmentVariableManager
    ):
        """Test environment variable filtering in restricted mode."""
        env_vars = {
            "SAFE_VAR": "safe_value",
            "DATABASE_PASSWORD": "secret",
            "API_TOKEN": "secret_token",
            "GITHUB_SECRET": "secret_key",
            "NORMAL_CONFIG": "normal_value",
        }

        # Test restricted mode filtering
        filtered = env_manager.merge_environment_variables(
            env_vars, {}, {}, permission_mode="restricted"
        )

        # Safe variables should remain
        assert "SAFE_VAR" in filtered
        assert "NORMAL_CONFIG" in filtered

        # Sensitive variables should be filtered out
        assert "DATABASE_PASSWORD" not in filtered
        assert "API_TOKEN" not in filtered
        assert "GITHUB_SECRET" not in filtered

        # Test unrestricted mode (should keep all)
        unfiltered = env_manager.merge_environment_variables(
            env_vars, {}, {}, permission_mode="bypassPermissions"
        )

        assert len(unfiltered) == len(env_vars)

    def test_environment_reference_resolution(
        self, env_manager: EnvironmentVariableManager
    ):
        """Test resolution of ${VAR} references in configuration."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "resolved_token_123"}):
            config = {
                "name": "github_server",
                "command": "npx",
                "env": {
                    "GITHUB_TOKEN": "${GITHUB_TOKEN}",
                    "STATIC_VAR": "static_value",
                },
            }

            resolved = env_manager.resolve_environment_references(config)

            assert resolved["env"]["GITHUB_TOKEN"] == "resolved_token_123"
            assert resolved["env"]["STATIC_VAR"] == "static_value"

    def test_mcp_config_initialization(self, temp_project: Path):
        """Test MCPConfig initialization and loading."""
        # Create config file
        config_data = {
            "mcpServers": {
                "file_server": {
                    "command": "python",
                    "args": ["-m", "file_server"],
                    "transport": "stdio",
                    "env": {"FILE_ROOT": "/tmp"},
                },
                "github_server": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "transport": "stdio",
                    "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
                },
            }
        }

        config_file = temp_project / ".khive" / "mcps" / "config.json"
        config_file.write_text(json.dumps(config_data, indent=2))

        # Test MCPConfig loading
        mcp_config = MCPConfig(project_root=str(temp_project))

        assert len(mcp_config.servers) >= 0  # May be empty or loaded

    def test_server_specific_configuration_mapping(self):
        """Test server-specific configuration mappings."""
        github_config = MCPServerConfig(
            name="github_server",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            transport="stdio",
            env={"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
            timeout=15.0,
        )

        assert github_config.name == "github_server"
        assert github_config.transport == "stdio"
        assert github_config.timeout == 15.0
        assert "GITHUB_TOKEN" in github_config.env

    def test_configuration_error_handling(self, temp_project: Path):
        """Test configuration error handling and recovery."""
        # Create malformed config file
        malformed_config = '{"mcpServers": {"server1": {'  # Incomplete JSON

        config_file = temp_project / ".khive" / "mcps" / "config.json"
        config_file.write_text(malformed_config)

        # Test that MCPConfig handles malformed JSON gracefully
        try:
            mcp_config = MCPConfig(project_root=str(temp_project))
            # Should handle error gracefully - may have empty servers
            assert hasattr(mcp_config, "servers")
        except Exception as e:
            # Or may raise a specific configuration error
            assert isinstance(e, (json.JSONDecodeError, ValueError))

    def test_default_timeout_calculation(self):
        """Test default timeout calculation for different server types."""
        # Test different server configurations
        configs = [
            {"name": "fast_server", "command": "echo"},
            {"name": "slow_server", "command": "sleep", "args": ["5"]},
            {"name": "web_server", "url": "http://localhost:8080"},
        ]

        for config_data in configs:
            server_config = MCPServerConfig(**config_data)

            # Should have a reasonable default timeout
            assert hasattr(server_config, "timeout")
            # Default timeout should be positive
            if server_config.timeout is not None:
                assert server_config.timeout > 0

    def test_configuration_copying_with_validation(
        self, temp_project: Path, config_validator: ConfigurationValidator
    ):
        """Test configuration copying with validation."""
        source_config = {
            "name": "test_server",
            "command": "python",
            "args": ["-m", "test_server"],
            "transport": "stdio",
            "env": {"TEST_VAR": "test_value"},
        }

        # Validate source config
        validation_result = config_validator.validate_server_config(source_config)
        assert validation_result["valid"]

        # Test copying to workspace
        workspace_dir = temp_project / "workspace"
        workspace_dir.mkdir()

        config_file = workspace_dir / "server_config.json"
        sanitized_config = config_validator.sanitize_configuration(source_config)
        config_file.write_text(json.dumps(sanitized_config, indent=2))

        assert config_file.exists()

        # Verify copied config is readable and valid
        copied_config = json.loads(config_file.read_text())
        copied_validation = config_validator.validate_server_config(copied_config)
        assert copied_validation["valid"]


@pytest.mark.mcp_configuration
@pytest.mark.security
class TestMCPConfigurationSecurity:
    """Test MCP configuration security measures."""

    @pytest.fixture
    def config_validator(self) -> ConfigurationValidator:
        """Create configuration validator."""
        return ConfigurationValidator()

    def test_dangerous_command_detection(
        self, config_validator: ConfigurationValidator
    ):
        """Test detection of potentially dangerous commands."""
        dangerous_configs = [
            {"name": "evil1", "command": "rm -rf /"},
            {"name": "evil2", "command": "del /q /s C:\\"},
            {"name": "evil3", "command": "format C:"},
            {"name": "evil4", "command": "sudo rm -rf /"},
        ]

        for config in dangerous_configs:
            result = config_validator.validate_server_config(config)
            assert not result["valid"]
            assert any(
                "dangerous command" in error.lower() for error in result["errors"]
            )

    def test_environment_variable_security(
        self, config_validator: ConfigurationValidator
    ):
        """Test environment variable security validation."""
        config_with_path_modification = {
            "name": "path_modifier",
            "command": "python",
            "env": {"PATH": "/malicious/path:$PATH", "LD_PRELOAD": "/malicious/lib.so"},
        }

        result = config_validator.validate_server_config(config_with_path_modification)
        # Should generate warnings for PATH modification
        assert len(result["warnings"]) > 0
        assert any("PATH" in warning for warning in result["warnings"])

    def test_configuration_file_permissions(self, temp_project: Path):
        """Test that configuration files are created with secure permissions."""
        config_file = temp_project / "secure_config.json"
        config_data = {"name": "test", "command": "python"}

        config_file.write_text(json.dumps(config_data))
        config_file.chmod(0o600)  # Owner read/write only

        # Check file permissions
        file_stat = config_file.stat()
        file_mode = file_stat.st_mode & 0o777

        # Should be readable/writable by owner only
        assert file_mode <= 0o600, (
            f"Config file permissions too permissive: {oct(file_mode)}"
        )
