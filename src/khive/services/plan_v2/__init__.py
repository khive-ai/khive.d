"""Plan V2 Service - Simplified and elegant orchestration planning.

This module provides the consolidated plan_v2 service with:
- Simple rule-based task analysis
- Unified pattern generation (Direct, Fanout, Tournament, Hierarchical)
- Centralized configuration without over-engineering
- Fast consensus building without complex voting algorithms

Public API:
    - PlanService: Main service class
    - plan_task: Convenience function for quick planning
    - All core data models and enums
"""

from .analysis import (
    analyze_task,
    calculate_task_metrics,
    recommend_pattern,
    validate_analysis,
)
from .config import (  # Configuration constants; Helper functions
    CRITICAL_INDICATORS,
    DEFAULT_AGENT_TEMPLATES,
    DOMAIN_CONFIG,
    EXAMPLE_TASKS,
    PATTERN_RULES,
    PATTERN_WEIGHTS,
    QUALITY_GATE_RULES,
    ROLE_CONFIG,
    SERVICE_CONFIG,
    apply_complexity_bias,
    get_domain_config,
    get_role_config,
    get_suitable_domains,
    get_suitable_roles,
    validate_config,
)
from .core import (  # Main service; Data models; Enums; Consensus logic
    AgentSpec,
    ComplexityLevel,
    ExecutionPlan,
    PatternType,
    Phase,
    PlanRequest,
    PlanResponse,
    PlanService,
    QualityGate,
    build_consensus,
    create_agent_spec,
    plan_task,
)
from .patterns import generate_pattern_plan, validate_pattern_context

# Version info
__version__ = "2.0.0"
__author__ = "Ocean (HaiyangLi)"
__description__ = "Simplified orchestration planning service"

# Export all public symbols
__all__ = [
    # Main service
    "PlanService",
    "plan_task",
    "create_agent_spec",
    # Data models
    "ExecutionPlan",
    "Phase",
    "AgentSpec",
    "PlanRequest",
    "PlanResponse",
    # Enums
    "PatternType",
    "ComplexityLevel",
    "QualityGate",
    # Core functions
    "build_consensus",
    "analyze_task",
    "recommend_pattern",
    "validate_analysis",
    "generate_pattern_plan",
    "validate_pattern_context",
    "calculate_task_metrics",
    # Configuration
    "SERVICE_CONFIG",
    "PATTERN_WEIGHTS",
    "PATTERN_RULES",
    "ROLE_CONFIG",
    "DOMAIN_CONFIG",
    "QUALITY_GATE_RULES",
    "CRITICAL_INDICATORS",
    "DEFAULT_AGENT_TEMPLATES",
    "EXAMPLE_TASKS",
    # Config helpers
    "get_role_config",
    "get_domain_config",
    "get_suitable_roles",
    "get_suitable_domains",
    "apply_complexity_bias",
    "validate_config",
]


# Quick validation on import
def _validate_service():
    """Quick validation that service is properly configured."""
    try:
        config_status = validate_config()
        if not config_status["valid"]:
            print(f"Warning: Configuration issues detected: {config_status['issues']}")
        return config_status["valid"]
    except Exception as e:
        print(f"Warning: Service validation failed: {e}")
        return False


# Run validation on import
_VALIDATION_STATUS = _validate_service()

# Convenience aliases for common usage patterns
plan = plan_task  # Shorter alias
analyze = analyze_task  # Shorter alias
