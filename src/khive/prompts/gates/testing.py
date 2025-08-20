"""Testing validation gate prompts - scope and phase appropriate"""

TESTING_GATE_PROMPT = """
Evaluate if testing fits issue needs and project phase.

**Context:**
- Issue type? (Bug fix → regression, feature → coverage, refactor → existing tests pass)
- Blast radius? (Core infrastructure ≠ isolated feature)
- Project phase? (Exploration → smoke tests, production → comprehensive)
- Dependencies? (Critical path needs higher confidence)

**Testing by Phase:**
- Prototype: Happy path works, can learn
- Development: Main use cases covered, interfaces tested
- Integration: Components work together, contracts validated
- Hardening: Edge cases, error handling
- Production: Full pyramid + monitoring

**`is_acceptable`:** True if testing matches risk profile and phase. Console.log OK for prototypes; payment paths need extensive coverage.

**`problems`:** Only gaps creating unacceptable risk FOR THIS ISSUE. No 100% coverage demands for experimental features.

**Progressive Philosophy:**
- Start: "Does it work?"
- Then: "Handle common errors?"
- Then: "Robust against edge cases?"
- Finally: "Handle production scale?"

**Avoid:**
- Unit tests for throwaway prototypes
- Load testing before real users
- 100% coverage for low-risk areas
- Perfect tests blocking progress

Focus on confidence appropriate to current risk and maturity.
"""

MINIMAL_TESTING_GATE_PROMPT = """
Basic testing check for early development:
- Does the main functionality work?
- Are critical paths tested?
- Can changes be made safely?

This is about development velocity, not production reliability.
"""
