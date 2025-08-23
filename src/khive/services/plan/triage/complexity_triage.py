"""Two-tier complexity triage system for efficient planning.

First tier: 3 LLMs vote on complexity and provide draft recommendations.
Second tier: Complex tasks escalate to 10 LLM consensus.
"""

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field, create_model

from khive.utils import KHIVE_CONFIG_DIR


def _load_available_roles() -> list[str]:
    """Load available roles from KHIVE_CONFIG_DIR/prompts/roles/"""
    roles_dir = KHIVE_CONFIG_DIR / "prompts" / "roles"
    if not roles_dir.exists():
        # Fallback to default roles if user hasn't copied them yet
        return [
            "researcher",
            "analyst",
            "architect",
            "implementer",
            "tester",
            "critic",
            "reviewer",
        ]

    roles = []
    for role_file in roles_dir.glob("*.md"):
        if role_file.name != "README.md":
            roles.append(role_file.stem)

    return (
        sorted(roles)
        if roles
        else [
            "researcher",
            "analyst",
            "architect",
            "implementer",
            "tester",
            "critic",
            "reviewer",
        ]
    )


def _load_available_domains() -> list[str]:
    """Load available domains from KHIVE_CONFIG_DIR/prompts/domains/"""
    domains_dir = KHIVE_CONFIG_DIR / "prompts" / "domains"
    if not domains_dir.exists():
        # Fallback to common domains if user hasn't copied them yet
        return [
            "api-design",
            "backend-development",
            "frontend-development",
            "database-design",
            "async-programming",
        ]

    domains = []
    for category_dir in domains_dir.iterdir():
        if category_dir.is_dir() and not category_dir.name.startswith("_"):
            for domain_file in category_dir.glob("*.yaml"):
                domains.append(domain_file.stem)

    return (
        sorted(domains)
        if domains
        else [
            "api-design",
            "backend-development",
            "frontend-development",
            "database-design",
            "async-programming",
        ]
    )


def _create_dynamic_triage_vote() -> type[BaseModel]:
    """Create TriageVote model with actual available roles and domains."""
    available_roles = _load_available_roles()
    available_domains = _load_available_domains()

    # Create Literal types from actual available options
    RoleLiteral = Literal[tuple(available_roles)]
    DomainLiteral = Literal[tuple(available_domains)]

    return create_model(
        "TriageVote",
        __config__=ConfigDict(extra="forbid"),
        decision=(
            Literal["proceed", "escalate"],
            Field(description="proceed with fast triage or escalate to full consensus"),
        ),
        confidence=(
            float,
            Field(ge=0.0, le=1.0, description="Confidence in assessment"),
        ),
        reasoning=(
            str,
            Field(max_length=200, description="Brief reasoning for triage decision"),
        ),
        recommended_agents=(
            int,
            Field(ge=0, le=10, description="Number of agents (0 if escalating)"),
        ),
        suggested_roles=(
            list[RoleLiteral],
            Field(
                default_factory=list,
                max_length=3,
                description="Suggested roles (empty if escalating)",
            ),
        ),
        suggested_domains=(
            list[DomainLiteral],
            Field(
                default_factory=list,
                max_length=2,
                description="Suggested domains (empty if escalating)",
            ),
        ),
        __base__=BaseModel,
    )


# TriageVote is now dynamically created - see _create_dynamic_triage_vote()


class TriageConsensus(BaseModel):
    """Consensus from 3 triage agents."""

    should_escalate: bool
    decision_votes: dict[str, int]  # {"proceed": 2, "escalate": 1}
    average_confidence: float

    # Consensus recommendations if proceeding with fast triage
    final_agent_count: int | None = None
    final_roles: list[str] | None = None
    final_domains: list[str] | None = None
    consensus_reasoning: str | None = None


@dataclass
class TriageRecord:
    """Record for future model training."""

    timestamp: str
    prompt: str
    word_count: int
    votes: list[dict[str, Any]]
    consensus: dict[str, Any]
    escalated: bool
    final_decision: str | None = None
    actual_agents_used: int | None = None
    execution_success: bool | None = None

    def to_jsonl(self) -> str:
        """Convert to JSONL format for training data."""
        return json.dumps(asdict(self))


