# Khive Performance Testing Suite

Comprehensive performance testing framework for the khive intelligent
development system. This suite validates system scalability, resource usage,
response times, and throughput characteristics to ensure khive can handle
production workloads efficiently and maintain performance over time.

## 📋 Overview

The performance testing suite consists of multiple specialized test modules that
comprehensively evaluate different aspects of the khive system:

### Test Modules

| Module                              | Purpose                                 | Coverage                                                        |
| ----------------------------------- | --------------------------------------- | --------------------------------------------------------------- |
| `conftest.py`                       | Core performance testing infrastructure | Fixtures, profiling, load testing, monitoring                   |
| `test_orchestration_performance.py` | Orchestration service performance       | Branch creation, atomic analysis, workflow scaling              |
| `test_planning_performance.py`      | Planning service performance            | Complexity assessment, role selection, cost tracking            |
| `test_session_performance.py`       | Session management performance          | Session lifecycle, concurrency, memory usage                    |
| `test_artifacts_performance.py`     | Artifacts service performance           | Document operations, storage I/O, registry performance          |
| `test_cache_performance.py`         | Cache layer performance                 | Get/set operations, hit/miss ratios, Redis backend              |
| `test_integration_performance.py`   | Cross-service workflows                 | End-to-end workflows, service coordination, resource contention |
| `test_benchmark_regression.py`      | Performance monitoring                  | Baseline tracking, regression detection, automated alerts       |

## 🏗️ Architecture

### Core Infrastructure (`conftest.py`)

The performance testing framework is built on several key components:

#### PerformanceProfiler

Advanced profiler that tracks:

- Operation timing with microsecond precision
- Memory usage snapshots (RSS, VMS)
- CPU utilization monitoring
- Success/failure rates with metadata
- Custom metrics for domain-specific measurements

```python
profiler = PerformanceProfiler()
profiler.start_measurement()
# ... perform operations ...
profiler.record_operation(duration, success=True, operation_type="cache_get")
profiler.end_measurement()
metrics = profiler.get_comprehensive_metrics()
```

#### LoadTestRunner

Sophisticated load testing framework supporting:

- Asynchronous concurrent operations
- Controlled ramp-up patterns
- Throughput and latency measurement
- Success rate tracking under load

```python
runner = LoadTestRunner(profiler)
results = await runner.run_async_load_test(
    operation_func,
    concurrent_tasks=10,
    operations_per_task=100,
    ramp_up_seconds=1.0
)
```

#### Memory Monitoring

Integrated memory profiling with:

- Before/after memory snapshots
- Memory leak detection algorithms
- Garbage collection impact analysis
- Memory usage per operation tracking

### Performance Thresholds

Configurable performance thresholds for different services:

```python
thresholds = {
    'orchestration': {
        'simple_operation_ms': 100,
        'complex_operation_ms': 1000,
        'memory_limit_mb': 50,
        'throughput_ops_per_sec': 10,
    },
    'cache': {
        'cache_get_ms': 5,
        'cache_set_ms': 10,
        'throughput_ops_per_sec': 1000,
    },
    # ... additional service thresholds
}
```

## 🚀 Running Performance Tests

### Prerequisites

Ensure you have the required dependencies:

```bash
uv add --dev pytest psutil pytest-asyncio
```

### Basic Test Execution

Run all performance tests:

```bash
pytest tests/performance/ -v
```

Run specific service performance tests:

```bash
# Orchestration performance
pytest tests/performance/test_orchestration_performance.py -v

# Cache performance
pytest tests/performance/test_cache_performance.py -v

# Integration performance
pytest tests/performance/test_integration_performance.py -v
```

### Advanced Test Execution

Run with detailed profiling output:

```bash
pytest tests/performance/ -v -s --tb=short
```

Run only benchmark and regression tests:

```bash
pytest tests/performance/test_benchmark_regression.py -v
```

Run with custom performance thresholds:

```bash
PERF_CACHE_GET_MS=3 PERF_CACHE_SET_MS=8 pytest tests/performance/test_cache_performance.py
```

### Parallel Test Execution

For faster execution of independent test modules:

```bash
pytest tests/performance/ -n auto --dist=loadscope
```

## 📊 Test Categories

