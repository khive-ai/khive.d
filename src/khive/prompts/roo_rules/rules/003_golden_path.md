---
title: "The Practical Golden Path: Hub-and-Spoke Workflow"
by: "khive Team"
created: "2025-04-05"
updated: "2025-05-09"
version: "2.0"
description: >
  Practical coding standards for khive. Designed to be easy to follow from the terminal with the khive helper scripts; enforced in Quality Review & CI.
---

# 🛤️ The Golden Path: Service-Orchestrated Workflow

> **Core Principle**: All work flows through intelligent services coordinated by
> the Orchestrator. Express **what** you want, let services figure out **how**.

## 🎯 The Service Architecture Model

```
                 ┌─────────────┐
                 │ Orchestrator│ (Coordinates services & modes)
                 └──────┬──────┘
                        │
     ┌─────────────────┼─────────────────┐
     │                 │                 │
┌────▼────┐      ┌────▼────┐      ┌────▼────--┐
│Researcher│     │Architect│      │Implementer│
└────┬────┘      └────┬────┘      └─────┬────-┘
     │                │                  │
     └────────────────┴──────────────────┘
              🔧 8 Intelligent Services
     (khive dev|git|info|fmt|ci|mcp|new-doc|init)
```

**Every interaction follows this pattern:**

1. Orchestrator assigns **intent-based** subtask
2. Mode uses **services** to execute
3. Services handle complexity, mode reports **outcomes**

---

## 🎯 Modern Service Overview

### The 8 Intelligent Services

| Service         | Purpose                  | Natural Language Examples                               |
| --------------- | ------------------------ | ------------------------------------------------------- |
| `khive dev`     | Development intelligence | "check my code", "fix all issues", "diagnose problems"  |
| `khive git`     | Natural git operations   | "save my progress", "ready for review", "what changed?" |
| `khive info`    | Synthesized insights     | "research OAuth patterns", "analyze our architecture"   |
| `khive fmt`     | Smart formatting         | (Usually called by khive dev automatically)             |
| `khive ci`      | Intelligent testing      | (Usually called by khive dev automatically)             |
| `khive mcp`     | Secure external ops      | "khive mcp call github create_issue --title..."         |
| `khive new-doc` | Template creation        | "khive new-doc RR 123"                                  |
| `khive init`    | Project setup            | "khive init" (auto-detects stack)                       |

---

## 📋 Modern Task Assignment Templates

### To Researcher: Investigation with Services

```markdown
SUBTASK: Research authentication approaches for CLI tool TYPE: Technical
Investigation PRIORITY: High TIME_BUDGET: 2 hours max

CONTEXT:

- Issue #123 requires secure CLI authentication
- No browser popups allowed (pure CLI)
- Must support CI/CD environments
- Previous OAuth attempt failed (see comment #123-4)

DELIVERABLES:

1. Create RR-123.md using `khive new-doc RR 123`
2. Use `khive info` to research:
   - "How do GitHub CLI, AWS CLI, Stripe CLI handle authentication"
   - "Security implications of token storage in CLI applications"
   - "Token refresh strategies without user interaction"
3. Document synthesized insights with citations

SERVICE GUIDANCE:

- Primary: `khive info` for research synthesis
- Use detailed queries with context (20-30 words)
- Service will provide citations automatically

REPORT BACK: "Research complete - see RR-123.md"
```

### To Architect: Design with Intelligence

```markdown
SUBTASK: Design authentication system based on research TYPE: Technical Design
PRIORITY: High CONTEXT: Research in .khive/reports/rr/RR-123.md

BACKGROUND:

- Token file approach recommended
- Need atomic operations for safety
- Multi-account support required

DELIVERABLES:

1. Create TDS-123.md with `khive new-doc TDS 123`
2. Design complete system with:
   - Clear interfaces (what, not how)
   - Service-friendly architecture
   - Risk assessment

VALIDATION:

- Use `khive info` to validate design decisions
- Example: "Trade-offs between file vs keyring token storage"

REPORT BACK: "Design complete - see TDS-123.md"
```

### To Implementer: Build with Services

```markdown
SUBTASK: Implement authentication system TYPE: Implementation PRIORITY: High
DESIGN: .khive/reports/tds/TDS-123.md

WORKFLOW:

1. Start: `khive git "starting OAuth implementation for issue 123"`
2. Create plan: `khive new-doc IP 123`
3. Build with continuous validation: `khive dev "check progress"`
4. Save progress: `khive git "implemented token storage"`
5. Complete: `khive git "ready for review"`

SERVICE FEATURES:

- khive git handles branching automatically
- khive dev validates continuously
- khive git creates smart commits

FOCUS ON: Writing quality code, let services handle the rest

REPORT BACK: "Implementation complete - PR #xxx ready"
```

---

## 🔄 Modern Response Patterns

### Researcher Response with Services

