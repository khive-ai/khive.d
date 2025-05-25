# AI-First CLI Implementation Guide for Khive

## Executive Summary

Based on research and the unique challenges AI agents face when using CLIs, this
guide provides a practical implementation roadmap for transforming khive into
the first truly AI-native command-line tool. We focus on immediate, high-impact
improvements that can be implemented incrementally.

## Core Principles (From Research)

1. **Dynamic Error Recovery**: LLMs can understand context and adapt recovery
   strategies
2. **Pre-execution Validation**: Commands should be validated before execution
3. **Structured Communication**: Standardized formats for all interactions
4. **Deterministic Behavior**: Identical inputs yield identical outputs
5. **Contextual Awareness**: Commands understand their environment

## Phase 1: Foundation (Week 1-2)

### 1.1 Agent Mode Flag

Add a global `--agent-mode` flag that transforms all output to structured JSON:

```python
# src/khive/cli/khive_cli.py
def add_global_arguments(parser):
    parser.add_argument(
        "--agent-mode",
        action="store_true",
        help="Enable AI agent mode with structured JSON output"
    )

# Example usage:
# khive --agent-mode mcp call github create_issue --title "Bug"
# Returns: {"success": false, "error": {"type": "MissingParameter", ...}}
```

### 1.2 Command Discovery

Implement `khive discover` for runtime introspection:

```python
# src/khive/cli/khive_discover.py
import argparse
import json
from typing import Dict, Any, List

def build_parser():
    parser = argparse.ArgumentParser(description="Discover khive capabilities")
    subparsers = parser.add_subparsers(dest="discover_type")

    # Discover all commands
    commands_parser = subparsers.add_parser(
        "commands",
        help="List all available commands"
    )

    # Discover parameters for a command
    params_parser = subparsers.add_parser(
        "parameters",
        help="List parameters for a specific command"
    )
    params_parser.add_argument("command", help="Command to inspect")

    # Discover examples
    examples_parser = subparsers.add_parser(
        "examples",
        help="Get examples for a command"
    )
    examples_parser.add_argument("command", help="Command to get examples for")

    return parser

async def cmd_discover_commands() -> Dict[str, Any]:
    """Discover all khive commands by introspecting the CLI."""
    from khive.cli.khive_cli import build_parser as main_parser

    parser = main_parser()
    commands = {}

    # Extract top-level commands
    for action in parser._subparsers._actions:
        if isinstance(action, argparse._SubParsersAction):
            for cmd_name, cmd_parser in action.choices.items():
                commands[cmd_name] = {
                    "description": cmd_parser.description or "",
                    "subcommands": {}
                }

                # Check for subcommands
                for sub_action in cmd_parser._actions:
                    if isinstance(sub_action, argparse._SubParsersAction):
                        for sub_name, sub_parser in sub_action.choices.items():
                            commands[cmd_name]["subcommands"][sub_name] = {
                                "description": sub_parser.description or ""
                            }

    return {
        "success": True,
        "commands": commands,
        "total": len(commands)
    }

async def cmd_discover_parameters(command: str) -> Dict[str, Any]:
    """Discover parameters for a specific command."""
    # Parse command path (e.g., "mcp.call")
    parts = command.split(".")

    # Get the appropriate parser
    parser = get_parser_for_command(parts)

    if not parser:
        return {
            "success": False,
            "error": f"Command '{command}' not found"
        }

    parameters = {}
    for action in parser._actions:
        if action.dest == "help":
            continue

        param_info = {
            "type": get_type_name(action.type),
            "required": action.required if hasattr(action, 'required') else False,
            "description": action.help or "",
            "default": action.default if action.default != argparse.SUPPRESS else None,
            "choices": list(action.choices) if action.choices else None
        }

        # Handle flags vs arguments
        if action.option_strings:
            param_info["flags"] = action.option_strings

        parameters[action.dest] = param_info

    return {
        "success": True,
        "command": command,
        "parameters": parameters
    }

# Integration with main CLI
def cli_entry_discover():
    parser = build_parser()
    args = parser.parse_args()

    if args.discover_type == "commands":
        result = asyncio.run(cmd_discover_commands())
    elif args.discover_type == "parameters":
        result = asyncio.run(cmd_discover_parameters(args.command))
    elif args.discover_type == "examples":
        result = asyncio.run(cmd_discover_examples(args.command))

    print(json.dumps(result, indent=2))
```

