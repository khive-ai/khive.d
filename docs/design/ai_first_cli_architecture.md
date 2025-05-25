# AI-First CLI Architecture: Technical Design Specification

## Executive Summary

Traditional CLIs are designed for humans who can see, remember context, and
iteratively explore. AI agents need fundamentally different interaction
patterns: predictable schemas, rich introspection, stateful execution, and
compositional workflows. This specification outlines a revolutionary AI-first
CLI architecture that maintains human usability while optimizing for machine
interaction.

## Core Design Philosophy

### 1. **Schema-First Design**

Every command, parameter, and output follows a strict schema that can be
introspected at runtime.

```python
class CommandSchema(BaseModel):
    name: str
    description: str
    parameters: Dict[str, ParameterSchema]
    output_schema: Dict[str, Any]
    examples: List[CommandExample]
    error_types: List[ErrorSchema]
    side_effects: List[SideEffect]
    dependencies: List[str]
```

### 2. **Predictable Execution Model**

Commands declare their side effects and can be validated/simulated before
execution.

```python
class ExecutionPlan(BaseModel):
    command: str
    predicted_outputs: Dict[str, Any]
    side_effects: List[SideEffect]
    rollback_strategy: Optional[RollbackPlan]
    confidence: float  # 0.0-1.0
```

### 3. **Rich State Management**

The CLI maintains comprehensive state that agents can query and manipulate.

```python
class CLIState(BaseModel):
    session_id: str
    project_context: ProjectContext
    command_history: List[CommandExecution]
    active_transactions: List[Transaction]
    cached_results: Dict[str, CachedResult]
    agent_preferences: AgentPreferences
```

## Technical Architecture

### Layer 1: Command Introspection Engine

```python
class CommandIntrospector:
    """Provides complete runtime introspection of CLI capabilities."""

    def get_command_schema(self, command_path: str) -> CommandSchema:
        """Return complete schema for any command."""

    def validate_command(self, command: str) -> ValidationResult:
        """Validate command without execution."""

    def suggest_completion(self, partial_command: str) -> List[Suggestion]:
        """Provide intelligent command completion."""

    def find_commands_by_intent(self, intent: str) -> List[CommandMatch]:
        """Semantic search for commands by intent."""
```

### Layer 2: Execution Prediction Engine

```python
class ExecutionPredictor:
    """Predicts command outcomes before execution."""

    def predict_execution(self, command: str, context: CLIState) -> ExecutionPlan:
        """Predict what would happen if command executed."""

    def simulate_execution(self, command: str) -> SimulationResult:
        """Run command in simulation mode."""

    def check_conflicts(self, commands: List[str]) -> List[Conflict]:
        """Check for conflicts between multiple commands."""
```

### Layer 3: State Management Engine

```python
class StateManager:
    """Manages persistent CLI state for AI agents."""

    def get_current_state(self) -> CLIState:
        """Get complete current state."""

    def update_context(self, context_updates: Dict[str, Any]) -> None:
        """Update project context."""

    def add_command_history(self, execution: CommandExecution) -> None:
        """Record command execution."""

    def create_checkpoint(self) -> CheckpointId:
        """Create state checkpoint for rollback."""

    def rollback_to_checkpoint(self, checkpoint_id: CheckpointId) -> None:
        """Rollback to previous state."""
```

### Layer 4: Agent Communication Protocol

```python
class AgentProtocol:
    """Optimized communication protocol for AI agents."""

    def execute_with_prediction(self, command: str) -> PredictedExecution:
        """Execute command with prediction data."""

    def batch_execute(self, commands: List[str]) -> BatchResult:
        """Execute multiple commands atomically."""

    def stream_execution(self, command: str) -> AsyncIterator[ExecutionEvent]:
        """Stream execution events for long-running commands."""
```

## Implementation Strategy

### Phase 1: Schema Foundation (Weeks 1-2)

#### 1.1 Command Schema Registry

```python
# src/khive/agent/schemas.py
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class ParameterSchema(BaseModel):
    name: str
    type: str  # "string", "integer", "boolean", "json"
    required: bool
    description: str
    examples: List[str]
    validation_pattern: Optional[str] = None
    allowed_values: Optional[List[str]] = None

class CommandSchema(BaseModel):
    name: str
    path: str  # e.g., "mcp.call"
    description: str
    parameters: Dict[str, ParameterSchema]
    output_schema: Dict[str, Any]
    examples: List[Dict[str, Any]]
    error_schemas: List[Dict[str, Any]]
    side_effects: List[str]  # "file_write", "network_request", etc.

class SchemaRegistry:
    def __init__(self):
        self._schemas: Dict[str, CommandSchema] = {}

    def register_command(self, schema: CommandSchema):
        self._schemas[schema.path] = schema

    def get_schema(self, command_path: str) -> Optional[CommandSchema]:
        return self._schemas.get(command_path)

    def search_by_intent(self, intent: str) -> List[CommandSchema]:
        # Semantic search implementation
        pass
```

