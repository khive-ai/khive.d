"""
Khive Planning Service using lionagi orchestration.

This module implements the Adaptive Orchestration model with:
- Decomposer-Strategist-Critic pipeline using lionagi Branch
- Multi-model orchestration evaluation
- Coordination strategy optimization
- Consensus algorithms for robust planning
"""

from .models import (
    # Enums
    CoordinationStrategy,
    ComplexityLevel,
    QualityGate,
    
    # Request/Response
    PlannerRequest,
    PlannerResponse,
    TaskPhase,
    AgentRecommendation,
    
    # Pipeline models
    TaskDecomposition,
    DecomposedPhase,
    StrategyRecommendation,
    PhaseAllocation,
    AllocatedAgent,
    PlanCritique,
    OrchestrationResult,
)

from .orchestrator import (
    # Consensus
    ConsensusConfig,
    ConsensusAlgorithm,
    DecompositionConsensus,
    StrategyConsensus,
    CritiqueConsensus,
    
    # Orchestration
    OrchestrationEvaluator,
    AdaptivePlanner,
)

from .service import PlannerService
from .cost_tracker import CostTracker

__all__ = [
    # Enums
    "CoordinationStrategy",
    "ComplexityLevel",
    "QualityGate",
    
    # Request/Response
    "PlannerRequest",
    "PlannerResponse",
    "TaskPhase",
    "AgentRecommendation",
    
    # Pipeline models
    "TaskDecomposition",
    "DecomposedPhase",
    "StrategyRecommendation",
    "PhaseAllocation", 
    "AllocatedAgent",
    "PlanCritique",
    "OrchestrationResult",
    
    # Consensus
    "ConsensusConfig",
    "ConsensusAlgorithm",
    "DecompositionConsensus",
    "StrategyConsensus",
    "CritiqueConsensus",
    
    # Orchestration
    "OrchestrationEvaluator",
    "AdaptivePlanner",
    
    # Service
    "PlannerService",
    "CostTracker",
]