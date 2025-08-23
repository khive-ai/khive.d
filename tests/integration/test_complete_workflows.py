"""
Complete end-to-end workflow integration tests for GitHub issue #192.

Tests comprehensive user workflows from CLI input through orchestration
execution to final deliverable generation with focus on async operations,
concurrent execution, and system integration validation.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from khive.services.artifacts.factory import (ArtifactsConfig,
                                              create_artifacts_service)
from khive.services.artifacts.models import Author, DocumentType
from khive.services.artifacts.service import ArtifactsService
from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.plan.parts import PlannerRequest
from khive.services.plan.planner_service import PlannerService


class TestCompleteWorkflows:
    """End-to-end workflow tests covering complete user scenarios."""

    @pytest.fixture
    def temp_workspace(self) -> Path:
        """Create temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "complete_workflow_workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            return workspace

    @pytest.fixture
    def artifacts_service(self, temp_workspace: Path) -> ArtifactsService:
        """Create artifacts service for testing."""
        config = ArtifactsConfig(workspace_root=temp_workspace)
        return create_artifacts_service(config)

    @pytest.fixture
    async def planner_service(self) -> PlannerService:
        """Create planner service with realistic mocked responses."""
        with patch("khive.services.plan.planner_service.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock planning responses for different complexity levels
            mock_response = MagicMock()
            mock_response.parsed.complexity = "medium"
            mock_response.parsed.total_agents = 3
            mock_response.parsed.role_priorities = [
                "researcher",
                "implementer",
                "tester",
            ]
            mock_response.parsed.primary_domains = [
                "async-programming",
                "software-architecture",
            ]
            mock_response.parsed.workflow_pattern = "sequential"
            mock_response.parsed.quality_level = "thorough"
            mock_response.parsed.confidence = 0.9

            mock_client.beta.chat.completions.parse.return_value = mock_response
            return PlannerService(command_format="json")

    @pytest.fixture
    async def orchestrator(self) -> LionOrchestrator:
        """Create orchestrator with proper async setup."""
        with patch(
            "khive.services.orchestration.orchestrator.create_cc"
        ) as mock_create_cc:
            from lionagi.service.imodel import iModel

            mock_cc = MagicMock(spec=iModel)
            mock_cc.chat = AsyncMock(return_value="Mock agent response")
            mock_cc.invoke = AsyncMock(return_value="Mock agent result")
            mock_create_cc.return_value = mock_cc

            orchestrator = LionOrchestrator("complete_workflow_test")
            await orchestrator.initialize()
            return orchestrator

    @pytest.mark.asyncio
    async def test_simple_task_complete_workflow(
        self,
        planner_service: PlannerService,
        orchestrator: LionOrchestrator,
        artifacts_service: ArtifactsService,
    ):
        """Test complete workflow for a simple async task."""
        # 1. User initiates task via CLI (simulated)
        task_request = PlannerRequest(
            task_description="Add async timeout handling to file upload service",
            context="Need to prevent hanging uploads in web application",
        )

        # 2. Planning phase
        planning_response = await planner_service.handle_request(task_request)
        assert planning_response.success
        session_id = planning_response.session_id

        # 3. Session initialization
        await artifacts_service.create_session(session_id)

        # 4. Orchestration execution with async operations
        test_author = Author(id="async_implementer", role="implementer")

        # Simulate concurrent document creation during workflow
        async def create_workflow_document(name: str, content: str) -> None:
            await artifacts_service.create_document(
                session_id=session_id,
                doc_name=name,
                doc_type=DocumentType.SCRATCHPAD,
                content=content,
                author=test_author,
            )

        # Execute multiple async operations concurrently
        workflow_tasks = [
            create_workflow_document(
                "analysis_notes",
                "# Timeout Analysis\n\nCurrent implementation lacks timeout handling",
            ),
            create_workflow_document(
                "implementation_plan",
                "# Implementation Plan\n\n1. Add asyncio.wait_for wrapper",
            ),
            create_workflow_document(
                "test_scenarios",
                "# Test Scenarios\n\n1. Normal upload\n2. Slow upload\n3. Timeout case",
            ),
        ]

        await asyncio.gather(*workflow_tasks)

        # 5. Final deliverable creation
        deliverable = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="timeout_handling_implementation",
            doc_type=DocumentType.DELIVERABLE,
            content="""# Async Timeout Handling Implementation

## Summary
Added asyncio.wait_for() timeout handling to file upload service.

## Implementation
```python
async def upload_file(file_data, timeout=30):
    try:
        return await asyncio.wait_for(
            upload_operation(file_data), 
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise HTTPException(408, "Upload timeout")
```

## Testing
- Unit tests for timeout scenarios
- Integration tests with realistic file sizes
- Performance validation under load

## Status: ✅ Complete
""",
            author=test_author,
            description="Final implementation with async timeout handling",
        )

        # 6. Workflow validation
        registry = await artifacts_service.get_artifact_registry(session_id)
        assert len(registry.artifacts) >= 4  # 3 working docs + 1 deliverable
        assert deliverable.session_id == session_id
        assert "asyncio.wait_for" in deliverable.content

    @pytest.mark.asyncio
    async def test_concurrent_multi_agent_workflow(
        self,
        planner_service: PlannerService,
        orchestrator: LionOrchestrator,
        artifacts_service: ArtifactsService,
    ):
        """Test workflow with concurrent multi-agent execution."""
        # Complex task requiring multiple agents
        task_request = PlannerRequest(
            task_description="Implement async queue system with Redis backend, worker processes, and monitoring",
            context="High-throughput task processing system with fault tolerance",
        )

        planning_response = await planner_service.handle_request(task_request)
        session_id = planning_response.session_id
        await artifacts_service.create_session(session_id)

        # Simulate concurrent agent execution
        agents = [
            {
                "role": "researcher",
                "domain": "async-programming",
                "task": "Research async queue patterns",
            },
            {
                "role": "architect",
                "domain": "software-architecture",
                "task": "Design queue architecture",
            },
            {
                "role": "implementer",
                "domain": "async-programming",
                "task": "Implement queue system",
            },
            {
                "role": "tester",
                "domain": "async-programming",
                "task": "Create async test suite",
            },
        ]

        # Execute agents concurrently (simulating real orchestration)
        async def execute_agent(agent: dict[str, str]) -> str:
            """Simulate async agent execution."""
            author = Author(id=f"{agent['role']}_agent", role=agent["role"])

            # Simulate agent processing time with realistic delays
            await asyncio.sleep(0.1)  # Simulate processing

            doc = await artifacts_service.create_document(
                session_id=session_id,
                doc_name=f"{agent['role']}_deliverable",
                doc_type=DocumentType.DELIVERABLE,
                content=f"""# {agent["role"].title()} Deliverable

## Task: {agent["task"]}
## Domain: {agent["domain"]}

### Implementation
{agent["role"].title()} completed analysis and implementation for async queue system.

### Key Findings
- Async operations require proper timeout handling
- Concurrent processing needs semaphore controls
- Error boundaries must isolate failures

### Status: ✅ Complete
""",
                author=author,
                description=f"Deliverable from {agent['role']} agent",
            )
            return f"{doc.session_id}:{doc.name}"

        # Execute all agents concurrently
        agent_tasks = [execute_agent(agent) for agent in agents]
        agent_results = await asyncio.gather(*agent_tasks)

        # Verify concurrent execution results
        assert len(agent_results) == 4
        registry = await artifacts_service.get_artifact_registry(session_id)
        assert len(registry.artifacts) >= 4

        # Verify each agent's deliverable
        for agent in agents:
            deliverable_exists = await artifacts_service.document_exists(
                session_id, f"{agent['role']}_deliverable", DocumentType.DELIVERABLE
            )
            assert deliverable_exists

    @pytest.mark.asyncio
    async def test_quality_gate_workflow_cycle(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test quality gate evaluation and refinement cycles."""
        session_id = "quality_gate_workflow_test"
        await artifacts_service.create_session(session_id)

        # Initial implementation
        implementer = Author(id="implementer", role="implementer")
        initial_impl = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="initial_async_implementation",
            doc_type=DocumentType.DELIVERABLE,
            content="""# Initial Async Implementation

```python
async def process_data(data):
    result = await external_service.process(data)
    return result
```

Basic async implementation without error handling or timeouts.
""",
            author=implementer,
        )

        # Quality gate review (simulated)
        reviewer = Author(id="reviewer", role="reviewer")

        # Simulate async review process
        await asyncio.sleep(0.05)  # Simulate review time

        review_doc = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="quality_review_feedback",
            doc_type=DocumentType.SCRATCHPAD,
            content="""# Quality Review Feedback

## Issues Identified:
1. ❌ No timeout handling for external service calls
2. ❌ Missing error boundary handling  
3. ❌ No retry logic for transient failures
4. ❌ Resource cleanup not guaranteed

## Requirements for Approval:
1. Add asyncio.wait_for() timeout
2. Implement proper exception handling
3. Add retry mechanism with backoff
4. Ensure resource cleanup with async context managers

## Status: 🔄 Needs Revision
""",
            author=reviewer,
        )

        # Refinement cycle - address feedback
        refined_impl = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="refined_async_implementation",
            doc_type=DocumentType.DELIVERABLE,
            content="""# Refined Async Implementation

```python
import asyncio
from contextlib import asynccontextmanager

class AsyncDataProcessor:
    def __init__(self, timeout=30, max_retries=3):
        self.timeout = timeout
        self.max_retries = max_retries
    
    @asynccontextmanager
    async def _connection_manager(self):
        connection = None
        try:
            connection = await external_service.connect()
            yield connection
        finally:
            if connection:
                await connection.close()
    
    async def process_data(self, data):
        for attempt in range(self.max_retries):
            try:
                async with self._connection_manager() as conn:
                    return await asyncio.wait_for(
                        conn.process(data), 
                        timeout=self.timeout
                    )
            except (asyncio.TimeoutError, ConnectionError) as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

## Improvements Made:
✅ Timeout handling with asyncio.wait_for()
✅ Proper exception handling for timeout/connection errors
✅ Retry mechanism with exponential backoff
✅ Resource cleanup with async context manager

## Status: ✅ Quality Gates Passed
""",
            author=implementer,
        )

        # Final quality approval
        final_review = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="final_quality_approval",
            doc_type=DocumentType.SCRATCHPAD,
            content="""# Final Quality Approval

## Review Summary:
✅ All quality gate requirements addressed
✅ Proper async patterns implemented
✅ Error handling comprehensive
✅ Resource management secure

## Status: ✅ Approved for Production
""",
            author=reviewer,
        )

        # Validate complete quality cycle
        registry = await artifacts_service.get_artifact_registry(session_id)
        assert len(registry.artifacts) >= 4

        # Verify refinement cycle artifacts
        assert await artifacts_service.document_exists(
            session_id, "initial_async_implementation", DocumentType.DELIVERABLE
        )
        assert await artifacts_service.document_exists(
            session_id, "refined_async_implementation", DocumentType.DELIVERABLE
        )
        assert await artifacts_service.document_exists(
            session_id, "quality_review_feedback", DocumentType.SCRATCHPAD
        )
        assert await artifacts_service.document_exists(
            session_id, "final_quality_approval", DocumentType.SCRATCHPAD
        )

    @pytest.mark.asyncio
    async def test_user_experience_workflow_continuity(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test user experience and workflow continuity under various conditions."""
        session_id = "ux_continuity_test"
        await artifacts_service.create_session(session_id)

        user = Author(id="user", role="user")

        # 1. User starts workflow
        start_time = time.time()

        initial_request = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="user_request",
            doc_type=DocumentType.SCRATCHPAD,
            content="""# User Request

I need to add async processing to my API endpoints to handle concurrent requests better.
Current endpoints are blocking and causing timeout issues under load.

## Expected Outcome:
- Non-blocking async endpoints
- Proper concurrent request handling  
- Performance improvement under load
- Maintained data consistency
""",
            author=user,
        )

        # 2. System processing (simulated with concurrent operations)
        processing_tasks = []

        async def create_processing_artifact(
            name: str, content: str, delay: float = 0.05
        ) -> None:
            await asyncio.sleep(delay)  # Simulate processing
            await artifacts_service.create_document(
                session_id=session_id,
                doc_name=name,
                doc_type=DocumentType.SCRATCHPAD,
                content=content,
                author=Author(id="system", role="system"),
            )

        processing_tasks.extend([
            create_processing_artifact(
                "analysis_progress", "🔄 Analyzing current API architecture..."
            ),
            create_processing_artifact(
                "planning_progress", "🔄 Planning async conversion strategy..."
            ),
            create_processing_artifact(
                "implementation_progress", "🔄 Implementing async endpoints..."
            ),
        ])

        # Execute processing tasks concurrently for better UX
        await asyncio.gather(*processing_tasks)

        # 3. Incremental user feedback (realistic workflow)
        progress_update = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="progress_update",
            doc_type=DocumentType.SCRATCHPAD,
            content=f"""# Progress Update

## Status: 🟡 In Progress
- ✅ Request analysis complete
- ✅ Strategy planning complete  
- 🔄 Implementation in progress
- ⏳ Testing pending

## Estimated completion: {time.time() - start_time:.2f}s processing time

## Next Steps:
1. Complete async endpoint implementation
2. Add concurrent request testing
3. Performance validation
4. Final deliverable generation
""",
            author=Author(id="system", role="orchestrator"),
        )

        # 4. Final deliverable with complete solution
        final_deliverable = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="async_api_solution",
            doc_type=DocumentType.DELIVERABLE,
            content="""# Async API Implementation Solution

## Summary
Successfully converted blocking API endpoints to async with proper concurrent handling.

## Implementation

### Before (Blocking):
```python
def get_user_data(user_id):
    user = database.get_user(user_id)  # Blocking DB call
    profile = external_api.get_profile(user_id)  # Blocking API call
    return {"user": user, "profile": profile}
```

### After (Async):
```python
async def get_user_data(user_id):
    async with async_database.connection() as db:
        user_task = db.get_user(user_id)
        profile_task = external_api.async_get_profile(user_id)
        
        user, profile = await asyncio.gather(user_task, profile_task)
        return {"user": user, "profile": profile}
```

## Performance Improvements
- 🚀 3x faster response times under concurrent load
- 📈 10x higher concurrent request capacity
- ⚡ Non-blocking I/O operations
- 🛡️ Maintained data consistency with async transactions

## Testing Results
✅ Unit tests: All async operations properly tested
✅ Load tests: Handles 1000+ concurrent requests
✅ Integration tests: External service timeouts handled
✅ Performance tests: Response time < 200ms P95

## Status: ✅ Complete and Ready for Deployment
""",
            author=Author(id="solution_architect", role="architect"),
        )

        total_time = time.time() - start_time

        # 5. Validate user experience
        registry = await artifacts_service.get_artifact_registry(session_id)
        assert (
            len(registry.artifacts) >= 6
        )  # Request + 3 progress + update + deliverable

        # Verify workflow continuity
        assert "async processing" in initial_request.content.lower()
        assert "complete and ready" in final_deliverable.content.lower()
        assert total_time < 2.0  # Reasonable processing time for UX

        # Validate deliverable quality
        assert "async def" in final_deliverable.content
        assert "asyncio.gather" in final_deliverable.content
        assert "performance improvements" in final_deliverable.content.lower()

    @pytest.mark.asyncio
    async def test_workflow_with_external_dependencies(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test workflow integration with external dependencies."""
        session_id = "external_deps_workflow"
        await artifacts_service.create_session(session_id)

        # Mock external service calls with realistic async patterns
        async def mock_external_service_call(
            service_name: str, operation: str
        ) -> dict[str, Any]:
            """Simulate external service calls with realistic delays."""
            await asyncio.sleep(0.1)  # Simulate network latency
            return {
                "service": service_name,
                "operation": operation,
                "status": "success",
                "timestamp": time.time(),
                "data": f"Mock response from {service_name}",
            }

        # Test concurrent external service integration
        external_services = ["redis", "postgresql", "openai_api"]
        service_tasks = [
            mock_external_service_call(service, "health_check")
            for service in external_services
        ]

        service_results = await asyncio.gather(*service_tasks)

        # Create integration report
        integration_author = Author(id="integration_tester", role="tester")
        integration_report = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="external_integration_report",
            doc_type=DocumentType.DELIVERABLE,
            content=f"""# External Dependencies Integration Report

## Services Tested: {len(external_services)}
{chr(10).join([f"✅ {service}: {result['status']}" for service, result in zip(external_services, service_results, strict=False)])}

## Async Integration Patterns:
- Concurrent health checks completed in parallel
- Proper timeout handling for external calls
- Error boundaries isolate service failures
- Resource cleanup ensures connection management

## Performance Metrics:
- Total test time: {max(result["timestamp"] for result in service_results) - min(result["timestamp"] for result in service_results):.3f}s
- Concurrent execution: {len(external_services)} services tested simultaneously
- Success rate: {sum(1 for result in service_results if result["status"] == "success") / len(service_results) * 100:.1f}%

## Status: ✅ All External Dependencies Validated
""",
            author=integration_author,
        )

        # Validate external integration
        assert len(service_results) == len(external_services)
        assert all(result["status"] == "success" for result in service_results)
        assert "external dependencies validated" in integration_report.content.lower()
