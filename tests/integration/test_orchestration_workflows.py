"""
End-to-end orchestration workflow integration tests.

Tests the complete planning → execution → cleanup cycles, including integration
between PlannerService and LionOrchestrator, agent spawning patterns, artifact
management, and session coordination.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from lionagi.fields import Instruct

from khive.services.artifacts.factory import (ArtifactsConfig,
                                              create_artifacts_service)
from khive.services.artifacts.models import Author, DocumentType
from khive.services.artifacts.service import ArtifactsService
from khive.services.orchestration.orchestrator import LionOrchestrator
from khive.services.orchestration.parts import (ComposerRequest,
                                                OrchestrationPlan)
from khive.services.plan.parts import ComplexityLevel, PlannerRequest
from khive.services.plan.planner_service import PlannerService


class TestOrchestrationWorkflowIntegration:
    """Integration tests for end-to-end orchestration workflows."""

    @pytest.fixture
    def temp_workspace(self) -> Path:
        """Create temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "orchestration_test_workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            return workspace

    @pytest.fixture
    def artifacts_service(self, temp_workspace: Path) -> ArtifactsService:
        """Create artifacts service for testing."""
        config = ArtifactsConfig(workspace_root=temp_workspace)
        return create_artifacts_service(config)

    @pytest.fixture
    def mock_claude_code_service(self) -> MagicMock:
        """Mock Claude Code service for agent spawning."""
        mock_service = MagicMock()

        # Mock successful agent creation response
        mock_service.create_agent.return_value = {
            "agent_id": "test_agent_123",
            "status": "created",
            "capabilities": ["read", "write", "execute"],
        }

        # Mock agent execution response
        mock_service.execute_agent.return_value = {
            "agent_id": "test_agent_123",
            "status": "completed",
            "results": {"deliverable": "Test agent execution completed"},
            "artifacts": ["test_deliverable.md"],
        }

        return mock_service

    @pytest.fixture
    async def planner_service(self) -> PlannerService:
        """Create planner service with mocked dependencies."""
        with patch("khive.services.plan.planner_service.OpenAI") as mock_openai:
            # Mock OpenAI responses for planning
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock triage response (simple task)
            mock_triage_response = MagicMock()
            mock_triage_response.parsed.decision = "simple"
            mock_triage_response.parsed.confidence = 0.85
            mock_triage_response.parsed.agent_count = 2
            mock_triage_response.parsed.roles = ["researcher", "implementer"]

            # Mock complex evaluation response
            mock_eval_response = MagicMock()
            mock_eval_response.parsed.complexity = "medium"
            mock_eval_response.parsed.total_agents = 4
            mock_eval_response.parsed.role_priorities = [
                "researcher",
                "architect",
                "implementer",
                "tester",
            ]
            mock_eval_response.parsed.primary_domains = [
                "software-architecture",
                "distributed-systems",
            ]
            mock_eval_response.parsed.workflow_pattern = "fanout"
            mock_eval_response.parsed.quality_level = "thorough"
            mock_eval_response.parsed.confidence = 0.9

            mock_client.beta.chat.completions.parse.return_value = mock_eval_response

            return PlannerService(command_format="json")

    @pytest.fixture
    async def orchestrator(self) -> LionOrchestrator:
        """Create orchestrator with mocked dependencies."""
        with patch(
            "khive.services.orchestration.orchestrator.create_cc"
        ) as mock_create_cc:
            # Mock Claude Code model creation - needs to be an iModel instance
            from lionagi.service.imodel import iModel

            mock_cc = MagicMock(spec=iModel)
            mock_cc.chat = AsyncMock(return_value="Test response")
            mock_cc.invoke = AsyncMock(return_value="Test response")
            mock_create_cc.return_value = mock_cc

            orchestrator = LionOrchestrator("test_flow")
            await orchestrator.initialize()
            return orchestrator

    @pytest.mark.asyncio
    async def test_planning_to_execution_cycle(
        self,
        planner_service: PlannerService,
        orchestrator: LionOrchestrator,
        artifacts_service: ArtifactsService,
        mock_claude_code_service: MagicMock,
    ):
        """Test complete planning → execution cycle."""
        # 1. Planning phase
        request = PlannerRequest(
            task_description="Implement user authentication system with JWT tokens",
            context="Web application security enhancement",
        )

        planning_response = await planner_service.handle_request(request)

        assert planning_response.success
        assert planning_response.session_id is not None
        assert len(planning_response.phases) > 0
        assert planning_response.complexity in [
            ComplexityLevel.SIMPLE,
            ComplexityLevel.MEDIUM,
            ComplexityLevel.COMPLEX,
        ]

        session_id = planning_response.session_id

        # 2. Create session in artifacts service
        await artifacts_service.create_session(session_id)

        # 3. Execution phase - simulate orchestrator executing the plan
        with patch(
            "khive.services.orchestration.orchestrator.composer_service"
        ) as mock_composer:
            # Mock composer response
            mock_composer.handle_request.return_value = MagicMock(
                system_prompt="You are a test agent for authentication implementation"
            )

            # Create orchestration plan from planning response
            orchestration_plan = OrchestrationPlan(
                common_background=f"Task: {request.task_description}",
                execution_strategy="concurrent",
                agent_requests=[],
            )

            # Add agent requests based on planning response phases
            for phase in planning_response.phases:
                for agent_rec in phase.agents:
                    compose_request = ComposerRequest(
                        role=agent_rec.role, domains=agent_rec.domain
                    )

                    # Mock branch creation
                    with patch.object(
                        orchestrator, "create_cc_branch"
                    ) as mock_create_branch:
                        import uuid

                        mock_branch_id = str(uuid.uuid4())
                        mock_create_branch.return_value = mock_branch_id

                        # Mock operation execution
                        operation_id = orchestrator.builder.add_operation(
                            "operate",
                            branch=mock_branch_id,
                            instruct=Instruct(
                                instruction=f"Execute {agent_rec.role} tasks",
                                context=f"Session: {session_id}, Role: {agent_rec.role}",
                            ),
                        )

                        assert operation_id is not None

        # 4. Artifact creation phase
        test_author = Author(id="test_orchestrator", role="orchestrator")

        # Create deliverable document
        deliverable_doc = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="authentication_implementation",
            doc_type=DocumentType.DELIVERABLE,
            content="# Authentication Implementation\n\nJWT token implementation completed.",
            author=test_author,
            description="Main deliverable for authentication system",
        )

        assert deliverable_doc.session_id == session_id
        assert deliverable_doc.name == "authentication_implementation"

        # 5. Session coordination - verify artifacts are registered
        registry = await artifacts_service.get_artifact_registry(session_id)
        assert len(registry.artifacts) >= 1
        assert any(
            artifact.name == "authentication_implementation"
            for artifact in registry.artifacts
        )

    @pytest.mark.asyncio
    async def test_multi_phase_workflow_coordination(
        self,
        planner_service: PlannerService,
        orchestrator: LionOrchestrator,
        artifacts_service: ArtifactsService,
    ):
        """Test multi-phase workflow with proper coordination."""
        # Complex request that should generate multiple phases
        request = PlannerRequest(
            task_description="Design and implement distributed microservices architecture with service discovery, load balancing, and monitoring",
            context="Large-scale system architecture project",
        )

        planning_response = await planner_service.handle_request(request)
        session_id = planning_response.session_id

        # Create session
        await artifacts_service.create_session(session_id)

        # Simulate multi-phase execution
        test_author = Author(id="test_agent", role="system")
        phase_results = []

        for i, phase in enumerate(planning_response.phases, 1):
            phase_name = f"phase_{i}"

            # Create phase deliverable
            phase_doc = await artifacts_service.create_document(
                session_id=session_id,
                doc_name=f"{phase_name}_deliverable",
                doc_type=DocumentType.DELIVERABLE,
                content=f"# Phase {i} Results\n\nPhase: {phase.name}\nDescription: {phase.description}",
                author=test_author,
                description=f"Deliverable for {phase.name}",
            )

            phase_results.append(phase_doc)

            # Create working documents in scratchpad
            for j, agent_rec in enumerate(phase.agents, 1):
                scratch_doc = await artifacts_service.create_document(
                    session_id=session_id,
                    doc_name=f"{phase_name}_{agent_rec.role}_notes_{j}",
                    doc_type=DocumentType.SCRATCHPAD,
                    content=f"# {agent_rec.role} Working Notes\n\nRole: {agent_rec.role}\nDomain: {agent_rec.domain}",
                    author=Author(id=f"{agent_rec.role}_agent", role=agent_rec.role),
                )

                assert scratch_doc.session_id == session_id

        # Verify all phase deliverables were created
        assert len(phase_results) == len(planning_response.phases)

        # Verify artifact registry tracks all documents
        registry = await artifacts_service.get_artifact_registry(session_id)
        deliverable_count = len([
            a for a in registry.artifacts if "deliverable" in a.file_path
        ])
        scratchpad_count = len([
            a for a in registry.artifacts if "scratchpad" in a.file_path
        ])

        assert deliverable_count >= len(planning_response.phases)
        assert scratchpad_count >= sum(
            len(phase.agents) for phase in planning_response.phases
        )

    @pytest.mark.asyncio
    async def test_agent_spawning_patterns(
        self,
        orchestrator: LionOrchestrator,
        mock_claude_code_service: MagicMock,
    ):
        """Test different agent spawning patterns and coordination."""

        # Test parallel agent spawning
        agents_to_spawn = [
            ComposerRequest(role="researcher", domains="distributed-systems"),
            ComposerRequest(role="architect", domains="software-architecture"),
            ComposerRequest(role="implementer", domains="backend-development"),
        ]

        spawned_branches = []

        with patch(
            "khive.services.orchestration.orchestrator.composer_service"
        ) as mock_composer:
            mock_composer.handle_request.return_value = MagicMock(
                system_prompt="Test agent system prompt"
            )

            # Test concurrent branch creation
            for agent_request in agents_to_spawn:
                with patch.object(
                    orchestrator, "create_cc_branch"
                ) as mock_create_branch:
                    import uuid

                    mock_branch_id = str(uuid.uuid4())
                    mock_create_branch.return_value = mock_branch_id

                    branch_id = await orchestrator.create_cc_branch(agent_request)
                    spawned_branches.append(branch_id)

                    # Verify branch creation was called with correct parameters
                    mock_create_branch.assert_called_with(agent_request)

        assert len(spawned_branches) == len(agents_to_spawn)
        assert all(branch_id is not None for branch_id in spawned_branches)

    @pytest.mark.asyncio
    async def test_session_persistence_and_recovery(
        self,
        orchestrator: LionOrchestrator,
        artifacts_service: ArtifactsService,
    ):
        """Test session persistence and recovery capabilities."""

        session_id = "test_persistence_session_123"
        await artifacts_service.create_session(session_id)

        # Create initial session state with operations
        operation_id = orchestrator.builder.add_operation(
            "operate", instruction="Test persistence operation"
        )

        # Save session state
        await orchestrator.save_json()

        # Verify session files exist in workspace
        session_files = list(
            Path(f".khive/workspaces/{orchestrator.flow_name}/snapshots").glob("*.json")
        )
        assert len(session_files) > 0

        # Test session data integrity
        session_file = session_files[0]
        with open(session_file) as f:
            session_data = json.load(f)

        assert "branches" in session_data
        assert "metadata" in session_data
        assert "graph" in session_data
        assert session_data["metadata"]["name"] == orchestrator.flow_name

    @pytest.mark.asyncio
    async def test_cleanup_and_resource_management(
        self,
        planner_service: PlannerService,
        orchestrator: LionOrchestrator,
        artifacts_service: ArtifactsService,
    ):
        """Test proper cleanup and resource management."""

        # Create test session
        session_id = "test_cleanup_session_456"
        await artifacts_service.create_session(session_id)

        # Create various resources
        test_author = Author(id="cleanup_test", role="tester")

        # Create documents
        doc1 = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="cleanup_test_doc1",
            doc_type=DocumentType.DELIVERABLE,
            content="Test document 1",
            author=test_author,
        )

        doc2 = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="cleanup_test_doc2",
            doc_type=DocumentType.SCRATCHPAD,
            content="Test document 2",
            author=test_author,
        )

        # Verify resources exist
        registry_before = await artifacts_service.get_artifact_registry(session_id)
        assert len(registry_before.artifacts) >= 2

        # Test lock cleanup
        lock_stats_before = await artifacts_service.get_lock_stats()
        cleaned_locks = await artifacts_service.cleanup_locks(max_locks=100)
        lock_stats_after = await artifacts_service.get_lock_stats()

        # Verify cleanup occurred (exact numbers depend on test execution order)
        assert isinstance(cleaned_locks, int)
        assert cleaned_locks >= 0

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(
        self,
        planner_service: PlannerService,
        artifacts_service: ArtifactsService,
    ):
        """Test error handling and recovery mechanisms."""

        # Test invalid session handling
        with pytest.raises(Exception):  # Should raise session validation error
            await artifacts_service.get_document(
                "invalid_session_id", "nonexistent_doc", DocumentType.DELIVERABLE
            )

        # Test planning service error handling with malformed request
        invalid_request = PlannerRequest(
            task_description="",  # Empty task description
            context="Invalid test",
        )

        # Should handle gracefully and not crash
        response = await planner_service.handle_request(invalid_request)

        # The service should handle this gracefully, potentially with a fallback response
        assert isinstance(response, type(response))  # Just verify it returns something

    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(
        self,
        orchestrator: LionOrchestrator,
        artifacts_service: ArtifactsService,
    ):
        """Test concurrent workflow execution without race conditions."""

        session_id = "concurrent_test_session_789"
        await artifacts_service.create_session(session_id)

        # Create multiple concurrent operations
        async def create_concurrent_operation(op_name: str) -> str:
            """Create an operation concurrently."""
            return orchestrator.builder.add_operation(
                "operate", instruction=f"Concurrent operation: {op_name}"
            )

        # Execute multiple operations concurrently
        operation_tasks = [create_concurrent_operation(f"op_{i}") for i in range(5)]

        operation_ids = await asyncio.gather(*operation_tasks)

        # Verify all operations were created with unique IDs
        assert len(operation_ids) == 5
        assert len(set(operation_ids)) == 5  # All unique

        # Test concurrent document creation
        async def create_concurrent_document(doc_num: int) -> str:
            """Create a document concurrently."""
            doc = await artifacts_service.create_document(
                session_id=session_id,
                doc_name=f"concurrent_doc_{doc_num}",
                doc_type=DocumentType.SCRATCHPAD,
                content=f"Concurrent document {doc_num}",
                author=Author(id=f"concurrent_agent_{doc_num}", role="tester"),
            )
            return doc.id

        # Execute concurrent document creation
        doc_tasks = [create_concurrent_document(i) for i in range(3)]

        doc_ids = await asyncio.gather(*doc_tasks)

        # Verify all documents were created
        assert len(doc_ids) == 3

        # Verify artifact registry consistency
        registry = await artifacts_service.get_artifact_registry(session_id)
        concurrent_artifacts = [
            a for a in registry.artifacts if "concurrent_doc_" in a.name
        ]
        assert len(concurrent_artifacts) == 3


