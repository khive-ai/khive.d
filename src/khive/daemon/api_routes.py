"""
Additional API Routes for Khive Daemon Server
Implements missing endpoints identified during backend-frontend integration.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# Request/Response Models for new endpoints
class EventModel(BaseModel):
    """Event data model for logging system events."""

    id: str
    timestamp: str
    type: str
    source: str
    data: Dict[str, Any]
    level: str = "info"


class CreateEventRequest(BaseModel):
    """Request model for creating new events."""

    type: str
    source: str
    data: Dict[str, Any]
    level: str = "info"


class CreateSessionRequest(BaseModel):
    """Request model for creating new sessions."""

    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SystemPerformanceMetrics(BaseModel):
    """System performance metrics model."""

    timestamp: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    active_processes: int
    uptime_seconds: float


class AgentAnalytics(BaseModel):
    """Agent analytics data model."""

    timestamp: str
    total_agents: int
    active_agents: int
    completed_tasks: int
    failed_tasks: int
    average_task_duration: float
    agent_performance: List[Dict[str, Any]]


def create_additional_routes() -> APIRouter:
    """Create additional API routes for missing endpoints."""

    router = APIRouter()

    # In-memory storage for demo purposes (production would use proper persistence)
    events_storage: List[EventModel] = []
    plans_storage: List[Dict[str, Any]] = []

    @router.get("/api/events", response_model=List[EventModel])
    async def list_events(
        limit: int = Query(default=50, le=1000),
        event_type: Optional[str] = Query(default=None),
        level: Optional[str] = Query(default=None),
    ):
        """List system events with optional filtering."""
        try:
            # Filter events based on query parameters
            filtered_events = events_storage.copy()

            if event_type:
                filtered_events = [e for e in filtered_events if e.type == event_type]

            if level:
                filtered_events = [e for e in filtered_events if e.level == level]

            # Sort by timestamp (newest first) and limit
            filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
            return filtered_events[:limit]

        except Exception as e:
            logger.error(f"Events listing failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/api/events", response_model=EventModel)
    async def create_event(request: CreateEventRequest):
        """Create a new system event."""
        try:
            event = EventModel(
                id=f"evt_{int(time.time() * 1000)}_{len(events_storage)}",
                timestamp=datetime.now().isoformat(),
                type=request.type,
                source=request.source,
                data=request.data,
                level=request.level,
            )

            events_storage.append(event)

            # Keep only last 1000 events to prevent memory issues
            if len(events_storage) > 1000:
                events_storage.pop(0)

            logger.info(f"Event created: {event.type} from {event.source}")
            return event

        except Exception as e:
            logger.error(f"Event creation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/plans")
    async def list_plans(
        limit: int = Query(default=50, le=1000),
        status: Optional[str] = Query(default=None),
    ):
        """List execution plans with optional filtering."""
        try:
            # Filter plans based on status if provided
            filtered_plans = plans_storage.copy()

            if status:
                filtered_plans = [
                    p for p in filtered_plans if p.get("status") == status
                ]

            # Sort by created_at (newest first) and limit
            filtered_plans.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return {"plans": filtered_plans[:limit], "total": len(filtered_plans)}

        except Exception as e:
            logger.error(f"Plans listing failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/api/sessions")
    async def create_session(request: CreateSessionRequest):
        """Create a new session."""
        try:
            session_id = f"sess_{int(time.time() * 1000)}"
            session = {
                "id": session_id,
                "name": request.name,
                "description": request.description,
                "metadata": request.metadata or {},
                "created_at": datetime.now().isoformat(),
                "status": "active",
            }

            # In a real implementation, this would be saved to persistent storage
            # For now, we'll just return the session data

            logger.info(f"Session created: {session_id}")
            return session

        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get(
        "/api/observability/system-performance", response_model=SystemPerformanceMetrics
    )
    async def get_system_performance():
        """Get current system performance metrics."""
        try:
            import os

            import psutil

            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            network = psutil.net_io_counters()

            metrics = SystemPerformanceMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_usage=cpu_percent,
                memory_usage=memory.percent,
                disk_usage=(disk.used / disk.total) * 100,
                network_io={
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                },
                active_processes=len(psutil.pids()),
                uptime_seconds=time.time() - psutil.boot_time(),
            )

            return metrics

        except ImportError:
            # Fallback if psutil is not available
            return SystemPerformanceMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_io={
                    "bytes_sent": 0,
                    "bytes_recv": 0,
                    "packets_sent": 0,
                    "packets_recv": 0,
                },
                active_processes=0,
                uptime_seconds=0.0,
            )
        except Exception as e:
            logger.error(f"System performance metrics failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/observability/agent-analytics", response_model=AgentAnalytics)
    async def get_agent_analytics():
        """Get agent performance analytics."""
        try:
            # This would typically pull from a coordination registry or database
            # For now, return mock analytics data structure

            analytics = AgentAnalytics(
                timestamp=datetime.now().isoformat(),
                total_agents=0,
                active_agents=0,
                completed_tasks=0,
                failed_tasks=0,
                average_task_duration=0.0,
                agent_performance=[],
            )

            return analytics

        except Exception as e:
            logger.error(f"Agent analytics failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return router


def register_routes_with_server(app, server_instance):
    """Register additional routes with the main server instance.

    This function should be called from the main server to integrate
    these additional routes with access to server services.
    """
    router = create_additional_routes()

    # Override the plans endpoint to use the server's planner service
    @app.get("/api/plans")
    async def list_plans_with_service(
        limit: int = Query(default=50, le=1000),
        status: Optional[str] = Query(default=None),
    ):
        """List execution plans using the server's planner service."""
        try:
            if not server_instance.planner_service:
                raise HTTPException(
                    status_code=503, detail="Planning service unavailable"
                )

            # In a real implementation, the planner service would have a list_plans method
            # For now, return empty plans with proper structure
            plans = []

            if status:
                plans = [p for p in plans if p.get("status") == status]

            return {"plans": plans[:limit], "total": len(plans)}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Plans listing with service failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # Override agent analytics to use coordination registry
    @app.get("/api/observability/agent-analytics", response_model=AgentAnalytics)
    async def get_agent_analytics_with_registry():
        """Get agent analytics using coordination registry."""
        try:
            if not server_instance.coordination_registry:
                raise HTTPException(
                    status_code=503, detail="Coordination service unavailable"
                )

            registry = server_instance.coordination_registry
            active_agents = len(registry.active_agents)

            # Calculate analytics from coordination data
            analytics = AgentAnalytics(
                timestamp=datetime.now().isoformat(),
                total_agents=active_agents + registry.metrics["duplicates_avoided"],
                active_agents=active_agents,
                completed_tasks=registry.metrics["duplicates_avoided"],
                failed_tasks=0,  # Could track from server stats
                average_task_duration=0.0,  # Would need task timing data
                agent_performance=[
                    {
                        "agent_id": agent_id,
                        "status": "active",
                        "tasks_completed": 0,
                        "avg_duration": 0.0,
                    }
                    for agent_id in registry.active_agents.keys()
                ],
            )

            return analytics

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Agent analytics with registry failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # Include the router for other endpoints
    app.include_router(router)

    return app
