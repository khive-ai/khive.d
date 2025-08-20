"""
Handoff Coordinator for Parallel Fan-Out Execution

This module manages parallel agent execution, dependency resolution, and
artifact handoffs in the khive.d orchestration system.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from khive.core import TimePolicy

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AgentSpec:
    """Specification for an agent to be spawned"""

    role: str
    domain: str
    priority: float
    dependencies: list[str] = field(default_factory=list)
    spawn_command: str = ""
    session_id: str = ""
    phase: str = ""
    context: str = ""


@dataclass
class ExecutionNode:
    """Represents an agent execution node in the dependency graph"""

    agent_spec: AgentSpec
    status: str = "pending"  # pending, ready, running, completed, failed
    start_time: datetime | None = None
    completion_time: datetime | None = None
    artifacts: list[str] = field(default_factory=list)
    dependencies_met: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)


class HandoffCoordinator:
    """
    Coordinates parallel agent execution with dependency resolution.

    Features:
    - Topological scheduling of agents based on dependencies
    - Parallel fan-out execution for independent agents
    - Artifact management and handoff tracking
    - Quality gate enforcement
    - Timeout handling
    """

    def __init__(self, session_id: str, workspace_dir: Path):
        """
        Initialize the handoff coordinator.

        Args:
            session_id: Unique session identifier
            workspace_dir: Directory for artifact storage
        """
        self.session_id = session_id
        self.workspace_dir = workspace_dir
        self.session_dir = workspace_dir / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Execution state
        self.execution_graph: dict[str, ExecutionNode] = {}
        self.ready_queue: deque[str] = deque()
        self.running_agents: set[str] = set()
        self.completed_agents: set[str] = set()
        self.failed_agents: set[str] = set()

        # Configuration
        self.max_concurrent_agents = 8
        self.agent_timeout = 300  # 5 minutes
        self.quality_gate_timeout = 60  # 1 minute

        # Metrics
        self.start_time: datetime | None = None
        self.execution_metrics: dict[str, float] = {}

        # Artifact registry
        self.registry_path = self.session_dir / "artifact_registry.json"
        self.load_artifact_registry()

    def load_artifact_registry(self) -> None:
        """Load existing artifact registry or create new one"""
        if self.registry_path.exists():
            with open(self.registry_path) as f:
                self.artifact_registry = json.load(f)
        else:
            self.artifact_registry = {
                "session_id": self.session_id,
                "created_at": TimePolicy.now_utc().isoformat(),
                "artifacts": [],
                "phases": [],
                "status": "active",
                "coordination_metadata": {
                    "parallel_execution": True,
                    "dependency_resolution": True,
                    "max_concurrent_agents": self.max_concurrent_agents,
                },
            }
            self.save_artifact_registry()

    def save_artifact_registry(self) -> None:
        """Save artifact registry to disk"""
        with open(self.registry_path, "w") as f:
            json.dump(self.artifact_registry, f, indent=2)

    def add_agent(self, agent_spec: AgentSpec) -> str:
        """
        Add an agent to the execution graph.

        Args:
            agent_spec: Agent specification

        Returns:
            Agent identifier
        """
        agent_id = f"{agent_spec.role}_{agent_spec.domain}"

        # Create execution node
        node = ExecutionNode(agent_spec=agent_spec)
        self.execution_graph[agent_id] = node

        logger.info(f"Added agent {agent_id} to execution graph")
        return agent_id

    def _are_dependencies_met(self, agent_id: str) -> bool:
        """Check if all dependencies for an agent are met"""
        agent_spec = self.execution_graph[agent_id].agent_spec

        # Check if all role dependencies are satisfied
        for dep_role in agent_spec.dependencies:
            # Find agent with this role that has completed
            dep_satisfied = False
            for completed_agent_id in self.completed_agents:
                if self.execution_graph[completed_agent_id].agent_spec.role == dep_role:
                    dep_satisfied = True
                    break

            if not dep_satisfied:
                return False

        return True

    def build_dependency_graph(self, agent_specs: list[AgentSpec]) -> None:
        """
        Build the complete dependency graph from agent specifications.

        Args:
            agent_specs: List of agent specifications
        """
        # Clear existing graph
        self.execution_graph.clear()
        self.ready_queue.clear()

        # Add all agents to graph first
        agent_id_map = {}  # Map role names to agent IDs
        for spec in agent_specs:
            agent_id = self.add_agent(spec)
            agent_id_map[spec.role] = agent_id

        # Set up dependencies after all agents are added
        for agent_id, node in self.execution_graph.items():
            for dep_role in node.agent_spec.dependencies:
                if dep_role in agent_id_map:
                    dep_agent_id = agent_id_map[dep_role]
                    self.execution_graph[dep_agent_id].dependents.add(agent_id)

        # Check which agents are ready to execute
        for agent_id in self.execution_graph:
            if self._are_dependencies_met(agent_id):
                self.execution_graph[agent_id].status = "ready"
                self.ready_queue.append(agent_id)

        # Perform topological sort to validate dependencies
        if not self._validate_dependency_graph():
            raise ValueError("Circular dependency detected in agent execution graph")

        logger.info(f"Built dependency graph with {len(agent_specs)} agents")

    def _validate_dependency_graph(self) -> bool:
        """Validate dependency graph for cycles using topological sort"""
        # Kahn's algorithm for cycle detection
        in_degree = defaultdict(int)

        # Calculate in-degrees
        for agent_id, node in self.execution_graph.items():
            for dep in node.agent_spec.dependencies:
                in_degree[agent_id] += 1

        # Find nodes with no incoming edges
        queue = deque([
            agent_id for agent_id in self.execution_graph if in_degree[agent_id] == 0
        ])
        processed = 0

        while queue:
            current = queue.popleft()
            processed += 1

            # Remove edges from current node
            for dependent in self.execution_graph[current].dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return processed == len(self.execution_graph)

    async def execute_parallel_fanout(
        self, timeout: float | None = None
    ) -> dict[str, str]:
        """
        Execute agents in parallel with dependency resolution.

        Args:
            timeout: Overall execution timeout in seconds

        Returns:
            Dictionary mapping agent IDs to their execution status
        """
        self.start_time = TimePolicy.now_utc()
        logger.info(
            f"Starting parallel fan-out execution with {len(self.execution_graph)} agents"
        )

        # Create execution tasks
        execution_tasks = []

        try:
            # Main execution loop
            while self.ready_queue or self.running_agents:
                # Start new agents if slots available
                while (
                    self.ready_queue
                    and len(self.running_agents) < self.max_concurrent_agents
                ):
                    agent_id = self.ready_queue.popleft()
                    task = asyncio.create_task(self._execute_agent(agent_id))
                    execution_tasks.append(task)

                # Wait for at least one agent to complete
                if self.running_agents:
                    done, pending = await asyncio.wait(
                        execution_tasks,
                        return_when=asyncio.FIRST_COMPLETED,
                        timeout=timeout,
                    )

                    # Process completed tasks
                    for task in done:
                        try:
                            agent_id, status = await task
                            self._handle_agent_completion(agent_id, status)
                        except Exception as e:
                            logger.exception(f"Agent execution failed: {e}")

                    # Update task list
                    execution_tasks = list(pending)

                # Check for timeout
                if (
                    timeout
                    and (TimePolicy.now_utc() - self.start_time).total_seconds() > timeout
                ):
                    logger.warning("Parallel execution timeout reached")
                    break

        except Exception as e:
            logger.exception(f"Parallel execution error: {e}")
            raise

        finally:
            # Cancel any remaining tasks
            for task in execution_tasks:
                task.cancel()

        # Generate execution report
        execution_time = (TimePolicy.now_utc() - self.start_time).total_seconds()
        self.execution_metrics["total_time"] = execution_time
        self.execution_metrics["agents_completed"] = len(self.completed_agents)
        self.execution_metrics["agents_failed"] = len(self.failed_agents)

        logger.info(f"Parallel execution completed in {execution_time:.2f}s")

        return self._generate_execution_status()

    async def _execute_agent(self, agent_id: str) -> tuple[str, str]:
        """
        Execute a single agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Tuple of (agent_id, status)
        """
        node = self.execution_graph[agent_id]
        node.status = "running"
        node.start_time = TimePolicy.now_utc()
        self.running_agents.add(agent_id)

        logger.info(f"Starting execution of agent {agent_id}")

        try:
            # Generate spawn command with enhanced context
            self._generate_spawn_command(node.agent_spec)

            # Execute the agent (simulate with async task)
            # In real implementation, this would spawn the actual Task agent
            await asyncio.sleep(0.1)  # Simulate agent execution

            # Track artifact creation
            artifact_path = self._generate_artifact_path(node.agent_spec)
            node.artifacts.append(artifact_path)

            # Update artifact registry
            self._register_artifact(agent_id, artifact_path)

            node.status = "completed"
            node.completion_time = TimePolicy.now_utc()

            logger.info(f"Agent {agent_id} completed successfully")
            return agent_id, "completed"

        except Exception as e:
            node.status = "failed"
            node.completion_time = TimePolicy.now_utc()
            logger.exception(f"Agent {agent_id} failed: {e}")
            return agent_id, "failed"

        finally:
            self.running_agents.discard(agent_id)

    def _handle_agent_completion(self, agent_id: str, status: str) -> None:
        """
        Handle agent completion and update dependent agents.

        Args:
            agent_id: Completed agent identifier
            status: Completion status
        """
        if status == "completed":
            self.completed_agents.add(agent_id)

            # Check dependents and add to ready queue
            node = self.execution_graph[agent_id]
            for dependent_id in node.dependents:
                if self._are_dependencies_met(dependent_id):
                    dependent_node = self.execution_graph[dependent_id]
                    if dependent_node.status == "pending":
                        dependent_node.status = "ready"
                        self.ready_queue.append(dependent_id)
                        logger.info(f"Agent {dependent_id} is now ready for execution")

        elif status == "failed":
            self.failed_agents.add(agent_id)

            # Handle failure propagation
            self._handle_failure_propagation(agent_id)

    def _handle_failure_propagation(self, failed_agent_id: str) -> None:
        """
        Handle failure propagation to dependent agents.

        Args:
            failed_agent_id: ID of the failed agent
        """
        node = self.execution_graph[failed_agent_id]

        # Mark all dependents as failed
        for dependent_id in node.dependents:
            if dependent_id not in self.completed_agents:
                self.failed_agents.add(dependent_id)
                self.execution_graph[dependent_id].status = "failed"
                logger.warning(f"Agent {dependent_id} failed due to dependency failure")

    def _generate_spawn_command(self, agent_spec: AgentSpec) -> str:
        """
        Generate spawn command for an agent with enhanced context.

        Args:
            agent_spec: Agent specification

        Returns:
            Spawn command string
        """
        # Get context from completed agents
        context_artifacts = []
        for dep in agent_spec.dependencies:
            if dep in self.completed_agents:
                dep_node = self.execution_graph[dep]
                context_artifacts.extend(dep_node.artifacts)

        # Enhanced context with dependency information
        enhanced_context = f"""
