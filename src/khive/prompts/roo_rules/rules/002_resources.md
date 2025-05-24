# Khive Security-First Tooling Guide

> **🔒 Security Rule #1**: NO direct MCP access. All external operations through
> CLI or controlled wrapper.

## Tool Selection Order (STRICT)

### 1️⃣ **Khive CLI** (Always First Choice)

```bash
khive init          # Project setup
khive fmt           # Code formatting
khive ci            # Run tests
khive commit        # Git commit with conventions
khive pr            # Create/manage PRs
khive info          # Search and consult
khive reader        # Read documents
khive new-doc       # Create from templates
khive clean         # Branch cleanup
```

### 2️⃣ **Standard CLI** (When Khive Doesn't Have It)

```bash
git checkout -b     # Branch creation
git diff            # View changes
git status          # Check status
gh issue create     # Create issues
gh issue comment    # Add comments
gh pr review        # Submit reviews
uv run pytest       # Run Python tests
```

### 3️⃣ **Controlled MCP** (Emergency Only - Logged & Audited)

Khive MCP needs to be configured under `.khive/mcps/config.json` file, same as
any other MCP client configuration.

```bash
# ❌ NEVER DO THIS:
mcp: github.create_issue

# ✅ ONLY THIS (when CLI fails):
khive mcp call github create_issue --title "..." --body "..."
```

## Common Workflows - CLI Only

### Creating an Issue

```bash
# Primary method
gh issue create --title "Bug: X happens" --body "Details..."

# Only if gh fails
khive mcp call github create_issue --title "Bug: X happens" --body "Details..."
```

### Working with PRs

```bash
# Create PR
khive pr --title "feat: add feature"

# Review PR
gh pr checkout 123
khive ci
gh pr review 123 --approve -b "LGTM"

# Comment on PR
gh pr comment 123 --body "See review at..."
```

### File Operations

```bash
# Always use local tools
cat file.md
less large_file.py
git show HEAD:path/to/file.py

# Never use MCP for local files
```

## Why This Matters

1. **Security**: External MCP servers could be compromised
2. **Auditability**: All `khive mcp call` operations are logged
3. **Consistency**: Same tools = same results
4. **Control**: We can add features to our CLI as needed

## Red Flags 🚩

If you find yourself:

- Using `mcp:` directly → STOP, use `khive mcp call`
- Needing MCP frequently → Report to Orchestrator for CLI improvement
- Unsure which tool → Default to Khive CLI, ask Orchestrator if stuck

Remember: Every external operation is a potential security risk. CLI tools are
battle-tested and secure.

### Additional Recommendations

1. **Create a Quick Reference Card** for each role showing their most common
   operations:

```markdown
# Quick Ref: Implementer

- Branch: `git checkout -b feat/issue-123`
- Test: `khive ci` or `uv run pytest`
- Format: `khive fmt`
- Commit: `khive commit --type feat --scope api --by khive-implementer`
- PR: `khive pr`
```

2. **Add Examples to Each Role Prompt** showing real workflows:

````markdown
## Example Workflow (No MCP Needed)

```bash
# 1. Start work
git checkout -b feat/issue-123

# 2. Make changes
# ... edit files ...

# 3. Format - if it is in conflict with pre-commit, follow pre-commit
khive fmt

# 4. Test, lint, format check
khive ci

# 5. Commit
khive commit --type feat --scope api --subject "add user auth" --by khive-implementer

# 6. Create PR (auto-pushes)
khive pr --title "feat(api): add user authentication"

# 7. Done! No MCP needed
```
````

3. **Add a Troubleshooting Section**:

````markdown
## When CLI Tools Fail

Before using `khive mcp call`:

1. Check your authentication: `gh auth status`
2. Verify git setup: `git remote -v`
3. Update tools: `uv self update`, `gh extension upgrade --all`
4. Check network: `ping github.com`

If still failing, use wrapped MCP with justification:

```bash
# Document why CLI failed
khive mcp call github create_issue \
  --title "CLI Issue: gh fails with error X" \
  --body "CLI failed because... Using MCP as fallback"
```
````

This approach maintains security while being practical about real-world tool
limitations.
