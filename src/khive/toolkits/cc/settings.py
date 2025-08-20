# SPDX-License-Identifier: Apache-2.0

from pydantic import field_validator
from pydantic_settings import SettingsConfigDict

from ..base.settings import BaseKhiveSettings


class CCSettings(BaseKhiveSettings):
    """Configuration settings for Claude Code flows."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local", ".secrets.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="KHIVE_CC_",
        check_fields=False,
    )

    # project settings
    CLI_THEME: str = "dark"

    # model settings
    PERMISSION_MODE: str = "acceptEdits"
    MODEL: str = "sonnet"

    # orchestrator settings
    ORCHESTRATOR_VERBOSE: bool = True
    ORCHESTRATOR_AUTO_FINISH: bool = True
    ORCHESTRATOR_SKIP_PERMISSIONS: bool = False
    ORCHESTRATOR_MODEL: str | None = None

    # task settings
    TASK_VERBOSE: bool = False
    TASK_AUTO_FINISH: bool = False
    TASK_SKIP_PERMISSIONS: bool = False
    TASK_MODEL: str = "sonnet"

    @field_validator(
        "ORCHESTRATOR_VERBOSE",
        "ORCHESTRATOR_AUTO_FINISH",
        "ORCHESTRATOR_SKIP_PERMISSIONS",
        "TASK_VERBOSE",
        "TASK_AUTO_FINISH",
        "TASK_SKIP_PERMISSIONS",
        mode="before",
    )
    def parse_bool(cls, value):
        """Parse boolean values from environment variables."""
        if isinstance(value, str):
            value = value.lower() in ("true", "1", "yes")
        return value


cc_settings = CCSettings()
CCSettings._instance = cc_settings

__all__ = ("CCSettings", "cc_settings")
