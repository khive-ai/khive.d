"""
Clean data models for multi-round consensus planning system.
Based on ChatGPT's design - no legacy fields, no fallbacks.
"""

from __future__ import annotations

from enum import Enum

from lionagi.models import HashableModel
from pydantic import Field


class ComplexityLevel(str, Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class QualityGate(str, Enum):
    BASIC = "basic"
    THOROUGH = "thorough"
    CRITICAL = "critical"


class CoordinationStrategy(str, Enum):
    FAN_OUT_SYNTHESIZE = "fan_out_synthesize"
    SEQUENTIAL_REFINEMENT = "sequential_refinement"
    SWARM = "swarm"
    MAP_REDUCE = "map_reduce"
    CONSENSUS_VOTING = "consensus_voting"
    AUTONOMOUS = "autonomous"


class AgentRecommendation(HashableModel):
    """Agent allocation recommendation."""

    role: str
    domain: str
    priority: float = Field(ge=0.0, le=1.0)
    reasoning: str


class TaskPhase(HashableModel):
    """A single execution phase with clear coordination strategy."""

    name: str
    description: str
    agents: list[AgentRecommendation]
    dependencies: list[str] = Field(default_factory=list)
    quality_gate: QualityGate
    coordination_strategy: CoordinationStrategy
    expected_artifacts: list[str] = Field(default_factory=list)


class PlannerRequest(HashableModel):
    """Clean request model - no legacy fields."""

    task_description: str
    context: str | None = None
    time_budget_seconds: float = Field(default=60.0, ge=10.0, le=300.0)


class PlannerResponse(HashableModel):
    """Clean response model - only essential fields."""

    success: bool
    summary: str
    complexity: ComplexityLevel
    recommended_agents: int
    phases: list[TaskPhase]
    coordination_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    error: str | None = None
    spawn_commands: list[str] = Field(default_factory=list)
    # NEW (optional, for transparency & downstream budgeting)
    pattern: str | None = None
    complexity_score: float | None = Field(default=None, ge=0.0, le=1.0)


# Internal consensus models
class DecompositionCandidate(HashableModel):
    """Raw phase decomposition from generator."""

    reasoning: str
    phases: list[dict]  # Raw phase data before TaskPhase validation
    estimated_complexity: ComplexityLevel
    parallelizable_groups: list[list[str]] = Field(default_factory=list)


class StrategyCandidate(HashableModel):
    """Strategy assignment from strategist."""

    reasoning: str
    phases: list[TaskPhase]
    coordination_rationale: str
    estimated_agents: int


class JudgeScore(HashableModel):
    """Judge scoring of a candidate plan."""

    feasibility: float = Field(ge=0.0, le=10.0)
    risk: float = Field(ge=0.0, le=10.0)
    coverage: float = Field(ge=0.0, le=10.0)
    cost_efficiency: float = Field(ge=0.0, le=10.0)
    coordination_clarity: float = Field(ge=0.0, le=10.0)
    testability: float = Field(ge=0.0, le=10.0)
    overall: float = Field(ge=0.0, le=10.0)
    judge_id: str
    reasoning: str


class PairwiseComparison(HashableModel):
    """Pairwise comparison result from judge."""

    candidate_a_id: str
    candidate_b_id: str
    winner_id: str  # Which candidate won
    judge_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class ConsensusResult(HashableModel):
    """Result from consensus algorithm."""

    winner_id: str
    scores: dict[str, float]  # candidate_id -> consensus score
    margin: float  # separation between top 2
    algorithm_used: str
    round_number: int
    converged: bool
