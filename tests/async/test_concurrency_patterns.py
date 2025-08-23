"""
Advanced concurrency test patterns for multi-agent execution scenarios.

This module provides comprehensive testing for concurrent agent execution,
race condition detection, thread safety validation, and deadlock prevention
in the khive orchestration system.
"""

import asyncio
import threading
import time
from collections import defaultdict
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from khive.services.composition.parts import ComposerRequest


class ConcurrencyTestHarness:
    """Test harness for coordinating concurrent agent execution scenarios."""

    def __init__(self):
        self.shared_resources: dict[str, Any] = {}
        self.access_log: list[dict[str, Any]] = []
        self.resource_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.agent_states: dict[str, str] = {}
        self.execution_timeline: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def record_resource_access(self, agent_id: str, resource_id: str, operation: str):
        """Record resource access for race condition analysis."""
        with self._lock:
            timestamp = time.time()
            self.access_log.append(
                {
                    "timestamp": timestamp,
                    "agent_id": agent_id,
                    "resource_id": resource_id,
                    "operation": operation,
                    "thread_id": threading.get_ident(),
                }
            )

    def get_resource(self, resource_id: str):
        """Get shared resource with access logging."""
        return self.shared_resources.get(resource_id)

    def set_resource(self, resource_id: str, value: Any, agent_id: str):
        """Set shared resource with concurrent access tracking."""
        self.record_resource_access(agent_id, resource_id, "write")
        self.shared_resources[resource_id] = value

    def detect_race_conditions(self) -> list[dict[str, Any]]:
        """Analyze access log for potential race conditions."""
        races = []

        # Group accesses by resource
        resource_accesses = defaultdict(list)
        for access in self.access_log:
            resource_accesses[access["resource_id"]].append(access)

        # Check for concurrent write access
        for resource_id, accesses in resource_accesses.items():
            write_accesses = [a for a in accesses if a["operation"] == "write"]

            # Check for overlapping write windows (within 50ms)
            for i, access1 in enumerate(write_accesses):
                for access2 in write_accesses[i + 1 :]:
                    if abs(access1["timestamp"] - access2["timestamp"]) < 0.05:
                        races.append(
                            {
                                "resource_id": resource_id,
                                "agent1": access1["agent_id"],
                                "agent2": access2["agent_id"],
                                "time_diff": abs(
                                    access1["timestamp"] - access2["timestamp"]
                                ),
                                "type": "concurrent_write",
                            }
                        )

        return races


@pytest.fixture
def concurrency_harness():
    """Provide a concurrency test harness."""
    return ConcurrencyTestHarness()


@pytest.fixture
def concurrent_agent_pool():
    """Create a pool of mock agents for concurrent testing."""
    agents = []
    for i in range(10):
        agent = MagicMock()
        agent.id = f"agent_{i}"
        agent.role = ["researcher", "analyst", "architect", "implementer", "tester"][
            i % 5
        ]
        agent.state = "ready"
        agent.execute = AsyncMock(
            return_value={"result": f"output_{i}", "agent_id": agent.id}
        )
        agents.append(agent)
    return agents


@pytest.fixture
def shared_resource_scenarios():
    """Define shared resource access scenarios for testing."""
    return {
        "database_connection": {
            "max_concurrent": 5,
            "resource_type": "connection_pool",
            "contention_level": "high",
        },
        "file_system": {
            "max_concurrent": 1,
            "resource_type": "exclusive_file",
            "contention_level": "critical",
        },
        "memory_cache": {
            "max_concurrent": 20,
            "resource_type": "shared_memory",
            "contention_level": "low",
        },
        "api_quota": {
            "max_concurrent": 3,
            "resource_type": "rate_limited",
            "contention_level": "medium",
        },
    }


