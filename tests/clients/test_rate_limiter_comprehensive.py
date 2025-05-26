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
            max_tokens=20,  # 20 token capacity
            initial_tokens=20,  # Start with full bucket
        )

    @pytest.fixture
    def slow_rate_limiter(self):
        """Create a slow rate limiter for testing."""
        return TokenBucketRateLimiter(
            rate=2.0,  # 2 tokens per second
            max_tokens=5,  # 5 token capacity
            initial_tokens=5,  # Start with full bucket
        )

    @pytest.fixture
    def fast_rate_limiter(self):
        """Create a fast rate limiter for testing."""
        return TokenBucketRateLimiter(
            rate=100.0,  # 100 tokens per second
            max_tokens=200,  # 200 token capacity
            initial_tokens=200,  # Start with full bucket
        )

    def test_initialization(self, rate_limiter):
        """Test TokenBucketRateLimiter initialization."""
        assert rate_limiter.rate == 10.0
        assert rate_limiter.max_tokens == 20
        assert rate_limiter.tokens == 20
        assert rate_limiter.last_refill is not None

    def test_initialization_with_defaults(self):
        """Test initialization with default parameters."""
        limiter = TokenBucketRateLimiter(rate=1.0)

        assert limiter.rate == 1.0
        assert limiter.max_tokens == 1.0  # defaults to rate
        assert limiter.tokens == 1.0

    def test_initialization_custom_parameters(self):
        """Test initialization with custom parameters."""
        limiter = TokenBucketRateLimiter(
            rate=5.0,
            period=2.0,
            max_tokens=10.0,
            initial_tokens=8.0
        )
        
        assert limiter.rate == 5.0
        assert limiter.period == 2.0
        assert limiter.max_tokens == 10.0
        assert limiter.tokens == 8.0

    async def test_acquire_single_token_success(self, rate_limiter):
        """Test acquiring a single token successfully."""
        wait_time = await rate_limiter.acquire(1)
        assert wait_time == 0.0  # Should be immediate
        assert rate_limiter.tokens == 19

    async def test_acquire_multiple_tokens_success(self, rate_limiter):
        """Test acquiring multiple tokens successfully."""
        wait_time = await rate_limiter.acquire(5)
        assert wait_time == 0.0  # Should be immediate
        assert rate_limiter.tokens == 15

    async def test_acquire_all_tokens(self, rate_limiter):
        """Test acquiring all available tokens."""
        wait_time = await rate_limiter.acquire(20)
        assert wait_time == 0.0  # Should be immediate
        assert rate_limiter.tokens == 0

    async def test_acquire_more_than_available_tokens(self, rate_limiter):
        """Test acquiring more tokens than available."""
        # First, drain most tokens
        await rate_limiter.acquire(15)
        assert rate_limiter.tokens == 5

        # Try to acquire more than available - should return wait time
        wait_time = await rate_limiter.acquire(10)
        assert wait_time > 0  # Should need to wait
        # Note: tokens aren't consumed until after wait

    async def test_acquire_zero_tokens(self, rate_limiter):
        """Test acquiring zero tokens."""
        initial_tokens = rate_limiter.tokens
        wait_time = await rate_limiter.acquire(0)
        assert wait_time == 0.0
        assert rate_limiter.tokens == initial_tokens

    async def test_acquire_with_wait(self, slow_rate_limiter):
        """Test acquiring tokens when wait is required."""
        # Drain all tokens
        await slow_rate_limiter.acquire(5)
        assert slow_rate_limiter.tokens == 0
        
        # Request more tokens - should return wait time
        wait_time = await slow_rate_limiter.acquire(1)
        assert wait_time > 0  # Should need to wait for refill
async def test_token_refill_over_time(self, slow_rate_limiter):
    """Test that tokens are refilled over time."""
    # Drain all tokens
    await slow_rate_limiter.acquire(5)
    assert slow_rate_limiter.tokens == 0

    # Wait for some refill (2 tokens per second, so 0.6 seconds should give ~1 token)
    await asyncio.sleep(0.6)

    # Should be able to acquire at least 1 token with minimal wait
    wait_time = await slow_rate_limiter.acquire(1)
    assert wait_time < 0.5  # Should be available soon

