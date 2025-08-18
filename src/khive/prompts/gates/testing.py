"""Testing validation gate prompts - scope and phase appropriate"""

TESTING_GATE_PROMPT = """
Evaluate whether testing is appropriate for THIS issue's specific needs and project context.

**Context Questions First:**
- What type of issue is this? (Bug fix needs regression test, new feature needs basic coverage, refactor needs existing tests to pass)
- What's the blast radius? (Core infrastructure needs thorough testing, isolated feature needs focused testing)
- What phase are we in? (Exploration needs smoke tests, production needs comprehensive coverage)
- What depends on this? (Critical path items need higher confidence)

**Scope-Appropriate Testing:**
- Prototype/Exploration: Does it work in the happy path? Can we learn what we need?
- Feature Development: Are the main use cases covered? Do interfaces have tests?
- Integration: Do components work together? Are contracts validated?
- Hardening: Are edge cases covered? Is error handling tested?
- Production: Full test pyramid with monitoring and alerting

**For `is_acceptable`:** Return `true` if testing matches the issue's risk profile and project phase. A console.log might be fine for prototypes; critical payment paths need extensive coverage.

**For `problems`:** Only flag testing gaps that create unacceptable risk FOR THIS ISSUE. Don't demand 100% coverage for experimental features or comprehensive load testing for internal tools.

**Progressive Testing Philosophy:**
- Start with: "Does it basically work?"
- Evolve to: "Does it handle common errors?"
- Then: "Is it robust against edge cases?"
- Finally: "Can it handle production scale?"

**Anti-patterns to Avoid:**
- Don't demand unit tests for prototype code that might be thrown away
- Don't require load testing before you have real users
- Don't insist on 100% coverage for low-risk areas
- Don't block progress for perfect tests

Focus on tests that give confidence appropriate to the current risk and maturity level.
"""

MINIMAL_TESTING_GATE_PROMPT = """
Basic testing check for early development:
- Does the main functionality work?
- Are critical paths tested?
- Can changes be made safely?

This is about development velocity, not production reliability.
"""