```markdown
@khive-orchestrator

✅ Research complete using khive info

DELIVERABLE: RR-123.md at .khive/reports/rr/RR-123.md

SYNTHESIS FROM KHIVE INFO:

- 80% of CLI tools use token files (confidence: high)
- System keyring adds complexity with minimal benefit
- Refresh typically handled via background process

SERVICE INSIGHTS:

- khive info provided 5 synthesized findings
- All citations included automatically
- Follow-up suggestions available

RECOMMENDATION: Token file approach with atomic writes

Time spent: 1.5 hours Service calls: 3 khive info queries
```

### Implementer Response with Services

```markdown
@khive-orchestrator

✅ Implementation complete

SERVICE WORKFLOW EXECUTED:

1. `khive git "start OAuth feature"` - created branch
2. `khive dev "check"` - continuous validation (all green)
3. `khive git "save progress"` - 5 commits created
4. `khive git "ready for review"` - PR #456 created

AUTOMATED RESULTS:

- Test coverage: 87.3% (khive dev verified)
- All checks passing (khive dev ensured)
- PR created with full context

KEY DECISIONS:

- Used atomic file operations (khive info helped research)
- Added retry logic for robustness

READY FOR: Review
```

---

## 🎯 Service Usage Patterns

### Research with khive info

```bash
# DON'T: Vague queries
khive info "OAuth"

# DO: Detailed context-rich queries
khive info "Compare OAuth token storage methods for CLI tools focusing on security and offline capability"

# DO: Problem-specific research
khive info "Debug Python asyncio connection pool exhaustion in Kubernetes environments"

# DO: Architecture validation
khive info "Trade-offs between monolith vs microservices for AI workloads"
```

### Development with khive git/dev

```bash
# Starting work
khive git "starting work on payment feature for issue 45"

# Regular progress saves
khive git "implemented Stripe webhook handling"

# Validation
khive dev "check everything"  # Runs ALL validations

# Completion
khive git "feature complete, ready for review"
```

### Diagnosis with khive dev

```bash
# When things go wrong
khive dev "why are tests failing?"
khive dev "analyze performance issues"
khive dev "check security vulnerabilities"
```

---

## 🚦 Service-Aware Autonomy Guidelines

### When Stuck with Services

```
Has the service helped resolve the issue?
├─ No → Try rephrasing your intent
└─ Still stuck → Have you tried different service modes?
    ├─ No → Try diagnostic mode: khive dev --diagnostic
    └─ Yes → Report to Orchestrator with:
        - What you asked services
        - What responses you got
        - What you expected

Services learn from usage - report unclear responses
```

### For Orchestrator: Service Delegation

```
Is the task expressed as an intent?
├─ No → Rephrase as what, not how
└─ Yes → Does it specify which services might help?
    ├─ No → Add service hints
    └─ Yes → Is success criteria clear?
        ├─ No → Define expected outcomes
        └─ Yes → Delegate with confidence
```

---

## 📝 Service Intelligence Features

### What Services Do Automatically

1. **khive git**
   - Creates appropriate branch names
   - Generates semantic commit messages
   - Handles push and PR creation
   - Maintains work context

2. **khive dev**
   - Runs all relevant checks
   - Fixes auto-fixable issues
   - Provides actionable insights
   - Suggests next steps

3. **khive info**
   - Searches multiple sources
   - Synthesizes findings
   - Provides citations
   - Suggests follow-ups

### What You Focus On

1. **Clear Intent Expression**
   - Say what you want to achieve
   - Provide context when helpful
   - Let services handle details

2. **Quality Outcomes**
   - Well-designed systems
   - Clean, tested code
   - Clear documentation
   - Thoughtful reviews

---

## 🚀 Example: Complete Feature Workflow

### 1. Orchestrator Creates Issue

```bash
gh issue create --title "Add OAuth authentication" \
  --body "Need secure CLI auth without browser popups"
```

### 2. Research Phase

```bash
# Researcher
khive info "Research OAuth patterns for CLI tools without browser popups"
khive new-doc RR 123
# Service provides synthesis, researcher adds interpretation
```

### 3. Design Phase

```bash
# Architect  
khive info "Validate token file storage security for CLI applications"
khive new-doc TDS 123
# Service provides evidence, architect creates design
```

### 4. Implementation Phase

```bash
# Implementer
khive git "starting OAuth implementation for issue 123"
# ... write code ...
khive dev "check my progress"
khive git "implemented secure token storage"
# ... more code ...
khive git "ready for review - OAuth implementation complete"
```

### 5. Review Phase

```bash
# Reviewer
git checkout pr-123
khive dev "comprehensive diagnostic review"
khive new-doc CRR 123
gh pr review 123 --comment --body "Review complete - see CRR-123.md"
```

### 6. Documentation Phase

```bash
# Documenter
khive info "what needs documenting for OAuth features?"
# ... update docs ...
khive git "updated OAuth documentation"
```

---

## 🎯 The Meta Rules - Service Edition

1. **Services own complexity** - You own intent and quality
2. **Natural language first** - Express what, not how
3. **Trust service intelligence** - But verify outcomes
4. **Context enables autonomy** - Share why, not just what
5. **Outcomes over process** - Focus on results

Remember: The new khive turns tedious command sequences into natural
conversations. Express your intent clearly and let the services handle the
complexity!
