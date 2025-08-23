# Performance Monitoring Infrastructure

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