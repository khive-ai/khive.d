# Compact Conversation Command

**Purpose**: Create comprehensive, searchable summaries of development
conversations for knowledge preservation and future reference

**Category**: Knowledge Management **Complexity**: Intermediate
**Dependencies**: Bash, file system access

## Quick Start

```bash
# Create summary of current conversation
/project:compact-convo

# Create summary with specific focus
/project:compact-convo "DAG implementation discussion"
```

## Synopsis

```bash
/project:compact-convo [topic_override]
```

## Description

This command creates detailed, structured summaries of conversations, preserving
technical decisions, code changes, insights, and lessons learned. It builds a
searchable knowledge base for future reference.

## Process Overview

**Target Length**: 150-500 lines depending on session substance

### 1. Timestamp Generation

- Gets accurate UTC timestamp
- Creates unique session ID
- Estimates conversation duration

### 2. Directory Setup

- Ensures summary directories exist
- Creates proper file structure
- Maintains organization

### 3. Comprehensive Analysis

- Problem identification
- Solution journey
- Technical insights
- Lessons learned

### 4. Memory Integration

- Captures key insights to memory system
- Extracts patterns and breakthroughs
- Stores searchable memory entries
- Links conversation to knowledge base

### 5. Structured Output

- YAML front matter for indexing
- Consistent section format
- Searchable tags
- Memory references included

## MANDATORY: Session Summary Template

**CRITICAL**: This command MUST follow the official session summary template
located at: `.claude/resources/templates/session-summary-template.md`

### Required Template Structure

```yaml
session_summary:
  # Session Metadata
  session_id: "{uuid}"
  date: "{YYYY-MM-DD}"
  duration: "{duration_in_hours}"
  projects: ["{project_names}"]

  # Work Completed
  commits: [...]
  issues_addressed: [...]
  pull_requests: [...]

  # Key Outcomes
  achievements: [...]
  decisions_made: [...]
  problems_solved: [...]

  # Knowledge Captured
  insights: [...]
  patterns_discovered: [...]
  errors_encountered: [...]

  # Orchestration (if used)
  orchestration:
    pattern_used: "{parallel_discovery|sequential_pipeline|lionagi_flow|single_agent}"
    agent_count: { number }
    success_rate: "{percentage}"
    duration: "{time_taken}"
    lessons_learned: ["{insights}"]

  # Pending Work
  todo_items: [...]
  open_questions: [...]
  next_actions: [...]

  # Handoff Notes
  handoff: { ... }

  # Metrics
  metrics: { ... }
```

### MANDATORY Process

1. **Read Template**: Always start by reading the template file
2. **Follow Structure**: Use exact YAML structure from template
3. **Complete All Sections**: Fill every section with session-specific content
4. **Save to Correct Location**: `.khive/notes/summaries/YYYY-MM-DD_HH-MM.md`
5. **Validate Format**: Ensure YAML is valid and complete

## Examples

### Basic Usage

```bash
# At end of debugging session
/project:compact-convo

# After architecture discussion
/project:compact-convo "DAG architecture design session"
```

### Output Location

```bash
# MANDATORY: Summary saved to:
.khive/notes/summaries/summary_YYYYMMDD_HHMMSS.md

# Example:
.khive/notes/summaries/summary_20250704_032229.md

# Template structure preview:
---
date: 2025-07-04 03:22:29 UTC
session_id: conv_20250704_description
duration: ~3 hours
main_topic: Primary Focus Area
tags: [tag1, tag2, tag3]
key_insights:
  - Key insight from session
files_modified:
  - /full/path/to/file.py
orchestration:
  pattern_used: parallel_discovery
  agent_count: 4
  success_rate: 92%
  duration: 45_minutes
  lessons_learned: ["Critic agent prevented major architecture error", "Batch operations 4x faster than sequential"]
status: completed
---
```

## Best Practices

### Content Guidelines

1. **MANDATORY Template Compliance**: Must follow session-summary-template.md
   structure exactly
2. **Complete All Sections**: Every YAML section must be filled with
   session-specific content
