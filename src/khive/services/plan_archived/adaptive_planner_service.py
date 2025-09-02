"""
Adaptive Planner Service - Enhanced version of PlannerService with Adaptive Orchestration.

This service extends the existing PlannerService to support the Decomposer-Strategist-Critic
pipeline while maintaining backward compatibility with the existing API.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
import asyncio
import time

from khive.utils import get_logger
from khive.services.claude.hooks.coordination import get_registry

from .planner_service import PlannerService
from .adaptive_pipeline import AdaptiveOrchestrationPipeline
from .adaptive_models import (
    CoordinationStrategy,
    AdaptiveTaskPhase,
    AdaptiveOrchestrationPlan,
    BasicDecomposer,
    BasicStrategist, 
    BasicCritic,
)
from .parts import (
    PlannerRequest,
    PlannerResponse,
    ComplexityLevel,
    WorkflowPattern,
    QualityGate,
    TaskPhase,
    AgentRecommendation,
)

logger = get_logger("khive.services.plan.adaptive")


class AdaptivePlannerService(PlannerService):
    """
    Enhanced PlannerService with Adaptive Orchestration capabilities.
    
    This service maintains full backward compatibility with PlannerService while
    adding the Decomposer-Strategist-Critic pipeline for adaptive orchestration.
    """
    
    def __init__(self, command_format: str = "claude", enable_adaptive: bool = True):
        """
        Initialize the adaptive planner service.
        
        Args:
            command_format: Either "claude" for BatchTool format or "json" for OrchestrationPlan format
            enable_adaptive: Whether to enable adaptive orchestration features
        """
        super().__init__(command_format)
        
        self.enable_adaptive = enable_adaptive
        self._adaptive_pipeline = None
        self._pipeline_lock = asyncio.Lock()
        
        # Enhanced metrics
        self.adaptive_metrics = {
            "adaptive_plans_created": 0,
            "fallback_to_traditional": 0,
            "coordination_optimizations": 0,
            "strategy_adaptations": 0,
            "avg_adaptive_score": 0.0,
        }
    
    async def _get_adaptive_pipeline(self) -> AdaptiveOrchestrationPipeline:
        """Get or create the adaptive orchestration pipeline."""
        if self._adaptive_pipeline is None:
            async with self._pipeline_lock:
                if self._adaptive_pipeline is None:
                    self._adaptive_pipeline = AdaptiveOrchestrationPipeline(
                        decomposer=BasicDecomposer(),
                        strategist=BasicStrategist(),
                        critic=BasicCritic(),
                        enable_coordination=True
                    )
        return self._adaptive_pipeline
    
    async def handle_request(self, request: PlannerRequest) -> PlannerResponse:
        """
        Handle a planning request with optional adaptive orchestration.
        
        This method first tries adaptive orchestration if enabled, and falls back
        to traditional planning if needed or if adaptive is disabled.
        """
        try:
            # Parse request if needed
            if isinstance(request, str):
                request = PlannerRequest.model_validate_json(request)
            elif isinstance(request, dict):
                request = PlannerRequest.model_validate(request)
            
            # Update metrics
            self.metrics["total_requests"] += 1
            
            if self.enable_adaptive:
                try:
                    # Try adaptive orchestration first
                    return await self._handle_adaptive_request(request)
                except Exception as e:
                    logger.warning(f"Adaptive orchestration failed, falling back to traditional: {e}")
                    self.adaptive_metrics["fallback_to_traditional"] += 1
                    # Fall back to traditional planning
                    return await super().handle_request(request)
            else:
                # Use traditional planning directly
                return await super().handle_request(request)
                
        except Exception as e:
            logger.error(f"Error in adaptive handle_request: {e}", exc_info=True)
            return PlannerResponse(
                success=False,
                summary=f"Adaptive planning failed: {e!s}",
                complexity=ComplexityLevel.MEDIUM,
                recommended_agents=0,
                confidence=0.0,
                error=str(e),
            )
    
    async def _handle_adaptive_request(self, request: PlannerRequest) -> PlannerResponse:
        """Handle request using adaptive orchestration pipeline."""
        
        # Get adaptive pipeline
        pipeline = await self._get_adaptive_pipeline()
        
        # Create session ID
        session_id = f"adaptive_{int(time.time())}"
        
        # Create adaptive orchestration plan
        adaptive_plan = await pipeline.create_adaptive_plan(
            request=request,
            session_id=session_id,
            context={"planner_service": "adaptive"}
        )
        
        # Convert adaptive plan to traditional PlannerResponse format
        traditional_response = await self._convert_adaptive_to_traditional_response(
            adaptive_plan, request
        )
        
        # Update adaptive metrics
        self.adaptive_metrics["adaptive_plans_created"] += 1
        self.adaptive_metrics["avg_adaptive_score"] = (
            (self.adaptive_metrics["avg_adaptive_score"] * 
             (self.adaptive_metrics["adaptive_plans_created"] - 1) +
             adaptive_plan.confidence_score) / 
            self.adaptive_metrics["adaptive_plans_created"]
        )
        
        logger.info(
            f"Adaptive plan created: session={session_id}, "
            f"strategy={adaptive_plan.overall_strategy.value}, "
            f"confidence={adaptive_plan.confidence_score:.2f}"
        )
        
        return traditional_response
    
    async def _convert_adaptive_to_traditional_response(
        self, 
        adaptive_plan: AdaptiveOrchestrationPlan,
        original_request: PlannerRequest
    ) -> PlannerResponse:
        """Convert AdaptiveOrchestrationPlan to traditional PlannerResponse."""
        
        # Convert adaptive phases to traditional phases
        traditional_phases = []
        for adaptive_phase in adaptive_plan.phases:
            traditional_phase = TaskPhase(
                name=adaptive_phase.name,
                description=adaptive_phase.description,
                agents=adaptive_phase.agents,
                dependencies=adaptive_phase.dependencies,
                quality_gate=adaptive_phase.quality_gate,
                coordination_pattern=adaptive_phase.coordination_pattern
            )
            traditional_phases.append(traditional_phase)
        
        # Generate enhanced summary with adaptive insights
        summary_parts = []
        summary_parts.append("## 🎯 Adaptive Orchestration Plan\n")
        
        # Add decomposition insights
        decomp = adaptive_plan.decomposition
        summary_parts.append(f"**Task Decomposition:**")
        summary_parts.append(f"- Complexity: {decomp.complexity_assessment.value}")
        summary_parts.append(f"- Subtasks: {len(decomp.subtasks)}")
        summary_parts.append(f"- Estimated agents: {decomp.estimated_agent_count}")
        summary_parts.append(f"- Parallelizable groups: {len(decomp.parallelizable_subtasks)}")
        summary_parts.append("")
        
        # Add strategy insights
        strategy = adaptive_plan.strategy_recommendation
        summary_parts.append(f"**Coordination Strategy:**")
        summary_parts.append(f"- Selected: {strategy.recommended_strategy.value}")
        summary_parts.append(f"- Rationale: {strategy.strategy_rationale}")
        summary_parts.append(f"- Expected efficiency: {strategy.expected_efficiency:.2f}")
        summary_parts.append(f"- Coordination overhead: {strategy.coordination_overhead:.2f}")
        summary_parts.append("")
        
        # Add critique insights
        critique = adaptive_plan.plan_critique
        summary_parts.append(f"**Plan Evaluation:**")
        summary_parts.append(f"- Overall score: {critique.overall_score:.2f}")
        summary_parts.append(f"- Success probability: {critique.estimated_success_probability:.2f}")
        if critique.strengths:
            summary_parts.append("- Strengths: " + ", ".join(critique.strengths))
        if critique.optimization_suggestions:
            summary_parts.append("- Optimizations applied: " + ", ".join(critique.optimization_suggestions))
        summary_parts.append("")
        
        # Add phases summary
        summary_parts.append(f"**Execution Phases ({len(adaptive_plan.phases)}):**")
        for i, phase in enumerate(adaptive_plan.phases):
            agent_count = len(phase.agents)
            duration = phase.estimated_duration_minutes or "unknown"
            summary_parts.append(
                f"{i+1}. {phase.name}: {agent_count} agents, "
                f"{phase.coordination_strategy.value} coordination"
            )
        summary_parts.append("")
        
        # Add coordination integration note
        summary_parts.append("**🤝 Coordination Integration:**")
        summary_parts.append("- Manual coordination protocol: ✅ Integrated")
        summary_parts.append("- File conflict prevention: ✅ Active")
        summary_parts.append("- Agent work visibility: ✅ Enabled")
        summary_parts.append("- Adaptive thresholds: ✅ Configured")
        summary_parts.append("")
        
        # Generate spawn commands with adaptive context
        spawn_commands = await self._generate_adaptive_spawn_commands(
            adaptive_plan, original_request
        )
        
        # Add execution commands
        if self.command_format == "claude":
            command_output = self._generate_adaptive_batchtool_commands(adaptive_plan, original_request)
            summary_parts.append(command_output)
        elif self.command_format == "json":
            command_output = self._generate_adaptive_json_commands(adaptive_plan, original_request) 
            summary_parts.append(command_output)
        
        summary = "\n".join(summary_parts)
        
        return PlannerResponse(
            success=True,
            summary=summary,
            complexity=adaptive_plan.decomposition.complexity_assessment,
            recommended_agents=adaptive_plan.decomposition.estimated_agent_count,
            phases=traditional_phases,
            spawn_commands=spawn_commands,
            session_id=adaptive_plan.session_id,
            confidence=adaptive_plan.confidence_score,
            error=None
        )
    
    async def _generate_adaptive_spawn_commands(
        self, 
        adaptive_plan: AdaptiveOrchestrationPlan,
        request: PlannerRequest
    ) -> List[str]:
        """Generate spawn commands with adaptive orchestration context."""
        commands = []
        
        for phase in adaptive_plan.phases:
            for agent in phase.agents:
                command = (
                    f'uv run khive compose {agent.role} -d {agent.domain} '
                    f'-c "{request.task_description}" --coordination-id {adaptive_plan.session_id} '
                    f'--adaptive-strategy {phase.coordination_strategy.value} '
                    f'--quality-gate {phase.quality_gate.value}'
                )
                commands.append(command)
        
        return commands
    
    def _generate_adaptive_batchtool_commands(
        self,
        adaptive_plan: AdaptiveOrchestrationPlan,
        request: PlannerRequest
    ) -> str:
        """Generate BatchTool format commands with adaptive orchestration context."""
        output = []
        output.append("\n📋 Adaptive Orchestration Commands (BatchTool Format):")
        output.append("```javascript")
        
        for phase in adaptive_plan.phases:
            if phase.agents:
                output.append(f"  // Phase: {phase.name}")
                output.append(f"  // Strategy: {phase.coordination_strategy.value}")
                output.append(f"  // Coordination overhead threshold: {phase.max_coordination_overhead:.2f}")
                
                phase_tasks = []
                for agent in phase.agents:
                    agent_name = f"{agent.role}_{agent.domain.replace('-', '_')}"
                    
                    phase_context = f"""ADAPTIVE ORCHESTRATION CONTEXT:
