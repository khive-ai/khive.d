"""Comprehensive tests for timeout management and async execution patterns."""

import asyncio
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from khive.services.artifacts.handlers.timeout_manager import (
    TimeoutConfig, TimeoutManager, TimeoutResult, TimeoutStatus, TimeoutType,
    create_timeout_manager, timeout_agent_execution, timeout_phase_completion)
from khive.services.plan.planner_service import OrchestrationPlanner


@pytest.mark.unit
class TestTimeoutConfig:
    """Test TimeoutConfig functionality."""

    def test_timeout_config_defaults(self):
        """Test default timeout configuration values."""
        config = TimeoutConfig()

        assert config.agent_execution_timeout == 300.0
        assert config.phase_completion_timeout == 1800.0
        assert config.total_orchestration_timeout == 3600.0
        assert config.response_timeout == 60.0
        assert config.handoff_timeout == 30.0
        assert config.max_retries == 3
        assert config.retry_delay == 5.0
        assert config.escalation_enabled is True
        assert config.performance_threshold == 0.7
        assert config.timeout_reduction_factor == 0.3

    def test_timeout_config_custom_values(self):
        """Test timeout configuration with custom values."""
        config = TimeoutConfig(
            agent_execution_timeout=600.0,
            max_retries=5,
            performance_threshold=0.9,
        )

        assert config.agent_execution_timeout == 600.0
        assert config.max_retries == 5
        assert config.performance_threshold == 0.9
        # Other values should still be defaults
        assert config.phase_completion_timeout == 1800.0

    def test_timeout_config_serialization(self):
        """Test timeout configuration serialization."""
        config = TimeoutConfig(agent_execution_timeout=600.0, max_retries=5)
        data = config.to_dict()

        assert isinstance(data, dict)
        assert data["agent_execution_timeout"] == 600.0
        assert data["max_retries"] == 5
        assert data["escalation_enabled"] is True

    @pytest.mark.parametrize(
        "timeout_type,expected_timeout",
        [
            (TimeoutType.AGENT_EXECUTION, 300.0),
            (TimeoutType.PHASE_COMPLETION, 1800.0),
            (TimeoutType.TOTAL_ORCHESTRATION, 3600.0),
            (TimeoutType.RESPONSE_TIMEOUT, 60.0),
            (TimeoutType.HANDOFF_TIMEOUT, 30.0),
        ],
    )
    def test_timeout_type_mapping(self, timeout_type, expected_timeout):
        """Test timeout type to value mapping."""
        config = TimeoutConfig()
        manager = TimeoutManager(config)

        timeout_value = manager._get_timeout_value(timeout_type)
        assert timeout_value == expected_timeout


