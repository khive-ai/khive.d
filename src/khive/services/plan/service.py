"""
Multi-Round Consensus Planning Service.
Implements ChatGPT's design: iterative generation → cross-evaluation → robust aggregation → repair.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# KILL ALL LOGS AT MODULE LEVEL
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger("root").setLevel(logging.CRITICAL)
logging.getLogger("lionagi").setLevel(logging.CRITICAL)
logging.getLogger("backoff").setLevel(logging.CRITICAL)
for handler in logging.getLogger().handlers[:]:
    logging.getLogger().removeHandler(handler)
for handler in logging.getLogger("root").handlers[:]:
    logging.getLogger("root").removeHandler(handler)

from .complexity import (
    choose_pattern,
    estimate_agent_count,
    score_complexity,
    should_escalate_to_expert,
)
from .consensus import ConsensusMethod, MultiRoundConsensus
from .cost_tracker import CostTracker
from .generators import (
    DecomposerEngine,
    GenerationConfig,
    RefinerEngine,
    StrategistEngine,
)
from .judges import JudgeEngine
from .models import ComplexityLevel, PlannerRequest, PlannerResponse


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

        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        # Initialize engines
        gen_config = GenerationConfig(self.config)
        self.decomposer = DecomposerEngine(gen_config)
        self.strategist = StrategistEngine(gen_config)
        self.refiner = RefinerEngine(gen_config)
        self.judge_engine = JudgeEngine(self.config)

        # Initialize consensus system
        consensus_method = ConsensusMethod(
            self.config.get("orchestration", {}).get(
                "consensus_method", "bradley_terry_luce"
            )
        )
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
        # Generate human-readable coordination ID
        # Format: YYYYMMDD_HHMM_task_slug
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")

        # Extract key words from task for readability
        task_words = re.findall(r"\b\w+\b", request.task_description.lower())
        # Prioritize action words and nouns
        action_words = ["add", "fix", "create", "update", "implement", "test", "deploy"]
        key_words = [w for w in task_words if w in action_words][:2]
        if not key_words:
            key_words = [w for w in task_words if len(w) > 3][:2]
        task_slug = "_".join(key_words) if key_words else "task"

        coordination_id = f"{timestamp}_{task_slug}"
        start_time = time.time()

        # Budget enforcement
        time_budget = min(
            request.time_budget_seconds, self.budgets.get("time_seconds", 90.0)
        )
        deadline = start_time + time_budget

        try:
            print(
                f"🚀 Starting Multi-Round Consensus Planning (Coordination: {coordination_id})"
            )
            print(f"   Time Budget: {time_budget:.1f}s")
            print(f"   Max Rounds: {self.orchestration.get('max_rounds', 3)}")

            # COMPLEXITY CHECK - Prevent over-orchestration
            complexity_score = score_complexity(request.task_description)
            print(f"   📊 Complexity Score: {complexity_score:.2f}")

            if should_escalate_to_expert(request.task_description):
                print(
                    "   ⚡ Task is simple - delegating to single expert (no orchestration needed)"
                )

                # Create simple expert-level response
                from .models import AgentRecommendation, TaskPhase

                # Determine the most appropriate role for this task
                task_lower = request.task_description.lower()
                if any(
                    word in task_lower
                    for word in ["api", "endpoint", "server", "backend"]
                ):
                    role, domain = "implementer", "async-programming"
                elif any(
                    word in task_lower
                    for word in ["ui", "frontend", "component", "style"]
                ):
                    role, domain = "implementer", "software-architecture"
                elif any(word in task_lower for word in ["test", "testing"]):
                    role, domain = "tester", "software-architecture"
                elif any(word in task_lower for word in ["doc", "documentation"]):
                    role, domain = "reviewer", "software-architecture"
                else:
                    role, domain = "implementer", "software-architecture"

                expert_agent = AgentRecommendation(
                    role=role,
                    domain=domain,
                    priority=1.0,
                    reasoning=f"Single expert sufficient for simple task (complexity: {complexity_score:.2f})",
                )

                expert_phase = TaskPhase(
                    name="Direct Implementation",
                    description=request.task_description,
                    agents=[expert_agent],
                    quality_gate="basic",
                    coordination_strategy="autonomous",
                )

                # Generate simple spawn command
                spawn_cmd = f'Task("{role}+{domain}: {request.task_description} --coordination-id {coordination_id}")'

                total_time = time.time() - start_time
                print(f"✅ Expert assignment completed in {total_time:.1f}s")
                print(f"📍 Coordination ID: {coordination_id}")

                return PlannerResponse(
                    success=True,
                    summary=f"Expert Assignment - {role.title()} specializing in {domain}",
                    complexity=ComplexityLevel.SIMPLE,
                    recommended_agents=1,
                    phases=[expert_phase],
                    coordination_id=coordination_id,
                    confidence=0.95,  # High confidence for simple tasks
                    spawn_commands=[spawn_cmd],
                )

            # Multi-round orchestration loop (for complex tasks)
            round_number = 0
            best_candidate = None
            best_margin = 0.0
            best_confidence = 0.0

            max_rounds = self.orchestration.get("max_rounds", 3)
            convergence_threshold = self.orchestration.get(
                "convergence_threshold", 0.15
            )

            while (
                round_number < max_rounds
                and time.time() < deadline
                and not self._is_over_budget()
            ):
                round_start = time.time()
                print(f"\n🔄 Round {round_number + 1}")

                # Phase 1: Generate diverse candidates
                print("   📊 Generating decomposition candidates...")
                decompositions = await self.decomposer.generate_candidates(
                    request=request,
                    target_count=self.orchestration.get("candidates_per_round", 8),
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
                    target_count=len(decompositions),
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
                    max_pairs=self.orchestration.get("judge_pairs_per_round", 24),
                )

                if not pairwise_comparisons:
                    print("   ⚠️  No pairwise comparisons completed")
                    # Use first candidate as fallback
                    best_candidate = strategy_candidates[0]
                    best_confidence = 0.5
                    break

                print(
                    f"   ✅ Completed {len(pairwise_comparisons)} pairwise comparisons"
                )

                # Phase 4: Consensus aggregation
                print("   🧮 Computing consensus ranking...")

                # Convert comparisons to format expected by consensus algorithm
                comparison_tuples = []
                candidate_ids = [str(i) for i in range(len(strategy_candidates))]

                for comp in pairwise_comparisons:
                    try:
                        winner_idx = int(comp.winner_id)
                        loser_idx = int(
                            comp.candidate_b_id
                            if comp.winner_id == comp.candidate_a_id
                            else comp.candidate_a_id
                        )
                        judge_id = hash(comp.judge_id) % 1000  # Simple judge ID mapping
                        comparison_tuples.append((winner_idx, loser_idx, judge_id))
                    except (ValueError, AttributeError):
                        continue

                if comparison_tuples:
                    ranked_ids, scores, margin = self.consensus.rank_candidates(
                        comparisons=comparison_tuples, candidate_ids=candidate_ids
                    )

                    # Get best candidate
                    if ranked_ids:
                        best_idx = int(ranked_ids[0])
                        if best_idx < len(strategy_candidates):
                            current_best = strategy_candidates[best_idx]
                            current_confidence = scores.get(ranked_ids[0], 0.0)

                            print(
                                f"   📈 Best candidate: {best_idx}, margin: {margin:.3f}, confidence: {current_confidence:.3f}"
                            )

                            # Update if this is better
                            if margin > best_margin:
                                best_candidate = current_best
                                best_margin = margin
                                best_confidence = current_confidence

                            # Check convergence
                            if self.consensus.should_converge(
                                margin, convergence_threshold
                            ):
                                print(
                                    f"   🎯 Convergence achieved! Margin: {margin:.3f} > threshold: {convergence_threshold}"
                                )
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
                    coordination_id=coordination_id,
                    confidence=0.0,
                    error="Candidate generation failed across all rounds",
                )

            print("\n🔧 Refining and validating final plan...")

            # Get top candidates for refinement
            top_candidates = [best_candidate]

            final_plan = await self.refiner.refine_and_validate(
                top_candidates=top_candidates, request=request
            )

            # Generate summary
            total_time = time.time() - start_time
            summary = self._generate_summary(
                coordination_id=coordination_id,
                rounds_completed=round_number,
                total_time=total_time,
                final_plan=final_plan,
            )

            print(f"✅ Planning completed in {total_time:.1f}s")
            print(
                f"   Rounds: {round_number}, Agents: {len([a for p in final_plan.phases for a in p.agents])}"
            )
            print(f"📍 Coordination ID: {coordination_id}")

            return PlannerResponse(
                success=True,
                summary=summary,
                complexity=ComplexityLevel.COMPLEX,  # Could infer from candidates
                recommended_agents=final_plan.estimated_agents,
                phases=final_plan.phases,
                coordination_id=coordination_id,
                confidence=best_confidence,
                spawn_commands=self._generate_spawn_commands(
                    final_plan, coordination_id
                ),
            )

        except Exception as e:
            print(f"❌ Planning failed: {e}")
            return PlannerResponse(
                success=False,
                summary=f"Planning failed: {str(e)}",
                complexity=ComplexityLevel.SIMPLE,
                recommended_agents=0,
                phases=[],
                coordination_id=coordination_id,
                confidence=0.0,
                error=str(e),
            )

    async def create_plan(self, task: str) -> Dict[str, Any]:
        """
        Create execution plan from task description.

        Wrapper method for compatibility with server.py calls.
        Converts string task to PlannerRequest and returns dict format.

        Args:
            task: Task description string

        Returns:
            Dict containing plan data
        """
        try:
            # Create PlannerRequest from task string
            from .models import ComplexityLevel, PlannerRequest

            request = PlannerRequest(
                task_description=task,
                max_agents=8,  # Default reasonable limit
                complexity=ComplexityLevel.MODERATE,
                time_budget_hours=2.0,
                coordination_id="default",
            )

            # Get plan response
            response = await self.plan(request)

            # Convert to dict format expected by server
            return {
                "success": response.success,
                "summary": response.summary,
                "complexity": (
                    response.complexity.value if response.complexity else "moderate"
                ),
                "recommended_agents": response.recommended_agents,
                "phases": [
                    {
                        "name": phase.name,
                        "description": phase.description,
                        "agents": [
                            {
                                "role": agent.role,
                                "domain": agent.domain,
                                "agent_id": agent.agent_id,
                            }
                            for agent in phase.agents
                        ],
                    }
                    for phase in response.phases
                ],
                "coordination_id": response.coordination_id,
                "confidence": response.confidence,
                "spawn_commands": response.spawn_commands or [],
                "error": response.error,
            }

        except Exception as e:
            return {
                "success": False,
                "summary": f"Plan creation failed: {str(e)}",
                "error": str(e),
            }

    def _is_over_budget(self) -> bool:
        """Check if we're over budget constraints."""
        cost_budget = self.budgets.get("cost_usd", 0.02)
        return self.cost_tracker.total_cost >= cost_budget * 0.95  # 95% threshold

    def _generate_summary(
        self, coordination_id: str, rounds_completed: int, total_time: float, final_plan
    ) -> str:
        """Generate human-readable summary."""
        agent_count = sum(len(phase.agents) for phase in final_plan.phases)

        summary_parts = [
            f"🎯 Multi-Round Consensus Plan (Coordination: {coordination_id})",
            f"📊 Generated through {rounds_completed} consensus rounds in {total_time:.1f}s",
            f"🤖 Allocates {agent_count} agents across {len(final_plan.phases)} phases",
            "",
            "📋 Phase Overview:",
        ]

        for i, phase in enumerate(final_plan.phases, 1):
            agent_roles = [f"{agent.role}+{agent.domain}" for agent in phase.agents]
            summary_parts.append(
                f"  {i}. {phase.name} ({phase.coordination_strategy}) - {', '.join(agent_roles)}"
            )

        return "\n".join(summary_parts)

    def _generate_spawn_commands(self, final_plan, coordination_id: str) -> List[str]:
        """Generate spawn commands with mandatory compose + coordination protocol + orchestrator validation."""
        commands = []

        for phase_idx, phase in enumerate(final_plan.phases):
            # Add orchestrator validation checkpoint BEFORE each phase (except first)
            if phase_idx > 0:
                validation_prompt = f"""
🚨 ORCHESTRATOR VALIDATION CHECKPOINT - PHASE {phase_idx}

**TRUST BUT VERIFY - MANDATORY VALIDATION**

Before proceeding to "{phase.name}", you MUST validate the previous phase:

1. **EMPIRICAL VERIFICATION**:
   - Check actual files created/modified by agents
   - Verify claimed functionality actually works
   - Test integration points between existing systems
   - Validate no over-engineering occurred

2. **DELIVERABLE VALIDATION**:
   - Read agent deliverables: `uv run khive coordinate status`
   - Check workspace artifacts for actual vs claimed work
   - Ensure agents built on existing systems, not created parallel ones
   - Verify <100 lines for "integration" tasks

3. **INTEGRATION TESTING**:
   - Test connections between frontend and backend
   - Verify existing systems still function
   - Check that user workflows actually work end-to-end
   - Confirm no breaking changes to existing functionality

4. **PROCEED ONLY IF**:
   - Agents delivered what they claimed
   - Integration is working (not just "completed")
   - No over-engineering detected
   - Previous phase genuinely complete

❌ **BLOCK PROGRESSION IF**:
   - Agents lied about completion
   - Over-engineering detected (quantum/evolutionary code)
   - Integration not working
   - Existing systems broken

**VALIDATION COMPLETE?** Only spawn Phase {phase_idx + 1} agents after verification.
"""
                commands.append(validation_prompt.strip())

            # Generate agent tasks for current phase
            phase_commands = []
            for agent_idx, agent in enumerate(phase.agents):
                agent_id = f"{agent.role}-{phase_idx:02d}{agent_idx:02d}"

                # Build command with MANDATORY composition + coordination
                cmd_parts = [
                    f'Task("{agent.role}+{agent.domain}: {phase.name}',
                    "",
                    "MANDATORY FIRST ACTION:",
                    f'uv run khive compose {agent.role} -d {agent.domain} -c "{phase.name} - {phase.description[:100]}..." --coordination-id {coordination_id}',
                    "",
                    "MANDATORY COORDINATION PROTOCOL:",
                    f'1. Pre-task: uv run khive coordinate pre-task --description "{phase.name}" --agent-id {agent_id} --coordination-id {coordination_id}',
                    f"2. Validate peer work: Check and test other agents' claimed deliverables BEFORE using them",
                    f'3. Before editing files: uv run khive coordinate check --file "/path/to/file" --agent-id {agent_id}',
                    f'4. After editing files: uv run khive coordinate post-edit --file "/path/to/file" --agent-id {agent_id}',
                    f'5. Post-task: uv run khive coordinate post-task --agent-id {agent_id} --summary "Phase complete"',
                    "",
                    f"TASK DETAILS: {phase.description}",
                    f"COORDINATION STRATEGY: {phase.coordination_strategy}",
                    f"QUALITY GATE: {phase.quality_gate}",
                    f"EXPECTED ARTIFACTS: {', '.join(phase.expected_artifacts)}",
                    f'DEPENDENCIES: {", ".join(phase.dependencies) if phase.dependencies else "None"}")',
                ]

                phase_commands.append("\n".join(cmd_parts))

            # Add all agents for this phase at once (for parallel execution)
            if phase_commands:
                commands.append("\n".join(phase_commands))

        # Final validation checkpoint after all phases
        final_validation = """
🏁 FINAL ORCHESTRATOR VALIDATION CHECKPOINT

**COMPLETE SYSTEM VALIDATION**

Before declaring orchestration complete, verify:

1. **END-TO-END FUNCTIONALITY**:
   - Frontend forms actually spawn real agents
   - Backend APIs connect to real coordination system  
   - Users can complete full workflows successfully
   - All integration points working

2. **NO OVER-ENGINEERING**:
   - No quantum/evolutionary code remains
   - Simple integration achieved
   - Existing systems enhanced, not replaced

3. **DELIVERABLE QUALITY**:
   - All agent deliverables reviewed and validated
   - Claims match actual implementation
   - Integration documented and tested

**SYSTEM READY FOR PRODUCTION?** Only complete orchestration if fully validated.
"""

        commands.append(final_validation.strip())

        return commands


# Factory function for easy instantiation
def create_planner(config_path: Optional[Path] = None) -> ConsensusPlannerV3:
    """Create a consensus planner instance."""
    return ConsensusPlannerV3(config_path)
