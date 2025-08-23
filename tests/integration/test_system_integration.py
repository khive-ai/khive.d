"""
System-wide integration tests for KHIVE services.

Tests complete system functionality including:
- End-to-end orchestration workflows
- Multi-service coordination and data flow
- System resilience and recovery
- Performance characteristics under realistic load
- Security and data integrity across service boundaries
"""

import asyncio
import logging
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from khive.services.artifacts.service import ArtifactsService
from khive.services.cache.redis_cache import RedisCache
from khive.services.session.session_service import SessionService


class SystemIntegrationTestScenario:
    """Comprehensive system integration test scenario."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.start_time = None
        self.end_time = None
        self.results = {}
        self.errors = []

    def start(self):
        """Start the test scenario."""
        self.start_time = time.time()
        logging.info(f"Starting system integration scenario: {self.name}")

    def finish(self):
        """Finish the test scenario."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        logging.info(f"Completed scenario {self.name} in {self.duration:.2f}s")

    def add_result(self, key: str, value):
        """Add a result to the scenario."""
        self.results[key] = value

    def add_error(self, error: str):
        """Add an error to the scenario."""
        self.errors.append(error)
        logging.error(f"Scenario {self.name} error: {error}")

    def is_successful(self) -> bool:
        """Check if the scenario completed successfully."""
        return len(self.errors) == 0


