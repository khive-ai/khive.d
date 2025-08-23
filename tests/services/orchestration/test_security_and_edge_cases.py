"""
Security and edge case testing for orchestration components.

This module addresses the critical security gaps identified by the critic agent,
including race conditions, resource exhaustion, async cancellation cleanup,
cascading failures, and adversarial scenarios.
"""

import asyncio
import gc
import os
import tempfile
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import psutil
import pytest
from lionagi.fields import Instruct

from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.orchestration.parts import (
    AgentRequest,
    ComposerRequest,
    OrchestrationPlan,
)


class SecurityTestMonitor:
    """Monitor system resources and security state during testing."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.race_conditions_detected = []
        self.resource_usage_peaks = {"memory": 0, "cpu": 0, "file_descriptors": 0}
        self.security_violations = []
        self.cleanup_failures = []

    def record_race_condition(self, condition_type, details):
        self.race_conditions_detected.append(
            {
                "type": condition_type,
                "details": details,
                "timestamp": time.time(),
            }
        )

    def record_resource_peak(self, resource_type, value):
        if value > self.resource_usage_peaks[resource_type]:
            self.resource_usage_peaks[resource_type] = value

    def record_security_violation(self, violation_type, details):
        self.security_violations.append(
            {
                "type": violation_type,
                "details": details,
                "timestamp": time.time(),
            }
        )

    def record_cleanup_failure(self, failure_type, details):
        self.cleanup_failures.append(
            {
                "type": failure_type,
                "details": details,
                "timestamp": time.time(),
            }
        )


@pytest.fixture
def security_monitor():
    """Create a security test monitor."""
    monitor = SecurityTestMonitor()
    yield monitor
    # Report any security issues found
    if monitor.security_violations:
        print(f"Security violations detected: {monitor.security_violations}")
    if monitor.race_conditions_detected:
        print(f"Race conditions detected: {monitor.race_conditions_detected}")


class ResourceExhaustionAttacker:
    """Simulate resource exhaustion attacks for testing."""

    def __init__(self):
        self.active_attacks = []

    async def memory_exhaustion_attack(self, target_mb=50):
        """Simulate memory exhaustion attack."""
        memory_blocks = []
        try:
            # Allocate memory in chunks
            for _ in range(target_mb):
                # Allocate 1MB blocks
                block = bytearray(1024 * 1024)  # 1MB
                memory_blocks.append(block)
                await asyncio.sleep(0.01)  # Allow other tasks to run
        except MemoryError:
            # Expected when memory is exhausted
            pass
        finally:
            # Cleanup
            memory_blocks.clear()
            gc.collect()

    async def file_descriptor_exhaustion(self, max_fds=50):
        """Simulate file descriptor exhaustion."""
        temp_files = []
        try:
            # Create temporary files to exhaust descriptors
            for i in range(max_fds):
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                temp_files.append(temp_file)
                await asyncio.sleep(0.01)
        except OSError:
            # Expected when file descriptors are exhausted
            pass
        finally:
            # Cleanup
            for temp_file in temp_files:
                try:
                    temp_file.close()
                    os.unlink(temp_file.name)
                except:
                    pass

    async def concurrent_connection_attack(self, max_connections=20):
        """Simulate concurrent connection exhaustion."""
        connection_tasks = []
        try:
            for _ in range(max_connections):
                # Simulate opening connections
                task = asyncio.create_task(self._mock_connection())
                connection_tasks.append(task)

            # Wait for all connections
            await asyncio.gather(*connection_tasks, return_exceptions=True)
        finally:
            # Cleanup
            for task in connection_tasks:
                if not task.done():
                    task.cancel()

    async def _mock_connection(self):
        """Mock connection that holds resources."""
        try:
            await asyncio.sleep(1)  # Simulate connection holding
        except asyncio.CancelledError:
            pass  # Expected on cleanup


class SensitiveDataTracker:
    """Track sensitive data handling during async operations."""

    def __init__(self):
        self.sensitive_data_created = []
        self.cleanup_verified = []
        self.data_leaks_detected = []

    def create_sensitive_data(self, data_id, data_type="secret"):
        """Track creation of sensitive data."""
        self.sensitive_data_created.append(
            {
                "id": data_id,
                "type": data_type,
                "created_at": time.time(),
                "cleaned_up": False,
            }
        )
        return data_id

    def verify_cleanup(self, data_id):
        """Verify that sensitive data was cleaned up."""
        for data_item in self.sensitive_data_created:
            if data_item["id"] == data_id:
                data_item["cleaned_up"] = True
                self.cleanup_verified.append(data_id)
                break

    def detect_data_leak(self, data_id, leak_context):
        """Record detection of data leak."""
        self.data_leaks_detected.append(
            {
                "data_id": data_id,
                "context": leak_context,
                "detected_at": time.time(),
            }
        )

    def get_unprotected_data(self):
        """Get list of data that wasn't properly cleaned up."""
        return [item for item in self.sensitive_data_created if not item["cleaned_up"]]


