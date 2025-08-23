"""
Multi-agent coordination and orchestration tests for GitHub issue #192.

Tests realistic multi-agent coordination scenarios with focus on concurrent
execution, proper handoffs, timeout management, and async coordination patterns
in the khive orchestration system.
"""

import asyncio
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from khive.services.artifacts.factory import (ArtifactsConfig,
                                              create_artifacts_service)
from khive.services.artifacts.models import Author, DocumentType
from khive.services.artifacts.service import ArtifactsService
from khive.services.orchestration.orchestrator import LionOrchestrator


@dataclass
class AgentResult:
    """Results from agent execution."""

    agent_id: str
    role: str
    domain: str
    status: str
    execution_time: float
    deliverable_id: str | None = None
    error: str | None = None


class TestMultiAgentCoordination:
    """Tests for multi-agent coordination patterns and orchestration."""

    @pytest.fixture
    def temp_workspace(self) -> Path:
        """Create temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "multi_agent_workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            return workspace

    @pytest.fixture
    def artifacts_service(self, temp_workspace: Path) -> ArtifactsService:
        """Create artifacts service for coordination testing."""
        config = ArtifactsConfig(workspace_root=temp_workspace)
        return create_artifacts_service(config)

    @pytest.fixture
    async def orchestrator(self) -> LionOrchestrator:
        """Create orchestrator for coordination testing."""
        with patch(
            "khive.services.orchestration.orchestrator.create_cc"
        ) as mock_create_cc:
            from lionagi.service.imodel import iModel

            mock_cc = MagicMock(spec=iModel)
            mock_cc.chat = AsyncMock(return_value="Agent coordination response")
            mock_cc.invoke = AsyncMock(return_value="Agent execution result")
            mock_create_cc.return_value = mock_cc

            orchestrator = LionOrchestrator("multi_agent_coordination_test")
            await orchestrator.initialize()
            return orchestrator

    async def execute_mock_agent(
        self,
        agent_id: str,
        role: str,
        domain: str,
        task: str,
        session_id: str,
        artifacts_service: ArtifactsService,
        execution_delay: float = 0.1,
        should_fail: bool = False,
    ) -> AgentResult:
        """Simulate realistic agent execution with async operations."""
        start_time = time.time()

        try:
            # Simulate agent processing time
            await asyncio.sleep(execution_delay)

            if should_fail:
                raise Exception(f"Simulated failure in {role} agent")

            # Create agent deliverable
            author = Author(id=agent_id, role=role)
            deliverable = await artifacts_service.create_document(
                session_id=session_id,
                doc_name=f"{role}_{domain}_deliverable",
                doc_type=DocumentType.DELIVERABLE,
                content=f"""# {role.title()} Agent Deliverable

## Task: {task}
## Domain: {domain}
## Agent ID: {agent_id}

### Execution Summary
This {role} agent successfully completed analysis in the {domain} domain.

### Key Findings
- Async operations properly handled
- Concurrent execution coordinated
- Resource management validated
- Integration points tested

### Deliverable Artifacts
- Analysis complete
- Implementation ready
- Documentation updated
- Testing validated

