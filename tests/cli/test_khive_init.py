from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    import tomllib  # py311+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


# Make the src directory importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from khive.cli.khive_init import (
    CustomStepConfig,
    InitConfig,
    InitCommand,
    main,
)


@pytest.fixture
def mock_project_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def init_command():
    return InitCommand()


@pytest.fixture
def mock_cli_args_default(mock_project_root: Path):
    return argparse.Namespace(
        project_root=mock_project_root,
        json_output=False,
        dry_run=False,
        step=None,
        verbose=False,
        stack=None,
        extra=None,
    )


class TestInitConfig:
    """Test InitConfig dataclass."""

    def test_init_config_creation(self, mock_project_root: Path):
        config = InitConfig(project_root=mock_project_root)
        assert config.project_root == mock_project_root
        assert config.ignore_missing_optional_tools is False
        assert config.disable_auto_stacks == []
        assert config.force_enable_steps == []
        assert config.custom_steps == {}
        assert config.steps_to_run_explicitly is None
        assert config.stack is None
        assert config.extra is None


class TestCustomStepConfig:
    """Test CustomStepConfig dataclass."""

    def test_custom_step_config_creation(self):
        config = CustomStepConfig(
            cmd="echo hello", run_if="file_exists:README.md", cwd="subdir"
        )
        assert config.cmd == "echo hello"
        assert config.run_if == "file_exists:README.md"
        assert config.cwd == "subdir"

    def test_custom_step_config_defaults(self):
        config = CustomStepConfig()
        assert config.cmd is None
        assert config.run_if is None
        assert config.cwd is None


