"""
Candidate generation via LionAGI: Decomposer/Strategist/Refiner pipeline.
Implements self-consistency and multi-model diversity as per ChatGPT's design.
"""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from typing import Any

from lionagi import Branch, iModel

from .models import (
    AgentRecommendation,
    CoordinationStrategy,
    DecompositionCandidate,
    PlannerRequest,
    QualityGate,
    StrategyCandidate,
    TaskPhase,
)


class GenerationConfig:
    """Configuration for candidate generation."""

    def __init__(self, config_dict: dict[str, Any]):
        self.generators = config_dict.get("generators", [])
        self.self_consistency = config_dict.get("self_consistency", {})
        self.validation = config_dict.get("validation", {})
        self.max_concurrency = config_dict.get("budgets", {}).get(
            "max_total_concurrency", 8
        )


class SelfConsistencyEngine:
    """Implements self-consistency for candidate selection."""

    @staticmethod
    def extract_consistent_structure(
        candidates: list[DecompositionCandidate], threshold: float = 0.6
    ) -> DecompositionCandidate | None:
        """
        Apply self-consistency to retain majority structure across rationales.
        Reference: https://arxiv.org/abs/2203.11171
        """
        if not candidates:
            return None

        # Extract structure elements for comparison
        phase_names = []
        dependencies = []
        complexity_votes = []

        for candidate in candidates:
            phase_names.extend([phase.get("name", "") for phase in candidate.phases])
            complexity_votes.append(candidate.estimated_complexity)

            # Extract dependency patterns
            for phase in candidate.phases:
                deps = phase.get("dependencies", [])
                dependencies.extend(deps)

        # Find majority consensus on key elements
        name_counter = Counter(phase_names)
        dep_counter = Counter(dependencies)
        complexity_counter = Counter(complexity_votes)

        # Select candidate with most consistent structure
        best_candidate = None
        best_score = 0

        for candidate in candidates:
            score = 0
            candidate_names = [phase.get("name", "") for phase in candidate.phases]

            # Score based on majority consensus
            for name in candidate_names:
                if name_counter[name] >= len(candidates) * threshold:
                    score += 1

            # Complexity consistency
            if (
                complexity_counter[candidate.estimated_complexity]
                >= len(candidates) * threshold
            ):
                score += 1

            if score > best_score:
                best_score = score
                best_candidate = candidate

        return best_candidate or candidates[0]  # Fallback to first


class DecomposerEngine:
    """Generates diverse phase decompositions using multiple models."""

    DECOMPOSER_PROMPT = """You are an expert software development lifecycle (SDLC) planner and task decomposer.

RULES:
1. Break down the task into 3-7 distinct, actionable phases
2. Each phase must have a clear, descriptive name (not generic like "Design")
3. Phases must follow logical progression toward the objective
4. Identify explicit dependencies between phases
5. Estimate overall complexity: simple, medium, complex, or very_complex
6. Identify which phases can run in parallel

TASK: {task_description}
CONTEXT: {context}

Return a structured JSON response with:
- reasoning: Your rationale for this decomposition
- phases: Array of phase objects with name, description, and dependencies
- estimated_complexity: One of simple, medium, complex, very_complex
- parallelizable_groups: Arrays of phase names that can run in parallel

Focus on practical, implementable phases that build toward the final goal."""

    def __init__(self, config: GenerationConfig):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrency)

    async def generate_candidates(
        self, request: PlannerRequest, target_count: int = 8
    ) -> list[DecompositionCandidate]:
        """Generate diverse decomposition candidates."""
        tasks = []

        # Create tasks for each generator × temperature combination
        generators = [
            g for g in self.config.generators if g.get("role") == "decomposer"
        ]

        for generator in generators[:target_count]:  # Limit to target count
            for temp in generator.get("temps", [0.3]):
                task = asyncio.create_task(
                    self._generate_single_candidate(
                        provider=generator["provider"],
                        model=generator["model"],
                        temperature=temp,
                        request=request,
                    )
                )
                tasks.append(task)

                if len(tasks) >= target_count:
                    break
            if len(tasks) >= target_count:
                break

        # Execute with concurrency limit
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        candidates = [
            result for result in results if isinstance(result, DecompositionCandidate)
        ]

        return candidates[:target_count]  # Ensure we don't exceed target

    async def _generate_single_candidate(
        self, provider: str, model: str, temperature: float, request: PlannerRequest
    ) -> DecompositionCandidate | None:
        """Generate a single decomposition candidate."""
        async with self.semaphore:
            try:
                # Create LionAGI branch
                branch = Branch(chat_model=iModel(provider=provider, model=model))

                # Format prompt
                instruction = self.DECOMPOSER_PROMPT.format(
                    task_description=request.task_description,
                    context=request.context or "No additional context provided",
                )

                # Generate with structured response
                result = await branch.operate(
                    instruction=instruction,
                    response_format=DecompositionCandidate,
                    temperature=temperature,
                )

                return result

            except Exception as e:
                print(f"Decomposition failed for {provider}/{model}: {e}")
                return None