async def test_token_refill_does_not_exceed_capacity(self, slow_rate_limiter):
    """Test that token refill doesn't exceed capacity."""
    # Start with some tokens
    await slow_rate_limiter.acquire(2)
    assert slow_rate_limiter.tokens == 3

    # Wait longer than needed to fill to capacity
    await asyncio.sleep(2.0)  # Should add 4 tokens, but max_tokens is 5

    # Check that we don't exceed capacity by trying to acquire
    # Check that we don't exceed capacity by trying to acquire
    await slow_rate_limiter._refill()
    assert slow_rate_limiter.tokens <= slow_rate_limiter.max_tokens

async def test_concurrent_token_acquisition(self, rate_limiter):
    """Test concurrent token acquisition."""

    async def acquire_tokens(count):
        wait_time = await rate_limiter.acquire(count)
        return wait_time == 0.0  # True if immediate, False if needs wait

    # Start multiple concurrent acquisitions
    tasks = [
        acquire_tokens(3),
        acquire_tokens(4),
        acquire_tokens(5),
        acquire_tokens(6),
    ]

    results = await asyncio.gather(*tasks)

    # Some should succeed immediately, some might need to wait
    immediate_acquisitions = sum(1 for result in results if result)
    assert immediate_acquisitions >= 1  # At least one should succeed immediately

async def test_execute_with_rate_limiting(self, rate_limiter):
    """Test execute method with rate limiting."""
    
    async def test_operation(value):
        return f"result_{value}"

    # Test successful execution
    result = await rate_limiter.execute(test_operation, "test")
    assert result == "result_test"
    assert rate_limiter.tokens == 19  # Should consume 1 token by default

async def test_execute_with_custom_tokens(self, rate_limiter):
    """Test execute method with custom token count."""
    
    async def test_operation():
        return "success"

    # Test execution with custom token cost
    result = await rate_limiter.execute(test_operation, tokens=5)
    assert result == "success"
    assert rate_limiter.tokens == 15  # Should consume 5 tokens

async def test_execute_with_operation_exception(self, rate_limiter):
    """Test execute when operation raises exception."""

    async def failing_operation():
        raise ValueError("Operation failed")

    # Tokens should still be consumed even if operation fails
    with pytest.raises(ValueError):
        await rate_limiter.execute(failing_operation, tokens=5)

    assert rate_limiter.tokens == 15

    async def test_tokens_property(self, rate_limiter):
        """Test the tokens property."""
        assert rate_limiter.tokens == 20

        await rate_limiter.acquire(5)
        assert rate_limiter.tokens == 15

    async def test_refill_tokens_manual(self, rate_limiter):
        """Test manual token refill."""
        # Drain some tokens
        await rate_limiter.acquire(10)
        assert rate_limiter.tokens == 10

        # Manually trigger refill (simulates time passing)
        with patch("time.monotonic") as mock_time:
            # Simulate 1 second passing
            mock_time.side_effect = [
                rate_limiter.last_refill,  # Current time
                rate_limiter.last_refill + 1.0,  # 1 second later
            ]
            await rate_limiter._refill()

        # Should have added 10 tokens (10 tokens/second * 1 second)
        assert rate_limiter.tokens == 20  # Back to max_tokens

    async def test_burst_handling(self, rate_limiter):
        """Test handling of burst requests."""
        # Make a burst of requests
        wait_times = []
        for i in range(25):  # More than max_tokens
            wait_time = await rate_limiter.acquire(1)
            wait_times.append(wait_time)

        # First 20 should be immediate (wait_time == 0), rest should require waiting
        immediate_count = sum(1 for wt in wait_times if wt == 0.0)
        assert immediate_count == 20

    async def test_rate_adjustment(self, rate_limiter):
        """Test adjusting the rate dynamically."""
        original_rate = rate_limiter.rate

        # Change rate
        rate_limiter.rate = 20.0  # Double the rate
        assert rate_limiter.rate == 20.0
        assert rate_limiter.rate != original_rate

    async def test_max_tokens_adjustment(self, rate_limiter):
        """Test adjusting max_tokens."""
        original_max_tokens = rate_limiter.max_tokens

        # Increase max_tokens
        rate_limiter.max_tokens = 30
        assert rate_limiter.max_tokens == 30

        # Decrease max_tokens below current tokens
        await rate_limiter.acquire(5)  # Now at 15 tokens
        rate_limiter.max_tokens = 10
        rate_limiter.tokens = min(rate_limiter.tokens, rate_limiter.max_tokens)
        assert rate_limiter.tokens == 10


