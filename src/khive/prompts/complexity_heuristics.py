"""Complexity assessment heuristics for task complexity analysis.

This module provides heuristic-based complexity assessment functionality
that was extracted from the planner service to support independent testing
and modular usage in the khive plan system.
"""

from typing import List


class Request:
    """Request model for complexity assessment."""
    
    def __init__(self, text: str):
        self.text = text.lower()  # For easier pattern matching
        self.original = text


def assess_by_heuristics(task_description: str) -> List[str]:
    """Assess complexity using heuristic patterns when direct indicators don't match.
    
    This function analyzes a task description and returns a list of complexity 
    tiers that match the task based on keyword patterns and heuristics.
    
    Args:
        task_description: The task description to analyze
        
    Returns:
        List of complexity tier strings (e.g., ["simple"], ["complex"])
    """
    req = Request(task_description)
    hits = []
    text = req.text

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
        "fix",
        "update",
        "add",
        "remove"
    ]

    # Complex indicators  
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
        "implement",
        "create", 
        "design",
        "develop",
        "moderate"
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
        "consensus",
        "algorithm",
        "blockchain",
        "machine learning",
        "architecture",
        "system"
    ]

    # Count pattern matches
    simple_count = sum(1 for pattern in simple_patterns if pattern in text)
    complex_count = sum(1 for pattern in complex_patterns if pattern in text)
    very_complex_count = sum(1 for pattern in very_complex_patterns if pattern in text)

    # Special phrases that override pattern counts
    if "distributed system" in text:
        hits.append("complex")
    elif (
        any(pattern in text for pattern in ["entire system", "complete platform"])
        or len(text.split()) > 100
    ):
        hits.append("very_complex")
    # When multiple tier patterns exist, select highest complexity
    elif very_complex_count > 0 and (complex_count > 0 or simple_count > 0):
        # Mixed patterns with very_complex - return highest tier
        hits.append("very_complex")
    elif complex_count > 0 and simple_count > 0:
        # Mixed patterns with complex - return complex
        hits.append("complex")
    # Determine complexity based on pattern density
    elif very_complex_count >= 2:
        hits.append("very_complex")
    elif complex_count >= 2:
        hits.append("complex")
    elif simple_count >= 2:
        hits.append("simple")
    # Single pattern matches
    elif very_complex_count >= 1:
        hits.append("very_complex")
    elif complex_count >= 1:
        hits.append("complex")
    elif simple_count >= 1:
        hits.append("simple")
    else:
        hits.append("medium")

    return hits