"""Memory profiling tests with tracemalloc integration.

This module provides comprehensive memory profiling tests including:
- Memory leak detection across service operations
- Memory usage pattern analysis
- Resource cleanup validation
- Memory growth trend analysis
"""

import asyncio
import gc
import statistics
import time
import tracemalloc
import weakref
from unittest.mock import AsyncMock, Mock, patch

import psutil
import pytest

from khive.services.artifacts.service import ArtifactsService
from khive.services.cache.service import CacheService
from khive.services.composition.agent_composer import AgentComposer
from khive.services.composition.parts import ComposerRequest
from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.plan.planner_service import PlannerService
from khive.services.session.session_service import SessionService


class MemoryLeakDetector:
    """Advanced memory leak detection and analysis."""

    def __init__(self):
        self.baseline_memory = 0
        self.measurements = []
        self.objects_tracked = []
        self.process = psutil.Process()

    def start_monitoring(self):
        """Start memory leak monitoring."""
        tracemalloc.start()
        gc.collect()  # Clean up before baseline
        self.baseline_memory = self.process.memory_info().rss

    def record_measurement(self, label: str = None):
        """Record a memory measurement point."""
        gc.collect()  # Force cleanup before measurement
        current_memory = self.process.memory_info().rss
        memory_delta = (current_memory - self.baseline_memory) / 1024 / 1024  # MB

        # Get tracemalloc statistics
        current, peak = tracemalloc.get_traced_memory()

        measurement = {
            "timestamp": time.perf_counter(),
            "label": label or f"measurement_{len(self.measurements)}",
            "memory_delta_mb": memory_delta,
            "traced_current_mb": current / 1024 / 1024,
            "traced_peak_mb": peak / 1024 / 1024,
            "total_objects": len(gc.get_objects()),
        }

        self.measurements.append(measurement)
        return measurement

    def add_object_tracking(self, obj, name: str):
        """Add object for weak reference tracking."""
        self.objects_tracked.append(
            {
                "name": name,
                "ref": weakref.ref(obj),
                "created_at": time.perf_counter(),
            }
        )

    def check_object_leaks(self) -> list:
        """Check for objects that should have been garbage collected."""
        leaks = []
        for tracked in self.objects_tracked:
            if tracked["ref"]() is not None:
                leaks.append(
                    {
                        "name": tracked["name"],
                        "age_seconds": time.perf_counter() - tracked["created_at"],
                    }
                )
        return leaks

    def analyze_memory_trend(self, window_size: int = 10) -> dict:
        """Analyze memory growth trends."""
        if len(self.measurements) < window_size:
            return {"trend": "insufficient_data"}

        recent_measurements = self.measurements[-window_size:]
        early_measurements = self.measurements[:window_size]

        recent_avg = statistics.mean(
            [m["memory_delta_mb"] for m in recent_measurements]
        )
        early_avg = statistics.mean([m["memory_delta_mb"] for m in early_measurements])

        trend_slope = recent_avg - early_avg

        # Calculate standard deviation for trend stability
        all_deltas = [m["memory_delta_mb"] for m in self.measurements]
        trend_stability = statistics.stdev(all_deltas) if len(all_deltas) > 1 else 0

        return {
            "trend": (
                "increasing"
                if trend_slope > 2.0
                else "stable" if abs(trend_slope) <= 2.0 else "decreasing"
            ),
            "trend_slope_mb": trend_slope,
            "trend_stability": trend_stability,
            "recent_avg_mb": recent_avg,
            "early_avg_mb": early_avg,
            "max_delta_mb": max(all_deltas) if all_deltas else 0,
            "measurements_count": len(self.measurements),
        }

    def stop_monitoring(self):
        """Stop memory leak monitoring."""
        tracemalloc.stop()


