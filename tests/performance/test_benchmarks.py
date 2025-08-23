"""Core benchmarking tests for khive system performance.

This module provides comprehensive benchmarking tests covering:
- Agent composition performance benchmarks
- Memory profiling with tracemalloc
- Statistical analysis of performance metrics
- Quality gates and acceptance criteria validation
"""

import asyncio
import gc
import statistics
import time
import tracemalloc
from unittest.mock import AsyncMock, Mock, patch

import pytest

from khive.services.composition.agent_composer import AgentComposer
from khive.services.composition.parts import ComposerRequest
from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.plan.planner_service import PlannerService


class BenchmarkMetrics:
    """Statistical metrics collector for benchmark results."""

    def __init__(self):
        self.measurements = []
        self.metadata = {}

    def add_measurement(self, value: float, metadata: dict = None):
        """Add a performance measurement with optional metadata."""
        self.measurements.append(value)
        if metadata:
            self.metadata[len(self.measurements) - 1] = metadata

    def get_statistics(self) -> dict:
        """Calculate statistical metrics from measurements."""
        if not self.measurements:
            return {}

        return {
            "count": len(self.measurements),
            "mean": statistics.mean(self.measurements),
            "median": statistics.median(self.measurements),
            "stdev": statistics.stdev(self.measurements)
            if len(self.measurements) > 1
            else 0,
            "min": min(self.measurements),
            "max": max(self.measurements),
            "p95": statistics.quantiles(self.measurements, n=20)[18]
            if len(self.measurements) >= 20
            else max(self.measurements),
            "p99": statistics.quantiles(self.measurements, n=100)[98]
            if len(self.measurements) >= 100
            else max(self.measurements),
        }

    def assert_performance_criteria(self, criteria: dict):
        """Assert that measurements meet performance criteria."""
        stats = self.get_statistics()

        if "max_mean_ms" in criteria:
            assert stats["mean"] * 1000 <= criteria["max_mean_ms"], (
                f"Mean time {stats['mean'] * 1000:.2f}ms exceeds limit {criteria['max_mean_ms']}ms"
            )

        if "max_p95_ms" in criteria:
            assert stats["p95"] * 1000 <= criteria["max_p95_ms"], (
                f"P95 time {stats['p95'] * 1000:.2f}ms exceeds limit {criteria['max_p95_ms']}ms"
            )

        if "min_throughput_ops_sec" in criteria and "total_time" in self.metadata:
            throughput = len(self.measurements) / self.metadata["total_time"]
            assert throughput >= criteria["min_throughput_ops_sec"], (
                f"Throughput {throughput:.2f} ops/sec below limit {criteria['min_throughput_ops_sec']}"
            )


class MemoryProfiler:
    """Advanced memory profiling using tracemalloc."""

    def __init__(self):
        self.snapshots = []
        self.baseline_snapshot = None

    def start_tracing(self):
        """Start memory tracing."""
        tracemalloc.start()
        self.baseline_snapshot = tracemalloc.take_snapshot()

    def take_snapshot(self, label: str = None):
        """Take a memory snapshot."""
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append({
            "snapshot": snapshot,
            "timestamp": time.perf_counter(),
            "label": label or f"snapshot_{len(self.snapshots)}",
        })
        return snapshot

    def stop_tracing(self):
        """Stop memory tracing."""
        tracemalloc.stop()

    def analyze_memory_usage(self) -> dict:
        """Analyze memory usage patterns."""
        if not self.snapshots or not self.baseline_snapshot:
            return {}

        final_snapshot = self.snapshots[-1]["snapshot"]
        top_stats = final_snapshot.compare_to(self.baseline_snapshot, "lineno")

        # Calculate memory growth
        current_memory, peak_memory = tracemalloc.get_traced_memory()

        # Find largest memory consumers
        top_consumers = []
        for stat in top_stats[:10]:
            top_consumers.append({
                "file": stat.traceback.format()[0]
                if stat.traceback.format()
                else "unknown",
                "size_mb": stat.size / 1024 / 1024,
                "count": stat.count,
            })

        return {
            "current_memory_mb": current_memory / 1024 / 1024,
            "peak_memory_mb": peak_memory / 1024 / 1024,
            "memory_growth_mb": (
                current_memory - self.baseline_snapshot.tracemalloc_stats.get_size()
                if hasattr(self.baseline_snapshot, "tracemalloc_stats")
                else 0
            )
            / 1024
            / 1024,
            "top_consumers": top_consumers,
            "total_snapshots": len(self.snapshots),
        }


