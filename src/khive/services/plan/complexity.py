"""
Complexity scorer for task planning.
Implements ChatGPT's mathematical approach to prevent over-engineering.
"""

import math
import re
from collections import Counter

from .models import ComplexityLevel

# Keywords that indicate simple tasks
SIMPLE_KEYWORDS = {
    "add",
    "fix",
    "rename",
    "doc",
    "endpoint",
    "route",
    "update",
    "change",
    "modify",
    "edit",
    "delete",
    "remove",
    "create",
}

# Keywords that indicate complex tasks
COMPLEX_KEYWORDS = {
    "architecture",
    "framework",
    "multi-tenant",
    "orchestration",
    "scaffold",
    "refactor",
    "migrate",
    "redesign",
    "system",
}

# Keywords that indicate high-risk tasks
RISK_KEYWORDS = {
    "protocol",
    "security",
    "migration",
    "distributed",
    "performance",
    "scaling",
    "optimization",
    "concurrent",
    "parallel",
}


def sigmoid(x: float) -> float:
    """Sigmoid activation function."""
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def score_to_level(s: float) -> ComplexityLevel:
    """Map complexity score to complexity level enum."""
    if s < 0.3:
        return ComplexityLevel.SIMPLE
    if s < 0.5:
        return ComplexityLevel.MEDIUM
    if s < 0.8:
        return ComplexityLevel.COMPLEX
    return ComplexityLevel.VERY_COMPLEX


def reconcile_level(
    score: float, votes: list[ComplexityLevel] | None
) -> ComplexityLevel:
    """Reconcile score-based level with model votes using majority rule."""
    lvl = score_to_level(score)
    if not votes:
        return lvl

    # Majority vote with ordering resolution
    order = [
        ComplexityLevel.SIMPLE,
        ComplexityLevel.MEDIUM,
        ComplexityLevel.COMPLEX,
        ComplexityLevel.VERY_COMPLEX,
    ]
    majority = Counter(votes).most_common(1)[0][0]
    return majority if order.index(majority) >= order.index(lvl) else lvl


def extract_task_features(task_description: str) -> tuple[int, int, int, int]:
    """
    Extract features from task description.

    Returns:
        (token_count, simple_count, complex_count, risk_count)
    """
    task_lower = task_description.lower()

    # Count tokens (simple word split)
    tokens = re.findall(r"\b\w+\b", task_lower)
    token_count = len(tokens)

    # Count keyword matches
    simple_count = sum(1 for word in tokens if word in SIMPLE_KEYWORDS)
    complex_count = sum(1 for word in tokens if word in COMPLEX_KEYWORDS)
    risk_count = sum(1 for word in tokens if word in RISK_KEYWORDS)

    return token_count, simple_count, complex_count, risk_count


def score_complexity(task_description: str) -> float:
    """
    Score task complexity using ChatGPT's sigmoid approach.

    Returns:
        Float between 0.0 (simple) and 1.0 (complex)
    """
    token_count, simple_count, complex_count, risk_count = extract_task_features(
        task_description
    )

    # Weights from ChatGPT's specification
    w0, w1, w2, w3 = -2.0, 0.02, 0.6, 0.8

    # Calculate sigmoid input
    x = w0 + w1 * token_count + w2 * (complex_count - simple_count) + w3 * risk_count

    # Apply sigmoid
    s = sigmoid(x)

    # Integration bias - prefer modification over new development
    if "integration" in task_description.lower():
        s = max(0.0, s - 0.2)

    # Clamp to [0, 1]
    return max(0.0, min(1.0, s))


def choose_pattern(
    complexity_score: float,
    has_dependencies: bool = False,
    quality_critical: bool = False,
    reusable: bool = False,
    multiphase: bool = False,
) -> str:
    """
    Choose orchestration pattern based on complexity and requirements.

    Args:
        complexity_score: 0.0-1.0 complexity score
        has_dependencies: Whether task has sequential dependencies
        quality_critical: Whether task requires high quality gates
        reusable: Whether this is for reusable workflows
        multiphase: Whether task naturally splits into phases

    Returns:
        Pattern name: Expert, P∥, P→, P⊕, Pⓕ, P⊗
    """
    # Simple tasks - single expert only if not multi-phase and no deps
    if complexity_score < 0.3 and not (has_dependencies or multiphase):
        return "Expert"

    # Multi-phase tasks should prefer sequential or hybrid
    if multiphase and has_dependencies:
        return "P→"  # Sequential
    if multiphase:
        return "P∥"  # Parallel small fan-out

    # Complex reusable workflows
    if reusable or complexity_score > 0.75:
        return "Pⓕ"  # LionAGI Flow

    # Sequential dependencies
    if has_dependencies:
        return "P→"  # Sequential

    # Quality critical
    if quality_critical:
        return "P⊕"  # Tournament

    # Default parallel
    return "P∥"  # Parallel


def estimate_agent_count(complexity_score: float, pattern: str) -> int:
    """
    Estimate appropriate agent count based on complexity and pattern.

    Args:
        complexity_score: 0.0-1.0 complexity score
        pattern: Chosen orchestration pattern

    Returns:
        Estimated number of agents
    """
    if pattern == "Expert":
        return 1
    elif pattern == "P→":  # Sequential
        return max(2, min(4, int(2 + complexity_score * 2)))
    elif pattern == "P∥":  # Parallel
        return max(3, min(5, int(3 + complexity_score * 2)))
    elif pattern == "P⊕":  # Tournament
        return max(3, min(6, int(3 + complexity_score * 3)))
    elif pattern == "Pⓕ":  # LionAGI Flow
        return max(5, min(8, int(5 + complexity_score * 3)))
    elif pattern == "P⊗":  # Hybrid
        return max(4, min(8, int(4 + complexity_score * 4)))
    else:
        return 3  # Default fallback


def should_escalate_to_expert(task_description: str) -> bool:
    """
    Determine if task should be handled by single expert rather than orchestration.

    This prevents over-orchestration of simple tasks.
    """
    complexity = score_complexity(task_description)
    return complexity < 0.3


# Export main functions
__all__ = [
    "score_complexity",
    "choose_pattern",
    "estimate_agent_count",
    "should_escalate_to_expert",
    "score_to_level",
    "reconcile_level",
]
