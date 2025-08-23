#!/usr/bin/env python3
"""Setup comprehensive performance monitoring infrastructure for khive."""

import json
import sys
from pathlib import Path


def setup_performance_infrastructure():
    """Set up the complete performance monitoring infrastructure."""

    print("🔧 Setting up khive performance monitoring infrastructure...")

    # Create performance directories
    performance_dirs = [
        ".khive/performance",
        ".khive/performance/benchmarks",
        ".khive/performance/reports",
        ".khive/performance/dashboards",
        "performance_results",
        "scripts/performance",
    ]

    for dir_path in performance_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {dir_path}")

    # Create performance configuration
    performance_config = {
        "benchmarking": {
            "storage_path": ".khive/performance/benchmarks",
            "reports_path": ".khive/performance/reports",
            "dashboards_path": ".khive/performance/dashboards",
            "monitoring_interval": 0.1,
            "cleanup_after_days": 30,
        },
        "thresholds": {
            "orchestration": {
                "max_duration_seconds": 30.0,
                "max_memory_mb": 100.0,
                "min_success_rate": 0.95,
                "max_cpu_percent": 80.0,
            },
            "cache": {
                "max_duration_ms": 50.0,
                "max_memory_mb": 200.0,
                "min_throughput_ops_per_sec": 100.0,
            },
            "artifacts": {
                "max_duration_seconds": 10.0,
                "max_memory_mb": 50.0,
                "max_io_mb": 100.0,
            },
            "session": {
                "max_duration_seconds": 5.0,
                "max_memory_mb": 25.0,
                "max_concurrent_sessions": 100,
            },
        },
        "regression_detection": {
            "minor_threshold": 1.2,
            "moderate_threshold": 1.5,
            "critical_threshold": 2.0,
            "min_samples": 5,
            "statistical_confidence": 0.8,
        },
        "bottleneck_detection": {
            "cpu_threshold_percent": 80.0,
            "memory_threshold_percent": 80.0,
            "io_threshold_mb": 10.0,
            "network_threshold_mb": 5.0,
        },
        "optimization": {
            "auto_tune_enabled": False,
            "max_recommendations": 20,
            "improvement_threshold_percent": 5.0,
        },
        "reporting": {
            "generate_html_reports": True,
            "generate_ci_reports": True,
            "report_retention_days": 90,
            "dashboard_refresh_hours": 6,
        },
        "ci_integration": {
            "fail_on_regression": True,
            "performance_budget_enabled": True,
            "alert_on_bottlenecks": True,
            "generate_pr_comments": True,
        },
    }

    config_file = Path(".khive/performance/config.json")
    with open(config_file, "w") as f:
        json.dump(performance_config, f, indent=2)
    print(f"✅ Created performance configuration: {config_file}")

    # Create pytest configuration for performance tests
    pytest_perf_config = """
[tool:pytest]
markers =
    benchmark: Performance benchmark tests
    slow: Slow-running tests (>5s)
    load_test: Load and stress testing
    memory_test: Memory usage and leak tests
    regression_test: Performance regression tests

# Performance test configuration
addopts = --strict-markers --tb=short
testpaths = tests/performance
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Benchmark-specific settings
benchmark_group_by = group
benchmark_min_rounds = 3
benchmark_max_time = 30
benchmark_timer = time.perf_counter
benchmark_warmup = true
benchmark_disable_gc = true
benchmark_sort = mean
"""

    pytest_perf_file = Path("tests/performance/pytest.ini")
    with open(pytest_perf_file, "w") as f:
        f.write(pytest_perf_config.strip())
    print(f"✅ Created pytest performance configuration: {pytest_perf_file}")

    # Create performance test runner script
    perf_runner_script = '''#!/usr/bin/env python3
"""Performance test runner with comprehensive reporting."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from khive.services.performance import (
    BenchmarkStorage,
    PerformanceReporter,
    CIIntegration,
)


def run_performance_tests(
    test_pattern="tests/performance/test_comprehensive_benchmarks.py",
    generate_report=True,
    ci_mode=False,
    fail_on_regression=True
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
        "-m", "benchmark",
        "--tb=short",
        f"--junit-xml=performance_results/pytest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
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
            include_recommendations=True
        )

        print(f"✅ Performance report generated:")
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
            fail_on_regression=fail_on_regression
        )

        # Save CI report
        ci_report_file = Path(f"performance_results/ci_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        ci_report_file.parent.mkdir(exist_ok=True)

        with open(ci_report_file, 'w') as f:
            json.dump(ci_report, f, indent=2)

        print(f"✅ CI report status: {ci_report['status']}")
        print(f"   Regressions: {len(ci_report.get('regressions', []))}")
        print(f"   Bottlenecks: {len(ci_report.get('bottlenecks', []))}")
        print(f"   Report saved: {ci_report_file}")

        # Exit with error if CI should fail
        if fail_on_regression and ci_report['status'] == 'FAIL':
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
        help="Test pattern to run (default: comprehensive benchmarks)"
    )

    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip generating performance report"
    )

    parser.add_argument(
        "--ci",
        action="store_true",
        help="Run in CI mode with minimal output"
    )

    parser.add_argument(
        "--no-fail-on-regression",
        action="store_true",
        help="Don't fail CI on performance regressions"
    )

    args = parser.parse_args()

    success = run_performance_tests(
        test_pattern=args.pattern,
        generate_report=not args.no_report,
        ci_mode=args.ci,
        fail_on_regression=not args.no_fail_on_regression
    )

    if not success:
        print("❌ Performance tests failed")
        sys.exit(1)
    else:
        print("✅ Performance tests completed successfully")


if __name__ == "__main__":
    main()
'''

    perf_runner_file = Path("scripts/performance/run_performance_tests.py")
    perf_runner_file.parent.mkdir(parents=True, exist_ok=True)
    with open(perf_runner_file, "w") as f:
        f.write(perf_runner_script.strip())
    perf_runner_file.chmod(0o755)
    print(f"✅ Created performance test runner: {perf_runner_file}")

    # Create GitHub Actions workflow
    github_workflow = """
name: Performance Monitoring

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC

jobs:
  performance-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install uv
        uv sync

    - name: Run performance benchmarks
      run: |
        python scripts/performance/run_performance_tests.py --ci

    - name: Upload performance results
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: performance-results-${{ github.run_id }}
        path: |
          performance_results/
          .khive/performance/reports/
        retention-days: 30

    - name: Comment PR with performance results
      if: github.event_name == 'pull_request' && always()
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const glob = require('@actions/glob');

          // Find latest CI report
          const globber = await glob.create('performance_results/ci_report_*.json');
          const files = await globber.glob();

          if (files.length > 0) {
            const reportFile = files.sort().pop(); // Get latest
            const report = JSON.parse(fs.readFileSync(reportFile, 'utf8'));

            const status = report.status;
            const regressions = report.regressions || [];
            const bottlenecks = report.bottlenecks || [];

            let comment = `## 🔍 Performance Test Results\\n\\n`;
            comment += `**Status:** ${status === 'PASS' ? '✅ PASS' : '❌ FAIL'}\\n\\n`;

            if (regressions.length > 0) {
              comment += `### ⚠️ Performance Regressions (${regressions.length})\\n`;
              regressions.slice(0, 5).forEach(reg => {
                comment += `- **${reg.benchmark_name}.${reg.operation_type}**: ${reg.relative_change.toFixed(2)}x slower (${reg.severity})\\n`;
              });
              comment += '\\n';
            }

            if (bottlenecks.length > 0) {
              comment += `### 🐛 Performance Bottlenecks (${bottlenecks.length})\\n`;
              bottlenecks.slice(0, 5).forEach(bot => {
                comment += `- **${bot.benchmark_name}**: ${bot.bottleneck_type} bottleneck (${bot.performance_impact.toFixed(1)}% impact)\\n`;
              });
            }

            if (regressions.length === 0 && bottlenecks.length === 0) {
              comment += '✅ No performance issues detected!\\n';
            }

            comment += `\\n---\\n*Generated by khive performance monitoring*`;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
          }

    - name: Fail on performance regression
      if: always()
      run: |
        # Check if any CI reports indicate failure
        for report in performance_results/ci_report_*.json; do
          if [ -f "$report" ]; then
            if grep -q '"status": "FAIL"' "$report"; then
              echo "❌ Performance regression detected - failing build"
              cat "$report" | jq '.summary'
              exit 1
            fi
          fi
        done
        echo "✅ No performance regressions detected"
"""

    workflow_dir = Path(".github/workflows")
    workflow_dir.mkdir(parents=True, exist_ok=True)

    workflow_file = workflow_dir / "performance.yml"
    with open(workflow_file, "w") as f:
        f.write(github_workflow.strip())
    print(f"✅ Created GitHub Actions workflow: {workflow_file}")

    # Create performance monitoring documentation
    perf_docs = """# Performance Monitoring Infrastructure

This document describes the comprehensive performance monitoring infrastructure for khive.

## Overview

The performance monitoring system provides:

- **Benchmarking Framework**: Comprehensive performance measurement with resource monitoring
- **Statistical Analysis**: Trend detection, regression analysis, and bottleneck identification
- **Optimization Recommendations**: AI-powered suggestions for performance improvements
- **Automated Reporting**: HTML dashboards, CI integration, and trend reports
- **Storage & Persistence**: SQLite and JSON-based performance data storage

## Quick Start

### Running Performance Tests

```bash
# Run all performance benchmarks
python scripts/performance/run_performance_tests.py

# Run in CI mode (minimal output)
python scripts/performance/run_performance_tests.py --ci

# Run specific test pattern
python scripts/performance/run_performance_tests.py --pattern "tests/performance/test_cache_*"
```

### Using the Benchmarking Framework

```python
from khive.services.performance import BenchmarkFramework, BenchmarkStorage

# Initialize framework
framework = BenchmarkFramework()
storage = BenchmarkStorage()

# Benchmark synchronous operations
with framework.benchmark("my_operation", "performance_test"):
    # Your code here
    result = expensive_function()

# Benchmark async operations
async with framework.async_benchmark("async_operation", "async_test"):
    result = await async_function()

# Store results
for result in framework.get_results():
    storage.store_result(result)
```

### Load Testing

```python
# Run concurrent load test
load_result = await framework.benchmark_load(
    func=my_async_function,
    name="load_test",
    concurrent_tasks=20,
    operations_per_task=50,
    ramp_up_seconds=2.0
)
```

## Performance Analysis

### Trend Analysis

```python
from khive.services.performance import TrendAnalyzer

analyzer = TrendAnalyzer(storage)
trend = analyzer.analyze_trend(
    benchmark_name="my_service",
    operation_type="api_call",
    metric_name="duration",
    days_back=30
)

print(f"Trend: {trend.direction.value}, Confidence: {trend.confidence:.2f}")
```

### Regression Detection

```python
from khive.services.performance import RegressionDetector

detector = RegressionDetector(storage)
regression = detector.detect_regression(
    current_result=latest_benchmark_result,
    metric_name="duration"
)

if regression.regression_detected:
    print(f"Regression: {regression.severity.value} - {regression.recommendation}")
```

### Bottleneck Identification

```python
from khive.services.performance import BottleneckIdentifier

identifier = BottleneckIdentifier(storage)
bottlenecks = identifier.identify_bottlenecks("my_service", days_back=7)

for bottleneck in bottlenecks:
    print(f"{bottleneck.bottleneck_type}: {bottleneck.performance_impact:.1f}% impact")
```

## Optimization Recommendations

```python
from khive.services.performance import OptimizationRecommender

recommender = OptimizationRecommender(storage)
plan = recommender.generate_recommendations(
    benchmark_name="my_service",
    days_back=30,
    max_recommendations=10
)

print(f"Optimization plan: {plan.total_estimated_improvement:.1f}% improvement")
for rec in plan.critical_recommendations:
    print(f"- {rec.title}: {rec.estimated_improvement_percent:.1f}% improvement")
```

## Reporting and Dashboards

### Generate HTML Reports

```python
from khive.services.performance import PerformanceReporter

reporter = PerformanceReporter(storage)
report_files = reporter.generate_comprehensive_report(
    report_name="monthly_performance_report",
    days_back=30,
    include_recommendations=True
)

print(f"HTML report: {report_files['html']}")
```

### CI Integration

```python
# Generate CI-focused report
recent_results = storage.get_results(days_back=1)
ci_report = reporter.generate_ci_report(
    current_results=recent_results,
    fail_on_regression=True
)

if ci_report['status'] == 'FAIL':
    print(f"CI failure: {len(ci_report['regressions'])} regressions detected")
```

## Configuration

Performance monitoring is configured via `.khive/performance/config.json`:

```json
{
  "thresholds": {
    "orchestration": {
      "max_duration_seconds": 30.0,
      "max_memory_mb": 100.0,
      "min_success_rate": 0.95
    }
  },
  "regression_detection": {
    "minor_threshold": 1.2,
    "critical_threshold": 2.0
  },
  "ci_integration": {
    "fail_on_regression": true,
    "generate_pr_comments": true
  }
}
```

## Storage and Data Persistence

Performance data is stored in multiple formats:

- **SQLite Database**: `.khive/performance/benchmarks/benchmarks.db` - Structured performance data with indexes
- **JSON Exports**: `.khive/performance/benchmarks/json_exports/` - Portable data exports
- **Reports**: `.khive/performance/reports/` - Generated HTML, JSON, and text reports

## CI/CD Integration

### GitHub Actions

The system includes a comprehensive GitHub Actions workflow that:

- Runs performance tests on every PR and push
- Generates performance reports and artifacts
- Comments on PRs with performance analysis
- Fails builds on critical performance regressions

### Jenkins Pipeline

A Jenkins pipeline is also provided for organizations using Jenkins CI/CD.

## Troubleshooting

### Common Issues

**High Memory Usage**: Check for memory leaks using the memory profiling features:
```python
# Enable detailed memory monitoring
framework = BenchmarkFramework(monitoring_interval=0.05)
```

**Flaky Performance Tests**: Use statistical analysis to identify variance:
```python
analysis = analyzer.analyze_metric(results, "duration")
cv = analysis["coefficient_of_variation"]
if cv > 0.3:
    print("High variance detected - investigate consistency")
```

**Missing Performance Data**: Ensure proper storage:
```python
# Always store results after benchmarking
for result in framework.get_results():
    storage.store_result(result)
```

## Best Practices

1. **Consistent Test Environment**: Use Docker containers for reproducible performance testing
2. **Baseline Management**: Establish performance baselines and update them regularly
3. **Gradual Rollout**: Implement performance budgets and gradual degradation thresholds
4. **Regular Monitoring**: Set up automated daily/weekly performance reporting
5. **Root Cause Analysis**: Use bottleneck identification to find performance issues early

## Support

For questions about performance monitoring:
- Check configuration in `.khive/performance/config.json`
- Review performance reports in `.khive/performance/reports/`
- Run diagnostics with `python scripts/performance/run_performance_tests.py --ci`
"""

    docs_file = Path("docs/performance_monitoring.md")
    docs_file.parent.mkdir(exist_ok=True)
    with open(docs_file, "w") as f:
        f.write(perf_docs.strip())
    print(f"✅ Created performance monitoring documentation: {docs_file}")

    # Update main pyproject.toml to include performance dependencies
    print("\n📦 Performance monitoring infrastructure setup complete!")
    print("\nNext steps:")
    print("1. Install additional dependencies if needed:")
    print("   uv add plotly  # For visualization dashboards")
    print("2. Run initial performance tests:")
    print("   python scripts/performance/run_performance_tests.py")
    print("3. Check the generated reports in .khive/performance/reports/")
    print("4. Customize configuration in .khive/performance/config.json")
    print("\n✅ Performance monitoring is ready to use!")

    return True


if __name__ == "__main__":
    try:
        setup_performance_infrastructure()
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)
