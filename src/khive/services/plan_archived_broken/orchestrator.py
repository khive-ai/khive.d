"""
Orchestration components for the Adaptive Planning system.

This module implements the consensus algorithms and orchestration logic
for the Decomposer-Strategist-Critic pipeline using lionagi.
"""

from __future__ import annotations

import asyncio
import time
from typing import List, Dict, Any, Optional, TypeVar, Generic
from collections import Counter
from dataclasses import dataclass
import json

# Lazy lionagi access to allow offline tests without import-time failure
from khive._types import BaseModel as HashableModel
try:  # pragma: no cover - exercised in integration
    from lionagi import Branch as _Branch, iModel as _iModel, ln as _ln
except Exception:  # pragma: no cover
    _Branch = None
    _iModel = None
    class _LN:  # minimal shim for asyncio.gather
        async def gather(self, *aws, return_exceptions=False):
            import asyncio
            return await asyncio.gather(*aws, return_exceptions=return_exceptions)
    _ln = _LN()
from pydantic import Field

from .models import (
    TaskDecomposition,
    DecomposedPhase,
    StrategyRecommendation,
    PhaseAllocation,
    AllocatedAgent,
    PlanCritique,
    OrchestrationResult,
    ComplexityLevel,
    CoordinationStrategy,
    QualityGate,
    PlannerRequest,
    PlannerResponse,
    TaskPhase,
    AgentRecommendation,
)
from .cost_tracker import CostTracker

# Logging setup
try:
    from khive.utils import get_logger
    logger = get_logger("khive.services.plan.orchestrator")
except Exception:  # pragma: no cover - fallback logger
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("khive.services.plan.orchestrator")

T = TypeVar('T', bound=HashableModel)


@dataclass
class ConsensusConfig:
    """Configuration for consensus algorithms."""
    min_agents: int = 3
    max_agents: int = 10
    consensus_threshold: float = 0.6  # 60% agreement required
    confidence_weight: float = 0.3  # Weight for confidence in voting
    timeout_seconds: float = 30.0
    
    
class ConsensusAlgorithm(Generic[T]):
    """
    Generic consensus algorithm for multi-agent voting.
    
    Supports different voting strategies:
    - Simple majority
    - Weighted by confidence
    - Quorum-based
    """
    
    def __init__(self, config: ConsensusConfig = None):
        self.config = config or ConsensusConfig()
    
    async def simple_majority(self, results: List[T]) -> T:
        """Select result with simple majority vote."""
        if not results:
            raise ValueError("No results to reach consensus on")
        
        # For complex objects, serialize to JSON for comparison
        serialized = [r.model_dump_json(exclude_none=True) for r in results]
        counter = Counter(serialized)
        
        # Get the most common result
        most_common = counter.most_common(1)[0]
        most_common_json, count = most_common
        
        # Check if it meets threshold
        threshold = len(results) * self.config.consensus_threshold
        if count < threshold:
            # No clear consensus, return the first high-confidence result
            return results[0]
        
        # Deserialize back to object
        for r in results:
            if r.model_dump_json(exclude_none=True) == most_common_json:
                return r
        
        return results[0]  # Fallback
    
    async def weighted_consensus(
        self, 
        results: List[T], 
        weights: Optional[List[float]] = None
    ) -> T:
        """Select result using weighted voting."""
        if not results:
            raise ValueError("No results to reach consensus on")
        
        if weights is None:
            weights = [1.0] * len(results)
        
        # Create weighted votes
        vote_map: Dict[str, float] = {}
        for result, weight in zip(results, weights):
            key = result.model_dump_json(exclude_none=True)
            vote_map[key] = vote_map.get(key, 0) + weight
        
        # Find winner
        winner_key = max(vote_map, key=vote_map.get)
        
        # Return the corresponding result
        for r in results:
            if r.model_dump_json(exclude_none=True) == winner_key:
                return r
        
        return results[0]  # Fallback
    
    async def merge_results(self, results: List[T]) -> T:
        """
        Merge multiple results into a single consensus result.
        This is type-specific and should be overridden for each model type.
        """
        # Default implementation: use simple majority
        return await self.simple_majority(results)


