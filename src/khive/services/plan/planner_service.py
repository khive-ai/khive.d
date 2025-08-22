from __future__ import annotations

import asyncio
import json
import os
import time
from enum import Enum
from pathlib import Path
from typing import Protocol

import yaml
from openai import OpenAI

from khive.core import TimePolicy
from khive.services.artifacts.handlers import (
    HandoffAgentSpec,
    TimeoutConfig,
    TimeoutManager,
    TimeoutType,
)
from khive.utils import get_logger

from .cost_tracker import CostTracker
from .models import OrchestrationEvaluation
from .parts import (
    AgentRecommendation,
    ComplexityLevel,
    PlannerRequest,
    PlannerResponse,
    QualityGate,
    TaskPhase,
    WorkflowPattern,
)
from .triage.complexity_triage import ComplexityTriageService, TriageConsensus

logger = get_logger("khive.services.plan")


class ComplexityTier(Enum):
    """Complexity tier enumeration based on decision matrix"""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class Request:
    """Request model for complexity assessment"""

    def __init__(self, text: str):
        self.text = text.lower()  # For easier pattern matching
        self.original = text


class ComplexityAssessor(Protocol):
    """Trait for complexity assessment functionality"""

    def assess(self, req: Request) -> ComplexityTier:
        """Assess request complexity and return tier"""
        ...


class RoleSelector(Protocol):
    """Trait for role selection functionality"""

    def select_roles(self, req: Request, complexity: ComplexityTier) -> list[str]:
        """Select appropriate roles based on request and complexity"""
        ...


