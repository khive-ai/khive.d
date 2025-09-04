"""
Business logic monitoring for CLI workflows and agent orchestration.

Tracks business-level metrics including CLI workflow success rates, agent 
orchestration performance, task completion metrics, and user experience.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import logging
from collections import defaultdict, Counter

from khive.services.claude.hooks.coordination_metrics import get_metrics_collector

logger = logging.getLogger(__name__)


@dataclass
class CLIWorkflowMetrics:
    """Metrics for CLI workflow performance."""
    command: str
    success_count: int = 0
    failure_count: int = 0
    total_executions: int = 0
    avg_execution_time_ms: float = 0.0
    success_rate_percent: float = 100.0
    last_execution: Optional[datetime] = None
    common_errors: Dict[str, int] = field(default_factory=dict)
    performance_trend: str = "stable"  # "improving", "stable", "degrading"


@dataclass
class AgentOrchestrationMetrics:
    """Metrics for agent orchestration performance."""
    agent_role: str
    domain: Optional[str] = None
    tasks_assigned: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_completion_time_ms: float = 0.0
    success_rate_percent: float = 100.0
    coordination_efficiency: float = 100.0
    resource_utilization: float = 0.0
    last_activity: Optional[datetime] = None
    

@dataclass
class TaskFlowMetrics:
    """Metrics for task flow and user experience."""
    workflow_type: str
    total_workflows: int = 0
    successful_workflows: int = 0
    failed_workflows: int = 0
    avg_workflow_duration_ms: float = 0.0
    user_satisfaction_score: float = 100.0
    bottleneck_stages: List[str] = field(default_factory=list)
    optimization_opportunities: List[str] = field(default_factory=list)


@dataclass
class BusinessLogicMetrics:
    """Comprehensive business logic metrics."""
    timestamp: datetime
    
    # CLI Workflow Metrics
    cli_workflows: Dict[str, CLIWorkflowMetrics] = field(default_factory=dict)
    cli_success_rate_overall: float = 100.0
    cli_avg_response_time_ms: float = 0.0
    
    # Agent Orchestration Metrics
    agent_orchestration: Dict[str, AgentOrchestrationMetrics] = field(default_factory=dict)
    orchestration_success_rate: float = 100.0
    avg_agent_utilization: float = 0.0
    
    # Task Flow Metrics
    task_flows: Dict[str, TaskFlowMetrics] = field(default_factory=dict)
    overall_user_satisfaction: float = 100.0
    
    # System Efficiency Metrics
    coordination_overhead_percent: float = 0.0
    resource_contention_events: int = 0
    optimization_score: float = 100.0
    

class BusinessLogicMonitor:
    """
    Advanced business logic monitoring system.
    
    Tracks business-critical metrics including CLI workflows, agent orchestration,
    task completion rates, and user experience metrics with deep analytics.
    """
    
    def __init__(self):
        self.metrics_collector = get_metrics_collector()
        
        # Business metrics history
        self.metrics_history: List[BusinessLogicMetrics] = []
        self.max_history_size = 1000
        
        # CLI command tracking
        self.cli_command_history: List[Dict[str, Any]] = []
        self.max_cli_history = 2000
        
        # Agent activity tracking  
        self.agent_activity_history: List[Dict[str, Any]] = []
        self.max_agent_history = 2000
        
        # Performance baselines for comparison
        self.baselines: Dict[str, float] = {
            "cli_success_rate": 95.0,
            "cli_response_time_ms": 100.0,  # Ocean's target
            "agent_success_rate": 90.0,
            "orchestration_efficiency": 85.0,
            "user_satisfaction": 90.0
        }
        
        # Business thresholds
        self.thresholds = {
            "cli_success_rate_percent": 90.0,
            "cli_response_time_ms": 200.0,  # Warning threshold
            "agent_success_rate_percent": 85.0,
            "orchestration_efficiency_percent": 80.0,
            "coordination_overhead_percent": 15.0,
            "user_satisfaction_percent": 85.0
        }
    
    async def track_cli_command(
        self, 
        command: str, 
        execution_time_ms: float,
        success: bool,
        error_message: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Track CLI command execution for performance analysis."""
        command_data = {
            "timestamp": datetime.now(),
            "command": command,
            "execution_time_ms": execution_time_ms,
            "success": success,
            "error_message": error_message,
            "session_id": session_id
        }
        
        self.cli_command_history.append(command_data)
        if len(self.cli_command_history) > self.max_cli_history:
            self.cli_command_history.pop(0)
    
    async def track_agent_activity(
        self,
        agent_id: str,
        role: str,
        domain: Optional[str],
        task_description: str,
        duration_ms: float,
        success: bool,
        coordination_overhead_ms: float = 0.0,
        error_message: Optional[str] = None
    ):
        """Track agent activity for orchestration performance analysis."""
        activity_data = {
            "timestamp": datetime.now(),
            "agent_id": agent_id,
            "role": role,
            "domain": domain,
            "task_description": task_description,
            "duration_ms": duration_ms,
            "success": success,
            "coordination_overhead_ms": coordination_overhead_ms,
            "error_message": error_message
        }
        
        self.agent_activity_history.append(activity_data)
        if len(self.agent_activity_history) > self.max_agent_history:
            self.agent_activity_history.pop(0)
    
    def _analyze_cli_workflows(self, lookback_hours: int = 24) -> Dict[str, CLIWorkflowMetrics]:
        """Analyze CLI workflow performance."""
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        recent_commands = [
            cmd for cmd in self.cli_command_history
            if cmd["timestamp"] >= cutoff_time
        ]
        
        if not recent_commands:
            return {}
        
        # Group commands by type
        command_groups = defaultdict(list)
        for cmd in recent_commands:
            # Normalize command (extract base command)
            base_command = cmd["command"].split()[0] if cmd["command"] else "unknown"
            command_groups[base_command].append(cmd)
        
        cli_metrics = {}
        for command, executions in command_groups.items():
            success_count = sum(1 for cmd in executions if cmd["success"])
            failure_count = len(executions) - success_count
            total_executions = len(executions)
            
            execution_times = [cmd["execution_time_ms"] for cmd in executions]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            
            success_rate = (success_count / total_executions * 100) if total_executions > 0 else 0
            
            # Collect common errors
            common_errors = Counter()
            for cmd in executions:
                if not cmd["success"] and cmd["error_message"]:
                    # Extract error type from message
                    error_key = cmd["error_message"][:50]  # First 50 chars
                    common_errors[error_key] += 1
            
            # Determine performance trend (simple heuristic)
            if len(executions) >= 10:
                recent_half = executions[-len(executions)//2:]
                earlier_half = executions[:len(executions)//2]
                
                recent_success_rate = sum(1 for cmd in recent_half if cmd["success"]) / len(recent_half) * 100
                earlier_success_rate = sum(1 for cmd in earlier_half if cmd["success"]) / len(earlier_half) * 100
                
                if recent_success_rate > earlier_success_rate + 5:
                    trend = "improving"
                elif recent_success_rate < earlier_success_rate - 5:
                    trend = "degrading"
                else:
                    trend = "stable"
            else:
                trend = "stable"
            
            last_execution = max(cmd["timestamp"] for cmd in executions)
            
            cli_metrics[command] = CLIWorkflowMetrics(
                command=command,
                success_count=success_count,
                failure_count=failure_count,
                total_executions=total_executions,
                avg_execution_time_ms=avg_execution_time,
                success_rate_percent=success_rate,
                last_execution=last_execution,
                common_errors=dict(common_errors),
                performance_trend=trend
            )
        
        return cli_metrics
    
    def _analyze_agent_orchestration(self, lookback_hours: int = 24) -> Dict[str, AgentOrchestrationMetrics]:
        """Analyze agent orchestration performance."""
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        recent_activities = [
            activity for activity in self.agent_activity_history
            if activity["timestamp"] >= cutoff_time
        ]
        
        if not recent_activities:
            return {}
        
        # Group by agent role+domain combination
        agent_groups = defaultdict(list)
        for activity in recent_activities:
            key = f"{activity['role']}_{activity['domain'] or 'general'}"
            agent_groups[key].append(activity)
        
        orchestration_metrics = {}
        for agent_key, activities in agent_groups.items():
            role, domain = agent_key.rsplit('_', 1)
            if domain == 'general':
                domain = None
            
            tasks_assigned = len(activities)
            tasks_completed = sum(1 for a in activities if a["success"])
            tasks_failed = tasks_assigned - tasks_completed
            
            completion_times = [a["duration_ms"] for a in activities if a["success"]]
            avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
            
            success_rate = (tasks_completed / tasks_assigned * 100) if tasks_assigned > 0 else 0
            
            # Calculate coordination efficiency (lower overhead = higher efficiency)
            coordination_times = [a["coordination_overhead_ms"] for a in activities]
            avg_coordination_overhead = sum(coordination_times) / len(coordination_times) if coordination_times else 0
            total_time = avg_completion_time + avg_coordination_overhead
            coordination_efficiency = (avg_completion_time / total_time * 100) if total_time > 0 else 100
            
            # Simple resource utilization heuristic
            unique_agents = len(set(a["agent_id"] for a in activities))
            resource_utilization = min(100.0, tasks_assigned / max(1, unique_agents) * 10)
            
            last_activity = max(a["timestamp"] for a in activities)
            
            orchestration_metrics[agent_key] = AgentOrchestrationMetrics(
                agent_role=role,
                domain=domain,
                tasks_assigned=tasks_assigned,
                tasks_completed=tasks_completed,
                tasks_failed=tasks_failed,
                avg_completion_time_ms=avg_completion_time,
                success_rate_percent=success_rate,
                coordination_efficiency=coordination_efficiency,
                resource_utilization=resource_utilization,
                last_activity=last_activity
            )
        
        return orchestration_metrics
    
    def _analyze_task_flows(self, cli_metrics: Dict[str, CLIWorkflowMetrics]) -> Dict[str, TaskFlowMetrics]:
        """Analyze task flow and user experience metrics."""
        task_flows = {}
        
        # Group CLI workflows by category
        workflow_categories = {
            "planning": ["plan", "khive"],
            "coordination": ["coordinate", "compose"],
            "development": ["run", "test", "build"],
            "monitoring": ["status", "health", "metrics"],
            "management": ["start", "stop", "restart", "cleanup"]
        }
        
        for category, commands in workflow_categories.items():
            category_workflows = {
                cmd: metrics for cmd, metrics in cli_metrics.items()
                if any(command in cmd for command in commands)
            }
            
            if not category_workflows:
                continue
            
            total_workflows = sum(m.total_executions for m in category_workflows.values())
            successful_workflows = sum(m.success_count for m in category_workflows.values())
            failed_workflows = sum(m.failure_count for m in category_workflows.values())
            
            # Calculate average workflow duration
            workflow_durations = []
            for metrics in category_workflows.values():
                workflow_durations.extend([metrics.avg_execution_time_ms] * metrics.total_executions)
            
            avg_workflow_duration = sum(workflow_durations) / len(workflow_durations) if workflow_durations else 0
            
            # Calculate user satisfaction score based on success rate and response time
            success_rate = (successful_workflows / total_workflows * 100) if total_workflows > 0 else 100
            response_time_score = max(0, 100 - (avg_workflow_duration - 100) / 10)  # Penalty for >100ms
            user_satisfaction = (success_rate * 0.7 + response_time_score * 0.3)
            
            # Identify bottleneck stages (commands with high failure rates or slow performance)
            bottlenecks = []
            optimization_opportunities = []
            
            for cmd, metrics in category_workflows.items():
                if metrics.success_rate_percent < 90:
                    bottlenecks.append(f"{cmd} (success: {metrics.success_rate_percent:.1f}%)")
                if metrics.avg_execution_time_ms > 200:  # Slower than 200ms
                    optimization_opportunities.append(
                        f"{cmd} (avg: {metrics.avg_execution_time_ms:.1f}ms)"
                    )
            
            task_flows[category] = TaskFlowMetrics(
                workflow_type=category,
                total_workflows=total_workflows,
                successful_workflows=successful_workflows,
                failed_workflows=failed_workflows,
                avg_workflow_duration_ms=avg_workflow_duration,
                user_satisfaction_score=user_satisfaction,
                bottleneck_stages=bottlenecks,
                optimization_opportunities=optimization_opportunities
            )
        
        return task_flows
    
    async def collect_business_metrics(self, lookback_hours: int = 24) -> BusinessLogicMetrics:
        """Collect comprehensive business logic metrics."""
        timestamp = datetime.now()
        
        # Analyze CLI workflows
        cli_workflows = self._analyze_cli_workflows(lookback_hours)
        
        # Calculate overall CLI metrics
        if cli_workflows:
            total_cli_executions = sum(m.total_executions for m in cli_workflows.values())
            total_cli_successes = sum(m.success_count for m in cli_workflows.values())
            cli_success_rate = (total_cli_successes / total_cli_executions * 100) if total_cli_executions > 0 else 100
            
            all_execution_times = []
            for metrics in cli_workflows.values():
                all_execution_times.extend([metrics.avg_execution_time_ms] * metrics.total_executions)
            cli_avg_response_time = sum(all_execution_times) / len(all_execution_times) if all_execution_times else 0
        else:
            cli_success_rate = 100.0
            cli_avg_response_time = 0.0
        
        # Analyze agent orchestration
        agent_orchestration = self._analyze_agent_orchestration(lookback_hours)
        
        # Calculate overall orchestration metrics
        if agent_orchestration:
            total_tasks = sum(m.tasks_assigned for m in agent_orchestration.values())
            total_completed = sum(m.tasks_completed for m in agent_orchestration.values())
            orchestration_success_rate = (total_completed / total_tasks * 100) if total_tasks > 0 else 100
            
            avg_agent_utilization = sum(m.resource_utilization for m in agent_orchestration.values()) / len(agent_orchestration)
        else:
            orchestration_success_rate = 100.0
            avg_agent_utilization = 0.0
        
        # Analyze task flows
        task_flows = self._analyze_task_flows(cli_workflows)
        
        # Calculate overall user satisfaction
        if task_flows:
            satisfaction_scores = [flow.user_satisfaction_score for flow in task_flows.values()]
            overall_user_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores)
        else:
            overall_user_satisfaction = 100.0
        
        # Get coordination metrics from existing system
        coordination_report = self.metrics_collector.generate_report()
        coordination_overhead = coordination_report["detailed_metrics"]["performance"].get("avg_coordination_overhead", 0.0)
        
        # Calculate optimization score based on multiple factors
        optimization_factors = [
            cli_success_rate / 100,
            max(0, (200 - cli_avg_response_time) / 200),  # Response time factor
            orchestration_success_rate / 100,
            max(0, (100 - coordination_overhead) / 100),  # Lower overhead is better
            overall_user_satisfaction / 100
        ]
        optimization_score = sum(optimization_factors) / len(optimization_factors) * 100
        
        metrics = BusinessLogicMetrics(
            timestamp=timestamp,
            cli_workflows=cli_workflows,
            cli_success_rate_overall=cli_success_rate,
            cli_avg_response_time_ms=cli_avg_response_time,
            agent_orchestration=agent_orchestration,
            orchestration_success_rate=orchestration_success_rate,
            avg_agent_utilization=avg_agent_utilization,
            task_flows=task_flows,
            overall_user_satisfaction=overall_user_satisfaction,
            coordination_overhead_percent=coordination_overhead,
            resource_contention_events=0,  # TODO: Implement
            optimization_score=optimization_score
        )
        
        # Add to history
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history.pop(0)
        
        return metrics
    
    def check_business_violations(self, metrics: BusinessLogicMetrics) -> List[Dict[str, Any]]:
        """Check for business metric threshold violations."""
        violations = []
        
        # CLI success rate threshold
        if metrics.cli_success_rate_overall < self.thresholds["cli_success_rate_percent"]:
            violations.append({
                "metric": "cli_success_rate",
                "current": metrics.cli_success_rate_overall,
                "threshold": self.thresholds["cli_success_rate_percent"],
                "severity": "CRITICAL" if metrics.cli_success_rate_overall < 80 else "WARNING",
                "impact": "User experience degradation"
            })
        
        # CLI response time threshold (Ocean's <100ms target)
        if metrics.cli_avg_response_time_ms > self.thresholds["cli_response_time_ms"]:
            violations.append({
                "metric": "cli_response_time",
                "current": metrics.cli_avg_response_time_ms,
                "threshold": self.thresholds["cli_response_time_ms"],
                "severity": "WARNING",
                "impact": "Performance degradation",
                "target": "Ocean's target: <100ms"
            })
        
        # Agent success rate threshold
        if metrics.orchestration_success_rate < self.thresholds["agent_success_rate_percent"]:
            violations.append({
                "metric": "agent_success_rate",
                "current": metrics.orchestration_success_rate,
                "threshold": self.thresholds["agent_success_rate_percent"],
                "severity": "WARNING",
                "impact": "Reduced system reliability"
            })
        
        # Coordination overhead threshold
        if metrics.coordination_overhead_percent > self.thresholds["coordination_overhead_percent"]:
            violations.append({
                "metric": "coordination_overhead",
                "current": metrics.coordination_overhead_percent,
                "threshold": self.thresholds["coordination_overhead_percent"],
                "severity": "WARNING",
                "impact": "Efficiency degradation"
            })
        
        # User satisfaction threshold
        if metrics.overall_user_satisfaction < self.thresholds["user_satisfaction_percent"]:
            violations.append({
                "metric": "user_satisfaction",
                "current": metrics.overall_user_satisfaction,
                "threshold": self.thresholds["user_satisfaction_percent"],
                "severity": "CRITICAL",
                "impact": "Poor user experience"
            })
        
        # Individual workflow violations
        for cmd, workflow_metrics in metrics.cli_workflows.items():
            if workflow_metrics.success_rate_percent < 85:  # Individual command threshold
                violations.append({
                    "metric": f"cli_command_{cmd}_success_rate",
                    "current": workflow_metrics.success_rate_percent,
                    "threshold": 85.0,
                    "severity": "WARNING",
                    "impact": f"Command '{cmd}' reliability issues"
                })
        
        return violations
    
    def get_performance_insights(self) -> List[str]:
        """Generate actionable performance insights."""
        if not self.metrics_history:
            return ["No performance data available yet"]
        
        latest = self.metrics_history[-1]
        insights = []
        
        # CLI performance insights
        if latest.cli_avg_response_time_ms > 100:  # Ocean's target
            insights.append(
                f"CLI response time ({latest.cli_avg_response_time_ms:.1f}ms) exceeds Ocean's target of <100ms"
            )
        
        # Success rate insights
        if latest.cli_success_rate_overall < 95:
            insights.append(
                f"CLI success rate ({latest.cli_success_rate_overall:.1f}%) below optimal threshold"
            )
        
        # Identify specific problem commands
        problem_commands = [
            cmd for cmd, metrics in latest.cli_workflows.items()
            if metrics.success_rate_percent < 90 or metrics.avg_execution_time_ms > 200
        ]
        if problem_commands:
            insights.append(
                f"Commands needing attention: {', '.join(problem_commands[:3])}"
            )
        
        # Agent orchestration insights
        if latest.orchestration_success_rate < 90:
            insights.append(
                f"Agent orchestration success rate ({latest.orchestration_success_rate:.1f}%) needs improvement"
            )
        
        # Coordination overhead insights
        if latest.coordination_overhead_percent > 10:
            insights.append(
                f"Coordination overhead ({latest.coordination_overhead_percent:.1f}%) is high"
            )
        
        # User satisfaction insights
        if latest.overall_user_satisfaction < 90:
            insights.append(
                f"User satisfaction ({latest.overall_user_satisfaction:.1f}%) below target"
            )
        
        # Optimization opportunities
        optimization_opportunities = []
        for flow in latest.task_flows.values():
            optimization_opportunities.extend(flow.optimization_opportunities[:2])  # Limit to 2 per flow
        
        if optimization_opportunities:
            insights.append(f"Optimization opportunities: {', '.join(optimization_opportunities[:3])}")
        
        return insights if insights else ["System performance is optimal"]
    
    def get_business_summary(self) -> Dict[str, Any]:
        """Get comprehensive business logic monitoring summary."""
        if not self.metrics_history:
            return {"status": "no_data", "metrics_collected": 0}
        
        latest = self.metrics_history[-1]
        violations = self.check_business_violations(latest)
        insights = self.get_performance_insights()
        
        # Determine overall business health
        if any(v["severity"] == "CRITICAL" for v in violations):
            business_health = "CRITICAL"
        elif any(v["severity"] == "WARNING" for v in violations):
            business_health = "WARNING"
        else:
            business_health = "HEALTHY"
        
        return {
            "business_health": business_health,
            "timestamp": latest.timestamp.isoformat(),
            "metrics_collected": len(self.metrics_history),
            "violations": violations,
            "performance_insights": insights,
            "cli_performance": {
                "success_rate_percent": latest.cli_success_rate_overall,
                "avg_response_time_ms": latest.cli_avg_response_time_ms,
                "total_workflows": len(latest.cli_workflows),
                "target_response_time_ms": 100.0  # Ocean's target
            },
            "agent_orchestration": {
                "success_rate_percent": latest.orchestration_success_rate,
                "avg_utilization_percent": latest.avg_agent_utilization,
                "active_agent_types": len(latest.agent_orchestration)
            },
            "user_experience": {
                "satisfaction_score": latest.overall_user_satisfaction,
                "workflow_categories": len(latest.task_flows),
                "optimization_score": latest.optimization_score
            },
            "baselines": self.baselines,
            "thresholds": self.thresholds
        }