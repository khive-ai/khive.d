from __future__ import annotations

import asyncio
import json
import os
import time
from enum import Enum
from pathlib import Path
from typing import Protocol

import yaml
from khive.core import TimePolicy
from khive.prompts.complexity_heuristics import assess_by_heuristics
from khive.services.artifacts.handlers import (
    HandoffAgentSpec,
    TimeoutConfig,
    TimeoutManager,
    TimeoutType,
)
from khive.utils import get_logger
from openai import OpenAI

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
        from khive.utils import KHIVE_CONFIG_DIR

        # Get path to user's prompts directory
        agents_path = KHIVE_CONFIG_DIR / "prompts" / "roles"
        roles = []

        for agent_file in agents_path.glob("*.md"):
            if agent_file.name != "README.md":
                role_name = agent_file.stem
                roles.append(role_name)

        return sorted(roles)

    def _load_available_domains(self) -> list[str]:
        """Scan domains directory for available domains"""
        from khive.utils import KHIVE_CONFIG_DIR

        # Get path to user's prompts directory
        domains_path = KHIVE_CONFIG_DIR / "prompts" / "domains"
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
        from khive.utils import KHIVE_CONFIG_DIR

        # First try user-customizable location
        user_prompts_path = KHIVE_CONFIG_DIR / "prompts" / "agent_prompts.yaml"

        # Fallback to package defaults (shouldn't normally be needed)
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
        from khive.utils import KHIVE_CONFIG_DIR

        # First try user-customizable location
        user_matrix_path = KHIVE_CONFIG_DIR / "prompts" / "decision_matrix.yaml"

        # Fallback to package defaults (shouldn't normally be needed)
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
        # Generate session ID with timestamp first for better ordering
        timestamp = TimePolicy.now_utc().strftime("%Y%m%d_%H%M%S")
        task_slug = "".join(
            c for c in task_description.lower()[:15] if c.isalnum() or c in "-_"
        )
        session_id = f"{timestamp}_{task_slug}"

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

        return ComplexityTier(tier)

    def _tier_rank(self, tier: str) -> int:
        """Get numeric rank for complexity tier (for max() comparison)"""
        tier_ranks = {"simple": 1, "medium": 2, "complex": 3, "very_complex": 4}
        return tier_ranks.get(tier, 2)  # Default to medium

    def _assess_by_heuristics(self, req: Request) -> list[str]:
        """Assess complexity using heuristic patterns when direct indicators don't match"""
        return assess_by_heuristics(req.original)

    def select_roles(self, req: Request, complexity: ComplexityTier) -> list[str]:
        """Select appropriate roles based on request and complexity.

        Returns a list that may contain duplicate roles for parallel work.
        E.g., [researcher, researcher, implementer, tester, implementer]
        """
        role_rules = self.matrix.get("agent_role_selection", {})

        # Determine which phases are needed based on request content
        needed_phases = self._determine_required_phases(req)

        # Collect roles from required phases (allow duplicates for parallel work)
        selected_roles = []
        for phase in needed_phases:
            if phase in role_rules:
                phase_roles = role_rules[phase].get("roles", [])
                selected_roles.extend(phase_roles)  # Use extend, not update

        # Scale based on complexity - add more agents for complex tasks
        if complexity == ComplexityTier.SIMPLE:
            # Simple: 1-4 agents total
            if len(selected_roles) > 4:
                selected_roles = selected_roles[:4]
            elif len(selected_roles) < 2:
                selected_roles = ["researcher", "implementer"]

        elif complexity == ComplexityTier.MEDIUM:
            # Medium: 3-12 agents, potentially duplicate roles
            if len(selected_roles) < 3:
                selected_roles.extend(["researcher", "implementer", "analyst"])

        elif complexity == ComplexityTier.COMPLEX:
            # Complex: 5-12 agents, add duplicates for parallel work
            if len(selected_roles) < 5:
                selected_roles.extend([
                    "researcher",
                    "researcher",
                    "implementer",
                    "tester",
                    "reviewer",
                ])

        elif complexity == ComplexityTier.VERY_COMPLEX:
            # Very complex: 8-20 agents, multiple of each role for parallel work
            if len(selected_roles) < 8:
                # Add multiple agents of key roles
                selected_roles.extend([
                    "researcher",
                    "researcher",
                    "researcher",
                    "implementer",
                    "implementer",
                    "analyst",
                    "analyst",
                    "tester",
                    "critic",
                    "reviewer",
                ])

        # Ensure all roles are valid (but keep duplicates)
        final_roles = [r for r in selected_roles if r in self.available_roles]

        # Fallback to minimal set if no roles selected
        if not final_roles:
            final_roles = ["researcher", "implementer"]

        return final_roles

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
                processed_results.append({
                    "agent_id": agent_id,
                    "status": "error",
                    "duration": None,
                    "retry_count": 0,
                    "error": str(result),
                    "execution_time": None,
                })
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
        from khive.utils import KHIVE_CONFIG_DIR

        # Get path to user's prompts directory
        dp = KHIVE_CONFIG_DIR / "prompts" / "decision_matrix.yaml"
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

            configs.append({
                "name": agent_config.get("name", agent_name),
                "system_prompt": system_prompt,
                # "temperature": agent_config.get("temperature", 0.3),
                "description": agent_config.get("description", ""),
            })

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
        self,
        evaluations: list[dict],
        request: str = "",
        command_format: str = "claude",
        session_id: str = None,
    ) -> tuple[str, dict]:
        """Build consensus from multiple evaluations

        Args:
            evaluations: List of evaluation dictionaries
            request: The original request text
            command_format: Either "claude" for BatchTool format or "json" for orchestration format
            session_id: Session ID for artifact management (created once per orchestration)

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

        # NOTE: Command generation moved to handle_request after phases are created
        # This ensures commands use actual phase information instead of hardcoded "phase1"

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

        # Determine expected artifacts based on phase
        phase_dependencies = {
            "phase1": [],
            "discovery_phase": [],
            "design_phase": ["discovery_phase"],
            "implementation_phase": ["discovery_phase", "design_phase"],
            "validation_phase": [
                "discovery_phase",
                "design_phase",
                "implementation_phase",
            ],
            "refinement_phase": [
                "discovery_phase",
                "design_phase",
                "implementation_phase",
                "validation_phase",
            ],
            "execution_phase": [],  # Single phase execution
        }

        expected_phases = phase_dependencies.get(phase, [])
        expected_artifacts_msg = ""

        if expected_phases:
            expected_artifacts_msg = f"""

