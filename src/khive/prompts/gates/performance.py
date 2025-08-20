"""Performance validation gate prompts - based on actual requirements"""

PERFORMANCE_GATE_PROMPT = """
Evaluate performance against ACTUAL requirements and usage.

**Reality Check:**
- Actual users? (Don't optimize for millions with dozens)
- Usage pattern? (Sustained vs bursty load)
- Performance budget? (Internal tool ≠ customer-facing SLAs)
- Development stage? (Premature optimization is evil)

**Performance by Phase:**
- Prototype: Works without timeout, approach validated
- Development: Fast enough for dev efficiency
- Beta: Meets basic expectations, no obvious bottlenecks
- Production: Meets SLAs, handles current + reasonable growth
- Scale: Handles 10x growth, no architectural limits

**`is_acceptable`:** True if appropriate for current needs. 500ms OK for admin panel used twice daily.

**`problems`:** Only issues affecting ACTUAL users or dev velocity. Don't optimize unnecessarily.

**Progressive Strategy:**
1. Make it work (correctness first)
2. Remove painful bottlenecks
3. Measure actual usage (data-driven)
4. Optimize hot paths (focus effort)
5. Plan for scale (don't build prematurely)

**Guidelines:**
- Measure before optimizing (assumptions often wrong)
- User perception > raw metrics
- Good enough is good enough
- Architecture > micro-optimizations
- Caching solves/creates problems

**Performance Matters When:**
- User-facing interactions
- High-frequency operations
- Resource-constrained environments
- Cost-sensitive operations

Don't sacrifice clarity, maintainability, or velocity for unnecessary gains.
"""

MINIMAL_PERFORMANCE_GATE_PROMPT = """
Basic performance check for development:
- Does it complete in reasonable time?
- Are there obvious bottlenecks?
- Is it usable for development/testing?

Optimization can come after validation.
"""
