from functools import partial
from pathlib import Path

import aiofiles
from lionagi import iModel

from .settings import cc_settings

_get_cc_imodel = partial(
    iModel,
    provider="claude_code",
    endpoint=cc_settings.ENDPOINT,
    repo=cc_settings.REPO_LOCAL,
    cli_display_theme=cc_settings.CLI_THEME,
)


def _calculate_workspace_depth(workspace: str) -> int:
    if not workspace:
        return None
    if "/" not in workspace:
        return 1
    return workspace.count("/") + 1


def create_orchestrator_cc_model(
    model: str = None,
    verbose_output: bool = None,
    permission_mode=None,
    auto_finish: bool = None,
):
    """
    Create a task orchestrator for Claude Code. Orchestrator will automatically gain
    project repo root access and uses the root project .claude/settings for configuration.

    - orchestrator settings include:
     - model: the model to use for the orchestrator (sonnet, opus)
     - verbose_output: whether to print verbose output in cli
     - permission_mode: bypassPermissions, default, acceptEdits
     - auto_finish: whether to automatically enforce result message as final output
    """
    model = model or cc_settings.ORCHESTRATOR_MODEL or cc_settings.MODEL
    verbose_output = (
        verbose_output
        if verbose_output is not None
        else cc_settings.ORCHESTRATOR_VERBOSE
    )
    permission_mode = (
        "bypassPermissions"
        if cc_settings.ORCHESTRATOR_SKIP_PERMISSIONS
        else permission_mode or cc_settings.PERMISSION_MODE
    )
    auto_finish = (
        auto_finish if auto_finish is not None else cc_settings.ORCHESTRATOR_AUTO_FINISH
    )

    return _get_cc_imodel(
        model=model,
        verbose_output=verbose_output,
        permission_mode=permission_mode,
        auto_finish=auto_finish,
    )


def create_task_cc_model(
    subdir: str = None,
    model: str = None,
    verbose_output: bool = None,
    permission_mode: str = None,
    auto_finish: bool = None,
    requires_root: bool = False,
):
    """Create a task iModel for Claude Code.

    Typically for analysis type of roles, we assign them a dedicated workspace
    and grant read access to the project repo root. They are free to write and
    edit within their workspace, but cannot write outside of it. They typically
    are granted with only safe commands or khive native commands.

    For tasks that require root access, e.g., devops, we can set requires_root=True
    implementer, tester for example, in this case, the subdir is not the workspace/subdir,
    it is root/subdir, and the iModel will have full read/write access to the root/subdir
    if subdir is None, it will be root/
    """

    verbose_output = (
        verbose_output if verbose_output is not None else cc_settings.TASK_VERBOSE
    )
    if permission_mode is None:
        if cc_settings.TASK_SKIP_PERMISSIONS:
            permission_mode = "bypassPermissions"
        else:
            permission_mode = cc_settings.PERMISSION_MODE
    model = model or cc_settings.TASK_MODEL or cc_settings.MODEL
    auto_finish = (
        auto_finish if auto_finish is not None else cc_settings.TASK_AUTO_FINISH
    )

    ws_, add_dir = None, None
    if requires_root:
        ws_ = subdir
        add_dir = None
        if ws_:
            ws_depth = _calculate_workspace_depth(ws_)
            add_dir = "../" * ws_depth if ws_depth else None
    else:
        ws_ = cc_settings.WORKSPACE
        if subdir:
            ws_ = f"{ws_}/{subdir}"

        ws_depth = _calculate_workspace_depth(ws_)
        add_dir = "../" * ws_depth
    return (
        _get_cc_imodel(
            model=model,
            ws=ws_,
            verbose_output=verbose_output,
            permission_mode=permission_mode,
            auto_finish=auto_finish,
            add_dir=add_dir,
        ),
        ws_,
    )


async def create_cc(
    as_orchestrator: bool = False,
    subdir: str = None,
    model: str = None,
    verbose_output: bool = None,
    permission_mode: str = None,
    auto_finish: bool = None,
    requires_root: bool = False,
    overwrite_config: bool = False,
    copy_mcp_config_from: str | Path = None,
    copy_settings_from: str | Path = None,
    copy_claude_md_from: str | Path = None,
) -> iModel:
    if copy_mcp_config_from:
        if requires_root or as_orchestrator:
            raise ValueError(
                "copy_mcp_config cannot be used with requires_root or as_orchestrator. "
                "We assume mcp config is already set in root"
            )
        if not Path(copy_mcp_config_from).exists():
            raise ValueError("copy_mcp_config must be a valid file path")

    if as_orchestrator:
        return create_orchestrator_cc_model(
            model=model,
            verbose_output=verbose_output,
            permission_mode=permission_mode,
            auto_finish=auto_finish,
        )
    imodel, ws = create_task_cc_model(
        subdir=subdir,
        model=model,
        verbose_output=verbose_output,
        permission_mode=permission_mode,
        auto_finish=auto_finish,
        requires_root=requires_root,
    )
    if ws:
        from lionagi.utils import create_path

        ws_fp = Path(ws)

        if copy_mcp_config_from:
            if overwrite_config or not (ws_fp / ".mcp.json").exists():
                fp = create_path(ws, ".mcp.json", dir_exist_ok=True, file_exist_ok=True)
                src_mcp = Path(copy_mcp_config_from)

                async with (
                    aiofiles.open(src_mcp, "r") as src_file,
                    aiofiles.open(fp, "w") as dest_file,
                ):
                    content = await src_file.read()
                    await dest_file.write(content)

        if copy_settings_from:
            if overwrite_config or not (ws_fp / ".claude/settings.json").exists():
                fp = create_path(
                    ws, ".claude/settings.json", dir_exist_ok=True, file_exist_ok=True
                )
                src_settings = Path(copy_settings_from)

                async with (
                    aiofiles.open(src_settings, "r") as src_file,
                    aiofiles.open(fp, "w") as dest_file,
                ):
                    content = await src_file.read()
                    await dest_file.write(content)

        if copy_claude_md_from:
            if overwrite_config or not (ws_fp / "CLAUDE.md").exists():
                fp = create_path(ws, "CLAUDE.md", dir_exist_ok=True, file_exist_ok=True)
                src_claude_md = Path(copy_claude_md_from)

                async with (
                    aiofiles.open(src_claude_md, "r") as src_file,
                    aiofiles.open(fp, "w") as dest_file,
                ):
                    content = await src_file.read()
                    await dest_file.write(content)

    return imodel