class DecompositionConsensus(ConsensusAlgorithm[TaskDecomposition]):
    """Consensus algorithm specific to task decomposition."""
    
    async def merge_results(self, results: List[TaskDecomposition]) -> TaskDecomposition:
        """Merge multiple decompositions into consensus."""
        if not results:
            raise ValueError("No decomposition results to merge")
        
        # Aggregate phases from all decompositions
        all_phases: List[DecomposedPhase] = []
        phase_frequency: Dict[str, int] = {}
        
        for decomp in results:
            for phase in decomp.phases:
                phase_key = phase.name.lower()
                phase_frequency[phase_key] = phase_frequency.get(phase_key, 0) + 1
                all_phases.append(phase)
        
        # Select phases that appear in majority of decompositions
        threshold = len(results) * self.config.consensus_threshold
        consensus_phases: List[DecomposedPhase] = []
        seen_names = set()
        
        for phase in all_phases:
            phase_key = phase.name.lower()
            if phase_key not in seen_names and phase_frequency[phase_key] >= threshold:
                consensus_phases.append(phase)
                seen_names.add(phase_key)
        
        # Determine complexity by majority vote
        complexity_votes = Counter([d.estimated_complexity for d in results])
        consensus_complexity = complexity_votes.most_common(1)[0][0]
        
        # Build consensus decomposition
        return TaskDecomposition(
            reasoning="Consensus from multiple decomposition agents",
            phases=consensus_phases,
            estimated_complexity=consensus_complexity,
            parallelizable_groups=[]  # Will be computed separately
        )


class StrategyConsensus(ConsensusAlgorithm[StrategyRecommendation]):
    """Consensus algorithm for strategy recommendations."""
    
    async def merge_results(self, results: List[StrategyRecommendation]) -> StrategyRecommendation:
        """Merge multiple strategy recommendations."""
        if not results:
            raise ValueError("No strategy results to merge")
        
        # Aggregate phase allocations
        phase_allocations: Dict[str, List[PhaseAllocation]] = {}
        
        for strategy in results:
            for allocation in strategy.phase_allocations:
                if allocation.phase_name not in phase_allocations:
                    phase_allocations[allocation.phase_name] = []
                phase_allocations[allocation.phase_name].append(allocation)
        
        # Build consensus allocations
        consensus_allocations: List[PhaseAllocation] = []
        
        for phase_name, allocations in phase_allocations.items():
            # Vote on coordination strategy
            coord_votes = Counter([a.coordination_strategy for a in allocations])
            consensus_coord = coord_votes.most_common(1)[0][0]
            
            # Vote on quality gate
            quality_votes = Counter([a.quality_gate for a in allocations])
            consensus_quality = quality_votes.most_common(1)[0][0]
            
            # Merge agents (take union of all suggested agents)
            all_agents: Dict[str, AllocatedAgent] = {}
            for alloc in allocations:
                for agent in alloc.agents:
                    key = f"{agent.role}_{agent.domain}"
                    if key not in all_agents:
                        all_agents[key] = agent
            
            consensus_allocations.append(PhaseAllocation(
                phase_name=phase_name,
                agents=list(all_agents.values()),
                coordination_strategy=consensus_coord,
                quality_gate=consensus_quality,
                expected_artifacts=[]  # Will be determined later
            ))
        
        # Overall coordination strategy by vote
        overall_votes = Counter([s.overall_coordination for s in results])
        consensus_overall = overall_votes.most_common(1)[0][0]
        
        return StrategyRecommendation(
            reasoning="Consensus from multiple strategy agents",
            phase_allocations=consensus_allocations,
            overall_coordination=consensus_overall
        )