@pytest.mark.unit
class TestTimeoutResult:
    """Test TimeoutResult functionality."""

    def test_timeout_result_creation(self):
        """Test TimeoutResult creation and initial state."""
        from khive.core import TimePolicy

        start_time = TimePolicy.now_utc()
        result = TimeoutResult(
            operation_id="test_op_001",
            timeout_type=TimeoutType.AGENT_EXECUTION,
            status=TimeoutStatus.PENDING,
            start_time=start_time,
        )

        assert result.operation_id == "test_op_001"
        assert result.timeout_type == TimeoutType.AGENT_EXECUTION
        assert result.status == TimeoutStatus.PENDING
        assert result.start_time == start_time
        assert result.end_time is None
        assert result.duration is None
        assert result.error is None
        assert result.retry_count == 0

    def test_timeout_result_mark_completed(self):
        """Test marking timeout result as completed."""
        from khive.core import TimePolicy

        result = TimeoutResult(
            operation_id="test_op",
            timeout_type=TimeoutType.AGENT_EXECUTION,
            status=TimeoutStatus.IN_PROGRESS,
            start_time=TimePolicy.now_utc(),
        )

        # Wait a small amount to get measurable duration
        time.sleep(0.01)
        result.mark_completed()

        assert result.status == TimeoutStatus.COMPLETED
        assert result.end_time is not None
        assert result.duration is not None
        assert result.duration > 0
        assert result.error is None

    def test_timeout_result_mark_timed_out(self):
        """Test marking timeout result as timed out."""
        from khive.core import TimePolicy

        result = TimeoutResult(
            operation_id="test_op",
            timeout_type=TimeoutType.AGENT_EXECUTION,
            status=TimeoutStatus.IN_PROGRESS,
            start_time=TimePolicy.now_utc(),
        )

        error_msg = "Operation timed out after 300s"
        result.mark_timed_out(error_msg)

        assert result.status == TimeoutStatus.TIMED_OUT
        assert result.end_time is not None
        assert result.duration is not None
        assert result.error == error_msg

    def test_timeout_result_mark_error(self):
        """Test marking timeout result with error."""
        from khive.core import TimePolicy

        result = TimeoutResult(
            operation_id="test_op",
            timeout_type=TimeoutType.AGENT_EXECUTION,
            status=TimeoutStatus.IN_PROGRESS,
            start_time=TimePolicy.now_utc(),
        )

        error_msg = "Operation failed with exception"
        result.mark_error(error_msg)

        assert result.status == TimeoutStatus.ERROR
        assert result.end_time is not None
        assert result.duration is not None
        assert result.error == error_msg

    def test_timeout_result_serialization(self):
        """Test TimeoutResult serialization."""
        from khive.core import TimePolicy

        result = TimeoutResult(
            operation_id="test_op",
            timeout_type=TimeoutType.AGENT_EXECUTION,
            status=TimeoutStatus.COMPLETED,
            start_time=TimePolicy.now_utc(),
            retry_count=2,
        )
        result.mark_completed()

        data = result.to_dict()

        assert isinstance(data, dict)
        assert data["operation_id"] == "test_op"
        assert data["timeout_type"] == "agent_execution"
        assert data["status"] == "completed"
        assert data["retry_count"] == 2
        assert "start_time" in data
        assert "end_time" in data
        assert "duration" in data


