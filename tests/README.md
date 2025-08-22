# Test Architecture for Orchestration Evaluation System

This directory contains a comprehensive test architecture for the orchestration
evaluation and planning system, designed to ensure reliability, maintainability,
and extensibility.

## 🚀 Quick Start

```bash
# All tests
uv run pytest

# With coverage and verbose output
uv run pytest -v --cov=khive.services.plan --cov-report=html

# Stop after first failure
uv run pytest -x

# Run specific test categories
uv run pytest -m unit          # Unit tests only
uv run pytest -m integration   # Integration tests only
uv run pytest -m performance   # Performance tests only
```

## 📁 Test Architecture Structure

```
tests/
├── README.md                           # This file - test architecture overview
├── conftest.py                         # Global test configuration and fixtures
├── test_config.py                      # Test configuration, constants, and patterns
├── test_orchestration_evaluation.py    # Main test suite for orchestration evaluation
├── fixtures/
│   ├── __init__.py
│   ├── planning_fixtures.py           # Planning service test fixtures
│   ├── orchestration_fixtures.py      # Orchestration system fixtures
│   ├── cli_fixtures.py               # CLI testing fixtures
│   ├── service_fixtures.py           # Service layer fixtures
│   └── filesystem_fixtures.py        # File system mocking fixtures
├── mocks/
│   ├── __init__.py
│   └── external_models.py             # External API mocking framework
├── validation/
│   ├── __init__.py
│   └── pydantic_validators.py         # Pydantic model validation patterns
└── test_*.py                          # Individual test modules
```

## 🎯 Testing Philosophy

### Design Principles

1. **Comprehensive Coverage**: Target >90% code coverage for planning modules
2. **Realistic Simulation**: Mock external services with realistic behavior
   patterns
3. **Maintainable Patterns**: Reusable fixtures and validation patterns
4. **Performance Validation**: Test performance characteristics under load
5. **Error Resilience**: Comprehensive error injection and recovery testing

### Test Categories

- **Unit Tests** (`@pytest.mark.unit`): Individual component validation
- **Integration Tests** (`@pytest.mark.integration`): End-to-end workflow
  validation
- **Performance Tests** (`@pytest.mark.performance`): Load, latency, and
  resource usage validation
- **Regression Tests** (`@pytest.mark.regression`): Prevent known issues from
  reoccurring

## 🧪 Key Test Components

### 1. Planning Service Test Fixtures (`fixtures/planning_fixtures.py`)

Comprehensive fixtures for testing the orchestration evaluation system:

```python
# Example usage
def test_complexity_assessment(mock_decision_matrix, complexity_scenarios):
    for request_text, expected_complexity in complexity_scenarios:
        # Test complexity assessment logic
        pass
```

**Key Fixtures:**

- `mock_decision_matrix`: Configurable decision matrix for testing
- `sample_orchestration_evaluation`: Valid evaluation model instances
- `complexity_scenarios`: Parameterized complexity test cases
- `mock_openai_client`: External API mocking
- `integration_test_scenarios`: End-to-end test scenarios

### 2. External Model Mocking (`mocks/external_models.py`)

Sophisticated mocking framework for external planning models:

```python
# Create realistic OpenAI client mock
mock_client = MockOpenAIClient(MockResponseConfig(
    base_latency_ms=500,
    success_rate=0.95,
    complexity_variation=True
))

# Simulate concurrent evaluations
evaluator = MockMultiAgentEvaluator()
results = await evaluator.evaluate_with_all_agents(request)
```

**Features:**

- Realistic latency and failure simulation
- Cost tracking and budget validation
- Multi-agent evaluation scenarios
- Adaptive behavior based on request patterns

### 3. Pydantic Validation Patterns (`validation/pydantic_validators.py`)

Comprehensive validation utilities for all Pydantic models:

```python
# Validate model constraints
OrchestrationEvaluationValidator.test_field_constraints()

# Cross-model consistency validation
issues = CrossModelValidator.validate_evaluation_consistency(evaluation)

# Complete workflow validation
issues = ComprehensiveModelValidator.validate_full_orchestration_workflow()
```

## 📊 Test Coverage Targets

| Component             | Target Coverage | Focus Areas                                             |
| --------------------- | --------------- | ------------------------------------------------------- |
| `planner_service.py`  | ≥95%            | Complexity assessment, role selection, evaluation logic |
| `models.py`           | ≥90%            | Pydantic model validation and constraints               |
| `parts.py`            | ≥90%            | Data structures and enums                               |
| `cost_tracker.py`     | ≥85%            | Budget tracking and cost calculation                    |
| External integrations | ≥80%            | API mocking and error handling                          |

## 🚀 Running Tests

### Environment Setup

```bash
# Test configuration
export KHIVE_TEST_MODE=true
export KHIVE_DISABLE_EXTERNAL_APIS=true
export OPENAI_API_KEY=test_key_for_mocking
```

### Test Execution

```bash
# All tests with coverage
uv run pytest --cov=khive.services.plan --cov-report=html --cov-report=term-missing

# Specific test categories
uv run pytest -m unit          # Fast unit tests
uv run pytest -m integration   # Integration tests
uv run pytest -m performance   # Performance tests
uv run pytest -m regression    # Regression tests

# Parallel execution
uv run pytest -n auto          # Use all CPU cores

# Stop on first failure
uv run pytest -x

# Verbose output
uv run pytest -v

# Open coverage report
open htmlcov/index.html
```

## ✍️ Writing New Tests

### Test Naming Conventions

