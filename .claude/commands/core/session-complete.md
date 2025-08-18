# Session Completion Procedure

## Overview

This procedure should be executed at the end of significant sessions to properly
organize, document, and archive session work while capturing lessons learned and
setting up actionable next steps.

## Prerequisites

- Session work has been completed
- All major deliverables have been created
- Final outcomes have been validated
- Ready to consolidate learnings and archive work

## Procedure Steps

### 1. Date Verification (MANDATORY)

```bash
# ALWAYS check current date first - never assume dates
date
# Use actual output for all date-dependent operations
```

### 2. Create Conversation Summary (MANDATORY)

```bash
# Create comprehensive session summary
/compact-convo

# This creates: .khive/notes/summaries/summary_YYYYMMDD_HHMMSS.md
# Including orchestration patterns used, lessons learned, and key outcomes
```

### 3. Process Diary Entries (MANDATORY)

```bash
# Use khive session service to process conversation summaries into diary entries
uv run khive session end

# This processes unprocessed summaries and creates diary entries in:
# .khive/notes/diaries/diary_YYYYMMDD.md
```

### 4. Archive Working Files (If Any)

```bash
# Only if you have temporary working files to archive
if [ -d ".khive/workspace" ] && [ "$(ls -A .khive/workspace 2>/dev/null)" ]; then
    DATE_DIR=$(date +%Y_%m_%d)
    mkdir -p .khive/workspace_archive/${DATE_DIR}/
    mv .khive/workspace/* .khive/workspace_archive/${DATE_DIR}/
fi
```

### 5. Save Key Learnings to Memory (MANDATORY)

Store valuable insights for future sessions:

```python
# Save key orchestration insights
if orchestration_patterns_used:
    for pattern in successful_patterns:
        mcp__memory__save(
            f"ORCHESTRATION SUCCESS: {pattern['name']} pattern achieved {pattern['success_rate']}% success for {pattern['task_type']}",
            type="fact",
            topics=["orchestration", "patterns", "success"]
        )

# Save Ocean's guidance and preferences
for guidance in ocean_guidance_received:
    mcp__memory__save(
        f"OCEAN GUIDANCE: {guidance['context']} - {guidance['instruction']}",
        type="preference", 
        topics=["ocean", "guidance", guidance['domain']]
    )

# Save session outcomes and learnings
mcp__memory__save(
    f"SESSION COMPLETE: {session_topic} - Key outcomes: {outcomes}",
    type="event",
    topics=["session", "completion", session_tags]
)
```

### 6. Create GitHub Issues for Next Steps (If Needed)

For actionable outcomes that require follow-up work:

```bash
# Create issues for concrete next steps
gh issue create \
  --title "Follow-up: [Brief description]" \
  --body "Based on session [date]: [outcome description]

Next actions:
- [ ] [Specific task 1]
- [ ] [Specific task 2]

References:
- Session summary: .khive/notes/summaries/summary_[timestamp].md
- Key insights: [Specific learnings from session]" \
  --label "follow-up"
```

### 7. Verify Session Completion

Check that all steps completed successfully:

```bash
# Verify summary was created
ls -la .khive/notes/summaries/summary_$(date +%Y%m%d)*.md

# Verify diary processing (if summaries existed)
ls -la .khive/notes/diaries/diary_$(date +%Y%m%d).md

# Check git status for any uncommitted work
git status
```

## Session Completion Checklist

Before considering the session complete, verify:

- [ ] **Date verified** with `date` command
- [ ] **Conversation summary created** via `/compact-convo`
- [ ] **Diary entries processed** via `uv run khive session end`
- [ ] **Key learnings saved** to memory MCP
- [ ] **Next steps documented** (GitHub issues if needed)
- [ ] **Verification completed** (files exist, git status clean)

## Session Success Criteria

A successful session completion includes:

1. **Knowledge Preserved**: Summary captures key insights and patterns
2. **Learnings Stored**: Memory MCP contains searchable insights for future
   sessions
3. **Continuity Maintained**: Diary entries provide narrative context
4. **Action Items Clear**: Next steps are documented and trackable
5. **Context Clean**: No loose ends or unclear outcomes

## Common Session Types

### Single Agent Sessions

- Create summary focused on insights and solutions
- Save key patterns or approaches to memory
- Simple completion - no complex orchestration metrics

### Multi-Agent Orchestration Sessions

- Document which patterns worked (parallel_discovery, sequential_pipeline,
  lionagi_flow)
- Record agent composition successes (role+domain combinations)
- Save orchestration lessons learned to memory
- Note quality gate effectiveness (critic agent insights)

### Research/Analysis Sessions

- Focus on discoveries and breakthrough insights
- Document Ocean's guidance and course corrections
- Save research patterns and methodologies
- Create issues for follow-up investigation if needed

### Implementation Sessions

- Emphasize technical solutions and code patterns
- Document debugging approaches that worked
- Save architectural decisions and trade-offs
- Ensure deliverables are properly committed/documented

## Best Practices

### Efficient Session Completion

1. **Run `/compact-convo` early** - Don't wait until context is full
2. **Be selective with memory saves** - Focus on truly valuable insights
3. **Use practical language** - Avoid theoretical concepts in documentation
4. **Create actionable next steps** - Concrete tasks, not vague intentions
5. **Verify completion** - Check that files were actually created

### Quality Focus

- **Accuracy over completeness** - Better to document key insights well than
  everything superficially
- **Future utility** - Will this be useful in 3 months?
- **Searchable content** - Use clear, descriptive language for memory entries
- **Context preservation** - Capture enough context for future understanding

---

**This streamlined procedure ensures systematic session completion with
practical knowledge preservation and clear next steps.**
