"""
Adaptive Orchestration Models for khive planning system.

This module implements the Adaptive Orchestration model with:
- CoordinationStrategy enum for different coordination approaches
- Enhanced TaskPhase models with adaptive capabilities  
- Decomposer-Strategist-Critic pipeline components
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Any, Protocol
from dataclasses import dataclass, field
import time

from khive._types import BaseModel
from pydantic import Field

from .parts import (
    ComplexityLevel,
    WorkflowPattern,
    QualityGate,
    AgentRecommendation,
)


class CoordinationStrategy(str, Enum):
    """Coordination strategies for adaptive orchestration."""
    
    AUTONOMOUS = "autonomous"           # Agents work independently with minimal coordination
    HIERARCHICAL = "hierarchical"     # Tree-like coordination with team leads
    COLLABORATIVE = "collaborative"   # Peer-to-peer coordination with shared context
    PIPELINE = "pipeline"             # Sequential handoffs between specialized agents
    SWARM = "swarm"                   # Dynamic coordination with emergent behavior
    HYBRID = "hybrid"                 # Mixed strategies based on task characteristics


class AdaptiveTaskPhase(BaseModel):
    """Enhanced TaskPhase with adaptive orchestration capabilities."""

    name: str = Field(..., description="Phase name")
    description: str = Field(..., description="Phase description")
    agents: list[AgentRecommendation] = Field(
        ..., description="Recommended agents for this phase"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="Phase dependencies"
    )
    quality_gate: QualityGate = Field(..., description="Quality gate for this phase")
    coordination_pattern: WorkflowPattern = Field(
        ..., description="Base coordination pattern"
    )
    
    # Adaptive orchestration fields
    coordination_strategy: CoordinationStrategy = Field(
        default=CoordinationStrategy.COLLABORATIVE, 
        description="Adaptive coordination strategy"
    )
    adaptive_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, 
        description="Threshold for adaptive strategy changes"
    )
    max_coordination_overhead: float = Field(
        default=0.3, ge=0.0, le=1.0, 
        description="Maximum allowed coordination overhead"
    )
    fallback_strategy: CoordinationStrategy = Field(
        default=CoordinationStrategy.AUTONOMOUS, 
        description="Fallback strategy if primary fails"
    )
    
    # Metrics and monitoring
    estimated_duration_minutes: Optional[int] = Field(
        default=None, description="Estimated phase duration"
    )
    coordination_checkpoints: list[str] = Field(
        default_factory=list, description="Coordination checkpoint triggers"
    )


@dataclass
class TaskDecomposition:
    """Output from Decomposer component."""
    
    subtasks: List[str]
    complexity_assessment: ComplexityLevel
    estimated_agent_count: int
    parallelizable_subtasks: List[List[str]]
    sequential_dependencies: Dict[str, List[str]]
    coordination_requirements: List[str]
    risk_factors: List[str]
    decomposition_confidence: float


@dataclass  
class StrategyRecommendation:
    """Output from Strategist component."""
    
    recommended_strategy: CoordinationStrategy
    alternative_strategies: List[CoordinationStrategy]
    strategy_rationale: str
    expected_efficiency: float
    coordination_overhead: float
    risk_assessment: Dict[str, float]
    monitoring_points: List[str]
    adaptation_triggers: List[str]


@dataclass
class PlanCritique:
    """Output from Critic component."""
    
    overall_score: float
    strengths: List[str]
    weaknesses: List[str] 
    optimization_suggestions: List[str]
    risk_warnings: List[str]
    alternative_approaches: List[str]
    confidence_assessment: float
    estimated_success_probability: float


class Decomposer(Protocol):
    """Protocol for task decomposition component."""
    
    def decompose_task(self, task_description: str, context: Optional[str] = None) -> TaskDecomposition:
        """Decompose a task into manageable subtasks."""
        ...
    
    def assess_parallelization(self, subtasks: List[str]) -> List[List[str]]:
        """Assess which subtasks can be parallelized."""
        ...
    
    def identify_dependencies(self, subtasks: List[str]) -> Dict[str, List[str]]:
        """Identify dependencies between subtasks."""
        ...


class Strategist(Protocol):
    """Protocol for coordination strategy selection component."""
    
    def select_strategy(
        self, 
        decomposition: TaskDecomposition,
        context: Optional[Dict[str, Any]] = None
    ) -> StrategyRecommendation:
        """Select optimal coordination strategy."""
        ...
    
    def adapt_strategy(
        self,
        current_strategy: CoordinationStrategy,
        performance_metrics: Dict[str, float],
        context: Dict[str, Any]
    ) -> CoordinationStrategy:
        """Adapt strategy based on runtime metrics."""
        ...


class Critic(Protocol):
    """Protocol for plan evaluation and optimization component."""
    
    def evaluate_plan(
        self,
        decomposition: TaskDecomposition,
        strategy: StrategyRecommendation,
        phases: List[AdaptiveTaskPhase]
    ) -> PlanCritique:
        """Evaluate and critique the orchestration plan."""
        ...
    
    def suggest_optimizations(
        self,
        plan_critique: PlanCritique,
        constraints: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Suggest specific optimizations for the plan."""
        ...


