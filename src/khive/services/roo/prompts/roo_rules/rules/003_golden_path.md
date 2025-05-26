---
title: "The Practical Golden Path: Hub-and-Spoke Workflow"
by: "khive Team"
created: "2025-04-05"
updated: "2025-05-09"
version: "1.7"
description: >
  Practical coding standards for khive. Designed to be easy to follow from the terminal with the khive helper scripts; enforced in Quality Review & CI.
---

# 🛤️ The Golden Path: Orchestrator-Centric Workflow

> **Core Principle**: All work flows through the Orchestrator. No direct
> mode-to-mode communication. ALWAYS CHECK WHICH BRANCH YOU ARE ON !!! ALWAYS
> CHECK THE ISSUE YOU ARE WORKING ON !!!

## 🎯 The Communication Model

```
                 ┌─────────────┐
                 │ Orchestrator│
                 └──────┬──────┘
                        │
     ┌─────────────────┼─────────────────┐
     │                 │                 │
┌────▼────-┐      ┌────▼────┐      ┌────▼────--┐
│Researcher│      │Architect│      │Implementer│
└─────────-┘      └─────────┘      └──────────-┘
```

**Every interaction follows this pattern:**

1. Orchestrator assigns subtask with context
2. Mode executes and reports back
3. Orchestrator evaluates and assigns next subtask

---

## 📋 Orchestrator Task Assignment Templates

### To Researcher: Starting Investigation

```markdown
SUBTASK: Research authentication approaches for CLI tool TYPE: Technical
Investigation PRIORITY: High DUE: 2 hours max

CONTEXT:

- Issue #123 requires secure CLI authentication
- No browser popups allowed (pure CLI)
- Must support CI/CD environments
- Previous attempt with OAuth failed (see comment #123-4)

SPECIFIC DELIVERABLES:

1. Create RR-123.md using template
2. Research these specific questions:
   - How do GitHub CLI, AWS CLI, Stripe CLI handle auth?
   - What are security implications of token storage methods?
   - How to handle token refresh without user interaction?
3. Include comparison matrix with pros/cons
4. Cite all findings with (pplx:xxx) format

SEARCH GUIDANCE: Start with: "Comparative analysis GitHub CLI AWS CLI Stripe CLI
authentication mechanisms focusing on token storage security offline usage
patterns and CI/CD compatibility requirements in 2024-2025"

IF NO RESULTS: Try breaking down into components (token storage, refresh
mechanisms, etc.)

REPORT BACK: Comment on Issue #123 with "Research complete - see RR-123.md"
```

### To Architect: Design Phase

```markdown
SUBTASK: Design authentication system based on research TYPE: Technical Design
PRIORITY: High CONTEXT PATH: .khive/reports/rr/RR-123.md

BACKGROUND:

- Researcher found token file approach most suitable
- System keyring adds complexity for minimal benefit
- Need to support multiple accounts (not researched fully)

SPECIFIC DELIVERABLES:

1. Create TDS-123.md with complete technical design
2. Must address:
   - Token storage interface (abstract for testing)
   - File format and permissions
   - Refresh mechanism (atomic operations required)
   - Multi-account support (design even without full research)
3. Include error handling patterns
4. Add risks section with mitigations

VALIDATION QUERIES: Use these to verify design choices: "Token file atomic write
operations filesystem consistency guarantees POSIX systems with specific focus
on preventing corruption during concurrent access and power loss scenarios"

CONSTRAINTS:

- Keep it simple (KISS principle)
- Must be testable
- Consider Windows/Mac/Linux differences

REPORT BACK: Comment on Issue #123 with "Design complete - see TDS-123.md"
```

### To Implementer: Build Phase

```markdown
SUBTASK: Implement authentication system per design TYPE: Implementation
PRIORITY: High DESIGN DOC: .khive/reports/tds/TDS-123.md

IMPLEMENTATION CHECKLIST:

1. Create IP-123.md implementation plan first
2. Required modules (from TDS section 3):
   - auth/token_store.py (interface)
   - auth/file_store.py (main implementation)
   - auth/cli_commands.py (login/logout commands)
3. Test requirements:
   - Unit tests with 85%+ coverage
   - Integration test for full auth flow
   - Test atomic write behavior

CRITICAL REQUIREMENTS:

- Token file permissions MUST be 0600
- Refresh must not lose tokens on failure
- Clear error messages for permission issues

BRANCH: feat/cli-auth-123

VALIDATION SEARCHES: If stuck on implementation details: "Python atomic file
write operations using tempfile and os.replace with proper error handling for
cross-platform compatibility focusing on permission preservation and fsync
guarantees"

REPORT BACK:

1. Push all code to branch
2. Comment "Implementation complete - PR #xxx ready for review"
```

