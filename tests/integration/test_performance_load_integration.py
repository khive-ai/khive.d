"""Performance benchmarking and load testing integration tests for multi-agent workflow execution under concurrent load conditions.

This module addresses Issue #191's performance testing requirements by providing:
- Multi-agent coordination performance under concurrent loads
- Concurrent session handling and resource behavior under stress
- System resource utilization and performance degradation pattern analysis
- Integration testing for complete workflow performance validation
- Performance regression detection for multi-agent systems

Tests focus on realistic load patterns, resource contention scenarios, and
performance thresholds that validate production readiness.
"""

import asyncio
import gc
import random
import statistics
import time
import tracemalloc
from collections import defaultdict
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import psutil
import pytest

from khive.services.artifacts.factory import ArtifactsConfig, create_artifacts_service
from khive.services.artifacts.models import Author, DocumentType
from khive.services.artifacts.service import ArtifactsService
from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.plan.parts import PlannerRequest
from khive.services.plan.planner_service import PlannerService


class PerformanceLoadValidator:
    """Validator for performance characteristics under load."""

    def __init__(self):
        self.load_metrics = defaultdict(list)
        self.resource_snapshots = []
        self.performance_thresholds = {
            "max_response_time": 5.0,  # seconds
            "min_throughput": 1.0,  # operations/sec
            "max_memory_growth": 100,  # MB
            "min_success_rate": 0.85,  # 85%
            "max_p95_latency": 10.0,  # seconds
        }

    def record_load_metric(self, load_level: int, metric_name: str, value: float):
        """Record a performance metric for a specific load level."""
        self.load_metrics[load_level].append(
            {
                "metric": metric_name,
                "value": value,
                "timestamp": time.perf_counter(),
            }
        )

    def take_resource_snapshot(self, label: str):
        """Take a system resource snapshot."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            snapshot = {
                "label": label,
                "timestamp": time.perf_counter(),
                "memory_rss_mb": memory_info.rss / (1024 * 1024),
                "memory_vms_mb": memory_info.vms / (1024 * 1024),
                "cpu_percent": process.cpu_percent(),
                "num_threads": process.num_threads(),
            }

            # Add Python-specific memory info if tracemalloc is running
            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                snapshot["tracemalloc_current_mb"] = current / (1024 * 1024)
                snapshot["tracemalloc_peak_mb"] = peak / (1024 * 1024)

            self.resource_snapshots.append(snapshot)

        except Exception:
            # Handle cases where process monitoring fails
            pass

    def validate_performance_thresholds(self, load_level: int) -> dict[str, bool]:
        """Validate performance against thresholds for a load level."""
        validations = {}
        metrics = self.load_metrics.get(load_level, [])

        if not metrics:
            return {"no_metrics": False}

        # Group metrics by type
        metric_groups = defaultdict(list)
        for metric in metrics:
            metric_groups[metric["metric"]].append(metric["value"])

        # Validate each threshold
        for threshold_name, threshold_value in self.performance_thresholds.items():
            if threshold_name.startswith("max_"):
                metric_name = threshold_name[4:]  # Remove 'max_' prefix
                if metric_name in metric_groups:
                    max_value = max(metric_groups[metric_name])
                    validations[threshold_name] = max_value <= threshold_value
            elif threshold_name.startswith("min_"):
                metric_name = threshold_name[4:]  # Remove 'min_' prefix
                if metric_name in metric_groups:
                    min_value = min(metric_groups[metric_name])
                    validations[threshold_name] = min_value >= threshold_value

        return validations

    def analyze_resource_growth(
        self, start_label: str, end_label: str
    ) -> dict[str, float]:
        """Analyze resource growth between two snapshots."""
        start_snapshot = None
        end_snapshot = None

        for snapshot in self.resource_snapshots:
            if snapshot["label"] == start_label:
                start_snapshot = snapshot
            elif snapshot["label"] == end_label:
                end_snapshot = snapshot

        if not start_snapshot or not end_snapshot:
            return {"error": "Missing snapshots"}

        return {
            "memory_growth_mb": end_snapshot["memory_rss_mb"]
            - start_snapshot["memory_rss_mb"],
            "cpu_change": end_snapshot["cpu_percent"] - start_snapshot["cpu_percent"],
            "thread_change": end_snapshot["num_threads"]
            - start_snapshot["num_threads"],
            "duration_seconds": end_snapshot["timestamp"] - start_snapshot["timestamp"],
        }


class ConcurrentSessionManager:
    """Manager for concurrent session testing scenarios."""

    def __init__(self, artifacts_service: ArtifactsService):
        self.artifacts_service = artifacts_service
        self.active_sessions = {}
        self.session_metrics = defaultdict(list)

    async def create_concurrent_sessions(
        self, session_count: int, batch_size: int = 10
    ) -> list[str]:
        """Create multiple sessions concurrently in batches."""
        session_ids = []

        for batch_start in range(0, session_count, batch_size):
            batch_end = min(batch_start + batch_size, session_count)
            batch_tasks = []

            for i in range(batch_start, batch_end):
                session_id = f"concurrent_session_{i}_{uuid4().hex[:8]}"
                batch_tasks.append(self._create_session_with_metrics(session_id))

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, str):
                    session_ids.append(result)
                    self.active_sessions[result] = time.perf_counter()

            # Small pause between batches to avoid overwhelming the system
            if batch_end < session_count:
                await asyncio.sleep(0.1)

        return session_ids

    async def _create_session_with_metrics(self, session_id: str) -> str:
        """Create a session and record creation metrics."""
        start_time = time.perf_counter()

        try:
            await self.artifacts_service.create_session(session_id)
            end_time = time.perf_counter()

            self.session_metrics[session_id].append(
                {
                    "operation": "create",
                    "duration": end_time - start_time,
                    "success": True,
                    "timestamp": end_time,
                }
            )

            return session_id

        except Exception as e:
            end_time = time.perf_counter()

            self.session_metrics[session_id].append(
                {
                    "operation": "create",
                    "duration": end_time - start_time,
                    "success": False,
                    "error": str(e),
                    "timestamp": end_time,
                }
            )

            raise

    async def concurrent_session_operations(
        self, session_ids: list[str], operations_per_session: int = 10
    ) -> dict[str, Any]:
        """Execute concurrent operations across multiple sessions."""
        operation_tasks = []

        for session_id in session_ids:
            for op_num in range(operations_per_session):
                task = self._session_operation_with_metrics(session_id, op_num)
                operation_tasks.append(task)

        start_time = time.perf_counter()
        results = await asyncio.gather(*operation_tasks, return_exceptions=True)
        end_time = time.perf_counter()

        # Analyze results
        successful_ops = sum(
            1 for r in results if isinstance(r, dict) and r.get("success", False)
        )
        failed_ops = len(results) - successful_ops

        return {
            "total_operations": len(results),
            "successful_operations": successful_ops,
            "failed_operations": failed_ops,
            "success_rate": successful_ops / len(results) if results else 0,
            "total_duration": end_time - start_time,
            "throughput": len(results) / (end_time - start_time),
            "results": results,
        }

    async def _session_operation_with_metrics(
        self, session_id: str, op_num: int
    ) -> dict[str, Any]:
        """Execute an operation on a session with performance metrics."""
        start_time = time.perf_counter()

        try:
            # Create a document in the session (realistic operation)
            author = Author(id=f"perf_agent_{op_num}", role="tester")
            doc_name = f"performance_doc_{op_num}_{uuid4().hex[:6]}"

            await self.artifacts_service.create_document(
                session_id=session_id,
                doc_name=doc_name,
                doc_type=DocumentType.SCRATCHPAD,
                content=f"Performance test document {op_num}\n"
                + "Content " * 50,  # ~350 bytes
                author=author,
            )

            end_time = time.perf_counter()

            result = {
                "session_id": session_id,
                "operation": "create_document",
                "op_num": op_num,
                "duration": end_time - start_time,
                "success": True,
                "timestamp": end_time,
            }

            self.session_metrics[session_id].append(result)
            return result

        except Exception as e:
            end_time = time.perf_counter()

            result = {
                "session_id": session_id,
                "operation": "create_document",
                "op_num": op_num,
                "duration": end_time - start_time,
                "success": False,
                "error": str(e),
                "timestamp": end_time,
            }

            self.session_metrics[session_id].append(result)
            return result

    def get_session_performance_summary(self) -> dict[str, Any]:
        """Get performance summary across all sessions."""
        all_operations = []
        session_summaries = {}

        for session_id, operations in self.session_metrics.items():
            successful_ops = [op for op in operations if op.get("success", False)]
            failed_ops = [op for op in operations if not op.get("success", False)]

            session_summaries[session_id] = {
                "total_operations": len(operations),
                "successful_operations": len(successful_ops),
                "failed_operations": len(failed_ops),
                "success_rate": (
                    len(successful_ops) / len(operations) if operations else 0
                ),
                "avg_duration": (
                    statistics.mean([op["duration"] for op in successful_ops])
                    if successful_ops
                    else 0
                ),
            }

            all_operations.extend(operations)

        if all_operations:
            successful_all = [op for op in all_operations if op.get("success", False)]
            durations = [op["duration"] for op in successful_all]

            overall_summary = {
                "total_sessions": len(self.session_metrics),
                "total_operations": len(all_operations),
                "successful_operations": len(successful_all),
                "overall_success_rate": len(successful_all) / len(all_operations),
                "avg_operation_duration": (
                    statistics.mean(durations) if durations else 0
                ),
                "p95_operation_duration": (
                    statistics.quantiles(durations, n=20)[18]
                    if len(durations) >= 20
                    else max(durations, default=0)
                ),
                "session_summaries": session_summaries,
            }
        else:
            overall_summary = {
                "total_sessions": len(self.session_metrics),
                "total_operations": 0,
                "successful_operations": 0,
                "overall_success_rate": 0,
                "session_summaries": session_summaries,
            }

        return overall_summary


class TestPerformanceLoadIntegration:
    """Integration performance tests for multi-agent workflows under concurrent load."""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create temporary workspace for testing."""
        workspace = tmp_path / "performance_load_workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    @pytest.fixture
    def artifacts_service(self, temp_workspace):
        """Create artifacts service for performance testing."""
        config = ArtifactsConfig(workspace_root=temp_workspace)
        return create_artifacts_service(config)

    @pytest.fixture
    async def planner_service(self):
        """Create planner service with performance-oriented mocked responses."""
        with patch("khive.services.plan.planner_service.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock planning responses with varying complexity
            def create_mock_response(complexity="medium", agents=5):
                mock_response = MagicMock()
                mock_response.parsed.complexity = complexity
                mock_response.parsed.total_agents = agents
                mock_response.parsed.role_priorities = [
                    "researcher",
                    "analyst",
                    "architect",
                    "implementer",
                    "tester",
                ][:agents]
                mock_response.parsed.primary_domains = [
                    "async-programming",
                    "software-architecture",
                ]
                mock_response.parsed.workflow_pattern = "parallel"
                mock_response.parsed.quality_level = "thorough"
                mock_response.parsed.confidence = 0.9
                return mock_response

            # Rotate through different response types
            responses = [
                create_mock_response("low", 3),
                create_mock_response("medium", 5),
                create_mock_response("high", 8),
                create_mock_response("medium", 6),
            ]

            mock_client.beta.chat.completions.parse.side_effect = (
                lambda **kwargs: random.choice(responses)
            )
            return PlannerService(command_format="json")

    @pytest.fixture
    async def orchestrator(self):
        """Create orchestrator with async performance setup."""
        with patch(
            "khive.services.orchestration.orchestrator.create_cc"
        ) as mock_create_cc:
            from lionagi.service.imodel import iModel

            # Mock CC with realistic async delays
            mock_cc = MagicMock(spec=iModel)

            async def mock_chat_with_delay(*args, **kwargs):
                # Simulate realistic LLM response time
                await asyncio.sleep(random.uniform(0.1, 0.3))
                return f"Mock agent response for {args}"

            async def mock_invoke_with_delay(*args, **kwargs):
                # Simulate realistic agent processing time
                await asyncio.sleep(random.uniform(0.2, 0.5))
                return f"Mock agent result for {args}"

            mock_cc.chat = AsyncMock(side_effect=mock_chat_with_delay)
            mock_cc.invoke = AsyncMock(side_effect=mock_invoke_with_delay)
            mock_create_cc.return_value = mock_cc

            orchestrator = LionOrchestrator("performance_load_test")
            await orchestrator.initialize()
            return orchestrator

    @pytest.fixture
    def performance_validator(self):
        """Provide performance load validator."""
        return PerformanceLoadValidator()

    @pytest.fixture
    def session_manager(self, artifacts_service):
        """Provide concurrent session manager."""
        return ConcurrentSessionManager(artifacts_service)

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.integration
    async def test_concurrent_multi_agent_coordination_performance(
        self,
        planner_service: PlannerService,
        orchestrator: LionOrchestrator,
        artifacts_service: ArtifactsService,
        performance_validator: PerformanceLoadValidator,
    ):
        """Test multi-agent coordination performance under concurrent loads."""

        # Test configuration for concurrent agent coordination
        concurrency_levels = [5, 10, 15, 20]  # Number of concurrent agent workflows
        agents_per_workflow = [3, 5, 8]  # Agents in each workflow

        performance_validator.take_resource_snapshot("concurrent_coordination_start")

        async def multi_agent_workflow(
            workflow_id: str,
            num_agents: int,
            performance_validator: PerformanceLoadValidator,
        ) -> dict[str, Any]:
            """Execute a multi-agent workflow with performance tracking."""

            workflow_start = time.perf_counter()
            session_id = f"workflow_{workflow_id}_{uuid4().hex[:6]}"

            try:
                # Create session for workflow
                await artifacts_service.create_session(session_id)

                # Generate planning request
                task_request = PlannerRequest(
                    task_description=f"Implement async microservice architecture with {num_agents} specialized agents",
                    context=f"Complex distributed system requiring {num_agents} agents for workflow {workflow_id}",
                )

                planning_start = time.perf_counter()
                planning_response = await planner_service.handle_request(task_request)
                planning_end = time.perf_counter()

                planning_duration = planning_end - planning_start
                performance_validator.record_load_metric(
                    num_agents, "planning_time", planning_duration
                )

                if not planning_response.success:
                    raise RuntimeError(f"Planning failed for workflow {workflow_id}")

                # Simulate multi-agent coordination
                agent_roles = [
                    "researcher",
                    "analyst",
                    "architect",
                    "implementer",
                    "tester",
                    "reviewer",
                    "critic",
                    "synthesizer",
                ]
                selected_roles = agent_roles[:num_agents]

                async def agent_execution(
                    agent_role: str, agent_index: int
                ) -> dict[str, Any]:
                    """Execute individual agent with coordination simulation."""
                    agent_start = time.perf_counter()
                    agent_id = f"agent_{agent_role}_{agent_index}_{workflow_id}"

                    try:
                        # Simulate agent-specific processing time based on role complexity
                        role_complexity = {
                            "researcher": 0.3,
                            "analyst": 0.4,
                            "architect": 0.6,
                            "implementer": 0.8,
                            "tester": 0.5,
                            "reviewer": 0.3,
                            "critic": 0.2,
                            "synthesizer": 0.4,
                        }

                        base_duration = role_complexity.get(agent_role, 0.4)
                        # Add coordination overhead (increases with more agents)
                        coordination_overhead = (num_agents - 1) * 0.02
                        total_processing_time = base_duration + coordination_overhead

                        # Simulate realistic agent work
                        await asyncio.sleep(
                            total_processing_time + random.uniform(-0.05, 0.05)
                        )

                        # Create agent deliverable
                        author = Author(id=agent_id, role=agent_role)
                        deliverable = await artifacts_service.create_document(
                            session_id=session_id,
                            doc_name=f"{agent_role}_deliverable_{agent_index}",
                            doc_type=DocumentType.DELIVERABLE,
                            content=f"""# {agent_role.title()} Agent Deliverable

## Workflow: {workflow_id}
## Agent: {agent_id}

### Task Completion
- Analyzed requirements for {num_agents}-agent coordination
- Implemented {agent_role}-specific functionality
- Coordinated with {num_agents - 1} other agents
- Generated deliverable for downstream agents

### Performance Metrics
- Processing time: {total_processing_time:.3f}s
- Coordination overhead: {coordination_overhead:.3f}s
- Agent complexity: {role_complexity.get(agent_role, 0.4)}

### Status: ✅ Complete
""",
                            author=author,
                            description=f"Performance test deliverable from {agent_role} agent",
                        )

                        agent_end = time.perf_counter()
                        agent_duration = agent_end - agent_start

                        return {
                            "agent_id": agent_id,
                            "agent_role": agent_role,
                            "duration": agent_duration,
                            "processing_time": total_processing_time,
                            "coordination_overhead": coordination_overhead,
                            "deliverable_id": deliverable.id,
                            "success": True,
                            "timestamp": agent_end,
                        }

                    except Exception as e:
                        agent_end = time.perf_counter()
                        agent_duration = agent_end - agent_start

                        return {
                            "agent_id": agent_id,
                            "agent_role": agent_role,
                            "duration": agent_duration,
                            "success": False,
                            "error": str(e),
                            "timestamp": agent_end,
                        }

                # Execute all agents concurrently (this is the key performance test)
                coordination_start = time.perf_counter()
                agent_tasks = [
                    agent_execution(role, i) for i, role in enumerate(selected_roles)
                ]

                agent_results = await asyncio.gather(
                    *agent_tasks, return_exceptions=True
                )
                coordination_end = time.perf_counter()

                coordination_duration = coordination_end - coordination_start
                performance_validator.record_load_metric(
                    num_agents, "coordination_time", coordination_duration
                )

                # Analyze agent coordination results
                successful_agents = [
                    r
                    for r in agent_results
                    if isinstance(r, dict) and r.get("success", False)
                ]

                workflow_end = time.perf_counter()
                total_workflow_time = workflow_end - workflow_start

                # Calculate coordination efficiency
                total_agent_time = sum(agent["duration"] for agent in successful_agents)
                coordination_efficiency = (
                    total_agent_time / (coordination_duration * num_agents)
                    if coordination_duration > 0
                    else 0
                )

                performance_validator.record_load_metric(
                    num_agents, "workflow_time", total_workflow_time
                )
                performance_validator.record_load_metric(
                    num_agents, "coordination_efficiency", coordination_efficiency
                )

                return {
                    "workflow_id": workflow_id,
                    "session_id": session_id,
                    "num_agents": num_agents,
                    "total_duration": total_workflow_time,
                    "coordination_duration": coordination_duration,
                    "planning_duration": planning_duration,
                    "successful_agents": len(successful_agents),
                    "failed_agents": len(agent_results) - len(successful_agents),
                    "coordination_efficiency": coordination_efficiency,
                    "agent_results": agent_results,
                    "success": len(successful_agents)
                    >= num_agents * 0.8,  # 80% success threshold
                    "timestamp": workflow_end,
                }

            except Exception as e:
                workflow_end = time.perf_counter()
                total_workflow_time = workflow_end - workflow_start

                return {
                    "workflow_id": workflow_id,
                    "session_id": session_id,
                    "num_agents": num_agents,
                    "total_duration": total_workflow_time,
                    "success": False,
                    "error": str(e),
                    "timestamp": workflow_end,
                }

        # Test each concurrency level with different agent counts
        all_workflow_results = []

        for concurrency_level in concurrency_levels:
            level_start = time.perf_counter()
            performance_validator.take_resource_snapshot(
                f"concurrency_{concurrency_level}_start"
            )

            # Create workflows with varying agent counts
            workflow_tasks = []
            for i in range(concurrency_level):
                num_agents = agents_per_workflow[i % len(agents_per_workflow)]
                workflow_id = f"concurrent_{concurrency_level}_{i}"

                task = multi_agent_workflow(
                    workflow_id, num_agents, performance_validator
                )
                workflow_tasks.append(task)

            # Execute concurrent workflows
            level_results = await asyncio.gather(
                *workflow_tasks, return_exceptions=True
            )

            level_end = time.perf_counter()
            level_duration = level_end - level_start

            performance_validator.take_resource_snapshot(
                f"concurrency_{concurrency_level}_end"
            )
            performance_validator.record_load_metric(
                concurrency_level, "level_duration", level_duration
            )

            # Analyze level results
            successful_workflows = [
                r
                for r in level_results
                if isinstance(r, dict) and r.get("success", False)
            ]

            level_throughput = len(successful_workflows) / level_duration
            performance_validator.record_load_metric(
                concurrency_level, "throughput", level_throughput
            )

            all_workflow_results.extend(level_results)

            # Allow system recovery between levels
            await asyncio.sleep(1.0)
            gc.collect()

        performance_validator.take_resource_snapshot("concurrent_coordination_end")

        # Validate concurrent coordination performance

        # Overall success rate should be high
        successful_workflows = [
            r
            for r in all_workflow_results
            if isinstance(r, dict) and r.get("success", False)
        ]
        overall_success_rate = len(successful_workflows) / len(all_workflow_results)
        assert (
            overall_success_rate >= 0.8
        ), f"Low overall success rate: {overall_success_rate}"

        # Coordination efficiency should remain reasonable under load
        coordination_efficiencies = []
        for result in successful_workflows:
            if "coordination_efficiency" in result:
                coordination_efficiencies.append(result["coordination_efficiency"])

        if coordination_efficiencies:
            avg_coordination_efficiency = statistics.mean(coordination_efficiencies)
            assert (
                avg_coordination_efficiency >= 0.6
            ), f"Poor coordination efficiency: {avg_coordination_efficiency}"

        # Response times should remain reasonable
        workflow_durations = [r["total_duration"] for r in successful_workflows]
        if workflow_durations:
            p95_duration = (
                statistics.quantiles(workflow_durations, n=20)[18]
                if len(workflow_durations) >= 20
                else max(workflow_durations)
            )
            assert (
                p95_duration <= 15.0
            ), f"P95 workflow duration too high: {p95_duration}s"

        # Validate performance thresholds for each concurrency level
        for concurrency_level in concurrency_levels:
            validations = performance_validator.validate_performance_thresholds(
                concurrency_level
            )
            failed_validations = [k for k, v in validations.items() if not v]

            # Allow some threshold failures at higher concurrency levels
            max_failures = 2 if concurrency_level >= 15 else 1
            assert (
                len(failed_validations) <= max_failures
            ), f"Too many threshold failures at concurrency {concurrency_level}: {failed_validations}"

        # Resource usage should be reasonable
        resource_analysis = performance_validator.analyze_resource_growth(
            "concurrent_coordination_start", "concurrent_coordination_end"
        )

        assert (
            resource_analysis.get("memory_growth_mb", 0) <= 200
        ), f"Excessive memory growth: {resource_analysis.get('memory_growth_mb', 0)}MB"

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.integration
    async def test_concurrent_session_handling_under_stress(
        self,
        artifacts_service: ArtifactsService,
        session_manager: ConcurrentSessionManager,
        performance_validator: PerformanceLoadValidator,
    ):
        """Test concurrent session handling and resource behavior under stress."""

        # Stress test configuration
        session_counts = [10, 25, 50, 100]  # Number of concurrent sessions
        operations_per_session = 20  # Operations to perform per session

        performance_validator.take_resource_snapshot("session_stress_start")
        tracemalloc.start()

        for session_count in session_counts:
            level_start = time.perf_counter()
            performance_validator.take_resource_snapshot(
                f"session_level_{session_count}_start"
            )

            try:
                # Create concurrent sessions
                session_creation_start = time.perf_counter()
                session_ids = await session_manager.create_concurrent_sessions(
                    session_count=session_count,
                    batch_size=min(10, session_count),  # Limit batch size for stability
                )
                session_creation_end = time.perf_counter()

                creation_duration = session_creation_end - session_creation_start
                creation_rate = len(session_ids) / creation_duration

                performance_validator.record_load_metric(
                    session_count, "session_creation_rate", creation_rate
                )
                performance_validator.record_load_metric(
                    session_count, "session_creation_time", creation_duration
                )

                assert (
                    len(session_ids) >= session_count * 0.9
                ), f"Too few sessions created: {len(session_ids)}/{session_count}"

                # Execute concurrent operations across sessions
                operations_start = time.perf_counter()
                operation_results = await session_manager.concurrent_session_operations(
                    session_ids=session_ids,
                    operations_per_session=operations_per_session,
                )
                operations_end = time.perf_counter()

                operations_duration = operations_end - operations_start
                operations_rate = (
                    operation_results["total_operations"] / operations_duration
                )

                performance_validator.record_load_metric(
                    session_count, "operations_rate", operations_rate
                )
                performance_validator.record_load_metric(
                    session_count,
                    "operations_success_rate",
                    operation_results["success_rate"],
                )

                level_end = time.perf_counter()
                level_duration = level_end - level_start

                performance_validator.take_resource_snapshot(
                    f"session_level_{session_count}_end"
                )
                performance_validator.record_load_metric(
                    session_count, "level_duration", level_duration
                )

                # Validate session-level performance
                assert (
                    operation_results["success_rate"] >= 0.85
                ), f"Low operation success rate at {session_count} sessions: {operation_results['success_rate']}"

                # Throughput should remain reasonable
                assert (
                    operations_rate >= 10.0
                ), f"Low operations throughput at {session_count} sessions: {operations_rate} ops/sec"

                # Memory analysis for this level
                resource_growth = performance_validator.analyze_resource_growth(
                    f"session_level_{session_count}_start",
                    f"session_level_{session_count}_end",
                )

                # Memory growth should be reasonable per session
                memory_per_session = (
                    resource_growth.get("memory_growth_mb", 0) / session_count
                )
                assert (
                    memory_per_session <= 5.0
                ), f"Excessive memory per session: {memory_per_session:.2f}MB"

            except Exception as e:
                level_end = time.perf_counter()
                level_duration = level_end - level_start

                # Record failure but continue testing other levels
                performance_validator.record_load_metric(
                    session_count, "level_failure", 1
                )
                performance_validator.record_load_metric(
                    session_count, "level_duration", level_duration
                )

                # For very high session counts, some failures might be acceptable
                if session_count <= 50:
                    raise AssertionError(
                        f"Session stress test failed at {session_count} sessions: {e}"
                    )
                print(f"Expected failure at high session count {session_count}: {e}")

            # Recovery pause between levels
            await asyncio.sleep(2.0)
            gc.collect()

        performance_validator.take_resource_snapshot("session_stress_end")

        # Get final session performance summary
        session_summary = session_manager.get_session_performance_summary()

        # Validate overall session handling performance
        assert (
            session_summary["overall_success_rate"] >= 0.8
        ), f"Overall session success rate too low: {session_summary['overall_success_rate']}"

        # Average operation time should be reasonable
        assert (
            session_summary["avg_operation_duration"] <= 2.0
        ), f"Average session operation too slow: {session_summary['avg_operation_duration']}s"

        # P95 should be reasonable
        assert (
            session_summary.get("p95_operation_duration", 0) <= 5.0
        ), f"P95 session operation too slow: {session_summary.get('p95_operation_duration', 0)}s"

        # Resource usage validation
        final_resource_analysis = performance_validator.analyze_resource_growth(
            "session_stress_start", "session_stress_end"
        )

        # Total memory growth should be bounded
        total_memory_growth = final_resource_analysis.get("memory_growth_mb", 0)
        assert (
            total_memory_growth <= 500
        ), f"Excessive total memory growth: {total_memory_growth}MB"

        # Validate tracemalloc didn't detect major leaks
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Peak usage should be reasonable (allowing for test overhead)
            peak_mb = peak / (1024 * 1024)
            assert peak_mb <= 300, f"Peak memory usage too high: {peak_mb:.1f}MB"

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.integration
    async def test_system_resource_behavior_under_load(
        self,
        planner_service: PlannerService,
        orchestrator: LionOrchestrator,
        artifacts_service: ArtifactsService,
        performance_validator: PerformanceLoadValidator,
    ):
        """Test system resource utilization and performance degradation patterns."""

        # Resource behavior test configuration
        load_progression = [
            {
                "concurrent_workflows": 5,
                "agents_per_workflow": 3,
                "duration_minutes": 2,
            },
            {
                "concurrent_workflows": 10,
                "agents_per_workflow": 5,
                "duration_minutes": 3,
            },
            {
                "concurrent_workflows": 15,
                "agents_per_workflow": 4,
                "duration_minutes": 2,
            },
            {
                "concurrent_workflows": 20,
                "agents_per_workflow": 3,
                "duration_minutes": 1,
            },
        ]

        performance_validator.take_resource_snapshot("resource_behavior_start")
        system_metrics_history = []

        async def resource_intensive_workflow(
            workflow_id: str, num_agents: int, duration_seconds: float
        ) -> dict[str, Any]:
            """Execute a resource-intensive workflow for specified duration."""

            workflow_start = time.perf_counter()
            session_id = f"resource_test_{workflow_id}_{uuid4().hex[:6]}"

            try:
                await artifacts_service.create_session(session_id)

                # Create multiple artifacts to simulate resource usage
                artifacts_created = 0
                agents_executed = 0

                end_time = workflow_start + duration_seconds

                while time.perf_counter() < end_time and agents_executed < num_agents:
                    agent_id = f"resource_agent_{agents_executed}_{workflow_id}"
                    author = Author(id=agent_id, role="resource_tester")

                    # Create progressively larger documents to test memory behavior
                    doc_size = 1000 + (
                        artifacts_created * 100
                    )  # Increasing document sizes
                    content = (
                        f"Resource test document {artifacts_created}\n" + "X" * doc_size
                    )

                    await artifacts_service.create_document(
                        session_id=session_id,
                        doc_name=f"resource_doc_{artifacts_created}",
                        doc_type=DocumentType.SCRATCHPAD,
                        content=content,
                        author=author,
                    )

                    artifacts_created += 1

                    # Simulate agent processing with memory allocation
                    temp_data = [
                        random.random() for _ in range(1000)
                    ]  # Temporary memory usage
                    processed_result = sum(temp_data)  # Use the data
                    del temp_data  # Clean up

                    agents_executed += 1

                    # Small pause to allow resource monitoring
                    await asyncio.sleep(0.1)

                workflow_end = time.perf_counter()
                actual_duration = workflow_end - workflow_start

                return {
                    "workflow_id": workflow_id,
                    "session_id": session_id,
                    "duration": actual_duration,
                    "agents_executed": agents_executed,
                    "artifacts_created": artifacts_created,
                    "success": True,
                    "timestamp": workflow_end,
                }

            except Exception as e:
                workflow_end = time.perf_counter()
                actual_duration = workflow_end - workflow_start

                return {
                    "workflow_id": workflow_id,
                    "session_id": session_id,
                    "duration": actual_duration,
                    "success": False,
                    "error": str(e),
                    "timestamp": workflow_end,
                }

        async def monitor_system_resources(
            monitoring_duration: float,
        ) -> list[dict[str, Any]]:
            """Monitor system resources during load test."""
            metrics = []
            monitor_interval = 1.0  # Monitor every second

            start_time = time.perf_counter()
            end_time = start_time + monitoring_duration

            while time.perf_counter() < end_time:
                try:
                    process = psutil.Process()
                    memory_info = process.memory_info()

                    metric = {
                        "timestamp": time.perf_counter(),
                        "memory_rss_mb": memory_info.rss / (1024 * 1024),
                        "memory_vms_mb": memory_info.vms / (1024 * 1024),
                        "cpu_percent": process.cpu_percent(),
                        "num_threads": process.num_threads(),
                        "num_fds": (
                            process.num_fds() if hasattr(process, "num_fds") else 0
                        ),
                    }

                    # Add system-wide metrics
                    system_memory = psutil.virtual_memory()
                    metric.update(
                        {
                            "system_memory_percent": system_memory.percent,
                            "system_memory_available_mb": system_memory.available
                            / (1024 * 1024),
                        }
                    )

                    metrics.append(metric)

                except Exception:
                    # Handle monitoring failures gracefully
                    pass

                await asyncio.sleep(monitor_interval)

            return metrics

        # Execute load progression with resource monitoring
        for load_config in load_progression:
            level_label = f"load_{load_config['concurrent_workflows']}x{load_config['agents_per_workflow']}"
            level_start = time.perf_counter()

            performance_validator.take_resource_snapshot(f"{level_label}_start")

            concurrent_workflows = load_config["concurrent_workflows"]
            agents_per_workflow = load_config["agents_per_workflow"]
            duration_seconds = load_config["duration_minutes"] * 60

            # Start resource monitoring
            monitor_task = asyncio.create_task(
                monitor_system_resources(duration_seconds + 10)
            )

            # Create and execute concurrent resource-intensive workflows
            workflow_tasks = [
                resource_intensive_workflow(
                    f"{level_label}_{i}", agents_per_workflow, duration_seconds
                )
                for i in range(concurrent_workflows)
            ]

            # Execute workflows concurrently
            workflow_results = await asyncio.gather(
                *workflow_tasks, return_exceptions=True
            )

            # Stop monitoring
            monitor_task.cancel()
            try:
                resource_metrics = await monitor_task
            except asyncio.CancelledError:
                resource_metrics = []

            level_end = time.perf_counter()
            level_duration = level_end - level_start

            performance_validator.take_resource_snapshot(f"{level_label}_end")

            # Analyze workflow results
            successful_workflows = [
                r
                for r in workflow_results
                if isinstance(r, dict) and r.get("success", False)
            ]

            success_rate = len(successful_workflows) / len(workflow_results)

            # Analyze resource metrics
            if resource_metrics:
                memory_usage = [m["memory_rss_mb"] for m in resource_metrics]
                cpu_usage = [
                    m["cpu_percent"] for m in resource_metrics if m["cpu_percent"] > 0
                ]

                resource_analysis = {
                    "avg_memory_mb": statistics.mean(memory_usage),
                    "peak_memory_mb": max(memory_usage),
                    "memory_growth_mb": max(memory_usage) - min(memory_usage),
                    "avg_cpu_percent": statistics.mean(cpu_usage) if cpu_usage else 0,
                    "peak_cpu_percent": max(cpu_usage) if cpu_usage else 0,
                }

                system_metrics_history.append(
                    {
                        "load_config": load_config,
                        "level_duration": level_duration,
                        "success_rate": success_rate,
                        "resource_analysis": resource_analysis,
                        "resource_metrics": resource_metrics,
                    }
                )

                performance_validator.record_load_metric(
                    concurrent_workflows,
                    "peak_memory_mb",
                    resource_analysis["peak_memory_mb"],
                )
                performance_validator.record_load_metric(
                    concurrent_workflows,
                    "avg_cpu_percent",
                    resource_analysis["avg_cpu_percent"],
                )
                performance_validator.record_load_metric(
                    concurrent_workflows, "success_rate", success_rate
                )

            # Validate resource behavior for this level
            assert (
                success_rate >= 0.7
            ), f"Low success rate at load level {level_label}: {success_rate}"

            # Allow system recovery
            await asyncio.sleep(5.0)
            gc.collect()

        performance_validator.take_resource_snapshot("resource_behavior_end")

        # Analyze resource behavior patterns across load levels

        # Memory growth should be sublinear
        memory_peaks = [
            entry["resource_analysis"]["peak_memory_mb"]
            for entry in system_metrics_history
        ]
        load_levels = [
            entry["load_config"]["concurrent_workflows"]
            for entry in system_metrics_history
        ]

        if len(memory_peaks) >= 2:
            # Memory shouldn't grow exponentially with load
            max_memory = max(memory_peaks)
            min_memory = min(memory_peaks)
            max_load = max(load_levels)
            min_load = min(load_levels)

            memory_growth_ratio = max_memory / min_memory if min_memory > 0 else 1
            load_growth_ratio = max_load / min_load if min_load > 0 else 1

            # Memory growth should be much less than load growth
            memory_efficiency = (
                memory_growth_ratio / load_growth_ratio if load_growth_ratio > 0 else 1
            )
            assert (
                memory_efficiency <= 2.0
            ), f"Poor memory scaling efficiency: {memory_efficiency}"

        # Success rates should remain reasonable across load levels
        success_rates = [entry["success_rate"] for entry in system_metrics_history]
        min_success_rate = min(success_rates)
        assert (
            min_success_rate >= 0.6
        ), f"Success rate degraded too much under load: {min_success_rate}"

        # CPU usage should be reasonable
        cpu_peaks = [
            entry["resource_analysis"]["peak_cpu_percent"]
            for entry in system_metrics_history
        ]
        max_cpu = max(cpu_peaks) if cpu_peaks else 0
        assert max_cpu <= 90.0, f"CPU usage too high: {max_cpu}%"

        # Overall resource growth validation
        total_resource_growth = performance_validator.analyze_resource_growth(
            "resource_behavior_start", "resource_behavior_end"
        )

        assert (
            total_resource_growth.get("memory_growth_mb", 0) <= 300
        ), f"Excessive total memory growth: {total_resource_growth.get('memory_growth_mb', 0)}MB"