#### 1.2 Auto-Schema Generation

```python
# src/khive/agent/introspection.py
import inspect
import argparse
from typing import get_type_hints

class ArgumentParserIntrospector:
    """Extract schemas from existing argparse parsers."""

    def extract_schema(self, parser: argparse.ArgumentParser) -> CommandSchema:
        """Convert argparse parser to CommandSchema."""
        parameters = {}

        for action in parser._actions:
            if action.dest == 'help':
                continue

            param_schema = ParameterSchema(
                name=action.dest,
                type=self._infer_type(action.type),
                required=action.required if hasattr(action, 'required') else False,
                description=action.help or "",
                examples=self._generate_examples(action),
            )
            parameters[action.dest] = param_schema

        return CommandSchema(
            name=parser.prog,
            path=self._get_command_path(parser),
            description=parser.description or "",
            parameters=parameters,
            output_schema=self._infer_output_schema(parser),
            examples=self._generate_command_examples(parser),
            error_schemas=self._get_error_schemas(parser),
            side_effects=self._detect_side_effects(parser)
        )
```

### Phase 2: Agent Interface (Weeks 3-4)

#### 2.1 Discovery Command

```python
# src/khive/cli/khive_discover.py

async def cmd_discover_commands(format_type: str = "json") -> Dict[str, Any]:
    """Discover all available commands."""
    registry = get_schema_registry()

    if format_type == "json":
        return {
            "commands": {
                schema.path: {
                    "description": schema.description,
                    "parameters": {p.name: p.dict() for p in schema.parameters.values()},
                    "examples": schema.examples
                }
                for schema in registry.get_all_schemas()
            }
        }

async def cmd_discover_parameters(command: str) -> Dict[str, Any]:
    """Discover parameters for a specific command."""
    registry = get_schema_registry()
    schema = registry.get_schema(command)

    if not schema:
        return {"error": f"Command {command} not found"}

    return {
        "command": command,
        "parameters": {
            name: {
                "type": param.type,
                "required": param.required,
                "description": param.description,
                "examples": param.examples
            }
            for name, param in schema.parameters.items()
        }
    }
```

#### 2.2 Validation Command

```python
# src/khive/cli/khive_validate.py

class CommandValidator:
    def __init__(self, registry: SchemaRegistry):
        self.registry = registry

    def validate_command(self, command_line: str) -> ValidationResult:
        """Validate a command line without executing it."""
        try:
            # Parse command line
            parts = shlex.split(command_line)
            if not parts or parts[0] != "khive":
                return ValidationResult(
                    valid=False,
                    errors=["Command must start with 'khive'"]
                )

            # Find command schema
            command_path = ".".join(parts[1:])
            schema = self.registry.get_schema(command_path)

            if not schema:
                return ValidationResult(
                    valid=False,
                    errors=[f"Unknown command: {command_path}"],
                    suggestions=self._suggest_similar_commands(command_path)
                )

            # Validate parameters
            parsed_args = self._parse_arguments(parts[2:], schema)
            validation_errors = self._validate_parameters(parsed_args, schema)

            if validation_errors:
                return ValidationResult(
                    valid=False,
                    errors=validation_errors,
                    suggestions=self._generate_fix_suggestions(validation_errors, schema)
                )

            return ValidationResult(
                valid=True,
                predicted_side_effects=schema.side_effects,
                predicted_output_schema=schema.output_schema
            )

        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[f"Parse error: {str(e)}"]
            )
```

### Phase 3: State Management (Weeks 5-6)

#### 3.1 State Storage

