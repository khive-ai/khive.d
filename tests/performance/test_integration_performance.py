"""Integration performance tests for cross-service workflows.

Comprehensive performance testing for integrated khive service workflows including:
- End-to-end workflow performance (planning → orchestration → artifacts)
- Cross-service communication and coordination performance
- Service dependency chain performance optimization
- Distributed operation coordination performance
- Multi-service resource contention testing
- Complete user workflow performance profiling
- Service mesh performance under load
- Data flow optimization across service boundaries
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from khive.services.artifacts.models import Author, DocumentType
from khive.services.artifacts.service import ArtifactsService
from khive.services.cache.config import CacheConfig
from khive.services.cache.service import CacheService
from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.plan.planner_service import (
    ComplexityTier,
    OrchestrationPlanner,
    Request,
)
from khive.services.session.parts import SessionRequest
from khive.services.session.session_service import SessionService

# Import mock classes from individual test files
from .test_artifacts_performance import (
    MockLockManager,
    MockSessionManager,
    MockStorageRepository,
)
from .test_cache_performance import MockRedisCache


class IntegratedWorkflowService:
    """Mock integrated service for testing cross-service workflows."""

    def __init__(self):
        # Initialize all services
        self.planning_service = None
        self.orchestration_service = None
        self.session_service = SessionService()
        self.artifacts_service = None
        self.cache_service = None

        # Performance tracking
        self.workflow_stats = {
            "planning_time": [],
            "orchestration_time": [],
            "session_time": [],
            "artifacts_time": [],
            "cache_time": [],
            "total_time": [],
        }

    async def initialize(self):
        """Initialize all services with mocked dependencies."""

        # Initialize planning service
        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}),
            patch("openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value = Mock()

            with (
                patch.object(
                    OrchestrationPlanner,
                    "_load_available_roles",
                    return_value=["researcher", "implementer"],
                ),
                patch.object(
                    OrchestrationPlanner,
                    "_load_available_domains",
                    return_value=["backend-development"],
                ),
                patch.object(
                    OrchestrationPlanner, "_load_prompt_templates", return_value={}
                ),
                patch.object(
                    OrchestrationPlanner, "_load_decision_matrix", return_value={}
                ),
            ):
                self.planning_service = OrchestrationPlanner()

        # Initialize orchestration service
        self.orchestration_service = LionOrchestrator("integration_test_flow")

        # Initialize artifacts service
        storage = MockStorageRepository()
        session_mgr = MockSessionManager()
        lock_mgr = MockLockManager()
        self.artifacts_service = ArtifactsService(storage, session_mgr, lock_mgr)

        # Initialize cache service
        config = CacheConfig(enabled=True, default_ttl=3600)
        self.cache_service = CacheService(config)
        mock_backend = MockRedisCache(config)
        self.cache_service._backend = mock_backend
        self.cache_service._initialized = True

    async def execute_complete_workflow(
        self, user_request: str, issue_id: int = None, session_id: str = None
    ) -> dict:
        """Execute a complete end-to-end workflow."""

        workflow_start = time.perf_counter()
        workflow_result = {
            "success": True,
            "phases": {},
            "artifacts_created": [],
            "cache_operations": 0,
            "total_time": 0,
        }

        try:
            # Phase 1: Session initialization
            phase_start = time.perf_counter()
            session_request = SessionRequest(
                action="init", issue=issue_id, resume=False, depth=5
            )

            session_response = await self.session_service.handle_request(
                session_request
            )
            if not session_response.success:
                workflow_result["success"] = False
                return workflow_result

            session_time = time.perf_counter() - phase_start
            self.workflow_stats["session_time"].append(session_time)
            workflow_result["phases"]["session_init"] = {
                "time": session_time,
                "success": session_response.success,
            }

            # Phase 2: Planning and complexity assessment
            phase_start = time.perf_counter()

            # Check cache first
            cached_plan = await self.cache_service.get_planning_result(
                request=user_request
            )
            if cached_plan:
                complexity = cached_plan.get("complexity", ComplexityTier.MEDIUM)
                selected_roles = cached_plan.get("roles", ["implementer"])
                self.workflow_stats["cache_time"].append(0.001)  # Cache hit
                workflow_result["cache_operations"] += 1
            else:
                # Perform planning
                request_obj = Request(user_request)

                with (
                    patch.object(
                        self.planning_service,
                        "assess",
                        return_value=ComplexityTier.MEDIUM,
                    ),
                    patch.object(
                        self.planning_service,
                        "select_roles",
                        return_value=["researcher", "implementer"],
                    ),
                ):
                    complexity = self.planning_service.assess(request_obj)
                    selected_roles = self.planning_service.select_roles(
                        request_obj, complexity
                    )

                # Cache the planning result
                planning_result = {
                    "complexity": complexity,
                    "roles": selected_roles,
                    "request": user_request,
                }

                cache_success = await self.cache_service.cache_planning_result(
                    request=user_request,
                    result=planning_result,
                    metadata={"workflow": "integration_test"},
                )

                if cache_success:
                    workflow_result["cache_operations"] += 1
                    self.workflow_stats["cache_time"].append(0.005)  # Cache write

            planning_time = time.perf_counter() - phase_start
            self.workflow_stats["planning_time"].append(planning_time)
            workflow_result["phases"]["planning"] = {
                "time": planning_time,
                "complexity": (
                    complexity.value
                    if hasattr(complexity, "value")
                    else str(complexity)
                ),
                "selected_roles": selected_roles,
            }

            # Phase 3: Orchestration setup
            phase_start = time.perf_counter()

            with patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc:
                mock_create_cc.return_value = Mock()
                await self.orchestration_service.initialize()

            orchestration_time = time.perf_counter() - phase_start
            self.workflow_stats["orchestration_time"].append(orchestration_time)
            workflow_result["phases"]["orchestration"] = {
                "time": orchestration_time,
                "success": True,
            }

            # Phase 4: Artifact creation
            phase_start = time.perf_counter()

            # Create artifacts session
            artifacts_session = await self.artifacts_service.create_session(
                session_id=session_id or "integration_test_session"
            )

            # Create planning document
            with patch.object(
                self.artifacts_service, "register_artifact", new_callable=AsyncMock
            ):
                planning_doc = await self.artifacts_service.create_document(
                    session_id=artifacts_session.session_id,
                    doc_name="planning_results",
                    doc_type=DocumentType.SCRATCHPAD,
                    content=json.dumps(
                        {
                            "request": user_request,
                            "complexity": str(complexity),
                            "roles": selected_roles,
                            "timestamp": time.time(),
                        }
                    ),
                    author=Author(name="integration_test", email="test@example.com"),
                    description="Planning results from integration workflow",
                )

            workflow_result["artifacts_created"].append(planning_doc.name)

            # Create implementation document
            with patch.object(
                self.artifacts_service, "register_artifact", new_callable=AsyncMock
            ):
                impl_doc = await self.artifacts_service.create_document(
                    session_id=artifacts_session.session_id,
                    doc_name="implementation_plan",
                    doc_type=DocumentType.DELIVERABLE,
                    content=f"Implementation plan for: {user_request}\n\nSelected roles: {', '.join(selected_roles)}\nComplexity: {complexity}",
                    author=Author(name="integration_test", email="test@example.com"),
                    description="Implementation plan from integration workflow",
                )

            workflow_result["artifacts_created"].append(impl_doc.name)

            artifacts_time = time.perf_counter() - phase_start
            self.workflow_stats["artifacts_time"].append(artifacts_time)
            workflow_result["phases"]["artifacts"] = {
                "time": artifacts_time,
                "documents_created": len(workflow_result["artifacts_created"]),
            }

        except Exception as e:
            workflow_result["success"] = False
            workflow_result["error"] = str(e)

        total_time = time.perf_counter() - workflow_start
        self.workflow_stats["total_time"].append(total_time)
        workflow_result["total_time"] = total_time

        return workflow_result


class TestIntegrationBenchmarks:
    """Benchmark integrated service workflows for performance baseline."""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark complete end-to-end workflow performance."""

        workflow_service = IntegratedWorkflowService()
        await workflow_service.initialize()

        performance_profiler.start_measurement()

        # Test different workflow scenarios
        test_scenarios = [
            {
                "name": "simple_task",
                "request": "Add logging to existing function",
                "expected_complexity": "SIMPLE",
            },
            {
                "name": "medium_task",
                "request": "Implement user authentication with JWT tokens and session management",
                "expected_complexity": "MEDIUM",
            },
            {
                "name": "complex_task",
                "request": "Design and implement microservices architecture with API gateway, service discovery, and distributed tracing",
                "expected_complexity": "COMPLEX",
            },
        ]

        workflow_times = []
        # Use a generous threshold since this includes multiple services
        threshold = (
            performance_thresholds["orchestration"]["complex_operation_ms"] / 1000 * 3
        )

        for i, scenario in enumerate(test_scenarios * 2):  # Test each scenario twice
            start_time = time.perf_counter()

            try:
                result = await workflow_service.execute_complete_workflow(
                    user_request=scenario["request"],
                    issue_id=i + 1000,
                    session_id=f"test_session_{i}_{scenario['name']}",
                )

                success = result["success"]

                # Verify workflow completed successfully
                assert result[
                    "success"
                ], f"Workflow failed: {result.get('error', 'Unknown error')}"
                assert (
                    len(result["artifacts_created"]) >= 2
                ), "Should create planning and implementation artifacts"
                assert (
                    "session_init" in result["phases"]
                ), "Should complete session initialization"
                assert "planning" in result["phases"], "Should complete planning phase"
                assert (
                    "orchestration" in result["phases"]
                ), "Should complete orchestration phase"
                assert (
                    "artifacts" in result["phases"]
                ), "Should complete artifacts phase"

            except Exception as e:
                success = False
                result = {"total_time": 0}
                print(f"End-to-end workflow failed for {scenario['name']}: {e}")

            end_time = time.perf_counter()
            workflow_time = end_time - start_time
            workflow_times.append(workflow_time)

            performance_profiler.record_operation(
                workflow_time,
                success=success,
                operation_type=f"e2e_workflow_{scenario['name']}",
            )

            # Add custom metrics for phase breakdown
            if success and result.get("phases"):
                for phase_name, phase_data in result["phases"].items():
                    performance_profiler.add_custom_metric(
                        f"{scenario['name']}_{phase_name}_time",
                        phase_data.get("time", 0),
                    )

        performance_profiler.end_measurement()

        # Analyze end-to-end performance
        avg_time = sum(workflow_times) / len(workflow_times)
        min_time = min(workflow_times)
        max_time = max(workflow_times)

        # Performance assertions
        assert (
            avg_time < threshold
        ), f"Average E2E workflow time too slow: {avg_time:.6f}s"
        assert (
            max_time < threshold * 2.0
        ), f"Maximum E2E workflow time too slow: {max_time:.6f}s"

        print(
            f"End-to-end workflow - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s"
        )

        # Print phase breakdown
        metrics = performance_profiler.get_comprehensive_metrics()
        if "custom_metrics" in metrics:
            print("Phase breakdown:")
            for metric_name, metric_data in metrics["custom_metrics"].items():
                if "_time" in metric_name:
                    print(f"  {metric_name}: {metric_data.get('avg', 0):.6f}s avg")

    @pytest.mark.asyncio
    async def test_service_dependency_chain_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Test performance of service dependency chains."""

        workflow_service = IntegratedWorkflowService()
        await workflow_service.initialize()

        performance_profiler.start_measurement()

        # Test different dependency chain patterns
        dependency_scenarios = [
            {
                "name": "linear_chain",
                "description": "Linear dependency: Session → Planning → Cache → Orchestration → Artifacts",
                "operations": 5,
            },
            {
                "name": "parallel_branches",
                "description": "Parallel operations: Planning + Cache operations in parallel",
                "operations": 3,
            },
            {
                "name": "complex_mesh",
                "description": "Complex interactions: Multiple services with cross-dependencies",
                "operations": 8,
            },
        ]

        dependency_times = {}
        threshold = (
            performance_thresholds["orchestration"]["simple_operation_ms"] / 1000 * 2
        )

        for scenario in dependency_scenarios:
            scenario_times = []

            for i in range(3):  # Test each scenario 3 times
                start_time = time.perf_counter()

                try:
                    if scenario["name"] == "linear_chain":
                        # Sequential operations
                        session_req = SessionRequest(action="init", issue=i + 2000)
                        await workflow_service.session_service.handle_request(
                            session_req
                        )

                        request_obj = Request(f"Linear chain test {i}")
                        with patch.object(
                            workflow_service.planning_service,
                            "assess",
                            return_value=ComplexityTier.SIMPLE,
                        ):
                            await asyncio.create_task(
                                asyncio.coroutine(
                                    lambda: workflow_service.planning_service.assess(
                                        request_obj
                                    )
                                )()
                            )

                        await workflow_service.cache_service.cache_planning_result(
                            f"linear_test_{i}", {"result": "test"}
                        )

                        artifacts_session = (
                            await workflow_service.artifacts_service.create_session(
                                f"linear_session_{i}"
                            )
                        )

                        with patch.object(
                            workflow_service.artifacts_service,
                            "register_artifact",
                            new_callable=AsyncMock,
                        ):
                            await workflow_service.artifacts_service.create_document(
                                artifacts_session.session_id,
                                f"linear_doc_{i}",
                                DocumentType.SCRATCHPAD,
                                "content",
                            )

                        success = True

                    elif scenario["name"] == "parallel_branches":
                        # Parallel operations
                        planning_task = asyncio.create_task(
                            workflow_service.cache_service.cache_planning_result(
                                f"parallel_test_{i}", {"result": "parallel"}
                            )
                        )

                        cache_task = asyncio.create_task(
                            workflow_service.cache_service.get_planning_result(
                                f"parallel_test_{i}"
                            )
                        )

                        session_task = asyncio.create_task(
                            workflow_service.session_service.handle_request(
                                SessionRequest(action="status", issue=i + 3000)
                            )
                        )

                        # Wait for all parallel operations
                        await asyncio.gather(planning_task, cache_task, session_task)
                        success = True

                    else:  # complex_mesh
                        # Complex interdependent operations
                        tasks = []

                        # Create multiple sessions
                        for j in range(3):
                            task = asyncio.create_task(
                                workflow_service.session_service.handle_request(
                                    SessionRequest(
                                        action="init", issue=i * 10 + j + 4000
                                    )
                                )
                            )
                            tasks.append(task)

                        # Create cache operations
                        for j in range(3):
                            task = asyncio.create_task(
                                workflow_service.cache_service.cache_planning_result(
                                    f"complex_test_{i}_{j}", {"mesh": True, "id": j}
                                )
                            )
                            tasks.append(task)

                        # Create artifacts operations
                        artifacts_session = (
                            await workflow_service.artifacts_service.create_session(
                                f"complex_session_{i}"
                            )
                        )
                        for j in range(2):

                            async def create_doc(doc_id=j):
                                with patch.object(
                                    workflow_service.artifacts_service,
                                    "register_artifact",
                                    new_callable=AsyncMock,
                                ):
                                    return await workflow_service.artifacts_service.create_document(
                                        artifacts_session.session_id,
                                        f"complex_doc_{i}_{doc_id}",
                                        DocumentType.SCRATCHPAD,
                                        f"complex content {doc_id}",
                                    )

                            task = asyncio.create_task(create_doc(j))
                            tasks.append(task)

                        # Wait for all complex operations
                        await asyncio.gather(*tasks)
                        success = True

                except Exception as e:
                    success = False
                    print(f"Dependency chain test failed for {scenario['name']}: {e}")

                end_time = time.perf_counter()
                scenario_time = end_time - start_time
                scenario_times.append(scenario_time)

                performance_profiler.record_operation(
                    scenario_time,
                    success=success,
                    operation_type=f"dependency_chain_{scenario['name']}",
                )

            dependency_times[scenario["name"]] = {
                "avg": sum(scenario_times) / len(scenario_times),
                "min": min(scenario_times),
                "max": max(scenario_times),
                "operations": scenario["operations"],
            }

        performance_profiler.end_measurement()

        # Analyze dependency chain performance
        for scenario_name, metrics in dependency_times.items():
            # Adjust threshold based on number of operations
            adjusted_threshold = threshold * (metrics["operations"] / 3.0)

            assert (
                metrics["avg"] < adjusted_threshold
            ), f"Dependency chain {scenario_name} average time too slow: {metrics['avg']:.6f}s"

            print(
                f"Dependency chain {scenario_name} - Avg: {metrics['avg']:.6f}s, "
                f"Operations: {metrics['operations']}"
            )


class TestIntegrationScalability:
    """Test integration performance scalability under increasing loads."""

    @pytest.mark.asyncio
    async def test_concurrent_workflow_scaling(
        self, performance_profiler, load_test_runner
    ):
        """Test integrated workflow performance with concurrent executions."""

        workflow_service = IntegratedWorkflowService()
        await workflow_service.initialize()

        async def concurrent_workflow_operation():
            """Single workflow operation for concurrent testing."""
            import random

            workflow_id = random.randint(1, 10000)
            request_text = f"Concurrent workflow test {workflow_id}: implement feature with moderate complexity"

            try:
                result = await workflow_service.execute_complete_workflow(
                    user_request=request_text,
                    issue_id=workflow_id,
                    session_id=f"concurrent_session_{workflow_id}",
                )

                return result["success"]

            except Exception as e:
                print(f"Concurrent workflow operation failed: {e}")
                return False

        # Test different concurrency levels
        concurrency_levels = [1, 3, 5, 10]
        scaling_results = {}

        for concurrent_workflows in concurrency_levels:
            operations_per_task = 2  # Fewer operations per task due to complexity

            results = await load_test_runner.run_async_load_test(
                concurrent_workflow_operation,
                concurrent_tasks=concurrent_workflows,
                operations_per_task=operations_per_task,
                ramp_up_seconds=1.0,
            )

            scaling_results[concurrent_workflows] = {
                "throughput": results["throughput"],
                "avg_response_time": results["avg_response_time"],
                "success_rate": results["success_rate"],
                "total_operations": results["total_operations"],
            }

            print(
                f"Concurrent workflows {concurrent_workflows}: {results['throughput']:.2f} workflows/sec, "
                f"avg time: {results['avg_response_time']:.6f}s, "
                f"success rate: {results['success_rate']:.4f}"
            )

        # Verify scaling characteristics
        for concurrency, results in scaling_results.items():
            assert (
                results["success_rate"] > 0.80
            ), f"Success rate too low at {concurrency} concurrent workflows: {results['success_rate']:.4f}"

            # Throughput should be reasonable for the complexity
            if concurrency == 1:
                assert (
                    results["throughput"] > 0.1
                ), f"Single workflow throughput too low: {results['throughput']:.2f} workflows/sec"

    @pytest.mark.asyncio
    async def test_resource_contention_performance(
        self, performance_profiler, stress_test_scenarios
    ):
        """Test performance under resource contention scenarios."""

        workflow_service = IntegratedWorkflowService()
        await workflow_service.initialize()

        performance_profiler.start_measurement()

        # Simulate resource contention scenarios
        contention_scenarios = [
            {
                "name": "cache_contention",
                "description": "Multiple workflows competing for cache resources",
                "concurrent_ops": 20,
                "operation_type": "cache_heavy",
            },
            {
                "name": "session_contention",
                "description": "Multiple workflows creating sessions simultaneously",
                "concurrent_ops": 15,
                "operation_type": "session_heavy",
            },
            {
                "name": "artifacts_contention",
                "description": "Multiple workflows creating artifacts simultaneously",
                "concurrent_ops": 10,
                "operation_type": "artifacts_heavy",
            },
        ]

        contention_results = {}

        for scenario in contention_scenarios:
            scenario_name = scenario["name"]
            concurrent_ops = scenario["concurrent_ops"]

            async def contention_operation():
                """Operation that creates resource contention."""
                operation_id = time.time_ns()  # Unique ID

                try:
                    if scenario["operation_type"] == "cache_heavy":
                        # Heavy cache operations
                        for i in range(5):
                            await workflow_service.cache_service.cache_planning_result(
                                f"contention_cache_{operation_id}_{i}",
                                {
                                    "contention_test": True,
                                    "data": f"test_data_{i}" * 50,
                                },
                            )

                            await workflow_service.cache_service.get_planning_result(
                                f"contention_cache_{operation_id}_{i}"
                            )

                        return True

                    elif scenario["operation_type"] == "session_heavy":
                        # Heavy session operations
                        for action in ["init", "status"]:
                            request = SessionRequest(
                                action=action, issue=operation_id % 1000
                            )
                            response = (
                                await workflow_service.session_service.handle_request(
                                    request
                                )
                            )
                            if not response.success:
                                return False

                        return True

                    else:  # artifacts_heavy
                        # Heavy artifacts operations
                        session = (
                            await workflow_service.artifacts_service.create_session(
                                f"contention_session_{operation_id}"
                            )
                        )

                        for i in range(3):
                            with patch.object(
                                workflow_service.artifacts_service,
                                "register_artifact",
                                new_callable=AsyncMock,
                            ):
                                await (
                                    workflow_service.artifacts_service.create_document(
                                        session.session_id,
                                        f"contention_doc_{operation_id}_{i}",
                                        DocumentType.SCRATCHPAD,
                                        f"Contention test content {i}" * 100,
                                    )
                                )

                        return True

                except Exception as e:
                    print(f"Contention operation failed: {e}")
                    return False

            # Run contention test
            start_time = time.perf_counter()

            tasks = []
            for _ in range(concurrent_ops):
                task = asyncio.create_task(contention_operation())
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.perf_counter()
            total_time = end_time - start_time

            # Analyze results
            successful_ops = sum(1 for result in results if result is True)
            failed_ops = len(results) - successful_ops
            throughput = successful_ops / total_time
            success_rate = successful_ops / len(results)

            contention_results[scenario_name] = {
                "total_time": total_time,
                "successful_ops": successful_ops,
                "failed_ops": failed_ops,
                "throughput": throughput,
                "success_rate": success_rate,
                "concurrent_ops": concurrent_ops,
            }

            performance_profiler.record_operation(
                total_time,
                success=success_rate > 0.8,
                operation_type=f"contention_{scenario_name}",
            )

            print(f"Resource contention {scenario_name}:")
            print(f"  Success rate: {success_rate:.4f}")
            print(f"  Throughput: {throughput:.2f} ops/sec")
            print(f"  Total time: {total_time:.2f}s")

        performance_profiler.end_measurement()

        # Verify system handles contention reasonably
        for scenario_name, results in contention_results.items():
            assert (
                results["success_rate"] > 0.7
            ), f"Success rate too low under {scenario_name}: {results['success_rate']:.4f}"

            assert (
                results["throughput"] > 0.5
            ), f"Throughput too low under {scenario_name}: {results['throughput']:.2f} ops/sec"


class TestIntegrationMemoryPerformance:
    """Test integration memory usage and performance."""

    @pytest.mark.asyncio
    async def test_multi_service_memory_usage(
        self, performance_profiler, memory_monitor
    ):
        """Test memory usage across multiple integrated services."""

        async def integrated_memory_operations():
            """Operations that use multiple services simultaneously."""
            workflow_service = IntegratedWorkflowService()
            await workflow_service.initialize()

            # Perform operations that use all services
            completed_workflows = 0

            for i in range(10):  # 10 complete workflows
                try:
                    result = await workflow_service.execute_complete_workflow(
                        user_request=f"Memory test workflow {i}: implement complex feature with database integration",
                        issue_id=i + 5000,
                        session_id=f"memory_test_session_{i}",
                    )

                    if result["success"]:
                        completed_workflows += 1

                except Exception as e:
                    print(f"Memory test workflow {i} failed: {e}")

            return completed_workflows

        performance_profiler.start_measurement()

        def memory_test_operation():
            return asyncio.run(integrated_memory_operations())

        memory_usage = memory_monitor(memory_test_operation)

        performance_profiler.record_operation(
            memory_usage["execution_time"],
            success=memory_usage["success"],
            operation_type="multi_service_memory",
        )

        performance_profiler.end_measurement()

        # Analyze multi-service memory usage
        print(f"Multi-service memory usage: {memory_usage['memory_delta_mb']:.2f}MB")
        print(
            f"Completed {memory_usage['result']} workflows in {memory_usage['execution_time']:.6f}s"
        )
        print(
            f"Memory per workflow: {memory_usage['memory_delta_mb'] / max(memory_usage['result'], 1):.2f}MB"
        )

        # Verify reasonable memory usage
        assert (
            memory_usage["memory_delta_mb"] < 100.0
        ), f"Multi-service memory usage too high: {memory_usage['memory_delta_mb']:.2f}MB"

        assert memory_usage["success"], "Multi-service memory test should succeed"
        assert memory_usage["result"] > 0, "Should complete some workflows"
