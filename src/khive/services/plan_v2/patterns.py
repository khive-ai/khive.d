"""Pattern Generators - All orchestration patterns in one clean file.

This module contains all pattern generation logic without over-engineering.
Direct, fanout, tournament, and hierarchical patterns unified.
"""

from typing import Any, Dict, List

from .core import (
    AgentSpec,
    ComplexityLevel,
    ExecutionPlan,
    PatternType,
    Phase,
    QualityGate,
)


async def generate_pattern_plan(
    pattern_type: PatternType, task: str, consensus: Dict[str, Any]
) -> ExecutionPlan:
    """Generate execution plan for any pattern type."""

    generators = {
        PatternType.DIRECT: _generate_direct,
        PatternType.FANOUT: _generate_fanout,
        PatternType.TOURNAMENT: _generate_tournament,
        PatternType.HIERARCHICAL: _generate_hierarchical,
    }

    generator = generators.get(pattern_type)
    if not generator:
        raise ValueError(f"Unknown pattern type: {pattern_type}")

    return await generator(task, consensus)


# ============================================================================
# Direct Pattern - Single agent execution
# ============================================================================


async def _generate_direct(task: str, consensus: Dict[str, Any]) -> ExecutionPlan:
    """Generate direct execution plan - simple and fast."""

    roles = consensus["roles"]
    domains = consensus["domains"]
    complexity = consensus["complexity"]

    # Single execution phase
    agent = AgentSpec(
        role=roles[0],
        domain=domains[0],
        priority=1.0,
        reasoning=f"Direct execution of {task[:50]}...",
    )

    phases = [
        Phase(
            name="execution",
            description=f"Execute task: {task}",
            agents=[agent],
            pattern="sequential",
            quality_gate=(
                QualityGate.BASIC
                if complexity == ComplexityLevel.SIMPLE
                else QualityGate.THOROUGH
            ),
            estimated_minutes=5,
        )
    ]

    return ExecutionPlan(
        pattern_type=PatternType.DIRECT,
        phases=phases,
        total_agents=1,
        complexity=complexity,
        estimated_minutes=5,
        metadata={"simple_execution": True},
    )


# ============================================================================
# Fanout Pattern - Parallel discovery + synthesis
# ============================================================================


async def _generate_fanout(task: str, consensus: Dict[str, Any]) -> ExecutionPlan:
    """Generate fanout execution plan - parallel discovery with synthesis."""

    roles = consensus["roles"]
    domains = consensus["domains"]
    complexity = consensus["complexity"]
    agent_count = consensus["agent_count"]

    phases = []

    # Phase 1: Parallel Discovery
    discovery_agents = []
    for i in range(min(agent_count - 1, len(roles))):  # Save one for synthesis
        agent = AgentSpec(
            role=roles[i % len(roles)],
            domain=domains[i % len(domains)],
            priority=1.0 - (i * 0.1),
            reasoning=f"Discovery perspective {i + 1}: {task[:40]}...",
        )
        discovery_agents.append(agent)

    phases.append(
        Phase(
            name="discovery",
            description="Parallel discovery and analysis",
            agents=discovery_agents,
            pattern="parallel",
            quality_gate=(
                QualityGate.THOROUGH
                if complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX]
                else QualityGate.BASIC
            ),
            estimated_minutes=8,
        )
    )

    # Phase 2: Synthesis
    synthesis_agent = AgentSpec(
        role="analyst" if "analyst" in roles else roles[0],
        domain=domains[0],
        priority=1.0,
        reasoning=f"Synthesize discoveries for {task[:40]}...",
    )

    phases.append(
        Phase(
            name="synthesis",
            description="Synthesize discoveries into unified result",
            agents=[synthesis_agent],
            pattern="sequential",
            dependencies=["discovery"],
            quality_gate=QualityGate.THOROUGH,
            estimated_minutes=5,
        )
    )

    total_agents = len(discovery_agents) + 1
    return ExecutionPlan(
        pattern_type=PatternType.FANOUT,
        phases=phases,
        total_agents=total_agents,
        complexity=complexity,
        estimated_minutes=13,
        metadata={"discovery_agents": len(discovery_agents), "has_synthesis": True},
    )