class CritiqueConsensus(ConsensusAlgorithm[PlanCritique]):
    """Consensus algorithm for plan critiques."""
    
    async def merge_results(self, results: List[PlanCritique]) -> PlanCritique:
        """Merge multiple critiques into consensus."""
        if not results:
            raise ValueError("No critique results to merge")
        
        # Aggregate all feedback
        all_strengths = []
        all_weaknesses = []
        all_risks = []
        all_bottlenecks = []
        all_improvements = []
        confidence_scores = []
        
        for critique in results:
            all_strengths.extend(critique.strengths)
            all_weaknesses.extend(critique.weaknesses)
            all_risks.extend(critique.risks)
            all_bottlenecks.extend(critique.bottlenecks)
            all_improvements.extend(critique.suggested_improvements)
            confidence_scores.append(critique.confidence)
        
        # Deduplicate and take most frequent items
        def get_top_items(items: List[str], limit: int = 5) -> List[str]:
            if not items:
                return []
            counter = Counter(items)
            return [item for item, _ in counter.most_common(limit)]
        
        # Calculate average confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        
        return PlanCritique(
            overall_assessment="Consensus critique from multiple analysis agents",
            strengths=get_top_items(all_strengths, 3),
            weaknesses=get_top_items(all_weaknesses, 3),
            risks=get_top_items(all_risks, 5),
            bottlenecks=get_top_items(all_bottlenecks, 3),
            suggested_improvements=get_top_items(all_improvements, 5),
            confidence=avg_confidence
        )


class OrchestrationEvaluator:
    """
    Main orchestration evaluator using lionagi.
    
    This class coordinates the Decomposer-Strategist-Critic pipeline
    with consensus algorithms for robust planning.
    """
    
    def __init__(
        self,
        model_provider: str = "openrouter",
        model_name: str = "google/gemini-2.0-flash-001",
        consensus_config: Optional[ConsensusConfig] = None,
        cost_tracker: Optional[CostTracker] = None,
    ):
        self.model_provider = model_provider
        self.model_name = model_name
        self.consensus_config = consensus_config or ConsensusConfig()
        self.cost_tracker = cost_tracker or CostTracker()
        
        # Load prompts
        self.prompts = self._load_prompts()
        
        # Load available roles and domains
        self.available_roles = [
            "researcher", "analyst", "architect", "strategist",
            "implementer", "tester", "critic", "reviewer",
            "auditor", "innovator", "commentator"
        ]
        self.available_domains = [
            "software-architecture", "distributed-systems", "api-design",
            "security-engineering", "microservices-architecture",
            "frontend-development", "database-design", "cloud-infrastructure",
            "performance-optimization", "testing-strategies", "python", 
            "fastapi", "rest-api", "authentication", "data-modeling"
        ]
        
        # Consensus algorithms for each stage
        self.decomposition_consensus = DecompositionConsensus(self.consensus_config)
        self.strategy_consensus = StrategyConsensus(self.consensus_config)
        self.critique_consensus = CritiqueConsensus(self.consensus_config)
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load system prompts from package or user config."""
        import yaml
        from pathlib import Path

        # Preferred: package prompts next to source tree
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "prompts" / "planner_prompts.yaml",
            Path.home() / ".khive" / "prompts" / "planner_prompts.yaml",
            Path.cwd() / "prompts" / "planner_prompts.yaml",
        ]
        for p in candidates:
            try:
                if p.exists():
                    with p.open("r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                        if data:
                            logger.info(f"Loaded planner prompts from {p}")
                            return data
            except Exception as e:
                logger.warning(f"Failed loading prompts from {p}: {e}")
        logger.warning("Planner prompts not found; proceeding with empty prompts")
        return {}
    
    async def get_orchestration_evaluation(
        self,
        request: PlannerRequest,
        num_evaluators: int = 10
    ) -> OrchestrationResult:
        """
        Execute the full orchestration pipeline with consensus.
        
        Uses lionagi Branch operations with nvidia/nemotron model.
        """
        # Run each stage of the pipeline with consensus
        decomposition = await self._run_decomposer_consensus(request, num_evaluators)
        strategy = await self._run_strategist_consensus(decomposition, request, num_evaluators)
        critique = await self._run_critic_consensus(decomposition, strategy, num_evaluators)
        
        # Build the orchestration result
        from .models import OrchestrationResult
        return OrchestrationResult(
            decomposition=decomposition,
            strategy=strategy,
            critique=critique,
            final_plan=self.synthesize_plan(
                request=request,
                decomposition=decomposition,
                strategy=strategy,
                critique=critique,
                session_id=f"plan_{int(time.time())}"
            )
        )
    
    async def _run_decomposer_consensus(
        self,
        request: PlannerRequest,
        num_agents: int
    ) -> TaskDecomposition:
        """Run multiple decomposer agents and reach consensus."""
        if _iModel is None:
            raise RuntimeError("lionagi not available in this environment")
        model = _iModel(provider=self.model_provider, model=self.model_name)
        
        # Get system prompt
        system_prompt = self.prompts.get("DECOMPOSER_SYSTEM", "")
        
        async def _get_eval():
            branch = _Branch(
                chat_model=model,
                system=system_prompt
            )
            
            instruction = f"""
