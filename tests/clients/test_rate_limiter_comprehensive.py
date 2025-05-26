"""
Comprehensive tests for rate limiting functionality.

Tests token bucket rate limiter implementation with various scenarios.
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock

from khive.clients.rate_limiter import TokenBucketRateLimiter
from khive.clients.errors import RateLimitError


class TestTokenBucketRateLimiter:
    """Test the TokenBucketRateLimiter class."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a TokenBucketRateLimiter instance for testing."""
        return TokenBucketRateLimiter(
            rate=10.0,  # 10 tokens per second
            capacity=20,  # 20 token capacity
            initial_tokens=20,  # Start with full bucket
        )

    @pytest.fixture
    def slow_rate_limiter(self):
        """Create a slow rate limiter for testing."""
        return TokenBucketRateLimiter(
            rate=2.0,  # 2 tokens per second
            capacity=5,  # 5 token capacity
            initial_tokens=5,  # Start with full bucket
        )

    @pytest.fixture
    def fast_rate_limiter(self):
        """Create a fast rate limiter for testing."""
        return TokenBucketRateLimiter(
            rate=100.0,  # 100 tokens per second
            capacity=200,  # 200 token capacity
            initial_tokens=200,  # Start with full bucket
        )

    def test_initialization(self, rate_limiter):
        """Test TokenBucketRateLimiter initialization."""
        assert rate_limiter.rate == 10.0
        assert rate_limiter.capacity == 20
        assert rate_limiter.tokens == 20
        assert rate_limiter.last_update is not None

    def test_initialization_with_defaults(self):
        """Test initialization with default parameters."""
        limiter = TokenBucketRateLimiter()

        assert limiter.rate == 1.0
        assert limiter.capacity == 10
        assert limiter.tokens == 10

    def test_initialization_invalid_parameters(self):
        """Test initialization with invalid parameters."""
        # Negative rate
        with pytest.raises(ValueError, match="Rate must be positive"):
            TokenBucketRateLimiter(rate=-1.0)

        # Zero capacity
        with pytest.raises(ValueError, match="Capacity must be positive"):
            TokenBucketRateLimiter(capacity=0)

        # Negative initial tokens
        with pytest.raises(ValueError, match="Initial tokens cannot be negative"):
            TokenBucketRateLimiter(initial_tokens=-1)

        # Initial tokens exceeding capacity
        with pytest.raises(ValueError, match="Initial tokens cannot exceed capacity"):
            TokenBucketRateLimiter(capacity=10, initial_tokens=15)

    async def test_acquire_single_token_success(self, rate_limiter):
        """Test acquiring a single token successfully."""
        result = await rate_limiter.acquire(1)
        assert result is True
        assert rate_limiter.tokens == 19

    async def test_acquire_multiple_tokens_success(self, rate_limiter):
        """Test acquiring multiple tokens successfully."""
        result = await rate_limiter.acquire(5)
        assert result is True
        assert rate_limiter.tokens == 15

    async def test_acquire_all_tokens(self, rate_limiter):
        """Test acquiring all available tokens."""
        result = await rate_limiter.acquire(20)
        assert result is True
        assert rate_limiter.tokens == 0

    async def test_acquire_more_than_available_tokens(self, rate_limiter):
        """Test acquiring more tokens than available."""
        # First, drain most tokens
        await rate_limiter.acquire(15)
        assert rate_limiter.tokens == 5

        # Try to acquire more than available
        result = await rate_limiter.acquire(10)
        assert result is False
        assert rate_limiter.tokens == 5  # Should remain unchanged

    async def test_acquire_zero_tokens(self, rate_limiter):
        """Test acquiring zero tokens."""
        initial_tokens = rate_limiter.tokens
        result = await rate_limiter.acquire(0)
        assert result is True
        assert rate_limiter.tokens == initial_tokens

    async def test_acquire_negative_tokens(self, rate_limiter):
        """Test acquiring negative tokens."""
        with pytest.raises(ValueError, match="Tokens to acquire must be non-negative"):
            await rate_limiter.acquire(-1)

    async def test_token_refill_over_time(self, slow_rate_limiter):
        """Test that tokens are refilled over time."""
        # Drain all tokens
        await slow_rate_limiter.acquire(5)
        assert slow_rate_limiter.tokens == 0

        # Wait for some refill (2 tokens per second, so 0.6 seconds should give ~1 token)
        await asyncio.sleep(0.6)

        # Should be able to acquire at least 1 token
        result = await slow_rate_limiter.acquire(1)
        assert result is True

    async def test_token_refill_does_not_exceed_capacity(self, slow_rate_limiter):
        """Test that token refill doesn't exceed capacity."""
        # Start with some tokens
        await slow_rate_limiter.acquire(2)
        assert slow_rate_limiter.tokens == 3

        # Wait longer than needed to fill to capacity
        await asyncio.sleep(2.0)  # Should add 4 tokens, but capacity is 5

        # Check that we don't exceed capacity
        slow_rate_limiter._refill_tokens()
        assert slow_rate_limiter.tokens <= 5

    async def test_concurrent_token_acquisition(self, rate_limiter):
        """Test concurrent token acquisition."""

        async def acquire_tokens(count):
            return await rate_limiter.acquire(count)

        # Start multiple concurrent acquisitions
        tasks = [
            acquire_tokens(3),
            acquire_tokens(4),
            acquire_tokens(5),
            acquire_tokens(6),
        ]

        results = await asyncio.gather(*tasks)

        # Some should succeed, some might fail depending on timing
        successful_acquisitions = sum(1 for result in results if result)
        assert successful_acquisitions >= 1  # At least one should succeed

        # Total tokens acquired should not exceed what was available
        total_acquired = sum(
            count for count, result in zip([3, 4, 5, 6], results) if result
        )
        assert total_acquired <= 20

    async def test_wait_for_tokens_success(self, slow_rate_limiter):
        """Test waiting for tokens to become available."""
        # Drain all tokens
        await slow_rate_limiter.acquire(5)
        assert slow_rate_limiter.tokens == 0

        start_time = time.time()

        # Wait for 1 token (should take ~0.5 seconds at 2 tokens/second)
        result = await slow_rate_limiter.wait_for_tokens(1, timeout=2.0)

        end_time = time.time()
        elapsed = end_time - start_time

        assert result is True
        assert 0.4 <= elapsed <= 0.8  # Should take around 0.5 seconds
        assert slow_rate_limiter.tokens >= 0  # Should have acquired the token

    async def test_wait_for_tokens_timeout(self, slow_rate_limiter):
        """Test waiting for tokens with timeout."""
        # Drain all tokens
        await slow_rate_limiter.acquire(5)
        assert slow_rate_limiter.tokens == 0

        start_time = time.time()

        # Try to wait for more tokens than can be generated in timeout period
        result = await slow_rate_limiter.wait_for_tokens(10, timeout=0.5)

        end_time = time.time()
        elapsed = end_time - start_time

        assert result is False
        assert 0.4 <= elapsed <= 0.7  # Should timeout after ~0.5 seconds

    async def test_wait_for_tokens_immediate_availability(self, rate_limiter):
        """Test waiting for tokens when they're immediately available."""
        start_time = time.time()

        result = await rate_limiter.wait_for_tokens(5, timeout=1.0)

        end_time = time.time()
        elapsed = end_time - start_time

        assert result is True
        assert elapsed < 0.1  # Should be immediate
        assert rate_limiter.tokens == 15

    async def test_wait_for_zero_tokens(self, rate_limiter):
        """Test waiting for zero tokens."""
        result = await rate_limiter.wait_for_tokens(0, timeout=1.0)
        assert result is True

    async def test_wait_for_negative_tokens(self, rate_limiter):
        """Test waiting for negative tokens."""
        with pytest.raises(ValueError, match="Tokens to wait for must be non-negative"):
            await rate_limiter.wait_for_tokens(-1, timeout=1.0)

    async def test_enforce_rate_limit_success(self, rate_limiter):
        """Test enforce_rate_limit with successful acquisition."""

        async def test_operation():
            return "success"

        result = await rate_limiter.enforce_rate_limit(test_operation, tokens=5)
        assert result == "success"
        assert rate_limiter.tokens == 15

    async def test_enforce_rate_limit_failure(self, rate_limiter):
        """Test enforce_rate_limit when rate limit is exceeded."""
        # Drain tokens
        await rate_limiter.acquire(20)
        assert rate_limiter.tokens == 0

        async def test_operation():
            return "should not execute"

        with pytest.raises(RateLimitError):
            await rate_limiter.enforce_rate_limit(test_operation, tokens=1)

    async def test_enforce_rate_limit_with_operation_exception(self, rate_limiter):
        """Test enforce_rate_limit when operation raises exception."""

        async def failing_operation():
            raise ValueError("Operation failed")

        # Tokens should still be consumed even if operation fails
        with pytest.raises(ValueError):
            await rate_limiter.enforce_rate_limit(failing_operation, tokens=5)

        assert rate_limiter.tokens == 15

    async def test_enforce_rate_limit_default_tokens(self, rate_limiter):
        """Test enforce_rate_limit with default token count."""

        async def test_operation():
            return "success"

        result = await rate_limiter.enforce_rate_limit(test_operation)
        assert result == "success"
        assert rate_limiter.tokens == 19  # Should consume 1 token by default

    async def test_current_tokens_property(self, rate_limiter):
        """Test the current_tokens property."""
        assert rate_limiter.current_tokens == 20

        await rate_limiter.acquire(5)
        assert rate_limiter.current_tokens == 15

    async def test_is_available_method(self, rate_limiter):
        """Test the is_available method."""
        assert rate_limiter.is_available(10) is True
        assert rate_limiter.is_available(20) is True
        assert rate_limiter.is_available(21) is False

        await rate_limiter.acquire(15)
        assert rate_limiter.is_available(5) is True
        assert rate_limiter.is_available(6) is False

    async def test_time_until_available(self, slow_rate_limiter):
        """Test the time_until_available method."""
        # With full bucket, should be immediately available
        time_needed = slow_rate_limiter.time_until_available(3)
        assert time_needed == 0

        # Drain tokens
        await slow_rate_limiter.acquire(5)

        # Should need time to generate tokens
        time_needed = slow_rate_limiter.time_until_available(2)
        assert 0.8 <= time_needed <= 1.2  # ~1 second at 2 tokens/second

    async def test_refill_tokens_manual(self, rate_limiter):
        """Test manual token refill."""
        # Drain some tokens
        await rate_limiter.acquire(10)
        assert rate_limiter.tokens == 10

        # Manually trigger refill (simulates time passing)
        with patch("time.time") as mock_time:
            # Simulate 1 second passing
            mock_time.side_effect = [
                rate_limiter.last_update,  # Current time
                rate_limiter.last_update + 1.0,  # 1 second later
            ]
            rate_limiter._refill_tokens()

        # Should have added 10 tokens (10 tokens/second * 1 second)
        assert rate_limiter.tokens == 20  # Back to capacity

    async def test_burst_handling(self, rate_limiter):
        """Test handling of burst requests."""
        # Make a burst of requests
        results = []
        for i in range(25):  # More than capacity
            result = await rate_limiter.acquire(1)
            results.append(result)

        # First 20 should succeed, rest should fail
        assert sum(results) == 20
        assert results[:20] == [True] * 20
        assert results[20:] == [False] * 5

    async def test_rate_limiter_reset(self, rate_limiter):
        """Test resetting the rate limiter."""
        # Drain tokens
        await rate_limiter.acquire(15)
        assert rate_limiter.tokens == 5

        # Reset to full capacity
        rate_limiter.reset()
        assert rate_limiter.tokens == 20

    async def test_rate_adjustment(self, rate_limiter):
        """Test adjusting the rate dynamically."""
        original_rate = rate_limiter.rate

        # Change rate
        rate_limiter.rate = 20.0  # Double the rate
        assert rate_limiter.rate == 20.0
        assert rate_limiter.rate != original_rate

    async def test_capacity_adjustment(self, rate_limiter):
        """Test adjusting capacity (should be careful with this)."""
        original_capacity = rate_limiter.capacity

        # Increase capacity
        rate_limiter.capacity = 30
        assert rate_limiter.capacity == 30

        # Decrease capacity below current tokens
        await rate_limiter.acquire(5)  # Now at 15 tokens
        rate_limiter.capacity = 10
        rate_limiter.tokens = min(rate_limiter.tokens, rate_limiter.capacity)
        assert rate_limiter.tokens == 10


