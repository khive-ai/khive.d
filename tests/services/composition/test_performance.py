"""Performance tests for AgentComposer class.

This module provides comprehensive performance testing including:
- Scalability testing with increasing loads
- Memory usage monitoring
- Response time benchmarking
- Throughput measurement
- Resource utilization tracking
"""

import gc
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest
import yaml

from khive.services.composition.agent_composer import AgentComposer


class TestPerformanceBenchmarks:
    """Benchmark core operations for performance baseline."""

    def test_role_loading_performance(self, temp_dir):
        """Benchmark role loading performance."""
        composer = AgentComposer(str(temp_dir))

        # Create test role
        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()

        role_data = {
            "identity": {"id": "perf_test", "type": "performance"},
            "role": "Performance test role",
            "capabilities": ["test", "benchmark", "measure"],
        }
        role_file = roles_dir / "perf_test.yaml"
        role_file.write_text(yaml.dump(role_data))

        # Warm up
        for _ in range(5):
            composer.load_agent_role("perf_test")

        # Benchmark
        times = []
        for _ in range(100):
            start_time = time.perf_counter()
            result = composer.load_agent_role("perf_test")
            end_time = time.perf_counter()

            times.append(end_time - start_time)
            assert result["identity"]["id"] == "perf_test"

        # Analyze performance
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        # Performance assertions (adjust based on expected performance)
        assert avg_time < 0.010, f"Average load time too slow: {avg_time:.6f}s"
        assert min_time < 0.005, f"Minimum load time too slow: {min_time:.6f}s"
        assert max_time < 0.050, f"Maximum load time too slow: {max_time:.6f}s"

        print(
            f"Role loading - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s"
        )

    def test_domain_loading_performance(self, temp_dir):
        """Benchmark domain loading performance."""
        composer = AgentComposer(str(temp_dir))

        # Create test domain
        domains_dir = temp_dir / "domains"
        domains_dir.mkdir()

        domain_data = {
            "domain": {"id": "perf_domain"},
            "knowledge_patterns": {"patterns": [f"pattern_{i}" for i in range(50)]},
            "decision_rules": {"rules": [f"rule_{i}" for i in range(30)]},
        }
        domain_file = domains_dir / "perf_domain.yaml"
        domain_file.write_text(yaml.dump(domain_data))

        # Warm up
        for _ in range(5):
            composer.load_domain_expertise("perf_domain")

        # Benchmark
        times = []
        for _ in range(100):
            start_time = time.perf_counter()
            result = composer.load_domain_expertise("perf_domain")
            end_time = time.perf_counter()

            times.append(end_time - start_time)
            assert result["domain"]["id"] == "perf_domain"

        # Analyze performance
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        assert avg_time < 0.010, f"Average domain load time too slow: {avg_time:.6f}s"
        assert min_time < 0.005, f"Minimum domain load time too slow: {min_time:.6f}s"
        assert max_time < 0.050, f"Maximum domain load time too slow: {max_time:.6f}s"

        print(
            f"Domain loading - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s"
        )

    def test_composition_performance(self, temp_dir):
        """Benchmark agent composition performance."""
        composer = AgentComposer(str(temp_dir))

        # Setup test data
        self._create_performance_test_data(temp_dir)

        # Warm up
        for _ in range(5):
            composer.compose_agent("perf_role", "perf_domain")

        # Benchmark single domain composition
        single_times = []
        for _ in range(50):
            start_time = time.perf_counter()
            result = composer.compose_agent("perf_role", "perf_domain")
            end_time = time.perf_counter()

            single_times.append(end_time - start_time)
            assert result["identity"]["id"] == "perf_role"

        # Benchmark multi-domain composition
        multi_times = []
        for _ in range(25):
            start_time = time.perf_counter()
            result = composer.compose_agent("perf_role", "perf_domain,perf_domain2")
            end_time = time.perf_counter()

            multi_times.append(end_time - start_time)
            assert len(result["domains"]) == 2

        # Analyze performance
        single_avg = sum(single_times) / len(single_times)
        multi_avg = sum(multi_times) / len(multi_times)

        assert (
            single_avg < 0.020
        ), f"Single domain composition too slow: {single_avg:.6f}s"
        assert multi_avg < 0.050, f"Multi domain composition too slow: {multi_avg:.6f}s"

        print(f"Composition - Single: {single_avg:.6f}s, Multi: {multi_avg:.6f}s")

    def _create_performance_test_data(self, temp_dir):
        """Create test data for performance benchmarks."""
        # Create role
        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()

        role_data = {
            "identity": {"id": "perf_role", "type": "performance"},
            "role": "Performance test role",
        }
        (roles_dir / "perf_role.yaml").write_text(yaml.dump(role_data))

        # Create domains
        domains_dir = temp_dir / "domains"
        domains_dir.mkdir()

        for i in range(1, 3):
            domain_data = {
                "domain": {"id": f"perf_domain{i if i > 1 else ''}"},
                "knowledge_patterns": {"patterns": [f"pattern_{j}" for j in range(20)]},
                "decision_rules": {"rules": [f"rule_{j}" for j in range(15)]},
            }
            (domains_dir / f"perf_domain{i if i > 1 else ''}.yaml").write_text(
                yaml.dump(domain_data)
            )


