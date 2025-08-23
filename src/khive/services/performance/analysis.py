"""Performance analysis, trend detection, and regression analysis."""

import logging
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from .benchmark_framework import BenchmarkResult
from .storage import BenchmarkStorage

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    """Performance trend directions."""

    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    INSUFFICIENT_DATA = "insufficient_data"
    VOLATILE = "volatile"


class RegressionSeverity(Enum):
    """Regression severity levels."""

    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    CRITICAL = "critical"


@dataclass
class TrendAnalysis:
    """Performance trend analysis result."""

    direction: TrendDirection
    confidence: float  # 0.0 to 1.0
    slope: float  # Rate of change
    correlation: float  # -1.0 to 1.0
    sample_size: int
    time_span_days: float

    # Statistical metrics
    mean_value: float
    std_deviation: float
    min_value: float
    max_value: float

    # Recent vs historical comparison
    recent_mean: float
    historical_mean: float
    recent_vs_historical_change: float

    metadata: dict[str, Any]


@dataclass
class RegressionResult:
    """Performance regression detection result."""

    regression_detected: bool
    severity: RegressionSeverity
    confidence: float

    current_value: float
    baseline_mean: float
    baseline_std: float

    relative_change: float  # Multiplier (1.5 = 50% increase)
    absolute_change: float  # Raw difference
    z_score: float  # Standard deviations from mean

    threshold_exceeded: bool
    trend_analysis: TrendAnalysis
    recommendation: str

    metadata: dict[str, Any]


@dataclass
class BottleneckAnalysis:
    """System bottleneck identification result."""

    bottleneck_type: str  # cpu, memory, io, network, etc.
    severity: str  # low, medium, high, critical
    confidence: float

    # Resource utilization
    current_utilization: float
    historical_avg_utilization: float
    utilization_percentile: float

    # Impact analysis
    performance_impact: float  # Estimated % impact on performance
    operations_affected: list[str]

    recommendation: str
    optimization_suggestions: list[str]

    metadata: dict[str, Any]


class PerformanceAnalyzer:
    """Core performance analysis functionality."""

    def __init__(self, storage: BenchmarkStorage):
        self.storage = storage

    def analyze_metric(
        self,
        results: list[BenchmarkResult],
        metric_name: str,
        include_outliers: bool = True,
    ) -> dict[str, Any]:
        """Analyze a specific performance metric across results."""

        if not results:
            return {"error": "No results provided"}

        values = []
        timestamps = []

        for result in results:
            metric_value = self._extract_metric_value(result, metric_name)
            if metric_value is not None:
                values.append(metric_value)
                timestamps.append(result.timestamp)

        if not values:
            return {"error": f"No valid values found for metric {metric_name}"}

        # Remove outliers if requested
        if not include_outliers:
            values = self._remove_outliers(values)

        # Basic statistical analysis
        analysis = {
            "metric_name": metric_name,
            "sample_size": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "mode": statistics.mode(values) if len(set(values)) < len(values) else None,
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "variance": statistics.variance(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
        }

        # Percentiles
        if len(values) > 1:
            sorted_values = sorted(values)
            analysis.update(
                {
                    "p25": sorted_values[int(len(sorted_values) * 0.25)],
                    "p50": sorted_values[int(len(sorted_values) * 0.50)],
                    "p75": sorted_values[int(len(sorted_values) * 0.75)],
                    "p90": sorted_values[int(len(sorted_values) * 0.90)],
                    "p95": sorted_values[int(len(sorted_values) * 0.95)],
                    "p99": sorted_values[int(len(sorted_values) * 0.99)],
                }
            )

        # Time-based analysis
        if len(timestamps) > 1:
            time_span = (
                max(timestamps) - min(timestamps)
            ).total_seconds() / 86400  # days
            analysis["time_span_days"] = time_span
            analysis["samples_per_day"] = len(values) / max(time_span, 1)

        # Distribution analysis
        analysis["coefficient_of_variation"] = (
            analysis["std_dev"] / analysis["mean"]
            if analysis["mean"] != 0
            else float("inf")
        )

        analysis["skewness"] = self._calculate_skewness(values)
        analysis["kurtosis"] = self._calculate_kurtosis(values)

        return analysis

    def _extract_metric_value(
        self, result: BenchmarkResult, metric_name: str
    ) -> float | None:
        """Extract a specific metric value from a benchmark result."""

        # Check standard metrics first
        if hasattr(result.metrics, metric_name):
            return getattr(result.metrics, metric_name)

        # Check computed properties
        computed_metrics = {
            "success_rate": result.metrics.success_rate,
            "throughput_ops_per_sec": result.metrics.throughput_ops_per_sec,
            "avg_operation_time_ms": result.metrics.avg_operation_time_ms,
        }

        if metric_name in computed_metrics:
            return computed_metrics[metric_name]

        # Check custom metrics
        if metric_name in result.metrics.custom_metrics:
            custom_value = result.metrics.custom_metrics[metric_name]
            if isinstance(custom_value, (int, float)):
                return custom_value

        return None

    def _remove_outliers(self, values: list[float], method: str = "iqr") -> list[float]:
        """Remove outliers from a list of values."""

        if len(values) < 4:
            return values

        if method == "iqr":
            # Interquartile Range method
            sorted_values = sorted(values)
            q1 = sorted_values[len(sorted_values) // 4]
            q3 = sorted_values[3 * len(sorted_values) // 4]
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            return [v for v in values if lower_bound <= v <= upper_bound]

        if method == "zscore":
            # Z-score method
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values)

            if std_val == 0:
                return values

            return [v for v in values if abs((v - mean_val) / std_val) <= 3]

        return values

    def _calculate_skewness(self, values: list[float]) -> float:
        """Calculate skewness of a distribution."""
        if len(values) < 3:
            return 0.0

        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values)

        if std_val == 0:
            return 0.0

        n = len(values)
        skewness = (
            sum(((x - mean_val) / std_val) ** 3 for x in values)
            * n
            / ((n - 1) * (n - 2))
        )
        return skewness

    def _calculate_kurtosis(self, values: list[float]) -> float:
        """Calculate kurtosis of a distribution."""
        if len(values) < 4:
            return 0.0

        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values)

        if std_val == 0:
            return 0.0

        n = len(values)
        fourth_moment = sum(((x - mean_val) / std_val) ** 4 for x in values) / n
        kurtosis = fourth_moment - 3  # Excess kurtosis
        return kurtosis


