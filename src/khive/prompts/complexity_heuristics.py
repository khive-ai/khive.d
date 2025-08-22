"""Complexity assessment heuristics for orchestration planning.

This module provides nuanced semantic understanding for complexity assessment,
balancing keyword matching with intent recognition.
"""

from typing import List


def assess_by_heuristics(text: str) -> List[str]:
    """Assess complexity using heuristic patterns with nuanced semantic understanding.

    Args:
        text: The request text to analyze

    Returns:
        List of complexity tier matches (e.g., ["simple"], ["complex"], ["very_complex"])
    """
    hits = []
    text = text.lower()

    # Simple indicators
    simple_patterns = [
        "simple",
        "basic",
        "quick",
        "easy",
        "straightforward",
        "single",
        "one",
        "just",
        "only",
        "minimal",
    ]

    # Complex indicators (weighted by semantic intensity)
    complex_patterns = [
        "complex",
        "complicated",
        "advanced",
        "sophisticated",
        "distributed",
        "scalable",
        "enterprise",
        "production",
        "multiple",
        "many",
        "various",
        "comprehensive",
    ]

    # Very complex indicators
    very_complex_patterns = [
        "research",
        "novel",
        "innovative",
        "cutting-edge",
        "entire",
        "complete",
        "full",
        "platform",
        "ecosystem",
        "migration",
        "transformation",
        "overhaul",
    ]

    # High-intensity complex indicators that suggest very_complex when combined
    high_intensity_complex = [
        "distributed",
        "sophisticated",
        "advanced",
        "enterprise",
        "comprehensive",
    ]

    # Count pattern matches
    simple_count = sum(1 for pattern in simple_patterns if pattern in text)
    complex_count = sum(1 for pattern in complex_patterns if pattern in text)
    very_complex_count = sum(1 for pattern in very_complex_patterns if pattern in text)
    high_intensity_count = sum(
        1 for pattern in high_intensity_complex if pattern in text
    )

    # Special phrase overrides - these strongly indicate specific tiers
    if any(
        phrase in text
        for phrase in ["entire system", "complete platform", "distributed system"]
    ):
        hits.append("very_complex")
    # Dense complexity indicators suggest escalation to very_complex
    # When we have multiple high-intensity complex indicators, escalate
    elif complex_count >= 3 and high_intensity_count >= 2:
        # Multiple high-intensity complex indicators together indicate very complex work
        hits.append("very_complex")
    elif complex_count >= 4 or high_intensity_count >= 3:
        # Many complex indicators or several high-intensity ones
        hits.append("very_complex")
    # Mixed very_complex with other patterns - escalate to highest
    elif very_complex_count > 0 and (complex_count > 0 or simple_count > 0):
        hits.append("very_complex")
    # Pattern density thresholds
    elif very_complex_count >= 2:
        hits.append("very_complex")
    elif complex_count >= 2:
        hits.append("complex")
    elif simple_count >= 2:
        hits.append("simple")
    # Single pattern matches as fallback
    elif very_complex_count >= 1:
        hits.append("very_complex")
    elif complex_count >= 1:
        hits.append("complex")
    elif simple_count >= 1:
        hits.append("simple")
    # Mixed simple and complex without clear winner
    elif complex_count > 0 and simple_count > 0:
        hits.append("medium")
    else:
        hits.append("medium")

    return hits or ["medium"]


def get_complexity_weight(text: str) -> float:
    """Calculate a weighted complexity score from 0.0 to 1.0.

    This provides a continuous measure of complexity that can be used
    for more nuanced decision making.

    Args:
        text: The request text to analyze

    Returns:
        Float between 0.0 (simple) and 1.0 (very complex)
    """
    text = text.lower()

    # Weight values for different pattern types
    weights = {
        "simple": -0.1,
        "medium": 0.0,
        "complex": 0.2,
        "very_complex": 0.4,
        "high_intensity": 0.3,
    }

    score = 0.5  # Start at medium

    # Simple patterns reduce score
    simple_patterns = ["simple", "basic", "quick", "easy", "straightforward", "minimal"]
    for pattern in simple_patterns:
        if pattern in text:
            score += weights["simple"]

    # Complex patterns increase score
    complex_patterns = [
        "complex",
        "complicated",
        "advanced",
        "sophisticated",
        "distributed",
    ]
    for pattern in complex_patterns:
        if pattern in text:
            score += weights["complex"]

    # Very complex patterns significantly increase score
    very_complex_patterns = [
        "research",
        "novel",
        "innovative",
        "cutting-edge",
        "entire",
        "platform",
    ]
    for pattern in very_complex_patterns:
        if pattern in text:
            score += weights["very_complex"]

    # Clamp between 0 and 1
    return max(0.0, min(1.0, score))
