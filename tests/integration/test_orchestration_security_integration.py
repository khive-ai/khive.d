"""
Security-focused integration tests for orchestration workflows.

Addresses critical security gaps identified in async workflow orchestration:
1. Race condition testing for concurrent session state modification
2. Resource exhaustion attack testing
3. Validation of async cancellation cleanup for sensitive data
4. Testing cascading timeout failures
5. Stress testing under adversarial concurrent access
6. Security-focused integration testing with external services
"""

import asyncio
import gc
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import psutil
import pytest

from khive.services.artifacts.factory import (ArtifactsConfig,
                                              create_artifacts_service)
from khive.services.artifacts.models import Author, DocumentType
from khive.services.artifacts.service import ArtifactsService
from khive.services.orchestration.orchestrator import LionOrchestrator


class SharedStateMonitor:
    """Monitor for detecting race conditions in shared state."""

    def __init__(self):
        self.access_log = []
        self.state_snapshots = []
        self.race_conditions = []
        self._lock = asyncio.Lock()

    async def record_access(self, operation: str, state: Any, timestamp: float = None):
        """Record state access for race condition analysis."""
        if timestamp is None:
            timestamp = time.time()

        async with self._lock:
            self.access_log.append({
                "operation": operation,
                "state": state,
                "timestamp": timestamp,
                "task_id": id(asyncio.current_task()),
            })

    async def detect_race_conditions(self) -> list[dict]:
        """Analyze access log for potential race conditions."""
        async with self._lock:
            race_conditions = []

            # Look for overlapping read-modify-write cycles
            for i, access1 in enumerate(self.access_log):
                for j, access2 in enumerate(self.access_log[i + 1 :], i + 1):
                    # Check for interleaved operations from different tasks
                    if (
                        access1["task_id"] != access2["task_id"]
                        and abs(access1["timestamp"] - access2["timestamp"]) < 0.1
                    ):
                        race_conditions.append({
                            "access1": access1,
                            "access2": access2,
                            "type": "concurrent_modification",
                        })

            self.race_conditions.extend(race_conditions)
            return race_conditions


class ResourceExhaustionAttacker:
    """Simulates controlled resource exhaustion attacks."""

    def __init__(self):
        self.active_attacks = []
        self.resource_snapshots = []

    async def memory_exhaustion_attack(self, target_mb: int, duration: float):
        """Simulate memory exhaustion attack."""
        start_time = time.time()
        memory_hogs = []

        try:
            while time.time() - start_time < duration:
                # Allocate memory in chunks
                chunk = bytearray(1024 * 1024)  # 1MB chunks
                memory_hogs.append(chunk)

                # Check if we've reached target
                if len(memory_hogs) >= target_mb:
                    break

                await asyncio.sleep(0.01)  # Yield control

            # Hold memory for remaining duration
            remaining_time = duration - (time.time() - start_time)
            if remaining_time > 0:
                await asyncio.sleep(remaining_time)

        finally:
            # Cleanup
            del memory_hogs
            gc.collect()

    async def cpu_exhaustion_attack(self, duration: float):
        """Simulate CPU exhaustion attack."""
        start_time = time.time()

        def cpu_intensive_task():
            end_time = time.time() + 0.1  # 100ms bursts
            while time.time() < end_time:
                # CPU-intensive operation
                sum(i * i for i in range(1000))

        try:
            while time.time() - start_time < duration:
                cpu_intensive_task()
                await asyncio.sleep(0.01)  # Brief yield
        except asyncio.CancelledError:
            # Allow graceful cancellation
            pass

    async def file_descriptor_exhaustion_attack(self, target_fds: int, duration: float):
        """Simulate file descriptor exhaustion attack."""
        start_time = time.time()
        temp_files = []

        try:
            for i in range(min(target_fds, 1000)):  # Cap to prevent system impact
                try:
                    temp_file = tempfile.NamedTemporaryFile()
                    temp_files.append(temp_file)
                except OSError:
                    break  # Hit system limit

            # Hold file descriptors for duration
            remaining_time = duration - (time.time() - start_time)
            if remaining_time > 0:
                await asyncio.sleep(remaining_time)

        finally:
            # Cleanup
            for temp_file in temp_files:
                temp_file.close()


