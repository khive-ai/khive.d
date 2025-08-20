"""Design completeness gate prompts - context-aware and phase-appropriate"""

DESIGN_GATE_PROMPT = """
Evaluate if design fits issue scope and project phase.

**Context:**
- Issue goal? (Don't over-architect)
- Project phase? (Prototype ≠ Production needs)
- Critical path? (Affects rigor level)
- Dependencies? (Can't design unknowns)

**Focus:**
- Foundational: interfaces, contracts
- Feature: workflows, integration points
- Optimization: bottlenecks, constraints
- Experimental: learning goals, hypotheses

**`is_acceptable`:** True if sufficient for THIS issue. Sketch OK for exploration; specs needed for infrastructure.

**`problems`:** Only gaps blocking issue objectives. No nice-to-haves or future considerations.

**Standards by Phase:**
- Early: "Can we build?" > "Is it optimal?"
- Integration: contracts, not internals
- Final: completeness + optimization

Perfect is the enemy of good. Match design detail to issue importance and maturity.
"""