class AdaptiveOrchestrationPlan(BaseModel):
    """Complete adaptive orchestration plan."""
    
    session_id: str = Field(..., description="Unique session identifier")
    task_description: str = Field(..., description="Original task description")
    
    # Pipeline outputs
    decomposition: TaskDecomposition = Field(..., description="Task decomposition results")
    strategy_recommendation: StrategyRecommendation = Field(..., description="Strategy selection results")
    plan_critique: PlanCritique = Field(..., description="Plan evaluation results")
    
    # Execution plan
    phases: List[AdaptiveTaskPhase] = Field(..., description="Execution phases")
    overall_strategy: CoordinationStrategy = Field(..., description="Overall coordination strategy")
    
    # Metadata
    created_at: float = Field(default_factory=time.time, description="Creation timestamp")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall plan confidence")
    estimated_total_duration_minutes: Optional[int] = Field(None, description="Total estimated duration")
    
    class Config:
        extra = "allow"


# Concrete implementations of the pipeline components


class BasicDecomposer:
    """Basic implementation of task decomposer."""
    
    def __init__(self):
        self.complexity_keywords = {
            'simple': ['fix', 'update', 'add', 'remove', 'change'],
            'medium': ['implement', 'create', 'design', 'refactor'],
            'complex': ['migrate', 'integrate', 'architecture', 'system'],
            'very_complex': ['platform', 'complete', 'entire', 'full-scale']
        }
    
    def decompose_task(self, task_description: str, context: Optional[str] = None) -> TaskDecomposition:
        """Basic task decomposition using keyword analysis."""
        
        task_lower = task_description.lower()
        
        # Assess complexity
        complexity = self._assess_complexity(task_lower)
        
        # Generate subtasks based on common patterns
        subtasks = self._generate_subtasks(task_description, complexity)
        
        # Estimate agent count
        agent_count = self._estimate_agent_count(complexity, len(subtasks))
        
        # Identify parallelizable groups
        parallelizable = self._identify_parallelizable_groups(subtasks)
        
        # Identify dependencies
        dependencies = self._identify_basic_dependencies(subtasks)
        
        # Assess coordination requirements
        coordination_reqs = self._assess_coordination_requirements(task_lower, len(subtasks))
        
        # Identify risk factors
        risks = self._identify_risk_factors(task_lower, complexity)
        
        return TaskDecomposition(
            subtasks=subtasks,
            complexity_assessment=complexity,
            estimated_agent_count=agent_count,
            parallelizable_subtasks=parallelizable,
            sequential_dependencies=dependencies,
            coordination_requirements=coordination_reqs,
            risk_factors=risks,
            decomposition_confidence=0.8  # Basic confidence
        )
    
    def _assess_complexity(self, task_lower: str) -> ComplexityLevel:
        """Assess task complexity using keyword matching."""
        scores = {level: 0 for level in ['simple', 'medium', 'complex', 'very_complex']}
        
        for level, keywords in self.complexity_keywords.items():
            for keyword in keywords:
                if keyword in task_lower:
                    scores[level] += 1
        
        max_level = max(scores.items(), key=lambda x: x[1])[0]
        return ComplexityLevel(max_level)
    
    def _generate_subtasks(self, task_description: str, complexity: ComplexityLevel) -> List[str]:
        """Generate subtasks based on task description and complexity."""
        base_subtasks = [
            "Analyze requirements and constraints",
            "Research existing solutions and patterns",
            "Design implementation approach",
            "Implement core functionality",
            "Test and validate implementation", 
            "Document solution and process"
        ]
        
        if complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX]:
            base_subtasks.extend([
                "Create integration tests",
                "Perform security review",
                "Optimize performance",
                "Create deployment plan"
            ])
        
        return base_subtasks
    
    def _estimate_agent_count(self, complexity: ComplexityLevel, subtask_count: int) -> int:
        """Estimate required agent count."""
        base_count = max(2, subtask_count // 2)
        
        multipliers = {
            ComplexityLevel.SIMPLE: 1.0,
            ComplexityLevel.MEDIUM: 1.5,
            ComplexityLevel.COMPLEX: 2.0,
            ComplexityLevel.VERY_COMPLEX: 2.5
        }
        
        return min(20, max(2, int(base_count * multipliers[complexity])))
    
    def _identify_parallelizable_groups(self, subtasks: List[str]) -> List[List[str]]:
        """Identify groups of subtasks that can be done in parallel."""
        # Simple heuristic - research/analysis can be parallel, implementation sequential
        parallel_groups = []
        
        research_tasks = [task for task in subtasks if any(keyword in task.lower() 
                         for keyword in ['analyze', 'research', 'review'])]
        if research_tasks:
            parallel_groups.append(research_tasks)
        
        implementation_tasks = [task for task in subtasks if any(keyword in task.lower()
                               for keyword in ['implement', 'create', 'build'])]
        if implementation_tasks:
            parallel_groups.append(implementation_tasks)
        
        return parallel_groups
    
    def _identify_basic_dependencies(self, subtasks: List[str]) -> Dict[str, List[str]]:
        """Identify basic dependencies between subtasks."""
        dependencies = {}
        
        # Simple rule: implementation depends on design, testing depends on implementation
        for i, task in enumerate(subtasks):
            task_lower = task.lower()
            deps = []
            
            if 'implement' in task_lower and i > 0:
                # Implementation depends on previous design/analysis tasks
                for j in range(i):
                    if any(keyword in subtasks[j].lower() 
                          for keyword in ['analyze', 'design', 'research']):
                        deps.append(subtasks[j])
            
            elif 'test' in task_lower:
                # Testing depends on implementation
                for j in range(i):
                    if 'implement' in subtasks[j].lower():
                        deps.append(subtasks[j])
            
            if deps:
                dependencies[task] = deps
        
        return dependencies
    
    def _assess_coordination_requirements(self, task_lower: str, subtask_count: int) -> List[str]:
        """Assess coordination requirements."""
        requirements = []
        
        if subtask_count > 5:
            requirements.append("Regular synchronization checkpoints")
        
        if any(keyword in task_lower for keyword in ['integrate', 'migrate', 'system']):
            requirements.extend([
                "Cross-team communication",
                "Shared artifact management",
                "Conflict resolution protocol"
            ])
        
        return requirements
    
    def _identify_risk_factors(self, task_lower: str, complexity: ComplexityLevel) -> List[str]:
        """Identify potential risk factors."""
        risks = []
        
        if complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX]:
            risks.append("High coordination overhead")
        
        if any(keyword in task_lower for keyword in ['migrate', 'refactor', 'legacy']):
            risks.extend([
                "Potential breaking changes",
                "Integration compatibility issues"
            ])
        
        if any(keyword in task_lower for keyword in ['system', 'platform', 'architecture']):
            risks.append("Cross-system dependencies")
        
        return risks


