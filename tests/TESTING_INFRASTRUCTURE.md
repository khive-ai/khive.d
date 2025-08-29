# Khive Testing Infrastructure

This document provides a comprehensive guide to the khive testing
infrastructure, including fixtures, utilities, and testing patterns.

## 🚀 Quick Start

```bash
# Install dependencies
uv sync --group dev

# Run all tests
uv run pytest

# Run specific test categories
uv run pytest -m unit          # Unit tests
uv run pytest -m integration   # Integration tests
uv run pytest -m security      # Security tests
uv run pytest -m performance   # Performance tests
uv run pytest -m e2e          # End-to-end tests

# Run with coverage
uv run pytest --cov=src/khive --cov-report=html

# Run parallel tests
uv run pytest -n auto
```

## 📊 Test Categories and Markers

### Core Test Types

- `unit`: Fast unit tests (<100ms)
- `integration`: Integration tests with dependencies
- `e2e`: End-to-end integration tests
- `slow`: Slow-running tests (>5s)
- `smoke`: Basic smoke tests for core functionality
- `regression`: Regression tests for known bug fixes

### Domain-Specific Testing

- `cli`: Command-line interface tests
- `api`: API endpoint and service tests
- `database`: Database integration tests
- `filesystem`: File system operation tests
- `network`: Network communication tests

### Async and Concurrency

- `async_test`: Async/await pattern tests
- `concurrency`: Concurrent execution and thread safety tests
- `timeout_handling`: Timeout and cancellation handling tests
- `race_condition`: Race condition detection tests
- `deadlock`: Deadlock prevention tests

### Security Testing

- `security`: Security validation and vulnerability tests
- `input_validation`: Input sanitization and validation tests
- `auth`: Authentication and authorization tests
- `secrets`: Secret handling and protection tests
- `injection`: Injection attack prevention tests

### Performance Testing

- `performance`: Performance benchmark tests
- `load`: Load testing with high volume
- `stress`: Stress testing under extreme conditions
- `memory`: Memory usage and leak detection tests
- `cpu`: CPU usage optimization tests
- `scalability`: Scalability and capacity tests

## 🛠️ Available Fixtures

### Async Testing Fixtures

```python
@pytest.mark.async_test
async def test_async_operation(async_test_env, async_timeout_manager):
    \"\"\"Test async operations with proper timeout management.\"\"\"
    timeout_manager = async_timeout_manager

    async def slow_operation():
        await asyncio.sleep(0.1)
        return "completed"

    # Test with timeout
    result = await timeout_manager.with_timeout(slow_operation(), timeout=1.0)
    assert result == "completed"
```

### CLI Testing Fixtures

```python
@pytest.mark.cli
def test_cli_command(cli_test_environment, cli_command_builder):
    \"\"\"Test CLI commands in isolated environment.\"\"\"
    env = cli_test_environment
    builder = cli_command_builder

    # Build command
    cmd = builder.plan("Implement new feature", complexity="medium")
    assert cmd[0] == "uv"
    assert "khive" in cmd
    assert "plan" in cmd
```

### Filesystem Testing Fixtures

```python
@pytest.mark.filesystem
def test_file_operations(temp_workspace, mock_filesystem):
    \"\"\"Test file operations with workspace isolation.\"\"\"
    workspace = temp_workspace

    # Test workspace structure
    assert (workspace / "src").exists()
    assert (workspace / "tests").exists()

    # Create test file
    test_file = workspace / "test.py"
    test_file.write_text("print('Hello, World!')")

    assert test_file.exists()
    assert "Hello, World!" in test_file.read_text()
```

### Performance Testing Fixtures

```python
@pytest.mark.performance
def test_performance_benchmark(performance_monitor, benchmark_config):
    \"\"\"Test performance with monitoring and assertions.\"\"\"
    monitor = performance_monitor
    config = benchmark_config

    monitor.start_monitoring()

    # Perform operations
    for i in range(config["test_iterations"]):
        # Simulate work
        result = sum(range(100))
        monitor.record_operation(success=True)

    metrics = monitor.stop_monitoring()

    # Assert performance criteria
    assert metrics.duration < config["timeout_seconds"]
    assert metrics.operations_per_second > config["throughput_threshold_ops"]
```

### Security Testing Fixtures

```python
@pytest.mark.security
def test_input_validation(security_scanner, security_test_config):
    \"\"\"Test input validation and security scanning.\"\"\"
    scanner = security_scanner
    config = security_test_config

    # Test various inputs
    valid_inputs = ["hello", "test@example.com", "safe_filename.txt"]
    for input_data in valid_inputs:
        result = scanner.validate_input(input_data, config["max_input_length"])
        assert result["is_valid"], f"Valid input rejected: {input_data}"

    # Test dangerous inputs
    dangerous_inputs = ["<script>alert('xss')</script>", "'; DROP TABLE users; --"]
    for input_data in dangerous_inputs:
        result = scanner.validate_input(input_data, config["max_input_length"])
        # Depending on your validation logic, adjust assertion
```

### Mock Service Fixtures

