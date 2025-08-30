"""
Khive Daemon Server - Ollama-style persistent service.

Provides core khive services via HTTP API:
- Coordination registry (stateful, memory-intensive)
- Hook event processing (needs persistent connections)
- Planning service (caches patterns and learnings)
- Session management (maintains state across commands)
- MCP server management (long-running processes)

Client-side operations (NOT in daemon):
- File operations (edit, write, read)
- Git operations 
- Simple CLI commands
"""

import asyncio
import json
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from khive.services.claude.hooks import (
    CoordinationRegistry,
    get_registry,
    coordinate_task_start,
    coordinate_task_complete,
    get_coordination_insights,
)
from khive.services.plan.planner_service import PlannerService
# from khive.services.session.session_service import SessionService
# from khive.services.artifacts.service import ArtifactsService
from khive.utils import get_logger

logger = get_logger("KhiveDaemon", "🔮 [KHIVE-DAEMON]")

# Daemon configuration
DAEMON_HOST = os.getenv("KHIVE_DAEMON_HOST", "127.0.0.1")
DAEMON_PORT = int(os.getenv("KHIVE_DAEMON_PORT", "11434"))  # Similar to Ollama
PID_FILE = Path.home() / ".khive" / "daemon.pid"
LOG_FILE = Path.home() / ".khive" / "daemon.log"


