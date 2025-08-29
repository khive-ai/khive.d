"""Performance testing fixtures for benchmarking and load testing."""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass

import pytest


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    duration: float
    memory_peak: int
    memory_avg: int
    cpu_percent: float
    operations_per_second: float
    throughput: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    error_rate: float
    success_rate: float
    operation_count: int


@pytest.fixture
def performance_monitor():
    """Monitor performance metrics during test execution."""
    import threading
    from queue import Queue

    import psutil

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.memory_samples = Queue()
            self.cpu_samples = Queue()
            self.operation_count = 0
            self.error_count = 0
            self.monitoring = False
            self.monitor_thread = None
            self.process = psutil.Process()

        def start_monitoring(self):
            """Start performance monitoring."""
            self.start_time = time.perf_counter()
            self.monitoring = True
            self.operation_count = 0
            self.error_count = 0

            # Start background monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_resources)
            self.monitor_thread.start()

        def stop_monitoring(self) -> PerformanceMetrics:
            """Stop monitoring and return metrics."""
            self.end_time = time.perf_counter()
            self.monitoring = False

            if self.monitor_thread:
                self.monitor_thread.join(timeout=1.0)

            return self._calculate_metrics()

        def record_operation(self, success: bool = True):
            """Record a completed operation."""
            self.operation_count += 1
            if not success:
                self.error_count += 1

        def _monitor_resources(self):
            """Background resource monitoring."""
            while self.monitoring:
                try:
                    memory_info = self.process.memory_info()
                    cpu_percent = self.process.cpu_percent()

                    self.memory_samples.put(memory_info.rss)
                    self.cpu_samples.put(cpu_percent)

                    time.sleep(0.1)  # Sample every 100ms
                except psutil.NoSuchProcess:
                    break
                except Exception:
                    # Ignore monitoring errors
                    pass

        def _calculate_metrics(self) -> PerformanceMetrics:
            """Calculate performance metrics from samples."""
            duration = self.end_time - self.start_time

            # Collect memory samples
            memory_samples = []
            while not self.memory_samples.empty():
                memory_samples.append(self.memory_samples.get())

            # Collect CPU samples
            cpu_samples = []
            while not self.cpu_samples.empty():
                cpu_samples.append(self.cpu_samples.get())

            # Calculate metrics
            memory_peak = max(memory_samples) if memory_samples else 0
            memory_avg = (
                sum(memory_samples) / len(memory_samples) if memory_samples else 0
            )
            cpu_avg = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0

            ops_per_second = self.operation_count / duration if duration > 0 else 0
            error_rate = (
                self.error_count / self.operation_count
                if self.operation_count > 0
                else 0
            )
            success_rate = 1.0 - error_rate

            # For simple cases, use duration-based latency estimates
            latency_p50 = (
                duration / self.operation_count if self.operation_count > 0 else 0
            )
            latency_p95 = latency_p50 * 1.5  # Rough estimate
            latency_p99 = latency_p50 * 2.0  # Rough estimate

            return PerformanceMetrics(
                duration=duration,
                memory_peak=memory_peak,
                memory_avg=int(memory_avg),
                cpu_percent=cpu_avg,
                operations_per_second=ops_per_second,
                throughput=ops_per_second,  # Same for simple cases
                latency_p50=latency_p50,
                latency_p95=latency_p95,
                latency_p99=latency_p99,
                error_rate=error_rate,
                success_rate=success_rate,
                operation_count=self.operation_count,
            )

    return PerformanceMonitor()


@pytest.fixture
def benchmark_config():
    """Configuration for benchmark tests."""
    return {
        "warmup_iterations": 10,
        "test_iterations": 100,
        "timeout_seconds": 60,
        "memory_threshold_mb": 512,
        "cpu_threshold_percent": 80,
        "latency_threshold_ms": 1000,
        "throughput_threshold_ops": 100,
        "error_rate_threshold": 0.05,
    }


