"""Scalability testing for khive system components.

This module provides comprehensive scalability tests including:
- Load testing scenarios with varying agent counts and workloads
- Database operation performance measurement under load
- Concurrent execution scaling tests
- System resource utilization monitoring
"""

import asyncio
import statistics
import time
from typing import Any
from unittest.mock import Mock, patch

import pytest

from khive.services.composition.parts import ComposerRequest
from khive.services.orchestration.orchestrator import LionOrchestrator


class ScalabilityTestRunner:
    """Advanced scalability test runner with resource monitoring."""

    def __init__(self):
        self.test_results = {}
        self.resource_snapshots = []

    def record_resource_snapshot(self, label: str):
        """Record system resource usage snapshot."""
        import psutil

        process = psutil.Process()
        snapshot = {
            "timestamp": time.perf_counter(),
            "label": label,
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "threads": process.num_threads(),
            "open_files": len(process.open_files())
            if hasattr(process, "open_files")
            else 0,
        }
        self.resource_snapshots.append(snapshot)
        return snapshot

    async def run_scalability_test(
        self,
        test_operation,
        scale_factors: list[int],
        operations_per_scale: int = 10,
        max_duration_seconds: int = 60,
    ) -> dict[str, Any]:
        """Run a scalability test across different scale factors."""
        results = {}

        for scale_factor in scale_factors:
            print(f"Testing scale factor: {scale_factor}")

            start_snapshot = self.record_resource_snapshot(
                f"start_scale_{scale_factor}"
            )
            start_time = time.perf_counter()

            # Run operations at this scale
            tasks = []
            for i in range(scale_factor):
                for j in range(operations_per_scale):
                    task = asyncio.create_task(
                        test_operation(f"scale_{scale_factor}_op_{i}_{j}")
                    )
                    tasks.append(task)

            # Wait for completion with timeout
            try:
                completed_results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=max_duration_seconds,
                )

                # Count successful operations
                successful_ops = sum(
                    1
                    for result in completed_results
                    if not isinstance(result, Exception)
                )
                failed_ops = len(completed_results) - successful_ops

            except asyncio.TimeoutError:
                # Cancel remaining tasks
                for task in tasks:
                    if not task.done():
                        task.cancel()
                completed_results = []
                successful_ops = 0
                failed_ops = len(tasks)

            end_time = time.perf_counter()
            end_snapshot = self.record_resource_snapshot(f"end_scale_{scale_factor}")

            total_time = end_time - start_time
            throughput = successful_ops / total_time if total_time > 0 else 0

            results[scale_factor] = {
                "total_operations": len(tasks),
                "successful_operations": successful_ops,
                "failed_operations": failed_ops,
                "success_rate": successful_ops / len(tasks) if tasks else 0,
                "total_time_seconds": total_time,
                "throughput_ops_per_sec": throughput,
                "avg_time_per_operation": total_time / len(tasks) if tasks else 0,
                "resource_usage": {
                    "cpu_delta": end_snapshot["cpu_percent"]
                    - start_snapshot["cpu_percent"],
                    "memory_delta_mb": end_snapshot["memory_mb"]
                    - start_snapshot["memory_mb"],
                    "threads_delta": end_snapshot["threads"]
                    - start_snapshot["threads"],
                },
            }

            print(
                f"Scale {scale_factor}: {successful_ops}/{len(tasks)} ops, "
                f"{throughput:.2f} ops/sec, {total_time:.2f}s"
            )

        return results

    def analyze_scalability_characteristics(
        self, results: dict[int, dict[str, Any]]
    ) -> dict[str, Any]:
        """Analyze scalability characteristics from test results."""
        scale_factors = sorted(results.keys())

        throughputs = [results[sf]["throughput_ops_per_sec"] for sf in scale_factors]
        success_rates = [results[sf]["success_rate"] for sf in scale_factors]
        avg_times = [results[sf]["avg_time_per_operation"] for sf in scale_factors]

        # Calculate scaling efficiency
        baseline_throughput = throughputs[0] if throughputs else 0
        scaling_efficiency = []

        for i, sf in enumerate(scale_factors):
            if i == 0:
                scaling_efficiency.append(1.0)
            else:
                expected_throughput = baseline_throughput * sf
                actual_throughput = throughputs[i]
                efficiency = (
                    actual_throughput / expected_throughput
                    if expected_throughput > 0
                    else 0
                )
                scaling_efficiency.append(efficiency)

        return {
            "scale_factors": scale_factors,
            "throughput_trend": "increasing"
            if throughputs[-1] > throughputs[0]
            else "decreasing",
            "max_throughput": max(throughputs) if throughputs else 0,
            "baseline_throughput": baseline_throughput,
            "scaling_efficiency": scaling_efficiency,
            "avg_scaling_efficiency": statistics.mean(scaling_efficiency[1:])
            if len(scaling_efficiency) > 1
            else 1.0,
            "success_rate_stability": statistics.stdev(success_rates)
            if len(success_rates) > 1
            else 0,
            "performance_degradation": {
                "throughput_drop_pct": (
                    (throughputs[0] - throughputs[-1]) / throughputs[0] * 100
                )
                if throughputs[0] > 0
                else 0,
                "response_time_increase": avg_times[-1] / avg_times[0]
                if avg_times[0] > 0
                else 1,
            },
        }


