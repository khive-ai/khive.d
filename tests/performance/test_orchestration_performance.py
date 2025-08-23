"""Performance tests for orchestration service.

Comprehensive performance testing for the khive orchestration service including:
- Orchestrator initialization and session management
- Branch creation and management performance
- Atomic analysis operations (RequirementsAnalysis, CodeContextAnalysis, etc.)
- Flow planning and orchestration scaling
- Concurrent orchestration operations
- Memory usage profiling for complex orchestrations
- Quality gate performance evaluation
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from khive.services.composition.parts import ComposerRequest
from khive.services.orchestration.orchestrator import LionOrchestrator


class TestOrchestrationBenchmarks:
    """Benchmark orchestration core operations for performance baseline."""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark orchestrator initialization performance."""
        performance_profiler.start_measurement()

        initialization_times = []
        threshold = (
            performance_thresholds["orchestration"]["simple_operation_ms"] / 1000
        )

        # Test multiple initializations to get reliable metrics
        for i in range(10):
            start_time = time.perf_counter()

            orchestrator = LionOrchestrator(f"test_flow_{i}")

            # Mock the create_cc call to avoid external dependencies
            with patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc:
                mock_create_cc.return_value = Mock()
                await orchestrator.initialize(model="test-model", system="test system")

            end_time = time.perf_counter()
            init_time = end_time - start_time
            initialization_times.append(init_time)

            performance_profiler.record_operation(
                init_time, success=True, operation_type="orchestrator_init"
            )

            assert orchestrator.session is not None
            assert orchestrator.builder is not None
            assert orchestrator.flow_name == f"test_flow_{i}"

        performance_profiler.end_measurement()

        # Analyze performance
        avg_time = sum(initialization_times) / len(initialization_times)
        min_time = min(initialization_times)
        max_time = max(initialization_times)

        # Performance assertions
        assert avg_time < threshold, f"Average init time too slow: {avg_time:.6f}s"
        assert min_time < threshold * 0.5, (
            f"Minimum init time too slow: {min_time:.6f}s"
        )
        assert max_time < threshold * 2.0, (
            f"Maximum init time too slow: {max_time:.6f}s"
        )

        metrics = performance_profiler.get_comprehensive_metrics()
        print(
            f"Orchestrator init - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s"
        )
        print(f"Memory growth: {metrics.get('memory_growth_mb', 0):.2f}MB")

    @pytest.mark.asyncio
    async def test_branch_creation_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark branch creation performance."""
        orchestrator = LionOrchestrator("test_branch_perf")

        # Initialize with mocked dependencies
        with patch(
            "khive.services.orchestration.orchestrator.create_cc"
        ) as mock_create_cc:
            mock_create_cc.return_value = Mock()
            await orchestrator.initialize()

        performance_profiler.start_measurement()

        branch_creation_times = []
        threshold = (
            performance_thresholds["orchestration"]["complex_operation_ms"] / 1000
        )

        # Test branch creation with different configurations
        test_configs = [
            {"role": "researcher", "domains": "software-architecture"},
            {"role": "implementer", "domains": "backend-development,code-quality"},
            {"role": "tester", "domains": "testing-strategies"},
            {"role": "reviewer", "domains": "code-review,quality-assurance"},
        ]

        for i, config in enumerate(test_configs * 3):  # Test each config 3 times
            compose_request = ComposerRequest(
                role=config["role"],
                domains=config["domains"],
                context=f"Test context for branch {i}",
            )

            start_time = time.perf_counter()

            # Mock external dependencies
            with (
                patch(
                    "khive.services.orchestration.orchestrator.create_cc"
                ) as mock_create_cc,
                patch(
                    "khive.services.orchestration.orchestrator.composer_service"
                ) as mock_composer,
            ):
                mock_create_cc.return_value = Mock()
                mock_composer.handle_request.return_value = AsyncMock(
                    system_prompt=f"System prompt for {config['role']}"
                )

                try:
                    branch_id = await orchestrator.create_cc_branch(
                        compose_request, agent_suffix=f"_test_{i}"
                    )
                    success = True
                    assert branch_id is not None
                except Exception as e:
                    success = False
                    print(f"Branch creation failed: {e}")

            end_time = time.perf_counter()
            creation_time = end_time - start_time
            branch_creation_times.append(creation_time)

            performance_profiler.record_operation(
                creation_time,
                success=success,
                operation_type=f"branch_create_{config['role']}",
            )

        performance_profiler.end_measurement()

        # Analyze performance
        avg_time = sum(branch_creation_times) / len(branch_creation_times)
        min_time = min(branch_creation_times)
        max_time = max(branch_creation_times)

        assert avg_time < threshold, (
            f"Average branch creation time too slow: {avg_time:.6f}s"
        )
        assert max_time < threshold * 2.0, (
            f"Maximum branch creation time too slow: {max_time:.6f}s"
        )

        print(
            f"Branch creation - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s"
        )

    @pytest.mark.asyncio
    async def test_atomic_analysis_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark atomic analysis operations performance."""
        orchestrator = LionOrchestrator("test_atomic_perf")

        # Test all atomic analysis types
        atomic_types = list(LionOrchestrator.ATOMIC_ANALYSES.keys())
        performance_profiler.start_measurement()

        analysis_times = {}
        threshold = (
            performance_thresholds["orchestration"]["complex_operation_ms"] / 1000
        )

        for analysis_type in atomic_types:
            analysis_class = LionOrchestrator.ATOMIC_ANALYSES[analysis_type]

            # Test instantiation and basic operations
            times = []
            for i in range(5):
                start_time = time.perf_counter()

                try:
                    # Create instance of the analysis type
                    if hasattr(analysis_class, "__init__"):
                        # Create with minimal required fields
                        analysis_instance = analysis_class()
                        success = True
                    else:
                        success = False
                except Exception as e:
                    success = False
                    print(f"Failed to create {analysis_type}: {e}")

                end_time = time.perf_counter()
                operation_time = end_time - start_time
                times.append(operation_time)

                performance_profiler.record_operation(
                    operation_time,
                    success=success,
                    operation_type=f"atomic_analysis_{analysis_type}",
                )

            analysis_times[analysis_type] = {
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
            }

        performance_profiler.end_measurement()

        # Verify all analysis types perform within acceptable limits
        for analysis_type, metrics in analysis_times.items():
            assert metrics["avg"] < threshold, (
                f"{analysis_type} average time too slow: {metrics['avg']:.6f}s"
            )
            print(
                f"{analysis_type} - Avg: {metrics['avg']:.6f}s, Min: {metrics['min']:.6f}s, Max: {metrics['max']:.6f}s"
            )


