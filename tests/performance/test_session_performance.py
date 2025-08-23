"""Performance tests for session management service.

Comprehensive performance testing for the khive session management service including:
- Session initialization performance and scalability
- Session end and diary processing performance
- Session status check performance
- Concurrent session handling and locking performance
- Session memory usage profiling
- Large-scale session operations benchmarking
- Thread pool execution performance
- Session lifecycle stress testing
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from khive.services.session.parts import SessionRequest, SessionResponse
from khive.services.session.session import DiaryWritingAssistant, SessionInitializer
from khive.services.session.session_service import SessionService


class TestSessionBenchmarks:
    """Benchmark session core operations for performance baseline."""

    @pytest.mark.asyncio
    async def test_session_initialization_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark session initialization performance."""
        service = SessionService()

        performance_profiler.start_measurement()

        initialization_times = []
        threshold = performance_thresholds["session"]["session_create_ms"] / 1000

        # Test multiple initialization scenarios
        test_requests = [
            SessionRequest(action="init", issue=123, resume=False, depth=5),
            SessionRequest(action="init", issue=456, resume=True, depth=7),
            SessionRequest(action="init", issue=None, resume=False, depth=3),
            SessionRequest(action="init", issue=789, resume=True, depth=10),
        ]

        for i, request in enumerate(test_requests * 3):  # Test each scenario 3 times
            start_time = time.perf_counter()

            try:
                # Mock the SessionInitializer to avoid file system operations
                with patch(
                    "khive.services.session.session_service.SessionInitializer"
                ) as mock_initializer:
                    mock_instance = Mock()
                    mock_instance.initialize.return_value = f"Session {i} initialized"
                    mock_instance.context = {
                        "pending_tasks": [{"id": i, "task": f"Task {i}"}],
                        "git_status": {"branch": "main", "clean": True},
                        "unprocessed_summaries": i % 3,
                    }
                    mock_initializer.return_value = mock_instance

                    response = await service.handle_request(request)
                    success = response.success

                    assert isinstance(response, SessionResponse)
                    assert response.summary == "Session initialized successfully"

            except Exception as e:
                success = False
                print(f"Session initialization failed for request {i}: {e}")

            end_time = time.perf_counter()
            init_time = end_time - start_time
            initialization_times.append(init_time)

            performance_profiler.record_operation(
                init_time,
                success=success,
                operation_type=f"session_init_{request.action}",
            )

        performance_profiler.end_measurement()

        # Analyze performance
        avg_time = sum(initialization_times) / len(initialization_times)
        min_time = min(initialization_times)
        max_time = max(initialization_times)

        # Performance assertions
        assert (
            avg_time < threshold
        ), f"Average session init time too slow: {avg_time:.6f}s"
        assert (
            min_time < threshold * 0.5
        ), f"Minimum session init time too slow: {min_time:.6f}s"
        assert (
            max_time < threshold * 2.0
        ), f"Maximum session init time too slow: {max_time:.6f}s"

        metrics = performance_profiler.get_comprehensive_metrics()
        print(
            f"Session init - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s"
        )
        print(f"Memory growth: {metrics.get('memory_growth_mb', 0):.2f}MB")

    @pytest.mark.asyncio
    async def test_session_status_check_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark session status check performance."""
        service = SessionService()

        performance_profiler.start_measurement()

        status_times = []
        threshold = performance_thresholds["session"]["session_load_ms"] / 1000

        # Test status checks with different session states
        status_requests = [
            SessionRequest(action="status", issue=123, depth=5),
            SessionRequest(action="status", issue=456, depth=10),
            SessionRequest(action="status", issue=None, depth=3),
        ]

        for i, request in enumerate(status_requests * 5):  # Test each scenario 5 times
            start_time = time.perf_counter()

            try:
                # Mock SessionInitializer methods for status check
                with patch(
                    "khive.services.session.session_service.SessionInitializer"
                ) as mock_initializer:
                    mock_instance = Mock()
                    mock_instance.count_unprocessed_summaries.return_value = i % 5
                    mock_instance.get_pending_tasks.return_value = [
                        {"id": j, "task": f"Pending task {j}"} for j in range(i % 3)
                    ]
                    mock_instance.get_git_status.return_value = {
                        "branch": "main",
                        "clean": i % 2 == 0,
                        "ahead": i % 4,
                    }
                    mock_initializer.return_value = mock_instance

                    response = await service.handle_request(request)
                    success = response.success

                    assert isinstance(response, SessionResponse)
                    assert "Session status:" in response.summary

            except Exception as e:
                success = False
                print(f"Session status check failed for request {i}: {e}")

            end_time = time.perf_counter()
            status_time = end_time - start_time
            status_times.append(status_time)

            performance_profiler.record_operation(
                status_time, success=success, operation_type="session_status_check"
            )

        performance_profiler.end_measurement()

        # Analyze performance
        avg_time = sum(status_times) / len(status_times)
        min_time = min(status_times)
        max_time = max(status_times)

        assert (
            avg_time < threshold
        ), f"Average status check time too slow: {avg_time:.6f}s"
        assert (
            max_time < threshold * 2.0
        ), f"Maximum status check time too slow: {max_time:.6f}s"

        print(
            f"Session status - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s"
        )

    @pytest.mark.asyncio
    async def test_session_end_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark session end and diary processing performance."""
        service = SessionService()

        performance_profiler.start_measurement()

        end_times = []
        threshold = (
            performance_thresholds["session"]["session_create_ms"] / 1000 * 2
        )  # End may take longer

        # Test session end operations
        end_requests = [
            SessionRequest(action="end"),
            SessionRequest(action="end"),
            SessionRequest(action="end"),
        ]

        for i, request in enumerate(end_requests * 2):  # Test each scenario 2 times
            start_time = time.perf_counter()

            try:
                # Mock DiaryWritingAssistant to avoid file system operations
                with patch(
                    "khive.services.session.session_service.DiaryWritingAssistant"
                ) as mock_diary:
                    mock_instance = Mock()
                    mock_instance.process_diaries = Mock()  # Sync method
                    mock_diary.return_value = mock_instance

                    response = await service.handle_request(request)
                    success = response.success

                    assert isinstance(response, SessionResponse)
                    assert (
                        "Session ended and diary processing completed"
                        in response.summary
                    )

                    # Verify diary processing was called
                    mock_instance.process_diaries.assert_called_once()

            except Exception as e:
                success = False
                print(f"Session end failed for request {i}: {e}")

            end_time = time.perf_counter()
            end_session_time = end_time - start_time
            end_times.append(end_session_time)

            performance_profiler.record_operation(
                end_session_time, success=success, operation_type="session_end"
            )

        performance_profiler.end_measurement()

        # Analyze performance
        avg_time = sum(end_times) / len(end_times)
        min_time = min(end_times)
        max_time = max(end_times)

        assert (
            avg_time < threshold
        ), f"Average session end time too slow: {avg_time:.6f}s"
        assert (
            max_time < threshold * 2.0
        ), f"Maximum session end time too slow: {max_time:.6f}s"

        print(
            f"Session end - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s"
        )


