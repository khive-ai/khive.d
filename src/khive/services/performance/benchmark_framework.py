"""Core benchmarking framework for khive performance testing."""

import asyncio
import gc
import threading
import time
from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import psutil


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics container."""

    # Timing metrics
    duration: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0

    # Memory metrics
    memory_start_mb: float = 0.0
    memory_end_mb: float = 0.0
    memory_peak_mb: float = 0.0
    memory_delta_mb: float = 0.0

    # CPU metrics
    cpu_percent_avg: float = 0.0
    cpu_percent_peak: float = 0.0

    # I/O metrics
    io_read_bytes: int = 0
    io_write_bytes: int = 0
    io_read_count: int = 0
    io_write_count: int = 0

    # Network metrics (if applicable)
    network_sent_bytes: int = 0
    network_recv_bytes: int = 0
    network_connections: int = 0

    # Operation metrics
    operations_count: int = 0
    success_count: int = 0
    error_count: int = 0

    # Custom metrics
    custom_metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.error_count
        return self.success_count / max(total, 1)

    @property
    def throughput_ops_per_sec(self) -> float:
        """Calculate operations per second."""
        return self.operations_count / max(self.duration, 0.001)

    @property
    def avg_operation_time_ms(self) -> float:
        """Average operation time in milliseconds."""
        return (self.duration * 1000) / max(self.operations_count, 1)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            # Core timing
            "duration": self.duration,
            "start_time": self.start_time,
            "end_time": self.end_time,
            # Memory usage
            "memory_start_mb": self.memory_start_mb,
            "memory_end_mb": self.memory_end_mb,
            "memory_peak_mb": self.memory_peak_mb,
            "memory_delta_mb": self.memory_delta_mb,
            # CPU usage
            "cpu_percent_avg": self.cpu_percent_avg,
            "cpu_percent_peak": self.cpu_percent_peak,
            # I/O statistics
            "io_read_bytes": self.io_read_bytes,
            "io_write_bytes": self.io_write_bytes,
            "io_read_count": self.io_read_count,
            "io_write_count": self.io_write_count,
            # Network statistics
            "network_sent_bytes": self.network_sent_bytes,
            "network_recv_bytes": self.network_recv_bytes,
            "network_connections": self.network_connections,
            # Operation statistics
            "operations_count": self.operations_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            # Computed metrics
            "success_rate": self.success_rate,
            "throughput_ops_per_sec": self.throughput_ops_per_sec,
            "avg_operation_time_ms": self.avg_operation_time_ms,
            # Custom metrics
            "custom_metrics": self.custom_metrics,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PerformanceMetrics":
        """Create from dictionary."""
        # Extract custom metrics separately
        custom_metrics = data.pop("custom_metrics", {})

        # Create instance with standard fields
        metrics = cls(**{
            k: v for k, v in data.items() if k in cls.__dataclass_fields__
        })
        metrics.custom_metrics = custom_metrics
        return metrics


@dataclass
class BenchmarkResult:
    """Result of a benchmark execution."""

    benchmark_name: str
    operation_type: str
    timestamp: datetime
    metrics: PerformanceMetrics
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "benchmark_name": self.benchmark_name,
            "operation_type": self.operation_type,
            "timestamp": self.timestamp.isoformat(),
            "metrics": self.metrics.to_dict(),
            "metadata": self.metadata,
            "tags": self.tags,
            "environment": self.environment,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkResult":
        """Create from dictionary."""
        return cls(
            benchmark_name=data["benchmark_name"],
            operation_type=data["operation_type"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metrics=PerformanceMetrics.from_dict(data["metrics"]),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            environment=data.get("environment", {}),
        )


class PerformanceMonitor:
    """Monitors system performance during benchmark execution."""

    def __init__(self, monitoring_interval: float = 0.1):
        self.monitoring_interval = monitoring_interval
        self.process = psutil.Process()
        self.is_monitoring = False
        self.monitor_thread = None

        # Monitoring data
        self.cpu_samples = []
        self.memory_samples = []
        self.io_samples = []
        self.network_samples = []
        self.start_io = None
        self.start_network = None

    def start_monitoring(self):
        """Start performance monitoring."""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.cpu_samples = []
        self.memory_samples = []
        self.io_samples = []
        self.network_samples = []

        # Capture initial state
        self.start_io = self.process.io_counters()
        self.start_network = psutil.net_io_counters()

        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self) -> PerformanceMetrics:
        """Stop monitoring and return collected metrics."""
        self.is_monitoring = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)

        return self._compute_metrics()

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # CPU monitoring
                cpu_percent = self.process.cpu_percent()
                self.cpu_samples.append(cpu_percent)

                # Memory monitoring
                memory_info = self.process.memory_info()
                self.memory_samples.append(memory_info.rss / (1024 * 1024))  # MB

                # I/O monitoring
                io_counters = self.process.io_counters()
                self.io_samples.append({
                    "read_bytes": io_counters.read_bytes - self.start_io.read_bytes,
                    "write_bytes": io_counters.write_bytes - self.start_io.write_bytes,
                    "read_count": io_counters.read_count - self.start_io.read_count,
                    "write_count": io_counters.write_count - self.start_io.write_count,
                })

                # Network monitoring
                net_counters = psutil.net_io_counters()
                self.network_samples.append({
                    "sent_bytes": net_counters.bytes_sent
                    - self.start_network.bytes_sent,
                    "recv_bytes": net_counters.bytes_recv
                    - self.start_network.bytes_recv,
                })

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process might have ended or access denied
                break

            time.sleep(self.monitoring_interval)

    def _compute_metrics(self) -> PerformanceMetrics:
        """Compute performance metrics from collected samples."""
        metrics = PerformanceMetrics()

        # Memory metrics
        if self.memory_samples:
            metrics.memory_start_mb = self.memory_samples[0]
            metrics.memory_end_mb = self.memory_samples[-1]
            metrics.memory_peak_mb = max(self.memory_samples)
            metrics.memory_delta_mb = metrics.memory_end_mb - metrics.memory_start_mb

        # CPU metrics
        if self.cpu_samples:
            valid_cpu_samples = [s for s in self.cpu_samples if s > 0]
            if valid_cpu_samples:
                metrics.cpu_percent_avg = sum(valid_cpu_samples) / len(
                    valid_cpu_samples
                )
                metrics.cpu_percent_peak = max(valid_cpu_samples)

        # I/O metrics
        if self.io_samples:
            final_io = self.io_samples[-1]
            metrics.io_read_bytes = final_io["read_bytes"]
            metrics.io_write_bytes = final_io["write_bytes"]
            metrics.io_read_count = final_io["read_count"]
            metrics.io_write_count = final_io["write_count"]

        # Network metrics
        if self.network_samples:
            final_network = self.network_samples[-1]
            metrics.network_sent_bytes = final_network["sent_bytes"]
            metrics.network_recv_bytes = final_network["recv_bytes"]
            metrics.network_connections = len(psutil.net_connections())

        return metrics


class BenchmarkFramework:
    """Main benchmarking framework for khive performance testing."""

    def __init__(self, monitoring_interval: float = 0.1):
        self.monitoring_interval = monitoring_interval
        self.results = []
        self.environment = self._capture_environment()

    def _capture_environment(self) -> dict[str, Any]:
        """Capture current system environment."""
        return {
            "python_version": psutil.__version__,
            "platform": psutil.os.name,
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "disk_usage_gb": psutil.disk_usage("/").total / (1024**3),
            "timestamp": datetime.now().isoformat(),
        }

    @contextmanager
    def benchmark(
        self,
        name: str,
        operation_type: str = "general",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Context manager for benchmarking synchronous operations."""

        monitor = PerformanceMonitor(self.monitoring_interval)
        start_time = time.perf_counter()

        # Force garbage collection before benchmark
        gc.collect()

        # Start monitoring
        monitor.start_monitoring()

        try:
            yield
        finally:
            end_time = time.perf_counter()

            # Stop monitoring and collect metrics
            metrics = monitor.stop_monitoring()
            metrics.start_time = start_time
            metrics.end_time = end_time
            metrics.duration = end_time - start_time

            # Create benchmark result
            result = BenchmarkResult(
                benchmark_name=name,
                operation_type=operation_type,
                timestamp=datetime.now(),
                metrics=metrics,
                metadata=metadata or {},
                tags=tags or [],
                environment=self.environment,
            )

            self.results.append(result)

    @asynccontextmanager
    async def async_benchmark(
        self,
        name: str,
        operation_type: str = "async",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Async context manager for benchmarking asynchronous operations."""

        monitor = PerformanceMonitor(self.monitoring_interval)
        start_time = time.perf_counter()

        # Force garbage collection before benchmark
        gc.collect()

        # Start monitoring
        monitor.start_monitoring()

        try:
            yield
        finally:
            end_time = time.perf_counter()

            # Stop monitoring and collect metrics
            metrics = monitor.stop_monitoring()
            metrics.start_time = start_time
            metrics.end_time = end_time
            metrics.duration = end_time - start_time

            # Create benchmark result
            result = BenchmarkResult(
                benchmark_name=name,
                operation_type=operation_type,
                timestamp=datetime.now(),
                metrics=metrics,
                metadata=metadata or {},
                tags=tags or [],
                environment=self.environment,
            )

            self.results.append(result)

    async def benchmark_function(
        self,
        func: Callable,
        name: str,
        args: tuple = (),
        kwargs: dict[str, Any] | None = None,
        operation_type: str = "function",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Benchmark a single function call."""

        if asyncio.iscoroutinefunction(func):
            async with self.async_benchmark(name, operation_type, tags, metadata):
                return await func(*args, **(kwargs or {}))
        else:
            with self.benchmark(name, operation_type, tags, metadata):
                return func(*args, **(kwargs or {}))

    async def benchmark_load(
        self,
        func: Callable,
        name: str,
        concurrent_tasks: int = 10,
        operations_per_task: int = 100,
        ramp_up_seconds: float = 1.0,
        operation_type: str = "load_test",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BenchmarkResult:
        """Run load testing benchmark."""

        async def task_worker(task_id: int, delay: float = 0):
            if delay > 0:
                await asyncio.sleep(delay)

            task_results = {"operations": 0, "errors": 0}

            for _ in range(operations_per_task):
                try:
                    if asyncio.iscoroutinefunction(func):
                        await func()
                    else:
                        func()
                    task_results["operations"] += 1
                except Exception:
                    task_results["errors"] += 1

            return task_results

        # Start load test benchmark
        monitor = PerformanceMonitor(self.monitoring_interval)
        start_time = time.perf_counter()
        monitor.start_monitoring()

        # Create tasks with staggered start
        tasks = []
        ramp_delay = ramp_up_seconds / concurrent_tasks if concurrent_tasks > 1 else 0

        for task_id in range(concurrent_tasks):
            delay = task_id * ramp_delay
            task = asyncio.create_task(task_worker(task_id, delay))
            tasks.append(task)

        # Execute load test
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.perf_counter()
        metrics = monitor.stop_monitoring()

        # Aggregate results
        total_operations = sum(
            r["operations"]
            for r in task_results
            if isinstance(r, dict) and "operations" in r
        )
        total_errors = sum(
            r["errors"] for r in task_results if isinstance(r, dict) and "errors" in r
        )

        # Update metrics
        metrics.start_time = start_time
        metrics.end_time = end_time
        metrics.duration = end_time - start_time
        metrics.operations_count = total_operations
        metrics.success_count = total_operations
        metrics.error_count = total_errors

        # Add load test specific metadata
        load_metadata = {
            "concurrent_tasks": concurrent_tasks,
            "operations_per_task": operations_per_task,
            "ramp_up_seconds": ramp_up_seconds,
            "total_operations": total_operations,
            "total_errors": total_errors,
        }
        load_metadata.update(metadata or {})

        result = BenchmarkResult(
            benchmark_name=name,
            operation_type=operation_type,
            timestamp=datetime.now(),
            metrics=metrics,
            metadata=load_metadata,
            tags=tags or [],
            environment=self.environment,
        )

        self.results.append(result)
        return result

    def get_results(self) -> list[BenchmarkResult]:
        """Get all benchmark results."""
        return self.results.copy()

    def clear_results(self):
        """Clear all benchmark results."""
        self.results.clear()

    def get_results_by_name(self, name: str) -> list[BenchmarkResult]:
        """Get benchmark results by name."""
        return [r for r in self.results if r.benchmark_name == name]

    def get_results_by_operation(self, operation_type: str) -> list[BenchmarkResult]:
        """Get benchmark results by operation type."""
        return [r for r in self.results if r.operation_type == operation_type]


class BenchmarkSuite:
    """Collection of benchmarks with organization and execution management."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.benchmarks = []
        self.framework = BenchmarkFramework()

    def add_benchmark(
        self,
        func: Callable,
        name: str,
        operation_type: str = "general",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        args: tuple = (),
        kwargs: dict[str, Any] | None = None,
    ):
        """Add a benchmark function to the suite."""
        self.benchmarks.append({
            "func": func,
            "name": name,
            "operation_type": operation_type,
            "tags": tags or [],
            "metadata": metadata or {},
            "args": args,
            "kwargs": kwargs or {},
        })

    async def run_all(self) -> list[BenchmarkResult]:
        """Run all benchmarks in the suite."""
        results = []

        for benchmark in self.benchmarks:
            try:
                result = await self.framework.benchmark_function(
                    func=benchmark["func"],
                    name=benchmark["name"],
                    args=benchmark["args"],
                    kwargs=benchmark["kwargs"],
                    operation_type=benchmark["operation_type"],
                    tags=benchmark["tags"],
                    metadata=benchmark["metadata"],
                )

                # Get the latest result
                latest_result = self.framework.get_results()[-1]
                results.append(latest_result)

            except Exception as e:
                # Create error result
                error_result = BenchmarkResult(
                    benchmark_name=benchmark["name"],
                    operation_type=benchmark["operation_type"],
                    timestamp=datetime.now(),
                    metrics=PerformanceMetrics(),
                    metadata={
                        **benchmark["metadata"],
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    tags=benchmark["tags"] + ["error"],
                    environment=self.framework.environment,
                )
                results.append(error_result)

        return results

    async def run_benchmark(self, name: str) -> BenchmarkResult | None:
        """Run a specific benchmark by name."""
        benchmark = next((b for b in self.benchmarks if b["name"] == name), None)
        if not benchmark:
            return None

        try:
            await self.framework.benchmark_function(
                func=benchmark["func"],
                name=benchmark["name"],
                args=benchmark["args"],
                kwargs=benchmark["kwargs"],
                operation_type=benchmark["operation_type"],
                tags=benchmark["tags"],
                metadata=benchmark["metadata"],
            )
            return self.framework.get_results()[-1]

        except Exception as e:
            return BenchmarkResult(
                benchmark_name=benchmark["name"],
                operation_type=benchmark["operation_type"],
                timestamp=datetime.now(),
                metrics=PerformanceMetrics(),
                metadata={
                    **benchmark["metadata"],
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                tags=benchmark["tags"] + ["error"],
                environment=self.framework.environment,
            )
