"""Enhanced planning scenario fixtures for comprehensive testing.

This module provides realistic planning scenarios that cover:
- Real-world task complexity variations
- Multi-domain integration scenarios
- Edge cases and boundary conditions
- Performance testing scenarios
- Integration test workflows
- Production-like validation scenarios

Used for integration and end-to-end testing of the planning service.
"""

from uuid import uuid4

import pytest

from khive.services.plan.parts import (
    ComplexityLevel,
    PlannerRequest,
    QualityGate,
    WorkflowPattern,
)
from khive.services.plan.planner_service import ComplexityTier


@pytest.fixture
def real_world_planning_scenarios():
    """Real-world planning scenarios for comprehensive testing."""
    return [
        {
            "name": "oauth2_authentication_system",
            "description": "Implement OAuth2 authentication with JWT tokens, refresh tokens, and multi-provider support",
            "expected_complexity": ComplexityLevel.MEDIUM,
            "expected_agents": (4, 6),
            "expected_roles": ["researcher", "architect", "implementer", "reviewer"],
            "expected_domains": [
                "software-architecture",
                "backend-development",
                "security",
            ],
            "expected_workflow": WorkflowPattern.SEQUENTIAL,
            "context": {
                "project_type": "web_application",
                "security_requirements": "high",
                "integration_complexity": "medium",
                "performance_requirements": "standard",
            },
            "validation_criteria": {
                "includes_security_review": True,
                "has_architecture_phase": True,
                "includes_testing": True,
                "estimated_hours": (32, 80),
            },
        },
        {
            "name": "microservices_platform_migration",
            "description": "Migrate monolithic e-commerce platform to microservices architecture with event sourcing, CQRS, and distributed transactions",
            "expected_complexity": ComplexityLevel.VERY_COMPLEX,
            "expected_agents": (8, 12),
            "expected_roles": [
                "researcher",
                "architect",
                "implementer",
                "tester",
                "reviewer",
                "auditor",
            ],
            "expected_domains": [
                "microservices-architecture",
                "distributed-systems",
                "event-sourcing",
                "database-design",
            ],
            "expected_workflow": WorkflowPattern.HYBRID,
            "context": {
                "project_type": "platform_migration",
                "scale": "enterprise",
                "risk_level": "high",
                "timeline": "months",
                "team_size": "large",
            },
            "validation_criteria": {
                "requires_research_phase": True,
                "includes_architecture_review": True,
                "has_migration_strategy": True,
                "includes_rollback_plan": True,
                "estimated_hours": (320, 800),
            },
        },
        {
            "name": "simple_bug_fix",
            "description": "Fix login form validation error where empty email field shows incorrect error message",
            "expected_complexity": ComplexityLevel.SIMPLE,
            "expected_agents": (1, 2),
            "expected_roles": ["implementer"],
            "expected_domains": ["frontend-development"],
            "expected_workflow": WorkflowPattern.SEQUENTIAL,
            "context": {
                "project_type": "bug_fix",
                "urgency": "medium",
                "impact": "low",
                "complexity": "minimal",
            },
            "validation_criteria": {
                "single_phase": True,
                "no_research_needed": True,
                "quick_turnaround": True,
                "estimated_hours": (2, 8),
            },
        },
        {
            "name": "ai_recommendation_engine",
            "description": "Design and implement machine learning recommendation engine with real-time inference, A/B testing, and personalization algorithms",
            "expected_complexity": ComplexityLevel.COMPLEX,
            "expected_agents": (6, 10),
            "expected_roles": [
                "researcher",
                "analyst",
                "architect",
                "implementer",
                "tester",
            ],
            "expected_domains": [
                "machine-learning",
                "distributed-systems",
                "data-engineering",
                "backend-development",
            ],
            "expected_workflow": WorkflowPattern.PARALLEL,
            "context": {
                "project_type": "ml_system",
                "data_requirements": "high",
                "performance_critical": True,
                "experimental": True,
            },
            "validation_criteria": {
                "includes_research_phase": True,
                "requires_data_analysis": True,
                "includes_ab_testing": True,
                "estimated_hours": (160, 320),
            },
        },
        {
            "name": "blockchain_consensus_protocol",
            "description": "Research and implement novel Byzantine fault-tolerant consensus protocol with formal verification and performance optimization for 1000+ nodes",
            "expected_complexity": ComplexityLevel.VERY_COMPLEX,
            "expected_agents": (10, 12),
            "expected_roles": [
                "theorist",
                "researcher",
                "analyst",
                "architect",
                "implementer",
                "auditor",
                "critic",
            ],
            "expected_domains": [
                "distributed-consensus",
                "cryptography",
                "formal-verification",
                "performance-optimization",
            ],
            "expected_workflow": WorkflowPattern.HYBRID,
            "context": {
                "project_type": "research_implementation",
                "novelty": "high",
                "verification_required": True,
                "performance_critical": True,
                "academic_rigor": True,
            },
            "validation_criteria": {
                "requires_formal_verification": True,
                "includes_theoretical_analysis": True,
                "requires_peer_review": True,
                "includes_performance_benchmarks": True,
                "estimated_hours": (800, 1600),
            },
        },
    ]