class TestOrchestrationScalability:
    """Test orchestration performance scalability under increasing loads."""

    @pytest.mark.asyncio
    async def test_concurrent_orchestration_scaling(
        self, performance_profiler, load_test_runner, performance_thresholds
    ):
        """Test performance scaling with concurrent orchestration operations."""

        async def create_orchestrator_operation():
            """Single orchestration operation for load testing."""
            orchestrator = LionOrchestrator("concurrent_test")

            with patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc:
                mock_create_cc.return_value = Mock()
                await orchestrator.initialize()

                # Simulate some work
                await asyncio.sleep(0.001)  # Minimal async work
                return orchestrator

        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20, 50]
        scaling_results = {}

        for concurrent_ops in concurrency_levels:
            operations_per_task = 5

            results = await load_test_runner.run_async_load_test(
                create_orchestrator_operation,
                concurrent_tasks=concurrent_ops,
                operations_per_task=operations_per_task,
                ramp_up_seconds=1.0,
            )

            scaling_results[concurrent_ops] = {
                "throughput": results["throughput"],
                "avg_response_time": results["avg_response_time"],
                "success_rate": results["success_rate"],
                "total_operations": results["total_operations"],
            }

            print(
                f"Concurrency {concurrent_ops}: {results['throughput']:.2f} ops/sec, "
                f"avg time: {results['avg_response_time']:.6f}s, "
                f"success rate: {results['success_rate']:.4f}"
            )

        # Verify scaling characteristics
        baseline_throughput = scaling_results[1]["throughput"]
        min_threshold = performance_thresholds["orchestration"][
            "throughput_ops_per_sec"
        ]

        for concurrency, results in scaling_results.items():
            # All concurrency levels should maintain minimum throughput
            assert results["throughput"] >= min_threshold, (
                f"Throughput too low at {concurrency} concurrent ops: {results['throughput']:.2f} ops/sec"
            )

            # Success rate should remain high
            assert results["success_rate"] > 0.95, (
                f"Success rate too low at {concurrency} concurrent ops: {results['success_rate']:.4f}"
            )

    @pytest.mark.asyncio
    async def test_flow_planning_scalability(
        self, performance_profiler, performance_thresholds
    ):
        """Test flow planning performance with increasing complexity."""
        orchestrator = LionOrchestrator("flow_planning_test")

        performance_profiler.start_measurement()

        # Test different plan complexities
        complexity_levels = [
            {"phases": 1, "agents_per_phase": 1, "name": "simple"},
            {"phases": 2, "agents_per_phase": 2, "name": "moderate"},
            {"phases": 3, "agents_per_phase": 3, "name": "complex"},
            {"phases": 5, "agents_per_phase": 2, "name": "multi_phase"},
            {"phases": 2, "agents_per_phase": 5, "name": "high_concurrency"},
        ]

        planning_times = {}
        threshold = (
            performance_thresholds["orchestration"]["complex_operation_ms"] / 1000
        )

        for config in complexity_levels:
            times = []

            for i in range(3):  # Test each complexity 3 times
                start_time = time.perf_counter()

                try:
                    # Generate flow plans field (static method)
                    plans_description = {}
                    for phase in range(config["phases"]):
                        for agent in range(config["agents_per_phase"]):
                            plan_name = f"phase_{phase}_agent_{agent}"
                            plans_description[plan_name] = (
                                f"Plan for {plan_name} in {config['name']} scenario"
                            )

                    flow_plans_field = LionOrchestrator.generate_flow_plans_field(
                        **plans_description
                    )
                    success = flow_plans_field is not None

                except Exception as e:
                    success = False
                    print(f"Flow planning failed for {config['name']}: {e}")

                end_time = time.perf_counter()
                plan_time = end_time - start_time
                times.append(plan_time)

                performance_profiler.record_operation(
                    plan_time,
                    success=success,
                    operation_type=f"flow_planning_{config['name']}",
                )

            planning_times[config["name"]] = {
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "config": config,
            }

        performance_profiler.end_measurement()

        # Verify planning performance scales reasonably
        simple_time = planning_times["simple"]["avg"]
        complex_time = planning_times["complex"]["avg"]

        # Complex planning shouldn't be more than 10x slower than simple
        scaling_ratio = complex_time / simple_time if simple_time > 0 else 1
        assert scaling_ratio < 10.0, f"Flow planning scaling poor: {scaling_ratio:.2f}x"

        # All planning operations should complete within threshold
        for complexity, metrics in planning_times.items():
            assert metrics["avg"] < threshold, (
                f"Flow planning for {complexity} too slow: {metrics['avg']:.6f}s"
            )
            print(f"Flow planning {complexity} - Avg: {metrics['avg']:.6f}s")


