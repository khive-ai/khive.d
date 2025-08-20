"""Mock framework for external planning models.

This module provides comprehensive mocking for external API services,
particularly OpenAI GPT models used in orchestration evaluation.
Supports various scenarios including success, failure, latency, and cost simulation.
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from khive.services.plan.models import OrchestrationEvaluation
from openai.types.completion_usage import CompletionUsage

# ============================================================================
# Mock Response Configuration
# ============================================================================


@dataclass
class MockResponseConfig:
    """Configuration for mock API responses."""

    # Response timing
    base_latency_ms: float = 500
    latency_variance_ms: float = 200

    # Token usage
    base_prompt_tokens: int = 400
    base_completion_tokens: int = 200
    token_variance: float = 0.2

    # Cost simulation
    input_token_cost_per_million: float = 0.10
    output_token_cost_per_million: float = 0.40
    cached_token_cost_per_million: float = 0.025

    # Reliability
    success_rate: float = 0.95
    timeout_rate: float = 0.02
    rate_limit_rate: float = 0.01

    # Response variation
    complexity_variation: bool = True
    agent_count_variation: bool = True
    confidence_variation: bool = True


@dataclass
class MockEvaluationTemplate:
    """Template for generating mock evaluations."""

    complexity: str = "medium"
    complexity_reason: str = "Multi-objective task requiring coordination"
    total_agents: int = 5
    agent_reason: str = "Balanced team for comprehensive coverage"
    rounds_needed: int = 2
    role_priorities: list[str] = field(
        default_factory=lambda: ["researcher", "architect", "implementer"]
    )
    primary_domains: list[str] = field(default_factory=lambda: ["distributed-systems"])
    domain_reason: str = "Core technical expertise required"
    workflow_pattern: str = "parallel"
    workflow_reason: str = "Tasks can be executed concurrently"
    quality_level: str = "thorough"
    quality_reason: str = "Important system requiring validation"
    rules_applied: list[str] = field(default_factory=lambda: ["complexity_assessment"])
    confidence: float = 0.8
    summary: str = "Standard orchestration evaluation"

    def with_variation(self, config: MockResponseConfig) -> "MockEvaluationTemplate":
        """Apply configured variations to the template."""
        template = MockEvaluationTemplate(
            complexity=self.complexity,
            complexity_reason=self.complexity_reason,
            total_agents=self.total_agents,
            agent_reason=self.agent_reason,
            rounds_needed=self.rounds_needed,
            role_priorities=self.role_priorities.copy(),
            primary_domains=self.primary_domains.copy(),
            domain_reason=self.domain_reason,
            workflow_pattern=self.workflow_pattern,
            workflow_reason=self.workflow_reason,
            quality_level=self.quality_level,
            quality_reason=self.quality_reason,
            rules_applied=self.rules_applied.copy(),
            confidence=self.confidence,
            summary=self.summary,
        )

        if config.complexity_variation:
            complexities = ["simple", "medium", "complex", "very_complex"]
            if random.random() < 0.3:  # 30% chance to vary complexity
                template.complexity = random.choice(complexities)

        if config.agent_count_variation:
            variance = int(template.total_agents * 0.3)
            template.total_agents += random.randint(-variance, variance)
            template.total_agents = max(1, min(20, template.total_agents))

        if config.confidence_variation:
            confidence_change = random.uniform(-0.15, 0.15)
            template.confidence = max(
                0.0, min(1.0, template.confidence + confidence_change)
            )

        return template


# ============================================================================
# External Model Mock Framework
# ============================================================================


class MockOpenAIClient:
    """Comprehensive mock for OpenAI client with realistic behavior simulation."""

    def __init__(self, config: MockResponseConfig = None):
        self.config = config or MockResponseConfig()
        self.request_count = 0
        self.total_cost = 0.0
        self.request_history = []

        # Set up mock structure
        self.beta = Mock()
        self.beta.chat = Mock()
        self.beta.chat.completions = Mock()
        self.beta.chat.completions.parse = self._create_parse_mock()

    def _create_parse_mock(self):
        """Create the parse method mock with realistic behavior."""

        async def mock_parse(*args, **kwargs):
            return await self._simulate_api_call(*args, **kwargs)

        # For synchronous calls (used with asyncio.to_thread)
        def sync_parse(*args, **kwargs):
            return self._simulate_sync_api_call(*args, **kwargs)

        # Set up both async and sync versions
        parse_mock = AsyncMock(side_effect=mock_parse)
        parse_mock.sync = Mock(side_effect=sync_parse)

        return parse_mock

    async def _simulate_api_call(self, *args, **kwargs) -> Mock:
        """Simulate realistic API call with latency, failures, and costs."""
        self.request_count += 1

        # Record request
        request_info = {
            "timestamp": time.time(),
            "args": args,
            "kwargs": kwargs,
            "request_id": self.request_count,
        }
        self.request_history.append(request_info)

        # Simulate network latency
        latency = (
            max(
                0,
                random.normalvariate(
                    self.config.base_latency_ms, self.config.latency_variance_ms
                ),
            )
            / 1000
        )
        await asyncio.sleep(latency)

        # Simulate failures
        rand = random.random()

        if rand < (1 - self.config.success_rate):
            if rand < self.config.timeout_rate:
                raise asyncio.TimeoutError("Mock API timeout")
            if rand < self.config.timeout_rate + self.config.rate_limit_rate:
                raise Exception("Rate limit exceeded")
            raise Exception("API error")

        # Generate response
        return self._generate_response(request_info)

    def _simulate_sync_api_call(self, *args, **kwargs) -> Mock:
        """Simulate synchronous API call (for asyncio.to_thread usage)."""
        self.request_count += 1

        # Record request
        request_info = {
            "timestamp": time.time(),
            "args": args,
            "kwargs": kwargs,
            "request_id": self.request_count,
        }
        self.request_history.append(request_info)

        # Simulate latency (synchronous sleep)
        latency = (
            max(
                0,
                random.normalvariate(
                    self.config.base_latency_ms, self.config.latency_variance_ms
                ),
            )
            / 1000
        )
        time.sleep(latency)

        # Simulate failures
        rand = random.random()

        if rand < (1 - self.config.success_rate):
            if rand < self.config.timeout_rate:
                raise TimeoutError("Mock API timeout")
            if rand < self.config.timeout_rate + self.config.rate_limit_rate:
                raise Exception("Rate limit exceeded")
            raise Exception("API error")

        # Generate response
        return self._generate_response(request_info)

    def _generate_response(self, request_info: dict) -> Mock:
        """Generate a realistic API response."""
        # Extract request details for personalized response
        messages = request_info.get("kwargs", {}).get("messages", [])
        user_content = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_content = msg.get("content", "")
                break

        # Generate token usage with variation
        prompt_tokens = max(
            1,
            int(
                random.normalvariate(
                    self.config.base_prompt_tokens,
                    self.config.base_prompt_tokens * self.config.token_variance,
                )
            ),
        )

        completion_tokens = max(
            1,
            int(
                random.normalvariate(
                    self.config.base_completion_tokens,
                    self.config.base_completion_tokens * self.config.token_variance,
                )
            ),
        )

        # Calculate cost
        cost = (
            prompt_tokens / 1_000_000
        ) * self.config.input_token_cost_per_million + (
            completion_tokens / 1_000_000
        ) * self.config.output_token_cost_per_million
        self.total_cost += cost

        # Generate evaluation based on request content
        evaluation = self._generate_evaluation_from_request(user_content)

        # Create mock response structure
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.parsed = evaluation

        mock_response.usage = CompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

        return mock_response

    def _generate_evaluation_from_request(
        self, request_content: str
    ) -> OrchestrationEvaluation:
        """Generate contextually appropriate evaluation based on request."""
        # Analyze request for complexity indicators
        content_lower = request_content.lower()

        # Determine complexity based on content
        if any(
            indicator in content_lower
            for indicator in ["simple", "basic", "single", "quick"]
        ):
            template = MockEvaluationTemplate(
                complexity="simple",
                total_agents=random.randint(1, 3),
                complexity_reason="Simple task with clear objectives",
            )
        elif any(
            indicator in content_lower
            for indicator in ["complex", "distributed", "consensus", "byzantine"]
        ):
            template = MockEvaluationTemplate(
                complexity="complex",
                total_agents=random.randint(6, 10),
                complexity_reason="Complex distributed system requiring specialized expertise",
            )
        elif any(
            indicator in content_lower
            for indicator in ["research", "novel", "cutting-edge", "frontier"]
        ):
            template = MockEvaluationTemplate(
                complexity="very_complex",
                total_agents=random.randint(10, 15),
                complexity_reason="Research-level work requiring deep expertise",
            )
        else:
            template = MockEvaluationTemplate()  # Default medium complexity

        # Apply variations
        template = template.with_variation(self.config)

        # Create OrchestrationEvaluation
        return OrchestrationEvaluation(
            complexity=template.complexity,
            complexity_reason=template.complexity_reason,
            total_agents=template.total_agents,
            agent_reason=template.agent_reason,
            rounds_needed=template.rounds_needed,
            role_priorities=template.role_priorities,
            primary_domains=template.primary_domains,
            domain_reason=template.domain_reason,
            workflow_pattern=template.workflow_pattern,
            workflow_reason=template.workflow_reason,
            quality_level=template.quality_level,
            quality_reason=template.quality_reason,
            rules_applied=template.rules_applied,
            confidence=template.confidence,
            summary=template.summary,
        )

    def get_usage_stats(self) -> dict[str, Any]:
        """Get usage statistics for analysis."""
        return {
            "request_count": self.request_count,
            "total_cost": self.total_cost,
            "average_cost_per_request": self.total_cost / max(1, self.request_count),
            "request_history": self.request_history,
        }

    def reset_stats(self):
        """Reset usage statistics."""
        self.request_count = 0
        self.total_cost = 0.0
        self.request_history = []


class MockMultiAgentEvaluator:
    """Mock for multi-agent evaluation scenarios with different agent perspectives."""

    def __init__(self, agent_configs: list[dict[str, Any]] | None = None):
        self.agent_configs = agent_configs or self._default_agent_configs()
        self.clients = {}

        # Create individual mock clients for each agent
        for config in self.agent_configs:
            agent_name = config["name"]
            mock_config = MockResponseConfig(
                success_rate=config.get("reliability", 0.95),
                base_latency_ms=config.get("latency_ms", 500),
                complexity_variation=config.get("vary_complexity", True),
            )
            self.clients[agent_name] = MockOpenAIClient(mock_config)

    def _default_agent_configs(self) -> list[dict[str, Any]]:
        """Default agent configurations for testing."""
        return [
            {
                "name": "efficiency_analyst",
                "bias": "minimize_resources",
                "reliability": 0.98,
                "latency_ms": 400,
                "vary_complexity": False,
            },
            {
                "name": "quality_architect",
                "bias": "maximize_quality",
                "reliability": 0.95,
                "latency_ms": 600,
                "vary_complexity": True,
            },
            {
                "name": "risk_auditor",
                "bias": "paranoid_about_risks",
                "reliability": 0.97,
                "latency_ms": 700,
                "vary_complexity": True,
            },
            {
                "name": "innovation_strategist",
                "bias": "breakthrough_solutions",
                "reliability": 0.92,
                "latency_ms": 800,
                "vary_complexity": True,
            },
        ]

    def get_client(self, agent_name: str) -> MockOpenAIClient:
        """Get mock client for specific agent."""
        return self.clients.get(agent_name)

    async def evaluate_with_all_agents(self, request: str) -> list[dict[str, Any]]:
        """Simulate evaluation with all configured agents."""
        results = []

        for config in self.agent_configs:
            agent_name = config["name"]
            client = self.clients[agent_name]

            try:
                response = await client.beta.chat.completions.parse(
                    model="gpt-5-nano",
                    messages=[
                        {"role": "system", "content": f"You are {agent_name}"},
                        {"role": "user", "content": request},
                    ],
                    response_format=OrchestrationEvaluation,
                )

                results.append({
                    "config": config,
                    "evaluation": response.choices[0].message.parsed,
                    "cost": 0.001,  # Simulated cost
                    "usage": response.usage,
                    "response_time_ms": 500,  # Simulated response time
                    "success": True,
                })

            except Exception as e:
                results.append({"config": config, "error": str(e), "success": False})

        return results

    def get_combined_stats(self) -> dict[str, Any]:
        """Get combined statistics from all agents."""
        combined_stats = {"total_requests": 0, "total_cost": 0.0, "agent_stats": {}}

        for agent_name, client in self.clients.items():
            stats = client.get_usage_stats()
            combined_stats["agent_stats"][agent_name] = stats
            combined_stats["total_requests"] += stats["request_count"]
            combined_stats["total_cost"] += stats["total_cost"]

        return combined_stats


# ============================================================================
# Scenario-Specific Mock Factories
# ============================================================================


class MockScenarioFactory:
    """Factory for creating mocks for specific test scenarios."""

    @staticmethod
    def create_high_performance_mock() -> MockOpenAIClient:
        """Create mock optimized for performance testing."""
        config = MockResponseConfig(
            base_latency_ms=200,
            latency_variance_ms=50,
            success_rate=0.99,
            timeout_rate=0.001,
            complexity_variation=False,
            agent_count_variation=False,
            confidence_variation=False,
        )
        return MockOpenAIClient(config)

    @staticmethod
    def create_unreliable_mock() -> MockOpenAIClient:
        """Create mock for testing error handling and resilience."""
        config = MockResponseConfig(
            base_latency_ms=1000,
            latency_variance_ms=500,
            success_rate=0.7,
            timeout_rate=0.15,
            rate_limit_rate=0.1,
        )
        return MockOpenAIClient(config)

    @staticmethod
    def create_cost_tracking_mock() -> MockOpenAIClient:
        """Create mock for testing cost tracking functionality."""
        config = MockResponseConfig(
            base_prompt_tokens=800,
            base_completion_tokens=400,
            token_variance=0.3,
            input_token_cost_per_million=0.15,  # Higher cost for testing
            output_token_cost_per_million=0.50,
        )
        return MockOpenAIClient(config)

    @staticmethod
    def create_consensus_building_mock() -> MockMultiAgentEvaluator:
        """Create mock for testing consensus building across multiple agents."""
        agent_configs = [
            {
                "name": "efficiency_focused",
                "bias": "minimal_agents",
                "reliability": 0.95,
                "complexity_tendency": "lower",
            },
            {
                "name": "quality_focused",
                "bias": "thorough_validation",
                "reliability": 0.98,
                "complexity_tendency": "higher",
            },
            {
                "name": "balanced_approach",
                "bias": "pragmatic",
                "reliability": 0.96,
                "complexity_tendency": "neutral",
            },
        ]
        return MockMultiAgentEvaluator(agent_configs)


# ============================================================================
# Pytest Fixtures for Mock Framework
# ============================================================================


@pytest.fixture
def mock_openai_client():
    """Standard mock OpenAI client for testing."""
    return MockOpenAIClient()


@pytest.fixture
def high_performance_mock():
    """High-performance mock for performance testing."""
    return MockScenarioFactory.create_high_performance_mock()


@pytest.fixture
def unreliable_mock():
    """Unreliable mock for error handling testing."""
    return MockScenarioFactory.create_unreliable_mock()


@pytest.fixture
def cost_tracking_mock():
    """Cost tracking mock for budget testing."""
    return MockScenarioFactory.create_cost_tracking_mock()


@pytest.fixture
def multi_agent_evaluator():
    """Multi-agent evaluator for consensus testing."""
    return MockScenarioFactory.create_consensus_building_mock()


@pytest.fixture
def mock_openai_environment(mock_openai_client):
    """Complete mock environment for OpenAI integration."""
    with pytest.mock.patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
        with pytest.mock.patch(
            "khive.services.plan.planner_service.OpenAI"
        ) as mock_class:
            mock_class.return_value = mock_openai_client
            yield mock_openai_client


# ============================================================================
# Advanced Mock Behaviors
# ============================================================================


class AdaptiveMockBehavior:
    """Advanced mock that adapts behavior based on request patterns."""

    def __init__(self, base_client: MockOpenAIClient):
        self.base_client = base_client
        self.request_patterns = {}
        self.learning_enabled = True

    def learn_from_request(self, request_content: str, expected_complexity: str):
        """Learn expected responses for request patterns."""
        if not self.learning_enabled:
            return

        # Extract key patterns from request
        patterns = self._extract_patterns(request_content)

        for pattern in patterns:
            if pattern not in self.request_patterns:
                self.request_patterns[pattern] = []
            self.request_patterns[pattern].append(expected_complexity)

    def _extract_patterns(self, content: str) -> list[str]:
        """Extract meaningful patterns from request content."""
        content_lower = content.lower()
        patterns = []

        # Complexity indicators
        complexity_words = [
            "simple",
            "basic",
            "complex",
            "sophisticated",
            "research",
            "novel",
        ]
        for word in complexity_words:
            if word in content_lower:
                patterns.append(f"complexity:{word}")

        # Domain indicators
        domain_words = [
            "distributed",
            "consensus",
            "api",
            "frontend",
            "database",
            "microservices",
        ]
        for word in domain_words:
            if word in content_lower:
                patterns.append(f"domain:{word}")

        # Scale indicators
        scale_words = ["single", "multiple", "entire", "platform", "system"]
        for word in scale_words:
            if word in content_lower:
                patterns.append(f"scale:{word}")

        return patterns

    async def adaptive_parse(self, *args, **kwargs):
        """Parse with adaptive behavior based on learned patterns."""
        # Extract request content
        messages = kwargs.get("messages", [])
        user_content = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_content = msg.get("content", "")
                break

        # Check for learned patterns
        patterns = self._extract_patterns(user_content)
        predicted_complexity = self._predict_complexity(patterns)

        # Modify mock behavior based on prediction
        if predicted_complexity:
            # Temporarily adjust mock configuration
            original_template = (
                self.base_client._generate_evaluation_from_request.__self__
            )
            # Apply learned behavior...

        # Delegate to base client
        return await self.base_client.beta.chat.completions.parse(*args, **kwargs)

    def _predict_complexity(self, patterns: list[str]) -> str | None:
        """Predict complexity based on learned patterns."""
        complexity_votes = []

        for pattern in patterns:
            if pattern in self.request_patterns:
                complexity_votes.extend(self.request_patterns[pattern])

        if not complexity_votes:
            return None

        # Return most common complexity
        from collections import Counter

        return Counter(complexity_votes).most_common(1)[0][0]