```python
# src/khive/agent/state.py

class CLIStateManager:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.state_file = project_root / ".khive" / "agent_state.json"
        self.current_state = self._load_state()

    def _load_state(self) -> CLIState:
        """Load state from disk or create new."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                return CLIState.parse_obj(data)
            except Exception:
                # Corrupted state file, create new
                pass

        return CLIState(
            session_id=str(uuid.uuid4()),
            project_context=self._detect_project_context(),
            command_history=[],
            active_transactions=[],
            cached_results={},
            agent_preferences=AgentPreferences()
        )

    def _detect_project_context(self) -> ProjectContext:
        """Auto-detect project context."""
        context = ProjectContext()

        # Detect git info
        try:
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                text=True
            ).strip()
            context.git_branch = branch
        except subprocess.CalledProcessError:
            pass

        # Detect current issue from branch name
        if context.git_branch:
            issue_match = re.search(r'(\d+)', context.git_branch)
            if issue_match:
                context.current_issue = int(issue_match.group(1))

        return context

    def update_context(self, **kwargs) -> None:
        """Update project context."""
        for key, value in kwargs.items():
            if hasattr(self.current_state.project_context, key):
                setattr(self.current_state.project_context, key, value)
        self._save_state()

    def record_command(self, command: str, result: Dict[str, Any]) -> None:
        """Record command execution."""
        execution = CommandExecution(
            timestamp=datetime.utcnow(),
            command=command,
            result=result,
            success=result.get("status") == "success"
        )
        self.current_state.command_history.append(execution)

        # Keep only last 100 commands
        if len(self.current_state.command_history) > 100:
            self.current_state.command_history = self.current_state.command_history[-100:]

        self._save_state()
```

#### 3.2 Context-Aware Commands

```python
# Enhance existing commands to use context

def enhance_commit_command(state_manager: CLIStateManager):
    """Enhance commit command with context awareness."""

    original_commit = cmd_commit  # Save original function

    def contextual_commit(message: str = None, **kwargs):
        """Commit with automatic context injection."""
        context = state_manager.current_state.project_context

        # Auto-add issue reference
        if not message and context.current_issue:
            # Generate message from context
            message = f"feat: implement changes for issue #{context.current_issue}"

        if message and context.current_issue:
            # Add closes reference if not present
            if f"#{context.current_issue}" not in message:
                message += f" (closes #{context.current_issue})"

        return original_commit(message=message, **kwargs)

    return contextual_commit
```

### Phase 4: Advanced Features (Weeks 7-8)

#### 4.1 Batch Execution Engine

```python
# src/khive/agent/batch.py

class BatchExecutor:
    def __init__(self, state_manager: CLIStateManager):
        self.state_manager = state_manager

    async def execute_batch(self, commands: List[str]) -> BatchResult:
        """Execute multiple commands with rollback support."""
        transaction_id = str(uuid.uuid4())
        checkpoint_id = self.state_manager.create_checkpoint()

        results = []
        try:
            for i, command in enumerate(commands):
                # Support variable substitution
                expanded_command = self._expand_variables(command, results)

                # Execute command
                result = await self._execute_single_command(expanded_command)
                results.append(result)

                # Check for failure
                if result.get("status") != "success":
                    # Rollback and return
                    await self._rollback_batch(results[:i], checkpoint_id)
                    return BatchResult(
                        success=False,
                        results=results,
                        failed_at=i,
                        error=result.get("error")
                    )

            return BatchResult(
                success=True,
                results=results,
                transaction_id=transaction_id
            )

        except Exception as e:
            await self._rollback_batch(results, checkpoint_id)
            return BatchResult(
                success=False,
                results=results,
                error=str(e)
            )

    def _expand_variables(self, command: str, previous_results: List[Dict]) -> str:
        """Expand variables like {{previous.result}} in commands."""
        # Simple template expansion
        if "{{previous.result}}" in command and previous_results:
            last_result = previous_results[-1].get("result", "")
            command = command.replace("{{previous.result}}", str(last_result))

        return command
```

## Advanced AI Agent Features

### 1. **Semantic Command Search**

```python
class SemanticCommandMatcher:
    """Match natural language intent to commands."""

    def __init__(self, registry: SchemaRegistry):
        self.registry = registry
        self.embeddings = self._build_command_embeddings()

    def find_commands_by_intent(self, intent: str) -> List[CommandMatch]:
        """Find commands that match natural language intent."""
        intent_embedding = self._embed_text(intent)

        matches = []
        for command_path, command_embedding in self.embeddings.items():
            similarity = cosine_similarity(intent_embedding, command_embedding)
            if similarity > 0.7:  # Threshold
                schema = self.registry.get_schema(command_path)
                matches.append(CommandMatch(
                    command=command_path,
                    confidence=similarity,
                    schema=schema,
                    suggested_parameters=self._suggest_parameters(intent, schema)
                ))

        return sorted(matches, key=lambda x: x.confidence, reverse=True)
```

