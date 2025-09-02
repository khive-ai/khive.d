"""
Adaptive Orchestration Pipeline for khive planning system.

This module implements the Decomposer-Strategist-Critic pipeline that integrates
with the existing PlannerService to provide adaptive orchestration capabilities.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
import asyncio
import time

from khive.utils import get_logger
from khive.services.claude.hooks.coordination import get_registry

from .adaptive_models import (
    CoordinationStrategy,
    AdaptiveTaskPhase,
    TaskDecomposition,
    StrategyRecommendation,
    PlanCritique,
    AdaptiveOrchestrationPlan,
    BasicDecomposer,
    BasicStrategist,
    BasicCritic,
    Decomposer,
    Strategist,
    Critic,
)
from .parts import (
    ComplexityLevel,
    WorkflowPattern,
    QualityGate,
    AgentRecommendation,
    PlannerRequest,
    PlannerResponse,
)


logger = get_logger("khive.services.plan.adaptive")


class AdaptiveOrchestrationPipeline:
    """
    Implements the Decomposer-Strategist-Critic pipeline for adaptive orchestration.
    
    This pipeline transforms traditional static planning into adaptive orchestration
    that can adjust coordination strategies based on task characteristics and runtime conditions.
    """
    
    def __init__(
        self,
        decomposer: Optional[Decomposer] = None,
        strategist: Optional[Strategist] = None,
        critic: Optional[Critic] = None,
        enable_coordination: bool = True
    ):
        """Initialize the adaptive orchestration pipeline.
        
        Args:
            decomposer: Task decomposition component (defaults to BasicDecomposer)
            strategist: Strategy selection component (defaults to BasicStrategist)
            critic: Plan evaluation component (defaults to BasicCritic)
            enable_coordination: Whether to integrate with manual coordination protocol
        """
        self.decomposer = decomposer or BasicDecomposer()
        self.strategist = strategist or BasicStrategist()
        self.critic = critic or BasicCritic()
        self.enable_coordination = enable_coordination
        
        # Coordination registry for manual coordination integration
        self._coordination_registry = get_registry() if enable_coordination else None
        
        # Pipeline metrics
        self.metrics = {
            "total_plans": 0,
            "successful_plans": 0,
            "adaptation_events": 0,
            "coordination_conflicts": 0,
            "avg_plan_score": 0.0,
            "total_processing_time": 0.0,
        }
    
    async def create_adaptive_plan(
        self, 
        request: PlannerRequest,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AdaptiveOrchestrationPlan:
        """
        Create an adaptive orchestration plan using the Decomposer-Strategist-Critic pipeline.
        
        Args:
            request: Planning request
            session_id: Unique session identifier
            context: Additional context for planning
            
        Returns:
            Complete adaptive orchestration plan
        """
        start_time = time.time()
        self.metrics["total_plans"] += 1
        
        try:
            logger.info(f"Creating adaptive plan for session {session_id}")
            
            # Phase 1: Decomposer - Break down task into manageable subtasks
            logger.debug("Running Decomposer phase...")
            decomposition = await self._run_decomposer(request.task_description, context)
            
            # Phase 2: Strategist - Select optimal coordination strategy
            logger.debug("Running Strategist phase...")
            strategy_recommendation = await self._run_strategist(decomposition, context)
            
            # Phase 3: Generate phases from decomposition and strategy
            logger.debug("Generating execution phases...")
            phases = self._generate_adaptive_phases(
                decomposition, 
                strategy_recommendation,
                session_id
            )
            
            # Phase 4: Critic - Evaluate and optimize the plan
            logger.debug("Running Critic phase...")
            plan_critique = await self._run_critic(decomposition, strategy_recommendation, phases)
            
            # Phase 5: Apply optimizations if needed
            if plan_critique.overall_score < 0.7:
                logger.info("Applying optimizations based on critique...")
                phases, strategy_recommendation = self._apply_optimizations(
                    phases, strategy_recommendation, plan_critique
                )
                # Re-evaluate after optimizations
                plan_critique = await self._run_critic(decomposition, strategy_recommendation, phases)
            
            # Create final adaptive orchestration plan
            plan = AdaptiveOrchestrationPlan(
                session_id=session_id,
                task_description=request.task_description,
                decomposition=decomposition,
                strategy_recommendation=strategy_recommendation,
                plan_critique=plan_critique,
                phases=phases,
                overall_strategy=strategy_recommendation.recommended_strategy,
                confidence_score=plan_critique.confidence_assessment,
                estimated_total_duration_minutes=self._estimate_total_duration(phases),
            )
            
            # Register with coordination system if enabled
            if self.enable_coordination and self._coordination_registry:
                await self._register_plan_with_coordination(plan)
            
            # Update metrics
            self.metrics["successful_plans"] += 1
            self.metrics["avg_plan_score"] = (
                (self.metrics["avg_plan_score"] * (self.metrics["successful_plans"] - 1) + 
                 plan_critique.overall_score) / self.metrics["successful_plans"]
            )
            
            processing_time = time.time() - start_time
            self.metrics["total_processing_time"] += processing_time
            
            logger.info(
                f"Adaptive plan created successfully: score={plan_critique.overall_score:.2f}, "
                f"strategy={strategy_recommendation.recommended_strategy.value}, "
                f"phases={len(phases)}, time={processing_time:.2f}s"
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"Failed to create adaptive plan: {e}", exc_info=True)
            # Fallback: create basic plan structure
            return self._create_fallback_plan(request, session_id, str(e))
    
    async def _run_decomposer(
        self, 
        task_description: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> TaskDecomposition:
        """Run the decomposer component."""
        if asyncio.iscoroutinefunction(self.decomposer.decompose_task):
            return await self.decomposer.decompose_task(task_description, context)
        else:
            return self.decomposer.decompose_task(task_description, context)
    
    async def _run_strategist(
        self, 
        decomposition: TaskDecomposition,
        context: Optional[Dict[str, Any]] = None
    ) -> StrategyRecommendation:
        """Run the strategist component."""
        # Add coordination system context if available
        coordination_context = context or {}
        if self.enable_coordination and self._coordination_registry:
            coord_status = self._coordination_registry.get_status()
            coordination_context.update({
                "active_agents": coord_status["active_agents"],
                "coordination_overhead": len(coord_status["locked_files"]) / max(1, coord_status["active_agents"]),
                "current_conflicts": len(coord_status["locked_files"]),
            })
        
        if asyncio.iscoroutinefunction(self.strategist.select_strategy):
            return await self.strategist.select_strategy(decomposition, coordination_context)
        else:
            return self.strategist.select_strategy(decomposition, coordination_context)
    
    async def _run_critic(
        self,
        decomposition: TaskDecomposition,
        strategy: StrategyRecommendation,
        phases: List[AdaptiveTaskPhase]
    ) -> PlanCritique:
        """Run the critic component."""
        if asyncio.iscoroutinefunction(self.critic.evaluate_plan):
            return await self.critic.evaluate_plan(decomposition, strategy, phases)
        else:
            return self.critic.evaluate_plan(decomposition, strategy, phases)
    
    def _generate_adaptive_phases(
        self,
        decomposition: TaskDecomposition,
        strategy: StrategyRecommendation,
        session_id: str
    ) -> List[AdaptiveTaskPhase]:
        """Generate adaptive execution phases from decomposition and strategy."""
        phases = []
        
        # Create agent recommendations from subtasks
        agents_per_subtask = max(1, decomposition.estimated_agent_count // len(decomposition.subtasks))
        
        if strategy.recommended_strategy == CoordinationStrategy.PIPELINE:
            # Sequential phases for pipeline strategy
            for i, subtask in enumerate(decomposition.subtasks):
                phase = AdaptiveTaskPhase(
                    name=f"phase_{i+1}",
                    description=subtask,
                    agents=self._create_agent_recommendations(subtask, agents_per_subtask),
                    dependencies=[f"phase_{i}"] if i > 0 else [],
                    quality_gate=self._select_quality_gate(decomposition.complexity_assessment),
                    coordination_pattern=WorkflowPattern.SEQUENTIAL,
                    coordination_strategy=strategy.recommended_strategy,
                    adaptive_threshold=0.7,
                    max_coordination_overhead=strategy.coordination_overhead,
                    estimated_duration_minutes=self._estimate_phase_duration(subtask, agents_per_subtask)
                )
                phases.append(phase)
                
        elif strategy.recommended_strategy == CoordinationStrategy.HIERARCHICAL:
            # Hierarchical phases with team leads
            discovery_phase = AdaptiveTaskPhase(
                name="discovery_phase",
                description="Research and analysis coordination",
                agents=self._create_hierarchical_agents("discovery", decomposition.estimated_agent_count // 3),
                quality_gate=QualityGate.THOROUGH,
                coordination_pattern=WorkflowPattern.HYBRID,
                coordination_strategy=strategy.recommended_strategy,
                coordination_checkpoints=["Team lead sync", "Cross-team review"]
            )
            
            implementation_phase = AdaptiveTaskPhase(
                name="implementation_phase", 
                description="Implementation coordination",
                agents=self._create_hierarchical_agents("implementation", decomposition.estimated_agent_count // 2),
                dependencies=["discovery_phase"],
                quality_gate=QualityGate.THOROUGH,
                coordination_pattern=WorkflowPattern.HYBRID,
                coordination_strategy=strategy.recommended_strategy,
                coordination_checkpoints=["Integration points", "Progress reviews"]
            )
            
            validation_phase = AdaptiveTaskPhase(
                name="validation_phase",
                description="Testing and validation coordination", 
                agents=self._create_hierarchical_agents("validation", decomposition.estimated_agent_count // 4),
                dependencies=["implementation_phase"],
                quality_gate=QualityGate.CRITICAL,
                coordination_pattern=WorkflowPattern.PARALLEL,
                coordination_strategy=strategy.recommended_strategy
            )
            
            phases.extend([discovery_phase, implementation_phase, validation_phase])
            
        else:
            # Default adaptive phases for other strategies
            # Group subtasks by parallelizable groups
            if decomposition.parallelizable_subtasks:
                for i, parallel_group in enumerate(decomposition.parallelizable_subtasks):
                    phase = AdaptiveTaskPhase(
                        name=f"parallel_phase_{i+1}",
                        description=f"Parallel execution: {', '.join(parallel_group)}",
                        agents=self._create_agent_recommendations_for_group(parallel_group, agents_per_subtask),
                        quality_gate=self._select_quality_gate(decomposition.complexity_assessment),
                        coordination_pattern=WorkflowPattern.PARALLEL,
                        coordination_strategy=strategy.recommended_strategy,
                        adaptive_threshold=0.6,  # More adaptive for parallel phases
                        max_coordination_overhead=strategy.coordination_overhead * 1.2  # Allow higher overhead for parallel
                    )
                    phases.append(phase)
            else:
                # Single execution phase
                phase = AdaptiveTaskPhase(
                    name="execution_phase",
                    description="Execute all subtasks with adaptive coordination",
                    agents=self._create_agent_recommendations_for_all_subtasks(decomposition),
                    quality_gate=self._select_quality_gate(decomposition.complexity_assessment),
                    coordination_pattern=WorkflowPattern.HYBRID,
                    coordination_strategy=strategy.recommended_strategy,
                    adaptive_threshold=0.7,
                    max_coordination_overhead=strategy.coordination_overhead
                )
                phases.append(phase)
        
        return phases
    
    def _create_agent_recommendations(self, subtask: str, count: int) -> List[AgentRecommendation]:
        """Create agent recommendations for a subtask."""
        # Simple role mapping based on subtask content
        role_mapping = {
            "analyze": "analyst",
            "research": "researcher", 
            "design": "architect",
            "implement": "implementer",
            "test": "tester",
            "document": "commentator",
            "review": "reviewer",
            "optimize": "critic"
        }
        
        task_lower = subtask.lower()
        role = "implementer"  # default
        for keyword, mapped_role in role_mapping.items():
            if keyword in task_lower:
                role = mapped_role
                break
        
        agents = []
        for i in range(count):
            domain = self._select_domain_for_subtask(subtask)
            agents.append(AgentRecommendation(
                role=role,
                domain=domain,
                priority=1.0 - (i * 0.1),  # Decreasing priority
                reasoning=f"Selected {role} for {subtask} (adaptive orchestration)"
            ))
        
        return agents
    
    def _create_agent_recommendations_for_group(
        self, 
        parallel_group: List[str], 
        agents_per_task: int
    ) -> List[AgentRecommendation]:
        """Create agent recommendations for a group of parallel subtasks."""
        all_agents = []
        for subtask in parallel_group:
            agents = self._create_agent_recommendations(subtask, agents_per_task)
            all_agents.extend(agents)
        return all_agents
    
    def _create_agent_recommendations_for_all_subtasks(
        self, 
        decomposition: TaskDecomposition
    ) -> List[AgentRecommendation]:
        """Create agent recommendations for all subtasks."""
        agents_per_subtask = max(1, decomposition.estimated_agent_count // len(decomposition.subtasks))
        all_agents = []
        
        for subtask in decomposition.subtasks:
            agents = self._create_agent_recommendations(subtask, agents_per_subtask)
            all_agents.extend(agents)
        
        # Ensure we don't exceed estimated count
        return all_agents[:decomposition.estimated_agent_count]
    
    def _create_hierarchical_agents(self, phase_type: str, count: int) -> List[AgentRecommendation]:
        """Create hierarchical agent structure with team leads."""
        agents = []
        
        # Add team lead
        if count > 3:
            lead_role = {
                "discovery": "researcher",
                "implementation": "architect", 
                "validation": "auditor"
            }.get(phase_type, "analyst")
            
            agents.append(AgentRecommendation(
                role=lead_role,
                domain="software-architecture",
                priority=1.0,
                reasoning=f"Team lead for {phase_type} phase"
            ))
            count -= 1
        
        # Add team members
        member_roles = {
            "discovery": ["researcher", "analyst"],
            "implementation": ["implementer", "innovator"],
            "validation": ["tester", "critic", "reviewer"]
        }.get(phase_type, ["implementer", "analyst"])
        
        for i in range(count):
            role = member_roles[i % len(member_roles)]
            domain = self._select_domain_for_phase(phase_type)
            agents.append(AgentRecommendation(
                role=role,
                domain=domain,
                priority=0.9 - (i * 0.1),
                reasoning=f"Team member for {phase_type} phase"
            ))
        
        return agents
    
    def _select_quality_gate(self, complexity: ComplexityLevel) -> QualityGate:
        """Select appropriate quality gate based on complexity."""
        mapping = {
            ComplexityLevel.SIMPLE: QualityGate.BASIC,
            ComplexityLevel.MEDIUM: QualityGate.THOROUGH,
            ComplexityLevel.COMPLEX: QualityGate.THOROUGH,
            ComplexityLevel.VERY_COMPLEX: QualityGate.CRITICAL
        }
        return mapping.get(complexity, QualityGate.THOROUGH)
    
    def _select_domain_for_subtask(self, subtask: str) -> str:
        """Select appropriate domain for a subtask."""
        task_lower = subtask.lower()
        
        domain_mapping = {
            "system": "distributed-systems",
            "architecture": "software-architecture", 
            "security": "security-protocols",
            "performance": "performance-optimization",
            "test": "test-automation",
            "ui": "user-interface",
            "api": "api-design",
            "data": "data-engineering",
            "ml": "machine-learning",
            "integration": "integration-patterns"
        }
        
        for keyword, domain in domain_mapping.items():
            if keyword in task_lower:
                return domain
        
        return "software-architecture"  # default
    
    def _select_domain_for_phase(self, phase_type: str) -> str:
        """Select appropriate domain for a phase type."""
        phase_domains = {
            "discovery": "research-methodology",
            "implementation": "software-architecture", 
            "validation": "quality-assurance"
        }
        return phase_domains.get(phase_type, "software-architecture")
    
    def _estimate_phase_duration(self, subtask: str, agent_count: int) -> int:
        """Estimate duration for a phase in minutes."""
        # Base duration estimation (very basic)
        base_minutes = 60  # 1 hour base
        
        task_lower = subtask.lower()
        if any(keyword in task_lower for keyword in ["implement", "build", "create"]):
            base_minutes *= 2  # Implementation takes longer
        elif any(keyword in task_lower for keyword in ["test", "validate"]):
            base_minutes *= 1.5  # Testing takes moderately longer
        
        # Adjust for agent count (diminishing returns)
        if agent_count > 1:
            efficiency = min(agent_count, 4) * 0.7  # Max 70% efficiency per agent, cap at 4
            base_minutes = int(base_minutes / efficiency)
        
        return base_minutes
    
    def _estimate_total_duration(self, phases: List[AdaptiveTaskPhase]) -> int:
        """Estimate total duration for all phases."""
        total = 0
        for phase in phases:
            if phase.estimated_duration_minutes:
                total += phase.estimated_duration_minutes
            else:
                # Default estimation if not provided
                total += 90  # 1.5 hours per phase
        
        return total
    
    def _apply_optimizations(
        self,
        phases: List[AdaptiveTaskPhase],
        strategy: StrategyRecommendation,
        critique: PlanCritique
    ) -> tuple[List[AdaptiveTaskPhase], StrategyRecommendation]:
        """Apply optimizations based on critique."""
        optimized_phases = phases.copy()
        optimized_strategy = strategy
        
        for suggestion in critique.optimization_suggestions:
            if "simplifying coordination" in suggestion.lower():
                # Simplify coordination strategy
                if strategy.recommended_strategy == CoordinationStrategy.HIERARCHICAL:
                    optimized_strategy = StrategyRecommendation(
                        recommended_strategy=CoordinationStrategy.COLLABORATIVE,
                        alternative_strategies=strategy.alternative_strategies,
                        strategy_rationale="Simplified from hierarchical based on critique",
                        expected_efficiency=strategy.expected_efficiency + 0.1,
                        coordination_overhead=strategy.coordination_overhead - 0.1,
                        risk_assessment=strategy.risk_assessment,
                        monitoring_points=strategy.monitoring_points,
                        adaptation_triggers=strategy.adaptation_triggers
                    )
                    
                    # Update phases to use collaborative strategy
                    for phase in optimized_phases:
                        phase.coordination_strategy = CoordinationStrategy.COLLABORATIVE
                        phase.max_coordination_overhead *= 0.8
            
            elif "smaller" in suggestion.lower():
                # Break down phases with too many agents
                new_phases = []
                for phase in optimized_phases:
                    if len(phase.agents) > 8:
                        # Split the phase
                        mid_point = len(phase.agents) // 2
                        
                        phase1 = AdaptiveTaskPhase(
                            name=f"{phase.name}_part1",
                            description=f"{phase.description} (Part 1)",
                            agents=phase.agents[:mid_point],
                            dependencies=phase.dependencies,
                            quality_gate=phase.quality_gate,
                            coordination_pattern=phase.coordination_pattern,
                            coordination_strategy=phase.coordination_strategy,
                            adaptive_threshold=phase.adaptive_threshold,
                            max_coordination_overhead=phase.max_coordination_overhead
                        )
                        
                        phase2 = AdaptiveTaskPhase(
                            name=f"{phase.name}_part2",
                            description=f"{phase.description} (Part 2)",
                            agents=phase.agents[mid_point:],
                            dependencies=[phase1.name],
                            quality_gate=phase.quality_gate,
                            coordination_pattern=phase.coordination_pattern,
                            coordination_strategy=phase.coordination_strategy,
                            adaptive_threshold=phase.adaptive_threshold,
                            max_coordination_overhead=phase.max_coordination_overhead
                        )
                        
                        new_phases.extend([phase1, phase2])
                    else:
                        new_phases.append(phase)
                
                optimized_phases = new_phases
        
        return optimized_phases, optimized_strategy
    
    async def _register_plan_with_coordination(self, plan: AdaptiveOrchestrationPlan):
        """Register plan with coordination system for conflict prevention."""
        if not self._coordination_registry:
            return
            
        # Register anticipated file operations
        for phase in plan.phases:
            for agent in phase.agents:
                agent_id = f"{agent.role}_{agent.domain}"
                task_desc = f"{phase.description} ({plan.task_description})"
                
                # Register the work
                result = self._coordination_registry.register_agent_work(
                    agent_id, task_desc, []
                )
                
                if result["status"] == "duplicate_detected":
                    self.metrics["coordination_conflicts"] += 1
                    logger.warning(f"Coordination conflict detected: {result['message']}")
    
    def _create_fallback_plan(
        self, 
        request: PlannerRequest, 
        session_id: str, 
        error_message: str
    ) -> AdaptiveOrchestrationPlan:
        """Create a basic fallback plan when adaptive planning fails."""
        # Basic decomposition
        fallback_decomposition = TaskDecomposition(
            subtasks=["Analyze requirements", "Implement solution", "Test and validate"],
            complexity_assessment=ComplexityLevel.MEDIUM,
            estimated_agent_count=3,
            parallelizable_subtasks=[],
            sequential_dependencies={},
            coordination_requirements=[],
            risk_factors=["Adaptive planning failed"],
            decomposition_confidence=0.5
        )
        
        # Basic strategy
        fallback_strategy = StrategyRecommendation(
            recommended_strategy=CoordinationStrategy.AUTONOMOUS,
            alternative_strategies=[],
            strategy_rationale=f"Fallback strategy due to error: {error_message}",
            expected_efficiency=0.6,
            coordination_overhead=0.1,
            risk_assessment={"planning_failure": 0.8},
            monitoring_points=[],
            adaptation_triggers=[]
        )
        
        # Basic critique
        fallback_critique = PlanCritique(
            overall_score=0.5,
            strengths=["Simple fallback approach"],
            weaknesses=["Adaptive planning failed", "Limited optimization"],
            optimization_suggestions=["Retry with manual planning"],
            risk_warnings=["High uncertainty due to planning failure"],
            alternative_approaches=["Manual task breakdown"],
            confidence_assessment=0.5,
            estimated_success_probability=0.6
        )
        
        # Basic phases
        fallback_phases = [AdaptiveTaskPhase(
            name="fallback_execution",
            description="Execute task with basic coordination",
            agents=[
                AgentRecommendation(
                    role="implementer",
                    domain="software-architecture", 
                    priority=1.0,
                    reasoning="Fallback agent assignment"
                )
            ],
            quality_gate=QualityGate.BASIC,
            coordination_pattern=WorkflowPattern.SEQUENTIAL,
            coordination_strategy=CoordinationStrategy.AUTONOMOUS
        )]
        
        return AdaptiveOrchestrationPlan(
            session_id=session_id,
            task_description=request.task_description,
            decomposition=fallback_decomposition,
            strategy_recommendation=fallback_strategy,
            plan_critique=fallback_critique,
            phases=fallback_phases,
            overall_strategy=CoordinationStrategy.AUTONOMOUS,
            confidence_score=0.5,
            estimated_total_duration_minutes=180  # 3 hours fallback
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get pipeline performance metrics."""
        metrics = self.metrics.copy()
        if metrics["total_plans"] > 0:
            metrics["success_rate"] = metrics["successful_plans"] / metrics["total_plans"]
            metrics["avg_processing_time"] = metrics["total_processing_time"] / metrics["total_plans"]
        else:
            metrics["success_rate"] = 0.0
            metrics["avg_processing_time"] = 0.0
        
        return metrics