class TrendAnalyzer:
    """Analyzes performance trends over time."""

    def __init__(self, storage: BenchmarkStorage):
        self.storage = storage
        self.analyzer = PerformanceAnalyzer(storage)

    def analyze_trend(
        self,
        benchmark_name: str,
        operation_type: str,
        metric_name: str = "duration",
        days_back: int = 30,
        min_samples: int = 5,
    ) -> TrendAnalysis:
        """Analyze performance trend for a specific benchmark and metric."""

        since = datetime.now() - timedelta(days=days_back)
        results = self.storage.get_results(
            benchmark_name=benchmark_name, operation_type=operation_type, since=since
        )

        if len(results) < min_samples:
            return TrendAnalysis(
                direction=TrendDirection.INSUFFICIENT_DATA,
                confidence=0.0,
                slope=0.0,
                correlation=0.0,
                sample_size=len(results),
                time_span_days=0.0,
                mean_value=0.0,
                std_deviation=0.0,
                min_value=0.0,
                max_value=0.0,
                recent_mean=0.0,
                historical_mean=0.0,
                recent_vs_historical_change=0.0,
                metadata={
                    "reason": f"Insufficient samples: {len(results)} < {min_samples}",
                    "benchmark_name": benchmark_name,
                    "operation_type": operation_type,
                    "metric_name": metric_name,
                },
            )

        # Extract values and timestamps
        values = []
        timestamps = []

        for result in sorted(results, key=lambda r: r.timestamp):
            value = self.analyzer._extract_metric_value(result, metric_name)
            if value is not None:
                values.append(value)
                timestamps.append(result.timestamp)

        if not values:
            return TrendAnalysis(
                direction=TrendDirection.INSUFFICIENT_DATA,
                confidence=0.0,
                slope=0.0,
                correlation=0.0,
                sample_size=0,
                time_span_days=0.0,
                mean_value=0.0,
                std_deviation=0.0,
                min_value=0.0,
                max_value=0.0,
                recent_mean=0.0,
                historical_mean=0.0,
                recent_vs_historical_change=0.0,
                metadata={"reason": f"No valid {metric_name} values found"},
            )

        # Calculate time-based metrics
        time_span = (timestamps[-1] - timestamps[0]).total_seconds() / 86400  # days

        # Basic statistics
        mean_value = statistics.mean(values)
        std_deviation = statistics.stdev(values) if len(values) > 1 else 0
        min_value = min(values)
        max_value = max(values)

        # Trend analysis using linear correlation
        x_values = [(ts - timestamps[0]).total_seconds() for ts in timestamps]
        correlation = self._calculate_correlation(x_values, values)
        slope = self._calculate_slope(x_values, values)

        # Determine trend direction
        direction = self._determine_trend_direction(
            correlation, slope, std_deviation, mean_value
        )

        # Calculate confidence based on correlation strength and sample size
        confidence = self._calculate_trend_confidence(
            correlation, len(values), std_deviation, mean_value
        )

        # Recent vs historical comparison
        split_point = max(1, len(values) // 3)  # Use last 1/3 as "recent"
        recent_values = values[-split_point:]
        historical_values = (
            values[:-split_point] if len(values) > split_point else values
        )

        recent_mean = statistics.mean(recent_values)
        historical_mean = statistics.mean(historical_values)
        recent_vs_historical_change = (
            (recent_mean / historical_mean) if historical_mean != 0 else 1.0
        )

        return TrendAnalysis(
            direction=direction,
            confidence=confidence,
            slope=slope,
            correlation=correlation,
            sample_size=len(values),
            time_span_days=time_span,
            mean_value=mean_value,
            std_deviation=std_deviation,
            min_value=min_value,
            max_value=max_value,
            recent_mean=recent_mean,
            historical_mean=historical_mean,
            recent_vs_historical_change=recent_vs_historical_change,
            metadata={
                "benchmark_name": benchmark_name,
                "operation_type": operation_type,
                "metric_name": metric_name,
                "days_analyzed": days_back,
                "coefficient_of_variation": (
                    std_deviation / mean_value if mean_value != 0 else 0
                ),
            },
        )

    def _calculate_correlation(
        self, x_values: list[float], y_values: list[float]
    ) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x_values) < 2 or len(y_values) < 2:
            return 0.0

        try:
            return statistics.correlation(x_values, y_values)
        except statistics.StatisticsError:
            return 0.0

    def _calculate_slope(self, x_values: list[float], y_values: list[float]) -> float:
        """Calculate linear regression slope."""
        if len(x_values) < 2:
            return 0.0

        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values, strict=False))
        sum_x2 = sum(x * x for x in x_values)

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope

    def _determine_trend_direction(
        self, correlation: float, slope: float, std_deviation: float, mean_value: float
    ) -> TrendDirection:
        """Determine trend direction based on correlation and other factors."""

        # Check for high volatility
        coefficient_of_variation = std_deviation / mean_value if mean_value != 0 else 0
        if coefficient_of_variation > 0.5:  # More than 50% relative variation
            return TrendDirection.VOLATILE

        # Determine direction based on correlation
        if abs(correlation) < 0.2:
            return TrendDirection.STABLE
        if correlation > 0.3:
            return TrendDirection.DEGRADING if slope > 0 else TrendDirection.IMPROVING
        if correlation < -0.3:
            return TrendDirection.IMPROVING if slope < 0 else TrendDirection.DEGRADING
        return TrendDirection.STABLE

    def _calculate_trend_confidence(
        self,
        correlation: float,
        sample_size: int,
        std_deviation: float,
        mean_value: float,
    ) -> float:
        """Calculate confidence in trend analysis."""

        # Base confidence on correlation strength
        base_confidence = min(abs(correlation), 1.0)

        # Adjust for sample size (more samples = higher confidence)
        sample_factor = min(sample_size / 20.0, 1.0)  # Max confidence at 20+ samples

        # Adjust for data consistency (lower std dev = higher confidence)
        coefficient_of_variation = (
            std_deviation / mean_value if mean_value != 0 else 1.0
        )
        consistency_factor = max(0.1, 1.0 - coefficient_of_variation)

        confidence = base_confidence * sample_factor * consistency_factor
        return min(confidence, 1.0)


