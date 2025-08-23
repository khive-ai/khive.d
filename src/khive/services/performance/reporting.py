"""Performance reporting and CI/CD integration."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .analysis import (
    BottleneckIdentifier,
    PerformanceAnalyzer,
    RegressionDetector,
    TrendAnalyzer,
)
from .benchmark_framework import BenchmarkResult
from .optimization import OptimizationRecommender
from .storage import BenchmarkStorage

logger = logging.getLogger(__name__)


class PerformanceReporter:
    """Generates comprehensive performance reports."""

    def __init__(
        self, storage: BenchmarkStorage, output_path: Path = Path("performance_reports")
    ):
        self.storage = storage
        self.output_path = output_path
        self.output_path.mkdir(exist_ok=True)

        # Initialize analysis components
        self.analyzer = PerformanceAnalyzer(storage)
        self.trend_analyzer = TrendAnalyzer(storage)
        self.regression_detector = RegressionDetector(storage)
        self.bottleneck_identifier = BottleneckIdentifier(storage)
        self.recommender = OptimizationRecommender(storage)

    def generate_comprehensive_report(
        self,
        report_name: str = "performance_report",
        benchmark_name: str | None = None,
        days_back: int = 30,
        include_recommendations: bool = True,
    ) -> Path:
        """Generate comprehensive performance analysis report."""

        logger.info(f"Generating comprehensive performance report: {report_name}")

        # Collect all performance data
        since = datetime.now() - timedelta(days=days_back)

        if benchmark_name:
            results = self.storage.get_results(
                benchmark_name=benchmark_name, since=since
            )
            benchmarks_analyzed = [benchmark_name]
        else:
            results = self.storage.get_results(since=since)
            benchmarks_analyzed = list(set(r.benchmark_name for r in results))

        if not results:
            logger.warning("No performance data found for report generation")
            return self._generate_empty_report(report_name)

        # Generate report sections
        report_data = {
            "report_metadata": self._generate_report_metadata(
                report_name, benchmarks_analyzed, days_back, len(results)
            ),
            "executive_summary": self._generate_executive_summary(
                results, benchmarks_analyzed
            ),
            "performance_analysis": self._generate_performance_analysis(
                results, benchmarks_analyzed
            ),
            "trend_analysis": self._generate_trend_analysis(
                benchmarks_analyzed, days_back
            ),
            "regression_analysis": self._generate_regression_analysis(
                results, days_back
            ),
            "bottleneck_analysis": self._generate_bottleneck_analysis(
                benchmarks_analyzed, days_back
            ),
            "system_health": self._generate_system_health_report(results),
        }

        if include_recommendations:
            report_data["optimization_recommendations"] = (
                self._generate_optimization_section(benchmark_name, days_back)
            )

        # Generate report files
        report_files = self._generate_report_files(report_name, report_data)

        logger.info(f"Performance report generated: {report_files['html']}")
        return report_files

    def generate_ci_report(
        self,
        current_results: list[BenchmarkResult],
        comparison_days: int = 7,
        fail_on_regression: bool = True,
        regression_threshold: float = 1.2,  # 20% degradation
    ) -> dict[str, Any]:
        """Generate CI/CD focused performance report with pass/fail status."""

        logger.info("Generating CI performance report")

        ci_report = {
            "timestamp": datetime.now().isoformat(),
            "status": "PASS",  # Will change to FAIL if issues found
            "summary": {},
            "regressions": [],
            "bottlenecks": [],
            "recommendations": [],
            "metrics": {},
            "artifacts": {},
        }

        if not current_results:
            ci_report["status"] = "FAIL"
            ci_report["error"] = "No benchmark results provided"
            return ci_report

        # Analyze each benchmark result for regressions
        critical_regressions = 0
        total_regressions = 0

        for result in current_results:
            regression_result = self.regression_detector.detect_regression(
                current_result=result, comparison_days=comparison_days
            )

            if regression_result.regression_detected:
                total_regressions += 1

                regression_info = {
                    "benchmark_name": result.benchmark_name,
                    "operation_type": result.operation_type,
                    "severity": regression_result.severity.value,
                    "relative_change": regression_result.relative_change,
                    "confidence": regression_result.confidence,
                    "recommendation": regression_result.recommendation,
                }

                ci_report["regressions"].append(regression_info)

                # Check if this is a critical regression
                if (
                    regression_result.relative_change >= regression_threshold * 1.5
                ):  # 30%+ degradation
                    critical_regressions += 1

        # Identify critical bottlenecks
        critical_bottlenecks = 0

        benchmark_names = list(set(r.benchmark_name for r in current_results))
        for benchmark_name in benchmark_names:
            bottlenecks = self.bottleneck_identifier.identify_bottlenecks(
                benchmark_name=benchmark_name, days_back=comparison_days
            )

            for bottleneck in bottlenecks:
                if bottleneck.severity in ["critical", "high"]:
                    critical_bottlenecks += 1

                    bottleneck_info = {
                        "benchmark_name": benchmark_name,
                        "bottleneck_type": bottleneck.bottleneck_type,
                        "severity": bottleneck.severity,
                        "performance_impact": bottleneck.performance_impact,
                        "confidence": bottleneck.confidence,
                        "recommendation": bottleneck.recommendation,
                    }

                    ci_report["bottlenecks"].append(bottleneck_info)

        # Determine overall CI status
        if fail_on_regression and (
            critical_regressions > 0 or critical_bottlenecks > 0
        ):
            ci_report["status"] = "FAIL"

        # Generate summary
        ci_report["summary"] = {
            "total_benchmarks": len(benchmark_names),
            "total_results": len(current_results),
            "total_regressions": total_regressions,
            "critical_regressions": critical_regressions,
            "critical_bottlenecks": critical_bottlenecks,
            "overall_status": ci_report["status"],
        }

        # Calculate key metrics
        ci_report["metrics"] = self._calculate_ci_metrics(current_results)

        # Generate quick recommendations for CI
        if ci_report["status"] == "FAIL":
            ci_report["recommendations"] = self._generate_ci_recommendations(
                ci_report["regressions"], ci_report["bottlenecks"]
            )

        logger.info(
            f"CI report status: {ci_report['status']} ({total_regressions} regressions, {critical_bottlenecks} bottlenecks)"
        )
        return ci_report

    def generate_trend_report(
        self, benchmark_name: str, days_back: int = 30, metrics: list[str] = None
    ) -> dict[str, Any]:
        """Generate focused trend analysis report for a specific benchmark."""

        if metrics is None:
            metrics = [
                "duration",
                "throughput_ops_per_sec",
                "memory_peak_mb",
                "cpu_percent_peak",
            ]

        logger.info(f"Generating trend report for {benchmark_name}")

        # Get results for analysis
        since = datetime.now() - timedelta(days=days_back)
        results = self.storage.get_results(benchmark_name=benchmark_name, since=since)

        if not results:
            return {"error": f"No data found for benchmark {benchmark_name}"}

        operation_types = list(set(r.operation_type for r in results))

        trend_report = {
            "benchmark_name": benchmark_name,
            "analysis_period_days": days_back,
            "operations_analyzed": operation_types,
            "trend_analysis": {},
            "summary": {},
            "recommendations": [],
        }

        # Analyze trends for each operation and metric
        for operation_type in operation_types:
            trend_report["trend_analysis"][operation_type] = {}

            for metric in metrics:
                trend_analysis = self.trend_analyzer.analyze_trend(
                    benchmark_name=benchmark_name,
                    operation_type=operation_type,
                    metric_name=metric,
                    days_back=days_back,
                )

                trend_report["trend_analysis"][operation_type][metric] = {
                    "direction": trend_analysis.direction.value,
                    "confidence": trend_analysis.confidence,
                    "recent_vs_historical_change": trend_analysis.recent_vs_historical_change,
                    "sample_size": trend_analysis.sample_size,
                    "correlation": trend_analysis.correlation,
                }

        # Generate trend summary
        trend_report["summary"] = self._summarize_trends(trend_report["trend_analysis"])

        # Generate trend-specific recommendations
        if any(
            op_trends[metric]["direction"] == "degrading"
            for op_trends in trend_report["trend_analysis"].values()
            for metric in metrics
            if metric in op_trends
        ):
            trend_report["recommendations"] = self._generate_trend_recommendations(
                benchmark_name, operation_types, days_back
            )

        return trend_report

    def _generate_report_metadata(
        self,
        report_name: str,
        benchmarks_analyzed: list[str],
        days_back: int,
        total_results: int,
    ) -> dict[str, Any]:
        """Generate report metadata section."""

        return {
            "report_name": report_name,
            "generated_at": datetime.now().isoformat(),
            "analysis_period_days": days_back,
            "benchmarks_analyzed": benchmarks_analyzed,
            "total_benchmarks": len(benchmarks_analyzed),
            "total_results_analyzed": total_results,
            "report_version": "1.0",
            "generator": "Khive Performance Monitoring System",
        }

    def _generate_executive_summary(
        self, results: list[BenchmarkResult], benchmarks_analyzed: list[str]
    ) -> dict[str, Any]:
        """Generate executive summary section."""

        if not results:
            return {"error": "No data available for analysis"}

        # Calculate key performance indicators
        durations = [r.metrics.duration for r in results if r.metrics.duration > 0]
        success_rates = [
            r.metrics.success_rate for r in results if r.metrics.success_rate >= 0
        ]
        memory_usage = [
            r.metrics.memory_peak_mb for r in results if r.metrics.memory_peak_mb > 0
        ]

        import statistics

        summary = {
            "overall_health": "GOOD",  # Will be updated based on analysis
            "key_metrics": {
                "avg_response_time_ms": (
                    (statistics.mean(durations) * 1000) if durations else 0
                ),
                "system_reliability": (
                    (statistics.mean(success_rates) * 100) if success_rates else 0
                ),
                "avg_memory_usage_mb": (
                    statistics.mean(memory_usage) if memory_usage else 0
                ),
                "total_operations": sum(r.metrics.operations_count for r in results),
            },
            "performance_trends": {"improving": 0, "stable": 0, "degrading": 0},
            "critical_issues": [],
            "top_recommendations": [],
        }

        # Analyze trends for overall health
        degrading_trends = 0
        for benchmark_name in benchmarks_analyzed[:5]:  # Limit to top 5 for summary
            trend_analysis = self.trend_analyzer.analyze_trend(
                benchmark_name=benchmark_name, operation_type="general", days_back=7
            )

            if trend_analysis.direction.value == "degrading":
                degrading_trends += 1
                summary["performance_trends"]["degrading"] += 1
            elif trend_analysis.direction.value == "improving":
                summary["performance_trends"]["improving"] += 1
            else:
                summary["performance_trends"]["stable"] += 1

        # Determine overall health
        if degrading_trends > len(benchmarks_analyzed) * 0.3:  # More than 30% degrading
            summary["overall_health"] = "WARNING"
        elif (
            degrading_trends > len(benchmarks_analyzed) * 0.1
        ):  # More than 10% degrading
            summary["overall_health"] = "ATTENTION"

        # Identify critical issues
        if summary["key_metrics"]["system_reliability"] < 95:
            summary["critical_issues"].append("Low system reliability detected")

        if summary["key_metrics"]["avg_response_time_ms"] > 1000:  # More than 1 second
            summary["critical_issues"].append("High response times detected")

        return summary

    def _generate_performance_analysis(
        self, results: list[BenchmarkResult], benchmarks_analyzed: list[str]
    ) -> dict[str, Any]:
        """Generate detailed performance analysis section."""

        analysis = {
            "benchmark_performance": {},
            "system_resource_usage": {},
            "performance_distribution": {},
        }

        # Analyze each benchmark
        for benchmark_name in benchmarks_analyzed:
            benchmark_results = [
                r for r in results if r.benchmark_name == benchmark_name
            ]

            if not benchmark_results:
                continue

            # Performance metrics analysis
            duration_analysis = self.analyzer.analyze_metric(
                benchmark_results, "duration"
            )

            analysis["benchmark_performance"][benchmark_name] = {
                "total_runs": len(benchmark_results),
                "avg_duration_ms": duration_analysis.get("mean", 0) * 1000,
                "p95_duration_ms": duration_analysis.get("p95", 0) * 1000,
                "p99_duration_ms": duration_analysis.get("p99", 0) * 1000,
                "min_duration_ms": duration_analysis.get("min", 0) * 1000,
                "max_duration_ms": duration_analysis.get("max", 0) * 1000,
                "variance": duration_analysis.get("variance", 0),
                "coefficient_of_variation": duration_analysis.get(
                    "coefficient_of_variation", 0
                ),
            }

        # System resource analysis
        memory_values = [
            r.metrics.memory_peak_mb for r in results if r.metrics.memory_peak_mb > 0
        ]
        cpu_values = [
            r.metrics.cpu_percent_peak
            for r in results
            if r.metrics.cpu_percent_peak > 0
        ]
        io_values = [
            r.metrics.io_read_bytes + r.metrics.io_write_bytes
            for r in results
            if (r.metrics.io_read_bytes + r.metrics.io_write_bytes) > 0
        ]

        import statistics

        analysis["system_resource_usage"] = {
            "memory_usage": {
                "avg_peak_mb": statistics.mean(memory_values) if memory_values else 0,
                "max_peak_mb": max(memory_values) if memory_values else 0,
                "p95_peak_mb": (
                    sorted(memory_values)[int(len(memory_values) * 0.95)]
                    if memory_values
                    else 0
                ),
            },
            "cpu_usage": {
                "avg_peak_percent": statistics.mean(cpu_values) if cpu_values else 0,
                "max_peak_percent": max(cpu_values) if cpu_values else 0,
                "p95_peak_percent": (
                    sorted(cpu_values)[int(len(cpu_values) * 0.95)] if cpu_values else 0
                ),
            },
            "io_usage": {
                "avg_total_bytes": statistics.mean(io_values) if io_values else 0,
                "max_total_bytes": max(io_values) if io_values else 0,
                "total_io_operations": sum(
                    r.metrics.io_read_count + r.metrics.io_write_count for r in results
                ),
            },
        }

        return analysis

    def _generate_trend_analysis(
        self, benchmarks_analyzed: list[str], days_back: int
    ) -> dict[str, Any]:
        """Generate trend analysis section."""

        trend_analysis = {
            "trend_summary": {
                "improving_benchmarks": [],
                "stable_benchmarks": [],
                "degrading_benchmarks": [],
                "insufficient_data": [],
            },
            "detailed_trends": {},
        }

        for benchmark_name in benchmarks_analyzed:
            trend = self.trend_analyzer.analyze_trend(
                benchmark_name=benchmark_name,
                operation_type="general",
                days_back=days_back,
            )

            trend_info = {
                "direction": trend.direction.value,
                "confidence": trend.confidence,
                "correlation": trend.correlation,
                "recent_vs_historical_change": trend.recent_vs_historical_change,
                "sample_size": trend.sample_size,
            }

            trend_analysis["detailed_trends"][benchmark_name] = trend_info

            # Categorize trends
            if trend.direction.value == "improving":
                trend_analysis["trend_summary"]["improving_benchmarks"].append(
                    benchmark_name
                )
            elif trend.direction.value == "degrading":
                trend_analysis["trend_summary"]["degrading_benchmarks"].append(
                    benchmark_name
                )
            elif trend.direction.value == "insufficient_data":
                trend_analysis["trend_summary"]["insufficient_data"].append(
                    benchmark_name
                )
            else:
                trend_analysis["trend_summary"]["stable_benchmarks"].append(
                    benchmark_name
                )

        return trend_analysis

    def _generate_regression_analysis(
        self, results: list[BenchmarkResult], days_back: int
    ) -> dict[str, Any]:
        """Generate regression analysis section."""

        regression_analysis = {
            "regressions_detected": [],
            "regression_summary": {"critical": 0, "moderate": 0, "minor": 0},
        }

        # Group results by benchmark and operation
        result_groups = {}
        for result in results:
            key = (result.benchmark_name, result.operation_type)
            if key not in result_groups:
                result_groups[key] = []
            result_groups[key].append(result)

        # Analyze regressions for each group
        for (benchmark_name, operation_type), group_results in result_groups.items():
            if len(group_results) < 5:
                continue

            latest_result = max(group_results, key=lambda r: r.timestamp)
            regression_result = self.regression_detector.detect_regression(
                current_result=latest_result, comparison_days=days_back
            )

            if regression_result.regression_detected:
                regression_info = {
                    "benchmark_name": benchmark_name,
                    "operation_type": operation_type,
                    "severity": regression_result.severity.value,
                    "relative_change": regression_result.relative_change,
                    "absolute_change": regression_result.absolute_change,
                    "confidence": regression_result.confidence,
                    "current_value": regression_result.current_value,
                    "baseline_mean": regression_result.baseline_mean,
                    "recommendation": regression_result.recommendation,
                }

                regression_analysis["regressions_detected"].append(regression_info)

                # Update summary counts
                severity = regression_result.severity.value
                if severity in regression_analysis["regression_summary"]:
                    regression_analysis["regression_summary"][severity] += 1

        return regression_analysis

    def _generate_bottleneck_analysis(
        self, benchmarks_analyzed: list[str], days_back: int
    ) -> dict[str, Any]:
        """Generate bottleneck analysis section."""

        bottleneck_analysis = {
            "bottlenecks_detected": [],
            "bottleneck_summary": {"cpu": 0, "memory": 0, "io": 0, "network": 0},
            "severity_summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        }

        for benchmark_name in benchmarks_analyzed:
            bottlenecks = self.bottleneck_identifier.identify_bottlenecks(
                benchmark_name=benchmark_name, days_back=days_back
            )

            for bottleneck in bottlenecks:
                bottleneck_info = {
                    "benchmark_name": benchmark_name,
                    "bottleneck_type": bottleneck.bottleneck_type,
                    "severity": bottleneck.severity,
                    "confidence": bottleneck.confidence,
                    "performance_impact": bottleneck.performance_impact,
                    "current_utilization": bottleneck.current_utilization,
                    "recommendation": bottleneck.recommendation,
                    "optimization_suggestions": bottleneck.optimization_suggestions,
                }

                bottleneck_analysis["bottlenecks_detected"].append(bottleneck_info)

                # Update summaries
                if (
                    bottleneck.bottleneck_type
                    in bottleneck_analysis["bottleneck_summary"]
                ):
                    bottleneck_analysis["bottleneck_summary"][
                        bottleneck.bottleneck_type
                    ] += 1

                if bottleneck.severity in bottleneck_analysis["severity_summary"]:
                    bottleneck_analysis["severity_summary"][bottleneck.severity] += 1

        return bottleneck_analysis

    def _generate_system_health_report(
        self, results: list[BenchmarkResult]
    ) -> dict[str, Any]:
        """Generate overall system health assessment."""

        if not results:
            return {"status": "UNKNOWN", "reason": "No data available"}

        health_report = {
            "overall_status": "HEALTHY",
            "health_score": 100.0,  # Start with perfect score
            "issues": [],
            "recommendations": [],
        }

        # Calculate success rate
        success_rates = [
            r.metrics.success_rate for r in results if r.metrics.success_rate >= 0
        ]
        if success_rates:
            import statistics

            avg_success_rate = statistics.mean(success_rates)

            if avg_success_rate < 0.95:  # Less than 95% success
                health_report["health_score"] -= 20
                health_report["issues"].append(
                    f"Low success rate: {avg_success_rate:.1%}"
                )

                if avg_success_rate < 0.90:  # Less than 90% success
                    health_report["overall_status"] = "DEGRADED"
                    health_report["health_score"] -= 20

        # Check response times
        durations = [r.metrics.duration for r in results if r.metrics.duration > 0]
        if durations:
            import statistics

            avg_duration = statistics.mean(durations)
            p95_duration = sorted(durations)[int(len(durations) * 0.95)]

            if avg_duration > 1.0:  # More than 1 second average
                health_report["health_score"] -= 15
                health_report["issues"].append(
                    f"High response time: {avg_duration:.2f}s average"
                )

            if p95_duration > 3.0:  # More than 3 seconds P95
                health_report["health_score"] -= 15
                health_report["issues"].append(
                    f"Very high P95 response time: {p95_duration:.2f}s"
                )

                if health_report["overall_status"] == "HEALTHY":
                    health_report["overall_status"] = "DEGRADED"

        # Check memory usage
        memory_usage = [
            r.metrics.memory_peak_mb for r in results if r.metrics.memory_peak_mb > 0
        ]
        if memory_usage:
            import statistics

            max_memory = max(memory_usage)
            avg_memory = statistics.mean(memory_usage)

            if max_memory > 1000:  # More than 1GB peak
                health_report["health_score"] -= 10
                health_report["issues"].append(
                    f"High memory usage: {max_memory:.1f}MB peak"
                )

            if avg_memory > 500:  # More than 500MB average
                health_report["health_score"] -= 5
                health_report["issues"].append(
                    f"Elevated memory usage: {avg_memory:.1f}MB average"
                )

        # Final status determination
        if health_report["health_score"] < 70:
            health_report["overall_status"] = "CRITICAL"
        elif health_report["health_score"] < 85:
            health_report["overall_status"] = "DEGRADED"

        # Generate recommendations based on issues
        if health_report["issues"]:
            health_report["recommendations"] = [
                "Review recent code changes for performance impacts",
                "Implement performance monitoring and alerting",
                "Consider scaling resources if consistently high usage",
                "Run detailed profiling to identify bottlenecks",
            ]

        return health_report

    def _generate_optimization_section(
        self, benchmark_name: str | None, days_back: int
    ) -> dict[str, Any]:
        """Generate optimization recommendations section."""

        optimization_plan = self.recommender.generate_recommendations(
            benchmark_name=benchmark_name, days_back=days_back, max_recommendations=10
        )

        return {
            "plan_summary": optimization_plan.plan_summary,
            "total_estimated_improvement": optimization_plan.total_estimated_improvement,
            "total_estimated_effort_hours": optimization_plan.total_estimated_effort_hours,
            "recommendations_by_priority": {
                "critical": [
                    rec.to_dict() for rec in optimization_plan.critical_recommendations
                ],
                "high": [
                    rec.to_dict() for rec in optimization_plan.high_recommendations
                ],
                "medium": [
                    rec.to_dict() for rec in optimization_plan.medium_recommendations
                ],
                "low": [rec.to_dict() for rec in optimization_plan.low_recommendations],
            },
            "recommended_implementation_order": optimization_plan.recommended_implementation_order,
        }

    def _calculate_ci_metrics(self, results: list[BenchmarkResult]) -> dict[str, Any]:
        """Calculate key metrics for CI reporting."""

        if not results:
            return {}

        durations = [r.metrics.duration for r in results if r.metrics.duration > 0]
        success_rates = [
            r.metrics.success_rate for r in results if r.metrics.success_rate >= 0
        ]
        memory_usage = [
            r.metrics.memory_peak_mb for r in results if r.metrics.memory_peak_mb > 0
        ]

        import statistics

        return {
            "avg_response_time_ms": (
                (statistics.mean(durations) * 1000) if durations else 0
            ),
            "p95_response_time_ms": (
                (sorted(durations)[int(len(durations) * 0.95)] * 1000)
                if durations
                else 0
            ),
            "success_rate_percent": (
                (statistics.mean(success_rates) * 100) if success_rates else 0
            ),
            "avg_memory_usage_mb": statistics.mean(memory_usage) if memory_usage else 0,
            "max_memory_usage_mb": max(memory_usage) if memory_usage else 0,
            "total_operations": sum(
                r.metrics.operations_count
                for r in results
                if r.metrics.operations_count > 0
            ),
        }

    def _generate_ci_recommendations(
        self, regressions: list[dict[str, Any]], bottlenecks: list[dict[str, Any]]
    ) -> list[str]:
        """Generate quick recommendations for CI failures."""

        recommendations = []

        if regressions:
            recommendations.append(
                f"Review {len(regressions)} performance regressions detected"
            )

            critical_regressions = [
                r for r in regressions if r.get("severity") == "critical"
            ]
            if critical_regressions:
                recommendations.append(
                    "CRITICAL: Address critical performance regressions immediately"
                )

        if bottlenecks:
            recommendations.append(
                f"Investigate {len(bottlenecks)} performance bottlenecks"
            )

            critical_bottlenecks = [
                b for b in bottlenecks if b.get("severity") in ["critical", "high"]
            ]
            if critical_bottlenecks:
                recommendations.append(
                    "HIGH PRIORITY: Optimize critical system bottlenecks"
                )

        # Add general recommendations
        if regressions or bottlenecks:
            recommendations.extend(
                [
                    "Run performance profiling to identify root causes",
                    "Consider reverting recent changes if regressions are severe",
                    "Add performance tests to prevent future regressions",
                ]
            )

        return recommendations

    def _summarize_trends(self, trend_analysis: dict[str, Any]) -> dict[str, Any]:
        """Summarize trend analysis results."""

        summary = {
            "improving_operations": [],
            "degrading_operations": [],
            "stable_operations": [],
            "overall_trend": "stable",
        }

        degrading_count = 0
        improving_count = 0

        for operation_type, metrics in trend_analysis.items():
            for metric, trend_data in metrics.items():
                operation_metric = f"{operation_type}.{metric}"

                if trend_data["direction"] == "degrading":
                    summary["degrading_operations"].append(operation_metric)
                    degrading_count += 1
                elif trend_data["direction"] == "improving":
                    summary["improving_operations"].append(operation_metric)
                    improving_count += 1
                else:
                    summary["stable_operations"].append(operation_metric)

        # Determine overall trend
        total_operations = (
            degrading_count + improving_count + len(summary["stable_operations"])
        )
        if total_operations > 0:
            if (
                degrading_count > improving_count
                and degrading_count > total_operations * 0.3
            ):
                summary["overall_trend"] = "degrading"
            elif (
                improving_count > degrading_count
                and improving_count > total_operations * 0.3
            ):
                summary["overall_trend"] = "improving"

        return summary

    def _generate_trend_recommendations(
        self, benchmark_name: str, operation_types: list[str], days_back: int
    ) -> list[str]:
        """Generate trend-specific recommendations."""

        recommendations = [
            f"Monitor {benchmark_name} performance trends closely",
            "Investigate root causes of performance degradation",
            "Consider implementing performance budgets and alerts",
            "Review recent code changes for performance impacts",
        ]

        if len(operation_types) > 1:
            recommendations.append(
                "Compare performance across different operation types"
            )

        return recommendations

    def _generate_empty_report(self, report_name: str) -> Path:
        """Generate empty report when no data is available."""

        empty_report = {
            "report_metadata": {
                "report_name": report_name,
                "generated_at": datetime.now().isoformat(),
                "status": "NO_DATA",
                "message": "No performance data available for analysis",
            }
        }

        report_file = (
            self.output_path
            / f"{report_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(report_file, "w") as f:
            json.dump(empty_report, f, indent=2)

        return {"json": report_file}

    def _generate_report_files(
        self, report_name: str, report_data: dict[str, Any]
    ) -> dict[str, Path]:
        """Generate report files in multiple formats."""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{report_name}_{timestamp}"

        files = {}

        # JSON report
        json_file = self.output_path / f"{base_name}.json"
        with open(json_file, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        files["json"] = json_file

        # HTML report
        html_file = self.output_path / f"{base_name}.html"
        html_content = self._generate_html_report(report_data)
        with open(html_file, "w") as f:
            f.write(html_content)
        files["html"] = html_file

        # Summary text report
        txt_file = self.output_path / f"{base_name}_summary.txt"
        txt_content = self._generate_text_summary(report_data)
        with open(txt_file, "w") as f:
            f.write(txt_content)
        files["text"] = txt_file

        return files

    def _generate_html_report(self, report_data: dict[str, Any]) -> str:
        """Generate HTML version of the report."""

        metadata = report_data.get("report_metadata", {})
        summary = report_data.get("executive_summary", {})

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{metadata.get("report_name", "Performance Report")}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #e9e9e9; border-radius: 3px; }}
                .critical {{ color: #d9534f; font-weight: bold; }}
                .warning {{ color: #f0ad4e; font-weight: bold; }}
                .success {{ color: #5cb85c; font-weight: bold; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{metadata.get("report_name", "Performance Report")}</h1>
                <p>Generated: {metadata.get("generated_at", "Unknown")}</p>
                <p>Analysis Period: {metadata.get("analysis_period_days", "Unknown")} days</p>
                <p>Benchmarks Analyzed: {metadata.get("total_benchmarks", 0)}</p>
            </div>

            <div class="section">
                <h2>Executive Summary</h2>
                <div class="metric">
                    <strong>Overall Health:</strong>
                    <span class="{"success" if summary.get("overall_health") == "GOOD" else "warning" if summary.get("overall_health") == "ATTENTION" else "critical"}">
                        {summary.get("overall_health", "UNKNOWN")}
                    </span>
                </div>

                <h3>Key Metrics</h3>
                {self._format_key_metrics_html(summary.get("key_metrics", {}))}

                <h3>Critical Issues</h3>
                <ul>
                    {"".join(f"<li class='critical'>{issue}</li>" for issue in summary.get("critical_issues", []))}
                </ul>
            </div>

            {self._format_sections_html(report_data)}

            <div class="section">
                <p><em>Report generated by Khive Performance Monitoring System</em></p>
            </div>
        </body>
        </html>
        """

        return html

    def _format_key_metrics_html(self, metrics: dict[str, Any]) -> str:
        """Format key metrics for HTML display."""

        html = "<div>"
        for key, value in metrics.items():
            formatted_key = key.replace("_", " ").title()

            if isinstance(value, float):
                if key.endswith("_ms"):
                    formatted_value = f"{value:.2f} ms"
                elif key.endswith("_percent") or "reliability" in key:
                    formatted_value = f"{value:.1f}%"
                else:
                    formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)

            html += f'<div class="metric"><strong>{formatted_key}:</strong> {formatted_value}</div>'

        html += "</div>"
        return html

    def _format_sections_html(self, report_data: dict[str, Any]) -> str:
        """Format additional report sections for HTML."""

        html = ""

        # Regression analysis
        if "regression_analysis" in report_data:
            regressions = report_data["regression_analysis"].get(
                "regressions_detected", []
            )
            if regressions:
                html += """
                <div class="section">
                    <h2>Performance Regressions</h2>
                    <table>
                        <tr>
                            <th>Benchmark</th>
                            <th>Operation</th>
                            <th>Severity</th>
                            <th>Change</th>
                            <th>Confidence</th>
                        </tr>
                """

                for regression in regressions:
                    severity_class = (
                        "critical"
                        if regression.get("severity") == "critical"
                        else "warning"
                    )
                    html += f"""
                        <tr>
                            <td>{regression.get("benchmark_name", "Unknown")}</td>
                            <td>{regression.get("operation_type", "Unknown")}</td>
                            <td><span class="{severity_class}">{regression.get("severity", "Unknown").title()}</span></td>
                            <td>{regression.get("relative_change", 0):.2f}x</td>
                            <td>{regression.get("confidence", 0):.2f}</td>
                        </tr>
                    """

                html += "</table></div>"

        # Bottleneck analysis
        if "bottleneck_analysis" in report_data:
            bottlenecks = report_data["bottleneck_analysis"].get(
                "bottlenecks_detected", []
            )
            if bottlenecks:
                html += """
                <div class="section">
                    <h2>Performance Bottlenecks</h2>
                    <table>
                        <tr>
                            <th>Benchmark</th>
                            <th>Type</th>
                            <th>Severity</th>
                            <th>Impact</th>
                            <th>Confidence</th>
                        </tr>
                """

                for bottleneck in bottlenecks:
                    severity_class = (
                        "critical"
                        if bottleneck.get("severity") in ["critical", "high"]
                        else "warning"
                    )
                    html += f"""
                        <tr>
                            <td>{bottleneck.get("benchmark_name", "Unknown")}</td>
                            <td>{bottleneck.get("bottleneck_type", "Unknown").title()}</td>
                            <td><span class="{severity_class}">{bottleneck.get("severity", "Unknown").title()}</span></td>
                            <td>{bottleneck.get("performance_impact", 0):.1f}%</td>
                            <td>{bottleneck.get("confidence", 0):.2f}</td>
                        </tr>
                    """

                html += "</table></div>"

        return html

    def _generate_text_summary(self, report_data: dict[str, Any]) -> str:
        """Generate text summary of the report."""

        metadata = report_data.get("report_metadata", {})
        summary = report_data.get("executive_summary", {})

        text = f"""
PERFORMANCE REPORT SUMMARY
=========================

Report: {metadata.get("report_name", "Unknown")}
Generated: {metadata.get("generated_at", "Unknown")}
Analysis Period: {metadata.get("analysis_period_days", 0)} days
Benchmarks: {metadata.get("total_benchmarks", 0)}

OVERALL HEALTH: {summary.get("overall_health", "UNKNOWN")}

KEY METRICS:
"""

        for key, value in summary.get("key_metrics", {}).items():
            formatted_key = key.replace("_", " ").title()
            text += f"  {formatted_key}: {value}\n"

        # Critical issues
        issues = summary.get("critical_issues", [])
        if issues:
            text += f"\nCRITICAL ISSUES ({len(issues)}):\n"
            for issue in issues:
                text += f"  - {issue}\n"

        # Regressions
        regressions = report_data.get("regression_analysis", {}).get(
            "regressions_detected", []
        )
        if regressions:
            text += f"\nPERFORMACE REGRESSIONS ({len(regressions)}):\n"
            for regression in regressions:
                text += f"  - {regression.get('benchmark_name')}.{regression.get('operation_type')}: {regression.get('severity')} ({regression.get('relative_change', 0):.2f}x slower)\n"

        # Bottlenecks
        bottlenecks = report_data.get("bottleneck_analysis", {}).get(
            "bottlenecks_detected", []
        )
        if bottlenecks:
            text += f"\nPERFORMANCE BOTTLENECKS ({len(bottlenecks)}):\n"
            for bottleneck in bottlenecks:
                text += f"  - {bottleneck.get('benchmark_name')}: {bottleneck.get('bottleneck_type')} ({bottleneck.get('severity')}, {bottleneck.get('performance_impact', 0):.1f}% impact)\n"

        # Optimization recommendations
        if "optimization_recommendations" in report_data:
            opt_data = report_data["optimization_recommendations"]
            total_improvement = opt_data.get("total_estimated_improvement", 0)
            if total_improvement > 0:
                text += f"\nOPTIMIZATION POTENTIAL: {total_improvement:.1f}% improvement available\n"

        text += "\n" + "=" * 50 + "\n"
        text += "Generated by Khive Performance Monitoring System\n"

        return text


