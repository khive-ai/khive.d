"""Documentation validation gate prompts - progressive and practical"""

DOCUMENTATION_GATE_PROMPT = """
Evaluate documentation based on who needs it NOW and what they need to know.

**Key Questions:**
- Who is the immediate audience? (Self, team, external users)
- What decisions need to be recorded? (Why more important than what)
- What would confuse someone in 3 months? (Document that)
- What's likely to change? (Don't over-document unstable areas)

**Phase-Appropriate Documentation:**
- Exploration: Key decisions, assumptions, and open questions
- Development: Setup instructions, architecture decisions, API contracts
- Integration: Interface documentation, deployment notes
- Production: Operational runbooks, troubleshooting guides
- Maintenance: Everything someone new would need to know

**For `is_acceptable`:** Return `true` if documentation serves its immediate purpose. A README with setup steps might be perfect for now.

**For `problems`:** Only flag missing documentation that would block current work or cause confusion. Don't demand comprehensive docs for experimental code.

**Documentation Philosophy:**
- Document WHY (decisions) over WHAT (code explains what)
- Document surprises and non-obvious choices
- Document external interfaces before internals
- Document what you wish you had known
- Update docs when reality changes

**Progressive Documentation:**
1. Start: README with what it does and how to run it
2. Add: Key architectural decisions and trade-offs
3. Add: API documentation as interfaces stabilize
4. Add: Operational guides as you approach production
5. Add: Comprehensive docs as project matures

**Anti-patterns to Avoid:**
- Don't document obvious code with comments
- Don't maintain documentation that nobody reads
- Don't document unstable/experimental features in detail
- Don't prioritize documentation over working code
- Don't copy-paste documentation that will diverge

**High-Value Documentation:**
- Setup/installation that actually works
- Architecture decisions and their rationale
- API examples that can be copy-pasted
- Troubleshooting for common problems
- Configuration with sensible defaults

Remember: The best documentation is code that doesn't need documentation. The second best is documentation that helps someone solve a problem.
"""

MINIMAL_DOCUMENTATION_GATE_PROMPT = """
Essential documentation check:
- Can someone else run this?
- Are key decisions recorded?
- Are interfaces documented?

Documentation should grow with project maturity.
"""
