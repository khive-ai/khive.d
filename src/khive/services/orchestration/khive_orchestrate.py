"""
Khive Orchestration Core Engine

This module provides the main entry points for orchestration workflows,
integrating the LionOrchestrator with daemon services, CLI commands,
and session management.

Key Integration Points:
- CLI commands → orchestrate() entry point
- Daemon planning service → workflow execution  
- Session management → persistence and state
- Inter-agent coordination → distributed execution patterns

Design Principles (Distributed Systems):
- Consensus-based decision making for complex workflows
- Fault-tolerant execution with graceful degradation
- Coordination patterns for agent synchronization
- State management for long-running orchestrations
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from khive.daemon.client import KhiveDaemonClient, get_daemon_client
from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.orchestration.parts import (
    FanoutConfig, 
    FanoutPatterns, 
    Issue,
    IssueExecution,
    IssuePlan,
    RefinementConfig
)
from khive.utils import get_logger

logger = get_logger("khive.orchestration", "🎭 [ORCHESTRATOR]")

# Global orchestration registry for distributed coordination
_active_orchestrations: Dict[str, 'OrchestrationSession'] = {}


class OrchestrationSession:
    """
    Manages a single orchestration session with distributed coordination.
    
    Handles:
    - LionOrchestrator lifecycle management
    - Daemon service integration  
    - Session persistence and recovery
    - Inter-agent coordination
    """
    
    def __init__(
        self, 
        session_id: str, 
        flow_name: str,
        daemon_client: Optional[KhiveDaemonClient] = None
    ):
        self.session_id = session_id
        self.flow_name = flow_name
        self.daemon_client = daemon_client or get_daemon_client()
        self.orchestrator: Optional[LionOrchestrator] = None
        self.start_time = time.time()
        self.status = "initializing"
        self.results: Dict[str, Any] = {}
        
    async def initialize(
        self, 
        model: Optional[str] = None,
        system: Optional[str] = None,
        resume_from: Optional[str] = None
    ):
        """Initialize orchestration session with optional resume capability."""
        try:
            self.status = "initializing"
            
            # Initialize LionOrchestrator
            self.orchestrator = LionOrchestrator(self.flow_name)
            
            if resume_from:
                # Resume from saved session
                logger.info(f"Resuming orchestration from {resume_from}")
                self.orchestrator = await LionOrchestrator.load_json(resume_from)
            else:
                # Fresh initialization
                await self.orchestrator.initialize(model=model, system=system)
            
            # Register with coordination system
            await self._register_with_daemon()
            
            self.status = "ready" 
            logger.info(f"✅ Orchestration session {self.session_id} initialized")
            
        except Exception as e:
            self.status = "failed"
            logger.error(f"❌ Failed to initialize session {self.session_id}: {e}")
            raise
    
    async def _register_with_daemon(self):
        """Register orchestration session with daemon for coordination."""
        try:
            if self.daemon_client.is_running():
                coordination_info = self.daemon_client.coordinate_start(
                    f"Orchestration session: {self.flow_name}",
                    self.session_id
                )
                logger.debug(f"Registered with daemon: {coordination_info}")
        except Exception as e:
            logger.warning(f"Failed to register with daemon: {e}")
            # Continue without daemon coordination
    
    async def save_checkpoint(self) -> str:
        """Save orchestration state for recovery."""
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
            
        checkpoint_path = await self.orchestrator.save_json()
        logger.info(f"💾 Checkpoint saved: {checkpoint_path}")
        return checkpoint_path
    
    async def execute_fanout(
        self,
        config: FanoutConfig,
        max_agents: int = 8,
        visualize: bool = False
    ):
        """Execute fanout orchestration pattern."""
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
            
        self.status = "executing"
        
        try:
            result = await self.orchestrator.fanout(
                initial_desc=config.initial_desc,
                planning_instruction=config.planning_instruction,
                synth_instruction=config.synth_instruction,
                context=config.context,
                max_agents=max_agents,
                visualize=visualize
            )
            
            self.results["fanout"] = {
                "status": "completed",
                "synth_result": result.synth_result,
                "execution_time": time.time() - self.start_time
            }
            
            self.status = "completed"
            return result
            
        except Exception as e:
            self.status = "failed"
            self.results["error"] = str(e)
            logger.error(f"❌ Fanout execution failed: {e}")
            raise
    
    async def execute_fanout_with_refinement(
        self,
        fanout_config: FanoutConfig,
        refinement_config: RefinementConfig,
        max_agents: int = 8,
        visualize: bool = False,
        project_phase: Optional[str] = None,
        is_critical_path: bool = False,
        is_experimental: bool = False
    ):
        """Execute fanout with gated refinement pattern."""
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
            
        self.status = "executing"
        
        try:
            result = await self.orchestrator.fanout_w_gated_refinement(
                initial_desc=fanout_config.initial_desc,
                refinement_desc=refinement_config.refinement_desc,
                gate_instruction=refinement_config.gate_instruction,
                synth_instruction=fanout_config.synth_instruction,
                planning_instruction=fanout_config.planning_instruction,
                context=fanout_config.context,
                critic_domain=refinement_config.critic_domain,
                critic_role=refinement_config.critic_role,
                gates=refinement_config.gates,
                max_agents=max_agents,
                visualize=visualize,
                project_phase=project_phase,
                is_critical_path=is_critical_path,
                is_experimental=is_experimental
            )
            
            self.results["fanout_with_refinement"] = {
                "status": "completed",
                "synth_result": result.synth_result,
                "gate_passed": result.gate_passed,
                "refinement_executed": result.refinement_executed,
                "execution_time": time.time() - self.start_time
            }
            
            self.status = "completed"
            return result
            
        except Exception as e:
            self.status = "failed"  
            self.results["error"] = str(e)
            logger.error(f"❌ Fanout with refinement execution failed: {e}")
            raise
    
    async def cleanup(self):
        """Clean up orchestration session resources."""
        try:
            # Notify daemon of completion
            if self.daemon_client.is_running():
                self.daemon_client.coordinate_complete(
                    self.session_id,
                    self.session_id,
                    json.dumps(self.results),
                    []
                )
            
            # Save final state
            if self.orchestrator and self.status == "completed":
                await self.save_checkpoint()
            
            self.status = "cleaned_up"
            logger.info(f"🧹 Session {self.session_id} cleaned up")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


class OrchestrationEngine:
    """
    Main orchestration engine providing high-level workflow execution.
    
    Implements distributed systems patterns:
    - Consensus-based workflow selection
    - Fault-tolerant execution with retries
    - Coordination with daemon services
    - Session management and recovery
    """
    
    def __init__(self, daemon_client: Optional[KhiveDaemonClient] = None):
        self.daemon_client = daemon_client or get_daemon_client()
        
    async def orchestrate_from_plan(
        self,
        plan: IssuePlan,
        session_id: Optional[str] = None,
        resume_from: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute orchestration workflow from a structured plan.
        
        Main entry point for CLI and daemon integration.
        """
        session_id = session_id or f"orch_{int(time.time())}"
        
        try:
            # Create orchestration session
            session = OrchestrationSession(
                session_id=session_id,
                flow_name=plan.flow_name,
                daemon_client=self.daemon_client
            )
            
            # Register session globally for coordination
            _active_orchestrations[session_id] = session
            
            # Initialize session (filter kwargs to only include supported parameters)
            init_kwargs = {k: v for k, v in kwargs.items() if k in ['model', 'system']}
            await session.initialize(
                system=plan.system,
                resume_from=resume_from,
                **init_kwargs
            )
            
            # Execute based on pattern type
            result = None
            
            if plan.pattern == FanoutPatterns.FANOUT:
                result = await session.execute_fanout(
                    config=plan.fanout_config,
                    max_agents=kwargs.get('max_agents', 8),
                    visualize=kwargs.get('visualize', False)
                )
                
            elif plan.pattern == FanoutPatterns.W_REFINEMENT:
                if not plan.refinement_config:
                    raise ValueError("Refinement config required for gated refinement pattern")
                    
                result = await session.execute_fanout_with_refinement(
                    fanout_config=plan.fanout_config,
                    refinement_config=plan.refinement_config,
                    max_agents=kwargs.get('max_agents', 8),
                    visualize=kwargs.get('visualize', False),
                    project_phase=plan.project_phase,
                    is_critical_path=plan.is_critical_path,
                    is_experimental=plan.is_experimental
                )
                
            else:
                raise ValueError(f"Unsupported orchestration pattern: {plan.pattern}")
            
            # Create issue execution record
            issue = await Issue.get(plan.issue_num, plan)
            execution = IssueExecution(
                success=True,
                result=result
            )
            issue.content.issue_result.executions.append(execution)
            issue.content.operation_status = "completed"
            issue.content.gate_passed = getattr(result, 'gate_passed', True)
            await issue.sync()
            
            return {
                "success": True,
                "session_id": session_id,
                "result": result,
                "execution_time": time.time() - session.start_time
            }
            
        except Exception as e:
            logger.error(f"❌ Orchestration failed for session {session_id}: {e}")
            
            # Record failure if issue exists
            try:
                issue = await Issue.get(plan.issue_num, plan)
                execution = IssueExecution(
                    success=False,
                    result=None  # type: ignore
                )
                issue.content.issue_result.executions.append(execution)
                issue.content.operation_status = "failed"
                await issue.sync()
            except Exception:
                pass  # Don't fail on failure recording
            
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e),
                "execution_time": time.time() - session.start_time
            }
            
        finally:
            # Cleanup session
            if session_id in _active_orchestrations:
                await _active_orchestrations[session_id].cleanup()
                del _active_orchestrations[session_id]


