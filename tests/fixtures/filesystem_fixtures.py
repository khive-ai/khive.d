"""Filesystem testing fixtures for file operations and workspace management."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import mock_open, patch

import pytest


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a comprehensive temporary workspace with realistic project structure."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create standard project directories
    directories = [
        "src/khive",
        "tests/unit",
        "tests/integration",
        "tests/fixtures",
        "docs",
        "scripts",
        "config",
        "logs",
        "cache",
        ".git",
        ".khive/workspaces",
        ".khive/sessions",
        "flows",
        "data/logs",
    ]

    for dir_path in directories:
        (workspace / dir_path).mkdir(parents=True, exist_ok=True)

    # Create essential files
    files = {
        "pyproject.toml": """
[project]
name = "test-workspace"
version = "0.1.0"
description = "Test workspace"
requires-python = ">=3.10"
dependencies = ["khive"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
        """.strip(),
        "README.md": "# Test Workspace\\n\\nA test workspace for khive testing.",
        ".gitignore": """
__pycache__/
*.pyc
.venv/
.env
logs/
cache/
*.log
        """.strip(),
        "src/khive/__init__.py": '"""Test khive module."""\\n__version__ = "0.1.0"',
        ".khive/config.yaml": """
project:
  name: test-workspace
  version: 0.1.0

testing:
  enabled: true
  coverage_threshold: 85
        """.strip(),
        "tests/conftest.py": """
import pytest

@pytest.fixture
def sample_data():
    return {"test": "data"}
        """.strip(),
    }

    for file_path, content in files.items():
        file_obj = workspace / file_path
        file_obj.parent.mkdir(parents=True, exist_ok=True)
        file_obj.write_text(content)

    yield workspace


@pytest.fixture
def mock_filesystem():
    """Mock filesystem operations with configurable behavior."""

    class MockFileSystem:
        def __init__(self):
            self.files = {}
            self.directories = set()
            self.operations = []  # Track operations for testing

        def add_file(self, path: str, content: str = ""):
            """Add a mock file."""
            self.files[path] = content
            # Add parent directories
            parent = str(Path(path).parent)
            while parent != "." and parent not in self.directories:
                self.directories.add(parent)
                parent = str(Path(parent).parent)

        def add_directory(self, path: str):
            """Add a mock directory."""
            self.directories.add(path)

        def exists(self, path: str) -> bool:
            """Check if path exists."""
            return path in self.files or path in self.directories

        def read_text(self, path: str) -> str:
            """Read file content."""
            if path in self.files:
                return self.files[path]
            raise FileNotFoundError(f"File not found: {path}")

        def write_text(self, path: str, content: str):
            """Write file content."""
            self.files[path] = content
            self.operations.append(("write", path, content))

        def delete(self, path: str):
            """Delete file or directory."""
            if path in self.files:
                del self.files[path]
            elif path in self.directories:
                self.directories.remove(path)
            self.operations.append(("delete", path))

    mock_fs = MockFileSystem()

    # Setup common project files
    mock_fs.add_file("pyproject.toml", "[project]\\nname = 'test'")
    mock_fs.add_file("README.md", "# Test Project")
    mock_fs.add_directory("src")
    mock_fs.add_directory("tests")

    with (
        patch("pathlib.Path.exists", side_effect=mock_fs.exists),
        patch("pathlib.Path.read_text", side_effect=mock_fs.read_text),
        patch("pathlib.Path.write_text", side_effect=mock_fs.write_text),
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.unlink", side_effect=mock_fs.delete),
    ):
        yield mock_fs


@pytest.fixture
def file_operation_tracker():
    """Track file operations for testing."""

    class FileOperationTracker:
        def __init__(self):
            self.operations = []

        def track_open(self, filename, mode="r", **kwargs):
            """Track file open operations."""
            self.operations.append(
                {
                    "operation": "open",
                    "filename": filename,
                    "mode": mode,
                    "kwargs": kwargs,
                }
            )
            return mock_open()()

        def track_remove(self, path):
            """Track file removal operations."""
            self.operations.append({"operation": "remove", "path": path})

        def track_mkdir(self, path, **kwargs):
            """Track directory creation."""
            self.operations.append(
                {
                    "operation": "mkdir",
                    "path": path,
                    "kwargs": kwargs,
                }
            )

        def get_operations(self, operation_type=None):
            """Get tracked operations."""
            if operation_type:
                return [
                    op for op in self.operations if op["operation"] == operation_type
                ]
            return self.operations.copy()

        def clear(self):
            """Clear tracked operations."""
            self.operations.clear()

    tracker = FileOperationTracker()

    with (
        patch("builtins.open", side_effect=tracker.track_open),
        patch("os.remove", side_effect=tracker.track_remove),
        patch("os.mkdir", side_effect=tracker.track_mkdir),
        patch("pathlib.Path.mkdir", side_effect=tracker.track_mkdir),
    ):
        yield tracker


@pytest.fixture
def git_workspace(temp_workspace: Path) -> Generator[Path, None, None]:
    """Create a git-initialized workspace."""
    import subprocess

    # Initialize git repository
    subprocess.run(["git", "init"], cwd=temp_workspace, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=temp_workspace,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=temp_workspace, check=True
    )

    # Create .gitignore
    gitignore = temp_workspace / ".gitignore"
    gitignore.write_text(
        """
__pycache__/
*.pyc
.venv/
.env
logs/
cache/
*.log
.DS_Store
    """.strip()
    )

    # Initial commit
    subprocess.run(["git", "add", "."], cwd=temp_workspace, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=temp_workspace, check=True
    )

    yield temp_workspace


@pytest.fixture
def workspace_manager():
    """Manage multiple workspaces for testing."""

    class WorkspaceManager:
        def __init__(self, base_path: Path):
            self.base_path = base_path
            self.workspaces = {}

        def create_workspace(self, name: str, template: str = "default") -> Path:
            """Create a new workspace."""
            workspace = self.base_path / name
            workspace.mkdir(exist_ok=True)

            if template == "python":
                self._create_python_workspace(workspace)
            elif template == "khive":
                self._create_khive_workspace(workspace)
            else:
                self._create_default_workspace(workspace)

            self.workspaces[name] = workspace
            return workspace

        def _create_default_workspace(self, path: Path):
            """Create default workspace structure."""
            (path / "src").mkdir(exist_ok=True)
            (path / "tests").mkdir(exist_ok=True)
            (path / "README.md").write_text("# Workspace")

        def _create_python_workspace(self, path: Path):
            """Create Python project workspace."""
            self._create_default_workspace(path)
            (path / "pyproject.toml").write_text(
                """
[project]
name = "workspace"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
            """.strip()
            )

        def _create_khive_workspace(self, path: Path):
            """Create khive-specific workspace."""
            self._create_python_workspace(path)

            # Add khive-specific directories
            khive_dirs = [
                ".khive/workspaces",
                ".khive/sessions",
                "flows",
                "logs",
                "cache",
            ]

            for dir_path in khive_dirs:
                (path / dir_path).mkdir(parents=True, exist_ok=True)

            # Add khive config
            (path / ".khive" / "config.yaml").write_text(
                """
project:
  name: khive-workspace
  type: khive

orchestration:
  enabled: true
  max_agents: 8
            """.strip()
            )

        def get_workspace(self, name: str) -> Path:
            """Get workspace by name."""
            return self.workspaces.get(name)

        def cleanup(self):
            """Cleanup all workspaces."""
            for workspace in self.workspaces.values():
                if workspace.exists():
                    shutil.rmtree(workspace, ignore_errors=True)
            self.workspaces.clear()

    # Use tmp_path fixture through dependency injection
    manager = WorkspaceManager(Path(tempfile.mkdtemp()))

    try:
        yield manager
    finally:
        manager.cleanup()


@pytest.fixture
def file_content_generator():
    """Generate various file contents for testing."""

    class FileContentGenerator:
        @staticmethod
        def python_module(name: str, functions: list[str] = None) -> str:
            """Generate Python module content."""
            functions = functions or ["main"]
            content = [f'"""Module: {name}"""', "", ""]

            for func in functions:
                content.extend(
                    [
                        f"def {func}():",
                        f'    """Function: {func}"""',
                        "    pass",
                        "",
                    ]
                )

            return "\\n".join(content)

        @staticmethod
        def test_module(test_functions: list[str] = None) -> str:
            """Generate test module content."""
            test_functions = test_functions or ["test_example"]
            content = ['"""Test module"""', "", "import pytest", "", ""]

            for func in test_functions:
                content.extend(
                    [
                        f"def {func}():",
                        f'    """Test: {func}"""',
                        "    assert True",
                        "",
                    ]
                )

            return "\\n".join(content)

        @staticmethod
        def config_file(format_type: str = "yaml", data: dict[str, Any] = None) -> str:
            """Generate configuration file content."""
            data = data or {"test": {"enabled": True}}

            if format_type == "yaml":
                import yaml

                return yaml.dump(data)
            elif format_type == "json":
                import json

                return json.dumps(data, indent=2)
            elif format_type == "toml":
                # Simple TOML generation for basic cases
                lines = []
                for section, values in data.items():
                    lines.append(f"[{section}]")
                    for key, value in values.items():
                        if isinstance(value, str):
                            lines.append(f'{key} = "{value}"')
                        else:
                            lines.append(f"{key} = {value}")
                    lines.append("")
                return "\\n".join(lines)
            else:
                return str(data)

        @staticmethod
        def markdown_file(title: str, sections: dict[str, str] = None) -> str:
            """Generate markdown file content."""
            sections = sections or {"Overview": "This is a test document."}

            content = [f"# {title}", ""]

            for section_title, section_content in sections.items():
                content.extend([f"## {section_title}", "", section_content, ""])

            return "\\n".join(content)

    return FileContentGenerator()