@pytest.fixture
def edge_case_scenarios():
    """Edge case scenarios for boundary testing."""
    return [
        {
            "name": "empty_description",
            "description": "",
            "expected_behavior": "validation_error",
            "context": {"test_type": "input_validation"},
        },
        {
            "name": "minimal_description",
            "description": "fix",
            "expected_behavior": "validation_error",
            "context": {"test_type": "input_validation"},
        },
        {
            "name": "maximum_length_description",
            "description": "implement " * 2000 + "system",  # Very long description
            "expected_complexity": ComplexityLevel.VERY_COMPLEX,
            "expected_behavior": "handles_gracefully",
            "context": {"test_type": "boundary_testing"},
        },
        {
            "name": "unicode_and_special_chars",
            "description": "实现分布式系统 with émojis 🚀 and spëcial chàracters & symbols @#$%",
            "expected_complexity": ComplexityLevel.MEDIUM,
            "expected_behavior": "handles_gracefully",
            "context": {"test_type": "encoding_handling"},
        },
        {
            "name": "conflicting_complexity_indicators",
            "description": "simple easy basic complex sophisticated advanced distributed research novel",
            "expected_complexity": ComplexityLevel.COMPLEX,  # Should resolve to higher complexity
            "expected_behavior": "resolves_to_higher_complexity",
            "context": {"test_type": "ambiguity_resolution"},
        },
        {
            "name": "all_caps_shouting",
            "description": "IMPLEMENT DISTRIBUTED MICROSERVICES ARCHITECTURE WITH KUBERNETES AND SERVICE MESH",
            "expected_complexity": ComplexityLevel.COMPLEX,
            "expected_behavior": "handles_case_insensitive",
            "context": {"test_type": "case_handling"},
        },
    ]


@pytest.fixture
def performance_test_scenarios():
    """Performance testing scenarios with various loads."""
    return [
        {
            "name": "single_request_latency",
            "requests": [
                PlannerRequest(
                    task_description="Implement user authentication system",
                    session_id=str(uuid4()),
                    priority_level="medium",
                )
            ],
            "expected_max_time": 2.0,  # 2 seconds
            "test_type": "latency",
        },
        {
            "name": "batch_processing",
            "requests": [
                PlannerRequest(
                    task_description=f"Implement feature {i}",
                    session_id=str(uuid4()),
                    priority_level="medium",
                )
                for i in range(10)
            ],
            "expected_max_time": 15.0,  # 15 seconds for 10 requests
            "test_type": "throughput",
        },
        {
            "name": "concurrent_requests",
            "requests": [
                PlannerRequest(
                    task_description="Design distributed system",
                    session_id=str(uuid4()),
                    priority_level="high",
                )
                for _ in range(5)
            ],
            "expected_max_time": 10.0,  # Should be faster than sequential
            "test_type": "concurrency",
        },
        {
            "name": "memory_stress_test",
            "requests": [
                PlannerRequest(
                    task_description="Very complex " * 100 + "system implementation",
                    session_id=str(uuid4()),
                    priority_level="low",
                )
                for _ in range(20)
            ],
            "expected_memory_limit": 100 * 1024 * 1024,  # 100MB
            "test_type": "memory",
        },
    ]


