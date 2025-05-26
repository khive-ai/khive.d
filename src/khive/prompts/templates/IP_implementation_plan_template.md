---
title: "Implementation Plan Template"
by: "khive-implementer"
created: "2025-04-12"
updated: "2025-04-12"
version: "1.1"
doc_type: "IP"
output_subdir: "ip"
description: "Implementation planning for service-based development"
---

# Guidance

**Purpose**\
Plan implementation leveraging khive services for maximum efficiency.

**Service Integration**

- Plan around service capabilities
- Focus on business logic tasks
- Let services handle infrastructure

---

# Implementation Plan: [Component Name]

## 1. Service-Based Approach

### 1.1 Development Setup

```bash
# One command setup
khive init  # Auto-detects and configures project

# Start feature
khive git "starting [component] implementation for issue X"
```

### 1.2 Service Utilization Plan

| Service    | Purpose                 | When to Use                       |
| ---------- | ----------------------- | --------------------------------- |
| khive git  | Branching, commits, PRs | Start, progress saves, completion |
| khive dev  | Validation, testing     | After each component completion   |
| khive info | Problem solving         | When stuck or need patterns       |

## 2. Implementation Phases

### 2.1 Phase 1: Foundation

**Intent:** Set up basic structure and interfaces

**Service Workflow:**

```bash
khive git "implement base service structure"
khive dev "validate structure"
khive git "save foundation phase"
```

**Focus Tasks:**

- Define interfaces (what, not how)
- Create base models
- Set up test structure

### 2.2 Phase 2: Core Logic

**Intent:** Implement business logic

**Service Assistance:**

- Use `khive info` for algorithm research
- Use `khive dev` for continuous validation
- Let `khive git` handle version control

**Focus Tasks:**

- Implement core algorithms
- Handle business rules
- Add error cases

## 3. Test Strategy with Services

### 3.1 Service-Driven Testing

```python
# khive dev will automatically run these
def test_component_basics():
    """khive dev ensures >80% coverage"""
    # Write clear, focused tests
    # Service handles coverage reporting
    pass

# khive dev provides performance metrics
def test_performance():
    """Service validates performance automatically"""
    pass
```

### 3.2 Continuous Validation

- After each function: `khive dev "quick check"`
- After each module: `khive dev "full check"`
- Before PR: `khive dev "comprehensive diagnostic"`

## 4. Implementation Tasks

### 4.1 Task Breakdown

| ID | Task Description     | Service Support              | Focus On         |
| -- | -------------------- | ---------------------------- | ---------------- |
| T1 | Create service class | khive git handles branches   | Clean interfaces |
| T2 | Implement auth logic | khive info provides patterns | Business logic   |
| T3 | Add error handling   | khive dev validates coverage | Domain errors    |
| T4 | Write tests          | khive ci runs automatically  | Test cases       |

### 4.2 Natural Language Tasks

Instead of detailed steps:

1. "Implement token storage with atomic writes"
2. "Add refresh logic with exponential backoff"
3. "Create comprehensive test suite"

Let services figure out the details.

## 5. Progress Tracking

### 5.1 Service-Based Checkpoints

```bash
# Regular progress saves
khive git "completed phase 1 - basic structure"
khive git "added token storage logic"
khive git "implemented refresh mechanism"

# Service tracks progress automatically
```

### 5.2 Validation Milestones

- [ ] khive dev shows all green
- [ ] Coverage >80% (automatic with khive dev)
- [ ] khive git created PR
- [ ] khive dev diagnostic passes

## 6. Problem Resolution

### 6.1 When Stuck

```bash
# Get help from services
khive info "how to implement [specific problem]"
khive info "debug [error message]"
khive dev "why is this test failing?"
```

### 6.2 Service Intelligence

Services provide:

- Error explanations
- Solution patterns
- Performance insights
- Security warnings

## 7. Completion Criteria

### 7.1 Service Validations

- [ ] `khive dev --check` all green
- [ ] `khive dev --diagnostic` no issues
- [ ] `khive git "ready for review"` creates PR
- [ ] All tests pass in CI (automatic)