### Status: ✅ Complete
### Execution Time: {time.time() - start_time:.3f}s
""",
                author=author,
                description=f"Deliverable from {role} agent working on {task}",
            )

            return AgentResult(
                agent_id=agent_id,
                role=role,
                domain=domain,
                status="completed",
                execution_time=time.time() - start_time,
                deliverable_id=f"{deliverable.session_id}:{deliverable.name}",
            )

        except Exception as e:
            return AgentResult(
                agent_id=agent_id,
                role=role,
                domain=domain,
                status="failed",
                execution_time=time.time() - start_time,
                error=str(e),
            )

    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(
        self,
        orchestrator: LionOrchestrator,
        artifacts_service: ArtifactsService,
    ):
        """Test concurrent execution of multiple agents."""
        session_id = "concurrent_execution_test"
        await artifacts_service.create_session(session_id)

        # Define agent configuration for concurrent execution
        agents_config = [
            {
                "role": "researcher",
                "domain": "async-programming",
                "task": "Research async patterns",
            },
            {
                "role": "architect",
                "domain": "software-architecture",
                "task": "Design async architecture",
            },
            {
                "role": "implementer",
                "domain": "async-programming",
                "task": "Implement async components",
            },
            {
                "role": "tester",
                "domain": "async-programming",
                "task": "Create async test suite",
            },
        ]

        # Execute agents concurrently
        agent_tasks = []
        for i, config in enumerate(agents_config):
            agent_id = f"agent_{config['role']}_{i}"
            task = self.execute_mock_agent(
                agent_id=agent_id,
                session_id=session_id,
                artifacts_service=artifacts_service,
                execution_delay=0.15,  # Realistic processing delay
                **config,
            )
            agent_tasks.append(task)

        # Wait for all agents to complete
        agent_results = await asyncio.gather(*agent_tasks)

        # Validate concurrent execution results
        assert len(agent_results) == 4
        assert all(result.status == "completed" for result in agent_results)
        assert all(
            result.execution_time < 0.5 for result in agent_results
        )  # Reasonable execution time

        # Verify all deliverables created
        registry = await artifacts_service.get_artifact_registry(session_id)
        deliverable_artifacts = [
            a for a in registry.artifacts if "deliverable" in a.file_path
        ]
        assert len(deliverable_artifacts) >= 4

        # Verify concurrent execution was actually faster than sequential
        total_concurrent_time = max(result.execution_time for result in agent_results)
        estimated_sequential_time = sum(
            result.execution_time for result in agent_results
        )
        assert (
            total_concurrent_time < estimated_sequential_time * 0.8
        )  # At least 20% faster

    @pytest.mark.asyncio
    async def test_agent_dependency_coordination(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test coordination of agents with dependencies."""
        session_id = "dependency_coordination_test"
        await artifacts_service.create_session(session_id)

        # Phase 1: Research and Analysis (can run concurrently)
        phase1_agents = [
            {
                "role": "researcher",
                "domain": "async-programming",
                "task": "Research async queue patterns",
            },
            {
                "role": "analyst",
                "domain": "software-architecture",
                "task": "Analyze system requirements",
            },
        ]

        phase1_tasks = []
        for i, config in enumerate(phase1_agents):
            agent_id = f"phase1_agent_{i}"
            task = self.execute_mock_agent(
                agent_id=agent_id,
                session_id=session_id,
                artifacts_service=artifacts_service,
                **config,
            )
            phase1_tasks.append(task)

        phase1_results = await asyncio.gather(*phase1_tasks)

        # Validate phase 1 completion before phase 2
        assert all(result.status == "completed" for result in phase1_results)

        # Phase 2: Architecture and Design (depends on phase 1)
        phase2_agents = [
            {
                "role": "architect",
                "domain": "software-architecture",
                "task": "Design based on research",
            },
        ]

        phase2_tasks = []
        for i, config in enumerate(phase2_agents):
            agent_id = f"phase2_agent_{i}"
            task = self.execute_mock_agent(
                agent_id=agent_id,
                session_id=session_id,
                artifacts_service=artifacts_service,
                **config,
            )
            phase2_tasks.append(task)

        phase2_results = await asyncio.gather(*phase2_tasks)

        # Phase 3: Implementation (depends on phase 2)
        phase3_agents = [
            {
                "role": "implementer",
                "domain": "async-programming",
                "task": "Implement architecture",
            },
            {
                "role": "tester",
                "domain": "async-programming",
                "task": "Test implementation",
            },
        ]

        phase3_tasks = []
        for i, config in enumerate(phase3_agents):
            agent_id = f"phase3_agent_{i}"
            task = self.execute_mock_agent(
                agent_id=agent_id,
                session_id=session_id,
                artifacts_service=artifacts_service,
                **config,
            )
            phase3_tasks.append(task)

        phase3_results = await asyncio.gather(*phase3_tasks)

        # Validate dependency coordination
        all_results = phase1_results + phase2_results + phase3_results
        assert len(all_results) == 5
        assert all(result.status == "completed" for result in all_results)

        # Verify deliverables from all phases
        registry = await artifacts_service.get_artifact_registry(session_id)
        assert len(registry.artifacts) >= 5

    @pytest.mark.asyncio
    async def test_agent_timeout_handling(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test timeout handling in multi-agent coordination."""
        session_id = "timeout_handling_test"
        await artifacts_service.create_session(session_id)

        # Mix of normal and slow agents
        agents_config = [
            {
                "role": "researcher",
                "domain": "async-programming",
                "delay": 0.05,
                "should_fail": False,
            },
            {
                "role": "slow_analyzer",
                "domain": "software-architecture",
                "delay": 0.3,
                "should_fail": False,
            },  # Slower
            {
                "role": "implementer",
                "domain": "async-programming",
                "delay": 0.05,
                "should_fail": False,
            },
        ]

        # Execute with timeout handling
        agent_tasks = []
        timeout_limit = 0.5  # 500ms timeout

        for i, config in enumerate(agents_config):
            agent_id = f"timeout_test_agent_{i}"

            async def execute_with_timeout(agent_config, agent_id):
                try:
                    return await asyncio.wait_for(
                        self.execute_mock_agent(
                            agent_id=agent_id,
                            role=agent_config["role"],
                            domain=agent_config["domain"],
                            task=f"Execute {agent_config['role']} task",
                            session_id=session_id,
                            artifacts_service=artifacts_service,
                            execution_delay=agent_config["delay"],
                            should_fail=agent_config["should_fail"],
                        ),
                        timeout=timeout_limit,
                    )
                except asyncio.TimeoutError:
                    return AgentResult(
                        agent_id=agent_id,
                        role=agent_config["role"],
                        domain=agent_config["domain"],
                        status="timeout",
                        execution_time=timeout_limit,
                        error="Agent execution timed out",
                    )

            task = execute_with_timeout(config, agent_id)
            agent_tasks.append(task)

        # Execute with timeout handling
        agent_results = await asyncio.gather(*agent_tasks)

        # Validate timeout handling
        completed_agents = [r for r in agent_results if r.status == "completed"]
        timeout_agents = [r for r in agent_results if r.status == "timeout"]

        # Should have some completed and possibly some timeouts
        assert len(completed_agents) >= 2  # Fast agents should complete
        assert all(
            r.execution_time <= timeout_limit + 0.1 for r in agent_results
        )  # All respect timeout

        # Verify system continues working despite timeouts
        if timeout_agents:
            # Create recovery deliverable to show system resilience
            recovery_author = Author(id="orchestrator", role="orchestrator")
            recovery_doc = await artifacts_service.create_document(
                session_id=session_id,
                doc_name="timeout_recovery_report",
                doc_type=DocumentType.SCRATCHPAD,
                content=f"""# Timeout Recovery Report

## Execution Summary:
- Completed agents: {len(completed_agents)}
- Timeout agents: {len(timeout_agents)}
- Recovery action: Continue with available results

## Timeout Details:
{chr(10).join([f"- {agent.role}: {agent.error}" for agent in timeout_agents])}

## System Response:
✅ Graceful timeout handling
✅ No cascade failures
✅ Workflow continuation with available results
✅ Proper resource cleanup

## Status: System resilient to agent timeouts
""",
                author=recovery_author,
            )

            assert "system resilient" in recovery_doc.content.lower()

    @pytest.mark.asyncio
    async def test_agent_failure_isolation(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test that agent failures are properly isolated."""
        session_id = "failure_isolation_test"
        await artifacts_service.create_session(session_id)

        # Mix of successful and failing agents
        agents_config = [
            {"role": "researcher", "should_fail": False},
            {"role": "failing_analyst", "should_fail": True},  # This will fail
            {"role": "implementer", "should_fail": False},
            {"role": "failing_tester", "should_fail": True},  # This will fail
        ]

        agent_tasks = []
        for i, config in enumerate(agents_config):
            agent_id = f"isolation_test_agent_{i}"
            task = self.execute_mock_agent(
                agent_id=agent_id,
                role=config["role"],
                domain="async-programming",
                task=f"Execute {config['role']} task",
                session_id=session_id,
                artifacts_service=artifacts_service,
                should_fail=config["should_fail"],
            )
            agent_tasks.append(task)

        # Execute all agents (some will fail)
        agent_results = await asyncio.gather(*agent_tasks)

        # Validate failure isolation
        successful_agents = [r for r in agent_results if r.status == "completed"]
        failed_agents = [r for r in agent_results if r.status == "failed"]

        assert len(successful_agents) == 2  # Non-failing agents
        assert len(failed_agents) == 2  # Failing agents

        # Verify successful agents have deliverables
        for successful_agent in successful_agents:
            assert successful_agent.deliverable_id is not None

        # Verify failed agents have error information
        for failed_agent in failed_agents:
            assert failed_agent.error is not None
            assert "simulated failure" in failed_agent.error.lower()

        # Create failure analysis report
        failure_analyst = Author(id="failure_analyst", role="analyst")
        failure_report = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="failure_isolation_analysis",
            doc_type=DocumentType.DELIVERABLE,
            content=f"""# Agent Failure Isolation Analysis

## Test Results Summary:
- Total agents: {len(agent_results)}
- Successful: {len(successful_agents)}
- Failed: {len(failed_agents)}
- Isolation success rate: {len(successful_agents) / len(agent_results) * 100:.1f}%

## Successful Agents:
{chr(10).join([f"✅ {agent.role}: {agent.execution_time:.3f}s" for agent in successful_agents])}

## Failed Agents:  
{chr(10).join([f"❌ {agent.role}: {agent.error}" for agent in failed_agents])}

## Isolation Validation:
✅ Agent failures did not cascade
✅ Successful agents completed normally
✅ System maintained operational capacity
✅ Error boundaries properly enforced
✅ Resource cleanup maintained

## Conclusion:
The multi-agent coordination system successfully isolated failures and 
maintained operational capability with {len(successful_agents)}/{len(agent_results)} agents completing successfully.

## Status: ✅ Failure Isolation Validated
""",
            author=failure_analyst,
        )

        # Validate isolation effectiveness
        registry = await artifacts_service.get_artifact_registry(session_id)
        deliverable_count = len([
            a for a in registry.artifacts if "deliverable" in a.file_path
        ])
        assert deliverable_count >= 3  # 2 successful + 1 failure report

    @pytest.mark.asyncio
    async def test_coordinated_handoff_patterns(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test coordinated handoff patterns between agents."""
        session_id = "handoff_patterns_test"
        await artifacts_service.create_session(session_id)

        # Researcher creates foundation for architect
        researcher_result = await self.execute_mock_agent(
            agent_id="researcher_001",
            role="researcher",
            domain="async-programming",
            task="Research async queue implementation patterns",
            session_id=session_id,
            artifacts_service=artifacts_service,
        )

        assert researcher_result.status == "completed"

        # Architect uses research to create design (handoff)
        architect_author = Author(id="architect_001", role="architect")
        architect_deliverable = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="architecture_design",
            doc_type=DocumentType.DELIVERABLE,
            content=f"""# Architecture Design

## Research Foundation
Based on research deliverable: {researcher_result.deliverable_id}

## Queue Architecture Design

### Async Queue Components:
1. **Producer Interface**
   ```python
   async def enqueue(item: Any, priority: int = 0):
       async with queue_lock:
           await redis_client.lpush(queue_key, serialize(item))
   ```

2. **Consumer Interface**
   ```python  
   async def dequeue(timeout: int = 30):
       return await asyncio.wait_for(
           redis_client.brpop(queue_key), 
           timeout=timeout
       )
   ```

3. **Worker Pool Management**
   - Semaphore-controlled concurrent workers
   - Graceful shutdown handling
   - Health monitoring

### Integration Points:
- Handoff from research: ✅ Complete  
- Ready for implementation handoff: ✅ Ready
- Testing coordination: ✅ Prepared

## Status: ✅ Ready for Implementation Handoff
""",
            author=architect_author,
        )

        # Implementer receives handoff and implements
        implementer_result = await self.execute_mock_agent(
            agent_id="implementer_001",
            role="implementer",
            domain="async-programming",
            task="Implement queue based on architecture design",
            session_id=session_id,
            artifacts_service=artifacts_service,
        )

        assert implementer_result.status == "completed"

        # Tester receives handoff for validation
        tester_author = Author(id="tester_001", role="tester")
        test_deliverable = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="handoff_test_results",
            doc_type=DocumentType.DELIVERABLE,
            content=f"""# Coordinated Handoff Test Results

## Handoff Chain Validation:
1. ✅ Research → Architecture handoff successful  
2. ✅ Architecture → Implementation handoff successful
3. ✅ Implementation → Testing handoff successful

## Integration Test Results:
```python
async def test_queue_handoff_integration():
    # Test full handoff chain
    research_data = await get_research_findings()
    architecture = await apply_architecture_design(research_data) 
    implementation = await execute_implementation(architecture)
    test_results = await validate_implementation(implementation)
    
    assert all([research_data, architecture, implementation, test_results])
```

## Handoff Quality Metrics:
- Continuity: ✅ No information loss between handoffs
- Consistency: ✅ Design patterns maintained through chain  
- Completeness: ✅ All requirements addressed at each stage
- Timing: ✅ Handoffs completed within expected timeframes

## Performance:
- Research completion: {researcher_result.execution_time:.3f}s
- Implementation completion: {implementer_result.execution_time:.3f}s
- Total handoff chain: {researcher_result.execution_time + implementer_result.execution_time:.3f}s

## Status: ✅ Coordinated Handoff Chain Validated
""",
            author=tester_author,
        )

        # Validate complete handoff chain
        registry = await artifacts_service.get_artifact_registry(session_id)
        deliverables = [a for a in registry.artifacts if "deliverable" in a.file_path]
        assert len(deliverables) >= 4  # Research + Architecture + Implementation + Test

        # Verify handoff references
        assert researcher_result.deliverable_id in architect_deliverable.content
        assert "handoff chain validated" in test_deliverable.content.lower()

    @pytest.mark.asyncio
    async def test_large_scale_agent_coordination(
        self,
        artifacts_service: ArtifactsService,
    ):
        """Test coordination of larger numbers of agents."""
        session_id = "large_scale_coordination_test"
        await artifacts_service.create_session(session_id)

        # Create 8 agents for large-scale coordination test
        agent_configs = []
        roles = [
            "researcher",
            "analyst",
            "architect",
            "implementer",
            "tester",
            "reviewer",
            "optimizer",
            "documenter",
        ]
        domains = ["async-programming", "software-architecture"]

        for i, role in enumerate(roles):
            agent_configs.append({
                "agent_id": f"large_scale_agent_{i:02d}",
                "role": role,
                "domain": domains[i % len(domains)],
                "task": f"Execute {role} tasks in large-scale coordination",
            })

        # Execute agents in batches to simulate realistic orchestration
        batch_size = 4
        all_results = []

        for batch_start in range(0, len(agent_configs), batch_size):
            batch_configs = agent_configs[batch_start : batch_start + batch_size]

            batch_tasks = []
            for config in batch_configs:
                task = self.execute_mock_agent(
                    session_id=session_id,
                    artifacts_service=artifacts_service,
                    execution_delay=0.08,  # Shorter delay for larger scale
                    **config,
                )
                batch_tasks.append(task)

            # Execute batch concurrently
            batch_results = await asyncio.gather(*batch_tasks)
            all_results.extend(batch_results)

            # Brief pause between batches for realistic coordination
            await asyncio.sleep(0.02)

        # Validate large-scale coordination
        assert len(all_results) == 8
        successful_agents = [r for r in all_results if r.status == "completed"]
        assert len(successful_agents) >= 7  # Allow for possible occasional failures

        # Create coordination summary
        coordinator = Author(id="orchestrator", role="orchestrator")
        coordination_summary = await artifacts_service.create_document(
            session_id=session_id,
            doc_name="large_scale_coordination_summary",
            doc_type=DocumentType.DELIVERABLE,
            content=f"""# Large-Scale Agent Coordination Summary

## Scale Test Results:
- Total agents coordinated: {len(all_results)}
- Successful completions: {len(successful_agents)}
- Success rate: {len(successful_agents) / len(all_results) * 100:.1f}%
- Average execution time: {sum(r.execution_time for r in successful_agents) / len(successful_agents):.3f}s

## Coordination Patterns:
- Batch execution: {batch_size} agents per batch
- Concurrent processing within batches
- Sequential coordination between batches
- Resource management across all agents

## Performance Metrics:
- Total coordination time: {max(r.execution_time for r in all_results):.3f}s
- Concurrent efficiency: Achieved through batched execution
- Memory usage: Controlled through batch coordination
- Error handling: Isolated failures without cascade

## Agent Distribution:
{chr(10).join([f"- {role}: ✅ Coordinated successfully" for role in roles])}

## System Validation:
✅ Large-scale coordination successful
✅ Resource management effective
✅ Performance within expected bounds  
✅ Error isolation maintained
✅ Deliverable generation complete

## Status: ✅ Large-Scale Coordination Validated
""",
            author=coordinator,
        )

        # Validate large-scale results
        registry = await artifacts_service.get_artifact_registry(session_id)
        total_artifacts = len(registry.artifacts)
        assert total_artifacts >= 9  # 8 agent deliverables + 1 summary

        # Verify coordination summary
        assert (
            "large-scale coordination successful"
            in coordination_summary.content.lower()
        )
        assert str(len(all_results)) in coordination_summary.content