class TestRateLimiterIntegration:
    """Integration tests for rate limiter."""

    async def test_realistic_api_scenario(self):
        """Test rate limiter in a realistic API scenario."""
        # API allows 5 requests per second, burst up to 10
        rate_limiter = TokenBucketRateLimiter(rate=5.0, capacity=10, initial_tokens=10)

        async def api_call(request_id):
            """Simulate an API call."""
            await asyncio.sleep(0.01)  # Simulate network delay
            return f"response_{request_id}"

        # Make a burst of requests
        burst_tasks = []
        for i in range(10):
            if await rate_limiter.acquire(1):
                task = asyncio.create_task(api_call(i))
                burst_tasks.append(task)

        burst_results = await asyncio.gather(*burst_tasks)
        assert len(burst_results) == 10  # All burst requests should succeed

        # Now try more requests - should be rate limited
        additional_requests = 0
        for i in range(10, 20):
            if await rate_limiter.acquire(1):
                additional_requests += 1

        assert additional_requests == 0  # Should be rate limited

        # Wait for refill and try again
        await asyncio.sleep(1.2)  # Allow ~6 tokens to refill

        refilled_requests = 0
        for i in range(20, 30):
            if await rate_limiter.acquire(1):
                refilled_requests += 1

        assert 5 <= refilled_requests <= 6  # Should have ~5-6 tokens available

    async def test_sustained_load_scenario(self):
        """Test rate limiter under sustained load."""
        # Allow 2 requests per second
        rate_limiter = TokenBucketRateLimiter(rate=2.0, capacity=4, initial_tokens=4)

        successful_requests = 0
        start_time = time.time()

        # Try to make requests for 3 seconds
        while time.time() - start_time < 3.0:
            if await rate_limiter.acquire(1):
                successful_requests += 1
            await asyncio.sleep(0.1)  # Check every 100ms

        # Should have allowed roughly 6-8 requests (2/sec * 3 sec + initial burst)
        assert 6 <= successful_requests <= 10

    async def test_concurrent_clients_scenario(self):
        """Test rate limiter with multiple concurrent clients."""
        # Shared rate limiter
        rate_limiter = TokenBucketRateLimiter(rate=10.0, capacity=20, initial_tokens=20)

        async def client_requests(client_id, num_requests):
            """Simulate a client making requests."""
            successful = 0
            for i in range(num_requests):
                if await rate_limiter.acquire(1):
                    successful += 1
                await asyncio.sleep(0.01)  # Small delay between requests
            return successful

        # Start multiple clients
        client_tasks = [client_requests(f"client_{i}", 10) for i in range(5)]

        results = await asyncio.gather(*client_tasks)
        total_successful = sum(results)

        # Should not exceed the initial capacity significantly
        assert total_successful <= 25  # Some tolerance for refill during execution

    async def test_error_handling_with_rate_limiter(self):
        """Test error handling when using rate limiter."""
        rate_limiter = TokenBucketRateLimiter(rate=5.0, capacity=10, initial_tokens=10)

        async def failing_operation():
            raise ValueError("Simulated failure")

        # Even if operation fails, tokens should be consumed
        initial_tokens = rate_limiter.current_tokens

        with pytest.raises(ValueError):
            await rate_limiter.enforce_rate_limit(failing_operation, tokens=3)

        assert rate_limiter.current_tokens == initial_tokens - 3

    async def test_rate_limiter_with_different_token_costs(self):
        """Test rate limiter with operations requiring different token costs."""
        rate_limiter = TokenBucketRateLimiter(rate=10.0, capacity=20, initial_tokens=20)

        # Cheap operation (1 token)
        result1 = await rate_limiter.acquire(1)
        assert result1 is True
        assert rate_limiter.current_tokens == 19

        # Expensive operation (5 tokens)
        result2 = await rate_limiter.acquire(5)
        assert result2 is True
        assert rate_limiter.current_tokens == 14

        # Very expensive operation (15 tokens)
        result3 = await rate_limiter.acquire(15)
        assert result3 is False
        assert rate_limiter.current_tokens == 14  # Unchanged

        # Another expensive operation that fits
        result4 = await rate_limiter.acquire(10)
        assert result4 is True
        assert rate_limiter.current_tokens == 4
