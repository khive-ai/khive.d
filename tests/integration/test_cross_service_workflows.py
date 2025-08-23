"""
Cross-service integration tests for KHIVE services.

Tests end-to-end workflows that span multiple services:
- Planning Service + Cache Service integration
- Artifacts Service + Session Service coordination
- Full orchestration workflows across all services
- Error propagation and recovery across service boundaries
- Performance of multi-service operations
"""

import asyncio
import json
import time
from typing import Dict, List
from unittest.mock import AsyncMock, patch

import pytest

from khive.services.artifacts.service import ArtifactsService
from khive.services.cache.redis_cache import RedisCache
from khive.services.session.session_service import SessionService


class TestCrossServiceWorkflows:
    """Integration tests for cross-service workflows."""

    @pytest.mark.integration
    async def test_session_artifacts_integration_workflow(
        self,
        artifacts_service: ArtifactsService,
        session_service: SessionService,
        integration_test_data,
    ):
        """Test complete session and artifacts workflow integration."""
        session_id = "cross_service_workflow_test"

        # Phase 1: Session Service creates session
        session_metadata = integration_test_data.sample_session_metadata()
        session = session_service.create_session(session_id, metadata=session_metadata)

        assert session.session_id == session_id

        # Phase 2: Artifacts Service creates documents within session
        document_names = [
            "requirements",
            "architecture",
            "implementation",
            "validation",
        ]
        created_documents = []

        for doc_name in document_names:
            doc = artifacts_service.create_document(
                doc_name,
                session_id,
                content=f"Content for {doc_name} phase",
                description=f"Document for {doc_name} workflow phase",
                metadata={"phase": doc_name, "workflow": "cross_service_test"},
            )
            created_documents.append(doc)

        # Phase 3: Session Service tracks document creation
        session_documents = session_service.get_session_documents(session_id)
        assert len(session_documents) == len(document_names)

        # Phase 4: Collaborative document updates
        for doc in created_documents:
            # Simulate collaborative editing
            updated_doc = artifacts_service.update_document(
                doc.name,
                session_id,
                content=f"{doc.content}\n\nUpdated by collaborative workflow",
                metadata={**doc.metadata, "last_updated": time.time()},
            )

            # Verify update through session service
            session_doc = session_service.get_document(doc.name, session_id)
            assert session_doc.version == updated_doc.version
            assert "collaborative workflow" in session_doc.content

        # Phase 5: Session completion and summary
        session_summary = session_service.get_session_summary(session_id)

        assert session_summary["session_id"] == session_id
        assert session_summary["total_documents"] == len(document_names)
        assert all(
            phase in [doc["metadata"]["phase"] for doc in session_summary["documents"]]
            for phase in document_names
        )

    @pytest.mark.integration
    async def test_planning_cache_integration_workflow(
        self, redis_cache: RedisCache, mock_external_apis, integration_test_data
    ):
        """Test planning service integration with cache for performance optimization."""
        planning_request = integration_test_data.sample_planning_request()
        cache_key = f"planning:request:{hash(planning_request)}"

        # Phase 1: Cache miss - first planning request
        cached_result = await redis_cache.get(cache_key)
        assert cached_result is None, "Cache should be empty initially"

        # Simulate planning service operation with external API
        mock_planning_result = {
            "complexity": "high",
            "confidence": 0.92,
            "reasoning": "Complex authentication system requires multiple services",
            "recommended_agents": 5,
            "roles": [
                "security_architect",
                "backend_implementer",
                "frontend_implementer",
                "tester",
                "reviewer",
            ],
            "estimated_cost": 0.45,
            "processing_time": 2.3,
        }

        # Phase 2: Store result in cache (simulating planning service caching)
        await redis_cache.set(cache_key, mock_planning_result, ttl=3600)

        # Phase 3: Cache hit - subsequent identical request
        start_time = time.time()
        cached_result = await redis_cache.get(cache_key)
        cache_retrieval_time = time.time() - start_time

        assert cached_result is not None
        assert cached_result["complexity"] == "high"
        assert cached_result["recommended_agents"] == 5
        assert cache_retrieval_time < 0.1, "Cache retrieval should be fast"

        # Phase 4: Test cache invalidation and refresh
        # Simulate planning parameters change
        updated_request = planning_request + " with additional security requirements"
        updated_cache_key = f"planning:request:{hash(updated_request)}"

        # Should be cache miss for updated request
        updated_cached_result = await redis_cache.get(updated_cache_key)
        assert updated_cached_result is None

        # Store updated result
        updated_planning_result = {
            **mock_planning_result,
            "complexity": "very_high",
            "recommended_agents": 7,
        }
        await redis_cache.set(updated_cache_key, updated_planning_result, ttl=3600)

        # Verify both cache entries coexist
        original_cached = await redis_cache.get(cache_key)
        updated_cached = await redis_cache.get(updated_cache_key)

        assert original_cached["recommended_agents"] == 5
        assert updated_cached["recommended_agents"] == 7

    @pytest.mark.integration
    async def test_orchestration_full_service_workflow(
        self,
        artifacts_service: ArtifactsService,
        session_service: SessionService,
        redis_cache: RedisCache,
        mock_external_apis,
        integration_test_data,
    ):
        """Test full orchestration workflow across all services."""
        orchestration_session_id = "full_orchestration_workflow"
        project_request = "Build a microservices API gateway with rate limiting"

        # Phase 1: Planning with caching
        planning_cache_key = f"planning:orchestration:{hash(project_request)}"

        # Simulate planning service operation
        planning_result = {
            "complexity": "high",
            "confidence": 0.88,
            "phases": [
                "analysis",
                "architecture",
                "implementation",
                "testing",
                "deployment",
            ],
            "total_agents": 8,
            "estimated_duration_hours": 12,
            "services_involved": [
                "gateway",
                "rate_limiter",
                "auth_service",
                "monitoring",
            ],
        }

        await redis_cache.set(planning_cache_key, planning_result, ttl=7200)

        # Phase 2: Session initialization for orchestration
        session = session_service.create_session(
            orchestration_session_id,
            metadata={
                "project": "api_gateway",
                "complexity": planning_result["complexity"],
                "total_phases": len(planning_result["phases"]),
                "orchestration": True,
            },
        )

        # Phase 3: Phase execution with document creation
        phase_results = []

        for phase_index, phase_name in enumerate(planning_result["phases"]):
            # Create phase document
            phase_doc = artifacts_service.create_document(
                f"phase_{phase_index:02d}_{phase_name}",
                orchestration_session_id,
                content=f"# {phase_name.capitalize()} Phase\n\nInitial phase setup for {project_request}",
                description=f"Phase {phase_index + 1}: {phase_name}",
                metadata={
                    "phase_index": phase_index,
                    "phase_name": phase_name,
                    "status": "in_progress",
                },
            )

            # Simulate phase execution
            execution_time = 0.5  # Simulated execution time
            await asyncio.sleep(execution_time)

            # Update phase completion
            completed_doc = artifacts_service.update_document(
                phase_doc.name,
                orchestration_session_id,
                content=f"{phase_doc.content}\n\n## Results\n\nPhase completed successfully.\nExecuted at: {time.time()}",
                metadata={
                    **phase_doc.metadata,
                    "status": "completed",
                    "execution_time": execution_time,
                },
            )

            phase_results.append(
                {
                    "phase": phase_name,
                    "document": completed_doc,
                    "execution_time": execution_time,
                }
            )

        # Phase 4: Cross-phase coordination and validation
        # Create summary document linking all phases
        summary_content = f"# Orchestration Summary\n\nProject: {project_request}\n\n"
        summary_content += "## Completed Phases\n\n"

        for result in phase_results:
            summary_content += f"- **{result['phase'].capitalize()}**: Completed in {result['execution_time']}s\n"

        summary_content += f"\n## Total Execution Time: {sum(r['execution_time'] for r in phase_results)}s\n"

        summary_doc = artifacts_service.create_document(
            "orchestration_summary",
            orchestration_session_id,
            content=summary_content,
            description="Complete orchestration workflow summary",
            metadata={
                "summary": True,
                "total_phases": len(phase_results),
                "total_execution_time": sum(r["execution_time"] for r in phase_results),
            },
        )

        # Phase 5: Validation across all services
        # Verify session state
        final_session_summary = session_service.get_session_summary(
            orchestration_session_id
        )
        assert (
            final_session_summary["total_documents"]
            == len(planning_result["phases"]) + 1
        )  # +1 for summary

        # Verify all phase documents exist and are completed
        all_documents = artifacts_service.list_session_documents(
            orchestration_session_id
        )
        phase_documents = [
            doc for doc in all_documents if doc.name.startswith("phase_")
        ]

        assert len(phase_documents) == len(planning_result["phases"])

        for doc in phase_documents:
            assert doc.metadata["status"] == "completed"
            assert "Results" in doc.content

        # Verify cache still contains planning result
        cached_planning = await redis_cache.get(planning_cache_key)
        assert cached_planning is not None
        assert cached_planning["complexity"] == planning_result["complexity"]

        # Phase 6: Performance validation
        total_workflow_time = sum(r["execution_time"] for r in phase_results)
        assert (
            total_workflow_time < 10.0
        ), "Full workflow should complete in reasonable time"

    @pytest.mark.integration
    async def test_error_propagation_across_services(
        self,
        artifacts_service: ArtifactsService,
        session_service: SessionService,
        redis_cache: RedisCache,
    ):
        """Test error handling and propagation across service boundaries."""
        error_test_session_id = "error_propagation_test"

        # Phase 1: Normal operation setup
        session = session_service.create_session(error_test_session_id)

        # Phase 2: Inject artifacts service error
        with patch.object(artifacts_service._storage, "save_document") as mock_save:
            mock_save.side_effect = OSError("Simulated storage failure")

            # Attempt document creation - should fail gracefully
            with pytest.raises(OSError):
                artifacts_service.create_document(
                    "failing_document",
                    error_test_session_id,
                    content="This should fail",
                )

            # Session should still be accessible
            session_info = session_service.get_session_info(error_test_session_id)
            assert session_info is not None
            assert session_info["session_id"] == error_test_session_id

        # Phase 3: Test cache service error handling
        with patch.object(redis_cache, "_get_redis") as mock_redis:
            mock_redis.side_effect = ConnectionError("Redis connection failed")

            # Cache operations should fail gracefully
            cache_result = await redis_cache.get("test_key")
            assert cache_result is None  # Should return None, not raise exception

            cache_set_result = await redis_cache.set("test_key", {"test": "data"})
            assert cache_set_result is False  # Should return False, not raise exception

        # Phase 4: Verify system recovery after errors
        # Services should continue working after temporary failures

        # Test artifacts service recovery
        recovery_doc = artifacts_service.create_document(
            "recovery_document",
            error_test_session_id,
            content="This should work after error recovery",
        )
        assert recovery_doc is not None
        assert recovery_doc.name == "recovery_document"

        # Test cache service recovery
        cache_recovery_result = await redis_cache.set(
            "recovery_key", {"recovered": True}, ttl=300
        )
        assert cache_recovery_result is True

        cached_recovery_value = await redis_cache.get("recovery_key")
        assert cached_recovery_value is not None
        assert cached_recovery_value["recovered"] is True

    @pytest.mark.performance
    @pytest.mark.integration
    async def test_cross_service_performance_under_load(
        self,
        artifacts_service: ArtifactsService,
        session_service: SessionService,
        redis_cache: RedisCache,
        performance_test_config,
    ):
        """Test performance of cross-service operations under concurrent load."""
        num_concurrent_workflows = performance_test_config["concurrent_operations"]

        async def execute_workflow(workflow_id: int) -> Dict:
            """Execute a complete cross-service workflow."""
            session_id = f"perf_workflow_{workflow_id}"

            try:
                start_time = time.time()

                # 1. Create session
                session = session_service.create_session(
                    session_id,
                    metadata={"workflow_id": workflow_id, "performance_test": True},
                )

                # 2. Cache some workflow data
                cache_key = f"workflow:{session_id}"
                workflow_data = {
                    "workflow_id": workflow_id,
                    "status": "running",
                    "created_at": time.time(),
                }
                await redis_cache.set(cache_key, workflow_data, ttl=300)

                # 3. Create documents
                documents_created = []
                for doc_index in range(3):  # 3 documents per workflow
                    doc = artifacts_service.create_document(
                        f"workflow_doc_{doc_index}",
                        session_id,
                        content=f"Workflow {workflow_id}, Document {doc_index}",
                        description=f"Performance test document {doc_index}",
                    )
                    documents_created.append(doc)

                # 4. Update cache with completion status
                workflow_data["status"] = "completed"
                workflow_data["documents_created"] = len(documents_created)
                await redis_cache.set(cache_key, workflow_data, ttl=300)

                execution_time = time.time() - start_time

                return {
                    "workflow_id": workflow_id,
                    "success": True,
                    "execution_time": execution_time,
                    "documents_created": len(documents_created),
                    "session_id": session_id,
                }

            except Exception as e:
                return {"workflow_id": workflow_id, "success": False, "error": str(e)}

        # Execute concurrent workflows
        start_time = time.time()

        workflow_tasks = [execute_workflow(i) for i in range(num_concurrent_workflows)]
        results = await asyncio.gather(*workflow_tasks)

        total_time = time.time() - start_time

        # Analyze results
        successful_workflows = [r for r in results if r["success"]]
        failed_workflows = [r for r in results if not r["success"]]

        # Verify success rate
        success_rate = len(successful_workflows) / len(results)
        assert success_rate >= 0.95, f"Success rate too low: {success_rate * 100}%"

        # Verify performance
        avg_execution_time = sum(
            r["execution_time"] for r in successful_workflows
        ) / len(successful_workflows)
        workflows_per_second = num_concurrent_workflows / total_time

        assert (
            avg_execution_time < 5.0
        ), f"Average workflow execution time too high: {avg_execution_time}s"
        assert (
            workflows_per_second > 1.0
        ), f"Workflow throughput too low: {workflows_per_second} workflows/sec"

        # Verify data consistency across services
        for result in successful_workflows:
            session_id = result["session_id"]

            # Check session service
            session_info = session_service.get_session_info(session_id)
            assert session_info is not None

            # Check artifacts service
            documents = artifacts_service.list_session_documents(session_id)
            assert len(documents) == result["documents_created"]

            # Check cache service
            cache_key = f"workflow:{session_id}"
            cached_data = await redis_cache.get(cache_key)
            assert cached_data is not None
            assert cached_data["status"] == "completed"
            assert cached_data["documents_created"] == result["documents_created"]