Decompose this task into 3-7 distinct phases with clear dependencies.

Task: {request.task_description}

Additional Context: {request.context or "None provided"}

Requirements:
1. Each phase must have a clear, descriptive name (not generic like "Design")
2. Phases must follow logical progression
3. Identify dependencies between phases
4. Estimate overall complexity: simple, medium, complex, or very_complex

Output the result in the exact schema format required.
"""
            
            result = await branch.operate(
                instruction=instruction,
                response_format=TaskDecomposition,
            )
            # Approximate cost tracking
            try:
                out_json = result.model_dump_json(exclude_none=True)
                in_tokens = max(1, len(instruction) // 4)
                out_tokens = max(1, len(out_json) // 4)
                self.cost_tracker.add_request(
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    cached_tokens=0,
                    model_name=self.model_name,
                )
            except Exception:
                pass
            return result
        
        results = await _ln.gather(*[_get_eval() for _ in range(num_agents)], return_exceptions=True)
        
        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, TaskDecomposition)]
        
        if not valid_results:
            raise RuntimeError(f"All {num_agents} decomposer agents failed to produce valid results")
        
        # Use consensus algorithm
        return await self.decomposition_consensus.merge_results(valid_results)
    
    async def _run_strategist_consensus(
        self,
        decomposition: TaskDecomposition,
        request: PlannerRequest,
        num_agents: int
    ) -> StrategyRecommendation:
        """Run multiple strategist agents and reach consensus."""
        if _iModel is None:
            raise RuntimeError("lionagi not available in this environment")
        model = _iModel(provider=self.model_provider, model=self.model_name)
        
        # Get system prompt
        system_prompt = self.prompts.get("STRATEGIST_SYSTEM", "")
        
        async def _get_eval():
            branch = _Branch(
                chat_model=model,
                system=system_prompt
            )
            
            # Format phases for context
            phases_desc = "\n".join([
                f"- {p.name}: {p.description} (deps: {', '.join(p.dependencies) or 'none'})"
                for p in decomposition.phases
            ])
            
            instruction = f"""
Allocate specialized agents (Role + Domain) to execute this plan efficiently.

Original Task: {request.task_description}
Complexity: {decomposition.estimated_complexity.value}

Phases to staff:
{phases_desc}

Available Roles: {', '.join(self.available_roles)}

Available Domains: {', '.join(self.available_domains)}

For each phase, specify:
1. Agents with specific Role + Domain combinations
2. SPECIFIC task assignment for each agent (what they will do)
3. Coordination strategy: fan_out_synthesize, sequential_refinement, swarm, map_reduce, consensus_voting, or autonomous
4. Quality gate: basic, thorough, or critical
5. Expected artifacts/outputs from the phase

Allocate 1-5 agents per phase based on complexity. Output in the exact schema format required.
"""
            
            result = await branch.operate(
                instruction=instruction,
                response_format=StrategyRecommendation,
            )
            # Approximate cost tracking
            try:
                out_json = result.model_dump_json(exclude_none=True)
                in_tokens = max(1, len(instruction) // 4)
                out_tokens = max(1, len(out_json) // 4)
                self.cost_tracker.add_request(
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    cached_tokens=0,
                    model_name=self.model_name,
                )
            except Exception:
                pass
            return result
        
        results = await _ln.gather(*[_get_eval() for _ in range(num_agents)], return_exceptions=True)
        
        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, StrategyRecommendation)]
        
        if not valid_results:
            raise RuntimeError(f"All {num_agents} strategist agents failed to produce valid results")
        
        # Use consensus algorithm
        return await self.strategy_consensus.merge_results(valid_results)
    
    async def _run_critic_consensus(
        self,
        decomposition: TaskDecomposition,
        strategy: StrategyRecommendation,
        num_agents: int
    ) -> PlanCritique:
        """Run multiple critic agents and reach consensus."""
        if _iModel is None:
            raise RuntimeError("lionagi not available in this environment")
        model = _iModel(provider=self.model_provider, model=self.model_name)
        
        # Get system prompt
        system_prompt = self.prompts.get("CRITIC_SYSTEM", "")
        
        async def _get_eval():
            branch = _Branch(
                chat_model=model,
                system=system_prompt
            )
            
            # Format plan summary for critique
            phases_summary = []
            for alloc in strategy.phase_allocations:
                agents_desc = ", ".join([
                    f"{a.role}+{a.domain}" for a in alloc.agents
                ])
                phases_summary.append(
                    f"- {alloc.phase_name}: {agents_desc} ({alloc.coordination_strategy.value})"
                )
            
            instruction = f"""
