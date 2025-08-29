# Comprehensive Testing Guide for Khive

This guide provides complete information on using the khive testing
infrastructure for reliable, comprehensive testing across all domains.

## 🚀 Quick Start

```bash
# Install test dependencies
uv sync --group dev

# Run all tests
uv run pytest

# Run specific test types
uv run pytest -m "unit"              # Unit tests only
uv run pytest -m "integration"       # Integration tests only
uv run pytest -m "security"         # Security tests only
uv run pytest -m "performance"      # Performance benchmarks

# Run with coverage
uv run pytest --cov=src/khive --cov-report=html
```

## 📋 Test Categories and Markers

### Core Test Types

- `@pytest.mark.unit` - Fast unit tests (<100ms)
- `@pytest.mark.integration` - Integration tests with dependencies
- `@pytest.mark.e2e` - End-to-end integration tests
- `@pytest.mark.smoke` - Basic functionality smoke tests
- `@pytest.mark.regression` - Regression tests for known bug fixes

### Domain-Specific Testing

- `@pytest.mark.cli` - Command-line interface tests
- `@pytest.mark.api` - API endpoint and service tests
- `@pytest.mark.database` - Database integration tests
- `@pytest.mark.filesystem` - File system operation tests
- `@pytest.mark.network` - Network communication tests

### Quality Assurance

- `@pytest.mark.security` - Security validation and vulnerability tests
- `@pytest.mark.performance` - Performance benchmark tests
- `@pytest.mark.load` - Load testing with high volume
- `@pytest.mark.stress` - Stress testing under extreme conditions
- `@pytest.mark.memory` - Memory usage and leak detection tests

### Agent System Testing

- `@pytest.mark.agent_composition` - Agent composition and configuration tests
- `@pytest.mark.orchestration` - Multi-agent orchestration workflow tests
- `@pytest.mark.planning` - Planning algorithm and strategy tests
- `@pytest.mark.workflow` - Workflow execution and coordination tests

### MCP Protocol Testing

- `@pytest.mark.mcp_protocol` - MCP protocol compliance tests
- `@pytest.mark.mcp_transport` - MCP transport reliability tests
- `@pytest.mark.mcp_lifecycle` - MCP server lifecycle management tests

## 🏗️ Test Infrastructure Architecture

```
tests/
├── fixtures/              # Centralized fixture management
│   ├── agent_fixtures.py      # Agent composition fixtures
│   ├── security_fixtures.py   # Security testing fixtures
│   ├── performance_fixtures.py # Performance testing fixtures
│   └── ...
├── mocks/                 # Sophisticated mocking framework
│   ├── api_mocks.py           # OpenAI and external API mocks
│   ├── database_mocks.py      # Database mocking utilities
│   └── ...
├── utils/                 # Testing utilities and helpers
│   ├── test_data.py           # Test data factories
│   ├── validators.py          # Validation utilities
│   └── helpers.py            # Test execution helpers
├── security/              # Security-specific tests
├── performance/           # Performance benchmarks
├── integration/           # Integration tests
├── e2e/                  # End-to-end tests
└── reports/              # Generated test reports
```

## 🧪 Writing Effective Tests

### Unit Test Example

```python
import pytest
from khive.services.composition.agent_composer import AgentComposer

@pytest.mark.unit
@pytest.mark.agent_composition
async def test_agent_composition_basic(agent_composer_fixture, mock_agent_request):
    """Test basic agent composition functionality."""
    composer = agent_composer_fixture
    request = mock_agent_request

    result = await composer.compose_agent(request)

    assert result["persona"] is not None
    assert "capabilities" in result
    assert len(result["capabilities"]) > 0
```

### Security Test Example

```python
import pytest
from khive.security.validation import validate_input_security

@pytest.mark.security
@pytest.mark.input_validation
def test_sql_injection_prevention(security_test_cases, malicious_payloads):
    """Test prevention of SQL injection attacks."""
    sql_payloads = malicious_payloads["sql_injection"]

    for payload in sql_payloads:
        with pytest.raises(SecurityValidationError):
            validate_input_security(payload, field_type="context")
```

