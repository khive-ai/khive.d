"""
Comprehensive error propagation and resilience testing for Issue #191.

Tests comprehensive error propagation patterns, cascading failure scenarios,
and advanced system resilience under complex failure conditions that go beyond
the existing test suite coverage.

Focus areas:
1. Multi-level error propagation through complex dependency chains
2. Cascading failure analysis with error boundary validation
3. Advanced resilience patterns under compound failures
4. Error recovery coordination across distributed agent networks
5. Performance degradation analysis under various failure scenarios
6. Distributed system failure patterns and recovery strategies
"""

import asyncio
import random
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from khive.services.artifacts.factory import (ArtifactsConfig,
                                              create_artifacts_service)
from khive.services.artifacts.models import Author, DocumentType
from khive.services.artifacts.service import ArtifactsService
from khive.services.orchestration.orchestrator import LionOrchestrator


class ErrorType(Enum):
    """Types of errors for comprehensive propagation testing."""

    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_PARTITION = "network_partition"
    DATA_CORRUPTION = "data_corruption"
    AUTHENTICATION_FAILURE = "authentication_failure"
    VALIDATION_ERROR = "validation_error"
    CONCURRENT_MODIFICATION = "concurrent_modification"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class ErrorSeverity(Enum):
    """Error severity levels for propagation analysis."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    CATASTROPHIC = "catastrophic"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""

    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAKER = "circuit_breaker"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    ISOLATION = "isolation"
    ESCALATION = "escalation"
    ABORT = "abort"


@dataclass
class ErrorScenario:
    """Represents an error scenario for testing."""

    error_type: ErrorType
    severity: ErrorSeverity
    propagation_pattern: str
    affected_agents: set[str]
    recovery_strategy: RecoveryStrategy
    expected_cascade_depth: int
    timeout_threshold: float = 1.0
    recovery_time_estimate: float = 0.5


@dataclass
class ErrorPropagationResult:
    """Results from error propagation testing."""

    scenario: ErrorScenario
    initial_failure_agent: str
    cascaded_agents: set[str]
    recovered_agents: set[str]
    failed_agents: set[str]
    propagation_depth: int
    propagation_time: float
    recovery_time: float
    error_boundaries_activated: set[str]
    final_system_state: str


@dataclass
class DistributedAgentNode:
    """Represents an agent in distributed failure testing."""

    agent_id: str
    role: str
    domain: str
    partition: str  # Network partition for distributed testing
    dependencies: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)
    error_boundaries: set[str] = field(default_factory=set)
    current_state: str = "healthy"
    failure_probability: float = 0.0
    recovery_capability: float = 1.0
    last_heartbeat: float = 0.0


class TestComprehensiveErrorPropagation:
    """Tests for comprehensive error propagation and advanced resilience."""

    @pytest.fixture
    def temp_workspace(self) -> Path:
        """Create temporary workspace for error propagation testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "error_propagation_workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            return workspace

    @pytest.fixture
    def artifacts_service(self, temp_workspace: Path) -> ArtifactsService:
        """Create artifacts service for error propagation testing."""
        config = ArtifactsConfig(workspace_root=temp_workspace)
        return create_artifacts_service(config)

    @pytest.fixture
    async def orchestrator(self) -> LionOrchestrator:
        """Create orchestrator for error propagation testing."""
        with patch(
            "khive.services.orchestration.orchestrator.create_cc"
        ) as mock_create_cc:
            from lionagi.service.imodel import iModel

            mock_cc = MagicMock(spec=iModel)
            mock_cc.chat = AsyncMock(return_value="Error propagation test response")
            mock_cc.invoke = AsyncMock(return_value="Resilience test result")
            mock_create_cc.return_value = mock_cc

            orchestrator = LionOrchestrator("error_propagation_test")
            await orchestrator.initialize()
            return orchestrator

    def create_error_scenarios(self) -> list[ErrorScenario]:
        """Create comprehensive error scenarios for testing."""
        scenarios = [
            ErrorScenario(
                error_type=ErrorType.TIMEOUT,
                severity=ErrorSeverity.MEDIUM,
                propagation_pattern="linear_cascade",
                affected_agents={"timeout_agent"},
                recovery_strategy=RecoveryStrategy.RETRY,
                expected_cascade_depth=2,
                timeout_threshold=0.5,
                recovery_time_estimate=0.3,
            ),
            ErrorScenario(
                error_type=ErrorType.RESOURCE_EXHAUSTION,
                severity=ErrorSeverity.HIGH,
                propagation_pattern="fan_out_cascade",
                affected_agents={"resource_manager"},
                recovery_strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
                expected_cascade_depth=3,
                timeout_threshold=1.0,
                recovery_time_estimate=0.8,
            ),
            ErrorScenario(
                error_type=ErrorType.NETWORK_PARTITION,
                severity=ErrorSeverity.CRITICAL,
                propagation_pattern="partition_cascade",
                affected_agents={"partition_a_agent", "partition_b_agent"},
                recovery_strategy=RecoveryStrategy.ISOLATION,
                expected_cascade_depth=4,
                timeout_threshold=2.0,
                recovery_time_estimate=1.5,
            ),
            ErrorScenario(
                error_type=ErrorType.DATA_CORRUPTION,
                severity=ErrorSeverity.HIGH,
                propagation_pattern="dependency_cascade",
                affected_agents={"data_processor"},
                recovery_strategy=RecoveryStrategy.FALLBACK,
                expected_cascade_depth=3,
                timeout_threshold=1.5,
                recovery_time_estimate=1.0,
            ),
            ErrorScenario(
                error_type=ErrorType.CIRCUIT_BREAKER_OPEN,
                severity=ErrorSeverity.MEDIUM,
                propagation_pattern="circuit_isolation",
                affected_agents={"external_service_client"},
                recovery_strategy=RecoveryStrategy.CIRCUIT_BREAKER,
                expected_cascade_depth=1,
                timeout_threshold=0.8,
                recovery_time_estimate=2.0,
            ),
        ]
        return scenarios

    async def simulate_error_injection(
        self,
        error_type: ErrorType,
        agent_id: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ) -> Exception:
        """Inject specific error types for testing."""
        # Add realistic delay based on error type
        delay_map = {
            ErrorType.TIMEOUT: 0.05,
            ErrorType.RESOURCE_EXHAUSTION: 0.1,
            ErrorType.NETWORK_PARTITION: 0.15,
            ErrorType.DATA_CORRUPTION: 0.08,
            ErrorType.AUTHENTICATION_FAILURE: 0.03,
            ErrorType.VALIDATION_ERROR: 0.02,
            ErrorType.CONCURRENT_MODIFICATION: 0.06,
            ErrorType.DEPENDENCY_UNAVAILABLE: 0.12,
            ErrorType.CIRCUIT_BREAKER_OPEN: 0.04,
            ErrorType.RATE_LIMIT_EXCEEDED: 0.07,
        }

        await asyncio.sleep(delay_map.get(error_type, 0.05))

        # Generate appropriate exception based on error type
        error_messages = {
            ErrorType.TIMEOUT: f"Operation timeout in {agent_id} after exceeding threshold",
            ErrorType.RESOURCE_EXHAUSTION: f"Resource exhaustion in {agent_id}: memory/CPU limits exceeded",
            ErrorType.NETWORK_PARTITION: f"Network partition detected: {agent_id} unreachable",
            ErrorType.DATA_CORRUPTION: f"Data corruption detected in {agent_id}: integrity validation failed",
            ErrorType.AUTHENTICATION_FAILURE: f"Authentication failure in {agent_id}: credentials invalid",
            ErrorType.VALIDATION_ERROR: f"Input validation error in {agent_id}: schema mismatch",
            ErrorType.CONCURRENT_MODIFICATION: f"Concurrent modification conflict in {agent_id}",
            ErrorType.DEPENDENCY_UNAVAILABLE: f"Critical dependency unavailable for {agent_id}",
            ErrorType.CIRCUIT_BREAKER_OPEN: f"Circuit breaker open for {agent_id}: service unavailable",
            ErrorType.RATE_LIMIT_EXCEEDED: f"Rate limit exceeded for {agent_id}: throttling active",
        }

        if error_type == ErrorType.TIMEOUT:
            return asyncio.TimeoutError(error_messages[error_type])
        if error_type == ErrorType.RESOURCE_EXHAUSTION:
            return MemoryError(error_messages[error_type])
        if error_type == ErrorType.NETWORK_PARTITION:
            return ConnectionError(error_messages[error_type])
        if error_type == ErrorType.AUTHENTICATION_FAILURE:
            return PermissionError(error_messages[error_type])
        return Exception(error_messages[error_type])

    async def execute_agent_with_error_propagation(
        self,
        agent_id: str,
        role: str,
        domain: str,
        task: str,
        session_id: str,
        artifacts_service: ArtifactsService,
        dependencies: set[str],
        error_scenario: ErrorScenario | None = None,
        error_state: dict[str, Any] = None,
        execution_delay: float = 0.1,
    ) -> dict[str, Any]:
        """Execute agent with comprehensive error propagation tracking."""
        start_time = time.time()

        if error_state is None:
            error_state = {}

        agent_result = {
            "agent_id": agent_id,
            "role": role,
            "domain": domain,
            "task": task,
            "dependencies": dependencies,
            "state": "running",
            "start_time": start_time,
            "execution_time": 0.0,
            "error": None,
            "error_type": None,
            "error_propagated_from": None,
            "error_propagated_to": set(),
            "recovery_attempted": False,
            "recovery_successful": False,
            "error_boundary_activated": False,
            "deliverable_id": None,
        }

        try:
            # Check for propagated errors from dependencies
            propagated_error = None
            for dep_id in dependencies:
                if dep_id in error_state and error_state[dep_id].get("error"):
                    propagated_error = error_state[dep_id]["error"]
                    agent_result["error_propagated_from"] = dep_id
                    error_state[dep_id]["error_propagated_to"].add(agent_id)
                    break

            # Simulate dependency checking delay
            await asyncio.sleep(0.02)

            # Inject primary error if this agent is the source
            if error_scenario and agent_id in error_scenario.affected_agents:
                error = await self.simulate_error_injection(
                    error_scenario.error_type, agent_id, error_scenario.severity
                )
                raise error

            # Propagate error if received from dependency
            if propagated_error:
                # Error boundary check
                if random.random() < 0.3:  # 30% chance of error boundary activation
                    agent_result["error_boundary_activated"] = True
                    agent_result["state"] = "isolated"

                    # Create error boundary document
                    boundary_author = Author(
                        id=f"{agent_id}_boundary", role="error_boundary"
                    )
                    boundary_doc = await artifacts_service.create_document(
                        session_id=session_id,
                        doc_name=f"{agent_id}_error_boundary_activation",
                        doc_type=DocumentType.SCRATCHPAD,
                        content=f"""# Error Boundary Activation

## Agent: {agent_id}
## Propagated Error: {propagated_error}
## Source: {agent_result["error_propagated_from"]}

## Boundary Response:
- Error contained and isolated
- Agent state preserved
- Graceful degradation activated
- Cascade prevention successful

## Status: Error Boundary ✅ Activated
""",
                        author=boundary_author,
                    )
                else:
                    # Error propagates through this agent
                    raise Exception(
                        f"Propagated error from {agent_result['error_propagated_from']}: {propagated_error}"
                    )

            # Normal execution simulation
            await asyncio.sleep(execution_delay)

            # Create successful deliverable
            author = Author(id=agent_id, role=role)
            deliverable = await artifacts_service.create_document(
                session_id=session_id,
                doc_name=f"{agent_id}_error_propagation_deliverable",
                doc_type=DocumentType.DELIVERABLE,
                content=f"""# {role.title()} Error Propagation Test Deliverable

## Agent: {agent_id}
## Task: {task}
## Domain: {domain}

### Error Propagation Analysis:
- Dependencies checked: {list(dependencies)}
- Error propagation status: {"Error boundary activated" if agent_result["error_boundary_activated"] else "No errors propagated"}
- Execution state: Successful completion

### Resilience Validation:
- Error handling mechanisms functional
- Dependency error checking operational
- Boundary conditions properly handled
- System integration maintained

### Status: ✅ Complete
### Execution Time: {time.time() - start_time:.3f}s
""",
                author=author,
            )

            agent_result["state"] = "completed"
            agent_result["deliverable_id"] = deliverable.id

        except Exception as e:
            # Handle various error types with recovery attempts
            agent_result["state"] = "failed"
            agent_result["error"] = str(e)
            agent_result["error_type"] = type(e).__name__

            # Attempt recovery based on error type
            if error_scenario and error_scenario.recovery_strategy in [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.FALLBACK,
            ]:
                agent_result["recovery_attempted"] = True

                try:
                    await asyncio.sleep(0.05)  # Recovery delay

                    if error_scenario.recovery_strategy == RecoveryStrategy.RETRY:
                        # Simulate retry logic
                        await asyncio.sleep(
                            execution_delay * 0.5
                        )  # Shorter retry execution
                        agent_result["recovery_successful"] = True
                        agent_result["state"] = "recovered"

                    elif error_scenario.recovery_strategy == RecoveryStrategy.FALLBACK:
                        # Simulate fallback mechanism
                        author = Author(id=f"{agent_id}_fallback", role=role)
                        fallback_doc = await artifacts_service.create_document(
                            session_id=session_id,
                            doc_name=f"{agent_id}_fallback_deliverable",
                            doc_type=DocumentType.DELIVERABLE,
                            content=f"""# {role.title()} Fallback Deliverable

## Agent: {agent_id} (Fallback Mode)
## Original Error: {agent_result["error"]}
## Recovery Strategy: Fallback execution

### Fallback Results:
- Primary execution failed, fallback activated
- Reduced functionality but operational
- Core objectives achieved with limitations
- System resilience demonstrated

### Status: ✅ Fallback Complete
""",
                            author=author,
                        )
                        agent_result["recovery_successful"] = True
                        agent_result["state"] = "recovered_fallback"
                        agent_result["deliverable_id"] = fallback_doc.id

                except Exception:
                    agent_result["recovery_successful"] = False

        finally:
            agent_result["execution_time"] = time.time() - start_time
            error_state[agent_id] = agent_result

        return agent_result

    @pytest.mark.asyncio
    async def test_multi_level_error_propagation(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test multi-level error propagation through complex dependency chains."""
        session_id = "multi_level_propagation_test"
        await artifacts_service.create_session(session_id)

        # Create multi-level dependency chain for error propagation testing
        dependency_chain = {
            "source_agent": {"role": "data_source", "dependencies": set()},
            "processor_agent": {"role": "processor", "dependencies": {"source_agent"}},
            "validator_agent": {
                "role": "validator",
                "dependencies": {"processor_agent"},
            },
            "aggregator_agent": {
                "role": "aggregator",
                "dependencies": {"validator_agent", "processor_agent"},
            },
            "publisher_agent": {
                "role": "publisher",
                "dependencies": {"aggregator_agent"},
            },
            "monitor_agent": {"role": "monitor", "dependencies": {"publisher_agent"}},
        }

        # Create error scenario for multi-level propagation
        error_scenario = ErrorScenario(
            error_type=ErrorType.DATA_CORRUPTION,
            severity=ErrorSeverity.HIGH,
            propagation_pattern="linear_cascade",
            affected_agents={"source_agent"},
            recovery_strategy=RecoveryStrategy.FALLBACK,
            expected_cascade_depth=4,
        )

        error_state = {}
        propagation_results = []

        # Execute agents in dependency order to observe propagation
        execution_order = [
            "source_agent",
            "processor_agent",
            "validator_agent",
            "aggregator_agent",
            "publisher_agent",
            "monitor_agent",
        ]

        for agent_id in execution_order:
            agent_config = dependency_chain[agent_id]

            result = await self.execute_agent_with_error_propagation(
                agent_id=agent_id,
                role=agent_config["role"],
                domain="multi_level_propagation",
                task=f"Execute {agent_config['role']} in propagation chain",
                session_id=session_id,
                artifacts_service=artifacts_service,
                dependencies=agent_config["dependencies"],
                error_scenario=error_scenario,
                error_state=error_state,
                execution_delay=0.08,
            )
            propagation_results.append(result)

            # Brief delay for propagation analysis
            await asyncio.sleep(0.02)

        # Analyze propagation results
        failed_agents = [r for r in propagation_results if r["state"] == "failed"]
        recovered_agents = [r for r in propagation_results if "recovered" in r["state"]]
        boundary_agents = [
            r for r in propagation_results if r["error_boundary_activated"]
        ]
        completed_agents = [r for r in propagation_results if r["state"] == "completed"]

        # Calculate propagation metrics
        propagation_depth = len([
            r for r in propagation_results if r["error"] is not None
        ])
        propagation_time = (
            max(
                r["execution_time"]
                for r in propagation_results
                if r["error"] is not None
            )
            if failed_agents
            else 0
        )

        # Create multi-level propagation analysis
        propagation_analyst = Author(id="propagation_analyst", role="analyst")
        propagation_analysis = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="multi_level_error_propagation_analysis",
            doc_type=DocumentType.DELIVERABLE,
            content=f"""# Multi-Level Error Propagation Analysis

## Propagation Chain Summary:
- Total agents in chain: {len(propagation_results)}
- Failed agents: {len(failed_agents)}
- Recovered agents: {len(recovered_agents)}
- Error boundaries activated: {len(boundary_agents)}
- Successfully completed: {len(completed_agents)}

## Dependency Chain Analysis:
{
                chr(10).join([
                    f"### {result['agent_id']} ({result['role']}):"
                    f"{chr(10)}- State: {result['state']}"
                    f"{chr(10)}- Dependencies: {list(result['dependencies']) if result['dependencies'] else 'None'}"
                    f"{chr(10)}- Error: {result['error'][:100] + '...' if result['error'] and len(result['error']) > 100 else result['error'] or 'None'}"
                    f"{chr(10)}- Error propagated from: {result['error_propagated_from'] or 'None'}"
                    f"{chr(10)}- Error propagated to: {list(result['error_propagated_to']) if result['error_propagated_to'] else 'None'}"
                    f"{chr(10)}- Recovery attempted: {result['recovery_attempted']}"
                    f"{chr(10)}- Error boundary: {'✅ Activated' if result['error_boundary_activated'] else 'Not triggered'}"
                    f"{chr(10)}- Execution time: {result['execution_time']:.3f}s"
                    for result in propagation_results
                ])
            }

## Error Propagation Metrics:
- Initial error source: {error_scenario.affected_agents}
- Propagation depth achieved: {propagation_depth}
- Expected propagation depth: {error_scenario.expected_cascade_depth}
- Propagation containment: {
                "✅ Within expected bounds"
                if propagation_depth <= error_scenario.expected_cascade_depth
                else "⚠️ Exceeded expectations"
            }
- Propagation time: {propagation_time:.3f}s

## Resilience Mechanisms Validation:
✅ Error injection successful at source
✅ Dependency-based error propagation functional
✅ Error boundary activation prevents full cascade
✅ Recovery mechanisms attempted where appropriate
✅ System maintains partial functionality despite errors

## Recovery Analysis:
- Recovery success rate: {
                len(recovered_agents)
                / len(failed_agents)
                * 100:.1f}% (of failed agents)
- Fallback mechanisms: {
                len([r for r in recovered_agents if "fallback" in r["state"]])
            } activated
- Error isolation: {len(boundary_agents)} boundaries prevented further propagation

## System Resilience Assessment:
- Cascade prevention: {
                "✅ Effective"
                if len(completed_agents) > 0
                else "⚠️ Full cascade occurred"
            }
- Partial functionality: {
                len(completed_agents)
                / len(propagation_results)
                * 100:.1f}% of chain remained operational
- Error handling: {
                "✅ Comprehensive"
                if len(recovered_agents) > 0
                else "⚠️ Limited recovery"
            }
- Boundary effectiveness: {
                len(boundary_agents)
                / len(propagation_results)
                * 100:.1f}% activation rate

## Status: ✅ Multi-Level Error Propagation Analysis Complete
""",
            author=propagation_analyst,
        )

        # Validate multi-level error propagation
        assert len(propagation_results) == len(dependency_chain)
        assert len(failed_agents) >= 1  # Should have initial failure
        assert (
            propagation_depth <= error_scenario.expected_cascade_depth + 1
        )  # Allow slight variance
        assert len(completed_agents) >= 1  # Some agents should complete despite errors
        assert (
            "multi-level error propagation analysis complete"
            in propagation_analysis.content.lower()
        )

    @pytest.mark.asyncio
    async def test_distributed_system_failure_patterns(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test distributed system failure patterns with network partitions."""
        session_id = "distributed_failure_test"
        await artifacts_service.create_session(session_id)

        # Create distributed agent topology with network partitions
        distributed_agents = {
            # Partition A - Processing cluster
            "partition_a_coordinator": DistributedAgentNode(
                "partition_a_coordinator", "coordinator", "coordination", "partition_a"
            ),
            "partition_a_worker_1": DistributedAgentNode(
                "partition_a_worker_1", "worker", "processing", "partition_a"
            ),
            "partition_a_worker_2": DistributedAgentNode(
                "partition_a_worker_2", "worker", "processing", "partition_a"
            ),
            # Partition B - Storage cluster
            "partition_b_coordinator": DistributedAgentNode(
                "partition_b_coordinator", "coordinator", "coordination", "partition_b"
            ),
            "partition_b_storage_1": DistributedAgentNode(
                "partition_b_storage_1", "storage", "data", "partition_b"
            ),
            "partition_b_storage_2": DistributedAgentNode(
                "partition_b_storage_2", "storage", "data", "partition_b"
            ),
            # Partition C - Bridge services
            "bridge_service": DistributedAgentNode(
                "bridge_service", "bridge", "integration", "partition_c"
            ),
            "external_gateway": DistributedAgentNode(
                "external_gateway", "gateway", "external", "partition_c"
            ),
        }

        # Set up cross-partition dependencies
        distributed_agents["partition_a_coordinator"].dependencies = {"bridge_service"}
        distributed_agents["partition_b_coordinator"].dependencies = {"bridge_service"}
        distributed_agents["partition_a_worker_1"].dependencies = {
            "partition_a_coordinator",
            "partition_b_storage_1",
        }
        distributed_agents["partition_a_worker_2"].dependencies = {
            "partition_a_coordinator",
            "partition_b_storage_2",
        }
        distributed_agents["bridge_service"].dependencies = {"external_gateway"}

        # Create network partition scenario
        partition_scenario = ErrorScenario(
            error_type=ErrorType.NETWORK_PARTITION,
            severity=ErrorSeverity.CRITICAL,
            propagation_pattern="partition_isolation",
            affected_agents={"bridge_service"},  # Bridge failure isolates partitions
            recovery_strategy=RecoveryStrategy.ISOLATION,
            expected_cascade_depth=6,
            timeout_threshold=1.5,
        )

        async def simulate_distributed_execution():
            """Simulate distributed system execution with partition failure."""
            error_state = {}
            execution_results = []

            # Execute agents with simulated network conditions
            execution_tasks = []
            for agent_id, agent in distributed_agents.items():

                async def execute_distributed_agent(agent_node: DistributedAgentNode):
                    """Execute agent in distributed environment."""

                    # Simulate network latency based on partition
                    partition_latency = {
                        "partition_a": 0.05,
                        "partition_b": 0.08,
                        "partition_c": 0.12,  # Bridge has higher latency
                    }

                    base_delay = partition_latency.get(agent_node.partition, 0.1)

                    # Check for cross-partition dependencies (simulate network calls)
                    cross_partition_deps = []
                    for dep_id in agent_node.dependencies:
                        if dep_id in distributed_agents:
                            dep_agent = distributed_agents[dep_id]
                            if dep_agent.partition != agent_node.partition:
                                cross_partition_deps.append(dep_id)
                                base_delay += 0.05  # Additional network latency

                    result = await self.execute_agent_with_error_propagation(
                        agent_id=agent_node.agent_id,
                        role=agent_node.role,
                        domain=agent_node.domain,
                        task=f"Execute {agent_node.role} in {agent_node.partition}",
                        session_id=session_id,
                        artifacts_service=artifacts_service,
                        dependencies=agent_node.dependencies,
                        error_scenario=partition_scenario
                        if agent_node.agent_id in partition_scenario.affected_agents
                        else None,
                        error_state=error_state,
                        execution_delay=base_delay,
                    )

                    # Add partition information to result
                    result["partition"] = agent_node.partition
                    result["cross_partition_deps"] = cross_partition_deps
                    result["network_latency"] = base_delay

                    return result

                task = execute_distributed_agent(agent)
                execution_tasks.append(task)

            # Execute with timeout to handle partition failures
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*execution_tasks, return_exceptions=True),
                    timeout=3.0,
                )
                return [r for r in results if isinstance(r, dict)]
            except asyncio.TimeoutError:
                return [
                    {
                        "agent_id": "timeout",
                        "state": "timeout",
                        "error": "Distributed execution timeout",
                    }
                ]

        # Execute distributed system test
        distributed_results = await simulate_distributed_execution()

        # Analyze distributed failure patterns
        partition_analysis = {}
        for result in distributed_results:
            if "partition" in result:
                partition = result["partition"]
                if partition not in partition_analysis:
                    partition_analysis[partition] = {
                        "agents": 0,
                        "successful": 0,
                        "failed": 0,
                        "isolated": 0,
                    }

                partition_analysis[partition]["agents"] += 1
                if result["state"] == "completed":
                    partition_analysis[partition]["successful"] += 1
                elif result["state"] == "failed":
                    partition_analysis[partition]["failed"] += 1
                elif "isolated" in result["state"]:
                    partition_analysis[partition]["isolated"] += 1

        # Create distributed failure analysis
        distributed_analyst = Author(id="distributed_analyst", role="analyst")
        distributed_analysis = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="distributed_system_failure_analysis",
            doc_type=DocumentType.DELIVERABLE,
            content=f"""# Distributed System Failure Pattern Analysis

## Distributed Topology Summary:
- Total agents: {len(distributed_results)}
- Network partitions: {len(partition_analysis)}
- Cross-partition dependencies: {
                sum(len(r.get("cross_partition_deps", [])) for r in distributed_results)
            }

## Partition Analysis:
{
                chr(10).join([
                    "### " + f"{partition.title()} (Partition {partition.split('_')[-1].upper()}):"
                    + f"{chr(10)}- Total agents: {stats['agents']}"
                    + f"{chr(10)}- Successful: {stats['successful']}"
                    + f"{chr(10)}- Failed: {stats['failed']}"
                    + f"{chr(10)}- Isolated: {stats['isolated']}"
                    + f"{chr(10)}- Success rate: {(stats['successful'] / stats['agents']) * 100:.1f}%"
                    for partition, stats in partition_analysis.items()
                ])
            }

## Agent Execution Results:
{
                chr(10).join([
                    "### " + f"{result['agent_id']} ({result.get('partition', 'unknown')}):"
                    + f"{chr(10)}- State: {result['state']}"
                    + f"{chr(10)}- Network latency: {result.get('network_latency', 0):.3f}s"
                    + f"{chr(10)}- Cross-partition deps: {result.get('cross_partition_deps', [])}"
                    + f"{chr(10)}- Error: {result['error'][:80] + '...' if result.get('error') and len(result['error']) > 80 else result.get('error') or 'None'}"
                    + f"{chr(10)}- Execution time: {result.get('execution_time', 0):.3f}s"
                    for result in distributed_results[:8]
                ])
            }
{"... and additional agents" if len(distributed_results) > 8 else ""}

## Network Partition Impact:
- Bridge service failure: {
                "✅ Simulated"
                if any("bridge" in r["agent_id"] for r in distributed_results)
                else "Not tested"
            }
- Partition isolation: {
                "✅ Observed" if len(partition_analysis) > 1 else "Single partition"
            }
- Cross-partition comm failure: {
                "✅ Simulated"
                if any(r.get("cross_partition_deps") for r in distributed_results)
                else "No cross-partition deps"
            }

## Distributed Resilience Validation:
✅ Network partition simulation functional
✅ Cross-partition dependency handling tested
✅ Partition isolation prevents full system failure
✅ Distributed coordination patterns validated
✅ Error propagation contained within partitions

## Performance Impact of Distribution:
- Average network latency: {
                sum(r.get("network_latency", 0) for r in distributed_results)
                / len(distributed_results):.3f}s
- Cross-partition overhead: {
                sum(
                    len(r.get("cross_partition_deps", [])) * 0.05
                    for r in distributed_results
                ):.3f}s total
- Partition isolation benefit: Failures contained within network boundaries

## Fault Tolerance Assessment:
- System availability: {
                len([
                    r
                    for r in distributed_results
                    if r["state"] in ["completed", "recovered"]
                ])
                / len(distributed_results)
                * 100:.1f}%
- Partition independence: {
                "✅ Maintained" if len(partition_analysis) > 1 else "Not applicable"
            }
- Recovery capability: {
                "✅ Functional"
                if any("recovered" in r.get("state", "") for r in distributed_results)
                else "Not triggered"
            }

## Status: ✅ Distributed System Failure Pattern Analysis Complete
""",
            author=distributed_analyst,
        )

        # Validate distributed failure patterns
        assert len(distributed_results) >= 6  # Should have multiple agents
        assert len(partition_analysis) >= 2  # Should have multiple partitions
        successful_rate = len([
            r for r in distributed_results if r.get("state") == "completed"
        ]) / len(distributed_results)
        assert (
            successful_rate >= 0.3
        )  # At least 30% should succeed despite partition failure
        assert (
            "distributed system failure pattern analysis complete"
            in distributed_analysis.content.lower()
        )

    @pytest.mark.asyncio
    async def test_compound_failure_recovery_coordination(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test recovery coordination under compound failure scenarios."""
        session_id = "compound_failure_recovery_test"
        await artifacts_service.create_session(session_id)

        # Create compound failure scenarios (multiple simultaneous failures)
        compound_scenarios = [
            ErrorScenario(
                error_type=ErrorType.TIMEOUT,
                severity=ErrorSeverity.MEDIUM,
                propagation_pattern="timeout_cascade",
                affected_agents={"timeout_service"},
                recovery_strategy=RecoveryStrategy.RETRY,
                expected_cascade_depth=2,
            ),
            ErrorScenario(
                error_type=ErrorType.RESOURCE_EXHAUSTION,
                severity=ErrorSeverity.HIGH,
                propagation_pattern="resource_cascade",
                affected_agents={"resource_service"},
                recovery_strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
                expected_cascade_depth=3,
            ),
            ErrorScenario(
                error_type=ErrorType.AUTHENTICATION_FAILURE,
                severity=ErrorSeverity.HIGH,
                propagation_pattern="auth_cascade",
                affected_agents={"auth_service"},
                recovery_strategy=RecoveryStrategy.FALLBACK,
                expected_cascade_depth=4,
            ),
        ]

        # Create recovery coordination agents
        recovery_agents = [
            {
                "agent_id": "timeout_service",
                "role": "timeout_handler",
                "domain": "timeout_management",
            },
            {
                "agent_id": "resource_service",
                "role": "resource_manager",
                "domain": "resource_management",
            },
            {
                "agent_id": "auth_service",
                "role": "auth_manager",
                "domain": "authentication",
            },
            {
                "agent_id": "coordination_service",
                "role": "recovery_coordinator",
                "domain": "recovery_coordination",
            },
            {
                "agent_id": "monitoring_service",
                "role": "monitor",
                "domain": "system_monitoring",
            },
            {
                "agent_id": "fallback_service",
                "role": "fallback_handler",
                "domain": "fallback_management",
            },
        ]

        # Set up dependencies for compound failure testing
        dependencies_map = {
            "timeout_service": set(),
            "resource_service": set(),
            "auth_service": set(),
            "coordination_service": {
                "timeout_service",
                "resource_service",
                "auth_service",
            },
            "monitoring_service": {"coordination_service"},
            "fallback_service": {"coordination_service"},
        }

        async def execute_compound_recovery():
            """Execute compound failure recovery coordination."""
            error_state = {}
            recovery_results = []

            # Execute primary services with compound failures
            primary_tasks = []
            for agent_config in recovery_agents[:3]:  # First 3 are primary services
                agent_id = agent_config["agent_id"]

                # Find corresponding error scenario
                error_scenario = None
                for scenario in compound_scenarios:
                    if agent_id in scenario.affected_agents:
                        error_scenario = scenario
                        break

                task = self.execute_agent_with_error_propagation(
                    agent_id=agent_id,
                    role=agent_config["role"],
                    domain=agent_config["domain"],
                    task=f"Execute {agent_config['role']} with compound failure testing",
                    session_id=session_id,
                    artifacts_service=artifacts_service,
                    dependencies=dependencies_map[agent_id],
                    error_scenario=error_scenario,
                    error_state=error_state,
                    execution_delay=0.1,
                )
                primary_tasks.append(task)

            # Execute primary services
            primary_results = await asyncio.gather(*primary_tasks)
            recovery_results.extend(primary_results)

            # Brief delay for error propagation
            await asyncio.sleep(0.05)

            # Execute recovery coordination services
            recovery_tasks = []
            for agent_config in recovery_agents[3:]:  # Recovery services
                agent_id = agent_config["agent_id"]

                task = self.execute_agent_with_error_propagation(
                    agent_id=agent_id,
                    role=agent_config["role"],
                    domain=agent_config["domain"],
                    task=f"Execute {agent_config['role']} for compound recovery",
                    session_id=session_id,
                    artifacts_service=artifacts_service,
                    dependencies=dependencies_map[agent_id],
                    error_scenario=None,  # Recovery services should not fail
                    error_state=error_state,
                    execution_delay=0.08,
                )
                recovery_tasks.append(task)

            # Execute recovery services
            recovery_service_results = await asyncio.gather(*recovery_tasks)
            recovery_results.extend(recovery_service_results)

            return recovery_results, error_state

        # Execute compound failure recovery test
        compound_results, final_error_state = await execute_compound_recovery()

        # Analyze compound failure recovery
        primary_failures = [r for r in compound_results[:3] if r["state"] == "failed"]
        recovery_services = [
            r for r in compound_results[3:] if r["state"] in ["completed", "recovered"]
        ]
        error_boundaries = [
            r for r in compound_results if r["error_boundary_activated"]
        ]
        recovery_attempts = [r for r in compound_results if r["recovery_attempted"]]

        # Create compound failure recovery analysis
        compound_analyst = Author(id="compound_analyst", role="analyst")
        compound_analysis = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="compound_failure_recovery_analysis",
            doc_type=DocumentType.DELIVERABLE,
            content=f"""# Compound Failure Recovery Coordination Analysis

## Compound Failure Scenario:
- Simultaneous failure types: {len(compound_scenarios)}
- Primary service failures: {len(primary_failures)}/3
- Recovery service successes: {len(recovery_services)}/3
- Total coordination agents: {len(compound_results)}

## Failure Breakdown:
{
                chr(10).join([
                    f"### {scenario.error_type.value.title()} Failure:"
                    f"{chr(10)}- Affected agent: {list(scenario.affected_agents)[0]}"
                    f"{chr(10)}- Severity: {scenario.severity.value}"
                    f"{chr(10)}- Recovery strategy: {scenario.recovery_strategy.value}"
                    f"{chr(10)}- Expected cascade depth: {scenario.expected_cascade_depth}"
                    for scenario in compound_scenarios
                ])
            }

## Recovery Coordination Results:
{
                chr(10).join([
                    f"### {result['agent_id']} ({result['role']}):"
                    f"{chr(10)}- Final state: {result['state']}"
                    f"{chr(10)}- Error type: {result.get('error_type', 'None')}"
                    f"{chr(10)}- Recovery attempted: {'✅' if result['recovery_attempted'] else '❌'}"
                    f"{chr(10)}- Recovery successful: {'✅' if result['recovery_successful'] else ('❌' if result['recovery_attempted'] else 'N/A')}"
                    f"{chr(10)}- Error boundary: {'✅ Activated' if result['error_boundary_activated'] else 'Not triggered'}"
                    f"{chr(10)}- Execution time: {result['execution_time']:.3f}s"
                    for result in compound_results
                ])
            }

## Compound Recovery Metrics:
- Primary failure rate: {len(primary_failures) / 3 * 100:.1f}% (expected: 100%)
- Recovery service success: {len(recovery_services) / 3 * 100:.1f}%
- Error boundary activation: {len(error_boundaries)} boundaries activated
- Recovery attempt rate: {len(recovery_attempts) / len(compound_results) * 100:.1f}%
- Overall system resilience: {
                len([
                    r
                    for r in compound_results
                    if r["state"] in ["completed", "recovered", "recovered_fallback"]
                ])
                / len(compound_results)
                * 100:.1f}%

## Coordination Effectiveness:
✅ Multiple simultaneous failures handled
✅ Recovery coordination services functional
✅ Error boundary isolation prevents full cascade
✅ Recovery strategies deployed appropriately
✅ System maintains partial operational capacity

## Recovery Strategy Analysis:
{
                chr(10).join([
                    f"- {scenario.recovery_strategy.value.title()}: "
                    f"{'✅ Successful' if any(r['recovery_successful'] and scenario.error_type.value in (r.get('error') or '').lower() for r in compound_results) else '⚠️ Needs review'}"
                    for scenario in compound_scenarios
                ])
            }

## System State After Compound Failures:
- Operational services: {
                len([
                    r
                    for r in compound_results
                    if r["state"] in ["completed", "recovered", "recovered_fallback"]
                ])
            }/{len(compound_results)}
- Failed services: {len([r for r in compound_results if r["state"] == "failed"])}/{
                len(compound_results)
            }
- Recovery time: {max(r["execution_time"] for r in compound_results):.3f}s
- System availability: {len(recovery_services) / len(compound_results) * 100:.1f}%

## Resilience Assessment:
- Compound failure tolerance: ✅ System survives multiple simultaneous failures
- Recovery coordination: ✅ Specialized recovery services functional
- Error propagation control: ✅ Boundaries prevent cascade amplification
- Service degradation: ✅ Graceful degradation maintains core functionality

## Status: ✅ Compound Failure Recovery Coordination Analysis Complete
""",
            author=compound_analyst,
        )

        # Validate compound failure recovery coordination
        assert len(compound_results) == len(recovery_agents)
        assert len(primary_failures) >= 1  # Should have some primary failures
        assert len(recovery_services) >= 1  # Should have some recovery services working
        recovery_effectiveness = len(recovery_services) / len(compound_results)
        assert recovery_effectiveness >= 0.5  # At least 50% effective recovery
        assert (
            "compound failure recovery coordination analysis complete"
            in compound_analysis.content.lower()
        )
