# AI Agent CLI Improvements for Khive

## Core Problem

As an AI agent, I face unique challenges using CLI tools:

- No visual feedback or tab completion
- Must parse text output to understand results
- Cannot maintain state between invocations
- Limited ability to recover from errors

## Practical Improvements for AI Agents

### 1. **Structured Discovery Commands**

```bash
# Current: I have to read docs or guess
khive mcp tools github  # Returns human-readable list

# Proposed: Machine-readable discovery
khive discover commands --format json
# Returns: {"commands": ["mcp", "init", "commit", ...], "subcommands": {...}}

khive discover parameters --command "mcp call" --format json
# Returns: {"required": ["server", "tool"], "optional": ["--var", "--json"], ...}

khive discover examples --command "mcp call" --format json
# Returns: [{"description": "Read file", "command": "khive mcp call fs read_file --path x"}]
```

### 2. **Command Validation (Dry Run++)**

```bash
# Current: I run commands and hope they work
khive mcp call github create_issue --title "Bug"
# Error: Missing required parameter 'body'

# Proposed: Validate without execution
khive validate "mcp call github create_issue --title 'Bug'"
# Returns: {"valid": false, "errors": ["Missing required parameter: body"],
#          "suggestion": "Add --body 'description'"}
```

### 3. **State Query Commands**

```bash
# Proposed: Let me query project state
khive state show --format json
# Returns: {
#   "branch": "feat/148-fix-mcp",
#   "issue": 148,
#   "uncommitted_files": ["src/khive/adapters/fastmcp_client.py"],
#   "last_command": "khive mcp call fs write_file",
#   "tests_passing": true
# }

khive state history --last 5 --format json
# Returns last 5 khive commands with results
```

### 4. **Error Enhancement Mode**

```bash
# Proposed: Rich error context for agents
export KHIVE_AGENT_MODE=1  # Or --agent-mode flag

khive mcp call github create_issue --title "Bug"
# Returns structured error:
{
  "success": false,
  "error": {
    "type": "MissingParameter",
    "parameter": "body",
    "message": "Missing required parameter 'body'",
    "fix": {
      "add_flag": "--body",
      "example_value": "Issue description here",
      "full_command": "khive mcp call github create_issue --title \"Bug\" --body \"Description\""
    }
  }
}
```

### 5. **Batch Command Support**

```bash
# Proposed: Execute multiple commands atomically
khive batch execute --format json << 'EOF'
mcp call fs read_file --path src/main.py
mcp call fs write_file --path backup.py --var content="{{previous.result}}"
commit -m "backup: save main.py"
EOF

# Returns: {"results": [...], "success": true, "rollback_available": true}
```

### 6. **Context Persistence (Simple)**

```bash
# Proposed: Simple file-based context
khive context set --issue 148 --pr-title "fix: remove custom MCP"
# Writes to .khive/context.json

khive context get --key issue
# Returns: 148

# Commands auto-read context:
khive commit  # Automatically adds "Closes #148" from context
```

## Implementation Strategy

### Phase 1: Discovery & Validation (No Backend)

- Add `khive discover` command that introspects argparse
- Add `khive validate` that runs parsers without execution
- All data comes from existing code structure

### Phase 2: State & Context (Local Files)

- Add `.khive/state.json` for command history
- Add `.khive/context.json` for session context
- Simple file read/write, no database

### Phase 3: Agent Mode (Enhanced Output)

- Add `--agent-mode` global flag
- Structured JSON errors with fix suggestions
- Command examples in error messages

### Phase 4: Batch Operations (Advanced)

- Parse multi-line command input
- Execute with rollback capability
- Template variable substitution

## Design Principles for AI Tools

1. **Discoverable**: I should be able to find out what's possible without
   external docs
2. **Validatable**: I should know if a command will work before running it
3. **Recoverable**: Errors should tell me exactly how to fix them
4. **Stateful**: I should be able to query what's happened and what state we're
   in
5. **Structured**: All output should be parseable (JSON) in agent mode

## Example: How This Helps Me

```python
# Current AI agent struggle:
result = execute_command("khive mcp call github create_issue --title 'Bug'")
# Parse error text, guess what's wrong, try to fix...

# With improvements:
# First, discover what's needed
discovery = execute_command("khive discover parameters --command 'mcp call github create_issue' --format json")
required_params = discovery['required']

# Validate before running
validation = execute_command(f"khive validate 'mcp call github create_issue --title \"Bug\"' --format json")
if not validation['valid']:
    suggestion = validation['suggestion']
    # Use the suggestion to build correct command

# Execute with confidence
result = execute_command("khive mcp call github create_issue --title 'Bug' --body 'Details'")
```

## Benefits

1. **Reduced Failures**: Validation prevents most errors
2. **Faster Recovery**: Structured errors with fixes
3. **Better Context**: State tracking across commands
4. **Improved Reliability**: Batch operations with rollback
5. **Learning Capability**: Discover commands dynamically

## Next Steps

1. Start with `khive discover` - pure introspection, no infrastructure needed
2. Add `--agent-mode` to existing commands for structured output
3. Implement simple file-based context (just JSON files)
4. Gradually add validation and state tracking

The key insight: **Design for machines first, humans second**. The pretty colors
and formatting can stay, but every command needs a machine-readable mode.