class StrategistEngine:
    """Maps roles, domains, and coordination strategies to phases."""

    STRATEGIST_PROMPT = """You are an elite orchestration strategist specializing in multi-agent coordination.

Your job: Transform phase decompositions into concrete agent allocations with coordination strategies.

CRITICAL REQUIREMENT: Each phase MUST have exactly 6 agents with diverse role+domain combinations.

AVAILABLE ROLES: researcher, analyst, architect, implementer, critic, auditor, tester, reviewer, innovator, strategist, commentator

AVAILABLE DOMAINS: memory-systems, distributed-systems, agentic-systems, event-sourcing, temporal-reasoning, graph-theory, category-theory, software-architecture, microkernel-architecture, protocol-design, async-programming, rust-performance, game-theory

COORDINATION STRATEGIES:
- fan_out_synthesize: Multiple agents work independently, then synthesize
- sequential_refinement: Agents pass work in pipeline fashion
- swarm: Multiple similar agents coordinate dynamically
- map_reduce: Divide work, process in parallel, combine results
- consensus_voting: Multiple agents vote on decisions
- autonomous: Single agent works independently

QUALITY GATES:
- basic: Standard validation
- thorough: Enhanced testing and review
- critical: Maximum oversight and validation

PHASES TO ALLOCATE: {phases_json}
TASK CONTEXT: {task_description}

For each phase, specify:
1. Agents: EXACTLY 6 role + domain combinations with priority (0.0-1.0) and reasoning
2. coordination_strategy: How agents work together
3. quality_gate: Level of validation required
4. expected_artifacts: What this phase produces

AGENT ALLOCATION STRATEGY:
- Use diverse roles (architect, implementer, tester, reviewer, analyst, critic)
- Vary domains based on phase requirements
- Ensure good coverage of skills for each phase

Return structured JSON with reasoning and complete TaskPhase objects."""

    def __init__(self, config: GenerationConfig):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrency)

    async def generate_strategies(
        self,
        decompositions: list[DecompositionCandidate],
        request: PlannerRequest,
        target_count: int = 6,
    ) -> list[StrategyCandidate]:
        """Generate strategy candidates from decompositions."""
        tasks = []

        # Create strategy tasks
        generators = [
            g for g in self.config.generators if g.get("role") == "strategist"
        ]

        for i, decomposition in enumerate(decompositions[:target_count]):
            if i < len(generators):
                generator = generators[i % len(generators)]
                for temp in generator.get("temps", [0.4])[
                    :1
                ]:  # Use one temp per decomposition
                    task = asyncio.create_task(
                        self._generate_single_strategy(
                            provider=generator["provider"],
                            model=generator["model"],
                            temperature=temp,
                            decomposition=decomposition,
                            request=request,
                        )
                    )
                    tasks.append(task)

        # Execute with concurrency
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        strategies = [
            result for result in results if isinstance(result, StrategyCandidate)
        ]

        return strategies

    async def _generate_single_strategy(
        self,
        provider: str,
        model: str,
        temperature: float,
        decomposition: DecompositionCandidate,
        request: PlannerRequest,
    ) -> StrategyCandidate | None:
        """Generate strategy for a decomposition."""
        async with self.semaphore:
            try:
                branch = Branch(chat_model=iModel(provider=provider, model=model))

                instruction = self.STRATEGIST_PROMPT.format(
                    phases_json=json.dumps(decomposition.phases, indent=2),
                    task_description=request.task_description,
                )

                result = await branch.operate(
                    instruction=instruction,
                    response_format=StrategyCandidate,
                    temperature=temperature,
                )

                return result

            except Exception as e:
                print(f"Strategy generation failed for {provider}/{model}: {e}")
                return None


