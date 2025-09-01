"""
Khive Daemon Server - Clean Implementation

Provides basic coordination and planning services for khive agents.
No fake or misleading functionality - only working features.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from khive.services.claude.hooks.coordination import (
    CoordinationRegistry,
    get_registry,
    before_file_edit,
    after_file_edit,
    check_duplicate_work,
    whats_happening,
)
from khive.services.plan.planner_service import PlannerService
from khive.services.session.session_service import SessionService
from khive.services.artifacts.service import ArtifactsService
from khive.services.artifacts.factory import create_artifacts_service_from_env

logger = logging.getLogger(__name__)


# Request/Response Models
class CoordinateRequest(BaseModel):
    task_id: str
    description: str
    agent_id: str


class CoordinateCompleteRequest(BaseModel):
    task_id: str
    agent_id: str
    result: str


class InsightsRequest(BaseModel):
    task_description: str
    agent_id: str


class FileOperationRequest(BaseModel):
    file_path: str
    agent_id: str


class FileUnregisterRequest(BaseModel):
    file_path: str
    agent_id: str


class KhiveDaemonServer:
    """Clean khive daemon server with basic coordination."""

    def __init__(self):
        self.app = FastAPI(title="Khive Daemon", version="1.0.0")
        self.coordination_registry: CoordinationRegistry | None = None
        self.planner_service: PlannerService | None = None
        self.session_service: SessionService | None = None
        self.artifact_service: ArtifactsService | None = None
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
                }
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
                        "existing_task": duplicate
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
                    raise HTTPException(status_code=503, detail="Coordination service unavailable")

                result = self.coordination_registry.complete_task(
                    request.task_id, request.agent_id, request.result
                )
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
                    raise HTTPException(status_code=503, detail="Coordination service unavailable")

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
                    raise HTTPException(
                        status_code=409,
                        detail=result
                    )
                
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

        # Planning service endpoints
        @self.app.post("/api/plan")
        async def create_plan(request: Dict[str, Any]):
            """Create execution plan."""
            self.stats["requests"] += 1
            try:
                if not self.planner_service:
                    raise HTTPException(status_code=503, detail="Planning service unavailable")

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
                    raise HTTPException(status_code=503, detail="Session service unavailable")

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
                    raise HTTPException(status_code=503, detail="Artifacts service unavailable")

                artifacts = await self.artifact_service.list_artifacts()
                return {"artifacts": artifacts}
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Artifacts listing failed: {e}")
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
    config = uvicorn.Config(
        server.app,
        host=host,
        port=port,
        log_level="info"
    )
    
    uvicorn_server = uvicorn.Server(config)
    await uvicorn_server.serve()


if __name__ == "__main__":
    asyncio.run(run_daemon_server())