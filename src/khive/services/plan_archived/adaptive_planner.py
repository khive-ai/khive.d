"""
Adaptive Planner Extension for Khive Planning System.

This module extends the existing planner service with adaptive orchestration
capabilities including the Decomposer-Strategist-Critic pipeline.
"""

from __future__ import annotations

from typing import List, Optional

from .coordination_models import (
    AdaptiveTaskPhase,
    CoordinationStrategy,
    PipelineStage,
    FeedbackType,
    DecomposerStrategistCriticPipeline,
    create_decomposer_strategist_critic_phases
)
from .parts import (
    AgentRecommendation,
    ComplexityLevel, 
    PlannerRequest,
    PlannerResponse,
    TaskPhase,
    QualityGate,
    WorkflowPattern
)


class AdaptivePlannerService:
    """Extended planner service with adaptive orchestration capabilities."""
    
    def __init__(self, base_planner_service):
        """Initialize with reference to base planner service."""
        self.base_planner = base_planner_service
        
    async def create_adaptive_plan(
        self, 
        request: PlannerRequest,
        coordination_strategy: CoordinationStrategy = CoordinationStrategy.DECOMPOSER_STRATEGIST_CRITIC
    ) -> PlannerResponse:
        """Create an adaptive orchestration plan with advanced coordination."""
        
        # Get base plan from existing planner
        base_response = await self.base_planner.handle_request(request)
        
        if not base_response.success:
            return base_response
            
        # Convert to adaptive phases based on coordination strategy
        if coordination_strategy == CoordinationStrategy.DECOMPOSER_STRATEGIST_CRITIC:
            adaptive_phases = self._create_dsc_pipeline(
                request.task_description,
                base_response.phases,
                base_response.session_id
            )
        elif coordination_strategy == CoordinationStrategy.FAN_OUT_FAN_IN:
            adaptive_phases = self._create_fanout_fanin_phases(
                base_response.phases
            )
        elif coordination_strategy == CoordinationStrategy.PIPELINE_WITH_FEEDBACK:
            adaptive_phases = self._create_feedback_pipeline(
                base_response.phases
            )
        else:
            # Use existing phases with minimal adaptation
            adaptive_phases = self._adapt_existing_phases(
                base_response.phases,
                coordination_strategy
            )
            
        # Update response with adaptive phases
        base_response.phases = adaptive_phases
        
        # Update summary with adaptive orchestration context
        base_response.summary += f"\n\n🎯 ADAPTIVE ORCHESTRATION ENABLED"
        base_response.summary += f"\nCoordination Strategy: {coordination_strategy.value}"
        base_response.summary += f"\nManual Coordination: Integrated with explicit protocol"
        base_response.summary += f"\nPipeline Stages: {len(adaptive_phases)} phases with feedback loops"
        
        return base_response
        
    def _create_dsc_pipeline(
        self,
        task_description: str,
        base_phases: List[TaskPhase],
        session_id: Optional[str]
    ) -> List[AdaptiveTaskPhase]:
        """Create Decomposer-Strategist-Critic pipeline phases."""
        
        # Extract agents from base phases
        all_agents = []
        for phase in base_phases:
            all_agents.extend(phase.agents)
            
        # Create DSC phases
        dsc_phases = create_decomposer_strategist_critic_phases(
            task_description=task_description,
            agents=all_agents,
            coordination_id=session_id
        )
        
        # Add implementation phase if needed
        implementation_agents = [a for a in all_agents if a.role in ["implementer", "innovator"]]
        if implementation_agents:
            implementation_phase = AdaptiveTaskPhase(
                name="implementation_phase",
                description="Implement solution based on refined strategy",
                agents=implementation_agents,
                dependencies=["critique_phase"],
                quality_gate=QualityGate.THOROUGH,
                coordination_pattern=WorkflowPattern.PARALLEL,
                coordination_strategy=CoordinationStrategy.PIPELINE_WITH_FEEDBACK,
                pipeline_stage=PipelineStage.SYNTHESIS,
                feedback_type=FeedbackType.IMMEDIATE,
                requires_manual_coordination=True,
                coordination_checkpoints=["implementation_complete"]
            )
            dsc_phases.append(implementation_phase)
            
        return dsc_phases
        
    def _create_fanout_fanin_phases(
        self, 
        base_phases: List[TaskPhase]
    ) -> List[AdaptiveTaskPhase]:
        """Create fan-out/fan-in coordination phases."""
        
        adaptive_phases = []
        
        for phase in base_phases:
            adaptive_phase = AdaptiveTaskPhase(
                name=phase.name,
                description=phase.description,
                agents=phase.agents,
                dependencies=phase.dependencies,
                quality_gate=phase.quality_gate,
                coordination_pattern=phase.coordination_pattern,
                coordination_strategy=CoordinationStrategy.FAN_OUT_FAN_IN,
                feedback_type=FeedbackType.PHASE_END,
                requires_manual_coordination=True,
                coordination_checkpoints=[f"{phase.name}_fanout", f"{phase.name}_fanin"]
            )
            adaptive_phases.append(adaptive_phase)
            
        return adaptive_phases
        
    def _create_feedback_pipeline(
        self, 
        base_phases: List[TaskPhase]
    ) -> List[AdaptiveTaskPhase]:
        """Create pipeline with feedback loops."""
        
        adaptive_phases = []
        
        for phase in base_phases:
            adaptive_phase = AdaptiveTaskPhase(
                name=phase.name,
                description=phase.description + " (with feedback loops)",
                agents=phase.agents,
                dependencies=phase.dependencies,
                quality_gate=phase.quality_gate,
                coordination_pattern=phase.coordination_pattern,
                coordination_strategy=CoordinationStrategy.PIPELINE_WITH_FEEDBACK,
                feedback_type=FeedbackType.ITERATIVE,
                requires_manual_coordination=True,
                coordination_checkpoints=[f"{phase.name}_feedback"]
            )
            adaptive_phases.append(adaptive_phase)
            
        return adaptive_phases
        
    def _adapt_existing_phases(
        self,
        base_phases: List[TaskPhase],
        coordination_strategy: CoordinationStrategy
    ) -> List[AdaptiveTaskPhase]:
        """Adapt existing phases with minimal changes."""
        
        adaptive_phases = []
        
        for phase in base_phases:
            adaptive_phase = AdaptiveTaskPhase(
                name=phase.name,
                description=phase.description,
                agents=phase.agents,
                dependencies=phase.dependencies,
                quality_gate=phase.quality_gate,
                coordination_pattern=phase.coordination_pattern,
                coordination_strategy=coordination_strategy,
                requires_manual_coordination=True,
                coordination_checkpoints=[f"{phase.name}_complete"]
            )
            adaptive_phases.append(adaptive_phase)
            
        return adaptive_phases


