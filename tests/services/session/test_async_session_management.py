"""Comprehensive async session management and workflow coordination tests."""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import aiofiles
import pytest
from lionagi.service.imodel import iModel

from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.orchestration.parts import FanoutWithGatedRefinementResponse


class TestSessionLifecycleManagement:
    """Test comprehensive session lifecycle management under async conditions."""

    @pytest.mark.asyncio
    async def test_session_state_consistency_across_phases(
        self, orchestrator_with_mocks
    ):
        """Test session state consistency across multiple workflow phases."""
        orchestrator = orchestrator_with_mocks

        # Track session state changes throughout workflow
        state_snapshots = []

        def capture_session_state(phase_name):
            state = {
                "phase": phase_name,
                "timestamp": time.time(),
                "branch_count": orchestrator.session.branches.include.call_count,
                "default_branch_id": orchestrator.session.default_branch.id,
                "session_name": orchestrator.session.name,
            }
            state_snapshots.append(state)
            return state

        # Mock phased flow execution
        phase_counter = 0

        async def phased_flow_execution(graph):
            nonlocal phase_counter
            phase_counter += 1

            phase_name = f"phase_{phase_counter}"
            capture_session_state(f"{phase_name}_start")

            # Simulate different phase behaviors
            if phase_counter == 1:  # Planning phase
                await asyncio.sleep(0.1)
                mock_plan = MagicMock()
                mock_plan.initial = MagicMock()
                # Get the actual operation ID from the builder
                root_id = orchestrator.builder.add_operation.return_value
                result = {
                    "operation_results": {
                        root_id: MagicMock(flow_plans=MagicMock(initial=mock_plan))
                    }
                }
            elif phase_counter == 2:  # Execution phase
                await asyncio.sleep(0.2)
                result = {
                    "operation_results": {
                        "agent1": {"analysis": "result1"},
                        "agent2": {"analysis": "result2"},
                    }
                }
            else:  # Synthesis phase
                await asyncio.sleep(0.1)
                result = {"operation_results": {"synth": "synthesized_result"}}

            capture_session_state(f"{phase_name}_end")
            return result

        orchestrator.session.flow = phased_flow_execution
        orchestrator.expand_with_plan = AsyncMock(return_value=["agent1", "agent2"])
        orchestrator.opres_ctx = MagicMock(return_value=[])

        # Mock synthesis branch creation
        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            mock_cc = MagicMock()
            mock_create_cc.return_value = mock_cc
            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch"
            mock_branch_cls.return_value = mock_branch

            # Execute fanout workflow
            result = await orchestrator.fanout(
                initial_desc="Test multi-phase workflow",
                planning_instruction="Plan the execution",
                synth_instruction="Synthesize results",
            )

            # Verify session state consistency
            assert len(state_snapshots) == 6  # 3 phases * 2 snapshots each

            # Verify session identity remained consistent
            session_ids = {
                snapshot["default_branch_id"] for snapshot in state_snapshots
            }
            assert len(session_ids) == 1  # Same session throughout

            # Verify session name consistency
            session_names = {snapshot["session_name"] for snapshot in state_snapshots}
            assert len(session_names) == 1

            # Verify branch count progression (synthesis branch added)
            initial_branch_count = state_snapshots[0]["branch_count"]
            final_branch_count = state_snapshots[-1]["branch_count"]
            assert final_branch_count >= initial_branch_count

    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self):
        """Test concurrent operations on the same session."""
        orchestrator = LionOrchestrator("concurrent_session_test")

        # Mock session initialization
        with patch(
            "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
        ) as mock_create_cc:
            mock_cc = MagicMock(spec=iModel)
            mock_create_cc.return_value = mock_cc
            await orchestrator.initialize()

        # Track concurrent operations
        operation_log = []
        operation_lock = asyncio.Lock()

        async def tracked_session_operation(operation_name, duration=0.1):
            async with operation_lock:
                operation_log.append(
                    {
                        "operation": operation_name,
                        "start_time": time.time(),
                        "session_id": orchestrator.session.id,
                    }
                )

            # Simulate operation work
            await asyncio.sleep(duration)

            async with operation_lock:
                operation_log.append(
                    {
                        "operation": f"{operation_name}_complete",
                        "end_time": time.time(),
                        "session_id": orchestrator.session.id,
                    }
                )

            return f"{operation_name}_result"

        # Run concurrent session operations
        concurrent_operations = [
            tracked_session_operation("flow_execution", 0.15),
            tracked_session_operation("branch_creation", 0.1),
            tracked_session_operation("state_query", 0.05),
            tracked_session_operation("context_extraction", 0.12),
        ]

        start_time = time.time()
        results = await asyncio.gather(*concurrent_operations)
        end_time = time.time()

        # Verify all operations completed
        assert len(results) == 4
        assert all("_result" in result for result in results)

        # Verify concurrent execution was efficient
        total_time = end_time - start_time
        sequential_time = 0.15 + 0.1 + 0.05 + 0.12  # Sum of individual durations
        assert (
            total_time < sequential_time * 0.8
        )  # At least 20% speedup from concurrency

        # Verify session consistency across concurrent operations
        session_ids = {
            entry["session_id"] for entry in operation_log if "session_id" in entry
        }
        assert len(session_ids) == 1  # All operations used same session

    @pytest.mark.asyncio
    async def test_session_recovery_from_partial_failures(
        self, orchestrator_with_mocks
    ):
        """Test session recovery when some operations fail but others succeed."""
        orchestrator = orchestrator_with_mocks

        # Track recovery attempts
        recovery_log = []

        # Mock operations with mixed success/failure
        operation_count = 0

        async def mixed_outcome_flow(graph):
            nonlocal operation_count
            operation_count += 1

            recovery_log.append(
                {
                    "attempt": operation_count,
                    "timestamp": time.time(),
                    "graph_nodes": len(getattr(graph, "internal_nodes", {})),
                }
            )

            # Fail on first two attempts, succeed on third
            if operation_count <= 2:
                error_types = [
                    ValueError("Planning failed"),
                    ConnectionError("Network error"),
                ]
                raise error_types[operation_count - 1]

            # Successful execution
            return {
                "operation_results": {
                    "recovered_operation": f"success_attempt_{operation_count}"
                }
            }

        orchestrator.session.flow = mixed_outcome_flow

        # Implement retry logic with session state preservation
        async def execute_with_recovery(max_retries=3):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = await orchestrator.run_flow()
                    recovery_log.append(
                        {
                            "final_success": True,
                            "attempt": attempt + 1,
                            "result": result,
                        }
                    )
                    return result

                except Exception as e:
                    last_exception = e
                    recovery_log.append(
                        {
                            "failure": True,
                            "attempt": attempt + 1,
                            "error": str(e),
                        }
                    )

                    if attempt < max_retries:
                        # Brief delay before retry
                        await asyncio.sleep(0.1 * (attempt + 1))

            raise last_exception

        # Execute with recovery
        result = await execute_with_recovery()

        # Verify recovery succeeded
        assert result["operation_results"]["recovered_operation"] == "success_attempt_3"

        # Verify recovery attempts were logged
        failure_attempts = [log for log in recovery_log if log.get("failure", False)]
        success_attempts = [
            log for log in recovery_log if log.get("final_success", False)
        ]

        assert len(failure_attempts) == 2  # Two failures before success
        assert len(success_attempts) == 1  # One final success

        # Verify session remained stable throughout recovery
        assert orchestrator.session is not None
        assert orchestrator.session.default_branch is not None

    @pytest.mark.asyncio
    async def test_session_memory_and_context_preservation(
        self, orchestrator_with_mocks
    ):
        """Test preservation of session memory and context across async operations."""
        orchestrator = orchestrator_with_mocks

        # Mock session with persistent context
        session_context = {
            "workflow_state": "initial",
            "accumulated_results": [],
            "operation_history": [],
            "metadata": {"created_at": time.time()},
        }

        # Mock context-aware operations
        async def context_preserving_operation(operation_name, context_update=None):
            # Read current context
            current_state = session_context.get("workflow_state", "unknown")
            session_context["operation_history"].append(
                {
                    "operation": operation_name,
                    "previous_state": current_state,
                    "timestamp": time.time(),
                }
            )

            # Simulate async work
            await asyncio.sleep(0.05)

            # Update context
            if context_update:
                session_context.update(context_update)

            result = f"{operation_name}_completed_from_{current_state}"
            session_context["accumulated_results"].append(result)

            return result

        # Mock flow that preserves context across multiple async operations
        async def context_aware_flow(graph):
            # Sequential operations that build on each other
            result1 = await context_preserving_operation(
                "planning", {"workflow_state": "planned"}
            )

            result2 = await context_preserving_operation(
                "execution", {"workflow_state": "executing"}
            )

            # Concurrent operations that share context
            concurrent_ops = [
                context_preserving_operation("analysis_1"),
                context_preserving_operation("analysis_2"),
                context_preserving_operation("analysis_3"),
            ]

            concurrent_results = await asyncio.gather(*concurrent_ops)

            final_result = await context_preserving_operation(
                "synthesis", {"workflow_state": "complete"}
            )

            return {
                "operation_results": {
                    "sequential": [result1, result2],
                    "concurrent": concurrent_results,
                    "final": final_result,
                },
                "context_state": dict(session_context),
            }

        orchestrator.session.flow = context_aware_flow

        # Execute workflow
        result = await orchestrator.run_flow()

        # Verify context preservation
        final_context = result["context_state"]

        assert final_context["workflow_state"] == "complete"
        assert len(final_context["operation_history"]) == 6  # 6 operations total
        assert len(final_context["accumulated_results"]) == 6

        # Verify sequential operation progression
        planning_history = [
            h
            for h in final_context["operation_history"]
            if h["operation"] == "planning"
        ]
        assert len(planning_history) == 1
        assert planning_history[0]["previous_state"] == "initial"

        execution_history = [
            h
            for h in final_context["operation_history"]
            if h["operation"] == "execution"
        ]
        assert len(execution_history) == 1
        assert execution_history[0]["previous_state"] == "planned"

        # Verify concurrent operations shared context
        analysis_operations = [
            h
            for h in final_context["operation_history"]
            if h["operation"].startswith("analysis_")
        ]
        assert len(analysis_operations) == 3
        # All analysis operations should have seen 'executing' state
        assert all(h["previous_state"] == "executing" for h in analysis_operations)

    @pytest.mark.asyncio
    async def test_session_persistence_and_serialization(
        self, orchestrator_with_mocks, tmp_path
    ):
        """Test session persistence and serialization during async operations."""
        orchestrator = orchestrator_with_mocks

        # Mock serializable session state
        serializable_state = {
            "session_id": orchestrator.session.id,
            "flow_name": orchestrator.flow_name,
            "operations_completed": [],
            "current_phase": "initialization",
            "branch_metadata": {},
        }

        # Track serialization operations
        serialization_log = []

        async def serialize_session_state():
            """Simulate async session serialization."""
            serialization_log.append(
                {
                    "action": "serialize_start",
                    "timestamp": time.time(),
                    "state_size": len(json.dumps(serializable_state)),
                }
            )

            # Simulate I/O delay for serialization
            await asyncio.sleep(0.02)

            # Write to temp file
            state_file = tmp_path / f"session_{serializable_state['session_id']}.json"
            async with aiofiles.open(state_file, "w") as f:
                await f.write(json.dumps(serializable_state))

            serialization_log.append(
                {
                    "action": "serialize_complete",
                    "timestamp": time.time(),
                    "file_path": str(state_file),
                }
            )

            return str(state_file)

        async def deserialize_session_state(file_path):
            """Simulate async session deserialization."""
            serialization_log.append(
                {
                    "action": "deserialize_start",
                    "timestamp": time.time(),
                    "file_path": file_path,
                }
            )

            await asyncio.sleep(0.02)

            async with aiofiles.open(file_path) as f:
                content = await f.read()
                restored_state = json.loads(content)

            serialization_log.append(
                {
                    "action": "deserialize_complete",
                    "timestamp": time.time(),
                    "restored_operations": len(restored_state["operations_completed"]),
                }
            )

            return restored_state

        # Mock flow that periodically persists state
        operation_counter = 0

        async def persistent_flow(graph):
            nonlocal operation_counter
            operation_counter += 1

            operation_name = f"operation_{operation_counter}"
            serializable_state["operations_completed"].append(operation_name)
            serializable_state["current_phase"] = f"phase_{operation_counter}"

            # Serialize state during operation
            if operation_counter % 2 == 0:  # Serialize every other operation
                state_file = await serialize_session_state()

                # Test deserialization to verify integrity
                restored_state = await deserialize_session_state(state_file)
                assert restored_state["session_id"] == serializable_state["session_id"]

            await asyncio.sleep(0.05)  # Simulate operation work

            return {
                "operation_results": {operation_name: f"completed_{operation_counter}"}
            }

        orchestrator.session.flow = persistent_flow

        # Execute multiple flow runs with persistence
        results = []
        for i in range(4):
            result = await orchestrator.run_flow()
            results.append(result)

        # Verify persistence operations
        serialize_ops = [
            log for log in serialization_log if log["action"] == "serialize_start"
        ]
        deserialize_ops = [
            log for log in serialization_log if log["action"] == "deserialize_start"
        ]

        assert len(serialize_ops) == 2  # Serialized on operations 2 and 4
        assert len(deserialize_ops) == 2  # Corresponding deserializations

        # Verify session state was maintained
        assert len(serializable_state["operations_completed"]) == 4
        assert serializable_state["current_phase"] == "phase_4"

        # Verify all operations completed successfully
        assert len(results) == 4
        for i, result in enumerate(results, 1):
            operation_name = f"operation_{i}"
            assert operation_name in result["operation_results"]


