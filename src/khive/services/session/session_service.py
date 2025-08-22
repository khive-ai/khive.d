# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import logging

from .parts import SessionRequest, SessionResponse
from .session import DiaryWritingAssistant, SessionInitializer

logger = logging.getLogger(__name__)


class SessionService:
    """
    Session Management Service.

    Wraps the SessionInitializer and DiaryWritingAssistant to provide
    session management capabilities.
    """

    def __init__(self):
        """Initialize the session service."""
        self._session_lock = asyncio.Lock()

    async def handle_request(self, request: SessionRequest) -> SessionResponse:
        """
        Handle a session request.

        Args:
            request: The session request

        Returns:
            Session response with operation results
        """
        try:
            # Parse request if needed
            if isinstance(request, str):
                request = SessionRequest.model_validate_json(request)
            elif isinstance(request, dict):
                request = SessionRequest.model_validate(request)

            async with self._session_lock:
                if request.action == "init":
                    return await self._handle_init(request)
                if request.action == "end":
                    return await self._handle_end(request)
                if request.action == "status":
                    return await self._handle_status(request)
                return SessionResponse(
                    success=False,
                    summary=f"Unknown action: {request.action}",
                    error="Supported actions: init, end, status",
                )

        except Exception as e:
            logger.error(f"Error in handle_request: {e}", exc_info=True)
            return SessionResponse(
                success=False,
                summary=f"Session operation failed: {e!s}",
                error=str(e),
            )

    async def _handle_init(self, request: SessionRequest) -> SessionResponse:
        """Handle session initialization."""
        initializer = SessionInitializer(
            issue=request.issue,
            resume=request.resume,
            depth=request.depth,
            continue_session=request.continue_session,
        )

        # Run initialization in thread pool since it's sync
        session_output = await asyncio.get_event_loop().run_in_executor(
            None, initializer.initialize
        )

        return SessionResponse(
            success=True,
            summary="Session initialized successfully",
            session_output=session_output,
            pending_tasks=initializer.context.get("pending_tasks", []),
            git_status=initializer.context.get("git_status", {}),
            unprocessed_summaries=initializer.context.get("unprocessed_summaries", 0),
        )

    async def _handle_end(self, request: SessionRequest) -> SessionResponse:
        """Handle session end (diary writing)."""
        assistant = DiaryWritingAssistant(dry_run=False, target_date=None)

        # Run diary processing in thread pool since it's sync
        await asyncio.get_event_loop().run_in_executor(None, assistant.process_diaries)

        return SessionResponse(
            success=True, summary="Session ended and diary processing completed"
        )

    async def _handle_status(self, request: SessionRequest) -> SessionResponse:
        """Handle session status check."""
        initializer = SessionInitializer(
            issue=request.issue,
            resume=request.resume,
            depth=request.depth,
            continue_session=request.continue_session,
        )

        # Get status information
        unprocessed_count = initializer.count_unprocessed_summaries()
        pending_tasks = initializer.get_pending_tasks()
        git_status = initializer.get_git_status()

        return SessionResponse(
            success=True,
            summary=f"Session status: {unprocessed_count} unprocessed summaries, {len(pending_tasks)} pending tasks",
            pending_tasks=pending_tasks,
            git_status=git_status,
            unprocessed_summaries=unprocessed_count,
        )

    async def init_session(self, request: SessionRequest) -> SessionResponse:
        """
        Initialize a session (alias for handle_request with action='init').

        Args:
            request: The session request

        Returns:
            Session response
        """
        request.action = "init"
        return await self.handle_request(request)

    async def end_session(self, request: SessionRequest) -> SessionResponse:
        """
        End a session (alias for handle_request with action='end').

        Args:
            request: The session request

        Returns:
            Session response
        """
        request.action = "end"
        return await self.handle_request(request)

    async def close(self) -> None:
        """Clean up resources."""
        try:
            # No cleanup needed for session service
            pass
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
