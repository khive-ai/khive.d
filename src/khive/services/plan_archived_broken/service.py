"""
Main planning service integrating lionagi orchestration.

This module provides the main entry point for the planning system,
coordinating between the orchestrator, consensus algorithms, and lionagi.
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml

from .models import (
    PlannerRequest,
    PlannerResponse,
    ComplexityLevel,
    TaskPhase,
    AgentRecommendation,
)
from .orchestrator import (
    OrchestrationEvaluator,
    AdaptivePlanner,
    ConsensusConfig,
)
from .cost_tracker import CostTracker

# Logging setup
try:
    from khive.utils import get_logger
    logger = get_logger("khive.services.plan")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("khive.services.plan")


class PlannerService:
    """
    Main planning service using lionagi for orchestration.
    
    This service coordinates the Decomposer-Strategist-Critic pipeline
    with consensus algorithms to generate robust orchestration plans.
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        consensus_config: Optional[ConsensusConfig] = None,
        parallel_evaluators: int = 5
    ):
        """
        Initialize the planner service.
        
        Args:
            provider: LLM provider (e.g., "nvidia_nim", "openai")
            model: Model name (e.g., "nvidia/nemotron", "gpt-4o")
            consensus_config: Configuration for consensus algorithms
            parallel_evaluators: Number of parallel evaluators for consensus
        """
        # Model configuration from environment or parameters
        self.provider = provider or os.getenv("KHIVE_PLANNER_PROVIDER", "openrouter")
        self.model_name = model or os.getenv("KHIVE_PLANNER_MODEL", "google/gemini-2.0-flash-001")
        self.parallel_evaluators = min(10, max(3, parallel_evaluators))
        
        # Initialize components
        self.consensus_config = consensus_config or ConsensusConfig()
        self.cost_tracker = CostTracker()
        self.planner = AdaptivePlanner(
            model_provider=self.provider,
            model_name=self.model_name,
            consensus_config=self.consensus_config,
            cost_tracker=self.cost_tracker,
        )
        
        # Resource paths and data
        self.prompts: Dict[str, str] = {}
        self.available_roles: List[str] = []
        self.available_domains: List[str] = []
        self._initialized = False
        self._init_lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the service and load resources."""
        if self._initialized:
            return
        
        async with self._init_lock:
            if self._initialized:
                return
            
            logger.info(f"Initializing Planner Service (Provider: {self.provider}, Model: {self.model_name})")
            
            # Load resources
            self._load_prompts()
            self._load_roles_and_domains()
            
            self._initialized = True
            logger.info("Planner Service initialized successfully")
    
    def _get_resource_base_path(self) -> Path:
        """Get the base path for resource files."""
        # Try KHIVE_CONFIG_DIR first
        config_dir = os.getenv("KHIVE_CONFIG_DIR")
        if config_dir:
            base_path = Path(config_dir) / "prompts"
            if base_path.exists():
                return base_path
        
        # Try relative to this file
        try:
            relative_path = Path(__file__).resolve().parent.parent.parent / "prompts"
            if relative_path.exists():
                return relative_path
        except NameError:
            pass
        
        # Fallback to current directory
        cwd_path = Path.cwd() / "prompts"
        if cwd_path.exists():
            return cwd_path
        
        # Default fallback
        logger.warning("Could not find prompts directory, using default location")
        default_path = Path.home() / ".khive" / "prompts"
        default_path.mkdir(parents=True, exist_ok=True)
        return default_path
    
    def _load_prompts(self):
        """Load system prompts for the pipeline stages."""
        base_path = self._get_resource_base_path()
        prompts_file = base_path / "planner_prompts.yaml"
        
        if prompts_file.exists():
            try:
                with open(prompts_file, 'r', encoding='utf-8') as f:
                    self.prompts = yaml.safe_load(f) or {}
                logger.info(f"Loaded prompts from {prompts_file}")
            except Exception as e:
                logger.error(f"Failed to load prompts: {e}")
                self.prompts = self._get_default_prompts()
        else:
            logger.warning(f"Prompts file not found at {prompts_file}, using defaults")
            self.prompts = self._get_default_prompts()
            
            # Write default prompts for future use
            try:
                prompts_file.parent.mkdir(parents=True, exist_ok=True)
                with open(prompts_file, 'w', encoding='utf-8') as f:
                    yaml.dump(self.prompts, f, default_flow_style=False)
                logger.info(f"Created default prompts file at {prompts_file}")
            except Exception as e:
                logger.warning(f"Could not write default prompts: {e}")
    
    def _get_default_prompts(self) -> Dict[str, str]:
        """Get default system prompts."""
        return {
            "DECOMPOSER_SYSTEM": """You are an expert task decomposer. Break down high-level objectives into 3-7 concrete phases with clear dependencies. Focus on actionable, measurable outcomes.""",
            
            "STRATEGIST_SYSTEM": """You are an orchestration strategist. Allocate the best Role+Domain agents per phase. Define coordination strategies and quality gates. Optimize for efficiency and robustness.""",
            
            "CRITIC_SYSTEM": """You are a critical plan analyst. Identify risks, bottlenecks, and improvements. Provide honest confidence assessment based on plan feasibility."""
        }
    
    def _load_roles_and_domains(self):
        """Load available roles and domains."""
        base_path = self._get_resource_base_path()
        
        # Load roles
        roles_path = base_path / "roles"
        if roles_path.exists():
            role_files = list(roles_path.glob("*.md")) + list(roles_path.glob("*.yaml"))
            self.available_roles = sorted(list(set(
                f.stem for f in role_files if f.stem != "README"
            )))
        
        if not self.available_roles:
            # Default roles
            self.available_roles = [
                "researcher", "analyst", "architect", "strategist",
                "implementer", "tester", "critic", "reviewer",
                "auditor", "innovator", "commentator"
            ]
            logger.info(f"Using default roles: {', '.join(self.available_roles)}")
        
        # Load domains
        domains_path = base_path / "domains"
        if domains_path.exists():
            domain_files = list(domains_path.rglob("*.yaml"))
            self.available_domains = sorted(list(set(
                f.stem for f in domain_files 
                if f.stem not in ["TAXONOMY", "README"]
            )))
        
        if not self.available_domains:
            # Default domains
            self.available_domains = [
                "software-architecture", "distributed-systems", "api-design",
                "security-engineering", "microservices-architecture",
                "frontend-development", "database-design", "cloud-infrastructure",
                "performance-optimization", "testing-strategies"
            ]
            logger.info(f"Using default domains (subset): {', '.join(self.available_domains[:5])}...")
    
    async def handle_request(self, request: PlannerRequest) -> PlannerResponse:
        """
        Handle a planning request.
        
        This is the main entry point for the planning service.
        """
        await self.initialize()
        
        # Validate request
        if isinstance(request, dict):
            request = PlannerRequest(**request)
        elif isinstance(request, str):
            request = PlannerRequest.model_validate_json(request)
        
        # Generate plan using the adaptive planner
        try:
            response = await self.planner.plan(
                request=request,
                num_evaluators=self.parallel_evaluators
            )
            
            # Track cost if available
            if self.cost_tracker.request_count > 0:
                usage_summary = self.cost_tracker.get_usage_summary()
                logger.info(f"Planning cost: ${usage_summary['total_cost']:.4f} ({usage_summary['request_count']} requests)")
            
            return response
            
        except NotImplementedError as e:
            # Lionagi implementation pending
            logger.error(f"Lionagi implementation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Planning failed: {e}", exc_info=True)
            return PlannerResponse(
                success=False,
                summary=f"Planning failed: {str(e)}",
                complexity=ComplexityLevel.MEDIUM,
                recommended_agents=0,
                phases=[],
                session_id=f"plan_{int(time.time())}",
                confidence=0.0,
                error=str(e)
            )
    
    async def plan(self, request: PlannerRequest) -> PlannerResponse:
        """Alias for handle_request for compatibility."""
        return await self.handle_request(request)
    
    def _create_fallback_response(self, request: PlannerRequest) -> PlannerResponse:
        """Create a simple fallback response when lionagi is not available."""
        session_id = f"plan_{int(time.time())}"
        
        # Simple heuristic planning
        phases = [
            TaskPhase(
                name="analysis_phase",
                description="Analyze requirements and constraints",
                agents=[
                    AgentRecommendation(
                        role="researcher",
                        domain="software-architecture",
                        priority=1.0,
                        reasoning="Research best practices and existing solutions"
                    ),
                    AgentRecommendation(
                        role="analyst",
                        domain="requirements",
                        priority=0.9,
                        reasoning="Extract and validate requirements"
                    )
                ],
                dependencies=[],
                quality_gate="thorough",
                coordination_strategy="fan_out_synthesize",
                expected_artifacts=["requirements.md", "analysis.md"]
            ),
            TaskPhase(
                name="implementation_phase",
                description="Implement the solution",
                agents=[
                    AgentRecommendation(
                        role="implementer",
                        domain="python",
                        priority=1.0,
                        reasoning="Implement core functionality"
                    )
                ],
                dependencies=["analysis_phase"],
                quality_gate="thorough",
                coordination_strategy="autonomous",
                expected_artifacts=["implementation.py", "tests.py"]
            )
        ]
        
        summary = self._generate_summary(request, phases, session_id)
        
        return PlannerResponse(
            success=True,
            summary=summary,
            complexity=ComplexityLevel.MEDIUM,
            recommended_agents=3,
            phases=phases,
            session_id=session_id,
            confidence=0.65,
            spawn_commands=[]
        )
    
    def _generate_summary(
        self, 
        request: PlannerRequest, 
        phases: List[TaskPhase],
        session_id: str
    ) -> str:
        """Generate a human-readable summary."""
        lines = []
        
        lines.append("🎯 Orchestration Plan (Fallback Mode)")
        lines.append("-" * 40)
        lines.append(f"📊 Task: {request.task_description[:100]}...")
        lines.append(f"🔗 Session: {session_id}")
        lines.append(f"📋 Phases: {len(phases)}")
        
        for i, phase in enumerate(phases, 1):
            lines.append(f"\n{i}. {phase.name}")
            lines.append(f"   Agents: {len(phase.agents)}")
            for agent in phase.agents:
                lines.append(f"   - {agent.role} ({agent.domain})")
        
        return "\n".join(lines)
    
    async def close(self):
        """Clean up resources."""
        # Placeholder for cleanup
        pass