3. **Ocean's Guidance**: Capture messages that changed direction or provided key
   insights
4. **Important Code**: Include patterns worth remembering and solutions to
   tricky problems
5. **Full Paths**: Always use complete file paths
6. **Learning Focus**: Balance what was done with what was learned
7. **Factual Only**: Document what happened, not speculation
8. **Structured Knowledge**: Use YAML structure for searchability and
   consistency
9. **Orchestration Metrics**: Include performance data if orchestration was used
10. **Pattern Effectiveness**: Document which approaches worked best

### What to Include vs Skip

**Include**:

- Breakthrough moments and "aha" discoveries
- Solutions to complex problems
- Ocean's corrections that improved the approach
- Reusable patterns and code
- Failed attempts that taught valuable lessons
- Effective orchestration patterns (parallel/sequential/flow)
- Agent composition approaches that worked well
- Successful quality gates and critic insights

**Skip**:

- Routine file operations
- Repetitive attempts with same error
- Standard boilerplate code
- Minor typo fixes
- Verbose tool outputs

### Formatting Standards

1. **Consistent Headers**: Use the standard section structure
2. **Code Blocks**: Properly format with language tags
3. **Lists**: Use bullets for clarity
4. **Links**: Include references to related documents

### When to Use

- **End of Session**: Before context window fills
- **Major Milestone**: After completing significant work
- **Before Break**: Preserve state before interruption
- **Complex Debugging**: Document investigation process
- **Architecture Decisions**: Capture design discussions
- **After Orchestration**: Capture orchestration performance and lessons learned
- **Pattern Success**: Document effective approaches and agent compositions

### CRITICAL Implementation Requirements

**MANDATORY STEPS FOR EVERY COMPACT-CONVO:**

1. **Read Template First**:
   ```bash
   Read(".claude/resources/templates/session-summary-template.md")
   ```

2. **Follow Template Structure**: Use exact YAML sections and field names

3. **Complete Every Section**: No section should be left empty or incomplete

4. **Save to Correct Location**: Always use `.khive/notes/summaries/` directory

5. **Validate YAML**: Ensure proper YAML formatting and structure

**FAILURE TO FOLLOW TEMPLATE = INVALID SUMMARY**

## Integration

### With Session Management

```bash
# Typical workflow
/project:session-start "Implement DAG system"
# ... work happens ...
/project:compact-convo "DAG implementation progress"
/project:session-complete
```

### With Memory System

The compact-convo command now automatically:

- **Captures Key Insights**: Extracts main discoveries and breakthroughs
- **Stores Patterns**: Identifies reusable solutions and approaches
- **Links Context**: References conversation in memory system
- **Enables Search**: Makes insights findable in future sessions

#### Memory Operations Performed

```python
# Automatically executed during compact-convo:
mcp__memory__save(
    f"CONVERSATION SUMMARY: {topic} - {key_insights}",
    type="event",
    topics=["conversation", "summary", topic_slug]
)

# If breakthroughs detected:
mcp__memory__save(
    f"BREAKTHROUGH: {key_discovery}",
    type="fact",
    topics=["breakthrough", "discovery", relevant_tags]
)

# For technical patterns:
mcp__memory__save(
    f"PATTERN: {technical_pattern} worked well for {use_case}",
    type="fact",
    topics=["pattern", "solution", technology_tags]
)

# For orchestration patterns:
mcp__memory__save(
    f"ORCHESTRATION: {pattern_name} with {agent_count} agents achieved {success_rate}% success",
    type="fact",
    topics=["orchestration", "patterns", "success"]
)

# For Ocean's guidance:
mcp__memory__save(
    f"OCEAN GUIDANCE: {guidance_summary}",
    type="preference",
    topics=["ocean", "guidance", "preferences"]
)
```

### With Knowledge Base

- Summaries are indexed for search
- Tags enable topic discovery
- Cross-references link related work
- Insights feed into documentation
- Memory entries provide immediate search access

### With Knowledge MCP (Optional)

For sessions with significant knowledge discoveries:

```python
# Optional: Create entities for major technical concepts discovered
if major_concepts_discovered:
    for concept in key_concepts:
        mcp__knowledge__create_entity(
            name=concept["name"],
            entity_type=concept["type"], 
            created_by="compact_agent",
            properties=concept.get("properties", {})
        )

# Record key insights for future reference
for insight in conversation_insights:
    mcp__knowledge__record_insight(
        insight=insight["content"],
        connections=[],  # Simple approach - no complex relationships
        strength=0.8,
        created_by="compact_agent"
    )
```

This creates searchable knowledge entries for significant discoveries.

## Practical Usage Guidelines

### When to Create Summaries

**High Priority** (Always create):

- Sessions with major breakthroughs or "aha" moments
- Complex debugging that revealed root causes
- Ocean provided significant course corrections
- Multi-agent orchestration with lessons learned
- Architecture decisions with trade-off analysis

**Medium Priority** (Create if time allows):

- Routine development sessions with interesting patterns
- Problem-solving sessions with reusable solutions
- Sessions that refined existing approaches

**Low Priority** (Skip):

- Routine file operations or minor bug fixes
- Sessions primarily consisting of reading/research
- Repetitive work with no new insights

### Template Simplification

Focus on the most valuable sections:

```yaml
# Essential sections (always fill):
session_summary:
  session_id: "{descriptive_id}"
  date: "{YYYY-MM-DD}"
  duration: "{hours}"
  main_topic: "{primary_focus}"

  # Core outcomes
  achievements: ["{concrete_deliverables}"]
  insights: ["{key_learnings}"]
  problems_solved: ["{solutions_found}"]

  # If orchestration was used
  orchestration:
    pattern_used: "{pattern_name}"
    agent_count: { number }
    success_rate: "{percentage}"
    lessons_learned: ["{insights}"]
```

### Code Snippet Preservation

````markdown
### Reusable Patterns

\```python

# Event-driven task update pattern

async def on_task_complete(event): task_id = event['task_id'] output =
event['output']

    # Update dependent tasks
    for dep_task in dag.get_dependents(task_id):
        if dep_task.can_run():
            await scheduler.queue(dep_task)

\```
````

### Cross-References

```markdown
### Related Work

- Previous session: [DAG Research](../summaries/summary_20250618_120000.md)
- Design doc: [DAG Architecture](../../docs/dag_architecture.md)
- Issues: #119, #120, #121
```

## Search and Discovery

### Using Tags

Tags enable finding related summaries:

```bash
# Find all DAG-related summaries
grep -l "tags:.*dag" .khive/notes/summaries/*.md

# Find performance insights
grep -l "performance" .khive/notes/summaries/*.md | xargs grep -h "Performance" -A 5
```

### Building Indexes

Future integration will support:

- Full-text search
- Tag-based navigation
- Insight extraction
- Pattern mining

## Performance Notes

- Summaries typically 2-5KB
- No external API calls required
- Fast file system operations
- Incremental index updates planned

## Error Handling

| Issue               | Cause            | Solution                    |
| ------------------- | ---------------- | --------------------------- |
| `Permission denied` | Write access     | Check directory permissions |
| `No space left`     | Disk full        | Clean old summaries         |
| `Invalid YAML`      | Formatting error | Validate front matter       |

## Command Metadata

```yaml
command: compact-convo
category: knowledge-management
complexity: intermediate
author: khive-ai
version: 2.0
last_updated: 2025-06-19
arguments:
  topic_override:
    type: string
    required: false
    description: "Override auto-detected topic"
tags:
  - documentation
  - knowledge-management
  - summary
  - memory
related_commands:
  - session-complete
  - session-start
```

## Important Notes

1. **MANDATORY TEMPLATE**: Must use session-summary-template.md structure - no
   exceptions
2. **Context Preservation**: Run before context window limit
3. **Accuracy**: Review generated summary for completeness
4. **Privacy**: Summaries may contain sensitive code/data
5. **Versioning**: Summaries are immutable once created
6. **Backup**: Include summaries in repository backups
7. **Location**: Always save to .khive/notes/summaries/ directory

Arguments: $ARGUMENTS