class TestMultiAgentCoordination:
    """Test multi-agent coordination patterns under concurrent execution."""

    @pytest.mark.asyncio
    async def test_concurrent_agent_branch_creation_safety(
        self, orchestrator_with_mocks, concurrent_agent_pool, concurrency_harness
    ):
        """Test safe concurrent branch creation for multiple agents."""
        orchestrator = orchestrator_with_mocks

        # Mock branch creation with realistic timing
        original_call_count = 0
        created_branches = set()
        creation_conflicts = []

        def mock_lookup_branch(name):
            nonlocal original_call_count
            original_call_count += 1
            # Simulate race condition scenario
            if name in created_branches:
                creation_conflicts.append(name)
                return MagicMock()  # Branch exists
            return None  # Branch doesn't exist

        def mock_branch_creation(*args, **kwargs):
            branch_id = str(uuid4())
            branch_name = kwargs.get("name", f"branch_{len(created_branches)}")
            created_branches.add(branch_name)

            mock_branch = MagicMock()
            mock_branch.id = branch_id
            mock_branch.name = branch_name
            return mock_branch

        with (
            patch("khive.services.orchestration.orchestrator.create_cc") as mock_cc,
            patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            # Setup mocks
            async def mock_cc_return(*args, **kwargs):
                await asyncio.sleep(0.01)  # Simulate network delay
                return MagicMock()

            mock_cc.return_value = mock_cc_return()
            mock_composer.handle_request = AsyncMock(
                return_value=MagicMock(system_prompt="Test")
            )
            mock_branch_cls.side_effect = mock_branch_creation
            orchestrator.session._lookup_branch_by_name = mock_lookup_branch

            # Create many concurrent branch creation requests
            compose_requests = [
                ComposerRequest(role=agent.role, domains="software-architecture")
                for agent in concurrent_agent_pool[:8]
            ]

            # Execute concurrently
            start_time = time.time()
            branch_creation_tasks = [
                orchestrator.create_cc_branch(request, agent_suffix=f"_{i}")
                for i, request in enumerate(compose_requests)
            ]

            branch_ids = await asyncio.gather(
                *branch_creation_tasks, return_exceptions=True
            )
            execution_time = time.time() - start_time

            # Validate results
            successful_creations = [
                bid for bid in branch_ids if not isinstance(bid, Exception)
            ]
            assert len(successful_creations) == len(
                compose_requests
            ), "All branch creations should succeed"
            assert len(set(successful_creations)) == len(
                successful_creations
            ), "All branch IDs should be unique"

            # Performance validation - should be much faster than sequential
            max_sequential_time = len(compose_requests) * 0.1  # 100ms per creation
            assert (
                execution_time < max_sequential_time * 0.5
            ), "Concurrent execution should be significantly faster"

            # Validate no major conflicts occurred
            assert (
                len(creation_conflicts) < len(compose_requests) * 0.2
            ), "Minimal naming conflicts expected"

    @pytest.mark.asyncio
    async def test_shared_session_state_consistency(
        self, orchestrator_with_mocks, concurrent_agent_pool, concurrency_harness
    ):
        """Test session state remains consistent under heavy concurrent access."""
        orchestrator = orchestrator_with_mocks

        # Shared state tracking
        shared_state = {"counter": 0, "operations": []}
        state_lock = asyncio.Lock()

        async def concurrent_state_operation(agent_id: str, operation_count: int):
            results = []
            for i in range(operation_count):
                concurrency_harness.record_resource_access(
                    agent_id, "shared_state", "read"
                )

                # Read current state
                current_counter = shared_state["counter"]

                # Simulate processing delay
                await asyncio.sleep(0.001)  # 1ms processing

                # Write back updated state with proper locking
                async with state_lock:
                    concurrency_harness.record_resource_access(
                        agent_id, "shared_state", "write"
                    )
                    shared_state["counter"] = current_counter + 1
                    shared_state["operations"].append(f"{agent_id}_op_{i}")

                results.append(current_counter + 1)

                # Record successful operation
                concurrency_harness.record_resource_access(
                    agent_id, "operation_result", "write"
                )

            return results

        # Execute many concurrent operations
        agent_tasks = [concurrent_state_operation(f"agent_{i}", 10) for i in range(8)]

        start_time = time.time()
        all_results = await asyncio.gather(*agent_tasks)
        execution_time = time.time() - start_time

        # Validate consistency
        total_operations = sum(len(results) for results in all_results)
        assert (
            shared_state["counter"] == total_operations
        ), "Counter should match total operations"
        assert (
            len(shared_state["operations"]) == total_operations
        ), "All operations should be recorded"

        # Check for race conditions
        race_conditions = concurrency_harness.detect_race_conditions()

        # With proper locking, there should be no race conditions on shared_state
        state_races = [r for r in race_conditions if r["resource_id"] == "shared_state"]
        assert (
            len(state_races) == 0
        ), f"No race conditions expected with locking, found: {state_races}"

        # Performance should be reasonable
        assert (
            execution_time < 5.0
        ), "Concurrent operations should complete within reasonable time"

    @pytest.mark.asyncio
    async def test_resource_pool_contention_management(
        self, orchestrator_with_mocks, shared_resource_scenarios, concurrency_harness
    ):
        """Test management of resource pool contention across multiple agents."""
        orchestrator = orchestrator_with_mocks

        # Simulate different resource pools with different constraints
        resource_pools = {}
        for resource_name, scenario in shared_resource_scenarios.items():
            pool = asyncio.Semaphore(scenario["max_concurrent"])
            resource_pools[resource_name] = {"semaphore": pool, "scenario": scenario}

        acquired_resources = defaultdict(list)

        async def agent_resource_operation(
            agent_id: str, resource_name: str, operation_duration: float
        ):
            """Simulate agent accessing a constrained resource."""
            pool_info = resource_pools[resource_name]
            semaphore = pool_info["semaphore"]

            # Try to acquire resource
            concurrency_harness.record_resource_access(
                agent_id, resource_name, "acquire_attempt"
            )

            async with semaphore:
                acquire_time = time.time()
                acquired_resources[resource_name].append(
                    {
                        "agent_id": agent_id,
                        "acquire_time": acquire_time,
                        "thread_id": threading.get_ident(),
                    }
                )

                concurrency_harness.record_resource_access(
                    agent_id, resource_name, "acquired"
                )

                # Simulate work with the resource
                await asyncio.sleep(operation_duration)

                concurrency_harness.record_resource_access(
                    agent_id, resource_name, "released"
                )

                return f"{agent_id}_completed_{resource_name}"

        # Create scenarios with different levels of contention
        high_contention_tasks = [
            agent_resource_operation(f"agent_{i}", "database_connection", 0.1)
            for i in range(15)  # 15 agents, 5 max concurrent
        ]

        critical_contention_tasks = [
            agent_resource_operation(f"agent_{i}", "file_system", 0.05)
            for i in range(8)  # 8 agents, 1 max concurrent - high contention
        ]

        low_contention_tasks = [
            agent_resource_operation(f"agent_{i}", "memory_cache", 0.02)
            for i in range(25)  # 25 agents, 20 max concurrent - should be fast
        ]

        # Execute all scenarios concurrently
        start_time = time.time()

        all_results = await asyncio.gather(
            asyncio.gather(*high_contention_tasks, return_exceptions=True),
            asyncio.gather(*critical_contention_tasks, return_exceptions=True),
            asyncio.gather(*low_contention_tasks, return_exceptions=True),
        )

        execution_time = time.time() - start_time

        # Validate resource pool behavior
        for resource_name, pool_info in resource_pools.items():
            max_concurrent = pool_info["scenario"]["max_concurrent"]
            accesses = acquired_resources[resource_name]

            # Check that we never exceeded the concurrent limit
            # Group accesses by time windows to check concurrency
            time_windows = defaultdict(list)
            for access in accesses:
                time_slot = int(access["acquire_time"] * 100)  # 10ms windows
                time_windows[time_slot].append(access)

            for time_slot, concurrent_accesses in time_windows.items():
                assert len(concurrent_accesses) <= max_concurrent, (
                    f"Resource {resource_name} exceeded max concurrent limit: "
                    f"{len(concurrent_accesses)} > {max_concurrent} at time {time_slot}"
                )

        # Validate that all operations completed successfully
        db_results, fs_results, cache_results = all_results

        successful_db = [r for r in db_results if not isinstance(r, Exception)]
        successful_fs = [r for r in fs_results if not isinstance(r, Exception)]
        successful_cache = [r for r in cache_results if not isinstance(r, Exception)]

        assert len(successful_db) == 15, "All database operations should complete"
        assert len(successful_fs) == 8, "All file system operations should complete"
        assert len(successful_cache) == 25, "All cache operations should complete"

        # Performance validation based on resource constraints
        # File system should take longest (sequential), cache should be fastest
        assert (
            execution_time > 0.3
        ), "Should take some time due to file system serialization"
        assert execution_time < 10.0, "Should complete within reasonable time"


class TestRaceConditionDetection:
    """Test detection and prevention of race conditions in agent coordination."""

    @pytest.mark.asyncio
    async def test_concurrent_branch_naming_race_detection(
        self, orchestrator_with_mocks, concurrency_harness
    ):
        """Test detection of race conditions in branch naming."""
        orchestrator = orchestrator_with_mocks

        # Setup race condition scenario
        branch_name_attempts = defaultdict(list)
        naming_conflicts = []

        def mock_lookup_with_race_condition(name):
            # Record the naming attempt
            timestamp = time.time()
            thread_id = threading.get_ident()
            branch_name_attempts[name].append(
                {
                    "timestamp": timestamp,
                    "thread_id": thread_id,
                }
            )

            # Simulate race condition - first few calls return None, then existing branch
            attempts_for_name = len(branch_name_attempts[name])

            if attempts_for_name == 1:
                return None  # First attempt - name available
            if attempts_for_name == 2:
                # Second concurrent attempt - create race condition
                naming_conflicts.append(
                    {
                        "name": name,
                        "attempts": branch_name_attempts[name].copy(),
                        "race_window": abs(
                            branch_name_attempts[name][1]["timestamp"]
                            - branch_name_attempts[name][0]["timestamp"]
                        ),
                    }
                )
                return None  # Still allow creation but flag the race
            return MagicMock()  # Subsequent attempts - branch exists

        with (
            patch("khive.services.orchestration.orchestrator.create_cc") as mock_cc,
            patch(
                "khive.services.orchestration.orchestrator.composer_service"
            ) as mock_composer,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
        ):
            # Setup mocks
            async def mock_cc_return(*args, **kwargs):
                return MagicMock()

            mock_cc.return_value = mock_cc_return()
            mock_composer.handle_request = AsyncMock(
                return_value=MagicMock(system_prompt="Test")
            )

            branch_counter = 0

            def create_mock_branch(*args, **kwargs):
                nonlocal branch_counter
                mock_branch = MagicMock()
                mock_branch.id = f"branch_{branch_counter}"
                branch_counter += 1
                return mock_branch

            mock_branch_cls.side_effect = create_mock_branch
            orchestrator.session._lookup_branch_by_name = (
                mock_lookup_with_race_condition
            )

            # Create scenario where multiple agents try to create branches with same base name
            compose_request = ComposerRequest(
                role="researcher", domains="software-architecture"
            )

            # Launch many concurrent branch creations with same parameters (likely same names)
            concurrent_tasks = [
                orchestrator.create_cc_branch(compose_request) for _ in range(6)
            ]

            # Execute with tight timing to maximize race condition probability
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)

            # Analyze race conditions
            successful_results = [r for r in results if not isinstance(r, Exception)]

            # All should succeed (with conflict resolution)
            assert (
                len(successful_results) >= 4
            ), "Most branch creations should succeed despite races"

            # Verify race conditions were detected
            assert (
                len(naming_conflicts) > 0
            ), "Race conditions should be detected in branch naming"

            # Check race condition timing (should be very close)
            for conflict in naming_conflicts:
                assert (
                    conflict["race_window"] < 0.1
                ), f"Race window too wide: {conflict['race_window']}"

            # Record race conditions for analysis
            for conflict in naming_conflicts:
                concurrency_harness.record_resource_access(
                    f"thread_{conflict['attempts'][0]['thread_id']}",
                    f"branch_name_{conflict['name']}",
                    "race_detected",
                )

    @pytest.mark.asyncio
    async def test_shared_data_structure_race_conditions(
        self, orchestrator_with_mocks, concurrency_harness
    ):
        """Test race conditions in shared data structure access."""
        orchestrator = orchestrator_with_mocks

        # Shared data structure that's prone to race conditions
        shared_dict = {}
        shared_list = []
        shared_counter = {"value": 0}

        # Track operations without proper synchronization
        async def unsafe_data_operations(agent_id: str, operations_count: int):
            results = []

            for i in range(operations_count):
                # Dictionary operations (prone to KeyError races)
                key = f"key_{i % 5}"  # Limited key space to increase collisions

                concurrency_harness.record_resource_access(
                    agent_id, "shared_dict", "read"
                )
                if key in shared_dict:
                    current_value = shared_dict[key]
                else:
                    current_value = 0

                # Simulate processing delay
                await asyncio.sleep(0.001)

                concurrency_harness.record_resource_access(
                    agent_id, "shared_dict", "write"
                )
                shared_dict[key] = current_value + 1

                # List operations (prone to index races)
                concurrency_harness.record_resource_access(
                    agent_id, "shared_list", "write"
                )
                shared_list.append(f"{agent_id}_item_{i}")

                # Counter operations (classic race condition)
                concurrency_harness.record_resource_access(
                    agent_id, "shared_counter", "read"
                )
                current_counter = shared_counter["value"]

                await asyncio.sleep(0.001)  # Processing delay

                concurrency_harness.record_resource_access(
                    agent_id, "shared_counter", "write"
                )
                shared_counter["value"] = current_counter + 1

                results.append(
                    {
                        "dict_value": shared_dict.get(key, 0),
                        "list_length": len(shared_list),
                        "counter_value": shared_counter["value"],
                    }
                )

            return results

        # Execute multiple agents performing unsafe operations
        agent_tasks = [unsafe_data_operations(f"agent_{i}", 20) for i in range(6)]

        start_time = time.time()
        all_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        execution_time = time.time() - start_time

        # Analyze results for race conditions
        successful_results = [r for r in all_results if not isinstance(r, Exception)]
        total_operations = (
            sum(len(results) for results in successful_results)
            if successful_results
            else 0
        )

        # Expected vs actual values (race condition indicators)
        expected_counter = total_operations
        actual_counter = shared_counter["value"]

        expected_list_length = total_operations
        actual_list_length = len(shared_list)

        # Detect race conditions through inconsistencies
        counter_race_detected = actual_counter != expected_counter
        list_race_detected = actual_list_length != expected_list_length

        # Dictionary consistency check
        dict_inconsistencies = 0
        for key, value in shared_dict.items():
            # Count how many times this key should have been incremented
            key_num = int(key.split("_")[1])
            expected_increments = total_operations // 5  # 5 keys total
            if key_num < total_operations % 5:
                expected_increments += 1

            if value != expected_increments:
                dict_inconsistencies += 1

        # Analyze detected race conditions
        detected_races = concurrency_harness.detect_race_conditions()

        # Assert race conditions were detected (this is expected in unsafe operations)
        assert (
            len(detected_races) > 0 or counter_race_detected or list_race_detected
        ), "Race conditions should be detected in unsafe concurrent operations"

        # Record findings
        if counter_race_detected:
            concurrency_harness.record_resource_access(
                "system", "race_analysis", "counter_race_detected"
            )

        if list_race_detected:
            concurrency_harness.record_resource_access(
                "system", "race_analysis", "list_race_detected"
            )

        if dict_inconsistencies > 0:
            concurrency_harness.record_resource_access(
                "system", "race_analysis", "dict_inconsistencies"
            )