class TestInitCommand:
    """Test InitCommand class methods."""

    def test_init_command_creation(self, init_command):
        assert init_command.command_name == "init"
        assert init_command.description == "Initialize project dependencies and tooling"
        assert init_command.config_filename == "init.toml"
        assert "tools" in init_command.builtin_steps
        assert "python" in init_command.builtin_steps
        assert "npm" in init_command.builtin_steps
        assert "rust" in init_command.builtin_steps
        assert "husky" in init_command.builtin_steps

    def test_default_config(self, init_command):
        default = init_command.default_config
        assert default["ignore_missing_optional_tools"] is False
        assert default["disable_auto_stacks"] == []
        assert default["force_enable_steps"] == []
        assert default["custom_steps"] == {}

    def test_create_config_basic(self, init_command, mock_cli_args_default):
        with patch.object(init_command, "_load_command_config", return_value={}):
            config = init_command._create_config(mock_cli_args_default)
            assert isinstance(config, InitConfig)
            assert config.project_root == mock_cli_args_default.project_root

    def test_create_config_with_custom_steps(self, init_command, mock_cli_args_default):
        mock_loaded_config = {
            "custom_steps": {
                "test_step": {
                    "cmd": "echo test",
                    "run_if": "file_exists:test.txt",
                    "cwd": "test_dir",
                }
            }
        }
        with patch.object(
            init_command, "_load_command_config", return_value=mock_loaded_config
        ):
            config = init_command._create_config(mock_cli_args_default)
            assert "test_step" in config.custom_steps
            assert isinstance(config.custom_steps["test_step"], CustomStepConfig)
            assert config.custom_steps["test_step"].cmd == "echo test"

    def test_check_condition_file_exists_true(self, init_command, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.touch()
        assert init_command._check_condition("file_exists:test.txt", tmp_path) is True

    def test_check_condition_file_exists_false(self, init_command, tmp_path):
        assert (
            init_command._check_condition("file_exists:nonexistent.txt", tmp_path)
            is False
        )

    def test_check_condition_tool_exists(self, init_command, tmp_path):
        with patch("khive.cli.khive_init.check_tool_available", return_value=True):
            assert init_command._check_condition("tool_exists:python", tmp_path) is True

        with patch("khive.cli.khive_init.check_tool_available", return_value=False):
            assert (
                init_command._check_condition("tool_exists:nonexistent", tmp_path)
                is False
            )

    def test_check_condition_no_expression(self, init_command, tmp_path):
        assert init_command._check_condition(None, tmp_path) is True
        assert init_command._check_condition("", tmp_path) is True

    def test_check_condition_unknown_type(self, init_command, tmp_path):
        with patch("khive.cli.khive_init.warn_msg") as mock_warn:
            result = init_command._check_condition("unknown_type:value", tmp_path)
            assert result is False
            mock_warn.assert_called_once()

    def test_determine_steps_explicit(self, init_command, mock_project_root):
        config = InitConfig(
            project_root=mock_project_root, steps_to_run_explicitly=["tools", "python"]
        )
        steps = init_command._determine_steps_to_run(config)
        assert list(steps.keys()) == ["tools", "python"]
        assert steps["tools"][0] == "builtin"
        assert steps["python"][0] == "builtin"

    def test_determine_steps_stack_specific(self, init_command, mock_project_root):
        config = InitConfig(project_root=mock_project_root, stack="uv")
        with patch.object(Path, "exists", return_value=False):
            steps = init_command._determine_steps_to_run(config)
            assert "tools" in steps
            assert "python" in steps

    def test_determine_steps_auto_detection_python(
        self, init_command, mock_project_root
    ):
        config = InitConfig(project_root=mock_project_root)

        def mock_exists(self):
            return str(self).endswith("pyproject.toml")

        with patch.object(Path, "exists", mock_exists):
            steps = init_command._determine_steps_to_run(config)
            assert "tools" in steps
            assert "python" in steps

    def test_determine_steps_auto_detection_npm(self, init_command, mock_project_root):
        config = InitConfig(project_root=mock_project_root)

        def mock_exists(self):
            return str(self).endswith("package.json")

        with patch.object(Path, "exists", mock_exists):
            steps = init_command._determine_steps_to_run(config)
            assert "tools" in steps
            assert "npm" in steps
            assert "husky" in steps

    def test_determine_steps_disabled_stacks(self, init_command, mock_project_root):
        config = InitConfig(
            project_root=mock_project_root, disable_auto_stacks=["python"]
        )

        def mock_exists(self):
            return str(self).endswith("pyproject.toml")

        with patch.object(Path, "exists", mock_exists):
            steps = init_command._determine_steps_to_run(config)
            assert "tools" in steps
            assert "python" not in steps

    def test_dry_run_step_builtin(self, init_command, mock_project_root):
        config = InitConfig(project_root=mock_project_root, dry_run=True)
        result = init_command._dry_run_step("tools", "builtin", None, config)
        assert result["name"] == "tools"
        assert result["status"] == "DRY_RUN"
        assert "Would run builtin step 'tools'" in result["message"]

    def test_dry_run_step_custom(self, init_command, mock_project_root):
        config = InitConfig(project_root=mock_project_root, dry_run=True)
        custom_cfg = CustomStepConfig(cmd="echo hello", cwd="subdir")
        result = init_command._dry_run_step("custom", "custom", custom_cfg, config)
        assert result["name"] == "custom"
        assert result["status"] == "DRY_RUN"
        assert "Would run custom step 'custom'" in result["message"]
        assert "echo hello" in result["message"]


class TestAsyncMethods:
    """Test async methods of InitCommand."""

    @pytest.mark.asyncio
    async def test_run_shell_command_success(self, init_command, tmp_path):
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"success output", b"")
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_shell", return_value=mock_process):
            result = await init_command._run_shell_command_async(
                "echo hello", cwd=tmp_path, step_name="test"
            )

        assert result["name"] == "test"
        assert result["status"] == "OK"
        assert result["stdout"] == "success output"
        assert result["return_code"] == 0

    @pytest.mark.asyncio
    async def test_run_shell_command_failure(self, init_command, tmp_path):
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"error output")
        mock_process.returncode = 1

        with patch("asyncio.create_subprocess_shell", return_value=mock_process):
            result = await init_command._run_shell_command_async(
                "exit 1", cwd=tmp_path, step_name="test"
            )

        assert result["name"] == "test"
        assert result["status"] == "FAILED"
        assert result["stderr"] == "error output"
        assert result["return_code"] == 1

    @pytest.mark.asyncio
    async def test_run_custom_step_condition_not_met(
        self, init_command, mock_project_root
    ):
        config = InitConfig(project_root=mock_project_root)
        custom_cfg = CustomStepConfig(
            cmd="echo hello", run_if="file_exists:nonexistent.txt"
        )

        result = await init_command._run_custom_step("test", custom_cfg, config)

        assert result["name"] == "test"
        assert result["status"] == "SKIPPED"
        assert "Condition" in result["message"]

    @pytest.mark.asyncio
    async def test_run_custom_step_no_command(self, init_command, mock_project_root):
        config = InitConfig(project_root=mock_project_root)
        custom_cfg = CustomStepConfig(cmd=None)

        result = await init_command._run_custom_step("test", custom_cfg, config)

        assert result["name"] == "test"
        assert result["status"] == "SKIPPED"
        assert "No command defined" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_step_tools_all_present(self, init_command, mock_project_root):
        config = InitConfig(project_root=mock_project_root)

        with patch("khive.cli.khive_init.check_tool_available", return_value=True):
            with patch.object(Path, "exists", return_value=False):  # No project files
                result = await init_command._step_tools(config)

        assert result["name"] == "tools"
        assert result["status"] == "OK"
    @pytest.mark.asyncio
    async def test_step_tools_missing_required(self, init_command, mock_project_root):
        config = InitConfig(project_root=mock_project_root)

        def mock_tool_check(tool):
            return tool != "uv"  # uv is missing

        def mock_exists(self):
            return str(self).endswith("pyproject.toml")  # Python project detected

        with patch("khive.cli.khive_init.check_tool_available", side_effect=mock_tool_check):
            with patch.object(Path, "exists", mock_exists):
                result = await init_command._step_tools(config)

        assert result["name"] == "tools"
        assert result["status"] == "FAILED"
        assert "Missing required tools" in result["message"]

    @pytest.mark.asyncio
    async def test_step_python_no_pyproject(self, init_command, mock_project_root):
        config = InitConfig(project_root=mock_project_root)

        with patch.object(Path, "exists", return_value=False):
            result = await init_command._step_python(config)

        assert result["name"] == "python"
        assert result["status"] == "SKIPPED"
        assert "No pyproject.toml found" in result["message"]

    @pytest.mark.asyncio
    async def test_step_python_success(self, init_command, mock_project_root):
        config = InitConfig(project_root=mock_project_root)

        def mock_exists(self):
            return str(self).endswith("pyproject.toml")

        mock_result = {"name": "python", "status": "OK", "message": "uv sync completed"}

        with patch.object(Path, "exists", mock_exists):
            with patch("khive.cli.khive_init.check_tool_available", return_value=True):
                with patch.object(
                    init_command, "_run_shell_command_async", return_value=mock_result
                ):
                    result = await init_command._step_python(config)

        assert result["name"] == "python"
        assert result["status"] == "OK"

    @pytest.mark.asyncio
    async def test_step_npm_no_package_json(self, init_command, mock_project_root):
        config = InitConfig(project_root=mock_project_root)

        with patch.object(Path, "exists", return_value=False):
            result = await init_command._step_npm(config)

        assert result["name"] == "npm"
        assert result["status"] == "SKIPPED"
        assert "No package.json found" in result["message"]

    @pytest.mark.asyncio
    async def test_step_rust_no_cargo_toml(self, init_command, mock_project_root):
        config = InitConfig(project_root=mock_project_root)

        with patch.object(Path, "exists", return_value=False):
            result = await init_command._step_rust(config)

        assert result["name"] == "rust"
        assert result["status"] == "SKIPPED"
        assert "No Cargo.toml found" in result["message"]


class TestMainFunction:
    """Test the main entry point function."""

    def test_main_function_exists(self):
        # Just verify the main function can be called
        assert callable(main)

    @patch("khive.cli.khive_init.InitCommand")
    def test_main_calls_init_command(self, mock_init_command_class):
        mock_command = MagicMock()
        mock_init_command_class.return_value = mock_command

        main(["--help"])

        mock_init_command_class.assert_called_once()
        mock_command.run.assert_called_once_with(["--help"])
