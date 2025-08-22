# Planning Service Unit Tests - Implementation Guide

## Overview

This document describes the comprehensive unit test implementation for the khive
planning service and orchestration evaluation system. The tests cover workflow
pattern determination, external planning model integration, and consistency
validation as required by Issue 187.

## Test Architecture

### Core Test Categories

1. **Workflow Pattern Determination Tests** (`TestComplexityAssessment`,
   `TestRoleSelection`)
   - Complexity assessment algorithms
   - RAGRS complexity modifiers
   - Role selection logic
   - Phase determination
   - Heuristic pattern matching

2. **External Model Integration Tests** (`TestExternalModelIntegration`)
   - OpenAI API integration mocking
   - Cost tracking and budget awareness
   - Concurrent evaluation handling
   - Error handling and timeouts
   - Request validation

3. **Consistency Validation Tests** (`TestConsistencyValidation`)
   - Deterministic behavior verification
   - Input normalization consistency
   - Boundary condition stability
   - RAGRS modifier consistency

4. **Performance Benchmarks** (`TestPerformanceBenchmarks`)
   - Critical path performance testing
   - Memory usage stability
   - Concurrent operation handling
   - Scalability validation

5. **Pydantic Model Validation** (`TestPydanticValidation`)
   - Schema validation
   - Error handling
   - Model constraint testing

6. **Integration Tests** (`TestPlannerServiceIntegration`)
   - End-to-end workflow testing
   - Service lifecycle management
   - Error recovery testing

## Key Features Implemented

### 🎯 Workflow Pattern Determination

- **Complexity Assessment**: Tests for simple, medium, complex, and very complex
  task classification
- **Role Selection**: Validates agent role selection based on task complexity
  and phase requirements
- **RAGRS Integration**: Tests for specialized domain triggers and complexity
  modifiers
- **Boundary Testing**: Edge cases and input normalization validation

### 🔌 External Model Integration

- **OpenAI API Mocking**: Complete mock framework for testing without real API
  calls
- **Cost Tracking**: Integration with cost tracking system and budget
  constraints
- **Concurrent Evaluation**: Multi-agent evaluation with proper error handling
- **Timeout Management**: Graceful handling of API timeouts and failures

### ✅ Consistency Validation

- **Deterministic Testing**: Ensures identical inputs produce identical outputs
- **Heuristic Stability**: Validates that heuristic-based assessments are stable
- **Input Normalization**: Tests various input formats produce consistent
  results
- **Session Management**: Consistent artifact registry structure validation

### ⚡ Performance Requirements

- **Critical Path Benchmarks**:
  - Complexity assessment: <0.5ms per call
  - Role selection: <1ms per call
  - Session creation: <5ms per session
  - Phase determination: <0.5ms per call
- **Memory Stability**: <50MB growth during 1000 operations
- **Concurrent Performance**: Handle 100+ concurrent operations efficiently

## Test Coverage Goals

- **Target Coverage**: >90% for planning modules
- **Critical Components**: 100% coverage for core algorithms
- **Integration Points**: Complete testing of external dependencies
- **Error Paths**: Comprehensive error handling validation

## File Structure

```
tests/
├── test_planning_service.py          # Main comprehensive test suite
├── fixtures/
│   ├── planning_fixtures.py          # Test fixtures and mock objects
│   ├── cli_fixtures.py              # CLI testing fixtures
│   └── service_fixtures.py          # Service-level fixtures
├── conftest.py                       # Global test configuration
├── README_planning_tests.md          # This documentation
└── run_planning_tests.py            # Comprehensive test runner

pytest.ini                           # Pytest configuration
coverage.json                        # Coverage report (generated)
htmlcov/                             # HTML coverage reports (generated)
```

## Mock Framework

### MockDecisionMatrix

Provides consistent test data for complexity assessment rules, role selection
matrices, and RAGRS domain triggers.

### MockOpenAIResponse

Simulates OpenAI API responses with configurable evaluation data for testing
external model integration.

### Fixture System

- **Deterministic fixtures**: Ensure consistent test behavior
- **Workspace management**: Temporary directories for session testing
- **Parameterized scenarios**: Comprehensive test case coverage

## Running Tests

### Quick Start

