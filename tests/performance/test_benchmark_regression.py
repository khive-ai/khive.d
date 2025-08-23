"""Performance benchmarking and regression detection tests.

Comprehensive performance benchmarking and regression detection including:
- Baseline performance benchmark establishment
- Historical performance tracking and comparison
- Automated regression detection algorithms
- Performance trend analysis and alerting
- Benchmark report generation and visualization
- CI/CD integration for continuous performance monitoring
- Performance threshold validation and enforcement
- Statistical analysis of performance variations
"""

import json
import statistics
from datetime import datetime, timedelta
from pathlib import Path

import pytest


class PerformanceBenchmark:
    """Performance benchmark data structure."""

    def __init__(
        self,
        test_name: str,
        operation_type: str,
        timestamp: datetime,
        metrics: dict[str, float],
        metadata: dict | None = None,
    ):
        self.test_name = test_name
        self.operation_type = operation_type
        self.timestamp = timestamp
        self.metrics = metrics
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """Convert benchmark to dictionary for serialization."""
        return {
            "test_name": self.test_name,
            "operation_type": self.operation_type,
            "timestamp": self.timestamp.isoformat(),
            "metrics": self.metrics,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PerformanceBenchmark":
        """Create benchmark from dictionary."""
        return cls(
            test_name=data["test_name"],
            operation_type=data["operation_type"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metrics=data["metrics"],
            metadata=data.get("metadata", {}),
        )


class BenchmarkStorage:
    """Storage and retrieval system for performance benchmarks."""

    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or Path(".khive/performance/benchmarks")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.benchmark_file = self.storage_path / "benchmarks.jsonl"

    def save_benchmark(self, benchmark: PerformanceBenchmark) -> None:
        """Save a performance benchmark."""
        with open(self.benchmark_file, "a") as f:
            json.dump(benchmark.to_dict(), f)
            f.write("\n")

    def load_benchmarks(
        self,
        test_name: str | None = None,
        operation_type: str | None = None,
        days_back: int | None = 30,
    ) -> list[PerformanceBenchmark]:
        """Load benchmarks with optional filtering."""
        benchmarks = []

        if not self.benchmark_file.exists():
            return benchmarks

        cutoff_date = datetime.now() - timedelta(days=days_back) if days_back else None

        with open(self.benchmark_file) as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    benchmark = PerformanceBenchmark.from_dict(data)

                    # Apply filters
                    if test_name and benchmark.test_name != test_name:
                        continue
                    if operation_type and benchmark.operation_type != operation_type:
                        continue
                    if cutoff_date and benchmark.timestamp < cutoff_date:
                        continue

                    benchmarks.append(benchmark)

                except (json.JSONDecodeError, KeyError, ValueError):
                    continue  # Skip malformed entries

        return benchmarks

    def get_latest_baseline(
        self, test_name: str, operation_type: str
    ) -> PerformanceBenchmark | None:
        """Get the most recent baseline benchmark."""
        benchmarks = self.load_benchmarks(
            test_name=test_name, operation_type=operation_type
        )

        if not benchmarks:
            return None

        # Return most recent benchmark
        return max(benchmarks, key=lambda b: b.timestamp)


class RegressionDetector:
    """Automated performance regression detection."""

    def __init__(
        self,
        regression_threshold: float = 1.2,  # 20% degradation threshold
        min_samples: int = 5,
        statistical_confidence: float = 0.95,
    ):
        self.regression_threshold = regression_threshold
        self.min_samples = min_samples
        self.statistical_confidence = statistical_confidence

    def detect_regression(
        self,
        current_metrics: dict[str, float],
        historical_benchmarks: list[PerformanceBenchmark],
        metric_name: str = "avg_operation_time",
    ) -> dict:
        """Detect performance regressions."""

        if len(historical_benchmarks) < self.min_samples:
            return {
                "regression_detected": False,
                "reason": f"Insufficient historical data (need {self.min_samples}, have {len(historical_benchmarks)})",
                "confidence": 0.0,
            }

        # Extract historical values for the metric
        historical_values = []
        for benchmark in historical_benchmarks:
            if metric_name in benchmark.metrics:
                historical_values.append(benchmark.metrics[metric_name])

        if not historical_values:
            return {
                "regression_detected": False,
                "reason": f"No historical data for metric {metric_name}",
                "confidence": 0.0,
            }

        current_value = current_metrics.get(metric_name)
        if current_value is None:
            return {
                "regression_detected": False,
                "reason": f"Current metrics missing {metric_name}",
                "confidence": 0.0,
            }

        # Statistical analysis
        historical_mean = statistics.mean(historical_values)
        historical_stdev = (
            statistics.stdev(historical_values) if len(historical_values) > 1 else 0
        )

        # Calculate deviation from historical mean
        if historical_mean == 0:
            relative_change = float("inf") if current_value > 0 else 0
        else:
            relative_change = current_value / historical_mean

        # Detect regression using threshold
        regression_detected = relative_change > self.regression_threshold

        # Calculate statistical confidence
        if historical_stdev > 0:
            z_score = abs(current_value - historical_mean) / historical_stdev
            confidence = min(z_score / 2.0, 1.0)  # Normalize to 0-1 range
        else:
            confidence = 1.0 if regression_detected else 0.0

        # Additional analysis
        trend_analysis = self._analyze_trend(historical_values)

        return {
            "regression_detected": regression_detected,
            "current_value": current_value,
            "historical_mean": historical_mean,
            "historical_stdev": historical_stdev,
            "relative_change": relative_change,
            "threshold_exceeded": relative_change > self.regression_threshold,
            "confidence": confidence,
            "trend": trend_analysis,
            "recommendation": self._get_recommendation(
                regression_detected, relative_change, trend_analysis
            ),
        }

    def _analyze_trend(self, values: list[float]) -> dict:
        """Analyze performance trend over time."""
        if len(values) < 3:
            return {"trend": "insufficient_data"}

        # Simple linear trend analysis
        x_values = list(range(len(values)))

        # Calculate correlation coefficient for trend
        try:
            correlation = statistics.correlation(x_values, values)

            if correlation > 0.3:
                trend = "degrading"
            elif correlation < -0.3:
                trend = "improving"
            else:
                trend = "stable"

        except statistics.StatisticsError:
            trend = "stable"

        # Recent vs older comparison
        recent_values = values[-min(5, len(values) // 2) :]
        older_values = values[: -len(recent_values)]

        if older_values:
            recent_mean = statistics.mean(recent_values)
            older_mean = statistics.mean(older_values)
            recent_change = recent_mean / older_mean if older_mean > 0 else 1.0
        else:
            recent_change = 1.0

        return {
            "trend": trend,
            "correlation": correlation if "correlation" in locals() else 0.0,
            "recent_change": recent_change,
            "sample_size": len(values),
        }

    def _get_recommendation(
        self, regression_detected: bool, relative_change: float, trend_analysis: dict
    ) -> str:
        """Generate recommendations based on regression analysis."""
        if not regression_detected:
            if trend_analysis["trend"] == "improving":
                return "Performance is stable and improving. Continue current optimizations."
            return "Performance is within acceptable limits. Continue monitoring."

        severity = (
            "critical"
            if relative_change > 2.0
            else "moderate"
            if relative_change > 1.5
            else "minor"
        )

        recommendations = {
            "critical": "CRITICAL: Performance regression detected. Immediate investigation required.",
            "moderate": "Moderate performance regression detected. Review recent changes and optimize.",
            "minor": "Minor performance regression detected. Monitor closely and consider optimization.",
        }

        return recommendations[severity]


class BenchmarkReporter:
    """Generate performance benchmark reports."""

    def __init__(self, storage: BenchmarkStorage):
        self.storage = storage

    def generate_report(
        self,
        test_results: dict,
        days_back: int = 30,
        output_path: Path | None = None,
    ) -> dict:
        """Generate comprehensive performance report."""

        report = {
            "generated_at": datetime.now().isoformat(),
            "period_days": days_back,
            "test_summary": {},
            "regressions": [],
            "trends": {},
            "recommendations": [],
        }

        detector = RegressionDetector()

        # Analyze each test
        for test_name, test_metrics in test_results.items():
            # Load historical data
            historical_benchmarks = self.storage.load_benchmarks(
                test_name=test_name, days_back=days_back
            )

            # Analyze for regressions
            for operation_type, metrics in test_metrics.items():
                regression_result = detector.detect_regression(
                    current_metrics=metrics,
                    historical_benchmarks=[
                        b
                        for b in historical_benchmarks
                        if b.operation_type == operation_type
                    ],
                )

                if regression_result["regression_detected"]:
                    report["regressions"].append({
                        "test_name": test_name,
                        "operation_type": operation_type,
                        "regression_details": regression_result,
                    })

                # Store trend analysis
                report["trends"][f"{test_name}_{operation_type}"] = (
                    regression_result.get("trend", {})
                )

            # Test summary
            report["test_summary"][test_name] = {
                "operations_tested": len(test_metrics),
                "historical_samples": len(historical_benchmarks),
                "regressions_detected": len([
                    r for r in report["regressions"] if r["test_name"] == test_name
                ]),
            }

        # Generate recommendations
        report["recommendations"] = self._generate_recommendations(report)

        # Save report if output path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)

        return report

    def _generate_recommendations(self, report: dict) -> list[str]:
        """Generate actionable recommendations from report."""
        recommendations = []

        regression_count = len(report["regressions"])

        if regression_count == 0:
            recommendations.append(
                "No performance regressions detected. System performance is stable."
            )
        elif regression_count < 3:
            recommendations.append(
                f"Minor regressions detected in {regression_count} area(s). Monitor closely."
            )
        else:
            recommendations.append(
                f"Multiple regressions detected ({regression_count}). Comprehensive performance review recommended."
            )

        # Add specific recommendations for critical regressions
        critical_regressions = [
            r
            for r in report["regressions"]
            if r["regression_details"].get("relative_change", 0) > 2.0
        ]

        if critical_regressions:
            recommendations.append(
                f"CRITICAL: {len(critical_regressions)} critical performance regressions require immediate attention."
            )

        return recommendations


class TestBenchmarkRegression:
    """Test performance benchmarking and regression detection."""

    @pytest.fixture
    def benchmark_storage(self, tmp_path):
        """Provide benchmark storage instance."""
        return BenchmarkStorage(storage_path=tmp_path / "benchmarks")

    @pytest.fixture
    def regression_detector(self):
        """Provide regression detector instance."""
        return RegressionDetector(regression_threshold=1.3, min_samples=3)

    def test_benchmark_storage_and_retrieval(self, benchmark_storage):
        """Test benchmark storage and retrieval functionality."""

        # Create test benchmarks
        benchmarks = []
        for i in range(10):
            benchmark = PerformanceBenchmark(
                test_name="test_storage_retrieval",
                operation_type=f"operation_{i % 3}",
                timestamp=datetime.now() - timedelta(days=i),
                metrics={
                    "avg_operation_time": 0.1 + (i * 0.01),
                    "throughput": 100 - (i * 2),
                    "memory_usage": 50 + (i * 3),
                },
                metadata={"test_run": i, "version": "1.0"},
            )
            benchmarks.append(benchmark)
            benchmark_storage.save_benchmark(benchmark)

        # Test retrieval without filters
        all_benchmarks = benchmark_storage.load_benchmarks()
        assert len(all_benchmarks) == 10

        # Test retrieval with test name filter
        filtered_benchmarks = benchmark_storage.load_benchmarks(
            test_name="test_storage_retrieval"
        )
        assert len(filtered_benchmarks) == 10

        # Test retrieval with operation type filter
        operation_benchmarks = benchmark_storage.load_benchmarks(
            operation_type="operation_0"
        )
        assert len(operation_benchmarks) == 4  # Every 3rd benchmark (0, 3, 6, 9)

        # Test retrieval with time filter
        recent_benchmarks = benchmark_storage.load_benchmarks(days_back=5)
        assert len(recent_benchmarks) <= 6  # Benchmarks from last 5 days

        # Test latest baseline retrieval
        latest_baseline = benchmark_storage.get_latest_baseline(
            "test_storage_retrieval", "operation_1"
        )
        assert latest_baseline is not None
        assert latest_baseline.operation_type == "operation_1"

        print(
            f"Storage test completed: {len(all_benchmarks)} benchmarks stored and retrieved"
        )

    def test_regression_detection_algorithms(
        self, benchmark_storage, regression_detector
    ):
        """Test regression detection algorithms."""

        # Create baseline benchmarks with stable performance
        baseline_metrics = [
            0.1,
            0.11,
            0.09,
            0.10,
            0.12,
            0.10,
            0.11,
        ]  # Stable around 0.1

        for i, metric_value in enumerate(baseline_metrics):
            benchmark = PerformanceBenchmark(
                test_name="test_regression_detection",
                operation_type="stable_operation",
                timestamp=datetime.now() - timedelta(days=len(baseline_metrics) - i),
                metrics={"avg_operation_time": metric_value},
                metadata={"baseline": True},
            )
            benchmark_storage.save_benchmark(benchmark)

        # Load historical benchmarks
        historical_benchmarks = benchmark_storage.load_benchmarks(
            test_name="test_regression_detection", operation_type="stable_operation"
        )

        # Test 1: No regression (performance within normal range)
        current_metrics = {"avg_operation_time": 0.105}
        result = regression_detector.detect_regression(
            current_metrics=current_metrics, historical_benchmarks=historical_benchmarks
        )

        assert not result["regression_detected"], (
            "Should not detect regression for stable performance"
        )
        assert result["relative_change"] < 1.3, (
            "Relative change should be within threshold"
        )
        print(
            f"No regression test: {result['current_value']:.6f}s (change: {result['relative_change']:.2f}x)"
        )

        # Test 2: Minor regression (just over threshold)
        current_metrics = {"avg_operation_time": 0.14}  # 40% increase
        result = regression_detector.detect_regression(
            current_metrics=current_metrics, historical_benchmarks=historical_benchmarks
        )

        assert result["regression_detected"], "Should detect minor regression"
        assert result["relative_change"] > 1.3, "Should exceed threshold"
        assert (
            "minor" in result["recommendation"].lower()
            or "moderate" in result["recommendation"].lower()
        )
        print(
            f"Minor regression test: {result['current_value']:.6f}s (change: {result['relative_change']:.2f}x)"
        )

        # Test 3: Critical regression (major performance degradation)
        current_metrics = {"avg_operation_time": 0.25}  # 150% increase
        result = regression_detector.detect_regression(
            current_metrics=current_metrics, historical_benchmarks=historical_benchmarks
        )

        assert result["regression_detected"], "Should detect critical regression"
        assert result["relative_change"] > 2.0, "Should indicate critical degradation"
        assert "critical" in result["recommendation"].lower()
        print(
            f"Critical regression test: {result['current_value']:.6f}s (change: {result['relative_change']:.2f}x)"
        )

        # Test 4: Performance improvement
        current_metrics = {"avg_operation_time": 0.08}  # 20% improvement
        result = regression_detector.detect_regression(
            current_metrics=current_metrics, historical_benchmarks=historical_benchmarks
        )

        assert not result["regression_detected"], (
            "Should not detect regression for improvement"
        )
        assert result["relative_change"] < 1.0, "Should show improvement"
        print(
            f"Performance improvement test: {result['current_value']:.6f}s (change: {result['relative_change']:.2f}x)"
        )

    def test_trend_analysis(self, benchmark_storage, regression_detector):
        """Test performance trend analysis."""

        # Create benchmarks with degrading trend
        degrading_metrics = [0.1, 0.12, 0.14, 0.16, 0.18, 0.20, 0.22]

        for i, metric_value in enumerate(degrading_metrics):
            benchmark = PerformanceBenchmark(
                test_name="test_trend_analysis",
                operation_type="degrading_operation",
                timestamp=datetime.now() - timedelta(days=len(degrading_metrics) - i),
                metrics={"avg_operation_time": metric_value},
                metadata={"trend": "degrading"},
            )
            benchmark_storage.save_benchmark(benchmark)

        # Test trend detection
        historical_benchmarks = benchmark_storage.load_benchmarks(
            test_name="test_trend_analysis", operation_type="degrading_operation"
        )

        current_metrics = {"avg_operation_time": 0.24}
        result = regression_detector.detect_regression(
            current_metrics=current_metrics, historical_benchmarks=historical_benchmarks
        )

        assert result["trend"]["trend"] == "degrading", "Should detect degrading trend"
        assert result["trend"]["correlation"] > 0, (
            "Should show positive correlation (degrading)"
        )
        print(
            f"Trend analysis: {result['trend']['trend']} (correlation: {result['trend']['correlation']:.3f})"
        )

        # Create benchmarks with improving trend
        improving_metrics = [0.2, 0.18, 0.16, 0.14, 0.12, 0.10, 0.08]

        for i, metric_value in enumerate(improving_metrics):
            benchmark = PerformanceBenchmark(
                test_name="test_trend_analysis",
                operation_type="improving_operation",
                timestamp=datetime.now() - timedelta(days=len(improving_metrics) - i),
                metrics={"avg_operation_time": metric_value},
                metadata={"trend": "improving"},
            )
            benchmark_storage.save_benchmark(benchmark)

        # Test improving trend detection
        historical_benchmarks = benchmark_storage.load_benchmarks(
            test_name="test_trend_analysis", operation_type="improving_operation"
        )

        current_metrics = {"avg_operation_time": 0.07}
        result = regression_detector.detect_regression(
            current_metrics=current_metrics, historical_benchmarks=historical_benchmarks
        )

        assert result["trend"]["trend"] == "improving", "Should detect improving trend"
        assert result["trend"]["correlation"] < 0, (
            "Should show negative correlation (improving)"
        )
        print(
            f"Improving trend analysis: {result['trend']['trend']} (correlation: {result['trend']['correlation']:.3f})"
        )

    def test_benchmark_reporting(self, benchmark_storage, tmp_path):
        """Test benchmark report generation."""

        # Create various test benchmarks
        test_scenarios = {
            "orchestration_performance": {
                "operation_init": {"avg_operation_time": 0.15, "memory_usage": 25.5},
                "operation_execute": {"avg_operation_time": 0.45, "memory_usage": 45.2},
            },
            "cache_performance": {
                "cache_get": {"avg_operation_time": 0.005, "throughput": 1000},
                "cache_set": {"avg_operation_time": 0.008, "throughput": 800},
            },
            "artifacts_performance": {
                "document_create": {"avg_operation_time": 0.025, "memory_usage": 15.3},
                "document_get": {"avg_operation_time": 0.012, "memory_usage": 8.7},
            },
        }

        # Create historical benchmarks for each test
        for test_name, operations in test_scenarios.items():
            for operation_type, metrics in operations.items():
                # Create 7 days of historical data with slight variations
                for day in range(7):
                    variation = 1.0 + (day * 0.02)  # Slight degradation over time
                    historical_metrics = {k: v * variation for k, v in metrics.items()}

                    benchmark = PerformanceBenchmark(
                        test_name=test_name,
                        operation_type=operation_type,
                        timestamp=datetime.now() - timedelta(days=7 - day),
                        metrics=historical_metrics,
                        metadata={"historical": True, "day": day},
                    )
                    benchmark_storage.save_benchmark(benchmark)

        # Generate report
        reporter = BenchmarkReporter(benchmark_storage)
        report = reporter.generate_report(
            test_results=test_scenarios,
            days_back=30,
            output_path=tmp_path / "benchmark_report.json",
        )

        # Verify report structure
        assert "generated_at" in report
        assert "test_summary" in report
        assert "regressions" in report
        assert "trends" in report
        assert "recommendations" in report

        # Verify test summaries
        assert len(report["test_summary"]) == len(test_scenarios)

        for test_name in test_scenarios:
            assert test_name in report["test_summary"]
            assert report["test_summary"][test_name]["historical_samples"] > 0

        # Verify report file was created
        report_file = tmp_path / "benchmark_report.json"
        assert report_file.exists()

        # Load and verify report file
        with open(report_file) as f:
            saved_report = json.load(f)

        assert saved_report["period_days"] == 30
        assert len(saved_report["recommendations"]) > 0

        print(
            f"Generated benchmark report with {len(report['test_summary'])} test suites"
        )
        print(f"Detected {len(report['regressions'])} performance regressions")
        print(f"Generated {len(report['recommendations'])} recommendations")

