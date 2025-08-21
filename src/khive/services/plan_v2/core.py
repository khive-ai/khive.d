"""Core Plan Service - Simplified and elegant orchestration planning.

This module contains the main service logic, data models, and consensus building
in a single cohesive file. No over-engineering, just what's needed.
"""

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

# ============================================================================
# Core Data Models
# ============================================================================


@dataclass
class OrchestrationEvaluation:
    """Structured evaluation response from cheap model agents."""

    complexity: str
    complexity_reason: str
    total_agents: int
    agent_reason: str
    role_priorities: List[str]
    primary_domains: List[str]
    workflow_pattern: str
    quality_level: str
    confidence: float


class PatternType(str, Enum):
    """Available orchestration patterns."""

    DIRECT = "direct"
    FANOUT = "fanout"
    TOURNAMENT = "tournament"
    HIERARCHICAL = "hierarchical"


class ComplexityLevel(str, Enum):
    """Task complexity levels."""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class QualityGate(str, Enum):
    """Quality gate levels."""

    BASIC = "basic"
    THOROUGH = "thorough"
    CRITICAL = "critical"


@dataclass
class AgentSpec:
    """Simple agent specification."""

    role: str
    domain: str
    priority: float = 1.0
    reasoning: str = ""


@dataclass
class Phase:
    """Execution phase specification."""

    name: str
    description: str
    agents: List[AgentSpec]
    pattern: str  # "parallel" or "sequential"
    dependencies: List[str] = field(default_factory=list)
    quality_gate: QualityGate = QualityGate.BASIC
    estimated_minutes: int = 5


@dataclass
class ExecutionPlan:
    """Complete execution plan."""

    pattern_type: PatternType
    phases: List[Phase]
    total_agents: int
    complexity: ComplexityLevel
    estimated_minutes: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanRequest:
    """Planning request."""

    task: str
    context: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PlanResponse:
    """Planning response."""

    request_id: str
    plan: ExecutionPlan
    confidence: float
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================================================
# Simple Consensus Logic (replaces complex voting algorithms)
# ============================================================================


