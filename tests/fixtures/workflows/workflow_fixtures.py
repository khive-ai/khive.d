"""
Comprehensive workflow test fixtures for GitHub issue #192.

Provides realistic test data, mock services, and utilities for testing
async operations, concurrent execution, system recovery, and performance
under load conditions in the khive orchestration system.
"""

import asyncio
import random
import tempfile
import time
from collections.abc import Callable
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
from khive.services.plan.planner_service import PlannerService


class WorkflowType(Enum):
    """Types of workflows for testing."""

    SIMPLE_TASK = "simple_task"
    MULTI_AGENT = "multi_agent"
    QUALITY_GATE = "quality_gate"
    RECOVERY = "recovery"
    PERFORMANCE = "performance"


@dataclass
class MockAgentConfig:
    """Configuration for mock agent execution."""

    agent_id: str
    role: str
    domain: str
    task: str
    execution_delay: float = 0.1
    should_fail: bool = False
    failure_type: str = "timeout"
    deliverable_content: str | None = None


@dataclass
class WorkflowScenario:
    """Complete workflow test scenario configuration."""

    name: str
    workflow_type: WorkflowType
    description: str
    agents: list[MockAgentConfig]
    expected_deliverables: int
    max_execution_time: float
    success_criteria: dict[str, Any]


@dataclass
class PerformanceMetrics:
    """Performance metrics for workflow execution."""

    execution_time: float
    throughput: float
    success_rate: float
    memory_usage: int | None = None
    concurrent_operations: int = 1
    error_rate: float = 0.0


