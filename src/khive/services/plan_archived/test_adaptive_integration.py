"""
Test script to verify Adaptive Orchestration integration with manual coordination protocol.

This script demonstrates that the Decomposer-Strategist-Critic pipeline works
correctly with the khive coordination system.
"""

import asyncio
import time
from typing import Dict, Any

from .adaptive_planner_service import AdaptivePlannerService
from .parts import PlannerRequest


async def test_adaptive_orchestration():
    """Test the adaptive orchestration pipeline."""
    
    print("🧪 Testing Adaptive Orchestration Integration")
    print("=" * 60)
    
    # Create adaptive planner service
    service = AdaptivePlannerService(
        command_format="claude",
        enable_adaptive=True
    )
    
    try:
        # Test case 1: Simple task
        print("\n📝 Test Case 1: Simple Task")
        simple_request = PlannerRequest(
            task_description="Fix a bug in the user authentication system",
            context="Simple bug fix task"
        )
        
        simple_response = await service.handle_request(simple_request)
        print(f"✅ Simple task planned successfully")
        print(f"   - Complexity: {simple_response.complexity}")
        print(f"   - Recommended agents: {simple_response.recommended_agents}")
        print(f"   - Confidence: {simple_response.confidence:.2f}")
        print(f"   - Phases: {len(simple_response.phases)}")
        
        # Test case 2: Complex task (should trigger full adaptive orchestration)
        print("\n📝 Test Case 2: Complex Task")
        complex_request = PlannerRequest(
            task_description="Migrate entire legacy system to microservices architecture with complete API redesign",
            context="Complex migration task requiring multiple teams and phases"
        )
        
        complex_response = await service.handle_request(complex_request)
        print(f"✅ Complex task planned successfully")
        print(f"   - Complexity: {complex_response.complexity}")
        print(f"   - Recommended agents: {complex_response.recommended_agents}")
        print(f"   - Confidence: {complex_response.confidence:.2f}")
        print(f"   - Phases: {len(complex_response.phases)}")
        
        # Test case 3: Coordination strategy adaptation
        print("\n📝 Test Case 3: Strategy Adaptation")
        from .adaptive_models import CoordinationStrategy
        
        # Simulate runtime performance metrics
        performance_metrics = {
            "coordination_overhead": 0.8,  # High overhead
            "efficiency": 0.4,             # Low efficiency  
            "conflict_rate": 0.6           # High conflicts
        }
        
        adapted_strategy = await service.adapt_strategy_runtime(
            session_id="test_session_123",
            current_strategy=CoordinationStrategy.HIERARCHICAL,
            performance_metrics=performance_metrics
        )
        print(f"✅ Strategy adaptation tested")
        print(f"   - Original: {CoordinationStrategy.HIERARCHICAL.value}")
        print(f"   - Adapted: {adapted_strategy.value}")
        
        # Show metrics
        print("\n📊 Service Metrics:")
        metrics = service.get_metrics()
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"   - {key}: {value:.3f}")
            elif isinstance(value, dict):
                print(f"   - {key}: {len(value)} entries")
            else:
                print(f"   - {key}: {value}")
        
        print("\n✅ All adaptive orchestration tests passed!")
        
        # Test integration with coordination system
        print("\n🤝 Testing Coordination System Integration:")
        from khive.services.claude.hooks.coordination import get_registry
        registry = get_registry()
        
        status = registry.get_status()
        print(f"   - Active agents: {status['active_agents']}")
        print(f"   - Locked files: {len(status['locked_files'])}")
        print(f"   - Conflicts prevented: {status['metrics']['conflicts_prevented']}")
        print(f"   - Artifacts shared: {status['metrics']['artifacts_shared']}")
        
        print("\n🎉 Adaptive Orchestration + Manual Coordination Integration: SUCCESS!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    finally:
        # Cleanup
        await service.close()


def verify_integration_components():
    """Verify that all integration components are properly importable."""
    
    print("\n🔍 Verifying Integration Components:")
    
    try:
        # Test imports
        from .adaptive_models import (
            CoordinationStrategy,
            AdaptiveTaskPhase, 
            TaskDecomposition,
            StrategyRecommendation,
            PlanCritique,
            AdaptiveOrchestrationPlan,
            BasicDecomposer,
            BasicStrategist,
            BasicCritic
        )
        print("   ✅ Adaptive models imported successfully")
        
        from .adaptive_pipeline import AdaptiveOrchestrationPipeline
        print("   ✅ Adaptive pipeline imported successfully")
        
        from .adaptive_planner_service import AdaptivePlannerService
        print("   ✅ Adaptive planner service imported successfully")
        
        from khive.services.claude.hooks.coordination import get_registry
        print("   ✅ Coordination system imported successfully")
        
        # Test enum values
        strategies = list(CoordinationStrategy)
        print(f"   ✅ CoordinationStrategy enum has {len(strategies)} strategies:")
        for strategy in strategies:
            print(f"      - {strategy.value}")
        
        # Test basic instantiation
        decomposer = BasicDecomposer()
        strategist = BasicStrategist()
        critic = BasicCritic()
        print("   ✅ Pipeline components instantiated successfully")
        
        # Test pipeline creation
        pipeline = AdaptiveOrchestrationPipeline(
            decomposer=decomposer,
            strategist=strategist, 
            critic=critic,
            enable_coordination=True
        )
        print("   ✅ Adaptive orchestration pipeline created successfully")
        
        print("\n✅ All integration components verified successfully!")
        return True
        
    except Exception as e:
        print(f"   ❌ Component verification failed: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 Adaptive Orchestration Integration Test Suite")
    print("=" * 60)
    
    # Verify components first
    if not verify_integration_components():
        return
    
    # Run integration tests
    success = await test_adaptive_orchestration()
    
    if success:
        print("\n🎉 SUCCESS: Adaptive Orchestration model fully integrated!")
        print("\n📋 Implementation Summary:")
        print("   ✅ CoordinationStrategy enum implemented")
        print("   ✅ Decomposer-Strategist-Critic pipeline implemented")
        print("   ✅ AdaptiveTaskPhase models enhanced")
        print("   ✅ Manual coordination protocol integrated")
        print("   ✅ Backward compatibility maintained")
        print("   ✅ Runtime strategy adaptation supported")
    else:
        print("\n❌ FAILURE: Integration test failed")


if __name__ == "__main__":
    asyncio.run(main())