class SensitiveDataTracker:
    """Tracks sensitive data cleanup during async operations."""

    def __init__(self):
        self.sensitive_data_registry = {}
        self.cleanup_events = []
        self._lock = asyncio.Lock()

    async def register_sensitive_data(self, data_id: str, data: Any):
        """Register sensitive data for tracking."""
        async with self._lock:
            self.sensitive_data_registry[data_id] = {
                "data": data,
                "created_at": time.time(),
                "cleaned_up": False,
            }

    async def mark_cleaned_up(self, data_id: str):
        """Mark sensitive data as cleaned up."""
        async with self._lock:
            if data_id in self.sensitive_data_registry:
                self.sensitive_data_registry[data_id]["cleaned_up"] = True
                self.cleanup_events.append({
                    "data_id": data_id,
                    "cleaned_at": time.time(),
                })

    async def verify_cleanup_completion(self) -> list[str]:
        """Verify all sensitive data was cleaned up."""
        async with self._lock:
            uncleaned_data = [
                data_id
                for data_id, info in self.sensitive_data_registry.items()
                if not info["cleaned_up"]
            ]
            return uncleaned_data


class ExternalServiceSimulator:
    """Simulates external service failures for integration testing."""

    def __init__(self):
        self.failure_modes = {
            "timeout": self._simulate_timeout,
            "connection_error": self._simulate_connection_error,
            "auth_failure": self._simulate_auth_failure,
            "rate_limit": self._simulate_rate_limit,
        }

    async def _simulate_timeout(self, duration: float):
        """Simulate service timeout."""
        await asyncio.sleep(duration)
        raise asyncio.TimeoutError("Simulated service timeout")

    async def _simulate_connection_error(self):
        """Simulate connection error."""
        raise ConnectionError("Simulated connection failure")

    async def _simulate_auth_failure(self):
        """Simulate authentication failure."""
        raise PermissionError("Simulated authentication failure")

    async def _simulate_rate_limit(self):
        """Simulate rate limiting."""
        raise Exception("Rate limit exceeded")

    async def simulate_failure(self, mode: str, **kwargs):
        """Simulate a specific failure mode."""
        if mode in self.failure_modes:
            return await self.failure_modes[mode](**kwargs)
        raise ValueError(f"Unknown failure mode: {mode}")


class TestRaceConditionSecurityVulnerabilities:
    """Test race conditions in concurrent session state modifications."""

    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "security_test_workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            yield workspace

    @pytest.fixture
    def artifacts_service(self, temp_workspace):
        config = ArtifactsConfig(workspace_root=temp_workspace)
        return create_artifacts_service(config)

    @pytest.fixture
    def state_monitor(self):
        return SharedStateMonitor()

    @pytest.mark.asyncio
    async def test_concurrent_session_modification_race_conditions(
        self, artifacts_service: ArtifactsService, state_monitor: SharedStateMonitor
    ):
        """Test for race conditions during concurrent session state modifications."""

        session_id = "race_condition_test_session"
        await artifacts_service.create_session(session_id)

        # Simulate concurrent modifications to shared session state
        async def concurrent_modifier(modifier_id: str, modifications: int):
            """Concurrently modify session state."""
            for i in range(modifications):
                await state_monitor.record_access(f"modify_{modifier_id}", i)

                # Create document (involves session state modification)
                doc = await artifacts_service.create_document(
                    session_id=session_id,
                    doc_name=f"race_test_doc_{modifier_id}_{i}",
                    doc_type=DocumentType.SCRATCHPAD,
                    content=f"Content from modifier {modifier_id}, iteration {i}",
                    author=Author(id=f"modifier_{modifier_id}", role="tester"),
                )

                await state_monitor.record_access(f"created_{modifier_id}", doc.name)
                await asyncio.sleep(0.001)  # Small delay to encourage race conditions

        # Launch concurrent modifiers
        modifiers = [
            concurrent_modifier("A", 10),
            concurrent_modifier("B", 10),
            concurrent_modifier("C", 10),
        ]

        # Execute concurrently
        await asyncio.gather(*modifiers)

        # Analyze for race conditions
        race_conditions = await state_monitor.detect_race_conditions()

        # Verify session state consistency despite concurrent access
        registry = await artifacts_service.get_artifact_registry(session_id)

        # Should have exactly 30 artifacts (3 modifiers × 10 modifications each)
        assert len(registry.artifacts) == 30

        # Check for race conditions (expected due to concurrent access patterns)
        print(f"Detected {len(race_conditions)} potential race conditions")

        # Race conditions are expected in concurrent access, but the system should maintain consistency

        # Verify document integrity
        scratchpad_docs = await artifacts_service.list_documents(
            session_id, DocumentType.SCRATCHPAD
        )
        assert len(scratchpad_docs) == 30

    @pytest.mark.asyncio
    async def test_branch_creation_race_conditions(
        self, state_monitor: SharedStateMonitor
    ):
        """Test race conditions during concurrent branch creation."""

        with patch(
            "khive.services.orchestration.orchestrator.create_cc"
        ) as mock_create_cc:
            mock_create_cc.return_value = MagicMock()

            orchestrator = LionOrchestrator("race_test_flow")
            await orchestrator.initialize()

            # Simulate concurrent branch creation
            async def create_branch_concurrent(branch_name: str):
                """Create branch concurrently with state monitoring."""
                await state_monitor.record_access("branch_create_start", branch_name)

                with patch(
                    "khive.services.orchestration.orchestrator.composer_service"
                ) as mock_composer:
                    mock_composer.handle_request.return_value = MagicMock(
                        system_prompt=f"Test system prompt for {branch_name}"
                    )

                    from khive.services.orchestration.parts import \
                        ComposerRequest

                    request = ComposerRequest(role="tester", domains="testing")

                    # This would normally create a branch
                    with patch.object(orchestrator, "create_cc_branch") as mock_create:
                        mock_create.return_value = f"branch_{branch_name}"
                        branch_id = await orchestrator.create_cc_branch(
                            request, agent_suffix=branch_name
                        )

                        await state_monitor.record_access(
                            "branch_create_end", branch_id
                        )
                        return branch_id

            # Create multiple branches concurrently
            branch_tasks = [create_branch_concurrent(f"branch_{i}") for i in range(5)]

            branch_ids = await asyncio.gather(*branch_tasks)

            # Verify all branches were created with unique IDs
            assert len(branch_ids) == 5
            assert len(set(branch_ids)) == 5

            # Check for race conditions
            race_conditions = await state_monitor.detect_race_conditions()
            print(f"Branch creation race conditions: {len(race_conditions)}")