class TestScalabilityPerformance:
    """Test performance scalability under increasing loads."""

    def test_concurrent_operation_scaling(self, temp_dir):
        """Test performance scaling with concurrent operations."""
        composer = AgentComposer(str(temp_dir))

        # Setup test data
        self._setup_scaling_test_data(temp_dir)

        thread_counts = [1, 2, 4, 8, 16]
        scaling_results = {}

        for thread_count in thread_counts:
            operations_per_thread = 20

            start_time = time.perf_counter()

            def worker():
                results = []
                for i in range(operations_per_thread):
                    role_name = f"scale_role_{i % 5}"  # Cycle through 5 roles
                    result = composer.load_agent_role(role_name)
                    results.append(result)
                return results

            # Run concurrent operations
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [executor.submit(worker) for _ in range(thread_count)]
                all_results = []
                for future in as_completed(futures):
                    thread_results = future.result()
                    all_results.extend(thread_results)

            end_time = time.perf_counter()
            total_time = end_time - start_time
            total_ops = thread_count * operations_per_thread
            throughput = total_ops / total_time

            scaling_results[thread_count] = {
                "total_time": total_time,
                "throughput": throughput,
                "avg_time_per_op": total_time / total_ops,
                "successful_ops": len(all_results),
            }

            print(
                f"Threads: {thread_count}, Throughput: {throughput:.2f} ops/sec, "
                f"Avg time: {total_time / total_ops:.6f}s"
            )

        # Verify scaling characteristics
        baseline_throughput = scaling_results[1]["throughput"]

        for thread_count in [2, 4, 8]:
            current_throughput = scaling_results[thread_count]["throughput"]
            scaling_factor = current_throughput / baseline_throughput

            # Should achieve some level of scaling (not necessarily linear)
            min_expected_scaling = min(
                thread_count * 0.6, 4.0
            )  # At least 60% efficiency up to 4x
            assert (
                scaling_factor >= min_expected_scaling
            ), f"Poor scaling at {thread_count} threads: {scaling_factor:.2f}x vs expected {min_expected_scaling:.2f}x"

    def test_large_dataset_performance(self, temp_dir):
        """Test performance with large datasets."""
        composer = AgentComposer(str(temp_dir))

        # Create large role files
        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()
        domains_dir = temp_dir / "domains"
        domains_dir.mkdir()

        # Create roles with varying sizes
        role_sizes = [1, 10, 50, 100]  # KB
        load_times = {}

        for size_kb in role_sizes:
            role_name = f"large_role_{size_kb}kb"

            # Create large role data
            large_data = {
                "identity": {"id": role_name, "type": "large"},
                "role": "Large role for performance testing",
                "large_content": "x"
                * (size_kb * 1024 - 200),  # Approximately size_kb KB
                "capabilities": [f"capability_{i}" for i in range(100)],
            }

            role_file = roles_dir / f"{role_name}.yaml"
            role_file.write_text(yaml.dump(large_data))

            # Benchmark loading
            times = []
            for _ in range(10):
                start_time = time.perf_counter()
                result = composer.load_agent_role(role_name)
                end_time = time.perf_counter()

                times.append(end_time - start_time)
                assert result["identity"]["id"] == role_name

            avg_time = sum(times) / len(times)
            load_times[size_kb] = avg_time

            print(f"Role size {size_kb}KB: {avg_time:.6f}s average load time")

        # Verify performance scaling with file size
        # Loading time should scale reasonably with file size
        time_1kb = load_times[1]
        time_100kb = load_times[100]

        # 100KB file shouldn't take more than 10x longer than 1KB file
        scaling_ratio = time_100kb / time_1kb
        assert (
            scaling_ratio < 10.0
        ), f"Performance doesn't scale well with file size: {scaling_ratio:.2f}x"

        # All files should load within reasonable time
        for size_kb, avg_time in load_times.items():
            assert (
                avg_time < 0.100
            ), f"Large file ({size_kb}KB) loads too slowly: {avg_time:.6f}s"

    def test_composition_complexity_scaling(self, temp_dir):
        """Test performance scaling with composition complexity."""
        composer = AgentComposer(str(temp_dir))

        # Setup role
        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()

        role_data = {"identity": {"id": "complex_role"}}
        (roles_dir / "complex_role.yaml").write_text(yaml.dump(role_data))

        # Create domains with different complexity levels
        domains_dir = temp_dir / "domains"
        domains_dir.mkdir()

        complexity_levels = [1, 3, 5, 10, 15]  # Number of domains
        composition_times = {}

        for complexity in complexity_levels:
            # Create domains for this complexity level
            domain_names = []
            for i in range(complexity):
                domain_name = f"complex_domain_{complexity}_{i}"
                domain_data = {
                    "domain": {"id": domain_name},
                    "knowledge_patterns": {
                        f"pattern_type_{j}": [f"pattern_{j}_{k}" for k in range(10)]
                        for j in range(5)
                    },
                    "decision_rules": {
                        f"rule_category_{j}": [f"rule_{j}_{k}" for k in range(8)]
                        for j in range(3)
                    },
                }

                domain_file = domains_dir / f"{domain_name}.yaml"
                domain_file.write_text(yaml.dump(domain_data))
                domain_names.append(domain_name)

            # Benchmark composition
            domains_str = ",".join(domain_names)
            times = []

            for _ in range(10):
                start_time = time.perf_counter()
                result = composer.compose_agent("complex_role", domains_str)
                end_time = time.perf_counter()

                times.append(end_time - start_time)
                assert len(result["domains"]) == complexity

            avg_time = sum(times) / len(times)
            composition_times[complexity] = avg_time

            print(
                f"Complexity {complexity} domains: {avg_time:.6f}s average composition time"
            )

        # Verify reasonable scaling
        time_1_domain = composition_times[1]
        time_15_domains = composition_times[15]

        # 15 domains shouldn't take more than 15x longer than 1 domain
        scaling_ratio = time_15_domains / time_1_domain
        assert (
            scaling_ratio < 15.0
        ), f"Composition complexity scaling poor: {scaling_ratio:.2f}x"

        # All compositions should complete within reasonable time
        for complexity, avg_time in composition_times.items():
            max_acceptable_time = 0.010 + (
                complexity * 0.005
            )  # Base time + linear scaling
            assert (
                avg_time < max_acceptable_time
            ), f"Complex composition ({complexity} domains) too slow: {avg_time:.6f}s"

    def _setup_scaling_test_data(self, temp_dir):
        """Setup test data for scaling tests."""
        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()

        # Create multiple roles for scaling tests
        for i in range(5):
            role_data = {
                "identity": {"id": f"scale_role_{i}", "type": "scaling"},
                "role": f"Scaling test role {i}",
            }
            role_file = roles_dir / f"scale_role_{i}.yaml"
            role_file.write_text(yaml.dump(role_data))