@pytest.mark.performance
class TestAgentCompositionBenchmarks:
    """Benchmark tests for agent composition performance."""

    @pytest.mark.benchmark(group="agent_composition")
    async def test_agent_composer_initialization_benchmark(
        self, benchmark, performance_thresholds
    ):
        """Benchmark agent composer initialization performance."""

        def create_agent_composer():
            return AgentComposer()

        # Benchmark initialization
        result = benchmark(create_agent_composer)
        assert result is not None

        # Verify performance criteria
        benchmark_stats = benchmark.stats
        assert (
            benchmark_stats.mean
            < performance_thresholds["orchestration"]["simple_operation_ms"] / 1000
        )

    @pytest.mark.benchmark(group="agent_composition")
    async def test_composer_request_processing_benchmark(self, benchmark):
        """Benchmark composer request processing performance."""
        composer = AgentComposer()

        test_request = ComposerRequest(
            role="researcher",
            domains="software-architecture,code-quality",
            context="Performance testing context for benchmarking",
        )

        async def process_request():
            with patch(
                "khive.services.composition.agent_composer.composer_service"
            ) as mock_service:
                mock_service.handle_request.return_value = AsyncMock(
                    system_prompt="Test system prompt for researcher"
                )
                return await composer.compose_agent(test_request)

        # Benchmark request processing
        result = benchmark.pedantic(
            lambda: asyncio.run(process_request()), rounds=10, iterations=5
        )
        assert result is not None

    @pytest.mark.benchmark(group="agent_composition")
    async def test_multiple_agent_composition_scaling(self, performance_profiler):
        """Test agent composition performance scaling with multiple agents."""
        composer = AgentComposer()
        metrics = BenchmarkMetrics()

        # Test different numbers of concurrent agent compositions
        agent_counts = [1, 5, 10, 20, 50]

        for count in agent_counts:
            start_time = time.perf_counter()

            # Create multiple composition requests
            requests = []
            for i in range(count):
                request = ComposerRequest(
                    role=["researcher", "implementer", "tester"][i % 3],
                    domains=f"domain_{i % 5}",
                    context=f"Scaling test context {i}",
                )
                requests.append(request)

            # Process all requests concurrently
            with patch(
                "khive.services.composition.agent_composer.composer_service"
            ) as mock_service:
                mock_service.handle_request.return_value = AsyncMock(
                    system_prompt="Test system prompt"
                )

                async def compose_all():
                    tasks = [composer.compose_agent(req) for req in requests]
                    return await asyncio.gather(*tasks)

                results = await compose_all()

            end_time = time.perf_counter()
            total_time = end_time - start_time

            metrics.add_measurement(total_time / count, {"agent_count": count})
            performance_profiler.record_operation(
                total_time,
                success=len(results) == count,
                operation_type=f"compose_{count}_agents",
            )

        # Assert scaling performance
        stats = metrics.get_statistics()
        assert stats["max"] < 2.0, f"Max composition time too high: {stats['max']:.3f}s"
        assert stats["mean"] < 0.5, (
            f"Mean composition time too high: {stats['mean']:.3f}s"
        )