@pytest.mark.performance
class TestAgentOrchestrationScalability:
    """Test orchestration scalability with varying agent counts."""

    async def test_agent_count_scaling_performance(self, performance_profiler):
        """Test how performance scales with number of agents."""
        scalability_runner = ScalabilityTestRunner()

        async def create_orchestrator_with_agents(test_id: str):
            """Create orchestrator and simulate multiple agent operations."""
            orchestrator = LionOrchestrator(f"scaling_test_{test_id}")

            with patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_cc:
                mock_cc.return_value = Mock()
                await orchestrator.initialize()

                # Simulate agent creation and coordination
                compose_request = ComposerRequest(
                    role="implementer",
                    domains="backend-development",
                    context=f"Scaling test context {test_id}",
                )

                with patch.object(orchestrator, "create_cc_branch") as mock_branch:
                    mock_branch.return_value = f"branch_{test_id}"
                    await orchestrator.create_cc_branch(compose_request)

                    # Simulate some processing time
                    await asyncio.sleep(0.005)  # 5ms processing time

                return f"completed_{test_id}"

        # Test different agent count scales
        agent_scales = [1, 5, 10, 25, 50, 100]

        results = await scalability_runner.run_scalability_test(
            create_orchestrator_with_agents,
            scale_factors=agent_scales,
            operations_per_scale=2,  # 2 operations per agent
            max_duration_seconds=30,
        )

        # Analyze scaling characteristics
        analysis = scalability_runner.analyze_scalability_characteristics(results)

        print(f"Agent scaling analysis: {analysis}")

        # Verify scaling performance
        assert analysis["avg_scaling_efficiency"] > 0.5, (
            f"Poor scaling efficiency: {analysis['avg_scaling_efficiency']:.3f}"
        )

        assert analysis["success_rate_stability"] < 0.2, (
            f"Unstable success rates across scales: {analysis['success_rate_stability']:.3f}"
        )

        # Performance shouldn't degrade more than 50% at highest scale
        perf_degradation = analysis["performance_degradation"]["response_time_increase"]
        assert perf_degradation < 3.0, (
            f"Performance degradation too high: {perf_degradation:.2f}x slower"
        )

    async def test_concurrent_orchestration_workflows(self, load_test_runner):
        """Test concurrent orchestration workflows under load."""

        async def complex_orchestration_workflow():
            """Complex orchestration workflow for load testing."""
            orchestrator = LionOrchestrator("concurrent_workflow")

            with patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_cc:
                mock_cc.return_value = Mock()
                await orchestrator.initialize()

                # Simulate multi-phase workflow
                phases = [
                    ("analysis", "researcher"),
                    ("design", "architect"),
                    ("implementation", "implementer"),
                    ("testing", "tester"),
                    ("review", "reviewer"),
                ]

                workflow_results = []

                for phase_name, role in phases:
                    compose_request = ComposerRequest(
                        role=role,
                        domains=f"{phase_name}-domain",
                        context=f"Concurrent workflow {phase_name} phase",
                    )

                    with patch.object(orchestrator, "create_cc_branch") as mock_branch:
                        mock_branch.return_value = f"{phase_name}_branch"
                        result = await orchestrator.create_cc_branch(compose_request)
                        workflow_results.append(result)

                    # Simulate phase processing time
                    await asyncio.sleep(0.01)

                return {"phases_completed": len(workflow_results)}

        # Test different concurrency levels for workflows
        concurrency_levels = [1, 3, 5, 10, 15]
        workflow_results = {}

        for concurrency in concurrency_levels:
            results = await load_test_runner.run_async_load_test(
                complex_orchestration_workflow,
                concurrent_tasks=concurrency,
                operations_per_task=2,
                ramp_up_seconds=0.5,
            )

            workflow_results[concurrency] = {
                "throughput": results["throughput"],
                "avg_response_time": results["avg_response_time"],
                "success_rate": results["success_rate"],
                "total_operations": results["total_operations"],
            }

            print(
                f"Workflow concurrency {concurrency}: {results['throughput']:.2f} workflows/sec, "
                f"avg time: {results['avg_response_time'] * 1000:.0f}ms"
            )

        # Verify workflow scaling
        for concurrency, result in workflow_results.items():
            assert result["success_rate"] > 0.9, (
                f"Workflow success rate too low at concurrency {concurrency}: {result['success_rate']:.3f}"
            )

            # Response time should remain reasonable even at high concurrency
            max_acceptable_time = 2.0  # 2 seconds
            assert result["avg_response_time"] < max_acceptable_time, (
                f"Workflow response time too high at concurrency {concurrency}: {result['avg_response_time']:.3f}s"
            )


