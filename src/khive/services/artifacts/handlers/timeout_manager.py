"""
Timeout Management System for Agent Execution
Provides configurable timeout handling for orchestration agents
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiofiles
from khive.core import TimePolicy

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

logger = logging.getLogger(__name__)


class TimeoutType(str, Enum):
    """Types of timeouts in the system."""

    AGENT_EXECUTION = "agent_execution"
    PHASE_COMPLETION = "phase_completion"
    TOTAL_ORCHESTRATION = "total_orchestration"
    RESPONSE_TIMEOUT = "response_timeout"
    HANDOFF_TIMEOUT = "handoff_timeout"


class TimeoutStatus(str, Enum):
    """Status of timeout operations."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class TimeoutConfig:
    """Configuration for timeout handling."""

    # Agent execution timeouts
    agent_execution_timeout: float = 300.0  # 5 minutes default
    phase_completion_timeout: float = 1800.0  # 30 minutes default
    total_orchestration_timeout: float = 3600.0  # 1 hour default

    # Response timeouts
    response_timeout: float = 60.0  # 1 minute default
    handoff_timeout: float = 30.0  # 30 seconds default

    # Timeout behavior
    max_retries: int = 3
    retry_delay: float = 5.0
    escalation_enabled: bool = True

    # Performance targets
    performance_threshold: float = 0.7  # 70% success rate threshold
    timeout_reduction_factor: float = 0.3  # 30% time reduction target

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_execution_timeout": self.agent_execution_timeout,
            "phase_completion_timeout": self.phase_completion_timeout,
            "total_orchestration_timeout": self.total_orchestration_timeout,
            "response_timeout": self.response_timeout,
            "handoff_timeout": self.handoff_timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "escalation_enabled": self.escalation_enabled,
            "performance_threshold": self.performance_threshold,
            "timeout_reduction_factor": self.timeout_reduction_factor,
        }


@dataclass
class TimeoutResult:
    """Result of a timeout operation."""

    operation_id: str
    timeout_type: TimeoutType
    status: TimeoutStatus
    start_time: datetime
    end_time: datetime | None = None
    duration: float | None = None
    error: str | None = None
    retry_count: int = 0

    def mark_completed(self) -> None:
        """Mark operation as completed."""
        self.end_time = TimePolicy.now_utc()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.status = TimeoutStatus.COMPLETED

    def mark_timed_out(self, error: str) -> None:
        """Mark operation as timed out."""
        self.end_time = TimePolicy.now_utc()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.status = TimeoutStatus.TIMED_OUT
        self.error = error

    def mark_error(self, error: str) -> None:
        """Mark operation as failed with error."""
        self.end_time = TimePolicy.now_utc()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.status = TimeoutStatus.ERROR
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation_id": self.operation_id,
            "timeout_type": self.timeout_type.value,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "error": self.error,
            "retry_count": self.retry_count,
        }


