#!/usr/bin/env python3
"""Performance test runner with comprehensive reporting."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from khive.services.performance import BenchmarkStorage, PerformanceReporter


def run_performance_tests(
    test_pattern="tests/performance/test_comprehensive_benchmarks.py",
    generate_report=True,
    ci_mode=False,
    fail_on_regression=True,
):
    """Run performance tests with comprehensive reporting."""

    print(f"🚀 Running performance tests: {test_pattern}")

    # Import pytest here to handle missing dependency gracefully
    try:
        import pytest
    except ImportError:
        print("❌ pytest not found. Install with: pip install pytest")
        return False

    # Run pytest with performance markers
    pytest_args = [
        test_pattern,
        "-v",
        "-m",
        "benchmark",
        "--tb=short",
        f"--junit-xml=performance_results/pytest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml",
    ]

    if ci_mode:
        pytest_args.extend(["--quiet", "--no-header"])

    # Run tests
    exit_code = pytest.main(pytest_args)

    if generate_report and not ci_mode:
        generate_performance_report()

    if ci_mode:
        generate_ci_report(fail_on_regression)

    return exit_code == 0


def generate_performance_report():
    """Generate comprehensive performance report."""

    print("📊 Generating performance report...")

    try:
        storage = BenchmarkStorage()
        reporter = PerformanceReporter(storage)

        report_files = reporter.generate_comprehensive_report(
            report_name="automated_performance_report",
            days_back=30,
            include_recommendations=True,
        )

        print("✅ Performance report generated:")
        for file_type, file_path in report_files.items():
            print(f"   {file_type.upper()}: {file_path}")

    except Exception as e:
        print(f"❌ Failed to generate performance report: {e}")


def generate_ci_report(fail_on_regression=True):
    """Generate CI-focused performance report."""

    print("🔍 Generating CI performance report...")

    try:
        storage = BenchmarkStorage()
        reporter = PerformanceReporter(storage)

        # Get recent results for CI analysis
        recent_results = storage.get_results(days_back=1, limit=50)

        ci_report = reporter.generate_ci_report(
            current_results=recent_results,
            comparison_days=7,
            fail_on_regression=fail_on_regression,
        )

        # Save CI report
        ci_report_file = Path(
            f"performance_results/ci_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        ci_report_file.parent.mkdir(exist_ok=True)

        with open(ci_report_file, "w") as f:
            json.dump(ci_report, f, indent=2)

        print(f"✅ CI report status: {ci_report['status']}")
        print(f"   Regressions: {len(ci_report.get('regressions', []))}")
        print(f"   Bottlenecks: {len(ci_report.get('bottlenecks', []))}")
        print(f"   Report saved: {ci_report_file}")

        # Exit with error if CI should fail
        if fail_on_regression and ci_report["status"] == "FAIL":
            print("❌ CI failing due to performance issues")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Failed to generate CI report: {e}")
        if fail_on_regression:
            sys.exit(1)


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description="Run khive performance tests with comprehensive reporting"
    )

    parser.add_argument(
        "--pattern",
        default="tests/performance/test_comprehensive_benchmarks.py",
        help="Test pattern to run (default: comprehensive benchmarks)",
    )

    parser.add_argument(
        "--no-report", action="store_true", help="Skip generating performance report"
    )

    parser.add_argument(
        "--ci", action="store_true", help="Run in CI mode with minimal output"
    )

    parser.add_argument(
        "--no-fail-on-regression",
        action="store_true",
        help="Don't fail CI on performance regressions",
    )

    args = parser.parse_args()

    success = run_performance_tests(
        test_pattern=args.pattern,
        generate_report=not args.no_report,
        ci_mode=args.ci,
        fail_on_regression=not args.no_fail_on_regression,
    )

    if not success:
        print("❌ Performance tests failed")
        sys.exit(1)
    else:
        print("✅ Performance tests completed successfully")


if __name__ == "__main__":
    main()