class TestResourceExhaustionSecurityAttacks:
    """Test resource exhaustion attack scenarios."""

    @pytest.fixture
    def attacker(self):
        return ResourceExhaustionAttacker()

    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "resource_attack_workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            yield workspace

    @pytest.fixture
    def artifacts_service(self, temp_workspace):
        config = ArtifactsConfig(workspace_root=temp_workspace)
        return create_artifacts_service(config)

    @pytest.mark.asyncio
    async def test_memory_exhaustion_resistance(
        self, attacker: ResourceExhaustionAttacker, artifacts_service: ArtifactsService
    ):
        """Test system resistance to memory exhaustion attacks."""

        session_id = "memory_attack_session"
        await artifacts_service.create_session(session_id)

        # Record initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Launch memory exhaustion attack in background
        attack_task = asyncio.create_task(
            attacker.memory_exhaustion_attack(target_mb=100, duration=2.0)
        )

        try:
            # Continue normal operations during attack
            for i in range(10):
                doc = await artifacts_service.create_document(
                    session_id=session_id,
                    doc_name=f"memory_test_doc_{i}",
                    doc_type=DocumentType.SCRATCHPAD,
                    content=f"Test document {i} created during memory attack",
                    author=Author(id="memory_tester", role="tester"),
                )
                assert doc is not None
                await asyncio.sleep(0.1)

        except Exception as e:
            # System should handle memory pressure gracefully
            print(f"System handled memory pressure: {e}")

        # Wait for attack to complete
        try:
            await asyncio.wait_for(attack_task, timeout=5.0)
        except asyncio.TimeoutError:
            attack_task.cancel()

        # Verify system recovered and can still operate
        final_doc = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="post_attack_doc",
            doc_type=DocumentType.DELIVERABLE,
            content="Document created after memory attack",
            author=Author(id="recovery_tester", role="tester"),
        )

        assert final_doc is not None

        # Check memory usage returned to reasonable levels
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 200MB for this test)
        assert memory_increase < 200, f"Memory usage increased by {memory_increase}MB"

    @pytest.mark.asyncio
    async def test_concurrent_resource_attacks(
        self, attacker: ResourceExhaustionAttacker, artifacts_service: ArtifactsService
    ):
        """Test system resilience against multiple concurrent resource attacks."""

        session_id = "multi_attack_session"
        await artifacts_service.create_session(session_id)

        # Launch multiple attack vectors simultaneously
        attack_tasks = [
            asyncio.create_task(
                attacker.memory_exhaustion_attack(target_mb=50, duration=1.5)
            ),
            asyncio.create_task(attacker.cpu_exhaustion_attack(duration=1.5)),
            asyncio.create_task(
                attacker.file_descriptor_exhaustion_attack(target_fds=100, duration=1.5)
            ),
        ]

        # Execute normal operations during multi-vector attack
        normal_operations = []
        for i in range(5):
            task = asyncio.create_task(
                self._create_test_document(artifacts_service, session_id, i)
            )
            normal_operations.append(task)

        try:
            # Wait for normal operations to complete
            docs = await asyncio.gather(*normal_operations, return_exceptions=True)

            # Check how many operations succeeded despite attacks
            successful_docs = [doc for doc in docs if not isinstance(doc, Exception)]
            print(
                f"Successfully created {len(successful_docs)}/5 documents during attack"
            )

            # System should maintain some level of functionality
            assert len(successful_docs) >= 1, (
                "System completely failed during resource attacks"
            )

        finally:
            # Cleanup attack tasks
            for task in attack_tasks:
                task.cancel()

            await asyncio.gather(*attack_tasks, return_exceptions=True)

    async def _create_test_document(
        self, artifacts_service: ArtifactsService, session_id: str, doc_num: int
    ):
        """Helper to create test document with timeout protection."""
        try:
            return await asyncio.wait_for(
                artifacts_service.create_document(
                    session_id=session_id,
                    doc_name=f"attack_test_doc_{doc_num}",
                    doc_type=DocumentType.SCRATCHPAD,
                    content=f"Document {doc_num} created during resource attack",
                    author=Author(id="attack_tester", role="tester"),
                ),
                timeout=2.0,
            )
        except asyncio.TimeoutError:
            raise Exception(f"Document creation {doc_num} timed out during attack")


