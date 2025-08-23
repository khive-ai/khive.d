"""Tests for artifacts handlers (timeout manager and handoff coordinator)."""

import asyncio

import pytest

from khive.services.artifacts.handlers.handoff_coordinator import (
    AgentSpec,
    HandoffCoordinator,
)
from khive.services.artifacts.handlers.timeout_manager import (
    TimeoutConfig,
    TimeoutManager,
    TimeoutType,
)


class TestTimeoutManager:
    """Test the TimeoutManager class."""

    @pytest.fixture
    def timeout_config(self):
        """Create a test timeout configuration."""
        return TimeoutConfig(
            timeout_seconds=5.0, timeout_type=TimeoutType.AGENT_EXECUTION, max_retries=2
        )

    @pytest.fixture
    def timeout_manager(self, timeout_config):
        """Create a TimeoutManager instance."""
        return TimeoutManager(timeout_config)

    @pytest.mark.unit
    def test_timeout_manager_initialization(self, timeout_manager, timeout_config):
        """Test TimeoutManager initialization."""
        assert timeout_manager is not None
        assert timeout_manager.config == timeout_config

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_with_timeout_success(self, timeout_manager):
        """Test successful execution within timeout."""

        async def quick_task():
            await asyncio.sleep(0.1)
            return "success"

        result = await timeout_manager.execute_with_timeout(quick_task())
        assert result == "success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_with_timeout_failure(self, timeout_manager):
        """Test timeout handling for slow tasks."""

        async def slow_task():
            await asyncio.sleep(10)  # Longer than timeout
            return "too slow"

        with pytest.raises(asyncio.TimeoutError):
            await timeout_manager.execute_with_timeout(slow_task())

    @pytest.mark.unit
    def test_timeout_config_validation(self):
        """Test timeout configuration validation."""
        # Valid configuration
        valid_config = TimeoutConfig(agent_execution_timeout=30.0, max_retries=3)
        assert valid_config.agent_execution_timeout == 30.0

        # Invalid configuration should raise error
        with pytest.raises((ValueError, TypeError)):
            TimeoutConfig(
                agent_execution_timeout=-5.0,
                max_retries=1,  # Negative timeout
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_mechanism(self, timeout_manager):
        """Test retry mechanism for failed operations."""
        call_count = 0

        async def flaky_task():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return "success after retry"

        result = await timeout_manager.execute_with_retries(flaky_task)
        assert result == "success after retry"
        assert call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, timeout_manager):
        """Test behavior when max retries are exceeded."""

        async def always_failing_task():
            raise Exception("Always fails")

        with pytest.raises(Exception):
            await timeout_manager.execute_with_retries(always_failing_task)

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_timeout_operations(self, timeout_manager):
        """Test handling of concurrent timeout operations."""

        async def concurrent_task(task_id):
            await asyncio.sleep(0.1)
            return f"task_{task_id}_complete"

        # Run multiple tasks concurrently
        tasks = [
            timeout_manager.execute_with_timeout(concurrent_task(i)) for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        for i, result in enumerate(results):
            assert result == f"task_{i}_complete"


class TestHandoffCoordinator:
    """Test the HandoffCoordinator class."""

    @pytest.fixture
    def agent_spec(self):
        """Create a test agent specification."""
        return AgentSpec(
            agent_id="test_agent_001",
            role="researcher",
            domain="test_domain",
            capabilities=["read", "write", "analyze"],
            session_id="test_session",
        )

    @pytest.fixture
    def handoff_coordinator(self):
        """Create a HandoffCoordinator instance."""
        return HandoffCoordinator()

    @pytest.mark.unit
    def test_handoff_coordinator_initialization(self, handoff_coordinator):
        """Test HandoffCoordinator initialization."""
        assert handoff_coordinator is not None
        assert hasattr(handoff_coordinator, "register_agent")
        assert hasattr(handoff_coordinator, "coordinate_handoff")

    @pytest.mark.unit
    def test_agent_registration(self, handoff_coordinator, agent_spec):
        """Test agent registration."""
        # Register agent
        handoff_coordinator.register_agent(agent_spec)

        # Verify registration
        registered_agents = handoff_coordinator.list_registered_agents()
        assert len(registered_agents) == 1
        assert registered_agents[0].agent_id == agent_spec.agent_id

    @pytest.mark.unit
    def test_duplicate_agent_registration(self, handoff_coordinator, agent_spec):
        """Test handling of duplicate agent registration."""
        # Register agent twice
        handoff_coordinator.register_agent(agent_spec)

        # Second registration should either update or raise error
        with pytest.raises((ValueError, Exception)):
            handoff_coordinator.register_agent(agent_spec)

    @pytest.mark.unit
    def test_agent_capability_validation(self, handoff_coordinator):
        """Test validation of agent capabilities."""
        # Valid agent spec
        valid_spec = AgentSpec(
            agent_id="valid_agent",
            role="analyst",
            domain="test_domain",
            capabilities=["read", "write", "analyze"],
            session_id="test_session",
        )

        handoff_coordinator.register_agent(valid_spec)

        # Invalid agent spec (empty capabilities)
        invalid_spec = AgentSpec(
            agent_id="invalid_agent",
            role="analyst",
            domain="test_domain",
            capabilities=[],  # Empty capabilities
            session_id="test_session",
        )

        with pytest.raises((ValueError, Exception)):
            handoff_coordinator.register_agent(invalid_spec)

    @pytest.mark.unit
    def test_coordinate_handoff_between_agents(self, handoff_coordinator):
        """Test coordinating handoff between agents."""
        # Register source and target agents
        source_agent = AgentSpec(
            agent_id="source_agent",
            role="researcher",
            domain="source_domain",
            capabilities=["read", "analyze"],
            session_id="test_session",
        )

        target_agent = AgentSpec(
            agent_id="target_agent",
            role="implementer",
            domain="target_domain",
            capabilities=["write", "execute"],
            session_id="test_session",
        )

        handoff_coordinator.register_agent(source_agent)
        handoff_coordinator.register_agent(target_agent)

        # Coordinate handoff
        handoff_result = handoff_coordinator.coordinate_handoff(
            source_agent_id="source_agent",
            target_agent_id="target_agent",
            artifacts=["analysis_results.md", "recommendations.json"],
        )

        assert handoff_result is not None
        assert handoff_result.source_agent_id == "source_agent"
        assert handoff_result.target_agent_id == "target_agent"

    @pytest.mark.unit
    def test_handoff_with_nonexistent_agents(self, handoff_coordinator, agent_spec):
        """Test handoff coordination with non-existent agents."""
        # Register only one agent
        handoff_coordinator.register_agent(agent_spec)

        # Try to handoff to non-existent agent
        with pytest.raises((ValueError, Exception)):
            handoff_coordinator.coordinate_handoff(
                source_agent_id=agent_spec.agent_id,
                target_agent_id="nonexistent_agent",
                artifacts=["test_artifact.md"],
            )

    @pytest.mark.integration
    def test_session_isolation_in_handoffs(self, handoff_coordinator):
        """Test that handoffs are properly isolated by session."""
        # Create agents in different sessions
        agent1_session1 = AgentSpec(
            agent_id="agent1",
            role="researcher",
            domain="domain1",
            capabilities=["read"],
            session_id="session_1",
        )

        agent1_session2 = AgentSpec(
            agent_id="agent1",  # Same ID, different session
            role="implementer",
            domain="domain2",
            capabilities=["write"],
            session_id="session_2",
        )

        handoff_coordinator.register_agent(agent1_session1)
        handoff_coordinator.register_agent(agent1_session2)

        # Verify both agents are registered separately
        registered = handoff_coordinator.list_registered_agents()
        assert len(registered) == 2

        # Verify session isolation
        session1_agents = handoff_coordinator.list_agents_by_session("session_1")
        session2_agents = handoff_coordinator.list_agents_by_session("session_2")

        assert len(session1_agents) == 1
        assert len(session2_agents) == 1
        assert session1_agents[0].session_id == "session_1"
        assert session2_agents[0].session_id == "session_2"

    @pytest.mark.performance
    def test_high_volume_agent_registration(self, handoff_coordinator):
        """Test handling of high volume agent registration."""
        # Register many agents
        num_agents = 50
        for i in range(num_agents):
            agent_spec = AgentSpec(
                agent_id=f"bulk_agent_{i}",
                role="tester",
                domain="bulk_domain",
                capabilities=["test"],
                session_id=f"bulk_session_{i % 5}",  # 5 different sessions
            )
            handoff_coordinator.register_agent(agent_spec)

        # Verify all agents are registered
        registered_agents = handoff_coordinator.list_registered_agents()
        assert len(registered_agents) == num_agents

        # Verify session distribution
        unique_sessions = {agent.session_id for agent in registered_agents}
        assert len(unique_sessions) == 5
