"""Comprehensive performance test runner with reporting and CI integration.

This module provides a unified interface for running performance tests with:
- Automated test suite execution
- Performance metrics collection and analysis
- Quality gates validation
- CI/CD integration support
- Performance regression detection
- Detailed reporting with statistical analysis
"""

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest


class PerformanceTestRunner:
    """Comprehensive performance test runner with reporting capabilities."""

    def __init__(self, output_dir: str = "tests/results/performance"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_results = {}
        self.performance_report = {}
        self.quality_gates = self._load_quality_gates()

    def _load_quality_gates(self) -> dict[str, Any]:
        """Load quality gates configuration."""
        return {
            "orchestration": {
                "max_init_time_ms": 100,
                "max_branch_creation_ms": 500,
                "min_throughput_ops_sec": 10,
                "max_memory_growth_mb": 50,
                "max_p95_response_time_ms": 1000,
            },
            "composition": {
                "max_agent_creation_ms": 200,
                "min_throughput_ops_sec": 5,
                "max_memory_per_agent_mb": 5,
                "max_scaling_degradation_ratio": 2.0,
            },
            "memory": {
                "max_leak_rate_mb_per_op": 0.1,
                "max_peak_memory_mb": 200,
                "max_memory_growth_trend_mb": 10,
                "min_cleanup_efficiency_pct": 80,
            },
            "scalability": {
                "min_scaling_efficiency": 0.5,
                "max_response_time_degradation": 3.0,
                "min_success_rate_under_load": 0.85,
                "max_resource_usage_per_op_mb": 2.0,
            },
        }

    def run_performance_test_suite(
        self,
        test_categories: list[str] | None = None,
        parallel: bool = False,
        verbose: bool = True,
        generate_report: bool = True,
    ) -> dict[str, Any]:
        """Run comprehensive performance test suite."""
        print("🚀 Starting Khive Performance Test Suite")
        print(f"📅 Timestamp: {datetime.now().isoformat()}")
        print(f"📂 Output directory: {self.output_dir}")

        # Define test categories and their corresponding files
        available_categories = {
            "benchmarks": "tests/performance/test_benchmarks.py",
            "memory": "tests/performance/test_memory_profiling.py",
            "scalability": "tests/performance/test_scalability.py",
            "orchestration": "tests/performance/test_orchestration_performance.py",
            "artifacts": "tests/performance/test_artifacts_performance.py",
            "cache": "tests/performance/test_cache_performance.py",
            "planning": "tests/performance/test_planning_performance.py",
            "session": "tests/performance/test_session_performance.py",
        }

        # Filter test categories
        if test_categories:
            categories_to_run = {
                k: v for k, v in available_categories.items() if k in test_categories
            }
        else:
            categories_to_run = available_categories

        print(f"🔍 Running test categories: {list(categories_to_run.keys())}")

        # Configure pytest arguments
        pytest_args = [
            "-v" if verbose else "-q",
            "--tb=short",
            "--durations=10",
            "--benchmark-only",
            "--benchmark-sort=mean",
            f"--benchmark-json={self.output_dir}/benchmark_results.json",
            "-m",
            "performance",
            "--maxfail=5",  # Stop after 5 failures
        ]

        if parallel:
            pytest_args.extend(["-n", "auto"])

        # Add test files
        for test_file in categories_to_run.values():
            if Path(test_file).exists():
                pytest_args.append(test_file)

        start_time = time.perf_counter()

        print(f"📋 Running pytest with args: {' '.join(pytest_args)}")

        # Run tests
        exit_code = pytest.main(pytest_args)

        end_time = time.perf_counter()
        total_runtime = end_time - start_time

        # Collect results
        test_results = {
            "exit_code": exit_code,
            "total_runtime_seconds": total_runtime,
            "timestamp": datetime.now().isoformat(),
            "categories_tested": list(categories_to_run.keys()),
            "pytest_args": pytest_args,
        }

        # Load benchmark results if available
        benchmark_file = self.output_dir / "benchmark_results.json"
        if benchmark_file.exists():
            with open(benchmark_file) as f:
                benchmark_data = json.load(f)
                test_results["benchmark_data"] = benchmark_data

        self.test_results = test_results

        print(f"✅ Test suite completed in {total_runtime:.2f} seconds")
        print(f"📊 Exit code: {exit_code}")

        if generate_report:
            self.generate_performance_report()

        return test_results

    def generate_performance_report(self) -> dict[str, Any]:
        """Generate comprehensive performance report."""
        print("📈 Generating performance report...")

        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "test_runtime": self.test_results.get("total_runtime_seconds", 0),
                "categories_tested": self.test_results.get("categories_tested", []),
            },
            "summary": {},
            "benchmark_analysis": {},
            "quality_gates": {},
            "recommendations": [],
        }

        # Analyze benchmark data if available
        if "benchmark_data" in self.test_results:
            benchmark_analysis = self._analyze_benchmark_data(
                self.test_results["benchmark_data"]
            )
            report["benchmark_analysis"] = benchmark_analysis
            report["summary"]["total_benchmarks"] = len(
                benchmark_analysis.get("benchmarks", [])
            )

        # Validate quality gates
        quality_gates_results = self._validate_quality_gates(
            report["benchmark_analysis"]
        )
        report["quality_gates"] = quality_gates_results

        # Generate recommendations
        recommendations = self._generate_recommendations(
            report["benchmark_analysis"], quality_gates_results
        )
        report["recommendations"] = recommendations

        # Calculate overall health score
        health_score = self._calculate_health_score(quality_gates_results)
        report["summary"]["health_score"] = health_score
        report["summary"]["status"] = (
            "PASS" if health_score >= 80 else "WARN" if health_score >= 60 else "FAIL"
        )

        self.performance_report = report

        # Save report
        report_file = (
            self.output_dir
            / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"📄 Performance report saved to: {report_file}")

        # Print summary
        self._print_report_summary(report)

        return report

    def _analyze_benchmark_data(self, benchmark_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze benchmark results and extract performance metrics."""
        benchmarks = benchmark_data.get("benchmarks", [])

        analysis = {
            "benchmarks": [],
            "categories": {},
            "statistics": {},
        }

        # Process individual benchmarks
        for benchmark in benchmarks:
            benchmark_info = {
                "name": benchmark.get("name", "unknown"),
                "group": benchmark.get("group", "default"),
                "mean_time_ms": benchmark.get("stats", {}).get("mean", 0) * 1000,
                "min_time_ms": benchmark.get("stats", {}).get("min", 0) * 1000,
                "max_time_ms": benchmark.get("stats", {}).get("max", 0) * 1000,
                "stddev_ms": benchmark.get("stats", {}).get("stddev", 0) * 1000,
                "ops_per_sec": 1.0 / benchmark.get("stats", {}).get("mean", 1.0),
                "rounds": benchmark.get("stats", {}).get("rounds", 0),
            }
            analysis["benchmarks"].append(benchmark_info)

            # Group by category
            group = benchmark_info["group"]
            if group not in analysis["categories"]:
                analysis["categories"][group] = []
            analysis["categories"][group].append(benchmark_info)

        # Calculate category statistics
        for category, category_benchmarks in analysis["categories"].items():
            mean_times = [b["mean_time_ms"] for b in category_benchmarks]
            ops_per_sec = [b["ops_per_sec"] for b in category_benchmarks]

            if mean_times:
                analysis["categories"][category] = {
                    "benchmarks": category_benchmarks,
                    "count": len(category_benchmarks),
                    "avg_mean_time_ms": statistics.mean(mean_times),
                    "min_time_ms": min(b["min_time_ms"] for b in category_benchmarks),
                    "max_time_ms": max(b["max_time_ms"] for b in category_benchmarks),
                    "total_ops_per_sec": sum(ops_per_sec),
                    "avg_ops_per_sec": statistics.mean(ops_per_sec),
                }

        # Overall statistics
        if benchmarks:
            all_mean_times = [b["mean_time_ms"] for b in analysis["benchmarks"]]
            all_ops_per_sec = [b["ops_per_sec"] for b in analysis["benchmarks"]]

            analysis["statistics"] = {
                "total_benchmarks": len(benchmarks),
                "avg_benchmark_time_ms": statistics.mean(all_mean_times),
                "fastest_benchmark_ms": min(all_mean_times),
                "slowest_benchmark_ms": max(all_mean_times),
                "total_throughput_ops_sec": sum(all_ops_per_sec),
                "avg_throughput_ops_sec": statistics.mean(all_ops_per_sec),
            }

        return analysis

    def _validate_quality_gates(
        self, benchmark_analysis: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate performance against quality gates."""
        results = {
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "details": {},
        }

        categories = benchmark_analysis.get("categories", {})

        for gate_category, thresholds in self.quality_gates.items():
            category_results = {
                "status": "PASS",
                "violations": [],
                "metrics": {},
            }

            # Find matching benchmark category
            benchmark_category = None
            for cat_name, cat_data in categories.items():
                if gate_category.lower() in cat_name.lower():
                    benchmark_category = cat_data
                    break

            if not benchmark_category:
                category_results["status"] = "SKIP"
                category_results["violations"].append(
                    f"No benchmarks found for {gate_category}"
                )
                results["details"][gate_category] = category_results
                continue

            # Validate thresholds
            if "max_init_time_ms" in thresholds:
                init_benchmarks = [
                    b
                    for b in benchmark_category["benchmarks"]
                    if "init" in b["name"].lower()
                ]
                if init_benchmarks:
                    max_init_time = max(b["mean_time_ms"] for b in init_benchmarks)
                    category_results["metrics"]["max_init_time_ms"] = max_init_time

                    if max_init_time > thresholds["max_init_time_ms"]:
                        violation = f"Initialization time {max_init_time:.1f}ms > {thresholds['max_init_time_ms']}ms"
                        category_results["violations"].append(violation)
                        category_results["status"] = "FAIL"

            if "min_throughput_ops_sec" in thresholds:
                avg_throughput = benchmark_category.get("avg_ops_per_sec", 0)
                category_results["metrics"]["avg_throughput_ops_sec"] = avg_throughput

                if avg_throughput < thresholds["min_throughput_ops_sec"]:
                    violation = f"Throughput {avg_throughput:.2f} ops/sec < {thresholds['min_throughput_ops_sec']} ops/sec"
                    category_results["violations"].append(violation)
                    category_results["status"] = "FAIL"

            if "max_p95_response_time_ms" in thresholds:
                # Approximate P95 as max time (conservative estimate)
                max_response_time = benchmark_category.get("max_time_ms", 0)
                category_results["metrics"]["max_response_time_ms"] = max_response_time

                if max_response_time > thresholds["max_p95_response_time_ms"]:
                    violation = f"Max response time {max_response_time:.1f}ms > {thresholds['max_p95_response_time_ms']}ms"
                    category_results["violations"].append(violation)
                    if category_results["status"] == "PASS":
                        category_results["status"] = "WARN"

            # Update counters
            if category_results["status"] == "PASS":
                results["passed"] += 1
            elif category_results["status"] == "FAIL":
                results["failed"] += 1
            elif category_results["status"] == "WARN":
                results["warnings"] += 1

            results["details"][gate_category] = category_results

        return results

    def _generate_recommendations(
        self, benchmark_analysis: dict[str, Any], quality_gates: dict[str, Any]
    ) -> list[dict[str, str]]:
        """Generate performance optimization recommendations."""
        recommendations = []

        # Check for slow benchmarks
        if benchmark_analysis.get("statistics"):
            stats = benchmark_analysis["statistics"]
            if stats.get("slowest_benchmark_ms", 0) > 1000:  # > 1 second
                recommendations.append(
                    {
                        "type": "PERFORMANCE",
                        "severity": "HIGH",
                        "message": f"Slowest benchmark takes {stats['slowest_benchmark_ms']:.1f}ms - investigate bottlenecks",
                        "category": "response_time",
                    }
                )

            if stats.get("avg_throughput_ops_sec", 0) < 5:  # < 5 ops/sec average
                recommendations.append(
                    {
                        "type": "THROUGHPUT",
                        "severity": "MEDIUM",
                        "message": f"Average throughput is {stats['avg_throughput_ops_sec']:.2f} ops/sec - consider optimization",
                        "category": "throughput",
                    }
                )

        # Check quality gate failures
        for category, results in quality_gates.get("details", {}).items():
            if results.get("status") == "FAIL":
                for violation in results.get("violations", []):
                    recommendations.append(
                        {
                            "type": "QUALITY_GATE",
                            "severity": "HIGH",
                            "message": f"{category}: {violation}",
                            "category": category,
                        }
                    )

        # Memory recommendations
        categories = benchmark_analysis.get("categories", {})
        for cat_name, cat_data in categories.items():
            if "memory" in cat_name.lower():
                avg_time = cat_data.get("avg_mean_time_ms", 0)
                if avg_time > 500:  # > 500ms for memory operations
                    recommendations.append(
                        {
                            "type": "MEMORY",
                            "severity": "MEDIUM",
                            "message": f"Memory operations averaging {avg_time:.1f}ms - check for memory leaks or inefficient allocation",
                            "category": "memory",
                        }
                    )

        # Scalability recommendations
        for cat_name, cat_data in categories.items():
            if "scalab" in cat_name.lower() or "concur" in cat_name.lower():
                max_time = cat_data.get("max_time_ms", 0)
                avg_time = cat_data.get("avg_mean_time_ms", 0)
                if max_time > avg_time * 5:  # High variance in response times
                    recommendations.append(
                        {
                            "type": "SCALABILITY",
                            "severity": "MEDIUM",
                            "message": f"High response time variance in {cat_name} (max: {max_time:.1f}ms, avg: {avg_time:.1f}ms) - investigate scaling bottlenecks",
                            "category": "scalability",
                        }
                    )

        # Add general recommendations if no specific issues found
        if not recommendations:
            recommendations.append(
                {
                    "type": "SUCCESS",
                    "severity": "INFO",
                    "message": "All performance tests passed! Consider adding more comprehensive test scenarios.",
                    "category": "general",
                }
            )

        return recommendations

    def _calculate_health_score(self, quality_gates: dict[str, Any]) -> int:
        """Calculate overall performance health score (0-100)."""
        total_gates = (
            quality_gates.get("passed", 0)
            + quality_gates.get("failed", 0)
            + quality_gates.get("warnings", 0)
        )

        if total_gates == 0:
            return 50  # Neutral score if no gates evaluated

        passed = quality_gates.get("passed", 0)
        warnings = quality_gates.get("warnings", 0)
        failed = quality_gates.get("failed", 0)

        # Weight: Pass=100%, Warning=70%, Fail=0%
        weighted_score = (passed * 100 + warnings * 70 + failed * 0) / total_gates

        return int(weighted_score)

    def _print_report_summary(self, report: dict[str, Any]):
        """Print performance report summary to console."""
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE TEST REPORT SUMMARY")
        print("=" * 60)

        # Overall status
        summary = report.get("summary", {})
        health_score = summary.get("health_score", 0)
        status = summary.get("status", "UNKNOWN")

        status_emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(status, "❓")
        print(
            f"Overall Status: {status_emoji} {status} (Health Score: {health_score}/100)"
        )

        # Test execution summary
        metadata = report.get("metadata", {})
        print(f"Test Runtime: {metadata.get('test_runtime', 0):.2f} seconds")
        print(f"Categories Tested: {', '.join(metadata.get('categories_tested', []))}")

        # Benchmark statistics
        benchmark_stats = report.get("benchmark_analysis", {}).get("statistics", {})
        if benchmark_stats:
            print("\n📈 Benchmark Statistics:")
            print(f"  Total Benchmarks: {benchmark_stats.get('total_benchmarks', 0)}")
            print(
                f"  Average Time: {benchmark_stats.get('avg_benchmark_time_ms', 0):.2f}ms"
            )
            print(f"  Fastest: {benchmark_stats.get('fastest_benchmark_ms', 0):.2f}ms")
            print(f"  Slowest: {benchmark_stats.get('slowest_benchmark_ms', 0):.2f}ms")
            print(
                f"  Total Throughput: {benchmark_stats.get('total_throughput_ops_sec', 0):.1f} ops/sec"
            )

        # Quality gates summary
        quality_gates = report.get("quality_gates", {})
        if quality_gates:
            print("\n🚪 Quality Gates:")
            print(f"  Passed: {quality_gates.get('passed', 0)}")
            print(f"  Warnings: {quality_gates.get('warnings', 0)}")
            print(f"  Failed: {quality_gates.get('failed', 0)}")

        # Top recommendations
        recommendations = report.get("recommendations", [])
        high_priority_recs = [r for r in recommendations if r.get("severity") == "HIGH"]
        if high_priority_recs:
            print("\n🔥 High Priority Recommendations:")
            for rec in high_priority_recs[:3]:  # Show top 3
                print(f"  • {rec.get('message', 'No message')}")

        print("=" * 60)

    def check_performance_regression(
        self, baseline_file: str | None = None, threshold_percent: float = 15.0
    ) -> dict[str, Any]:
        """Check for performance regressions against baseline."""
        if not baseline_file:
            # Look for most recent baseline
            baseline_files = list(self.output_dir.glob("performance_report_*.json"))
            if len(baseline_files) < 2:
                return {
                    "status": "NO_BASELINE",
                    "message": "No baseline found for comparison",
                }

            baseline_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            baseline_file = str(
                baseline_files[1]
            )  # Second most recent (current is most recent)

        try:
            with open(baseline_file) as f:
                baseline_report = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"status": "ERROR", "message": f"Cannot load baseline: {e}"}

        current_benchmarks = self.performance_report.get("benchmark_analysis", {}).get(
            "benchmarks", []
        )
        baseline_benchmarks = baseline_report.get("benchmark_analysis", {}).get(
            "benchmarks", []
        )

        if not current_benchmarks or not baseline_benchmarks:
            return {
                "status": "NO_DATA",
                "message": "Insufficient benchmark data for comparison",
            }

        # Create benchmark lookup by name
        baseline_lookup = {b["name"]: b for b in baseline_benchmarks}

        regressions = []
        improvements = []

        for current_bench in current_benchmarks:
            name = current_bench["name"]
            baseline_bench = baseline_lookup.get(name)

            if not baseline_bench:
                continue  # Skip if benchmark not in baseline

            current_time = current_bench["mean_time_ms"]
            baseline_time = baseline_bench["mean_time_ms"]

            if baseline_time > 0:
                change_percent = ((current_time - baseline_time) / baseline_time) * 100

                if change_percent > threshold_percent:
                    regressions.append(
                        {
                            "benchmark": name,
                            "current_time_ms": current_time,
                            "baseline_time_ms": baseline_time,
                            "regression_percent": change_percent,
                        }
                    )
                elif change_percent < -threshold_percent:
                    improvements.append(
                        {
                            "benchmark": name,
                            "current_time_ms": current_time,
                            "baseline_time_ms": baseline_time,
                            "improvement_percent": abs(change_percent),
                        }
                    )

        regression_result = {
            "status": "REGRESSION" if regressions else "OK",
            "baseline_file": baseline_file,
            "threshold_percent": threshold_percent,
            "regressions": regressions,
            "improvements": improvements,
            "total_comparisons": len(
                [b for b in current_benchmarks if b["name"] in baseline_lookup]
            ),
        }

        return regression_result