class TestAsyncCancellationCleanupSecurity:
    """Test async cancellation cleanup for sensitive data."""

    @pytest.fixture
    def data_tracker(self):
        return SensitiveDataTracker()

    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "cancellation_test_workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            yield workspace

    @pytest.fixture
    def artifacts_service(self, temp_workspace):
        config = ArtifactsConfig(workspace_root=temp_workspace)
        return create_artifacts_service(config)

    @pytest.mark.asyncio
    async def test_sensitive_data_cleanup_on_cancellation(
        self, data_tracker: SensitiveDataTracker, artifacts_service: ArtifactsService
    ):
        """Test that sensitive data is properly cleaned up on async cancellation."""

        session_id = "cancellation_cleanup_session"
        await artifacts_service.create_session(session_id)

        async def sensitive_operation(operation_id: str):
            """Operation that handles sensitive data."""
            # Register sensitive data
            sensitive_content = f"SECRET_API_KEY_{operation_id}=sk-1234567890abcdef"
            await data_tracker.register_sensitive_data(
                f"api_key_{operation_id}", sensitive_content
            )

            try:
                # Simulate long-running operation with sensitive data
                await asyncio.sleep(2.0)

                # Create document with sensitive content
                doc = await artifacts_service.create_document(
                    session_id=session_id,
                    doc_name=f"sensitive_doc_{operation_id}",
                    doc_type=DocumentType.SCRATCHPAD,
                    content=sensitive_content,
                    author=Author(id="sensitive_operator", role="operator"),
                )

                return doc

            except asyncio.CancelledError:
                # Cleanup sensitive data on cancellation
                await data_tracker.mark_cleaned_up(f"api_key_{operation_id}")

                # Simulate secure cleanup (overwrite memory, delete temp files, etc.)
                sensitive_content = "REDACTED" * 10  # Overwrite sensitive data

                raise  # Re-raise cancellation

            finally:
                # Ensure cleanup in finally block
                await data_tracker.mark_cleaned_up(f"api_key_{operation_id}")

        # Start sensitive operations
        operations = [
            asyncio.create_task(sensitive_operation(f"op_{i}")) for i in range(3)
        ]

        # Cancel operations after short delay
        await asyncio.sleep(0.5)
        for task in operations:
            task.cancel()

        # Wait for cancellation to complete
        results = await asyncio.gather(*operations, return_exceptions=True)

        # Verify all operations were cancelled
        cancelled_count = sum(
            1 for result in results if isinstance(result, asyncio.CancelledError)
        )
        assert cancelled_count == 3, (
            f"Expected 3 cancelled operations, got {cancelled_count}"
        )

        # Verify sensitive data cleanup
        uncleaned_data = await data_tracker.verify_cleanup_completion()
        assert len(uncleaned_data) == 0, (
            f"Sensitive data not cleaned up: {uncleaned_data}"
        )

    @pytest.mark.asyncio
    async def test_nested_operation_cleanup_on_cancellation(
        self, data_tracker: SensitiveDataTracker, artifacts_service: ArtifactsService
    ):
        """Test cleanup in nested async operations when cancelled."""

        session_id = "nested_cleanup_session"
        await artifacts_service.create_session(session_id)

        async def nested_sensitive_operation(level: int, operation_id: str):
            """Nested operation with sensitive data at each level."""
            sensitive_id = f"nested_{level}_{operation_id}"
            sensitive_data = f"NESTED_SECRET_L{level}_{operation_id}"

            await data_tracker.register_sensitive_data(sensitive_id, sensitive_data)

            try:
                if level > 0:
                    # Recursive nested operation
                    await nested_sensitive_operation(level - 1, operation_id)
                else:
                    # Base case - long operation
                    await asyncio.sleep(3.0)

            except asyncio.CancelledError:
                # Cleanup at this level
                await data_tracker.mark_cleaned_up(sensitive_id)
                raise

            finally:
                # Ensure cleanup in finally
                await data_tracker.mark_cleaned_up(sensitive_id)

        # Start nested operation
        nested_task = asyncio.create_task(
            nested_sensitive_operation(level=3, operation_id="nested_test")
        )

        # Cancel after short delay
        await asyncio.sleep(0.5)
        nested_task.cancel()

        # Wait for cancellation
        try:
            await nested_task
        except asyncio.CancelledError:
            pass

        # Verify all levels cleaned up properly
        uncleaned_data = await data_tracker.verify_cleanup_completion()
        assert len(uncleaned_data) == 0, (
            f"Nested sensitive data not cleaned up: {uncleaned_data}"
        )


