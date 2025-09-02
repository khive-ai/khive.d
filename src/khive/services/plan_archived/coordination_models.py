"""
Adaptive Orchestration Models for Khive Planning System.

This module implements the Decomposer-Strategist-Critic pipeline and advanced
coordination strategies for intelligent task orchestration.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from khive._types import BaseModel
from pydantic import Field

from .parts import AgentRecommendation, QualityGate, WorkflowPattern


class CoordinationStrategy(str, Enum):
    """Advanced coordination strategies for adaptive orchestration model."""
    
    # Basic patterns (backwards compatibility)
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential" 
    HYBRID = "hybrid"
    
    # Adaptive orchestration patterns
    DECOMPOSER_STRATEGIST_CRITIC = "decomposer_strategist_critic"
    FAN_OUT_FAN_IN = "fan_out_fan_in"
    PIPELINE_WITH_FEEDBACK = "pipeline_with_feedback"
    
    # Advanced coordination patterns
    CONSENSUS_BUILDING = "consensus_building"
    COMPETITIVE_ANALYSIS = "competitive_analysis"
    HIERARCHICAL_REFINEMENT = "hierarchical_refinement"


class PipelineStage(str, Enum):
    """Pipeline stages for decomposer-strategist-critic pattern."""
    
    DECOMPOSER = "decomposer"
    STRATEGIST = "strategist" 
    CRITIC = "critic"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"
    REFINEMENT = "refinement"


class FeedbackType(str, Enum):
    """Types of feedback loops in adaptive orchestration."""
    
    IMMEDIATE = "immediate"  # Real-time feedback during execution
    PHASE_END = "phase_end"  # Feedback at end of each phase
    ITERATIVE = "iterative"  # Multiple rounds of refinement
    CONSENSUS = "consensus"   # Feedback until consensus reached


class AdaptiveTaskPhase(BaseModel):
    """Enhanced task phase supporting adaptive orchestration patterns."""

    # Core phase information (backwards compatible)
    name: str = Field(..., description="Phase name")
    description: str = Field(..., description="Phase description")
    agents: List[AgentRecommendation] = Field(
        ..., description="Recommended agents for this phase"
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Phase dependencies"
    )
    quality_gate: QualityGate = Field(..., description="Quality gate for this phase")
    coordination_pattern: WorkflowPattern = Field(
        ..., description="Basic coordination pattern"
    )
    
    # Adaptive orchestration extensions
    coordination_strategy: CoordinationStrategy = Field(
        default=CoordinationStrategy.PARALLEL, 
        description="Advanced coordination strategy"
    )
    pipeline_stage: Optional[PipelineStage] = Field(
        default=None, 
        description="Pipeline stage for decomposer-strategist-critic pattern"
    )
    feedback_type: Optional[FeedbackType] = Field(
        default=None,
        description="Type of feedback loop enabled"
    )
    
    # Manual coordination integration
    requires_manual_coordination: bool = Field(
        default=False,
        description="Requires explicit manual coordination protocol"
    )
    coordination_checkpoints: List[str] = Field(
        default_factory=list,
        description="Manual coordination checkpoints within phase"
    )


class DecomposerStrategistCriticPipeline(BaseModel):
    """Configuration for the Decomposer-Strategist-Critic pipeline pattern."""
    
    # Pipeline configuration
    decomposer_agents: List[AgentRecommendation] = Field(
        ..., description="Agents responsible for problem decomposition"
    )
    strategist_agents: List[AgentRecommendation] = Field(
        ..., description="Agents responsible for strategy development"
    )
    critic_agents: List[AgentRecommendation] = Field(
        ..., description="Agents responsible for critical analysis"
    )
    
    # Integration with manual coordination
    coordination_checkpoints: List[str] = Field(
        default_factory=lambda: [
            "decomposition_complete",
            "strategy_formulated", 
            "critique_provided",
            "refinement_needed"
        ],
        description="Coordination checkpoints for manual protocol integration"
    )


def create_decomposer_strategist_critic_phases(
    task_description: str,
    agents: List[AgentRecommendation],
    coordination_id: Optional[str] = None
) -> List[AdaptiveTaskPhase]:
    """Create phases for the Decomposer-Strategist-Critic pipeline pattern."""
    phases = []
    
    # Decomposer Phase
    decomposer_agents = [a for a in agents if a.role in ["researcher", "analyst"]]
    phases.append(AdaptiveTaskPhase(
        name="decomposition_phase",
        description="Decompose the problem into manageable components",
        agents=decomposer_agents[:3],
        quality_gate=QualityGate.THOROUGH,
        coordination_pattern=WorkflowPattern.PARALLEL,
        coordination_strategy=CoordinationStrategy.DECOMPOSER_STRATEGIST_CRITIC,
        pipeline_stage=PipelineStage.DECOMPOSER,
        feedback_type=FeedbackType.PHASE_END,
        requires_manual_coordination=True,
        coordination_checkpoints=["decomposition_complete"]
    ))
    
    # Strategist Phase
    strategist_agents = [a for a in agents if a.role in ["architect", "strategist"]]
    phases.append(AdaptiveTaskPhase(
        name="strategy_phase", 
        description="Develop comprehensive implementation strategy",
        agents=strategist_agents[:2],
        dependencies=["decomposition_phase"],
        quality_gate=QualityGate.THOROUGH,
        coordination_pattern=WorkflowPattern.SEQUENTIAL,
        coordination_strategy=CoordinationStrategy.DECOMPOSER_STRATEGIST_CRITIC,
        pipeline_stage=PipelineStage.STRATEGIST,
        feedback_type=FeedbackType.ITERATIVE,
        requires_manual_coordination=True,
        coordination_checkpoints=["strategy_formulated"]
    ))
    
    # Critic Phase
    critic_agents = [a for a in agents if a.role in ["critic", "auditor", "tester"]]
    phases.append(AdaptiveTaskPhase(
        name="critique_phase",
        description="Provide critical analysis and identify improvements",
        agents=critic_agents[:2],
        dependencies=["strategy_phase"],
        quality_gate=QualityGate.CRITICAL,
        coordination_pattern=WorkflowPattern.PARALLEL,
        coordination_strategy=CoordinationStrategy.DECOMPOSER_STRATEGIST_CRITIC,
        pipeline_stage=PipelineStage.CRITIC,
        feedback_type=FeedbackType.CONSENSUS,
        requires_manual_coordination=True,
        coordination_checkpoints=["critique_provided"]
    ))
    
    return phases