class DaemonServer:
    """Khive daemon server providing core services."""
    
    def __init__(self):
        self.app = FastAPI(title="Khive Daemon", version="1.0.0")
        self.coordination_registry: Optional[CoordinationRegistry] = None
        self.planner_service: Optional[PlannerService] = None
        # self.session_service: Optional[SessionService] = None
        # self.artifact_service: Optional[ArtifactsService] = None
        self.startup_time = datetime.now()
        self.stats = {
            "requests": 0,
            "errors": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
        
        # Setup routes
        self._setup_routes()
    
    async def initialize(self):
        """Initialize daemon services."""
        logger.info("Initializing Khive daemon services...")
        
        # Initialize core services
        self.coordination_registry = get_registry()
        self.planner_service = PlannerService()
        # TODO: Add session and artifact services once properly configured
        # self.session_service = SessionService()
        # self.artifact_service = ArtifactsService()
        
        logger.info("✅ Daemon services initialized")
    
    def _setup_routes(self):
        """Setup API routes."""
        
        # Health check
        @self.app.get("/")
        async def health():
            return {
                "status": "ok",
                "version": "1.0.0",
                "uptime": str(datetime.now() - self.startup_time),
                "stats": self.stats,
            }
        
        # Planning endpoints
        @self.app.post("/api/plan")
        async def plan(request: PlanRequest):
            """Generate orchestration plan."""
            self.stats["requests"] += 1
            try:
                result = await self.planner_service.plan(
                    task_description=request.task_description,
                    context=request.context,
                )
                return JSONResponse(content=result)
            except Exception as e:
                self.stats["errors"] += 1
                raise HTTPException(status_code=500, detail=str(e))
        
        # Coordination endpoints
        @self.app.post("/api/coordinate/start")
        async def coordinate_start(request: CoordinateStartRequest):
            """Register task start."""
            self.stats["requests"] += 1
            task_info = coordinate_task_start(
                request.task_description,
                request.agent_id,
            )
            return JSONResponse(content={
                "task_id": task_info.task_id,
                "task_hash": task_info.task_hash,
                "is_duplicate": task_info.task_hash in self.coordination_registry.task_by_hash,
            })
        
        @self.app.post("/api/coordinate/complete")
        async def coordinate_complete(request: CoordinateCompleteRequest):
            """Register task completion."""
            self.stats["requests"] += 1
            coordinate_task_complete(
                request.task_id,
                request.output,
                request.artifacts,
            )
            return JSONResponse(content={"success": True})
        
        @self.app.post("/api/coordinate/insights")
        async def coordination_insights(request: InsightsRequest):
            """Get coordination insights."""
            self.stats["requests"] += 1
            insights = get_coordination_insights(request.task_description)
            return JSONResponse(content=insights)
        
        # Session endpoints (TODO: Enable when SessionService is configured)
        # @self.app.post("/api/session/init")
        # async def session_init(request: SessionInitRequest):
        #     """Initialize or resume session."""
        #     self.stats["requests"] += 1
        #     if request.resume:
        #         result = await self.session_service.resume()
        #     else:
        #         result = await self.session_service.initialize()
        #     return JSONResponse(content=result)
        
        # @self.app.post("/api/session/end")
        # async def session_end():
        #     """End current session."""
        #     self.stats["requests"] += 1
        #     result = await self.session_service.end()
        #     return JSONResponse(content=result)
        
        # @self.app.get("/api/session/status")
        # async def session_status():
        #     """Get session status."""
        #     self.stats["requests"] += 1
        #     return JSONResponse(content=self.session_service.get_status())
        
        # Hook processing endpoints (for daemon-side hooks)
        @self.app.post("/api/hooks/process")
        async def process_hook(request: HookRequest):
            """Process a hook request."""
            self.stats["requests"] += 1
            
            # Only process hooks that need daemon state
            if request.hook_type in ["pre_command", "post_command", "pre_edit", "post_edit"]:
                # These can benefit from coordination state
                if request.hook_type == "pre_edit":
                    file_path = request.data.get("file_path", "")
                    active_edits = self.coordination_registry.get_active_file_operations()
                    if file_path in active_edits:
                        return JSONResponse(content={
                            "proceed": False,
                            "reason": f"File being edited by: {active_edits[file_path]}",
                        })
                    self.coordination_registry.register_file_operation(
                        file_path,
                        request.data.get("agent_id", "unknown"),
                    )
                    return JSONResponse(content={"proceed": True})
                elif request.hook_type == "post_edit":
                    file_path = request.data.get("file_path", "")
                    self.coordination_registry.unregister_file_operation(file_path)
                    return JSONResponse(content={"success": True})
                    
            return JSONResponse(content={"success": True})
        
        # Artifact service endpoints (TODO: Enable when ArtifactsService is configured)
        # @self.app.post("/api/artifacts/register")
        # async def register_artifact(request: ArtifactRequest):
        #     """Register an artifact."""
        #     self.stats["requests"] += 1
        #     artifact_id = await self.artifact_service.register(
        #         path=request.path,
        #         content=request.content,
        #         metadata=request.metadata,
        #     )
        #     return JSONResponse(content={"artifact_id": artifact_id})
        
        # @self.app.get("/api/artifacts/{artifact_id}")
        # async def get_artifact(artifact_id: str):
        #     """Retrieve an artifact."""
        #     self.stats["requests"] += 1
        #     artifact = await self.artifact_service.get(artifact_id)
        #     if not artifact:
        #         raise HTTPException(status_code=404, detail="Artifact not found")
        #     return JSONResponse(content=artifact)
        
        # Server management
        @self.app.post("/api/shutdown")
        async def shutdown():
            """Gracefully shutdown the daemon."""
            logger.info("Shutdown requested via API")
            asyncio.create_task(self._shutdown())
            return JSONResponse(content={"status": "shutting down"})
    
    async def _shutdown(self):
        """Graceful shutdown."""
        await asyncio.sleep(0.5)  # Let response return
        os.kill(os.getpid(), signal.SIGTERM)
    
    async def start(self):
        """Start the daemon server."""
        # Ensure directories exist
        PID_FILE.parent.mkdir(exist_ok=True)
        
        # Write PID file
        PID_FILE.write_text(str(os.getpid()))
        
        # Initialize services
        await self.initialize()
        
        # Run server
        config = uvicorn.Config(
            app=self.app,
            host=DAEMON_HOST,
            port=DAEMON_PORT,
            log_level="info",
            access_log=False,  # Reduce noise
        )
        server = uvicorn.Server(config)
        
        logger.info(f"✅ Khive daemon started on {DAEMON_HOST}:{DAEMON_PORT}")
        logger.info(f"PID: {os.getpid()}")
        
        await server.serve()
    
    @classmethod
    def run(cls):
        """Run the daemon."""
        daemon = cls()
        asyncio.run(daemon.start())


# Request models
class PlanRequest(BaseModel):
    task_description: str
    context: Optional[Dict[str, Any]] = None


class CoordinateStartRequest(BaseModel):
    task_description: str
    agent_id: str


class CoordinateCompleteRequest(BaseModel):
    task_id: str
    output: str
    artifacts: list[str] = []


class InsightsRequest(BaseModel):
    task_description: str


# class SessionInitRequest(BaseModel):
#     resume: bool = False


class HookRequest(BaseModel):
    hook_type: str
    data: Dict[str, Any]


# class ArtifactRequest(BaseModel):
#     path: str
#     content: Optional[str] = None
#     metadata: Dict[str, Any] = {}


def main():
    """Main entry point."""
    DaemonServer.run()


if __name__ == "__main__":
    main()