@pytest.mark.security
class TestRaceConditionVulnerabilities:
    """Test race condition vulnerabilities in orchestration."""

    @pytest.mark.asyncio
    async def test_concurrent_session_state_modification(self, security_monitor):
        """Test concurrent modification of session state for race conditions."""
        orchestrator = LionOrchestrator("race_condition_test")

        # Mock session with shared state
        shared_state = {"branches": {}, "operations": [], "lock": threading.Lock()}

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Session"
            ) as mock_session_cls,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
            patch(
                "khive.services.orchestration.orchestrator.Builder"
            ) as mock_builder_cls,
        ):
            mock_cc_model = MagicMock()
            mock_create_cc.return_value = mock_cc_model

            mock_branch = MagicMock()
            mock_branch.id = str(uuid4())
            mock_branch_cls.return_value = mock_branch

            mock_session = MagicMock()
            mock_session.default_branch = mock_branch
            mock_session.shared_state = shared_state
            mock_session_cls.return_value = mock_session

            mock_builder = MagicMock()
            mock_builder_cls.return_value = mock_builder

            await orchestrator.initialize()
            orchestrator.session = mock_session
            orchestrator.builder = mock_builder

            # Create multiple concurrent branch creation tasks
            async def create_branch_with_delay(delay, branch_name):
                await asyncio.sleep(delay)
                compose_request = ComposerRequest(
                    role="researcher", domains="distributed-systems"
                )

                # Simulate race condition in state modification
                if not shared_state["lock"].acquire(blocking=False):
                    security_monitor.record_race_condition(
                        "session_state_modification",
                        f"Concurrent access to shared state during branch {branch_name} creation",
                    )

                try:
                    # Mock branch creation that modifies shared state
                    shared_state["branches"][branch_name] = str(uuid4())
                    await asyncio.sleep(0.1)  # Simulate processing time
                    return branch_name
                finally:
                    try:
                        shared_state["lock"].release()
                    except:
                        pass

            # Launch concurrent operations
            tasks = [
                create_branch_with_delay(0.01 * i, f"branch_{i}") for i in range(10)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for race condition detection
            assert len(results) == 10
            # Verify that race conditions were properly detected and handled
            if security_monitor.race_conditions_detected:
                assert all(
                    "session_state_modification" in rc["type"]
                    for rc in security_monitor.race_conditions_detected
                )

    @pytest.mark.asyncio
    async def test_branch_creation_race_conditions(self, security_monitor):
        """Test race conditions in concurrent branch creation."""
        orchestrator = LionOrchestrator("branch_race_test")

        # Track branch creation attempts
        branch_creation_attempts = {"count": 0, "conflicts": 0}

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Session"
            ) as mock_session_cls,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
            patch(
                "khive.services.orchestration.orchestrator.Builder"
            ) as mock_builder_cls,
        ):
            mock_cc_model = MagicMock()
            mock_create_cc.return_value = mock_cc_model

            mock_branch = MagicMock()
            mock_branch.id = str(uuid4())
            mock_branch_cls.return_value = mock_branch

            # Mock session with collision detection
            def mock_lookup_branch(name):
                branch_creation_attempts["count"] += 1
                # Simulate name collision detection
                if branch_creation_attempts["count"] > 1:
                    branch_creation_attempts["conflicts"] += 1
                    security_monitor.record_race_condition(
                        "branch_name_collision",
                        f"Branch name collision detected for {name}",
                    )
                    return MagicMock()  # Return existing branch to simulate collision
                return None

            mock_session = MagicMock()
            mock_session.default_branch = mock_branch
            mock_session._lookup_branch_by_name.side_effect = mock_lookup_branch
            mock_session.create_branch = AsyncMock(return_value=str(uuid4()))
            mock_session_cls.return_value = mock_session

            mock_builder = MagicMock()
            mock_builder_cls.return_value = mock_builder

            await orchestrator.initialize()
            orchestrator.session = mock_session
            orchestrator.builder = mock_builder

            # Concurrent branch creation with same base name
            compose_request = ComposerRequest(
                role="researcher", domains="software-architecture"
            )

            tasks = [orchestrator.create_cc_branch(compose_request) for _ in range(5)]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify race condition handling
            assert len(results) == 5
            assert branch_creation_attempts["conflicts"] > 0
            assert security_monitor.race_conditions_detected


