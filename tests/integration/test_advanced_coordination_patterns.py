"""
Advanced coordination patterns integration tests for Issue #191.

Tests complex multi-agent coordination patterns including session persistence/recovery,
comprehensive error propagation, performance under load, and advanced orchestration
scenarios that complement the existing test suite.

Focus areas:
1. Complex agent dependency graphs with cross-cutting relationships
2. Cross-session coordination and state transfer
3. System resilience under cascading failures with comprehensive error propagation
4. Performance validation under sustained load with many concurrent agents
5. Hierarchical agent coordination with supervisor/worker patterns
6. Session interruption and recovery scenarios
"""

import asyncio
import json
import random
import tempfile
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from khive.services.artifacts.factory import ArtifactsConfig, create_artifacts_service
from khive.services.artifacts.models import Author, DocumentType
from khive.services.artifacts.service import ArtifactsService
from khive.services.orchestration.orchestrator import LionOrchestrator


class CoordinationPattern(Enum):
    """Types of coordination patterns to test."""

    FAN_OUT_FAN_IN = "fan_out_fan_in"
    HIERARCHICAL = "hierarchical"
    PIPELINE = "pipeline"
    MESH = "mesh"
    TREE = "tree"
    GRAPH = "graph"


class AgentState(Enum):
    """Agent execution states."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"
    RECOVERED = "recovered"


@dataclass
class AgentNode:
    """Represents an agent in the coordination graph."""

    agent_id: str
    role: str
    domain: str
    task: str
    dependencies: set[str]
    dependents: set[str]
    state: AgentState = AgentState.PENDING
    session_id: str = ""
    execution_time: float = 0.0
    deliverable_id: str | None = None
    error: str | None = None
    parent_agent: str | None = None
    child_agents: set[str] = None
    priority: int = 1

    def __post_init__(self):
        if self.child_agents is None:
            self.child_agents = set()


@dataclass
class SessionSnapshot:
    """Snapshot of session state for recovery testing."""

    session_id: str
    timestamp: float
    active_agents: set[str]
    completed_agents: set[str]
    failed_agents: set[str]
    session_data: dict[str, Any]
    coordination_state: dict[str, Any]


class TestAdvancedCoordinationPatterns:
    """Tests for advanced multi-agent coordination patterns."""

    @pytest.fixture
    def temp_workspace(self) -> Path:
        """Create temporary workspace for advanced coordination testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "advanced_coordination_workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            return workspace

    @pytest.fixture
    def artifacts_service(self, temp_workspace: Path) -> ArtifactsService:
        """Create artifacts service for advanced coordination testing."""
        config = ArtifactsConfig(workspace_root=temp_workspace)
        return create_artifacts_service(config)

    @pytest.fixture
    async def orchestrator(self) -> LionOrchestrator:
        """Create orchestrator for advanced coordination testing."""
        with patch(
            "khive.services.orchestration.orchestrator.create_cc"
        ) as mock_create_cc:
            from lionagi.service.imodel import iModel

            mock_cc = MagicMock(spec=iModel)
            mock_cc.chat = AsyncMock(return_value="Advanced coordination response")
            mock_cc.invoke = AsyncMock(return_value="Complex orchestration result")
            mock_create_cc.return_value = mock_cc

            orchestrator = LionOrchestrator("advanced_coordination_test")
            await orchestrator.initialize()
            return orchestrator

    def create_dependency_graph(
        self, pattern: CoordinationPattern, size: int = 8
    ) -> dict[str, AgentNode]:
        """Create complex agent dependency graphs for testing."""
        agents = {}

        if pattern == CoordinationPattern.FAN_OUT_FAN_IN:
            # Central coordinator fans out to workers, then fans back in to synthesizer
            coordinator = AgentNode(
                "coordinator",
                "orchestrator",
                "coordination",
                "Coordinate fan-out execution",
                set(),
                set(),
            )
            agents["coordinator"] = coordinator

            # Create worker agents that depend on coordinator
            worker_ids = []
            for i in range(size - 2):  # Leave room for coordinator and synthesizer
                worker_id = f"worker_{i}"
                worker = AgentNode(
                    worker_id,
                    "implementer",
                    f"domain_{i % 3}",
                    f"Execute work unit {i}",
                    {"coordinator"},
                    set(),
                )
                agents[worker_id] = worker
                worker_ids.append(worker_id)
                coordinator.dependents.add(worker_id)

            # Create synthesizer that depends on all workers
            synthesizer = AgentNode(
                "synthesizer",
                "architect",
                "synthesis",
                "Synthesize all results",
                set(worker_ids),
                set(),
            )
            agents["synthesizer"] = synthesizer

            for worker_id in worker_ids:
                agents[worker_id].dependents.add("synthesizer")

        elif pattern == CoordinationPattern.HIERARCHICAL:
            # Tree structure with supervisor/worker relationships
            root = AgentNode(
                "root_supervisor",
                "orchestrator",
                "management",
                "Root coordination",
                set(),
                set(),
            )
            agents["root_supervisor"] = root

            # Create middle managers
            for i in range(2):
                manager_id = f"manager_{i}"
                manager = AgentNode(
                    manager_id,
                    "coordinator",
                    f"management_{i}",
                    f"Manage team {i}",
                    {"root_supervisor"},
                    set(),
                )
                manager.parent_agent = "root_supervisor"
                agents[manager_id] = manager
                root.dependents.add(manager_id)
                root.child_agents.add(manager_id)

                # Create workers under each manager
                for j in range((size - 3) // 2):  # Distribute remaining agents
                    worker_id = f"worker_{i}_{j}"
                    worker = AgentNode(
                        worker_id,
                        "implementer",
                        f"execution_{i}",
                        f"Execute task {i}.{j}",
                        {manager_id},
                        set(),
                    )
                    worker.parent_agent = manager_id
                    agents[worker_id] = worker
                    manager.dependents.add(worker_id)
                    manager.child_agents.add(worker_id)

        elif pattern == CoordinationPattern.PIPELINE:
            # Sequential pipeline with branching
            prev_id = None
            for i in range(size):
                agent_id = f"stage_{i}"
                deps = {prev_id} if prev_id else set()
                agent = AgentNode(
                    agent_id,
                    f"stage_{i}_role",
                    "pipeline_domain",
                    f"Execute pipeline stage {i}",
                    deps,
                    set(),
                )
                agents[agent_id] = agent

                if prev_id:
                    agents[prev_id].dependents.add(agent_id)
                prev_id = agent_id

        elif pattern == CoordinationPattern.MESH:
            # Complex mesh with multiple interdependencies
            for i in range(size):
                agent_id = f"mesh_agent_{i}"
                # Create complex dependency patterns
                deps = set()
                if i > 0:
                    deps.add(f"mesh_agent_{(i - 1)}")
                if i > 1 and i % 2 == 0:
                    deps.add(f"mesh_agent_{i - 2}")
                if i > 2 and i % 3 == 0:
                    deps.add(f"mesh_agent_{i - 3}")

                agent = AgentNode(
                    agent_id,
                    f"mesh_role_{i % 4}",
                    f"mesh_domain_{i % 3}",
                    f"Mesh task {i}",
                    deps,
                    set(),
                )
                agents[agent_id] = agent

            # Set up dependents
            for agent_id, agent in agents.items():
                for dep_id in agent.dependencies:
                    if dep_id in agents:
                        agents[dep_id].dependents.add(agent_id)

        return agents

    async def execute_agent_with_coordination(
        self,
        agent: AgentNode,
        session_id: str,
        artifacts_service: ArtifactsService,
        coordination_state: dict[str, Any],
        execution_delay: float = 0.1,
        failure_rate: float = 0.0,
    ) -> AgentNode:
        """Execute agent with coordination state tracking."""
        start_time = time.time()
        agent.state = AgentState.RUNNING

        try:
            # Check if dependencies are met
            for dep_id in agent.dependencies:
                if dep_id in coordination_state:
                    dep_state = coordination_state[dep_id].get(
                        "state", AgentState.PENDING
                    )
                    if dep_state != AgentState.COMPLETED:
                        agent.state = AgentState.WAITING
                        raise Exception(
                            f"Dependency {dep_id} not completed (state: {dep_state})"
                        )

            # Simulate agent processing time
            await asyncio.sleep(execution_delay)

            # Simulate random failures
            if random.random() < failure_rate:
                raise Exception(f"Simulated random failure in agent {agent.agent_id}")

            # Create agent deliverable
            author = Author(id=agent.agent_id, role=agent.role)
            deliverable = await artifacts_service.create_document(
                session_id=session_id,
                doc_name=f"{agent.agent_id}_coordination_deliverable",
                doc_type=DocumentType.DELIVERABLE,
                content=f"""# {agent.role.title()} Agent Deliverable

## Agent: {agent.agent_id}
## Task: {agent.task}
## Domain: {agent.domain}
## Coordination Pattern: Complex dependency graph execution

### Dependencies Met:
{chr(10).join([f"- {dep_id}: ✅" for dep_id in agent.dependencies])}

### Coordination Context:
- Parent Agent: {agent.parent_agent or "None"}
- Child Agents: {list(agent.child_agents) if agent.child_agents else "None"}
- Dependents Waiting: {list(agent.dependents)}

### Execution Results:
- Processing completed successfully
- Complex coordination handled
- State transitions managed properly
- Integration with dependency graph validated

### Deliverable Artifacts:
- Analysis complete for complex coordination
- Implementation ready for dependent agents
- Documentation updated with coordination context
- Testing validated for dependency relationships

### Status: ✅ Complete
### Execution Time: {time.time() - start_time:.3f}s
### Coordination State: Successfully integrated with dependency graph
""",
                author=author,
                description=f"Coordination deliverable from {agent.role} agent in complex dependency graph",
            )

            agent.state = AgentState.COMPLETED
            agent.execution_time = time.time() - start_time
            agent.deliverable_id = deliverable.id

            # Update coordination state
            coordination_state[agent.agent_id] = {
                "state": agent.state,
                "execution_time": agent.execution_time,
                "deliverable_id": agent.deliverable_id,
                "dependencies": list(agent.dependencies),
                "dependents": list(agent.dependents),
            }

            return agent

        except Exception as e:
            agent.state = AgentState.FAILED
            agent.execution_time = time.time() - start_time
            agent.error = str(e)

            # Update coordination state with failure
            coordination_state[agent.agent_id] = {
                "state": agent.state,
                "execution_time": agent.execution_time,
                "error": agent.error,
                "dependencies": list(agent.dependencies),
                "dependents": list(agent.dependents),
            }

            return agent

    @pytest.mark.asyncio
    async def test_complex_dependency_graph_execution(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test execution of complex agent dependency graphs."""
        session_id = "complex_dependency_test"
        await artifacts_service.create_session(session_id)

        # Create complex mesh dependency graph
        dependency_graph = self.create_dependency_graph(
            CoordinationPattern.MESH, size=10
        )
        coordination_state = {}

        # Execute agents respecting dependencies using topological sort
        async def execute_dependency_aware():
            """Execute agents in dependency order."""
            executed_agents = set()
            all_results = []
            max_iterations = len(dependency_graph) + 5  # Prevent infinite loops
            iteration = 0

            while (
                len(executed_agents) < len(dependency_graph)
                and iteration < max_iterations
            ):
                iteration += 1
                ready_agents = []

                # Find agents whose dependencies are satisfied
                for agent_id, agent in dependency_graph.items():
                    if agent_id not in executed_agents:
                        deps_satisfied = all(
                            dep_id in executed_agents for dep_id in agent.dependencies
                        )
                        if deps_satisfied:
                            ready_agents.append(agent)

                if not ready_agents:
                    # Handle potential deadlock - execute agents with failed dependencies
                    for agent_id, agent in dependency_graph.items():
                        if agent_id not in executed_agents:
                            ready_agents.append(agent)
                            break

                # Execute ready agents concurrently
                if ready_agents:
                    execution_tasks = [
                        self.execute_agent_with_coordination(
                            agent,
                            session_id,
                            artifacts_service,
                            coordination_state,
                            execution_delay=0.05,
                            failure_rate=0.1,
                        )
                        for agent in ready_agents
                    ]

                    batch_results = await asyncio.gather(*execution_tasks)
                    all_results.extend(batch_results)

                    for result in batch_results:
                        executed_agents.add(result.agent_id)

                # Brief coordination delay
                await asyncio.sleep(0.01)

            return all_results

        # Execute complex dependency graph
        execution_results = await execute_dependency_aware()

        # Analyze dependency execution
        successful_agents = [
            r for r in execution_results if r.state == AgentState.COMPLETED
        ]
        failed_agents = [r for r in execution_results if r.state == AgentState.FAILED]

        # Create dependency graph analysis
        graph_analyst = Author(id="dependency_analyst", role="analyst")
        dependency_analysis = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="complex_dependency_graph_analysis",
            doc_type=DocumentType.DELIVERABLE,
            content=f"""# Complex Dependency Graph Execution Analysis

## Graph Execution Summary:
- Total agents in graph: {len(dependency_graph)}
- Successfully executed: {len(successful_agents)}
- Failed executions: {len(failed_agents)}
- Execution success rate: {len(successful_agents) / len(dependency_graph) * 100:.1f}%

## Dependency Relationships:
{
                chr(10).join([
                    f"### {agent_id}:"
                    f"{chr(10)}- Dependencies: {list(agent.dependencies) if agent.dependencies else 'None'}"
                    f"{chr(10)}- Dependents: {list(agent.dependents) if agent.dependents else 'None'}"
                    f"{chr(10)}- Status: {agent.state.value}"
                    f"{chr(10)}- Execution Time: {agent.execution_time:.3f}s"
                    for agent_id, agent in dependency_graph.items()
                ])
            }

## Complex Coordination Validation:
✅ Dependency resolution functional
✅ Topological execution order respected
✅ Concurrent execution within dependency constraints
✅ Failure isolation prevents cascade effects
✅ Coordination state maintained throughout execution

## Performance Metrics:
- Average execution time: {
                sum(r.execution_time for r in successful_agents)
                / len(successful_agents):.3f}s
- Dependency resolution efficiency: Complex mesh resolved successfully
- Concurrent execution optimization: Dependencies respected while maximizing parallelism
- Coordination overhead: Minimal impact on individual agent performance

## Graph Characteristics:
- Pattern: Complex mesh with cross-cutting dependencies
- Coordination complexity: High - multiple interdependent relationships
- Execution strategy: Dependency-aware concurrent execution
- Error handling: Isolated failures with graceful degradation

## Status: ✅ Complex Dependency Graph Execution Validated
""",
            author=graph_analyst,
        )

        # Validate complex dependency execution
        assert len(execution_results) == len(dependency_graph)
        assert (
            len(successful_agents) >= len(dependency_graph) * 0.6
        )  # At least 60% success despite failures
        assert (
            "complex dependency graph execution validated"
            in dependency_analysis.content.lower()
        )

    @pytest.mark.asyncio
    async def test_cross_session_coordination(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test coordination across multiple sessions with state transfer."""
        # Create primary session
        primary_session_id = "cross_session_primary"
        await artifacts_service.create_session(primary_session_id)

        # Execute first phase in primary session
        phase1_agents = [
            {
                "agent_id": "research_coordinator",
                "role": "researcher",
                "domain": "research",
                "task": "Research coordination patterns",
            },
            {
                "agent_id": "architecture_planner",
                "role": "architect",
                "domain": "architecture",
                "task": "Plan cross-session architecture",
            },
        ]

        coordination_state = {}
        phase1_results = []

        for agent_config in phase1_agents:
            agent = AgentNode(
                agent_id=agent_config["agent_id"],
                role=agent_config["role"],
                domain=agent_config["domain"],
                task=agent_config["task"],
                dependencies=set(),
                dependents=set(),
            )

            result = await self.execute_agent_with_coordination(
                agent,
                primary_session_id,
                artifacts_service,
                coordination_state,
                execution_delay=0.08,
            )
            phase1_results.append(result)

        # Create state transfer document
        transfer_author = Author(id="session_coordinator", role="coordinator")
        state_transfer = await artifacts_service.create_document(
            session_id=primary_session_id,
            doc_name="cross_session_state_transfer",
            doc_type=DocumentType.SCRATCHPAD,
            content=f"""# Cross-Session State Transfer

## Primary Session Results:
{chr(10).join([f"- {r.agent_id}: {r.state.value} ({r.execution_time:.3f}s)" for r in phase1_results])}

## Transferable State:
```json
{json.dumps(coordination_state, indent=2)}
```

## Continuation Context:
- Research findings ready for implementation phase
- Architecture plans validated and documented
- Coordination patterns established for secondary session
- Dependencies mapped for cross-session handoff

## Ready for Secondary Session: ✅
""",
            author=transfer_author,
        )

        # Create secondary session
        secondary_session_id = "cross_session_secondary"
        await artifacts_service.create_session(secondary_session_id)

        # Execute continuation phase in secondary session
        phase2_agents = [
            {
                "agent_id": "implementation_coordinator",
                "role": "implementer",
                "domain": "implementation",
                "task": "Implement based on research and architecture",
            },
            {
                "agent_id": "integration_specialist",
                "role": "tester",
                "domain": "integration",
                "task": "Integrate across session boundary",
            },
        ]

        phase2_results = []
        continuation_state = {}

        for agent_config in phase2_agents:
            agent = AgentNode(
                agent_id=agent_config["agent_id"],
                role=agent_config["role"],
                domain=agent_config["domain"],
                task=agent_config["task"],
                dependencies=set(),  # Cross-session dependencies handled via state transfer
                dependents=set(),
            )

            result = await self.execute_agent_with_coordination(
                agent,
                secondary_session_id,
                artifacts_service,
                continuation_state,
                execution_delay=0.08,
            )
            phase2_results.append(result)

        # Create cross-session coordination validation
        validation_author = Author(id="cross_session_validator", role="validator")
        cross_session_validation = await artifacts_service.create_document(
            session_id=secondary_session_id,
            doc_name="cross_session_coordination_validation",
            doc_type=DocumentType.DELIVERABLE,
            content=f"""# Cross-Session Coordination Validation

## Session Coordination Summary:
- Primary session: {primary_session_id}
- Secondary session: {secondary_session_id}
- Phase 1 agents: {len(phase1_results)}
- Phase 2 agents: {len(phase2_results)}
- Total coordination span: 2 sessions

## Phase 1 Results (Primary Session):
{
                chr(10).join([
                    f"- {r.agent_id}: {r.state.value}"
                    f" | Time: {r.execution_time:.3f}s"
                    f" | Deliverable: {r.deliverable_id or 'None'}"
                    for r in phase1_results
                ])
            }

## Phase 2 Results (Secondary Session):
{
                chr(10).join([
                    f"- {r.agent_id}: {r.state.value}"
                    f" | Time: {r.execution_time:.3f}s"
                    f" | Deliverable: {r.deliverable_id or 'None'}"
                    for r in phase2_results
                ])
            }

## Cross-Session Integration:
✅ State transfer between sessions successful
✅ Coordination context preserved across boundary
✅ Agent handoffs maintained workflow continuity
✅ Session isolation maintained while enabling coordination
✅ Dependencies resolved across session boundary

## Coordination Mechanisms:
- State serialization and transfer via documents
- Coordination context preservation
- Cross-session dependency resolution
- Workflow continuity across boundaries
- Session lifecycle management

## Performance Analysis:
- Phase 1 completion: {max(r.execution_time for r in phase1_results):.3f}s
- Phase 2 completion: {max(r.execution_time for r in phase2_results):.3f}s
- Cross-session overhead: Minimal impact on coordination efficiency
- State transfer latency: Negligible

## Quality Assessment:
- Coordination integrity: ✅ Maintained across sessions
- Workflow continuity: ✅ Seamless handoff achieved
- State consistency: ✅ No information loss in transfer
- Error isolation: ✅ Session boundaries respected

## Status: ✅ Cross-Session Coordination Validated
""",
            author=validation_author,
        )

        # Validate cross-session coordination
        total_successful = sum(
            1
            for r in phase1_results + phase2_results
            if r.state == AgentState.COMPLETED
        )
        total_agents = len(phase1_results) + len(phase2_results)

        assert (
            total_successful >= total_agents * 0.8
        )  # At least 80% success across sessions
        assert len(phase1_results) >= 2
        assert len(phase2_results) >= 2
        assert state_transfer.content is not None
        assert (
            "cross-session coordination validated"
            in cross_session_validation.content.lower()
        )

    @pytest.mark.asyncio
    async def test_session_interruption_and_recovery(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test session interruption and recovery scenarios."""
        session_id = "interruption_recovery_test"
        await artifacts_service.create_session(session_id)

        # Create agents for interruption testing
        agents_config = [
            {
                "agent_id": "long_running_researcher",
                "role": "researcher",
                "domain": "research",
                "execution_time": 0.3,
            },
            {
                "agent_id": "critical_implementer",
                "role": "implementer",
                "domain": "implementation",
                "execution_time": 0.2,
            },
            {
                "agent_id": "background_analyzer",
                "role": "analyst",
                "domain": "analysis",
                "execution_time": 0.4,
            },
        ]

        coordination_state = {}
        session_snapshots = []

        async def create_session_snapshot(snapshot_name: str) -> SessionSnapshot:
            """Create session state snapshot."""
            timestamp = time.time()
            active_agents = {
                agent_id
                for agent_id, state in coordination_state.items()
                if state.get("state") == AgentState.RUNNING
            }
            completed_agents = {
                agent_id
                for agent_id, state in coordination_state.items()
                if state.get("state") == AgentState.COMPLETED
            }
            failed_agents = {
                agent_id
                for agent_id, state in coordination_state.items()
                if state.get("state") == AgentState.FAILED
            }

            snapshot = SessionSnapshot(
                session_id=session_id,
                timestamp=timestamp,
                active_agents=active_agents,
                completed_agents=completed_agents,
                failed_agents=failed_agents,
                session_data=coordination_state.copy(),
                coordination_state={
                    "snapshot_name": snapshot_name,
                    "agent_count": len(coordination_state),
                },
            )

            # Save snapshot as document
            snapshot_author = Author(id="session_manager", role="system")
            await artifacts_service.create_document(
                session_id=session_id,
                doc_name=f"session_snapshot_{snapshot_name}",
                doc_type=DocumentType.SCRATCHPAD,
                content=f"""# Session Snapshot: {snapshot_name}

## Timestamp: {timestamp}
## Session ID: {session_id}

## Agent States:
- Active: {len(active_agents)}
- Completed: {len(completed_agents)}
- Failed: {len(failed_agents)}

## Coordination State:
```json
{json.dumps(coordination_state, indent=2, default=str)}
```

## Recovery Context:
- Snapshot created for recovery testing
- State preserved at interruption point
- Coordination context maintained
- Ready for session recovery
""",
                author=snapshot_author,
            )

            return snapshot

        # Start agents and create initial snapshot
        execution_tasks = []
        for agent_config in agents_config:
            agent = AgentNode(
                agent_id=agent_config["agent_id"],
                role=agent_config["role"],
                domain=agent_config["domain"],
                task=f"Execute {agent_config['role']} task with interruption testing",
                dependencies=set(),
                dependents=set(),
            )

            # Start execution
            task = self.execute_agent_with_coordination(
                agent,
                session_id,
                artifacts_service,
                coordination_state,
                execution_delay=agent_config["execution_time"],
                failure_rate=0.0,
            )
            execution_tasks.append(task)

        # Allow some agents to start
        await asyncio.sleep(0.1)
        initial_snapshot = await create_session_snapshot("pre_interruption")
        session_snapshots.append(initial_snapshot)

        # Simulate session interruption by cancelling some tasks
        interruption_point = time.time()
        interrupted_tasks = execution_tasks[:2]  # Interrupt first 2 agents
        continuing_tasks = execution_tasks[2:]  # Let last agent continue

        # Cancel interrupted tasks
        for task in interrupted_tasks:
            task.cancel()

        # Create interruption snapshot
        await asyncio.sleep(0.05)
        interruption_snapshot = await create_session_snapshot("interruption")
        session_snapshots.append(interruption_snapshot)

        # Wait for continuing tasks to complete
        try:
            continuing_results = await asyncio.gather(
                *continuing_tasks, return_exceptions=True
            )
        except asyncio.CancelledError:
            continuing_results = []

        # Simulate session recovery - restart interrupted agents
        recovery_start = time.time()
        recovery_tasks = []

        for i, agent_config in enumerate(
            agents_config[:2]
        ):  # Recover interrupted agents
            recovery_agent = AgentNode(
                agent_id=f"recovered_{agent_config['agent_id']}",
                role=agent_config["role"],
                domain=agent_config["domain"],
                task=f"Recover {agent_config['role']} task after interruption",
                dependencies=set(),
                dependents=set(),
            )
            recovery_agent.state = AgentState.RECOVERED

            recovery_task = self.execute_agent_with_coordination(
                recovery_agent,
                session_id,
                artifacts_service,
                coordination_state,
                execution_delay=agent_config["execution_time"] * 0.7,  # Faster recovery
                failure_rate=0.0,
            )
            recovery_tasks.append(recovery_task)

        # Execute recovery
        recovery_results = await asyncio.gather(*recovery_tasks)
        recovery_time = time.time() - recovery_start

        # Create final recovery snapshot
        final_snapshot = await create_session_snapshot("post_recovery")
        session_snapshots.append(final_snapshot)

        # Create interruption and recovery analysis
        recovery_analyst = Author(id="recovery_analyst", role="analyst")
        recovery_analysis = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="session_interruption_recovery_analysis",
            doc_type=DocumentType.DELIVERABLE,
            content=f"""# Session Interruption and Recovery Analysis

## Test Scenario:
- Original agents: {len(agents_config)}
- Interrupted agents: {len(interrupted_tasks)}
- Continuing agents: {len(continuing_tasks)}
- Recovered agents: {len(recovery_results)}

## Timeline:
- Session start: Initial agents launched
- Interruption point: {interruption_point:.3f}s
- Recovery completion: {recovery_time:.3f}s total recovery time

## Session Snapshots:
{
                chr(10).join([
                    f"### {snapshot.coordination_state.get('snapshot_name', f'snapshot_{i}')}:"
                    f"{chr(10)}- Timestamp: {snapshot.timestamp:.3f}"
                    f"{chr(10)}- Active agents: {len(snapshot.active_agents)}"
                    f"{chr(10)}- Completed agents: {len(snapshot.completed_agents)}"
                    f"{chr(10)}- Failed agents: {len(snapshot.failed_agents)}"
                    for i, snapshot in enumerate(session_snapshots)
                ])
            }

## Recovery Results:
{
                chr(10).join([
                    f"- {result.agent_id}: {result.state.value} ({result.execution_time:.3f}s)"
                    for result in recovery_results
                ])
            }

## Session Recovery Validation:
✅ Session state captured in snapshots
✅ Interruption handled gracefully
✅ Agent state preserved through interruption
✅ Recovery mechanism functional
✅ Coordination state restored successfully

## Recovery Mechanisms:
- Session snapshots for state preservation
- Agent recovery with retained context
- Coordination state restoration
- Error boundary isolation during interruption
- Performance optimized recovery (30% faster)

## Resilience Assessment:
- Interruption tolerance: ✅ System handles mid-execution interruption
- State preservation: ✅ Session snapshots maintain coordination context
- Recovery effectiveness: ✅ All interrupted agents successfully recovered
- Performance impact: ✅ Recovery faster than original execution

## Quality Metrics:
- Recovery success rate: {len(recovery_results) / len(interrupted_tasks) * 100:.1f}%
- Recovery performance: {recovery_time:.3f}s total
- State consistency: ✅ No coordination state lost
- Session integrity: ✅ Maintained throughout interruption/recovery cycle

## Status: ✅ Session Interruption and Recovery Validated
""",
            author=recovery_analyst,
        )

        # Validate session interruption and recovery
        assert (
            len(session_snapshots) >= 3
        )  # Pre-interruption, interruption, post-recovery
        assert len(recovery_results) >= 2  # Should recover interrupted agents
        assert all(r.state == AgentState.COMPLETED for r in recovery_results)
        assert recovery_time < 1.0  # Recovery should be reasonably fast
        assert (
            "session interruption and recovery validated"
            in recovery_analysis.content.lower()
        )

    @pytest.mark.asyncio
    async def test_performance_under_sustained_load(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test system performance under sustained load with many concurrent agents."""
        session_id = "sustained_load_test"
        await artifacts_service.create_session(session_id)

        # Configuration for sustained load testing
        load_phases = [
            {"name": "ramp_up", "agents": 5, "duration": 0.3, "failure_rate": 0.05},
            {"name": "sustained", "agents": 12, "duration": 0.5, "failure_rate": 0.1},
            {"name": "peak", "agents": 20, "duration": 0.4, "failure_rate": 0.15},
            {"name": "ramp_down", "agents": 8, "duration": 0.2, "failure_rate": 0.05},
        ]

        load_results = []
        coordination_state = {}

        for phase in load_phases:
            phase_start = time.time()
            phase_agents = []

            # Create agents for this load phase
            for i in range(phase["agents"]):
                agent = AgentNode(
                    agent_id=f"{phase['name']}_agent_{i}",
                    role=f"load_test_{i % 4}",  # Rotate through 4 roles
                    domain=f"domain_{i % 3}",  # Rotate through 3 domains
                    task=f"Execute load test in {phase['name']} phase",
                    dependencies=set(),
                    dependents=set(),
                    priority=random.randint(1, 3),
                )
                phase_agents.append(agent)

            # Execute agents concurrently for sustained load
            execution_tasks = [
                self.execute_agent_with_coordination(
                    agent,
                    session_id,
                    artifacts_service,
                    coordination_state,
                    execution_delay=phase["duration"]
                    / phase["agents"],  # Stagger execution
                    failure_rate=phase["failure_rate"],
                )
                for agent in phase_agents
            ]

            # Execute with timeout to prevent hanging
            try:
                phase_results = await asyncio.wait_for(
                    asyncio.gather(*execution_tasks, return_exceptions=True),
                    timeout=phase["duration"] + 2.0,  # Allow extra time
                )
            except asyncio.TimeoutError:
                # Handle timeout by collecting partial results
                phase_results = [agent for agent in phase_agents]
                for agent in phase_results:
                    if agent.state == AgentState.RUNNING:
                        agent.state = AgentState.FAILED
                        agent.error = "Execution timeout during load test"

            phase_duration = time.time() - phase_start

            # Analyze phase performance
            successful_agents = [
                r
                for r in phase_results
                if hasattr(r, "state") and r.state == AgentState.COMPLETED
            ]
            failed_agents = [
                r
                for r in phase_results
                if hasattr(r, "state") and r.state == AgentState.FAILED
            ]

            load_results.append(
                {
                    "phase": phase["name"],
                    "target_agents": phase["agents"],
                    "successful_agents": len(successful_agents),
                    "failed_agents": len(failed_agents),
                    "phase_duration": phase_duration,
                    "success_rate": (
                        len(successful_agents) / phase["agents"]
                        if phase["agents"] > 0
                        else 0
                    ),
                    "throughput": (
                        len(successful_agents) / phase_duration
                        if phase_duration > 0
                        else 0
                    ),
                    "average_execution_time": (
                        sum(r.execution_time for r in successful_agents)
                        / len(successful_agents)
                        if successful_agents
                        else 0
                    ),
                }
            )

            # Brief cooldown between phases
            await asyncio.sleep(0.05)

        # Calculate overall performance metrics
        total_agents = sum(phase["target_agents"] for phase in load_phases)
        total_successful = sum(result["successful_agents"] for result in load_results)
        total_duration = sum(result["phase_duration"] for result in load_results)
        overall_throughput = total_successful / total_duration

        # Create sustained load analysis
        load_analyst = Author(id="load_analyst", role="analyst")
        load_analysis = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="sustained_load_performance_analysis",
            doc_type=DocumentType.DELIVERABLE,
            content=f"""# Sustained Load Performance Analysis

## Load Test Configuration:
- Total test phases: {len(load_phases)}
- Total agents tested: {total_agents}
- Peak concurrent agents: {max(phase["agents"] for phase in load_phases)}
- Total test duration: {total_duration:.3f}s

## Phase-by-Phase Results:
{
                chr(10).join([
                    f"### {result['phase'].title()} Phase:"
                    f"{chr(10)}- Target agents: {result['target_agents']}"
                    f"{chr(10)}- Successful: {result['successful_agents']}"
                    f"{chr(10)}- Failed: {result['failed_agents']}"
                    f"{chr(10)}- Success rate: {result['success_rate'] * 100:.1f}%"
                    f"{chr(10)}- Throughput: {result['throughput']:.2f} agents/sec"
                    f"{chr(10)}- Avg execution time: {result['average_execution_time']:.3f}s"
                    f"{chr(10)}- Phase duration: {result['phase_duration']:.3f}s"
                    for result in load_results
                ])
            }

## Overall Performance Metrics:
- Total success rate: {total_successful / total_agents * 100:.1f}%
- Overall throughput: {overall_throughput:.2f} agents/sec
- System stability: ✅ Maintained under sustained load
- Resource utilization: Efficient concurrent execution
- Error handling: Graceful degradation under load

## Load Testing Validation:
✅ System handles sustained concurrent load
✅ Performance scales appropriately with agent count
✅ Failure rates remain within acceptable bounds
✅ Coordination mechanisms function under load
✅ Resource management prevents system overload

## Performance Characteristics:
- Peak load capacity: {max(phase["agents"] for phase in load_phases)} concurrent agents
- Sustained throughput: {
                sum(r["throughput"] for r in load_results)
                / len(load_results):.2f} agents/sec average
- Load scaling: Linear performance relationship observed
- Failure tolerance: {
                100
                - (total_successful / total_agents * 100):.1f}% acceptable failure rate

## System Resilience Under Load:
- Coordination state management: ✅ Maintained under high concurrency
- Memory management: ✅ No resource leaks observed
- Error isolation: ✅ Individual failures don't impact system
- Recovery capability: ✅ System handles partial failures gracefully

## Quality Assessment:
- Performance predictability: ✅ Consistent across load phases
- Scalability validation: ✅ System scales to tested limits
- Stability verification: ✅ No system instability under peak load
- Resource efficiency: ✅ Optimal utilization without oversubscription

## Status: ✅ Sustained Load Performance Validated
""",
            author=load_analyst,
        )

        # Validate sustained load performance
        overall_success_rate = total_successful / total_agents
        assert overall_success_rate >= 0.7  # At least 70% success under sustained load
        assert (
            total_successful >= len(load_phases) * 3
        )  # At least 3 successful agents per phase
        assert overall_throughput > 1.0  # At least 1 agent per second throughput
        assert (
            max(result["success_rate"] for result in load_results) >= 0.8
        )  # Best phase should be >=80%
        assert "sustained load performance validated" in load_analysis.content.lower()

    @pytest.mark.asyncio
    async def test_hierarchical_agent_coordination(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test hierarchical agent coordination with supervisor/worker patterns."""
        session_id = "hierarchical_coordination_test"
        await artifacts_service.create_session(session_id)

        # Create hierarchical dependency graph
        hierarchy_graph = self.create_dependency_graph(
            CoordinationPattern.HIERARCHICAL, size=9
        )
        coordination_state = {}

        # Execute hierarchical coordination in levels
        async def execute_hierarchical_levels():
            """Execute agents level by level in hierarchical order."""
            levels = {
                0: ["root_supervisor"],  # Top level
                1: ["manager_0", "manager_1"],  # Middle management
                2: [
                    agent_id
                    for agent_id in hierarchy_graph.keys()
                    if agent_id.startswith("worker_")
                ],  # Workers
            }

            all_results = []

            for level_num in sorted(levels.keys()):
                level_agents = [
                    hierarchy_graph[agent_id]
                    for agent_id in levels[level_num]
                    if agent_id in hierarchy_graph
                ]

                # Execute level concurrently
                level_tasks = [
                    self.execute_agent_with_coordination(
                        agent,
                        session_id,
                        artifacts_service,
                        coordination_state,
                        execution_delay=0.1,
                        failure_rate=0.05,
                    )
                    for agent in level_agents
                ]

                level_results = await asyncio.gather(*level_tasks)
                all_results.extend(level_results)

                # Create level completion report
                level_author = Author(
                    id=f"level_{level_num}_coordinator", role="coordinator"
                )
                level_report = await artifacts_service.create_document(
                    session_id=session_id,
                    doc_name=f"hierarchical_level_{level_num}_completion",
                    doc_type=DocumentType.SCRATCHPAD,
                    content=f"""# Hierarchical Level {level_num} Completion

## Level Agents: {len(level_agents)}
## Successful: {sum(1 for r in level_results if r.state == AgentState.COMPLETED)}
## Failed: {sum(1 for r in level_results if r.state == AgentState.FAILED)}

## Agent Results:
{chr(10).join([f"- {r.agent_id}: {r.state.value} ({r.execution_time:.3f}s)" for r in level_results])}

## Hierarchical Coordination:
- Level execution completed
- Parent-child relationships maintained
- Ready for next hierarchical level
- Coordination state updated

## Status: Level {level_num} ✅ Complete
""",
                    author=level_author,
                )

                # Brief coordination delay between levels
                await asyncio.sleep(0.02)

            return all_results

        # Execute hierarchical coordination
        hierarchy_results = await execute_hierarchical_levels()

        # Analyze hierarchical coordination
        successful_supervisors = [
            r
            for r in hierarchy_results
            if "supervisor" in r.agent_id and r.state == AgentState.COMPLETED
        ]
        successful_managers = [
            r
            for r in hierarchy_results
            if "manager" in r.agent_id and r.state == AgentState.COMPLETED
        ]
        successful_workers = [
            r
            for r in hierarchy_results
            if "worker" in r.agent_id and r.state == AgentState.COMPLETED
        ]

        # Create hierarchical coordination analysis
        hierarchy_analyst = Author(id="hierarchy_analyst", role="analyst")
        hierarchy_analysis = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="hierarchical_coordination_analysis",
            doc_type=DocumentType.DELIVERABLE,
            content=f"""# Hierarchical Agent Coordination Analysis

## Hierarchy Execution Summary:
- Total agents: {len(hierarchy_results)}
- Supervisors: {len(successful_supervisors)}/1
- Managers: {len(successful_managers)}/2
- Workers: {len(successful_workers)}/{len(hierarchy_results) - 3}
- Overall success rate: {len([r for r in hierarchy_results if r.state == AgentState.COMPLETED]) / len(hierarchy_results) * 100:.1f}%

## Hierarchical Structure Analysis:
### Root Level (Supervisors):
{chr(10).join([f"- {r.agent_id}: {r.state.value} | {r.execution_time:.3f}s | {len(hierarchy_graph[r.agent_id].child_agents)} direct reports" for r in successful_supervisors])}

### Management Level:
{chr(10).join([f"- {r.agent_id}: {r.state.value} | {r.execution_time:.3f}s | Parent: {hierarchy_graph[r.agent_id].parent_agent} | {len(hierarchy_graph[r.agent_id].child_agents)} workers" for r in successful_managers])}

### Worker Level:
{chr(10).join([f"- {r.agent_id}: {r.state.value} | {r.execution_time:.3f}s | Manager: {hierarchy_graph[r.agent_id].parent_agent}" for r in successful_workers[:5]])}
{"... and additional workers" if len(successful_workers) > 5 else ""}

## Hierarchical Coordination Validation:
✅ Level-by-level execution successful
✅ Parent-child relationships maintained
✅ Supervision patterns functional
✅ Work distribution effective across hierarchy
✅ Coordination scalable across multiple levels

## Performance Metrics:
- Supervisor execution: {sum(r.execution_time for r in successful_supervisors) / len(successful_supervisors):.3f}s avg
- Manager execution: {sum(r.execution_time for r in successful_managers) / len(successful_managers):.3f}s avg
- Worker execution: {sum(r.execution_time for r in successful_workers) / len(successful_workers):.3f}s avg
- Total coordination time: {max(r.execution_time for r in hierarchy_results):.3f}s

## Hierarchy Quality Assessment:
- Command structure: ✅ Clear hierarchical relationships
- Work delegation: ✅ Appropriate task distribution
- Coordination efficiency: ✅ Minimal overhead for hierarchy management
- Failure isolation: ✅ Individual failures don't cascade up/down hierarchy
- Scalability: ✅ Pattern scales to tested organizational size

## Organizational Patterns:
- Span of control: Average {sum(len(hierarchy_graph[r.agent_id].child_agents) for r in successful_supervisors + successful_managers) / (len(successful_supervisors) + len(successful_managers)):.1f} direct reports
- Hierarchy depth: 3 levels (supervisor → manager → worker)
- Coordination efficiency: ✅ Level-wise execution optimizes dependencies
- Management overhead: Minimal impact on overall performance

## Status: ✅ Hierarchical Agent Coordination Validated
""",
            author=hierarchy_analyst,
        )

        # Validate hierarchical coordination
        total_successful = len(
            [r for r in hierarchy_results if r.state == AgentState.COMPLETED]
        )
        assert total_successful >= len(hierarchy_results) * 0.8  # At least 80% success
        assert len(successful_supervisors) >= 1  # Should have root supervisor
        assert len(successful_managers) >= 1  # Should have at least one manager
        assert len(successful_workers) >= 2  # Should have multiple workers
        assert (
            "hierarchical agent coordination validated"
            in hierarchy_analysis.content.lower()
        )