# Global engine instance
_global_engine: Optional[OrchestrationEngine] = None


def get_orchestration_engine() -> OrchestrationEngine:
    """Get or create global orchestration engine."""
    global _global_engine
    if _global_engine is None:
        _global_engine = OrchestrationEngine()
    return _global_engine


# Main CLI Entry Points

async def orchestrate_task(
    task_description: str,
    context: Optional[str] = None,
    pattern: str = "fanout",
    max_agents: int = 8,
    visualize: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Orchestrate a task from description.
    
    Main entry point for ad-hoc orchestration without formal planning.
    """
    engine = get_orchestration_engine()
    
    # Get orchestration plan from daemon
    try:
        if engine.daemon_client.is_running():
            plan_response = engine.daemon_client.plan(
                task_description, 
                {"context": context} if context else None
            )
        else:
            # Fallback: create simple plan
            plan_response = _create_fallback_plan(task_description, context, pattern)
            
    except Exception as e:
        logger.error(f"Failed to get plan: {e}")
        plan_response = _create_fallback_plan(task_description, context, pattern)
    
    # Convert to IssuePlan and execute
    plan = _convert_to_issue_plan(plan_response, task_description)
    
    return await engine.orchestrate_from_plan(
        plan=plan,
        max_agents=max_agents,
        visualize=visualize,
        **kwargs
    )


async def orchestrate_issue(
    issue_num: Union[str, int],
    **kwargs
) -> Dict[str, Any]:
    """
    Orchestrate execution of a GitHub issue.
    
    Entry point for issue-based orchestration workflows.
    """
    engine = get_orchestration_engine()
    
    # Load or create issue plan
    issue_num_int = int(issue_num)
    issue = await Issue.load(issue_num_int)
    
    if not issue:
        raise ValueError(f"Issue #{issue_num} not found. Create a plan first with 'khive plan'")
    
    return await engine.orchestrate_from_plan(
        plan=issue.content.issue_plan,
        **kwargs
    )


def _create_fallback_plan(
    task_description: str, 
    context: Optional[str], 
    pattern: str
) -> Dict[str, Any]:
    """Create a simple fallback plan when daemon is unavailable."""
    return {
        "orchestration_plan": {
            "flow_name": f"task_{int(time.time())}",
            "system": f"You are orchestrating: {task_description}",
            "pattern": pattern,
            "fanout_config": {
                "initial_desc": task_description,
                "planning_instruction": f"Plan how to accomplish: {task_description}",
                "synth_instruction": "Synthesize results and provide final deliverable",
                "context": context
            }
        }
    }


def _convert_to_issue_plan(plan_data: Dict[str, Any], task_description: str) -> IssuePlan:
    """Convert daemon plan response to IssuePlan object."""
    plan_info = plan_data.get("orchestration_plan", {})
    
    fanout_config = FanoutConfig(
        initial_desc=plan_info.get("initial_desc", task_description),
        planning_instruction=plan_info.get("planning_instruction", f"Plan: {task_description}"),
        synth_instruction=plan_info.get("synth_instruction", "Synthesize results"),
        context=plan_info.get("context")
    )
    
    issue_plan = IssuePlan(
        issue_num=0,  # Ad-hoc task
        flow_name=plan_info.get("flow_name", f"task_{int(time.time())}"),
        system=plan_info.get("system", f"Orchestrating: {task_description}"),
        pattern=FanoutPatterns(plan_info.get("pattern", "fanout")),
        fanout_config=fanout_config
    )
    
    return issue_plan


# Session Management Functions

async def list_active_sessions() -> List[Dict[str, Any]]:
    """List all active orchestration sessions."""
    sessions = []
    for session_id, session in _active_orchestrations.items():
        sessions.append({
            "session_id": session_id,
            "flow_name": session.flow_name,
            "status": session.status,
            "start_time": session.start_time,
            "duration": time.time() - session.start_time
        })
    return sessions


async def get_session_status(session_id: str) -> Optional[Dict[str, Any]]:
    """Get status of a specific orchestration session."""
    if session_id not in _active_orchestrations:
        return None
        
    session = _active_orchestrations[session_id]
    return {
        "session_id": session_id,
        "flow_name": session.flow_name,
        "status": session.status,
        "start_time": session.start_time,
        "duration": time.time() - session.start_time,
        "results": session.results
    }


async def stop_session(session_id: str) -> bool:
    """Stop a running orchestration session."""
    if session_id not in _active_orchestrations:
        return False
        
    session = _active_orchestrations[session_id]
    session.status = "stopping"
    
    try:
        await session.cleanup()
        del _active_orchestrations[session_id]
        return True
    except Exception as e:
        logger.error(f"Error stopping session {session_id}: {e}")
        return False


# CLI Integration

def main():
    """Main CLI entry point for orchestration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Khive Orchestration Engine")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Task orchestration command
    task_parser = subparsers.add_parser("task", help="Orchestrate a task")
    task_parser.add_argument("description", help="Task description")
    task_parser.add_argument("--context", help="Additional context")
    task_parser.add_argument("--pattern", default="fanout", choices=["fanout", "fanout_with_gated_refinement"])
    task_parser.add_argument("--max-agents", type=int, default=8, help="Maximum number of agents")
    task_parser.add_argument("--visualize", action="store_true", help="Visualize workflow")
    
    # Issue orchestration command  
    issue_parser = subparsers.add_parser("issue", help="Orchestrate a GitHub issue")
    issue_parser.add_argument("issue_num", type=int, help="GitHub issue number")
    issue_parser.add_argument("--max-agents", type=int, default=8, help="Maximum number of agents")
    issue_parser.add_argument("--visualize", action="store_true", help="Visualize workflow")
    
    # Session management commands
    sessions_parser = subparsers.add_parser("sessions", help="Manage orchestration sessions")
    sessions_subparsers = sessions_parser.add_subparsers(dest="sessions_command")
    
    sessions_subparsers.add_parser("list", help="List active sessions")
    
    status_parser = sessions_subparsers.add_parser("status", help="Get session status")
    status_parser.add_argument("session_id", help="Session ID")
    
    stop_parser = sessions_subparsers.add_parser("stop", help="Stop session")
    stop_parser.add_argument("session_id", help="Session ID")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute commands
    try:
        if args.command == "task":
            result = asyncio.run(orchestrate_task(
                task_description=args.description,
                context=args.context,
                pattern=args.pattern,
                max_agents=args.max_agents,
                visualize=args.visualize
            ))
            print(json.dumps(result, indent=2))
            
        elif args.command == "issue":
            result = asyncio.run(orchestrate_issue(
                issue_num=args.issue_num,
                max_agents=args.max_agents,
                visualize=args.visualize
            ))
            print(json.dumps(result, indent=2))
            
        elif args.command == "sessions":
            if args.sessions_command == "list":
                sessions = asyncio.run(list_active_sessions())
                print(json.dumps(sessions, indent=2))
                
            elif args.sessions_command == "status":
                status = asyncio.run(get_session_status(args.session_id))
                if status:
                    print(json.dumps(status, indent=2))
                else:
                    print(f"Session {args.session_id} not found")
                    
            elif args.sessions_command == "stop":
                success = asyncio.run(stop_session(args.session_id))
                if success:
                    print(f"Session {args.session_id} stopped")
                else:
                    print(f"Failed to stop session {args.session_id}")
                    
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()