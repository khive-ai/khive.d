"""Design completeness gate prompts - context-aware and phase-appropriate"""

DESIGN_GATE_PROMPT = """
Evaluate whether the design is appropriate for the CURRENT issue's scope and position in the project.

**Context Considerations:**
- What is this issue trying to accomplish? (Don't over-architect beyond stated needs)
- What phase is the project in? (Prototype vs Production have different needs)
- What issues does this block? (Critical path items need more rigor)
- What issues does this depend on? (Can't design what depends on unknowns)

**Assessment Approach:**
- For foundational issues: Focus on interfaces and contracts
- For feature issues: Focus on user workflows and integration points
- For optimization issues: Focus on bottlenecks and constraints
- For experimental issues: Focus on learning goals and hypotheses

**For `is_acceptable`:** Return `true` if the design is sufficient for THIS issue's goals. A sketch might be perfect for exploration; detailed specs might be needed for critical infrastructure.

**For `problems`:** List only gaps that would prevent THIS issue from achieving its stated objectives. Don't list nice-to-haves or future considerations unless they block current work.

**Scope-Appropriate Standards:**
- Early issues: "Can we build this?" is more important than "Is it optimal?"
- Integration issues: Focus on contracts, not internals
- Final issues: Now we care about completeness and optimization

Remember: Perfect is the enemy of good. Design detail should match issue importance and project maturity.
"""

MINIMAL_DESIGN_GATE_PROMPT = """
Quick design check for exploratory/experimental work:
- Is the core approach clear?
- Are major risks identified?
- Can implementation begin?

This is for learning and iteration, not production deployment.
"""