def main():
    """Main CLI entry point for performance test runner."""
    parser = argparse.ArgumentParser(description="Khive Performance Test Runner")
    parser.add_argument(
        "--categories",
        nargs="*",
        help="Test categories to run (default: all)",
        choices=[
            "benchmarks",
            "memory",
            "scalability",
            "orchestration",
            "artifacts",
            "cache",
            "planning",
            "session",
        ],
    )
    parser.add_argument(
        "--parallel", "-p", action="store_true", help="Run tests in parallel"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Reduce output verbosity"
    )
    parser.add_argument(
        "--no-report", action="store_true", help="Skip report generation"
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="tests/results/performance",
        help="Output directory",
    )
    parser.add_argument(
        "--check-regression", help="Check for regressions against baseline file"
    )
    parser.add_argument(
        "--regression-threshold",
        type=float,
        default=15.0,
        help="Regression threshold percentage",
    )
    parser.add_argument(
        "--ci-mode", action="store_true", help="CI mode - fail on regressions"
    )

    args = parser.parse_args()

    # Initialize runner
    runner = PerformanceTestRunner(output_dir=args.output_dir)

    # Run tests
    test_results = runner.run_performance_test_suite(
        test_categories=args.categories,
        parallel=args.parallel,
        verbose=not args.quiet,
        generate_report=not args.no_report,
    )

    exit_code = test_results.get("exit_code", 1)

    # Check for regressions if requested
    if args.check_regression or args.ci_mode:
        regression_result = runner.check_performance_regression(
            baseline_file=args.check_regression,
            threshold_percent=args.regression_threshold,
        )

        if regression_result["status"] == "REGRESSION":
            print("\n❌ Performance regressions detected:")
            for regression in regression_result["regressions"]:
                print(
                    f"  • {regression['benchmark']}: {regression['regression_percent']:.1f}% slower"
                )

            if args.ci_mode:
                print("\n💥 Failing build due to performance regressions")
                exit_code = 1
        elif regression_result["status"] == "OK":
            print(
                f"\n✅ No significant regressions found (threshold: {args.regression_threshold}%)"
            )
            if regression_result["improvements"]:
                print("🚀 Performance improvements:")
                for improvement in regression_result["improvements"]:
                    print(
                        f"  • {improvement['benchmark']}: {improvement['improvement_percent']:.1f}% faster"
                    )

    # Final status
    if exit_code == 0:
        print("\n🎉 All performance tests passed!")
    else:
        print(f"\n💥 Performance tests failed (exit code: {exit_code})")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
