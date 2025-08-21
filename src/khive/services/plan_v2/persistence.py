"""Data persistence for planner service using SQLite.

This module provides database persistence for planning sessions,
following the same pattern as Claude hooks for consistency.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from lionagi.protocols.types import Node
from pydantic import field_validator
from typing_extensions import TypedDict

from khive.utils import get_logger

logger = get_logger("khive.services.plan.persistence")

# Use project root .khive directory for database
from pathlib import Path

PROJECT_ROOT = Path.cwd()
PLANNER_DB_DSN = f"sqlite+aiosqlite:///{PROJECT_ROOT}/.khive/planner_sessions.db"


class PlannerSessionContent(TypedDict, total=False):
    """Content structure for planner session records."""

    session_id: str
    task_description: str
    complexity: str
    agent_count: int
    workflow_pattern: str
    confidence: float
    planning_cost: float
    evaluations: list[dict[str, Any]]
    consensus: dict[str, Any]
    execution_plan: str
    phases: list[dict[str, Any]]
    metadata: dict[str, Any]


class PlannerSession(Node):
    """Persistent storage for planner sessions."""

    content: PlannerSessionContent
    _initialized: ClassVar[bool] = False
    _table_name: ClassVar[str] = "planner_sessions"

    @field_validator("content", mode="before")
    def _validate_content(cls, value) -> dict:
        if value is None:
            raise ValueError("Content is required")

        if isinstance(value, dict):
            if "session_id" not in value:
                raise ValueError("Session ID is required")
            if "task_description" not in value:
                raise ValueError("Task description is required")
            return value
        raise ValueError("Content must be a dictionary")

    async def save(self):
        """Save planner session to database."""
        # Initialize adapter if needed
        _initialize_planner_adapter()

        # Save to database
        result = await self.adapt_to_async(
            obj_key="lionagi_async_pg",
            dsn=PLANNER_DB_DSN,
            table=self._table_name,
        )

        logger.info(f"Saved planner session: {self.content.get('session_id')}")
        return result

    @classmethod
    async def get_by_session_id(cls, session_id: str) -> PlannerSession | None:
        """Get planner session by session ID."""
        from sqlalchemy import text

        _initialize_planner_adapter()

        params = {
            "dsn": PLANNER_DB_DSN,
            "table": cls._table_name,
            "where": text(f"content->>'session_id' = '{session_id}'"),
            "limit": 1,
        }

        results = await cls.adapt_from_async(
            params,
            obj_key="lionagi_async_pg",
            many=True,
        )

        return results[0] if results else None

    @classmethod
    async def get_recent(cls, limit: int = 10) -> list[PlannerSession]:
        """Get recent planner sessions."""
        _initialize_planner_adapter()

        params = {
            "dsn": PLANNER_DB_DSN,
            "table": cls._table_name,
            "order_by": "created_at DESC",
            "limit": limit,
        }

        return await cls.adapt_from_async(
            params,
            obj_key="lionagi_async_pg",
            many=True,
        )

    @classmethod
    async def get_by_complexity(
        cls, complexity: str, limit: int | None = None
    ) -> list[PlannerSession]:
        """Get sessions by complexity level."""
        from sqlalchemy import text

        _initialize_planner_adapter()

        params = {
            "dsn": PLANNER_DB_DSN,
            "table": cls._table_name,
            "where": text(f"content->>'complexity' = '{complexity}'"),
            "order_by": "created_at DESC",
        }
        if limit:
            params["limit"] = limit

        return await cls.adapt_from_async(
            params,
            obj_key="lionagi_async_pg",
            many=True,
        )

    @classmethod
    async def get_by_date_range(
        cls, start_date: str, end_date: str | None = None, limit: int | None = None
    ) -> list[PlannerSession]:
        """Get sessions within a date range."""
        from sqlalchemy import text

        _initialize_planner_adapter()

        where_clause = f"created_at >= '{start_date}'"
        if end_date:
            where_clause += f" AND created_at <= '{end_date}'"

        params = {
            "dsn": PLANNER_DB_DSN,
            "table": cls._table_name,
            "where": text(where_clause),
            "order_by": "created_at DESC",
        }
        if limit:
            params["limit"] = limit

        return await cls.adapt_from_async(
            params,
            obj_key="lionagi_async_pg",
            many=True,
        )

    @classmethod
    async def get_stats(cls) -> dict[str, Any]:
        """Get statistics about stored sessions."""
        _initialize_planner_adapter()

        # This would need a raw SQL query for aggregation
        # For now, return basic stats
        all_sessions = await cls.adapt_from_async(
            {
                "dsn": PLANNER_DB_DSN,
                "table": cls._table_name,
            },
            obj_key="lionagi_async_pg",
            many=True,
        )

        if not all_sessions:
            return {
                "total_sessions": 0,
                "complexities": {},
                "avg_agent_count": 0,
                "avg_confidence": 0,
                "total_cost": 0,
            }

        complexities = {}
        total_agents = 0
        total_confidence = 0
        total_cost = 0

        for session in all_sessions:
            complexity = session.content.get("complexity", "unknown")
            complexities[complexity] = complexities.get(complexity, 0) + 1
            total_agents += session.content.get("agent_count", 0)
            total_confidence += session.content.get("confidence", 0)
            total_cost += session.content.get("planning_cost", 0)

        return {
            "total_sessions": len(all_sessions),
            "complexities": complexities,
            "avg_agent_count": total_agents / len(all_sessions) if all_sessions else 0,
            "avg_confidence": (
                total_confidence / len(all_sessions) if all_sessions else 0
            ),
            "total_cost": total_cost,
        }


def _initialize_planner_adapter():
    """Initialize the async adapter for planner SQLite database."""
    if PlannerSession._initialized:
        return

    from pydapter.exceptions import AdapterNotFoundError

    try:
        PlannerSession._async_registry.get("lionagi_async_pg")
    except (AdapterNotFoundError, KeyError):
        logger.info("Initializing database adapter for planner sessions...")
        from lionagi.adapters.async_postgres_adapter import LionAGIAsyncPostgresAdapter

        # Register the adapter (it will use default key)
        PlannerSession.register_async_adapter(LionAGIAsyncPostgresAdapter)

    PlannerSession._initialized = True
    logger.info("Planner database adapter initialized successfully")


async def save_planning_session(
    session_id: str,
    task_description: str,
    complexity: str,
    agent_count: int,
    workflow_pattern: str,
    confidence: float,
    planning_cost: float,
    evaluations: list[dict[str, Any]] | None = None,
    consensus: dict[str, Any] | None = None,
    execution_plan: str | None = None,
    phases: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> PlannerSession:
    """Helper function to save a planning session."""

    session = PlannerSession(
        content={
            "session_id": session_id,
            "task_description": task_description,
            "complexity": complexity,
            "agent_count": agent_count,
            "workflow_pattern": workflow_pattern,
            "confidence": confidence,
            "planning_cost": planning_cost,
            "evaluations": evaluations or [],
            "consensus": consensus or {},
            "execution_plan": execution_plan or "",
            "phases": phases or [],
            "metadata": metadata or {},
        }
    )

    await session.save()
    return session


__all__ = [
    "PlannerSession",
    "PlannerSessionContent",
    "save_planning_session",
    "PLANNER_DB_DSN",
]
