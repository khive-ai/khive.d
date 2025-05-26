# Khive Git CLI

Natural language git operations for humans and AI agents. Express what you want
to do, not how to do it.

## Installation

```bash
pip install khive[git]
```

## Quick Start

```bash
# Save your work
khive git "save my progress"

# Check what's happening
khive git "what changed?"

# Share for review
khive git "create a PR"

# Interactive mode
khive git -i
```

## Features

### 🗣️ Natural Language Interface

No need to remember git commands. Just say what you want:

```bash
# Instead of: git add -A && git commit -m "feat: add OAuth" && git push
khive git "I finished implementing OAuth"

# Instead of: git status && git diff
khive git "show me what changed"

# Instead of: git checkout -b feature/payments
khive git "start working on payment integration"
```

### 🧠 Intelligent Context

The CLI understands your workflow and maintains context:

```bash
# Provide context for better commits
khive git "implemented the login feature" \
  --context "Added OAuth2 with PKCE support" \
  --issues 123,456

# Continue where you left off
khive git "push those changes"  # Remembers your session
```

### 🎯 Smart Workflows

Multi-step operations are handled automatically:

```bash
# This single command will:
# 1. Commit your changes with a good message
# 2. Push to remote
# 3. Create a pull request
# 4. Assign optimal reviewers
khive git "ready to share this for review"
```

### 🎨 Beautiful Output

Rich, colorful output that's easy to understand:

- ✅ Clear status indicators
- 📁 File change trees
- 💡 Actionable recommendations
- 🎯 Next step suggestions

### 🤖 AI Agent Friendly

Perfect for AI assistants and automation:

```bash
# JSON output for parsing
khive git "analyze code quality" --json

# Session continuity for agents
khive git "save progress" --session abc123 --agent-id my-bot
```

## Usage Modes

### 1. Single Command Mode

Quick operations with immediate results:

```bash
khive git "save my changes"
khive git "what's the status?"
khive git "undo the last commit"
```

### 2. Interactive Mode

Guided, conversational interface:

```bash
khive git --interactive
# or
khive git -i

> What would you like to do? save my progress
✅ Saving implementation progress...

Would you like to add more context? (y/N) y
What are you working on? OAuth implementation
Related issue numbers? 123

✅ Created commit: abc1234
```

### 3. Session Mode

Continue where you left off:

```bash
# First command creates a session
khive git "starting work on the API"

# Later commands continue the session
khive git "I've added the endpoints"
khive git "ready for review"
```

### 4. Status Mode

Quick repository overview:

```bash
khive git --status
# or
khive git -s

╭─ Repository Status ──────────────────╮
│ Branch         │ feature/oauth      │
│ Work Phase     │ implementing       │
│ Has Changes    │ Yes                │
│ Commits Ahead  │ 3                  │
╰──────────────────────────────────────╯
```

## Command Examples

### Development Flow

```bash
# Start a feature
khive git "create a branch for user authentication"

# Save progress
khive git "implemented the login endpoint"

# Add tests
khive git "added unit tests for auth"

# Share for review
khive git "this is ready for review"

# Address feedback
khive git "fixed the issues reviewers mentioned"

# Complete the feature
khive git "all feedback addressed, ready to merge"
```

### Analysis & Understanding

```bash
# Understand changes
khive git "explain what changed in the auth module"

# Analyze quality
khive git "check code quality"

# Review history
khive git "show me the recent commits"

# Find patterns
khive git "what patterns are used in this codebase?"
```

### Maintenance

```bash
# Clean up
khive git "clean up old branches"

# Organize
khive git "organize the repository"

# Fix mistakes
khive git "undo the last commit"
khive git "revert commit abc123"
```

## Advanced Options

### Context Flags

Provide rich context for better results:

```bash
khive git "save progress" \
  --context "Implemented OAuth2 with PKCE" \
  --issues 123,456 \
  --requirements "Must support refresh tokens|Secure storage" \
  --decisions "Used authlib|Session-based tokens"
```

### Session Management

```bash
# Continue specific session
khive git "push changes" --session git-abc123

# Set agent identity
khive git "save" --agent-id khive-implementer
```

### Output Control

```bash
# JSON output for automation
khive git "status" --json

# Verbose mode for debugging
khive git "create pr" --verbose

# Specify commit style
khive git "save" --commit-style detailed
```

## Interactive Mode Commands

When in interactive mode, these special commands are available:

- `help` - Show help information
- `status` - Show repository status
- `history` - Show command history
- `exit` - Exit interactive mode

## Configuration

The CLI stores configuration in `~/.khive/`:

- `git_session.json` - Current session information
- `git_history.json` - Command history

## Environment Variables

- `KHIVE_AGENT_ID` - Default agent identifier
- `NO_COLOR` - Disable colored output

## Tips

1. **Be Natural**: Write like you're talking to a colleague
2. **Provide Context**: More context = better results
3. **Use Sessions**: Let the CLI maintain context for you
4. **Trust the Intelligence**: It understands git workflows

## Common Workflows

### Feature Development

```bash
khive git -i
> I'm starting work on the payment feature
> I've added the Stripe integration
> The tests are passing now
> Ready to share this for review
```

### Quick Fixes

```bash
khive git "fix typo in README" --issues 789
```

### Code Review

```bash
khive git "check out PR 123"
khive git "the code looks good but needs tests"
```

### Release Process

```bash
khive git "prepare release version 2.0.0"
```

## Troubleshooting

### "No git repository found"

Make sure you're in a git repository directory.

### "Session expired"

Sessions expire after 2 hours. Start a new session or use `--continue-session`.

### "Command not understood"

Try rephrasing more naturally or use `--interactive` mode for guidance.

## Integration with Other Tools

The Git CLI works seamlessly with other Khive tools:

```bash
# Format code and commit
khive fmt && khive git "formatted code"

# Run tests and share if passing
khive ci && khive git "tests passing, ready for review"

# Clean branches after PR merge
khive pr merge && khive git "clean up old branches"
```

## Contributing

The Git CLI is part of the Khive project. To contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a PR

## License

Apache 2.0 - See LICENSE file for details.