# ============================================================================
# Tournament Pattern - Competitive validation
# ============================================================================


async def _generate_tournament(task: str, consensus: Dict[str, Any]) -> ExecutionPlan:
    """Generate tournament execution plan - competitive approaches with validation."""

    roles = consensus["roles"]
    domains = consensus["domains"]
    complexity = consensus["complexity"]
    agent_count = max(consensus["agent_count"], 3)  # Minimum 3 for competition

    phases = []

    # Phase 1: Competing Proposals
    proposal_agents = []
    for i in range(min(3, agent_count - 1)):  # 3 competing approaches max
        agent = AgentSpec(
            role=roles[i % len(roles)],
            domain=domains[i % len(domains)],
            priority=1.0,
            reasoning=f"Competitive approach {i + 1}: {task[:40]}...",
        )
        proposal_agents.append(agent)

    phases.append(
        Phase(
            name="proposals",
            description="Generate competing approaches",
            agents=proposal_agents,
            pattern="parallel",
            quality_gate=QualityGate.THOROUGH,
            estimated_minutes=10,
        )
    )

    # Phase 2: Evaluation & Selection
    evaluator_role = "critic" if "critic" in roles else "analyst"
    evaluator = AgentSpec(
        role=evaluator_role,
        domain=domains[0],
        priority=1.0,
        reasoning=f"Evaluate and select best approach for {task[:40]}...",
    )

    phases.append(
        Phase(
            name="evaluation",
            description="Evaluate proposals and select winner",
            agents=[evaluator],
            pattern="sequential",
            dependencies=["proposals"],
            quality_gate=QualityGate.CRITICAL,
            estimated_minutes=8,
        )
    )

    # Phase 3: Optional Refinement for complex tasks
    if complexity == ComplexityLevel.VERY_COMPLEX:
        refiner = AgentSpec(
            role="architect" if "architect" in roles else roles[0],
            domain=domains[0],
            priority=1.0,
            reasoning=f"Refine selected approach for {task[:40]}...",
        )

        phases.append(
            Phase(
                name="refinement",
                description="Refine and optimize selected approach",
                agents=[refiner],
                pattern="sequential",
                dependencies=["evaluation"],
                quality_gate=QualityGate.THOROUGH,
                estimated_minutes=6,
            )
        )

    total_agents = (
        len(proposal_agents)
        + 1
        + (1 if complexity == ComplexityLevel.VERY_COMPLEX else 0)
    )
    estimated_time = sum(p.estimated_minutes for p in phases)

    return ExecutionPlan(
        pattern_type=PatternType.TOURNAMENT,
        phases=phases,
        total_agents=total_agents,
        complexity=complexity,
        estimated_minutes=estimated_time,
        metadata={
            "competing_approaches": len(proposal_agents),
            "has_refinement": complexity == ComplexityLevel.VERY_COMPLEX,
        },
    )


# ============================================================================
# Hierarchical Pattern - Multi-phase dependencies
# ============================================================================


