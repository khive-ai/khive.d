"""Sophisticated API mocking for realistic OpenAI and external service simulation."""

import asyncio
import json
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock

import pytest


@dataclass
class MockResponseConfig:
    """Configuration for mock API response behavior."""

    base_latency_ms: int = 500
    latency_variance: float = 0.3  # 30% variance
    success_rate: float = 0.95
    rate_limit_probability: float = 0.02
    token_variance: float = 0.2  # Token count variance
    realistic_errors: bool = True
    adaptive_behavior: bool = True


@dataclass
class APIMetrics:
    """Track API usage metrics for testing."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_requests: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    average_latency_ms: float = 0.0
    request_history: List[Dict] = field(default_factory=list)


class MockAPIResponse:
    """Mock API response with realistic behavior patterns."""

    def __init__(self, config: MockResponseConfig = None):
        self.config = config or MockResponseConfig()
        self.metrics = APIMetrics()

    def create_openai_completion_response(
        self, prompt: str, model: str = "gpt-4", response_content: str = None
    ) -> Dict:
        """Create realistic OpenAI completion response."""

        # Simulate latency
        latency_ms = self._calculate_latency()

        # Determine if request should fail
        if random.random() > self.config.success_rate:
            return self._create_error_response()

        # Check for rate limiting
        if random.random() < self.config.rate_limit_probability:
            return self._create_rate_limit_response()

        # Generate response content if not provided
        if response_content is None:
            response_content = self._generate_realistic_response_content(prompt)

        # Calculate token usage
        prompt_tokens = len(prompt.split()) * 1.3  # Approximate tokenization
        completion_tokens = len(response_content.split()) * 1.3
        total_tokens = int(
            (prompt_tokens + completion_tokens)
            * (
                1
                + random.uniform(
                    -self.config.token_variance, self.config.token_variance
                )
            )
        )

        response = {
            "id": f"chatcmpl-{random.randint(10000, 99999)}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": response_content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": int(prompt_tokens),
                "completion_tokens": int(completion_tokens),
                "total_tokens": total_tokens,
            },
            "_mock_latency_ms": latency_ms,
        }

        # Update metrics
        self._update_metrics(True, total_tokens, latency_ms, prompt, response_content)

        return response

    def create_planning_response(self, request_text: str) -> Dict:
        """Create realistic planning service response."""

        complexity_keywords = {
            "simple": ["add", "update", "fix", "change"],
            "moderate": ["implement", "design", "integrate", "optimize"],
            "complex": [
                "architect",
                "distributed",
                "consensus",
                "scalable",
                "security",
            ],
        }

        # Analyze request complexity based on keywords
        complexity = "simple"
        for level, keywords in complexity_keywords.items():
            if any(keyword in request_text.lower() for keyword in keywords):
                complexity = level

        # Determine agent count based on complexity
        agent_counts = {
            "simple": random.randint(2, 3),
            "moderate": random.randint(3, 5),
            "complex": random.randint(5, 8),
        }

        response = {
            "complexity": complexity,
            "confidence": round(random.uniform(0.8, 0.95), 2),
            "reasoning": f"Analysis indicates {complexity} complexity based on requirements scope",
            "recommended_agents": agent_counts[complexity],
            "suggested_roles": self._get_suggested_roles(complexity),
            "suggested_domains": self._get_suggested_domains(request_text),
            "estimated_duration_hours": agent_counts[complexity] * random.randint(2, 8),
            "cost_estimate_usd": round(random.uniform(5.0, 50.0), 2),
        }

        return response

    def _calculate_latency(self) -> int:
        """Calculate realistic latency with variance."""
        variance = self.config.base_latency_ms * self.config.latency_variance
        latency = self.config.base_latency_ms + random.uniform(-variance, variance)
        return max(int(latency), 100)  # Minimum 100ms

    def _create_error_response(self) -> Dict:
        """Create realistic error response."""
        error_types = [
            {
                "error": {
                    "message": "The server is overloaded. Please try again later.",
                    "type": "server_error",
                    "code": "service_unavailable",
                }
            },
            {
                "error": {
                    "message": "Invalid request format",
                    "type": "invalid_request_error",
                    "code": "bad_request",
                }
            },
            {
                "error": {
                    "message": "Content policy violation detected",
                    "type": "policy_violation",
                    "code": "content_policy",
                }
            },
        ]

        error_response = random.choice(error_types)
        self._update_metrics(False, 0, self._calculate_latency())
        return error_response

    def _create_rate_limit_response(self) -> Dict:
        """Create rate limit response."""
        self.metrics.rate_limited_requests += 1
        return {
            "error": {
                "message": "Rate limit exceeded. Please try again later.",
                "type": "rate_limit_error",
                "code": "rate_limit_exceeded",
                "retry_after": random.randint(60, 300),
            }
        }

    def _generate_realistic_response_content(self, prompt: str) -> str:
        """Generate contextually appropriate response content."""

        if "json" in prompt.lower():
            return json.dumps(
                {
                    "complexity": random.choice(["simple", "moderate", "complex"]),
                    "confidence": round(random.uniform(0.7, 0.95), 2),
                    "reasoning": "Generated mock response for testing purposes",
                }
            )

        # Default text response based on prompt keywords
        if any(
            keyword in prompt.lower()
            for keyword in ["analyze", "assessment", "evaluate"]
        ):
            return "Based on the analysis, this appears to be a well-structured request that requires careful consideration of multiple factors."
        elif any(
            keyword in prompt.lower() for keyword in ["implement", "build", "create"]
        ):
            return "To implement this solution, we should follow a systematic approach with proper testing and validation at each step."
        else:
            return "This is a mock response generated for testing purposes. The actual implementation would provide contextually relevant content."

    def _get_suggested_roles(self, complexity: str) -> List[str]:
        """Get role suggestions based on complexity."""
        base_roles = ["researcher", "implementer"]

        if complexity == "moderate":
            base_roles.extend(["architect", "tester"])
        elif complexity == "complex":
            base_roles.extend(["architect", "tester", "reviewer", "security_analyst"])

        return base_roles

    def _get_suggested_domains(self, request_text: str) -> List[str]:
        """Suggest domains based on request content."""
        domain_keywords = {
            "software-architecture": ["architecture", "design", "system"],
            "security": ["security", "auth", "encryption"],
            "performance": ["performance", "optimize", "scale"],
            "database-design": ["database", "data", "sql"],
            "api-design": ["api", "endpoint", "service"],
        }

        suggested_domains = []
        for domain, keywords in domain_keywords.items():
            if any(keyword in request_text.lower() for keyword in keywords):
                suggested_domains.append(domain)

        if not suggested_domains:
            suggested_domains = ["software-architecture"]  # Default

        return suggested_domains[:3]  # Limit to 3 domains

    def _update_metrics(
        self,
        success: bool,
        tokens: int = 0,
        latency_ms: int = 0,
        prompt: str = "",
        response: str = "",
    ):
        """Update API usage metrics."""
        self.metrics.total_requests += 1

        if success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1

        self.metrics.total_tokens_used += tokens
        self.metrics.total_cost_usd += self._calculate_cost(tokens)

        # Update average latency
        total_latency = self.metrics.average_latency_ms * (
            self.metrics.total_requests - 1
        )
        self.metrics.average_latency_ms = (
            total_latency + latency_ms
        ) / self.metrics.total_requests

        # Store request in history
        self.metrics.request_history.append(
            {
                "timestamp": time.time(),
                "success": success,
                "tokens": tokens,
                "latency_ms": latency_ms,
                "prompt_length": len(prompt),
                "response_length": len(response),
            }
        )

    def _calculate_cost(self, tokens: int) -> float:
        """Calculate cost based on token usage."""
        # Approximate GPT-4 pricing
        cost_per_1k_tokens = 0.03
        return (tokens / 1000) * cost_per_1k_tokens


class MockOpenAIClient:
    """Mock OpenAI client with realistic behavior patterns."""

    def __init__(self, config: MockResponseConfig = None):
        self.config = config or MockResponseConfig()
        self.response_generator = MockAPIResponse(config)
        self.chat = self._create_chat_interface()

    def _create_chat_interface(self):
        """Create mock chat interface."""
        chat_mock = MagicMock()
        completions_mock = MagicMock()

        def create_completion(**kwargs):
            messages = kwargs.get("messages", [])
            model = kwargs.get("model", "gpt-4")

            # Extract the last user message as prompt
            prompt = ""
            for message in reversed(messages):
                if message.get("role") == "user":
                    prompt = message.get("content", "")
                    break

            response = self.response_generator.create_openai_completion_response(
                prompt=prompt, model=model
            )

            # Simulate latency
            if "_mock_latency_ms" in response:
                latency_seconds = response.pop("_mock_latency_ms") / 1000
                time.sleep(latency_seconds)

            # Convert to mock response object
            mock_response = MagicMock()
            mock_response.choices = []

            for choice in response.get("choices", []):
                choice_mock = MagicMock()
                choice_mock.message.content = choice["message"]["content"]
                mock_response.choices.append(choice_mock)

            return mock_response

        # Set up async version
        async def create_async_completion(**kwargs):
            messages = kwargs.get("messages", [])
            model = kwargs.get("model", "gpt-4")

            prompt = ""
            for message in reversed(messages):
                if message.get("role") == "user":
                    prompt = message.get("content", "")
                    break

            response = self.response_generator.create_openai_completion_response(
                prompt=prompt, model=model
            )

            # Simulate async latency
            if "_mock_latency_ms" in response:
                latency_seconds = response.pop("_mock_latency_ms") / 1000
                await asyncio.sleep(latency_seconds)

            # Convert to mock response object
            mock_response = MagicMock()
            mock_response.choices = []

            for choice in response.get("choices", []):
                choice_mock = MagicMock()
                choice_mock.message.content = choice["message"]["content"]
                mock_response.choices.append(choice_mock)

            return mock_response

        completions_mock.create = create_completion
        completions_mock.create = AsyncMock(side_effect=create_async_completion)
        chat_mock.completions = completions_mock

        return chat_mock

    def get_metrics(self) -> APIMetrics:
        """Get API usage metrics."""
        return self.response_generator.metrics

    def reset_metrics(self):
        """Reset API usage metrics."""
        self.response_generator.metrics = APIMetrics()


class APIResponseBuilder:
    """Builder pattern for creating complex API responses."""

    def __init__(self):
        self.response_data = {}
        self.config = MockResponseConfig()

    def with_success_rate(self, rate: float):
        """Set success rate."""
        self.config.success_rate = rate
        return self

    def with_latency(self, base_ms: int, variance: float = 0.3):
        """Set latency configuration."""
        self.config.base_latency_ms = base_ms
        self.config.latency_variance = variance
        return self

    def with_content(self, content: str):
        """Set response content."""
        self.response_data["content"] = content
        return self

    def with_error_probability(self, probability: float):
        """Set error probability."""
        self.config.success_rate = 1.0 - probability
        return self

    def with_rate_limiting(self, probability: float = 0.05):
        """Enable rate limiting simulation."""
        self.config.rate_limit_probability = probability
        return self

    def build(self) -> MockAPIResponse:
        """Build the configured mock API response."""
        response = MockAPIResponse(self.config)

        # Apply any custom response data
        if hasattr(self, "_custom_content"):
            response._custom_content = self.response_data.get("content")

        return response


# Convenience functions for creating mock responses
def create_realistic_openai_response(
    prompt: str, complexity: str = "moderate", success_rate: float = 0.95
) -> MockOpenAIClient:
    """Create a realistic OpenAI client mock."""
    config = MockResponseConfig(
        base_latency_ms=800 if complexity == "complex" else 500,
        success_rate=success_rate,
        realistic_errors=True,
        adaptive_behavior=True,
    )
    return MockOpenAIClient(config)


def create_planning_service_mock(adaptive: bool = True) -> MockAPIResponse:
    """Create mock for planning service responses."""
    config = MockResponseConfig(
        base_latency_ms=1200, success_rate=0.92, adaptive_behavior=adaptive
    )
    return MockAPIResponse(config)


__all__ = [
    "MockResponseConfig",
    "APIMetrics",
    "MockAPIResponse",
    "MockOpenAIClient",
    "APIResponseBuilder",
    "create_realistic_openai_response",
    "create_planning_service_mock",
]
