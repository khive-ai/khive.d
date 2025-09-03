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
from typing import Any

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
    reconcile_level,
    score_complexity,
    score_to_level,
    should_escalate_to_expert,
)
from .consensus import ConsensusMethod, MultiRoundConsensus
from .cost_tracker import CostTracker
from .generators import (
    DecomposerEngine,
    GenerationConfig,
    RefinerEngine,
    SelfConsistencyEngine,
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

    def __init__(self, config_path: Path | None = None):
        """Initialize with configuration."""
        if config_path is None:
            config_path = Path(__file__).parent / "models.yaml"

        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        # Initialize tracking first
        self.cost_tracker = CostTracker(config=self.config)

        # Initialize engines with cost tracking
        gen_config = GenerationConfig(self.config)
        self.decomposer = DecomposerEngine(gen_config, cost_tracker=self.cost_tracker)
        self.strategist = StrategistEngine(gen_config, cost_tracker=self.cost_tracker)
        self.refiner = RefinerEngine(gen_config, cost_tracker=self.cost_tracker)
        self.judge_engine = JudgeEngine(self.config, cost_tracker=self.cost_tracker)

        # Initialize consensus system
        consensus_method = ConsensusMethod(
            self.config.get("orchestration", {}).get(
                "consensus_method", "bradley_terry_luce"
            )
        )
        self.consensus = MultiRoundConsensus(consensus_method)

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
            request.time_budget_seconds, self.budgets.get("time_seconds", 60.0)
        )
        deadline = start_time + time_budget

        try:
            print(
                f"🚀 Starting Multi-Round Consensus Planning (Coordination: {coordination_id})"
            )
            print(f"   Time Budget: {time_budget:.1f}s")
            print(f"   Max Rounds: {self.orchestration.get('max_rounds', 3)}")

            # Initialize complexity tracking (will be refined by LLM consensus)
            complexity_score = score_complexity(request.task_description)
            print(f"   📊 Initial Complexity Score: {complexity_score:.2f}")
            initial_level = score_to_level(complexity_score)

            # === EARLY EXPERT BYPASS (BEFORE ANY DECOMPOSITION) ===
            # Check human guidance first - don't bypass if user wants complex/specific pattern
            human_guidance = getattr(self, "_human_guidance", {})
            should_bypass = (
                should_escalate_to_expert(request.task_description)
                and not human_guidance.get("force_complex", False)
                and human_guidance.get("force_pattern") not in ["P∥", "P→", "P⊕"]
                and not human_guidance.get("target_agents")
            )  # Don't bypass if user set specific agent count

            if should_bypass:
                print(
                    f"   ⚡ Early Expert Bypass: Task suitable for single expert (complexity: {complexity_score:.2f})"
                )
                from .models import (
                    AgentRecommendation,
                    CoordinationStrategy,
                    QualityGate,
                    TaskPhase,
                )

                expert_agent = AgentRecommendation(
                    role="implementer",
                    domain="software-architecture",
                    priority=1.0,
                    reasoning="early-bypass: simple task detected",
                )
                expert_phase = TaskPhase(
                    name="Direct Implementation",
                    description=request.task_description,
                    agents=[expert_agent],
                    quality_gate=QualityGate.BASIC,
                    coordination_strategy=CoordinationStrategy.AUTONOMOUS,
                )
                spawn_cmd = f'Task("implementer+software-architecture: {request.task_description} --coordination-id {coordination_id}")'
                total_time = time.time() - start_time
                print(f"✅ Expert assignment completed in {total_time:.1f}s")
                return PlannerResponse(
                    success=True,
                    summary="Expert Assignment - Implementer specializing in software-architecture",
                    complexity=initial_level,
                    complexity_score=complexity_score,
                    pattern="Expert",
                    recommended_agents=1,
                    phases=[expert_phase],
                    coordination_id=coordination_id,
                    confidence=0.90,
                    spawn_commands=[spawn_cmd],
                )

            # Multi-round orchestration loop (let LLMs assess complexity)
            round_number = 0
            best_candidate = None
            best_margin = 0.0
            best_confidence = 0.0

            # Initialize complexity variables for use throughout complex planning
            level = initial_level  # Will be refined by decomposer votes
            initial_pattern = "P∥"  # Default, will be set from complexity analysis

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
                round_number += 1
                elapsed = round_start - start_time
                remaining = deadline - round_start
                print(f"\n🔄 Round {round_number}")
                print(f"   ⏰ Elapsed: {elapsed:.1f}s, Remaining: {remaining:.1f}s")

                # Phase 1: Generate diverse candidates
                phase1_start = time.time()
                print("   📊 Generating decomposition candidates...")

                # Calculate remaining time and apply timeout
                remaining_time = max(1.0, deadline - time.time())  # At least 1 second
                try:
                    decompositions = await asyncio.wait_for(
                        self.decomposer.generate_candidates(
                            request=request,
                            target_count=self.orchestration.get(
                                "candidates_per_round", 8
                            ),
                        ),
                        timeout=min(remaining_time, 20.0),  # Max 20s per phase
                    )
                except asyncio.TimeoutError:
                    print("   ⚠️  Decomposition timed out, using fallback")
                    decompositions = []  # Will trigger early exit

                phase1_time = time.time() - phase1_start
                print(f"   ⏰ Phase 1 took: {phase1_time:.1f}s")

                if not decompositions:
                    print("   ❌ No valid decompositions generated")
                    break

                print(f"   ✅ Generated {len(decompositions)} decompositions")

                # Stabilize decomposition structure via self-consistency (if multiple)
                if len(decompositions) > 1:
                    canonical = SelfConsistencyEngine.extract_consistent_structure(
                        decompositions
                    )
                    # Keep canonical plus a couple variants to preserve diversity
                    variants = [d for d in decompositions if d is not canonical][:2]
                    decompositions = [canonical] + variants
                    print(
                        f"   🔧 Applied self-consistency: {len(decompositions)} refined decompositions"
                    )

                # Use decomposer votes to refine complexity level & choose initial pattern for budgeting
                if round_number == 1:  # Only compute once in first round
                    dec_levels = [d.estimated_complexity for d in decompositions]
                    level = reconcile_level(complexity_score, dec_levels)

                    # Safe flags from decompositions to seed initial pattern:
                    has_deps = False
                    multiphase = False

                    for d in decompositions:
                        if isinstance(d.phases, list):
                            if any(
                                len(p.get("dependencies", [])) > 0
                                for p in d.phases
                                if isinstance(p, dict)
                            ):
                                has_deps = True
                            if len(d.phases) > 1:
                                multiphase = True

                    quality_critical = (
                        "test" in request.task_description.lower()
                        or "validate" in request.task_description.lower()
                    )

                    # Apply human guidance for pattern selection
                    human_guidance = getattr(self, "_human_guidance", {})
                    if human_guidance.get("force_pattern"):
                        initial_pattern = human_guidance["force_pattern"]
                    elif human_guidance.get("force_complex"):
                        # Force complex orchestration patterns (avoid Expert)
                        initial_pattern = "P∥" if not has_deps else "P→"
                    else:
                        initial_pattern = choose_pattern(
                            complexity_score,
                            has_dependencies=has_deps,
                            quality_critical=quality_critical,
                            reusable=False,
                            multiphase=multiphase,
                        )
                    print(
                        f"   🧪 Refined Complexity: {level.value} | Pattern: {initial_pattern}"
                    )

                    # Continue with multi-agent orchestration (Expert bypass handled earlier)

                # Phase 2: Strategy allocation
                phase2_start = time.time()
                print("   🎯 Generating strategy candidates...")

                # Set agent ceiling from pattern/level, respecting human guidance
                human_guidance = getattr(self, "_human_guidance", {})
                if human_guidance.get("force_complex"):
                    ceiling = 4  # Allow more agents when forcing complex
                elif initial_pattern == "Expert":
                    ceiling = 1
                elif level == ComplexityLevel.SIMPLE:
                    ceiling = 2
                else:
                    ceiling = 4

                # Calculate remaining time and apply timeout
                remaining_time = max(1.0, deadline - time.time())
                try:
                    strategy_candidates = await asyncio.wait_for(
                        self.strategist.generate_strategies(
                            decompositions=decompositions,
                            request=request,
                            target_count=len(decompositions),
                            agents_per_phase_max=ceiling,
                        ),
                        timeout=min(remaining_time, 20.0),  # Max 20s per phase
                    )
                except asyncio.TimeoutError:
                    print(
                        "   ⚠️  Strategy generation timed out, using first decomposition"
                    )
                    strategy_candidates = []  # Will trigger fallback

                phase2_time = time.time() - phase2_start
                print(f"   ⏰ Phase 2 took: {phase2_time:.1f}s")

                if not strategy_candidates:
                    print("   ❌ No valid strategy candidates generated")
                    break

                print(f"   ✅ Generated {len(strategy_candidates)} strategy candidates")

                # Phase 3: Cross-judgment and consensus
                phase3_start = time.time()
                print("   ⚖️  Running cross-judgment...")

                # Calculate remaining time and apply timeout
                remaining_time = max(1.0, deadline - time.time())
                try:
                    pairwise_comparisons = await asyncio.wait_for(
                        self.judge_engine.pairwise_comparisons(
                            candidates=strategy_candidates,
                            task_description=request.task_description,
                            max_pairs=self.orchestration.get(
                                "judge_pairs_per_round", 24
                            ),
                        ),
                        timeout=min(remaining_time, 15.0),  # Max 15s for judgments
                    )
                except asyncio.TimeoutError:
                    print("   ⚠️  Pairwise comparisons timed out, using first candidate")
                    pairwise_comparisons = []  # Will use first candidate as fallback

                phase3_time = time.time() - phase3_start
                print(f"   ⏰ Phase 3 took: {phase3_time:.1f}s")

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

            # Apply timeout to refinement as well
            remaining_time = max(1.0, deadline - time.time())
            try:
                final_plan = await asyncio.wait_for(
                    self.refiner.refine_and_validate(
                        top_candidates=top_candidates, request=request
                    ),
                    timeout=min(remaining_time, 10.0),  # Max 10s for refinement
                )
            except asyncio.TimeoutError:
                print("   ⚠️  Refinement timed out, using best candidate as-is")
                final_plan = best_candidate  # Use best candidate without refinement

            # GLOBAL AGENT CAP ENFORCEMENT - Keep it simple and predictable
            # Ensure total agents stays within spec limits
            def get_global_agent_limits(
                pattern: str, level: ComplexityLevel
            ) -> tuple[int, int]:
                """Get min/max total agents based on pattern and complexity."""
                if pattern == "Expert":
                    return (1, 1)
                elif level in (ComplexityLevel.SIMPLE, ComplexityLevel.MEDIUM):
                    return (2, 4)
                else:  # COMPLEX or VERY_COMPLEX
                    return (5, 8)

            min_agents, max_agents = get_global_agent_limits(initial_pattern, level)

            # Apply human guidance for target agent count if provided
            human_guidance = getattr(self, "_human_guidance", {})
            if human_guidance.get("target_agents"):
                max_agents = human_guidance["target_agents"]
                print(f"   🎯 Human Override: Target agents set to {max_agents}")

            total_agents = sum(len(phase.agents) for phase in final_plan.phases)

            # If we exceed the max, trim lowest priority agents while keeping at least 1 per phase
            if total_agents > max_agents:
                from .models import AgentRecommendation

                # Collect all agents with their phase index and priority
                agent_priorities = []
                for phase_idx, phase in enumerate(final_plan.phases):
                    for agent_idx, agent in enumerate(phase.agents):
                        agent_priorities.append(
                            (
                                agent.priority,
                                phase_idx,
                                agent_idx,
                                agent,
                            )
                        )

                # Sort by priority (highest first)
                agent_priorities.sort(reverse=True, key=lambda x: x[0])

                # Keep the top agents up to max_agents, ensuring at least 1 per phase
                kept_agents = {}  # phase_idx -> list of agent indices to keep

                # First, ensure each phase has at least one agent (the highest priority one)
                for phase_idx, phase in enumerate(final_plan.phases):
                    if phase.agents:
                        # Find the highest priority agent in this phase
                        best_agent_idx = max(
                            range(len(phase.agents)),
                            key=lambda i: phase.agents[i].priority,
                        )
                        kept_agents[phase_idx] = {best_agent_idx}

                # Now add more agents up to the max limit
                agents_added = sum(len(indices) for indices in kept_agents.values())
                for priority, phase_idx, agent_idx, agent in agent_priorities:
                    if agents_added >= max_agents:
                        break
                    if phase_idx not in kept_agents:
                        kept_agents[phase_idx] = set()
                    if agent_idx not in kept_agents[phase_idx]:
                        kept_agents[phase_idx].add(agent_idx)
                        agents_added += 1

                # Apply the trimming
                for phase_idx, phase in enumerate(final_plan.phases):
                    if phase_idx in kept_agents:
                        phase.agents = [
                            agent
                            for i, agent in enumerate(phase.agents)
                            if i in kept_agents[phase_idx]
                        ]
                    elif not phase.agents:
                        # Emergency: add a default agent if phase has none
                        phase.agents = [
                            AgentRecommendation(
                                role="implementer",
                                domain="software-architecture",
                                priority=0.5,
                                reasoning="Added to ensure phase has at least one agent",
                            )
                        ]

                print(
                    f"   📉 Trimmed agents from {total_agents} to {max_agents} (pattern: {initial_pattern})"
                )

            # Generate summary
            total_time = time.time() - start_time
            summary = self._generate_summary(
                coordination_id=coordination_id,
                rounds_completed=round_number,
                total_time=total_time,
                final_plan=final_plan,
            )

            # Get cost summary
            usage_summary = self.cost_tracker.get_usage_summary()

            print(f"✅ Planning completed in {total_time:.1f}s")
            print(
                f"   Rounds: {round_number}, Agents: {len([a for p in final_plan.phases for a in p.agents])}"
            )
            print(
                f"   💰 Cost: ${usage_summary['total_cost']:.4f} ({usage_summary['request_count']} requests)"
            )
            print(
                f"   🔢 Tokens: {usage_summary['total_input_tokens']:,}+{usage_summary['total_output_tokens']:,}"
            )
            print(f"📍 Coordination ID: {coordination_id}")

            # Compute robust recommended_agents
            computed_agents = estimate_agent_count(complexity_score, initial_pattern)
            recommended_agents = final_plan.estimated_agents or computed_agents

            return PlannerResponse(
                success=True,
                summary=summary,
                complexity=level,
                complexity_score=complexity_score,
                pattern=initial_pattern,
                recommended_agents=recommended_agents,
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
                summary=f"Planning failed: {e!s}",
                complexity=ComplexityLevel.SIMPLE,
                recommended_agents=0,
                phases=[],
                coordination_id=coordination_id,
                confidence=0.0,
                error=str(e),
            )

    async def create_plan(self, task: str) -> dict[str, Any]:
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
            request = PlannerRequest(task_description=task)  # only allowed fields
            response = await self.plan(request)
            return {
                "success": response.success,
                "summary": response.summary,
                "complexity": (
                    response.complexity.value if response.complexity else None
                ),
                "complexity_score": response.complexity_score,
                "pattern": response.pattern,
                "recommended_agents": response.recommended_agents,
                "phases": [
                    {
                        "name": phase.name,
                        "description": phase.description,
                        "agents": [
                            {"role": a.role, "domain": a.domain} for a in phase.agents
                        ],
                        "dependencies": phase.dependencies,
                        "quality_gate": phase.quality_gate,
                        "coordination_strategy": phase.coordination_strategy,
                        "expected_artifacts": phase.expected_artifacts,
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
                "summary": f"Plan creation failed: {e!s}",
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

    def _generate_spawn_commands(self, final_plan, coordination_id: str) -> list[str]:
        """Generate concise spawn commands - coordination protocol handled by khive compose."""
        commands = []

        for phase_idx, phase in enumerate(final_plan.phases):
            # Add validation checkpoint before each phase (except first)
            if phase_idx > 0:
                commands.append(
                    f"🚨 VALIDATION CHECKPOINT: Verify Phase {phase_idx} before proceeding to '{phase.name}'"
                )

            # Generate concise agent commands for current phase
            phase_agents = []
            for agent in phase.agents:
                # Concise spawn command - compose handles coordination protocol
                cmd = f'Task("{agent.role}+{agent.domain}: {phase.name} | {phase.coordination_strategy} | {phase.quality_gate} | {coordination_id}")'
                phase_agents.append(cmd)

            if phase_agents:
                commands.append(f"Phase {phase_idx + 1}: {phase.name}")
                commands.extend(phase_agents)
                commands.append("")  # Blank line between phases

        return commands


# Factory function for easy instantiation
def create_planner(config_path: Path | None = None) -> ConsensusPlannerV3:
    """Create a consensus planner instance."""
    return ConsensusPlannerV3(config_path)