def integrate_with_manual_coordination(
    phases: List[AdaptiveTaskPhase],
    coordination_id: str
) -> str:
    """Generate integration instructions for manual coordination protocol."""
    
    instructions = [
        "# Manual Coordination Protocol Integration",
        "",
        f"Coordination ID: {coordination_id}",
        "",
        "## Phase Execution Protocol",
        ""
    ]
    
    for phase in phases:
        instructions.extend([
            f"### {phase.name}",
            f"- Description: {phase.description}",
            f"- Strategy: {phase.coordination_strategy.value}",
            f"- Manual Coordination Required: {'Yes' if phase.requires_manual_coordination else 'No'}",
            ""
        ])
        
        if phase.coordination_checkpoints:
            instructions.append("- Coordination Checkpoints:")
            for checkpoint in phase.coordination_checkpoints:
                instructions.append(f"  - `uv run khive coordinate check --checkpoint {checkpoint}`")
            instructions.append("")
            
        if phase.pipeline_stage:
            instructions.extend([
                f"- Pipeline Stage: {phase.pipeline_stage.value}",
                f"- Feedback Type: {phase.feedback_type.value if phase.feedback_type else 'None'}",
                ""
            ])
    
    instructions.extend([
        "## Coordination Commands",
        "",
        "Before starting each phase:",
        "```bash",
        f"uv run khive coordinate pre-task --description \"[phase description]\" --agent-id [agent_id] --coordination-id {coordination_id}",
        "```",
        "",
        "Before editing files:",
        "```bash", 
        "uv run khive coordinate check --file \"[file_path]\" --agent-id [agent_id]",
        "```",
        "",
        "After editing files:",
        "```bash",
        "uv run khive coordinate post-edit --file \"[file_path]\" --agent-id [agent_id]",
        "```",
        "",
        "After completing phase:",
        "```bash",
        "uv run khive coordinate post-task --agent-id [agent_id] --summary \"[completion summary]\"",
        "```"
    ])
    
    return "\n".join(instructions)


__all__ = [
    "AdaptivePlannerService",
    "integrate_with_manual_coordination"
]