@pytest.mark.performance
class TestMemoryLeakDetection:
    """Memory leak detection tests for all major services."""

    async def test_orchestrator_memory_leaks(self, performance_profiler):
        """Test for memory leaks in orchestrator service operations."""
        leak_detector = MemoryLeakDetector()
        leak_detector.start_monitoring()

        try:
            leak_detector.record_measurement("baseline")

            # Perform repeated orchestrator operations
            for iteration in range(25):
                orchestrator = LionOrchestrator(f"leak_test_{iteration}")
                leak_detector.add_object_tracking(
                    orchestrator, f"orchestrator_{iteration}"
                )

                with patch(
                    "khive.services.orchestration.orchestrator.create_cc"
                ) as mock_cc:
                    mock_cc.return_value = Mock()
                    await orchestrator.initialize()

                    # Perform typical operations
                    compose_request = ComposerRequest(
                        role="implementer",
                        domains="backend-development",
                        context=f"Memory leak test context {iteration}",
                    )

                    with patch.object(orchestrator, "create_cc_branch") as mock_branch:
                        mock_branch.return_value = f"branch_{iteration}"
                        await orchestrator.create_cc_branch(compose_request)

                # Clean up references
                del orchestrator

                # Record memory every 5 iterations
                if iteration % 5 == 0:
                    measurement = leak_detector.record_measurement(
                        f"iteration_{iteration}"
                    )
                    print(
                        f"Iteration {iteration}: {measurement['memory_delta_mb']:.2f}MB delta"
                    )

                    # Early detection of severe leaks
                    if iteration > 10 and measurement["memory_delta_mb"] > 100:
                        pytest.fail(
                            f"Severe memory leak detected at iteration {iteration}: {measurement['memory_delta_mb']:.2f}MB"
                        )

            final_measurement = leak_detector.record_measurement("final")

            # Check for object leaks
            object_leaks = leak_detector.check_object_leaks()
            if object_leaks:
                print(
                    f"Object leaks detected: {len(object_leaks)} objects not garbage collected"
                )
                for leak in object_leaks:
                    print(f"  - {leak['name']}: {leak['age_seconds']:.2f}s old")

            # Analyze memory trend
            trend_analysis = leak_detector.analyze_memory_trend()
            print(f"Memory trend analysis: {trend_analysis}")

            # Assert no significant memory leaks
            assert (
                final_measurement["memory_delta_mb"] < 50
            ), f"Excessive memory growth: {final_measurement['memory_delta_mb']:.2f}MB"

            assert (
                trend_analysis["trend"] != "increasing"
            ), f"Memory leak trend detected: {trend_analysis['trend_slope_mb']:.2f}MB growth"

            assert (
                len(object_leaks) == 0
            ), f"Object leaks detected: {len(object_leaks)} objects not cleaned up"

        finally:
            leak_detector.stop_monitoring()

    async def test_composition_service_memory_leaks(self):
        """Test for memory leaks in agent composition service."""
        leak_detector = MemoryLeakDetector()
        leak_detector.start_monitoring()

        try:
            composer = AgentComposer()
            leak_detector.record_measurement("baseline")

            # Perform repeated composition operations
            for iteration in range(30):
                request = ComposerRequest(
                    role=["researcher", "implementer", "tester", "reviewer"][
                        iteration % 4
                    ],
                    domains=f"domain_{iteration % 7}",
                    context=f"Composition memory test {iteration} "
                    * 20,  # Large context
                )

                leak_detector.add_object_tracking(request, f"request_{iteration}")

                with patch(
                    "khive.services.composition.agent_composer.composer_service"
                ) as mock_service:
                    mock_service.handle_request.return_value = AsyncMock(
                        system_prompt=f"System prompt for iteration {iteration}"
                    )

                    result = await composer.compose_agent(request)
                    leak_detector.add_object_tracking(result, f"result_{iteration}")

                # Clean up references
                del request, result

                if iteration % 8 == 0:
                    measurement = leak_detector.record_measurement(
                        f"composition_{iteration}"
                    )
                    print(
                        f"Composition iteration {iteration}: {measurement['memory_delta_mb']:.2f}MB delta"
                    )

            final_measurement = leak_detector.record_measurement("composition_final")

            # Analyze results
            object_leaks = leak_detector.check_object_leaks()
            trend_analysis = leak_detector.analyze_memory_trend()

            print(f"Composition memory trend: {trend_analysis}")

            # Assert memory stability
            assert (
                final_measurement["memory_delta_mb"] < 30
            ), f"Composition service memory growth too high: {final_measurement['memory_delta_mb']:.2f}MB"

            assert (
                trend_analysis["max_delta_mb"] < 40
            ), f"Peak memory usage too high: {trend_analysis['max_delta_mb']:.2f}MB"

        finally:
            leak_detector.stop_monitoring()

    async def test_planning_service_memory_leaks(self, tmp_path):
        """Test for memory leaks in planning service operations."""
        leak_detector = MemoryLeakDetector()
        leak_detector.start_monitoring()

        try:
            planner = PlannerService()
            leak_detector.record_measurement("planning_baseline")

            # Test with various planning scenarios
            planning_scenarios = [
                "Simple feature implementation",
                "Complex system refactoring with multiple components",
                "Bug fix requiring analysis across multiple services",
                "Performance optimization with benchmarking requirements",
                "Security vulnerability remediation with testing validation",
            ]

            for iteration in range(20):
                scenario = planning_scenarios[iteration % len(planning_scenarios)]
                extended_scenario = (
                    f"{scenario} - iteration {iteration} " * 10
                )  # Large context

                with patch.object(planner, "analyze_issue") as mock_analyze:
                    # Simulate complex analysis result
                    mock_analyze.return_value = {
                        "complexity": ["simple", "medium", "complex"][iteration % 3],
                        "estimated_time": f"{iteration + 1}-{iteration + 3} hours",
                        "recommended_agents": [
                            f"agent_{i}" for i in range(iteration % 5 + 1)
                        ],
                        "dependencies": [f"dep_{i}" for i in range(iteration % 3)],
                        "risks": [f"risk_{i}" for i in range(iteration % 4)],
                        "detailed_analysis": extended_scenario,
                    }

                    result = await planner.analyze_issue(extended_scenario)
                    leak_detector.add_object_tracking(
                        result, f"planning_result_{iteration}"
                    )

                # Clean up
                del result

                if iteration % 6 == 0:
                    measurement = leak_detector.record_measurement(
                        f"planning_{iteration}"
                    )
                    print(
                        f"Planning iteration {iteration}: {measurement['memory_delta_mb']:.2f}MB delta"
                    )

            final_measurement = leak_detector.record_measurement("planning_final")

            # Analyze memory behavior
            trend_analysis = leak_detector.analyze_memory_trend()
            object_leaks = leak_detector.check_object_leaks()

            print(f"Planning service memory analysis: {trend_analysis}")

            # Validate memory stability
            assert (
                final_measurement["memory_delta_mb"] < 25
            ), f"Planning service memory growth: {final_measurement['memory_delta_mb']:.2f}MB"

            assert (
                trend_analysis["trend_stability"] < 15
            ), f"Planning service memory usage too unstable: {trend_analysis['trend_stability']:.2f}"

        finally:
            leak_detector.stop_monitoring()