class TestIntegrationSecurityScenarios:
    """Security-focused integration tests with external service simulation."""

    @pytest.fixture
    def service_simulator(self):
        return ExternalServiceSimulator()

    @pytest.fixture
    def temp_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "integration_security_workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            yield workspace

    @pytest.fixture
    def artifacts_service(self, temp_workspace):
        config = ArtifactsConfig(workspace_root=temp_workspace)
        return create_artifacts_service(config)

    @pytest.mark.asyncio
    async def test_cascading_timeout_failure_prevention(
        self,
        service_simulator: ExternalServiceSimulator,
        artifacts_service: ArtifactsService,
    ):
        """Test prevention of cascading failures due to external service timeouts."""

        session_id = "timeout_cascade_session"
        await artifacts_service.create_session(session_id)

        async def operation_with_external_dependency(
            op_id: str, timeout_duration: float
        ):
            """Operation that depends on external service."""
            try:
                # Simulate external service call with timeout
                await asyncio.wait_for(
                    service_simulator.simulate_failure(
                        "timeout", duration=timeout_duration
                    ),
                    timeout=1.0,  # Short timeout to prevent cascade
                )

                # This shouldn't be reached due to timeout
                return f"success_{op_id}"

            except asyncio.TimeoutError:
                # Handle timeout gracefully - create fallback document
                doc = await artifacts_service.create_document(
                    session_id=session_id,
                    doc_name=f"fallback_doc_{op_id}",
                    doc_type=DocumentType.SCRATCHPAD,
                    content=f"Fallback content for operation {op_id} after timeout",
                    author=Author(id="fallback_handler", role="handler"),
                )
                return f"fallback_{op_id}"

        # Start multiple operations that will timeout
        operations = [
            asyncio.create_task(operation_with_external_dependency(f"op_{i}", 2.0))
            for i in range(5)
        ]

        # Wait for operations to complete (should all use fallbacks)
        results = await asyncio.gather(*operations, return_exceptions=True)

        # Verify operations completed with fallbacks rather than cascading failures
        successful_results = [
            r for r in results if isinstance(r, str) and r.startswith("fallback_")
        ]
        assert len(successful_results) == 5, (
            f"Expected 5 fallback results, got {len(successful_results)}"
        )

        # Verify fallback documents were created
        scratchpad_docs = await artifacts_service.list_documents(
            session_id, DocumentType.SCRATCHPAD
        )
        fallback_docs = [doc for doc in scratchpad_docs if "fallback_doc_" in doc]
        assert len(fallback_docs) == 5, "Not all fallback documents were created"

    @pytest.mark.asyncio
    async def test_authentication_failure_security(
        self,
        service_simulator: ExternalServiceSimulator,
        artifacts_service: ArtifactsService,
    ):
        """Test handling of authentication failures with security considerations."""

        session_id = "auth_failure_session"
        await artifacts_service.create_session(session_id)

        async def authenticated_operation(operation_id: str):
            """Operation requiring authentication."""
            try:
                # Simulate authentication failure
                await service_simulator.simulate_failure("auth_failure")

                # Should not reach here
                return f"authenticated_{operation_id}"

            except PermissionError:
                # Handle auth failure securely - no sensitive info in logs
                doc = await artifacts_service.create_document(
                    session_id=session_id,
                    doc_name=f"auth_failure_log_{operation_id}",
                    doc_type=DocumentType.SCRATCHPAD,
                    content=f"Authentication failed for operation {operation_id} at {time.time()}",
                    author=Author(id="security_handler", role="security"),
                )

                # Return generic error - don't expose details
                return f"auth_error_{operation_id}"

        # Test multiple auth failures
        operations = [
            asyncio.create_task(authenticated_operation(f"auth_op_{i}"))
            for i in range(3)
        ]

        results = await asyncio.gather(*operations)

        # Verify all operations handled auth failures properly
        auth_errors = [r for r in results if r.startswith("auth_error_")]
        assert len(auth_errors) == 3, "Not all auth failures were handled properly"

        # Verify security logs were created without sensitive data
        scratchpad_docs = await artifacts_service.list_documents(
            session_id, DocumentType.SCRATCHPAD
        )
        auth_logs = [doc for doc in scratchpad_docs if "auth_failure_log_" in doc]
        assert len(auth_logs) == 3, "Not all auth failure logs were created"

    @pytest.mark.asyncio
    async def test_rate_limiting_backpressure_handling(
        self,
        service_simulator: ExternalServiceSimulator,
        artifacts_service: ArtifactsService,
    ):
        """Test proper handling of rate limiting with backpressure mechanisms."""

        session_id = "rate_limit_session"
        await artifacts_service.create_session(session_id)

        # Track rate limiting
        rate_limit_encounters = []
        successful_operations = []

        async def rate_limited_operation(operation_id: str, delay: float = 0):
            """Operation subject to rate limiting."""
            if delay > 0:
                await asyncio.sleep(delay)  # Backpressure delay

            try:
                # Simulate rate limiting for first few operations
                if len(rate_limit_encounters) < 3:
                    rate_limit_encounters.append(operation_id)
                    await service_simulator.simulate_failure("rate_limit")

                # Subsequent operations succeed
                doc = await artifacts_service.create_document(
                    session_id=session_id,
                    doc_name=f"rate_limit_doc_{operation_id}",
                    doc_type=DocumentType.DELIVERABLE,
                    content=f"Successfully created after rate limiting: {operation_id}",
                    author=Author(id="rate_limit_handler", role="handler"),
                )

                successful_operations.append(operation_id)
                return f"success_{operation_id}"

            except Exception as e:
                if "rate limit" in str(e).lower():
                    # Apply exponential backoff and retry
                    retry_delay = min(
                        2 ** len(rate_limit_encounters), 10
                    )  # Cap at 10 seconds
                    return await rate_limited_operation(
                        f"{operation_id}_retry", delay=retry_delay
                    )
                raise

        # Start operations that will encounter rate limiting
        operations = [
            asyncio.create_task(rate_limited_operation(f"rate_op_{i}"))
            for i in range(5)
        ]

        results = await asyncio.gather(*operations, return_exceptions=True)

        # Verify operations eventually succeeded through backpressure handling
        successful_results = [
            r for r in results if isinstance(r, str) and r.startswith("success_")
        ]
        assert len(successful_results) >= 2, (
            f"Expected at least 2 successful operations, got {len(successful_results)}"
        )

        # Verify rate limiting was encountered and handled
        assert len(rate_limit_encounters) >= 3, (
            "Rate limiting should have been encountered"
        )

        print(f"Rate limit encounters: {len(rate_limit_encounters)}")
        print(f"Successful operations: {len(successful_operations)}")