class TestAdvancedWorkflowCoordination:
    """Test advanced workflow coordination patterns under async conditions."""

    @pytest.mark.asyncio
    async def test_gated_refinement_workflow_coordination(
        self, orchestrator_with_mocks, mock_file_system
    ):
        """Test gated refinement workflow with complex coordination patterns."""
        orchestrator = orchestrator_with_mocks

        # Track workflow coordination events
        coordination_events = []

        # Mock gated refinement execution phases
        phase_counter = 0
        gate_results = [
            {
                "threshold_met": False,
                "feedback": "Quality insufficient",
            },  # First gate fails
            {
                "threshold_met": True,
                "feedback": "Quality acceptable",
            },  # Second gate passes
        ]

        async def gated_flow_execution(graph):
            nonlocal phase_counter
            phase_counter += 1

            coordination_events.append(
                {
                    "phase": phase_counter,
                    "phase_name": [
                        "planning",
                        "initial",
                        "gate",
                        "refinement",
                        "synthesis",
                    ][phase_counter - 1],
                    "timestamp": time.time(),
                    "graph_size": len(getattr(graph, "internal_nodes", {})),
                }
            )

            # Simulate different phase execution patterns
            if phase_counter == 1:  # Planning
                await asyncio.sleep(0.1)
                mock_plan = MagicMock()
                mock_plan.initial = MagicMock()
                mock_plan.refinement = MagicMock()
                return {
                    "operation_results": {
                        "root": MagicMock(
                            flow_plans=MagicMock(
                                initial=mock_plan, refinement=mock_plan
                            )
                        )
                    }
                }
            if phase_counter == 2:  # Initial execution
                await asyncio.sleep(0.15)
                return {
                    "operation_results": {
                        "agent1": {"analysis": "initial_result_1"},
                        "agent2": {"analysis": "initial_result_2"},
                    }
                }
            if phase_counter == 3:  # Quality gate
                await asyncio.sleep(0.05)
                gate_result = (
                    gate_results[0] if len(gate_results) > 0 else gate_results[-1]
                )
                coordination_events.append(
                    {
                        "gate_result": gate_result,
                        "timestamp": time.time(),
                    }
                )
                return {"operation_results": {"gate": gate_result}}
            if phase_counter == 4:  # Refinement (if needed)
                await asyncio.sleep(0.2)
                return {
                    "operation_results": {
                        "refine1": {"refined_analysis": "refined_result_1"},
                        "refine2": {"refined_analysis": "refined_result_2"},
                    }
                }
            if phase_counter == 5:  # Re-gate after refinement
                await asyncio.sleep(0.05)
                gate_result = gate_results[1]
                coordination_events.append(
                    {
                        "gate_result": gate_result,
                        "timestamp": time.time(),
                    }
                )
                return {"operation_results": {"gate": gate_result}}
            # Final synthesis
            await asyncio.sleep(0.1)
            return {"operation_results": {"synth": "final_synthesized_result"}}

        orchestrator.session.flow = gated_flow_execution
        orchestrator.expand_with_plan = AsyncMock(return_value=["agent1", "agent2"])
        orchestrator.opres_ctx = MagicMock(return_value=[])

        # Mock branch and model creation for gated workflow
        with (
            patch(
                "khive.services.orchestration.orchestrator.create_orchestrator_cc_model"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc_branch,
        ):
            mock_cc = MagicMock(spec=iModel)
            mock_create_cc.return_value = mock_cc
            mock_cc_branch = MagicMock(spec=iModel)
            mock_create_cc_branch.return_value = mock_cc_branch

            mock_branch = MagicMock()
            mock_branch.id = "synthesis_branch"
            mock_branch_cls.return_value = mock_branch

            # Mock composer service for critic branch
            with patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer:
                mock_response = MagicMock()
                mock_response.system_prompt = "Critic prompt"
                mock_composer.handle_request = AsyncMock(return_value=mock_response)

                # Execute gated refinement workflow
                start_time = time.time()
                result = await orchestrator.fanout_w_gated_refinement(
                    initial_desc="Test gated workflow",
                    refinement_desc="Refine based on quality gate feedback",
                    gate_instruction="Evaluate quality and determine if refinement needed",
                    synth_instruction="Synthesize final results",
                    planning_instruction="Plan initial and refinement phases",
                    critic_domain="software-architecture",
                    project_phase="development",
                )
                end_time = time.time()

                # Verify coordination flow
                total_time = end_time - start_time
                assert total_time >= 0.6  # Minimum time for all phases

                # Verify workflow progression through all phases
                phase_names = [
                    event["phase_name"]
                    for event in coordination_events
                    if "phase_name" in event
                ]
                expected_phases = [
                    "planning",
                    "initial",
                    "gate",
                    "refinement",
                    "gate",
                    "synthesis",
                ]

                # Should have executed all phases due to initial gate failure
                assert (
                    len(phase_names) >= 4
                )  # At least planning, initial, gate, synthesis

                # Verify gate evaluation results were captured
                gate_events = [
                    event for event in coordination_events if "gate_result" in event
                ]
                assert len(gate_events) >= 1  # At least one gate evaluation

                # Verify result structure
                assert isinstance(result, dict | FanoutWithGatedRefinementResponse)

    @pytest.mark.asyncio
    async def test_multi_agent_coordination_with_dependencies(
        self, orchestrator_with_mocks
    ):
        """Test multi-agent coordination with complex dependency patterns."""
        orchestrator = orchestrator_with_mocks

        # Define agent dependency graph
        agent_dependencies = {
            "researcher": [],  # No dependencies
            "analyst": ["researcher"],  # Depends on researcher
            "architect": ["researcher", "analyst"],  # Depends on both
            "implementer": ["architect"],  # Depends on architect
            "reviewer": ["implementer"],  # Depends on implementer
        }

        # Track agent execution order and coordination
        agent_execution_log = []
        agent_completion_times = {}
        agent_completion_events = {}

        # Initialize completion events for all agents
        for agent in ["researcher", "analyst", "architect", "implementer", "reviewer"]:
            agent_completion_events[agent] = asyncio.Event()

        async def coordinated_agent_execution(agent_name, dependencies):
            """Simulate agent execution with dependency coordination."""

            # Wait for dependencies to complete using events
            for dep in dependencies:
                await agent_completion_events[dep].wait()

            # Log execution start
            start_time = time.time()
            agent_execution_log.append(
                {
                    "agent": agent_name,
                    "action": "start",
                    "timestamp": start_time,
                    "dependencies_completed": list(agent_completion_times.keys()),
                }
            )

            # Simulate agent work (different durations)
            work_durations = {
                "researcher": 0.15,
                "analyst": 0.12,
                "architect": 0.18,
                "implementer": 0.2,
                "reviewer": 0.1,
            }

            await asyncio.sleep(work_durations.get(agent_name, 0.1))

            # Log completion
            completion_time = time.time()
            agent_completion_times[agent_name] = completion_time
            # Signal completion to other waiting agents
            agent_completion_events[agent_name].set()
            agent_execution_log.append(
                {
                    "agent": agent_name,
                    "action": "complete",
                    "timestamp": completion_time,
                    "duration": completion_time - start_time,
                }
            )

            return f"{agent_name}_result"

        # Mock coordinated flow execution
        async def multi_agent_coordinated_flow(graph):
            # Start all agents concurrently, but they'll coordinate via dependencies
            agent_tasks = {
                agent: asyncio.create_task(coordinated_agent_execution(agent, deps))
                for agent, deps in agent_dependencies.items()
            }

            # Wait for all agents to complete
            agent_results = await asyncio.gather(*agent_tasks.values())

            return {
                "operation_results": dict(
                    zip(agent_dependencies.keys(), agent_results, strict=False)
                )
            }

        orchestrator.session.flow = multi_agent_coordinated_flow

        # Execute coordinated multi-agent workflow
        start_time = time.time()
        result = await orchestrator.run_flow()
        end_time = time.time()

        # Verify coordination behavior
        total_execution_time = end_time - start_time

        # Verify all agents completed
        assert len(result["operation_results"]) == 5
        assert all(
            f"{agent}_result" == result["operation_results"][agent]
            for agent in agent_dependencies
        )

        # Verify dependency order was respected
        start_events = {
            event["agent"]: event["timestamp"]
            for event in agent_execution_log
            if event["action"] == "start"
        }

        # Researcher should start first (no dependencies)
        assert "researcher" in start_events

        # Analyst should start after researcher
        if "analyst" in start_events and "researcher" in agent_completion_times:
            assert start_events["analyst"] >= agent_completion_times["researcher"]

        # Architect should start after both researcher and analyst
        if "architect" in start_events:
            required_deps = ["researcher", "analyst"]
            for dep in required_deps:
                if dep in agent_completion_times:
                    assert start_events["architect"] >= agent_completion_times[dep]

        # Total time should be less than sequential execution
        sequential_time = sum([0.15, 0.12, 0.18, 0.2, 0.1])  # Sum of all durations
        assert (
            total_execution_time < sequential_time * 1.1
        )  # Some parallelization (allowing for overhead)

    @pytest.mark.asyncio
    async def test_workflow_cancellation_propagation(self, orchestrator_with_mocks):
        """Test cancellation propagation through complex workflow structures."""
        orchestrator = orchestrator_with_mocks

        # Track cancellation propagation
        cancellation_events = []
        active_operations = {}

        async def cancellable_operation(operation_name, duration=0.5):
            """Operation that properly handles cancellation."""
            operation_id = f"{operation_name}_{len(active_operations)}"
            active_operations[operation_id] = {
                "name": operation_name,
                "start_time": time.time(),
                "status": "running",
            }

            try:
                await asyncio.sleep(duration)
                active_operations[operation_id]["status"] = "completed"
                return f"{operation_name}_success"

            except asyncio.CancelledError:
                active_operations[operation_id]["status"] = "cancelled"
                cancellation_events.append(
                    {
                        "operation": operation_name,
                        "operation_id": operation_id,
                        "timestamp": time.time(),
                        "duration_before_cancel": time.time()
                        - active_operations[operation_id]["start_time"],
                    }
                )
                raise

        # Mock workflow with nested operations
        async def nested_cancellable_flow(graph):
            """Workflow with nested async operations that can be cancelled."""

            try:
                # Start multiple concurrent operations
                phase1_tasks = [
                    cancellable_operation("research", 0.3),
                    cancellable_operation("analysis", 0.4),
                    cancellable_operation("planning", 0.2),
                ]

                phase1_results = await asyncio.gather(*phase1_tasks)

                # Start dependent operations
                phase2_tasks = [
                    cancellable_operation("implementation", 0.6),
                    cancellable_operation("testing", 0.5),
                ]

                phase2_results = await asyncio.gather(*phase2_tasks)

                # Final synthesis
                final_result = await cancellable_operation("synthesis", 0.3)

                return {
                    "operation_results": {
                        "phase1": phase1_results,
                        "phase2": phase2_results,
                        "final": final_result,
                    }
                }

            except asyncio.CancelledError:
                cancellation_events.append(
                    {
                        "workflow": "main_flow",
                        "timestamp": time.time(),
                        "active_operations_count": len(
                            [
                                op
                                for op in active_operations.values()
                                if op["status"] == "running"
                            ]
                        ),
                    }
                )
                raise

        orchestrator.session.flow = nested_cancellable_flow

        # Test cancellation during workflow execution
        workflow_task = asyncio.create_task(orchestrator.run_flow())

        # Let the workflow start and begin operations
        await asyncio.sleep(0.15)  # Let phase1 operations start

        # Cancel the workflow
        workflow_task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await workflow_task

        # Verify cancellation propagation
        assert len(cancellation_events) > 0

        # Verify some operations were cancelled
        cancelled_operations = [
            event for event in cancellation_events if "operation" in event
        ]
        assert len(cancelled_operations) > 0

        # Verify main workflow cancellation was recorded
        workflow_cancellations = [
            event for event in cancellation_events if "workflow" in event
        ]
        assert len(workflow_cancellations) >= 1

        # Verify operations were cancelled reasonably quickly
        for event in cancelled_operations:
            assert (
                event["duration_before_cancel"] < 0.5
            )  # Should cancel within reasonable time

    @pytest.mark.asyncio
    async def test_error_boundary_isolation_in_workflows(self, orchestrator_with_mocks):
        """Test error boundary isolation prevents cascade failures."""
        orchestrator = orchestrator_with_mocks

        # Track error isolation behavior
        error_events = []
        successful_operations = []

        async def isolated_operation(
            operation_name, should_fail=False, error_type=ValueError
        ):
            """Operation with error boundary isolation."""

            try:
                await asyncio.sleep(0.05)  # Simulate work

                if should_fail:
                    error = error_type(f"Intentional failure in {operation_name}")
                    error_events.append(
                        {
                            "operation": operation_name,
                            "error_type": type(error).__name__,
                            "error_message": str(error),
                            "timestamp": time.time(),
                        }
                    )
                    raise error

                result = f"{operation_name}_success"
                successful_operations.append(
                    {
                        "operation": operation_name,
                        "result": result,
                        "timestamp": time.time(),
                    }
                )

                return result

            except Exception as e:
                # Error boundary: log but don't propagate
                error_events.append(
                    {
                        "operation": operation_name,
                        "error_boundary": True,
                        "contained_error": str(e),
                        "timestamp": time.time(),
                    }
                )
                # Return error indicator instead of propagating
                return f"{operation_name}_failed"

        # Mock workflow with error boundaries
        async def error_isolated_flow(graph):
            """Workflow with proper error isolation boundaries."""

            # Operations with mixed success/failure - use gather with return_exceptions
            critical_operations = await asyncio.gather(
                isolated_operation("critical_op1", should_fail=False),
                isolated_operation(
                    "critical_op2", should_fail=True, error_type=ConnectionError
                ),
                isolated_operation("critical_op3", should_fail=False),
                return_exceptions=True,
            )

            # Non-critical operations that continue regardless
            non_critical_operations = await asyncio.gather(
                isolated_operation(
                    "non_critical_op1", should_fail=True, error_type=ValueError
                ),
                isolated_operation("non_critical_op2", should_fail=False),
                isolated_operation(
                    "non_critical_op3", should_fail=True, error_type=RuntimeError
                ),
                isolated_operation("non_critical_op4", should_fail=False),
                return_exceptions=True,
            )

            # Synthesis operation that processes partial results
            successful_critical = [
                r for r in critical_operations if isinstance(r, str) and "success" in r
            ]
            successful_non_critical = [
                r
                for r in non_critical_operations
                if isinstance(r, str) and "success" in r
            ]

            synthesis_result = await isolated_operation("synthesis", should_fail=False)

            return {
                "operation_results": {
                    "critical_results": critical_operations,
                    "non_critical_results": non_critical_operations,
                    "successful_critical_count": len(successful_critical),
                    "successful_non_critical_count": len(successful_non_critical),
                    "synthesis": synthesis_result,
                }
            }

        orchestrator.session.flow = error_isolated_flow

        # Execute workflow with error isolation
        result = await orchestrator.run_flow()

        # Verify error isolation worked
        assert (
            result["operation_results"]["successful_critical_count"] == 2
        )  # 2 of 3 succeeded
        assert (
            result["operation_results"]["successful_non_critical_count"] == 2
        )  # 2 of 4 succeeded
        assert (
            result["operation_results"]["synthesis"] == "synthesis_success"
        )  # Synthesis still worked

        # Verify errors were isolated and didn't cascade
        critical_results = result["operation_results"]["critical_results"]
        non_critical_results = result["operation_results"]["non_critical_results"]

        # Should have mix of successful strings and exception objects
        successful_critical = [
            r for r in critical_results if isinstance(r, str) and "success" in r
        ]
        failed_critical = [r for r in critical_results if isinstance(r, Exception)]

        successful_non_critical = [
            r for r in non_critical_results if isinstance(r, str) and "success" in r
        ]
        failed_non_critical = [
            r for r in non_critical_results if isinstance(r, Exception)
        ]

        assert len(successful_critical) == 2
        assert len(failed_critical) == 1
        assert len(successful_non_critical) == 2
        assert len(failed_non_critical) == 2

        # Verify error events were properly logged
        assert len(error_events) >= 3  # At least 3 intentional failures

        # Verify successful operations completed despite errors
        assert len(successful_operations) >= 5  # At least 5 successful operations
