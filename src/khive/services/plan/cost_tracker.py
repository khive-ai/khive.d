"""
Cost tracking for planning operations.

Tracks API costs, token usage, and budget constraints.
"""

from typing import Optional


class CostTracker:
    """Track API costs and usage for planning operations."""

    def __init__(self):
        self.total_cost = 0.0
        self.request_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cached_tokens = 0

        # Default budgets
        self.token_budget = 100000  # Increased for lionagi multi-eval
        self.latency_budget = 60  # seconds
        self.cost_budget = 0.01  # USD per plan (increased for parallel evals)

    def add_request(
        self,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        model_name: Optional[str] = None,
    ) -> float:
        """
        Add a request and calculate cost.

        Supports different pricing models:
        - OpenAI GPT-4o pricing
        - Nvidia NIM pricing (if available)
        - Generic fallback pricing
        """
        # Update token counts
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cached_tokens += cached_tokens

        # Calculate cost based on model
        if model_name and "gemini" in model_name.lower():
            # Google Gemini Flash pricing via OpenRouter
            regular_input_tokens = input_tokens - cached_tokens
            input_cost = (regular_input_tokens / 1_000_000) * 0.10
            cached_cost = (
                cached_tokens / 1_000_000
            ) * 0.025  # Assume 25% of input cost
            output_cost = (output_tokens / 1_000_000) * 0.40
        elif model_name and "nvidia" in model_name.lower():
            # Nvidia NIM pricing (placeholder - adjust based on actual pricing)
            regular_input_tokens = input_tokens - cached_tokens
            input_cost = (regular_input_tokens / 1_000_000) * 0.05  # Lower cost
            cached_cost = (cached_tokens / 1_000_000) * 0.01
            output_cost = (output_tokens / 1_000_000) * 0.20
        elif model_name and "gpt-4o" in model_name.lower():
            # GPT-4o pricing
            regular_input_tokens = input_tokens - cached_tokens
            input_cost = (regular_input_tokens / 1_000_000) * 2.50
            cached_cost = (cached_tokens / 1_000_000) * 1.25
            output_cost = (output_tokens / 1_000_000) * 10.00
        else:
            # Generic pricing fallback (matches Gemini Flash)
            regular_input_tokens = input_tokens - cached_tokens
            input_cost = (regular_input_tokens / 1_000_000) * 0.10
            cached_cost = (cached_tokens / 1_000_000) * 0.025
            output_cost = (output_tokens / 1_000_000) * 0.40

        cost = input_cost + cached_cost + output_cost

        self.total_cost += cost
        self.request_count += 1

        return cost

    def get_token_budget(self) -> int:
        """Get current token budget."""
        return self.token_budget

    def get_latency_budget(self) -> int:
        """Get current latency budget in seconds."""
        return self.latency_budget

    def set_token_budget(self, budget: int):
        """Set token budget."""
        self.token_budget = budget

    def set_latency_budget(self, budget: int):
        """Set latency budget in seconds."""
        self.latency_budget = budget

    def get_cost_budget(self) -> float:
        """Get current cost budget in USD."""
        return self.cost_budget

    def set_cost_budget(self, budget: float):
        """Set cost budget in USD."""
        self.cost_budget = budget

    def is_over_budget(self) -> bool:
        """Check if current total cost exceeds budget."""
        return self.total_cost > self.cost_budget

    def is_over_token_budget(self) -> bool:
        """Check if total tokens exceed budget."""
        total_tokens = self.total_input_tokens + self.total_output_tokens
        return total_tokens > self.token_budget

    def get_per_evaluator_max_tokens(self, evaluator_count: int) -> int:
        """Calculate max tokens per evaluator to stay within budget."""
        if evaluator_count <= 0:
            return self.token_budget
        return max(
            500, self.token_budget // evaluator_count
        )  # Min 500 tokens per evaluator

    def get_usage_summary(self) -> dict:
        """Get a summary of usage and costs."""
        return {
            "total_cost": self.total_cost,
            "request_count": self.request_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cached_tokens": self.total_cached_tokens,
            "cost_budget": self.cost_budget,
            "token_budget": self.token_budget,
            "over_budget": self.is_over_budget(),
            "over_token_budget": self.is_over_token_budget(),
        }

    def reset(self):
        """Reset all counters."""
        self.total_cost = 0.0
        self.request_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cached_tokens = 0