@pytest.fixture
def integration_workflow_scenarios():
    """End-to-end integration workflow scenarios."""
    return [
        {
            "name": "complete_feature_development",
            "workflow_steps": [
                {
                    "step": "planning",
                    "input": PlannerRequest(
                        task_description="Build user profile management system with privacy controls",
                        session_id=str(uuid4()),
                        context={"project": "social_app", "privacy_critical": True},
                    ),
                    "expected_output": "orchestration_plan",
                },
                {
                    "step": "agent_allocation",
                    "expected_agents": 5,
                    "expected_phases": 3,
                },
                {
                    "step": "execution_monitoring",
                    "expected_artifacts": [
                        "requirements.md",
                        "architecture.md",
                        "implementation/",
                        "tests/",
                    ],
                },
                {
                    "step": "quality_validation",
                    "expected_quality_gate": QualityGate.THOROUGH,
                },
            ],
            "success_criteria": {
                "all_phases_complete": True,
                "artifacts_generated": True,
                "quality_gates_passed": True,
            },
        },
        {
            "name": "research_to_implementation",
            "workflow_steps": [
                {
                    "step": "research_planning",
                    "input": PlannerRequest(
                        task_description="Research and prototype novel graph database indexing algorithms",
                        session_id=str(uuid4()),
                        context={"research_phase": True, "prototype_required": True},
                    ),
                },
                {
                    "step": "knowledge_synthesis",
                    "expected_deliverables": [
                        "research_summary.md",
                        "algorithm_comparison.md",
                    ],
                },
                {
                    "step": "prototype_development",
                    "expected_deliverables": [
                        "prototype/",
                        "benchmarks/",
                        "evaluation_report.md",
                    ],
                },
            ],
            "success_criteria": {
                "research_complete": True,
                "prototype_functional": True,
                "benchmarks_available": True,
            },
        },
    ]


@pytest.fixture
def validation_test_scenarios():
    """Scenarios for testing validation and error handling."""
    return [
        {
            "name": "invalid_session_id",
            "request_data": {
                "task_description": "Valid task description",
                "session_id": "invalid-uuid-format",
            },
            "expected_error": "ValidationError",
            "error_field": "session_id",
        },
        {
            "name": "missing_required_fields",
            "request_data": {
                "session_id": str(uuid4())
                # Missing task_description
            },
            "expected_error": "ValidationError",
            "error_field": "task_description",
        },
        {
            "name": "invalid_priority_level",
            "request_data": {
                "task_description": "Valid task",
                "session_id": str(uuid4()),
                "priority_level": "invalid_priority",
            },
            "expected_error": "ValidationError",
            "error_field": "priority_level",
        },
        {
            "name": "task_too_long",
            "request_data": {
                "task_description": "x" * 10001,  # Over limit
                "session_id": str(uuid4()),
            },
            "expected_error": "ValidationError",
            "error_field": "task_description",
        },
        {
            "name": "negative_agent_count",
            "evaluation_data": {
                "complexity_tier": ComplexityTier.MEDIUM,
                "agent_count": -5,  # Invalid
                "recommended_roles": ["implementer"],
                "confidence_score": 0.8,
            },
            "expected_error": "ValidationError",
            "error_field": "agent_count",
        },
        {
            "name": "confidence_score_out_of_range",
            "evaluation_data": {
                "complexity_tier": ComplexityTier.MEDIUM,
                "agent_count": 4,
                "recommended_roles": ["implementer"],
                "confidence_score": 1.5,  # Over 1.0
            },
            "expected_error": "ValidationError",
            "error_field": "confidence_score",
        },
    ]


