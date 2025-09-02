"""
Data models for the Adaptive Orchestration Planning system.

This module defines all Pydantic models used in the planning pipeline:
- Core enums for complexity, quality gates, and coordination strategies
- Request/Response models for the planner service
- Internal models for the Decomposer-Strategist-Critic pipeline
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from khive._types import BaseModel as HashableModel
from pydantic import Field


# ============== Core Enums ==============

class ComplexityLevel(str, Enum):
    """Task complexity levels."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class QualityGate(str, Enum):
    """Quality gate levels for phase validation."""
    BASIC = "basic"
    THOROUGH = "thorough"
    CRITICAL = "critical"


class CoordinationStrategy(str, Enum):
    """
    Agent coordination strategies within a phase.
    
    Each strategy defines how agents work together:
    - FAN_OUT_SYNTHESIZE: Parallel exploration with final synthesis
    - SEQUENTIAL_REFINEMENT: Each agent builds upon previous work
    - SWARM: High parallelism with shared workspace (needs locking)
    - MAP_REDUCE: Specialized parallel processing and aggregation
    - CONSENSUS_VOTING: Multiple proposals with voting mechanism
    - AUTONOMOUS: Independent work with minimal coordination
    """
    FAN_OUT_SYNTHESIZE = "fan_out_synthesize"
    SEQUENTIAL_REFINEMENT = "sequential_refinement"
    SWARM = "swarm"
    MAP_REDUCE = "map_reduce"
    CONSENSUS_VOTING = "consensus_voting"
    AUTONOMOUS = "autonomous"


# ============== Request/Response Models ==============

class PlannerRequest(HashableModel):
    """Request to the planning service."""
    task_description: str = Field(..., description="Description of the task to plan")
    context: Optional[str] = Field(None, description="Additional context for planning")
    time_budget_seconds: float = Field(45.0, description="Maximum time for planning")


class AgentRecommendation(HashableModel):
    """Recommendation for an agent in the plan."""
    role: str = Field(..., description="Agent role (e.g., researcher, architect)")
    domain: str = Field(..., description="Domain expertise (e.g., distributed-systems)")
    priority: float = Field(..., description="Priority score (0.0-1.0)", ge=0.0, le=1.0)
    reasoning: str = Field(..., description="Specific task assignment for this agent")


class TaskPhase(HashableModel):
    """A phase in the orchestration plan."""
    name: str = Field(..., description="Unique, descriptive phase name")
    description: str = Field(..., description="Phase objectives and scope")
    agents: List[AgentRecommendation] = Field(..., description="Agents for this phase")
    dependencies: List[str] = Field(default_factory=list, description="Phase dependencies")
    quality_gate: QualityGate = Field(..., description="Quality validation level")
    coordination_strategy: CoordinationStrategy = Field(..., description="How agents coordinate")
    expected_artifacts: List[str] = Field(default_factory=list, description="Expected outputs")
    
    # Optional fields for monitoring
    estimated_duration_minutes: Optional[int] = Field(None, description="Estimated duration")
    coordination_checkpoints: List[str] = Field(default_factory=list, description="Checkpoint triggers")


class PlannerResponse(HashableModel):
    """Response from the planning service."""
    success: bool = Field(..., description="Whether planning succeeded")
    summary: str = Field(..., description="Human-readable summary")
    complexity: ComplexityLevel = Field(..., description="Assessed complexity")
    recommended_agents: int = Field(..., description="Total agent count")
    phases: List[TaskPhase] = Field(default_factory=list, description="Execution phases")
    session_id: Optional[str] = Field(None, description="Coordination session ID")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Plan confidence")
    error: Optional[str] = Field(None, description="Error if failed")
    
    # Deprecated but kept for compatibility
    spawn_commands: List[str] = Field(default_factory=list, description="Agent spawn commands")


# ============== Pipeline Models (Decomposer-Strategist-Critic) ==============

class TaskDecomposition(HashableModel):
    """Output from the Decomposer component."""
    reasoning: str = Field(..., description="Rationale for this decomposition")
    phases: List['DecomposedPhase'] = Field(..., description="Decomposed phases")
    estimated_complexity: ComplexityLevel = Field(..., description="Overall complexity")
    parallelizable_groups: List[List[str]] = Field(default_factory=list, description="Phases that can run in parallel")
    
    
class DecomposedPhase(HashableModel):
    """A single phase from decomposition."""
    name: str = Field(..., description="Unique phase name")
    description: str = Field(..., description="Phase objectives")
    dependencies: List[str] = Field(default_factory=list, description="Required predecessor phases")


class StrategyRecommendation(HashableModel):
    """Output from the Strategist component."""
    reasoning: str = Field(..., description="Rationale for this strategy")
    phase_allocations: List['PhaseAllocation'] = Field(..., description="Agent allocations per phase")
    overall_coordination: CoordinationStrategy = Field(..., description="Default coordination approach")
    
    
class PhaseAllocation(HashableModel):
    """Agent allocation for a single phase."""
    phase_name: str = Field(..., description="Target phase name")
    agents: List['AllocatedAgent'] = Field(..., description="Assigned agents")
    coordination_strategy: CoordinationStrategy = Field(..., description="Phase-specific coordination")
    quality_gate: QualityGate = Field(..., description="Quality requirements")
    expected_artifacts: List[str] = Field(default_factory=list, description="Expected outputs")


class AllocatedAgent(HashableModel):
    """An agent allocated to a phase."""
    role: str = Field(..., description="Agent role")
    domain: str = Field(..., description="Domain expertise")
    task_assignment: str = Field(..., description="Specific task for this agent")
    priority: float = Field(1.0, ge=0.0, le=1.0, description="Priority within phase")


class PlanCritique(HashableModel):
    """Output from the Critic component."""
    overall_assessment: str = Field(..., description="High-level assessment")
    strengths: List[str] = Field(default_factory=list, description="Plan strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Plan weaknesses")
    risks: List[str] = Field(default_factory=list, description="Identified risks")
    bottlenecks: List[str] = Field(default_factory=list, description="Potential bottlenecks")
    suggested_improvements: List[str] = Field(default_factory=list, description="Improvement suggestions")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    
    
class OrchestrationResult(HashableModel):
    """Combined result from the orchestration pipeline."""
    decomposition: TaskDecomposition
    strategy: StrategyRecommendation
    critique: PlanCritique
    final_plan: PlannerResponse


# Update forward references
TaskDecomposition.model_rebuild()
StrategyRecommendation.model_rebuild()