@pytest.fixture
def load_test_scenarios():
    """Predefined load testing scenarios."""
    return {
        "light_load": {
            "concurrent_users": 5,
            "requests_per_user": 10,
            "ramp_up_time": 5,
            "test_duration": 30,
        },
        "moderate_load": {
            "concurrent_users": 20,
            "requests_per_user": 50,
            "ramp_up_time": 10,
            "test_duration": 60,
        },
        "heavy_load": {
            "concurrent_users": 100,
            "requests_per_user": 100,
            "ramp_up_time": 30,
            "test_duration": 300,
        },
        "stress_test": {
            "concurrent_users": 500,
            "requests_per_user": 200,
            "ramp_up_time": 60,
            "test_duration": 600,
        },
    }


@pytest.fixture
def memory_profiler():
    """Memory profiling utilities."""
    import tracemalloc

    class MemoryProfiler:
        def __init__(self):
            self.start_snapshot = None
            self.end_snapshot = None
            self.peak_memory = 0

        def start_profiling(self):
            """Start memory profiling."""
            tracemalloc.start()
            self.start_snapshot = tracemalloc.take_snapshot()
            self.peak_memory = 0

        def stop_profiling(self):
            """Stop memory profiling and return statistics."""
            if self.start_snapshot is None:
                return {}

            self.end_snapshot = tracemalloc.take_snapshot()
            tracemalloc.stop()

            return self._analyze_memory_usage()

        def take_snapshot(self):
            """Take a memory snapshot for comparison."""
            if tracemalloc.is_tracing():
                return tracemalloc.take_snapshot()
            return None

        def _analyze_memory_usage(self):
            """Analyze memory usage between snapshots."""
            if not self.start_snapshot or not self.end_snapshot:
                return {}

            top_stats = self.end_snapshot.compare_to(self.start_snapshot, "lineno")

            total_size_diff = sum(stat.size_diff for stat in top_stats)
            total_count_diff = sum(stat.count_diff for stat in top_stats)

            # Get current memory usage
            current, peak = tracemalloc.get_traced_memory()

            return {
                "memory_diff_bytes": total_size_diff,
                "allocation_diff_count": total_count_diff,
                "current_memory_bytes": current,
                "peak_memory_bytes": peak,
                "top_allocations": [
                    {
                        "filename": (
                            stat.traceback.format()[0]
                            if stat.traceback.format()
                            else "unknown"
                        ),
                        "size_diff": stat.size_diff,
                        "count_diff": stat.count_diff,
                    }
                    for stat in top_stats[:10]  # Top 10 allocations
                ],
            }

    return MemoryProfiler()