### 1.3 Error Enhancement

Create structured error messages for agent mode:

```python
# src/khive/agent/errors.py
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class AgentError:
    """Structured error for AI agents."""
    error_type: str
    message: str
    parameter: Optional[str] = None
    suggested_fix: Optional[str] = None
    example_command: Optional[str] = None
    documentation_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.error_type,
            "message": self.message,
            "parameter": self.parameter,
            "fix": {
                "suggestion": self.suggested_fix,
                "example": self.example_command,
                "documentation": self.documentation_url
            } if self.suggested_fix else None
        }

class ErrorEnhancer:
    """Enhance errors with AI-friendly information."""

    def enhance_missing_parameter_error(
        self,
        command: str,
        parameter: str,
        parameter_schema: Dict[str, Any]
    ) -> AgentError:
        """Enhance missing parameter errors."""
        example_value = parameter_schema.get("examples", ["value"])[0]

        return AgentError(
            error_type="MissingParameter",
            message=f"Required parameter '{parameter}' is missing",
            parameter=parameter,
            suggested_fix=f"Add --{parameter} {example_value}",
            example_command=f"{command} --{parameter} {example_value}"
        )

    def enhance_validation_error(
        self,
        command: str,
        parameter: str,
        value: Any,
        validation_message: str
    ) -> AgentError:
        """Enhance validation errors."""
        return AgentError(
            error_type="ValidationError",
            message=validation_message,
            parameter=parameter,
            suggested_fix=self._suggest_validation_fix(parameter, value, validation_message)
        )
```

## Phase 2: State Management (Week 3-4)

### 2.1 Context Persistence

Simple file-based context that doesn't require a backend:

```python
# src/khive/agent/context.py
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class AgentContext:
    """Persistent context for AI agents."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.context_file = project_root / ".khive" / "agent_context.json"
        self.context_file.parent.mkdir(parents=True, exist_ok=True)
        self._context = self._load_context()

    def _load_context(self) -> Dict[str, Any]:
        """Load context from disk."""
        if self.context_file.exists():
            try:
                return json.loads(self.context_file.read_text())
            except:
                pass

        return {
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.utcnow().isoformat(),
            "values": {}
        }

    def set(self, key: str, value: Any) -> None:
        """Set a context value."""
        self._context["values"][key] = value
        self._context["updated_at"] = datetime.utcnow().isoformat()
        self._save_context()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        return self._context["values"].get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """Get all context values."""
        return self._context["values"].copy()

    def _save_context(self) -> None:
        """Save context to disk."""
        self.context_file.write_text(json.dumps(self._context, indent=2))

# CLI integration
def cli_entry_context():
    parser = argparse.ArgumentParser(description="Manage agent context")
    subparsers = parser.add_subparsers(dest="action")

    # Set context
    set_parser = subparsers.add_parser("set", help="Set context value")
    set_parser.add_argument("key", help="Context key")
    set_parser.add_argument("value", help="Context value")

    # Get context
    get_parser = subparsers.add_parser("get", help="Get context value")
    get_parser.add_argument("key", help="Context key")

    # Show all context
    show_parser = subparsers.add_parser("show", help="Show all context")

    args = parser.parse_args()
    context = AgentContext(PROJECT_ROOT)

    if args.action == "set":
        context.set(args.key, args.value)
        print(json.dumps({"success": True, "key": args.key, "value": args.value}))
    elif args.action == "get":
        value = context.get(args.key)
        print(json.dumps({"success": True, "key": args.key, "value": value}))
    elif args.action == "show":
        print(json.dumps({"success": True, "context": context.get_all()}))
```

### 2.2 Command History

Track command execution for learning and debugging:

```python
# src/khive/agent/history.py
from dataclasses import dataclass
from typing import List, Dict, Any
import json

@dataclass
class CommandExecution:
    timestamp: str
    command: str
    args: Dict[str, Any]
    result: Dict[str, Any]
    success: bool
    duration_ms: float

class CommandHistory:
    """Track command execution history."""

    def __init__(self, project_root: Path):
        self.history_file = project_root / ".khive" / "command_history.jsonl"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def record(self, execution: CommandExecution) -> None:
        """Record a command execution."""
        with self.history_file.open("a") as f:
            f.write(json.dumps(execution.__dict__) + "\n")

    def get_recent(self, limit: int = 10) -> List[CommandExecution]:
        """Get recent command executions."""
        if not self.history_file.exists():
            return []

        lines = self.history_file.read_text().strip().split("\n")
        recent_lines = lines[-limit:] if len(lines) > limit else lines

        executions = []
        for line in recent_lines:
            if line:
                data = json.loads(line)
                executions.append(CommandExecution(**data))

        return executions

    def search(self, pattern: str) -> List[CommandExecution]:
        """Search command history."""
        results = []
        if self.history_file.exists():
            for line in self.history_file.read_text().strip().split("\n"):
                if line and pattern in line:
                    data = json.loads(line)
                    results.append(CommandExecution(**data))
        return results
```

## Phase 3: Validation & Prediction (Week 5-6)

### 3.1 Command Validator

Validate commands without executing them:

```python
# src/khive/agent/validator.py
import shlex
from typing import Dict, Any, List, Optional

class CommandValidator:
    """Validate commands before execution."""

    def __init__(self, schema_registry):
        self.schema_registry = schema_registry

    def validate(self, command_line: str) -> Dict[str, Any]:
        """Validate a complete command line."""
        try:
            # Parse command
            parts = shlex.split(command_line)
            if not parts or parts[0] != "khive":
                return {
                    "valid": False,
                    "error": "Command must start with 'khive'",
                    "suggestion": "Try: khive <command> [options]"
                }

            # Find command schema
            command_path = self._get_command_path(parts[1:])
            schema = self.schema_registry.get_schema(command_path)

            if not schema:
                similar = self._find_similar_commands(command_path)
                return {
                    "valid": False,
                    "error": f"Unknown command: {command_path}",
                    "similar_commands": similar,
                    "suggestion": f"Did you mean: khive {similar[0]}?" if similar else None
                }

            # Parse arguments
            parsed_args = self._parse_arguments(parts[1:], schema)

            # Validate required parameters
            missing = self._check_required_parameters(parsed_args, schema)
            if missing:
                param = missing[0]
                param_schema = schema.parameters[param]
                example = param_schema.examples[0] if param_schema.examples else "value"

                return {
                    "valid": False,
                    "error": f"Missing required parameter: {param}",
                    "suggestion": f"Add --{param} {example}",
                    "example_command": f"{command_line} --{param} {example}"
                }

            # Validate parameter values
            validation_errors = self._validate_parameter_values(parsed_args, schema)
            if validation_errors:
                error = validation_errors[0]
                return {
                    "valid": False,
                    "error": error["message"],
                    "parameter": error["parameter"],
                    "suggestion": error["suggestion"]
                }

            # Success!
            return {
                "valid": True,
                "command": command_path,
                "parsed_arguments": parsed_args,
                "predicted_side_effects": schema.side_effects,
                "confidence": 0.95  # High confidence since we validated everything
            }

        except Exception as e:
            return {
                "valid": False,
                "error": f"Parse error: {str(e)}",
                "suggestion": "Check command syntax"
            }
```

### 3.2 Execution Predictor

Predict what will happen before execution:

```python
# src/khive/agent/predictor.py
from typing import Dict, Any, List

class ExecutionPredictor:
    """Predict command execution outcomes."""

    def predict(self, command: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Predict execution outcome."""
        # Validate first
        validation = self.validator.validate(command)
        if not validation["valid"]:
            return {
                "will_succeed": False,
                "reason": validation["error"],
                "suggestion": validation.get("suggestion")
            }

        schema = self.schema_registry.get_schema(validation["command"])

        # Check for conflicts
        conflicts = self._check_conflicts(schema, context)
        if conflicts:
            return {
                "will_succeed": False,
                "reason": f"Conflict detected: {conflicts[0]}",
                "suggestion": "Resolve conflict before execution"
            }

        # Predict side effects
        side_effects = []
        for effect in schema.side_effects:
            if effect == "file_write":
                side_effects.append({
                    "type": "file_write",
                    "description": "Will write to filesystem",
                    "reversible": True
                })
            elif effect == "network_request":
                side_effects.append({
                    "type": "network_request",
                    "description": "Will make network request",
                    "reversible": False
                })

        return {
            "will_succeed": True,
            "confidence": 0.85,
            "predicted_side_effects": side_effects,
            "estimated_duration_ms": self._estimate_duration(schema),
            "rollback_available": all(e["reversible"] for e in side_effects)
        }
```