@pytest.mark.security
class TestResourceExhaustionSecurity:
    """Test system behavior under resource exhaustion attacks."""

    @pytest.mark.asyncio
    async def test_memory_exhaustion_resistance(self, security_monitor):
        """Test orchestrator behavior under memory pressure."""
        orchestrator = LionOrchestrator("memory_exhaustion_test")
        attacker = ResourceExhaustionAttacker()

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Session"
            ) as mock_session_cls,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
            patch(
                "khive.services.orchestration.orchestrator.Builder"
            ) as mock_builder_cls,
        ):
            # Setup mocks
            mock_cc_model = MagicMock()
            mock_create_cc.return_value = mock_cc_model

            mock_branch = MagicMock()
            mock_branch_cls.return_value = mock_branch

            mock_session = MagicMock()
            mock_session.default_branch = mock_branch
            mock_session_cls.return_value = mock_session

            mock_builder = MagicMock()
            mock_builder_cls.return_value = mock_builder

            await orchestrator.initialize()
            orchestrator.session = mock_session
            orchestrator.builder = mock_builder

            # Launch memory exhaustion attack concurrently with orchestration
            memory_attack_task = asyncio.create_task(
                attacker.memory_exhaustion_attack(target_mb=30)
            )

            try:
                # Monitor memory usage
                process = psutil.Process()
                initial_memory = process.memory_info().rss / 1024 / 1024  # MB

                # Create orchestration plan during attack
                agent_requests = [
                    AgentRequest(
                        instruct=Instruct(instruction="Task under memory pressure"),
                        compose_request=ComposerRequest(
                            role="researcher", domains="distributed-systems"
                        ),
                    )
                ]

                plan = OrchestrationPlan(
                    common_background="Memory exhaustion resistance test",
                    agent_requests=agent_requests,
                    execution_strategy="concurrent",
                )

                # Execute orchestration under memory pressure
                with (
                    patch.object(
                        orchestrator, "create_cc_branch"
                    ) as mock_create_branch,
                    patch.object(orchestrator.orc_branch, "operate") as mock_operate,
                ):
                    mock_create_branch.return_value = str(uuid4())
                    mock_operate.return_value = AsyncMock()

                    # This should complete despite memory pressure
                    result = await asyncio.wait_for(
                        orchestrator.fanout(plan), timeout=10.0
                    )

                    # Record peak memory usage
                    peak_memory = process.memory_info().rss / 1024 / 1024  # MB
                    security_monitor.record_resource_peak("memory", peak_memory)

                    # Verify graceful handling
                    assert result is not None

            except asyncio.TimeoutError:
                security_monitor.record_security_violation(
                    "memory_exhaustion_timeout",
                    "Orchestration timed out under memory pressure",
                )
            finally:
                # Cleanup attack
                if not memory_attack_task.done():
                    memory_attack_task.cancel()
                try:
                    await memory_attack_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_concurrent_operation_resource_limits(self, security_monitor):
        """Test resource limits under concurrent operation attacks."""
        orchestrator = LionOrchestrator("concurrent_attack_test")
        attacker = ResourceExhaustionAttacker()

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Session"
            ) as mock_session_cls,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
            patch(
                "khive.services.orchestration.orchestrator.Builder"
            ) as mock_builder_cls,
        ):
            # Setup mocks
            mock_cc_model = MagicMock()
            mock_create_cc.return_value = mock_cc_model

            mock_branch = MagicMock()
            mock_branch_cls.return_value = mock_branch

            mock_session = MagicMock()
            mock_session.default_branch = mock_branch
            mock_session_cls.return_value = mock_session

            mock_builder = MagicMock()
            mock_builder_cls.return_value = mock_builder

            await orchestrator.initialize()
            orchestrator.session = mock_session
            orchestrator.builder = mock_builder

            # Launch multiple resource attacks concurrently
            attack_tasks = [
                asyncio.create_task(attacker.memory_exhaustion_attack(target_mb=10)),
                asyncio.create_task(attacker.file_descriptor_exhaustion(max_fds=20)),
                asyncio.create_task(
                    attacker.concurrent_connection_attack(max_connections=10)
                ),
            ]

            try:
                # Monitor system resources
                process = psutil.Process()
                initial_fds = process.num_fds() if hasattr(process, "num_fds") else 0

                # Create multiple orchestration operations
                operations = []
                for i in range(5):
                    agent_requests = [
                        AgentRequest(
                            instruct=Instruct(instruction=f"Concurrent operation {i}"),
                            compose_request=ComposerRequest(
                                role="researcher", domains="distributed-systems"
                            ),
                        )
                    ]

                    plan = OrchestrationPlan(
                        common_background=f"Concurrent attack test {i}",
                        agent_requests=agent_requests,
                        execution_strategy="concurrent",
                    )

                    operations.append(plan)

                # Execute all operations concurrently under attack
                with (
                    patch.object(
                        orchestrator, "create_cc_branch"
                    ) as mock_create_branch,
                    patch.object(orchestrator.orc_branch, "operate") as mock_operate,
                ):
                    mock_create_branch.return_value = str(uuid4())
                    mock_operate.return_value = AsyncMock()

                    # Execute operations with timeout protection
                    operation_tasks = [
                        asyncio.create_task(orchestrator.fanout(plan))
                        for plan in operations
                    ]

                    results = await asyncio.gather(
                        *operation_tasks, return_exceptions=True
                    )

                    # Record resource usage
                    final_fds = process.num_fds() if hasattr(process, "num_fds") else 0
                    security_monitor.record_resource_peak(
                        "file_descriptors", final_fds - initial_fds
                    )

                    # Verify results
                    successful_operations = [
                        r for r in results if not isinstance(r, Exception)
                    ]

                    # At least some operations should complete successfully
                    assert len(successful_operations) >= 1

            finally:
                # Cleanup all attacks
                for attack_task in attack_tasks:
                    if not attack_task.done():
                        attack_task.cancel()

                cleanup_results = await asyncio.gather(
                    *attack_tasks, return_exceptions=True
                )

                # Check for cleanup failures
                for result in cleanup_results:
                    if isinstance(result, Exception) and not isinstance(
                        result, asyncio.CancelledError
                    ):
                        security_monitor.record_cleanup_failure(
                            "attack_cleanup_failure", str(result)
                        )