📚 EXPECTED ARTIFACTS FROM PREVIOUS PHASES:
- {", ".join(expected_phases)} should be complete
- Check registry for specific deliverables from these phases"""

        return f"""
🗂️ ARTIFACT MANAGEMENT (MANDATORY DELIVERABLE):
1. **Session ID**: {session_id}
2. **YOUR MANDATORY DELIVERABLE**: `{artifact_path}`
3. **Registry**: Automatically managed when you use khive new-doc
4. **Current Phase**: {phase}{expected_artifacts_msg}

📋 DELIVERABLE CREATION PROTOCOL:
1. **CREATE**: Use `uv run khive new-doc agent-deliverable {session_id} --phase {phase} --role {agent_role} --domain {domain}`
   - This creates your deliverable template AND registers it safely
   - No registry conflicts - handled atomically by new-doc
2. **FILL**: Read the created template and complete all sections
3. **REFERENCE**: Check `{registry_path}` for previous phase artifacts to build upon

⚠️ REGISTRY SAFETY:
- **NEVER manually edit** registry.json - let khive new-doc handle it
- **RESPECT PEERS**: Never modify other agents' deliverables
- **ATOMIC UPDATES**: khive new-doc ensures safe concurrent registry updates

🔗 DELIVERABLE REQUIREMENTS:
Your MD file MUST include:
- **Summary**: Executive summary of your work
- **Key Findings**: 3-5 bullet points of main discoveries
- **Dependencies**: Which previous artifacts you built upon
- **Details**: Your analysis, design, or implementation
- **Next Steps**: Recommendations for subsequent phases