class BasicStrategist:
    """Basic implementation of coordination strategist."""
    
    def select_strategy(
        self, 
        decomposition: TaskDecomposition,
        context: Optional[Dict[str, Any]] = None
    ) -> StrategyRecommendation:
        """Select coordination strategy based on decomposition."""
        
        agent_count = decomposition.estimated_agent_count
        complexity = decomposition.complexity_assessment
        parallel_groups = len(decomposition.parallelizable_subtasks)
        
        # Strategy selection logic
        if agent_count <= 3:
            strategy = CoordinationStrategy.AUTONOMOUS
            overhead = 0.1
            efficiency = 0.9
        elif agent_count <= 6 and parallel_groups > 1:
            strategy = CoordinationStrategy.COLLABORATIVE  
            overhead = 0.2
            efficiency = 0.8
        elif complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX]:
            strategy = CoordinationStrategy.HIERARCHICAL
            overhead = 0.3
            efficiency = 0.75
        elif len(decomposition.sequential_dependencies) > 5:
            strategy = CoordinationStrategy.PIPELINE
            overhead = 0.25
            efficiency = 0.8
        else:
            strategy = CoordinationStrategy.HYBRID
            overhead = 0.35
            efficiency = 0.7
        
        # Alternative strategies
        alternatives = [s for s in CoordinationStrategy if s != strategy][:2]
        
        # Risk assessment
        risks = {
            "coordination_failure": overhead,
            "communication_bottleneck": min(0.8, agent_count * 0.1),
            "synchronization_overhead": max(0.1, parallel_groups * 0.1)
        }
        
        return StrategyRecommendation(
            recommended_strategy=strategy,
            alternative_strategies=alternatives,
            strategy_rationale=f"Selected {strategy.value} for {agent_count} agents with {complexity.value} complexity",
            expected_efficiency=efficiency,
            coordination_overhead=overhead,
            risk_assessment=risks,
            monitoring_points=["Agent synchronization", "Task completion rate"],
            adaptation_triggers=["High coordination overhead", "Low efficiency metrics"]
        )


