"""
Multi-Round Consensus Planning System.

Implements ChatGPT's design for robust plan generation through iterative
generation → cross-evaluation → consensus aggregation → repair.

Key components:
- generators.py: Decomposer, Strategist, Refiner engines
- judges.py: Cross-judgment and pairwise comparison
- consensus.py: BTL/RankCentrality/Schulze algorithms
- service.py: Main orchestrator
- models.py: Clean data models (no legacy fields)
"""

from .models import (
    ComplexityLevel,
    CoordinationStrategy,
    PlannerRequest,
    PlannerResponse,
)
from .service import ConsensusPlannerV3, create_planner

__all__ = [
    "ConsensusPlannerV3",
    "create_planner",
    "PlannerRequest",
    "PlannerResponse",
    "ComplexityLevel",
    "CoordinationStrategy",
]