def build_consensus(task: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Build consensus for planning decisions. Simple and effective."""

    # Simple keyword-based analysis
    task_lower = task.lower()
    word_count = len(task.split())

    # Determine complexity (replaces complex LLM analysis)
    if any(word in task_lower for word in ["simple", "basic", "quick"]):
        complexity = ComplexityLevel.SIMPLE
        agent_count = 1
    elif any(word in task_lower for word in ["complex", "difficult", "multiple"]):
        if word_count > 20:
            complexity = ComplexityLevel.VERY_COMPLEX
            agent_count = 5
        else:
            complexity = ComplexityLevel.COMPLEX
            agent_count = 4
    else:
        complexity = ComplexityLevel.MEDIUM
        agent_count = 3

    # Override from context
    agent_count = context.get("agents", agent_count)
    complexity = ComplexityLevel(context.get("complexity", complexity.value))

    # Determine task type and roles
    if any(word in task_lower for word in ["analyze", "research", "study"]):
        task_type = "analysis"
        roles = ["researcher", "analyst", "critic"]
    elif any(word in task_lower for word in ["implement", "build", "create"]):
        task_type = "implementation"
        roles = ["architect", "implementer", "tester"]
    elif any(word in task_lower for word in ["review", "validate", "check"]):
        task_type = "validation"
        roles = ["reviewer", "critic", "analyst"]
    else:
        task_type = "general"
        roles = ["analyst", "researcher", "critic"]

    # Determine domains
    if any(word in task_lower for word in ["api", "service", "system"]):
        domains = ["software-architecture", "api-design"]
    elif any(word in task_lower for word in ["database", "data"]):
        domains = ["backend-development", "database-design"]
    else:
        domains = ["distributed-systems", "software-architecture"]

    return {
        "complexity": complexity,
        "agent_count": min(agent_count, 8),  # Cap at 8 agents
        "task_type": task_type,
        "roles": roles[:agent_count],
        "domains": domains[:2],
        "confidence": 0.8,  # Simple static confidence
    }


# ============================================================================
# Main Plan Service
# ============================================================================


class PlanService:
    """Simplified Plan Service with group assessment using cheap model agents."""

    def __init__(self):
        """Initialize the service."""
        load_dotenv()

        # OpenAI client for cheap model evaluations
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=api_key)
        self._request_history = []

        # Group assessment configuration
        self.target_budget = 0.0035  # $0.0035 per plan = 285 plans per $1
        self.evaluation_agents = self._get_evaluation_agent_configs()

    async def create_plan(self, request: PlanRequest) -> PlanResponse:
        """Create an execution plan using group assessment with cheap model agents."""

        # Step 1: Group assessment with multiple cheap agents
        evaluations = await self._evaluate_with_group_assessment(request.task)

        # Step 2: Build consensus from multiple evaluations
        consensus = self._build_consensus_from_evaluations(evaluations, request.task)

        # Step 3: Select pattern based on consensus
        pattern = self._select_pattern_from_consensus(consensus)

        # Step 4: Generate plan using consensus data
        plan = await self._generate_plan(
            pattern_type=pattern, task=request.task, consensus=consensus
        )

        # Step 5: Create response
        avg_confidence = sum(e["evaluation"].confidence for e in evaluations) / len(
            evaluations
        )

        response = PlanResponse(
            request_id=request.request_id,
            plan=plan,
            confidence=avg_confidence,
            reasoning=f"Group consensus: {pattern.value} pattern with {len(evaluations)} agent evaluations",
        )

        # Track for analytics
        self._request_history.append(
            {
                "pattern": pattern.value,
                "complexity": consensus["complexity"].value,
                "agents": plan.total_agents,
                "evaluation_count": len(evaluations),
                "timestamp": datetime.now(),
            }
        )

        return response

    def _select_pattern(self, consensus: Dict[str, Any]) -> PatternType:
        """Simple pattern selection logic. Replaces complex decision matrix."""

        complexity = consensus["complexity"]
        agent_count = consensus["agent_count"]
        task_type = consensus["task_type"]

        # Simple rules-based selection
        if complexity == ComplexityLevel.SIMPLE or agent_count <= 1:
            return PatternType.DIRECT
        elif task_type == "validation" or "comparison" in task_type:
            return PatternType.TOURNAMENT
        elif complexity == ComplexityLevel.VERY_COMPLEX or agent_count >= 5:
            return PatternType.HIERARCHICAL
        else:
            return PatternType.FANOUT

    async def _generate_plan(
        self, pattern_type: PatternType, task: str, consensus: Dict[str, Any]
    ) -> ExecutionPlan:
        """Generate execution plan using selected pattern."""

        from .patterns import generate_pattern_plan

        return await generate_pattern_plan(
            pattern_type=pattern_type, task=task, consensus=consensus
        )

    def _get_evaluation_agent_configs(self) -> List[Dict[str, Any]]:
        """Define different agent perspectives for group assessment."""
        return [
            {
                "name": "efficiency_analyst",
                "system_prompt": """You MINIMIZE resources aggressively. Start with bare minimum.
You are an efficiency-focused orchestration analyst. Your bias is toward minimal resource usage.

BIAS: Prefer researcher→analyst→architect→implementer. Avoid redundant validation roles. 
Push for LOWER complexity ratings. Optimize for speed and cost efficiency.

Provide orchestration evaluation with focus on resource optimization.""",
            },
            {
                "name": "quality_architect",
                "system_prompt": """You MAXIMIZE quality obsessively. Never compromise on validation.
You are a quality-focused architecture analyst. Your bias is toward thorough validation.

BIAS: Always include critic→tester→reviewer→auditor. Push for CRITICAL quality on distributed/event systems.
Add 20-30% more agents for comprehensive coverage. Quality over speed.

Provide orchestration evaluation with focus on quality assurance.""",
            },
            {
                "name": "risk_auditor",
                "system_prompt": """You are PARANOID about risks. Assume everything will fail.
You are a risk-focused auditing analyst. Your bias is toward failure prevention.

BIAS: Auditor→tester→critic ALWAYS in top 3. Distributed=VeryComplex. Event-driven=VeryComplex.
Double validation roles. Assume worst-case scenarios. Better safe than sorry.

Provide orchestration evaluation with focus on risk mitigation.""",
            },
            {
                "name": "innovation_strategist",
                "system_prompt": """You seek BREAKTHROUGH solutions. Think differently.
You are an innovation-focused strategic analyst. Your bias is toward creative approaches.

BIAS: innovator→strategist→architect→researcher. Suggest unusual role combinations.
Push boundaries but stay practical. Look for novel orchestration patterns.

Provide orchestration evaluation with focus on innovative approaches.""",
            },
        ]

    async def _evaluate_with_group_assessment(self, task: str) -> List[Dict[str, Any]]:
        """Evaluate task with multiple cheap model agents concurrently."""
        print(
            f"📊 Group assessment with {len(self.evaluation_agents)} cheap model agents..."
        )

        # Create concurrent evaluation tasks
        tasks = []
        for config in self.evaluation_agents:
            task_coroutine = asyncio.create_task(self._safe_evaluation(task, config))
            tasks.append(task_coroutine)

        # Wait for all evaluations to complete
        results = await asyncio.gather(*tasks)

        # Filter successful evaluations
        evaluations = []
        for config, result in zip(self.evaluation_agents, results):
            if result is not None and "error" not in result:
                evaluations.append(result)
                print(f"✅ {config['name']}")
            elif result and "error" in result:
                print(f"❌ {config['name']} failed: {result['error']}")

        print(
            f"📊 Group assessment completed: {len(evaluations)}/{len(self.evaluation_agents)} agents successful"
        )
        return evaluations

    async def _safe_evaluation(
        self, task: str, config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Safely run evaluation with a single cheap model agent."""
        try:
            return await self._run_single_evaluation(task, config)
        except Exception as e:
            return {"error": str(e), "config": config}

    async def _run_single_evaluation(
        self, task: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run evaluation with single cheap model agent."""
        user_prompt = f"""Request: {task}

Provide orchestration evaluation. Keep reasons under 250 chars.
For role_priorities, provide a priority-ordered list of roles you recommend (most important first).
Example: ["researcher", "analyst", "critic", "implementer"]

Required fields:
- complexity: "simple", "medium", "complex", or "very_complex"
- complexity_reason: Brief explanation (under 250 chars)
- total_agents: Number of agents needed (1-12)
- agent_reason: Brief explanation (under 250 chars)
- role_priorities: List of role names in priority order
- primary_domains: List of domain names (2-3 max)
- workflow_pattern: "parallel", "sequential", or "hybrid"
- quality_level: "basic", "thorough", or "critical"
- confidence: Float between 0.0 and 1.0

Be different - show YOUR unique perspective based on your bias."""

        start_time = time.time()

        # Use cheap model for cost efficiency
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model="gpt-4o-mini",  # Using available cheap model
            messages=[
                {"role": "system", "content": config["system_prompt"]},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)

        # Parse response (simplified - in production would use structured output)
        content = response.choices[0].message.content

        # Create mock evaluation (in production would parse structured response)
        evaluation = self._parse_evaluation_response(content, config["name"])

        return {
            "config": config,
            "evaluation": evaluation,
            "response_time_ms": response_time_ms,
            "content": content,
        }

    def _parse_evaluation_response(
        self, content: str, agent_name: str
    ) -> OrchestrationEvaluation:
        """Parse evaluation response from cheap model using heuristic parsing."""

        content_lower = content.lower()

        # Parse complexity
        complexity = "medium"  # default
        if any(
            word in content_lower
            for word in ["simple", "basic", "straightforward", "easy"]
        ):
            complexity = "simple"
        elif any(
            word in content_lower
            for word in ["very complex", "extremely complex", "highly complex"]
        ):
            complexity = "very_complex"
        elif any(
            word in content_lower for word in ["complex", "complicated", "challenging"]
        ):
            complexity = "complex"

        # Parse agent count with bias
        agent_count = 3  # default
        if agent_name == "efficiency_analyst":
            agent_count = 2 if "simple" in content_lower else 3
        elif agent_name == "quality_architect":
            agent_count = 6 if "complex" in content_lower else 5
        elif agent_name == "risk_auditor":
            agent_count = (
                5 if "distributed" in content_lower or "system" in content_lower else 4
            )
        elif agent_name == "innovation_strategist":
            agent_count = 4

        # Extract number patterns (look for numbers 1-12)
        import re

        numbers = re.findall(r"\b([1-9]|1[0-2])\b", content_lower)
        if numbers:
            # Use first reasonable number found
            extracted_num = int(numbers[0])
            if 1 <= extracted_num <= 12:
                agent_count = extracted_num

        # Parse workflow pattern
        workflow_pattern = "parallel"
        if "sequential" in content_lower or "step by step" in content_lower:
            workflow_pattern = "sequential"
        elif "hybrid" in content_lower or "mixed" in content_lower:
            workflow_pattern = "hybrid"

        # Parse quality level based on agent bias
        quality_level = "basic"
        if agent_name in ["quality_architect", "risk_auditor"]:
            quality_level = "critical"
        elif agent_name == "innovation_strategist":
            quality_level = "thorough"
        elif "critical" in content_lower or "thorough" in content_lower:
            quality_level = "thorough"

        # Extract roles (look for common role words)
        role_keywords = {
            "researcher": ["research", "investigate", "discover"],
            "analyst": ["analyz", "assess", "evaluat"],
            "architect": ["design", "architect", "structure"],
            "implementer": ["implement", "build", "develop", "code"],
            "tester": ["test", "validat", "verify"],
            "critic": ["critic", "review", "audit"],
            "reviewer": ["review", "check", "inspect"],
            "strategist": ["strateg", "plan", "coordin"],
            "innovator": ["innovat", "creativ", "novel"],
        }

        found_roles = []
        for role, keywords in role_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                found_roles.append(role)

        # Apply agent bias to role priorities
        if agent_name == "efficiency_analyst":
            role_priorities = ["researcher", "analyst", "implementer"] + found_roles
        elif agent_name == "quality_architect":
            role_priorities = [
                "critic",
                "tester",
                "reviewer",
                "architect",
            ] + found_roles
        elif agent_name == "risk_auditor":
            role_priorities = ["auditor", "tester", "critic", "analyst"] + found_roles
        elif agent_name == "innovation_strategist":
            role_priorities = [
                "innovator",
                "strategist",
                "architect",
                "researcher",
            ] + found_roles
        else:
            role_priorities = ["analyst", "researcher"] + found_roles

        # Remove duplicates while preserving order
        role_priorities = list(dict.fromkeys(role_priorities))[:agent_count]

        # Parse confidence (look for percentage or confidence indicators)
        confidence = 0.8  # default
        if "confident" in content_lower or "certain" in content_lower:
            confidence = 0.9
        elif "uncertain" in content_lower or "unsure" in content_lower:
            confidence = 0.6

        # Extract percentage if mentioned
        pct_match = re.search(r"(\d+)%", content)
        if pct_match:
            confidence = min(max(int(pct_match.group(1)) / 100, 0.1), 1.0)

        return OrchestrationEvaluation(
            complexity=complexity,
            complexity_reason=f"Based on {agent_name} analysis of task characteristics",
            total_agents=agent_count,
            agent_reason=f"Agent count optimized for {agent_name} priorities and task complexity",
            role_priorities=role_priorities,
            primary_domains=["distributed-systems", "software-architecture"],
            workflow_pattern=workflow_pattern,
            quality_level=quality_level,
            confidence=confidence,
        )

    def _build_consensus_from_evaluations(
        self, evaluations: List[Dict[str, Any]], task: str
    ) -> Dict[str, Any]:
        """Build consensus from multiple agent evaluations."""
        if not evaluations:
            return build_consensus(task, {})  # Fallback to simple consensus

        all_evals = [e["evaluation"] for e in evaluations]

        # Complexity consensus (use highest complexity for safety)
        complexity_levels = {"simple": 1, "medium": 2, "complex": 3, "very_complex": 4}

        complexities = [e.complexity for e in all_evals]
        max_complexity_value = max(complexity_levels.get(c, 2) for c in complexities)

        # Map back to complexity string
        value_to_complexity = {v: k for k, v in complexity_levels.items()}
        consensus_complexity = value_to_complexity[max_complexity_value]

        # Agent count consensus (weighted average)
        agent_counts = [e.total_agents for e in all_evals]
        avg_agents = int(sum(agent_counts) / len(agent_counts))

        # Role consensus (position-weighted scoring)
        role_scores = {}
        for evaluation in evaluations:
            e = evaluation["evaluation"]
            for position, role in enumerate(e.role_priorities):
                if role not in role_scores:
                    role_scores[role] = 0
                position_weight = max(0.2, 1.0 - (position * 0.2))
                role_scores[role] += position_weight

        # Normalize and get top roles
        for role in role_scores:
            role_scores[role] = role_scores[role] / len(evaluations)

        sorted_roles = sorted(role_scores.items(), key=lambda x: x[1], reverse=True)
        top_roles = [role for role, _ in sorted_roles[:avg_agents]]

        # Domain consensus
        all_domains = []
        for e in all_evals:
            all_domains.extend(e.primary_domains)
        domain_counts = {d: all_domains.count(d) for d in set(all_domains)}
        top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[
            :2
        ]
        consensus_domains = [domain for domain, _ in top_domains]

        return {
            "complexity": ComplexityLevel(consensus_complexity),
            "agent_count": avg_agents,
            "task_type": "general",  # Simplified
            "roles": top_roles,
            "domains": consensus_domains,
            "confidence": sum(e.confidence for e in all_evals) / len(all_evals),
            "evaluations": evaluations,  # Include raw evaluations for debugging
        }

    def _select_pattern_from_consensus(self, consensus: Dict[str, Any]) -> PatternType:
        """Select pattern based on consensus data."""
        complexity = consensus["complexity"]
        agent_count = consensus["agent_count"]

        # Extract additional insights from evaluations if available
        has_critical_quality = False
        has_risk_focus = False

        if "evaluations" in consensus:
            for eval_data in consensus["evaluations"]:
                eval_obj = eval_data["evaluation"]
                if eval_obj.quality_level == "critical":
                    has_critical_quality = True
                if (
                    "auditor" in eval_obj.role_priorities[:3]
                    or "risk" in eval_data["config"]["name"]
                ):
                    has_risk_focus = True

        # Enhanced pattern selection logic
        if complexity == ComplexityLevel.SIMPLE or agent_count <= 1:
            return PatternType.DIRECT
        elif has_critical_quality or has_risk_focus:
            return PatternType.TOURNAMENT
        elif complexity == ComplexityLevel.VERY_COMPLEX or agent_count >= 5:
            return PatternType.HIERARCHICAL
        else:
            return PatternType.FANOUT

    def get_analytics(self) -> Dict[str, Any]:
        """Simple analytics for the service."""
        if not self._request_history:
            return {"total_requests": 0}

        patterns = [r["pattern"] for r in self._request_history]
        complexities = [r["complexity"] for r in self._request_history]

        return {
            "total_requests": len(self._request_history),
            "pattern_usage": {p: patterns.count(p) for p in set(patterns)},
            "complexity_distribution": {
                c: complexities.count(c) for c in set(complexities)
            },
            "avg_agents": sum(r["agents"] for r in self._request_history)
            / len(self._request_history),
        }


# ============================================================================
# Convenience Functions
# ============================================================================


async def plan_task(task: str, **context) -> PlanResponse:
    """Convenience function for quick planning."""
    service = PlanService()
    request = PlanRequest(task=task, context=context)
    return await service.create_plan(request)


def create_agent_spec(role: str, domain: str = "general", **kwargs) -> AgentSpec:
    """Create agent specification with defaults."""
    return AgentSpec(
        role=role,
        domain=domain,
        priority=kwargs.get("priority", 1.0),
        reasoning=kwargs.get("reasoning", f"{role} for {domain}"),
    )