@pytest.mark.performance
class TestDatabaseOperationScalability:
    """Test database operation performance under varying loads."""

    async def test_data_serialization_scaling(self, large_dataset_generator):
        """Test data serialization performance with increasing data sizes."""
        scalability_runner = ScalabilityTestRunner()

        async def serialization_operation(test_id: str):
            """Data serialization operation for scaling tests."""
            # Extract size from test_id (format: scale_X_op_Y_Z where X is size in MB)
            size_mb = float(test_id.split("_")[1]) / 10  # Convert scale factor to MB

            dataset = large_dataset_generator(size_mb, "medium")

            # Simulate database serialization operations
            import json
            import pickle

            # Test JSON serialization
            start_time = time.perf_counter()
            json_data = json.dumps(dataset)
            json_time = time.perf_counter() - start_time

            # Test pickle serialization
            start_time = time.perf_counter()
            pickle_data = pickle.dumps(dataset)
            pickle_time = time.perf_counter() - start_time

            # Test deserialization
            start_time = time.perf_counter()
            json_result = json.loads(json_data)
            json_deserialize_time = time.perf_counter() - start_time

            start_time = time.perf_counter()
            pickle_result = pickle.loads(pickle_data)
            pickle_deserialize_time = time.perf_counter() - start_time

            return {
                "json_serialize_time": json_time,
                "pickle_serialize_time": pickle_time,
                "json_deserialize_time": json_deserialize_time,
                "pickle_deserialize_time": pickle_deserialize_time,
                "data_size_mb": size_mb,
            }

        # Test with different data sizes (scale factor * 0.1 MB)
        data_size_scales = [1, 5, 10, 25, 50]  # 0.1MB to 5MB

        results = await scalability_runner.run_scalability_test(
            serialization_operation,
            scale_factors=data_size_scales,
            operations_per_scale=3,
            max_duration_seconds=45,
        )

        # Analyze serialization scaling
        for scale_factor, result in results.items():
            size_mb = scale_factor * 0.1

            # Operations should complete successfully
            assert result["success_rate"] > 0.8, (
                f"Serialization success rate too low for {size_mb}MB: {result['success_rate']:.3f}"
            )

            # Throughput should remain reasonable
            min_throughput = 0.5  # At least 0.5 ops/sec for larger datasets
            if scale_factor <= 25:  # For datasets up to 2.5MB
                assert result["throughput_ops_per_sec"] >= min_throughput, (
                    f"Serialization throughput too low for {size_mb}MB: {result['throughput_ops_per_sec']:.3f} ops/sec"
                )

        print("Serialization scaling results:")
        for scale_factor, result in results.items():
            size_mb = scale_factor * 0.1
            print(
                f"  {size_mb}MB: {result['throughput_ops_per_sec']:.2f} ops/sec, "
                f"{result['avg_time_per_operation'] * 1000:.0f}ms avg"
            )

    async def test_concurrent_data_operations(self, performance_profiler):
        """Test concurrent data operations scaling."""

        async def concurrent_data_operation(operation_id: str):
            """Concurrent data operation for testing."""
            # Simulate database-like operations
            data_size = 1000  # 1000 records

            # Generate test data
            test_records = []
            for i in range(data_size):
                record = {
                    "id": f"{operation_id}_record_{i}",
                    "timestamp": time.time(),
                    "data": f"test_data_{i}" * 10,  # ~100 bytes per record
                    "metadata": {"operation": operation_id, "index": i},
                }
                test_records.append(record)

            # Simulate data processing operations
            start_time = time.perf_counter()

            # Filter operation
            filtered_records = [
                r for r in test_records if r["metadata"]["index"] % 2 == 0
            ]

            # Aggregation operation
            total_size = sum(len(str(record)) for record in filtered_records)

            # Sort operation
            sorted_records = sorted(filtered_records, key=lambda x: x["id"])

            processing_time = time.perf_counter() - start_time

            return {
                "records_processed": len(test_records),
                "records_filtered": len(filtered_records),
                "processing_time": processing_time,
                "total_data_size": total_size,
            }

        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20, 40]
        concurrent_results = {}

        performance_profiler.start_measurement()

        for concurrency in concurrency_levels:
            print(f"Testing data operation concurrency: {concurrency}")

            start_time = time.perf_counter()

            # Create concurrent tasks
            tasks = []
            for i in range(concurrency):
                task = asyncio.create_task(
                    concurrent_data_operation(f"concurrent_{concurrency}_{i}")
                )
                tasks.append(task)

            # Wait for completion
            results = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.perf_counter()
            total_time = end_time - start_time

            # Analyze results
            successful_results = [r for r in results if not isinstance(r, Exception)]
            failed_operations = len(results) - len(successful_results)

            if successful_results:
                avg_processing_time = statistics.mean([
                    r["processing_time"] for r in successful_results
                ])
                total_records = sum(r["records_processed"] for r in successful_results)
            else:
                avg_processing_time = 0
                total_records = 0

            concurrent_results[concurrency] = {
                "success_rate": len(successful_results) / len(results),
                "total_time": total_time,
                "avg_processing_time": avg_processing_time,
                "total_records_processed": total_records,
                "throughput_records_per_sec": total_records / total_time
                if total_time > 0
                else 0,
                "failed_operations": failed_operations,
            }

            performance_profiler.record_operation(
                total_time,
                success=failed_operations == 0,
                operation_type=f"concurrent_data_ops_{concurrency}",
            )

            print(
                f"  Success rate: {concurrent_results[concurrency]['success_rate']:.3f}, "
                f"Records/sec: {concurrent_results[concurrency]['throughput_records_per_sec']:.0f}"
            )

        performance_profiler.end_measurement()

        # Verify concurrent data operation scaling
        for concurrency, result in concurrent_results.items():
            assert result["success_rate"] > 0.95, (
                f"Data operation success rate too low at concurrency {concurrency}: {result['success_rate']:.3f}"
            )

            # Higher concurrency should process more records per second overall
            if concurrency > 1:
                baseline_throughput = concurrent_results[1][
                    "throughput_records_per_sec"
                ]
                scaling_factor = (
                    result["throughput_records_per_sec"] / baseline_throughput
                    if baseline_throughput > 0
                    else 0
                )

                # Should achieve at least 50% linear scaling efficiency
                expected_min_scaling = concurrency * 0.5
                assert scaling_factor >= expected_min_scaling, (
                    f"Poor throughput scaling at concurrency {concurrency}: {scaling_factor:.2f}x vs expected {expected_min_scaling:.2f}x"
                )


