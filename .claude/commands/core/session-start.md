# session-start

## Purpose

Initialize orchestrator session with intelligent context loading

## Usage

```bash
/session-start [--issue NUMBER] [--resume] [--depth DAYS]
```

## Execution Pattern: **ORCHESTRATOR MUST PERFORM ALL THESE STEPS MANUALLY, NO DELEGATION**

### 1. Run Session Initializer (MANDATORY)

```bash
uv run khive session init [options]
```

This automatically:

- ✅ Verifies current date/time
- ✅ Loads recent session diaries and summaries
- ✅ Analyzes git status and open issues
- ✅ Generates optimized memory queries for context
- ✅ Includes project identity and Ocean's preferences
- ✅ Provides prioritized task recommendations
- ✅ Shows execution decision guidance

### 2. Execute Memory Context Loading (CRITICAL)

The session initializer provides optimized memory queries. Execute them in
parallel:

```python
# Execute memory queries in BATCH (max efficiency)
[BatchTool]:
  mcp__memory__search_by_type("preference", limit=10)
  mcp__memory__search("Ocean preferences lion khive", limit=5)
  mcp__memory__search("orchestration patterns successful", limit=5)
  mcp__memory__search("agent composition effective", limit=5)
  mcp__memory__search("lionagi flow patterns", limit=5)
```

### 3. Recent Work Context Loading

```python
# Load recent session summaries and outcomes
summary_files = Glob(".khive/notes/summaries/summary_*.md")
if summary_files:
    recent_summaries = sorted(summary_files, reverse=True)[:3]
    for summary_file in recent_summaries:
        Read(summary_file)

# Search for recent outcomes and patterns
mcp__memory__search("session outcome summary", limit=3)
mcp__memory__search("orchestration complete", limit=3)
```

### 6. Workspace Analysis

```bash
# Check git status and recent commits
git status
git log --oneline -5
gh issue list --state open --limit 10
```

### 3. Multi-Perspective Session Assessment (MANDATORY)

Apply multi-reasoning to understand current context:

```
<multi_reasoning>
To increase reasoning context, let me think through with 5 perspectives:

[^Critical]: Question assumptions, find flaws, evaluate current workspace state and pending work
[^System]: See interconnections, dependencies, ripple effects across projects and recent sessions  
[^Creative]: Generate novel approaches, think outside constraints for session focus and orchestration
[^Risk]: Identify what could go wrong, mitigation strategies for pending work and orchestration patterns
[^Practical]: Focus on implementation details, concrete next steps for today's orchestration work
</multi_reasoning>
```

### 4. Extract Orchestration Patterns from Memory (MANDATORY)