class RegressionDetector:
    """Detects performance regressions."""

    def __init__(
        self,
        storage: BenchmarkStorage,
        minor_threshold: float = 1.2,  # 20% degradation
        moderate_threshold: float = 1.5,  # 50% degradation
        critical_threshold: float = 2.0,  # 100% degradation
        min_samples: int = 5,
        statistical_confidence: float = 0.8,
    ):
        self.storage = storage
        self.minor_threshold = minor_threshold
        self.moderate_threshold = moderate_threshold
        self.critical_threshold = critical_threshold
        self.min_samples = min_samples
        self.statistical_confidence = statistical_confidence
        self.trend_analyzer = TrendAnalyzer(storage)

    def detect_regression(
        self,
        current_result: BenchmarkResult,
        metric_name: str = "duration",
        comparison_days: int = 30,
    ) -> RegressionResult:
        """Detect regression by comparing current result to historical baseline."""

        # Get historical results
        since = datetime.now() - timedelta(days=comparison_days)
        historical_results = self.storage.get_results(
            benchmark_name=current_result.benchmark_name,
            operation_type=current_result.operation_type,
            since=since,
        )

        # Remove current result if it's in historical data
        historical_results = [
            r for r in historical_results if r.timestamp < current_result.timestamp
        ]

        if len(historical_results) < self.min_samples:
            return RegressionResult(
                regression_detected=False,
                severity=RegressionSeverity.NONE,
                confidence=0.0,
                current_value=0.0,
                baseline_mean=0.0,
                baseline_std=0.0,
                relative_change=1.0,
                absolute_change=0.0,
                z_score=0.0,
                threshold_exceeded=False,
                trend_analysis=TrendAnalysis(
                    direction=TrendDirection.INSUFFICIENT_DATA,
                    confidence=0.0,
                    slope=0.0,
                    correlation=0.0,
                    sample_size=len(historical_results),
                    time_span_days=0.0,
                    mean_value=0.0,
                    std_deviation=0.0,
                    min_value=0.0,
                    max_value=0.0,
                    recent_mean=0.0,
                    historical_mean=0.0,
                    recent_vs_historical_change=1.0,
                    metadata={},
                ),
                recommendation="Insufficient historical data for regression detection",
                metadata={
                    "historical_samples": len(historical_results),
                    "min_required": self.min_samples,
                },
            )

        # Extract current and historical values
        analyzer = PerformanceAnalyzer(self.storage)
        current_value = analyzer._extract_metric_value(current_result, metric_name)

        if current_value is None:
            return self._create_error_result(
                f"Cannot extract metric {metric_name} from current result"
            )

        historical_values = []
        for result in historical_results:
            value = analyzer._extract_metric_value(result, metric_name)
            if value is not None:
                historical_values.append(value)

        if not historical_values:
            return self._create_error_result(
                f"No valid historical {metric_name} values found"
            )

        # Calculate baseline statistics
        baseline_mean = statistics.mean(historical_values)
        baseline_std = (
            statistics.stdev(historical_values) if len(historical_values) > 1 else 0
        )

        # Calculate regression metrics
        relative_change = current_value / baseline_mean if baseline_mean != 0 else 1.0
        absolute_change = current_value - baseline_mean
        z_score = abs(absolute_change) / baseline_std if baseline_std > 0 else 0.0

        # Determine regression severity
        regression_detected = relative_change > self.minor_threshold
        severity = self._determine_severity(relative_change)

        # Calculate confidence based on statistical significance
        confidence = self._calculate_regression_confidence(
            z_score, len(historical_values), baseline_std, baseline_mean
        )

        # Get trend analysis
        trend_analysis = self.trend_analyzer.analyze_trend(
            benchmark_name=current_result.benchmark_name,
            operation_type=current_result.operation_type,
            metric_name=metric_name,
            days_back=comparison_days,
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(
            severity, trend_analysis, relative_change
        )

        return RegressionResult(
            regression_detected=regression_detected,
            severity=severity,
            confidence=confidence,
            current_value=current_value,
            baseline_mean=baseline_mean,
            baseline_std=baseline_std,
            relative_change=relative_change,
            absolute_change=absolute_change,
            z_score=z_score,
            threshold_exceeded=relative_change > self.minor_threshold,
            trend_analysis=trend_analysis,
            recommendation=recommendation,
            metadata={
                "metric_name": metric_name,
                "comparison_days": comparison_days,
                "historical_samples": len(historical_values),
                "thresholds": {
                    "minor": self.minor_threshold,
                    "moderate": self.moderate_threshold,
                    "critical": self.critical_threshold,
                },
            },
        )

    def _determine_severity(self, relative_change: float) -> RegressionSeverity:
        """Determine regression severity based on relative change."""
        if relative_change >= self.critical_threshold:
            return RegressionSeverity.CRITICAL
        if relative_change >= self.moderate_threshold:
            return RegressionSeverity.MODERATE
        if relative_change >= self.minor_threshold:
            return RegressionSeverity.MINOR
        return RegressionSeverity.NONE

    def _calculate_regression_confidence(
        self,
        z_score: float,
        sample_size: int,
        baseline_std: float,
        baseline_mean: float,
    ) -> float:
        """Calculate confidence in regression detection."""

        # Statistical significance based on z-score
        statistical_confidence = min(z_score / 2.0, 1.0) if z_score > 0 else 0.0

        # Sample size confidence
        sample_confidence = min(
            sample_size / 30.0, 1.0
        )  # Max confidence at 30+ samples

        # Data quality confidence (lower std dev = higher confidence)
        if baseline_mean != 0 and baseline_std > 0:
            cv = baseline_std / baseline_mean
            quality_confidence = max(0.2, 1.0 - cv)  # Minimum 20% confidence
        else:
            quality_confidence = 0.5

        overall_confidence = (
            statistical_confidence * 0.5
            + sample_confidence * 0.3
            + quality_confidence * 0.2
        )

        return min(overall_confidence, 1.0)

    def _generate_recommendation(
        self,
        severity: RegressionSeverity,
        trend_analysis: TrendAnalysis,
        relative_change: float,
    ) -> str:
        """Generate actionable recommendation based on regression analysis."""

        if severity == RegressionSeverity.NONE:
            if trend_analysis.direction == TrendDirection.IMPROVING:
                return "Performance is stable and improving. Continue current optimizations."
            return "Performance is within acceptable limits. Continue monitoring."

        base_messages = {
            RegressionSeverity.MINOR: f"Minor performance regression detected ({relative_change:.1f}x slower). Monitor closely and consider optimization.",
            RegressionSeverity.MODERATE: f"Moderate performance regression detected ({relative_change:.1f}x slower). Review recent changes and optimize.",
            RegressionSeverity.CRITICAL: f"CRITICAL performance regression detected ({relative_change:.1f}x slower). Immediate investigation required.",
        }

        message = base_messages.get(severity, "")

        # Add trend-specific guidance
        if trend_analysis.direction == TrendDirection.DEGRADING:
            message += " Performance trend is consistently degrading over time."
        elif trend_analysis.direction == TrendDirection.VOLATILE:
            message += (
                " Performance is highly variable - investigate consistency issues."
            )

        return message

    def _create_error_result(self, error_message: str) -> RegressionResult:
        """Create a regression result for error cases."""
        return RegressionResult(
            regression_detected=False,
            severity=RegressionSeverity.NONE,
            confidence=0.0,
            current_value=0.0,
            baseline_mean=0.0,
            baseline_std=0.0,
            relative_change=1.0,
            absolute_change=0.0,
            z_score=0.0,
            threshold_exceeded=False,
            trend_analysis=TrendAnalysis(
                direction=TrendDirection.INSUFFICIENT_DATA,
                confidence=0.0,
                slope=0.0,
                correlation=0.0,
                sample_size=0,
                time_span_days=0.0,
                mean_value=0.0,
                std_deviation=0.0,
                min_value=0.0,
                max_value=0.0,
                recent_mean=0.0,
                historical_mean=0.0,
                recent_vs_historical_change=1.0,
                metadata={},
            ),
            recommendation=error_message,
            metadata={"error": error_message},
        )


class BottleneckIdentifier:
    """Identifies performance bottlenecks in system resources."""

    def __init__(self, storage: BenchmarkStorage):
        self.storage = storage

        # Thresholds for bottleneck detection (percentiles)
        self.cpu_threshold = 80.0  # CPU usage %
        self.memory_threshold = 80.0  # Memory usage %
        self.io_threshold = 1024 * 1024 * 10  # 10MB I/O
        self.network_threshold = 1024 * 1024 * 5  # 5MB network

    def identify_bottlenecks(
        self,
        benchmark_name: str,
        operation_type: str | None = None,
        days_back: int = 7,
    ) -> list[BottleneckAnalysis]:
        """Identify performance bottlenecks for a benchmark."""

        since = datetime.now() - timedelta(days=days_back)
        results = self.storage.get_results(
            benchmark_name=benchmark_name, operation_type=operation_type, since=since
        )

        if not results:
            return []

        bottlenecks = []

        # Analyze CPU bottlenecks
        cpu_bottleneck = self._analyze_cpu_bottleneck(results)
        if cpu_bottleneck:
            bottlenecks.append(cpu_bottleneck)

        # Analyze memory bottlenecks
        memory_bottleneck = self._analyze_memory_bottleneck(results)
        if memory_bottleneck:
            bottlenecks.append(memory_bottleneck)

        # Analyze I/O bottlenecks
        io_bottleneck = self._analyze_io_bottleneck(results)
        if io_bottleneck:
            bottlenecks.append(io_bottleneck)

        # Analyze network bottlenecks
        network_bottleneck = self._analyze_network_bottleneck(results)
        if network_bottleneck:
            bottlenecks.append(network_bottleneck)

        return bottlenecks

    def _analyze_cpu_bottleneck(
        self, results: list[BenchmarkResult]
    ) -> BottleneckAnalysis | None:
        """Analyze CPU usage patterns for bottlenecks."""

        cpu_values = [
            r.metrics.cpu_percent_peak
            for r in results
            if r.metrics.cpu_percent_peak > 0
        ]

        if not cpu_values:
            return None

        avg_cpu = statistics.mean(cpu_values)
        max_cpu = max(cpu_values)

        # Check if CPU usage is consistently high
        high_cpu_count = sum(1 for cpu in cpu_values if cpu > self.cpu_threshold)
        high_cpu_ratio = high_cpu_count / len(cpu_values)

        if (
            high_cpu_ratio > 0.3 or max_cpu > 95
        ):  # More than 30% of samples high, or any sample > 95%
            severity = self._determine_bottleneck_severity(avg_cpu, self.cpu_threshold)
            confidence = min(high_cpu_ratio + (max_cpu / 100), 1.0)

            return BottleneckAnalysis(
                bottleneck_type="cpu",
                severity=severity,
                confidence=confidence,
                current_utilization=max_cpu,
                historical_avg_utilization=avg_cpu,
                utilization_percentile=self._calculate_percentile(cpu_values, max_cpu),
                performance_impact=self._estimate_cpu_performance_impact(
                    avg_cpu, max_cpu
                ),
                operations_affected=[
                    r.operation_type
                    for r in results
                    if r.metrics.cpu_percent_peak > self.cpu_threshold
                ],
                recommendation=self._generate_cpu_recommendation(avg_cpu, max_cpu),
                optimization_suggestions=[
                    "Consider optimizing CPU-intensive algorithms",
                    "Review concurrent execution patterns",
                    "Profile code for hot spots",
                    "Consider using async/await for I/O operations",
                ],
                metadata={
                    "avg_cpu_percent": avg_cpu,
                    "max_cpu_percent": max_cpu,
                    "samples_above_threshold": high_cpu_count,
                    "total_samples": len(cpu_values),
                },
            )

        return None

    def _analyze_memory_bottleneck(
        self, results: list[BenchmarkResult]
    ) -> BottleneckAnalysis | None:
        """Analyze memory usage patterns for bottlenecks."""

        memory_values = [
            r.metrics.memory_peak_mb for r in results if r.metrics.memory_peak_mb > 0
        ]

        if not memory_values:
            return None

        avg_memory = statistics.mean(memory_values)
        max_memory = max(memory_values)

        # Check for memory growth patterns
        memory_growth = [
            r.metrics.memory_delta_mb for r in results if r.metrics.memory_delta_mb > 0
        ]

        avg_growth = statistics.mean(memory_growth) if memory_growth else 0

        # Detect potential memory issues
        high_memory_usage = max_memory > 500  # More than 500MB
        significant_growth = avg_growth > 10  # More than 10MB average growth

        if high_memory_usage or significant_growth:
            severity = self._determine_memory_severity(max_memory, avg_growth)
            confidence = self._calculate_memory_confidence(
                max_memory, avg_growth, len(memory_values)
            )

            return BottleneckAnalysis(
                bottleneck_type="memory",
                severity=severity,
                confidence=confidence,
                current_utilization=max_memory,
                historical_avg_utilization=avg_memory,
                utilization_percentile=self._calculate_percentile(
                    memory_values, max_memory
                ),
                performance_impact=self._estimate_memory_performance_impact(
                    avg_memory, max_memory, avg_growth
                ),
                operations_affected=[
                    r.operation_type
                    for r in results
                    if r.metrics.memory_peak_mb > avg_memory * 1.5
                ],
                recommendation=self._generate_memory_recommendation(
                    max_memory, avg_growth
                ),
                optimization_suggestions=[
                    "Review data structures for memory efficiency",
                    "Implement object pooling for frequently created objects",
                    "Consider lazy loading for large datasets",
                    "Profile memory allocations and deallocations",
                ],
                metadata={
                    "avg_memory_mb": avg_memory,
                    "max_memory_mb": max_memory,
                    "avg_growth_mb": avg_growth,
                    "samples_with_growth": len(memory_growth),
                },
            )

        return None

    def _analyze_io_bottleneck(
        self, results: list[BenchmarkResult]
    ) -> BottleneckAnalysis | None:
        """Analyze I/O patterns for bottlenecks."""

        io_read_values = [
            r.metrics.io_read_bytes for r in results if r.metrics.io_read_bytes > 0
        ]
        io_write_values = [
            r.metrics.io_write_bytes for r in results if r.metrics.io_write_bytes > 0
        ]

        if not io_read_values and not io_write_values:
            return None

        total_io_values = [
            r.metrics.io_read_bytes + r.metrics.io_write_bytes
            for r in results
            if (r.metrics.io_read_bytes + r.metrics.io_write_bytes) > 0
        ]

        if not total_io_values:
            return None

        avg_io = statistics.mean(total_io_values)
        max_io = max(total_io_values)

        # Check for high I/O usage
        if max_io > self.io_threshold or avg_io > self.io_threshold / 2:
            severity = self._determine_bottleneck_severity(avg_io, self.io_threshold)
            confidence = min((max_io / self.io_threshold) * 0.7, 1.0)

            return BottleneckAnalysis(
                bottleneck_type="io",
                severity=severity,
                confidence=confidence,
                current_utilization=max_io,
                historical_avg_utilization=avg_io,
                utilization_percentile=self._calculate_percentile(
                    total_io_values, max_io
                ),
                performance_impact=self._estimate_io_performance_impact(avg_io, max_io),
                operations_affected=[
                    r.operation_type
                    for r in results
                    if (r.metrics.io_read_bytes + r.metrics.io_write_bytes)
                    > avg_io * 1.5
                ],
                recommendation=self._generate_io_recommendation(avg_io, max_io),
                optimization_suggestions=[
                    "Implement I/O operation batching",
                    "Use asynchronous I/O operations",
                    "Consider caching frequently accessed data",
                    "Optimize file access patterns",
                ],
                metadata={
                    "avg_io_bytes": avg_io,
                    "max_io_bytes": max_io,
                    "avg_read_bytes": (
                        statistics.mean(io_read_values) if io_read_values else 0
                    ),
                    "avg_write_bytes": (
                        statistics.mean(io_write_values) if io_write_values else 0
                    ),
                },
            )

        return None

    def _analyze_network_bottleneck(
        self, results: list[BenchmarkResult]
    ) -> BottleneckAnalysis | None:
        """Analyze network patterns for bottlenecks."""

        network_values = [
            r.metrics.network_sent_bytes + r.metrics.network_recv_bytes
            for r in results
            if (r.metrics.network_sent_bytes + r.metrics.network_recv_bytes) > 0
        ]

        if not network_values:
            return None

        avg_network = statistics.mean(network_values)
        max_network = max(network_values)

        # Check for high network usage
        if (
            max_network > self.network_threshold
            or avg_network > self.network_threshold / 2
        ):
            severity = self._determine_bottleneck_severity(
                avg_network, self.network_threshold
            )
            confidence = min((max_network / self.network_threshold) * 0.6, 1.0)

            return BottleneckAnalysis(
                bottleneck_type="network",
                severity=severity,
                confidence=confidence,
                current_utilization=max_network,
                historical_avg_utilization=avg_network,
                utilization_percentile=self._calculate_percentile(
                    network_values, max_network
                ),
                performance_impact=self._estimate_network_performance_impact(
                    avg_network, max_network
                ),
                operations_affected=[
                    r.operation_type
                    for r in results
                    if (r.metrics.network_sent_bytes + r.metrics.network_recv_bytes)
                    > avg_network * 1.5
                ],
                recommendation=self._generate_network_recommendation(
                    avg_network, max_network
                ),
                optimization_suggestions=[
                    "Implement request batching and connection pooling",
                    "Use compression for large data transfers",
                    "Consider local caching to reduce network calls",
                    "Optimize API payload sizes",
                ],
                metadata={
                    "avg_network_bytes": avg_network,
                    "max_network_bytes": max_network,
                    "samples_analyzed": len(network_values),
                },
            )

        return None

    def _determine_bottleneck_severity(
        self, current_value: float, threshold: float
    ) -> str:
        """Determine bottleneck severity based on threshold comparison."""
        ratio = current_value / threshold

        if ratio >= 2.0:
            return "critical"
        if ratio >= 1.5:
            return "high"
        if ratio >= 1.2:
            return "medium"
        return "low"

    def _determine_memory_severity(self, max_memory: float, avg_growth: float) -> str:
        """Determine memory bottleneck severity."""
        if max_memory > 1000 or avg_growth > 50:  # 1GB or 50MB average growth
            return "critical"
        if max_memory > 500 or avg_growth > 20:  # 500MB or 20MB average growth
            return "high"
        if max_memory > 200 or avg_growth > 10:  # 200MB or 10MB average growth
            return "medium"
        return "low"

    def _calculate_percentile(self, values: list[float], target_value: float) -> float:
        """Calculate what percentile a value represents in the distribution."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        position = next(
            (i for i, v in enumerate(sorted_values) if v >= target_value),
            len(sorted_values),
        )
        return (position / len(sorted_values)) * 100

    def _calculate_memory_confidence(
        self, max_memory: float, avg_growth: float, sample_size: int
    ) -> float:
        """Calculate confidence in memory bottleneck detection."""
        memory_factor = min(max_memory / 1000, 1.0)  # Normalize to 1GB
        growth_factor = min(avg_growth / 50, 1.0)  # Normalize to 50MB
        sample_factor = min(sample_size / 20, 1.0)  # Normalize to 20 samples

        confidence = memory_factor * 0.4 + growth_factor * 0.4 + sample_factor * 0.2
        return min(confidence, 1.0)

    def _estimate_cpu_performance_impact(self, avg_cpu: float, max_cpu: float) -> float:
        """Estimate performance impact of CPU bottleneck."""
        # High CPU usage typically has significant performance impact
        if max_cpu > 95:
            return 40.0  # 40% estimated impact
        if avg_cpu > 80:
            return 25.0  # 25% estimated impact
        if avg_cpu > 60:
            return 15.0  # 15% estimated impact
        return 5.0  # 5% estimated impact

    def _estimate_memory_performance_impact(
        self, avg_memory: float, max_memory: float, avg_growth: float
    ) -> float:
        """Estimate performance impact of memory bottleneck."""
        # Memory impact depends on both absolute usage and growth patterns
        usage_impact = min((max_memory / 1000) * 20, 30)  # Up to 30% for 1GB+ usage
        growth_impact = min((avg_growth / 50) * 15, 20)  # Up to 20% for 50MB+ growth

        return usage_impact + growth_impact

    def _estimate_io_performance_impact(self, avg_io: float, max_io: float) -> float:
        """Estimate performance impact of I/O bottleneck."""
        # I/O can have significant impact on performance
        impact_ratio = max_io / (1024 * 1024 * 100)  # Normalize to 100MB
        return min(impact_ratio * 50, 60)  # Up to 60% impact

    def _estimate_network_performance_impact(
        self, avg_network: float, max_network: float
    ) -> float:
        """Estimate performance impact of network bottleneck."""
        # Network impact varies greatly by operation type
        impact_ratio = max_network / (1024 * 1024 * 50)  # Normalize to 50MB
        return min(impact_ratio * 30, 40)  # Up to 40% impact

    def _generate_cpu_recommendation(self, avg_cpu: float, max_cpu: float) -> str:
        """Generate CPU-specific recommendations."""
        if max_cpu > 95:
            return "Critical CPU bottleneck detected. Immediate optimization required to prevent system overload."
        if avg_cpu > 80:
            return "High CPU usage detected. Review algorithms and consider performance optimizations."
        return "Moderate CPU usage detected. Monitor for trends and consider preventive optimizations."

    def _generate_memory_recommendation(
        self, max_memory: float, avg_growth: float
    ) -> str:
        """Generate memory-specific recommendations."""
        if max_memory > 1000:
            return "Very high memory usage detected. Review data structures and implement memory optimization."
        if avg_growth > 20:
            return "Significant memory growth pattern detected. Investigate potential memory leaks."
        return "Elevated memory usage detected. Consider memory profiling and optimization."

    def _generate_io_recommendation(self, avg_io: float, max_io: float) -> str:
        """Generate I/O-specific recommendations."""
        if max_io > self.io_threshold * 5:
            return "Very high I/O operations detected. Consider batching, caching, or asynchronous patterns."
        return "High I/O operations detected. Review file access patterns and consider optimization."

    def _generate_network_recommendation(
        self, avg_network: float, max_network: float
    ) -> str:
        """Generate network-specific recommendations."""
        if max_network > self.network_threshold * 3:
            return "Very high network usage detected. Consider request batching, compression, and caching."
        return "High network usage detected. Review API calls and consider optimization strategies."