@pytest.fixture
async def async_performance_tester():
    """Async performance testing utilities."""

    class AsyncPerformanceTester:
        def __init__(self):
            self.latencies = []
            self.errors = []
            self.start_time = None
            self.end_time = None

        async def run_concurrent_test(
            self, test_func: Callable, concurrency: int, iterations: int, **kwargs
        ):
            """Run concurrent async test with performance tracking."""
            self.latencies.clear()
            self.errors.clear()

            self.start_time = time.perf_counter()

            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(concurrency)

            async def limited_test():
                async with semaphore:
                    start = time.perf_counter()
                    try:
                        result = await test_func(**kwargs)
                        end = time.perf_counter()
                        self.latencies.append(end - start)
                        return result
                    except Exception as e:
                        end = time.perf_counter()
                        self.latencies.append(end - start)
                        self.errors.append(str(e))
                        raise

            # Run all iterations
            tasks = [limited_test() for _ in range(iterations)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            self.end_time = time.perf_counter()

            # Filter successful results
            successful_results = [r for r in results if not isinstance(r, Exception)]

            return {
                "results": successful_results,
                "total_time": self.end_time - self.start_time,
                "success_count": len(successful_results),
                "error_count": len(self.errors),
                "latencies": self.latencies,
                "errors": self.errors,
            }

        async def measure_throughput(
            self, test_func: Callable, duration_seconds: int, **kwargs
        ):
            """Measure throughput over a fixed time period."""
            end_time = time.perf_counter() + duration_seconds
            operation_count = 0
            error_count = 0
            latencies = []

            while time.perf_counter() < end_time:
                start = time.perf_counter()
                try:
                    await test_func(**kwargs)
                    operation_count += 1
                except Exception:
                    error_count += 1

                latency = time.perf_counter() - start
                latencies.append(latency)

                # Small delay to prevent overwhelming
                await asyncio.sleep(0.001)

            return {
                "operations_per_second": operation_count / duration_seconds,
                "error_rate": (
                    error_count / (operation_count + error_count)
                    if operation_count + error_count > 0
                    else 0
                ),
                "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
                "total_operations": operation_count,
                "total_errors": error_count,
            }

        def calculate_percentiles(self, values: list[float]) -> dict[str, float]:
            """Calculate latency percentiles."""
            if not values:
                return {}

            sorted_values = sorted(values)
            n = len(sorted_values)

            return {
                "p50": sorted_values[int(0.5 * n)],
                "p90": sorted_values[int(0.9 * n)],
                "p95": sorted_values[int(0.95 * n)],
                "p99": sorted_values[int(0.99 * n)],
                "min": sorted_values[0],
                "max": sorted_values[-1],
                "avg": sum(sorted_values) / n,
            }

    return AsyncPerformanceTester()


@pytest.fixture
def performance_assertions():
    """Performance assertion utilities."""

    class PerformanceAssertions:
        def __init__(self):
            self.thresholds = {
                "max_duration_seconds": 10.0,
                "max_memory_mb": 512,
                "max_cpu_percent": 80.0,
                "min_throughput_ops": 10.0,
                "max_error_rate": 0.05,
                "max_latency_p95_ms": 1000.0,
            }

        def set_thresholds(self, **thresholds):
            """Update performance thresholds."""
            self.thresholds.update(thresholds)

        def assert_performance(self, metrics: PerformanceMetrics, message: str = ""):
            """Assert that performance metrics meet thresholds."""
            failures = []

            if metrics.duration > self.thresholds["max_duration_seconds"]:
                failures.append(
                    f"Duration {metrics.duration:.2f}s exceeds threshold {self.thresholds['max_duration_seconds']:.2f}s"
                )

            memory_mb = metrics.memory_peak / (1024 * 1024)
            if memory_mb > self.thresholds["max_memory_mb"]:
                failures.append(
                    f"Memory {memory_mb:.1f}MB exceeds threshold {self.thresholds['max_memory_mb']:.1f}MB"
                )

            if metrics.cpu_percent > self.thresholds["max_cpu_percent"]:
                failures.append(
                    f"CPU {metrics.cpu_percent:.1f}% exceeds threshold {self.thresholds['max_cpu_percent']:.1f}%"
                )

            if metrics.operations_per_second < self.thresholds["min_throughput_ops"]:
                failures.append(
                    f"Throughput {metrics.operations_per_second:.1f} ops/s below threshold {self.thresholds['min_throughput_ops']:.1f} ops/s"
                )

            if metrics.error_rate > self.thresholds["max_error_rate"]:
                failures.append(
                    f"Error rate {metrics.error_rate:.3f} exceeds threshold {self.thresholds['max_error_rate']:.3f}"
                )

            latency_p95_ms = metrics.latency_p95 * 1000
            if latency_p95_ms > self.thresholds["max_latency_p95_ms"]:
                failures.append(
                    f"P95 latency {latency_p95_ms:.1f}ms exceeds threshold {self.thresholds['max_latency_p95_ms']:.1f}ms"
                )

            if failures:
                failure_msg = "; ".join(failures)
                if message:
                    failure_msg = f"{message}: {failure_msg}"
                raise AssertionError(failure_msg)

        def assert_throughput(
            self, ops_per_second: float, min_threshold: float, message: str = ""
        ):
            """Assert minimum throughput requirement."""
            if ops_per_second < min_threshold:
                msg = f"Throughput {ops_per_second:.1f} ops/s below threshold {min_threshold:.1f} ops/s"
                if message:
                    msg = f"{message}: {msg}"
                raise AssertionError(msg)

        def assert_latency(
            self, latency_seconds: float, max_threshold: float, message: str = ""
        ):
            """Assert maximum latency requirement."""
            if latency_seconds > max_threshold:
                msg = f"Latency {latency_seconds * 1000:.1f}ms exceeds threshold {max_threshold * 1000:.1f}ms"
                if message:
                    msg = f"{message}: {msg}"
                raise AssertionError(msg)

    return PerformanceAssertions()
