"""Security validation gate prompts - proportional to actual risk"""

SECURITY_GATE_PROMPT = """
Evaluate security measures proportional to the issue's ACTUAL risk profile and deployment context.

**Risk Assessment First:**
- What data does this handle? (Public data vs PII vs payment info have different needs)
- Who can access this? (Internal tool vs public API have different threat models)
- What's the deployment context? (Local dev vs staging vs production)
- What's the issue's scope? (UI tweak vs auth system have different security implications)

**Proportional Security Requirements:**
- Development/Prototype: Basic security hygiene (no hardcoded secrets, basic input validation)
- Internal Tools: Standard authentication, logging, basic authorization
- External Features: Input validation, rate limiting, audit trails
- Sensitive Operations: Encryption, comprehensive authz, security monitoring
- Financial/Healthcare: Compliance requirements, extensive hardening

**For `is_acceptable`:** Return `true` if security measures match the actual risk. Don't demand bank-level security for a todo app prototype.

**For `problems`:** Only flag security issues that represent REAL risk given the context. A missing CSP header isn't critical for an internal dashboard.

**Progressive Security Approach:**
1. Start: Don't actively create vulnerabilities
2. Then: Protect against obvious attacks (SQL injection, XSS)
3. Next: Add authentication and basic authorization
4. Later: Implement defense in depth
5. Finally: Full security program with monitoring

**Pragmatic Considerations:**
- Perfect security doesn't exist - aim for appropriate security
- Security theater wastes time - focus on real threats
- Over-securing slows development - match measures to risk
- Early phases need flexibility - harden as you scale

**Red Flags (Always Address):**
- Hardcoded credentials or secrets
- SQL injection vulnerabilities  
- Storing passwords in plain text
- Exposed sensitive endpoints without auth

Everything else should be proportional to actual risk and project maturity.
"""

MINIMAL_SECURITY_GATE_PROMPT = """
Basic security check for development:
- No hardcoded secrets?
- No obvious injection vulnerabilities?
- Appropriate for deployment context?

Security can be enhanced iteratively as project matures.
"""