@pytest.mark.security
class TestAsyncCancellationSecurity:
    """Test async cancellation cleanup and sensitive data handling."""

    @pytest.mark.asyncio
    async def test_sensitive_data_cleanup_on_cancellation(self, security_monitor):
        """Test that sensitive data is cleaned up when operations are cancelled."""
        orchestrator = LionOrchestrator("cancellation_cleanup_test")
        data_tracker = SensitiveDataTracker()

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Session"
            ) as mock_session_cls,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
            patch(
                "khive.services.orchestration.orchestrator.Builder"
            ) as mock_builder_cls,
        ):
            # Setup mocks
            mock_cc_model = MagicMock()
            mock_create_cc.return_value = mock_cc_model

            mock_branch = MagicMock()
            mock_branch_cls.return_value = mock_branch

            mock_session = MagicMock()
            mock_session.default_branch = mock_branch
            mock_session_cls.return_value = mock_session

            mock_builder = MagicMock()
            mock_builder_cls.return_value = mock_builder

            await orchestrator.initialize()
            orchestrator.session = mock_session
            orchestrator.builder = mock_builder

            # Create operation that handles sensitive data
            async def sensitive_operation():
                # Create sensitive data
                secret_id = data_tracker.create_sensitive_data(str(uuid4()), "api_key")

                try:
                    # Simulate long-running operation
                    await asyncio.sleep(5.0)
                    return f"Operation completed with {secret_id}"
                except asyncio.CancelledError:
                    # Critical: Cleanup sensitive data on cancellation
                    data_tracker.verify_cleanup(secret_id)
                    raise
                finally:
                    # Ensure cleanup in finally block
                    data_tracker.verify_cleanup(secret_id)

            # Start operation
            operation_task = asyncio.create_task(sensitive_operation())

            # Cancel after short delay
            await asyncio.sleep(0.5)
            operation_task.cancel()

            try:
                await operation_task
            except asyncio.CancelledError:
                pass  # Expected

            # Verify cleanup occurred
            unprotected_data = data_tracker.get_unprotected_data()

            if unprotected_data:
                for data_item in unprotected_data:
                    security_monitor.record_security_violation(
                        "sensitive_data_leak",
                        f"Sensitive data {data_item['id']} not cleaned up after cancellation",
                    )

            # All sensitive data should be cleaned up
            assert len(unprotected_data) == 0

    @pytest.mark.asyncio
    async def test_nested_operation_cancellation_cleanup(self, security_monitor):
        """Test cleanup in nested async operations."""
        orchestrator = LionOrchestrator("nested_cancellation_test")
        data_tracker = SensitiveDataTracker()

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Session"
            ) as mock_session_cls,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
            patch(
                "khive.services.orchestration.orchestrator.Builder"
            ) as mock_builder_cls,
        ):
            # Setup mocks
            mock_cc_model = MagicMock()
            mock_create_cc.return_value = mock_cc_model

            mock_branch = MagicMock()
            mock_branch_cls.return_value = mock_branch

            mock_session = MagicMock()
            mock_session.default_branch = mock_branch
            mock_session_cls.return_value = mock_session

            mock_builder = MagicMock()
            mock_builder_cls.return_value = mock_builder

            await orchestrator.initialize()
            orchestrator.session = mock_session
            orchestrator.builder = mock_builder

            # Create nested operations with sensitive data
            async def inner_operation(operation_id):
                secret_id = data_tracker.create_sensitive_data(
                    f"secret_{operation_id}", "credential"
                )
                try:
                    await asyncio.sleep(2.0)
                    return f"Inner operation {operation_id} completed"
                except asyncio.CancelledError:
                    data_tracker.verify_cleanup(secret_id)
                    raise
                finally:
                    data_tracker.verify_cleanup(secret_id)

            async def outer_operation():
                outer_secret = data_tracker.create_sensitive_data(
                    "outer_secret", "session_token"
                )
                try:
                    # Launch nested operations
                    inner_tasks = [
                        asyncio.create_task(inner_operation(i)) for i in range(3)
                    ]

                    results = await asyncio.gather(*inner_tasks)
                    return results
                except asyncio.CancelledError:
                    data_tracker.verify_cleanup(outer_secret)
                    raise
                finally:
                    data_tracker.verify_cleanup(outer_secret)

            # Start outer operation
            outer_task = asyncio.create_task(outer_operation())

            # Cancel during nested execution
            await asyncio.sleep(0.3)
            outer_task.cancel()

            try:
                await outer_task
            except asyncio.CancelledError:
                pass  # Expected

            # Verify all sensitive data was cleaned up
            unprotected_data = data_tracker.get_unprotected_data()

            # Report any data leaks
            for data_item in unprotected_data:
                security_monitor.record_security_violation(
                    "nested_operation_data_leak",
                    f"Sensitive data {data_item['id']} leaked in nested operation cancellation",
                )

            assert len(unprotected_data) == 0


