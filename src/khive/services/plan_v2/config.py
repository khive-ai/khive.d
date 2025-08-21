"""Configuration and Rules - Centralized configuration without over-engineering.

This module contains all configuration, rules, and constants for the plan service.
No external YAML files, no complex loading - just simple, maintainable config.
"""

from typing import Any, Dict, List

from .core import ComplexityLevel, PatternType, QualityGate

# ============================================================================
# Service Configuration
# ============================================================================

# Service limits and constraints
SERVICE_CONFIG = {
    "max_agents": 8,
    "min_agents": 1,
    "max_task_length": 1000,
    "default_timeout_minutes": 30,
    "max_phases": 5,
    "default_confidence": 0.8,
    "cache_results": True,
    "enable_analytics": True,
}

# Pattern selection weights (replaces complex decision matrix)
PATTERN_WEIGHTS = {
    PatternType.DIRECT: {
        "simplicity": 1.0,
        "speed": 1.0,
        "resource_efficiency": 1.0,
        "coordination_overhead": 0.1,
    },
    PatternType.FANOUT: {
        "exploration": 1.0,
        "parallel_efficiency": 0.8,
        "synthesis_quality": 0.9,
        "coordination_overhead": 0.6,
    },
    PatternType.TOURNAMENT: {
        "quality_assurance": 1.0,
        "validation_rigor": 1.0,
        "decision_confidence": 0.9,
        "coordination_overhead": 0.8,
    },
    PatternType.HIERARCHICAL: {
        "dependency_handling": 1.0,
        "structured_approach": 1.0,
        "scalability": 0.8,
        "coordination_overhead": 0.9,
    },
}


# ============================================================================
# Role and Domain Configuration
# ============================================================================

# Available roles with their characteristics
ROLE_CONFIG = {
    "researcher": {
        "description": "Investigates and gathers information",
        "suitable_for": ["analysis", "discovery", "exploration"],
        "default_domains": ["distributed-systems", "software-architecture"],
        "typical_priority": 1.0,
    },
    "analyst": {
        "description": "Analyzes information and identifies patterns",
        "suitable_for": ["analysis", "evaluation", "synthesis"],
        "default_domains": ["software-architecture", "backend-development"],
        "typical_priority": 0.9,
    },
    "architect": {
        "description": "Designs system architecture and structure",
        "suitable_for": ["design", "planning", "integration"],
        "default_domains": ["software-architecture", "distributed-systems"],
        "typical_priority": 1.0,
    },
    "implementer": {
        "description": "Implements solutions and builds systems",
        "suitable_for": ["implementation", "development", "construction"],
        "default_domains": ["backend-development", "frontend-development"],
        "typical_priority": 0.8,
    },
    "tester": {
        "description": "Tests and validates implementations",
        "suitable_for": ["validation", "quality-assurance", "verification"],
        "default_domains": ["testing", "code-quality"],
        "typical_priority": 0.7,
    },
    "reviewer": {
        "description": "Reviews work and provides feedback",
        "suitable_for": ["validation", "quality-assurance", "evaluation"],
        "default_domains": ["software-architecture", "code-quality"],
        "typical_priority": 0.8,
    },
    "critic": {
        "description": "Provides critical analysis and identifies issues",
        "suitable_for": ["validation", "risk-assessment", "quality-assurance"],
        "default_domains": ["software-architecture", "code-quality"],
        "typical_priority": 0.9,
    },
}

# Available domains with their focus areas
DOMAIN_CONFIG = {
    "software-architecture": {
        "description": "System design and architectural patterns",
        "suitable_roles": ["architect", "analyst", "researcher"],
        "complexity_bias": 0.1,  # Slightly increases complexity assessment
    },
    "backend-development": {
        "description": "Server-side development and APIs",
        "suitable_roles": ["implementer", "analyst", "tester"],
        "complexity_bias": 0.0,
    },
    "frontend-development": {
        "description": "User interface and client-side development",
        "suitable_roles": ["implementer", "analyst", "tester"],
        "complexity_bias": -0.1,  # Slightly decreases complexity
    },
    "distributed-systems": {
        "description": "Distributed computing and system coordination",
        "suitable_roles": ["architect", "researcher", "analyst"],
        "complexity_bias": 0.2,  # Increases complexity significantly
    },
    "api-design": {
        "description": "API architecture and interface design",
        "suitable_roles": ["architect", "analyst", "implementer"],
        "complexity_bias": 0.0,
    },
    "database-design": {
        "description": "Data modeling and database architecture",
        "suitable_roles": ["architect", "implementer", "analyst"],
        "complexity_bias": 0.1,
    },
    "testing": {
        "description": "Quality assurance and validation",
        "suitable_roles": ["tester", "reviewer", "critic"],
        "complexity_bias": 0.0,
    },
    "security": {
        "description": "Security analysis and protection",
        "suitable_roles": ["analyst", "critic", "reviewer"],
        "complexity_bias": 0.15,
    },
}


# ============================================================================
# Pattern Rules and Constraints
# ============================================================================

# Pattern selection rules (replaces complex decision matrix)
PATTERN_RULES = [
    {
        "pattern": PatternType.DIRECT,
        "conditions": {
            "max_agents": 2,
            "max_complexity": ComplexityLevel.MEDIUM,
            "not_critical": True,
        },
        "priority": 1.0,
    },
    {
        "pattern": PatternType.FANOUT,
        "conditions": {
            "min_agents": 2,
            "min_complexity": ComplexityLevel.MEDIUM,
            "task_types": ["analysis", "research", "exploration"],
        },
        "priority": 0.8,
    },
    {
        "pattern": PatternType.TOURNAMENT,
        "conditions": {
            "min_agents": 3,
            "min_complexity": ComplexityLevel.COMPLEX,
            "task_types": ["validation", "comparison"],
            "is_critical": True,
        },
        "priority": 0.9,
    },
    {
        "pattern": PatternType.HIERARCHICAL,
        "conditions": {
            "min_agents": 3,
            "min_complexity": ComplexityLevel.COMPLEX,
            "has_dependencies": True,
            "task_types": ["implementation", "design"],
        },
        "priority": 0.85,
    },
]

