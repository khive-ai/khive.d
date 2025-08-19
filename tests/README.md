# Khive Testing Guide

## Quick Start

Run all tests:
```bash
uv run pytest
```

Run specific test categories:
```bash
# Fast unit tests only
uv run pytest tests/unit/ -v

# Integration tests 
uv run pytest tests/integration/ -v

# Performance tests
uv run pytest tests/performance/ -v

# Skip slow tests for quick feedback
uv run pytest -m "not slow"
```

## Test Structure

```
tests/
├── unit/              # Fast, isolated unit tests  
├── integration/       # Integration tests with dependencies
├── e2e/              # End-to-end workflow tests
├── performance/      # Basic performance validation
├── fixtures/         # Shared test fixtures
└── conftest.py       # Global test configuration
```

## Writing Tests

### Unit Tests
- Fast (< 1 second each)
- No external dependencies
- Test individual functions/classes
- Mark with `@pytest.mark.unit`

```python
@pytest.mark.unit
def test_basic_functionality():
    from khive.cli import khive_cli
    assert hasattr(khive_cli, 'main')
```

### Integration Tests  
- Test component interactions
- May use mocks for external services
- Mark with `@pytest.mark.integration`

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_service_integration(mock_openai_client):
    # Test service coordination
    pass
```

## Coverage

Current baseline: 18% (established baseline)
Short-term target: 30% (achievable with core logic tests)
- Run coverage: `uv run pytest --cov=src/khive`
- View HTML report: `open htmlcov/index.html`

## Useful Commands

```bash
# Run tests with coverage
uv run pytest --cov=src/khive --cov-report=html

# Run only failed tests from last run
uv run pytest --lf  

# Run tests matching pattern
uv run pytest -k "test_cli"

# Run tests in parallel (if needed)
uv run pytest -n auto
```

## Best Practices

1. **Start Simple**: Write basic tests first, add complexity gradually
2. **Fast Feedback**: Keep unit tests under 1 second each  
3. **Realistic Mocks**: Mock external APIs, use real internal logic
4. **Clear Names**: Test names should describe what they validate
5. **Focused Tests**: One concept per test

## Troubleshooting

**Import Errors**: Make sure you have `uv sync` installed dependencies

**Async Test Issues**: Use `@pytest.mark.asyncio` for async tests

**Coverage Too Low**: Add unit tests for core business logic first

**Tests Too Slow**: Move expensive operations to `@pytest.mark.slow` tests