```bash
# Run all planning service tests
pytest tests/test_planning_service.py -v

# Run specific test category
pytest tests/test_planning_service.py -m unit -v
pytest tests/test_planning_service.py -m integration -v
pytest tests/test_planning_service.py -m performance -v
```

### Comprehensive Test Suite

```bash
# Run the comprehensive test runner
python run_planning_tests.py
```

### Coverage Analysis

```bash
# Generate detailed coverage report
pytest tests/test_planning_service.py --cov=khive.services.plan --cov-report=html
```

### Performance Benchmarking

```bash
# Run only performance benchmarks
pytest tests/test_planning_service.py -m benchmark --benchmark-only
```

## Test Categories and Markers

- `@pytest.mark.unit`: Unit tests for individual components
- `@pytest.mark.integration`: Integration tests across components
- `@pytest.mark.performance`: Performance and benchmark tests
- `@pytest.mark.benchmark`: Tests with timing assertions
- `@pytest.mark.asyncio`: Async function testing
- `@pytest.mark.parametrize`: Parameterized test scenarios

## Key Test Scenarios

### Complexity Assessment Validation

```python
@pytest.mark.parametrize("request_text,expected_tier", [
    ("single objective well defined scope", ComplexityTier.SIMPLE),
    ("multiple objectives some unknowns", ComplexityTier.MEDIUM),
    ("many stakeholders high uncertainty", ComplexityTier.COMPLEX),
    ("research frontier multiple disciplines", ComplexityTier.VERY_COMPLEX),
])
def test_complexity_assessment_patterns(request_text, expected_tier):
    # Test implementation validates complexity assessment logic
```

### Consistency Validation

```python
def test_complexity_assessment_determinism(deterministic_planner, request_text):
    """Test that complexity assessment is completely deterministic."""
    results = [planner.assess(Request(request_text)) for _ in range(10)]
    assert all(result == results[0] for result in results)
```

### Performance Benchmarking

```python
@pytest.mark.benchmark
def test_complexity_assessment_performance(benchmark_planner):
    """Benchmark complexity assessment for various request types."""
    avg_time = measure_performance(benchmark_planner.assess, iterations=1000)
    assert avg_time < 0.0005  # <0.5ms requirement
```

## Expected Results

### Test Metrics

- **Total Tests**: ~150+ test cases
- **Coverage**: >90% for planning service modules
- **Performance**: All benchmarks pass timing requirements
- **Consistency**: 100% deterministic behavior validation

### Success Criteria

✅ All workflow pattern determination algorithms tested and validated\
✅ External model integration properly mocked and tested\
✅ Consistency validation ensures deterministic results\
✅ Performance benchmarks meet critical path requirements\
✅ >90% code coverage achieved\
✅ Error handling and edge cases covered

## Maintenance and Extension

### Adding New Tests

1. Create test methods following naming convention:
   `test_<functionality>_<scenario>`
2. Use appropriate pytest markers for categorization
3. Add fixtures to `planning_fixtures.py` for reusable mock data
4. Update this documentation with new test scenarios

### Performance Benchmarks

- Add new benchmarks to `TestPerformanceBenchmarks` class
- Use `@pytest.mark.benchmark` marker
- Set realistic performance thresholds based on requirements
- Include memory usage validation for long-running operations

### Mock Updates

- Update `MockDecisionMatrix` when decision matrix schema changes
- Extend `MockOpenAIResponse` for new evaluation fields
- Add new fixtures for additional external dependencies

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `khive` package is installed with
   `pip install -e .`
2. **Async Test Failures**: Check `pytest-asyncio` is installed and
   `asyncio_mode = auto` is set
3. **Coverage Issues**: Verify source paths in `pytest.ini` match project
   structure
4. **Performance Test Failures**: Adjust timing thresholds based on hardware
   capabilities

### Debug Mode

```bash
# Run tests with detailed output
pytest tests/test_planning_service.py -v -s --tb=long

# Run specific failing test
pytest tests/test_planning_service.py::TestClass::test_method -vvv
```

## Integration with CI/CD

The test suite is designed for integration with continuous integration systems:

```yaml
# Example GitHub Actions workflow
- name: Run Planning Service Tests
  run: |
    pip install -e .
    pip install pytest pytest-asyncio pytest-cov
    python run_planning_tests.py

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.json
```

This comprehensive test implementation ensures the planning service meets all
reliability, performance, and consistency requirements for production
deployment.
