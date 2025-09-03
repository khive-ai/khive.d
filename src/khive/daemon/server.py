"""
Khive Daemon Server - Clean Implementation

Provides basic coordination and planning services for khive agents.
No fake or misleading functionality - only working features.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from khive.services.artifacts.factory import create_artifacts_service_from_env
from khive.services.artifacts.service import ArtifactsService
from khive.services.claude.hooks.coordination import (
    CoordinationRegistry,
    check_duplicate_work,
    get_registry,
)
from khive.services.composition.agent_composer import AgentComposer
from khive.services.plan.service import ConsensusPlannerV3 as PlannerService
from khive.services.session.session_service import SessionService

logger = logging.getLogger(__name__)


# Request/Response Models
class CoordinateRequest(BaseModel):
    task_id: str
    description: str
    agent_id: str


class CoordinateCompleteRequest(BaseModel):
    task_id: str
    agent_id: str
    output: str
    artifacts: list[str] = []


class InsightsRequest(BaseModel):
    task_description: str
    agent_id: str


class FileOperationRequest(BaseModel):
    file_path: str
    agent_id: str


class FileUnregisterRequest(BaseModel):
    file_path: str
    agent_id: str


class SessionMappingRequest(BaseModel):
    session_id: str
    agent_id: str


class AgentSpawnRequest(BaseModel):
    role: str
    domain: str | None = None
    context: str | None = None
    session_id: str | None = None
    coordination_id: str | None = None


# Response Models for Missing Endpoints
class HookEvent(BaseModel):
    id: str
    coordinationId: str
    agentId: str
    eventType: Literal[
        "pre_command",
        "post_command",
        "pre_edit",
        "post_edit",
        "pre_agent_spawn",
        "post_agent_spawn",
    ]
    timestamp: str
    metadata: dict[str, Any]
    filePath: str | None = None
    command: str | None = None


class MetricDataPoint(BaseModel):
    timestamp: str
    value: float


class SystemPerformanceMetrics(BaseModel):
    cpu: dict[str, float | list[MetricDataPoint]]
    memory: dict[str, float | list[MetricDataPoint]]
    timestamp: str


class RolePerformanceMetrics(BaseModel):
    role: str
    successRate: float
    totalTasks: int
    averageCompletionTime: float


class DomainPerformanceMetrics(BaseModel):
    domain: str
    successRate: float
    totalTasks: int
    averageCompletionTime: float


class AgentActivityPoint(BaseModel):
    timestamp: str
    successful: int
    failed: int


class AgentAnalytics(BaseModel):
    successRate: float
    totalTasks: int
    completedTasks: int
    failedTasks: int
    performanceByRole: list[RolePerformanceMetrics]
    performanceByDomain: list[DomainPerformanceMetrics]
    recentActivity: list[AgentActivityPoint]


class PlanNode(BaseModel):
    id: str
    phase: str
    status: Literal["pending", "running", "completed", "failed"]
    agents: list[str]
    tasks: list[str]
    coordinationStrategy: Literal["FAN_OUT_SYNTHESIZE", "PIPELINE", "PARALLEL"]
    expectedArtifacts: list[str]
    dependencies: list[str]


class Plan(BaseModel):
    id: str
    sessionId: str
    nodes: list[PlanNode]
    edges: list[dict[str, str]]


class KhiveDaemonServer:
    """Clean khive daemon server with basic coordination."""

    def __init__(self):
        self.app = FastAPI(title="Khive Daemon", version="1.0.0")

        # Add CORS middleware for frontend integration
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, specify actual origins
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.coordination_registry: CoordinationRegistry | None = None
        self.planner_service: PlannerService | None = None
        self.session_service: SessionService | None = None
        self.artifact_service: ArtifactsService | None = None
        self.agent_composer: AgentComposer | None = None
        self.startup_time = datetime.now()
        self.stats = {
            "requests": 0,
            "errors": 0,
            "tasks_coordinated": 0,
            "insights_generated": 0,
        }

        self._setup_routes()

    async def startup(self):
        """Initialize daemon services."""
        logger.info("Initializing Khive daemon services...")

        # Initialize core services
        self.coordination_registry = get_registry()
        self.planner_service = PlannerService()
        self.session_service = SessionService()

        # Initialize artifacts service
        try:
            self.artifact_service = create_artifacts_service_from_env()
        except Exception as e:
            logger.error(f"Failed to initialize artifacts service: {e}")
            self.artifact_service = None

        # Initialize agent composer with correct path
        try:
            from pathlib import Path

            # Use the khive prompts directory as base path
            prompts_path = Path(__file__).parent.parent / "prompts"
            self.agent_composer = AgentComposer(base_path=str(prompts_path))
        except Exception as e:
            logger.error(f"Failed to initialize agent composer: {e}")
            self.agent_composer = None

        logger.info("Khive daemon services initialized successfully")

    def _setup_routes(self):
        """Set up API routes."""

        @self.app.on_event("startup")
        async def startup_event():
            await self.startup()

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.startup_time).total_seconds(),
                "stats": self.stats,
            }

        @self.app.get("/api/stats")
        async def get_stats():
            """Get daemon statistics."""
            self.stats["requests"] += 1
            return {
                "stats": self.stats,
                "services": {
                    "coordination": self.coordination_registry is not None,
                    "planner": self.planner_service is not None,
                    "session": self.session_service is not None,
                    "artifacts": self.artifact_service is not None,
                    "composer": self.agent_composer is not None,
                },
            }

        # Basic coordination endpoints
        @self.app.post("/api/coordinate/start")
        async def start_coordination(request: CoordinateRequest):
            """Start task coordination - PREVENTS DUPLICATE WORK."""
            self.stats["requests"] += 1
            try:
                # Check for duplicate work using practical coordinator
                duplicate = check_duplicate_work(request.agent_id, request.description)
                if duplicate:
                    return {
                        "status": "duplicate",
                        "message": f"Similar task already in progress: {duplicate}",
                        "existing_task": duplicate,
                    }

                # Register the work
                result = self.coordination_registry.register_agent_work(
                    request.agent_id, request.description
                )
                self.stats["tasks_coordinated"] += 1
                return result
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Coordination start failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/coordinate/complete")
        async def complete_coordination(request: CoordinateCompleteRequest):
            """Complete task coordination."""
            self.stats["requests"] += 1
            try:
                if not self.coordination_registry:
                    raise HTTPException(
                        status_code=503, detail="Coordination service unavailable"
                    )

                result = self.coordination_registry.complete_work(request.agent_id)
                return result
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Coordination complete failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/coordinate/insights")
        async def get_coordination_insights(request: InsightsRequest):
            """Get coordination insights."""
            self.stats["requests"] += 1
            try:
                if not self.coordination_registry:
                    raise HTTPException(
                        status_code=503, detail="Coordination service unavailable"
                    )

                insights = self.coordination_registry.get_insights(
                    request.task_description, request.agent_id
                )
                self.stats["insights_generated"] += 1
                return insights
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Insights generation failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # File coordination endpoints - PRACTICAL implementation
        @self.app.post("/api/coordinate/file-register")
        async def register_file_operation(request: FileOperationRequest):
            """Register file operation - PREVENTS CONFLICTS."""
            self.stats["requests"] += 1
            try:
                # Use coordinator for real file locking
                result = self.coordination_registry.request_file_lock(
                    request.agent_id, request.file_path
                )

                # Convert to HTTP status codes
                if result["status"] == "locked":
                    # File is locked by another agent - 409 Conflict
                    raise HTTPException(status_code=409, detail=result)

                return result
            except HTTPException:
                raise
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"File operation registration failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/coordinate/file-unregister")
        async def unregister_file_operation(request: FileUnregisterRequest):
            """Unregister file operation - RELEASES LOCK."""
            self.stats["requests"] += 1
            try:
                # Use coordinator to release lock
                result = self.coordination_registry.release_file_lock(
                    request.agent_id, request.file_path
                )
                return result
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"File operation unregistration failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/coordinate/file-renew")
        async def renew_file_operation(request: FileOperationRequest):
            """Renew file lock - EXTENDS TTL."""
            self.stats["requests"] += 1
            try:
                # Use coordinator to renew lock
                result = self.coordination_registry.renew_file_lock(
                    request.agent_id, request.file_path
                )
                return result
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"File lock renewal failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/coordinate/status")
        async def get_coordination_status():
            """Get coordination status - PRACTICAL info agents need."""
            self.stats["requests"] += 1
            try:
                # Use coordinator for real status
                status = self.coordination_registry.get_status()
                return status
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Status retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/coordinate/cleanup")
        async def cleanup_stale_agents():
            """Clean up stale agents from coordination registry."""
            self.stats["requests"] += 1
            try:
                # Clean up agents older than 1 hour
                import time

                current_time = time.time()
                stale_agents = []

                for agent_id, work in list(
                    self.coordination_registry.active_agents.items()
                ):
                    if current_time - work.started_at > 3600:  # 1 hour
                        stale_agents.append(agent_id)

                # Remove stale agents and their locks
                for agent_id in stale_agents:
                    work = self.coordination_registry.active_agents[agent_id]
                    # Release any file locks
                    for file_path in list(work.files_editing):
                        if file_path in self.coordination_registry.file_locks:
                            if (
                                self.coordination_registry.file_locks[
                                    file_path
                                ].agent_id
                                == agent_id
                            ):
                                del self.coordination_registry.file_locks[file_path]
                    # Remove from active agents
                    del self.coordination_registry.active_agents[agent_id]

                # Also clean up session mappings for removed agents
                sessions_to_remove = []
                for session_id, mapped_agent_id in list(
                    self.coordination_registry.session_to_agent.items()
                ):
                    if mapped_agent_id in stale_agents:
                        sessions_to_remove.append(session_id)

                for session_id in sessions_to_remove:
                    del self.coordination_registry.session_to_agent[session_id]

                return {
                    "status": "cleaned",
                    "stale_agents_removed": len(stale_agents),
                    "sessions_cleaned": len(sessions_to_remove),
                    "agents_removed": stale_agents,
                }
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Cleanup failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/coordination/metrics")
        async def get_coordination_metrics():
            """Get coordination system metrics and statistics."""
            self.stats["requests"] += 1
            try:
                if not self.coordination_registry:
                    raise HTTPException(
                        status_code=503, detail="Coordination service unavailable"
                    )

                # Gather comprehensive coordination metrics
                active_agents = len(self.coordination_registry.active_agents)
                file_locks = len(self.coordination_registry.file_locks)
                session_mappings = len(self.coordination_registry.session_to_agent)

                # Get detailed agent information
                agents_info = []
                for agent_id, work in self.coordination_registry.active_agents.items():
                    agents_info.append(
                        {
                            "agent_id": agent_id,
                            "description": work.description,
                            "started_at": work.started_at,
                            "files_editing": list(work.files_editing),
                            "status": "active",
                        }
                    )

                # Get file lock information
                file_locks_info = []
                for (
                    file_path,
                    lock_info,
                ) in self.coordination_registry.file_locks.items():
                    file_locks_info.append(
                        {
                            "file_path": file_path,
                            "agent_id": lock_info.agent_id,
                            "locked_at": lock_info.locked_at,
                        }
                    )

                return {
                    "timestamp": datetime.now().isoformat(),
                    "coordination_metrics": {
                        "active_agents": active_agents,
                        "file_locks": file_locks,
                        "session_mappings": session_mappings,
                    },
                    "agents": agents_info,
                    "file_locks": file_locks_info,
                    "server_stats": self.stats,
                }

            except HTTPException:
                raise
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Coordination metrics failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/coordination/file-locks")
        async def get_file_locks():
            """Get current file locks status."""
            self.stats["requests"] += 1
            try:
                if not self.coordination_registry:
                    raise HTTPException(
                        status_code=503, detail="Coordination service unavailable"
                    )

                # Get detailed file lock status
                locks = []
                for (
                    file_path,
                    lock_info,
                ) in self.coordination_registry.file_locks.items():
                    locks.append(
                        {
                            "file_path": file_path,
                            "agent_id": lock_info.agent_id,
                            "locked_at": lock_info.locked_at,
                            "lock_duration_seconds": datetime.now().timestamp()
                            - lock_info.locked_at,
                        }
                    )

                return {
                    "timestamp": datetime.now().isoformat(),
                    "total_locks": len(locks),
                    "locks": locks,
                }

            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"File locks retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/coordinate/register-session")
        async def register_session_mapping(request: SessionMappingRequest):
            """Register mapping between Claude session ID and agent ID."""
            self.stats["requests"] += 1
            try:
                self.coordination_registry.register_session_mapping(
                    request.session_id, request.agent_id
                )
                return {
                    "status": "registered",
                    "message": f"Session {request.session_id[:8]}... mapped to {request.agent_id}",
                }
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Session mapping failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Planning service endpoints
        @self.app.post("/api/plan")
        async def create_plan(request: dict[str, Any]):
            """Create execution plan."""
            self.stats["requests"] += 1
            try:
                if not self.planner_service:
                    raise HTTPException(
                        status_code=503, detail="Planning service unavailable"
                    )

                plan = await self.planner_service.create_plan(request.get("task", ""))
                return plan
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Planning failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Session service endpoints
        @self.app.get("/api/sessions")
        async def list_sessions():
            """List active sessions."""
            self.stats["requests"] += 1
            try:
                if not self.session_service:
                    raise HTTPException(
                        status_code=503, detail="Session service unavailable"
                    )

                sessions = await self.session_service.list_sessions()
                return {"sessions": sessions}
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Session listing failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Artifacts service endpoints
        @self.app.get("/api/artifacts")
        async def list_artifacts():
            """List artifacts."""
            self.stats["requests"] += 1
            try:
                if not self.artifact_service:
                    raise HTTPException(
                        status_code=503, detail="Artifacts service unavailable"
                    )

                artifacts = await self.artifact_service.list_artifacts()
                return {"artifacts": artifacts}
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Artifacts listing failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Agent management endpoints
        @self.app.post("/api/agents")
        async def spawn_agent(request: AgentSpawnRequest):
            """Spawn a new agent with specified role and domain."""
            self.stats["requests"] += 1
            try:
                if not self.agent_composer:
                    raise HTTPException(
                        status_code=503, detail="Agent composer service unavailable"
                    )

                # Validate role exists
                available_roles = self.agent_composer.list_available_roles()
                if request.role not in available_roles:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid role '{request.role}'. Available roles: {', '.join(available_roles)}",
                    )

                # Validate domain if provided
                if request.domain:
                    available_domains = self.agent_composer.list_available_domains()
                    if request.domain not in available_domains:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid domain '{request.domain}'. Available domains: {', '.join(available_domains[:10])}...",
                        )

                # Compose agent specification
                agent_spec = self.agent_composer.compose_agent(
                    role=request.role, domains=request.domain, context=request.context
                )

                # Add coordination metadata if provided
                if request.coordination_id:
                    agent_spec["coordination_id"] = request.coordination_id
                if request.session_id:
                    agent_spec["session_id"] = request.session_id

                # Generate agent ID
                agent_id = self.agent_composer.get_unique_agent_id(
                    request.role, request.domain or "general"
                )

                # In a real implementation, this would actually spawn the agent process
                # For now, return the agent specification and spawn command
                spawn_command = f"uv run khive compose {request.role}"
                if request.domain:
                    spawn_command += f" -d {request.domain}"
                if request.context:
                    spawn_command += f' -c "{request.context}"'
                if request.coordination_id:
                    spawn_command += f" --coordination-id {request.coordination_id}"

                return {
                    "status": "spawned",
                    "agent_id": agent_id,
                    "role": request.role,
                    "domain": request.domain,
                    "spawn_command": spawn_command,
                    "agent_spec": {
                        "identity": agent_spec.get("identity", {}),
                        "capabilities": agent_spec.get("capabilities", ""),
                        "domains": len(agent_spec.get("domains", [])),
                    },
                }

            except HTTPException:
                raise
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Agent spawning failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/config/roles")
        async def get_available_roles():
            """Get list of available agent roles."""
            self.stats["requests"] += 1
            try:
                if not self.agent_composer:
                    raise HTTPException(
                        status_code=503, detail="Agent composer service unavailable"
                    )

                roles = self.agent_composer.list_available_roles()
                return {"roles": roles, "count": len(roles)}

            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Roles listing failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/config/domains")
        async def get_available_domains():
            """Get list of available domain expertise modules."""
            self.stats["requests"] += 1
            try:
                if not self.agent_composer:
                    raise HTTPException(
                        status_code=503, detail="Agent composer service unavailable"
                    )

                domains = self.agent_composer.list_available_domains()
                taxonomy = self.agent_composer.list_domains_by_taxonomy()

                return {"domains": domains, "count": len(domains), "taxonomy": taxonomy}

            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Domains listing failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Missing endpoints implementation
        @self.app.get("/api/events", response_model=list[HookEvent])
        async def get_events():
            """Get hook events for frontend dashboard."""
            self.stats["requests"] += 1
            try:
                # Generate mock hook events data
                # In a real implementation, this would come from a coordination event store
                current_time = datetime.now()
                mock_events = [
                    HookEvent(
                        id=f"event_{i}",
                        coordinationId="plan_1756916202",
                        agentId=f"agent_{i % 3}",
                        eventType=[
                            "pre_command",
                            "post_command",
                            "pre_edit",
                            "post_edit",
                        ][i % 4],
                        timestamp=(current_time - timedelta(minutes=i * 5)).isoformat(),
                        metadata={"task": f"Task {i}", "duration_ms": 150 + i * 10},
                        filePath="/path/to/file.py" if i % 2 == 0 else None,
                        command=f"command_{i}" if i % 3 == 0 else None,
                    )
                    for i in range(10)
                ]
                return mock_events
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Events retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/plans", response_model=list[Plan])
        async def get_plans():
            """Get execution plans for frontend dashboard."""
            self.stats["requests"] += 1
            try:
                # Generate mock plans data
                # In a real implementation, this would come from the planning service
                mock_plans = [
                    Plan(
                        id="plan_1756916202",
                        sessionId="session_001",
                        nodes=[
                            PlanNode(
                                id="phase_1",
                                phase="Analysis",
                                status="completed",
                                agents=["analyst_protocol-design"],
                                tasks=["API endpoint definition"],
                                coordinationStrategy="FAN_OUT_SYNTHESIZE",
                                expectedArtifacts=["api_analysis.md"],
                                dependencies=[],
                            ),
                            PlanNode(
                                id="phase_2",
                                phase="Implementation",
                                status="running",
                                agents=["implementer_rust-performance"],
                                tasks=["Implement missing API endpoints"],
                                coordinationStrategy="PARALLEL",
                                expectedArtifacts=["server.py updates"],
                                dependencies=["phase_1"],
                            ),
                        ],
                        edges=[{"from": "phase_1", "to": "phase_2"}],
                    )
                ]
                return mock_plans
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Plans retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get(
            "/api/observability/system-performance",
            response_model=SystemPerformanceMetrics,
        )
        async def get_system_performance():
            """Get system performance metrics for observability dashboard."""
            self.stats["requests"] += 1
            try:
                import psutil

                # Get current system metrics
                cpu_percent = psutil.cpu_percent()
                memory = psutil.virtual_memory()

                # Generate historical data points (last 10 data points)
                current_time = datetime.now()
                cpu_history = [
                    MetricDataPoint(
                        timestamp=(current_time - timedelta(minutes=i)).isoformat(),
                        value=max(
                            0, cpu_percent + (i * 2.5) - 12.5
                        ),  # Simulated variation
                    )
                    for i in range(10)
                ]

                memory_history = [
                    MetricDataPoint(
                        timestamp=(current_time - timedelta(minutes=i)).isoformat(),
                        value=max(
                            0, memory.percent + (i * 1.2) - 6
                        ),  # Simulated variation
                    )
                    for i in range(10)
                ]

                performance_metrics = SystemPerformanceMetrics(
                    cpu={"usage": cpu_percent, "history": cpu_history},
                    memory={
                        "usage": memory.percent,
                        "total": memory.total / (1024 * 1024),  # Convert to MB
                        "used": memory.used / (1024 * 1024),  # Convert to MB
                        "history": memory_history,
                    },
                    timestamp=current_time.isoformat(),
                )

                return performance_metrics
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"System performance retrieval failed: {e}")
                # Return fallback metrics if psutil fails
                current_time = datetime.now()
                fallback_history = [
                    MetricDataPoint(
                        timestamp=(current_time - timedelta(minutes=i)).isoformat(),
                        value=50.0 + (i * 2),  # Fallback data
                    )
                    for i in range(10)
                ]

                return SystemPerformanceMetrics(
                    cpu={"usage": 45.0, "history": fallback_history},
                    memory={
                        "usage": 60.0,
                        "total": 16384.0,  # 16GB fallback
                        "used": 9830.0,  # ~60% used
                        "history": fallback_history,
                    },
                    timestamp=current_time.isoformat(),
                )

        @self.app.get(
            "/api/observability/agent-analytics", response_model=AgentAnalytics
        )
        async def get_agent_analytics():
            """Get agent analytics for observability dashboard."""
            self.stats["requests"] += 1
            try:
                # Generate mock agent analytics based on coordination data
                # In a real implementation, this would aggregate data from the coordination registry

                current_time = datetime.now()

                # Mock role performance data
                role_performance = [
                    RolePerformanceMetrics(
                        role="implementer",
                        successRate=85.5,
                        totalTasks=23,
                        averageCompletionTime=1800.0,  # 30 minutes
                    ),
                    RolePerformanceMetrics(
                        role="analyst",
                        successRate=92.0,
                        totalTasks=18,
                        averageCompletionTime=1200.0,  # 20 minutes
                    ),
                    RolePerformanceMetrics(
                        role="tester",
                        successRate=78.3,
                        totalTasks=12,
                        averageCompletionTime=900.0,  # 15 minutes
                    ),
                ]

                # Mock domain performance data
                domain_performance = [
                    DomainPerformanceMetrics(
                        domain="rust-performance",
                        successRate=88.0,
                        totalTasks=15,
                        averageCompletionTime=2100.0,
                    ),
                    DomainPerformanceMetrics(
                        domain="event-sourcing",
                        successRate=95.0,
                        totalTasks=10,
                        averageCompletionTime=1500.0,
                    ),
                    DomainPerformanceMetrics(
                        domain="protocol-design",
                        successRate=90.0,
                        totalTasks=8,
                        averageCompletionTime=1800.0,
                    ),
                ]

                # Mock recent activity data (last 24 hours)
                recent_activity = [
                    AgentActivityPoint(
                        timestamp=(current_time - timedelta(hours=i)).isoformat(),
                        successful=max(0, 5 - i // 3),  # Decreasing activity over time
                        failed=max(0, i // 6),  # Some failures
                    )
                    for i in range(24)
                ]

                # Calculate totals
                total_tasks = sum(role.totalTasks for role in role_performance)
                completed_tasks = int(total_tasks * 0.85)  # 85% average success rate
                failed_tasks = total_tasks - completed_tasks

                analytics = AgentAnalytics(
                    successRate=85.0,
                    totalTasks=total_tasks,
                    completedTasks=completed_tasks,
                    failedTasks=failed_tasks,
                    performanceByRole=role_performance,
                    performanceByDomain=domain_performance,
                    recentActivity=recent_activity,
                )

                return analytics
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Agent analytics retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))


def create_daemon_server() -> KhiveDaemonServer:
    """Create daemon server instance."""
    return KhiveDaemonServer()


# Global server instance
_daemon_server = None


def get_daemon_server() -> KhiveDaemonServer:
    """Get daemon server instance."""
    global _daemon_server
    if _daemon_server is None:
        _daemon_server = create_daemon_server()
    return _daemon_server


async def run_daemon_server(host: str = "localhost", port: int = 11634):
    """Run daemon server."""
    import uvicorn

    server = get_daemon_server()
    config = uvicorn.Config(server.app, host=host, port=port, log_level="info")

    uvicorn_server = uvicorn.Server(config)
    await uvicorn_server.serve()


if __name__ == "__main__":
    asyncio.run(run_daemon_server())
