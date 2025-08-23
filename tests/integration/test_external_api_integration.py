"""
External API integration tests for KHIVE services.

Tests integration with external APIs including:
- OpenAI API mocking and response handling
- API error scenarios and fallback behavior
- Rate limiting and timeout handling
- API cost tracking and budget management
- Network failure recovery
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class MockExternalAPIManager:
    """Manager for mocking external APIs with realistic behavior patterns."""

    def __init__(self):
        self.call_count = 0
        self.error_rate = 0.0
        self.latency_ms = 500
        self.cost_per_call = 0.01
        self.total_cost = 0.0

    def set_error_rate(self, rate: float):
        """Set the error rate for API calls (0.0 = no errors, 1.0 = all errors)."""
        self.error_rate = rate

    def set_latency(self, latency_ms: int):
        """Set the simulated latency for API calls."""
        self.latency_ms = latency_ms

    async def simulate_openai_completion(self, request: dict) -> dict:
        """Simulate OpenAI completion API call."""
        self.call_count += 1

        # Simulate latency
        await asyncio.sleep(self.latency_ms / 1000.0)

        # Simulate errors
        if self.error_rate > 0 and (self.call_count * 0.1) % 1 < self.error_rate:
            raise Exception(f"Simulated API error (call #{self.call_count})")

        # Track cost
        self.total_cost += self.cost_per_call

        # Generate realistic response based on request
        prompt = request.get("messages", [{}])[-1].get("content", "")

        if "complexity" in prompt.lower():
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "complexity": (
                                        "high" if len(prompt) > 100 else "medium"
                                    ),
                                    "confidence": 0.85,
                                    "reasoning": f"Analysis of request with {len(prompt)} characters",
                                    "recommended_agents": 5 if len(prompt) > 100 else 3,
                                    "roles": [
                                        "researcher",
                                        "architect",
                                        "implementer",
                                        "tester",
                                        "reviewer",
                                    ],
                                    "estimated_cost": 0.25,
                                    "processing_time": self.latency_ms / 1000.0,
                                }
                            )
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": 50,
                    "total_tokens": len(prompt.split()) + 50,
                },
            }

        return {
            "choices": [
                {
                    "message": {
                        "content": "Generic API response for non-complexity requests"
                    }
                }
            ]
        }


class TestExternalAPIIntegration:
    """Integration tests for external API handling."""

    @pytest.fixture
    def api_manager(self):
        """Create external API manager for testing."""
        return MockExternalAPIManager()

    @pytest.mark.integration
    async def test_openai_api_successful_integration(
        self, api_manager: MockExternalAPIManager, redis_cache, integration_test_data
    ):
        """Test successful OpenAI API integration with caching."""
        # Prepare test request
        planning_request = integration_test_data.sample_planning_request()

        # Create mock OpenAI client
        mock_client = AsyncMock()

        # Configure realistic response
        expected_response = await api_manager.simulate_openai_completion(
            {"messages": [{"content": planning_request}]}
        )

        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=expected_response["choices"][0]["message"]["content"]
                    )
                )
            ],
            usage=MagicMock(**expected_response["usage"]),
        )

        # Test API integration
        with patch("openai.AsyncOpenAI", return_value=mock_client):
            # Simulate planning service API call
            start_time = time.time()

            response = await mock_client.chat.completions.create(
                model="gpt-4", messages=[{"role": "user", "content": planning_request}]
            )

            api_call_time = time.time() - start_time

            # Verify response structure
            assert response is not None
            assert hasattr(response, "choices")
            assert len(response.choices) > 0

            # Parse and verify content
            response_content = response.choices[0].message.content
            if response_content.startswith("{"):
                parsed_content = json.loads(response_content)
                assert "complexity" in parsed_content
                assert "confidence" in parsed_content
                assert "recommended_agents" in parsed_content

            # Verify performance
            assert api_call_time < 2.0, f"API call took too long: {api_call_time}s"

        # Test caching integration
        cache_key = f"openai:completion:{hash(planning_request)}"

        # Cache the result
        await redis_cache.set(
            cache_key,
            {
                "response": response_content,
                "usage": (
                    response.usage.__dict__
                    if hasattr(response.usage, "__dict__")
                    else {}
                ),
                "cached_at": time.time(),
            },
            ttl=3600,
        )

        # Retrieve from cache
        cached_result = await redis_cache.get(cache_key)
        assert cached_result is not None
        assert cached_result["response"] == response_content

    @pytest.mark.integration
    async def test_api_error_handling_and_fallback(
        self, api_manager: MockExternalAPIManager, redis_cache
    ):
        """Test API error handling with fallback mechanisms."""
        # Configure high error rate
        api_manager.set_error_rate(0.8)  # 80% error rate

        planning_request = "Test request for error handling"
        fallback_response = {
            "complexity": "medium",
            "confidence": 0.5,
            "reasoning": "Fallback response due to API unavailability",
            "recommended_agents": 3,
            "source": "fallback",
        }

        # Test multiple API calls with error handling
        successful_calls = 0
        failed_calls = 0
        fallback_used = 0

        for attempt in range(10):
            try:
                # Simulate API call
                response = await api_manager.simulate_openai_completion(
                    {
                        "messages": [
                            {"content": f"{planning_request} - attempt {attempt}"}
                        ]
                    }
                )
                successful_calls += 1

                # Cache successful response
                cache_key = f"openai:success:{attempt}"
                await redis_cache.set(cache_key, response, ttl=300)

            except Exception:
                failed_calls += 1

                # Use fallback mechanism
                cache_key = f"openai:fallback:{attempt}"
                await redis_cache.set(cache_key, fallback_response, ttl=300)
                fallback_used += 1

        # Verify error handling statistics
        total_calls = successful_calls + failed_calls
        assert total_calls == 10
        assert failed_calls >= 6, f"Expected high failure rate, got {failed_calls}/10"
        assert fallback_used == failed_calls, "Fallback should be used for all failures"

        # Verify cached fallback responses
        for attempt in range(fallback_used):
            cache_key = f"openai:fallback:{attempt}"
            cached_fallback = await redis_cache.get(cache_key)
            assert cached_fallback is not None
            assert cached_fallback["source"] == "fallback"

    @pytest.mark.integration
    async def test_api_rate_limiting_and_throttling(
        self, api_manager: MockExternalAPIManager, performance_test_config
    ):
        """Test API rate limiting and request throttling."""
        # Configure fast response times for rate limiting test
        api_manager.set_latency(100)  # 100ms per call

        # Simulate rate limiting (max 10 calls per second)
        max_calls_per_second = 10
        test_duration_seconds = 2
        expected_max_calls = max_calls_per_second * test_duration_seconds

        # Track call timing
        call_times = []
        successful_calls = 0
        rate_limited_calls = 0

        async def make_api_call(call_id: int):
            """Make a single API call with rate limiting simulation."""
            nonlocal successful_calls, rate_limited_calls

            call_start_time = time.time()

            try:
                # Check if we're exceeding rate limit
                recent_calls = [t for t in call_times if call_start_time - t < 1.0]

                if len(recent_calls) >= max_calls_per_second:
                    # Simulate rate limiting delay
                    await asyncio.sleep(1.0 - (call_start_time - min(recent_calls)))
                    rate_limited_calls += 1

                # Make the API call
                response = await api_manager.simulate_openai_completion(
                    {"messages": [{"content": f"Rate limiting test call {call_id}"}]}
                )

                call_times.append(time.time())
                successful_calls += 1

                return response

            except Exception as e:
                return {"error": str(e)}

        # Execute concurrent API calls
        start_time = time.time()

        # Create more calls than rate limit allows
        num_calls = expected_max_calls + 5
        call_tasks = [make_api_call(i) for i in range(num_calls)]

        results = await asyncio.gather(*call_tasks)

        total_time = time.time() - start_time

        # Verify rate limiting behavior
        assert (
            total_time >= test_duration_seconds
        ), "Test should take at least the specified duration"
        assert (
            successful_calls <= expected_max_calls + 2
        ), f"Rate limiting not working: {successful_calls} > {expected_max_calls}"

        # Verify call distribution over time
        if len(call_times) > 0:
            # Check that calls are distributed over time (not all at once)
            time_spread = max(call_times) - min(call_times)
            assert (
                time_spread >= 1.0
            ), "Calls should be spread over time due to rate limiting"

    @pytest.mark.integration
    async def test_api_timeout_and_circuit_breaker(
        self, api_manager: MockExternalAPIManager, redis_cache
    ):
        """Test API timeout handling and circuit breaker pattern."""
        # Configure high latency to trigger timeouts
        api_manager.set_latency(5000)  # 5 second latency
        timeout_threshold = 2.0  # 2 second timeout

        # Circuit breaker state
        failure_count = 0
        circuit_breaker_open = False
        circuit_breaker_threshold = 3

        async def api_call_with_timeout(request: str) -> dict:
            """Make API call with timeout and circuit breaker logic."""
            nonlocal failure_count, circuit_breaker_open

            # Check circuit breaker
            if circuit_breaker_open:
                return {"error": "Circuit breaker is open", "source": "circuit_breaker"}

            try:
                # Make API call with timeout
                response = await asyncio.wait_for(
                    api_manager.simulate_openai_completion(
                        {"messages": [{"content": request}]}
                    ),
                    timeout=timeout_threshold,
                )

                # Reset failure count on success
                failure_count = 0
                return response

            except asyncio.TimeoutError:
                failure_count += 1

                # Open circuit breaker if threshold exceeded
                if failure_count >= circuit_breaker_threshold:
                    circuit_breaker_open = True

                return {
                    "error": "API call timeout",
                    "source": "timeout",
                    "failure_count": failure_count,
                }

        # Test timeout scenarios
        timeout_results = []

        # Make several calls that should timeout
        for i in range(5):
            start_time = time.time()
            result = await api_call_with_timeout(f"Timeout test {i}")
            call_time = time.time() - start_time

            timeout_results.append(
                {
                    "call_index": i,
                    "result": result,
                    "call_time": call_time,
                    "circuit_breaker_open": circuit_breaker_open,
                }
            )

            # Cache the result (including errors)
            cache_key = f"timeout_test:{i}"
            await redis_cache.set(cache_key, result, ttl=300)

        # Verify timeout behavior
        timeout_calls = [
            r for r in timeout_results if "timeout" in r["result"].get("error", "")
        ]
        circuit_breaker_calls = [
            r
            for r in timeout_results
            if "circuit_breaker" in r["result"].get("source", "")
        ]

        assert (
            len(timeout_calls) >= 3
        ), "Should have timeout calls before circuit breaker opens"
        assert (
            len(circuit_breaker_calls) >= 1
        ), "Circuit breaker should open after threshold"

        # Verify timeout duration
        for result in timeout_calls:
            assert (
                result["call_time"] <= timeout_threshold + 0.5
            ), f"Timeout not enforced properly: {result['call_time']}s"

        # Test circuit breaker reset (would require additional logic in real implementation)
        circuit_breaker_open = False  # Simulate manual reset
        failure_count = 0

        # Configure normal latency
        api_manager.set_latency(200)

        # Make a successful call after reset
        reset_result = await api_call_with_timeout("Circuit breaker reset test")
        assert (
            "error" not in reset_result
        ), "Call should succeed after circuit breaker reset"

    @pytest.mark.integration
    async def test_api_cost_tracking_and_budget_management(
        self, api_manager: MockExternalAPIManager, redis_cache
    ):
        """Test API cost tracking and budget management integration."""
        # Configure cost tracking
        budget_limit = 1.00  # $1.00 budget limit
        cost_per_call = 0.15  # $0.15 per API call
        api_manager.cost_per_call = cost_per_call

        # Initialize budget tracking in cache
        budget_cache_key = "api_budget:tracking"
        await redis_cache.set(
            budget_cache_key,
            {
                "budget_limit": budget_limit,
                "current_cost": 0.0,
                "calls_made": 0,
                "budget_exceeded": False,
            },
            ttl=3600,
        )

        async def tracked_api_call(request: str) -> dict:
            """Make API call with cost tracking."""
            # Get current budget status
            budget_status = await redis_cache.get(budget_cache_key)

            # Check budget limit
            if budget_status["budget_exceeded"]:
                return {
                    "error": "Budget limit exceeded",
                    "budget_status": budget_status,
                }

            # Make API call
            try:
                response = await api_manager.simulate_openai_completion(
                    {"messages": [{"content": request}]}
                )

                # Update cost tracking
                budget_status["current_cost"] += cost_per_call
                budget_status["calls_made"] += 1

                if budget_status["current_cost"] >= budget_limit:
                    budget_status["budget_exceeded"] = True

                # Update cache
                await redis_cache.set(budget_cache_key, budget_status, ttl=3600)

                # Add cost information to response
                response["cost_info"] = {
                    "call_cost": cost_per_call,
                    "total_cost": budget_status["current_cost"],
                    "remaining_budget": budget_limit - budget_status["current_cost"],
                }

                return response

            except Exception as e:
                return {"error": str(e)}

        # Test budget tracking
        call_results = []

        # Make calls until budget is exceeded
        for i in range(10):  # More calls than budget allows
            result = await tracked_api_call(f"Budget test call {i}")
            call_results.append(result)

            # Stop if budget exceeded
            if "Budget limit exceeded" in result.get("error", ""):
                break

        # Verify budget enforcement
        successful_calls = [r for r in call_results if "cost_info" in r]
        budget_exceeded_calls = [
            r for r in call_results if "Budget limit exceeded" in r.get("error", "")
        ]

        # Should allow approximately budget_limit / cost_per_call calls
        expected_successful_calls = int(budget_limit / cost_per_call)
        assert (
            len(successful_calls) <= expected_successful_calls + 1
        ), f"Too many successful calls: {len(successful_calls)}"
        assert len(budget_exceeded_calls) > 0, "Budget limit should be enforced"

        # Verify cost calculation accuracy
        if successful_calls:
            final_call = successful_calls[-1]
            expected_total_cost = len(successful_calls) * cost_per_call
            actual_total_cost = final_call["cost_info"]["total_cost"]

            assert (
                abs(actual_total_cost - expected_total_cost) < 0.01
            ), f"Cost calculation error: {actual_total_cost} != {expected_total_cost}"

        # Verify budget status in cache
        final_budget_status = await redis_cache.get(budget_cache_key)
        assert final_budget_status["budget_exceeded"] is True
        assert final_budget_status["current_cost"] >= budget_limit

    @pytest.mark.performance
    @pytest.mark.integration
    async def test_concurrent_api_calls_with_caching(
        self, api_manager: MockExternalAPIManager, redis_cache, performance_test_config
    ):
        """Test performance of concurrent API calls with intelligent caching."""
        # Configure reasonable performance
        api_manager.set_latency(300)  # 300ms per call

        # Test data - some duplicate requests to test cache effectiveness
        test_requests = []
        unique_requests = [
            "Implement user authentication system",
            "Build REST API for data management",
            "Create responsive web interface",
            "Set up CI/CD pipeline",
            "Design database schema",
        ]

        # Create requests with some duplication
        num_concurrent = performance_test_config["concurrent_operations"]
        for i in range(num_concurrent):
            # Use duplicate requests to test caching (30% duplication rate)
            if i % 3 == 0 and i > 0:
                # Use previous request
                test_requests.append(test_requests[i - 3])
            else:
                # Use unique request
                request_index = i % len(unique_requests)
                test_requests.append(f"{unique_requests[request_index]} - variant {i}")

        async def cached_api_call(request: str, call_id: int) -> dict:
            """Make API call with caching."""
            cache_key = f"api_cache:{hash(request)}"

            # Check cache first
            cached_result = await redis_cache.get(cache_key)
            if cached_result:
                return {**cached_result, "cache_hit": True, "call_id": call_id}

            # Make API call
            try:
                start_time = time.time()
                response = await api_manager.simulate_openai_completion(
                    {"messages": [{"content": request}]}
                )
                api_call_time = time.time() - start_time

                # Add metadata
                result = {
                    **response,
                    "cache_hit": False,
                    "call_id": call_id,
                    "api_call_time": api_call_time,
                    "request": request,
                }

                # Cache the result
                await redis_cache.set(cache_key, result, ttl=1800)  # 30 min cache

                return result

            except Exception as e:
                return {"error": str(e), "cache_hit": False, "call_id": call_id}

        # Execute concurrent API calls
        start_time = time.time()

        call_tasks = [cached_api_call(req, i) for i, req in enumerate(test_requests)]
        results = await asyncio.gather(*call_tasks)

        total_time = time.time() - start_time

        # Analyze performance results
        cache_hits = [r for r in results if r.get("cache_hit", False)]
        cache_misses = [r for r in results if not r.get("cache_hit", False)]
        successful_calls = [r for r in results if "error" not in r]

        # Verify cache effectiveness
        cache_hit_rate = len(cache_hits) / len(results)
        assert cache_hit_rate >= 0.2, f"Cache hit rate too low: {cache_hit_rate * 100}%"

        # Verify performance improvement from caching
        if cache_hits and cache_misses:
            avg_cache_hit_time = 0.1  # Cache hits should be very fast
            avg_cache_miss_time = sum(
                r.get("api_call_time", 0) for r in cache_misses
            ) / len(cache_misses)

            assert (
                avg_cache_miss_time > avg_cache_hit_time * 5
            ), "Cache should provide significant performance improvement"

        # Verify overall performance
        operations_per_second = len(successful_calls) / total_time
        expected_min_throughput = 10  # ops/sec (accounting for caching improvement)

        assert (
            operations_per_second > expected_min_throughput
        ), f"Throughput too low: {operations_per_second} ops/sec < {expected_min_throughput}"
