"""Simple task patterns for fast, accurate handling of common requests."""

from typing import List, Tuple

# Pattern: (keywords, required_roles, domains, max_agents)
SIMPLE_PATTERNS = {
    "bug_fix": {
        "triggers": ["fix", "bug", "broken", "not working", "error", "crash"],
        "required_roles": ["analyst", "implementer", "tester"],
        "domains": ["software-architecture"],
        "max_agents": 3,
        "complexity": 0.2,
    },
    "documentation": {
        "triggers": ["document", "readme", "docs", "documentation"],
        "required_roles": ["commentator"],
        "optional_roles": ["analyst"],
        "domains": ["software-architecture"],
        "max_agents": 2,
        "complexity": 0.1,
    },
    "security_audit": {
        "triggers": ["audit", "security", "vulnerability"],
        "required_roles": ["auditor", "analyst", "critic"],
        "domains": ["security-architecture"],
        "max_agents": 3,
        "complexity": 0.3,
    },
    "hotfix": {
        "triggers": ["critical", "production", "urgent", "hotfix"],
        "required_roles": ["analyst", "implementer", "tester"],
        "optional_roles": ["auditor"],
        "domains": ["backend-development"],
        "max_agents": 4,
        "complexity": 0.4,
    },
    "refactor": {
        "triggers": ["refactor", "cleanup", "reorganize"],
        "required_roles": ["analyst", "architect", "implementer"],
        "domains": ["software-architecture"],
        "max_agents": 3,
        "complexity": 0.3,
    },
}


def match_simple_pattern(prompt: str) -> dict | None:
    """
    Quick pattern matching for simple tasks.
    Returns pattern dict if matched, None otherwise.
    """
    prompt_lower = prompt.lower()

    # Check word count - simple tasks are usually short
    word_count = len(prompt.split())
    if word_count > 30:  # Complex tasks tend to be verbose
        return None

    for pattern_name, pattern in SIMPLE_PATTERNS.items():
        # Check if any trigger words are present
        if any(trigger in prompt_lower for trigger in pattern["triggers"]):
            return pattern

    return None


def enforce_required_roles(selected_roles: List[str], pattern: dict) -> List[str]:
    """Ensure required roles are present."""
    roles = list(selected_roles)

    for required in pattern.get("required_roles", []):
        if required not in roles:
            roles.insert(0, required)  # Prioritize required roles

    # Remove excess agents if over limit
    if "max_agents" in pattern and len(roles) > pattern["max_agents"]:
        # Keep required roles, trim optional ones
        required = set(pattern.get("required_roles", []))
        optional = [r for r in roles if r not in required]
        required_list = list(required)

        # Take required + some optional up to max
        remaining_slots = pattern["max_agents"] - len(required_list)
        roles = required_list + optional[:remaining_slots]

    return roles