@pytest.mark.performance
class TestMemoryUsagePatterns:
    """Test memory usage patterns under different load conditions."""

    async def test_concurrent_memory_usage_patterns(self, load_test_runner):
        """Test memory usage patterns under concurrent load."""
        leak_detector = MemoryLeakDetector()
        leak_detector.start_monitoring()

        try:

            async def memory_intensive_operation():
                """Memory-intensive operation for concurrent testing."""
                orchestrator = LionOrchestrator("concurrent_memory_test")

                with patch(
                    "khive.services.orchestration.orchestrator.create_cc"
                ) as mock_cc:
                    mock_cc.return_value = Mock()
                    await orchestrator.initialize()

                    # Create multiple composition requests
                    for i in range(5):
                        request = ComposerRequest(
                            role="implementer",
                            domains="backend-development",
                            context="Concurrent memory test " * 50,
                        )

                        with patch.object(
                            orchestrator, "create_cc_branch"
                        ) as mock_branch:
                            mock_branch.return_value = f"concurrent_branch_{i}"
                            await orchestrator.create_cc_branch(request)

                return "completed"

            leak_detector.record_measurement("concurrent_baseline")

            # Test different concurrency levels
            concurrency_levels = [1, 5, 10, 20]

            for concurrency in concurrency_levels:
                print(f"Testing concurrency level: {concurrency}")

                # Run concurrent load test
                results = await load_test_runner.run_async_load_test(
                    memory_intensive_operation,
                    concurrent_tasks=concurrency,
                    operations_per_task=3,
                    ramp_up_seconds=0.5,
                )

                measurement = leak_detector.record_measurement(
                    f"concurrency_{concurrency}"
                )

                print(
                    f"Concurrency {concurrency}: {measurement['memory_delta_mb']:.2f}MB, "
                    f"throughput: {results['throughput']:.2f} ops/sec"
                )

                # Verify memory usage scales reasonably with concurrency
                expected_max_memory = concurrency * 5  # 5MB per concurrent operation
                assert (
                    measurement["memory_delta_mb"] < expected_max_memory
                ), f"Memory usage too high for concurrency {concurrency}: {measurement['memory_delta_mb']:.2f}MB"

            # Final cleanup measurement
            gc.collect()
            await asyncio.sleep(1)  # Allow cleanup
            final_measurement = leak_detector.record_measurement("concurrent_final")

            # Memory should return close to baseline after operations
            assert (
                final_measurement["memory_delta_mb"] < 20
            ), f"Memory not properly cleaned up: {final_measurement['memory_delta_mb']:.2f}MB remaining"

        finally:
            leak_detector.stop_monitoring()

    async def test_large_dataset_memory_patterns(self, large_dataset_generator):
        """Test memory usage patterns with large datasets."""
        leak_detector = MemoryLeakDetector()
        leak_detector.start_monitoring()

        try:
            leak_detector.record_measurement("dataset_baseline")

            # Test different dataset sizes
            dataset_sizes = [0.5, 1, 2, 5, 10]  # MB

            for size_mb in dataset_sizes:
                print(f"Testing dataset size: {size_mb}MB")

                # Generate and process large dataset
                dataset = large_dataset_generator(size_mb, "complex")
                leak_detector.add_object_tracking(dataset, f"dataset_{size_mb}mb")

                # Simulate processing the dataset
                async def process_dataset(data):
                    """Simulate dataset processing operations."""
                    import json

                    # Serialize/deserialize (memory intensive)
                    serialized = json.dumps(data)
                    deserialized = json.loads(serialized)

                    # Simulate analysis operations
                    if isinstance(deserialized, dict):
                        keys_count = len(deserialized)
                        return {"processed_keys": keys_count}
                    return {"processed": True}

                result = await process_dataset(dataset)
                leak_detector.add_object_tracking(result, f"result_{size_mb}mb")

                measurement = leak_detector.record_measurement(f"dataset_{size_mb}mb")

                # Clean up dataset
                del dataset, result
                gc.collect()

                cleanup_measurement = leak_detector.record_measurement(
                    f"cleanup_{size_mb}mb"
                )

                print(
                    f"Dataset {size_mb}MB: peak {measurement['memory_delta_mb']:.2f}MB, "
                    f"after cleanup {cleanup_measurement['memory_delta_mb']:.2f}MB"
                )

                # Memory should scale reasonably with dataset size
                max_expected_memory = size_mb * 3  # Allow 3x overhead for processing
                assert (
                    measurement["memory_delta_mb"] < max_expected_memory
                ), f"Memory usage too high for {size_mb}MB dataset: {measurement['memory_delta_mb']:.2f}MB"

                # Memory should be mostly cleaned up after processing
                cleanup_threshold = (
                    size_mb * 0.5
                )  # 50% of dataset size should be cleaned up
                assert (
                    cleanup_measurement["memory_delta_mb"]
                    < measurement["memory_delta_mb"] - cleanup_threshold
                ), f"Insufficient memory cleanup for {size_mb}MB dataset"

            # Final analysis
            trend_analysis = leak_detector.analyze_memory_trend()
            print(f"Dataset processing memory analysis: {trend_analysis}")

            # Verify stable memory behavior
            assert (
                trend_analysis["trend_stability"] < 20
            ), f"Dataset processing memory too unstable: {trend_analysis['trend_stability']:.2f}"

        finally:
            leak_detector.stop_monitoring()


