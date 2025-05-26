# 🔍 Reviewer CLI Extension

_You have all global commands plus:_

## Reviewer Tools

### khive new-doc - Your Templates

- `khive new-doc CRR <issue>` - Code Review Report (PRIMARY)

### Review Commands (Python-aware)

# Check out and test

gh pr checkout <number> khive ci --verbose # See all test output

# Coverage verification

uv run pytest --cov=src | grep TOTAL # Quick coverage check uv run coverage
report # Detailed coverage

# Code quality checks

uv run pre-commit run --all-files # Should pass grep -r "TODO\|FIXME" . # Find
issues

### PR Review

gh pr review --approve|request-changes|comment [Examples of good review
comments]

# Enough Python to review, not to implement

### Review Commands

```bash
# PR Management
khive pr              # Create PR with smart defaults
gh pr checkout <num>  # Check out PR locally
gh pr review <num> --approve -b "LGTM"
gh pr review <num> --request-changes -b "See comments"

# Quality Checks
khive ci --verbose    # See detailed test output
grep -r "TODO\|FIXME\|HACK" --include="*.py" .

# Fast Review Function
review_pr() {
    gh pr checkout $1
    khive ci
    echo "=== Coverage ==="
    uv run pytest --cov=src | grep TOTAL
    echo "=== Issues ==="
    grep -r "TODO\|print(" --include="*.py" .
}
```
