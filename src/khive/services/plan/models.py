from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RolePriority(BaseModel):
    """Simple role priority model"""

    model_config = ConfigDict(extra="forbid")

    roles: list[str] = Field(
        min_length=3,
        max_length=10,
        description="Priority-ordered list of recommended roles",
    )


class OrchestrationEvaluation(BaseModel):
    """Single flat evaluation model for GPT-5-nano"""

    model_config = ConfigDict(extra="forbid")

    # Core Assessment
    complexity: Literal["simple", "medium", "complex", "very_complex"]
    complexity_reason: str = Field(max_length=200)

    total_agents: int = Field(ge=1, le=20)
    agent_reason: str = Field(max_length=200)

    rounds_needed: int = Field(ge=1, le=6)

    # Role Priority List
    role_priorities: list[str] = Field(
        max_length=10,
        description="Priority-ordered list of recommended roles (most important first)",
    )

    # Domains (just lists)
    primary_domains: list[str] = Field(max_length=3)
    domain_reason: str = Field(max_length=200)

    # Workflow
    workflow_pattern: Literal["parallel", "sequential", "hybrid"]
    workflow_reason: str = Field(max_length=200)

    # Quality
    quality_level: Literal["basic", "thorough", "critical"]
    quality_reason: str = Field(max_length=200)

    # Decision Matrix
    rules_applied: list[str] = Field(max_length=3)

    # Summary
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(max_length=300)


# Lion-Task Coordination Models (legacy coordination models removed)