class TestMemoryPerformance:
    """Test memory usage and performance."""

    def test_memory_usage_scaling(self, temp_dir):
        """Test memory usage scaling with composition complexity."""
        composer = AgentComposer(str(temp_dir))

        # Setup test data
        self._setup_memory_test_data(temp_dir)

        # Get baseline memory usage
        import psutil

        process = psutil.Process()
        baseline_memory = process.memory_info().rss

        # Test different composition sizes
        composition_sizes = [1, 5, 10, 20]
        memory_usage = {}

        for size in composition_sizes:
            # Force garbage collection for consistent measurement
            gc.collect()

            start_memory = process.memory_info().rss

            # Create compositions
            compositions = []
            domain_list = [f"mem_domain_{i}" for i in range(size)]

            for i in range(10):  # Create 10 compositions of each size
                result = composer.compose_agent("mem_role", ",".join(domain_list))
                compositions.append(result)

            end_memory = process.memory_info().rss
            memory_delta = end_memory - start_memory
            memory_per_composition = memory_delta / 10  # 10 compositions

            memory_usage[size] = {
                "total_delta_mb": memory_delta / (1024 * 1024),
                "per_composition_kb": memory_per_composition / 1024,
                "compositions": len(compositions),
            }

            print(
                f"Size {size}: {memory_delta / (1024 * 1024):.2f}MB total, "
                f"{memory_per_composition / 1024:.2f}KB per composition"
            )

            # Cleanup to prevent memory accumulation
            del compositions
            gc.collect()

        # Verify reasonable memory scaling
        mem_1 = memory_usage[1]["per_composition_kb"]
        mem_20 = memory_usage[20]["per_composition_kb"]

        # Memory usage should scale reasonably (not more than 20x for 20x complexity)
        if mem_1 > 0:  # Avoid division by zero
            scaling_ratio = mem_20 / mem_1
            assert (
                scaling_ratio < 25.0
            ), f"Memory usage scaling poor: {scaling_ratio:.2f}x"

        # No composition should use excessive memory
        for size, usage in memory_usage.items():
            per_comp_kb = usage["per_composition_kb"]
            max_acceptable_kb = 100 + (size * 10)  # Base + linear scaling
            assert (
                per_comp_kb < max_acceptable_kb
            ), f"Composition (size {size}) uses too much memory: {per_comp_kb:.2f}KB"

    def test_memory_leak_detection(self, temp_dir):
        """Test for memory leaks in repeated operations."""
        composer = AgentComposer(str(temp_dir))

        # Setup test data
        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()

        role_data = {"identity": {"id": "leak_test"}}
        (roles_dir / "leak_test.yaml").write_text(yaml.dump(role_data))

        import psutil

        process = psutil.Process()

        # Measure memory usage over multiple iterations
        memory_measurements = []
        iterations = 100

        for i in range(iterations):
            # Perform operations that might leak memory
            result = composer.load_agent_role("leak_test")
            sanitized = composer._sanitize_input("test_input_" + str(i))
            unique_id = composer.get_unique_agent_id("role", "domain_" + str(i))

            # Measure memory every 10 iterations
            if i % 10 == 0:
                gc.collect()  # Force garbage collection
                memory_mb = process.memory_info().rss / (1024 * 1024)
                memory_measurements.append((i, memory_mb))

                if len(memory_measurements) > 1:
                    # Check for significant memory growth
                    initial_memory = memory_measurements[0][1]
                    current_memory = memory_mb
                    growth = current_memory - initial_memory

                    # Memory growth should be reasonable
                    max_acceptable_growth = 10.0  # 10MB max growth
                    if growth > max_acceptable_growth:
                        pytest.fail(
                            f"Potential memory leak detected: {growth:.2f}MB growth after {i} iterations"
                        )

        # Final memory check
        final_memory = memory_measurements[-1][1]
        initial_memory = memory_measurements[0][1]
        total_growth = final_memory - initial_memory

        print(f"Memory growth over {iterations} iterations: {total_growth:.2f}MB")
        assert total_growth < 15.0, f"Excessive memory growth: {total_growth:.2f}MB"

    def _setup_memory_test_data(self, temp_dir):
        """Setup test data for memory tests."""
        # Create role
        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()

        role_data = {"identity": {"id": "mem_role"}}
        (roles_dir / "mem_role.yaml").write_text(yaml.dump(role_data))

        # Create domains
        domains_dir = temp_dir / "domains"
        domains_dir.mkdir()

        for i in range(20):
            domain_data = {
                "domain": {"id": f"mem_domain_{i}"},
                "knowledge_patterns": {
                    f"pattern_type_{j}": [f"pattern_{j}_{k}" for k in range(5)]
                    for j in range(3)
                },
            }
            domain_file = domains_dir / f"mem_domain_{i}.yaml"
            domain_file.write_text(yaml.dump(domain_data))