class OrchestrationPlanner(ComplexityAssessor, RoleSelector):
    def __init__(self, timeout_config: TimeoutConfig | None = None):
        from dotenv import load_dotenv

        load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=api_key)
        self.cost_tracker = CostTracker()
        self.target_budget = 0.0035  # $0.0035 per plan = 285 plans per $1
        # Create log directory if it doesn't exist
        self.log_dir = Path(".khive/logs/orchestration_planning")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = (
            self.log_dir
            / f"evaluations_{TimePolicy.now_utc().strftime('%Y%m%d')}.jsonl"
        )

        # Artifact management - use .khive folder instead of .claude
        self.workspace_dir = Path(".khive/workspace")
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_id = None

        # Timeout configuration for Phase 1 optimizations
        self.timeout_config = timeout_config or TimeoutConfig(
            agent_execution_timeout=300.0,  # 5 minutes
            phase_completion_timeout=1800.0,  # 30 minutes
            total_orchestration_timeout=3600.0,  # 1 hour
            max_retries=3,
            retry_delay=5.0,
            escalation_enabled=True,
            performance_threshold=0.9,
            timeout_reduction_factor=0.3,
        )

        # Timeout manager for coordinating agent execution
        self.timeout_manager = None

        # Parallel execution support
        self.parallel_execution_enabled = True

        # Load available roles and domains dynamically
        self.available_roles = self._load_available_roles()
        self.available_domains = self._load_available_domains()

        # Load prompt templates
        self.prompt_templates = self._load_prompt_templates()

        # Load decision matrix for complexity assessment
        self.matrix = self._load_decision_matrix()

    def _load_available_roles(self) -> list[str]:
        """Scan agents directory for available roles"""
        # Get path to shared prompts directory
        agents_path = Path(__file__).parent.parent.parent / "prompts" / "roles"
        roles = []

        for agent_file in agents_path.glob("*.md"):
            if agent_file.name != "README.md":
                role_name = agent_file.stem
                roles.append(role_name)

        return sorted(roles)

    def _load_available_domains(self) -> list[str]:
        """Scan domains directory for available domains"""
        # Get path to shared prompts directory
        domains_path = Path(__file__).parent.parent.parent / "prompts" / "domains"
        domains = []

        # Scan subdirectories for .yaml files (domains are organized in categories)
        for item in domains_path.iterdir():
            if item.is_dir():
                # Scan each category subdirectory for .yaml files
                for yaml_file in item.glob("*.yaml"):
                    domain_name = yaml_file.stem
                    domains.append(domain_name)
            elif item.is_file() and item.suffix == ".yaml":
                # Also handle any .yaml files in root (for backwards compatibility)
                domain_name = item.stem
                domains.append(domain_name)

        return sorted(domains)

    def _load_prompt_templates(self) -> dict:
        """Load prompt templates from YAML file - prefer user customization"""
        # First try user-customizable location
        user_prompts_path = Path(".khive/prompts/agent_prompts.yaml")

        # Fallback to package defaults
        default_prompts_path = (
            Path(__file__).parent.parent.parent / "prompts" / "agent_prompts.yaml"
        )

        # Use user prompts if available
        prompts_path = (
            user_prompts_path if user_prompts_path.exists() else default_prompts_path
        )

        if not prompts_path.exists():
            raise FileNotFoundError(f"Required prompts file not found: {prompts_path}")

        with open(prompts_path) as f:
            templates = yaml.safe_load(f)

        # Validate required keys
        required_keys = ["agents", "base_context_template", "user_prompt_template"]
        for key in required_keys:
            if key not in templates:
                raise ValueError(f"Missing required key '{key}' in prompts YAML")

        return templates

    def _load_decision_matrix(self) -> dict:
        """Load decision matrix YAML for complexity assessment - prefer user customization"""
        # First try user-customizable location
        user_matrix_path = Path(".khive/prompts/decision_matrix.yaml")

        # Fallback to package defaults
        default_matrix_path = (
            Path(__file__).parent.parent.parent / "prompts" / "decision_matrix.yaml"
        )

        # Use user matrix if available
        matrix_path = (
            user_matrix_path if user_matrix_path.exists() else default_matrix_path
        )

        if not matrix_path.exists():
            raise FileNotFoundError(
                f"Required decision matrix not found: {matrix_path}"
            )

        with open(matrix_path) as f:
            matrix = yaml.safe_load(f)

        # Validate required sections
        required_sections = ["complexity_assessment", "agent_role_selection"]
        for section in required_sections:
            if section not in matrix:
                raise ValueError(
                    f"Missing required section '{section}' in decision matrix"
                )

        return matrix

    def _get_timeout_manager(self, session_id: str) -> TimeoutManager:
        """Get or create timeout manager for session."""
        if (
            self.timeout_manager is None
            or self.timeout_manager.session_id != session_id
        ):
            self.timeout_manager = TimeoutManager(
                config=self.timeout_config, session_id=session_id
            )
        return self.timeout_manager

    def create_session(self, task_description: str) -> str:
        """Create new session with artifact management structure"""
        # Generate session ID from timestamp and task
        timestamp = TimePolicy.now_utc().strftime("%Y%m%d_%H%M%S")
        task_slug = "".join(
            c for c in task_description.lower()[:20] if c.isalnum() or c in "-_"
        )
        session_id = f"{task_slug}_{timestamp}"

        session_dir = self.workspace_dir / session_id
        session_dir.mkdir(exist_ok=True)

        # Initialize artifact registry
        registry = {
            "session_id": session_id,
            "created_at": TimePolicy.now_utc().isoformat(),
            "task_description": task_description,
            "artifacts": [],
            "phases": [],
            "status": "active",
        }

        registry_path = session_dir / "artifact_registry.json"
        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=2)

        self.current_session_id = session_id
        return session_id

    def assess(self, req: Request) -> ComplexityTier:
        """Assess request complexity and return tier (ComplexityAssessor trait implementation)"""
        # Get complexity assessment rules from decision matrix
        complexity_rules = self.matrix.get("complexity_assessment", {})

        hits = []

        # Check each complexity tier for indicator matches
        for tier, rules in complexity_rules.items():
            indicators = rules.get("indicators", [])

            # Check if all indicators for this tier are present in the request
            if all(
                indicator.replace("_", " ") in req.text for indicator in indicators
            ) or any(
                indicator.replace("_", " ") in req.text for indicator in indicators
            ):
                hits.append(tier)

        # If no direct hits, use heuristics based on request content
        if not hits:
            hits = self._assess_by_heuristics(req)

        # Return the highest complexity tier found
        tier = max(hits, key=self._tier_rank) if hits else "medium"

        # Apply RAGRS complexity modifiers if applicable
        tier = self._apply_complexity_modifiers(req, tier)

        return ComplexityTier(tier)

    def _tier_rank(self, tier: str) -> int:
        """Get numeric rank for complexity tier (for max() comparison)"""
        tier_ranks = {"simple": 1, "medium": 2, "complex": 3, "very_complex": 4}
        return tier_ranks.get(tier, 2)  # Default to medium

    def _assess_by_heuristics(self, req: Request) -> list[str]:
        """Assess complexity using heuristic patterns when direct indicators don't match"""
        hits = []
        text = req.text

        # Simple indicators
        simple_patterns = [
            "simple",
            "basic",
            "quick",
            "easy",
            "straightforward",
            "single",
            "one",
            "just",
            "only",
            "minimal",
        ]

        # Complex indicators
        complex_patterns = [
            "complex",
            "complicated",
            "advanced",
            "sophisticated",
            "distributed",
            "scalable",
            "enterprise",
            "production",
            "multiple",
            "many",
            "various",
            "comprehensive",
        ]

        # Very complex indicators
        very_complex_patterns = [
            "research",
            "novel",
            "innovative",
            "cutting-edge",
            "entire",
            "complete",
            "full",
            "platform",
            "ecosystem",
            "migration",
            "transformation",
            "overhaul",
        ]

        # Count pattern matches
        simple_count = sum(1 for pattern in simple_patterns if pattern in text)
        complex_count = sum(1 for pattern in complex_patterns if pattern in text)
        very_complex_count = sum(
            1 for pattern in very_complex_patterns if pattern in text
        )

        # Determine complexity based on pattern density
        if very_complex_count >= 2 or any(
            pattern in text for pattern in ["entire system", "complete platform"]
        ):
            hits.append("very_complex")
        elif complex_count >= 2 or any(
            pattern in text for pattern in ["distributed system", "microservices"]
        ):
            hits.append("complex")
        elif simple_count >= 2:
            hits.append("simple")
        else:
            hits.append("medium")

        return hits

    def _apply_complexity_modifiers(self, req: Request, base_tier: str) -> str:
        """Apply RAGRS complexity modifiers based on domain triggers"""
        modifiers = self.matrix.get("ragrs_complexity_modifiers", {})

        # Check for distributed consensus
        if (
            any(
                keyword in req.text
                for keyword in ["consensus", "byzantine", "distributed", "fault"]
            )
            and "distributed_consensus" in modifiers
        ):
            modifier = modifiers["distributed_consensus"]
            if modifier.get("complexity_increase") == "+1 level":
                tier_order = ["simple", "medium", "complex", "very_complex"]
                current_idx = (
                    tier_order.index(base_tier) if base_tier in tier_order else 1
                )
                if current_idx < len(tier_order) - 1:
                    return tier_order[current_idx + 1]

        # Check for energy constraints
        if (
            any(
                keyword in req.text
                for keyword in ["energy", "optimization", "performance", "efficiency"]
            )
            and ("microsecond" in req.text or "nanosecond" in req.text)
            and "energy_constraints" in modifiers
        ):
            modifier = modifiers["energy_constraints"]
            if "+1 level" in modifier.get("complexity_increase", ""):
                tier_order = ["simple", "medium", "complex", "very_complex"]
                current_idx = (
                    tier_order.index(base_tier) if base_tier in tier_order else 1
                )
                if current_idx < len(tier_order) - 1:
                    return tier_order[current_idx + 1]

        return base_tier

    def select_roles(self, req: Request, complexity: ComplexityTier) -> list[str]:
        """Select appropriate roles based on request and complexity (RoleSelector trait implementation)"""
        role_rules = self.matrix.get("agent_role_selection", {})

        # Determine which phases are needed based on request content
        needed_phases = self._determine_required_phases(req)

        # Collect roles from required phases
        selected_roles = set()
        for phase in needed_phases:
            if phase in role_rules:
                phase_roles = role_rules[phase].get("roles", [])
                selected_roles.update(phase_roles)

        # Convert to list and apply complexity scaling
        base_roles = list(selected_roles)

        # Scale based on complexity - trim for simple, expand for very complex
        if complexity == ComplexityTier.SIMPLE and len(base_roles) > 4:
            # Keep core roles: researcher, implementer + 1-2 others
            priority_order = ["researcher", "implementer", "analyst", "architect"]
            selected_roles = [r for r in priority_order if r in base_roles][:4]
        elif complexity == ComplexityTier.VERY_COMPLEX:
            # Ensure we have comprehensive coverage - add any missing critical roles
            critical_roles = [
                "researcher",
                "analyst",
                "theorist",
                "architect",
                "strategist",
                "implementer",
                "tester",
                "critic",
                "reviewer",
            ]
            for role in critical_roles:
                if role not in base_roles:
                    base_roles.append(role)
            selected_roles = base_roles
        else:
            selected_roles = base_roles

        # Check for RAGRS domain triggers and add mandatory roles
        ragrs_triggers = self.matrix.get("ragrs_domain_triggers", {})

        for trigger_config in ragrs_triggers.values():
            keywords = trigger_config.get("keywords", [])
            if any(keyword in req.text for keyword in keywords):
                mandatory_roles = trigger_config.get("mandatory_roles", [])
                for role in mandatory_roles:
                    if role not in selected_roles:
                        selected_roles.append(role)

        return selected_roles

    def _determine_required_phases(self, req: Request) -> list[str]:
        """Determine which development phases are needed based on request content"""
        text = req.text.lower()
        phases = []

        # Discovery phase - always needed for research/analysis tasks
        discovery_keywords = [
            "research",
            "analyze",
            "understand",
            "investigate",
            "explore",
            "study",
            "examine",
        ]
        if (
            any(keyword in text for keyword in discovery_keywords)
            or "what" in text
            or "how" in text
        ):
            phases.append("discovery_phase")

        # Design phase - needed for architecture/planning tasks
        design_keywords = [
            "design",
            "architect",
            "plan",
            "structure",
            "framework",
            "strategy",
            "approach",
        ]
        if any(keyword in text for keyword in design_keywords):
            phases.append("design_phase")

        # Implementation phase - needed for building/coding tasks
        impl_keywords = [
            "implement",
            "build",
            "create",
            "develop",
            "code",
            "write",
            "construct",
            "make",
        ]
        if any(keyword in text for keyword in impl_keywords):
            phases.append("implementation_phase")

        # Validation phase - needed for testing/verification tasks
        validation_keywords = [
            "test",
            "verify",
            "validate",
            "check",
            "audit",
            "review",
            "quality",
            "security",
        ]
        if any(keyword in text for keyword in validation_keywords):
            phases.append("validation_phase")

        # Refinement phase - needed for documentation/improvement tasks
        refinement_keywords = [
            "document",
            "improve",
            "refine",
            "optimize",
            "polish",
            "comment",
            "explain",
        ]
        if any(keyword in text for keyword in refinement_keywords):
            phases.append("refinement_phase")

        # Default phases if none detected
        if not phases:
            # Most tasks need at least discovery and implementation
            phases = ["discovery_phase", "implementation_phase"]

        return phases

    async def execute_agent_with_timeout(
        self,
        agent_id: str,
        agent_task: callable,
        timeout_type: TimeoutType = TimeoutType.AGENT_EXECUTION,
        *args,
        **kwargs,
    ) -> dict:
        """
        Execute an agent task with timeout handling.

        Args:
            agent_id: Unique identifier for the agent
            agent_task: The agent task function to execute
            timeout_type: Type of timeout to apply
            *args: Arguments for the agent task
            **kwargs: Keyword arguments for the agent task

        Returns:
            Dictionary with execution result and metrics
        """
        if not self.current_session_id:
            raise ValueError("No active session. Create a session first.")

        timeout_manager = self._get_timeout_manager(self.current_session_id)

        # Execute agent task with timeout
        result = await timeout_manager.execute_with_timeout(
            agent_id,
            timeout_type,
            agent_task,
            *args,
            **kwargs,
        )

        # Return result with additional metadata
        return {
            "agent_id": agent_id,
            "status": result.status,
            "duration": result.duration,
            "retry_count": result.retry_count,
            "error": result.error,
            "execution_time": result.end_time.isoformat() if result.end_time else None,
        }

    async def execute_agents_parallel(
        self,
        agent_tasks: list[tuple[str, callable]],
        timeout_type: TimeoutType = TimeoutType.AGENT_EXECUTION,
    ) -> list[dict]:
        """
        Execute multiple agent tasks in parallel with timeout handling.

        Args:
            agent_tasks: List of (agent_id, agent_task) tuples
            timeout_type: Type of timeout to apply

        Returns:
            List of execution results
        """
        if not self.current_session_id:
            raise ValueError("No active session. Create a session first.")

        # Create parallel execution tasks
        tasks = []
        for agent_id, agent_task in agent_tasks:
            task = asyncio.create_task(
                self.execute_agent_with_timeout(
                    agent_id=agent_id, agent_task=agent_task, timeout_type=timeout_type
                )
            )
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                agent_id = agent_tasks[i][0]
                processed_results.append(
                    {
                        "agent_id": agent_id,
                        "status": "error",
                        "duration": None,
                        "retry_count": 0,
                        "error": str(result),
                        "execution_time": None,
                    }
                )
            else:
                processed_results.append(result)

        return processed_results

    async def get_timeout_metrics(self) -> dict:
        """Get timeout and performance metrics for the current session."""
        if not self.timeout_manager:
            return {
                "total_operations": 0,
                "successful_operations": 0,
                "timeout_rate": 0.0,
                "performance_improvement": 0.0,
            }

        return await self.timeout_manager.get_performance_metrics()

    async def evaluate_request(self, request: str) -> list[dict]:
        """Evaluate with multiple agents concurrently"""

        configs = self.get_evaluation_configs()
        evaluations = []

        print(f"📊 Evaluating with {len(configs)} agents concurrently...")

        # Create tasks that handle their own exceptions
        tasks = []
        for config in configs:
            task = asyncio.create_task(self._safe_evaluation(request, config))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)

        # Process results
        for config, result in zip(configs, results, strict=False):
            if result is not None:
                if "error" in result:
                    print(f"❌ {config['name']} failed: {result['error']}")
                else:
                    evaluations.append(result)
                    print(f"✅ {config['name']}")

        print(f"\n📊 Evaluated {len(evaluations)} agents successfully")

        return evaluations

    async def _safe_evaluation(self, request: str, config: dict) -> dict:
        """Safely run evaluation, catching exceptions"""
        try:
            return await self._run_single_evaluation(request, config)
        except Exception as e:
            # Return exception info as a special result
            return {"error": str(e), "config": config}

    async def _run_single_evaluation(self, request: str, config: dict) -> dict:
        """Run evaluation with single agent using sync client in thread"""

        # Use YAML template for user prompt
        user_prompt_template = self.prompt_templates.get("user_prompt_template", "")
        if user_prompt_template:
            user_prompt = user_prompt_template.format(request=request)
        else:
            # Fallback to hardcoded prompt
            user_prompt = f"""Request: {request}

Provide orchestration evaluation. Keep reasons under 250 chars.
For role_priorities, provide a priority-ordered list of roles you recommend (most important first).
Example: ["researcher", "analyst", "critic", "implementer"]
Be different - show YOUR unique perspective on which roles matter most."""

        start_time = time.time()

        # Run sync OpenAI client in thread pool
        response = await asyncio.to_thread(
            self.client.beta.chat.completions.parse,
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": config["system_prompt"]},
                {"role": "user", "content": user_prompt},
            ],
            response_format=OrchestrationEvaluation,
        )

        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)

        # Extract response
        evaluation = response.choices[0].message.parsed
        usage = response.usage

        # Track cost
        cost = self.cost_tracker.add_request(
            usage.prompt_tokens, usage.completion_tokens, 0
        )

        return {
            "config": config,
            "evaluation": evaluation,
            "cost": cost,
            "usage": usage,
            "response_time_ms": response_time_ms,
        }

    def get_evaluation_configs(self) -> list[dict]:
        """Define different agent perspectives using YAML templates"""
        # Get path to shared prompts directory
        dp = Path(__file__).parent.parent.parent / "prompts" / "decision_matrix.yaml"
        decision_matrix_text = dp.read_text() if dp.exists() else ""

        roles_str = ", ".join(self.available_roles)
        domains_str = ", ".join(self.available_domains)

        # BUDGET AWARENESS: Fetch budgets from CostTracker
        token_budget = self.cost_tracker.get_token_budget()
        latency_budget = self.cost_tracker.get_latency_budget()
        cost_budget = self.cost_tracker.get_cost_budget()

        # Build base context from template
        base_context_template = self.prompt_templates.get("base_context_template", "")
        base_context = base_context_template.format(
            roles_str=roles_str,
            domains_str=domains_str,
            token_budget=token_budget,
            latency_budget=latency_budget,
            cost_budget=cost_budget,
            decision_matrix_content=(
                f"\n\nDecision Matrix:\n{decision_matrix_text.strip()}\n"
                if decision_matrix_text
                else ""
            ),
        )

        # Build agent configurations from YAML templates
        configs = []
        agents_config = self.prompt_templates.get("agents", {})

        for agent_name, agent_config in agents_config.items():
            system_prompt_template = agent_config.get("system_prompt_template", "")
            system_prompt = system_prompt_template.format(
                base_context=base_context,
                bias=agent_config.get("bias", ""),
                token_budget=token_budget,
                latency_budget=latency_budget,
                cost_budget=cost_budget,
                gate="thorough",  # Default gate for template
            )

            configs.append(
                {
                    "name": agent_config.get("name", agent_name),
                    "system_prompt": system_prompt,
                    # "temperature": agent_config.get("temperature", 0.3),
                    "description": agent_config.get("description", ""),
                }
            )

        # Fallback to hardcoded if YAML not available
        if not configs:
            return self._get_fallback_configs(base_context)

        return configs

    def _get_fallback_configs(self, base_context: str) -> list[dict]:
        """Fallback configurations if YAML not available"""
        return [
            {
                "name": "efficiency_analyst",
                "system_prompt": f"You MINIMIZE resources aggressively. Start with bare minimum.\n{base_context}\nYOUR BIAS: Prefer researcher→analyst→architect→implementer. Avoid redundant validation roles. Push for LOWER complexity ratings.",
            },
            {
                "name": "quality_architect",
                "system_prompt": f"You MAXIMIZE quality obsessively. Never compromise on validation.\n{base_context}\nYOUR BIAS: Always include critic→tester→reviewer→auditor. Push for CRITICAL quality on distributed/event systems. Add 20-30% more agents.",
            },
            {
                "name": "risk_auditor",
                "system_prompt": f"You are PARANOID about risks. Assume everything will fail.\n{base_context}\nYOUR BIAS: Auditor→tester→critic ALWAYS in top 3. Distributed=VeryComplex. Event-driven=VeryComplex. Double validation roles.",
            },
            {
                "name": "innovation_strategist",
                "system_prompt": f"You seek BREAKTHROUGH solutions. Think differently.\n{base_context}\nYOUR BIAS: innovator→strategist→architect→researcher. Suggest unusual role combinations. Push boundaries but stay practical.",
            },
        ]

    def build_consensus(
        self, evaluations: list[dict], request: str = ""
    ) -> tuple[str, dict]:
        """Build consensus from multiple evaluations

        Returns:
            Tuple of (formatted_output, consensus_data)
        """
        output = []
        output.append("## 🎯 Orchestration Planning Consensus\n")

        # Meta-insights analysis
        meta_insights = self._analyze_meta_insights(evaluations)
        output.append(meta_insights)
        output.append("")

        # Collect all evaluations
        all_evals = [e["evaluation"] for e in evaluations]

        # Complexity consensus
        complexities = [e.complexity for e in all_evals]
        complexity_counts = {c: complexities.count(c) for c in set(complexities)}
        consensus_complexity = max(complexity_counts, key=complexity_counts.get)

        output.append(f"Complexity Consensus: {consensus_complexity}")
        output.append("Agent assessments:")
        for evaluation in evaluations:
            e = evaluation["evaluation"]
            output.append(
                f"- {evaluation['config']['name']}: {e.complexity} - {e.complexity_reason}"
            )
        output.append("")

        # Agent count consensus with weighted voting
        agent_counts = [e.total_agents for e in all_evals]

        # Apply weighted voting (cost_optimizer and efficiency_analyst get x2 weight when budget tight)
        is_budget_tight = self.cost_tracker.total_cost >= (
            self.cost_tracker.get_cost_budget() * 0.8
        )

        weighted_sum = 0
        total_weight = 0

        for evaluation in evaluations:
            e = evaluation["evaluation"]
            agent_name = evaluation["config"]["name"]

            # Default weight
            weight = 1.0

            # Give cost-conscious agents more weight when budget is tight (reduced from 2.0 to 1.5)
            if is_budget_tight and agent_name in [
                "cost_optimizer",
                "efficiency_analyst",
            ]:
                weight = 1.5

            weighted_sum += e.total_agents * weight
            total_weight += weight

        avg_agents = (
            weighted_sum / total_weight
            if total_weight > 0
            else sum(agent_counts) / len(agent_counts)
        )

        output.append(
            f"Total Agents: {min(agent_counts)}-{max(agent_counts)} (avg: {avg_agents:.0f})"
        )
        output.append("Agent recommendations:")
        for evaluation in evaluations:
            e = evaluation["evaluation"]
            output.append(
                f"- {evaluation['config']['name']}: {e.total_agents} agents - {e.agent_reason}"
            )
        output.append("")

        # Calculate weighted role recommendations with position-based scoring
        output.append("Top 10 Role Recommendations (Position-Weighted):")
        role_scores = {}
        role_mentions = {}  # Track how many agents mentioned each role

        for evaluation in evaluations:
            e = evaluation["evaluation"]
            agent_weight = e.confidence

            # Score based on position in priority list
            for position, role in enumerate(e.role_priorities):
                if role not in role_scores:
                    role_scores[role] = 0
                    role_mentions[role] = 0

                # Position weight: 1st place = 1.0, 2nd = 0.8, 3rd = 0.6, etc.
                position_weight = max(0.2, 1.0 - (position * 0.2))
                role_scores[role] += position_weight * agent_weight
                role_mentions[role] += 1

        # Normalize by number of evaluations
        for role in role_scores:
            role_scores[role] = role_scores[role] / len(evaluations)

        sorted_roles = sorted(role_scores.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]

        for role, score in sorted_roles:
            mentions = role_mentions[role]
            output.append(
                f"- {role}: {score:.2f} score (mentioned by {mentions}/{len(evaluations)} agents)"
            )
        output.append("")

        # Show individual agent recommendations
        output.append("Individual Agent Priority Lists:")
        for evaluation in evaluations:
            e = evaluation["evaluation"]
            roles_str = " → ".join(e.role_priorities[:5])  # Show top 5
            output.append(
                f"- {evaluation['config']['name']} ({e.confidence:.0%}): {roles_str}"
            )
        output.append("")

        # Domain consensus
        all_domains = []
        for e in all_evals:
            all_domains.extend(e.primary_domains)
        domain_counts = {d: all_domains.count(d) for d in set(all_domains)}
        top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        output.append("Top Domains (by frequency):")
        for domain, count in top_domains:
            output.append(f"- {domain}: {count}/{len(evaluations)} agents")
        output.append("")

        # Workflow pattern consensus
        patterns = [e.workflow_pattern for e in all_evals]
        pattern_counts = {p: patterns.count(p) for p in set(patterns)}
        consensus_pattern = max(pattern_counts, key=pattern_counts.get)

        output.append(f"Workflow Pattern: {consensus_pattern}")
        output.append(
            f"Agreement: {pattern_counts[consensus_pattern]}/{len(evaluations)} agents"
        )
        output.append("")

        # Quality level consensus with gate escalation middleware
        qualities = [e.quality_level for e in all_evals]
        quality_counts = {q: qualities.count(q) for q in set(qualities)}
        consensus_quality = max(quality_counts, key=quality_counts.get)

        # Gate escalation middleware with full auditor enforcement
        has_auditor = any("auditor" in e.role_priorities for e in all_evals)

        # Rule 1: If gate == critical, ensure auditor is present
        if consensus_quality == "critical" and not has_auditor:
            # This would require modifying the role priorities, which we'll note
            escalation_note = (
                " (critical gate requires auditor - recommend adding auditor role)"
            )
        # Rule 2: If auditor present and gate == basic, upgrade to thorough
        elif has_auditor and consensus_quality == "basic":
            consensus_quality = "thorough"
            escalation_note = " (auto-escalated from basic due to auditor presence)"
        else:
            escalation_note = ""

        output.append(f"Quality Level: {consensus_quality}{escalation_note}")
        original_agreement = quality_counts.get(consensus_quality, 0)
        output.append(f"Agreement: {original_agreement}/{len(evaluations)} agents")
        output.append("")

        # Confidence scores
        confidences = [e.confidence for e in all_evals]
        avg_confidence = sum(confidences) / len(confidences)

        output.append(f"Overall Confidence: {avg_confidence:.0%}")
        output.append("Individual confidence scores:")
        output.extend(
            f"- {evaluation['config']['name']}: {evaluation['evaluation'].confidence:.0%}"
            for evaluation in evaluations
        )
        output.append("")

        # Add context reminder for orchestrator
        output.append("📝 CRITICAL CONTEXT REMINDER:")
        output.append(
            "As orchestrator, you MUST provide FULL CONTEXT to Task agents since this planner"
        )
        output.append(
            "doesn't know the complete request details. Each Task agent prompt should include:"
        )
        output.append("- Original user request in detail")
        output.append("- Specific requirements and constraints")
        output.append("- Expected deliverables and success criteria")
        output.append("- How their work integrates with other agents")
        output.append("")

        # Generate Parallel Fan-Out Execution Plan
        output.append("📋 Parallel Fan-Out Execution Plan:")
        output.append("```javascript")
        output.append(
            "// PARALLEL EXECUTION: Deploy agents simultaneously with dependency resolution"
        )
        output.append("[BatchTool]:")

        # Use actual top domains from consensus
        domain_list = (
            [domain for domain, _ in top_domains[:3]]
            if top_domains
            else ["distributed-systems"]
        )

        # Get consensus info for context
        consensus_complexity_str = (
            consensus_complexity if consensus_complexity else "medium"
        )
        avg_confidence = sum(e.confidence for e in all_evals) / len(all_evals)

        # Initialize Composer for domain canonicalization and duplicate prevention
        from khive.services.composition import AgentComposer

        composer = AgentComposer(Path(__file__).parent.parent.parent / "prompts")

        # Track seen combinations to prevent duplicates
        seen_combinations = set()

        # Create session for artifact management
        if not hasattr(self, "current_session_id") or not self.current_session_id:
            session_id = self.create_session(str(request))
        else:
            session_id = self.current_session_id

        # Collect agent specifications with dependency analysis
        agent_specs = []
        dependency_map = self._analyze_role_dependencies(sorted_roles[:10])

        for i, (role, score) in enumerate(sorted_roles[:10]):
            if score >= 0.1:  # Show any role with reasonable score
                # Rotate through top domains for variety
                raw_domain = domain_list[i % len(domain_list)]
                canonical_domain = composer.canonicalize_domain(raw_domain)

                # Create unique combination identifier
                combination = f"{role}:{canonical_domain}"

                # Only add if not seen before
                if combination not in seen_combinations:
                    seen_combinations.add(combination)

                    # Create AgentRecommendation with dependencies
                    agent_spec = AgentRecommendation(
                        role=role,
                        domain=canonical_domain,
                        priority=score,
                        reasoning=f"Essential {role} for {consensus_complexity} complexity task",
                    )
                    agent_specs.append(agent_spec)

                if len(agent_specs) >= int(
                    avg_agents
                ):  # Limit to consensus agent count
                    break

        # Session ID for artifact management (no coordinator needed)

        # Convert AgentRecommendation to HandoffAgentSpec
        handoff_agent_specs = []
        for agent_rec in agent_specs:
            # Get dependencies for this role from the dependency map
            role_dependencies = dependency_map.get(agent_rec.role, [])

            handoff_spec = HandoffAgentSpec(
                role=agent_rec.role,
                domain=agent_rec.domain,
                priority=agent_rec.priority,
                dependencies=role_dependencies,  # Use actual dependencies from analysis
                spawn_command=f"uv run khive compose {agent_rec.role} -d {agent_rec.domain}",
                session_id=session_id,
                phase="phase1",
                context=agent_rec.reasoning,
            )
            handoff_agent_specs.append(handoff_spec)

        # No dependency graph needed - orchestrator handles phasing

        # Use the request parameter passed to build_consensus
        if not request:
            request = "Task not specified"

        # Generate parallel execution commands - all agents can run in parallel
        # Orchestrator will handle phasing based on context
        for agent_spec in handoff_agent_specs:
            agent_name = f"{agent_spec.role}_{agent_spec.domain.replace('-', '_')}"

            # Enhanced context for parallel execution
            artifact_management = self.get_artifact_management_prompt(
                session_id, "phase1", agent_spec.role, agent_spec.domain
            )

            parallel_context = f"""PARALLEL EXECUTION CONTEXT:
- All agents executing in parallel
- Priority: {agent_spec.priority:.2f}
- Coordinate through shared artifacts

ORIGINAL REQUEST: {request}
COMPLEXITY: {consensus_complexity_str} (confidence: {avg_confidence:.0%})

{artifact_management}

CRITICAL PARALLEL EXECUTION INSTRUCTIONS:
- You are part of a parallel fan-out execution
- Check artifact registry for dependency completion status
- Your work may execute simultaneously with other agents
- Coordinate through shared artifact registry
- Wait for dependencies before starting core work

YOUR TASK:
1. Run: `uv run khive compose {agent_spec.role} -d {agent_spec.domain} -c "{request}"`
2. Provide COMPLETE context including parallel execution awareness
3. Monitor dependency completion via artifact registry
4. Execute immediately when dependencies are met

Remember: This is PARALLEL EXECUTION - coordinate via shared artifacts!"""

            # Escape prompt for JavaScript
            escaped_prompt = parallel_context.replace('"', '\\"').replace("\n", "\\n")
            output.append(
                f'  Task({{ description: "{agent_name}", prompt: "{escaped_prompt}" }})'
            )

        # No synchronization points needed - all agents run in parallel

        output.append("```")
        output.append("")

        # Enhanced output generation
        output.append(self._generate_efficiency_analysis(evaluations))

        # Check if task scope is too large
        phase_recommendation = self._check_task_scope(evaluations, request)
        if phase_recommendation:
            output.append(phase_recommendation)

        # Generate intelligent task recommendation
        if request:  # Only if we have the request context
            lion_recommendation = self._generate_task_recommendation(
                evaluations, request
            )
            output.append(lion_recommendation)
        else:
            # Fallback to basic recommendations
            output.append(self._generate_batchtool_composition(evaluations))
            output.append(self._generate_coordination_strategy(evaluations))

        # Performance summary
        avg_time = sum(e["response_time_ms"] for e in evaluations) / len(evaluations)

        output.append("---")
        output.append(
            f"_Evaluated by {len(evaluations)} agents in {avg_time:.0f}ms avg_"
        )

        # Prepare consensus data structure
        consensus_data = {
            "complexity": consensus_complexity,
            "agent_count": int(avg_agents),
            "role_recommendations": sorted_roles,
            "domains": [domain for domain, _ in top_domains],
            "workflow_pattern": consensus_pattern,
            "quality_level": consensus_quality,
            "confidence": avg_confidence,
            "request": request,
        }

        return "\n".join(output), consensus_data

    def get_artifact_management_prompt(
        self, session_id: str, phase: str, agent_role: str, domain: str
    ) -> str:
        """Generate artifact management section for Task agent prompts"""
        session_dir = self.workspace_dir / session_id
        artifact_path = self.generate_artifact_path(
            session_id, phase, agent_role, domain
        )
        registry_path = session_dir / "artifact_registry.json"

        # Get existing artifacts for coordination
        existing_artifacts = []
        if registry_path.exists():
            with open(registry_path) as f:
                registry = json.load(f)
                existing_artifacts = [a["artifact_path"] for a in registry["artifacts"]]

        return f"""
🗂️ ARTIFACT MANAGEMENT (MANDATORY):
1. **Session ID**: {session_id}
2. **Your Deliverable Path**: `{artifact_path}`
3. **Registry Location**: `{registry_path}`
4. **Existing Artifacts**: {len(existing_artifacts)} artifacts in session

📋 COORDINATION PROTOCOL:
- BEFORE starting: Read `{registry_path}` to see existing work
- AVOID duplication: If similar analysis exists, extend rather than duplicate
- FILE NAMING: Use provided path exactly as specified
- CROSS-REFERENCE: Mention other agents' findings when relevant

🔗 REGISTRY UPDATE (when complete):
Your deliverable will be automatically registered. Include in your final report:
- **Key Findings**: 3-5 bullet points of your main discoveries
- **References**: Which other artifacts you built upon
- **Next Steps**: What should happen in next phase
"""

    def generate_artifact_path(
        self, session_id: str, phase: str, agent_role: str, domain: str
    ) -> str:
        """Generate standardized artifact path"""
        session_dir = self.workspace_dir / session_id
        timestamp = TimePolicy.now_utc().strftime("%H%M%S")
        filename = f"{phase}_{agent_role}_{domain}_{timestamp}.md"
        return str(session_dir / filename)

    def _analyze_meta_insights(self, evaluations: list[dict]) -> str:
        """Analyze meta-orchestration insights"""
        all_evals = [e["evaluation"] for e in evaluations]
        agent_counts = [e.total_agents for e in all_evals]
        avg_agents = sum(agent_counts) / len(agent_counts)

        output = []
        output.append("🔬 Meta-Orchestration Analysis")

        # Efficiency cliff analysis
        if max(agent_counts) > 12:
            output.append(
                "⚠️ Efficiency Cliff Warning: Some recommendations exceed 12-agent optimum"
            )

        output.append(
            f"Agent Range: {min(agent_counts)}-{max(agent_counts)} (avg: {avg_agents:.1f})"
        )

        # Cost analysis
        total_cost = sum(e["cost"] for e in evaluations)
        output.append(f"Planning Cost: ${total_cost:.4f}")

        if total_cost > self.target_budget:
            output.append(
                f"⚠️ Cost Warning: Exceeds ${self.target_budget} target budget"
            )

        return "\n".join(output)

    def _check_task_scope(self, evaluations: list[dict], request: str) -> str:
        """Check if task scope is too large and recommend phases"""
        if not evaluations:
            return ""

        # Get agent counts
        all_evals = [e["evaluation"] for e in evaluations]
        agent_counts = [e.total_agents for e in all_evals]
        max_agents = max(agent_counts)
        avg_agents = sum(agent_counts) / len(agent_counts)

        # Check for scope indicators in request
        request_lower = request.lower()
        scope_indicators = {
            "entire": "Task mentions 'entire' system/platform",
            "complete": "Task mentions 'complete' solution",
            "full": "Task mentions 'full' implementation",
            "migrate": "Migration tasks are typically multi-phase",
            "platform": "Platform-level tasks exceed single orchestration",
            "everything": "Task scope includes 'everything'",
        }

        # Check for monolithic tasks
        triggered_indicators = [
            desc for word, desc in scope_indicators.items() if word in request_lower
        ]

        # Check if agents exceed reasonable limits
        if max_agents > 12 or avg_agents > 10 or triggered_indicators:
            output = []
            output.append("⚠️ Task Scope Analysis")

            if max_agents > 12:
                output.append(
                    f"Agent Count Warning: Max {max_agents} agents exceeds 12-agent limit"
                )

            if triggered_indicators:
                output.append(f"Scope Indicators: {', '.join(triggered_indicators)}")

            output.append("")
            output.append("📋 Recommended Phase Breakdown:")

            # Generate phase suggestions based on task type
            if "migrate" in request_lower:
                output.append("- Phase 1: Analysis & Planning (5-6 agents)")
                output.append("- Phase 2: Data Migration Strategy (6-7 agents)")
                output.append("- Phase 3: Service Implementation (7-8 agents)")
                output.append("- Phase 4: Cutover & Validation (5-6 agents)")
            elif "platform" in request_lower or "entire" in request_lower:
                output.append("- Phase 1: Core Infrastructure (6-8 agents)")
                output.append("- Phase 2: Business Logic Layer (7-8 agents)")
                output.append("- Phase 3: User Interface (5-7 agents)")
                output.append("- Phase 4: Integration & Testing (6-7 agents)")
            else:
                output.append("- Phase 1: Research & Architecture (5-7 agents)")
                output.append("- Phase 2: Core Implementation (6-8 agents)")
                output.append("- Phase 3: Integration & Testing (5-6 agents)")

            output.append("")
            output.append(
                '💡 Tip: Run `khive plan "Phase 1: [specific task]"` for each phase'
            )
            output.append("")

            return "\n".join(output)

        return ""

    def _generate_efficiency_analysis(self, evaluations: list[dict]) -> str:
        """Generate efficiency analysis"""
        output = []
        output.append("⚡ Efficiency Analysis")

        all_evals = [e["evaluation"] for e in evaluations]
        agent_counts = [e.total_agents for e in all_evals]

        # Efficiency recommendations
        if max(agent_counts) <= 8:
            output.append(
                "✅ Efficient Range: All recommendations within optimal 8-12 agent range"
            )
        elif max(agent_counts) <= 12:
            output.append(
                "✅ Optimal Range: Recommendations within 12-agent efficiency cliff"
            )
        else:
            output.append(
                "⚠️ Over-Staffed: Consider decomposing task to stay under 12 agents"
            )

        return "\n".join(output)

    def _generate_batchtool_composition(self, evaluations: list[dict]) -> str:
        """Generate BatchTool composition strategy"""
        output = []
        output.append("📦 BatchTool Composition Strategy")

        all_evals = [e["evaluation"] for e in evaluations]
        patterns = [e.workflow_pattern for e in all_evals]

        if "parallel" in patterns:
            output.append("Parallel Batch Execution: Deploy all agents simultaneously")
        elif "hybrid" in patterns:
            output.append(
                "Hybrid Batch Execution: Parallel research, sequential synthesis"
            )
        else:
            output.append("Sequential Batch Execution: Phase-by-phase deployment")

        return "\n".join(output)

    def _generate_coordination_strategy(self, evaluations: list[dict]) -> str:
        """Generate coordination strategy"""
        output = []
        output.append("🎯 Coordination Strategy")

        all_evals = [e["evaluation"] for e in evaluations]
        agent_counts = [e.total_agents for e in all_evals]
        avg_agents = sum(agent_counts) / len(agent_counts)

        if avg_agents <= 5:
            output.append("Strategy: Direct coordination with minimal overhead")
        elif avg_agents <= 10:
            output.append("Strategy: Hierarchical coordination with team leads")
        else:
            output.append(
                "Strategy: Multi-tier coordination with sub-team organization"
            )

        output.append(
            "Memory Coordination: Use lion-task memory keys for state management"
        )
        output.append("Progress Tracking: Post-edit hooks after major milestones")

        return "\n".join(output)

    def _generate_task_recommendation(
        self, evaluations: list[dict], request: str
    ) -> str:
        """Generate lion-task orchestration recommendation"""
        return "### 🚀 Lion-Task Orchestration Ready\n\nUse Task agents for coordinated execution without swarm overhead."

    async def cleanup(self):
        """Clean up resources including timeout manager."""
        if self.timeout_manager:
            await self.timeout_manager.cleanup()
            self.timeout_manager = None

    def _analyze_role_dependencies(
        self, sorted_roles: list[tuple]
    ) -> dict[str, list[str]]:
        """Analyze dependencies between roles for parallel execution"""
        dependency_map = {}

        # Most roles can work independently - orchestrator handles phasing
        role_dependencies = {
            "implementer": [
                "architect"
            ],  # Only hard requirement: implementer needs architecture
            "tester": ["implementer"],  # Tester needs something to test
            "commentator": ["implementer"],  # Commentator documents what was built
            "auditor": [],  # Can audit at any phase
            "critic": [],  # Can provide critique independently
            "reviewer": [],  # Can review plans or implementations
            "architect": [],  # Can design independently
            "strategist": [],  # Can strategize independently
            "innovator": [],  # Can innovate independently
            "theorist": [],  # Can theorize independently
            "researcher": [],  # Can research immediately
            "analyst": [],  # Can analyze immediately
        }

        # Extract role names from sorted_roles
        available_roles = [role for role, _ in sorted_roles]

        # Build dependency map for available roles only
        for role in available_roles:
            dependencies = [
                dep for dep in role_dependencies.get(role, []) if dep in available_roles
            ]
            dependency_map[role] = dependencies

        return dependency_map

    def _organize_execution_tiers(
        self, agent_specs: list[HandoffAgentSpec]
    ) -> list[list[HandoffAgentSpec]]:
        """Organize agents into execution tiers based on dependencies"""
        tiers = []
        remaining_agents = agent_specs.copy()
        completed_roles = set()

        while remaining_agents:
            # Find agents that can execute now (dependencies met)
            current_tier = []

            for agent in remaining_agents[:]:
                # Check if all dependencies are satisfied
                if all(dep in completed_roles for dep in agent.dependencies):
                    current_tier.append(agent)
                    remaining_agents.remove(agent)

            # If no agents can execute, we have a circular dependency or missing dependency
            if not current_tier:
                logger.warning(
                    f"Circular dependency detected. Remaining agents: {[a.role for a in remaining_agents]}"
                )
                # Add remaining agents to current tier to prevent infinite loop
                current_tier = remaining_agents
                remaining_agents = []

            tiers.append(current_tier)

            # Update completed roles
            completed_roles.update(agent.role for agent in current_tier)

        return tiers


