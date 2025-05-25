# Implementation Plan: Fix CI Test Failures for FastMCP Integration

**Issue:** #152  
**Date:** 2025-01-24  
**Implementer:** @khive-implementer

## Problem Analysis

The CI tests are failing because:
1. Tests still import and mock the old `MCPClient` class
2. The new `FastMCPClient` has a different interface (uses `stdio_client` from fastmcp)
3. Mock patterns need to be updated to match FastMCP's async patterns
4. Test isolation is broken - tests may be trying to connect to real MCP servers

## Implementation Strategy

### Phase 1: Update Test Imports and Mocks

1. **Update `tests/adapters/test_mcp_adapters.py`**:
   - Replace `MCPClient` mocks with `FastMCPClient` mocks
   - Mock `fastmcp.stdio_client` instead of the client class
   - Update mock return values to match FastMCP's response format

2. **Update `tests/cli/test_khive_mcp.py`**:
   - Replace `get_mcp_client` mocks with appropriate FastMCP mocks
   - Ensure test isolation by mocking at the right level

### Phase 2: Fix Mock Patterns

1. **FastMCP Client Creation**:
   ```python
   # Old pattern:
   mock_client = AsyncMock()
   mock_client.connect.return_value = True
   
   # New pattern:
   mock_client = AsyncMock()
   mock_stdio_client = AsyncMock(return_value=mock_client)
   ```

2. **Tool Listing**:
   ```python
   # FastMCP returns tools differently
   mock_client.list_tools.return_value = [...]  # Update format
   ```

3. **Tool Calling**:
   ```python
   # FastMCP call_tool interface
   mock_client.call_tool.return_value = {...}  # Update format
   ```

### Phase 3: Ensure Test Isolation

1. Mock at the module import level to prevent real connections
2. Use `pytest.fixture` for consistent mock setup
3. Add timeout guards to prevent hanging tests

### Phase 4: Coverage Improvement

1. Add tests for new FastMCP-specific functionality
2. Test error scenarios (connection failures, timeouts)
3. Test cleanup and shutdown paths

## File Changes

1. `tests/adapters/test_mcp_adapters.py` - Update all MCPClient mocks
2. `tests/cli/test_khive_mcp.py` - Update get_mcp_client mocks
3. Potentially add `tests/adapters/test_fastmcp_client.py` for specific FastMCP tests

## Success Criteria

- All tests pass in CI
- No real MCP server connections during tests
- Test coverage ≥ 80%
- Tests run quickly (< 30 seconds total)

## Risks and Mitigations

- **Risk:** FastMCP interface changes
  - **Mitigation:** Pin fastmcp version in pyproject.toml

- **Risk:** Async pattern differences
  - **Mitigation:** Use proper async test fixtures and mocking

## Estimated Time

- 1-2 hours for implementation
- 30 minutes for testing and validation