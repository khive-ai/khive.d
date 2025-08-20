"""Documentation validation gate prompts - progressive and practical"""

DOCUMENTATION_GATE_PROMPT = """
Evaluate docs based on who needs them NOW and what they need.

**Key Questions:**
- Immediate audience? (Self, team, external users)
- Decisions to record? (Why > what)
- What confuses in 3 months? (Document that)
- What's changing? (Don't over-document unstable areas)

**Docs by Phase:**
- Exploration: Key decisions, assumptions, open questions
- Development: Setup, architecture decisions, API contracts
- Integration: Interface docs, deployment notes
- Production: Runbooks, troubleshooting guides
- Maintenance: Everything new person needs

**`is_acceptable`:** True if serves immediate purpose. README with setup steps might be perfect.

**`problems`:** Only missing docs that block current work or cause confusion. No comprehensive docs for experimental code.

**Philosophy:**
- Document WHY (decisions) > WHAT (code explains what)
- Document surprises, non-obvious choices
- External interfaces before internals
- What you wish you'd known
- Update when reality changes

**Progressive Approach:**
1. README: what it does, how to run
2. Key architectural decisions, trade-offs
3. API docs as interfaces stabilize
4. Operational guides approaching production
5. Comprehensive docs as project matures

**Avoid:**
- Documenting obvious code
- Docs nobody reads
- Detailed docs for unstable features
- Docs over working code
- Copy-paste docs that diverge

**High-Value Docs:**
- Working setup/installation
- Architecture decisions + rationale
- Copy-pasteable API examples
- Common problem troubleshooting
- Configuration with defaults

Best docs: code needing none. Second best: docs solving problems.
"""

MINIMAL_DOCUMENTATION_GATE_PROMPT = """
Essential documentation check:
- Can someone else run this?
- Are key decisions recorded?
- Are interfaces documented?

Documentation should grow with project maturity.
"""
