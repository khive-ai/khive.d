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
from khive.prompts.complexity_heuristics import assess_by_heuristics
from khive.prompts.phase_determination import determine_required_phases
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
        # Normalize whitespace: convert tabs/newlines to spaces, collapse multiple spaces
        normalized = " ".join(text.split())
        self.text = normalized.lower()  # For easier pattern matching
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

    def create_session(
        self, task_description: str, session_id: str | None = None
    ) -> str:
        """Create new session with artifact management structure"""
        if session_id is None:
            # Generate session ID with timestamp first for better ordering
            timestamp = TimePolicy.now_utc().strftime("%Y%m%d_%H%M%S")
            task_slug = "".join(
                c for c in task_description.lower()[:15] if c.isalnum() or c in "-_"
            )
            session_id = f"{timestamp}_{task_slug}"

        session_dir = self.workspace_dir / session_id
        session_dir.mkdir(exist_ok=True)

        # Create workspace subdirectories
        (session_dir / "scratchpad").mkdir(exist_ok=True)
        (session_dir / "deliverable").mkdir(exist_ok=True)

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
        # Delegate to the complexity heuristics module for cleaner separation of concerns
        return assess_by_heuristics(req.text)

    # TODO: Implement RoleSelector mechnanism
    def select_roles(self, req: Request, complexity: ComplexityTier) -> list[str]:
        """Select appropriate roles based on request and complexity.

        Returns a list that may contain duplicate roles for parallel work.
        E.g., [researcher, researcher, implementer, tester, implementer]

        Note: This is a simple heuristic used primarily for testing.
        Production uses the full LLM consensus system.
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

        # Ensure all roles are valid (but keep duplicates)
        final_roles = [r for r in selected_roles if r in self.available_roles]

        # Fallback to minimal set if no roles selected
        if not final_roles:
            final_roles = ["researcher", "implementer"]

        return final_roles

    def _determine_required_phases(self, req: Request) -> list[str]:
        """Determine which development phases are needed based on request content"""
        # Delegate to the phase determination module for cleaner separation of concerns
        return determine_required_phases(req.text)

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
                    logger.warning(f"Agent {config['name']} failed: {result['error']}")
                else:
                    evaluations.append(result)

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
        self,
        evaluations: list[dict],
        request: str = "",
        command_format: str = "claude",
        session_id: str | None = None,
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

        # Generate phase-aware execution commands based on format flag
        if command_format == "json":
            output.append("📋 Execution Commands (JSON Format for Orchestration):")
            output.append("```json")
        else:  # claude format (BatchTool)
            output.append("📋 Execution Commands (BatchTool Format for Claude Code):")
            output.append("```javascript")

        # Use actual top domains from consensus for the consensus data
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
        from khive.utils import KHIVE_CONFIG_DIR

        composer = AgentComposer(KHIVE_CONFIG_DIR / "prompts")

        # Use provided session ID or create new one if not provided
        if not session_id:
            session_id = self.create_session(str(request))

        # NOTE: We don't generate commands here anymore - phases handle this
        # The command generation below is deprecated and will be removed

        # Collect agent specifications (allow duplicates for parallel work)
        agent_specs = []
        dependency_map = self._analyze_role_dependencies(
            sorted_roles[:15]
        )  # Get more for selection

        # Build agent list based on consensus with proportional distribution
        agent_specs = []
        target_count = int(avg_agents)

        # Calculate total score for normalization
        # Only consider roles with meaningful scores
        relevant_roles = [
            (role, score) for role, score in sorted_roles if score >= 0.05
        ]
        total_score = sum(score for _, score in relevant_roles)

        if total_score == 0:
            # Fallback if no scores
            total_score = 1

        # Calculate how many agents each role should get based on their weight
        role_allocations = []
        for role, score in relevant_roles:
            weight = score / total_score
            # Allocate agents proportionally, with minimum of 1 if role is selected
            agent_count_for_role = max(1, round(weight * target_count))
            # Cap at 3 instances of same role per phase
            agent_count_for_role = min(agent_count_for_role, 3)
            role_allocations.append((role, score, agent_count_for_role))

        # Sort by score to prioritize higher-scoring roles
        role_allocations.sort(key=lambda x: x[1], reverse=True)

        # Build the agent list
        agent_count = 0
        domain_index = 0

        for role, score, allocated_count in role_allocations:
            if agent_count >= target_count:
                break

            # Create the allocated number of agents for this role
            for instance in range(allocated_count):
                if agent_count >= target_count:
                    break

                # Rotate through domains for variety
                raw_domain = domain_list[domain_index % len(domain_list)]
                canonical_domain = composer.canonicalize_domain(raw_domain)
                domain_index += 1

                # Adjust priority slightly for duplicate instances
                adjusted_priority = score * (0.95**instance)

                reasoning = (
                    f"{'Parallel instance ' + str(instance + 1) + ' of ' if instance > 0 else ''}"
                    f"{role} for {consensus_complexity} complexity task "
                    f"(score: {score:.2f}, weight: {score / total_score:.1%})"
                )

                agent_spec = AgentRecommendation(
                    role=role,
                    domain=canonical_domain,
                    priority=adjusted_priority,
                    reasoning=reasoning,
                )
                agent_specs.append(agent_spec)
                agent_count += 1

        # If we still need more agents, fill with next best roles
        if agent_count < target_count:
            for role, score in sorted_roles:
                if agent_count >= target_count:
                    break

                # Skip if we already have 3 of this role
                existing_count = sum(1 for spec in agent_specs if spec.role == role)
                if existing_count >= 3:
                    continue

                # Skip very low scores
                if score < 0.05:
                    continue

                raw_domain = domain_list[domain_index % len(domain_list)]
                canonical_domain = composer.canonicalize_domain(raw_domain)
                domain_index += 1

                agent_spec = AgentRecommendation(
                    role=role,
                    domain=canonical_domain,
                    priority=score,
                    reasoning=f"Additional {role} to meet target count (score: {score:.2f})",
                )
                agent_specs.append(agent_spec)
                agent_count += 1

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

        # Generate commands based on chosen format
        if command_format == "json":
            # JSON format for orchestration - just provide the consensus data
            # The orchestrator will determine analysis_type based on its own logic

            consensus_json = {
                "session_id": session_id,
                "complexity": consensus_complexity_str,
                "confidence": f"{avg_confidence:.0%}",
                "workflow_pattern": consensus_pattern,
                "quality_level": consensus_quality,
                "request": request,
                "agents": [],
            }

            # Add agent specifications
            for agent_spec in handoff_agent_specs:
                agent_data = {
                    "role": agent_spec.role,
                    "domain": agent_spec.domain,
                    "priority": agent_spec.priority,
                    "phase": agent_spec.phase,
                    "dependencies": agent_spec.dependencies,
                    "spawn_command": agent_spec.spawn_command,
                    "context": agent_spec.context,
                    "artifact_path": self.generate_artifact_path(
                        session_id, agent_spec.phase, agent_spec.role, agent_spec.domain
                    ),
                }
                consensus_json["agents"].append(agent_data)

            # Output the consensus data as JSON
            output.append(json.dumps(consensus_json, indent=2))

        else:  # claude format (BatchTool)
            # Detect phases for the task
            from khive.prompts.phase_determination import (
                determine_required_phases,
                get_phase_description,
            )

            detected_phases = determine_required_phases(request)

            # If we have multiple phases, organize agents by phase
            if len(detected_phases) > 1:
                # Group agents by phase based on their roles
                phase_agent_groups = self._group_agents_by_phase(
                    handoff_agent_specs, detected_phases
                )

                # Generate commands organized by phase
                for phase_idx, phase_name in enumerate(detected_phases, 1):
                    phase_agents = phase_agent_groups.get(phase_name, [])
                    if not phase_agents:
                        continue

                    output.append(
                        f"\n  // Phase {phase_idx}: {phase_name.replace('_phase', '').title()}"
                    )
                    output.append(f"  // {get_phase_description(phase_name)}")

                    for agent_spec in phase_agents:
                        agent_name = (
                            f"{agent_spec.role}_{agent_spec.domain.replace('-', '_')}"
                        )

                        # Update phase in spec
                        agent_spec.phase = f"phase{phase_idx}"

                        # Enhanced context for phase-aware execution
                        artifact_management = self.get_artifact_management_prompt(
                            session_id,
                            f"phase{phase_idx}",
                            agent_spec.role,
                            agent_spec.domain,
                        )

                        phase_context = f"""PHASE {phase_idx} EXECUTION CONTEXT:
- Phase: {phase_name.replace("_phase", "").title()}
- Priority: {agent_spec.priority:.2f}
- Coordinate through shared artifacts

ORIGINAL REQUEST: {request}
COMPLEXITY: {consensus_complexity_str} (confidence: {avg_confidence:.0%})

{artifact_management}

PHASE EXECUTION INSTRUCTIONS:
- You are part of Phase {phase_idx}: {phase_name.replace("_phase", "").title()}
- Check artifact registry for previous phase outputs
- Your work executes in parallel with other Phase {phase_idx} agents
- Coordinate through shared artifact registry
- Build upon previous phase deliverables if available

YOUR TASK:
1. Run: `uv run khive compose {agent_spec.role} -d {agent_spec.domain} -c "{request}"`
2. Focus on Phase {phase_idx} objectives: {get_phase_description(phase_name)}
3. Reference artifacts from earlier phases if applicable
4. Execute with phase-specific goals in mind

Remember: This is PHASE {phase_idx} - coordinate with phase peers!"""

                        # Escape prompt for JavaScript
                        escaped_prompt = phase_context.replace('"', '\\"').replace(
                            "\n", "\\n"
                        )
                        output.append(
                            f'  Task({{ description: "{agent_name}_phase{phase_idx}", prompt: "{escaped_prompt}" }})'
                        )

                output.append(
                    "\n  // Execute phases sequentially or in parallel based on dependencies"
                )
            else:
                # Single phase or no phases detected - use original parallel execution
                for agent_spec in handoff_agent_specs:
                    agent_name = (
                        f"{agent_spec.role}_{agent_spec.domain.replace('-', '_')}"
                    )

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
                    escaped_prompt = parallel_context.replace('"', '\\"').replace(
                        "\n", "\\n"
                    )
                    output.append(
                        f'  Task({{ description: "{agent_name}", prompt: "{escaped_prompt}" }})'
                    )

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
        deliverable_path = (
            session_dir / "deliverable" / f"{phase}_{agent_role}_{domain}.md"
        )
        session_dir / "artifact_registry.json"

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
- Check scratchpad/ and deliverable/ folders for previous work"""

        return f"""
🗂️ WORKSPACE STRUCTURE:
- **Session**: {session_id}
- **Structure**: workspace/{session_id}/
  - `scratchpad/` - Working documents shared among all agents
  - `deliverable/` - Final phase deliverables
  - `artifact_registry.json` - Auto-managed artifact tracking

📋 ARTIFACT CREATION PROTOCOL:

1. **WORKING DOCUMENTS** (for notes, research, interim findings):
   ```bash
   uv run khive new-doc --artifact "{{name}}" -s {session_id} --description "{{purpose}}"
   ```
   - Creates in: `workspace/{session_id}/scratchpad/`
   - Visible to ALL agents in this session
   - Use for: Research notes, API findings, design drafts

2. **PHASE DELIVERABLE** (your final output):
   ```bash
   uv run khive new-doc agent-deliverable {{identifier}} --phase {phase} --role {agent_role} --domain {domain} -s {session_id}
   ```
   - Creates in: `workspace/{session_id}/deliverable/`
   - Your MANDATORY deliverable: `{deliverable_path.name}`
   - Registered automatically in artifact registry

3. **COLLABORATION**:
   - Check `scratchpad/` for other agents' working documents
   - Reference findings from previous phases
   - Build upon existing work{expected_artifacts_msg}

⚠️ IMPORTANT RULES:
- **NEVER manually edit** artifact_registry.json
- **RESPECT PEERS**: Never modify other agents' documents
- **USE khive new-doc**: Ensures atomic updates and proper registration

🔗 DELIVERABLE REQUIREMENTS:
Your final deliverable MUST include:
- **Summary**: Executive summary of your work
- **Key Findings**: 3-5 bullet points of main discoveries
- **Dependencies**: Which artifacts you referenced
- **Details**: Your complete analysis/design/implementation
- **Next Steps**: Recommendations for subsequent phases

💡 TIP: Create multiple working artifacts in scratchpad/ as you research, then consolidate into your final deliverable!
"""

    def generate_artifact_path(
        self, session_id: str, phase: str, agent_role: str, domain: str
    ) -> str:
        """Generate standardized artifact path for deliverables"""
        session_dir = self.workspace_dir / session_id
        filename = f"{phase}_{agent_role}_{domain}.md"
        return str(session_dir / "deliverable" / filename)

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

        # Get agent counts and complexity consensus
        all_evals = [e["evaluation"] for e in evaluations]
        agent_counts = [e.total_agents for e in all_evals]
        max_agents = max(agent_counts)
        avg_agents = sum(agent_counts) / len(agent_counts)

        # Get complexity consensus
        complexity_votes = {}
        for e in all_evals:
            comp = e.complexity
            complexity_votes[comp] = complexity_votes.get(comp, 0) + 1
        final_complexity = max(complexity_votes, key=complexity_votes.get)

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

        # Determine phases using our phase determination module
        from khive.prompts.phase_determination import (
            determine_required_phases,
            estimate_phase_complexity,
            get_phase_description,
        )

        detected_phases = determine_required_phases(request)

        # Show phase breakdown for:
        # 1. Tasks exceeding agent limits
        # 2. Complex or very_complex tasks
        # 3. Tasks with multiple phases detected
        # 4. Tasks with scope indicators
        show_phases = (
            max_agents > 12
            or avg_agents > 10
            or triggered_indicators
            or final_complexity in ["complex", "very_complex"]
            or len(detected_phases) > 2
        )

        if show_phases:
            output = []

            # Show warnings if applicable
            if max_agents > 12 or avg_agents > 10 or triggered_indicators:
                output.append("⚠️ Task Scope Analysis")
                if max_agents > 12:
                    output.append(
                        f"Agent Count Warning: Max {max_agents} agents exceeds 12-agent limit"
                    )
                if triggered_indicators:
                    output.append(
                        f"Scope Indicators: {', '.join(triggered_indicators)}"
                    )
                output.append("")

            # Show detected phases
            output.append("📋 Detected Phases:")
            for i, phase in enumerate(detected_phases, 1):
                phase_desc = get_phase_description(phase)
                estimated_agents = estimate_phase_complexity(phase, final_complexity)
                phase_name = phase.replace("_phase", "").title()
                output.append(f"- Phase {i}: {phase_name} ({estimated_agents} agents)")
                output.append(f"  {phase_desc}")

            # Add phase execution tip if multiple phases
            if len(detected_phases) > 1:
                output.append("")
                output.append(
                    '💡 Tip: For large tasks, run each phase separately: `khive plan "Phase 1: [specific focus]"`'
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

    def _group_agents_by_phase(
        self, agent_specs: list, phases: list[str]
    ) -> dict[str, list]:
        """Group agents by their appropriate phases based on role types."""
        phase_groups = {phase: [] for phase in phases}

        # Role to phase mapping
        role_phase_map = {
            # Discovery phase roles
            "researcher": "discovery_phase",
            "analyst": "discovery_phase",
            "theorist": "discovery_phase",
            # Design phase roles
            "architect": "design_phase",
            "strategist": "design_phase",
            # Implementation phase roles
            "implementer": "implementation_phase",
            "innovator": "implementation_phase",
            # Validation phase roles
            "tester": "validation_phase",
            "critic": "validation_phase",
            "auditor": "validation_phase",
            # Refinement phase roles
            "reviewer": "refinement_phase",
            "commentator": "refinement_phase",
        }

        # Distribute agents to appropriate phases
        for agent_spec in agent_specs:
            assigned_phase = role_phase_map.get(agent_spec.role)

            # Only assign to phases that were detected
            if assigned_phase and assigned_phase in phases:
                phase_groups[assigned_phase].append(agent_spec)
            else:
                # If role doesn't have a specific phase or phase not detected,
                # assign to the first available phase
                if phases:
                    phase_groups[phases[0]].append(agent_spec)

        # Ensure each phase has at least one agent if we have agents
        if agent_specs:
            for phase in phases:
                if not phase_groups[phase] and agent_specs:
                    # Take an agent from the phase with the most agents
                    max_phase = max(
                        phase_groups.keys(), key=lambda p: len(phase_groups[p])
                    )
                    if phase_groups[max_phase]:
                        phase_groups[phase].append(phase_groups[max_phase].pop())

        return phase_groups

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
        """Build a simple response from triage consensus with proper commands."""
        agent_recommendations = []
        spawn_commands = []

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

        # Check for explicit phases even in simple tasks
        detected_phases = self._detect_explicit_phases(request.task_description)

        if detected_phases:
            # Even "simple" tasks can have explicit phases
            phases = self._create_phases_from_detection(
                detected_phases, agent_recommendations
            )
            spawn_commands = self._generate_batched_spawn_commands(
                phases, request.task_description, session_id
            )
        else:
            # Single phase for truly simple tasks
            phase = TaskPhase(
                name="execution_phase",
                description="Execute the simple task",
                agents=agent_recommendations,
                quality_gate=QualityGate.BASIC,
                coordination_pattern=WorkflowPattern.PARALLEL,
            )
            phases = [phase]
            spawn_commands = self._generate_batched_spawn_commands(
                phases, request.task_description, session_id
            )

        # Generate rich summary like the complex consensus path
        if detected_phases:
            # For explicit phases, create detailed summary with BatchTool commands
            phase_summary = f"📋 Execution Phases ({len(phases)}):\n\n"
            for i, phase in enumerate(phases, 1):
                phase_summary += f"{i}. {phase.name.replace('_', ' ').title()}\n"
                phase_summary += f"   Description: {phase.description}\n"
                phase_summary += f"   Agents: {len(phase.agents)}\n"
                phase_summary += f"   Quality Gate: {phase.quality_gate}\n"
                phase_summary += f"   Pattern: {phase.coordination_pattern}\n"
                if phase.dependencies:
                    phase_summary += (
                        f"   Dependencies: {', '.join(phase.dependencies)}\n"
                    )
                phase_summary += "   Agent Details:\n"
                for agent in phase.agents:
                    phase_summary += f"     • {agent.role} ({agent.domain}) - Priority: {agent.priority:.1f}\n"
                    phase_summary += f"       Reasoning: {agent.reasoning}\n"
                phase_summary += "\n"

            phase_summary += "🚀 Task Agent Commands (for Claude Code):\n"
            phase_summary += "=" * 60 + "\n\n"
            phase_summary += "\n".join(spawn_commands)
            phase_summary += "\n" + "=" * 60 + "\n\n"
            phase_summary += (
                "💡 Copy and execute these commands in Claude Code to spawn agents"
            )

            final_summary = f"🎯 {phase_summary}"
        else:
            # Simple single-phase task
            final_summary = (
                f"🎯 Triage consensus (3 LLMs): {triage_consensus.decision_votes}"
            )

        return PlannerResponse(
            success=True,
            summary=final_summary,
            complexity=ComplexityLevel.SIMPLE,
            recommended_agents=triage_consensus.final_agent_count or 2,
            phases=phases,
            spawn_commands=spawn_commands,
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

            # Get planner instance early to create session
            planner = await self._get_planner()

            # Create session ID and workspace with timestamp first for better ordering
            timestamp = TimePolicy.now_utc().strftime("%Y%m%d_%H%M%S")
            task_type = "complex" if should_escalate else "simple"
            task_slug = "".join(
                c
                for c in request.task_description.lower()[:15]
                if c.isalnum() or c in "-_"
            )
            session_id = f"{timestamp}_{task_type}_{task_slug}"

            # Create the actual session workspace
            planner.create_session(request.task_description, session_id)
            planner.current_session_id = session_id

            if not should_escalate:
                # Simple task - use triage consensus
                self.metrics["triage_simple"] += 1
                # Suppress verbose logging for clean CLI output
                # logger.info(
                #     f"Simple task handled by triage: {triage_consensus.final_agent_count} agents, "
                #     f"confidence: {triage_consensus.average_confidence:.2f}"
                # )

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
            # Suppress verbose logging for clean CLI output
            # logger.info(
            #     f"Complex task escalated to full consensus: {triage_consensus.decision_votes}"
            # )

            # Planner already created above

            # Create orchestration request
            Request(request.task_description)

            # Session already created above for both simple and complex tasks
            # Just use the existing session_id that was created
            # planner.current_session_id is already set

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

            # Create phases based on explicit phase detection or complexity
            phases = []
            # Extract task description properly
            task_description = (
                request.task_description
                if hasattr(request, "task_description")
                else str(request)
            )
            detected_phases = self._detect_explicit_phases(task_description)

            if detected_phases:
                # Task explicitly mentions phases - create sequential multi-phase workflow
                phases = self._create_phases_from_detection(
                    detected_phases, agent_recommendations
                )
            elif complexity_level in [ComplexityLevel.SIMPLE, ComplexityLevel.MEDIUM]:
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
            # Generate proper BatchTool commands grouped by phase
            spawn_commands = self._generate_batched_spawn_commands(
                phases, task_description, session_id
            )

            # Use confidence from consensus
            confidence = consensus_data["confidence"]

            # Use proper summary format based on whether we have explicit phases
            if detected_phases:
                # For explicit phases, create summary with our BatchTool commands
                phase_summary = f"📋 Execution Phases ({len(phases)}):\n\n"
                for i, phase in enumerate(phases, 1):
                    phase_summary += f"{i}. {phase.name.replace('_', ' ').title()}\n"
                    phase_summary += f"   Description: {phase.description}\n"
                    phase_summary += f"   Agents: {len(phase.agents)}\n"
                    phase_summary += f"   Quality Gate: {phase.quality_gate}\n"
                    phase_summary += f"   Pattern: {phase.coordination_pattern}\n"
                    if phase.dependencies:
                        phase_summary += (
                            f"   Dependencies: {', '.join(phase.dependencies)}\n"
                        )
                    phase_summary += "   Agent Details:\n"
                    for agent in phase.agents:
                        phase_summary += f"     • {agent.role} ({agent.domain}) - Priority: {agent.priority:.1f}\n"
                        phase_summary += f"       Reasoning: {agent.reasoning}\n"
                    phase_summary += "\n"

                phase_summary += "🚀 Task Agent Commands (for Claude Code):\n"
                phase_summary += "=" * 60 + "\n\n"
                phase_summary += "\n".join(spawn_commands)
                phase_summary += "\n" + "=" * 60 + "\n\n"
                phase_summary += (
                    "💡 Copy and execute these commands in Claude Code to spawn agents"
                )

                final_summary = phase_summary
            else:
                # For non-phase tasks, use consensus output
                final_summary = consensus_output

            # Track metrics for complex path
            self.metrics["total_llm_calls"] += 10  # 10 consensus agents
            self.metrics["total_cost"] += 0.0037  # Full consensus cost
            self.metrics["escalation_rate"] = (
                self.metrics["triage_complex"] / self.metrics["total_requests"]
            )

            return PlannerResponse(
                success=True,
                summary=final_summary,  # Use phase-grouped commands when available
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

    def _generate_batched_spawn_commands(
        self, phases: list[TaskPhase], request: str, session_id: str | None = None
    ) -> list[str]:
        """Generate BatchTool commands grouped by phase."""
        batched_commands = []

        for phase in phases:
            if not phase.agents:
                continue

            # Create BatchTool header for this phase
            phase_commands = [f"# Phase: {phase.name}"]
            phase_commands.append("[BatchTool]")

            # Generate Task commands for each agent in this phase
            for agent in phase.agents:
                agent_name = f"{agent.role}_{agent.domain.replace('-', '_')}"

                # Simplified prompt for now - will fix artifact management later
                full_prompt = f"""TASK: {request}

🗂️ WORKSPACE STRUCTURE:
- **Session**: {session_id or "SESSION_ID_PLACEHOLDER"}
- **Structure**: workspace/{session_id or "SESSION_ID_PLACEHOLDER"}/
  - `scratchpad/` - Working documents shared among all agents
  - `deliverable/` - Final phase deliverables
  - `artifact_registry.json` - Auto-managed artifact tracking

YOUR ROLE: {agent.role} ({agent.domain})
PRIORITY: {agent.priority:.2f}

INSTRUCTIONS:
1. First run: `uv run khive compose {agent.role} -d {agent.domain} -c "{request}"`
2. Create working documents in scratchpad/ as needed
3. Complete your assigned task
4. Create final deliverable using khive new-doc

Remember: This is a {phase.coordination_pattern} task - focus on direct execution."""

                # Escape prompt for proper formatting
                escaped_prompt = full_prompt.replace('"', '\\"').replace("\n", "\\n")

                # Add Task command
                phase_commands.append(f'Task("{agent_name}: {escaped_prompt}")')

            phase_commands.append("")  # Empty line after each batch
            batched_commands.extend(phase_commands)

        return batched_commands

    def _detect_explicit_phases(self, request: str) -> list[dict]:
        """Detect explicit phases mentioned in the request."""
        import re

        detected_phases = []

        # Pattern 1: "Phase X - Description"
        phase_patterns = [
            r"Phase\s+(\d+)\s*[-:]\s*([^,\n.]+)",
            r"Step\s+(\d+)\s*[-:]\s*([^,\n.]+)",
            r"(\d+)[\)\.]\s*([^,\n.]+)",
        ]

        for pattern in phase_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if (
                matches and len(matches) >= 2
            ):  # At least 2 phases to be considered multi-phase
                for num, description in matches:
                    detected_phases.append(
                        {
                            "number": int(num),
                            "description": description.strip(),
                            "raw_text": f"Phase {num} - {description.strip()}",
                        }
                    )
                break  # Use first successful pattern

        # Sort by phase number
        detected_phases.sort(key=lambda x: x["number"])

        return detected_phases

    def _create_phases_from_detection(
        self, detected_phases: list[dict], agent_recommendations: list
    ) -> list[TaskPhase]:
        """Create TaskPhase objects from detected phases."""
        phases = []

        for i, phase_info in enumerate(detected_phases):
            phase_name = f"phase_{phase_info['number']}"

            # Assign agents based on phase content and order
            phase_agents = self._assign_agents_to_phase(
                phase_info, agent_recommendations, i, len(detected_phases)
            )

            # Set dependencies (each phase depends on previous)
            dependencies = (
                [f"phase_{detected_phases[i - 1]['number']}"] if i > 0 else []
            )

            phase = TaskPhase(
                name=phase_name,
                description=phase_info["description"],
                agents=phase_agents,
                dependencies=dependencies,
                quality_gate=QualityGate.THOROUGH,
                coordination_pattern=WorkflowPattern.PARALLEL,  # Parallel within phase, sequential between phases
            )
            phases.append(phase)

        return phases

    def _assign_agents_to_phase(
        self,
        phase_info: dict,
        agent_recommendations: list,
        phase_index: int,
        total_phases: int,
    ) -> list:
        """Distribute LLM-recommended agents across phases based on phase characteristics."""

        # Respect the LLM's intelligent role/domain recommendations
        # Just distribute them appropriately across phases

        total_agents = len(agent_recommendations)

        # For single phase, use all agents (up to reasonable limit)
        if total_phases == 1:
            return agent_recommendations[: min(8, total_agents)]

        # Calculate base distribution and remainder
        base_agents_per_phase = total_agents // total_phases
        remainder = total_agents % total_phases

        # Determine agents for this specific phase
        # Earlier phases get +1 agent if there's remainder
        agents_for_this_phase = base_agents_per_phase + (
            1 if phase_index < remainder else 0
        )

        # Ensure at least 1 agent per phase, max 6 agents per phase
        agents_for_this_phase = max(1, min(6, agents_for_this_phase))

        # Calculate start and end indices for this phase
        # Account for earlier phases potentially having +1 agent
        start_idx = 0
        for i in range(phase_index):
            phase_agent_count = base_agents_per_phase + (1 if i < remainder else 0)
            start_idx += phase_agent_count

        end_idx = min(start_idx + agents_for_this_phase, total_agents)

        # Extract agents for this phase
        phase_agents = agent_recommendations[start_idx:end_idx]

        # Safety check - if somehow we have no agents, take at least one
        if not phase_agents and agent_recommendations:
            phase_agents = [agent_recommendations[phase_index % total_agents]]

        return phase_agents

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