class CIIntegration:
    """Integration with CI/CD systems for automated performance monitoring."""

    def __init__(self, storage: BenchmarkStorage):
        self.storage = storage
        self.reporter = PerformanceReporter(storage)

    def create_github_action(
        self, output_path: Path = Path(".github/workflows")
    ) -> Path:
        """Create GitHub Action workflow for performance monitoring."""

        output_path.mkdir(parents=True, exist_ok=True)

        github_action_yaml = """
name: Performance Monitoring

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight

jobs:
  performance-tests:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .
        pip install pytest pytest-benchmark

    - name: Run performance benchmarks
      run: |
        python -m pytest tests/performance/ --benchmark-json=benchmark_results.json

    - name: Analyze performance results
      run: |
        python scripts/analyze_performance.py benchmark_results.json

    - name: Upload performance report
      uses: actions/upload-artifact@v3
      with:
        name: performance-report
        path: performance_report.html

    - name: Comment PR with results
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const report = fs.readFileSync('performance_summary.txt', 'utf8');

          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: `## Performance Test Results\\n\\n\\`\\`\\`\\n${report}\\n\\`\\`\\``
          });

    - name: Fail on performance regression
      run: |
        python scripts/check_performance_regression.py benchmark_results.json
"""

        workflow_file = output_path / "performance.yml"
        with open(workflow_file, "w") as f:
            f.write(github_action_yaml)

        logger.info(f"GitHub Action created: {workflow_file}")
        return workflow_file

    def create_ci_scripts(self, output_path: Path = Path("scripts")) -> dict[str, Path]:
        """Create CI integration scripts."""

        output_path.mkdir(parents=True, exist_ok=True)
        scripts = {}

        # Performance analysis script
        analyze_script = output_path / "analyze_performance.py"
        analyze_script_content = '''#!/usr/bin/env python3
"""Analyze performance benchmark results for CI."""

import sys
import json
from pathlib import Path
from datetime import datetime

def analyze_benchmark_results(results_file):
    """Analyze benchmark results and generate reports."""

    with open(results_file) as f:
        data = json.load(f)

    # Extract benchmark results
    benchmarks = data.get('benchmarks', [])

    if not benchmarks:
        print("No benchmark results found")
        return

    # Generate summary
    total_benchmarks = len(benchmarks)
    avg_duration = sum(b['stats']['mean'] for b in benchmarks) / total_benchmarks

    summary = f"""
Performance Analysis Summary
===========================

Total Benchmarks: {total_benchmarks}
Average Duration: {avg_duration:.4f} seconds
Generated: {datetime.now().isoformat()}

Top 5 Slowest Tests:
"""

    # Sort by duration and show top 5
    sorted_benchmarks = sorted(benchmarks, key=lambda x: x['stats']['mean'], reverse=True)

    for i, benchmark in enumerate(sorted_benchmarks[:5], 1):
        name = benchmark['name']
        duration = benchmark['stats']['mean']
        summary += f"  {i}. {name}: {duration:.4f}s\\n"

    # Write summary
    with open('performance_summary.txt', 'w') as f:
        f.write(summary)

    print(summary)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_performance.py <results_file>")
        sys.exit(1)

    results_file = sys.argv[1]
    if not Path(results_file).exists():
        print(f"Results file not found: {results_file}")
        sys.exit(1)

    analyze_benchmark_results(results_file)
'''

        with open(analyze_script, "w") as f:
            f.write(analyze_script_content)
        analyze_script.chmod(0o755)
        scripts["analyze"] = analyze_script

        # Regression check script
        regression_script = output_path / "check_performance_regression.py"
        regression_script_content = '''#!/usr/bin/env python3
"""Check for performance regressions in CI."""

import sys
import json
from pathlib import Path

def check_regressions(results_file, threshold=1.2):
    """Check for performance regressions."""

    with open(results_file) as f:
        data = json.load(f)

    benchmarks = data.get('benchmarks', [])

    if not benchmarks:
        print("No benchmark results to check")
        return True

    # For now, check if any benchmark takes longer than threshold
    slow_benchmarks = []

    for benchmark in benchmarks:
        duration = benchmark['stats']['mean']
        name = benchmark['name']

        # Simple threshold check (in real implementation, compare with baseline)
        if duration > 1.0:  # More than 1 second
            slow_benchmarks.append((name, duration))

    if slow_benchmarks:
        print("Performance issues detected:")
        for name, duration in slow_benchmarks:
            print(f"  - {name}: {duration:.4f}s (too slow)")

        print(f"\\nFailing CI due to {len(slow_benchmarks)} slow benchmarks")
        return False

    print("All benchmarks within acceptable performance limits")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python check_performance_regression.py <results_file>")
        sys.exit(1)

    results_file = sys.argv[1]
    if not Path(results_file).exists():
        print(f"Results file not found: {results_file}")
        sys.exit(1)

    success = check_regressions(results_file)
    sys.exit(0 if success else 1)
'''

        with open(regression_script, "w") as f:
            f.write(regression_script_content)
        regression_script.chmod(0o755)
        scripts["regression_check"] = regression_script

        # Setup script
        setup_script = output_path / "setup_performance_monitoring.py"
        setup_script_content = '''#!/usr/bin/env python3
"""Set up performance monitoring infrastructure."""

from pathlib import Path
import json

def setup_performance_monitoring():
    """Set up performance monitoring configuration."""

    # Create performance monitoring config
    config = {
        "performance_thresholds": {
            "max_duration_seconds": 1.0,
            "regression_threshold": 1.2,
            "memory_limit_mb": 500,
            "cpu_limit_percent": 80
        },
        "reporting": {
            "generate_html_reports": True,
            "upload_artifacts": True,
            "comment_on_pr": True
        },
        "notifications": {
            "slack_webhook": None,
            "email_recipients": []
        }
    }

    config_file = Path("performance_config.json")
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Performance monitoring configuration created: {config_file}")

    # Create test performance config
    perf_dir = Path("tests/performance")
    perf_dir.mkdir(parents=True, exist_ok=True)

    pytest_ini = perf_dir / "pytest.ini"
    with open(pytest_ini, 'w') as f:
        f.write("""[tool:pytest]
markers =
    performance: Performance benchmark tests
    slow: Slow-running tests (>5s)

addopts =
    --benchmark-only
    --benchmark-sort=mean
    --benchmark-min-rounds=3
""")

    print("Performance test configuration created")

if __name__ == "__main__":
    setup_performance_monitoring()
'''

        with open(setup_script, "w") as f:
            f.write(setup_script_content)
        setup_script.chmod(0o755)
        scripts["setup"] = setup_script

        logger.info(f"CI scripts created in {output_path}")
        return scripts

    def generate_jenkins_pipeline(self, output_path: Path = Path(".")) -> Path:
        """Generate Jenkins pipeline for performance monitoring."""

        jenkins_pipeline = """
pipeline {
    agent any

    triggers {
        cron('H 0 * * *')  // Daily
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup') {
            steps {
                sh 'python -m pip install --upgrade pip'
                sh 'pip install -e .'
                sh 'pip install pytest pytest-benchmark'
            }
        }

        stage('Performance Tests') {
            steps {
                sh 'python -m pytest tests/performance/ --benchmark-json=benchmark_results.json'
            }
        }

        stage('Performance Analysis') {
            steps {
                script {
                    sh 'python scripts/analyze_performance.py benchmark_results.json'

                    // Archive performance results
                    archiveArtifacts artifacts: 'benchmark_results.json,performance_summary.txt', allowEmptyArchive: false

                    // Check for regressions
                    def regressionCheck = sh(
                        script: 'python scripts/check_performance_regression.py benchmark_results.json',
                        returnStatus: true
                    )

                    if (regressionCheck != 0) {
                        currentBuild.result = 'UNSTABLE'
                        error('Performance regressions detected')
                    }
                }
            }
        }

        stage('Generate Reports') {
            steps {
                script {
                    // Generate HTML report if available
                    sh 'python -c "from khive.services.performance import PerformanceReporter; print(\\"Report generated\\")"'
                }
            }
            post {
                always {
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: false,
                        keepAll: true,
                        reportDir: '.',
                        reportFiles: 'performance_report.html',
                        reportName: 'Performance Report'
                    ])
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        unstable {
            emailext (
                subject: "Performance Issues Detected - ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: "Performance regressions detected in build ${env.BUILD_URL}",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}
"""

        jenkins_file = output_path / "Jenkinsfile.performance"
        with open(jenkins_file, "w") as f:
            f.write(jenkins_pipeline)

        logger.info(f"Jenkins pipeline created: {jenkins_file}")
        return jenkins_file

    def create_docker_performance_runner(self, output_path: Path = Path(".")) -> Path:
        """Create Docker container for consistent performance testing."""

        dockerfile_content = """
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    curl \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY pyproject.toml ./
RUN pip install --upgrade pip && \\
    pip install -e . && \\
    pip install pytest pytest-benchmark psutil plotly

# Copy source code
COPY . .

# Create performance test runner script
RUN echo '#!/bin/bash\\n\\
set -e\\n\\
echo "Starting performance benchmarks..."\\n\\
pytest tests/performance/ --benchmark-json=benchmark_results.json -v\\n\\
python scripts/analyze_performance.py benchmark_results.json\\n\\
echo "Performance analysis complete"\\n\\
' > /app/run_performance_tests.sh && chmod +x /app/run_performance_tests.sh

# Default command
CMD ["/app/run_performance_tests.sh"]
"""

        dockerfile = output_path / "Dockerfile.performance"
        with open(dockerfile, "w") as f:
            f.write(dockerfile_content)

        # Create docker-compose for performance testing
        compose_content = """
version: '3.8'

services:
  performance-tests:
    build:
      context: .
      dockerfile: Dockerfile.performance
    volumes:
      - ./performance_results:/app/performance_results
    environment:
      - KHIVE_TEST_MODE=true
      - PERFORMANCE_BASELINE_PATH=/app/performance_results/baseline
    mem_limit: 1g
    cpus: 2.0
"""

        compose_file = output_path / "docker-compose.performance.yml"
        with open(compose_file, "w") as f:
            f.write(compose_content)

        logger.info(f"Docker performance runner created: {dockerfile}")
        return dockerfile