class TimeoutManager:
    """
    Manages timeout operations for agent execution and orchestration.

    Provides configurable timeout handling, retry logic, and performance tracking
    for Phase 1 handoff optimizations.
    """

    def __init__(
        self, config: TimeoutConfig | None = None, session_id: str | None = None
    ):
        """
        Initialize timeout manager.

        Args:
            config: Timeout configuration (uses defaults if None)
            session_id: Session ID for tracking
        """
        self.config = config or TimeoutConfig()
        self.session_id = session_id
        self._active_operations: dict[str, TimeoutResult] = {}
        self._operation_tasks: dict[str, asyncio.Task] = {}
        self._performance_metrics: dict[str, Any] = {
            "total_operations": 0,
            "successful_operations": 0,
            "timed_out_operations": 0,
            "average_duration": 0.0,
            "timeout_rate": 0.0,
            "performance_improvement": 0.0,
        }

        # Create workspace directory for timeout tracking
        if session_id:
            self.workspace_dir = Path(f".khive/workspace/{session_id}")
            self.workspace_dir.mkdir(parents=True, exist_ok=True)
            self.metrics_file = self.workspace_dir / "timeout_metrics.json"
        else:
            self.workspace_dir = None
            self.metrics_file = None

    async def execute_with_timeout(
        self,
        operation_id: str,
        timeout_type: TimeoutType,
        operation: Callable[..., Any],
        *args,
        **kwargs,
    ) -> TimeoutResult:
        """
        Execute an operation with timeout handling.

        Args:
            operation_id: Unique identifier for the operation
            timeout_type: Type of timeout to apply
            operation: Callable to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            TimeoutResult with operation outcome
        """
        timeout_value = self._get_timeout_value(timeout_type)
        result = TimeoutResult(
            operation_id=operation_id,
            timeout_type=timeout_type,
            status=TimeoutStatus.PENDING,
            start_time=TimePolicy.now_utc(),
        )

        self._active_operations[operation_id] = result

        try:
            result.status = TimeoutStatus.IN_PROGRESS

            # Execute with timeout
            task = asyncio.create_task(
                self._execute_operation(operation, *args, **kwargs)
            )
            self._operation_tasks[operation_id] = task

            try:
                await asyncio.wait_for(task, timeout=timeout_value)
                result.mark_completed()
                logger.info(
                    f"Operation {operation_id} completed successfully in {result.duration:.2f}s"
                )

            except asyncio.TimeoutError:
                task.cancel()
                error_msg = f"Operation {operation_id} timed out after {timeout_value}s"
                result.mark_timed_out(error_msg)
                logger.warning(error_msg)

                # Try retry logic if enabled
                if self.config.max_retries > 0:
                    retry_result = await self._retry_operation(
                        operation_id, timeout_type, operation, *args, **kwargs
                    )
                    if retry_result.status == TimeoutStatus.COMPLETED:
                        result = retry_result

        except Exception as e:
            error_msg = f"Operation {operation_id} failed: {e!s}"
            result.mark_error(error_msg)
            logger.error(error_msg, exc_info=True)

        finally:
            # Clean up
            self._active_operations.pop(operation_id, None)
            self._operation_tasks.pop(operation_id, None)

            # Update metrics
            await self._update_metrics(result)

        return result

    async def _execute_operation(
        self, operation: Callable[..., Any], *args, **kwargs
    ) -> Any:
        """Execute the operation, handling both sync and async callables."""
        if asyncio.iscoroutinefunction(operation):
            return await operation(*args, **kwargs)
        return operation(*args, **kwargs)

    async def _retry_operation(
        self,
        operation_id: str,
        timeout_type: TimeoutType,
        operation: Callable[..., Any],
        *args,
        **kwargs,
    ) -> TimeoutResult:
        """Retry an operation with exponential backoff."""
        for retry in range(self.config.max_retries):
            retry_id = f"{operation_id}_retry_{retry + 1}"

            # Wait before retry
            await asyncio.sleep(self.config.retry_delay * (2**retry))

            logger.info(
                f"Retrying operation {operation_id} (attempt {retry + 1}/{self.config.max_retries})"
            )

            result = await self.execute_with_timeout(
                retry_id, timeout_type, operation, *args, **kwargs
            )

            if result.status == TimeoutStatus.COMPLETED:
                result.operation_id = operation_id  # Keep original ID
                result.retry_count = retry + 1
                return result

        # All retries failed
        final_result = TimeoutResult(
            operation_id=operation_id,
            timeout_type=timeout_type,
            status=TimeoutStatus.TIMED_OUT,
            start_time=TimePolicy.now_utc(),
            retry_count=self.config.max_retries,
        )
        final_result.mark_timed_out(
            f"Operation failed after {self.config.max_retries} retries"
        )
        return final_result

    def _get_timeout_value(self, timeout_type: TimeoutType) -> float:
        """Get timeout value for the specified type."""
        timeout_mapping = {
            TimeoutType.AGENT_EXECUTION: self.config.agent_execution_timeout,
            TimeoutType.PHASE_COMPLETION: self.config.phase_completion_timeout,
            TimeoutType.TOTAL_ORCHESTRATION: self.config.total_orchestration_timeout,
            TimeoutType.RESPONSE_TIMEOUT: self.config.response_timeout,
            TimeoutType.HANDOFF_TIMEOUT: self.config.handoff_timeout,
        }
        return timeout_mapping.get(timeout_type, self.config.agent_execution_timeout)

    async def _update_metrics(self, result: TimeoutResult) -> None:
        """Update performance metrics."""
        metrics = self._performance_metrics

        metrics["total_operations"] += 1

        if result.status == TimeoutStatus.COMPLETED:
            metrics["successful_operations"] += 1
        elif result.status == TimeoutStatus.TIMED_OUT:
            metrics["timed_out_operations"] += 1

        # Update timeout rate
        if metrics["total_operations"] > 0:
            metrics["timeout_rate"] = (
                metrics["timed_out_operations"] / metrics["total_operations"]
            )

        # Update average duration
        if result.duration and result.status == TimeoutStatus.COMPLETED:
            current_avg = metrics["average_duration"]
            successful_ops = metrics["successful_operations"]

            if successful_ops > 1:
                metrics["average_duration"] = (
                    (current_avg * (successful_ops - 1)) + result.duration
                ) / successful_ops
            else:
                metrics["average_duration"] = result.duration

        # Calculate performance improvement
        if metrics["total_operations"] > 0:
            success_rate = (
                metrics["successful_operations"] / metrics["total_operations"]
            )
            target_improvement = self.config.timeout_reduction_factor

            if success_rate >= self.config.performance_threshold:
                metrics["performance_improvement"] = min(
                    target_improvement, success_rate - 0.5
                )
            else:
                metrics["performance_improvement"] = 0.0

        # Save metrics to file
        if self.metrics_file:
            await self._save_metrics()

    async def _save_metrics(self) -> None:
        """Save metrics to file."""
        if not self.metrics_file:
            return

        metrics_data = {
            "session_id": self.session_id,
            "timestamp": TimePolicy.now_utc().isoformat(),
            "config": self.config.to_dict(),
            "metrics": self._performance_metrics,
            "active_operations": len(self._active_operations),
        }

        try:
            async with aiofiles.open(self.metrics_file, "w") as f:
                await f.write(json.dumps(metrics_data, indent=2))
        except Exception as e:
            logger.exception(f"Failed to save metrics: {e}")

    async def get_performance_metrics(self) -> dict[str, Any]:
        """Get current performance metrics."""
        return self._performance_metrics.copy()

    async def cancel_operation(self, operation_id: str) -> bool:
        """Cancel a running operation."""
        if operation_id in self._operation_tasks:
            task = self._operation_tasks[operation_id]
            task.cancel()

            if operation_id in self._active_operations:
                result = self._active_operations[operation_id]
                result.status = TimeoutStatus.CANCELLED
                result.mark_error("Operation cancelled")

            return True
        return False

    async def cancel_all_operations(self) -> int:
        """Cancel all running operations."""
        cancelled_count = 0

        for operation_id in list(self._operation_tasks.keys()):
            if await self.cancel_operation(operation_id):
                cancelled_count += 1

        return cancelled_count

    def get_active_operations(self) -> list[str]:
        """Get list of active operation IDs."""
        return list(self._active_operations.keys())

    def is_operation_active(self, operation_id: str) -> bool:
        """Check if an operation is currently active."""
        return operation_id in self._active_operations

    async def cleanup(self) -> None:
        """Clean up resources and save final metrics."""
        # Cancel all active operations
        await self.cancel_all_operations()

        # Save final metrics
        if self.metrics_file:
            await self._save_metrics()

        # Clear internal state
        self._active_operations.clear()
        self._operation_tasks.clear()