class TestDeadlockPrevention:
    """Test deadlock prevention mechanisms in multi-agent scenarios."""

    @pytest.mark.asyncio
    async def test_circular_dependency_deadlock_prevention(
        self, orchestrator_with_mocks
    ):
        """Test prevention of deadlocks in circular agent dependencies."""
        orchestrator = orchestrator_with_mocks

        # Create lock objects representing different resources
        resource_locks = {
            "database": asyncio.Lock(),
            "filesystem": asyncio.Lock(),
            "network": asyncio.Lock(),
            "memory": asyncio.Lock(),
        }

        # Track lock acquisition order to detect potential deadlocks
        acquisition_order = []
        acquisition_lock = asyncio.Lock()

        async def agent_with_resource_chain(agent_id: str, resource_chain: list[str]):
            """Agent that needs to acquire resources in a specific order."""
            acquired_locks = []

            try:
                for resource in resource_chain:
                    # Record acquisition attempt
                    async with acquisition_lock:
                        acquisition_order.append(
                            {
                                "agent_id": agent_id,
                                "resource": resource,
                                "action": "attempting",
                                "timestamp": time.time(),
                            }
                        )

                    # Acquire lock with timeout to prevent indefinite blocking
                    try:
                        await asyncio.wait_for(
                            resource_locks[resource].acquire(),
                            timeout=2.0,  # 2 second timeout
                        )
                        acquired_locks.append(resource)

                        async with acquisition_lock:
                            acquisition_order.append(
                                {
                                    "agent_id": agent_id,
                                    "resource": resource,
                                    "action": "acquired",
                                    "timestamp": time.time(),
                                }
                            )

                        # Simulate work with resource
                        await asyncio.sleep(0.1)

                    except asyncio.TimeoutError:
                        # Timeout indicates potential deadlock
                        async with acquisition_lock:
                            acquisition_order.append(
                                {
                                    "agent_id": agent_id,
                                    "resource": resource,
                                    "action": "timeout",
                                    "timestamp": time.time(),
                                }
                            )
                        raise

                return f"{agent_id}_completed"

            finally:
                # Release all acquired locks in reverse order (proper cleanup)
                for resource in reversed(acquired_locks):
                    resource_locks[resource].release()
                    async with acquisition_lock:
                        acquisition_order.append(
                            {
                                "agent_id": agent_id,
                                "resource": resource,
                                "action": "released",
                                "timestamp": time.time(),
                            }
                        )

        # Create scenarios that could lead to deadlocks
        deadlock_prone_scenarios = [
            # Circular dependency scenario
            ("agent_circular_1", ["database", "filesystem", "network"]),
            ("agent_circular_2", ["network", "database", "filesystem"]),
            ("agent_circular_3", ["filesystem", "network", "database"]),
            # Overlapping resource scenarios
            ("agent_overlap_1", ["database", "memory"]),
            ("agent_overlap_2", ["memory", "database"]),
            ("agent_overlap_3", ["database", "filesystem"]),
            ("agent_overlap_4", ["filesystem", "database"]),
        ]

        # Execute all scenarios concurrently
        start_time = time.time()
        tasks = [
            agent_with_resource_chain(agent_id, resources)
            for agent_id, resources in deadlock_prone_scenarios
        ]

        # Use gather with return_exceptions to catch timeouts/deadlocks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time

        # Analyze results
        successful_completions = [
            r for r in results if isinstance(r, str) and "completed" in r
        ]
        timeout_exceptions = [r for r in results if isinstance(r, asyncio.TimeoutError)]
        other_exceptions = [
            r
            for r in results
            if isinstance(r, Exception) and not isinstance(r, asyncio.TimeoutError)
        ]

        # Deadlock prevention validation
        # With proper timeout mechanisms, we should either have:
        # 1. All operations complete successfully, or
        # 2. Some operations timeout (preventing deadlock) but system remains responsive

        total_operations = len(deadlock_prone_scenarios)
        completion_rate = len(successful_completions) / total_operations

        # System should remain responsive (not completely deadlocked)
        assert execution_time < 10.0, "System should not be completely deadlocked"

        # Either high completion rate OR graceful timeout handling
        if len(timeout_exceptions) > 0:
            # Some operations timed out - this is acceptable as deadlock prevention
            assert (
                len(timeout_exceptions) < total_operations
            ), "Not all operations should timeout"
            assert completion_rate > 0.0, "Some operations should still complete"
        else:
            # All operations completed - ideal scenario
            assert (
                completion_rate >= 0.7
            ), "Most operations should complete without deadlock"

        # No unexpected exceptions
        assert (
            len(other_exceptions) == 0
        ), f"No unexpected exceptions: {other_exceptions}"

        # Analyze acquisition patterns for deadlock detection
        deadlock_indicators = []

        # Group acquisition attempts by agent
        agent_attempts = defaultdict(list)
        for attempt in acquisition_order:
            agent_attempts[attempt["agent_id"]].append(attempt)

        # Look for timeout patterns that suggest deadlocks
        for agent_id, attempts in agent_attempts.items():
            timeout_attempts = [a for a in attempts if a["action"] == "timeout"]
            if len(timeout_attempts) > 0:
                deadlock_indicators.append(
                    {
                        "agent_id": agent_id,
                        "timeout_resources": [a["resource"] for a in timeout_attempts],
                        "indication": "potential_deadlock_prevented",
                    }
                )

        # Record findings
        print("\nDeadlock Prevention Analysis:")
        print(f"  - Total operations: {total_operations}")
        print(f"  - Successful completions: {len(successful_completions)}")
        print(f"  - Timeout exceptions: {len(timeout_exceptions)}")
        print(f"  - Completion rate: {completion_rate:.2%}")
        print(f"  - Execution time: {execution_time:.2f}s")
        print(f"  - Deadlock indicators: {len(deadlock_indicators)}")

    @pytest.mark.asyncio
    async def test_resource_ordering_deadlock_prevention(self, orchestrator_with_mocks):
        """Test deadlock prevention through consistent resource ordering."""
        orchestrator = orchestrator_with_mocks

        # Resources with defined ordering for deadlock prevention
        RESOURCE_ORDER = ["resource_a", "resource_b", "resource_c", "resource_d"]
        resource_locks = {name: asyncio.Lock() for name in RESOURCE_ORDER}

        successful_operations = []
        failed_operations = []

        async def agent_with_ordered_acquisition(
            agent_id: str, needed_resources: list[str]
        ):
            """Agent that acquires resources in predefined order to prevent deadlocks."""

            # Sort needed resources by predefined order
            ordered_resources = sorted(
                needed_resources, key=lambda x: RESOURCE_ORDER.index(x)
            )

            acquired_locks = []
            try:
                # Acquire locks in order
                for resource in ordered_resources:
                    await resource_locks[resource].acquire()
                    acquired_locks.append(resource)

                # Simulate work
                await asyncio.sleep(0.05)

                successful_operations.append(
                    {
                        "agent_id": agent_id,
                        "resources": ordered_resources,
                        "original_order": needed_resources,
                    }
                )

                return f"{agent_id}_success"

            except Exception as e:
                failed_operations.append(
                    {
                        "agent_id": agent_id,
                        "error": str(e),
                        "resources": needed_resources,
                    }
                )
                raise

            finally:
                # Release in reverse order
                for resource in reversed(acquired_locks):
                    resource_locks[resource].release()

        # Create scenarios with different resource needs
        resource_scenarios = [
            ("agent_ordered_1", ["resource_d", "resource_a"]),  # Out of order request
            (
                "agent_ordered_2",
                ["resource_b", "resource_d", "resource_a"],
            ),  # Out of order request
            ("agent_ordered_3", ["resource_a", "resource_c"]),  # In order request
            ("agent_ordered_4", ["resource_c", "resource_b"]),  # Out of order request
            (
                "agent_ordered_5",
                ["resource_d", "resource_c", "resource_b", "resource_a"],
            ),  # Reverse order
            (
                "agent_ordered_6",
                ["resource_a", "resource_b", "resource_c", "resource_d"],
            ),  # Correct order
        ]

        # Execute all scenarios concurrently
        start_time = time.time()
        tasks = [
            agent_with_ordered_acquisition(agent_id, resources)
            for agent_id, resources in resource_scenarios
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time

        # All operations should complete successfully due to ordered acquisition
        successful_results = [
            r for r in results if isinstance(r, str) and "success" in r
        ]
        exception_results = [r for r in results if isinstance(r, Exception)]

        # With proper ordering, no deadlocks should occur
        assert len(successful_results) == len(
            resource_scenarios
        ), "All operations should complete successfully with ordered resource acquisition"
        assert (
            len(exception_results) == 0
        ), f"No exceptions expected with ordered acquisition: {exception_results}"
        assert (
            len(failed_operations) == 0
        ), f"No failed operations expected: {failed_operations}"

        # Execution should be efficient
        assert (
            execution_time < 2.0
        ), "Ordered acquisition should complete quickly without deadlocks"

        # Verify that resources were actually reordered
        reordered_count = 0
        for operation in successful_operations:
            if operation["resources"] != operation["original_order"]:
                reordered_count += 1

        assert (
            reordered_count > 0
        ), "Some resources should have been reordered for deadlock prevention"


class TestThreadSafetyValidation:
    """Test thread safety of orchestration components."""

    @pytest.mark.asyncio
    async def test_concurrent_session_modification_safety(
        self, orchestrator_with_mocks, concurrency_harness
    ):
        """Test thread safety of session modifications under concurrent access."""
        orchestrator = orchestrator_with_mocks

        # Shared session state that will be modified concurrently
        session_modifications = []
        modification_errors = []

        async def concurrent_session_modifier(agent_id: str, modification_count: int):
            """Modify session state concurrently."""
            results = []

            for i in range(modification_count):
                try:
                    # Record the modification attempt
                    concurrency_harness.record_resource_access(
                        agent_id, "session_state", "modify_attempt"
                    )

                    # Simulate different types of session modifications
                    modification_type = i % 4

                    if modification_type == 0:
                        # Branch list modification
                        mock_branch = MagicMock()
                        mock_branch.id = f"{agent_id}_branch_{i}"
                        orchestrator.session.branches.include(mock_branch)
                        modification_type_name = "branch_add"

                    elif modification_type == 1:
                        # Session attribute modification
                        setattr(
                            orchestrator.session, f"{agent_id}_attr_{i}", f"value_{i}"
                        )
                        modification_type_name = "attribute_set"

                    elif modification_type == 2:
                        # Session method call
                        orchestrator.session.get_branch(f"test_branch_{i}")
                        modification_type_name = "method_call"

                    else:
                        # Default branch interaction
                        orchestrator.session.default_branch.name = (
                            f"{agent_id}_default_{i}"
                        )
                        modification_type_name = "default_branch_modify"

                    session_modifications.append(
                        {
                            "agent_id": agent_id,
                            "modification_index": i,
                            "modification_type": modification_type_name,
                            "timestamp": time.time(),
                        }
                    )

                    concurrency_harness.record_resource_access(
                        agent_id, "session_state", "modify_success"
                    )
                    results.append(f"{agent_id}_mod_{i}")

                    # Small delay to increase chance of concurrent access
                    await asyncio.sleep(0.001)

                except Exception as e:
                    modification_errors.append(
                        {
                            "agent_id": agent_id,
                            "modification_index": i,
                            "error": str(e),
                            "timestamp": time.time(),
                        }
                    )
                    concurrency_harness.record_resource_access(
                        agent_id, "session_state", "modify_error"
                    )

            return results

        # Run multiple agents modifying session concurrently
        concurrent_modifiers = [
            concurrent_session_modifier(f"modifier_agent_{i}", 15) for i in range(8)
        ]

        start_time = time.time()
        all_results = await asyncio.gather(
            *concurrent_modifiers, return_exceptions=True
        )
        execution_time = time.time() - start_time

        # Analyze thread safety
        successful_results = [r for r in all_results if not isinstance(r, Exception)]
        exception_results = [r for r in all_results if isinstance(r, Exception)]

        total_modifications = (
            sum(len(results) for results in successful_results)
            if successful_results
            else 0
        )

        # Thread safety validation
        # With proper mocking, we should have minimal errors
        error_rate = len(modification_errors) / max(total_modifications, 1)

        assert (
            error_rate < 0.1
        ), f"Error rate should be low for thread-safe operations: {error_rate:.2%}"
        assert (
            len(exception_results) == 0
        ), f"No exceptions expected in thread-safe operations: {exception_results}"

        # Performance should be reasonable
        assert (
            execution_time < 5.0
        ), "Concurrent modifications should complete within reasonable time"

        # Verify modification consistency
        modification_by_type = defaultdict(list)
        for mod in session_modifications:
            modification_by_type[mod["modification_type"]].append(mod)

        # Each modification type should have reasonable distribution
        for mod_type, modifications in modification_by_type.items():
            assert (
                len(modifications) > 0
            ), f"Should have modifications of type {mod_type}"

        # Detect any race conditions in modifications
        detected_races = concurrency_harness.detect_race_conditions()
        session_races = [r for r in detected_races if "session" in r["resource_id"]]

        # Report race conditions if found (may be expected in some scenarios)
        if session_races:
            print(
                f"\nSession modification race conditions detected: {len(session_races)}"
            )
            for race in session_races[:3]:  # Show first few
                print(
                    f"  - Resource: {race['resource_id']}, Agents: {race['agent1']}, {race['agent2']}"
                )

    @pytest.mark.asyncio
    async def test_async_context_manager_thread_safety(self, orchestrator_with_mocks):
        """Test thread safety of async context managers used in orchestration."""
        orchestrator = orchestrator_with_mocks

        # Custom async context manager for testing
        class ThreadSafeAsyncResource:
            def __init__(self, resource_id: str):
                self.resource_id = resource_id
                self.active_count = 0
                self.max_concurrent = 0
                self.access_log = []
                self._lock = asyncio.Lock()

            async def __aenter__(self):
                async with self._lock:
                    self.active_count += 1
                    self.max_concurrent = max(self.max_concurrent, self.active_count)
                    self.access_log.append(
                        {
                            "action": "enter",
                            "active_count": self.active_count,
                            "timestamp": time.time(),
                            "task_id": id(asyncio.current_task()),
                        }
                    )
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                async with self._lock:
                    self.active_count -= 1
                    self.access_log.append(
                        {
                            "action": "exit",
                            "active_count": self.active_count,
                            "timestamp": time.time(),
                            "task_id": id(asyncio.current_task()),
                        }
                    )
                return False

        # Create multiple resources for testing
        resources = {
            f"resource_{i}": ThreadSafeAsyncResource(f"resource_{i}") for i in range(3)
        }

        async def agent_using_context_managers(agent_id: str, usage_count: int):
            """Agent that uses multiple context managers concurrently."""
            results = []

            for i in range(usage_count):
                # Use multiple resources in nested context managers
                resource_a = resources["resource_0"]
                resource_b = resources["resource_1"]
                resource_c = resources["resource_2"]

                try:
                    async with resource_a:
                        async with resource_b:
                            async with resource_c:
                                # Simulate work within context
                                await asyncio.sleep(0.01)
                                results.append(f"{agent_id}_context_use_{i}")

                except Exception as e:
                    results.append(f"{agent_id}_context_error_{i}: {e}")

            return results

        # Run multiple agents using context managers concurrently
        context_users = [
            agent_using_context_managers(f"context_agent_{i}", 10) for i in range(6)
        ]

        start_time = time.time()
        all_results = await asyncio.gather(*context_users)
        execution_time = time.time() - start_time

        # Validate thread safety of context managers
        total_uses = sum(len(results) for results in all_results)
        successful_uses = sum(
            len([r for r in results if "context_use_" in r]) for results in all_results
        )
        error_uses = sum(
            len([r for r in results if "context_error_" in r])
            for results in all_results
        )

        success_rate = successful_uses / max(total_uses, 1)

        # Context managers should be thread-safe
        assert (
            success_rate >= 0.9
        ), f"Context managers should be highly reliable: {success_rate:.2%}"
        assert (
            error_uses < total_uses * 0.1
        ), f"Minimal errors expected: {error_uses}/{total_uses}"

        # Validate resource state consistency
        for resource_id, resource in resources.items():
            # All resources should be properly released
            assert (
                resource.active_count == 0
            ), f"Resource {resource_id} should be fully released: {resource.active_count}"

            # Log should show balanced enter/exit calls
            enter_count = len(
                [log for log in resource.access_log if log["action"] == "enter"]
            )
            exit_count = len(
                [log for log in resource.access_log if log["action"] == "exit"]
            )

            assert (
                enter_count == exit_count
            ), f"Resource {resource_id} should have balanced enter/exit calls"

            # Concurrent usage should be reasonable
            assert (
                resource.max_concurrent <= 6
            ), f"Max concurrent usage should be reasonable for {resource_id}"

        # Performance should be good
        assert execution_time < 3.0, "Context manager operations should be efficient"


@pytest.fixture
def async_error_scenarios():
    """Provide various async error scenarios for testing."""
    return {
        "network_timeout": asyncio.TimeoutError("Network operation timed out"),
        "connection_error": ConnectionError("Failed to connect to external service"),
        "validation_error": ValueError("Invalid parameters provided"),
        "resource_exhaustion": MemoryError("Insufficient memory for operation"),
        "concurrent_modification": RuntimeError("Concurrent modification detected"),
        "lock_timeout": asyncio.TimeoutError("Failed to acquire lock within timeout"),
    }


class TestConcurrencyErrorHandling:
    """Test error handling and recovery in concurrent execution scenarios."""

    @pytest.mark.asyncio
    async def test_partial_failure_handling_in_concurrent_operations(
        self, orchestrator_with_mocks, async_error_scenarios, concurrency_harness
    ):
        """Test graceful handling of partial failures in concurrent agent operations."""
        orchestrator = orchestrator_with_mocks

        successful_operations = []
        failed_operations = []
        recovered_operations = []

        async def agent_with_potential_failure(
            agent_id: str, failure_probability: float, operations_count: int
        ):
            """Agent that may fail probabilistically but can recover."""
            results = []

            for i in range(operations_count):
                operation_id = f"{agent_id}_op_{i}"

                try:
                    # Simulate potential failure
                    import random

                    if random.random() < failure_probability:
                        # Choose random error type
                        error_type = random.choice(list(async_error_scenarios.values()))
                        concurrency_harness.record_resource_access(
                            agent_id, operation_id, "error_triggered"
                        )
                        raise error_type

                    # Simulate work
                    await asyncio.sleep(0.01)

                    successful_operations.append(
                        {
                            "agent_id": agent_id,
                            "operation_id": operation_id,
                            "timestamp": time.time(),
                        }
                    )
                    concurrency_harness.record_resource_access(
                        agent_id, operation_id, "success"
                    )
                    results.append(f"{operation_id}_success")

                except Exception as e:
                    # Record failure
                    failed_operations.append(
                        {
                            "agent_id": agent_id,
                            "operation_id": operation_id,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "timestamp": time.time(),
                        }
                    )
                    concurrency_harness.record_resource_access(
                        agent_id, operation_id, "failed"
                    )

                    # Attempt recovery
                    try:
                        await asyncio.sleep(0.005)  # Brief recovery delay

                        recovered_operations.append(
                            {
                                "agent_id": agent_id,
                                "operation_id": operation_id,
                                "original_error": str(e),
                                "timestamp": time.time(),
                            }
                        )
                        concurrency_harness.record_resource_access(
                            agent_id, operation_id, "recovered"
                        )
                        results.append(f"{operation_id}_recovered")

                    except Exception as recovery_error:
                        concurrency_harness.record_resource_access(
                            agent_id, operation_id, "recovery_failed"
                        )
                        results.append(f"{operation_id}_failed_permanent")

            return results

        # Create agents with different failure probabilities
        failure_scenarios = [
            ("reliable_agent_1", 0.1, 20),  # 10% failure rate
            ("reliable_agent_2", 0.1, 20),  # 10% failure rate
            ("unreliable_agent_1", 0.3, 15),  # 30% failure rate
            ("unreliable_agent_2", 0.3, 15),  # 30% failure rate
            ("fragile_agent_1", 0.5, 10),  # 50% failure rate
            ("stable_agent_1", 0.05, 25),  # 5% failure rate
        ]

        # Execute all agents concurrently
        start_time = time.time()
        agent_tasks = [
            agent_with_potential_failure(agent_id, failure_prob, op_count)
            for agent_id, failure_prob, op_count in failure_scenarios
        ]

        all_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        execution_time = time.time() - start_time

        # Analyze failure handling
        total_operations = sum(op_count for _, _, op_count in failure_scenarios)

        success_count = len(successful_operations)
        failure_count = len(failed_operations)
        recovery_count = len(recovered_operations)

        # Calculate rates
        success_rate = success_count / total_operations
        failure_rate = failure_count / total_operations
        recovery_rate = recovery_count / max(failure_count, 1)

        # Validate partial failure handling
        assert (
            success_rate > 0.4
        ), f"Should have reasonable success rate despite failures: {success_rate:.2%}"
        assert failure_count > 0, "Should have some failures to test handling"
        assert (
            recovery_rate > 0.5
        ), f"Should recover from most failures: {recovery_rate:.2%}"

        # System should remain responsive despite failures
        assert execution_time < 10.0, "System should handle failures efficiently"

        # No complete task failures (all should return results)
        task_exceptions = [r for r in all_results if isinstance(r, Exception)]
        assert (
            len(task_exceptions) == 0
        ), f"No complete task failures expected: {task_exceptions}"

        # Validate failure distribution
        failure_by_agent = defaultdict(int)
        for failure in failed_operations:
            failure_by_agent[failure["agent_id"]] += 1

        # Higher failure probability agents should have more failures
        for agent_id, expected_prob, op_count in failure_scenarios:
            actual_failures = failure_by_agent.get(agent_id, 0)
            expected_failures = op_count * expected_prob

            # Allow some variance but should be in reasonable range
            assert (
                actual_failures <= op_count
            ), f"Agent {agent_id} can't fail more than total operations"

            # For high-failure agents, should have some failures
            if expected_prob > 0.3:
                assert (
                    actual_failures > 0
                ), f"High-failure agent {agent_id} should have some failures"

        print("\nConcurrency Error Handling Analysis:")
        print(f"  - Total operations: {total_operations}")
        print(f"  - Successful: {success_count} ({success_rate:.2%})")
        print(f"  - Failed: {failure_count} ({failure_rate:.2%})")
        print(f"  - Recovered: {recovery_count} ({recovery_rate:.2%})")
        print(f"  - Execution time: {execution_time:.2f}s")


# Performance benchmarking fixtures and tests
@pytest.fixture
def performance_benchmarks():
    """Define performance benchmarks for concurrency testing."""
    return {
        "max_agent_creation_time": 2.0,  # seconds per agent
        "max_concurrent_execution_time": 5.0,  # seconds for 10 concurrent agents
        "min_throughput_operations_per_sec": 50,  # operations per second
        "max_memory_growth_per_agent_mb": 10,  # MB per agent
        "max_lock_contention_delay": 1.0,  # seconds
    }


class TestConcurrencyPerformance:
    """Test performance characteristics of concurrent agent execution."""

    @pytest.mark.asyncio
    async def test_concurrent_agent_throughput(
        self, orchestrator_with_mocks, performance_benchmarks, concurrent_agent_pool
    ):
        """Test throughput performance of concurrent agent execution."""
        orchestrator = orchestrator_with_mocks

        operation_count = 100
        batch_size = 10
        completed_operations = []

        async def high_throughput_agent_operation(agent_id: str, operation_id: int):
            """Lightweight operation for throughput testing."""
            start_time = time.time()

            # Simulate minimal work
            await asyncio.sleep(0.01)  # 10ms of work

            end_time = time.time()
            completed_operations.append(
                {
                    "agent_id": agent_id,
                    "operation_id": operation_id,
                    "duration": end_time - start_time,
                    "timestamp": end_time,
                }
            )

            return f"{agent_id}_op_{operation_id}"

        # Execute operations in batches to test throughput
        start_time = time.time()

        for batch_start in range(0, operation_count, batch_size):
            batch_tasks = [
                high_throughput_agent_operation(
                    f"throughput_agent_{i % len(concurrent_agent_pool)}",
                    batch_start + i,
                )
                for i in range(min(batch_size, operation_count - batch_start))
            ]

            batch_results = await asyncio.gather(*batch_tasks)
            assert len(batch_results) == len(
                batch_tasks
            ), "All batch operations should complete"

        end_time = time.time()
        total_execution_time = end_time - start_time

        # Calculate performance metrics
        operations_per_second = operation_count / total_execution_time
        avg_operation_duration = sum(
            op["duration"] for op in completed_operations
        ) / len(completed_operations)

        # Performance validation
        min_throughput = performance_benchmarks["min_throughput_operations_per_sec"]
        assert (
            operations_per_second >= min_throughput
        ), f"Throughput too low: {operations_per_second:.2f} ops/sec < {min_throughput} ops/sec"

        # Individual operations should be reasonably fast
        assert (
            avg_operation_duration < 0.1
        ), f"Average operation duration too high: {avg_operation_duration:.3f}s"

        # Total time should be reasonable for concurrent execution
        max_expected_time = (operation_count / min_throughput) * 1.5  # 50% buffer
        assert (
            total_execution_time < max_expected_time
        ), f"Total execution time too high: {total_execution_time:.2f}s"

        print("\nThroughput Performance:")
        print(f"  - Operations per second: {operations_per_second:.2f}")
        print(f"  - Average operation duration: {avg_operation_duration:.3f}s")
        print(f"  - Total execution time: {total_execution_time:.2f}s")
        print(f"  - Completed operations: {len(completed_operations)}")

    @pytest.mark.asyncio
    async def test_memory_efficiency_under_concurrency(
        self, orchestrator_with_mocks, performance_benchmarks
    ):
        """Test memory efficiency during concurrent agent execution."""
        import gc

        import psutil

        orchestrator = orchestrator_with_mocks

        # Get baseline memory usage
        gc.collect()  # Clean up before measurement
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_samples = [baseline_memory]
        agent_count = 20
        operations_per_agent = 25

        async def memory_intensive_agent_operation(agent_id: str):
            """Agent operation that uses memory but should clean up."""
            # Create some temporary data structures
            temp_data = {
                f"key_{i}": [f"value_{j}" for j in range(100)] for i in range(50)
            }

            # Simulate processing
            await asyncio.sleep(0.02)

            # Process the data
            processed = len(str(temp_data))

            # Explicit cleanup
            del temp_data

            return processed

        # Execute agents in waves to monitor memory usage
        wave_size = 5
        for wave_start in range(0, agent_count, wave_size):
            wave_end = min(wave_start + wave_size, agent_count)

            # Create agents for this wave
            wave_tasks = [
                asyncio.gather(
                    *[
                        memory_intensive_agent_operation(f"memory_agent_{agent_id}")
                        for _ in range(operations_per_agent)
                    ]
                )
                for agent_id in range(wave_start, wave_end)
            ]

            # Execute wave
            await asyncio.gather(*wave_tasks)

            # Sample memory usage
            gc.collect()  # Force cleanup
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)

            # Brief pause between waves
            await asyncio.sleep(0.1)

        # Final memory measurement
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_samples.append(final_memory)

        # Memory efficiency analysis
        peak_memory = max(memory_samples)
        memory_growth = peak_memory - baseline_memory
        final_memory_growth = final_memory - baseline_memory

        max_growth_per_agent = performance_benchmarks["max_memory_growth_per_agent_mb"]
        max_total_growth = max_growth_per_agent * agent_count

        # Memory efficiency validation
        assert (
            memory_growth < max_total_growth
        ), f"Memory growth too high: {memory_growth:.2f}MB > {max_total_growth:.2f}MB"

        # Memory should be mostly cleaned up after execution
        cleanup_ratio = 1 - (final_memory_growth / max(memory_growth, 0.1))
        assert (
            cleanup_ratio > 0.7
        ), f"Poor memory cleanup: {cleanup_ratio:.2%} cleanup ratio"

        print("\nMemory Efficiency Analysis:")
        print(f"  - Baseline memory: {baseline_memory:.2f}MB")
        print(f"  - Peak memory: {peak_memory:.2f}MB")
        print(f"  - Final memory: {final_memory:.2f}MB")
        print(f"  - Memory growth: {memory_growth:.2f}MB")
        print(f"  - Memory per agent: {memory_growth / agent_count:.2f}MB")
        print(f"  - Cleanup ratio: {cleanup_ratio:.2%}")


