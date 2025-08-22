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
from pydantic import BaseModel, ConfigDict, Field


class TriageVote(BaseModel):
    """Individual triage agent's vote on complexity."""

    model_config = ConfigDict(extra="forbid")

    complexity: Literal["simple", "complex"] = Field(
        description="simple or complex classification"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in assessment")
    reasoning: str = Field(
        max_length=200, description="Brief reasoning for complexity assessment"
    )

    # Always provide values (0 and empty lists for complex tasks)
    recommended_agents: int = Field(
        ge=0, le=10, description="Number of agents (0 if complex)"
    )
    suggested_roles: list[str] = Field(
        default_factory=list,
        max_items=3,
        description="Suggested roles (empty if complex)",
    )
    suggested_domains: list[str] = Field(
        default_factory=list,
        max_items=2,
        description="Suggested domains (empty if complex)",
    )


class TriageConsensus(BaseModel):
    """Consensus from 3 triage agents."""

    should_escalate: bool
    complexity_votes: dict[str, int]  # {"simple": 2, "complex": 1}
    average_confidence: float

    # Consensus recommendations if not escalating
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
    final_complexity: str | None = None
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

    async def _single_triage(self, prompt: str, perspective: str) -> TriageVote:
        """Single triage agent evaluation."""

        system_prompt = f"""You are a complexity triage specialist focused on {perspective}.

Assess if this task is SIMPLE or COMPLEX:

SIMPLE tasks (use 3 or fewer agents):
- Single clear objective
- Well-defined scope
- Standard patterns (fix bug, update docs, simple queries)
- No cross-system dependencies
- Can be done in one pass

COMPLEX tasks (escalate to full planning):
- Multiple objectives or phases
- Vague or broad scope ("completely", "entire", "full system")
- Novel problems requiring research
- Cross-system dependencies
- Requires iteration or validation

Perspective: {perspective}
- efficiency: Can this be done quickly with minimal agents?
- scope: Is the scope well-bounded or expansive?
- risk: Are there risks that require careful planning?

If SIMPLE, suggest 1-3 specific roles and domains.
If COMPLEX, set recommended_agents to 0 and leave lists empty.
Be deterministic and consistent."""

        user_prompt = f"""Task: {prompt}

Provide your assessment in this exact JSON format:
{{
    "complexity": "simple" or "complex",
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation (max 200 chars)",
    "recommended_agents": 1-3 if simple, 0 if complex,
    "suggested_roles": ["role1", "role2"] if simple, [] if complex,
    "suggested_domains": ["domain1"] if simple, [] if complex
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
        return TriageVote(**vote_data)

    def _build_consensus(self, votes: list[TriageVote]) -> TriageConsensus:
        """Build consensus from 3 votes."""

        # Count complexity votes
        complexity_votes = {"simple": 0, "complex": 0}
        for vote in votes:
            complexity_votes[vote.complexity] += 1

        # Should escalate if 2+ votes for complex
        should_escalate = complexity_votes["complex"] >= 2

        # Average confidence
        avg_confidence = sum(v.confidence for v in votes) / len(votes)

        consensus = TriageConsensus(
            should_escalate=should_escalate,
            complexity_votes=complexity_votes,
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
            reasons = [v.reasoning for v in votes if v.complexity == "simple"]
            consensus.consensus_reasoning = " | ".join(reasons)

        return consensus

    async def _record_triage(
        self, prompt: str, votes: list[TriageVote], consensus: TriageConsensus
    ):
        """Record triage decision for future model training."""

        record = TriageRecord(
            timestamp=datetime.now().isoformat(),
            prompt=prompt,
            word_count=len(prompt.split()),
            votes=[v.model_dump() for v in votes],
            consensus=consensus.model_dump(),
            escalated=consensus.should_escalate,
            final_complexity="complex" if consensus.should_escalate else "simple",
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