Critically analyze this orchestration plan and identify weaknesses.

Task: {decomposition.reasoning}
Complexity: {decomposition.estimated_complexity.value}

Phase Structure:
{chr(10).join([f"- {p.name}: {p.description}" for p in decomposition.phases])}

Agent Allocation:
{chr(10).join(phases_summary)}

Overall Strategy: {strategy.overall_coordination.value}

Provide:
1. Overall assessment of plan feasibility
2. Specific risks (missing expertise, security gaps, etc.)
3. Bottlenecks (dependencies, overloaded phases, etc.)
4. Actionable improvement suggestions
5. Confidence score (0.0 to 1.0) for success likelihood

Output in the exact schema format required.
"""
            
            result = await branch.operate(
                instruction=instruction,
                response_format=PlanCritique,
            )
            # Approximate cost tracking
            try:
                out_json = result.model_dump_json(exclude_none=True)
                in_tokens = max(1, len(instruction) // 4)
                out_tokens = max(1, len(out_json) // 4)
                self.cost_tracker.add_request(
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    cached_tokens=0,
                    model_name=self.model_name,
                )
            except Exception:
                pass
            return result
        
        results = await _ln.gather(*[_get_eval() for _ in range(num_agents)], return_exceptions=True)
        
        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, PlanCritique)]
        
        if not valid_results:
            raise RuntimeError(f"All {num_agents} critic agents failed to produce valid results")
        
        # Use consensus algorithm
        return await self.critique_consensus.merge_results(valid_results)
    
    def synthesize_plan(
        self,
        request: PlannerRequest,
        decomposition: TaskDecomposition,
        strategy: StrategyRecommendation,
        critique: PlanCritique,
        session_id: str
    ) -> PlannerResponse:
        """
        Synthesize the final plan from pipeline components.
        
        Converts internal models to the external PlannerResponse format.
        """
        # Map decomposition phases by name
        decomp_map = {phase.name: phase for phase in decomposition.phases}
        
        # Build final phases
        final_phases: List[TaskPhase] = []
        total_agents = 0
        spawn_cmds: List[str] = []
        
        for allocation in strategy.phase_allocations:
            if allocation.phase_name not in decomp_map:
                continue
            
            decomp_phase = decomp_map[allocation.phase_name]
            
            # Convert allocated agents to recommendations
            agent_recs: List[AgentRecommendation] = []
            for agent in allocation.agents:
                agent_recs.append(AgentRecommendation(
                    role=agent.role,
                    domain=agent.domain,
                    priority=agent.priority,
                    reasoning=agent.task_assignment
                ))
            
            total_agents += len(agent_recs)
            
            # Build phase
            phase_obj = TaskPhase(
                name=allocation.phase_name,
                description=decomp_phase.description,
                agents=agent_recs,
                dependencies=decomp_phase.dependencies,
                quality_gate=allocation.quality_gate,
                coordination_strategy=allocation.coordination_strategy,
                expected_artifacts=allocation.expected_artifacts,
                coordination_checkpoints=[
                    "pre-task",
                    "file-check",
                    "post-edit", 
                    "post-task"
                ]
            )
            final_phases.append(phase_obj)

            # Generate spawn commands per agent
            for rec in agent_recs:
                ctx = f"Task: {rec.reasoning}. Phase: {allocation.phase_name}. Goal: {request.task_description[:160]}"
                cmd = (
                    f"uv run khive compose {rec.role} -d {rec.domain} -c \"{ctx}\" --coordination-id {session_id}"
                )
                spawn_cmds.append(cmd)
        
        # Generate summary
        summary = self._generate_summary(
            request, 
            final_phases, 
            decomposition.estimated_complexity,
            critique,
            session_id
        )
        
        return PlannerResponse(
            success=True,
            summary=summary,
            complexity=decomposition.estimated_complexity,
            recommended_agents=total_agents,
            phases=final_phases,
            session_id=session_id,
            confidence=critique.confidence,
            spawn_commands=spawn_cmds,
        )
    
    def _generate_summary(
        self,
        request: PlannerRequest,
        phases: List[TaskPhase],
        complexity: ComplexityLevel,
        critique: PlanCritique,
        session_id: str
    ) -> str:
        """Generate human-readable summary."""
        lines = []
        
        lines.append("🎯 Adaptive Orchestration Plan")
        lines.append("-" * 40)
        lines.append(f"📊 Complexity: {complexity.value}")
        lines.append(f"✨ Confidence: {critique.confidence:.0%}")
        lines.append(f"🔗 Coordination ID: {session_id}")
        
        if critique.confidence < 0.75:
            lines.append("")
            lines.append("⚠️ Plan Analysis:")
            if critique.risks:
                lines.append(f"  Risks: {', '.join(critique.risks[:3])}")
            if critique.suggested_improvements:
                lines.append(f"  Suggestions: {', '.join(critique.suggested_improvements[:3])}")
        
        lines.append(f"\n📋 Execution Phases ({len(phases)}):")
        
        for i, phase in enumerate(phases, 1):
            lines.append(f"\n{i}. {phase.name}")
            lines.append(f"   {phase.description}")
            lines.append(f"   Strategy: {phase.coordination_strategy.value}")
            lines.append(f"   Quality: {phase.quality_gate.value}")
            
            if phase.dependencies:
                lines.append(f"   Dependencies: {', '.join(phase.dependencies)}")
            if phase.expected_artifacts:
                lines.append(f"   Artifacts: {', '.join(phase.expected_artifacts)}")
            
            lines.append(f"   Agents ({len(phase.agents)}):")
            for agent in phase.agents:
                lines.append(f"     • {agent.role} ({agent.domain})")
                lines.append(f"       Task: {agent.reasoning}")
        
        return "\n".join(lines)


class AdaptivePlanner:
    """
    High-level planner that uses the OrchestrationEvaluator.
    
    This is the main entry point for the planning service.
    """
    
    def __init__(
        self,
        model_provider: str = "openrouter", 
        model_name: str = "google/gemini-2.0-flash-001",
        consensus_config: Optional[ConsensusConfig] = None,
        cost_tracker: Optional[CostTracker] = None,
    ):
        self.evaluator = OrchestrationEvaluator(
            model_provider=model_provider,
            model_name=model_name,
            consensus_config=consensus_config,
            cost_tracker=cost_tracker,
        )
    
    async def plan(
        self,
        request: PlannerRequest,
        num_evaluators: int = 5
    ) -> PlannerResponse:
        """
        Generate an adaptive orchestration plan.
        
        Args:
            request: The planning request
            num_evaluators: Number of agents for consensus (3-10)
            
        Returns:
            PlannerResponse with the orchestration plan
        """
        # Validate num_evaluators
        config = self.evaluator.consensus_config
        num_evaluators = max(config.min_agents, min(config.max_agents, num_evaluators))
        
        # Generate session ID
        import time
        session_id = f"plan_{int(time.time())}"
        
        try:
            # Run the orchestration pipeline
            result = await self.evaluator.get_orchestration_evaluation(
                request=request,
                num_evaluators=num_evaluators
            )
            
            # Synthesize the final plan
            return self.evaluator.synthesize_plan(
                request=request,
                decomposition=result.decomposition,
                strategy=result.strategy,
                critique=result.critique,
                session_id=session_id
            )
        
        except Exception as e:
            # Return error response
            return PlannerResponse(
                success=False,
                summary=f"Planning failed: {str(e)}",
                complexity=ComplexityLevel.MEDIUM,
                recommended_agents=0,
                phases=[],
                session_id=session_id,
                confidence=0.0,
                error=str(e)
            )