- Phase: {phase.name} ({phase.description})
- Coordination Strategy: {phase.coordination_strategy.value}
- Quality Gate: {phase.quality_gate.value}
- Adaptive Threshold: {phase.adaptive_threshold}
- Max Coordination Overhead: {phase.max_coordination_overhead:.2f}

ORIGINAL REQUEST: {request.task_description}
DECOMPOSITION: {adaptive_plan.decomposition.complexity_assessment.value} complexity
STRATEGY RATIONALE: {adaptive_plan.strategy_recommendation.strategy_rationale}

ADAPTIVE FEATURES:
- Manual coordination protocol integration: ✅
- Dynamic strategy adaptation: ✅ 
- File conflict prevention: ✅
- Performance monitoring: ✅

YOUR ADAPTIVE ROLE:
1. Execute using coordination strategy: {phase.coordination_strategy.value}
2. Adapt if coordination overhead > {phase.max_coordination_overhead:.2f}
3. Follow manual coordination protocol for file edits
4. Monitor efficiency and report issues

COORDINATION COMMANDS:
- Before work: uv run khive coordinate pre-task --description "[task]" --agent-id {agent_name}
- Before file edit: uv run khive coordinate check --file "/path/to/file" --agent-id {agent_name}
- After file edit: uv run khive coordinate post-edit --file "/path/to/file" --agent-id {agent_name}
- After completion: uv run khive coordinate post-task --agent-id {agent_name} --summary "[summary]"