@pytest.mark.unit
class TestTimeoutManager:
    """Test TimeoutManager functionality."""

    @pytest.fixture
    def timeout_manager(self, tmp_path):
        """Create timeout manager for testing."""
        config = TimeoutConfig(
            agent_execution_timeout=1.0,  # Short timeout for testing
            max_retries=2,
            retry_delay=0.1,  # Short delay for testing
        )
        session_id = "test_session_123"

        # Create manager with temporary workspace
        manager = TimeoutManager(config, session_id)
        manager.workspace_dir = tmp_path / ".khive" / "workspace" / session_id
        manager.workspace_dir.mkdir(parents=True, exist_ok=True)
        manager.metrics_file = manager.workspace_dir / "timeout_metrics.json"

        return manager

    @pytest.mark.asyncio
    async def test_successful_operation_execution(self, timeout_manager):
        """Test successful operation execution within timeout."""

        async def fast_operation():
            await asyncio.sleep(0.05)  # Fast operation
            return "success"

        result = await timeout_manager.execute_with_timeout(
            "test_op_001",
            TimeoutType.AGENT_EXECUTION,
            fast_operation,
        )

        assert result.status == TimeoutStatus.COMPLETED
        assert result.operation_id == "test_op_001"
        assert result.timeout_type == TimeoutType.AGENT_EXECUTION
        assert result.duration is not None
        assert result.duration < 1.0  # Should be much faster than timeout
        assert result.error is None
        assert result.retry_count == 0

    @pytest.mark.asyncio
    async def test_operation_timeout(self, timeout_manager):
        """Test operation timing out."""

        async def slow_operation():
            await asyncio.sleep(2.0)  # Longer than timeout
            return "too slow"

        result = await timeout_manager.execute_with_timeout(
            "test_op_002",
            TimeoutType.AGENT_EXECUTION,
            slow_operation,
        )

        assert result.status == TimeoutStatus.TIMED_OUT
        assert result.operation_id == "test_op_002"
        assert result.error is not None
        assert "timed out" in result.error.lower()
        assert result.duration is not None
        assert result.duration >= 1.0  # Should be at least the timeout

    @pytest.mark.asyncio
    async def test_operation_exception(self, timeout_manager):
        """Test operation raising exception."""

        async def failing_operation():
            raise ValueError("Test error")

        result = await timeout_manager.execute_with_timeout(
            "test_op_003",
            TimeoutType.AGENT_EXECUTION,
            failing_operation,
        )

        assert result.status == TimeoutStatus.ERROR
        assert result.operation_id == "test_op_003"
        assert result.error is not None
        assert "Test error" in result.error

    @pytest.mark.asyncio
    async def test_sync_operation_execution(self, timeout_manager):
        """Test execution of synchronous operations."""

        def sync_operation(value):
            time.sleep(0.05)  # Small delay
            return f"processed_{value}"

        result = await timeout_manager.execute_with_timeout(
            "test_sync_001",
            TimeoutType.AGENT_EXECUTION,
            sync_operation,
            "test_input",
        )

        assert result.status == TimeoutStatus.COMPLETED
        assert result.operation_id == "test_sync_001"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_retry_logic_success(self, timeout_manager):
        """Test retry logic with eventual success."""
        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                await asyncio.sleep(2.0)  # First call times out
            else:
                await asyncio.sleep(0.05)  # Second call succeeds
            return "success"

        result = await timeout_manager.execute_with_timeout(
            "test_retry_001",
            TimeoutType.AGENT_EXECUTION,
            flaky_operation,
        )

        assert result.status == TimeoutStatus.COMPLETED
        assert result.retry_count == 1  # One retry
        assert call_count == 2  # Called twice

    @pytest.mark.asyncio
    async def test_retry_logic_all_fail(self, timeout_manager):
        """Test retry logic when all attempts fail."""
        call_count = 0

        async def always_slow_operation():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(2.0)  # Always times out
            return "never reached"

        result = await timeout_manager.execute_with_timeout(
            "test_retry_002",
            TimeoutType.AGENT_EXECUTION,
            always_slow_operation,
        )

        assert result.status == TimeoutStatus.TIMED_OUT
        assert result.retry_count == 2  # max_retries
        assert call_count == 3  # Initial + 2 retries
        assert "retries" in result.error.lower()

    @pytest.mark.asyncio
    async def test_active_operation_management(self, timeout_manager):
        """Test active operation tracking and cleanup."""
        # Initially no active operations
        assert len(timeout_manager.get_active_operations()) == 0
        assert not timeout_manager.is_operation_active("test_op")

        # Start a long-running operation
        async def long_operation():
            await asyncio.sleep(0.5)
            return "done"

        # Start operation in background
        task = asyncio.create_task(
            timeout_manager.execute_with_timeout(
                "test_long_op",
                TimeoutType.AGENT_EXECUTION,
                long_operation,
            )
        )

        # Give it time to start
        await asyncio.sleep(0.05)

        # Should be active now
        assert timeout_manager.is_operation_active("test_long_op")
        assert "test_long_op" in timeout_manager.get_active_operations()

        # Wait for completion
        result = await task

        # Should be cleaned up
        assert not timeout_manager.is_operation_active("test_long_op")
        assert len(timeout_manager.get_active_operations()) == 0
        assert result.status == TimeoutStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_operation_cancellation(self, timeout_manager):
        """Test operation cancellation."""

        async def long_operation():
            await asyncio.sleep(2.0)
            return "never reached"

        # Start operation
        task = asyncio.create_task(
            timeout_manager.execute_with_timeout(
                "test_cancel_op",
                TimeoutType.AGENT_EXECUTION,
                long_operation,
            )
        )

        # Give it time to start
        await asyncio.sleep(0.05)
        assert timeout_manager.is_operation_active("test_cancel_op")

        # Cancel it
        cancelled = await timeout_manager.cancel_operation("test_cancel_op")
        assert cancelled is True

        # Wait for task to complete (should be cancelled)
        result = await task
        assert result.status == TimeoutStatus.ERROR
        assert "cancelled" in result.error.lower()

    @pytest.mark.asyncio
    async def test_cancel_all_operations(self, timeout_manager):
        """Test cancelling all active operations."""

        async def long_operation(op_id):
            await asyncio.sleep(2.0)
            return f"done_{op_id}"

        # Start multiple operations
        tasks = []
        for i in range(3):
            op_id = f"test_cancel_all_{i}"
            task = asyncio.create_task(
                timeout_manager.execute_with_timeout(
                    op_id,
                    TimeoutType.AGENT_EXECUTION,
                    long_operation,
                    op_id,
                )
            )
            tasks.append(task)

        # Give them time to start
        await asyncio.sleep(0.05)
        assert len(timeout_manager.get_active_operations()) == 3

        # Cancel all
        cancelled_count = await timeout_manager.cancel_all_operations()
        assert cancelled_count == 3

        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should be in error/cancelled state
        for result in results:
            if isinstance(result, TimeoutResult):
                assert result.status == TimeoutStatus.ERROR

    @pytest.mark.asyncio
    async def test_performance_metrics_tracking(self, timeout_manager):
        """Test performance metrics calculation and tracking."""
        # Initial metrics
        initial_metrics = await timeout_manager.get_performance_metrics()
        assert initial_metrics["total_operations"] == 0
        assert initial_metrics["successful_operations"] == 0
        assert initial_metrics["timeout_rate"] == 0.0

        # Execute successful operation
        async def fast_op():
            await asyncio.sleep(0.05)
            return "success"

        result = await timeout_manager.execute_with_timeout(
            "metrics_test_001",
            TimeoutType.AGENT_EXECUTION,
            fast_op,
        )

        # Check metrics updated
        metrics = await timeout_manager.get_performance_metrics()
        assert metrics["total_operations"] == 1
        assert metrics["successful_operations"] == 1
        assert metrics["timeout_rate"] == 0.0
        assert metrics["average_duration"] > 0

        # Execute failing operation
        async def slow_op():
            await asyncio.sleep(2.0)
            return "too slow"

        await timeout_manager.execute_with_timeout(
            "metrics_test_002",
            TimeoutType.AGENT_EXECUTION,
            slow_op,
        )

        # Check metrics updated with timeout
        final_metrics = await timeout_manager.get_performance_metrics()
        assert final_metrics["total_operations"] == 2
        assert final_metrics["successful_operations"] == 1
        assert final_metrics["timed_out_operations"] == 1
        assert final_metrics["timeout_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_metrics_file_persistence(self, timeout_manager):
        """Test metrics persistence to file."""

        # Execute operation to generate metrics
        async def test_op():
            await asyncio.sleep(0.05)
            return "done"

        await timeout_manager.execute_with_timeout(
            "persistence_test",
            TimeoutType.AGENT_EXECUTION,
            test_op,
        )

        # Check metrics file exists and contains data
        assert timeout_manager.metrics_file.exists()

        with open(timeout_manager.metrics_file) as f:
            metrics_data = json.load(f)

        assert metrics_data["session_id"] == "test_session_123"
        assert "timestamp" in metrics_data
        assert "config" in metrics_data
        assert "metrics" in metrics_data
        assert metrics_data["metrics"]["total_operations"] == 1

    @pytest.mark.asyncio
    async def test_cleanup(self, timeout_manager):
        """Test timeout manager cleanup."""

        # Start some operations
        async def test_op():
            await asyncio.sleep(1.0)
            return "done"

        tasks = []
        for i in range(2):
            task = asyncio.create_task(
                timeout_manager.execute_with_timeout(
                    f"cleanup_test_{i}",
                    TimeoutType.AGENT_EXECUTION,
                    test_op,
                )
            )
            tasks.append(task)

        # Give them time to start
        await asyncio.sleep(0.05)
        assert len(timeout_manager.get_active_operations()) == 2

        # Cleanup should cancel all operations
        await timeout_manager.cleanup()

        assert len(timeout_manager.get_active_operations()) == 0
        assert len(timeout_manager._operation_tasks) == 0

        # Metrics file should exist with final metrics
        if timeout_manager.metrics_file:
            assert timeout_manager.metrics_file.exists()


@pytest.mark.unit
class TestTimeoutManagerFactory:
    """Test timeout manager factory functions."""

    def test_create_timeout_manager_defaults(self):
        """Test creating timeout manager with defaults."""
        manager = create_timeout_manager()

        assert isinstance(manager, TimeoutManager)
        assert manager.config.agent_execution_timeout == 300.0
        assert manager.session_id is None

    def test_create_timeout_manager_custom(self):
        """Test creating timeout manager with custom config."""
        manager = create_timeout_manager(
            session_id="custom_session",
            agent_execution_timeout=600.0,
            max_retries=5,
        )

        assert isinstance(manager, TimeoutManager)
        assert manager.session_id == "custom_session"
        assert manager.config.agent_execution_timeout == 600.0
        assert manager.config.max_retries == 5

    @pytest.mark.asyncio
    async def test_utility_functions(self, tmp_path):
        """Test utility functions for common timeout operations."""
        manager = create_timeout_manager(
            session_id="utility_test",
            agent_execution_timeout=1.0,
        )
        manager.workspace_dir = tmp_path / "test_workspace"
        manager.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Test agent execution utility
        async def test_agent():
            await asyncio.sleep(0.05)
            return "agent_result"

        result = await timeout_agent_execution(
            "agent_001",
            test_agent,
            manager,
        )

        assert result.status == TimeoutStatus.COMPLETED
        assert result.timeout_type == TimeoutType.AGENT_EXECUTION

        # Test phase completion utility
        async def test_phase():
            await asyncio.sleep(0.05)
            return "phase_result"

        result = await timeout_phase_completion(
            "discovery",
            test_phase,
            manager,
        )

        assert result.status == TimeoutStatus.COMPLETED
        assert result.timeout_type == TimeoutType.PHASE_COMPLETION
        assert result.operation_id == "phase_discovery"


@pytest.mark.integration
class TestOrchestrationPlannerTimeoutIntegration:
    """Test timeout manager integration with OrchestrationPlanner."""

    @pytest.fixture
    def mock_planner(self, tmp_path):
        """Create mock planner with timeout integration."""
        with patch.multiple(
            OrchestrationPlanner,
            _load_available_roles=MagicMock(return_value=["researcher", "implementer"]),
            _load_available_domains=MagicMock(return_value=["distributed-systems"]),
            _load_prompt_templates=MagicMock(return_value={"agents": {}}),
            _load_decision_matrix=MagicMock(return_value={"complexity_assessment": {}}),
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                planner = OrchestrationPlanner()
                planner.workspace_dir = tmp_path
                return planner

    @pytest.mark.asyncio
    async def test_planner_timeout_manager_creation(self, mock_planner):
        """Test planner creates timeout manager correctly."""
        session_id = "test_session_timeout"

        # Create session
        planner_session_id = mock_planner.create_session("Test task", session_id)
        assert planner_session_id == session_id

        # Get timeout manager
        timeout_manager = mock_planner._get_timeout_manager(session_id)

        assert timeout_manager is not None
        assert timeout_manager.session_id == session_id
        assert isinstance(timeout_manager.config, TimeoutConfig)

    @pytest.mark.asyncio
    async def test_agent_execution_with_timeout(self, mock_planner):
        """Test agent execution through planner timeout system."""
        session_id = "test_agent_timeout"
        mock_planner.create_session("Test task", session_id)

        # Mock agent task
        async def mock_agent_task():
            await asyncio.sleep(0.05)
            return {"result": "agent_completed", "status": "success"}

        # Execute with timeout
        result = await mock_planner.execute_agent_with_timeout(
            "test_agent_001",
            mock_agent_task,
            TimeoutType.AGENT_EXECUTION,
        )

        assert result["agent_id"] == "test_agent_001"
        assert result["status"] == TimeoutStatus.COMPLETED
        assert result["duration"] is not None
        assert result["retry_count"] == 0
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_parallel_agent_execution(self, mock_planner):
        """Test parallel agent execution with timeout management."""
        session_id = "test_parallel_timeout"
        mock_planner.create_session("Test task", session_id)

        # Mock multiple agent tasks
        async def fast_agent(agent_id):
            await asyncio.sleep(0.05)
            return f"result_{agent_id}"

        async def slow_agent(agent_id):
            await asyncio.sleep(0.1)
            return f"result_{agent_id}"

        agent_tasks = [
            ("agent_001", lambda: fast_agent("001")),
            ("agent_002", lambda: slow_agent("002")),
            ("agent_003", lambda: fast_agent("003")),
        ]

        # Execute in parallel
        results = await mock_planner.execute_agents_parallel(
            agent_tasks,
            TimeoutType.AGENT_EXECUTION,
        )

        assert len(results) == 3

        # All should have completed successfully
        for result in results:
            assert result["status"] == TimeoutStatus.COMPLETED
            assert result["agent_id"] in ["agent_001", "agent_002", "agent_003"]
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_timeout_metrics_retrieval(self, mock_planner):
        """Test timeout metrics retrieval from planner."""
        session_id = "test_metrics_timeout"
        mock_planner.create_session("Test task", session_id)

        # Execute some operations to generate metrics
        async def test_operation():
            await asyncio.sleep(0.05)
            return "completed"

        await mock_planner.execute_agent_with_timeout(
            "metrics_agent_001",
            test_operation,
        )

        # Get metrics
        metrics = await mock_planner.get_timeout_metrics()

        assert "total_operations" in metrics
        assert "successful_operations" in metrics
        assert "timeout_rate" in metrics
        assert metrics["total_operations"] >= 1

    @pytest.mark.asyncio
    async def test_planner_cleanup(self, mock_planner):
        """Test planner cleanup includes timeout manager cleanup."""
        session_id = "test_cleanup_timeout"
        mock_planner.create_session("Test task", session_id)

        # Start some operations
        async def long_operation():
            await asyncio.sleep(1.0)
            return "done"

        # Start but don't await
        asyncio.create_task(
            mock_planner.execute_agent_with_timeout(
                "cleanup_agent_001",
                long_operation,
            )
        )

        # Give it time to start
        await asyncio.sleep(0.05)

        # Cleanup should handle active operations
        await mock_planner.cleanup()

        # Timeout manager should be cleaned up
        assert (
            mock_planner.timeout_manager is None
            or len(mock_planner.timeout_manager.get_active_operations()) == 0
        )


@pytest.mark.performance
class TestTimeoutManagerPerformance:
    """Performance tests for timeout manager."""

    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self):
        """Test timeout manager performance with many concurrent operations."""
        config = TimeoutConfig(
            agent_execution_timeout=2.0,
            max_retries=1,
            retry_delay=0.1,
        )
        manager = TimeoutManager(config)

        async def test_operation(op_id):
            await asyncio.sleep(0.01)  # Simulate work
            return f"result_{op_id}"

        # Start many concurrent operations
        start_time = time.time()
        tasks = []
        num_operations = 100

        for i in range(num_operations):
            task = asyncio.create_task(
                manager.execute_with_timeout(
                    f"perf_op_{i}",
                    TimeoutType.AGENT_EXECUTION,
                    test_operation,
                    i,
                )
            )
            tasks.append(task)

        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # Performance assertions
        total_time = end_time - start_time
        assert total_time < 5.0  # Should complete in reasonable time
        assert len(results) == num_operations

        # All should be successful
        successful = [r for r in results if r.status == TimeoutStatus.COMPLETED]
        assert len(successful) == num_operations

    @pytest.mark.asyncio
    async def test_timeout_detection_accuracy(self):
        """Test accuracy of timeout detection."""
        config = TimeoutConfig(
            agent_execution_timeout=0.5,  # 500ms timeout
            max_retries=0,  # No retries for accurate timing
        )
        manager = TimeoutManager(config)

        async def precise_slow_operation():
            await asyncio.sleep(0.8)  # 800ms - should timeout
            return "too slow"

        start_time = time.time()
        result = await manager.execute_with_timeout(
            "timeout_accuracy_test",
            TimeoutType.AGENT_EXECUTION,
            precise_slow_operation,
        )
        end_time = time.time()

        # Should have timed out
        assert result.status == TimeoutStatus.TIMED_OUT

        # Timing should be reasonably accurate (within 100ms of expected)
        actual_duration = end_time - start_time
        expected_duration = 0.5
        assert abs(actual_duration - expected_duration) < 0.1

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self):
        """Test that timeout manager doesn't leak memory."""
        import gc

        config = TimeoutConfig(agent_execution_timeout=0.1, max_retries=0)
        manager = TimeoutManager(config)

        async def quick_operation():
            await asyncio.sleep(0.01)
            return "done"

        # Get initial memory usage
        gc.collect()
        initial_refs = len(gc.get_objects())

        # Run many operations
        for i in range(100):
            await manager.execute_with_timeout(
                f"memory_test_{i}",
                TimeoutType.AGENT_EXECUTION,
                quick_operation,
            )

        # Check memory usage hasn't grown significantly
        gc.collect()
        final_refs = len(gc.get_objects())

        # Allow some growth but not proportional to number of operations
        ref_growth = final_refs - initial_refs
        assert ref_growth < 500  # Should not grow by 100 objects per operation

    @pytest.mark.asyncio
    async def test_retry_performance_overhead(self):
        """Test performance overhead of retry logic."""
        config = TimeoutConfig(
            agent_execution_timeout=0.1,
            max_retries=3,
            retry_delay=0.01,  # Minimal delay for testing
        )
        manager = TimeoutManager(config)

        # Test with operation that always times out
        async def always_timeout():
            await asyncio.sleep(0.5)  # Will always timeout
            return "never reached"

        start_time = time.time()
        result = await manager.execute_with_timeout(
            "retry_overhead_test",
            TimeoutType.AGENT_EXECUTION,
            always_timeout,
        )
        end_time = time.time()

        # Should have tried 4 times (initial + 3 retries)
        assert result.retry_count == 3
        assert result.status == TimeoutStatus.TIMED_OUT

        # Total time should be reasonable
        # Expected: 4 * 0.1 (timeouts) + 3 * 0.01 (retry delays) = ~0.43s
        total_time = end_time - start_time
        assert 0.35 < total_time < 0.6  # Allow some variance