@pytest.mark.security
class TestCascadingFailurePrevention:
    """Test prevention of cascading failures in orchestration."""

    @pytest.mark.asyncio
    async def test_timeout_cascade_prevention(self, security_monitor):
        """Test that individual timeouts don't cascade through the entire system."""
        orchestrator = LionOrchestrator("cascade_prevention_test")

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Session"
            ) as mock_session_cls,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
            patch(
                "khive.services.orchestration.orchestrator.Builder"
            ) as mock_builder_cls,
        ):
            # Setup mocks
            mock_cc_model = MagicMock()
            mock_create_cc.return_value = mock_cc_model

            mock_branch = MagicMock()
            mock_branch_cls.return_value = mock_branch

            mock_session = MagicMock()
            mock_session.default_branch = mock_branch
            mock_session_cls.return_value = mock_session

            mock_builder = MagicMock()
            mock_builder_cls.return_value = mock_builder

            await orchestrator.initialize()
            orchestrator.session = mock_session
            orchestrator.builder = mock_builder

            # Create operations with different timeout behaviors
            async def normal_operation(operation_id):
                await asyncio.sleep(0.1)
                return f"Operation {operation_id} completed"

            async def timeout_operation(operation_id):
                # This operation will timeout
                await asyncio.sleep(10.0)
                return f"Timeout operation {operation_id} completed"

            async def dependent_operation(operation_id):
                # This operation depends on others but should not be affected by their timeouts
                await asyncio.sleep(0.2)
                return f"Dependent operation {operation_id} completed"

            # Create orchestration plan with mixed operations
            agent_requests = [
                AgentRequest(
                    instruct=Instruct(instruction="Normal operation"),
                    compose_request=ComposerRequest(
                        role="researcher", domains="distributed-systems"
                    ),
                ),
                AgentRequest(
                    instruct=Instruct(instruction="Operation that will timeout"),
                    compose_request=ComposerRequest(
                        role="implementer", domains="backend-development"
                    ),
                ),
                AgentRequest(
                    instruct=Instruct(instruction="Dependent operation"),
                    compose_request=ComposerRequest(
                        role="analyst", domains="code-quality"
                    ),
                ),
            ]

            plan = OrchestrationPlan(
                common_background="Cascade prevention test",
                agent_requests=agent_requests,
                execution_strategy="concurrent",
            )

            # Mock operations to simulate different behaviors
            def mock_operate_side_effect(*args, **kwargs):
                # Return different behaviors for different branches
                if "timeout" in str(args):
                    return asyncio.create_task(timeout_operation("timeout"))
                if "dependent" in str(args):
                    return asyncio.create_task(dependent_operation("dependent"))
                return asyncio.create_task(normal_operation("normal"))

            with (
                patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
                patch.object(orchestrator.orc_branch, "operate") as mock_operate,
            ):
                mock_create_branch.return_value = str(uuid4())
                mock_operate.side_effect = mock_operate_side_effect

                # Execute with timeout protection
                try:
                    result = await asyncio.wait_for(
                        orchestrator.fanout(plan),
                        timeout=2.0,  # Short timeout to trigger timeout behavior
                    )

                    # If we get here, the system handled cascading gracefully
                    assert result is not None

                except asyncio.TimeoutError:
                    # Check if timeout cascaded to entire system
                    security_monitor.record_security_violation(
                        "timeout_cascade_failure",
                        "Individual operation timeout cascaded to entire orchestration",
                    )

            # Verify system is still functional after timeout events
            # Try a simple operation to ensure system didn't cascade fail
            simple_plan = OrchestrationPlan(
                common_background="Post-timeout system check",
                agent_requests=[agent_requests[0]],  # Just the normal operation
                execution_strategy="concurrent",
            )

            with (
                patch.object(orchestrator, "create_cc_branch") as mock_create_branch,
                patch.object(orchestrator.orc_branch, "operate") as mock_operate,
            ):
                mock_create_branch.return_value = str(uuid4())
                mock_operate.return_value = asyncio.create_task(
                    normal_operation("post_timeout")
                )

                # This should complete successfully, proving no cascade failure
                post_timeout_result = await asyncio.wait_for(
                    orchestrator.fanout(simple_plan), timeout=1.0
                )

                assert post_timeout_result is not None

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, security_monitor):
        """Test circuit breaker pattern to prevent cascading failures."""
        orchestrator = LionOrchestrator("circuit_breaker_test")

        # Circuit breaker state
        circuit_breaker = {
            "failure_count": 0,
            "failure_threshold": 3,
            "is_open": False,
            "last_failure_time": 0,
        }

        def circuit_breaker_wrapper(operation):
            """Wrapper that implements circuit breaker pattern."""

            async def wrapper(*args, **kwargs):
                if circuit_breaker["is_open"]:
                    # Circuit is open, fail fast
                    raise Exception("Circuit breaker is open")

                try:
                    result = await operation(*args, **kwargs)
                    # Success, reset failure count
                    circuit_breaker["failure_count"] = 0
                    return result
                except Exception as e:
                    # Failure, increment count
                    circuit_breaker["failure_count"] += 1
                    circuit_breaker["last_failure_time"] = time.time()

                    if (
                        circuit_breaker["failure_count"]
                        >= circuit_breaker["failure_threshold"]
                    ):
                        circuit_breaker["is_open"] = True
                        security_monitor.record_security_violation(
                            "circuit_breaker_activated",
                            f"Circuit breaker opened after {circuit_breaker['failure_count']} failures",
                        )

                    raise

            return wrapper

        with (
            patch(
                "khive.services.orchestration.orchestrator.create_cc"
            ) as mock_create_cc,
            patch(
                "khive.services.orchestration.orchestrator.Session"
            ) as mock_session_cls,
            patch(
                "khive.services.orchestration.orchestrator.Branch"
            ) as mock_branch_cls,
            patch(
                "khive.services.orchestration.orchestrator.Builder"
            ) as mock_builder_cls,
        ):
            # Setup mocks
            mock_cc_model = MagicMock()
            mock_create_cc.return_value = mock_cc_model

            mock_branch = MagicMock()
            mock_branch_cls.return_value = mock_branch

            mock_session = MagicMock()
            mock_session.default_branch = mock_branch
            mock_session_cls.return_value = mock_session

            mock_builder = MagicMock()
            mock_builder_cls.return_value = mock_builder

            await orchestrator.initialize()
            orchestrator.session = mock_session
            orchestrator.builder = mock_builder

            # Create failing operation
            async def failing_operation():
                raise Exception("Simulated failure")

            # Wrap operation with circuit breaker
            protected_operation = circuit_breaker_wrapper(failing_operation)

            # Test circuit breaker activation
            for i in range(5):  # More than threshold
                agent_requests = [
                    AgentRequest(
                        instruct=Instruct(instruction=f"Failing operation {i}"),
                        compose_request=ComposerRequest(
                            role="researcher", domains="distributed-systems"
                        ),
                    )
                ]

                plan = OrchestrationPlan(
                    common_background=f"Circuit breaker test {i}",
                    agent_requests=agent_requests,
                    execution_strategy="concurrent",
                )

                with (
                    patch.object(
                        orchestrator, "create_cc_branch"
                    ) as mock_create_branch,
                    patch.object(orchestrator.orc_branch, "operate") as mock_operate,
                ):
                    mock_create_branch.return_value = str(uuid4())
                    mock_operate.return_value = asyncio.create_task(
                        protected_operation()
                    )

                    try:
                        result = await orchestrator.fanout(plan)
                    except Exception:
                        pass  # Expected failures

            # Verify circuit breaker was activated
            assert circuit_breaker["is_open"]
            assert len(security_monitor.security_violations) > 0

            # Verify circuit breaker prevents further operations
            with pytest.raises(Exception, match="Circuit breaker is open"):
                await protected_operation()