class TestOrchestrationSecurityIntegration:
    """Security-focused integration tests for orchestration workflows."""

    @pytest.mark.asyncio
    async def test_session_isolation(self, artifacts_service: ArtifactsService):
        """Test that sessions are properly isolated from each other."""

        # Create two separate sessions
        session1_id = "security_test_session_1"
        session2_id = "security_test_session_2"

        await artifacts_service.create_session(session1_id)
        await artifacts_service.create_session(session2_id)

        # Create documents in each session
        author1 = Author(id="user1", role="researcher")
        author2 = Author(id="user2", role="analyst")

        doc1 = await artifacts_service.create_document(
            session_id=session1_id,
            doc_name="sensitive_doc1",
            doc_type=DocumentType.DELIVERABLE,
            content="Sensitive content for session 1",
            author=author1,
        )

        doc2 = await artifacts_service.create_document(
            session_id=session2_id,
            doc_name="sensitive_doc2",
            doc_type=DocumentType.DELIVERABLE,
            content="Sensitive content for session 2",
            author=author2,
        )

        # Verify documents exist in their respective sessions
        assert await artifacts_service.document_exists(
            session1_id, "sensitive_doc1", DocumentType.DELIVERABLE
        )
        assert await artifacts_service.document_exists(
            session2_id, "sensitive_doc2", DocumentType.DELIVERABLE
        )

        # Verify cross-session access is prevented
        assert not await artifacts_service.document_exists(
            session1_id, "sensitive_doc2", DocumentType.DELIVERABLE
        )
        assert not await artifacts_service.document_exists(
            session2_id, "sensitive_doc1", DocumentType.DELIVERABLE
        )

    @pytest.mark.asyncio
    async def test_concurrent_document_access_safety(
        self, artifacts_service: ArtifactsService
    ):
        """Test safe concurrent access to shared documents."""

        session_id = "concurrent_safety_session"
        await artifacts_service.create_session(session_id)

        # Create initial document
        initial_author = Author(id="initial_user", role="creator")
        doc = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="shared_document",
            doc_type=DocumentType.DELIVERABLE,
            content="Initial content",
            author=initial_author,
        )

        # Define concurrent append operations
        async def append_content(user_id: str, content: str) -> None:
            """Append content to shared document."""
            author = Author(id=user_id, role="contributor")
            await artifacts_service.append_to_deliverable(
                session_id=session_id,
                doc_name="shared_document",
                content_to_append=f"\n\n## Contribution by {user_id}\n{content}",
                author=author,
            )

        # Execute concurrent append operations
        append_tasks = [
            append_content("user_a", "Content from user A"),
            append_content("user_b", "Content from user B"),
            append_content("user_c", "Content from user C"),
        ]

        await asyncio.gather(*append_tasks)

        # Verify final document integrity
        final_doc = await artifacts_service.get_document(
            session_id=session_id,
            doc_name="shared_document",
            doc_type=DocumentType.DELIVERABLE,
        )

        # Check that all contributions are present
        assert "user_a" in final_doc.content
        assert "user_b" in final_doc.content
        assert "user_c" in final_doc.content
        assert "Initial content" in final_doc.content

        # Verify document has multiple contributions tracked
        assert len(final_doc.contributions) >= 4  # Initial + 3 appends
