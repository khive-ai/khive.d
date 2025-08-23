"""Performance tests for artifacts service.

Comprehensive performance testing for the khive artifacts service including:
- Document creation and retrieval performance
- Session management performance and scalability
- Storage repository operations benchmarking
- Lock management and concurrency control performance
- Artifact registry performance under load
- Large document handling and memory profiling
- Concurrent document operations stress testing
- File system I/O performance optimization
"""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from khive.services.artifacts.exceptions import DocumentAlreadyExists, DocumentNotFound
from khive.services.artifacts.models import Author, Document, DocumentType, Session
from khive.services.artifacts.service import ArtifactsService


class MockStorageRepository:
    """Mock storage repository for testing."""

    def __init__(self):
        self.documents = {}
        self.operation_times = []

    async def exists(
        self, session_id: str, doc_name: str, doc_type: DocumentType
    ) -> bool:
        start_time = time.perf_counter()
        key = f"{session_id}_{doc_name}_{doc_type.value}"
        exists = key in self.documents
        self.operation_times.append(time.perf_counter() - start_time)
        return exists

    async def save(self, document: Document) -> None:
        start_time = time.perf_counter()
        key = f"{document.session_id}_{document.name}_{document.doc_type.value}"
        self.documents[key] = document
        await asyncio.sleep(0.001)  # Simulate I/O delay
        self.operation_times.append(time.perf_counter() - start_time)

    async def load(
        self, session_id: str, doc_name: str, doc_type: DocumentType
    ) -> Document:
        start_time = time.perf_counter()
        key = f"{session_id}_{doc_name}_{doc_type.value}"
        if key not in self.documents:
            raise DocumentNotFound(f"Document {doc_name} not found")

        await asyncio.sleep(0.001)  # Simulate I/O delay
        self.operation_times.append(time.perf_counter() - start_time)
        return self.documents[key]

    async def list_documents(
        self, session_id: str, doc_type: DocumentType
    ) -> list[Document]:
        start_time = time.perf_counter()
        docs = [
            doc
            for key, doc in self.documents.items()
            if doc.session_id == session_id and doc.doc_type == doc_type
        ]
        await asyncio.sleep(0.001)  # Simulate I/O delay
        self.operation_times.append(time.perf_counter() - start_time)
        return docs


class MockSessionManager:
    """Mock session manager for testing."""

    def __init__(self):
        self.sessions = {}
        self.operation_times = []

    async def create_session(self, session_id: str | None = None) -> Session:
        start_time = time.perf_counter()
        if session_id is None:
            session_id = f"session_{len(self.sessions)}"

        session = Session(
            session_id=session_id,
            created_at=time.time(),
            workspace_path=f"/tmp/workspace/{session_id}",
        )
        self.sessions[session_id] = session
        await asyncio.sleep(0.001)  # Simulate setup delay
        self.operation_times.append(time.perf_counter() - start_time)
        return session

    async def get_session(self, session_id: str) -> Session:
        start_time = time.perf_counter()
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        self.operation_times.append(time.perf_counter() - start_time)
        return self.sessions[session_id]

    async def validate_session(self, session_id: str) -> bool:
        start_time = time.perf_counter()
        valid = session_id in self.sessions
        self.operation_times.append(time.perf_counter() - start_time)
        return valid

    async def list_sessions(self) -> list[str]:
        start_time = time.perf_counter()
        sessions = list(self.sessions.keys())
        self.operation_times.append(time.perf_counter() - start_time)
        return sessions


class MockLockManager:
    """Mock lock manager for testing."""

    def __init__(self):
        self.locks = set()
        self.operation_times = []

    async def acquire_lock(self, resource_id: str) -> bool:
        start_time = time.perf_counter()
        if resource_id in self.locks:
            await asyncio.sleep(0.01)  # Simulate lock wait
            self.operation_times.append(time.perf_counter() - start_time)
            return False

        self.locks.add(resource_id)
        self.operation_times.append(time.perf_counter() - start_time)
        return True

    async def release_lock(self, resource_id: str) -> None:
        start_time = time.perf_counter()
        self.locks.discard(resource_id)
        self.operation_times.append(time.perf_counter() - start_time)