```python
@pytest.mark.integration
def test_service_integration(mock_api_clients, mock_external_services):
    \"\"\"Test service integration with mocked dependencies.\"\"\"
    # Use mock API clients
    openai_client = mock_api_clients["openai"]

    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "test"}]
    )

    assert response.choices[0].message.content == "Mock response"

    # Register custom mock services
    mock_services = mock_external_services
    custom_service = MagicMock()
    mock_services.register_service("custom", custom_service)

    service = mock_services.get_service("custom")
    assert service is custom_service
```

## 🔍 Testing Patterns

### Parametrized Testing

```python
@pytest.mark.parametrize("input_data,expected", [
    ("simple task", "simple"),
    ("complex distributed system", "complex"),
    ("urgent bug fix", "medium"),
])
@pytest.mark.unit
def test_complexity_assessment(input_data, expected):
    \"\"\"Test complexity assessment with various inputs.\"\"\"
    # Your test logic here
    pass
```

### Property-Based Testing with Hypothesis

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=1000))
@pytest.mark.unit
def test_input_handling_property(input_text):
    \"\"\"Property-based test for input handling.\"\"\"
    # Test that your function handles any valid input
    result = your_function(input_text)
    assert isinstance(result, str)
    assert len(result) > 0
```

### Async Concurrency Testing

```python
@pytest.mark.concurrency
async def test_concurrent_operations(async_performance_tester):
    \"\"\"Test concurrent operations for race conditions.\"\"\"
    tester = async_performance_tester

    async def concurrent_task(task_id):
        await asyncio.sleep(0.01)  # Simulate async work
        return f"Task {task_id} completed"

    # Run concurrent tasks
    results = await tester.run_concurrent_test(
        concurrent_task,
        concurrency=10,
        iterations=50
    )

    assert results["success_count"] == 50
    assert results["error_count"] == 0
```

### Error Injection Testing

```python
@pytest.mark.error_handling
async def test_error_handling(async_error_simulator):
    \"\"\"Test error handling with simulated failures.\"\"\"
    simulator = async_error_simulator

    # Test timeout handling
    with pytest.raises(asyncio.TimeoutError):
        await simulator.timeout_error(delay=0.1)

    # Test intermittent failures
    success_count = 0
    for _ in range(10):
        try:
            result = await simulator.intermittent_failure(success_rate=0.7)
            if result:
                success_count += 1
        except Exception:
            pass

    # Should have some successes due to 70% success rate
    assert success_count > 0
```

## 📈 Coverage and Quality Gates

### Coverage Thresholds

- Unit tests: ≥90% coverage
- Integration tests: ≥80% coverage
- Overall project: ≥85% coverage

### Performance Thresholds

- Unit test duration: <100ms each
- Integration test duration: <30s each
- Memory usage: <512MB peak
- CPU usage: <80% average

### Quality Gates

- All security scans pass
- No critical vulnerabilities
- Code style compliance (ruff, black, isort)
- Type checking compliance (mypy)

## 🔧 Configuration Files

### pytest.ini

Additional pytest configuration for special test scenarios.

### pyproject.toml [tool.pytest.ini_options]

Main pytest configuration with markers, coverage settings, and test discovery.

### ruff.toml

Code quality and style enforcement configuration.

## 🚨 CI/CD Integration

The testing infrastructure is fully integrated with GitHub Actions:

### Pre-checks Job

- Code formatting (black, isort)
- Linting (ruff)
- Type checking (mypy)
- Security scanning (bandit)

### Unit Tests Job

- Matrix testing across Python 3.10-3.13
- Coverage reporting
- Test report generation

### Integration Tests Job

- PostgreSQL service integration
- Database-dependent tests
- Service integration validation

### Security Tests Job

- Vulnerability scanning
- Input validation tests
- Dependency security checks

### Performance Tests Job

- Benchmark execution
- Performance regression detection
- Resource usage monitoring

### E2E Tests Job

- Full workflow validation
- Cross-component integration
- Real-world scenario testing

## 📝 Writing New Tests

### Test File Organization

```
tests/
├── unit/                   # Unit tests
├── integration/           # Integration tests
├── security/             # Security tests
├── performance/          # Performance tests
├── fixtures/             # Test fixtures
│   ├── async_fixtures.py
│   ├── cli_fixtures.py
│   ├── filesystem_fixtures.py
│   ├── performance_fixtures.py
│   ├── security_fixtures.py
│   └── service_fixtures.py
└── test_*.py            # Test modules
```

### Test Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `TestClassName`
- Test methods: `test_<functionality>_<scenario>`
- Fixtures: `<domain>_<purpose>_fixture`

### Best Practices

1. Use appropriate markers for test categorization
2. Keep unit tests fast (<100ms)
3. Use fixtures for setup and teardown
4. Mock external dependencies
5. Test both success and failure scenarios
6. Include edge cases and boundary conditions
7. Use descriptive test names and docstrings
8. Maintain test isolation and independence

## 🔗 Related Documentation

- [Test Architecture README](README.md)
- [CI/CD Workflows](.github/workflows/)
- [Security Testing Guidelines](security/)
- [Performance Testing Guidelines](performance/)

## 🤝 Contributing

When adding new tests:

1. Choose appropriate markers
2. Use existing fixtures when possible
3. Add new fixtures for reusable patterns
4. Update documentation for new patterns
5. Ensure CI/CD compatibility
6. Maintain test performance standards