⚠️ CRITICAL: Use `khive new-doc` to create your deliverable - it handles both file creation AND registry update!
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

    def __init__(self, command_format: str = "claude"):
        """Initialize the planner service.

        Args:
            command_format: Either "claude" for BatchTool format or "json" for OrchestrationPlan format
        """
        self._planner = None
        self._planner_lock = asyncio.Lock()
        self._triage_service = None
        self._triage_lock = asyncio.Lock()
        self.command_format = command_format

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
            # Store session ID for consistent use across all phases
            planner.current_session_id = session_id

            # Run evaluation - let LLMs determine complexity and roles
            evaluations = await planner.evaluate_request(request.task_description)

            # Build consensus - now returns tuple (formatted_output, consensus_data)
            consensus_output, consensus_data = planner.build_consensus(
                evaluations, request.task_description, self.command_format, session_id
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
                # Multi-phase execution - distribute agents properly across phases
                discovery_agents = [
                    a
                    for a in agent_recommendations
                    if a.role in ["researcher", "analyst"]
                ]
                design_agents = [
                    a
                    for a in agent_recommendations
                    if a.role in ["architect", "strategist"]
                ]
                implementation_agents = [
                    a
                    for a in agent_recommendations
                    if a.role in ["implementer", "innovator"]
                ]
                validation_agents = [
                    a
                    for a in agent_recommendations
                    if a.role in ["tester", "critic", "auditor"]
                ]

                # Fallback: if no agents match phase requirements, distribute evenly
                if not any([
                    discovery_agents,
                    design_agents,
                    implementation_agents,
                    validation_agents,
                ]):
                    # Distribute all agents evenly across phases
                    total_agents = len(agent_recommendations)
                    agents_per_phase = max(1, total_agents // 4)

                    discovery_agents = agent_recommendations[:agents_per_phase]
                    design_agents = agent_recommendations[
                        agents_per_phase : agents_per_phase * 2
                    ]
                    implementation_agents = agent_recommendations[
                        agents_per_phase * 2 : agents_per_phase * 3
                    ]
                    validation_agents = agent_recommendations[agents_per_phase * 3 :]

                phases.extend([
                    TaskPhase(
                        name="discovery_phase",
                        description="Research and analyze requirements",
                        agents=discovery_agents,  # Use all matching agents, no limit
                        quality_gate=QualityGate.THOROUGH,
                        coordination_pattern=WorkflowPattern.PARALLEL,
                    ),
                    TaskPhase(
                        name="design_phase",
                        description="Design architecture and approach",
                        agents=design_agents,  # Use all matching agents, no limit
                        dependencies=["discovery_phase"],
                        quality_gate=QualityGate.THOROUGH,
                        coordination_pattern=WorkflowPattern.SEQUENTIAL,
                    ),
                    TaskPhase(
                        name="implementation_phase",
                        description="Implement the solution",
                        agents=implementation_agents,  # Use all matching agents, no limit
                        dependencies=["design_phase"],
                        quality_gate=QualityGate.THOROUGH,
                        coordination_pattern=WorkflowPattern.PARALLEL,
                    ),
                    TaskPhase(
                        name="validation_phase",
                        description="Validate and test the solution",
                        agents=validation_agents,  # Use all matching agents, no limit
                        dependencies=["implementation_phase"],
                        quality_gate=(
                            QualityGate.CRITICAL
                            if complexity_level == ComplexityLevel.VERY_COMPLEX
                            else QualityGate.THOROUGH
                        ),
                        coordination_pattern=WorkflowPattern.PARALLEL,
                    ),
                ])

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

            # Generate phase-aware commands
            command_output = []

            if self.command_format == "claude":
                # BatchTool format with [BatchTool] wrappers
                command_output.append(
                    "\n📋 Execution Commands (Phase-Aware BatchTool Format):"
                )
                command_output.append("```javascript")

                for phase in phases:
                    if phase.agents:
                        command_output.append(
                            f"  // Phase: {phase.name} ({phase.description})"
                        )

                        # Create [BatchTool] wrapper for each phase
                        phase_tasks = []
                        for agent in phase.agents:
                            agent_name = (
                                f"{agent.role}_{agent.domain.replace('-', '_')}"
                            )

                            # Get planner for artifact management
                            planner = await self._get_planner()
                            artifact_management = (
                                planner.get_artifact_management_prompt(
                                    session_id, phase.name, agent.role, agent.domain
                                )
                            )

                            # Handle enum values safely
                            quality_gate_str = (
                                phase.quality_gate.value
                                if hasattr(phase.quality_gate, "value")
                                else str(phase.quality_gate)
                            )
                            coordination_pattern_str = (
                                phase.coordination_pattern.value
                                if hasattr(phase.coordination_pattern, "value")
                                else str(phase.coordination_pattern)
                            )
                            complexity_str = (
                                complexity_level.value
                                if hasattr(complexity_level, "value")
                                else str(complexity_level)
                            )

                            phase_context = f"""PHASE-AWARE EXECUTION CONTEXT:
- Phase: {phase.name} ({phase.description})
- Quality Gate: {quality_gate_str}
- Coordination: {coordination_pattern_str}
- Dependencies: {", ".join(phase.dependencies) if phase.dependencies else "None"}
- Priority: {agent.priority:.2f}

ORIGINAL REQUEST: {request.task_description}
COMPLEXITY: {complexity_str} (confidence: {confidence:.0%})

{artifact_management}

PHASE-SPECIFIC INSTRUCTIONS:
- This is {phase.name} - focus on: {phase.description}
- Quality gate: {quality_gate_str}
- Wait for dependencies: {", ".join(phase.dependencies) if phase.dependencies else "None"}
- Coordinate via: {coordination_pattern_str} pattern

YOUR TASK:
1. Run: `uv run khive compose {agent.role} -d {agent.domain} -c "{request.task_description}"`
2. Focus on {phase.name} deliverables
3. Respect phase dependencies and coordination pattern
4. Create your deliverable following phase requirements

Remember: This is {phase.name.upper()} - follow the phase-specific requirements!"""

                            # Escape for JavaScript
                            escaped_prompt = phase_context.replace('"', '\\"').replace(
                                "\n", "\\n"
                            )
                            phase_tasks.append(
                                f'    Task({{ description: "{agent_name}_{phase.name}", prompt: "{escaped_prompt}" }})'
                            )

                        # Wrap phase tasks in [BatchTool]
                        if phase_tasks:
                            command_output.append("  [BatchTool]([")
                            command_output.extend(phase_tasks)
                            command_output.append("  ])")
                            command_output.append("")  # Empty line between phases

                command_output.append("```")

            elif self.command_format == "json":
                # JSON format for orchestration
                command_output.append("\n📋 Execution Commands (JSON Format):")
                command_output.append("```json")

                json_structure = {
                    "session_id": session_id,
                    "complexity": (
                        complexity_level.value
                        if hasattr(complexity_level, "value")
                        else str(complexity_level)
                    ),
                    "confidence": f"{confidence:.0%}",
                    "total_agents": len(agent_recommendations),
                    "phases": [],
                }

                for phase in phases:
                    if phase.agents:
                        phase_json = {
                            "name": phase.name,
                            "description": phase.description,
                            "quality_gate": (
                                phase.quality_gate.value
                                if hasattr(phase.quality_gate, "value")
                                else str(phase.quality_gate)
                            ),
                            "coordination_pattern": (
                                phase.coordination_pattern.value
                                if hasattr(phase.coordination_pattern, "value")
                                else str(phase.coordination_pattern)
                            ),
                            "dependencies": (
                                phase.dependencies
                                if hasattr(phase, "dependencies") and phase.dependencies
                                else []
                            ),
                            "agents": [],
                        }

                        for agent in phase.agents:
                            agent_json = {
                                "role": agent.role,
                                "domain": agent.domain,
                                "priority": agent.priority,
                                "reasoning": agent.reasoning,
                                "spawn_command": f'uv run khive compose {agent.role} -d {agent.domain} -c "{request.task_description}"',
                                "artifact_path": f".khive/workspace/{session_id}/{phase.name}_{agent.role}_{agent.domain}.md",
                            }
                            phase_json["agents"].append(agent_json)

                        json_structure["phases"].append(phase_json)

                import json

                command_output.append(json.dumps(json_structure, indent=2))
                command_output.append("```")

            # Append commands to consensus output
            consensus_output += "\n".join(command_output)

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