class ComplexityTriageService:
    """Fast complexity triage using 3 deterministic LLMs."""

    def __init__(self, api_key: str | None = None):
        if api_key is None:
            # Try to load from environment
            import os

            from dotenv import load_dotenv

            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not provided and not in environment")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4.1-nano"  # Fast and cheap
        self.temperature = 0.0  # Deterministic

        # Create dynamic model with actual available roles/domains
        self.TriageVote = _create_dynamic_triage_vote()
        self.available_roles = _load_available_roles()
        self.available_domains = _load_available_domains()

        # Data collection for future tuning
        self.data_dir = Path(".khive/data/triage")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / f"triage_{datetime.now():%Y%m%d}.jsonl"

    async def triage(self, prompt: str) -> tuple[bool, TriageConsensus]:
        """
        Perform complexity triage with 3 LLMs.

        Returns:
            (should_escalate, consensus)
        """
        # Run 3 triage agents in parallel
        votes = await asyncio.gather(
            self._single_triage(prompt, "efficiency"),
            self._single_triage(prompt, "scope"),
            self._single_triage(prompt, "risk"),
        )

        # Build consensus
        consensus = self._build_consensus(votes)

        # Record for training data
        await self._record_triage(prompt, votes, consensus)

        return consensus.should_escalate, consensus

    async def _single_triage(self, prompt: str, perspective: str):
        """Single triage agent evaluation."""

        system_prompt = f"""You are a triage specialist focused on {perspective}.

Decide whether to PROCEED with fast triage or ESCALATE to full consensus:

PROCEED (use 3 or fewer agents):
- SIMPLE, single-step tasks
- Well-defined, narrow scope
- Standard patterns (fix bug, update docs, simple queries)
- No cross-system dependencies
- Can be done in one pass
- NOT research, analysis, or design tasks

ESCALATE (requires full planning consensus):
- Research, analysis, or investigation tasks
- Design, architecture, or planning tasks
- Multiple objectives or phases (e.g., "research AND analyze")
- Vague or broad scope ("completely", "entire", "full system")
- Novel problems or complex algorithms
- Cross-system dependencies
- Requires iteration or validation
- Performance analysis or optimization

Perspective: {perspective}
- efficiency: Can this be done quickly with minimal agents?
- scope: Is the scope well-bounded or expansive?
- risk: Are there risks that require careful planning?

If PROCEED, suggest 1-3 specific roles and domains from these valid options:
Available roles: {", ".join(self.available_roles)}
Available domains: {", ".join(self.available_domains)}

If ESCALATE, set recommended_agents to 0 and leave lists empty.
Be deterministic and consistent."""

        user_prompt = f"""Task: {prompt}

Provide your assessment in this exact JSON format:
{{
    "decision": "proceed" or "escalate",
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation (max 200 chars)",
    "recommended_agents": 1-3 if proceed, 0 if escalate,
    "suggested_roles": ["role1", "role2"] if proceed, [] if escalate,
    "suggested_domains": ["domain1"] if proceed, [] if escalate
}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        vote_data = json.loads(response.choices[0].message.content)

        # Gracefully handle LLM errors in role/domain suggestions
        corrected_data = self._correct_vote_data(vote_data)

        return self.TriageVote(**corrected_data)

    def _correct_vote_data(self, vote_data: dict) -> dict:
        """Gracefully correct LLM mistakes in role/domain suggestions using string similarity."""
        corrected = vote_data.copy()

        # Correct suggested roles
        if corrected.get("suggested_roles"):
            corrected["suggested_roles"] = [
                self._correct_string_value(role, self.available_roles)
                for role in corrected["suggested_roles"]
            ]

        # Correct suggested domains
        if corrected.get("suggested_domains"):
            corrected["suggested_domains"] = [
                self._correct_string_value(domain, self.available_domains)
                for domain in corrected["suggested_domains"]
            ]

        return corrected

    def _correct_string_value(self, value: str, valid_options: list[str]) -> str:
        """Correct a single string value using lionagi string similarity."""
        if value in valid_options:
            return value

        try:
            from lionagi.libs.validate.string_similarity import \
                string_similarity

            corrected = string_similarity(
                value,
                valid_options,
                threshold=0.8,
                case_sensitive=False,
                return_most_similar=True,
            )

            # If no good match found, return first valid option as fallback
            return corrected if corrected else valid_options[0]

        except ImportError:
            # Fallback if lionagi not available - return first valid option
            return valid_options[0]

    def _build_consensus(self, votes: list) -> TriageConsensus:
        """Build consensus from 3 votes."""

        # Count decision votes
        decision_votes = {"proceed": 0, "escalate": 0}
        for vote in votes:
            decision_votes[vote.decision] += 1

        # Should escalate if 2+ votes for escalate
        should_escalate = decision_votes["escalate"] >= 2

        # Average confidence
        avg_confidence = sum(v.confidence for v in votes) / len(votes)

        consensus = TriageConsensus(
            should_escalate=should_escalate,
            decision_votes=decision_votes,
            average_confidence=avg_confidence,
        )

        # If not escalating, build consensus recommendations
        if not should_escalate:
            # Merge role suggestions (most common)
            all_roles = []
            for vote in votes:
                if vote.suggested_roles:
                    all_roles.extend(vote.suggested_roles)

            # Count role frequency
            role_counts = {}
            for role in all_roles:
                role_counts[role] = role_counts.get(role, 0) + 1

            # Take top roles
            consensus.final_roles = sorted(
                role_counts.keys(), key=lambda r: role_counts[r], reverse=True
            )[:3]

            # Average agent count (round up, excluding 0 values from complex votes)
            agent_counts = [
                v.recommended_agents for v in votes if v.recommended_agents > 0
            ]
            consensus.final_agent_count = max(agent_counts) if agent_counts else 2

            # Merge domains
            all_domains = []
            for vote in votes:
                if vote.suggested_domains:
                    all_domains.extend(vote.suggested_domains)
            consensus.final_domains = list(set(all_domains))[:2]

            # Combine reasoning
            reasons = [v.reasoning for v in votes if v.decision == "proceed"]
            consensus.consensus_reasoning = " | ".join(reasons)

        return consensus

    async def _record_triage(
        self, prompt: str, votes: list, consensus: TriageConsensus
    ):
        """Record triage decision for future model training."""

        record = TriageRecord(
            timestamp=datetime.now().isoformat(),
            prompt=prompt,
            word_count=len(prompt.split()),
            votes=[v.model_dump() for v in votes],
            consensus=consensus.model_dump(),
            escalated=consensus.should_escalate,
            final_decision="escalate" if consensus.should_escalate else "proceed",
        )

        # Append to JSONL file
        async with asyncio.Lock():
            with open(self.data_file, "a") as f:
                f.write(record.to_jsonl() + "\n")

    async def update_outcome(self, prompt: str, actual_agents: int, success: bool):
        """Update record with actual execution outcome for learning."""
        # This would update the last record for this prompt
        # Used to validate if triage decisions were correct


class TriageAnalyzer:
    """Analyze triage performance for model tuning."""

    def __init__(self, data_dir: Path = Path(".khive/data/triage")):
        self.data_dir = data_dir

    def analyze_accuracy(self) -> dict[str, Any]:
        """Analyze triage accuracy from recorded data."""

        records = []
        for file in self.data_dir.glob("*.jsonl"):
            with open(file) as f:
                for line in f:
                    records.append(json.loads(line))

        if not records:
            return {"error": "No triage data found"}

        # Analysis metrics
        total = len(records)
        escalated = sum(1 for r in records if r["escalated"])

        # Confidence analysis
        simple_confidence = [
            r["consensus"]["average_confidence"] for r in records if not r["escalated"]
        ]
        complex_confidence = [
            r["consensus"]["average_confidence"] for r in records if r["escalated"]
        ]

        return {
            "total_triages": total,
            "escalation_rate": escalated / total if total > 0 else 0,
            "simple_tasks": total - escalated,
            "complex_tasks": escalated,
            "avg_simple_confidence": (
                sum(simple_confidence) / len(simple_confidence)
                if simple_confidence
                else 0
            ),
            "avg_complex_confidence": (
                sum(complex_confidence) / len(complex_confidence)
                if complex_confidence
                else 0
            ),
            "data_files": len(list(self.data_dir.glob("*.jsonl"))),
        }

    def export_training_data(self, output_file: Path):
        """Export data in format suitable for fine-tuning."""

        training_data = []
        for file in self.data_dir.glob("*.jsonl"):
            with open(file) as f:
                for line in f:
                    record = json.loads(line)

                    # Format for fine-tuning
                    training_data.append({
                        "prompt": record["prompt"],
                        "completion": {
                            "complexity": record["final_complexity"],
                            "agent_count": record.get("actual_agents_used"),
                            "success": record.get("execution_success"),
                        },
                    })

        with open(output_file, "w") as f:
            json.dump(training_data, f, indent=2)

        return len(training_data)