---

## 🔄 Mode Response Templates

### Researcher Response Pattern

```markdown
@khive-orchestrator

✅ Research subtask complete

DELIVERABLE: RR-123.md created at .khive/reports/rr/RR-123.md

KEY FINDINGS:

1. Token file approach used by 80% of CLI tools (pplx:abc123)
2. System keyring only 5% adoption due to complexity (pplx:def456)
3. Refresh handled via background process in most cases (pplx:ghi789)

GAPS IDENTIFIED:

- Multi-account patterns not well documented
- Windows-specific token storage unclear

RECOMMENDATION: Proceed with token file approach, defer keyring to v2

NEXT SUGGESTED STEP: Architect can design with token file focus

Time spent: 1.5 hours Searches performed: 7 (all cited in document)
```

### When Researcher Gets Stuck

```markdown
@khive-orchestrator

⚠️ Research subtask partially complete

DELIVERABLE: RR-123.md (partial) at .khive/reports/rr/RR-123.md

COMPLETED:

- Token storage methods researched
- Security implications documented

BLOCKED ON:

- No information found on "CLI auth in airgapped environments"
- Tried queries:
  1. "CLI authentication offline environments airgapped systems..."
  2. "Developer tools authentication without internet access..."
  3. "Offline token validation strategies CLI applications..."

RECOMMENDATION:

- Proceed without airgapped support, or
- Consult human expert, or
- Design for online-only in v1

Time spent: 2 hours (hit time limit)
```

### Implementer Success Response

```markdown
@khive-orchestrator

✅ Implementation subtask complete

DELIVERABLES:

- IP-123.md implementation plan
- Code pushed to feat/cli-auth-123
- PR #456 created

IMPLEMENTATION SUMMARY:

- All modules from TDS implemented
- Test coverage: 87.3%
- CI passing (all green)

KEY DECISIONS MADE:

- Used os.replace for atomic writes (pplx:xyz789)
- Added retry logic for lock contention
- Simplified error messages per UX research

NOTES FOR REVIEWER:

- Pay attention to auth/file_store.py line 45-67 (tricky logic)
- Windows tests mocked due to CI limitations

READY FOR: Code review
```

---

## 🎯 Smart Search Patterns

### Effective Perplexity Queries (15-30 words with context)

```bash
# DON'T: Too short, no context
"python token storage"

# DO: Context-rich query
khive info search --provider perplexity --query \
  "Python secure token storage implementation patterns for CLI applications \
   comparing filesystem keyring and memory approaches with focus on \
   cross-platform compatibility and CI/CD environment support 2024-2025"

# DO: Problem-specific query
khive info search --provider perplexity --query \
  "Debugging Python asyncio connection pool exhaustion when connections \
   marked as closed remain in TIME_WAIT preventing new allocations \
   specifically in aioredis with Redis 7.x in Kubernetes environments"

# DO: Comparison query
khive info search --provider perplexity --query \
  "Comparative analysis FastAPI Litestar Django performance characteristics \
   for high-throughput REST APIs with focus on async request handling \
   memory usage patterns and production deployment considerations 2025"
```

---

## 🚦 Autonomous Operation Guidelines

### For All Modes: When Stuck

```
Have I spent 30 minutes on this blocker?
├─ No → Try different search angles
└─ Yes → Have I tried 3+ different searches?
    ├─ No → Reformulate query with different terms
    └─ Yes → Report to Orchestrator with:
        - What you tried
        - What you found (even if not useful)
        - Suggested alternatives

Never spend >2 hours without reporting back
```

### For Orchestrator: Task Assignment

```
Is the context complete for the mode?
├─ No → Add missing context before assigning
└─ Yes → Is the task scope clear?
    ├─ No → Break down into smaller subtasks
    └─ Yes → Does mode have all file paths?
        ├─ No → Specify exact locations
        └─ Yes → Assign with deadline
```

---

## 📝 The Meta Rules for Autonomous Operation

1. **Orchestrator owns the workflow** - All work assignments and completions go
   through them
2. **Modes own their expertise** - Trust each mode to handle their domain
3. **Documentation over memory** - Write everything down, assume no shared
   context
4. **Time-boxed exploration** - 2 hours max before reporting back
5. **Clear completion signals** - Every task ends with explicit status report

Remember: The Orchestrator is the project manager with the full picture. Trust
their task assignments and provide clear, actionable status updates.