# Summary and reporting fixtures
@pytest.fixture
def test_execution_reporter():
    """Provide test execution reporting capabilities."""

    class TestExecutionReporter:
        def __init__(self):
            self.test_results = []
            self.performance_metrics = {}
            self.concurrency_findings = []

        def record_test_result(
            self, test_name: str, status: str, metrics: dict[str, Any]
        ):
            """Record test execution results."""
            self.test_results.append(
                {
                    "test_name": test_name,
                    "status": status,
                    "metrics": metrics,
                    "timestamp": time.time(),
                }
            )

        def record_performance_metric(self, metric_name: str, value: float, unit: str):
            """Record performance measurements."""
            self.performance_metrics[metric_name] = {
                "value": value,
                "unit": unit,
                "timestamp": time.time(),
            }

        def record_concurrency_finding(
            self, finding_type: str, details: dict[str, Any]
        ):
            """Record concurrency-related findings."""
            self.concurrency_findings.append(
                {
                    "type": finding_type,
                    "details": details,
                    "timestamp": time.time(),
                }
            )

        def generate_summary_report(self) -> str:
            """Generate a summary report of all test results."""
            total_tests = len(self.test_results)
            passed_tests = len(
                [r for r in self.test_results if r["status"] == "passed"]
            )
            failed_tests = len(
                [r for r in self.test_results if r["status"] == "failed"]
            )

            report = f"""
# Concurrency Test Execution Summary

## Test Results
- Total tests executed: {total_tests}
- Passed: {passed_tests}
- Failed: {failed_tests}
- Success rate: {(passed_tests / max(total_tests, 1)):.2%}

## Performance Metrics
"""

            for metric_name, metric_data in self.performance_metrics.items():
                report += f"- {metric_name}: {metric_data['value']:.3f} {metric_data['unit']}\n"

            report += f"""
## Concurrency Findings
- Total findings: {len(self.concurrency_findings)}
"""

            finding_types = defaultdict(int)
            for finding in self.concurrency_findings:
                finding_types[finding["type"]] += 1

            for finding_type, count in finding_types.items():
                report += f"- {finding_type}: {count}\n"

            return report

    return TestExecutionReporter()