class MockWorkflowServices:
    """Mock services for workflow testing."""

    def __init__(self):
        self.planner_service = None
        self.orchestrator = None
        self.artifacts_service = None

    async def setup_planner_service(self) -> PlannerService:
        """Setup mock planner service."""
        if self.planner_service:
            return self.planner_service

        with patch("khive.services.plan.planner_service.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock planning responses
            mock_response = MagicMock()
            mock_response.parsed.complexity = "medium"
            mock_response.parsed.total_agents = 3
            mock_response.parsed.role_priorities = [
                "researcher",
                "implementer",
                "tester",
            ]
            mock_response.parsed.primary_domains = [
                "async-programming",
                "software-architecture",
            ]
            mock_response.parsed.workflow_pattern = "concurrent"
            mock_response.parsed.quality_level = "thorough"
            mock_response.parsed.confidence = 0.9

            mock_client.beta.chat.completions.parse.return_value = mock_response
            self.planner_service = PlannerService(command_format="json")
            return self.planner_service

    async def setup_orchestrator(
        self, flow_name: str = "test_workflow"
    ) -> LionOrchestrator:
        """Setup mock orchestrator."""
        if self.orchestrator:
            return self.orchestrator

        with patch(
            "khive.services.orchestration.orchestrator.create_cc"
        ) as mock_create_cc:
            from lionagi.service.imodel import iModel

            mock_cc = MagicMock(spec=iModel)
            mock_cc.chat = AsyncMock(return_value="Mock orchestrator response")
            mock_cc.invoke = AsyncMock(return_value="Mock orchestration result")
            mock_create_cc.return_value = mock_cc

            self.orchestrator = LionOrchestrator(flow_name)
            await self.orchestrator.initialize()
            return self.orchestrator

    def setup_artifacts_service(self, workspace_root: Path) -> ArtifactsService:
        """Setup artifacts service with test workspace."""
        if self.artifacts_service:
            return self.artifacts_service

        config = ArtifactsConfig(workspace_root=workspace_root)
        self.artifacts_service = create_artifacts_service(config)
        return self.artifacts_service


class WorkflowTestDataGenerator:
    """Generates realistic test data for workflow testing."""

    @staticmethod
    def generate_task_scenarios() -> list[dict[str, Any]]:
        """Generate realistic task scenarios."""
        return [
            {
                "name": "Simple Async Implementation",
                "description": "Add async timeout handling to file upload service",
                "complexity": "simple",
                "expected_agents": 2,
                "domains": ["async-programming"],
            },
            {
                "name": "Multi-Service Integration",
                "description": "Implement async queue system with Redis backend and monitoring",
                "complexity": "medium",
                "expected_agents": 4,
                "domains": ["async-programming", "software-architecture"],
            },
            {
                "name": "Distributed System Design",
                "description": "Design distributed microservices with service discovery and load balancing",
                "complexity": "complex",
                "expected_agents": 6,
                "domains": ["software-architecture", "distributed-systems"],
            },
        ]

    @staticmethod
    def generate_agent_configurations(
        workflow_type: WorkflowType, num_agents: int = 4
    ) -> list[MockAgentConfig]:
        """Generate agent configurations for different workflow types."""
        base_roles = [
            "researcher",
            "architect",
            "implementer",
            "tester",
            "reviewer",
            "optimizer",
        ]
        domains = ["async-programming", "software-architecture", "distributed-systems"]

        agents = []
        for i in range(num_agents):
            role = base_roles[i % len(base_roles)]
            domain = random.choice(domains)

            # Adjust configuration based on workflow type
            config = MockAgentConfig(
                agent_id=f"{workflow_type.value}_agent_{i:02d}",
                role=role,
                domain=domain,
                task=f"Execute {role} tasks for {workflow_type.value} workflow",
                execution_delay=(
                    0.1 if workflow_type != WorkflowType.PERFORMANCE else 0.05
                ),
            )

            # Add failure scenarios for recovery testing
            if workflow_type == WorkflowType.RECOVERY and i % 3 == 0:
                config.should_fail = True
                config.failure_type = random.choice(
                    [
                        "timeout",
                        "connection_error",
                        "partial_failure",
                    ]
                )

            agents.append(config)

        return agents

    @staticmethod
    def generate_workflow_scenarios() -> list[WorkflowScenario]:
        """Generate comprehensive workflow test scenarios."""
        return [
            WorkflowScenario(
                name="Simple Task Workflow",
                workflow_type=WorkflowType.SIMPLE_TASK,
                description="Basic async task implementation workflow",
                agents=WorkflowTestDataGenerator.generate_agent_configurations(
                    WorkflowType.SIMPLE_TASK, 2
                ),
                expected_deliverables=2,
                max_execution_time=1.0,
                success_criteria={"min_success_rate": 0.9, "max_errors": 0},
            ),
            WorkflowScenario(
                name="Multi-Agent Coordination",
                workflow_type=WorkflowType.MULTI_AGENT,
                description="Complex multi-agent coordination workflow",
                agents=WorkflowTestDataGenerator.generate_agent_configurations(
                    WorkflowType.MULTI_AGENT, 5
                ),
                expected_deliverables=5,
                max_execution_time=2.0,
                success_criteria={"min_success_rate": 0.8, "max_errors": 1},
            ),
            WorkflowScenario(
                name="Quality Gate Cycle",
                workflow_type=WorkflowType.QUALITY_GATE,
                description="Quality gate evaluation and refinement workflow",
                agents=WorkflowTestDataGenerator.generate_agent_configurations(
                    WorkflowType.QUALITY_GATE, 3
                ),
                expected_deliverables=4,  # Initial + review + refined + approval
                max_execution_time=1.5,
                success_criteria={"min_success_rate": 0.9, "refinement_cycles": 1},
            ),
            WorkflowScenario(
                name="Recovery Testing",
                workflow_type=WorkflowType.RECOVERY,
                description="System recovery and resilience workflow",
                agents=WorkflowTestDataGenerator.generate_agent_configurations(
                    WorkflowType.RECOVERY, 6
                ),
                expected_deliverables=4,  # Some agents will fail
                max_execution_time=3.0,
                success_criteria={"min_success_rate": 0.6, "recovery_time": 2.0},
            ),
            WorkflowScenario(
                name="Performance Testing",
                workflow_type=WorkflowType.PERFORMANCE,
                description="High-throughput performance workflow",
                agents=WorkflowTestDataGenerator.generate_agent_configurations(
                    WorkflowType.PERFORMANCE, 8
                ),
                expected_deliverables=8,
                max_execution_time=1.0,
                success_criteria={"min_throughput": 5.0, "max_latency": 0.3},
            ),
        ]

    @staticmethod
    def generate_failure_scenarios() -> list[dict[str, Any]]:
        """Generate failure scenarios for resilience testing."""
        return [
            {
                "name": "Timeout Failures",
                "failure_type": "timeout",
                "failure_rate": 0.3,
                "recovery_expected": True,
                "max_recovery_time": 1.0,
            },
            {
                "name": "Connection Failures",
                "failure_type": "connection_error",
                "failure_rate": 0.2,
                "recovery_expected": True,
                "max_recovery_time": 0.5,
            },
            {
                "name": "Partial Service Failures",
                "failure_type": "partial_failure",
                "failure_rate": 0.4,
                "recovery_expected": True,
                "max_recovery_time": 2.0,
            },
            {
                "name": "Memory Pressure",
                "failure_type": "memory_error",
                "failure_rate": 0.1,
                "recovery_expected": False,
                "max_recovery_time": None,
            },
        ]

    @staticmethod
    def generate_performance_test_data(
        concurrency_levels: list[int],
    ) -> list[dict[str, Any]]:
        """Generate performance test configurations."""
        return [
            {
                "name": f"{level}_concurrent_operations",
                "concurrent_operations": level,
                "operation_complexity": "medium",
                "expected_throughput": min(
                    level * 0.8, 20
                ),  # Realistic throughput expectation
                "max_latency": 0.5
                + (level * 0.02),  # Latency increases with concurrency
                "timeout": 5.0,
                "success_rate_threshold": max(
                    0.8 - (level * 0.01), 0.6
                ),  # Lower success rate under high load
            }
            for level in concurrency_levels
        ]


class WorkflowExecutionUtils:
    """Utilities for executing workflow tests."""

    @staticmethod
    async def execute_mock_agent(
        agent_config: MockAgentConfig,
        session_id: str,
        artifacts_service: ArtifactsService,
    ) -> dict[str, Any]:
        """Execute mock agent with realistic behavior."""
        start_time = time.time()

        try:
            # Simulate agent processing
            await asyncio.sleep(agent_config.execution_delay)

            # Simulate failure conditions
            if agent_config.should_fail:
                if agent_config.failure_type == "timeout":
                    raise asyncio.TimeoutError(
                        f"Simulated timeout in {agent_config.role}"
                    )
                if agent_config.failure_type == "connection_error":
                    raise ConnectionError(
                        f"Simulated connection error in {agent_config.role}"
                    )
                if agent_config.failure_type == "partial_failure":
                    if random.random() < 0.7:  # 70% chance of actual failure
                        raise Exception(
                            f"Simulated partial failure in {agent_config.role}"
                        )

            # Create agent deliverable
            author = Author(id=agent_config.agent_id, role=agent_config.role)
            content = (
                agent_config.deliverable_content
                or f"""# {agent_config.role.title()} Deliverable

## Task: {agent_config.task}
## Domain: {agent_config.domain}
## Agent ID: {agent_config.agent_id}

### Execution Summary
Successfully completed {agent_config.role} analysis in {agent_config.domain} domain.

### Key Results
- Async operations properly implemented
- Error handling mechanisms in place
- Performance requirements validated
- Integration points verified

### Status: ✅ Complete
### Execution Time: {time.time() - start_time:.3f}s
"""
            )

            deliverable = await artifacts_service.create_document(
                session_id=session_id,
                doc_name=f"{agent_config.role}_{agent_config.domain}_deliverable",
                doc_type=DocumentType.DELIVERABLE,
                content=content,
                author=author,
                description=f"Deliverable from {agent_config.role} agent",
            )

            return {
                "agent_id": agent_config.agent_id,
                "status": "completed",
                "execution_time": time.time() - start_time,
                "deliverable_id": f"{deliverable.session_id}:{deliverable.name}",
                "role": agent_config.role,
                "domain": agent_config.domain,
            }

        except Exception as e:
            return {
                "agent_id": agent_config.agent_id,
                "status": "failed",
                "execution_time": time.time() - start_time,
                "error": str(e),
                "role": agent_config.role,
                "domain": agent_config.domain,
            }

    @staticmethod
    async def execute_workflow_scenario(
        scenario: WorkflowScenario, artifacts_service: ArtifactsService
    ) -> dict[str, Any]:
        """Execute complete workflow scenario."""
        session_id = f"{scenario.workflow_type.value}_test_{int(time.time())}"
        await artifacts_service.create_session(session_id)

        start_time = time.time()

        # Execute agents based on workflow type
        if scenario.workflow_type in [
            WorkflowType.SIMPLE_TASK,
            WorkflowType.MULTI_AGENT,
            WorkflowType.PERFORMANCE,
        ]:
            # Concurrent execution
            agent_tasks = [
                WorkflowExecutionUtils.execute_mock_agent(
                    agent, session_id, artifacts_service
                )
                for agent in scenario.agents
            ]
            agent_results = await asyncio.gather(*agent_tasks)

        elif scenario.workflow_type == WorkflowType.QUALITY_GATE:
            # Sequential execution with review cycles
            agent_results = []
            for agent in scenario.agents:
                result = await WorkflowExecutionUtils.execute_mock_agent(
                    agent, session_id, artifacts_service
                )
                agent_results.append(result)

                # Add review cycle for implementer
                if agent.role == "implementer":
                    await asyncio.sleep(0.05)  # Review delay

        elif scenario.workflow_type == WorkflowType.RECOVERY:
            # Mixed execution with failure handling
            agent_tasks = [
                WorkflowExecutionUtils.execute_mock_agent(
                    agent, session_id, artifacts_service
                )
                for agent in scenario.agents
            ]
            agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)

            # Process exceptions in recovery scenarios
            processed_results = []
            for result in agent_results:
                if isinstance(result, Exception):
                    processed_results.append(
                        {
                            "status": "exception",
                            "error": str(result),
                            "execution_time": 0.0,
                        }
                    )
                else:
                    processed_results.append(result)
            agent_results = processed_results

        total_execution_time = time.time() - start_time

        # Calculate metrics
        successful_agents = [r for r in agent_results if r.get("status") == "completed"]
        failed_agents = [
            r for r in agent_results if r.get("status") in ["failed", "exception"]
        ]

        success_rate = (
            len(successful_agents) / len(agent_results) if agent_results else 0
        )
        throughput = (
            len(successful_agents) / total_execution_time
            if total_execution_time > 0
            else 0
        )

        # Validate artifacts
        registry = await artifacts_service.get_artifact_registry(session_id)
        deliverable_count = len(
            [a for a in registry.artifacts if "deliverable" in a.file_path]
        )

        return {
            "scenario_name": scenario.name,
            "session_id": session_id,
            "execution_time": total_execution_time,
            "success_rate": success_rate,
            "throughput": throughput,
            "total_agents": len(agent_results),
            "successful_agents": len(successful_agents),
            "failed_agents": len(failed_agents),
            "deliverable_count": deliverable_count,
            "meets_criteria": WorkflowExecutionUtils.validate_success_criteria(
                scenario.success_criteria,
                success_rate,
                total_execution_time,
                throughput,
                deliverable_count,
            ),
            "agent_results": agent_results,
        }

    @staticmethod
    def validate_success_criteria(
        criteria: dict[str, Any],
        success_rate: float,
        execution_time: float,
        throughput: float,
        deliverable_count: int,
    ) -> bool:
        """Validate workflow results against success criteria."""
        checks = []

        if "min_success_rate" in criteria:
            checks.append(success_rate >= criteria["min_success_rate"])

        if "max_execution_time" in criteria:
            checks.append(execution_time <= criteria["max_execution_time"])

        if "min_throughput" in criteria:
            checks.append(throughput >= criteria["min_throughput"])

        if "min_deliverables" in criteria:
            checks.append(deliverable_count >= criteria["min_deliverables"])

        if "max_errors" in criteria:
            error_count = 1 - success_rate  # Simplified error rate calculation
            checks.append(error_count <= criteria["max_errors"])

        return all(checks) if checks else True

    @staticmethod
    async def measure_performance_metrics(
        operation: Callable, concurrency_level: int, timeout: float = 5.0
    ) -> PerformanceMetrics:
        """Measure performance metrics for async operations."""
        start_time = time.time()

        # Execute operations concurrently
        tasks = [operation() for _ in range(concurrency_level)]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=timeout
            )
        except asyncio.TimeoutError:
            results = [Exception("Operation timed out")] * concurrency_level

        execution_time = time.time() - start_time

        # Calculate metrics
        successful_ops = [r for r in results if not isinstance(r, Exception)]
        failed_ops = [r for r in results if isinstance(r, Exception)]

        success_rate = len(successful_ops) / len(results) if results else 0
        throughput = len(successful_ops) / execution_time if execution_time > 0 else 0
        error_rate = len(failed_ops) / len(results) if results else 0

        return PerformanceMetrics(
            execution_time=execution_time,
            throughput=throughput,
            success_rate=success_rate,
            concurrent_operations=concurrency_level,
            error_rate=error_rate,
        )