class TestRateLimiterIntegration:
    """Integration tests for rate limiter."""

    async def test_realistic_api_scenario(self):
        """Test rate limiter in a realistic API scenario."""
        # API allows 5 requests per second, burst up to 10
        rate_limiter = TokenBucketRateLimiter(rate=5.0, max_tokens=10, initial_tokens=10)

        async def api_call(request_id):
            """Simulate an API call."""
            await asyncio.sleep(0.01)  # Simulate network delay
            return f"response_{request_id}"

        # Make a burst of requests using execute
        burst_results = []
        for i in range(10):
            try:
                result = await rate_limiter.execute(api_call, i)
                burst_results.append(result)
            except Exception:
                break  # Stop if rate limited

        assert len(burst_results) == 10  # All burst requests should succeed

        # Now try more requests - should need to wait
        additional_requests = 0
        for i in range(10, 15):
            wait_time = await rate_limiter.acquire(1)
            if wait_time == 0.0:  # Only count immediate acquisitions
                additional_requests += 1

        assert additional_requests == 0  # Should be rate limited

        # Wait for refill and try again
        await asyncio.sleep(1.2)  # Allow tokens to refill

        refilled_requests = 0
        for i in range(15, 25):
            wait_time = await rate_limiter.acquire(1)
            if wait_time == 0.0:  # Only count immediate acquisitions
                refilled_requests += 1

        assert refilled_requests >= 5  # Should have some tokens available

    async def test_sustained_load_scenario(self):
        """Test rate limiter under sustained load."""
        # Allow 2 requests per second
        rate_limiter = TokenBucketRateLimiter(rate=2.0, max_tokens=4, initial_tokens=4)

        successful_requests = 0
        start_time = time.time()

        # Try to make requests for 3 seconds
        while time.time() - start_time < 3.0:
            wait_time = await rate_limiter.acquire(1)
            if wait_time == 0.0:  # Only count immediate acquisitions
                successful_requests += 1
            await asyncio.sleep(0.1)  # Check every 100ms

        # Should have allowed roughly 4-8 requests (initial burst + some refill)
        assert 4 <= successful_requests <= 10

    async def test_concurrent_clients_scenario(self):
        """Test rate limiter with multiple concurrent clients."""
        # Shared rate limiter
        rate_limiter = TokenBucketRateLimiter(rate=10.0, max_tokens=20, initial_tokens=20)

        async def client_requests(client_id, num_requests):
            """Simulate a client making requests."""
            successful = 0
            for i in range(num_requests):
                wait_time = await rate_limiter.acquire(1)
                if wait_time == 0.0:  # Only count immediate acquisitions
                    successful += 1
                await asyncio.sleep(0.01)  # Small delay between requests
            return successful

        # Start multiple clients
        client_tasks = [client_requests(f"client_{i}", 10) for i in range(5)]

        results = await asyncio.gather(*client_tasks)
        total_successful = sum(results)

        # Should not exceed the initial max_tokens significantly
        assert total_successful <= 25  # Some tolerance for refill during execution

    async def test_error_handling_with_rate_limiter(self):
        """Test error handling when using rate limiter."""
        rate_limiter = TokenBucketRateLimiter(rate=5.0, max_tokens=10, initial_tokens=10)

        async def failing_operation():
            raise ValueError("Simulated failure")

        # Even if operation fails, tokens should be consumed
        initial_tokens = rate_limiter.tokens

        with pytest.raises(ValueError):
            await rate_limiter.execute(failing_operation, tokens=3)

        assert rate_limiter.tokens == initial_tokens - 3

    async def test_rate_limiter_with_different_token_costs(self):
        """Test rate limiter with operations requiring different token costs."""
        rate_limiter = TokenBucketRateLimiter(rate=10.0, max_tokens=20, initial_tokens=20)

        # Cheap operation (1 token)
        wait_time1 = await rate_limiter.acquire(1)
        assert wait_time1 == 0.0
        assert rate_limiter.tokens == 19

        # Expensive operation (5 tokens)
        wait_time2 = await rate_limiter.acquire(5)
        assert wait_time2 == 0.0
        assert rate_limiter.tokens == 14

        # Very expensive operation (15 tokens) - should need to wait
        wait_time3 = await rate_limiter.acquire(15)
        assert wait_time3 > 0  # Should need to wait
        # Note: tokens aren't consumed until after wait

        # Another operation that fits
        wait_time4 = await rate_limiter.acquire(10)
        assert wait_time4 == 0.0
        assert rate_limiter.tokens == 4