@pytest.fixture
def algorithm_accuracy_scenarios():
    """Scenarios specifically designed to test algorithm accuracy."""
    return [
        {
            "category": "complexity_assessment",
            "test_cases": [
                {
                    "input": "fix typo in button text",
                    "expected_complexity": ComplexityTier.SIMPLE,
                    "confidence_threshold": 0.7,
                },
                {
                    "input": "implement OAuth2 authentication with JWT tokens",
                    "expected_complexity": ComplexityTier.MEDIUM,
                    "confidence_threshold": 0.7,
                },
                {
                    "input": "design distributed event-sourced microservices architecture",
                    "expected_complexity": ComplexityTier.COMPLEX,
                    "confidence_threshold": 0.7,
                },
                {
                    "input": "research novel Byzantine fault-tolerant consensus algorithms with formal verification",
                    "expected_complexity": ComplexityTier.VERY_COMPLEX,
                    "confidence_threshold": 0.7,
                },
            ],
        },
        {
            "category": "agent_count_optimization",
            "test_cases": [
                {
                    "complexity": ComplexityTier.SIMPLE,
                    "expected_range": (1, 3),
                    "efficiency_target": "minimal_overhead",
                },
                {
                    "complexity": ComplexityTier.MEDIUM,
                    "expected_range": (3, 6),
                    "efficiency_target": "balanced_coordination",
                },
                {
                    "complexity": ComplexityTier.COMPLEX,
                    "expected_range": (5, 9),
                    "efficiency_target": "optimal_specialization",
                },
                {
                    "complexity": ComplexityTier.VERY_COMPLEX,
                    "expected_range": (7, 12),  # Efficiency cliff at 12
                    "efficiency_target": "maximum_expertise",
                },
            ],
        },
        {
            "category": "role_selection_accuracy",
            "test_cases": [
                {
                    "task": "research machine learning algorithms",
                    "expected_roles": ["researcher", "analyst"],
                    "phase": "discovery",
                },
                {
                    "task": "design system architecture",
                    "expected_roles": ["architect", "strategist"],
                    "phase": "design",
                },
                {
                    "task": "implement API endpoints",
                    "expected_roles": ["implementer"],
                    "phase": "implementation",
                },
                {
                    "task": "validate system security",
                    "expected_roles": ["tester", "auditor", "critic"],
                    "phase": "validation",
                },
            ],
        },
    ]


@pytest.fixture
def production_simulation_scenarios():
    """Scenarios that simulate production workloads and conditions."""
    return [
        {
            "name": "typical_day_load",
            "description": "Simulate typical daily planning requests",
            "request_pattern": [
                {"time": "09:00", "requests": 5, "complexity": "mixed"},
                {"time": "11:00", "requests": 8, "complexity": "medium"},
                {"time": "14:00", "requests": 12, "complexity": "high"},
                {"time": "16:00", "requests": 3, "complexity": "simple"},
            ],
            "success_criteria": {
                "response_time_p95": 3.0,  # 95th percentile under 3s
                "error_rate": 0.01,  # Less than 1% errors
                "memory_stable": True,
            },
        },
        {
            "name": "peak_load_simulation",
            "description": "Simulate peak load conditions",
            "concurrent_requests": 20,
            "duration_minutes": 5,
            "request_types": ["simple", "medium", "complex"],
            "success_criteria": {
                "no_timeouts": True,
                "response_time_max": 10.0,
                "memory_growth_limit": "20%",
            },
        },
        {
            "name": "disaster_recovery",
            "description": "Test resilience under failure conditions",
            "failure_scenarios": [
                {"type": "api_timeout", "duration": 30},
                {"type": "memory_pressure", "level": "high"},
                {"type": "concurrent_overload", "multiplier": 5},
            ],
            "success_criteria": {
                "graceful_degradation": True,
                "recovery_time": 60,  # seconds
                "data_consistency": True,
            },
        },
    ]


@pytest.fixture
def cross_domain_scenarios():
    """Scenarios that test cross-domain integration and matching."""
    return [
        {
            "task": "Build full-stack e-commerce platform with ML recommendations",
            "expected_domains": [
                "frontend-development",
                "backend-development",
                "database-design",
                "machine-learning",
                "distributed-systems",
            ],
            "domain_interactions": [
                ("frontend", "backend", "api_integration"),
                ("backend", "database", "data_modeling"),
                ("ml", "backend", "inference_integration"),
            ],
        },
        {
            "task": "Implement blockchain-based supply chain tracking with IoT integration",
            "expected_domains": [
                "blockchain-development",
                "distributed-systems",
                "iot-systems",
                "cryptography",
                "database-design",
            ],
            "domain_interactions": [
                ("blockchain", "cryptography", "security_protocols"),
                ("iot", "blockchain", "data_verification"),
                ("distributed", "blockchain", "consensus_mechanisms"),
            ],
        },
    ]