@pytest.mark.integration
class TestTimeoutIntegrationScenarios:
    """Integration tests for timeout system with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_agent_handoff_timeout_scenario(self):
        """Test realistic agent handoff timeout scenario."""
        config = TimeoutConfig(
            handoff_timeout=0.2,  # 200ms handoff timeout
            agent_execution_timeout=1.0,
            max_retries=1,
        )
        manager = TimeoutManager(config, "handoff_session")

        # Simulate agent handoff that takes too long
        async def slow_handoff():
            # Simulate slow inter-agent communication
            await asyncio.sleep(0.5)
            return {"handoff_data": "agent_context", "status": "transferred"}

        result = await manager.execute_with_timeout(
            "agent_handoff_001",
            TimeoutType.HANDOFF_TIMEOUT,
            slow_handoff,
        )

        # Should timeout due to slow handoff
        assert result.status == TimeoutStatus.TIMED_OUT
        assert result.timeout_type == TimeoutType.HANDOFF_TIMEOUT

    @pytest.mark.asyncio
    async def test_phase_completion_timeout_scenario(self):
        """Test realistic phase completion timeout scenario."""
        config = TimeoutConfig(
            phase_completion_timeout=0.3,  # 300ms phase timeout
            agent_execution_timeout=0.1,  # 100ms agent timeout
            max_retries=2,
        )
        manager = TimeoutManager(config, "phase_session")

        # Simulate phase with multiple agent calls
        async def discovery_phase():
            # Multiple quick agent calls within a phase
            results = []
            for i in range(3):
                await asyncio.sleep(0.05)  # Each agent call
                results.append(f"agent_{i}_result")

            # Phase processing
            await asyncio.sleep(0.05)
            return {"phase": "discovery", "results": results}

        result = await manager.execute_with_timeout(
            "discovery_phase_001",
            TimeoutType.PHASE_COMPLETION,
            discovery_phase,
        )

        # Should complete successfully within phase timeout
        assert result.status == TimeoutStatus.COMPLETED
        assert result.timeout_type == TimeoutType.PHASE_COMPLETION
        assert result.duration < 0.3

    @pytest.mark.asyncio
    async def test_orchestration_timeout_hierarchy(self):
        """Test timeout hierarchy in orchestration scenarios."""
        config = TimeoutConfig(
            agent_execution_timeout=0.1,  # Strictest
            phase_completion_timeout=0.3,  # Medium
            total_orchestration_timeout=0.5,  # Most lenient
        )
        manager = TimeoutManager(config, "orchestration_session")

        # Test that agent timeout is enforced first
        async def slow_agent():
            await asyncio.sleep(0.2)  # Exceeds agent timeout
            return "slow_agent_result"

        agent_result = await manager.execute_with_timeout(
            "slow_agent_001",
            TimeoutType.AGENT_EXECUTION,
            slow_agent,
        )
        assert agent_result.status == TimeoutStatus.TIMED_OUT

        # Test that phase timeout allows multiple quick agents
        async def multi_agent_phase():
            results = []
            for i in range(2):
                await asyncio.sleep(0.08)  # Just under agent timeout
                results.append(f"agent_{i}")
            return results

        phase_result = await manager.execute_with_timeout(
            "multi_agent_phase_001",
            TimeoutType.PHASE_COMPLETION,
            multi_agent_phase,
        )
        assert phase_result.status == TimeoutStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_error_recovery_with_timeouts(self):
        """Test error recovery scenarios with timeout management."""
        config = TimeoutConfig(
            agent_execution_timeout=0.2,
            max_retries=2,
            retry_delay=0.05,
        )
        manager = TimeoutManager(config, "recovery_session")

        call_count = 0

        async def flaky_agent():
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First call: timeout
                await asyncio.sleep(0.5)
                return "timeout_result"
            if call_count == 2:
                # Second call: exception
                raise RuntimeError("Temporary error")
            # Third call: success
            await asyncio.sleep(0.05)
            return "success_result"

        result = await manager.execute_with_timeout(
            "flaky_agent_001",
            TimeoutType.AGENT_EXECUTION,
            flaky_agent,
        )

        # Should eventually succeed after retries
        assert result.status == TimeoutStatus.COMPLETED
        assert result.retry_count > 0
        assert call_count == 3  # All retry attempts used

    @pytest.mark.asyncio
    async def test_resource_cleanup_under_load(self):
        """Test resource cleanup under high load conditions."""
        config = TimeoutConfig(
            agent_execution_timeout=0.1,
            max_retries=1,
            retry_delay=0.01,
        )
        manager = TimeoutManager(config, "cleanup_session")

        # Create many operations that will timeout
        async def timeout_operation(op_id):
            await asyncio.sleep(0.5)  # Always timeout
            return f"never_reached_{op_id}"

        # Start many operations
        tasks = []
        for i in range(20):
            task = asyncio.create_task(
                manager.execute_with_timeout(
                    f"cleanup_op_{i}",
                    TimeoutType.AGENT_EXECUTION,
                    timeout_operation,
                    i,
                )
            )
            tasks.append(task)

        # Wait for all to complete (timeout)
        results = await asyncio.gather(*tasks)

        # Verify cleanup
        assert len(manager.get_active_operations()) == 0
        assert len(manager._operation_tasks) == 0

        # All should have timed out
        timed_out_count = sum(1 for r in results if r.status == TimeoutStatus.TIMED_OUT)
        assert timed_out_count == 20

        # Memory should be cleaned up
        await manager.cleanup()
        assert len(manager._active_operations) == 0
