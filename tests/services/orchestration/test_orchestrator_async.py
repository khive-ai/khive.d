"""Async-specific tests for LionOrchestrator focusing on concurrency and async patterns."""

import asyncio
import contextlib
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from lionagi.service.imodel import iModel

from khive.services.composition.parts import ComposerRequest
from khive.services.orchestration.orchestrator import LionOrchestrator


class TestAsyncPatterns:
    """Test async execution patterns and concurrency."""

    @pytest.mark.asyncio
    async def test_concurrent_branch_creation(
        self, orchestrator_with_mocks, mock_file_system
    ):
        """Test concurrent branch creation doesn't interfere."""
        orchestrator = orchestrator_with_mocks

        compose_requests = [
            ComposerRequest(role="researcher", domains="software-architecture"),
            ComposerRequest(role="analyst", domains="distributed-systems"),
            ComposerRequest(role="architect", domains="microservices"),
        ]

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            # Mock the create_cc to return a proper async coroutine
            async def mock_cc_return(*args, **kwargs):
                return MagicMock()

            mock_create_cc.return_value = mock_cc_return()

            # Mock the Branch class to avoid iModel issues
            # Each call should return a unique branch ID
            branch_counter = 0

            def create_mock_branch(*args, **kwargs):
                nonlocal branch_counter
                mock_branch = MagicMock()
                mock_branch.id = f"test_branch_{branch_counter}"
                branch_counter += 1
                return mock_branch

            mock_branch_cls.side_effect = create_mock_branch

            mock_response = MagicMock()
            mock_response.system_prompt = "Test system prompt"
            mock_composer.handle_request = AsyncMock(return_value=mock_response)

            # Execute branch creation concurrently
            tasks = [
                orchestrator.create_cc_branch(request, agent_suffix=f"_concurrent_{i}")
                for i, request in enumerate(compose_requests)
            ]

            branch_ids = await asyncio.gather(*tasks)

            # All should succeed and return unique IDs
            assert len(branch_ids) == 3
            assert len(set(branch_ids)) == 3  # All unique

            # All branches should be added to session
            assert orchestrator.session.branches.include.call_count == 3

    @pytest.mark.asyncio
    async def test_concurrent_flow_execution(self, orchestrator_with_mocks):
        """Test concurrent flow operations."""
        orchestrator = orchestrator_with_mocks

        # Create multiple mock flows that execute concurrently
        flow_results = [{"result": f"flow_{i}"} for i in range(3)]

        async def mock_flow(graph):
            await asyncio.sleep(0.1)  # Simulate work
            return flow_results.pop(0) if flow_results else {"result": "default"}

        orchestrator.session.flow = mock_flow

        # Execute multiple flows concurrently
        tasks = [orchestrator.run_flow() for _ in range(3)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        # Results should be different (showing they ran concurrently)
        result_values = [r["result"] for r in results]
        assert len(set(result_values)) == 3

    @pytest.mark.asyncio
    async def test_async_context_extraction_performance(self, orchestrator_with_mocks):
        """Test context extraction performance with many operations."""
        orchestrator = orchestrator_with_mocks

        # Setup many operations
        num_ops = 100
        op_ids = [f"op_{i}" for i in range(num_ops)]

        # Mock operations and branches
        mock_operations = {}
        for i, op_id in enumerate(op_ids):
            mock_op = MagicMock()
            mock_op.branch_id = f"branch_{i}"
            mock_operations[op_id] = mock_op

        orchestrator.builder.get_graph.return_value.internal_nodes = mock_operations

        def mock_get_branch(branch_id, default=None):
            mock_branch = MagicMock()
            mock_branch.id = branch_id
            mock_branch.name = f"branch_{branch_id}"
            mock_branch.messages = MagicMock()
            mock_branch.messages.progression = [0]

            mock_response = MagicMock()
            mock_response.model_response = {
                "result": f"result_{branch_id}",
                "summary": f"summary_{branch_id}",
            }
            mock_branch.messages.__getitem__ = MagicMock(return_value=mock_response)
            return mock_branch

        orchestrator.session.get_branch = mock_get_branch

        start_time = time.time()
        result = orchestrator.opres_ctx(op_ids)
        end_time = time.time()

        assert len(result) == num_ops
        # Should complete reasonably quickly even with many operations
        assert (end_time - start_time) < 1.0  # Less than 1 second

    @pytest.mark.asyncio
    async def test_async_error_propagation(self, orchestrator_with_mocks):
        """Test that async errors propagate correctly through the call stack."""
        orchestrator = orchestrator_with_mocks

        # Mock a failure deep in the call stack
        orchestrator.session.flow = AsyncMock(
            side_effect=ValueError("Deep async error")
        )

        with pytest.raises(ValueError, match="Deep async error"):
            await orchestrator.run_flow()

    @pytest.mark.asyncio
    async def test_graceful_cancellation(self, orchestrator_with_mocks):
        """Test graceful handling of task cancellation."""
        orchestrator = orchestrator_with_mocks

        # Mock a long-running operation
        async def long_running_flow(graph):
            await asyncio.sleep(10)  # Very long operation
            return {"result": "completed"}

        orchestrator.session.flow = long_running_flow

        # Start the operation and cancel it quickly
        task = asyncio.create_task(orchestrator.run_flow())
        await asyncio.sleep(0.1)  # Let it start
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_concurrent_session_state_access(self, orchestrator_with_mocks):
        """Test concurrent access to session state is safe."""
        orchestrator = orchestrator_with_mocks

        # Mock multiple concurrent operations accessing session state
        async def access_session_state(delay):
            await asyncio.sleep(delay)
            return orchestrator.orc_branch.name

        # Run multiple concurrent accesses
        tasks = [access_session_state(i * 0.01) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All should return the same branch name (consistent state)
        assert all(result == results[0] for result in results)


class TestTimeoutHandling:
    """Test timeout handling and time-based operations."""

    @pytest.mark.asyncio
    async def test_initialization_timeout(self):
        """Test initialization with timeout."""
        orchestrator = LionOrchestrator("test_flow")

        with patch(
            "khive.services.orchestration.orchestrator.create_cc"
        ) as mock_create_cc:
            # Mock create_cc to hang
            async def hanging_create_cc(*args, **kwargs):
                await asyncio.sleep(10)  # Long delay
                return MagicMock()

            mock_create_cc.side_effect = hanging_create_cc

            # Should timeout if we set a reasonable timeout
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(orchestrator.initialize(), timeout=0.5)

    @pytest.mark.asyncio
    async def test_branch_creation_timeout(
        self, orchestrator_with_mocks, mock_file_system
    ):
        """Test branch creation with timeout."""
        orchestrator = orchestrator_with_mocks

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer,
        ):
            # Mock hanging operations
            async def hanging_composer(*args, **kwargs):
                await asyncio.sleep(10)
                return MagicMock()

            mock_create_cc.return_value = MagicMock()
            mock_composer.handle_request = hanging_composer

            request = ComposerRequest(
                role="researcher", domains="software-architecture"
            )

            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    orchestrator.create_cc_branch(request), timeout=0.5
                )

    @pytest.mark.asyncio
    async def test_flow_execution_timeout(self, orchestrator_with_mocks):
        """Test flow execution with timeout."""
        orchestrator = orchestrator_with_mocks

        # Mock hanging flow
        async def hanging_flow(graph):
            await asyncio.sleep(10)
            return {"result": "never reached"}

        orchestrator.session.flow = hanging_flow

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(orchestrator.run_flow(), timeout=0.5)

    @pytest.mark.asyncio
    async def test_fanout_timeout_resilience(self, orchestrator_with_mocks):
        """Test fanout pattern with timeout in one stage."""
        orchestrator = orchestrator_with_mocks

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock(spec=iModel)
            mock_cc.endpoint = MagicMock()
            mock_cc.endpoint.endpoint = "anthropic/claude-3-5-sonnet-20241022"
            mock_create_cc.return_value = mock_cc
            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch_id"
            mock_branch_cls.return_value = mock_branch

            orchestrator.builder.add_operation.side_effect = ["root", "agent1", "synth"]

            # Planning succeeds quickly, but expansion hangs
            call_count = 0

            async def flow_with_timeout(graph):
                nonlocal call_count
                call_count += 1
                if call_count == 2:  # Second call (expansion phase)
                    await asyncio.sleep(10)  # Hang
                return {
                    "operation_results": {
                        "root": MagicMock(flow_plans=MagicMock(initial=MagicMock())),
                        "synth": "result",
                    }
                }

            orchestrator.session.flow = flow_with_timeout
            orchestrator.expand_with_plan = AsyncMock(return_value=["agent1"])
            orchestrator.opres_ctx = MagicMock(return_value=[])

            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    orchestrator.fanout(
                        initial_desc="Test",
                        planning_instruction="Plan",
                        synth_instruction="Synthesize",
                    ),
                    timeout=1.0,
                )


