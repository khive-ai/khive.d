# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pydantic import BaseModel, Field


class SessionRequest(BaseModel):
    """Request to the session service."""

    model_config = {"extra": "forbid"}

    action: str = Field(
        ...,
        min_length=1,
        description="Session action: init, end, status (must be non-empty)",
    )
    issue: int | None = Field(
        None, gt=0, description="GitHub issue number (must be positive)"
    )
    resume: bool = Field(False, description="Resume from previous session")
    depth: int = Field(
        7, gt=0, description="Memory depth for context (must be positive)"
    )
    continue_session: bool = Field(False, description="Continue current session")


class SessionResponse(BaseModel):
    """Response from the session service."""

    model_config = {"extra": "allow"}

    success: bool = Field(..., description="Whether session operation succeeded")
    summary: str = Field(
        ...,
        min_length=1,
        description="Summary of session operation (must be non-empty)",
    )

    session_output: str | None = Field(
        None, description="Session initialization output"
    )
    pending_tasks: list[dict] = Field(default_factory=list, description="Pending tasks")

    git_status: dict | None = Field(None, description="Git repository status")
    unprocessed_summaries: int = Field(
        0, ge=0, description="Number of unprocessed summaries (must be non-negative)"
    )

    error: str | None = Field(None, description="Error message if operation failed")