### Performance Test Example

```python
import pytest
from tests.fixtures.performance_fixtures import PerformanceMetrics

@pytest.mark.performance
@pytest.mark.benchmark
def test_agent_composition_performance(performance_monitor, benchmark_config):
    """Test agent composition performance meets requirements."""
    config = benchmark_config["agent_composition"]

    with performance_monitor() as monitor:
        # Execute performance-critical operation
        for _ in range(config["iterations"]):
            result = compose_test_agent()

    metrics = monitor.get_metrics()

    assert metrics.execution_time_ms < config["max_acceptable_ms"]
    assert metrics.memory_usage_mb < config["memory_limit_mb"]
```

### Integration Test Example

```python
import pytest

@pytest.mark.integration
@pytest.mark.orchestration
@pytest.mark.asyncio
async def test_full_orchestration_workflow(orchestration_scenarios):
    """Test complete orchestration workflow from request to completion."""
    scenario = orchestration_scenarios["complex_system"]

    # Create orchestration request
    request = OrchestrationRequest(
        description=scenario["description"],
        complexity=scenario["complexity"]
    )

    # Execute orchestration
    result = await orchestrator.execute_workflow(request)

    # Verify results
    assert result.success is True
    assert len(result.agents_created) == scenario["expected_agents"]
    assert all(role in result.roles_used for role in scenario["expected_roles"])
```

## 🔒 Security Testing

### Input Validation Testing

```python
@pytest.mark.security
@pytest.mark.parametrize("field,invalid_input", [
    ("role", "'; DROP TABLE users; --"),
    ("domain", "../../../etc/passwd"),
    ("context", "<script>alert('XSS')</script>"),
])
def test_input_validation_prevents_attacks(field, invalid_input):
    """Test input validation prevents common attacks."""
    with pytest.raises(ValidationError):
        validate_field_input(field, invalid_input)
```

### OWASP Top 10 Compliance Testing

```python
@pytest.mark.security
@pytest.mark.parametrize("owasp_category", [
    "A01_broken_access_control",
    "A02_cryptographic_failures",
    "A03_injection",
    # ... other OWASP categories
])
def test_owasp_compliance(owasp_category, security_compliance_checks):
    """Test compliance with OWASP Top 10 security standards."""
    test_cases = security_compliance_checks["owasp_top_10"][owasp_category]

    for test_case in test_cases:
        # Execute security validation
        result = execute_security_test(test_case)
        assert result.is_secure is True
```

## 📊 Performance Testing

### Benchmark Testing

```python
@pytest.mark.performance
def test_agent_creation_benchmark(benchmark):
    """Benchmark agent creation performance."""
    result = benchmark(create_agent_with_default_config)

    # Assertions are handled by pytest-benchmark
    assert result is not None
```

### Load Testing

```python
@pytest.mark.load
@pytest.mark.asyncio
async def test_concurrent_agent_creation_load(load_test_scenarios):
    """Test system behavior under concurrent agent creation load."""
    scenario = load_test_scenarios["heavy_load"]

    # Execute load test
    results = await run_load_test(
        target_function=create_agent,
        concurrent_users=scenario["concurrent_users"],
        duration_seconds=scenario["test_duration"]
    )

    # Validate load test results
    assert results["error_rate"] < 0.05  # Less than 5% errors
    assert results["avg_response_time"] < 2.0  # Under 2 seconds
```

### Memory Profiling

```python
@pytest.mark.memory
def test_memory_usage_agent_composition(memory_profiler):
    """Test memory usage during agent composition."""
    memory_profiler.start_profiling()

    # Execute memory-intensive operations
    agents = []
    for _ in range(100):
        agent = create_test_agent()
        agents.append(agent)

    memory_stats = memory_profiler.stop_profiling()

    # Check for memory leaks
    leaks = memory_profiler.detect_leaks(threshold_mb=10.0)
    assert len(leaks) == 0, f"Memory leaks detected: {leaks}"
```