# Pytest fixtures for workflow testing
@pytest.fixture
def workflow_workspace():
    """Create temporary workspace for workflow testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir) / "workflow_test_workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        yield workspace


@pytest.fixture
def mock_workflow_services():
    """Provide mock workflow services."""
    return MockWorkflowServices()


@pytest.fixture
def workflow_test_data():
    """Provide workflow test data generator."""
    return WorkflowTestDataGenerator()


@pytest.fixture
def workflow_execution_utils():
    """Provide workflow execution utilities."""
    return WorkflowExecutionUtils()


@pytest.fixture
async def configured_artifacts_service(workflow_workspace):
    """Provide configured artifacts service."""
    config = ArtifactsConfig(workspace_root=workflow_workspace)
    return create_artifacts_service(config)


@pytest.fixture
def workflow_scenarios():
    """Provide comprehensive workflow test scenarios."""
    return WorkflowTestDataGenerator.generate_workflow_scenarios()


@pytest.fixture
def failure_scenarios():
    """Provide failure test scenarios."""
    return WorkflowTestDataGenerator.generate_failure_scenarios()


@pytest.fixture
def performance_test_configs():
    """Provide performance test configurations."""
    return WorkflowTestDataGenerator.generate_performance_test_data([5, 10, 20, 50])