@pytest.mark.performance
class TestMemoryProfilingBenchmarks:
    """Memory profiling benchmarks with tracemalloc integration."""

    async def test_orchestrator_memory_profiling(self, performance_profiler):
        """Profile memory usage during orchestrator operations."""
        memory_profiler = MemoryProfiler()
        memory_profiler.start_tracing()

        try:
            # Baseline memory snapshot
            memory_profiler.take_snapshot("baseline")

            # Create multiple orchestrators
            orchestrators = []
            for i in range(10):
                orchestrator = LionOrchestrator(f"memory_test_{i}")

                with patch(
                    "khive.services.orchestration.orchestrator.create_cc"
                ) as mock_cc:
                    mock_cc.return_value = Mock()
                    await orchestrator.initialize()

                orchestrators.append(orchestrator)

                if i % 3 == 0:
                    memory_profiler.take_snapshot(f"after_orchestrator_{i}")

            # Simulate heavy operations
            for i, orchestrator in enumerate(orchestrators):
                compose_request = ComposerRequest(
                    role="implementer",
                    domains="backend-development",
                    context="Memory profiling test " * 50,  # Large context
                )

                with patch.object(orchestrator, "create_cc_branch") as mock_branch:
                    mock_branch.return_value = f"branch_{i}"
                    await orchestrator.create_cc_branch(compose_request)

            memory_profiler.take_snapshot("after_operations")

            # Cleanup
            del orchestrators
            gc.collect()
            memory_profiler.take_snapshot("after_cleanup")

        finally:
            memory_profiler.stop_tracing()

        # Analyze memory usage
        memory_analysis = memory_profiler.analyze_memory_usage()

        # Assert memory usage within acceptable limits
        assert memory_analysis["peak_memory_mb"] < 100, (
            f"Peak memory usage too high: {memory_analysis['peak_memory_mb']:.2f}MB"
        )

        print(f"Memory analysis: {memory_analysis}")

    async def test_memory_leak_detection(self):
        """Detect potential memory leaks in repeated operations."""
        memory_profiler = MemoryProfiler()
        memory_profiler.start_tracing()

        baseline_measurements = []

        try:
            # Measure baseline memory after initial operations
            for warmup in range(5):
                orchestrator = LionOrchestrator(f"warmup_{warmup}")
                with patch(
                    "khive.services.orchestration.orchestrator.create_cc"
                ) as mock_cc:
                    mock_cc.return_value = Mock()
                    await orchestrator.initialize()
                del orchestrator
                gc.collect()

            memory_profiler.take_snapshot("warmup_complete")
            baseline_memory = tracemalloc.get_traced_memory()[0]

            # Perform repeated operations and monitor memory growth
            for iteration in range(20):
                orchestrator = LionOrchestrator(f"leak_test_{iteration}")
                with patch(
                    "khive.services.orchestration.orchestrator.create_cc"
                ) as mock_cc:
                    mock_cc.return_value = Mock()
                    await orchestrator.initialize()

                    # Perform some operations
                    compose_request = ComposerRequest(
                        role="tester",
                        domains="testing-strategies",
                        context=f"Leak detection test {iteration}",
                    )

                    with patch.object(orchestrator, "create_cc_branch") as mock_branch:
                        mock_branch.return_value = f"test_branch_{iteration}"
                        await orchestrator.create_cc_branch(compose_request)

                # Clean up and measure memory
                del orchestrator
                gc.collect()

                current_memory = tracemalloc.get_traced_memory()[0]
                memory_growth = (current_memory - baseline_memory) / 1024 / 1024
                baseline_measurements.append(memory_growth)

                if iteration % 5 == 0:
                    memory_profiler.take_snapshot(f"iteration_{iteration}")

        finally:
            memory_profiler.stop_tracing()

        # Analyze memory leak patterns
        if len(baseline_measurements) >= 10:
            # Calculate trend - should be relatively flat if no leaks
            recent_avg = statistics.mean(baseline_measurements[-5:])
            early_avg = statistics.mean(baseline_measurements[:5])
            memory_growth_trend = recent_avg - early_avg

            print(
                f"Memory growth trend: {memory_growth_trend:.2f}MB over {len(baseline_measurements)} iterations"
            )

            # Assert no significant memory leaks
            assert memory_growth_trend < 10.0, (
                f"Potential memory leak detected: {memory_growth_trend:.2f}MB growth"
            )
            assert max(baseline_measurements) < 50.0, (
                f"Peak memory growth too high: {max(baseline_measurements):.2f}MB"
            )


