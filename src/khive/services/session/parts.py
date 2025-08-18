from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SessionRequest(BaseModel):
    """Request to the session service."""

    action: str = Field(..., description="Session action: init, end, status")
    issue: Optional[int] = Field(None, description="GitHub issue number")
    resume: bool = Field(False, description="Resume from previous session")
    depth: int = Field(7, description="Memory depth for context")
    continue_session: bool = Field(False, description="Continue current session")

    class Config:
        extra = "forbid"


class SessionResponse(BaseModel):
    """Response from the session service."""

    success: bool = Field(..., description="Whether session operation succeeded")
    summary: str = Field(..., description="Summary of session operation")

    session_output: Optional[str] = Field(
        None, description="Session initialization output"
    )
    memory_queries: list[str] = Field(
        default_factory=list, description="Recommended memory queries"
    )
    pending_tasks: list[dict] = Field(default_factory=list, description="Pending tasks")

    git_status: Optional[dict] = Field(None, description="Git repository status")
    unprocessed_summaries: int = Field(0, description="Number of unprocessed summaries")

    error: Optional[str] = Field(None, description="Error message if operation failed")

    class Config:
        extra = "allow"