async def _generate_hierarchical(task: str, consensus: Dict[str, Any]) -> ExecutionPlan:
    """Generate hierarchical execution plan - structured phases with dependencies."""

    roles = consensus["roles"]
    domains = consensus["domains"]
    complexity = consensus["complexity"]
    agent_count = consensus["agent_count"]

    phases = []

    # Phase 1: Research
    researcher = AgentSpec(
        role="researcher" if "researcher" in roles else roles[0],
        domain=domains[0],
        priority=1.0,
        reasoning=f"Initial research for {task[:40]}...",
    )

    phases.append(
        Phase(
            name="research",
            description="Initial research and context gathering",
            agents=[researcher],
            pattern="sequential",
            quality_gate=QualityGate.BASIC,
            estimated_minutes=6,
        )
    )

    # Phase 2: Analysis
    analysts = []
    analyst_count = 2 if complexity == ComplexityLevel.VERY_COMPLEX else 1

    for i in range(analyst_count):
        agent = AgentSpec(
            role="analyst" if "analyst" in roles else roles[i % len(roles)],
            domain=domains[i % len(domains)],
            priority=1.0 - (i * 0.1),
            reasoning=f"Analysis perspective {i + 1}: {task[:40]}...",
        )
        analysts.append(agent)

    phases.append(
        Phase(
            name="analysis",
            description="Detailed analysis based on research",
            agents=analysts,
            pattern="parallel" if len(analysts) > 1 else "sequential",
            dependencies=["research"],
            quality_gate=QualityGate.THOROUGH,
            estimated_minutes=10,
        )
    )

    # Phase 3: Design/Planning
    if "architect" in roles or complexity in [
        ComplexityLevel.COMPLEX,
        ComplexityLevel.VERY_COMPLEX,
    ]:
        architect = AgentSpec(
            role="architect" if "architect" in roles else roles[-1],
            domain=domains[0],
            priority=1.0,
            reasoning=f"Design solution for {task[:40]}...",
        )

        phases.append(
            Phase(
                name="design",
                description="Solution design and planning",
                agents=[architect],
                pattern="sequential",
                dependencies=["analysis"],
                quality_gate=QualityGate.THOROUGH,
                estimated_minutes=8,
            )
        )

    # Phase 4: Review & Validation
    reviewer_role = "critic" if "critic" in roles else "reviewer"
    if reviewer_role not in roles:
        reviewer_role = "analyst"

    reviewer = AgentSpec(
        role=reviewer_role,
        domain=domains[0],
        priority=1.0,
        reasoning=f"Final review and validation for {task[:40]}...",
    )

    last_phase = "design" if "design" in [p.name for p in phases] else "analysis"
    phases.append(
        Phase(
            name="review",
            description="Final review and validation",
            agents=[reviewer],
            pattern="sequential",
            dependencies=[last_phase],
            quality_gate=QualityGate.CRITICAL,
            estimated_minutes=6,
        )
    )

    total_agents = sum(len(p.agents) for p in phases)
    estimated_time = sum(p.estimated_minutes for p in phases)

    return ExecutionPlan(
        pattern_type=PatternType.HIERARCHICAL,
        phases=phases,
        total_agents=total_agents,
        complexity=complexity,
        estimated_minutes=estimated_time,
        metadata={
            "phase_count": len(phases),
            "has_design_phase": "design" in [p.name for p in phases],
            "sequential_execution": True,
        },
    )


# ============================================================================
# Pattern Validation
# ============================================================================


def validate_pattern_context(
    pattern_type: PatternType, consensus: Dict[str, Any]
) -> bool:
    """Simple validation for pattern appropriateness."""

    agent_count = consensus.get("agent_count", 1)
    complexity = consensus.get("complexity", ComplexityLevel.SIMPLE)

    if pattern_type == PatternType.DIRECT:
        return agent_count <= 2 and complexity in [
            ComplexityLevel.SIMPLE,
            ComplexityLevel.MEDIUM,
        ]
    elif pattern_type == PatternType.FANOUT:
        return agent_count >= 2 and complexity != ComplexityLevel.SIMPLE
    elif pattern_type == PatternType.TOURNAMENT:
        return agent_count >= 3 and complexity in [
            ComplexityLevel.COMPLEX,
            ComplexityLevel.VERY_COMPLEX,
        ]
    elif pattern_type == PatternType.HIERARCHICAL:
        return agent_count >= 3 and complexity in [
            ComplexityLevel.COMPLEX,
            ComplexityLevel.VERY_COMPLEX,
        ]

    return True  # Default allow