class RefinerEngine:
    """Repairs and validates final plans."""

    REFINER_PROMPT = """You are a master plan refiner and validator.

Your job: Take the top candidate plans and merge/repair them into one coherent, validated plan.

VALIDATION REQUIREMENTS:
1. DAG validation: Dependencies must be acyclic
2. Phase constraints: 3-7 phases, each with ≥1 agent
3. Agent deduplication: Same (role,domain) appears ≤2 times unless SWARM
4. Artifacts: Each phase lists expected_artifacts for handoffs
5. Coordination: Each phase has appropriate CoordinationStrategy

TOP CANDIDATE PLANS: {candidates_json}
ORIGINAL TASK: {task_description}

Merge the best elements from these candidates into a single, validated plan.
Fix any cycles, deduplicate redundant agents, ensure artifact handoffs work.

Return a complete plan with phases as TaskPhase objects."""

    def __init__(self, config: GenerationConfig):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrency)

    async def refine_and_validate(
        self, top_candidates: list[StrategyCandidate], request: PlannerRequest
    ) -> StrategyCandidate:
        """Refine top candidates into final validated plan."""
        async with self.semaphore:
            try:
                # Use best generator for refinement
                generators = [g for g in self.config.generators]
                generator = (
                    generators[0]
                    if generators
                    else {
                        "provider": "openrouter",
                        "model": "google/gemini-2.0-flash-001",
                    }
                )

                branch = Branch(
                    chat_model=iModel(
                        provider=generator["provider"], model=generator["model"]
                    )
                )

                instruction = self.REFINER_PROMPT.format(
                    candidates_json=json.dumps(
                        [
                            {
                                "phases": [
                                    phase.model_dump() for phase in candidate.phases
                                ]
                            }
                            for candidate in top_candidates
                        ],
                        indent=2,
                    ),
                    task_description=request.task_description,
                )

                result = await branch.operate(
                    instruction=instruction,
                    response_format=StrategyCandidate,
                    temperature=0.2,  # Low temperature for consistency
                )

                # Apply hard validation
                validated_result = self._apply_validation_gates(result)
                return validated_result

            except Exception as e:
                print(f"Refinement failed: {e}")
                # Return best candidate as fallback
                return (
                    top_candidates[0]
                    if top_candidates
                    else self._create_emergency_fallback(request)
                )

    def _apply_validation_gates(
        self, candidate: StrategyCandidate
    ) -> StrategyCandidate:
        """Apply hard validation rules."""
        # Ensure phase count is within bounds
        if len(candidate.phases) < 3:
            # Add missing phases (simplified)
            while len(candidate.phases) < 3:
                candidate.phases.append(
                    TaskPhase(
                        name=f"Additional Phase {len(candidate.phases) + 1}",
                        description="Generated phase to meet minimum requirements",
                        agents=[
                            AgentRecommendation(
                                role="implementer",
                                domain="software-architecture",
                                priority=0.8,
                                reasoning="Added to meet phase requirements",
                            )
                        ],
                        quality_gate=QualityGate.BASIC,
                        coordination_strategy=CoordinationStrategy.AUTONOMOUS,
                        expected_artifacts=["phase-output"],
                    )
                )

        elif len(candidate.phases) > 7:
            # Truncate excess phases
            candidate.phases = candidate.phases[:7]

        # Ensure each phase has at least one agent
        for phase in candidate.phases:
            if not phase.agents:
                phase.agents.append(
                    AgentRecommendation(
                        role="implementer",
                        domain="software-architecture",
                        priority=0.7,
                        reasoning="Added to ensure phase has at least one agent",
                    )
                )

        return candidate

    def _create_emergency_fallback(self, request: PlannerRequest) -> StrategyCandidate:
        """Create minimal valid plan as emergency fallback."""
        return StrategyCandidate(
            reasoning="Emergency fallback plan created due to generation failure",
            phases=[
                TaskPhase(
                    name="Analysis and Planning",
                    description="Analyze requirements and create detailed plan",
                    agents=[
                        AgentRecommendation(
                            role="analyst",
                            domain="software-architecture",
                            priority=1.0,
                            reasoning="Primary analysis role",
                        )
                    ],
                    quality_gate=QualityGate.THOROUGH,
                    coordination_strategy=CoordinationStrategy.AUTONOMOUS,
                    expected_artifacts=["analysis-report", "implementation-plan"],
                ),
                TaskPhase(
                    name="Implementation",
                    description="Execute the planned implementation",
                    agents=[
                        AgentRecommendation(
                            role="implementer",
                            domain="software-architecture",
                            priority=1.0,
                            reasoning="Primary implementation role",
                        )
                    ],
                    dependencies=["Analysis and Planning"],
                    quality_gate=QualityGate.THOROUGH,
                    coordination_strategy=CoordinationStrategy.AUTONOMOUS,
                    expected_artifacts=["implementation-code", "documentation"],
                ),
                TaskPhase(
                    name="Testing and Validation",
                    description="Test and validate the implementation",
                    agents=[
                        AgentRecommendation(
                            role="tester",
                            domain="software-architecture",
                            priority=1.0,
                            reasoning="Primary testing role",
                        )
                    ],
                    dependencies=["Implementation"],
                    quality_gate=QualityGate.CRITICAL,
                    coordination_strategy=CoordinationStrategy.AUTONOMOUS,
                    expected_artifacts=["test-results", "validation-report"],
                ),
            ],
            coordination_rationale="Simple sequential pipeline with thorough validation",
            estimated_agents=3,
        )