class TestOrchestrationMemoryPerformance:
    """Test orchestration memory usage and performance."""

    @pytest.mark.asyncio
    async def test_memory_usage_scaling(
        self, performance_profiler, memory_monitor, performance_thresholds
    ):
        """Test memory usage scaling with orchestration complexity."""

        async def create_complex_orchestration(complexity_level):
            """Create orchestration with specified complexity."""
            orchestrator = LionOrchestrator(f"memory_test_{complexity_level}")

            with patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc:
                mock_create_cc.return_value = Mock()
                await orchestrator.initialize()

                # Create multiple branches to increase memory usage
                compose_requests = []
                for i in range(complexity_level):
                    request = ComposerRequest(
                        role="researcher",
                        domains=f"domain_{i}",
                        context=f"Complex context {i} "
                        * 100,  # Add substantial context
                    )
                    compose_requests.append(request)

                # Mock the branch creation to avoid external dependencies
                with patch.object(
                    orchestrator, "create_cc_branch"
                ) as mock_create_branch:
                    mock_create_branch.return_value = f"branch_id_{complexity_level}"

                    for request in compose_requests:
                        await orchestrator.create_cc_branch(request)

                return orchestrator

        performance_profiler.start_measurement()

        # Test different complexity levels
        complexity_levels = [1, 5, 10, 20]
        memory_results = {}
        memory_limit = performance_thresholds["orchestration"]["memory_limit_mb"]

        for complexity in complexity_levels:
            # Measure memory usage for this complexity level
            def memory_test_operation():
                return asyncio.run(create_complex_orchestration(complexity))

            memory_usage = memory_monitor(memory_test_operation)

            memory_results[complexity] = {
                "memory_delta_mb": memory_usage["memory_delta_mb"],
                "execution_time": memory_usage["execution_time"],
                "success": memory_usage["success"],
            }

            performance_profiler.record_operation(
                memory_usage["execution_time"],
                success=memory_usage["success"],
                operation_type=f"memory_test_complexity_{complexity}",
            )

            print(
                f"Complexity {complexity}: {memory_usage['memory_delta_mb']:.2f}MB, "
                f"time: {memory_usage['execution_time']:.6f}s"
            )

        performance_profiler.end_measurement()

        # Verify memory usage scaling
        for complexity, results in memory_results.items():
            # Memory usage should be reasonable for the complexity
            max_expected_memory = memory_limit * (
                complexity / 10.0
            )  # Scale with complexity
            assert results["memory_delta_mb"] < max_expected_memory, (
                f"Memory usage too high for complexity {complexity}: {results['memory_delta_mb']:.2f}MB"
            )

            assert results["success"], f"Memory test failed for complexity {complexity}"

    @pytest.mark.asyncio
    async def test_orchestration_memory_leak_detection(
        self, performance_profiler, memory_monitor
    ):
        """Test for memory leaks in repeated orchestration operations."""

        async def repeated_orchestration_cycle():
            """Single orchestration cycle that might leak memory."""
            orchestrator = LionOrchestrator("leak_test")

            with patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc:
                mock_create_cc.return_value = Mock()
                await orchestrator.initialize()

                # Simulate typical orchestration work
                compose_request = ComposerRequest(
                    role="implementer",
                    domains="backend-development",
                    context="Test context for leak detection",
                )

                with patch.object(
                    orchestrator, "create_cc_branch"
                ) as mock_create_branch:
                    mock_create_branch.return_value = "test_branch_id"
                    await orchestrator.create_cc_branch(compose_request)

                # Clean up references
                del orchestrator

                return True

        performance_profiler.start_measurement()

        # Measure memory usage over multiple iterations
        memory_measurements = []
        iterations = 50

        for i in range(iterations):

            def single_cycle():
                return asyncio.run(repeated_orchestration_cycle())

            memory_usage = memory_monitor(single_cycle)
            memory_measurements.append({
                "iteration": i,
                "memory_delta_mb": memory_usage["memory_delta_mb"],
                "execution_time": memory_usage["execution_time"],
                "success": memory_usage["success"],
            })

            performance_profiler.record_operation(
                memory_usage["execution_time"],
                success=memory_usage["success"],
                operation_type="memory_leak_test",
            )

            # Check for significant memory growth every 10 iterations
            if i > 0 and i % 10 == 0:
                recent_memory = [
                    m["memory_delta_mb"] for m in memory_measurements[-10:]
                ]
                avg_recent_memory = sum(recent_memory) / len(recent_memory)

                # Memory growth should stabilize after initial overhead
                if i > 20 and avg_recent_memory > 5.0:  # 5MB threshold
                    pytest.fail(
                        f"Potential memory leak detected: {avg_recent_memory:.2f}MB average growth at iteration {i}"
                    )

        performance_profiler.end_measurement()

        # Final analysis
        successful_operations = sum(1 for m in memory_measurements if m["success"])
        total_memory_growth = sum(
            m["memory_delta_mb"] for m in memory_measurements if m["success"]
        )
        avg_memory_per_operation = total_memory_growth / max(successful_operations, 1)

        print(
            f"Memory leak test - {successful_operations}/{iterations} successful operations"
        )
        print(f"Average memory per operation: {avg_memory_per_operation:.4f}MB")
        print(f"Total memory growth: {total_memory_growth:.2f}MB")

        # Assert no significant memory leaks
        assert avg_memory_per_operation < 1.0, (
            f"Potential memory leak: {avg_memory_per_operation:.4f}MB per operation"
        )
        assert successful_operations / iterations > 0.95, (
            f"Success rate too low: {successful_operations / iterations:.4f}"
        )