# Quality gate escalation rules
QUALITY_GATE_RULES = {
    ComplexityLevel.SIMPLE: QualityGate.BASIC,
    ComplexityLevel.MEDIUM: QualityGate.BASIC,
    ComplexityLevel.COMPLEX: QualityGate.THOROUGH,
    ComplexityLevel.VERY_COMPLEX: QualityGate.CRITICAL,
}

# Critical task indicators (auto-escalation to higher quality gates)
CRITICAL_INDICATORS = [
    "production",
    "critical",
    "urgent",
    "security",
    "payment",
    "data loss",
    "downtime",
    "outage",
    "failure",
    "breach",
]


# ============================================================================
# Default Templates and Examples
# ============================================================================

# Default agent templates for common scenarios
DEFAULT_AGENT_TEMPLATES = {
    "analysis_task": {
        "roles": ["researcher", "analyst", "critic"],
        "domains": ["software-architecture", "distributed-systems"],
        "agent_count": 3,
    },
    "implementation_task": {
        "roles": ["architect", "implementer", "tester"],
        "domains": ["backend-development", "software-architecture"],
        "agent_count": 3,
    },
    "validation_task": {
        "roles": ["reviewer", "critic", "tester"],
        "domains": ["testing", "quality-assurance"],
        "agent_count": 3,
    },
    "design_task": {
        "roles": ["architect", "analyst", "reviewer"],
        "domains": ["software-architecture", "api-design"],
        "agent_count": 3,
    },
}

# Example task patterns for reference
EXAMPLE_TASKS = {
    "simple": [
        "Review the API documentation",
        "Check code formatting",
        "Update configuration file",
    ],
    "medium": [
        "Analyze system performance bottlenecks",
        "Design new API endpoints",
        "Implement user authentication",
    ],
    "complex": [
        "Refactor microservices architecture",
        "Implement distributed caching strategy",
        "Design fault-tolerant message queue",
    ],
    "very_complex": [
        "Migrate monolith to microservices",
        "Implement multi-region data replication",
        "Design comprehensive security framework",
    ],
}


# ============================================================================
# Helper Functions
# ============================================================================


def get_role_config(role: str) -> Dict[str, Any]:
    """Get configuration for a specific role."""
    return ROLE_CONFIG.get(
        role,
        {
            "description": f"Generic {role} role",
            "suitable_for": ["general"],
            "default_domains": ["software-architecture"],
            "typical_priority": 0.8,
        },
    )


def get_domain_config(domain: str) -> Dict[str, Any]:
    """Get configuration for a specific domain."""
    return DOMAIN_CONFIG.get(
        domain,
        {
            "description": f"Generic {domain} domain",
            "suitable_roles": ["analyst"],
            "complexity_bias": 0.0,
        },
    )


def get_suitable_roles(task_type: str) -> List[str]:
    """Get roles suitable for a task type."""
    suitable = []
    for role, config in ROLE_CONFIG.items():
        if task_type in config["suitable_for"] or "general" in config["suitable_for"]:
            suitable.append(role)

    return suitable if suitable else ["analyst", "researcher"]


def get_suitable_domains(roles: List[str]) -> List[str]:
    """Get domains suitable for given roles."""
    domain_scores = {}

    for role in roles:
        role_config = get_role_config(role)
        for domain in role_config.get("default_domains", ["software-architecture"]):
            domain_scores[domain] = domain_scores.get(domain, 0) + 1

    # Return domains sorted by suitability score
    return sorted(domain_scores.keys(), key=lambda d: domain_scores[d], reverse=True)


def apply_complexity_bias(
    base_complexity: ComplexityLevel, domains: List[str]
) -> ComplexityLevel:
    """Apply domain complexity bias to base assessment."""

    complexity_values = {
        ComplexityLevel.SIMPLE: 1,
        ComplexityLevel.MEDIUM: 2,
        ComplexityLevel.COMPLEX: 3,
        ComplexityLevel.VERY_COMPLEX: 4,
    }

    base_value = complexity_values[base_complexity]
    total_bias = sum(
        get_domain_config(domain).get("complexity_bias", 0.0) for domain in domains
    )

    adjusted_value = base_value + total_bias
    adjusted_value = max(1, min(4, round(adjusted_value)))  # Clamp between 1-4

    value_to_complexity = {
        1: ComplexityLevel.SIMPLE,
        2: ComplexityLevel.MEDIUM,
        3: ComplexityLevel.COMPLEX,
        4: ComplexityLevel.VERY_COMPLEX,
    }

    return value_to_complexity[adjusted_value]


def validate_config() -> Dict[str, Any]:
    """Validate configuration consistency."""

    issues = []

    # Check role-domain compatibility
    for role, config in ROLE_CONFIG.items():
        for domain in config.get("default_domains", []):
            if domain not in DOMAIN_CONFIG:
                issues.append(f"Role {role} references unknown domain {domain}")

    # Check pattern rule consistency
    for rule in PATTERN_RULES:
        pattern = rule.get("pattern")
        if pattern not in PatternType:
            issues.append(f"Unknown pattern type in rules: {pattern}")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "total_roles": len(ROLE_CONFIG),
        "total_domains": len(DOMAIN_CONFIG),
        "total_patterns": len(PatternType),
    }