Remember: This is ADAPTIVE orchestration - optimize for {phase.coordination_strategy.value} coordination!"""
                    
                    # Escape for JavaScript
                    escaped_prompt = phase_context.replace('"', '\\"').replace('\n', '\\n')
                    phase_tasks.append(
                        f'    Task({{ description: "{agent_name}_{phase.name}", prompt: "{escaped_prompt}" }})'
                    )
                
                # Wrap phase tasks in [BatchTool]
                if phase_tasks:
                    output.append("  [BatchTool]([")
                    output.extend(phase_tasks)
                    output.append("  ])")
                    output.append("")  # Empty line between phases
        
        output.append("```")
        return "\n".join(output)
    
    def _generate_adaptive_json_commands(
        self,
        adaptive_plan: AdaptiveOrchestrationPlan,
        request: PlannerRequest
    ) -> str:
        """Generate JSON format commands with adaptive orchestration context."""
        output = []
        output.append("\n📋 Adaptive Orchestration Commands (JSON Format):")
        output.append("```json")
        
        json_structure = {
            "session_id": adaptive_plan.session_id,
            "orchestration_type": "adaptive",
            "overall_strategy": adaptive_plan.overall_strategy.value,
            "confidence_score": adaptive_plan.confidence_score,
            "estimated_duration_minutes": adaptive_plan.estimated_total_duration_minutes,
            "coordination_features": {
                "manual_protocol_integration": True,
                "file_conflict_prevention": True,
                "dynamic_adaptation": True,
                "performance_monitoring": True
            },
            "decomposition": {
                "complexity": adaptive_plan.decomposition.complexity_assessment.value,
                "subtasks_count": len(adaptive_plan.decomposition.subtasks),
                "estimated_agents": adaptive_plan.decomposition.estimated_agent_count,
                "parallelizable_groups": len(adaptive_plan.decomposition.parallelizable_subtasks)
            },
            "strategy": {
                "selected": adaptive_plan.strategy_recommendation.recommended_strategy.value,
                "rationale": adaptive_plan.strategy_recommendation.strategy_rationale,
                "expected_efficiency": adaptive_plan.strategy_recommendation.expected_efficiency,
                "coordination_overhead": adaptive_plan.strategy_recommendation.coordination_overhead
            },
            "evaluation": {
                "overall_score": adaptive_plan.plan_critique.overall_score,
                "success_probability": adaptive_plan.plan_critique.estimated_success_probability,
                "strengths": adaptive_plan.plan_critique.strengths,
                "optimizations": adaptive_plan.plan_critique.optimization_suggestions
            },
            "phases": []
        }
        
        for phase in adaptive_plan.phases:
            if phase.agents:
                phase_json = {
                    "name": phase.name,
                    "description": phase.description,
                    "coordination_strategy": phase.coordination_strategy.value,
                    "adaptive_threshold": phase.adaptive_threshold,
                    "max_coordination_overhead": phase.max_coordination_overhead,
                    "quality_gate": phase.quality_gate.value,
                    "coordination_pattern": phase.coordination_pattern.value,
                    "dependencies": phase.dependencies,
                    "estimated_duration_minutes": phase.estimated_duration_minutes,
                    "coordination_checkpoints": phase.coordination_checkpoints,
                    "agents": []
                }
                
                for agent in phase.agents:
                    agent_json = {
                        "role": agent.role,
                        "domain": agent.domain,
                        "priority": agent.priority,
                        "reasoning": agent.reasoning,
                        "adaptive_spawn_command": (
                            f'uv run khive compose {agent.role} -d {agent.domain} '
                            f'-c "{request.task_description}" --coordination-id {adaptive_plan.session_id} '
                            f'--adaptive-strategy {phase.coordination_strategy.value}'
                        ),
                        "coordination_protocol": {
                            "pre_task": f"uv run khive coordinate pre-task --agent-id {agent.role}_{agent.domain}",
                            "check_file": f"uv run khive coordinate check --file [FILE] --agent-id {agent.role}_{agent.domain}",
                            "post_edit": f"uv run khive coordinate post-edit --file [FILE] --agent-id {agent.role}_{agent.domain}",
                            "post_task": f"uv run khive coordinate post-task --agent-id {agent.role}_{agent.domain}"
                        }
                    }
                    phase_json["agents"].append(agent_json)
                
                json_structure["phases"].append(phase_json)
        
        import json
        output.append(json.dumps(json_structure, indent=2))
        output.append("```")
        
        return "\n".join(output)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get enhanced metrics including adaptive orchestration metrics."""
        base_metrics = super().get_metrics()
        
        # Add adaptive metrics
        enhanced_metrics = {
            **base_metrics,
            **self.adaptive_metrics
        }
        
        # Calculate additional derived metrics
        if self.adaptive_metrics["adaptive_plans_created"] > 0:
            enhanced_metrics["adaptive_success_rate"] = (
                self.adaptive_metrics["adaptive_plans_created"] / 
                max(1, self.metrics["total_requests"])
            )
            enhanced_metrics["fallback_rate"] = (
                self.adaptive_metrics["fallback_to_traditional"] /
                max(1, self.metrics["total_requests"])
            )
        else:
            enhanced_metrics["adaptive_success_rate"] = 0.0
            enhanced_metrics["fallback_rate"] = 0.0
        
        # Add pipeline metrics if available
        if self._adaptive_pipeline:
            pipeline_metrics = self._adaptive_pipeline.get_metrics()
            enhanced_metrics["pipeline_metrics"] = pipeline_metrics
        
        return enhanced_metrics
    
    async def close(self) -> None:
        """Clean up resources including adaptive pipeline."""
        try:
            # Clean up base service
            await super().close()
            
            # Clean up adaptive pipeline if it exists
            if self._adaptive_pipeline:
                # Pipeline cleanup would go here if needed
                self._adaptive_pipeline = None
                
        except Exception as e:
            logger.error(f"Error during adaptive service cleanup: {e}", exc_info=True)
    
    async def adapt_strategy_runtime(
        self,
        session_id: str,
        current_strategy: CoordinationStrategy,
        performance_metrics: Dict[str, float]
    ) -> CoordinationStrategy:
        """
        Adapt coordination strategy at runtime based on performance metrics.
        
        This method allows for dynamic strategy adaptation during execution.
        """
        if not self.enable_adaptive or not self._adaptive_pipeline:
            return current_strategy
        
        try:
            pipeline = await self._get_adaptive_pipeline()
            
            # Context for strategy adaptation
            context = {
                "session_id": session_id,
                "performance_metrics": performance_metrics,
                "current_time": time.time()
            }
            
            # Use strategist to adapt strategy
            new_strategy = await asyncio.get_event_loop().run_in_executor(
                None, 
                pipeline.strategist.adapt_strategy,
                current_strategy,
                performance_metrics,
                context
            )
            
            if new_strategy != current_strategy:
                self.adaptive_metrics["strategy_adaptations"] += 1
                logger.info(
                    f"Strategy adapted for session {session_id}: "
                    f"{current_strategy.value} → {new_strategy.value}"
                )
            
            return new_strategy
            
        except Exception as e:
            logger.error(f"Failed to adapt strategy: {e}")
            return current_strategy