class BasicCritic:
    """Basic implementation of plan critic."""
    
    def evaluate_plan(
        self,
        decomposition: TaskDecomposition,
        strategy: StrategyRecommendation,
        phases: List[AdaptiveTaskPhase]
    ) -> PlanCritique:
        """Evaluate orchestration plan."""
        
        # Calculate overall score
        efficiency_score = strategy.expected_efficiency
        coordination_score = 1.0 - strategy.coordination_overhead
        decomposition_score = decomposition.decomposition_confidence
        
        overall_score = (efficiency_score + coordination_score + decomposition_score) / 3
        
        # Identify strengths
        strengths = []
        if strategy.expected_efficiency > 0.8:
            strengths.append("High expected efficiency")
        if strategy.coordination_overhead < 0.3:
            strengths.append("Low coordination overhead")
        if decomposition.decomposition_confidence > 0.7:
            strengths.append("Well-structured task decomposition")
        
        # Identify weaknesses  
        weaknesses = []
        if strategy.coordination_overhead > 0.4:
            weaknesses.append("High coordination overhead may impact efficiency")
        if decomposition.estimated_agent_count > 15:
            weaknesses.append("Large agent count may be difficult to coordinate")
        if len(phases) > 6:
            weaknesses.append("Many phases may extend timeline")
        
        # Optimization suggestions
        optimizations = []
        if strategy.coordination_overhead > 0.3:
            optimizations.append("Consider simplifying coordination strategy")
        if decomposition.estimated_agent_count > 12:
            optimizations.append("Consider breaking into smaller sub-projects")
        
        # Risk warnings
        risks = []
        for risk, probability in strategy.risk_assessment.items():
            if probability > 0.6:
                risks.append(f"High {risk.replace('_', ' ')} risk")
        
        return PlanCritique(
            overall_score=overall_score,
            strengths=strengths,
            weaknesses=weaknesses,
            optimization_suggestions=optimizations,
            risk_warnings=risks,
            alternative_approaches=[
                "Sequential phases with smaller teams",
                "Hybrid approach with mixed strategies"
            ],
            confidence_assessment=overall_score,
            estimated_success_probability=max(0.5, overall_score)
        )