### 2. **Predictive Error Recovery**

```python
class ErrorRecoveryEngine:
    """Provide intelligent error recovery suggestions."""

    def analyze_error(self, command: str, error: Dict[str, Any]) -> RecoveryPlan:
        """Analyze error and suggest recovery actions."""
        error_type = error.get("type", "unknown")

        if error_type == "MissingParameter":
            return self._suggest_missing_parameter_fix(command, error)
        elif error_type == "ValidationError":
            return self._suggest_validation_fix(command, error)
        elif error_type == "PermissionError":
            return self._suggest_permission_fix(command, error)
        else:
            return self._suggest_generic_fix(command, error)

    def _suggest_missing_parameter_fix(self, command: str, error: Dict) -> RecoveryPlan:
        """Suggest how to fix missing parameter errors."""
        missing_param = error.get("parameter")
        command_parts = command.split()

        # Find parameter schema
        schema = self.registry.get_schema(".".join(command_parts[1:]))
        if schema and missing_param in schema.parameters:
            param_schema = schema.parameters[missing_param]

            suggested_value = param_schema.examples[0] if param_schema.examples else "value"
            fixed_command = f"{command} --{missing_param} {suggested_value}"

            return RecoveryPlan(
                type="parameter_addition",
                description=f"Add missing parameter: --{missing_param}",
                suggested_command=fixed_command,
                confidence=0.9
            )
```

### 3. **Learning and Adaptation**

```python
class AgentLearningEngine:
    """Learn from agent behavior to improve suggestions."""

    def __init__(self, state_manager: CLIStateManager):
        self.state_manager = state_manager

    def learn_from_history(self) -> AgentInsights:
        """Analyze command history to learn patterns."""
        history = self.state_manager.current_state.command_history

        # Find common command sequences
        sequences = self._find_common_sequences(history)

        # Find frequently used parameters
        param_patterns = self._analyze_parameter_patterns(history)

        # Find error patterns
        error_patterns = self._analyze_error_patterns(history)

        return AgentInsights(
            common_sequences=sequences,
            parameter_patterns=param_patterns,
            error_patterns=error_patterns,
            suggestions=self._generate_suggestions(sequences, param_patterns)
        )

    def suggest_workflow_automation(self) -> List[WorkflowSuggestion]:
        """Suggest command sequences that could be automated."""
        insights = self.learn_from_history()

        suggestions = []
        for sequence in insights.common_sequences:
            if len(sequence.commands) >= 3:  # Worth automating
                suggestions.append(WorkflowSuggestion(
                    name=f"workflow_{len(suggestions)}",
                    description=f"Automate: {' -> '.join(sequence.commands)}",
                    commands=sequence.commands,
                    frequency=sequence.frequency
                ))

        return suggestions
```

## Performance Optimizations

### 1. **Command Result Caching**

```python
class ResultCache:
    """Cache command results for deterministic operations."""

    def __init__(self):
        self.cache: Dict[str, CachedResult] = {}

    def get_cache_key(self, command: str, context: Dict[str, Any]) -> str:
        """Generate cache key for command."""
        # Hash command + relevant context
        relevant_context = self._extract_relevant_context(command, context)
        cache_data = {"command": command, "context": relevant_context}
        return hashlib.sha256(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()

    def is_cacheable(self, command: str) -> bool:
        """Check if command results can be cached."""
        schema = self.registry.get_schema(command)
        if not schema:
            return False

        # Don't cache commands with side effects
        return "file_write" not in schema.side_effects and "network_request" not in schema.side_effects
```

### 2. **Parallel Execution**

```python
class ParallelExecutor:
    """Execute independent commands in parallel."""

    async def execute_parallel(self, commands: List[str]) -> List[Dict[str, Any]]:
        """Execute commands in parallel where safe."""
        # Analyze dependencies
        dependency_graph = self._build_dependency_graph(commands)

        # Execute in waves based on dependencies
        results = {}
        for wave in self._topological_sort(dependency_graph):
            wave_tasks = [
                self._execute_command(cmd)
                for cmd in wave
            ]
            wave_results = await asyncio.gather(*wave_tasks)

            for cmd, result in zip(wave, wave_results):
                results[cmd] = result

        return [results[cmd] for cmd in commands]
```

This architecture provides a foundation for truly AI-native CLI interaction
while maintaining backward compatibility with human users. The key insight is
treating the CLI as a queryable, predictable system rather than an opaque
command interface.