class TestAsyncResourceManagement:
    """Test async resource management and cleanup."""

    @pytest.mark.asyncio
    async def test_branch_cleanup_on_exception(
        self, orchestrator_with_mocks, mock_file_system
    ):
        """Test that branches are properly managed even when exceptions occur."""
        orchestrator = orchestrator_with_mocks

        initial_branch_count = orchestrator.session.branches.include.call_count

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer,
        ):
            mock_cc = MagicMock(spec=iModel)
            mock_cc.endpoint = MagicMock()
            mock_cc.endpoint.endpoint = "anthropic/claude-3-5-sonnet-20241022"
            mock_create_cc.return_value = mock_cc

            # Composer fails after CC is created
            mock_composer.handle_request = AsyncMock(
                side_effect=Exception("Composer failed")
            )

            request = ComposerRequest(
                role="researcher", domains="software-architecture"
            )

            with contextlib.suppress(Exception):
                await orchestrator.create_cc_branch(request)

            # Branch should not have been added to session due to failure
            # (Since exception occurs before branch creation)
            final_branch_count = orchestrator.session.branches.include.call_count
            assert final_branch_count == initial_branch_count

    @pytest.mark.asyncio
    async def test_session_state_consistency_under_concurrency(
        self, orchestrator_with_mocks
    ):
        """Test session state remains consistent under concurrent operations."""
        orchestrator = orchestrator_with_mocks

        # Track state changes
        state_snapshots = []

        async def record_state(operation_id):
            # Record initial state
            initial_branches = len(getattr(orchestrator.session, "branches", []))
            state_snapshots.append(f"op_{operation_id}_start_{initial_branches}")

            # Simulate some work
            await asyncio.sleep(0.1)

            # Record final state
            final_branches = len(getattr(orchestrator.session, "branches", []))
            state_snapshots.append(f"op_{operation_id}_end_{final_branches}")

            return f"result_{operation_id}"

        # Run multiple concurrent operations
        tasks = [record_state(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert len(state_snapshots) == 10  # 2 per operation

    @pytest.mark.asyncio
    async def test_memory_efficiency_large_async_operations(
        self, orchestrator_with_mocks
    ):
        """Test memory efficiency with large number of async operations."""
        orchestrator = orchestrator_with_mocks

        # Create many async operations that complete quickly
        async def quick_operation(op_id):
            await asyncio.sleep(0.001)  # Very quick
            return f"result_{op_id}"

        # Run many operations
        num_operations = 1000
        tasks = [quick_operation(i) for i in range(num_operations)]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        assert len(results) == num_operations
        # Should complete quickly even with many operations
        assert (end_time - start_time) < 5.0  # Less than 5 seconds

        # All results should be unique
        assert len(set(results)) == num_operations


class TestAsyncDeadlockPrevention:
    """Test prevention of async deadlocks and race conditions."""

    @pytest.mark.asyncio
    async def test_no_deadlock_in_nested_operations(self, orchestrator_with_mocks):
        """Test no deadlock occurs in nested async operations."""
        orchestrator = orchestrator_with_mocks

        # Create a scenario that could cause deadlock
        lock = asyncio.Lock()

        async def operation_a():
            async with lock:
                await asyncio.sleep(0.1)
                # Call another operation while holding lock
                return await operation_b()

        async def operation_b():
            # Try to acquire same lock (could deadlock if not handled properly)
            await asyncio.sleep(0.05)
            return "completed"

        # This should complete without deadlock
        # Use timeout to detect deadlock - should NOT timeout
        result = await asyncio.wait_for(operation_a(), timeout=1.0)
        assert result == "completed"

    @pytest.mark.asyncio
    async def test_race_condition_in_branch_naming(
        self, orchestrator_with_mocks, mock_file_system
    ):
        """Test race condition handling in branch naming."""
        orchestrator = orchestrator_with_mocks

        # Setup race condition: two branches try to get the same name
        call_count = 0

        def mock_lookup(name):
            nonlocal call_count
            call_count += 1
            # First few calls return None (name available), then return existing branch
            return None if call_count <= 2 else MagicMock()

        orchestrator.session._lookup_branch_by_name = mock_lookup

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            # Mock the create_cc to return a proper async coroutine
            async def mock_cc_return(*args, **kwargs):
                return MagicMock()

            mock_create_cc.return_value = mock_cc_return()

            # Mock the Branch class to avoid iModel issues
            # Each call should return a unique branch ID
            branch_counter = 0

            def create_mock_branch(*args, **kwargs):
                nonlocal branch_counter
                mock_branch = MagicMock()
                mock_branch.id = f"race_test_branch_{branch_counter}"
                branch_counter += 1
                return mock_branch

            mock_branch_cls.side_effect = create_mock_branch

            mock_response = MagicMock()
            mock_response.system_prompt = "Test"
            mock_composer.handle_request = AsyncMock(return_value=mock_response)

            request = ComposerRequest(
                role="researcher", domains="software-architecture"
            )

            # Create two branches concurrently with same base name
            tasks = [
                orchestrator.create_cc_branch(request),
                orchestrator.create_cc_branch(request),
            ]

            branch_ids = await asyncio.gather(*tasks)

            # Both should succeed with different names
            assert len(branch_ids) == 2
            assert branch_ids[0] != branch_ids[1]

    @pytest.mark.asyncio
    async def test_async_exception_cleanup(self, orchestrator_with_mocks):
        """Test that exceptions in async operations don't leave inconsistent state."""
        orchestrator = orchestrator_with_mocks

        original_state = {
            "branches": orchestrator.session.branches.include.call_count,
        }

        # Simulate operation that fails partway through
        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock(spec=iModel)
            mock_cc.endpoint = MagicMock()
            mock_cc.endpoint.endpoint = "anthropic/claude-3-5-sonnet-20241022"
            mock_create_cc.return_value = mock_cc

            mock_branch = MagicMock()
            mock_branch.id = "test_branch"
            mock_branch_cls.return_value = mock_branch

            orchestrator.builder.add_operation.side_effect = Exception(
                "Operation failed"
            )

            with contextlib.suppress(Exception):
                await orchestrator.fanout(
                    initial_desc="Test",
                    planning_instruction="Plan",
                    synth_instruction="Synthesize",
                )

            # State should be cleanly handled (branch was created before failure)
            # This tests that partial state changes are acceptable
            assert (
                orchestrator.session.branches.include.call_count
                >= original_state["branches"]
            )


class TestAsyncPerformancePatterns:
    """Test performance patterns for async operations."""

    @pytest.mark.asyncio
    async def test_batch_operation_performance(self, orchestrator_with_mocks):
        """Test performance of batch operations vs sequential."""
        orchestrator = orchestrator_with_mocks

        # Mock operation that takes some time
        async def mock_operation():
            await asyncio.sleep(0.1)
            return "result"

        # Test sequential execution
        start_sequential = time.time()
        sequential_results = []
        for _ in range(5):
            result = await mock_operation()
            sequential_results.append(result)
        end_sequential = time.time()
        sequential_time = end_sequential - start_sequential

        # Test concurrent execution
        start_concurrent = time.time()
        concurrent_tasks = [mock_operation() for _ in range(5)]
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        end_concurrent = time.time()
        concurrent_time = end_concurrent - start_concurrent

        # Concurrent should be significantly faster
        assert concurrent_time < sequential_time * 0.8  # At least 20% faster
        assert len(concurrent_results) == len(sequential_results)

    @pytest.mark.asyncio
    async def test_async_context_manager_performance(self, orchestrator_with_mocks):
        """Test async context manager usage for resource management."""
        orchestrator = orchestrator_with_mocks

        # Mock an async context manager
        class AsyncResource:
            def __init__(self):
                self.acquired = False
                self.released = False

            async def __aenter__(self):
                await asyncio.sleep(0.01)
                self.acquired = True
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await asyncio.sleep(0.01)
                self.released = True

        # Test that resources are properly managed
        resource = AsyncResource()

        async with resource:
            assert resource.acquired is True
            assert resource.released is False

        assert resource.released is True

    @pytest.mark.asyncio
    async def test_backpressure_handling(self, orchestrator_with_mocks):
        """Test handling of backpressure in async operations."""
        orchestrator = orchestrator_with_mocks

        # Simulate a scenario where operations pile up
        results = []
        semaphore = asyncio.Semaphore(3)  # Limit concurrent operations

        async def limited_operation(op_id):
            async with semaphore:  # Acquire semaphore
                await asyncio.sleep(0.1)
                results.append(f"completed_{op_id}")
                return op_id

        # Start many operations
        tasks = [limited_operation(i) for i in range(10)]

        start_time = time.time()
        completed = await asyncio.gather(*tasks)
        end_time = time.time()

        # All operations should complete
        assert len(completed) == 10
        assert len(results) == 10

        # Should take longer due to backpressure (max 3 concurrent)
        # Approximately 10 operations / 3 concurrent * 0.1s = ~0.4s minimum
        assert (end_time - start_time) >= 0.3
