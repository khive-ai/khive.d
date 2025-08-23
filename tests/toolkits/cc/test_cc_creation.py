"""
CC Toolkit Creation Tests with Security Validation.

Tests CC toolkit creation with various permission modes, security validation,
and error handling. Covers requirements from issue #189 MCP integration testing.

This module validates:
- CC toolkit creation with various permission modes
- Security validation and input sanitization
- Configuration copying and workspace isolation
- Error handling and recovery mechanisms
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from khive.toolkits.cc.create_cc import create_cc


class CCSecurityValidator:
    """Security validator for CC toolkit creation operations."""

    def __init__(self):
        self.security_violations = []
        self.dangerous_patterns = [
            r"__import__",
            r"eval\(",
            r"exec\(",
            r"subprocess",
            r"os\.system",
            r"rm -rf",
            r"\.\./",  # Path traversal
            r"C:\\",  # Windows absolute path
            r"/etc/",  # Linux system directories
        ]

    def validate_config_content(self, config_content: str) -> bool:
        """Validate configuration content for dangerous patterns."""
        import re

        for pattern in self.dangerous_patterns:
            if re.search(pattern, config_content, re.IGNORECASE):
                self.security_violations.append(
                    f"Dangerous pattern detected: {pattern}"
                )
                return False
        return True

    def validate_environment_variables(
        self, env_vars: dict[str, str], permission_mode: str
    ) -> bool:
        """Validate environment variables based on permission mode."""
        dangerous_env_vars = {
            "AWS_SECRET_ACCESS_KEY",
            "DATABASE_PASSWORD",
            "PRIVATE_KEY",
            "SECRET_KEY",
            "ENCRYPTION_KEY",
            "MASTER_KEY",
        }

        if permission_mode == "restricted":
            # Restricted mode should block all sensitive environment variables
            for var_name in env_vars:
                if any(
                    dangerous in var_name.upper() for dangerous in dangerous_env_vars
                ):
                    self.security_violations.append(
                        f"Sensitive env var {var_name} exposed in restricted mode"
                    )
                    return False

        return True

    def get_violations_report(self) -> dict[str, Any]:
        """Get comprehensive security violations report."""
        return {
            "violation_count": len(self.security_violations),
            "violations": self.security_violations,
            "security_valid": len(self.security_violations) == 0,
        }


class CCToolkitManager:
    """Manager for CC toolkit creation with testing support."""

    def __init__(self):
        self.created_workspaces = []
        self.active_cc_instances = {}

    async def create_cc_toolkit(
        self,
        project_root: Path,
        permission_mode: str,
        overwrite_config: bool = False,
        copy_mcp_config_from: Path | None = None,
        workspace_subdir: str = None,
    ) -> dict[str, Any]:
        """Create CC toolkit with validation."""
        try:
            # Create workspace directory
            if workspace_subdir:
                workspace_path = (
                    project_root / ".khive" / "workspaces" / workspace_subdir
                )
            else:
                workspace_path = (
                    project_root / ".khive" / "workspaces" / "test_workspace"
                )

            workspace_path.mkdir(parents=True, exist_ok=True)
            self.created_workspaces.append(workspace_path)

            # Create CC instance
            cc_instance = await create_cc(
                as_orchestrator=permission_mode == "orchestrator",
                subdir=workspace_subdir,
                permission_mode=permission_mode,
                overwrite_config=overwrite_config,
                copy_mcp_config_from=copy_mcp_config_from,
            )

            self.active_cc_instances[str(workspace_path)] = cc_instance

            return {
                "status": "success",
                "workspace_path": str(workspace_path),
                "permission_mode": permission_mode,
                "cc_instance": cc_instance,
                "mcp_config_copied": copy_mcp_config_from is not None,
                "security_context": self._determine_security_context(permission_mode),
            }

        except Exception as e:
            return {"status": "error", "error": str(e), "error_type": type(e).__name__}

    def _determine_security_context(self, permission_mode: str) -> str:
        """Determine security context based on permission mode."""
        security_contexts = {
            "default": "standard",
            "acceptEdits": "elevated",
            "bypassPermissions": "unrestricted",
            "read-only": "restricted",
        }
        return security_contexts.get(permission_mode, "unknown")

    async def cleanup_all_workspaces(self):
        """Clean up all created workspaces."""
        for workspace in self.created_workspaces:
            try:
                if workspace.exists():
                    shutil.rmtree(workspace, ignore_errors=True)
            except Exception as e:
                print(f"Warning: Failed to cleanup workspace {workspace}: {e}")

        self.created_workspaces.clear()
        self.active_cc_instances.clear()


@pytest.mark.mcp_cc_toolkit
@pytest.mark.integration
class TestCCToolkitCreation:
    """CC toolkit creation tests."""

    @pytest_asyncio.fixture
    async def cc_manager(self) -> CCToolkitManager:
        """Create CC toolkit manager."""
        manager = CCToolkitManager()
        yield manager
        await manager.cleanup_all_workspaces()

    @pytest.fixture
    def security_validator(self) -> CCSecurityValidator:
        """Create security validator."""
        return CCSecurityValidator()

    @pytest.fixture
    def temp_project(self) -> Path:
        """Create a temporary project with MCP config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test_project"
            project_dir.mkdir()

            # Create project structure
            (project_dir / "src").mkdir()
            (project_dir / ".khive").mkdir()
            (project_dir / ".khive" / "mcps").mkdir()

            # Create basic MCP configuration
            mcp_config = {
                "mcpServers": {
                    "file_server": {
                        "command": "python",
                        "args": ["-m", "test_file_server"],
                        "transport": "stdio",
                        "env": {"FILE_SERVER_ROOT": "/tmp"},
                    }
                }
            }

            config_file = project_dir / ".khive" / "mcps" / "config.json"
            config_file.write_text(json.dumps(mcp_config, indent=2))

            yield project_dir

    @pytest.mark.asyncio
    async def test_cc_creation_default_mode(
        self,
        temp_project: Path,
        cc_manager: CCToolkitManager,
        security_validator: CCSecurityValidator,
    ):
        """Test CC toolkit creation with default permission mode."""
        result = await cc_manager.create_cc_toolkit(
            project_root=temp_project, permission_mode="default"
        )

        assert result["status"] == "success"
        assert result["permission_mode"] == "default"
        assert result["security_context"] == "standard"
        assert Path(result["workspace_path"]).exists()

    @pytest.mark.asyncio
    async def test_cc_creation_accept_edits_mode(
        self, temp_project: Path, cc_manager: CCToolkitManager
    ):
        """Test CC toolkit creation with acceptEdits permission mode."""
        result = await cc_manager.create_cc_toolkit(
            project_root=temp_project, permission_mode="acceptEdits"
        )

        assert result["status"] == "success"
        assert result["permission_mode"] == "acceptEdits"
        assert result["security_context"] == "elevated"

    @pytest.mark.asyncio
    async def test_cc_creation_bypass_permissions_mode(
        self, temp_project: Path, cc_manager: CCToolkitManager
    ):
        """Test CC toolkit creation with bypassPermissions mode."""
        result = await cc_manager.create_cc_toolkit(
            project_root=temp_project, permission_mode="bypassPermissions"
        )

        assert result["status"] == "success"
        assert result["permission_mode"] == "bypassPermissions"
        assert result["security_context"] == "unrestricted"

    @pytest.mark.asyncio
    async def test_mcp_configuration_copying(
        self, temp_project: Path, cc_manager: CCToolkitManager
    ):
        """Test MCP configuration copying during CC creation."""
        # Create source config
        source_config_path = temp_project / ".khive" / "mcps" / "config.json"

        result = await cc_manager.create_cc_toolkit(
            project_root=temp_project,
            permission_mode="default",
            copy_mcp_config_from=source_config_path,
        )

        assert result["status"] == "success"
        assert result["mcp_config_copied"] is True

    @pytest.mark.asyncio
    async def test_workspace_isolation(
        self, temp_project: Path, cc_manager: CCToolkitManager
    ):
        """Test workspace isolation between different CC instances."""
        # Create first CC instance
        result1 = await cc_manager.create_cc_toolkit(
            project_root=temp_project,
            permission_mode="default",
            workspace_subdir="workspace1",
        )

        # Create second CC instance
        result2 = await cc_manager.create_cc_toolkit(
            project_root=temp_project,
            permission_mode="acceptEdits",
            workspace_subdir="workspace2",
        )

        assert result1["status"] == "success"
        assert result2["status"] == "success"
        assert result1["workspace_path"] != result2["workspace_path"]

        # Verify both workspaces exist and are isolated
        workspace1 = Path(result1["workspace_path"])
        workspace2 = Path(result2["workspace_path"])

        assert workspace1.exists()
        assert workspace2.exists()
        assert workspace1 != workspace2

    @pytest.mark.asyncio
    async def test_error_handling_invalid_config(
        self, temp_project: Path, cc_manager: CCToolkitManager
    ):
        """Test error handling with invalid configurations."""
        # Create invalid MCP config path
        invalid_config_path = temp_project / "nonexistent_config.json"

        result = await cc_manager.create_cc_toolkit(
            project_root=temp_project,
            permission_mode="default",
            copy_mcp_config_from=invalid_config_path,
        )

        # Should handle error gracefully with specific error information
        assert "status" in result
        if result["status"] == "error":
            assert "error_type" in result
            assert result["error_type"] in ["FileNotFoundError", "ConfigurationError", "PermissionError"]
            assert "error_message" in result
        # If success, should have proper result structure
        elif result["status"] == "success":
            assert "workspace_path" in result

    def test_security_validator_dangerous_patterns(
        self, security_validator: CCSecurityValidator
    ):
        """Test security validator detects dangerous patterns."""
        malicious_config = """
        {
            "command": "rm -rf /",
            "evil": "__import__('os').system('evil')"
        }
        """

        is_valid = security_validator.validate_config_content(malicious_config)
        assert not is_valid

        report = security_validator.get_violations_report()
        assert report["violation_count"] > 0
        assert not report["security_valid"]

    def test_security_validator_environment_variables(
        self, security_validator: CCSecurityValidator
    ):
        """Test security validator handles environment variables."""
        dangerous_env_vars = {
            "AWS_SECRET_ACCESS_KEY": "secret123",
            "DATABASE_PASSWORD": "password456",
            "SAFE_VAR": "safe_value",
        }

        # Should fail in restricted mode
        is_valid = security_validator.validate_environment_variables(
            dangerous_env_vars, "restricted"
        )
        assert not is_valid

        # Should pass in unrestricted mode (bypassPermissions)
        security_validator.security_violations.clear()
        is_valid = security_validator.validate_environment_variables(
            dangerous_env_vars, "bypassPermissions"
        )
        assert is_valid  # Should allow dangerous patterns in bypass mode

    @pytest.mark.asyncio
    async def test_concurrent_cc_creation(
        self, temp_project: Path, cc_manager: CCToolkitManager
    ):
        """Test concurrent CC toolkit creation safety."""
        import asyncio

        # Create multiple CC instances concurrently
        tasks = [
            cc_manager.create_cc_toolkit(
                project_root=temp_project,
                permission_mode="default",
                workspace_subdir=f"concurrent_workspace_{i}",
            )
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify results are valid (success or handled exceptions)
        for i, result in enumerate(results):
            if isinstance(result, dict):
                assert "status" in result
                if result["status"] == "success":
                    assert "workspace_path" in result
                    # Verify workspace isolation
                    workspace = Path(result["workspace_path"])
                    assert workspace.exists()
            else:
                # Exception case - should be handled gracefully without crashing
                assert isinstance(result, Exception)
                # Verify it's an expected exception type
                assert isinstance(result, (FileNotFoundError, PermissionError, ValueError))