## 🔧 Test Fixtures and Utilities

### Using Agent Composition Fixtures

```python
def test_agent_with_custom_scenario(agent_composition_scenarios):
    """Test agent composition with predefined scenarios."""
    scenario = agent_composition_scenarios[0]  # "simple_researcher"

    request = ComposerRequest(
        role=scenario["role"],
        domain=scenario["domain"],
        context=scenario["context"]
    )

    result = compose_agent(request)

    # Validate against expected capabilities
    for capability in scenario["expected_capabilities"]:
        assert capability in result["capabilities"]
```

### Mock External Services

```python
def test_with_openai_mock(create_realistic_openai_response):
    """Test functionality with realistic OpenAI API mock."""
    mock_client = create_realistic_openai_response(
        prompt="Test prompt",
        success_rate=0.95
    )

    # Use mock client in test
    with patch('openai.OpenAI', return_value=mock_client):
        result = call_openai_dependent_function()

    assert result is not None

    # Check API metrics
    metrics = mock_client.get_metrics()
    assert metrics.total_requests > 0
```

## 🎯 CI/CD Integration

### Test Execution in CI

The GitHub Actions workflow runs tests in multiple stages:

1. **Pre-checks** - Linting, formatting, type checking, security scanning
2. **Unit Tests** - Fast unit tests across Python versions
3. **Integration Tests** - Integration tests with database services
4. **Security Tests** - Vulnerability and security compliance testing
5. **Performance Tests** - Performance benchmarks and regression detection
6. **E2E Tests** - Full end-to-end workflow testing

### Coverage Requirements

- **Unit tests**: >90% coverage required
- **Integration tests**: >85% coverage for critical paths
- **Overall**: >85% combined coverage to pass CI

### Test Reports

All test runs generate comprehensive reports:

- **HTML reports**: `tests/reports/test-report.html`
- **JSON reports**: `tests/reports/test-report.json`
- **Coverage reports**: `htmlcov/index.html`
- **Performance reports**: `performance-results.json`

## 🐛 Debugging Test Failures

### Common Issues and Solutions

1. **Flaky Tests**
   ```python
   # Use proper isolation and deterministic mocks
   @pytest.mark.flaky(reruns=3)
   def test_potentially_flaky_operation():
       pass
   ```

2. **Async Test Issues**
   ```python
   # Ensure proper async test setup
   @pytest.mark.asyncio
   async def test_async_operation():
       # Use asyncio.wait_for for timeouts
       result = await asyncio.wait_for(async_operation(), timeout=5.0)
   ```

3. **Mock Inconsistencies**
   ```python
   # Ensure mocks match real API behavior
   @pytest.fixture
   def realistic_mock():
       mock = create_realistic_openai_response(
           prompt="test",
           success_rate=0.95,
           complexity="moderate"
       )
       return mock
   ```

### Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

def test_with_debug_logging():
    """Test with debug logging enabled."""
    logger = logging.getLogger(__name__)
    logger.debug("Debug information for test troubleshooting")
```

## 📈 Best Practices

### Test Organization

- Group related tests in classes
- Use descriptive test names that explain intent
- Keep tests focused on single functionality
- Use parametrized tests for multiple scenarios

### Test Data Management

- Use factories for creating test data
- Keep test data minimal and focused
- Use fixtures for reusable test setup
- Clean up test data after tests complete

### Performance Considerations

- Mark slow tests appropriately
- Use `pytest-xdist` for parallel execution
- Profile tests to identify bottlenecks
- Set appropriate timeouts for async operations

### Security Testing

- Test all input validation paths
- Include boundary condition testing
- Test error handling and edge cases
- Validate secure coding patterns

### Maintenance

- Update tests when behavior changes
- Remove obsolete tests regularly
- Keep fixtures and utilities up to date
- Monitor test execution times and optimize slow tests

## 🔗 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Python Security Testing](https://bandit.readthedocs.io/)

This comprehensive testing guide ensures reliable, secure, and performant
testing across the entire khive ecosystem.