class TestOrchestrationStressTesting:
    """Stress testing for orchestration service under extreme conditions."""

    @pytest.mark.asyncio
    async def test_high_concurrency_stress(
        self, performance_profiler, stress_test_scenarios
    ):
        """Test orchestration under high concurrency stress."""
        concurrent_config = stress_test_scenarios["concurrent_stress"]

        async def stress_orchestration_operation():
            """High-stress orchestration operation."""
            orchestrator = LionOrchestrator("stress_test")

            with patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc:
                mock_create_cc.return_value = Mock()
                await orchestrator.initialize()

                # Simulate resource-intensive work
                await asyncio.sleep(0.01)  # Simulate some processing time

                return {"status": "completed"}

        performance_profiler.start_measurement()

        # Test high concurrency scenario
        thread_count = concurrent_config["thread_counts"][
            2
        ]  # Use moderate high concurrency
        duration = concurrent_config["duration_seconds"][1]  # Use moderate duration
        target_rate = concurrent_config["operation_rates"][
            1
        ]  # Use moderate target rate

        start_time = time.perf_counter()
        completed_operations = 0
        errors = []

        # Run operations for specified duration
        async def stress_worker():
            nonlocal completed_operations
            while time.perf_counter() - start_time < duration:
                try:
                    await stress_orchestration_operation()
                    completed_operations += 1

                    performance_profiler.record_operation(
                        time.perf_counter() - start_time,
                        success=True,
                        operation_type="stress_test",
                    )

                    # Rate limiting to avoid overwhelming system
                    await asyncio.sleep(1.0 / target_rate)

                except Exception as e:
                    errors.append(str(e))
                    performance_profiler.record_operation(
                        time.perf_counter() - start_time,
                        success=False,
                        operation_type="stress_test_error",
                    )

        # Run concurrent workers
        tasks = [asyncio.create_task(stress_worker()) for _ in range(thread_count)]
        await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.perf_counter() - start_time
        performance_profiler.end_measurement()

        # Analyze stress test results
        actual_throughput = completed_operations / total_time
        error_rate = len(errors) / max(completed_operations + len(errors), 1)

        print("Stress test results:")
        print(f"- Duration: {total_time:.2f}s")
        print(f"- Completed operations: {completed_operations}")
        print(f"- Errors: {len(errors)}")
        print(f"- Throughput: {actual_throughput:.2f} ops/sec")
        print(f"- Error rate: {error_rate:.4f}")

        # Verify system survived stress test
        assert error_rate < 0.1, f"Error rate too high under stress: {error_rate:.4f}"
        assert completed_operations > 0, "No operations completed during stress test"

        metrics = performance_profiler.get_comprehensive_metrics()
        assert metrics["success_rate"] > 0.9, (
            f"Success rate too low: {metrics['success_rate']:.4f}"
        )