class TestSessionScalability:
    """Test session performance scalability under increasing loads."""

    @pytest.mark.asyncio
    async def test_concurrent_session_operations_scaling(
        self, performance_profiler, load_test_runner, performance_thresholds
    ):
        """Test session performance with concurrent operations."""
        service = SessionService()

        async def session_operation():
            """Single session operation for load testing."""
            request = SessionRequest(action="status", issue=123, depth=5)

            # Mock SessionInitializer for concurrent testing
            with patch(
                "khive.services.session.session_service.SessionInitializer"
            ) as mock_initializer:
                mock_instance = Mock()
                mock_instance.count_unprocessed_summaries.return_value = 2
                mock_instance.get_pending_tasks.return_value = [
                    {"id": 1, "task": "Test task"}
                ]
                mock_instance.get_git_status.return_value = {
                    "branch": "main",
                    "clean": True,
                }
                mock_initializer.return_value = mock_instance

                response = await service.handle_request(request)
                return response

        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 25, 50]
        scaling_results = {}

        for concurrent_ops in concurrency_levels:
            operations_per_task = 10

            results = await load_test_runner.run_async_load_test(
                session_operation,
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
        concurrent_sessions_limit = performance_thresholds["session"][
            "concurrent_sessions"
        ]

        for concurrency, results in scaling_results.items():
            # Success rate should remain high under load
            assert (
                results["success_rate"] > 0.95
            ), f"Success rate too low at {concurrency} concurrent sessions: {results['success_rate']:.4f}"

            # Throughput should be reasonable for the concurrency level
            if concurrency <= concurrent_sessions_limit:
                min_expected_throughput = min(
                    concurrency * 5, 100
                )  # Scale with concurrency, max 100
                assert (
                    results["throughput"] >= min_expected_throughput
                ), f"Throughput too low at {concurrency} concurrent sessions: {results['throughput']:.2f} ops/sec"

    @pytest.mark.asyncio
    async def test_session_locking_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Test session locking mechanism performance under concurrent access."""
        service = SessionService()

        performance_profiler.start_measurement()

        # Test concurrent access to sessions with locking
        async def concurrent_session_access(session_id: int):
            """Concurrent session access operation."""
            requests = [
                SessionRequest(action="init", issue=session_id, depth=5),
                SessionRequest(action="status", issue=session_id, depth=5),
                SessionRequest(action="end"),
            ]

            results = []
            for request in requests:
                try:
                    # Mock the appropriate components for each action
                    if request.action == "init":
                        with patch(
                            "khive.services.session.session_service.SessionInitializer"
                        ) as mock_init:
                            mock_instance = Mock()
                            mock_instance.initialize.return_value = (
                                f"Session {session_id} initialized"
                            )
                            mock_instance.context = {
                                "pending_tasks": [],
                                "git_status": {"branch": "main"},
                                "unprocessed_summaries": 0,
                            }
                            mock_init.return_value = mock_instance

                            response = await service.handle_request(request)

                    elif request.action == "status":
                        with patch(
                            "khive.services.session.session_service.SessionInitializer"
                        ) as mock_init:
                            mock_instance = Mock()
                            mock_instance.count_unprocessed_summaries.return_value = 1
                            mock_instance.get_pending_tasks.return_value = []
                            mock_instance.get_git_status.return_value = {
                                "branch": "main"
                            }
                            mock_init.return_value = mock_instance

                            response = await service.handle_request(request)

                    else:  # end
                        with patch(
                            "khive.services.session.session_service.DiaryWritingAssistant"
                        ) as mock_diary:
                            mock_instance = Mock()
                            mock_instance.process_diaries = Mock()
                            mock_diary.return_value = mock_instance

                            response = await service.handle_request(request)

                    results.append(
                        {
                            "success": response.success,
                            "action": request.action,
                        }
                    )

                except Exception as e:
                    results.append(
                        {
                            "success": False,
                            "action": request.action,
                            "error": str(e),
                        }
                    )

            return results

        # Run multiple concurrent sessions
        concurrent_sessions = 20
        lock_performance_start = time.perf_counter()

        tasks = []
        for session_id in range(concurrent_sessions):
            task = asyncio.create_task(concurrent_session_access(session_id))
            tasks.append(task)

        # Wait for all concurrent sessions to complete
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        lock_performance_time = time.perf_counter() - lock_performance_start

        performance_profiler.record_operation(
            lock_performance_time,
            success=True,
            operation_type="concurrent_session_locking",
        )

        performance_profiler.end_measurement()

        # Analyze locking performance
        successful_operations = 0
        total_operations = 0

        for result_set in all_results:
            if isinstance(result_set, list):  # Not an exception
                for result in result_set:
                    total_operations += 1
                    if result.get("success", False):
                        successful_operations += 1

        success_rate = successful_operations / max(total_operations, 1)
        throughput = total_operations / lock_performance_time

        print(f"Session locking performance:")
        print(f"- Total operations: {total_operations}")
        print(f"- Successful operations: {successful_operations}")
        print(f"- Success rate: {success_rate:.4f}")
        print(f"- Throughput: {throughput:.2f} ops/sec")
        print(f"- Total time: {lock_performance_time:.6f}s")

        # Verify locking doesn't significantly impact performance
        assert (
            success_rate > 0.95
        ), f"Session locking success rate too low: {success_rate:.4f}"
        assert (
            throughput > 50.0
        ), f"Session locking throughput too low: {throughput:.2f} ops/sec"


class TestSessionMemoryPerformance:
    """Test session memory usage and performance."""

    @pytest.mark.asyncio
    async def test_session_memory_usage_scaling(
        self, performance_profiler, memory_monitor, performance_thresholds
    ):
        """Test session memory usage scaling with session complexity."""

        async def create_session_with_complexity(complexity_level: int):
            """Create session with specified complexity level."""
            service = SessionService()

            # Create request with increasing complexity
            request = SessionRequest(
                action="init",
                issue=complexity_level * 100,
                depth=complexity_level * 2,  # Increase depth with complexity
                resume=complexity_level > 2,
            )

            # Mock SessionInitializer with complex data
            with patch(
                "khive.services.session.session_service.SessionInitializer"
            ) as mock_initializer:
                mock_instance = Mock()
                mock_instance.initialize.return_value = (
                    f"Complex session {complexity_level} initialized"
                )

                # Create complex context data scaled by complexity level
                mock_instance.context = {
                    "pending_tasks": [
                        {"id": i, "task": f"Complex task {i}", "data": "x" * 100}
                        for i in range(complexity_level * 10)
                    ],
                    "git_status": {
                        "branch": "main",
                        "files": [f"file_{i}.py" for i in range(complexity_level * 5)],
                        "history": [f"commit_{i}" for i in range(complexity_level * 3)],
                    },
                    "unprocessed_summaries": complexity_level * 2,
                    "session_data": {
                        f"data_section_{i}": "x" * 500 for i in range(complexity_level)
                    },
                }
                mock_initializer.return_value = mock_instance

                response = await service.handle_request(request)
                return response

        performance_profiler.start_measurement()

        # Test different complexity levels
        complexity_levels = [1, 3, 5, 10, 15]
        memory_results = {}
        memory_limit = performance_thresholds["session"]["memory_per_session_mb"]

        for complexity in complexity_levels:
            # Measure memory usage for this complexity level
            def memory_test_operation():
                return asyncio.run(create_session_with_complexity(complexity))

            memory_usage = memory_monitor(memory_test_operation)

            memory_results[complexity] = {
                "memory_delta_mb": memory_usage["memory_delta_mb"],
                "execution_time": memory_usage["execution_time"],
                "success": memory_usage["success"],
            }

            performance_profiler.record_operation(
                memory_usage["execution_time"],
                success=memory_usage["success"],
                operation_type=f"session_memory_complexity_{complexity}",
            )

            print(
                f"Complexity {complexity}: {memory_usage['memory_delta_mb']:.2f}MB, "
                f"time: {memory_usage['execution_time']:.6f}s"
            )

        performance_profiler.end_measurement()

        # Verify memory usage scaling
        for complexity, results in memory_results.items():
            # Memory usage should scale reasonably with complexity
            max_expected_memory = memory_limit * (
                complexity / 5.0
            )  # Scale with complexity
            assert (
                results["memory_delta_mb"] < max_expected_memory
            ), f"Memory usage too high for complexity {complexity}: {results['memory_delta_mb']:.2f}MB"

            assert results[
                "success"
            ], f"Session memory test failed for complexity {complexity}"

    @pytest.mark.asyncio
    async def test_session_memory_leak_detection(
        self, performance_profiler, memory_monitor
    ):
        """Test for memory leaks in repeated session operations."""
        service = SessionService()

        async def session_lifecycle():
            """Complete session lifecycle that might leak memory."""
            # Init session
            init_request = SessionRequest(action="init", issue=999, depth=5)
            with patch(
                "khive.services.session.session_service.SessionInitializer"
            ) as mock_init:
                mock_instance = Mock()
                mock_instance.initialize.return_value = "Test session initialized"
                mock_instance.context = {
                    "pending_tasks": [{"id": 1, "task": "Test task"}],
                    "git_status": {"branch": "main"},
                    "unprocessed_summaries": 1,
                }
                mock_init.return_value = mock_instance

                init_response = await service.handle_request(init_request)

            # Status check
            status_request = SessionRequest(action="status", issue=999, depth=5)
            with patch(
                "khive.services.session.session_service.SessionInitializer"
            ) as mock_init:
                mock_instance = Mock()
                mock_instance.count_unprocessed_summaries.return_value = 1
                mock_instance.get_pending_tasks.return_value = [
                    {"id": 1, "task": "Test"}
                ]
                mock_instance.get_git_status.return_value = {"branch": "main"}
                mock_init.return_value = mock_instance

                status_response = await service.handle_request(status_request)

            # End session
            end_request = SessionRequest(action="end")
            with patch(
                "khive.services.session.session_service.DiaryWritingAssistant"
            ) as mock_diary:
                mock_instance = Mock()
                mock_instance.process_diaries = Mock()
                mock_diary.return_value = mock_instance

                end_response = await service.handle_request(end_request)

            return (
                init_response.success
                and status_response.success
                and end_response.success
            )

        performance_profiler.start_measurement()

        # Measure memory usage over multiple iterations
        memory_measurements = []
        iterations = 30

        for i in range(iterations):

            def single_lifecycle():
                return asyncio.run(session_lifecycle())

            memory_usage = memory_monitor(single_lifecycle)
            memory_measurements.append(
                {
                    "iteration": i,
                    "memory_delta_mb": memory_usage["memory_delta_mb"],
                    "execution_time": memory_usage["execution_time"],
                    "success": memory_usage["success"],
                }
            )

            performance_profiler.record_operation(
                memory_usage["execution_time"],
                success=memory_usage["success"],
                operation_type="session_memory_leak_test",
            )

            # Check for significant memory growth every 10 iterations
            if i > 0 and i % 10 == 0:
                recent_memory = [m["memory_delta_mb"] for m in memory_measurements[-5:]]
                avg_recent_memory = sum(recent_memory) / len(recent_memory)

                # Memory growth should stabilize after initial overhead
                if i > 15 and avg_recent_memory > 2.0:  # 2MB threshold
                    pytest.fail(
                        f"Potential memory leak detected: {avg_recent_memory:.2f}MB average growth at iteration {i}"
                    )

        performance_profiler.end_measurement()

        # Final analysis
        successful_operations = sum(1 for m in memory_measurements if m["success"])
        total_memory_growth = sum(
            m["memory_delta_mb"] for m in memory_measurements if m["success"]
        )
        avg_memory_per_operation = total_memory_growth / max(successful_operations, 1)

        print(
            f"Session memory leak test - {successful_operations}/{iterations} successful operations"
        )
        print(f"Average memory per operation: {avg_memory_per_operation:.4f}MB")
        print(f"Total memory growth: {total_memory_growth:.2f}MB")

        # Assert no significant memory leaks
        assert (
            avg_memory_per_operation < 0.5
        ), f"Potential memory leak: {avg_memory_per_operation:.4f}MB per operation"
        assert (
            successful_operations / iterations > 0.95
        ), f"Success rate too low: {successful_operations / iterations:.4f}"


class TestSessionStressTesting:
    """Stress testing for session service under extreme conditions."""

    @pytest.mark.asyncio
    async def test_high_volume_session_stress(
        self, performance_profiler, stress_test_scenarios
    ):
        """Test session service under high volume stress conditions."""
        service = SessionService()

        async def stress_session_operation():
            """High-volume session operation for stress testing."""
            # Randomly choose operation type
            import random

            actions = ["init", "status", "end"]
            action = random.choice(actions)

            request = SessionRequest(
                action=action,
                issue=random.randint(1, 1000),
                depth=random.randint(3, 10),
                resume=random.choice([True, False]),
            )

            # Mock appropriate components based on action
            if action == "init":
                with patch(
                    "khive.services.session.session_service.SessionInitializer"
                ) as mock_init:
                    mock_instance = Mock()
                    mock_instance.initialize.return_value = (
                        "Stress test session initialized"
                    )
                    mock_instance.context = {
                        "pending_tasks": [
                            {"id": i, "task": f"Stress task {i}"} for i in range(5)
                        ],
                        "git_status": {"branch": "main"},
                        "unprocessed_summaries": random.randint(0, 5),
                    }
                    mock_init.return_value = mock_instance

                    response = await service.handle_request(request)

            elif action == "status":
                with patch(
                    "khive.services.session.session_service.SessionInitializer"
                ) as mock_init:
                    mock_instance = Mock()
                    mock_instance.count_unprocessed_summaries.return_value = (
                        random.randint(0, 10)
                    )
                    mock_instance.get_pending_tasks.return_value = [
                        {"id": i, "task": f"Task {i}"}
                        for i in range(random.randint(0, 5))
                    ]
                    mock_instance.get_git_status.return_value = {
                        "branch": "main",
                        "clean": True,
                    }
                    mock_init.return_value = mock_instance

                    response = await service.handle_request(request)

            else:  # end
                with patch(
                    "khive.services.session.session_service.DiaryWritingAssistant"
                ) as mock_diary:
                    mock_instance = Mock()
                    mock_instance.process_diaries = Mock()
                    mock_diary.return_value = mock_instance

                    response = await service.handle_request(request)

            return response.success

        performance_profiler.start_measurement()

        # Stress test configuration
        stress_config = stress_test_scenarios["concurrent_stress"]
        concurrent_ops = stress_config["thread_counts"][2]  # Use high concurrency
        duration = stress_config["duration_seconds"][1]  # Use moderate duration

        start_time = time.perf_counter()
        completed_operations = 0
        errors = []

        # Run stress test
        async def stress_worker():
            nonlocal completed_operations
            while time.perf_counter() - start_time < duration:
                try:
                    success = await stress_session_operation()
                    completed_operations += 1

                    performance_profiler.record_operation(
                        time.perf_counter() - start_time,
                        success=success,
                        operation_type="session_stress_test",
                    )

                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.005)  # 5ms delay

                except Exception as e:
                    errors.append(str(e))
                    performance_profiler.record_operation(
                        time.perf_counter() - start_time,
                        success=False,
                        operation_type="session_stress_error",
                    )

        # Run concurrent stress workers
        tasks = [asyncio.create_task(stress_worker()) for _ in range(concurrent_ops)]
        await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.perf_counter() - start_time
        performance_profiler.end_measurement()

        # Analyze stress test results
        error_rate = len(errors) / max(completed_operations + len(errors), 1)
        throughput = completed_operations / total_time

        print(f"Session stress test results:")
        print(f"- Duration: {total_time:.2f}s")
        print(f"- Completed operations: {completed_operations}")
        print(f"- Errors: {len(errors)}")
        print(f"- Throughput: {throughput:.2f} ops/sec")
        print(f"- Error rate: {error_rate:.4f}")

        # Verify system survived stress test
        assert error_rate < 0.1, f"Error rate too high under stress: {error_rate:.4f}"
        assert completed_operations > 0, "No operations completed during stress test"

        metrics = performance_profiler.get_comprehensive_metrics()
        assert (
            metrics["success_rate"] > 0.9
        ), f"Success rate too low: {metrics['success_rate']:.4f}"
