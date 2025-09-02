"""
Multi-Round Consensus Planning Service.
Implements ChatGPT's design: iterative generation → cross-evaluation → robust aggregation → repair.
"""
from __future__ import annotations
import asyncio
import time
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# KILL ALL LOGS AT MODULE LEVEL
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger("root").setLevel(logging.CRITICAL)
logging.getLogger("lionagi").setLevel(logging.CRITICAL)
logging.getLogger("backoff").setLevel(logging.CRITICAL)
for handler in logging.getLogger().handlers[:]:
    logging.getLogger().removeHandler(handler)
for handler in logging.getLogger("root").handlers[:]:
    logging.getLogger("root").removeHandler(handler)

from .models import PlannerRequest, PlannerResponse, ComplexityLevel
from .generators import DecomposerEngine, StrategistEngine, RefinerEngine, GenerationConfig
from .judges import JudgeEngine
from .consensus import MultiRoundConsensus, ConsensusMethod
from .cost_tracker import CostTracker


class ConsensusPlannerV3:
    """
    Multi-round consensus planner implementing ChatGPT's design.
    
    Workflow:
    1. Round 1-N: Candidate generation (decomposer → strategist)
    2. Cross-judgment: Pairwise comparisons and rubric scoring
    3. Consensus aggregation: BTL/RankCentrality ranking
    4. Convergence check: Stop if margin > threshold or budget exhausted
    5. Repair/Synthesis: Refine top candidates into final plan
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with configuration."""
        if config_path is None:
            config_path = Path(__file__).parent / "models.yaml"
            
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize engines
        gen_config = GenerationConfig(self.config)
        self.decomposer = DecomposerEngine(gen_config)
        self.strategist = StrategistEngine(gen_config)  
        self.refiner = RefinerEngine(gen_config)
        self.judge_engine = JudgeEngine(self.config)
        
        # Initialize consensus system
        consensus_method = ConsensusMethod(self.config.get("orchestration", {}).get("consensus_method", "bradley_terry_luce"))
        self.consensus = MultiRoundConsensus(consensus_method)
        
        # Initialize tracking
        self.cost_tracker = CostTracker()
        
        # Configuration shortcuts
        self.orchestration = self.config.get("orchestration", {})
        self.budgets = self.config.get("budgets", {})
    
    async def plan(self, request: PlannerRequest) -> PlannerResponse:
        """
        Execute multi-round consensus planning.
        
        Returns validated plan or error response.
        """
        session_id = f"plan_{int(time.time())}"
        start_time = time.time()
        
        # Budget enforcement
        time_budget = min(
            request.time_budget_seconds,
            self.budgets.get("time_seconds", 90.0)
        )
        deadline = start_time + time_budget
        
        try:
            print(f"🚀 Starting Multi-Round Consensus Planning (Session: {session_id})")
            print(f"   Time Budget: {time_budget:.1f}s")
            print(f"   Max Rounds: {self.orchestration.get('max_rounds', 3)}")
            
            # Multi-round orchestration loop
            round_number = 0
            best_candidate = None
            best_margin = 0.0
            best_confidence = 0.0
            
            max_rounds = self.orchestration.get("max_rounds", 3)
            convergence_threshold = self.orchestration.get("convergence_threshold", 0.15)
            
            while (round_number < max_rounds and 
                   time.time() < deadline and
                   not self._is_over_budget()):
                
                round_start = time.time()
                print(f"\n🔄 Round {round_number + 1}")
                
                # Phase 1: Generate diverse candidates
                print("   📊 Generating decomposition candidates...")
                decompositions = await self.decomposer.generate_candidates(
                    request=request,
                    target_count=self.orchestration.get("candidates_per_round", 8)
                )
                
                if not decompositions:
                    print("   ❌ No valid decompositions generated")
                    break
                
                print(f"   ✅ Generated {len(decompositions)} decompositions")
                
                # Phase 2: Strategy allocation
                print("   🎯 Generating strategy candidates...")
                strategy_candidates = await self.strategist.generate_strategies(
                    decompositions=decompositions,
                    request=request,
                    target_count=len(decompositions)
                )
                
                if not strategy_candidates:
                    print("   ❌ No valid strategy candidates generated")
                    break
                    
                print(f"   ✅ Generated {len(strategy_candidates)} strategy candidates")
                
                # Phase 3: Cross-judgment and consensus
                print("   ⚖️  Running cross-judgment...")
                pairwise_comparisons = await self.judge_engine.pairwise_comparisons(
                    candidates=strategy_candidates,
                    task_description=request.task_description,
                    max_pairs=self.orchestration.get("judge_pairs_per_round", 24)
                )
                
                if not pairwise_comparisons:
                    print("   ⚠️  No pairwise comparisons completed")
                    # Use first candidate as fallback
                    best_candidate = strategy_candidates[0]
                    best_confidence = 0.5
                    break
                
                print(f"   ✅ Completed {len(pairwise_comparisons)} pairwise comparisons")
                
                # Phase 4: Consensus aggregation
                print("   🧮 Computing consensus ranking...")
                
                # Convert comparisons to format expected by consensus algorithm  
                comparison_tuples = []
                candidate_ids = [str(i) for i in range(len(strategy_candidates))]
                
                for comp in pairwise_comparisons:
                    try:
                        winner_idx = int(comp.winner_id)
                        loser_idx = int(comp.candidate_b_id if comp.winner_id == comp.candidate_a_id else comp.candidate_a_id)
                        judge_id = hash(comp.judge_id) % 1000  # Simple judge ID mapping
                        comparison_tuples.append((winner_idx, loser_idx, judge_id))
                    except (ValueError, AttributeError):
                        continue
                
                if comparison_tuples:
                    ranked_ids, scores, margin = self.consensus.rank_candidates(
                        comparisons=comparison_tuples,
                        candidate_ids=candidate_ids
                    )
                    
                    # Get best candidate
                    if ranked_ids:
                        best_idx = int(ranked_ids[0])
                        if best_idx < len(strategy_candidates):
                            current_best = strategy_candidates[best_idx]
                            current_confidence = scores.get(ranked_ids[0], 0.0)
                            
                            print(f"   📈 Best candidate: {best_idx}, margin: {margin:.3f}, confidence: {current_confidence:.3f}")
                            
                            # Update if this is better
                            if margin > best_margin:
                                best_candidate = current_best
                                best_margin = margin
                                best_confidence = current_confidence
                            
                            # Check convergence
                            if self.consensus.should_converge(margin, convergence_threshold):
                                print(f"   🎯 Convergence achieved! Margin: {margin:.3f} > threshold: {convergence_threshold}")
                                break
                
                round_time = time.time() - round_start
                print(f"   ⏱️  Round completed in {round_time:.1f}s")
                round_number += 1
            
            # Phase 5: Final repair and validation
            if best_candidate is None:
                return PlannerResponse(
                    success=False,
                    summary="No valid candidates generated",
                    complexity=ComplexityLevel.SIMPLE,
                    recommended_agents=0,
                    phases=[],
                    session_id=session_id,
                    confidence=0.0,
                    error="Candidate generation failed across all rounds"
                )
            
            print("\n🔧 Refining and validating final plan...")
            
            # Get top candidates for refinement
            top_candidates = [best_candidate]
            
            final_plan = await self.refiner.refine_and_validate(
                top_candidates=top_candidates,
                request=request
            )
            
            # Generate summary
            total_time = time.time() - start_time
            summary = self._generate_summary(
                session_id=session_id,
                rounds_completed=round_number,
                total_time=total_time,
                final_plan=final_plan
            )
            
            print(f"✅ Planning completed in {total_time:.1f}s")
            print(f"   Rounds: {round_number}, Agents: {len([a for p in final_plan.phases for a in p.agents])}")
            
            return PlannerResponse(
                success=True,
                summary=summary,
                complexity=ComplexityLevel.COMPLEX,  # Could infer from candidates
                recommended_agents=final_plan.estimated_agents,
                phases=final_plan.phases,
                session_id=session_id,
                confidence=best_confidence,
                spawn_commands=self._generate_spawn_commands(final_plan, session_id)
            )
            
        except Exception as e:
            print(f"❌ Planning failed: {e}")
            return PlannerResponse(
                success=False,
                summary=f"Planning failed: {str(e)}",
                complexity=ComplexityLevel.SIMPLE,
                recommended_agents=0,
                phases=[],
                session_id=session_id,
                confidence=0.0,
                error=str(e)
            )
    
    def _is_over_budget(self) -> bool:
        """Check if we're over budget constraints."""
        cost_budget = self.budgets.get("cost_usd", 0.02)
        return self.cost_tracker.total_cost >= cost_budget * 0.95  # 95% threshold
    
    def _generate_summary(
        self,
        session_id: str,
        rounds_completed: int,
        total_time: float,
        final_plan
    ) -> str:
        """Generate human-readable summary."""
        agent_count = sum(len(phase.agents) for phase in final_plan.phases)
        
        summary_parts = [
            f"🎯 Multi-Round Consensus Plan (Session: {session_id})",
            f"📊 Generated through {rounds_completed} consensus rounds in {total_time:.1f}s",
            f"🤖 Allocates {agent_count} agents across {len(final_plan.phases)} phases",
            "",
            "📋 Phase Overview:"
        ]
        
        for i, phase in enumerate(final_plan.phases, 1):
            agent_roles = [f"{agent.role}+{agent.domain}" for agent in phase.agents]
            summary_parts.append(
                f"  {i}. {phase.name} ({phase.coordination_strategy}) - {', '.join(agent_roles)}"
            )
        
        return "\n".join(summary_parts)
    
    def _generate_spawn_commands(self, final_plan, session_id: str) -> List[str]:
        """Generate spawn commands with mandatory compose + coordination protocol."""
        commands = []
        
        for phase_idx, phase in enumerate(final_plan.phases):
            for agent_idx, agent in enumerate(phase.agents):
                agent_id = f"{agent.role}-{phase_idx:02d}{agent_idx:02d}"
                
                # Build command with MANDATORY composition + coordination
                cmd_parts = [
                    f'Task("{agent.role}+{agent.domain}: {phase.name}',
                    "",
                    "MANDATORY FIRST ACTION:",
                    f'uv run khive compose {agent.role} -d {agent.domain} -c "{phase.name} - {phase.description[:100]}..." --coordination-id {session_id}',
                    "",
                    "MANDATORY COORDINATION PROTOCOL:",
                    f'1. Pre-task: uv run khive coordinate pre-task --description "{phase.name}" --agent-id {agent_id} --coordination-id {session_id}',
                    f'2. Before editing files: uv run khive coordinate check --file "/path/to/file" --agent-id {agent_id}',
                    f'3. After editing files: uv run khive coordinate post-edit --file "/path/to/file" --agent-id {agent_id}',
                    f'4. Post-task: uv run khive coordinate post-task --agent-id {agent_id} --summary "Phase complete"',
                    "",
                    f"TASK DETAILS: {phase.description}",
                    f"COORDINATION STRATEGY: {phase.coordination_strategy}",
                    f"QUALITY GATE: {phase.quality_gate}",
                    f"EXPECTED ARTIFACTS: {', '.join(phase.expected_artifacts)}",
                    f"DEPENDENCIES: {', '.join(phase.dependencies) if phase.dependencies else 'None'}\")"
                ]
                
                commands.append('\n'.join(cmd_parts))
        
        return commands


# Factory function for easy instantiation
def create_planner(config_path: Optional[Path] = None) -> ConsensusPlannerV3:
    """Create a consensus planner instance."""
    return ConsensusPlannerV3(config_path)