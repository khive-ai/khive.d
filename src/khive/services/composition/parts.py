# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from khive.prompts import AgentRole

__all__ = (
    "ComposerRequest",
    "DomainExpertise",
    "ComposerResponse",
    "AgentCompositionRequest",
    "AgentSpec",
    "AgentRole",  # re-export for convenience
)


class ComposerRequest(BaseModel):
    """Request to the composer service."""

    role: AgentRole = Field(..., description="Agent role (e.g., researcher, architect)")
    domains: str | None = Field(None, description="Comma-separated domain list")
    context: str | None = Field(None, description="Task context for agent composition")


class DomainExpertise(BaseModel):
    """Domain expertise information."""

    domain_id: str = Field(..., description="Domain identifier")
    knowledge_patterns: dict = Field(
        default_factory=dict, description="Knowledge patterns for this domain"
    )
    decision_rules: dict = Field(
        default_factory=dict, description="Decision rules for this domain"
    )
    specialized_tools: list[str] = Field(
        default_factory=list, description="Specialized tools for this domain"
    )
    confidence_thresholds: dict = Field(
        default_factory=dict, description="Confidence thresholds"
    )


class ComposerResponse(BaseModel):
    """Response from the composer service."""

    model_config = ConfigDict(extra="allow")

    success: bool = Field(..., description="Whether composition succeeded")
    summary: str = Field(..., description="Summary of the composed agent")

    agent_id: str = Field(..., description="Unique agent identifier")
    role: str = Field(..., description="Agent role")
    domains: list[str] = Field(
        default_factory=list, description="List of domain expertise"
    )

    system_prompt: str = Field(..., description="Generated system prompt for the agent")
    capabilities: list[str] = Field(
        default_factory=list, description="Agent capabilities"
    )
    tools: list[str] = Field(default_factory=list, description="Available tools")

    domain_expertise: list[DomainExpertise] = Field(
        default_factory=list, description="Detailed domain expertise"
    )

    confidence: float = Field(
        ..., description="Confidence in the composition (0.0-1.0)"
    )
    error: Optional[str] = Field(
        None, description="Error message if composition failed"
    )


class AgentCompositionRequest(BaseModel):
    """Validated input for agent composition"""

    model_config = ConfigDict(extra="forbid")

    role: str = Field(min_length=1, max_length=100, description="Agent role name")
    domains: str | None = Field(
        None, max_length=500, description="Comma-separated domain list"
    )
    context: str | None = Field(None, max_length=10000, description="Task context")

    @field_validator("role")
    def validate_role(cls, v):
        if not v or not v.strip():
            raise ValueError("Role cannot be empty")
        # Basic sanitization in validator
        if any(char in v for char in ["..", "/", "\\\\"]):
            raise ValueError("Role contains invalid characters")
        return v.strip()


@dataclass
class AgentSpec:
    """Immutable agent specification (Pydantic-style contract)"""

    name: str
    role: str
    domain: str
    temperature: float
    system_prompt: str
    tools: list[str] = None

    def __post_init__(self):
        if self.tools is None:
            self.tools = []