@pytest.mark.performance
class TestResourceCleanupValidation:
    """Validate proper cleanup of resources and connections."""

    async def test_service_lifecycle_cleanup(self, tmp_path):
        """Test that services properly clean up resources during lifecycle."""
        leak_detector = MemoryLeakDetector()
        leak_detector.start_monitoring()

        try:
            # Test multiple service types
            services_to_test = [
                ("artifacts", lambda: ArtifactsService(workspace_path=str(tmp_path))),
                ("cache", lambda: CacheService()),
                ("session", lambda: SessionService()),
            ]

            for service_name, service_factory in services_to_test:
                print(f"Testing {service_name} service cleanup")

                baseline = leak_detector.record_measurement(f"{service_name}_baseline")

                # Create and use service multiple times
                for iteration in range(10):
                    service = service_factory()
                    leak_detector.add_object_tracking(
                        service, f"{service_name}_{iteration}"
                    )

                    # Simulate typical service operations
                    if service_name == "artifacts":
                        # Test file operations
                        test_data = {"test": f"data_{iteration}"}
                        if hasattr(service, "store_artifact"):
                            with patch.object(service, "store_artifact") as mock_store:
                                mock_store.return_value = f"artifact_{iteration}"
                                await service.store_artifact(
                                    f"test_{iteration}", test_data
                                )

                    elif service_name == "cache":
                        # Test cache operations
                        if hasattr(service, "set"):
                            with patch.object(service, "set") as mock_set:
                                mock_set.return_value = True
                                await service.set(
                                    f"key_{iteration}", f"value_{iteration}"
                                )

                    elif service_name == "session":
                        # Test session operations
                        if hasattr(service, "create_session"):
                            with patch.object(service, "create_session") as mock_create:
                                mock_create.return_value = f"session_{iteration}"
                                await service.create_session(
                                    f"test_session_{iteration}"
                                )

                    # Clean up service reference
                    del service
                    gc.collect()

                final = leak_detector.record_measurement(f"{service_name}_final")

                # Verify resource cleanup
                memory_growth = final["memory_delta_mb"] - baseline["memory_delta_mb"]
                print(f"{service_name} service memory growth: {memory_growth:.2f}MB")

                assert (
                    memory_growth < 10
                ), f"{service_name} service poor cleanup: {memory_growth:.2f}MB growth"

            # Check for overall object leaks
            object_leaks = leak_detector.check_object_leaks()
            assert (
                len(object_leaks) < 5
            ), f"Too many object leaks: {len(object_leaks)} objects not cleaned up"

        finally:
            leak_detector.stop_monitoring()

    async def test_async_resource_cleanup(self):
        """Test cleanup of async resources and connections."""
        leak_detector = MemoryLeakDetector()
        leak_detector.start_monitoring()

        try:
            baseline = leak_detector.record_measurement("async_baseline")

            # Test async resource management
            async def async_resource_operations():
                """Operations that create and clean up async resources."""
                tasks = []

                # Create multiple async tasks
                for i in range(10):

                    async def async_task(task_id):
                        orchestrator = LionOrchestrator(f"async_task_{task_id}")
                        with patch(
                            "khive.services.orchestration.orchestrator.create_cc"
                        ) as mock_cc:
                            mock_cc.return_value = Mock()
                            await orchestrator.initialize()
                            await asyncio.sleep(0.01)  # Simulate work
                        return f"completed_{task_id}"

                    task = asyncio.create_task(async_task(i))
                    tasks.append(task)

                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks)

                # Clean up task references
                del tasks, results

                return "async_operations_completed"

            # Run async operations multiple times
            for round_num in range(5):
                result = await async_resource_operations()
                leak_detector.add_object_tracking(result, f"async_round_{round_num}")

                gc.collect()
                measurement = leak_detector.record_measurement(
                    f"async_round_{round_num}"
                )
                print(
                    f"Async round {round_num}: {measurement['memory_delta_mb']:.2f}MB"
                )

            # Final cleanup
            gc.collect()
            await asyncio.sleep(0.5)  # Allow async cleanup
            final = leak_detector.record_measurement("async_final")

            # Verify async resource cleanup
            total_growth = final["memory_delta_mb"] - baseline["memory_delta_mb"]
            assert (
                total_growth < 15
            ), f"Async resources not properly cleaned up: {total_growth:.2f}MB growth"

            # Check for leaked async objects
            object_leaks = leak_detector.check_object_leaks()
            leaked_async_objects = [
                leak for leak in object_leaks if "async" in leak["name"].lower()
            ]
            assert (
                len(leaked_async_objects) == 0
            ), f"Async object leaks detected: {len(leaked_async_objects)} objects"

        finally:
            leak_detector.stop_monitoring()
