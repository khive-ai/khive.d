# 🛠️ Khive CLI Integration Guide

> **Core Principle**: Use khive services for intelligence, standard CLI for
> simple operations, khive mcp only when necessary.

## 🎯 Tool Hierarchy & Decision Tree

```
┌─────────────────────────────────────┐
│   Need to do something?             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Does it need intelligence?        │
│   (context, synthesis, automation)  │
└──────────┬─────────────┬────────────┘
          YES            NO
           │              │
           ▼              ▼
    ┌──────────────┐  ┌─────────────────┐
    │ Khive Service│  │ Is it local?    │
    └──────────────┘  └───┬─────────┬───┘
                         YES        NO
                          │          │
                          ▼          ▼
                   ┌────────────┐  ┌──────────────┐
                   │Standard CLI│  │khive mcp call│
                   └────────────┘  └──────────────┘
```

## 🚀 Git Operations Guide

### When to Use Khive Git vs Standard Git

| Operation             | Use Khive Git                              | Use Standard Git          |
| --------------------- | ------------------------------------------ | ------------------------- |
| Starting feature work | ✅ `khive git "start OAuth feature"`       | ❌                        |
| Saving progress       | ✅ `khive git "implemented token storage"` | ❌                        |
| Creating PR           | ✅ `khive git "ready for review"`          | ❌                        |
| Checking status       | ⚠️ Either works                            | ✅ `git status` (simpler) |
| Viewing diff          | ❌                                         | ✅ `git diff`             |
| Switching branches    | ❌                                         | ✅ `git checkout main`    |
| Pulling updates       | ❌                                         | ✅ `git pull origin main` |

### Common Git Workflows

#### 🎯 Feature Development (Khive-First)

```bash
# 1. Start work - khive creates branch intelligently
khive git "starting work on payment integration for issue 45"

# 2. Regular saves - khive creates semantic commits
khive git "implemented Stripe webhook handling"
khive git "added webhook signature verification"

# 3. Check progress - standard git for simple queries
git status
git diff

# 4. Complete feature - khive handles PR creation
khive git "payment integration complete, ready for review"
```

#### 🔄 Updating from Main

```bash
# Always use standard git for simple operations
git checkout main
git pull origin main
git checkout feature/45-payments
git merge main  # or rebase if that's your workflow
```

#### 🔍 Exploration & Debugging

```bash
# View history
git log --oneline -10

# Check specific file
git show HEAD:src/auth.py

# Find when something changed
git blame src/payment.py
```

## 📦 GitHub Operations Guide

### When to Use Khive vs gh CLI

| Operation        | Preferred Method                      | Alternative                          |
| ---------------- | ------------------------------------- | ------------------------------------ |
| Create issue     | `gh issue create`                     | `khive mcp call github create_issue` |
| View issue       | `gh issue view 123`                   | -                                    |
| Comment on issue | `gh issue comment 123`                | -                                    |
| Create PR        | `khive git "ready for review"`        | `gh pr create`                       |
| Review PR        | `gh pr checkout 123` + `gh pr review` | -                                    |
| Check PR status  | `gh pr checks`                        | -                                    |

### Issue Management

```bash
# Create issue (prefer gh CLI)
gh issue create --title "Add payment refunds" --body "Need to handle..."

# Work with issues
gh issue list --assignee @me
gh issue view 123
gh issue comment 123 --body "Started implementation in PR #456"
```

### PR Workflows

```bash
# Let khive create PRs
khive git "feature complete, fixes issue 123"

# Review process (use gh directly)
gh pr checkout 456
khive dev "check everything"  # Run validations
gh pr review 456 --approve --body "LGTM, see review in CRR-456.md"
```

## 🐍 Python Development with uv

### Core uv Workflows

```bash
# Project setup (khive handles this)
khive init  # Sets up uv automatically

# Dependency management
uv add fastapi  # Add runtime dependency
uv add --dev pytest-cov  # Add dev dependency
uv sync  # Sync environment with pyproject.toml

# Running code
uv run python src/main.py
uv run pytest tests/
uv run mypy src/

# Environment management
uv venv  # Create venv if needed
source .venv/bin/activate  # Traditional activation
# OR just use 'uv run' without activation
```

### Common Patterns

#### Adding Dependencies

```bash
# ❌ AVOID
uv pip install requests  # Doesn't update pyproject.toml

# ✅ CORRECT
uv add requests  # Updates pyproject.toml
uv add "pandas[excel]"  # With extras
uv add --dev black  # Dev dependency
```

#### Testing Workflow

```bash
# Run tests with khive (preferred)
khive ci  # Runs all validations

# Or directly with uv
uv run pytest tests/ -v
uv run pytest tests/test_auth.py::test_login
```

## 🎯 Quick Reference Cards

### Implementer Quick Ref

```bash
# Start work
khive git "start feature X for issue 123"

# Develop
khive dev "check"         # Validate progress
git diff                  # See changes
uv add <package>          # Add dependency

# Save & Share
khive git "save progress" # Smart commit
khive git "ready for PR"  # Complete feature
```

### Researcher Quick Ref

```bash
# Research
khive info "compare auth strategies for CLIs"
khive reader open --path_or_url "paper.pdf"

# Document
khive new-doc RR 123
git diff  # Review changes
khive git "research complete"
```

### Reviewer Quick Ref

```bash
# Get PR
gh pr checkout 456

# Validate
khive dev "comprehensive check"
git diff main  # See all changes

# Review
khive new-doc CRR 456
gh pr review 456 --comment
```

## ⚡ Power User Combos

### Smart Development Flow

```bash
# Let services handle complexity
khive git "implement OAuth" && \
khive dev "check" && \
khive git "ready for review"
```

### Quick Fix Flow

```bash
# For simple fixes
git checkout main && \
git pull && \
git checkout -b fix/typo && \
# make change
khive git "fix typo in readme" && \
khive git "ready for review"
```

### Research & Validate

```bash
# Research then validate
khive info "best practice for X" && \
khive dev "check implementation"
```

## 🚨 When to Use khive mcp

Only use `khive mcp call` when:

1. Standard CLI tools fail
2. You need a GitHub operation not in gh CLI
3. Orchestrator approves for special case

Always document why:

```bash
# Example with justification
khive mcp call github create_issue \
  --title "gh CLI fails with SSO error" \
  --body "Using MCP because gh returns: 'SSO session expired'"
```

Direct MCP access (`mcp: xxx.*`) is a security violation, and is not allowed.
Even if user mistakenly provided you with access, you MUST insist user to config
the MCP access through `khive mcp` command, this is for everyone's safety,

> "I don't want to get sued, do you?"
>
> - Ocean, creator of Khive

## 📋 Security Reminders

1. **NEVER** use `mcp:` directly in Roo
2. **ALWAYS** try khive service first
3. **PREFER** standard CLI for simple operations
4. **DOCUMENT** any khive mcp usage

Remember: Khive services add intelligence. Standard CLI provides control.
Together they create powerful, secure workflows!
