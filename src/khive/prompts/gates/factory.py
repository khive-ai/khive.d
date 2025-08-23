"""Quality gate prompt factory for composable validation instructions"""

from typing import Literal

from .design import DESIGN_GATE_PROMPT, MINIMAL_DESIGN_GATE_PROMPT
from .documentation import (DOCUMENTATION_GATE_PROMPT,
                            MINIMAL_DOCUMENTATION_GATE_PROMPT)
from .performance import (MINIMAL_PERFORMANCE_GATE_PROMPT,
                          PERFORMANCE_GATE_PROMPT)
from .security import MINIMAL_SECURITY_GATE_PROMPT, SECURITY_GATE_PROMPT
from .testing import MINIMAL_TESTING_GATE_PROMPT, TESTING_GATE_PROMPT

ProjectPhase = Literal["exploration", "development", "integration", "production"]
GateType = Literal["design", "security", "performance", "testing", "documentation"]


def get_gate_prompt(
    gate_type: GateType,
    phase: ProjectPhase | None = None,
    is_critical_path: bool = False,
    is_experimental: bool = False,
) -> str:
    """
    Get a context-appropriate gate prompt.

    Args:
        gate_type: Type of gate validation needed
        phase: Current project phase (affects strictness)
        is_critical_path: Whether this blocks other work (increases rigor)
        is_experimental: Whether this is experimental/exploratory (reduces strictness)

    Returns:
        Appropriate gate prompt for the context
    """

    # Use minimal gates for exploration/experimental work
    if phase == "exploration" or is_experimental:
        minimal_gates = {
            "design": MINIMAL_DESIGN_GATE_PROMPT,
            "security": MINIMAL_SECURITY_GATE_PROMPT,
            "performance": MINIMAL_PERFORMANCE_GATE_PROMPT,
            "testing": MINIMAL_TESTING_GATE_PROMPT,
            "documentation": MINIMAL_DOCUMENTATION_GATE_PROMPT,
        }
        return minimal_gates.get(gate_type, "")

    # Standard context-aware gates (already updated to be less restrictive)
    standard_gates = {
        "design": DESIGN_GATE_PROMPT,
        "security": SECURITY_GATE_PROMPT,
        "performance": PERFORMANCE_GATE_PROMPT,
        "testing": TESTING_GATE_PROMPT,
        "documentation": DOCUMENTATION_GATE_PROMPT,
    }

    prompt = standard_gates.get(gate_type, "")

    # Add context modifiers
    if is_critical_path and prompt:
        prompt = f"""**CRITICAL PATH ITEM**: This issue blocks other work, so pay extra attention to interfaces and contracts that others will depend on.

{prompt}"""

    if phase and prompt:
        phase_context = {
            "exploration": "This is exploratory work - focus on learning and validation over perfection.",
            "development": "This is active development - balance quality with velocity.",
            "integration": "This is integration phase - focus on interfaces and compatibility.",
            "production": "This is production phase - quality and reliability are paramount.",
        }
        if context := phase_context.get(phase):
            prompt = f"""**PROJECT PHASE: {phase.upper()}**
{context}

{prompt}"""

    return prompt


def get_composite_gate_prompt(
    gate_types: list[GateType],
    phase: ProjectPhase | None = None,
    is_critical_path: bool = False,
    is_experimental: bool = False,
) -> str:
    """
    Combine multiple gate prompts for comprehensive evaluation.

    Args:
        gate_types: List of gate types to combine
        phase: Current project phase
        is_critical_path: Whether this blocks other work
        is_experimental: Whether this is experimental work

    Returns:
        Combined gate prompt
    """
    prompts = [
        f"## {gate_type.upper()} GATE\n{prompt}"
        for gate_type in gate_types
        if (
            prompt := get_gate_prompt(
                gate_type, phase, is_critical_path, is_experimental
            )
        )
    ]

    if not prompts:
        return ""

    combined = "\n\n---\n\n".join(prompts)

    return f"""Evaluate against the following gates, keeping in mind that requirements should be proportional to the issue's scope and project phase:

{combined}

Remember: Perfect is the enemy of good. Focus on what's needed NOW, not hypothetical future requirements."""


def list_available_gates() -> list[str]:
    """List all available gate types"""
    return ["design", "security", "performance", "testing", "documentation"]


def get_phase_description(phase: ProjectPhase) -> str:
    """Get a description of what's important in each phase"""
    descriptions = {
        "exploration": "Focus on validating approach and learning. Speed over perfection.",
        "development": "Build core functionality. Balance quality with development velocity.",
        "integration": "Ensure components work together. Focus on interfaces and contracts.",
        "production": "Prepare for real users. Quality, reliability, and operations matter.",
    }
    return descriptions.get(phase, "")