class TestThroughputPerformance:
    """Test throughput and sustained performance."""

    def test_sustained_throughput(self, temp_dir):
        """Test sustained throughput over extended period."""
        composer = AgentComposer(str(temp_dir))

        # Setup test data
        self._setup_throughput_test_data(temp_dir)

        # Test parameters
        test_duration = 10.0  # seconds
        target_ops_per_second = 50

        operations_completed = []
        start_time = time.perf_counter()
        operation_count = 0

        while time.perf_counter() - start_time < test_duration:
            op_start = time.perf_counter()

            # Perform operation
            role_idx = operation_count % 5
            result = composer.load_agent_role(f"throughput_role_{role_idx}")

            op_end = time.perf_counter()
            op_time = op_end - op_start

            operations_completed.append(
                {
                    "operation_id": operation_count,
                    "duration": op_time,
                    "timestamp": op_end - start_time,
                    "success": result["identity"]["id"]
                    == f"throughput_role_{role_idx}",
                }
            )

            operation_count += 1

        total_time = time.perf_counter() - start_time
        successful_ops = sum(1 for op in operations_completed if op["success"])
        throughput = successful_ops / total_time

        print(f"Sustained throughput: {throughput:.2f} ops/sec over {total_time:.2f}s")
        print(
            f"Total operations: {len(operations_completed)}, Successful: {successful_ops}"
        )

        # Verify throughput meets minimum requirements
        min_acceptable_throughput = target_ops_per_second * 0.8  # 80% of target
        assert (
            throughput >= min_acceptable_throughput
        ), f"Throughput too low: {throughput:.2f} ops/sec (target: {target_ops_per_second})"

        # Verify operation success rate
        success_rate = successful_ops / len(operations_completed)
        assert success_rate > 0.99, f"Success rate too low: {success_rate:.4f}"

        # Analyze timing consistency
        op_times = [op["duration"] for op in operations_completed]
        avg_time = sum(op_times) / len(op_times)
        max_time = max(op_times)

        # Operations should be consistently fast
        assert avg_time < 0.020, f"Average operation time too slow: {avg_time:.6f}s"
        assert max_time < 0.100, f"Slowest operation too slow: {max_time:.6f}s"

    def test_burst_performance(self, temp_dir):
        """Test performance under burst loads."""
        composer = AgentComposer(str(temp_dir))

        # Setup test data
        self._setup_throughput_test_data(temp_dir)

        # Test burst scenarios
        burst_scenarios = [
            {"threads": 1, "ops_per_thread": 100, "name": "sequential_burst"},
            {"threads": 5, "ops_per_thread": 20, "name": "concurrent_burst"},
            {"threads": 10, "ops_per_thread": 10, "name": "high_concurrency_burst"},
        ]

        burst_results = {}

        for scenario in burst_scenarios:
            thread_count = scenario["threads"]
            ops_per_thread = scenario["ops_per_thread"]
            name = scenario["name"]

            def burst_worker():
                worker_results = []
                for i in range(ops_per_thread):
                    start_time = time.perf_counter()
                    role_idx = i % 5
                    result = composer.load_agent_role(f"throughput_role_{role_idx}")
                    end_time = time.perf_counter()

                    worker_results.append(
                        {
                            "duration": end_time - start_time,
                            "success": result["identity"]["id"]
                            == f"throughput_role_{role_idx}",
                        }
                    )
                return worker_results

            # Execute burst
            start_time = time.perf_counter()

            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [executor.submit(burst_worker) for _ in range(thread_count)]
                all_results = []
                for future in as_completed(futures):
                    thread_results = future.result()
                    all_results.extend(thread_results)

            end_time = time.perf_counter()
            total_time = end_time - start_time
            total_ops = len(all_results)
            successful_ops = sum(1 for r in all_results if r["success"])
            throughput = successful_ops / total_time

            burst_results[name] = {
                "throughput": throughput,
                "total_time": total_time,
                "success_rate": successful_ops / total_ops,
                "avg_op_time": sum(r["duration"] for r in all_results) / total_ops,
            }

            print(
                f"{name}: {throughput:.2f} ops/sec, {burst_results[name]['success_rate']:.4f} success rate"
            )

        # Verify burst performance meets requirements
        for name, results in burst_results.items():
            assert (
                results["success_rate"] > 0.95
            ), f"{name} success rate too low: {results['success_rate']:.4f}"
            assert (
                results["throughput"] > 20.0
            ), f"{name} throughput too low: {results['throughput']:.2f} ops/sec"
            assert (
                results["avg_op_time"] < 0.050
            ), f"{name} average op time too slow: {results['avg_op_time']:.6f}s"

    def _setup_throughput_test_data(self, temp_dir):
        """Setup test data for throughput tests."""
        roles_dir = temp_dir / "roles"
        roles_dir.mkdir()

        # Create multiple roles for throughput testing
        for i in range(5):
            role_data = {
                "identity": {"id": f"throughput_role_{i}", "type": "throughput"},
                "role": f"Throughput test role {i}",
            }
            role_file = roles_dir / f"throughput_role_{i}.yaml"
            role_file.write_text(yaml.dump(role_data))


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)