### 7.2 Manual Checks

- [ ] Code expresses clear intent
- [ ] Business logic is correct
- [ ] Edge cases handled

## 8. Handoff

```bash
# Simple completion
khive git "implementation complete, ready for review"
# Service handles: commit, push, PR creation, linking issues
```

````
## 🩺 Code Review Report (CRR) - Updated

```markdown
---
title: "Code Review Report Template"
by: "khive-reviewer"
created: "2025-04-12"
updated: "2025-01-16"
version: "2.0"
doc_type: "CRR"
output_subdir: "crr"
description: "Service-assisted code review template"
---

# Guidance

**Purpose**  
Review code quality beyond what services automatically check.

**Service Integration**
- Use `khive dev --diagnostic` for comprehensive analysis
- Focus on design and business logic
- Let services handle mechanical checks

---

# Code Review: [Component Name]

## 1. Service-Based Review Summary

### 1.1 Automated Checks (via khive dev)

```bash
# Service validation performed
khive dev "comprehensive diagnostic review"
````

| Check        | Result     | Service Report                |
| ------------ | ---------- | ----------------------------- |
| Tests        | ✅ Pass    | All tests green, coverage 87% |
| Security     | ✅ Pass    | No vulnerabilities detected   |
| Performance  | ⚠️ Warning | Minor optimization possible   |
| Code Quality | ✅ Pass    | Complexity within limits      |

### 1.2 Manual Review Focus

Since services validated mechanical aspects, this review focuses on:

- Design adherence
- Business logic correctness
- Code clarity and intent
- Error handling completeness

## 2. Design Compliance

### 2.1 Specification Adherence

| Aspect              | Compliance | Notes                            |
| ------------------- | ---------- | -------------------------------- |
| API Contracts       | ✅ Full    | Matches TDS exactly              |
| Data Models         | ✅ Full    | All fields implemented           |
| Service Integration | ⚠️ Partial | Could better leverage khive info |

### 2.2 Architecture Review

The implementation correctly:

- ✅ Uses service-friendly interfaces
- ✅ Leverages khive git for workflow
- ⚠️ Could better utilize khive info for runtime decisions

## 3. Code Quality Beyond Services

### 3.1 Intent Clarity

**Excellent Example:**

```python
async def refresh_token_with_backoff(self) -> Token:
    """Clear intent, service-friendly implementation"""
    # khive info validated this pattern
    for attempt in range(self.max_retries):
        try:
            return await self._attempt_refresh()
        except TokenRefreshError:
            await self._exponential_backoff(attempt)
    raise TokenRefreshFailure("All retries exhausted")
```

### 3.2 Business Logic Review

- ✅ Correctly implements token refresh logic
- ✅ Handles edge cases appropriately
- ⚠️ Could add more specific error types

## 4. Service Integration Review

### 4.1 Service Usage Patterns

**Good Pattern Observed:**

```python
# Developer effectively used services
# Regular commits with khive git
# Continuous validation with khive dev
```

**Improvement Opportunity:**

```python
# Could use khive info for runtime optimization
# Example: Dynamic timeout adjustment based on patterns
```

## 5. Recommendations

### 5.1 Immediate Improvements

1. Add service-discovered optimization for batch operations
2. Implement khive info suggestion for caching strategy

### 5.2 Future Enhancements

1. Integrate khive info for adaptive behavior
2. Add service telemetry for monitoring

## 6. Review Conclusion

### 6.1 Service Metrics

- khive dev: All checks passed
- Test coverage: 87% (exceeds requirement)
- Performance: Within targets

### 6.2 Manual Assessment

- Design compliance: Excellent
- Code clarity: Very good
- Service integration: Good (room for improvement)

### 6.3 Recommendation

**APPROVE** - Ready for merge after minor suggestions

## 7. Commendations

- Excellent use of khive git for workflow
- Clean, testable code structure
- Good error handling patterns
- Effective use of service validations