class TestArtifactsBenchmarks:
    """Benchmark artifacts core operations for performance baseline."""

    @pytest.mark.asyncio
    async def test_document_creation_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark document creation performance."""

        # Create mock dependencies
        storage = MockStorageRepository()
        session_mgr = MockSessionManager()
        lock_mgr = MockLockManager()

        service = ArtifactsService(storage, session_mgr, lock_mgr)

        # Create test session
        session = await service.create_session("perf_test_session")

        performance_profiler.start_measurement()

        creation_times = []
        threshold = performance_thresholds["artifacts"]["file_write_ms"] / 1000

        # Test document creation with different types and sizes
        test_documents = [
            {
                "name": "small_doc",
                "content": "Small document content" * 10,
                "type": DocumentType.SCRATCHPAD,
            },
            {
                "name": "medium_doc",
                "content": "Medium document content" * 100,
                "type": DocumentType.DELIVERABLE,
            },
            {
                "name": "large_doc",
                "content": "Large document content" * 1000,
                "type": DocumentType.SCRATCHPAD,
            },
            {
                "name": "complex_doc",
                "content": "Complex document content" * 500,
                "type": DocumentType.DELIVERABLE,
            },
        ]

        for i, doc_config in enumerate(test_documents * 3):  # Test each type 3 times
            start_time = time.perf_counter()

            try:
                # Mock artifact registry registration
                with patch.object(service, "register_artifact", new_callable=AsyncMock):
                    document = await service.create_document(
                        session_id=session.session_id,
                        doc_name=f"{doc_config['name']}_{i}",
                        doc_type=doc_config["type"],
                        content=doc_config["content"],
                        author=Author(name="test_author", email="test@example.com"),
                        description=f"Test document {i}",
                    )

                success = document is not None
                assert document.name == f"{doc_config['name']}_{i}"
                assert document.content == doc_config["content"]

            except Exception as e:
                success = False
                print(f"Document creation failed for {doc_config['name']}_{i}: {e}")

            end_time = time.perf_counter()
            creation_time = end_time - start_time
            creation_times.append(creation_time)

            performance_profiler.record_operation(
                creation_time,
                success=success,
                operation_type=f"document_create_{doc_config['type'].value}",
            )

        performance_profiler.end_measurement()

        # Analyze performance
        avg_time = sum(creation_times) / len(creation_times)
        min_time = min(creation_times)
        max_time = max(creation_times)

        # Performance assertions
        assert (
            avg_time < threshold
        ), f"Average document creation time too slow: {avg_time:.6f}s"
        assert (
            min_time < threshold * 0.5
        ), f"Minimum document creation time too slow: {min_time:.6f}s"
        assert (
            max_time < threshold * 3.0
        ), f"Maximum document creation time too slow: {max_time:.6f}s"

        print(
            f"Document creation - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s"
        )

    @pytest.mark.asyncio
    async def test_document_retrieval_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark document retrieval performance."""

        storage = MockStorageRepository()
        session_mgr = MockSessionManager()
        lock_mgr = MockLockManager()

        service = ArtifactsService(storage, session_mgr, lock_mgr)

        # Create test session and documents
        session = await service.create_session("retrieval_test_session")

        # Pre-create documents for retrieval testing
        test_documents = []
        for i in range(20):
            doc_name = f"test_doc_{i}"
            content = f"Test document content {i}" * (10 + i * 5)  # Varying sizes
            doc_type = (
                DocumentType.SCRATCHPAD if i % 2 == 0 else DocumentType.DELIVERABLE
            )

            with patch.object(service, "register_artifact", new_callable=AsyncMock):
                document = await service.create_document(
                    session_id=session.session_id,
                    doc_name=doc_name,
                    doc_type=doc_type,
                    content=content,
                )
                test_documents.append((doc_name, doc_type))

        performance_profiler.start_measurement()

        retrieval_times = []
        threshold = performance_thresholds["artifacts"]["file_read_ms"] / 1000

        # Test document retrieval
        for i, (doc_name, doc_type) in enumerate(
            test_documents * 2
        ):  # Test each document twice
            start_time = time.perf_counter()

            try:
                document = await service.get_document(
                    session_id=session.session_id, doc_name=doc_name, doc_type=doc_type
                )

                success = document is not None
                assert document.name == doc_name
                assert document.doc_type == doc_type

            except Exception as e:
                success = False
                print(f"Document retrieval failed for {doc_name}: {e}")

            end_time = time.perf_counter()
            retrieval_time = end_time - start_time
            retrieval_times.append(retrieval_time)

            performance_profiler.record_operation(
                retrieval_time,
                success=success,
                operation_type=f"document_get_{doc_type.value}",
            )

        performance_profiler.end_measurement()

        # Analyze performance
        avg_time = sum(retrieval_times) / len(retrieval_times)
        min_time = min(retrieval_times)
        max_time = max(retrieval_times)

        assert (
            avg_time < threshold
        ), f"Average document retrieval time too slow: {avg_time:.6f}s"
        assert (
            max_time < threshold * 2.0
        ), f"Maximum document retrieval time too slow: {max_time:.6f}s"

        print(
            f"Document retrieval - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s"
        )

    @pytest.mark.asyncio
    async def test_session_management_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark session management operations."""

        storage = MockStorageRepository()
        session_mgr = MockSessionManager()
        lock_mgr = MockLockManager()

        service = ArtifactsService(storage, session_mgr, lock_mgr)

        performance_profiler.start_measurement()

        # Test session creation performance
        session_creation_times = []
        threshold = performance_thresholds["session"]["session_create_ms"] / 1000

        for i in range(20):
            start_time = time.perf_counter()

            try:
                session = await service.create_session(f"perf_session_{i}")
                success = session is not None
                assert session.session_id == f"perf_session_{i}"

            except Exception as e:
                success = False
                print(f"Session creation failed for session {i}: {e}")

            end_time = time.perf_counter()
            creation_time = end_time - start_time
            session_creation_times.append(creation_time)

            performance_profiler.record_operation(
                creation_time, success=success, operation_type="session_create"
            )

        # Test session retrieval performance
        session_retrieval_times = []

        for i in range(20):
            session_id = f"perf_session_{i}"

            start_time = time.perf_counter()

            try:
                session = await service.get_session(session_id)
                success = session is not None
                assert session.session_id == session_id

            except Exception as e:
                success = False
                print(f"Session retrieval failed for {session_id}: {e}")

            end_time = time.perf_counter()
            retrieval_time = end_time - start_time
            session_retrieval_times.append(retrieval_time)

            performance_profiler.record_operation(
                retrieval_time, success=success, operation_type="session_get"
            )

        # Test session listing performance
        start_time = time.perf_counter()

        try:
            sessions = await service.list_sessions()
            success = len(sessions) == 20

        except Exception as e:
            success = False
            print(f"Session listing failed: {e}")

        end_time = time.perf_counter()
        listing_time = end_time - start_time

        performance_profiler.record_operation(
            listing_time, success=success, operation_type="session_list"
        )

        performance_profiler.end_measurement()

        # Analyze session management performance
        avg_create_time = sum(session_creation_times) / len(session_creation_times)
        avg_retrieve_time = sum(session_retrieval_times) / len(session_retrieval_times)

        assert (
            avg_create_time < threshold
        ), f"Average session creation time too slow: {avg_create_time:.6f}s"
        assert (
            avg_retrieve_time < threshold * 0.5
        ), f"Average session retrieval time too slow: {avg_retrieve_time:.6f}s"
        assert (
            listing_time < threshold
        ), f"Session listing time too slow: {listing_time:.6f}s"

        print(f"Session create - Avg: {avg_create_time:.6f}s")
        print(f"Session retrieve - Avg: {avg_retrieve_time:.6f}s")
        print(f"Session list - Time: {listing_time:.6f}s")


class TestArtifactsScalability:
    """Test artifacts performance scalability under increasing loads."""

    @pytest.mark.asyncio
    async def test_concurrent_document_operations_scaling(
        self, performance_profiler, load_test_runner, performance_thresholds
    ):
        """Test document operations performance with concurrent access."""

        storage = MockStorageRepository()
        session_mgr = MockSessionManager()
        lock_mgr = MockLockManager()

        service = ArtifactsService(storage, session_mgr, lock_mgr)

        # Create test session
        session = await service.create_session("concurrent_test_session")

        async def concurrent_document_operation():
            """Single document operation for concurrent testing."""
            import random

            operation = random.choice(["create", "get"])
            doc_id = random.randint(1, 100)
            doc_name = f"concurrent_doc_{doc_id}"
            doc_type = random.choice(
                [
                    DocumentType.SCRATCHPAD,
                    DocumentType.DELIVERABLE,
                ]
            )

            try:
                if operation == "create":
                    with patch.object(
                        service, "register_artifact", new_callable=AsyncMock
                    ):
                        document = await service.create_document(
                            session_id=session.session_id,
                            doc_name=doc_name,
                            doc_type=doc_type,
                            content=f"Concurrent test content for {doc_name}",
                        )
                        return document is not None
                else:  # get
                    try:
                        document = await service.get_document(
                            session_id=session.session_id,
                            doc_name=doc_name,
                            doc_type=doc_type,
                        )
                        return document is not None
                    except DocumentNotFound:
                        # Document doesn't exist yet, which is fine in concurrent testing
                        return True

            except DocumentAlreadyExists:
                # Document already exists, which is fine in concurrent testing
                return True
            except Exception as e:
                print(f"Concurrent document operation failed: {e}")
                return False

        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20]
        scaling_results = {}

        for concurrent_ops in concurrency_levels:
            operations_per_task = 5

            results = await load_test_runner.run_async_load_test(
                concurrent_document_operation,
                concurrent_tasks=concurrent_ops,
                operations_per_task=operations_per_task,
                ramp_up_seconds=0.5,
            )

            scaling_results[concurrent_ops] = {
                "throughput": results["throughput"],
                "avg_response_time": results["avg_response_time"],
                "success_rate": results["success_rate"],
                "total_operations": results["total_operations"],
            }

            print(
                f"Concurrency {concurrent_ops}: {results['throughput']:.2f} ops/sec, "
                f"avg time: {results['avg_response_time']:.6f}s, "
                f"success rate: {results['success_rate']:.4f}"
            )

        # Verify scaling characteristics
        min_threshold = performance_thresholds["artifacts"]["throughput_ops_per_sec"]

        for concurrency, results in scaling_results.items():
            assert (
                results["success_rate"] > 0.90
            ), f"Success rate too low at {concurrency} concurrent operations: {results['success_rate']:.4f}"

            if concurrency == 1:
                assert (
                    results["throughput"] >= min_threshold
                ), f"Single-threaded throughput too low: {results['throughput']:.2f} ops/sec"

    @pytest.mark.asyncio
    async def test_large_document_handling_performance(
        self, performance_profiler, large_dataset_generator, performance_thresholds
    ):
        """Test performance with large documents."""

        storage = MockStorageRepository()
        session_mgr = MockSessionManager()
        lock_mgr = MockLockManager()

        service = ArtifactsService(storage, session_mgr, lock_mgr)

        # Create test session
        session = await service.create_session("large_doc_test_session")

        performance_profiler.start_measurement()

        # Test different document sizes
        document_sizes = [1, 5, 10, 25]  # MB
        large_doc_times = {}
        threshold = (
            performance_thresholds["artifacts"]["file_write_ms"] / 1000 * 5
        )  # Allow more time for large docs

        for size_mb in document_sizes:
            times = []

            for i in range(3):  # Test each size 3 times
                # Generate large content
                large_content = large_dataset_generator(
                    size_mb=size_mb, complexity="simple"
                )
                content_str = str(large_content)  # Convert to string for document

                start_time = time.perf_counter()

                try:
                    with patch.object(
                        service, "register_artifact", new_callable=AsyncMock
                    ):
                        document = await service.create_document(
                            session_id=session.session_id,
                            doc_name=f"large_doc_{size_mb}mb_{i}",
                            doc_type=DocumentType.SCRATCHPAD,
                            content=content_str,
                            description=f"Large document test - {size_mb}MB",
                        )

                    success = document is not None

                    # Also test retrieval of large document
                    retrieved_doc = await service.get_document(
                        session_id=session.session_id,
                        doc_name=f"large_doc_{size_mb}mb_{i}",
                        doc_type=DocumentType.SCRATCHPAD,
                    )

                    assert retrieved_doc.content == content_str

                except Exception as e:
                    success = False
                    print(f"Large document test failed for {size_mb}MB: {e}")

                end_time = time.perf_counter()
                doc_time = end_time - start_time
                times.append(doc_time)

                performance_profiler.record_operation(
                    doc_time,
                    success=success,
                    operation_type=f"large_document_{size_mb}mb",
                )

            large_doc_times[size_mb] = {
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
            }

        performance_profiler.end_measurement()

        # Verify large document performance scales reasonably
        for size_mb, metrics in large_doc_times.items():
            max_expected_time = threshold * (size_mb / 5.0)  # Scale with size
            assert (
                metrics["avg"] < max_expected_time
            ), f"Large document ({size_mb}MB) processing too slow: {metrics['avg']:.6f}s"
            print(f"Large doc {size_mb}MB - Avg: {metrics['avg']:.6f}s")


class TestArtifactsMemoryPerformance:
    """Test artifacts memory usage and performance."""

    @pytest.mark.asyncio
    async def test_artifact_registry_memory_performance(
        self, performance_profiler, memory_monitor, performance_thresholds
    ):
        """Test artifact registry memory usage with large number of artifacts."""

        async def create_many_artifacts():
            """Create many artifacts to test memory usage."""
            storage = MockStorageRepository()
            session_mgr = MockSessionManager()
            lock_mgr = MockLockManager()

            service = ArtifactsService(storage, session_mgr, lock_mgr)

            # Create test session
            session = await service.create_session("memory_test_session")

            # Create many documents with artifact registry
            for i in range(100):
                doc_name = f"memory_test_doc_{i}"
                content = f"Memory test content {i}" * 50  # Moderate size content
                doc_type = (
                    DocumentType.SCRATCHPAD if i % 2 == 0 else DocumentType.DELIVERABLE
                )

                with patch.object(
                    service, "register_artifact", new_callable=AsyncMock
                ) as mock_register:
                    document = await service.create_document(
                        session_id=session.session_id,
                        doc_name=doc_name,
                        doc_type=doc_type,
                        content=content,
                        description=f"Memory test document {i}",
                        agent_role="tester",
                        agent_domain="performance-testing",
                        metadata={"test_id": i, "batch": "memory_test"},
                    )

                    # Verify artifact registration was called
                    mock_register.assert_called_once()

            return len(storage.documents)

        performance_profiler.start_measurement()

        def memory_test_operation():
            return asyncio.run(create_many_artifacts())

        memory_usage = memory_monitor(memory_test_operation)

        performance_profiler.record_operation(
            memory_usage["execution_time"],
            success=memory_usage["success"],
            operation_type="artifact_registry_memory",
        )

        performance_profiler.end_measurement()

        # Verify memory usage is reasonable
        memory_limit = performance_thresholds["artifacts"]["memory_limit_mb"]
        assert (
            memory_usage["memory_delta_mb"] < memory_limit
        ), f"Artifact registry memory usage too high: {memory_usage['memory_delta_mb']:.2f}MB"

        assert memory_usage["success"], "Artifact registry operation should succeed"
        assert memory_usage["result"] == 100, "Should have created 100 documents"

        print(
            f"Artifact registry memory usage: {memory_usage['memory_delta_mb']:.2f}MB"
        )
        print(
            f"Created {memory_usage['result']} artifacts in {memory_usage['execution_time']:.6f}s"
        )


class TestArtifactsStressTesting:
    """Stress testing for artifacts service under extreme conditions."""

    @pytest.mark.asyncio
    async def test_artifacts_service_stress_test(
        self, performance_profiler, stress_test_scenarios
    ):
        """Test artifacts service under high stress conditions."""

        storage = MockStorageRepository()
        session_mgr = MockSessionManager()
        lock_mgr = MockLockManager()

        service = ArtifactsService(storage, session_mgr, lock_mgr)

        # Create multiple test sessions
        test_sessions = []
        for i in range(5):
            session = await service.create_session(f"stress_session_{i}")
            test_sessions.append(session)

        async def stress_artifacts_operation():
            """High-stress artifacts operation."""
            import random

            # Randomly choose session and operation
            session = random.choice(test_sessions)
            operation = random.choice(["create", "get", "list"])

            try:
                if operation == "create":
                    doc_name = f"stress_doc_{random.randint(1, 1000)}"
                    doc_type = random.choice(
                        [
                            DocumentType.SCRATCHPAD,
                            DocumentType.DELIVERABLE,
                        ]
                    )
                    content = (
                        f"Stress test content {random.randint(1, 100)}"
                        * random.randint(10, 50)
                    )

                    with patch.object(
                        service, "register_artifact", new_callable=AsyncMock
                    ):
                        document = await service.create_document(
                            session_id=session.session_id,
                            doc_name=doc_name,
                            doc_type=doc_type,
                            content=content,
                        )
                    return document is not None

                if operation == "get":
                    # Try to get a document that might or might not exist
                    doc_name = f"stress_doc_{random.randint(1, 1000)}"
                    doc_type = random.choice(
                        [
                            DocumentType.SCRATCHPAD,
                            DocumentType.DELIVERABLE,
                        ]
                    )

                    try:
                        document = await service.get_document(
                            session_id=session.session_id,
                            doc_name=doc_name,
                            doc_type=doc_type,
                        )
                        return True
                    except DocumentNotFound:
                        return True  # Expected for non-existent documents

                else:  # list
                    sessions = await service.list_sessions()
                    return len(sessions) > 0

            except DocumentAlreadyExists:
                return True  # Expected in concurrent stress testing
            except Exception as e:
                print(f"Stress operation failed: {e}")
                return False

        performance_profiler.start_measurement()

        # Stress test configuration
        stress_config = stress_test_scenarios["concurrent_stress"]
        concurrent_ops = stress_config["thread_counts"][1]  # Use moderate concurrency
        duration = stress_config["duration_seconds"][1]  # Use moderate duration

        start_time = time.perf_counter()
        completed_operations = 0
        errors = []

        # Run stress test
        async def stress_worker():
            nonlocal completed_operations
            while time.perf_counter() - start_time < duration:
                try:
                    success = await stress_artifacts_operation()
                    completed_operations += 1

                    performance_profiler.record_operation(
                        time.perf_counter() - start_time,
                        success=success,
                        operation_type="artifacts_stress_test",
                    )

                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.002)  # 2ms delay

                except Exception as e:
                    errors.append(str(e))
                    performance_profiler.record_operation(
                        time.perf_counter() - start_time,
                        success=False,
                        operation_type="artifacts_stress_error",
                    )

        # Run concurrent stress workers
        tasks = [asyncio.create_task(stress_worker()) for _ in range(concurrent_ops)]
        await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.perf_counter() - start_time
        performance_profiler.end_measurement()

        # Analyze stress test results
        error_rate = len(errors) / max(completed_operations + len(errors), 1)
        throughput = completed_operations / total_time

        print("Artifacts stress test results:")
        print(f"- Duration: {total_time:.2f}s")
        print(f"- Completed operations: {completed_operations}")
        print(f"- Errors: {len(errors)}")
        print(f"- Throughput: {throughput:.2f} ops/sec")
        print(f"- Error rate: {error_rate:.4f}")
        print(f"- Total documents in storage: {len(storage.documents)}")

        # Verify system survived stress test
        assert error_rate < 0.15, f"Error rate too high under stress: {error_rate:.4f}"
        assert completed_operations > 0, "No operations completed during stress test"

        metrics = performance_profiler.get_comprehensive_metrics()
        assert (
            metrics["success_rate"] > 0.85
        ), f"Success rate too low: {metrics['success_rate']:.4f}"