Load proven patterns from memory context (don't hardcode):

```python
# Extract pattern insights from loaded memory context
# Parse the memory results from step 2 to identify:

pattern_insights = {
    "ocean_preferences": "Extract from memory: Ocean's working style and values",
    "proven_patterns": "Extract from memory: Recently successful orchestration patterns",
    "recent_learnings": "Extract from memory: Key insights from recent sessions", 
    "execution_focus": "Extract from memory: Effective techniques and approaches"
}

print("📊 Pattern Insights Extracted from Memory - Ready for orchestration")

# Example extraction logic:
# for memory_result in loaded_memories:
#     if "Ocean prefers" in memory_result: ocean_preferences += memory_result
#     if "pattern successful" in memory_result: proven_patterns += memory_result
#     etc.
```

### 5. Initialize Task Tracking (MANDATORY)

Always initialize task tracking for session management:

```python
# MANDATORY: Initialize TodoWrite for all sessions
TodoWrite([
    {"content": "Execute khive plan analysis", "status": "pending", "priority": "high", "id": "session_init_1"},
    {"content": "Apply memory-extracted patterns", "status": "pending", "priority": "high", "id": "session_init_2"},
    {"content": "Begin orchestration work", "status": "pending", "priority": "medium", "id": "session_init_3"}
])
```

### 6. Planning Phase Preparation

Now you're ready for orchestration. Key next steps:

```bash
# For any orchestration task, ALWAYS start with:
uv run khive plan "[detailed task description]"

# This provides:
# - Intelligent agent recommendations with role+domain composition
# - Task complexity analysis and pattern suggestions  
# - Ready-to-execute commands for agent deployment
```

## Critical Rules

1. **ALWAYS** use `uv run khive session init` for session startup
2. **ALWAYS** execute memory queries in batch (not sequential)
3. **ALWAYS** use `uv run khive plan` before any orchestration
4. **NEVER** delegate session initialization to Task agents
5. **ALWAYS** load memory context before starting new work
6. **ALWAYS** apply proven patterns from memory insights

## Options

- `--issue NUMBER`: Link session to specific GitHub issue
- `--resume`: Continue from previous session with additional context
- `--depth DAYS`: How far back to search memories (default: 7)

## Example Workflow

```bash
/session-start
# Then: uv run khive session-start

# Resume with issue context  
/session-start --issue 123 --resume

# Recent context only
/session-start --depth 1
```

## Success Output

```markdown
## 🦁 Lion Orchestrator Session Initialized

### 📋 Project Context

- **Project**: liongate (khive AI autonomous orchestration platform)
- **Repository**: Current working directory
- **Branch**: main (current working branch)
- **Date**: 2025-07-06 20:06:10 PST
- **Creator**: Ocean (HaiyangLi)
- **Orchestrator**: lion (Language Interoperable Network)

### 🔄 Git Status

- **Modified Files**: 26 files with pending changes
- **Last Commit**: 1b5cb522 - "Merge pull request #46 from
  khive-ai/feat/update-claude-code"
- **Active Issue**: #{issue_number} (if linked)

### 🧠 Memory Context Loaded

- **Total Memories**: {count} relevant items across {days} days
- **Preferences**: {preference_count} user/system preferences
- **Orchestration Patterns**: {pattern_count} proven workflows
- **Performance Data**: {performance_count} efficiency metrics
- **Session History**: {session_count} previous sessions analyzed

### 📚 Recent Work Summary

- **Completed**: {completed_tasks_count} tasks in last {days} days
- **Key Achievements**:
  - {recent_summary_1}
  - {recent_summary_2}
  - {recent_summary_3}
- **Patterns Learned**: {learned_patterns_count} new orchestration patterns
- **Pending Summaries**: {pending_summaries_count} conversation summaries
  awaiting diary processing

### 🎯 Current Priorities

**High Priority:**

1. {high_priority_1} (Est: {time_estimate_1})
2. {high_priority_2} (Est: {time_estimate_2})

**Medium Priority:** 3. {medium_priority_1} (Issue #{issue_num}) 4.
{medium_priority_2} (Issue #{issue_num})

**Low Priority:** 5. {low_priority_1} (Technical debt)

### 🧠 Recommended Neural Patterns

- **{pattern_1}** for {task_type_1} (Success rate: {success_rate_1}%)
- **{pattern_2}** for {task_type_2} (Success rate: {success_rate_2}%)
- **{pattern_3}** for {task_type_3} (Success rate: {success_rate_3}%)

### ⚡ Next Steps

1. Execute batched memory queries for detailed context
2. Load neural patterns for optimal orchestration
3. Initialize todo tracking for session management

**🚨 CRITICAL REMINDER**: Use `uv run khive plan "[task]"` for ALL orchestration
tasks

Ready to begin orchestration. Use `/help` for available commands.
```

## Best Practices

### Memory Learning Loop

During your session, continuously improve:

```python
# When you discover effective patterns:
mcp__memory__save(
    f"Pattern {pattern_name} worked well for {task_type} - achieved {success_metrics}",
    type="fact",
    topics=["orchestration", "patterns", "success"]
)

# When you complete tasks:
mcp__memory__save(
    f"Session outcome: {task_summary} - Pattern: {pattern_used} - Quality: {quality_score}",
    type="event", 
    topics=["session", "completion", "outcomes"]
)
```

### Session Flow

1. **Initialize** → Load context and patterns
2. **Plan** → Always use `uv run khive plan`
3. **Execute** → Apply proven orchestration patterns
4. **Learn** → Save successful approaches to memory
5. **Complete** → Use `uv run khive session end` for diary

## Important Notes

- **STOP** after session initialization - wait for specific tasks
- Session initialization prepares context but doesn't execute work
- All actual orchestration should follow the proven patterns loaded during
  initialization
