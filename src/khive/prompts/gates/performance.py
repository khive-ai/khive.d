"""Performance validation gate prompts - based on actual requirements"""

PERFORMANCE_GATE_PROMPT = """
Evaluate performance relative to the issue's ACTUAL requirements and current usage patterns.

**Reality Check First:**
- How many users do we actually have? (Don't optimize for millions if you have dozens)
- What's the real usage pattern? (Don't optimize for sustained load if usage is bursty)
- What's the performance budget? (Internal tool vs customer-facing have different SLAs)
- Where are we in development? (Premature optimization is evil)

**Context-Appropriate Performance:**
- Prototype: Does it work without timing out? Can we validate the approach?
- Development: Is it fast enough for developers to work efficiently?
- Beta/Testing: Does it meet basic user expectations? Are there obvious bottlenecks?
- Production: Does it meet SLAs? Can it handle current + reasonable growth?
- Scale: Can it handle 10x growth? Are there architectural limits?

**For `is_acceptable`:** Return `true` if performance is appropriate for current needs. A 500ms response might be fine for an admin panel used twice a day.

**For `problems`:** Only flag performance issues that affect ACTUAL users or development velocity. Don't optimize what doesn't need optimizing.

**Progressive Performance Strategy:**
1. Make it work (correctness first)
2. Make it work well enough (remove painful bottlenecks)
3. Measure actual usage (data-driven decisions)
4. Optimize hot paths (focus effort where it matters)
5. Plan for scale (but don't build for it prematurely)

**Pragmatic Guidelines:**
- Measure before optimizing - assumptions are often wrong
- User perception matters more than raw metrics
- Good enough is good enough - perfect performance isn't the goal
- Architectural decisions matter more than micro-optimizations
- Caching solves many problems but creates others

**When Performance Matters:**
- User-facing interactions (perceived responsiveness)
- High-frequency operations (small inefficiencies compound)
- Resource-constrained environments (mobile, embedded)
- Cost-sensitive operations (cloud resources = money)

Don't sacrifice clarity, maintainability, or development velocity for unnecessary performance gains.
"""

MINIMAL_PERFORMANCE_GATE_PROMPT = """
Basic performance check for development:
- Does it complete in reasonable time?
- Are there obvious bottlenecks?
- Is it usable for development/testing?

Optimization can come after validation.
"""