### 1. Benchmark Tests

Establish performance baselines for core operations:

- **Operation Timing**: Measure execution time for typical operations
- **Throughput Testing**: Determine maximum operations per second
- **Memory Usage**: Profile memory consumption patterns
- **Resource Utilization**: Track CPU, memory, and I/O usage

Example benchmark test:

```python
def test_cache_get_set_performance(performance_profiler, performance_thresholds):
    threshold = performance_thresholds['cache']['cache_get_ms'] / 1000

    for i in range(100):
        start_time = time.perf_counter()
        result = await cache_service.get(f"key_{i}")
        end_time = time.perf_counter()

        operation_time = end_time - start_time
        assert operation_time < threshold
        performance_profiler.record_operation(operation_time, success=True)
```

### 2. Scalability Tests

Evaluate performance under increasing loads:

- **Concurrent Operations**: Test with multiple simultaneous operations
- **Load Scaling**: Measure performance degradation under heavy load
- **Resource Contention**: Identify bottlenecks in shared resources
- **Horizontal Scaling**: Test multi-instance performance characteristics

Example scalability test:

```python
async def test_concurrent_operations_scaling(load_test_runner):
    for concurrency in [1, 5, 10, 25, 50]:
        results = await load_test_runner.run_async_load_test(
            cache_operation,
            concurrent_tasks=concurrency,
            operations_per_task=20
        )

        assert results['success_rate'] > 0.95
        assert results['throughput'] > min_acceptable_throughput
```

### 3. Memory Profiling Tests

Analyze memory usage patterns and detect leaks:

- **Memory Growth**: Track memory usage over time
- **Leak Detection**: Identify operations that don't release memory
- **Large Object Handling**: Test performance with substantial data
- **Garbage Collection**: Analyze GC impact on performance

Example memory test:

```python
def test_memory_leak_detection(memory_monitor):
    for i in range(100):
        memory_usage = memory_monitor(lambda: perform_operation())

        if i > 20 and memory_usage['memory_delta_mb'] > 5.0:
            pytest.fail(f"Potential memory leak detected at iteration {i}")
```

### 4. Stress Tests

Validate system behavior under extreme conditions:

- **Resource Exhaustion**: Test behavior when resources are depleted
- **High Concurrency**: Push concurrent operation limits
- **Extended Duration**: Long-running performance validation
- **Error Conditions**: Performance during error scenarios

Example stress test:

```python
async def test_high_concurrency_stress():
    concurrent_ops = 100
    duration = 30  # seconds

    completed_operations = 0
    errors = []

    async def stress_worker():
        nonlocal completed_operations
        while time.perf_counter() - start_time < duration:
            try:
                await perform_stress_operation()
                completed_operations += 1
            except Exception as e:
                errors.append(str(e))

    tasks = [asyncio.create_task(stress_worker()) for _ in range(concurrent_ops)]
    await asyncio.gather(*tasks, return_exceptions=True)

    error_rate = len(errors) / max(completed_operations + len(errors), 1)
    assert error_rate < 0.1  # Less than 10% error rate
```

## 📈 Performance Benchmarking & Regression Detection

### Benchmark Storage

The framework automatically stores performance benchmarks for historical
comparison:

```python
# Benchmarks are stored in .khive/performance/benchmarks/
benchmark = PerformanceBenchmark(
    test_name="cache_performance",
    operation_type="cache_get",
    timestamp=datetime.now(),
    metrics={
        'avg_operation_time': 0.004,
        'throughput': 1200,
        'memory_usage': 25.3
    }
)
storage.save_benchmark(benchmark)
```

### Regression Detection

Automated regression detection compares current performance against historical
baselines:

```python
detector = RegressionDetector(
    regression_threshold=1.2,  # 20% degradation threshold
    min_samples=5,
    statistical_confidence=0.95
)

result = detector.detect_regression(
    current_metrics=current_performance,
    historical_benchmarks=historical_data
)

if result['regression_detected']:
    print(f"Regression detected: {result['recommendation']}")
```

### Performance Reports

Generate comprehensive performance reports:

```bash
# Run tests and generate report
pytest tests/performance/ --benchmark-report=reports/performance_report.json
```

Report structure:

```json
{
  "generated_at": "2025-01-23T10:30:00",
  "period_days": 30,
  "test_summary": {
    "cache_performance": {
      "operations_tested": 4,
      "historical_samples": 150,
      "regressions_detected": 1
    }
  },
  "regressions": [
    {
      "test_name": "cache_performance",
      "operation_type": "cache_set",
      "regression_details": {
        "current_value": 0.012,
        "historical_mean": 0.008,
        "relative_change": 1.5,
        "confidence": 0.92
      }
    }
  ],
  "recommendations": [
    "Moderate regression detected in cache_set operations. Review recent changes."
  ]
}
```

## 🔧 Configuration & Customization

### Environment Variables

Configure performance testing behavior:

```bash
# Performance thresholds (in milliseconds)
export PERF_ORCHESTRATION_SIMPLE_MS=100
export PERF_ORCHESTRATION_COMPLEX_MS=1000
export PERF_CACHE_GET_MS=5
export PERF_CACHE_SET_MS=10
export PERF_SESSION_CREATE_MS=50

# Memory limits (in MB)
export PERF_ORCHESTRATION_MEMORY_MB=50
export PERF_CACHE_MEMORY_MB=200

# Throughput targets (operations per second)
export PERF_CACHE_THROUGHPUT_OPS=1000
export PERF_ARTIFACTS_THROUGHPUT_OPS=50

# Test execution
export PERF_CONCURRENT_SESSIONS=100
export PERF_STRESS_DURATION_SEC=30
```

### Custom Test Scenarios

Extend performance testing with custom scenarios:

```python
# tests/performance/test_custom_performance.py
import pytest
from khive.services.custom import CustomService

class TestCustomServicePerformance:

    @pytest.mark.asyncio
    async def test_custom_operation_performance(
        self, performance_profiler, performance_thresholds
    ):
        service = CustomService()

        performance_profiler.start_measurement()

        for i in range(100):
            start_time = time.perf_counter()
            result = await service.custom_operation(f"input_{i}")
            end_time = time.perf_counter()

            operation_time = end_time - start_time
            performance_profiler.record_operation(
                operation_time,
                success=result is not None,
                operation_type="custom_operation"
            )

        performance_profiler.end_measurement()

        metrics = performance_profiler.get_comprehensive_metrics()
        assert metrics['avg_operation_time'] < 0.050  # 50ms threshold
        assert metrics['success_rate'] > 0.99
```

## 🚨 Monitoring & Alerts

### Continuous Integration Integration

Add performance testing to CI/CD pipeline:

```yaml
# .github/workflows/performance.yml
name: Performance Testing

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  performance:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Run performance tests
        run: |
          uv run pytest tests/performance/ \
            --benchmark-report=performance_report.json \
            --junit-xml=performance_results.xml

      - name: Upload performance report
        uses: actions/upload-artifact@v3
        with:
          name: performance-report
          path: performance_report.json

      - name: Check for regressions
        run: |
          if grep -q '"regression_detected": true' performance_report.json; then
            echo "Performance regression detected!"
            exit 1
          fi
```

### Alert Configuration

Set up automated performance alerts:

```python
# scripts/performance_monitor.py
import json
from pathlib import Path

def check_performance_regressions(report_path: Path):
    with open(report_path) as f:
        report = json.load(f)

    regressions = report.get('regressions', [])
    critical_regressions = [
        r for r in regressions
        if r['regression_details'].get('relative_change', 0) > 2.0
    ]

    if critical_regressions:
        send_alert(
            f"CRITICAL: {len(critical_regressions)} performance regressions detected",
            details=critical_regressions
        )
    elif regressions:
        send_warning(
            f"WARNING: {len(regressions)} performance regressions detected",
            details=regressions
        )

def send_alert(message: str, details: list):
    # Integration with alerting system (Slack, email, etc.)
    print(f"🚨 ALERT: {message}")
    for detail in details:
        print(f"  - {detail['test_name']}.{detail['operation_type']}")
```

## 📚 Best Practices

### 1. Test Design Principles

- **Isolation**: Each test should be independent and not affect others
- **Repeatability**: Tests should produce consistent results across runs
- **Realistic Workloads**: Test scenarios should reflect actual usage patterns
- **Clear Metrics**: Define specific, measurable performance criteria

