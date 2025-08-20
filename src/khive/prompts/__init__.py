from typing import Literal

ALL_AGENT_ROLES = {
    "analyst",
    "architect",
    "auditor",
    "commentator",
    "critic",
    "implementer",
    "innovator",
    "researcher",
    "reviewer",
    "strategist",
    "tester",
    "theorist",
}


AgentRole = Literal[
    "analyst",
    "architect",
    "auditor",
    "commentator",
    "critic",
    "implementer",
    "innovator",
    "researcher",
    "reviewer",
    "strategist",
    "tester",
    "theorist",
]


__all__ = ("ALL_AGENT_ROLES", "AgentRole")
