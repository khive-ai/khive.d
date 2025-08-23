"""Basic performance tests to validate the benchmarking infrastructure."""


import pytest

from khive.services.performance import (BenchmarkFramework, BenchmarkStorage,
                                        PerformanceAnalyzer,
                                        PerformanceReporter)


class TestBasicPerformanceBenchmarks:
    """Basic performance benchmarks to validate the framework."""

    @pytest.fixture
    def benchmark_storage(self, tmp_path):
        """Provide benchmark storage for tests."""
        return BenchmarkStorage(tmp_path / "benchmarks")

    @pytest.fixture
    def benchmark_framework(self):
        """Provide benchmark framework for tests."""
        return BenchmarkFramework()

    def test_simple_benchmark_storage(self, benchmark_storage):
        """Test simple benchmark result storage and retrieval."""

        from datetime import datetime

        from khive.services.performance.benchmark_framework import (
            BenchmarkResult, PerformanceMetrics)

        # Create a simple test result
        metrics = PerformanceMetrics(
            duration=0.1, operations_count=1, success_count=1, error_count=0
        )

        test_result = BenchmarkResult(
            benchmark_name="simple_cpu_test",
            operation_type="computation",
            timestamp=datetime.now(),
            metrics=metrics,
            tags=["test"],
            metadata={"test_type": "basic"},
            environment={"platform": "test"},
        )

        # Store result
        storage_id = benchmark_storage.store_result(test_result)
        assert storage_id > 0

        # Retrieve result
        retrieved = benchmark_storage.get_baseline("simple_cpu_test", "computation")
        assert retrieved is not None
        assert retrieved.benchmark_name == test_result.benchmark_name
        assert retrieved.metrics.duration == 0.1
        assert retrieved.metrics.success_rate == 1.0
        assert retrieved.metrics.throughput_ops_per_sec > 0  # Computed property

    def test_memory_usage_benchmark(self, benchmark_framework, benchmark_storage):
        """Test memory usage tracking with storage operations."""

        from datetime import datetime

        from khive.services.performance.benchmark_framework import (
            BenchmarkResult, PerformanceMetrics)

        # Create a test benchmark result with memory metrics
        metrics = PerformanceMetrics(
            duration=0.05,
            memory_start_mb=50.0,
            memory_peak_mb=75.0,
            memory_end_mb=52.0,
            memory_delta_mb=2.0,
            operations_count=1,
            success_count=1,
            error_count=0,
        )

        test_result = BenchmarkResult(
            benchmark_name="memory_test",
            operation_type="memory_allocation",
            timestamp=datetime.now(),
            metrics=metrics,
            tags=["memory"],
            metadata={"test_type": "memory_tracking"},
            environment={"python_version": "3.10"},
        )

        # Store and verify
        storage_id = benchmark_storage.store_result(test_result)
        assert storage_id > 0

        stored_result = benchmark_storage.get_baseline(
            "memory_test", "memory_allocation"
        )
        assert stored_result is not None
        assert stored_result.metrics.memory_peak_mb == 75.0

    def test_concurrent_operations_benchmark(
        self, benchmark_framework, benchmark_storage
    ):
        """Test concurrent operation result storage."""

        from datetime import datetime

        from khive.services.performance.benchmark_framework import (
            BenchmarkResult, PerformanceMetrics)

        # Create test result for concurrent operations
        metrics = PerformanceMetrics(
            duration=0.15, operations_count=10, success_count=10, error_count=0
        )

        test_result = BenchmarkResult(
            benchmark_name="concurrent_test",
            operation_type="async_operations",
            timestamp=datetime.now(),
            metrics=metrics,
            tags=["async", "concurrent"],
            metadata={"concurrency_level": 10},
            environment={},
        )

        # Validate metrics
        assert test_result.metrics.operations_count == 10
        assert test_result.metrics.success_rate == 1.0
        assert test_result.metrics.throughput_ops_per_sec > 0

        # Store result
        storage_id = benchmark_storage.store_result(test_result)
        assert storage_id > 0

    def test_performance_analysis(self, benchmark_storage):
        """Test performance analysis capabilities."""

        # Create analyzer
        analyzer = PerformanceAnalyzer(benchmark_storage)

        # Test metric analysis with empty data
        analysis = analyzer.analyze_metric(results=[], metric_name="duration")

        # Should return error for no results
        assert analysis is not None
        assert "error" in analysis
        assert analysis["error"] == "No results provided"

    def test_performance_reporter(self, benchmark_storage, tmp_path):
        """Test performance reporting."""

        # Create reporter
        reporter = PerformanceReporter(benchmark_storage)

        # Generate report (should handle empty data gracefully)
        try:
            report_path = reporter.generate_comprehensive_report(
                report_name="test_report", days_back=7
            )

            # If successful, should return a Path
            assert report_path is not None
        except Exception as e:
            # Should handle gracefully if no data
            assert "No performance data" in str(e) or "error" in str(e).lower()

    def test_benchmark_storage_operations(self, benchmark_storage):
        """Test storage operations."""

        # Test getting summary with empty data
        summary = benchmark_storage.get_summary()
        assert "total_benchmarks" in summary
        assert summary["total_benchmarks"] == 0

        # Test storage info
        info = benchmark_storage.get_storage_info()
        assert "total_results" in info
        assert info["total_results"] == 0
        assert "storage_path" in info
