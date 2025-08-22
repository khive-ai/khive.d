# Test Fixtures Documentation

This directory contains comprehensive test fixtures for the KHIVE testing suite,
with specialized fixtures for orchestration testing.

## Overview

The fixture architecture follows a layered approach to support different testing
needs:

1. **Base Fixtures** (`conftest.py`) - Core async support, environment setup
2. **Service Fixtures** (`service_fixtures.py`) - Generic service mocking
3. **CLI Fixtures** (`cli_fixtures.py`) - Command-line interface testing
4. **Filesystem Fixtures** (`filesystem_fixtures.py`) - File system operations
5. **Orchestration Fixtures** (`orchestration_fixtures.py`) -
   LionOrchestrator-specific mocking

## Orchestration Testing Architecture

### Core Components

The orchestration testing architecture provides comprehensive mocking for:

- **LionAGI Dependencies**: Session, Branch, Builder, Graph, Operation
- **Claude Code Integration**: CC model creation and configuration
- **Composer Service**: Agent persona generation and system prompts
- **File System Operations**: Configuration files, workspace management
- **Async Operations**: Event loops, timeouts, concurrency patterns

### Key Fixtures

#### `mock_lionagi_session`

Mocks the LionAGI Session with:

- Session lifecycle (id, name, created_at)
- Branch management (include, lookup, get_branch)
- Flow execution with configurable results
- Default branch with messaging support

#### `mock_lionagi_branch`

Mocks individual Branch instances with:

- Branch identity (id, name)
- Message progression tracking
- Model assignment (chat_model, parse_model)
- Cloning capabilities
- Serialization (to_dict)

#### `mock_lionagi_builder`

Mocks the Builder for operation graph management:

- Operation creation and ID generation
- Graph visualization and retrieval
- Dependency tracking
- Operation metadata

#### `orchestrator_with_mocks`

Complete LionOrchestrator instance with all dependencies mocked:

- Pre-configured session and builder
- Ready for immediate testing
- Isolated from external dependencies

### Testing Patterns

#### Unit Testing Pattern

```python
def test_method(orchestrator_with_mocks):
    """Test individual orchestrator method."""
    orchestrator = orchestrator_with_mocks

    # Setup specific mocks for this test
    orchestrator.session.flow.return_value = {"result": "test"}

    # Execute method
    result = await orchestrator.run_flow()

    # Verify behavior
    assert result["result"] == "test"
    orchestrator.session.flow.assert_called_once()
```

#### Integration Testing Pattern

```python
def test_workflow(orchestrator_with_mocks, mock_create_cc, mock_composer_service):
    """Test complete workflow patterns."""
    orchestrator = orchestrator_with_mocks

    # Mock external services
    with patch("module.create_cc") as mock_cc:
        mock_cc.return_value = MagicMock()

        # Execute workflow
        result = await orchestrator.fanout(...)

        # Verify integration points
        assert isinstance(result, FanoutResponse)
```

#### Async Testing Pattern

```python
@pytest.mark.asyncio
async def test_concurrent_operations(orchestrator_with_mocks):
    """Test async concurrency patterns."""
    orchestrator = orchestrator_with_mocks

    # Setup concurrent operations
    tasks = [orchestrator.create_cc_branch(request) for request in requests]

    # Execute concurrently
    results = await asyncio.gather(*tasks)

    # Verify concurrent execution
    assert len(results) == len(requests)
```

### Coverage Goals

The orchestration testing suite targets >90% code coverage through:

1. **Method Coverage**: Every public method tested
2. **Branch Coverage**: All conditional paths tested
3. **Error Coverage**: Exception scenarios tested
4. **Integration Coverage**: Component interactions tested
5. **Async Coverage**: Concurrency patterns tested

## Usage Guidelines

### Test Organization

1. **Unit Tests** (`test_orchestrator.py`):
   - Individual method testing
   - Input validation
   - State management
   - Error handling

2. **Integration Tests** (`test_orchestrator_integration.py`):
   - Workflow patterns
   - Component interaction
   - End-to-end scenarios
   - Session management

3. **Async Tests** (`test_orchestrator_async.py`):
   - Concurrency patterns
   - Timeout handling
   - Race condition prevention
   - Performance characteristics

### Best Practices

#### Mock Strategy

- Mock at the appropriate abstraction level
- Verify mock calls to ensure correct interaction
- Use realistic mock return values
- Test both success and failure scenarios

#### Async Testing

- Always use `@pytest.mark.asyncio` for async tests
- Test timeout and cancellation scenarios
- Verify resource cleanup on exceptions
- Test concurrent access patterns

### Legacy Fixtures

- `cli_fixtures.py` - CLI testing utilities
- `filesystem_fixtures.py` - File operation mocking
- `service_fixtures.py` - Basic service mocking

#### Simple Usage Example

```python
def test_example(temp_dir, mock_subprocess):
    # Use temp_dir for file operations
    test_file = temp_dir / "test.txt"
    test_file.write_text("test")

    # Use mock_subprocess for CLI testing
    result = subprocess.run(["echo", "test"])
    assert result.returncode == 0
```
