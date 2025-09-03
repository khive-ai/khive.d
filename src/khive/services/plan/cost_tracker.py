"""
Cost tracking for planning operations.

Tracks API costs, token usage, and budget constraints.
"""


class CostTracker:
    """Track API costs and usage for planning operations."""

    def __init__(self, config: dict | None = None):
        self.total_cost = 0.0
        self.request_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cached_tokens = 0
        self.config = config or {}

        # Default budgets
        budgets = self.config.get("budgets", {})
        self.token_budget = (
            budgets.get("tokens_per_candidate", 100000) * 10
        )  # Scale for full planning
        self.latency_budget = budgets.get("time_seconds", 60)
        self.cost_budget = budgets.get("cost_usd", 0.01)

    def _get_pricing(self, model_name: str | None) -> dict:
        """Get pricing info from config for a given model."""
        if not model_name or not self.config:
            # Default Gemini Flash pricing
            return {"input_per_1m": 0.10, "output_per_1m": 0.40, "cached_per_1m": 0.025}

        # Search in all config sections for matching model
        for section in ["generators", "judges"]:
            for item in self.config.get(section, []):
                if item.get("model") == model_name:
                    return item.get(
                        "pricing",
                        {
                            "input_per_1m": 0.10,
                            "output_per_1m": 0.40,
                            "cached_per_1m": 0.025,
                        },
                    )

        # Fallback - default Gemini Flash pricing
        return {"input_per_1m": 0.10, "output_per_1m": 0.40, "cached_per_1m": 0.025}

    def add_request(
        self,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        model_name: str | None = None,
    ) -> float:
        """Add a request and calculate cost using config-based pricing."""
        # Update token counts
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cached_tokens += cached_tokens

        # Get pricing from config
        pricing = self._get_pricing(model_name)

        # Calculate cost
        regular_input_tokens = input_tokens - cached_tokens
        input_cost = (regular_input_tokens / 1_000_000) * pricing["input_per_1m"]
        cached_cost = (cached_tokens / 1_000_000) * pricing["cached_per_1m"]
        output_cost = (output_tokens / 1_000_000) * pricing["output_per_1m"]

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

    def add_lionagi_response(self, branch) -> float:
        """
        Extract usage data from LionAGI branch and add to cost tracking.

        Args:
            branch: LionAGI branch after branch.operate() call

        Returns:
            Cost of this request in USD
        """
        try:
            # Get model response from LionAGI
            model_response = branch.msgs.last_response.model_response
            usage = model_response.get("usage", {})
            model = model_response.get("model", "unknown")

            # Extract token counts
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            cached_tokens = usage.get("prompt_tokens_details", {}).get(
                "cached_tokens", 0
            )

            # Add to cost tracking with real data
            return self.add_request(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=cached_tokens,
                model_name=model,
            )

        except Exception as e:
            print(f"Warning: Could not extract usage from LionAGI response: {e}")
            # Fallback to estimate for budget tracking
            return self.add_request(500, 200, model_name="gemini-flash-estimate")

    def reset(self):
        """Reset all counters."""
        self.total_cost = 0.0
        self.request_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cached_tokens = 0
