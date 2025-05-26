# Khive Development Service

An intelligent development service that unifies khive's development tools (init,
format, test) into a single, agent-friendly interface. Instead of requiring
specific commands, agents and developers can describe what they want to achieve
in natural language.

## Architecture Overview

The service follows the same pattern as the info service:

```
khive/services/dev/
├── __init__.py         # Package exports
├── parts.py            # Request/response models
├── dev_service.py      # Main service logic
├── mcp.py             # MCP server for agents
└── khive_dev.py       # CLI for humans
```

## Key Features

### 1. **Intent-Based Interface**

Agents don't need to know about `khive init`, `khive fmt`, or `khive ci`. They
just describe their intent:

- "Fix all code issues"
- "Set up a new Python project"
- "Check if my project is ready for deployment"
- "Run tests and tell me what's wrong"

### 2. **Intelligent Mode Detection**

The service automatically detects the best approach:

- **QUICK_FIX** - Fast formatting/linting fixes
- **FULL_CHECK** - Comprehensive CI/CD pipeline
- **SETUP** - Project initialization
- **DIAGNOSTIC** - Deep analysis of issues
- **MAINTENANCE** - Cleanup and optimization

### 3. **Synthesized Insights**

Instead of raw command output, the service provides:

- Actionable summaries
- Categorized issues with severity
- Project health scores
- Specific next steps

### 4. **Unified Operations**

All development operations through a single interface:

- Project setup with auto-detected stacks
- Code quality fixes with automatic remediation
- Test execution with coverage analysis
- Diagnostic analysis with root cause identification

## Usage Examples

### For AI Agents (via MCP)

```python
# Natural language request
result = await dev_assist(
    intent="Fix all code quality issues and run tests",
    fix_issues=True
)

# Quick health check
health = await check_project_health(detailed=True)

# Setup new project
setup = await setup_project(
    project_type="python",
    extras=["testing", "ci", "docker"]
)
```

### For Developers (via CLI)

```bash
# Natural language
khive dev "fix all code issues"
khive dev "set up a new Python project with testing"

# Quick operations
khive dev --check          # Run full project check
khive dev --fix           # Fix all auto-fixable issues
khive dev --setup python  # Set up Python project

# With options
khive dev "run tests" --detailed --json
khive dev "check code quality" --no-fix --quiet
```

### Programmatic Usage

```python
from khive.services.dev import DevServiceGroup, DevRequest

# Initialize service
service = DevServiceGroup()

# Make request
request = DevRequest(
    intent="Run comprehensive project check",
    fix_issues=True,
    detailed_analysis=True
)

# Get response
response = await service.handle_request(request)

# Access structured data
print(f"Health Score: {response.project_health.score}/100")
print(f"Issues Fixed: {response.issues_fixed}")
print(f"Next Steps: {response.next_steps}")
```

## Response Structure

The service returns structured `DevResponse` objects containing:

```python
{
    "success": true,
    "summary": "Fixed 5 code quality issues and all tests passed",
    "mode_used": "full_check",
    "issues_found": [
        {
            "type": "formatting",
            "severity": "medium",
            "summary": "Inconsistent formatting in 10 files",
            "fix_applied": true
        }
    ],
    "test_results": [
        {
            "stack": "python",
            "total_tests": 50,
            "passed": 50,
            "coverage": 85.5
        }
    ],
    "project_health": {
        "score": 92,
        "status": "healthy",
        "strengths": ["Good test coverage", "All tests passing"],
        "concerns": []
    },
    "next_steps": [
        "Set up pre-commit hooks",
        "Consider adding type hints"
    ]
}
```

## Integration with Agent Frameworks

The service is designed for easy integration:

```python
# With LangChain
from langchain.tools import Tool
from khive.services.dev import DevServiceGroup

dev_service = DevServiceGroup()

dev_tool = Tool(
    name="Development Assistant",
    func=lambda x: asyncio.run(
        dev_service.handle_request(DevRequest(intent=x))
    ),
    description="Helps with code quality, testing, and project setup"
)

# With AutoGen
import autogen
from khive.services.dev.mcp import dev_assist

autogen.register_function(
    dev_assist,
    caller=assistant,
    executor=user_proxy,
    description="Intelligent development assistance"
)
```

## Philosophy

This service embodies the principle that **tools should enhance, not
complicate**. Agents shouldn't need to understand the intricacies of different
development tools - they should be able to express their intent and get
intelligent assistance.

The service acts as an intelligent layer that:

1. Understands developer intent
2. Routes to appropriate tools
3. Synthesizes results into insights
4. Provides actionable next steps

This makes development operations accessible to AI agents while maintaining the
power and flexibility of the underlying tools.