@pytest.mark.performance
class TestSystemResourceUtilization:
    """Test system resource utilization under different loads."""

    async def test_cpu_utilization_scaling(self, stress_test_scenarios):
        """Test CPU utilization under increasing computational loads."""
        scalability_runner = ScalabilityTestRunner()

        async def cpu_intensive_operation(operation_id: str):
            """CPU-intensive operation for testing."""
            # Simulate computational work
            iterations = 10000
            result = 0

            for i in range(iterations):
                # Mathematical operations to consume CPU
                result += i**0.5
                result = result % 1000000  # Keep numbers manageable

                # Yield control occasionally for async cooperation
                if i % 1000 == 0:
                    await asyncio.sleep(0)

            return {"result": result, "iterations": iterations}

        # Test different CPU load levels
        cpu_load_scales = [1, 5, 10, 20]  # Number of concurrent CPU operations
        cpu_results = {}

        for scale in cpu_load_scales:
            print(f"Testing CPU load scale: {scale}")

            start_snapshot = scalability_runner.record_resource_snapshot(
                f"cpu_start_{scale}"
            )
            start_time = time.perf_counter()

            # Run CPU-intensive operations
            tasks = []
            for i in range(scale):
                task = asyncio.create_task(cpu_intensive_operation(f"cpu_{scale}_{i}"))
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            end_time = time.perf_counter()
            end_snapshot = scalability_runner.record_resource_snapshot(
                f"cpu_end_{scale}"
            )

            total_time = end_time - start_time
            cpu_utilization = (
                end_snapshot["cpu_percent"] - start_snapshot["cpu_percent"]
            )

            cpu_results[scale] = {
                "total_time": total_time,
                "operations_completed": len(results),
                "cpu_utilization_delta": cpu_utilization,
                "throughput_ops_per_sec": len(results) / total_time
                if total_time > 0
                else 0,
            }

            print(
                f"  Scale {scale}: {cpu_utilization:.1f}% CPU delta, "
                f"{total_time:.2f}s, {len(results)} ops"
            )

        # Verify CPU scaling characteristics
        for scale, result in cpu_results.items():
            # All operations should complete
            assert result["operations_completed"] == scale, (
                f"Not all CPU operations completed at scale {scale}"
            )

            # CPU utilization should increase with scale (but may plateau due to system limits)
            if scale > 1:
                baseline_utilization = cpu_results[1]["cpu_utilization_delta"]
                if baseline_utilization > 0:
                    utilization_ratio = (
                        result["cpu_utilization_delta"] / baseline_utilization
                    )
                    # Should see at least some increase in CPU usage
                    assert utilization_ratio >= 0.8, (
                        f"CPU utilization not scaling properly at scale {scale}: {utilization_ratio:.2f}x"
                    )

    async def test_memory_utilization_scaling(self, large_dataset_generator):
        """Test memory utilization with increasing data loads."""
        scalability_runner = ScalabilityTestRunner()

        async def memory_intensive_operation(operation_id: str):
            """Memory-intensive operation for testing."""
            # Extract scale from operation_id
            scale_str = operation_id.split("_")[1]
            scale = int(scale_str)

            # Generate data proportional to scale
            dataset_size_mb = scale * 0.5  # 0.5MB per scale unit
            dataset = large_dataset_generator(dataset_size_mb, "medium")

            # Perform memory-intensive operations
            # Create additional data structures
            processed_data = []
            for i in range(scale * 100):  # More processing for higher scales
                processed_item = {
                    "id": i,
                    "source_data": dataset,
                    "computed_value": i**2,
                    "large_text": "memory_test_" * 50,  # ~500 bytes
                }
                processed_data.append(processed_item)

            # Simulate analysis operations
            total_items = len(processed_data)
            computed_sum = sum(item["computed_value"] for item in processed_data)

            return {
                "items_processed": total_items,
                "computed_sum": computed_sum,
                "dataset_size_mb": dataset_size_mb,
            }

        # Test different memory load scales
        memory_scales = [1, 3, 5, 8, 12]
        memory_results = {}

        for scale in memory_scales:
            print(f"Testing memory load scale: {scale}")

            start_snapshot = scalability_runner.record_resource_snapshot(
                f"memory_start_{scale}"
            )

            # Run memory-intensive operation
            result = await memory_intensive_operation(f"memory_{scale}_0")

            end_snapshot = scalability_runner.record_resource_snapshot(
                f"memory_end_{scale}"
            )

            memory_delta = end_snapshot["memory_mb"] - start_snapshot["memory_mb"]

            memory_results[scale] = {
                "memory_delta_mb": memory_delta,
                "items_processed": result["items_processed"],
                "dataset_size_mb": result["dataset_size_mb"],
                "memory_efficiency": result["items_processed"] / memory_delta
                if memory_delta > 0
                else 0,
            }

            print(
                f"  Scale {scale}: {memory_delta:.2f}MB used, "
                f"{result['items_processed']} items processed"
            )

            # Clean up to prevent accumulation
            del result
            import gc

            gc.collect()

        # Verify memory scaling characteristics
        for scale, result in memory_results.items():
            expected_min_memory = scale * 0.5  # Should use at least the dataset size
            assert result["memory_delta_mb"] >= expected_min_memory * 0.5, (
                f"Memory usage unexpectedly low at scale {scale}: {result['memory_delta_mb']:.2f}MB"
            )

            # Memory usage shouldn't grow exponentially
            max_expected_memory = scale * 10  # Allow up to 10MB per scale unit
            assert result["memory_delta_mb"] <= max_expected_memory, (
                f"Memory usage too high at scale {scale}: {result['memory_delta_mb']:.2f}MB"
            )

            # Should process a reasonable number of items
            min_items_expected = scale * 50  # At least 50 items per scale
            assert result["items_processed"] >= min_items_expected, (
                f"Too few items processed at scale {scale}: {result['items_processed']}"
            )

    async def test_mixed_resource_stress_scenarios(self, stress_test_scenarios):
        """Test mixed resource utilization under stress scenarios."""
        concurrent_config = stress_test_scenarios["concurrent_stress"]
        scalability_runner = ScalabilityTestRunner()

        async def mixed_stress_operation(operation_id: str):
            """Mixed CPU/memory/IO operation for stress testing."""
            # CPU-intensive component
            cpu_result = 0
            for i in range(1000):
                cpu_result += i**0.5
                if i % 100 == 0:
                    await asyncio.sleep(0)  # Yield control

            # Memory-intensive component
            large_data = []
            for i in range(500):  # Create ~50KB of data
                large_data.append({
                    "id": i,
                    "data": "x" * 100,  # 100 bytes per item
                    "computed": cpu_result + i,
                })

            # IO-like simulation (async operations)
            await asyncio.sleep(0.01)  # Simulate async IO

            # Data processing
            processed_count = len(large_data)
            total_computed = sum(item["computed"] for item in large_data)

            return {
                "cpu_result": cpu_result,
                "processed_count": processed_count,
                "total_computed": total_computed,
            }

        # Test different stress levels
        stress_levels = [5, 10, 20, 30]  # Concurrent operations
        stress_results = {}

        for stress_level in stress_levels:
            print(f"Testing mixed stress level: {stress_level}")

            start_snapshot = scalability_runner.record_resource_snapshot(
                f"stress_start_{stress_level}"
            )
            start_time = time.perf_counter()

            # Run concurrent mixed operations
            tasks = []
            for i in range(stress_level):
                task = asyncio.create_task(
                    mixed_stress_operation(f"stress_{stress_level}_{i}")
                )
                tasks.append(task)

            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=30,  # 30 second timeout
                )

                successful_results = [
                    r for r in results if not isinstance(r, Exception)
                ]
                failed_count = len(results) - len(successful_results)

            except asyncio.TimeoutError:
                successful_results = []
                failed_count = len(tasks)
                # Cancel remaining tasks
                for task in tasks:
                    if not task.done():
                        task.cancel()

            end_time = time.perf_counter()
            end_snapshot = scalability_runner.record_resource_snapshot(
                f"stress_end_{stress_level}"
            )

            total_time = end_time - start_time

            stress_results[stress_level] = {
                "successful_operations": len(successful_results),
                "failed_operations": failed_count,
                "success_rate": len(successful_results) / stress_level,
                "total_time": total_time,
                "throughput_ops_per_sec": len(successful_results) / total_time
                if total_time > 0
                else 0,
                "resource_usage": {
                    "cpu_delta": end_snapshot["cpu_percent"]
                    - start_snapshot["cpu_percent"],
                    "memory_delta_mb": end_snapshot["memory_mb"]
                    - start_snapshot["memory_mb"],
                    "threads_delta": end_snapshot["threads"]
                    - start_snapshot["threads"],
                },
            }

            print(
                f"  Stress {stress_level}: {len(successful_results)}/{stress_level} success, "
                f"{stress_results[stress_level]['throughput_ops_per_sec']:.2f} ops/sec"
            )

        # Verify stress test results
        for stress_level, result in stress_results.items():
            # Success rate should remain reasonable under stress
            min_success_rate = 0.7  # 70% minimum under stress
            assert result["success_rate"] >= min_success_rate, (
                f"Success rate too low under stress {stress_level}: {result['success_rate']:.3f}"
            )

            # Resource usage should be proportional to stress level
            memory_per_op = result["resource_usage"]["memory_delta_mb"] / max(
                result["successful_operations"], 1
            )
            assert memory_per_op < 5.0, (
                f"Memory usage per operation too high under stress {stress_level}: {memory_per_op:.2f}MB/op"
            )