# Factory function for creating timeout manager
def create_timeout_manager(
    session_id: str | None = None, **config_kwargs
) -> TimeoutManager:
    """
    Create a timeout manager with custom configuration.

    Args:
        session_id: Session ID for tracking
        **config_kwargs: Configuration parameters

    Returns:
        Configured TimeoutManager instance
    """
    config = TimeoutConfig(**config_kwargs)
    return TimeoutManager(config=config, session_id=session_id)


# Utility functions for common timeout operations
async def timeout_agent_execution(
    operation_id: str,
    agent_task: Callable[..., Any],
    timeout_manager: TimeoutManager,
    *args,
    **kwargs,
) -> TimeoutResult:
    """Execute an agent task with timeout handling."""
    return await timeout_manager.execute_with_timeout(
        operation_id,
        TimeoutType.AGENT_EXECUTION,
        agent_task,
        *args,
        **kwargs,
    )


async def timeout_phase_completion(
    phase_name: str,
    phase_task: Callable[..., Any],
    timeout_manager: TimeoutManager,
    *args,
    **kwargs,
) -> TimeoutResult:
    """Execute a phase task with timeout handling."""
    return await timeout_manager.execute_with_timeout(
        f"phase_{phase_name}",
        TimeoutType.PHASE_COMPLETION,
        phase_task,
        *args,
        **kwargs,
    )
