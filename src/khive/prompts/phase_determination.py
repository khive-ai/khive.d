"""Phase determination logic for orchestration planning.

This module provides phase detection based on task keywords and patterns,
helping to structure complex tasks into appropriate execution phases.
"""

from typing import List


def determine_required_phases(request_text: str) -> List[str]:
    """Determine which phases are needed based on request keywords.

    Args:
        request_text: The task description text

    Returns:
        List of phase names needed for the task
    """
    text = request_text.lower()
    phases = []

    # Phase keywords mapping
    phase_keywords = {
        "discovery_phase": [
            "research",
            "analyze",
            "understand",
            "investigate",
            "explore",
            "study",
            "examine",
            "discover",
            "assess",
            "evaluate",
        ],
        "design_phase": [
            "design",
            "architect",
            "plan",
            "structure",
            "model",
            "blueprint",
            "schema",
            "layout",
            "organize",
            "framework",
        ],
        "implementation_phase": [
            "implement",
            "build",
            "create",
            "develop",
            "code",
            "construct",
            "write",
            "program",
            "deploy",
            "execute",
        ],
        "validation_phase": [
            "test",
            "verify",
            "validate",
            "check",
            "ensure",
            "confirm",
            "prove",
            "audit",
            "review",
            "inspect",
        ],
        "refinement_phase": [
            "refine",
            "optimize",
            "improve",
            "enhance",
            "polish",
            "document",
            "finalize",
            "complete",
            "perfect",
            "tune",
        ],
    }

    # Check for keywords in request
    for phase, keywords in phase_keywords.items():
        if any(keyword in text for keyword in keywords):
            phases.append(phase)

    # Default phases if none detected
    if not phases:
        # Most tasks need at least discovery and implementation
        phases = ["discovery_phase", "implementation_phase"]

    # Ensure logical phase ordering
    phase_order = [
        "discovery_phase",
        "design_phase",
        "implementation_phase",
        "validation_phase",
        "refinement_phase",
    ]

    # Sort phases according to logical order
    ordered_phases = [phase for phase in phase_order if phase in phases]

    return ordered_phases


def get_phase_description(phase_name: str) -> str:
    """Get a human-readable description for a phase.

    Args:
        phase_name: The name of the phase

    Returns:
        Description of what the phase entails
    """
    descriptions = {
        "discovery_phase": "Research and analysis to understand requirements and constraints",
        "design_phase": "Architecture and system design planning",
        "implementation_phase": "Building and coding the solution",
        "validation_phase": "Testing and verification of the implementation",
        "refinement_phase": "Optimization, documentation, and final polish",
    }

    return descriptions.get(phase_name, f"Execute {phase_name.replace('_', ' ')}")


def estimate_phase_complexity(phase_name: str, task_complexity: str) -> int:
    """Estimate the number of agents needed for a phase based on complexity.

    Args:
        phase_name: The name of the phase
        task_complexity: The overall task complexity level

    Returns:
        Estimated number of agents for this phase
    """
    # Base agent counts by phase
    base_counts = {
        "discovery_phase": {"simple": 1, "medium": 2, "complex": 3, "very_complex": 4},
        "design_phase": {"simple": 1, "medium": 2, "complex": 3, "very_complex": 3},
        "implementation_phase": {
            "simple": 1,
            "medium": 3,
            "complex": 4,
            "very_complex": 5,
        },
        "validation_phase": {"simple": 1, "medium": 2, "complex": 3, "very_complex": 3},
        "refinement_phase": {"simple": 1, "medium": 1, "complex": 2, "very_complex": 2},
    }

    phase_counts = base_counts.get(
        phase_name, {"simple": 1, "medium": 2, "complex": 3, "very_complex": 3}
    )
    return phase_counts.get(task_complexity, 2)
