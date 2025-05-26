## Global CLI Commands - Essential Reference

# 🛠️ Khive Essential CLI Reference

> **Philosophy**: One command, one purpose. Learn these 6 commands to handle 90%
> of your work.

## 🌐 Universal Commands (Every Mode Needs These)

### 1. `khive info` - Your Research Assistant

```bash
# Search the web (ALWAYS use detailed queries)
khive info search --provider perplexity --query \
  "Detailed 20-30 word query with context constraints and timeframe"

# Consult AI for analysis
khive info consult --question "Specific question" --models openai/gpt-4o-mini

# Examples:
khive info search --provider perplexity --query \
  "Python async webhook implementation with retry logic and exponential backoff \
   for production systems handling 10k requests per minute 2024-2025"

khive info consult \
  --question "Compare these two approaches: [approach A] vs [approach B] for our use case" \
  --models openai/gpt-4o-mini
```

### 2. `khive commit` - Smart Git Commits

```bash
# Structured commit (auto-stages, pushes, and formats)
khive commit \
  --type feat|fix|docs|chore \
  --scope module \
  --subject "what changed" \
  --search-id pplx-abc123 \
  --by khive-role

# Quick commit (still smart)
khive commit "feat(api): add user auth (search: pplx-abc123)" --by khive-implementer

# What it does: add → commit → push in one command
```

### 3. `khive new-doc` - Report Templates

```bash
# Create any report with correct template
khive new-doc <TYPE> <issue-number>

# Common types:
khive new-doc RR 123   # Research Report
khive new-doc TDS 123  # Technical Design Spec
khive new-doc IP 123   # Implementation Plan
khive new-doc CRR 123  # Code Review Report

# Creates: .khive/reports/<type>/TYPE-123.md with template
```

### 4. `khive reader` - Document Reader

```bash
# Open any document/URL
khive reader open --path_or_url <path-or-url>
# Returns: doc_id

# Read specific section
khive reader read --doc_id <id> --start_offset 0 --end_offset 1000

# Example flow:
khive reader open --path_or_url "https://arxiv.org/pdf/2301.00001.pdf"
# Returns: {"doc_id": "DOC_123", "length": 45000}
khive reader read --doc_id DOC_123 --end_offset 2000
```

### 5. `git` - Essential Git Operations

```bash
# These specific git commands are universal
git checkout -b <branch-name>     # Create branch
git branch                        # Check current branch
git status                        # Check changes
git diff                          # View changes
git stash save "message"          # Save work temporarily
```

### 6. `gh` - GitHub CLI Basics

```bash
# Issue basics
gh issue create --title "..." --body "..."
gh issue comment <number> --body "..."
gh issue view <number>

# PR basics
gh pr create --title "..." --body "..."
gh pr view <number>
gh pr comment <number> --body "..."
```

## 📍 Quick Decision Guide

| Need to...            | Use this...         | NOT this...          |
| --------------------- | ------------------- | -------------------- |
| Search for info       | `khive info search` | Random googling      |
| Save your work        | `khive commit`      | `git commit` alone   |
| Create report         | `khive new-doc`     | Manual file creation |
| Read research paper   | `khive reader`      | Copy-paste chunks    |
| Create feature branch | `git checkout -b`   | Working on main      |
| Comment on issue      | `gh issue comment`  | Web browser          |

## 🎯 Mode-Specific Extensions

_These are documented in individual role prompts:_

- **Implementer**: `khive ci`, `khive fmt`, `uv run pytest`
- **Reviewer**: `khive pr`, `gh pr review`
- **Orchestrator**: Full `gh` command set
- **Researcher**: Advanced `khive info` patterns
