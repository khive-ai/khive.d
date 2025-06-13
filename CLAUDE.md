# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Development Commands

### Environment Setup

```bash
# Install khive with all dependencies using uv (preferred)
uv sync --extra all

# Or with pip
pip install -e ".[all,dev]"

# Activate virtual environment if needed
source .venv/bin/activate
```

### Common Development Tasks

```bash
# Run tests
uv run pytest                          # Run all tests
uv run pytest tests/clients/           # Run specific test directory
uv run pytest -k "test_api_client"     # Run tests matching pattern
uv run pytest -xvs                     # Stop on first failure, verbose

# Run tests with coverage
uv run pytest --cov=khive --cov-report=html
# View coverage report: open htmlcov/index.html

# Format code
uv run ruff format                     # Format all Python files
uv run ruff check --fix               # Fix auto-fixable lint issues

# Lint code
uv run ruff check                     # Check for lint issues

# Type checking (if mypy is added)
# uv run mypy src/khive

# Build package
uv build                              # Creates dist/ with wheel and sdist

# Clean up
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete
rm -rf dist/ build/ *.egg-info/
```

### Running khive Commands

```bash
# All khive commands can be run with uv
uv run khive init                     # Initialize project
uv run khive fmt                      # Format code
uv run khive ci                       # Run CI checks
uv run khive info "query"             # Search for information
uv run khive mcp                      # Start MCP servers
```

## High-Level Architecture

khive follows a **Service-Oriented CLI Architecture** designed for AI-augmented
development workflows.

### Core Architecture Layers

1. **CLI Layer** (`src/khive/cli/`)
   - Entry point: `khive_cli.py`
   - Command dispatcher using subcommands
   - Base classes: `BaseCLICommand`, `FileBasedCLICommand`,
     `ConfigurableCLICommand`
   - Lifecycle: `_add_arguments()` → `_create_config()` → `_execute()` →
     `_handle_result()`

2. **Commands Layer** (`src/khive/commands/`)
   - Command implementations that orchestrate services
   - Each command module contains command logic and service interactions
   - Examples: `info.py`, `git.py`, `dev.py`

3. **Services Layer** (`src/khive/services/`)
   - Business logic and domain functionality
   - All services implement `Service` base class with `handle_request()` method
   - Protocol-agnostic (works via CLI, MCP, or direct API)
   - Key services:
     - `InfoService`: Intelligent information retrieval and synthesis
     - `GitService`: Natural language git workflow automation
     - `DevService`: Development environment management
     - `FileService`: File operations and management

4. **Clients Layer** (`src/khive/clients/`)
   - Generic async API clients with resilience patterns
   - `AsyncAPIClient`: Base HTTP client with retry, rate limiting, circuit
     breaker
   - `AsyncExecutor`: Concurrent task execution with resource management
   - Resilience patterns: Circuit breaker, rate limiting (TokenBucket), retries

5. **Connections Layer** (`src/khive/connections/`)
   - Provider-specific endpoint configurations
   - Unified interface for different LLM providers (Anthropic, OpenAI,
     Perplexity, etc.)
   - Transport types: HTTP, SDK (OpenAI-compatible)

### Key Design Patterns

1. **Service Interface Pattern**
   - Services accept natural language requests
   - Understand intent and route to appropriate workflows
   - Return rich, structured responses with recommendations

2. **Provider Abstraction**
   - `Endpoint` class abstracts different API providers
   - Easy to add new LLM providers
   - Consistent interface regardless of transport

3. **Async Throughout**
   - All I/O operations are async
   - Proper resource cleanup with async context managers
   - Compatible with nested event loops (MCP support)

4. **Resilience by Design**
   - Every network operation has timeout, retry, and circuit breaker
   - Graceful degradation in services
   - Comprehensive error handling at every layer

### MCP Integration

khive integrates with Model Context Protocol (MCP) servers:

- Dynamic server discovery from `.khive/mcps/config.json`
- Intelligent transport detection (stdio/HTTP/SSE)
- Environment management and lifecycle control
- Services expose MCP tools for AI integration

### Configuration Hierarchy

1. Default values in code
2. Project-level `.khive/` config files
3. Environment variables (`.env` files supported)
4. CLI arguments (highest priority)

### AI Methodology Integration

khive implements the "Golden Path" development methodology:

- Prompts in `src/khive/prompts/roo_rules/` define AI team roles
- Templates in `src/khive/prompts/templates/` for structured outputs
- Six specialized AI roles: Orchestrator, Researcher, Architect, Implementer,
  Reviewer, Documenter
- Workflow: Research → Design → Implement → Review → Document → Merge

### Testing Strategy

- Tests use pytest with async support (`pytest-asyncio`)
- Comprehensive test coverage for all layers
- Integration tests for end-to-end workflows
- Mock external dependencies appropriately
- Run with `uv run pytest` for consistency

### Adding New Features

1. **New Command**: Create in `src/khive/cli/khive_*.py`, inherit from
   appropriate base class
2. **New Service**: Create in `src/khive/services/*/`, implement `Service`
   interface
3. **New Provider**: Add to `src/khive/connections/providers/`, create
   `EndpointConfig`
4. **New MCP Tool**: Add to service's `mcp.py` file, register in
   `get_mcp_tools()`

### Important Notes

- Always use `uv` for dependency management and command execution
- Follow existing patterns for consistency
- Services should understand natural language, not just execute commands
- Maintain high test coverage (>80%)
- Use async/await for all I/O operations
- Handle errors gracefully at service boundaries