class PlannerService:
    """
    Orchestration Planning Service.

    Wraps the OrchestrationPlanner to provide intelligent task planning
    and agent recommendations for complex workflows.
    """

    def __init__(self):
        """Initialize the planner service."""
        self._planner = None
        self._planner_lock = asyncio.Lock()
        self._triage_service = None
        self._triage_lock = asyncio.Lock()

        # Metrics tracking
        self.metrics = {
            "total_requests": 0,
            "triage_simple": 0,
            "triage_complex": 0,
            "total_cost": 0.0,
            "total_llm_calls": 0,
            "escalation_rate": 0.0,
        }

    async def _get_planner(self) -> OrchestrationPlanner:
        """Get or create the orchestration planner."""
        if self._planner is None:
            async with self._planner_lock:
                if self._planner is None:
                    # Create optimized timeout config for planner service
                    timeout_config = TimeoutConfig(
                        agent_execution_timeout=300.0,  # 5 minutes
                        phase_completion_timeout=1800.0,  # 30 minutes
                        total_orchestration_timeout=3600.0,  # 1 hour
                        max_retries=3,
                        retry_delay=5.0,
                        escalation_enabled=True,
                        performance_threshold=0.9,
                        timeout_reduction_factor=0.3,
                    )
                    self._planner = OrchestrationPlanner(timeout_config=timeout_config)
        return self._planner

    async def _get_triage_service(self) -> ComplexityTriageService:
        """Get or create the triage service."""
        if self._triage_service is None:
            async with self._triage_lock:
                if self._triage_service is None:
                    # Triage service will load API key from environment
                    self._triage_service = ComplexityTriageService()
        return self._triage_service

    def _build_simple_response(
        self,
        request: PlannerRequest,
        triage_consensus: TriageConsensus,
        session_id: str,
    ) -> PlannerResponse:
        """Build a simple response from triage consensus."""
        agent_recommendations = []

        # Build agent recommendations from triage consensus
        if triage_consensus.final_roles:
            domains = triage_consensus.final_domains or ["software-architecture"]
            for i, role in enumerate(triage_consensus.final_roles):
                domain = domains[i % len(domains)]
                agent_recommendations.append(
                    AgentRecommendation(
                        role=role,
                        domain=domain,
                        priority=1.0 - (i * 0.2),
                        reasoning=triage_consensus.consensus_reasoning
                        or f"Triage-selected {role} for simple task",
                    )
                )

        # Single phase for simple tasks
        phase = TaskPhase(
            name="execution_phase",
            description="Execute the simple task",
            agents=agent_recommendations,
            quality_gate=QualityGate.BASIC,
            coordination_pattern=WorkflowPattern.PARALLEL,
        )

        return PlannerResponse(
            success=True,
            summary=f"Triage consensus (3 LLMs): {triage_consensus.complexity_votes}",
            complexity=ComplexityLevel.SIMPLE,
            recommended_agents=triage_consensus.final_agent_count or 2,
            phases=[phase],
            spawn_commands=[],  # Simple tasks don't need spawn commands
            session_id=session_id,
            confidence=triage_consensus.average_confidence,
            error=None,
        )

    async def handle_request(self, request: PlannerRequest) -> PlannerResponse:
        """
        Handle a planning request with two-tier triage system.

        Args:
            request: The planning request

        Returns:
            Planning response with orchestration plan
        """
        try:
            # Parse request if needed
            if isinstance(request, str):
                request = PlannerRequest.model_validate_json(request)
            elif isinstance(request, dict):
                request = PlannerRequest.model_validate(request)

            # Update metrics
            self.metrics["total_requests"] += 1

            # === TIER 1: TRIAGE (3 LLMs, temp=0) ===
            triage_service = await self._get_triage_service()
            should_escalate, triage_consensus = await triage_service.triage(
                request.task_description
            )

            # Track metrics
            self.metrics["total_llm_calls"] += 3  # 3 triage calls
            self.metrics["total_cost"] += 0.001  # 3 mini calls

            # Create session ID for either path
            session_id = (
                f"{'complex' if should_escalate else 'simple'}_{int(time.time())}"
            )

            if not should_escalate:
                # Simple task - use triage consensus
                self.metrics["triage_simple"] += 1
                logger.info(
                    f"Simple task handled by triage: {triage_consensus.final_agent_count} agents, "
                    f"confidence: {triage_consensus.average_confidence:.2f}"
                )

                # Build and return simple response
                response = self._build_simple_response(
                    request, triage_consensus, session_id
                )

                # Update escalation rate
                self.metrics["escalation_rate"] = (
                    self.metrics["triage_complex"] / self.metrics["total_requests"]
                )

                return response

            # === TIER 2: FULL CONSENSUS (10 LLMs) ===
            self.metrics["triage_complex"] += 1
            logger.info(
                f"Complex task escalated to full consensus: {triage_consensus.complexity_votes}"
            )

            # Get planner
            planner = await self._get_planner()

            # Create orchestration request
            orchestration_request = Request(request.task_description)

            # Use existing session ID format for complex tasks
            session_id = planner.create_session(request.task_description)

            # Assess complexity
            complexity = planner.assess(orchestration_request)

            # Get role recommendations
            roles = planner.select_roles(orchestration_request, complexity)

            # Run evaluation
            evaluations = await planner.evaluate_request(request.task_description)

            # Build consensus - now returns tuple (formatted_output, consensus_data)
            consensus_output, consensus_data = planner.build_consensus(
                evaluations, request.task_description
            )

            # Use consensus complexity instead of separate assessment
            complexity_level = ComplexityLevel(consensus_data["complexity"])

            # Create agent recommendations from consensus
            agent_recommendations = []
            domains = consensus_data["domains"]

            # Use consensus role recommendations
            for i, (role, score) in enumerate(
                consensus_data["role_recommendations"][: consensus_data["agent_count"]]
            ):
                # Rotate through top domains for variety
                domain = (
                    domains[i % len(domains)] if domains else "software-architecture"
                )

                agent_recommendations.append(
                    AgentRecommendation(
                        role=role,
                        domain=domain,
                        priority=score,
                        reasoning=f"Consensus-selected {role} for {complexity_level} complexity task (score: {score:.2f})",
                    )
                )

            # Create phases based on complexity
            phases = []
            if complexity_level in [ComplexityLevel.SIMPLE, ComplexityLevel.MEDIUM]:
                # Single execution phase
                phases.append(
                    TaskPhase(
                        name="execution_phase",
                        description="Execute the task with coordinated agents",
                        agents=agent_recommendations,
                        quality_gate=(
                            QualityGate.BASIC
                            if complexity_level == ComplexityLevel.SIMPLE
                            else QualityGate.THOROUGH
                        ),
                        coordination_pattern=WorkflowPattern.PARALLEL,
                    )
                )
            else:
                # Multi-phase execution
                phases.extend(
                    [
                        TaskPhase(
                            name="discovery_phase",
                            description="Research and analyze requirements",
                            agents=[
                                a
                                for a in agent_recommendations
                                if a.role in ["researcher", "analyst"]
                            ][:3],
                            quality_gate=QualityGate.THOROUGH,
                            coordination_pattern=WorkflowPattern.PARALLEL,
                        ),
                        TaskPhase(
                            name="design_phase",
                            description="Design architecture and approach",
                            agents=[
                                a
                                for a in agent_recommendations
                                if a.role in ["architect", "strategist"]
                            ][:2],
                            dependencies=["discovery_phase"],
                            quality_gate=QualityGate.THOROUGH,
                            coordination_pattern=WorkflowPattern.SEQUENTIAL,
                        ),
                        TaskPhase(
                            name="implementation_phase",
                            description="Implement the solution",
                            agents=[
                                a
                                for a in agent_recommendations
                                if a.role in ["implementer", "innovator"]
                            ][:3],
                            dependencies=["design_phase"],
                            quality_gate=QualityGate.THOROUGH,
                            coordination_pattern=WorkflowPattern.PARALLEL,
                        ),
                        TaskPhase(
                            name="validation_phase",
                            description="Validate and test the solution",
                            agents=[
                                a
                                for a in agent_recommendations
                                if a.role in ["tester", "critic", "auditor"]
                            ][:2],
                            dependencies=["implementation_phase"],
                            quality_gate=(
                                QualityGate.CRITICAL
                                if complexity_level == ComplexityLevel.VERY_COMPLEX
                                else QualityGate.THOROUGH
                            ),
                            coordination_pattern=WorkflowPattern.PARALLEL,
                        ),
                    ]
                )

            # Extract spawn commands from consensus output
            spawn_commands = []
            if "khive compose" in consensus_output:
                lines = consensus_output.split("\n")
                spawn_commands.extend(
                    line.strip() for line in lines if "khive compose" in line
                )

            # Use confidence from consensus
            confidence = consensus_data["confidence"]

            # Track metrics for complex path
            self.metrics["total_llm_calls"] += 10  # 10 consensus agents
            self.metrics["total_cost"] += 0.0037  # Full consensus cost
            self.metrics["escalation_rate"] = (
                self.metrics["triage_complex"] / self.metrics["total_requests"]
            )

            return PlannerResponse(
                success=True,
                summary=consensus_output,  # Use the rich consensus output instead of simple summary
                complexity=complexity_level,
                recommended_agents=len(agent_recommendations),
                phases=phases,
                spawn_commands=spawn_commands,
                session_id=session_id,
                confidence=confidence,
            )

        except Exception as e:
            logger.error(f"Error in handle_request: {e}", exc_info=True)
            return PlannerResponse(
                success=False,
                summary=f"Planning failed: {e!s}",
                complexity=ComplexityLevel.MEDIUM,
                recommended_agents=0,
                confidence=0.0,
                error=str(e),
            )

    async def plan(self, request: PlannerRequest) -> PlannerResponse:
        """
        Plan a task (alias for handle_request).

        Args:
            request: The planning request

        Returns:
            Planning response
        """
        return await self.handle_request(request)

    async def execute_parallel_fanout(
        self,
        agent_specs: list[AgentRecommendation],
        session_id: str,
        timeout: float | None = None,
    ) -> dict[str, str]:
        """
        Execute parallel fan-out orchestration with dependency resolution.

        Args:
            agent_specs: List of agent specifications
            session_id: Session identifier
            timeout: Execution timeout in seconds

        Returns:
            Execution status report
        """
        try:
            # Get planner instance
            planner = await self._get_planner()

            # HandoffCoordinator removed - orchestrator handles execution
            # Returning empty status for now
            logger.info("execute_parallel_fanout deprecated - use orchestrator")
            return {"status": "deprecated", "message": "Use orchestrator for execution"}

        except Exception as e:
            logger.exception(f"Parallel fan-out execution failed: {e}")
            raise

    def get_metrics(self) -> dict:
        """Get current metrics for analysis."""
        return {
            **self.metrics,
            "avg_cost_per_request": self.metrics["total_cost"]
            / max(self.metrics["total_requests"], 1),
            "avg_llm_calls_per_request": self.metrics["total_llm_calls"]
            / max(self.metrics["total_requests"], 1),
        }

    async def close(self) -> None:
        """Clean up resources."""
        try:
            if self._planner is not None:
                # Clean up timeout manager
                await self._planner.cleanup()
                self._planner = None
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