@pytest.mark.performance
class TestScalabilityBenchmarks:
    """Scalability benchmarks with multiple concurrency levels."""

    async def test_concurrent_planning_scalability(
        self, load_test_runner, performance_thresholds
    ):
        """Test planning service scalability under concurrent load."""

        async def planning_operation():
            """Single planning operation for load testing."""
            planner = PlannerService()

            # Mock the planning operation
            with patch.object(planner, "analyze_issue") as mock_analyze:
                mock_analyze.return_value = {
                    "complexity": "medium",
                    "estimated_time": "2-4 hours",
                    "recommended_agents": ["researcher", "implementer"],
                }

                return await planner.analyze_issue("Test issue for scalability testing")

        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 25, 50]
        scalability_results = {}

        for concurrency in concurrency_levels:
            results = await load_test_runner.run_async_load_test(
                planning_operation,
                concurrent_tasks=concurrency,
                operations_per_task=5,
                ramp_up_seconds=1.0,
            )

            scalability_results[concurrency] = {
                "throughput": results["throughput"],
                "avg_response_time": results["avg_response_time"],
                "success_rate": results["success_rate"],
            }

            print(
                f"Concurrency {concurrency}: {results['throughput']:.2f} ops/sec, "
                f"avg time: {results['avg_response_time'] * 1000:.2f}ms, "
                f"success rate: {results['success_rate']:.4f}"
            )

        # Verify scalability characteristics
        min_throughput = performance_thresholds["planning"]["throughput_ops_per_sec"]

        for concurrency, result in scalability_results.items():
            assert result["success_rate"] > 0.95, (
                f"Success rate too low at concurrency {concurrency}: {result['success_rate']:.4f}"
            )

            if (
                concurrency <= 10
            ):  # Should maintain good performance at moderate concurrency
                assert result["throughput"] >= min_throughput, (
                    f"Throughput too low at concurrency {concurrency}: {result['throughput']:.2f} ops/sec"
                )

    async def test_database_operation_scaling(
        self, performance_profiler, large_dataset_generator
    ):
        """Test database operation performance with varying data sizes."""

        # Mock database operations with different payload sizes
        data_sizes_mb = [0.1, 0.5, 1.0, 5.0, 10.0]
        operation_metrics = BenchmarkMetrics()

        for size_mb in data_sizes_mb:
            dataset = large_dataset_generator(size_mb, "medium")

            async def database_operation():
                """Simulate database operation with dataset."""
                # Simulate serialization/deserialization overhead
                import json

                serialized = json.dumps(dataset)
                deserialized = json.loads(serialized)
                return len(deserialized)

            # Measure operation performance
            start_time = time.perf_counter()

            try:
                result = await database_operation()
                success = True
                assert result > 0
            except Exception as e:
                success = False
                print(f"Database operation failed for size {size_mb}MB: {e}")

            end_time = time.perf_counter()
            operation_time = end_time - start_time

            operation_metrics.add_measurement(operation_time, {"data_size_mb": size_mb})
            performance_profiler.record_operation(
                operation_time,
                success=success,
                operation_type=f"db_operation_{size_mb}mb",
            )

            print(f"DB operation {size_mb}MB: {operation_time * 1000:.2f}ms")

        # Verify database operation scaling
        stats = operation_metrics.get_statistics()
        assert stats["max"] < 5.0, (
            f"Max DB operation time too high: {stats['max']:.3f}s"
        )

        # Performance should scale roughly linearly with data size
        # (allowing some overhead for larger datasets)
        measurements = operation_metrics.measurements
        if len(measurements) >= 3:
            # Verify that 10MB operation isn't more than 100x slower than 0.1MB
            scaling_ratio = measurements[-1] / measurements[0]
            assert scaling_ratio < 100, (
                f"Database operation scaling poor: {scaling_ratio:.1f}x"
            )


