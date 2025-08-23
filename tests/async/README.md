# Async and Concurrency Testing

This directory contains comprehensive tests for async operations and concurrency
patterns in the khive system, implementing all requirements from issue #193.

## Test Organization

### Core Test Files

- **`test_async_operations.py`** - Core async reliability patterns
  - `TestAsyncReliabilityPatterns` - Concurrent operation isolation, timeout
    cascade prevention, graceful cancellation
  - `TestTimeoutScenarios` - Timeout handling with fallbacks, nested calls,
    partial results
  - `TestCancellationPatterns` - Structured cancellation propagation, async
    context managers, selective shielding
  - `TestAsyncResourceManagement` - Resource pools, lock contention, memory
    management

- **`test_concurrency_patterns.py`** - Multi-agent coordination and race
  detection
  - `TestMultiAgentCoordination` - Concurrent branch creation, session state
    consistency, resource contention
  - `TestRaceConditionDetection` - Branch naming races, shared data structure
    races
  - `TestDeadlockPrevention` - Circular dependency prevention, resource ordering
  - `TestThreadSafetyValidation` - Session modification safety, context manager
    thread safety
  - `TestConcurrencyErrorHandling` - Partial failure handling in concurrent
    operations
  - `TestConcurrencyPerformance` - Throughput testing, memory efficiency

- **`test_resource_management.py`** - Resource lifecycle and memory management
  - `TestAsyncResourceLifecycle` - Basic cleanup, exception handling, multiple
    resource coordination
  - `TestMemoryLeakDetection` - Memory monitoring, leak detection, service
    integration
  - `TestConcurrentResourceManagement` - Concurrent creation/cleanup, resource
    isolation
  - `TestResourceTimeoutHandling` - Cleanup on timeout, cancellation cleanup
  - `TestRaceConditionDetection` - File resource race conditions
  - `TestServiceResourceIntegration` - SessionManager and CacheService
    integration
  - `TestFileHandleManagement` - File handle leak prevention

### Supporting Infrastructure

- **`conftest.py`** - Shared fixtures and configuration for async tests
- **`tests/fixtures/async/async_fixtures.py`** - Comprehensive async testing
  fixtures
- **`tests/fixtures/async/__init__.py`** - Fixture module initialization

## Testing Requirements Coverage

✅ **1. Async method behavior validation tests**

- Concurrent operation isolation
- Timeout cascade prevention
- Graceful cancellation with cleanup
- Backpressure handling patterns

✅ **2. Concurrent execution scenario testing**

- Multi-agent coordination patterns
- Concurrent branch creation safety
- Resource pool contention management
- Performance throughput testing

✅ **3. Thread safety and race condition detection**

- Branch naming race detection
- Shared data structure races
- Session modification safety
- Context manager thread safety

✅ **4. Timeout and cancellation mechanism tests**

- Operation timeout with fallback
- Nested call timeout inheritance
- Structured cancellation propagation
- Resource cleanup on timeout/cancellation

✅ **5. Resource management and cleanup verification**

- Async resource lifecycle management
- Memory leak detection and monitoring
- File handle management
- Service resource integration

✅ **6. Error handling in async contexts validation**

- Partial failure handling
- Exception propagation in concurrent scenarios
- Recovery patterns
- Error isolation

✅ **7. Performance testing for concurrent operations**

- Agent throughput benchmarking
- Memory efficiency under concurrency
- Lock contention performance
- Resource usage optimization

## Test Execution

### Running All Async Tests

```bash
# Run all async tests
uv run pytest tests/async/

# Run with specific markers
uv run pytest -m "async_test"
uv run pytest -m "concurrency"
uv run pytest -m "resource_cleanup"
```

### CI/CD Integration

The enhanced CI/CD pipeline includes:

- **`async-concurrency-tests`** job with matrix strategy for different test
  types
- **`integration-async-tests`** job for integration scenarios
- **`performance-async-tests`** job for performance benchmarking
- Proper timeout handling (20-30 minutes per job)
- Parallel test execution with pytest-xdist
- Comprehensive coverage reporting

### Test Markers

- `async_test` - Basic async patterns
- `concurrency` - Thread safety validation
- `timeout_handling` - Cancellation scenarios
- `race_condition` - Data consistency testing
- `deadlock` - Prevention verification
- `resource_cleanup` - Lifecycle management
- `performance` - Benchmarking tests

## Performance Benchmarks

Default performance thresholds:

- Max operation duration: 1.0 seconds
- Max concurrent operations: 100
- Max memory increase: 20.0 MB
- Min operations per second: 50
- Max error rate: 5%

## Architecture Integration

These tests validate the async/concurrency behavior of:

- **LionOrchestrator** - Multi-agent coordination
- **SessionManager** - Session lifecycle management
- **CacheService** - Async caching operations
- **Branch Management** - Concurrent branch operations
- **Resource Pools** - Shared resource management

## Key Testing Patterns

1. **Isolation Testing** - Ensures failures don't cascade
2. **Timeout Cascade Prevention** - Maintains system responsiveness
3. **Graceful Degradation** - Handles partial failures elegantly
4. **Resource Cleanup Verification** - Prevents memory/handle leaks
5. **Race Condition Detection** - Identifies concurrency issues
6. **Deadlock Prevention** - Ensures system never hangs
7. **Performance Validation** - Maintains acceptable performance characteristics

This comprehensive testing infrastructure provides confidence in the async
reliability and concurrency safety of the khive orchestration system.
