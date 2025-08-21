"""Task Analysis - Simple and effective task analysis without over-engineering.

This module provides rule-based task analysis, complexity assessment, and
decision logic. No LLM calls, no complex heuristics - just practical rules.
"""

import re
from typing import Any, Dict, List, Tuple

from .core import ComplexityLevel, PatternType

# ============================================================================
# Task Analysis
# ============================================================================


def analyze_task(task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Analyze task to determine characteristics and requirements.

    This replaces the complex LLM-based analysis with simple, fast rules.
    """
    context = context or {}
    task_lower = task.lower()
    words = task.split()

    # Basic task metrics
    word_count = len(words)
    sentence_count = len([s for s in task.split(".") if s.strip()])

    # Task type identification
    task_type = _identify_task_type(task_lower)

    # Complexity assessment
    complexity = _assess_complexity(task_lower, word_count, context)

    # Agent recommendations
    agent_info = _recommend_agents(task_type, complexity, context)

    # Timing estimates
    timing = _estimate_timing(complexity, agent_info["count"])

    return {
        "task_type": task_type,
        "complexity": complexity,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "agent_count": agent_info["count"],
        "recommended_roles": agent_info["roles"],
        "recommended_domains": agent_info["domains"],
        "estimated_minutes": timing,
        "key_terms": _extract_key_terms(task_lower),
        "has_dependencies": _has_dependencies(task_lower),
        "is_critical": _is_critical_task(task_lower),
        "confidence": 0.85,  # Static confidence - good enough
    }


def _identify_task_type(task_lower: str) -> str:
    """Identify the primary type of task."""

    # Analysis tasks
    if any(
        word in task_lower
        for word in [
            "analyze",
            "investigation",
            "research",
            "study",
            "examine",
            "review",
            "assess",
            "evaluate",
            "understand",
        ]
    ):
        return "analysis"

    # Implementation tasks
    elif any(
        word in task_lower
        for word in [
            "implement",
            "build",
            "create",
            "develop",
            "code",
            "construct",
            "make",
            "generate",
            "produce",
        ]
    ):
        return "implementation"

    # Validation tasks
    elif any(
        word in task_lower
        for word in [
            "validate",
            "test",
            "verify",
            "check",
            "confirm",
            "audit",
            "inspect",
            "quality",
        ]
    ):
        return "validation"

    # Design tasks
    elif any(
        word in task_lower
        for word in [
            "design",
            "architect",
            "plan",
            "structure",
            "model",
            "blueprint",
            "framework",
            "pattern",
        ]
    ):
        return "design"

    # Optimization tasks
    elif any(
        word in task_lower
        for word in [
            "optimize",
            "improve",
            "enhance",
            "refactor",
            "streamline",
            "performance",
            "efficiency",
            "speed",
        ]
    ):
        return "optimization"

    # Debug/fix tasks
    elif any(
        word in task_lower
        for word in [
            "debug",
            "fix",
            "resolve",
            "troubleshoot",
            "repair",
            "issue",
            "problem",
            "error",
            "bug",
        ]
    ):
        return "debugging"

    return "general"


def _assess_complexity(
    task_lower: str, word_count: int, context: Dict[str, Any]
) -> ComplexityLevel:
    """Assess task complexity using simple heuristics."""

    # Explicit complexity indicators
    if any(word in task_lower for word in ["simple", "basic", "quick", "easy"]):
        return ComplexityLevel.SIMPLE
    elif any(
        word in task_lower
        for word in ["complex", "difficult", "comprehensive", "extensive"]
    ):
        return ComplexityLevel.VERY_COMPLEX

    # Context override
    if "complexity" in context:
        return ComplexityLevel(context["complexity"])

    complexity_score = 0

    # Length indicators
    if word_count > 50:
        complexity_score += 2
    elif word_count > 20:
        complexity_score += 1

    # Multiple components
    if any(
        word in task_lower for word in ["multiple", "several", "various", "different"]
    ):
        complexity_score += 1

    # Technical depth
    if any(
        word in task_lower
        for word in [
            "architecture",
            "system",
            "distributed",
            "microservice",
            "algorithm",
            "performance",
            "scalability",
            "security",
        ]
    ):
        complexity_score += 1

    # Integration requirements
    if any(word in task_lower for word in ["integrate", "connect", "interface", "api"]):
        complexity_score += 1

    # Dependencies
    if _has_dependencies(task_lower):
        complexity_score += 1

    # Critical/production impact
    if _is_critical_task(task_lower):
        complexity_score += 1

    # Map score to complexity
    if complexity_score <= 1:
        return ComplexityLevel.SIMPLE
    elif complexity_score <= 3:
        return ComplexityLevel.MEDIUM
    elif complexity_score <= 5:
        return ComplexityLevel.COMPLEX
    else:
        return ComplexityLevel.VERY_COMPLEX


def _recommend_agents(
    task_type: str, complexity: ComplexityLevel, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Recommend agents based on task type and complexity."""

    # Base agent counts by complexity
    base_counts = {
        ComplexityLevel.SIMPLE: 1,
        ComplexityLevel.MEDIUM: 3,
        ComplexityLevel.COMPLEX: 4,
        ComplexityLevel.VERY_COMPLEX: 5,
    }

    # Role recommendations by task type
    task_roles = {
        "analysis": ["researcher", "analyst", "critic"],
        "implementation": ["architect", "implementer", "tester"],
        "validation": ["reviewer", "critic", "analyst"],
        "design": ["architect", "analyst", "reviewer"],
        "optimization": ["analyst", "architect", "implementer"],
        "debugging": ["analyst", "implementer", "tester"],
        "general": ["analyst", "researcher", "critic"],
    }

    # Domain recommendations
    task_lower = " ".join([task_type, str(context.get("task", "")).lower()])

    if any(word in task_lower for word in ["api", "service", "system", "architecture"]):
        domains = ["software-architecture", "api-design"]
    elif any(word in task_lower for word in ["database", "data", "storage"]):
        domains = ["backend-development", "database-design"]
    elif any(word in task_lower for word in ["ui", "frontend", "interface", "user"]):
        domains = ["frontend-development", "user-experience"]
    elif any(word in task_lower for word in ["test", "quality", "validation"]):
        domains = ["testing", "quality-assurance"]
    elif any(word in task_lower for word in ["security", "auth", "permission"]):
        domains = ["security", "backend-development"]
    else:
        domains = ["distributed-systems", "software-architecture"]

    agent_count = context.get("agents", base_counts[complexity])
    agent_count = min(max(agent_count, 1), 8)  # Cap between 1-8

    roles = task_roles.get(task_type, task_roles["general"])

    return {"count": agent_count, "roles": roles[:agent_count], "domains": domains[:2]}


def _extract_key_terms(task_lower: str) -> List[str]:
    """Extract key technical terms from task description."""

    # Technical terms patterns
    tech_patterns = [
        r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b",  # CamelCase
        r"\b\w+[-_]\w+\b",  # hyphen/underscore terms
        r"\b(?:api|sql|json|yaml|xml|http|tcp|udp|rest|graphql)\b",  # protocols
        r"\b(?:database|server|client|service|microservice)\b",  # architecture
    ]

    terms = set()
    for pattern in tech_patterns:
        matches = re.findall(pattern, task_lower, re.IGNORECASE)
        terms.update(matches)

    # Filter common words
    stop_words = {
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
    }
    terms = {term.lower() for term in terms if term.lower() not in stop_words}

    return sorted(list(terms))[:10]  # Return top 10


def _has_dependencies(task_lower: str) -> bool:
    """Check if task has dependencies."""
    dependency_indicators = [
        "depends on",
        "requires",
        "needs",
        "based on",
        "after",
        "before",
        "following",
        "prerequisite",
        "conditional",
        "if",
        "when",
    ]
    return any(indicator in task_lower for indicator in dependency_indicators)


def _is_critical_task(task_lower: str) -> bool:
    """Check if task is critical/high priority."""
    critical_indicators = [
        "critical",
        "urgent",
        "important",
        "high priority",
        "production",
        "emergency",
        "asap",
        "immediately",
        "deadline",
        "milestone",
    ]
    return any(indicator in task_lower for indicator in critical_indicators)


def _estimate_timing(complexity: ComplexityLevel, agent_count: int) -> int:
    """Estimate task timing in minutes."""

    # Base time by complexity
    base_times = {
        ComplexityLevel.SIMPLE: 5,
        ComplexityLevel.MEDIUM: 10,
        ComplexityLevel.COMPLEX: 15,
        ComplexityLevel.VERY_COMPLEX: 20,
    }

    base_time = base_times[complexity]

    # Adjust for parallelism
    if agent_count > 1:
        # Parallel work is faster, but has coordination overhead
        parallel_efficiency = 0.7  # 70% efficiency due to coordination
        adjusted_time = (
            base_time * (1 + (agent_count - 1) * parallel_efficiency) / agent_count
        )
    else:
        adjusted_time = base_time

    return max(int(adjusted_time), 3)  # Minimum 3 minutes


# ============================================================================
# Decision Support
# ============================================================================


def recommend_pattern(analysis: Dict[str, Any]) -> Tuple[PatternType, str]:
    """Recommend orchestration pattern based on analysis.

    This replaces the complex decision matrix interpreter.
    """

    complexity = analysis["complexity"]
    agent_count = analysis["agent_count"]
    task_type = analysis["task_type"]
    has_dependencies = analysis["has_dependencies"]
    is_critical = analysis["is_critical"]

    # Simple decision tree
    if complexity == ComplexityLevel.SIMPLE or agent_count <= 1:
        return PatternType.DIRECT, "Simple task suitable for direct execution"

    elif task_type == "validation" or is_critical:
        return PatternType.TOURNAMENT, "Critical task requires competitive validation"

    elif complexity == ComplexityLevel.VERY_COMPLEX or has_dependencies:
        return (
            PatternType.HIERARCHICAL,
            "Complex task with dependencies needs phased approach",
        )

    else:
        return PatternType.FANOUT, "Standard parallel exploration with synthesis"


def validate_analysis(analysis: Dict[str, Any]) -> List[str]:
    """Validate analysis results and return any warnings."""

    warnings = []

    # Check for inconsistencies
    if analysis["complexity"] == ComplexityLevel.SIMPLE and analysis["agent_count"] > 2:
        warnings.append("Simple task assigned many agents - consider reducing count")

    if (
        analysis["complexity"] == ComplexityLevel.VERY_COMPLEX
        and analysis["agent_count"] < 3
    ):
        warnings.append("Very complex task may need more agents")

    if analysis["estimated_minutes"] > 30:
        warnings.append("Task estimate exceeds 30 minutes - consider breaking down")

    if len(analysis["recommended_roles"]) > analysis["agent_count"]:
        warnings.append("More roles recommended than agents available")

    return warnings


# ============================================================================
# Metrics and Analytics
# ============================================================================


def calculate_task_metrics(analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate metrics across multiple task analyses."""

    if not analyses:
        return {"error": "No analyses provided"}

    # Complexity distribution
    complexities = [a["complexity"].value for a in analyses]
    complexity_dist = {c: complexities.count(c) for c in set(complexities)}

    # Task type distribution
    task_types = [a["task_type"] for a in analyses]
    task_type_dist = {t: task_types.count(t) for t in set(task_types)}

    # Agent usage
    agent_counts = [a["agent_count"] for a in analyses]

    return {
        "total_analyses": len(analyses),
        "complexity_distribution": complexity_dist,
        "task_type_distribution": task_type_dist,
        "average_agents": sum(agent_counts) / len(agent_counts),
        "average_duration": sum(a["estimated_minutes"] for a in analyses)
        / len(analyses),
        "critical_tasks": sum(1 for a in analyses if a["is_critical"]),
        "dependency_tasks": sum(1 for a in analyses if a["has_dependencies"]),
    }
