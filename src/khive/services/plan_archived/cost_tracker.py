"""
Cost tracking from original orchestration_planner.py
"""


class CostTracker:
    """Track API costs"""

    def __init__(self):
        self.total_cost = 0.0
        self.request_count = 0
        # Default budgets
        self.token_budget = 10000  # tokens
        self.latency_budget = 60  # seconds
        self.cost_budget = 0.0035  # USD per plan (target budget)

    def add_request(
        self, input_tokens: int, output_tokens: int, cached_tokens: int = 0
    ):
        # GPT-4.1-nano pricing (per million tokens)
        # Input tokens: $0.10
        # Cached tokens: $0.025
        # Output tokens: $0.40

        regular_input_tokens = input_tokens - cached_tokens
        input_cost = (regular_input_tokens / 1_000_000) * 0.10
        cached_cost = (cached_tokens / 1_000_000) * 0.025
        output_cost = (output_tokens / 1_000_000) * 0.40

        cost = input_cost + cached_cost + output_cost

        self.total_cost += cost
        self.request_count += 1

        return cost

    def get_token_budget(self) -> int:
        """Get current token budget"""
        return self.token_budget

    def get_latency_budget(self) -> int:
        """Get current latency budget in seconds"""
        return self.latency_budget

    def set_token_budget(self, budget: int):
        """Set token budget"""
        self.token_budget = budget

    def set_latency_budget(self, budget: int):
        """Set latency budget in seconds"""
        self.latency_budget = budget

    def get_cost_budget(self) -> float:
        """Get current cost budget in USD"""
        return self.cost_budget

    def set_cost_budget(self, budget: float):
        """Set cost budget in USD"""
        self.cost_budget = budget

    def is_over_budget(self) -> bool:
        """Check if current total cost exceeds budget"""
        return self.total_cost > self.cost_budget

    def get_per_persona_max_tokens(self, persona_count: int) -> int:
        """Calculate max tokens per persona to stay within budget"""
        if persona_count <= 0:
            return self.token_budget
        return max(
            500, self.token_budget // persona_count
        )  # Min 500 tokens per persona