## Phase 4: Integration Examples

### 4.1 Enhanced MCP Command

Update the MCP command to use agent features:

```python
# src/khive/cli/khive_mcp.py (enhanced)
async def main_mcp_flow(args: argparse.Namespace, config: MCPConfig) -> dict[str, Any]:
    """Enhanced MCP flow with agent support."""
    # Get agent context if in agent mode
    if getattr(args, "agent_mode", False):
        context = AgentContext(args.project_root)
        history = CommandHistory(args.project_root)

        # Record command start
        start_time = time.time()

    try:
        # Original command logic
        result = await original_main_mcp_flow(args, config)

        # Enhance result for agent mode
        if getattr(args, "agent_mode", False):
            # Record execution
            duration_ms = (time.time() - start_time) * 1000
            history.record(CommandExecution(
                timestamp=datetime.utcnow().isoformat(),
                command="mcp " + args.command,
                args=vars(args),
                result=result,
                success=result.get("status") == "success",
                duration_ms=duration_ms
            ))

            # Add execution metadata
            result["_metadata"] = {
                "duration_ms": duration_ms,
                "context_used": context.get_all(),
                "timestamp": datetime.utcnow().isoformat()
            }

        return result

    except Exception as e:
        if getattr(args, "agent_mode", False):
            # Enhance error for agents
            enhancer = ErrorEnhancer()
            if "Missing required parameter" in str(e):
                # Extract parameter name
                param = str(e).split("'")[1]
                enhanced_error = enhancer.enhance_missing_parameter_error(
                    f"mcp {args.command}",
                    param,
                    {"examples": ["example_value"]}  # Get from schema
                )

                return {
                    "status": "failure",
                    "error": enhanced_error.to_dict(),
                    "_metadata": {
                        "duration_ms": (time.time() - start_time) * 1000,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }

        # Re-raise for normal mode
        raise
```

### 4.2 Usage Examples for AI Agents

```python
# Example 1: Discover available commands
result = execute_command("khive --agent-mode discover commands")
# {"success": true, "commands": {"mcp": {"description": "...", "subcommands": {...}}}}

# Example 2: Validate before execution
validation = execute_command("khive --agent-mode validate 'mcp call github create_issue --title Bug'")
# {"valid": false, "error": "Missing required parameter: body", "suggestion": "Add --body 'description'"}

# Example 3: Set context for session
execute_command("khive --agent-mode context set issue 148")
execute_command("khive --agent-mode context set pr_title 'fix: remove custom MCP'")

# Example 4: Execute with prediction
result = execute_command("khive --agent-mode mcp call github create_issue --title 'Bug' --body 'Details' --predict")
# {"will_succeed": true, "predicted_side_effects": [{"type": "network_request", ...}], ...}

# Example 5: Get command history
history = execute_command("khive --agent-mode history recent --limit 5")
# {"success": true, "executions": [...]}
```

## Implementation Priority

1. **Week 1**: Agent mode flag + basic structured output
2. **Week 2**: Discovery commands (commands, parameters, examples)
3. **Week 3**: Context persistence (set/get/show)
4. **Week 4**: Command history tracking
5. **Week 5**: Validation engine
6. **Week 6**: Prediction and enhanced errors

## Success Metrics

- **Error Reduction**: 80% fewer command failures due to validation
- **Discovery Success**: Agents can discover any command without documentation
- **Context Utilization**: 60% of commands use context to reduce parameters
- **Recovery Speed**: 90% of errors include actionable fix suggestions

## Next Steps

1. Create issue for "AI-First CLI Enhancement"
2. Implement Phase 1 (Foundation) as proof of concept
3. Gather feedback from AI agent usage
4. Iterate based on real-world agent behavior
5. Document patterns for other CLI tools to adopt

This approach transforms khive from a human-centric CLI to a dual-purpose tool
that serves both humans and AI agents effectively, setting a new standard for
AI-native development tools.
