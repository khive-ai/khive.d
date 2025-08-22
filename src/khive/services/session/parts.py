# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pydantic import BaseModel, Field


class SessionRequest(BaseModel):
    """Request to the session service."""

    model_config = {"extra": "forbid"}

    action: str = Field(..., description="Session action: init, end, status")
    issue: int | None = Field(None, description="GitHub issue number")
    resume: bool = Field(False, description="Resume from previous session")
    depth: int = Field(7, description="Memory depth for context")
    continue_session: bool = Field(False, description="Continue current session")


class SessionResponse(BaseModel):
    """Response from the session service."""

    model_config = {"extra": "allow"}

    success: bool = Field(..., description="Whether session operation succeeded")
    summary: str = Field(..., description="Summary of session operation")

    session_output: str | None = Field(
        None, description="Session initialization output"
    )
    pending_tasks: list[dict] = Field(default_factory=list, description="Pending tasks")

    git_status: dict | None = Field(None, description="Git repository status")
    unprocessed_summaries: int = Field(0, description="Number of unprocessed summaries")

    error: str | None = Field(None, description="Error message if operation failed")
