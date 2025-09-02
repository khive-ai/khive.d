"""
Integration layer for Adaptive Orchestration with existing Khive Planning System.

This module provides seamless integration between the existing planner service
and the new adaptive orchestration capabilities.
"""

from __future__ import annotations

from typing import Optional

from .adaptive_planner import AdaptivePlannerService, integrate_with_manual_coordination
from .coordination_models import CoordinationStrategy
from .parts import PlannerRequest, PlannerResponse
from .planner_service import PlannerService


class IntegratedPlannerService(PlannerService):
    """
    Enhanced planner service that integrates adaptive orchestration capabilities
    with the existing planning system.
    """
    
    def __init__(self, command_format: str = "claude", enable_adaptive: bool = True):
        """
        Initialize integrated planner service.
        
        Args:
            command_format: Either "claude" for BatchTool format or "json" for OrchestrationPlan format
            enable_adaptive: Enable adaptive orchestration features
        """
        super().__init__(command_format)
        self.enable_adaptive = enable_adaptive
        self._adaptive_planner = None
        
    async def _get_adaptive_planner(self) -> AdaptivePlannerService:
        """Get or create adaptive planner service."""
        if self._adaptive_planner is None:
            self._adaptive_planner = AdaptivePlannerService(self)
        return self._adaptive_planner
        
    async def handle_request(
        self, 
        request: PlannerRequest,
        coordination_strategy: Optional[CoordinationStrategy] = None
    ) -> PlannerResponse:
        """
        Handle planning request with optional adaptive orchestration.
        
        Args:
            request: The planning request
            coordination_strategy: Optional coordination strategy for adaptive orchestration
            
        Returns:
            Planning response with adaptive orchestration if enabled
        """
        
        # If adaptive orchestration is disabled or no strategy specified, use base planner
        if not self.enable_adaptive or coordination_strategy is None:
            return await super().handle_request(request)
            
        # Use adaptive orchestration
        adaptive_planner = await self._get_adaptive_planner()
        response = await adaptive_planner.create_adaptive_plan(request, coordination_strategy)
        
        # Add integration instructions for manual coordination
        if response.success and response.session_id:
            integration_instructions = integrate_with_manual_coordination(
                response.phases, 
                response.session_id
            )
            response.summary += f"\n\n{integration_instructions}"
            
        return response
        
    async def plan_with_decomposer_strategist_critic(
        self, 
        request: PlannerRequest
    ) -> PlannerResponse:
        """
        Create plan using Decomposer-Strategist-Critic pipeline.
        
        Args:
            request: The planning request
            
        Returns:
            Planning response with DSC pipeline configuration
        """
        return await self.handle_request(
            request, 
            CoordinationStrategy.DECOMPOSER_STRATEGIST_CRITIC
        )
        
    async def plan_with_fan_out_fan_in(
        self,
        request: PlannerRequest
    ) -> PlannerResponse:
        """
        Create plan using Fan-Out/Fan-In pattern.
        
        Args:
            request: The planning request
            
        Returns:
            Planning response with Fan-Out/Fan-In configuration
        """
        return await self.handle_request(
            request,
            CoordinationStrategy.FAN_OUT_FAN_IN
        )
        
    async def plan_with_feedback_pipeline(
        self,
        request: PlannerRequest
    ) -> PlannerResponse:
        """
        Create plan using Pipeline with Feedback pattern.
        
        Args:
            request: The planning request
            
        Returns:
            Planning response with feedback pipeline configuration
        """
        return await self.handle_request(
            request,
            CoordinationStrategy.PIPELINE_WITH_FEEDBACK
        )


def detect_coordination_strategy(task_description: str) -> CoordinationStrategy:
    """
    Automatically detect appropriate coordination strategy based on task description.
    
    Args:
        task_description: The task description to analyze
        
    Returns:
        Recommended coordination strategy
    """
    text = task_description.lower()
    
    # Protocol design specific patterns
    protocol_keywords = ["protocol", "communication", "network", "message", "api"]
    if any(keyword in text for keyword in protocol_keywords):
        if "design" in text or "architecture" in text:
            return CoordinationStrategy.DECOMPOSER_STRATEGIST_CRITIC
        elif "validate" in text or "test" in text:
            return CoordinationStrategy.PIPELINE_WITH_FEEDBACK
        else:
            return CoordinationStrategy.FAN_OUT_FAN_IN
            
    # Complex analysis tasks
    analysis_keywords = ["analyze", "research", "investigate", "understand"]
    if any(keyword in text for keyword in analysis_keywords):
        return CoordinationStrategy.DECOMPOSER_STRATEGIST_CRITIC
        
    # Implementation tasks with validation
    implementation_keywords = ["implement", "build", "create", "develop"]
    validation_keywords = ["test", "validate", "verify", "check"]
    
    if (any(impl in text for impl in implementation_keywords) and 
        any(val in text for val in validation_keywords)):
        return CoordinationStrategy.PIPELINE_WITH_FEEDBACK
        
    # Parallel exploration tasks
    exploration_keywords = ["explore", "discover", "survey", "evaluate"]
    if any(keyword in text for keyword in exploration_keywords):
        return CoordinationStrategy.FAN_OUT_FAN_IN
        
    # Default to DSC for complex tasks
    return CoordinationStrategy.DECOMPOSER_STRATEGIST_CRITIC


async def create_adaptive_plan(
    task_description: str,
    context: Optional[str] = None,
    coordination_strategy: Optional[CoordinationStrategy] = None,
    command_format: str = "claude"
) -> PlannerResponse:
    """
    Convenience function to create an adaptive orchestration plan.
    
    Args:
        task_description: Description of the task to plan
        context: Additional context for planning
        coordination_strategy: Optional coordination strategy (auto-detected if None)
        command_format: Command format ("claude" or "json")
        
    Returns:
        Planning response with adaptive orchestration
    """
    
    # Auto-detect coordination strategy if not provided
    if coordination_strategy is None:
        coordination_strategy = detect_coordination_strategy(task_description)
        
    # Create request
    request = PlannerRequest(
        task_description=task_description,
        context=context
    )
    
    # Create integrated planner
    planner = IntegratedPlannerService(command_format=command_format, enable_adaptive=True)
    
    try:
        # Generate adaptive plan
        response = await planner.handle_request(request, coordination_strategy)
        return response
    finally:
        await planner.close()


__all__ = [
    "IntegratedPlannerService",
    "detect_coordination_strategy", 
    "create_adaptive_plan"
]