```python
class TestComplexityAssessment:
    """Test class for complexity assessment functionality."""

    def test_simple_task_assessment(self):
        """Test complexity assessment for simple tasks."""
        pass

    def test_ragrs_modifier_application(self):
        """Test RAGRS complexity modifier application."""
        pass

    @pytest.mark.parametrize("request,expected", test_cases)
    def test_parametric_complexity_assessment(self, request, expected):
        """Parametric test for various complexity scenarios."""
        pass
```

### Mock Usage Patterns

```python
# Use realistic mocks
@pytest.fixture
def realistic_openai_mock():
    config = MockResponseConfig(
        base_latency_ms=500,
        success_rate=0.95,
        token_variance=0.2
    )
    return MockOpenAIClient(config)

# Test with error injection
def test_api_error_handling(unreliable_mock):
    with patch("khive.services.plan.planner_service.OpenAI") as mock_class:
        mock_class.return_value = unreliable_mock
        # Test error resilience
```

### Validation Testing

```python
def test_model_validation():
    """Test Pydantic model validation."""
    # Valid case
    data = OrchestrationEvaluationValidator.create_valid_data()
    evaluation = OrchestrationEvaluation.model_validate(data)

    # Invalid case
    invalid_data = data.copy()
    invalid_data["total_agents"] = -1

    with pytest.raises(ValidationError) as exc_info:
        OrchestrationEvaluation.model_validate(invalid_data)

    assert "total_agents" in str(exc_info.value)
```

## 🔍 Available Fixtures

### Core Fixtures (from `conftest.py`)

- `temp_dir`: Temporary directory for test files
- `mock_env`: Mock environment variables
- `sample_project_dir`: Sample project structure
- `mock_subprocess`: Mock subprocess calls
- `cli_runner`: CLI testing utilities

### Planning Service Fixtures (from `planning_fixtures.py`)

- `mock_decision_matrix`: Decision matrix configuration
- `sample_evaluation`: Valid OrchestrationEvaluation instance
- `complexity_scenarios`: Parameterized complexity test cases
- `mock_openai_client`: External API mocking
- `performance_test_config`: Performance testing configuration

### Mock Framework Fixtures (from `mocks/external_models.py`)

- `high_performance_mock`: Optimized mock for performance testing
- `unreliable_mock`: Mock for error handling testing
- `cost_tracking_mock`: Mock for budget testing
- `multi_agent_evaluator`: Multi-agent evaluation scenarios

## 🎭 Example Test Scenarios

### Complexity Assessment Testing

```python
@pytest.mark.parametrize("test_case", TestDataSets.COMPLEXITY_CASES)
def test_complexity_assessment(test_case, mock_decision_matrix):
    """Test complexity assessment accuracy."""
    request = Request(test_case.request_text)
    planner = create_planner_with_matrix(mock_decision_matrix)

    complexity = planner.assess(request)
    assert complexity == test_case.expected_complexity

    # Validate agent count range
    min_agents, max_agents = test_case.expected_agents_range
    roles = planner.select_roles(request, complexity)
    assert min_agents <= len(roles) <= max_agents
```

### Performance Testing

```python
@pytest.mark.performance
async def test_concurrent_evaluations(multi_agent_evaluator):
    """Test concurrent evaluation performance."""
    request = "Build distributed consensus system"

    start_time = time.time()
    results = await multi_agent_evaluator.evaluate_with_all_agents(request)
    duration = time.time() - start_time

    # Validate performance
    assert duration < 5.0, f"Evaluation took too long: {duration}s"

    # Validate results consistency
    successful = [r for r in results if r.get("success")]
    assert len(successful) >= 3, "Insufficient successful evaluations"
```

## 🔧 Debugging and Troubleshooting

### Common Issues

1. **Flaky Tests**: Use proper isolation and deterministic mocks
2. **Mock Inconsistencies**: Ensure mocks match real API behavior
3. **Timeout Issues**: Adjust timeout configurations in test config
4. **Coverage Gaps**: Use coverage reports to identify untested code paths

### Debug Utilities

```python
# Enable debug logging in tests
import logging
logging.basicConfig(level=logging.DEBUG)

# Capture test artifacts for inspection
def test_with_artifacts(tmp_path):
    result = run_orchestration_evaluation()

    # Save artifacts
    with open(tmp_path / "evaluation_result.json", "w") as f:
        json.dump(result, f, indent=2)

    assert result["success"]
```

## 📈 CI/CD Integration

Tests run automatically on:

- Pull requests to main branch
- Pushes to main branch

**Pipeline Steps:**

1. Code linting (ruff)
2. Code formatting check (ruff)
3. Tests with coverage (target: >90% for planning modules)
4. Coverage report upload
5. Performance regression detection

**Quality Gates:**

- **Coverage**: Minimum 90% for planning modules
- **Performance**: All tests complete within 60 seconds
- **Reliability**: >95% test success rate in CI

## 🔮 Contributing Guidelines

### Test Requirements

1. **Test First**: Write tests before implementing features
2. **Clear Names**: Use descriptive test and fixture names
3. **Focused Tests**: Each test should verify one specific behavior
4. **Proper Isolation**: Tests should not depend on each other
5. **Documentation**: Include docstrings explaining test purpose

### Review Checklist

- [ ] Tests cover happy path and error cases
- [ ] Mocks are realistic and maintainable
- [ ] Performance tests include appropriate thresholds
- [ ] Integration tests verify end-to-end workflows
- [ ] Validation tests cover all model constraints
- [ ] Documentation is clear and accurate

---

This test architecture provides a robust foundation for validating the
orchestration evaluation system with comprehensive coverage, realistic
simulation, and maintainable patterns.
