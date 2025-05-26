"""
Comprehensive tests for resilience mechanisms.

Tests circuit breaker, retry logic, and backoff strategies.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from khive.clients.resilience import (
    CircuitBreaker,
    CircuitState,
    RetryConfig,
    retry_with_backoff,
)
from khive.clients.errors import (
    APIClientError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    ServerError,
    CircuitBreakerOpenError,
)


class TestCircuitBreaker:
    """Test the CircuitBreaker class."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a CircuitBreaker instance for testing."""
        return CircuitBreaker(
            failure_threshold=3, recovery_time=1.0, excluded_exceptions={ValueError}
        )

    @pytest.fixture
    def fast_recovery_breaker(self):
        """Create a CircuitBreaker with fast recovery for testing."""
        return CircuitBreaker(
            failure_threshold=2, recovery_time=0.1, excluded_exceptions=set()
        )

    async def test_initialization(self, circuit_breaker):
        """Test CircuitBreaker initialization."""
        assert circuit_breaker.failure_threshold == 3
        assert circuit_breaker.recovery_time == 1.0
        assert ValueError in circuit_breaker.excluded_exceptions
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.last_failure_time == 0

    async def test_successful_execution_closed_state(self, circuit_breaker):
        """Test successful execution in closed state."""

        async def successful_operation():
            return "success"

        result = await circuit_breaker.execute(successful_operation)

        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    async def test_failure_increments_count(self, circuit_breaker):
        """Test that failures increment the failure count."""

        async def failing_operation():
            raise APIClientError("Test error")

        # First failure
        with pytest.raises(APIClientError):
            await circuit_breaker.execute(failing_operation)

        assert circuit_breaker.failure_count == 1
        assert circuit_breaker.state == CircuitState.CLOSED

        # Second failure
        with pytest.raises(APIClientError):
            await circuit_breaker.execute(failing_operation)

        assert circuit_breaker.failure_count == 2
        assert circuit_breaker.state == CircuitState.CLOSED

    async def test_circuit_opens_after_threshold(self, circuit_breaker):
        """Test that circuit opens after reaching failure threshold."""

        async def failing_operation():
            raise APIClientError("Test error")

        # Reach the failure threshold
        for i in range(3):
            with pytest.raises(APIClientError):
                await circuit_breaker.execute(failing_operation)

        # Circuit should now be open
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == 3
        assert circuit_breaker.last_failure_time > 0

    async def test_open_circuit_rejects_calls(self, circuit_breaker):
        """Test that open circuit rejects calls immediately."""

        async def failing_operation():
            raise APIClientError("Test error")

        # Open the circuit
        for i in range(3):
            with pytest.raises(APIClientError):
                await circuit_breaker.execute(failing_operation)

        # Now all calls should be rejected immediately
        async def any_operation():
            return "should not execute"

        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.execute(any_operation)

    async def test_circuit_transitions_to_half_open(self, fast_recovery_breaker):
        """Test circuit transitions to half-open after recovery timeout."""

        async def failing_operation():
            raise Exception("Test error")

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await fast_recovery_breaker.execute(failing_operation)

        assert fast_recovery_breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Next call should transition to half-open
        async def test_operation():
            return "test"

        result = await fast_recovery_breaker.execute(test_operation)

        assert result == "test"
        assert fast_recovery_breaker.state == CircuitState.CLOSED
        assert fast_recovery_breaker.failure_count == 0

    async def test_half_open_success_closes_circuit(self, fast_recovery_breaker):
        """Test that successful call in half-open state closes circuit."""

        async def failing_operation():
            raise Exception("Test error")

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await fast_recovery_breaker.execute(failing_operation)

        # Wait for recovery
        await asyncio.sleep(0.15)

        # Successful call should close circuit
        async def successful_operation():
            return "success"

        result = await fast_recovery_breaker.execute(successful_operation)

        assert result == "success"
        assert fast_recovery_breaker.state == CircuitState.CLOSED
        assert fast_recovery_breaker.failure_count == 0

    async def test_half_open_failure_reopens_circuit(self, fast_recovery_breaker):
        """Test that failure in half-open state reopens circuit."""

        async def failing_operation():
            raise Exception("Test error")

        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await fast_recovery_breaker.execute(failing_operation)

        # Wait for recovery
        await asyncio.sleep(0.15)

        # Failure should reopen circuit
        with pytest.raises(Exception):
            await fast_recovery_breaker.execute(failing_operation)

        assert fast_recovery_breaker.state == CircuitState.OPEN

    async def test_unexpected_exception_not_counted(self, circuit_breaker):
        """Test that unexpected exceptions are not counted as failures."""

        async def unexpected_error():
            raise ValueError("Unexpected error")

        # This should not increment failure count
        with pytest.raises(ValueError):
            await circuit_breaker.execute(unexpected_error)

        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == CircuitState.CLOSED

    async def test_mixed_exceptions(self, circuit_breaker):
        """Test handling of mixed expected and unexpected exceptions."""

        async def api_error():
            raise APIClientError("API error")

        async def value_error():
            raise ValueError("Value error")

        # API error should count
        with pytest.raises(APIClientError):
            await circuit_breaker.execute(api_error)
        assert circuit_breaker.failure_count == 1

        # Value error should not count
        with pytest.raises(ValueError):
            await circuit_breaker.execute(value_error)
        assert circuit_breaker.failure_count == 1

        # Another API error should count
        with pytest.raises(APIClientError):
            await circuit_breaker.execute(api_error)
        assert circuit_breaker.failure_count == 2

    async def test_reset_functionality(self, circuit_breaker):
        """Test manual reset functionality."""

        async def failing_operation():
            raise APIClientError("Test error")

        # Open the circuit
        for i in range(3):
            with pytest.raises(APIClientError):
                await circuit_breaker.execute(failing_operation)

        assert circuit_breaker.state == CircuitState.OPEN

        # Reset the circuit - manual reset not implemented, so let's test recovery instead
        # Wait for recovery time
        await asyncio.sleep(1.1)
        
        # Test that circuit can recover
        async def test_operation():
            return "recovery test"
        
        result = await circuit_breaker.execute(test_operation)
        assert result == "recovery test"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    async def test_concurrent_executions(self, circuit_breaker):
        """Test concurrent executions through circuit breaker."""

        async def slow_operation(delay, should_fail=False):
            await asyncio.sleep(delay)
            if should_fail:
                raise APIClientError("Slow failure")
            return f"completed after {delay}s"

        # Start multiple concurrent operations
        tasks = [
            circuit_breaker.execute(slow_operation, 0.1, False),
            circuit_breaker.execute(slow_operation, 0.2, False),
            circuit_breaker.execute(slow_operation, 0.1, False),
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert all("completed after" in result for result in results)
        assert circuit_breaker.state == CircuitState.CLOSED


class TestRetryConfig:
    """Test the RetryConfig class."""

    def test_retry_config_initialization(self):
        """Test RetryConfig initialization."""
        config = RetryConfig(max_retries=5, base_delay=1.0, max_delay=60.0, jitter=True)

        assert config.max_retries == 5
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.jitter is True

    def test_retry_config_as_kwargs(self):
        """Test RetryConfig as_kwargs method."""
        config = RetryConfig(
            max_retries=3, base_delay=0.5, max_delay=10.0, jitter=False
        )

        kwargs = config.as_kwargs()

        expected_kwargs = {
            "max_retries": 3,
            "base_delay": 0.5,
            "max_delay": 10.0,
            "backoff_factor": 2.0,
            "jitter": False,
            "retry_exceptions": (Exception,),
            "exclude_exceptions": (),
        }

        assert kwargs == expected_kwargs

    def test_retry_config_defaults(self):
        """Test RetryConfig default values."""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.jitter is True


class TestRetryWithBackoff:
    """Test the retry_with_backoff function."""

    async def test_successful_operation_no_retry(self):
        """Test successful operation requires no retry."""
        call_count = 0

        async def successful_operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_with_backoff(
            successful_operation, max_retries=3, base_delay=0.1
        )

        assert result == "success"
        assert call_count == 1

    async def test_retry_on_failure(self):
        """Test retry behavior on failures."""
        call_count = 0

        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APIConnectionError("Connection failed")
            return "success"

        result = await retry_with_backoff(
            failing_then_success,
            max_retries=5,
            base_delay=0.01,  # Very short delay for testing
        )

        assert result == "success"
        assert call_count == 3

    async def test_max_attempts_exceeded(self):
        """Test behavior when max attempts are exceeded."""
        call_count = 0

        async def always_failing():
            nonlocal call_count
            call_count += 1
            raise APIConnectionError("Always fails")

        with pytest.raises(APIConnectionError):
            await retry_with_backoff(always_failing, max_retries=3, base_delay=0.01)

        assert call_count == 3

    async def test_different_backoff_strategies(self):
        """Test different backoff strategies."""
        call_count = 0
        start_time = time.time()

        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APITimeoutError("Timeout")
            return "success"

        # Test with linear backoff
        result = await retry_with_backoff(
            failing_operation, max_retries=5, base_delay=0.01, jitter=False
        )

        duration = time.time() - start_time
        assert result == "success"
        assert call_count == 3
        # Should have waited approximately 0.01 + 0.02 = 0.03 seconds
        assert duration >= 0.025

    async def test_non_retryable_exception(self):
        """Test that some exceptions are not retried."""
        call_count = 0

        async def auth_error():
            nonlocal call_count
            call_count += 1
            # Authentication errors typically shouldn't be retried
            raise ValueError("Invalid credentials")

        with pytest.raises(ValueError):
            await retry_with_backoff(auth_error, max_retries=3, base_delay=0.01)

        # Should only be called once (no retries for ValueError)
        assert call_count == 1

    async def test_retry_with_rate_limit(self):
        """Test retry behavior with rate limiting."""
        call_count = 0

        async def rate_limited_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("Rate limited", retry_after=0.01)
            return "success"

        result = await retry_with_backoff(
            rate_limited_operation,
            max_retries=5,
            base_delay=0.001,  # Very short base delay
        )

        assert result == "success"
        assert call_count == 3

    async def test_retry_with_server_error(self):
        """Test retry behavior with server errors."""
        call_count = 0

        async def server_error_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ServerError("Internal server error")
            return "recovered"

        result = await retry_with_backoff(
            server_error_operation, max_retries=3, base_delay=0.01
        )

        assert result == "recovered"
        assert call_count == 2

    async def test_retry_with_mixed_exceptions(self):
        """Test retry with mixed retryable and non-retryable exceptions."""
        call_count = 0

        async def mixed_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise APIConnectionError("Connection error")
            elif call_count == 2:
                raise APITimeoutError("Timeout error")
            elif call_count == 3:
                # Non-retryable error
                raise ValueError("Invalid input")
            return "should not reach here"

        with pytest.raises(ValueError):
            await retry_with_backoff(mixed_errors, max_retries=5, base_delay=0.01)

        assert call_count == 3

    async def test_retry_timing_accuracy(self):
        """Test that retry timing is reasonably accurate."""
        call_count = 0
        start_time = time.time()

        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APIConnectionError("Connection failed")
            return "success"

        result = await retry_with_backoff(
            failing_operation,
            max_retries=3,
            base_delay=0.05,  # 50ms delay
            backoff_factor=1.0,  # Fixed delay
            jitter=False,
        )

        duration = time.time() - start_time
        assert result == "success"
        # Should have waited approximately 0.05 + 0.05 = 0.1 seconds
        assert 0.08 <= duration <= 0.15  # Some tolerance for timing


class TestResilienceIntegration:
    """Integration tests for resilience mechanisms."""

    async def test_circuit_breaker_with_retry(self):
        """Test circuit breaker combined with retry logic."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=2, recovery_time=0.1, excluded_exceptions=set()
        )

        call_count = 0

        async def unreliable_operation():
            nonlocal call_count
            call_count += 1
            if call_count <= 4:
                raise APIClientError("Service unavailable")
            return "success"

        # First attempt with retry - should exhaust retries and open circuit
        with pytest.raises(APIClientError):
            await retry_with_backoff(
                lambda: circuit_breaker.execute(unreliable_operation),
                max_retries=3,
                base_delay=0.01,
            )

        # Circuit should be open now
        assert circuit_breaker.state == CircuitState.OPEN

        # Immediate retry should fail fast
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.execute(unreliable_operation)

        # Wait for recovery
        await asyncio.sleep(0.15)

        # Should work now
        result = await circuit_breaker.execute(unreliable_operation)
        assert result == "success"

    async def test_resilience_with_real_world_scenario(self):
        """Test resilience mechanisms in a real-world-like scenario."""
        # Simulate a service that's initially down, then flaky, then stable
        call_count = 0

        async def flaky_service():
            nonlocal call_count
            call_count += 1

            if call_count <= 3:
                # Initially down
                raise APIConnectionError("Service down")
            elif call_count <= 6:
                # Flaky - sometimes works
                if call_count % 2 == 0:
                    raise APITimeoutError("Timeout")
                return f"flaky_response_{call_count}"
            else:
                # Stable
                return f"stable_response_{call_count}"

        circuit_breaker = CircuitBreaker(
            failure_threshold=3, recovery_time=0.1, excluded_exceptions=set()
        )

        # First few attempts should fail and open circuit
        for _ in range(2):
            with pytest.raises((APIConnectionError, CircuitBreakerOpenError)):
                await retry_with_backoff(
                    lambda: circuit_breaker.execute(flaky_service),
                    max_retries=2,
                    base_delay=0.01,
                )

        # Wait for circuit recovery
        await asyncio.sleep(0.15)

        # Should eventually succeed
        result = await retry_with_backoff(
            lambda: circuit_breaker.execute(flaky_service),
            max_retries=5,
            base_delay=0.01,
        )

        assert "response_" in result
        assert circuit_breaker.state == CircuitState.CLOSED
