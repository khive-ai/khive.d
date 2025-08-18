from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import Field

from khive._types import BaseModel


class ComplexityLevel(str, Enum):
    """Complexity level for orchestration tasks."""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class WorkflowPattern(str, Enum):
    """Workflow execution patterns."""

    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    HYBRID = "hybrid"


class QualityGate(str, Enum):
    """Quality gate levels."""

    BASIC = "basic"
    THOROUGH = "thorough"
    CRITICAL = "critical"


class PlannerRequest(BaseModel):
    """Request to the planner service."""

    task_description: str = Field(..., description="Description of the task to plan")
    context: Optional[str] = Field(None, description="Additional context for planning")
    time_budget_seconds: float = Field(30.0, description="Maximum time for planning")

    class Config:
        extra = "forbid"


class AgentRecommendation(BaseModel):
    """Recommendation for an agent in the plan."""

    role: str = Field(..., description="Agent role (e.g., researcher, architect)")
    domain: str = Field(..., description="Domain expertise (e.g., distributed-systems)")
    priority: float = Field(..., description="Priority score (0.0-1.0)")
    reasoning: str = Field(..., description="Why this agent is recommended")


class TaskPhase(BaseModel):
    """A phase in the orchestration plan."""

    name: str = Field(..., description="Phase name")
    description: str = Field(..., description="Phase description")
    agents: list[AgentRecommendation] = Field(
        ..., description="Recommended agents for this phase"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="Phase dependencies"
    )
    quality_gate: QualityGate = Field(..., description="Quality gate for this phase")
    coordination_pattern: WorkflowPattern = Field(
        ..., description="Coordination pattern"
    )


class PlannerResponse(BaseModel):
    """Response from the planner service."""

    success: bool = Field(..., description="Whether planning succeeded")
    summary: str = Field(..., description="Summary of the orchestration plan")
    complexity: ComplexityLevel = Field(..., description="Assessed complexity level")
    recommended_agents: int = Field(..., description="Total recommended agents")

    phases: list[TaskPhase] = Field(
        default_factory=list, description="Execution phases"
    )
    spawn_commands: list[str] = Field(
        default_factory=list, description="Agent spawn commands"
    )

    session_id: Optional[str] = Field(None, description="Session ID for coordination")

    confidence: float = Field(..., description="Confidence in the plan (0.0-1.0)")
    error: Optional[str] = Field(None, description="Error message if planning failed")

    class Config:
        extra = "allow"