PARALLEL EXECUTION CONTEXT:
- Session ID: {self.session_id}
- Phase: {agent_spec.phase}
- Priority: {agent_spec.priority}
- Dependencies: {", ".join(agent_spec.dependencies) if agent_spec.dependencies else "None"}
- Available Context Artifacts: {len(context_artifacts)}

ORIGINAL TASK: {agent_spec.context}

COORDINATION INSTRUCTIONS:
- You are part of a parallel fan-out execution
- Your work may be executed simultaneously with other agents
- Check artifact registry for latest coordination state
- Coordinate through shared artifact registry
"""

        return f'uv run khive compose {agent_spec.role} -d {agent_spec.domain} -c "{enhanced_context}"'

    def _generate_artifact_path(self, agent_spec: AgentSpec) -> str:
        """Generate artifact path for an agent"""
        timestamp = TimePolicy.now_utc().strftime("%H%M%S")
        filename = (
            f"{agent_spec.phase}_{agent_spec.role}_{agent_spec.domain}_{timestamp}.md"
        )
        return str(self.session_dir / filename)

    def _register_artifact(self, agent_id: str, artifact_path: str) -> None:
        """Register artifact in the registry"""
        artifact_entry = {
            "agent_id": agent_id,
            "artifact_path": artifact_path,
            "created_at": TimePolicy.now_utc().isoformat(),
            "phase": self.execution_graph[agent_id].agent_spec.phase,
            "role": self.execution_graph[agent_id].agent_spec.role,
            "domain": self.execution_graph[agent_id].agent_spec.domain,
        }

        self.artifact_registry["artifacts"].append(artifact_entry)
        self.save_artifact_registry()

    def _generate_execution_status(self) -> dict[str, str]:
        """Generate execution status report"""
        status = {}

        for agent_id, node in self.execution_graph.items():
            status[agent_id] = {
                "status": node.status,
                "start_time": node.start_time.isoformat() if node.start_time else None,
                "completion_time": (
                    node.completion_time.isoformat() if node.completion_time else None
                ),
                "artifacts": node.artifacts,
                "role": node.agent_spec.role,
                "domain": node.agent_spec.domain,
            }

        return status

    def get_execution_metrics(self) -> dict[str, float]:
        """Get execution performance metrics"""
        metrics = self.execution_metrics.copy()

        if self.start_time:
            current_time = TimePolicy.now_utc()
            metrics["elapsed_time"] = (current_time - self.start_time).total_seconds()

        metrics["completion_rate"] = (
            len(self.completed_agents) / len(self.execution_graph)
            if self.execution_graph
            else 0
        )

        metrics["failure_rate"] = (
            len(self.failed_agents) / len(self.execution_graph)
            if self.execution_graph
            else 0
        )

        return metrics

    def get_ready_agents(self) -> list[str]:
        """Get list of agents ready for execution"""
        return list(self.ready_queue)

    def get_running_agents(self) -> list[str]:
        """Get list of currently running agents"""
        return list(self.running_agents)

    def get_completed_agents(self) -> list[str]:
        """Get list of completed agents"""
        return list(self.completed_agents)

    def get_failed_agents(self) -> list[str]:
        """Get list of failed agents"""
        return list(self.failed_agents)

    async def enforce_quality_gate(self, phase: str, quality_level: str) -> bool:
        """
        Enforce quality gate for a phase.

        Args:
            phase: Phase name
            quality_level: Quality level (basic, thorough, critical)

        Returns:
            True if quality gate passes, False otherwise
        """
        logger.info(f"Enforcing {quality_level} quality gate for phase {phase}")

        # Get all agents in the phase
        phase_agents = [
            agent_id
            for agent_id, node in self.execution_graph.items()
            if node.agent_spec.phase == phase
        ]

        # Check completion rate
        completed_in_phase = [
            agent_id for agent_id in phase_agents if agent_id in self.completed_agents
        ]

        completion_rate = (
            len(completed_in_phase) / len(phase_agents) if phase_agents else 0
        )

        # Quality gate thresholds
        thresholds = {
            "basic": 0.8,  # 80% completion
            "thorough": 0.9,  # 90% completion
            "critical": 0.95,  # 95% completion
        }

        required_rate = thresholds.get(quality_level, 0.9)

        if completion_rate >= required_rate:
            logger.info(f"Quality gate passed: {completion_rate:.1%} completion rate")
            return True
        logger.warning(
            f"Quality gate failed: {completion_rate:.1%} < {required_rate:.1%}"
        )
        return False

    def optimize_execution_order(self) -> None:
        """
        Optimize execution order based on priorities and dependencies.

        This method reorders the ready queue to prioritize:
        1. High-priority agents
        2. Agents with more dependents
        3. Agents with fewer dependencies
        """
        if not self.ready_queue:
            return

        # Convert to list for sorting
        ready_agents = list(self.ready_queue)
        self.ready_queue.clear()

        # Sort by priority (higher first), then by number of dependents (more first)
        ready_agents.sort(
            key=lambda agent_id: (
                -self.execution_graph[agent_id].agent_spec.priority,
                -len(self.execution_graph[agent_id].dependents),
                len(self.execution_graph[agent_id].agent_spec.dependencies),
            )
        )

        # Rebuild ready queue
        self.ready_queue.extend(ready_agents)

        logger.info(f"Optimized execution order for {len(ready_agents)} ready agents")