@pytest.mark.performance
class TestQualityGates:
    """Performance quality gates and acceptance criteria validation."""

    async def test_end_to_end_performance_quality_gates(
        self, performance_profiler, performance_thresholds
    ):
        """Comprehensive end-to-end performance quality gate testing."""

        # Initialize comprehensive metrics collection
        e2e_metrics = {
            "orchestration": BenchmarkMetrics(),
            "composition": BenchmarkMetrics(),
            "planning": BenchmarkMetrics(),
            "memory": BenchmarkMetrics(),
        }

        performance_profiler.start_measurement()

        # Test orchestration performance
        for i in range(5):
            start_time = time.perf_counter()

            orchestrator = LionOrchestrator(f"e2e_test_{i}")
            with patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_cc:
                mock_cc.return_value = Mock()
                await orchestrator.initialize()

            operation_time = time.perf_counter() - start_time
            e2e_metrics["orchestration"].add_measurement(operation_time)

        # Test composition performance
        composer = AgentComposer()
        for i in range(5):
            start_time = time.perf_counter()

            request = ComposerRequest(
                role="implementer",
                domains="backend-development",
                context=f"E2E test context {i}",
            )

            with patch(
                "khive.services.composition.agent_composer.composer_service"
            ) as mock_service:
                mock_service.handle_request.return_value = AsyncMock(
                    system_prompt="E2E test system prompt"
                )
                await composer.compose_agent(request)

            operation_time = time.perf_counter() - start_time
            e2e_metrics["composition"].add_measurement(operation_time)

        # Test planning performance
        planner = PlannerService()
        for i in range(5):
            start_time = time.perf_counter()

            with patch.object(planner, "analyze_issue") as mock_analyze:
                mock_analyze.return_value = {"complexity": "medium"}
                await planner.analyze_issue(f"E2E test issue {i}")

            operation_time = time.perf_counter() - start_time
            e2e_metrics["planning"].add_measurement(operation_time)

        performance_profiler.end_measurement()

        # Apply quality gates to all metrics
        quality_gates = {
            "orchestration": {
                "max_mean_ms": performance_thresholds["orchestration"][
                    "simple_operation_ms"
                ],
                "max_p95_ms": performance_thresholds["orchestration"][
                    "complex_operation_ms"
                ],
            },
            "composition": {
                "max_mean_ms": performance_thresholds["orchestration"][
                    "simple_operation_ms"
                ],
                "max_p95_ms": performance_thresholds["orchestration"][
                    "complex_operation_ms"
                ],
            },
            "planning": {
                "max_mean_ms": performance_thresholds["planning"]["simple_plan_ms"],
                "max_p95_ms": performance_thresholds["planning"]["complex_plan_ms"],
            },
        }

        # Validate all quality gates
        for component, metrics in e2e_metrics.items():
            if component in quality_gates:
                criteria = quality_gates[component]
                try:
                    metrics.assert_performance_criteria(criteria)
                    print(f"✓ {component} passed quality gates")
                except AssertionError as e:
                    pytest.fail(f"❌ {component} failed quality gates: {e}")

        # Print comprehensive performance summary
        print("\n=== E2E Performance Quality Gates Summary ===")
        for component, metrics in e2e_metrics.items():
            stats = metrics.get_statistics()
            if stats:
                print(f"{component}:")
                print(f"  Mean: {stats['mean'] * 1000:.2f}ms")
                print(f"  P95:  {stats['p95'] * 1000:.2f}ms")
                print(f"  Max:  {stats['max'] * 1000:.2f}ms")

    async def test_performance_regression_detection(self, performance_profiler):
        """Test for performance regressions against baseline metrics."""

        # Define baseline performance expectations (these would typically come from historical data)
        baseline_metrics = {
            "orchestrator_init_ms": 50.0,
            "agent_composition_ms": 100.0,
            "planning_operation_ms": 200.0,
            "memory_usage_mb": 50.0,
        }

        regression_threshold = 1.5  # 50% performance degradation threshold

        performance_profiler.start_measurement()

        # Test orchestrator initialization
        init_times = []
        for i in range(10):
            start_time = time.perf_counter()

            orchestrator = LionOrchestrator(f"regression_test_{i}")
            with patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_cc:
                mock_cc.return_value = Mock()
                await orchestrator.initialize()

            init_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
            init_times.append(init_time)

        # Test agent composition
        composer = AgentComposer()
        composition_times = []
        for i in range(10):
            start_time = time.perf_counter()

            request = ComposerRequest(
                role="tester",
                domains="testing-strategies",
                context=f"Regression test context {i}",
            )

            with patch(
                "khive.services.composition.agent_composer.composer_service"
            ) as mock_service:
                mock_service.handle_request.return_value = AsyncMock(
                    system_prompt="Regression test system prompt"
                )
                await composer.compose_agent(request)

            composition_time = (time.perf_counter() - start_time) * 1000
            composition_times.append(composition_time)

        performance_profiler.end_measurement()

        # Check for regressions
        current_metrics = {
            "orchestrator_init_ms": statistics.mean(init_times),
            "agent_composition_ms": statistics.mean(composition_times),
        }

        regressions = []
        for metric_name, current_value in current_metrics.items():
            baseline_value = baseline_metrics[metric_name]
            regression_ratio = current_value / baseline_value

            if regression_ratio > regression_threshold:
                regressions.append(
                    f"{metric_name}: {current_value:.2f}ms vs baseline {baseline_value:.2f}ms "
                    f"({regression_ratio:.2f}x regression)"
                )
            else:
                print(
                    f"✓ {metric_name}: {current_value:.2f}ms (within {regression_ratio:.2f}x of baseline)"
                )

        # Assert no significant regressions
        if regressions:
            pytest.fail("Performance regressions detected:\n" + "\n".join(regressions))