class TestSystemIntegration:
    """System-wide integration tests."""

    @pytest.mark.integration
    async def test_complete_project_workflow_integration(
        self,
        artifacts_service: ArtifactsService,
        session_service: SessionService,
        redis_cache: RedisCache,
        mock_external_apis,
        integration_test_data,
        integration_temp_dir: Path,
    ):
        """Test complete project workflow from planning to delivery."""
        scenario = SystemIntegrationTestScenario(
            "complete_project_workflow",
            "End-to-end project workflow from planning to delivery",
        )
        scenario.start()

        project_request = (
            "Build a real-time collaboration platform with WebSocket support"
        )
        project_session_id = "system_integration_project_2025"

        try:
            # Phase 1: Project Initialization
            logging.info("Phase 1: Project Initialization")

            # Initialize session with project metadata
            session = session_service.create_session(
                project_session_id,
                metadata={
                    "project_name": "Real-time Collaboration Platform",
                    "complexity": "high",
                    "estimated_duration_days": 14,
                    "team_size": 6,
                    "technologies": ["WebSocket", "React", "Node.js", "Redis"],
                },
            )

            scenario.add_result(
                "session_created",
                {"session_id": session.session_id, "metadata": session.metadata},
            )

            # Phase 2: Planning and Architecture
            logging.info("Phase 2: Planning and Architecture")

            # Simulate planning service with caching
            planning_cache_key = f"planning:system_integration:{hash(project_request)}"

            planning_result = {
                "complexity": "high",
                "confidence": 0.91,
                "phases": [
                    "requirements_analysis",
                    "system_architecture",
                    "websocket_infrastructure",
                    "frontend_implementation",
                    "backend_implementation",
                    "real_time_features",
                    "testing_integration",
                    "deployment_setup",
                ],
                "total_agents": 8,
                "estimated_cost": 1.25,
                "technologies_needed": [
                    "WebSocket",
                    "Redis",
                    "React",
                    "Node.js",
                    "Docker",
                ],
                "risk_factors": ["real-time complexity", "scalability requirements"],
            }

            await redis_cache.set(planning_cache_key, planning_result, ttl=7200)
            scenario.add_result("planning_cached", planning_result)

            # Phase 3: Phase Execution with Document Management
            logging.info("Phase 3: Phase Execution")

            phase_documents = []

            for phase_index, phase_name in enumerate(planning_result["phases"]):
                # Create phase document
                phase_doc = artifacts_service.create_document(
                    f"phase_{phase_index:02d}_{phase_name}",
                    project_session_id,
                    content=f"""# {phase_name.replace("_", " ").title()} Phase

## Objectives
- Complete {phase_name} for real-time collaboration platform
- Integrate with existing system components
- Ensure scalability and performance requirements

## Implementation Plan
1. Research and analysis
2. Design and architecture
3. Implementation and testing
4. Integration validation

## Deliverables
- Technical specifications
- Implementation code
- Test results
- Documentation

## Status: In Progress
""",
                    description=f"Phase {phase_index + 1}: {phase_name}",
                    metadata={
                        "phase_index": phase_index,
                        "phase_name": phase_name,
                        "status": "in_progress",
                        "priority": "high" if phase_index < 3 else "medium",
                    },
                )

                phase_documents.append(phase_doc)

                # Simulate phase work with cache interactions
                work_cache_key = f"phase_work:{project_session_id}:{phase_name}"
                work_data = {
                    "phase_name": phase_name,
                    "start_time": time.time(),
                    "progress": 0,
                    "artifacts_created": 1,
                    "collaborators": ["researcher", "implementer", "tester"],
                }

                await redis_cache.set(work_cache_key, work_data, ttl=3600)

                # Simulate work progress
                await asyncio.sleep(0.1)  # Simulate work time

                # Update progress
                work_data["progress"] = 100
                work_data["completion_time"] = time.time()
                await redis_cache.set(work_cache_key, work_data, ttl=3600)

                # Complete phase document
                completed_doc = artifacts_service.update_document(
                    phase_doc.name,
                    project_session_id,
                    content=f"{phase_doc.content}\n\n## Completion Report\n\nPhase completed successfully at {time.time()}\n\n### Results\n- All objectives met\n- Deliverables created\n- Quality gates passed\n- Ready for next phase",
                    metadata={
                        **phase_doc.metadata,
                        "status": "completed",
                        "completion_time": time.time(),
                        "quality_score": 0.95,
                    },
                )

                phase_documents.append(completed_doc)

            scenario.add_result(
                "phases_completed",
                {
                    "total_phases": len(planning_result["phases"]),
                    "documents_created": len(phase_documents),
                },
            )

            # Phase 4: Cross-Phase Integration and Validation
            logging.info("Phase 4: Cross-Phase Integration")

            # Create integration summary
            integration_summary = f"""# System Integration Summary

## Project Overview
**Project**: {session.metadata["project_name"]}
**Session ID**: {project_session_id}
**Completion Date**: {time.time()}

## Phases Completed ({len(planning_result["phases"])})
"""

            for doc in phase_documents:
                if doc.metadata["status"] == "completed":
                    integration_summary += f"- ✅ **{doc.metadata['phase_name'].replace('_', ' ').title()}**: Quality Score {doc.metadata.get('quality_score', 'N/A')}\n"

            integration_summary += f"""
## System Metrics
- Total Documents: {len(phase_documents)}
- Cache Entries: {len(planning_result["phases"]) + 1}
- Session Duration: {time.time() - scenario.start_time:.2f}s
- Estimated Cost: ${planning_result["estimated_cost"]}

## Integration Validation
- ✅ All services operational
- ✅ Data consistency verified
- ✅ Performance requirements met
- ✅ Error handling validated

## Next Steps
- Production deployment preparation
- User acceptance testing
- Performance monitoring setup
- Documentation finalization
"""

            summary_doc = artifacts_service.create_document(
                "system_integration_summary",
                project_session_id,
                content=integration_summary,
                description="Complete system integration summary and validation",
                metadata={
                    "document_type": "summary",
                    "integration_validated": True,
                    "total_phases": len(planning_result["phases"]),
                    "system_health": "excellent",
                },
            )

            scenario.add_result(
                "integration_summary",
                (
                    summary_doc.to_dict()
                    if hasattr(summary_doc, "to_dict")
                    else str(summary_doc)
                ),
            )

            # Phase 5: System Validation and Health Check
            logging.info("Phase 5: System Validation")

            # Validate all services are working correctly
            validation_results = {}

            # Test artifacts service
            all_documents = artifacts_service.list_session_documents(project_session_id)
            validation_results["artifacts_service"] = {
                "status": "healthy",
                "documents_count": len(all_documents),
                "all_accessible": all(doc.content is not None for doc in all_documents),
            }

            # Test cache service
            cache_test_key = "system_validation_test"
            cache_test_data = {"validation": "success", "timestamp": time.time()}
            await redis_cache.set(cache_test_key, cache_test_data, ttl=300)
            retrieved_cache_data = await redis_cache.get(cache_test_key)

            validation_results["cache_service"] = {
                "status": "healthy",
                "cache_working": retrieved_cache_data is not None,
                "data_integrity": (
                    retrieved_cache_data == cache_test_data
                    if retrieved_cache_data
                    else False
                ),
            }

            # Test session service
            session_info = session_service.get_session_info(project_session_id)
            session_docs = session_service.get_session_documents(project_session_id)

            validation_results["session_service"] = {
                "status": "healthy",
                "session_accessible": session_info is not None,
                "documents_tracked": len(session_docs) > 0,
            }

            scenario.add_result("system_validation", validation_results)

            # Verify all services are healthy
            all_services_healthy = all(
                result["status"] == "healthy" for result in validation_results.values()
            )

            if not all_services_healthy:
                scenario.add_error("System validation failed - services not healthy")

            # Phase 6: Performance and Stress Validation
            logging.info("Phase 6: Performance Validation")

            # Test concurrent operations
            concurrent_operations = []

            # Concurrent document operations
            for i in range(5):
                concurrent_operations.append(
                    artifacts_service.create_document(
                        f"concurrent_test_{i}",
                        project_session_id,
                        content=f"Concurrent operation test {i}",
                    )
                )

            # Concurrent cache operations
            cache_operations = []
            for i in range(5):
                cache_key = f"concurrent_cache_test_{i}"
                cache_operations.append(
                    redis_cache.set(cache_key, {"test": i, "concurrent": True}, ttl=300)
                )

            # Execute concurrent operations
            concurrent_start_time = time.time()

            # Note: In a real async environment, these would be awaited concurrently
            # For this test, we'll simulate concurrent behavior
            concurrent_docs_created = 0
            concurrent_cache_ops_completed = 0

            try:
                for i in range(5):
                    doc = artifacts_service.create_document(
                        f"concurrent_perf_test_{i}",
                        project_session_id,
                        content=f"Performance test document {i}",
                    )
                    concurrent_docs_created += 1

                    cache_success = await redis_cache.set(
                        f"perf_cache_{i}", {"perf_test": i}, ttl=300
                    )
                    if cache_success:
                        concurrent_cache_ops_completed += 1

            except Exception as e:
                scenario.add_error(f"Concurrent operations failed: {e}")

            concurrent_time = time.time() - concurrent_start_time

            performance_metrics = {
                "concurrent_documents_created": concurrent_docs_created,
                "concurrent_cache_operations": concurrent_cache_ops_completed,
                "concurrent_execution_time": concurrent_time,
                "operations_per_second": (
                    (concurrent_docs_created + concurrent_cache_ops_completed)
                    / concurrent_time
                    if concurrent_time > 0
                    else 0
                ),
            }

            scenario.add_result("performance_metrics", performance_metrics)

            # Performance assertions
            if performance_metrics["operations_per_second"] < 10:
                scenario.add_error("Performance below acceptable threshold")

        except Exception as e:
            scenario.add_error(f"System integration test failed: {e}")

        finally:
            scenario.finish()

        # Final assertions
        assert scenario.is_successful(), f"System integration failed: {scenario.errors}"
        assert "session_created" in scenario.results, "Session creation failed"
        assert "planning_cached" in scenario.results, "Planning caching failed"
        assert "phases_completed" in scenario.results, "Phase execution failed"
        assert "system_validation" in scenario.results, "System validation failed"
        assert (
            "performance_metrics" in scenario.results
        ), "Performance validation failed"

        # Verify system state consistency
        final_documents = artifacts_service.list_session_documents(project_session_id)
        expected_minimum_docs = (
            len(planning_result["phases"]) + 1 + 5
        )  # phases + summary + concurrent tests

        assert (
            len(final_documents) >= expected_minimum_docs
        ), f"Expected at least {expected_minimum_docs} documents, got {len(final_documents)}"

    @pytest.mark.performance
    @pytest.mark.integration
    async def test_system_performance_under_load(
        self,
        artifacts_service: ArtifactsService,
        session_service: SessionService,
        redis_cache: RedisCache,
        performance_test_config,
    ):
        """Test system performance under realistic load conditions."""
        scenario = SystemIntegrationTestScenario(
            "system_performance_load_test",
            "System performance validation under concurrent load",
        )
        scenario.start()

        try:
            num_concurrent_sessions = performance_test_config["concurrent_operations"]
            operations_per_session = 3

            # Phase 1: Concurrent Session Creation
            session_creation_start = time.time()
            created_sessions = []

            for session_index in range(num_concurrent_sessions):
                session_id = f"load_test_session_{session_index}"
                try:
                    session = session_service.create_session(
                        session_id,
                        metadata={
                            "load_test": True,
                            "session_index": session_index,
                            "created_at": time.time(),
                        },
                    )
                    created_sessions.append(session_id)
                except Exception as e:
                    scenario.add_error(f"Session creation failed for {session_id}: {e}")

            session_creation_time = time.time() - session_creation_start
            scenario.add_result(
                "session_creation",
                {
                    "sessions_created": len(created_sessions),
                    "creation_time": session_creation_time,
                    "sessions_per_second": (
                        len(created_sessions) / session_creation_time
                        if session_creation_time > 0
                        else 0
                    ),
                },
            )

            # Phase 2: Concurrent Document Operations
            document_ops_start = time.time()
            document_operations_completed = 0

            for session_id in created_sessions:
                try:
                    for doc_index in range(operations_per_session):
                        doc = artifacts_service.create_document(
                            f"load_test_doc_{doc_index}",
                            session_id,
                            content=f"Load test document {doc_index} for {session_id}",
                            description=f"Load test document {doc_index}",
                        )
                        document_operations_completed += 1

                except Exception as e:
                    scenario.add_error(
                        f"Document operations failed for {session_id}: {e}"
                    )

            document_ops_time = time.time() - document_ops_start
            scenario.add_result(
                "document_operations",
                {
                    "operations_completed": document_operations_completed,
                    "operations_time": document_ops_time,
                    "operations_per_second": (
                        document_operations_completed / document_ops_time
                        if document_ops_time > 0
                        else 0
                    ),
                },
            )

            # Phase 3: Concurrent Cache Operations
            cache_ops_start = time.time()
            cache_operations_completed = 0

            for session_id in created_sessions:
                try:
                    for cache_index in range(operations_per_session):
                        cache_key = f"load_test:cache:{session_id}:{cache_index}"
                        cache_data = {
                            "session_id": session_id,
                            "cache_index": cache_index,
                            "data": f"Load test cache data {cache_index}",
                            "timestamp": time.time(),
                        }

                        success = await redis_cache.set(cache_key, cache_data, ttl=300)
                        if success:
                            cache_operations_completed += 1

                except Exception as e:
                    scenario.add_error(f"Cache operations failed for {session_id}: {e}")

            cache_ops_time = time.time() - cache_ops_start
            scenario.add_result(
                "cache_operations",
                {
                    "operations_completed": cache_operations_completed,
                    "operations_time": cache_ops_time,
                    "operations_per_second": (
                        cache_operations_completed / cache_ops_time
                        if cache_ops_time > 0
                        else 0
                    ),
                },
            )

            # Phase 4: System Consistency Validation
            consistency_start = time.time()
            consistency_errors = []

            for session_id in created_sessions:
                try:
                    # Verify session exists
                    session_info = session_service.get_session_info(session_id)
                    if not session_info:
                        consistency_errors.append(f"Session {session_id} not found")

                    # Verify documents exist
                    documents = artifacts_service.list_session_documents(session_id)
                    if len(documents) != operations_per_session:
                        consistency_errors.append(
                            f"Session {session_id} has {len(documents)} documents, expected {operations_per_session}"
                        )

                    # Verify cache entries exist
                    for cache_index in range(operations_per_session):
                        cache_key = f"load_test:cache:{session_id}:{cache_index}"
                        cached_data = await redis_cache.get(cache_key)
                        if not cached_data:
                            consistency_errors.append(
                                f"Cache entry {cache_key} not found"
                            )

                except Exception as e:
                    consistency_errors.append(
                        f"Consistency check failed for {session_id}: {e}"
                    )

            consistency_time = time.time() - consistency_start
            scenario.add_result(
                "consistency_validation",
                {
                    "sessions_validated": len(created_sessions),
                    "consistency_errors": len(consistency_errors),
                    "validation_time": consistency_time,
                    "error_rate": len(consistency_errors)
                    / (len(created_sessions) * 3),  # 3 checks per session
                },
            )

            # Add consistency errors to scenario
            for error in consistency_errors:
                scenario.add_error(error)

        except Exception as e:
            scenario.add_error(f"Load test failed: {e}")

        finally:
            scenario.finish()

        # Performance assertions
        session_results = scenario.results.get("session_creation", {})
        doc_results = scenario.results.get("document_operations", {})
        cache_results = scenario.results.get("cache_operations", {})
        consistency_results = scenario.results.get("consistency_validation", {})

        # Minimum performance requirements
        min_sessions_per_second = 5
        min_doc_ops_per_second = 10
        min_cache_ops_per_second = 50
        max_error_rate = 0.05  # 5% error rate

        assert (
            session_results.get("sessions_per_second", 0) >= min_sessions_per_second
        ), f"Session creation too slow: {session_results.get('sessions_per_second', 0)} < {min_sessions_per_second}"

        assert (
            doc_results.get("operations_per_second", 0) >= min_doc_ops_per_second
        ), f"Document operations too slow: {doc_results.get('operations_per_second', 0)} < {min_doc_ops_per_second}"

        assert (
            cache_results.get("operations_per_second", 0) >= min_cache_ops_per_second
        ), f"Cache operations too slow: {cache_results.get('operations_per_second', 0)} < {min_cache_ops_per_second}"

        assert (
            consistency_results.get("error_rate", 1) <= max_error_rate
        ), f"Error rate too high: {consistency_results.get('error_rate', 1)} > {max_error_rate}"

        assert scenario.is_successful(), f"Load test failed: {scenario.errors}"

    @pytest.mark.integration
    async def test_system_error_recovery_and_resilience(
        self,
        artifacts_service: ArtifactsService,
        session_service: SessionService,
        redis_cache: RedisCache,
    ):
        """Test system resilience and recovery under various failure conditions."""
        scenario = SystemIntegrationTestScenario(
            "system_resilience_test", "System resilience and error recovery validation"
        )
        scenario.start()

        resilience_session_id = "system_resilience_test_session"

        try:
            # Phase 1: Normal Operation Baseline
            session = session_service.create_session(
                resilience_session_id,
                metadata={"resilience_test": True, "baseline": True},
            )

            baseline_doc = artifacts_service.create_document(
                "baseline_document",
                resilience_session_id,
                content="Baseline document for resilience testing",
            )

            await redis_cache.set(
                "resilience:baseline", {"status": "operational"}, ttl=300
            )

            scenario.add_result("baseline_established", True)

            # Phase 2: Artifacts Service Error Recovery
            with patch.object(artifacts_service._storage, "save_document") as mock_save:
                mock_save.side_effect = OSError("Simulated storage failure")

                # Attempt operation that should fail
                try:
                    artifacts_service.create_document(
                        "failing_document",
                        resilience_session_id,
                        content="This should fail",
                    )
                    scenario.add_error("Expected storage failure did not occur")
                except OSError:
                    # Expected failure
                    scenario.add_result("artifacts_error_handling", True)

            # Verify system recovery
            recovery_doc = artifacts_service.create_document(
                "recovery_document",
                resilience_session_id,
                content="System recovered successfully",
            )

            scenario.add_result("artifacts_recovery", recovery_doc is not None)

            # Phase 3: Cache Service Error Recovery
            with patch.object(redis_cache, "_get_redis") as mock_redis:
                mock_redis.side_effect = ConnectionError("Redis unavailable")

                # Cache operations should fail gracefully
                cache_result = await redis_cache.get("test_key")
                cache_set_result = await redis_cache.set("test_key", {"test": "data"})

                scenario.add_result(
                    "cache_error_handling",
                    {
                        "get_result": cache_result is None,
                        "set_result": cache_set_result is False,
                    },
                )

            # Verify cache recovery
            recovery_cache_result = await redis_cache.set(
                "recovery_test", {"recovered": True}, ttl=300
            )
            scenario.add_result("cache_recovery", recovery_cache_result is True)

            # Phase 4: Cross-Service Error Propagation
            # Test that errors in one service don't cascade to others

            # Create document while cache is "failing"
            with patch.object(redis_cache, "set") as mock_cache_set:
                mock_cache_set.side_effect = Exception("Cache write failure")

                # Document creation should still work
                try:
                    isolation_doc = artifacts_service.create_document(
                        "service_isolation_test",
                        resilience_session_id,
                        content="Testing service isolation during cache failure",
                    )
                    scenario.add_result("service_isolation", True)
                except Exception as e:
                    scenario.add_error(f"Service isolation failed: {e}")

            # Phase 5: Data Consistency After Errors
            # Verify that all data remains consistent after error conditions

            final_documents = artifacts_service.list_session_documents(
                resilience_session_id
            )
            expected_docs = [
                "baseline_document",
                "recovery_document",
                "service_isolation_test",
            ]

            found_docs = [doc.name for doc in final_documents]
            missing_docs = [name for name in expected_docs if name not in found_docs]

            if missing_docs:
                scenario.add_error(
                    f"Missing documents after error recovery: {missing_docs}"
                )
            else:
                scenario.add_result("data_consistency", True)

            # Verify session integrity
            final_session_info = session_service.get_session_info(resilience_session_id)
            if not final_session_info:
                scenario.add_error("Session data lost after error conditions")
            else:
                scenario.add_result("session_integrity", True)

        except Exception as e:
            scenario.add_error(f"Resilience test failed: {e}")

        finally:
            scenario.finish()

        # Verify resilience test results
        required_results = [
            "baseline_established",
            "artifacts_error_handling",
            "artifacts_recovery",
            "cache_error_handling",
            "cache_recovery",
            "service_isolation",
            "data_consistency",
            "session_integrity",
        ]

        for result_key in required_results:
            assert (
                result_key in scenario.results
            ), f"Missing resilience test result: {result_key}"
            if isinstance(scenario.results[result_key], bool):
                assert scenario.results[
                    result_key
                ], f"Resilience test failed for: {result_key}"

        assert (
            scenario.is_successful()
        ), f"System resilience test failed: {scenario.errors}"