### 2. Performance Thresholds

- **Conservative Baselines**: Set initial thresholds based on worst-case
  acceptable performance
- **Regular Updates**: Adjust thresholds as system performance improves
- **Environment-Specific**: Use different thresholds for development, staging,
  and production
- **Service-Specific**: Tailor thresholds to each service's performance
  characteristics

### 3. Test Execution Strategy

- **Staged Rollout**: Run performance tests in phases (unit → integration →
  system)
- **Load Progression**: Start with light loads and gradually increase
- **Multiple Runs**: Execute tests multiple times to account for variance
- **Resource Monitoring**: Track system resources during test execution

### 4. Regression Analysis

- **Historical Context**: Consider performance trends, not just point
  comparisons
- **Statistical Significance**: Use proper statistical methods for regression
  detection
- **Root Cause Analysis**: Investigate the source of performance changes
- **Actionable Alerts**: Provide specific recommendations for performance issues

## 🛠️ Troubleshooting

### Common Issues

#### High Test Execution Time

```bash
# Run tests in parallel
pytest tests/performance/ -n auto

# Skip slow tests during development
pytest tests/performance/ -m "not slow"

# Run only critical performance tests
pytest tests/performance/ -k "benchmark"
```

#### Memory Usage Issues

```python
# Add explicit garbage collection
import gc

@pytest.fixture(autouse=True)
def cleanup_after_test():
    yield
    gc.collect()
```

#### Flaky Performance Tests

```python
# Add retries for unstable tests
@pytest.mark.flaky(reruns=3, reruns_delay=1)
def test_potentially_flaky_performance():
    # Test implementation
    pass
```

#### Resource Contention

```bash
# Use resource isolation
pytest tests/performance/ --forked

# Limit concurrent processes
pytest tests/performance/ -n 2
```

### Debug Performance Issues

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Add performance debugging
performance_profiler.debug = True
```

Profile individual operations:

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Perform operation
await service.expensive_operation()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative').print_stats(10)
```

## 📝 Contributing

### Adding New Performance Tests

1. **Create Test Module**: Follow the naming convention `test_*_performance.py`
2. **Use Standard Fixtures**: Leverage existing profiler and threshold fixtures
3. **Document Performance Criteria**: Clearly define what constitutes acceptable
   performance
4. **Include Multiple Scenarios**: Test various load levels and edge cases
5. **Add Regression Detection**: Ensure new tests support automated regression
   detection

### Performance Test Checklist

- [ ] Tests are isolated and repeatable
- [ ] Multiple performance scenarios are covered
- [ ] Appropriate performance thresholds are defined
- [ ] Memory usage is monitored and tested
- [ ] Concurrent/load testing is included
- [ ] Regression detection is enabled
- [ ] Documentation is updated

## 🤝 Integration with Development Workflow

### Pre-commit Hooks

Add performance validation to pre-commit:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: performance-quick-check
        name: Quick Performance Check
        entry: uv run pytest tests/performance/test_benchmark_regression.py -k "not slow"
        language: system
        pass_filenames: false
```

### Code Review Guidelines

Performance considerations for code reviews:

1. **Algorithm Complexity**: Verify O(n) complexity doesn't introduce
   performance regressions
2. **Resource Usage**: Check for potential memory leaks or excessive resource
   consumption
3. **Concurrent Safety**: Ensure thread-safe operations don't impact performance
4. **Caching Strategy**: Validate that caching improves rather than hinders
   performance

### Release Process Integration

Include performance validation in release pipeline:

```bash
# Performance gate in release pipeline
uv run pytest tests/performance/ --benchmark-report=release_performance.json

# Validate against production baselines
python scripts/validate_performance_for_release.py release_performance.json
```

---

## 📞 Support & Maintenance

For questions about performance testing or to report issues:

- **Issues**: Use GitHub issues with the `performance` label
- **Discussions**: Performance optimization discussions in GitHub Discussions
- **Documentation**: Updates to this README should accompany performance test
  changes

The performance testing suite is actively maintained and continuously improved
to ensure khive maintains excellent performance characteristics as the system
evolves.
