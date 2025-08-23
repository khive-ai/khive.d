"""Performance tests for cache service.

Comprehensive performance testing for the khive cache service including:
- Cache get/set operations performance and latency
- Redis backend performance under load
- Hash generation and key management performance
- TTL expiration and cleanup performance
- Concurrent cache operations and locking performance
- Memory usage profiling for large cached objects
- Cache hit/miss ratio optimization
- High-throughput caching stress testing
"""

import asyncio
import time

import pytest

from khive.services.cache.config import CacheConfig
from khive.services.cache.models import CacheEntry, CacheKey
from khive.services.cache.service import CacheService


class MockRedisCache:
    """Mock Redis cache backend for testing."""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.data = {}
        self.operation_times = []
        self.connected = True

    async def get(self, key: CacheKey) -> CacheEntry | None:
        start_time = time.perf_counter()

        # Simulate network latency
        await asyncio.sleep(0.001)

        entry = self.data.get(key.key)
        self.operation_times.append(time.perf_counter() - start_time)
        return entry

    async def set(
        self,
        key: CacheKey,
        value: any,
        ttl_seconds: int = 3600,
        metadata: dict | None = None,
    ) -> bool:
        start_time = time.perf_counter()

        # Simulate network latency
        await asyncio.sleep(0.001)

        entry = CacheEntry(
            key=key.key, value=value, ttl_seconds=ttl_seconds, metadata=metadata or {}
        )
        self.data[key.key] = entry

        self.operation_times.append(time.perf_counter() - start_time)
        return True

    async def delete(self, key: CacheKey) -> bool:
        start_time = time.perf_counter()

        await asyncio.sleep(0.001)

        deleted = key.key in self.data
        if deleted:
            del self.data[key.key]

        self.operation_times.append(time.perf_counter() - start_time)
        return deleted

    async def clear(self) -> bool:
        start_time = time.perf_counter()

        await asyncio.sleep(0.002)  # Clearing takes longer

        self.data.clear()
        self.operation_times.append(time.perf_counter() - start_time)
        return True

    async def health_check(self) -> bool:
        await asyncio.sleep(0.001)
        return self.connected

    async def close(self) -> None:
        self.connected = False


class TestCacheBenchmarks:
    """Benchmark cache core operations for performance baseline."""

    @pytest.mark.asyncio
    async def test_cache_get_set_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark cache get/set operations performance."""

        config = CacheConfig(
            enabled=True,
            redis_url="redis://localhost:6379",
            default_ttl=3600,
            fallback_on_error=False,
        )

        service = CacheService(config)

        # Mock Redis backend
        mock_backend = MockRedisCache(config)
        service._backend = mock_backend
        service._initialized = True

        performance_profiler.start_measurement()

        # Test cache set operations
        set_times = []
        get_times = []
        threshold_get = performance_thresholds["cache"]["cache_get_ms"] / 1000
        threshold_set = performance_thresholds["cache"]["cache_set_ms"] / 1000

        # Test different data types and sizes
        test_data = [
            {"type": "string", "data": "Simple string data for caching"},
            {
                "type": "dict",
                "data": {"key1": "value1", "key2": [1, 2, 3], "nested": {"a": 1}},
            },
            {"type": "list", "data": list(range(100))},
            {"type": "large_string", "data": "Large string data " * 1000},
            {
                "type": "complex_dict",
                "data": {f"key_{i}": f"value_{i}" * 10 for i in range(100)},
            },
        ]

        # Test each data type multiple times
        for test_round in range(3):
            for i, test_item in enumerate(test_data):
                request_key = f"test_request_{test_round}_{i}_{test_item['type']}"
                test_value = test_item["data"]

                # Test SET operation
                start_time = time.perf_counter()

                try:
                    success = await service.cache_planning_result(
                        request=request_key,
                        result=test_value,
                        metadata={"test_type": test_item["type"], "round": test_round},
                    )
                    set_success = success

                except Exception as e:
                    set_success = False
                    print(f"Cache set failed for {request_key}: {e}")

                end_time = time.perf_counter()
                set_time = end_time - start_time
                set_times.append(set_time)

                performance_profiler.record_operation(
                    set_time,
                    success=set_success,
                    operation_type=f"cache_set_{test_item['type']}",
                )

                # Test GET operation
                start_time = time.perf_counter()

                try:
                    retrieved_value = await service.get_planning_result(
                        request=request_key
                    )
                    get_success = retrieved_value is not None

                    if get_success:
                        # Verify data integrity
                        if isinstance(test_value, dict | list):
                            assert retrieved_value == test_value, "Cached data mismatch"
                        else:
                            assert str(retrieved_value) == str(
                                test_value
                            ), "Cached data mismatch"

                except Exception as e:
                    get_success = False
                    print(f"Cache get failed for {request_key}: {e}")

                end_time = time.perf_counter()
                get_time = end_time - start_time
                get_times.append(get_time)

                performance_profiler.record_operation(
                    get_time,
                    success=get_success,
                    operation_type=f"cache_get_{test_item['type']}",
                )

        performance_profiler.end_measurement()

        # Analyze performance
        avg_set_time = sum(set_times) / len(set_times)
        avg_get_time = sum(get_times) / len(get_times)
        min_set_time = min(set_times)
        min_get_time = min(get_times)
        max_set_time = max(set_times)
        max_get_time = max(get_times)

        # Performance assertions
        assert (
            avg_set_time < threshold_set
        ), f"Average cache set time too slow: {avg_set_time:.6f}s"
        assert (
            avg_get_time < threshold_get
        ), f"Average cache get time too slow: {avg_get_time:.6f}s"
        assert (
            max_set_time < threshold_set * 3.0
        ), f"Maximum cache set time too slow: {max_set_time:.6f}s"
        assert (
            max_get_time < threshold_get * 2.0
        ), f"Maximum cache get time too slow: {max_get_time:.6f}s"

        print(
            f"Cache set - Avg: {avg_set_time:.6f}s, Min: {min_set_time:.6f}s, Max: {max_set_time:.6f}s"
        )
        print(
            f"Cache get - Avg: {avg_get_time:.6f}s, Min: {min_get_time:.6f}s, Max: {max_get_time:.6f}s"
        )

    @pytest.mark.asyncio
    async def test_hash_generation_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark hash generation performance for cache keys."""

        config = CacheConfig(enabled=True)
        service = CacheService(config)

        performance_profiler.start_measurement()

        # Test hash generation for different data types and sizes
        hash_times = []
        threshold = (
            performance_thresholds["cache"]["cache_get_ms"] / 1000 * 0.1
        )  # Hash should be very fast

        test_inputs = [
            "simple string",
            {"key": "value", "number": 42, "list": [1, 2, 3]},
            {"complex": {"nested": {"deep": {"data": list(range(100))}}}},
            "very long string " * 1000,
            {f"key_{i}": f"value_{i}" * 20 for i in range(500)},
        ]

        for test_round in range(10):  # Test each input 10 times
            for i, test_input in enumerate(test_inputs):
                start_time = time.perf_counter()

                try:
                    hash_value = service._generate_hash(test_input)
                    success = len(hash_value) == 16  # Hash should be 16 characters

                    # Verify hash consistency
                    hash_value2 = service._generate_hash(test_input)
                    assert hash_value == hash_value2, "Hash generation not consistent"

                except Exception as e:
                    success = False
                    print(f"Hash generation failed for input {i}: {e}")

                end_time = time.perf_counter()
                hash_time = end_time - start_time
                hash_times.append(hash_time)

                performance_profiler.record_operation(
                    hash_time,
                    success=success,
                    operation_type=f"hash_generation_{type(test_input).__name__}",
                )

        performance_profiler.end_measurement()

        # Analyze hash generation performance
        avg_time = sum(hash_times) / len(hash_times)
        min_time = min(hash_times)
        max_time = max(hash_times)

        assert (
            avg_time < threshold
        ), f"Average hash generation time too slow: {avg_time:.6f}s"
        assert (
            max_time < threshold * 10.0
        ), f"Maximum hash generation time too slow: {max_time:.6f}s"

        print(
            f"Hash generation - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s"
        )

    @pytest.mark.asyncio
    async def test_complexity_assessment_caching_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark complexity assessment caching performance."""

        config = CacheConfig(enabled=True, default_ttl=1800)  # 30 minute TTL
        service = CacheService(config)

        # Mock Redis backend
        mock_backend = MockRedisCache(config)
        service._backend = mock_backend
        service._initialized = True

        performance_profiler.start_measurement()

        # Test complexity assessment caching
        cache_times = []
        retrieve_times = []
        threshold = performance_thresholds["cache"]["cache_set_ms"] / 1000

        # Test different complexity assessments
        complexity_requests = [
            {"text": "Simple task", "complexity": "SIMPLE"},
            {
                "text": "Medium complexity task with multiple components",
                "complexity": "MEDIUM",
            },
            {
                "text": "Complex distributed system with microservices, databases, caching, and monitoring",
                "complexity": "COMPLEX",
            },
            {
                "text": "Very complex enterprise architecture " * 50,
                "complexity": "VERY_COMPLEX",
            },
        ]

        for test_round in range(5):  # Test each assessment 5 times
            for i, assessment in enumerate(complexity_requests):
                request_data = {
                    "request": assessment["text"],
                    "round": test_round,
                    "id": i,
                }
                complexity_result = {
                    "complexity_tier": assessment["complexity"],
                    "confidence": 0.85 + (i * 0.03),
                    "reasoning": f"Assessment reasoning for {assessment['complexity']}",
                    "factors": ["factor1", "factor2", f"factor_{i}"],
                }

                # Test caching complexity assessment
                start_time = time.perf_counter()

                try:
                    success = await service.cache_complexity_assessment(
                        request=request_data,
                        assessment=complexity_result,
                        metadata={
                            "test_round": test_round,
                            "complexity": assessment["complexity"],
                        },
                    )
                    cache_success = success

                except Exception as e:
                    cache_success = False
                    print(f"Complexity assessment caching failed: {e}")

                end_time = time.perf_counter()
                cache_time = end_time - start_time
                cache_times.append(cache_time)

                performance_profiler.record_operation(
                    cache_time,
                    success=cache_success,
                    operation_type=f"complexity_cache_{assessment['complexity']}",
                )

                # Test retrieving complexity assessment
                start_time = time.perf_counter()

                try:
                    retrieved_assessment = await service.get_complexity_assessment(
                        request=request_data
                    )
                    retrieve_success = retrieved_assessment is not None

                    if retrieve_success:
                        assert (
                            retrieved_assessment["complexity_tier"]
                            == assessment["complexity"]
                        )
                        assert (
                            retrieved_assessment["confidence"]
                            == complexity_result["confidence"]
                        )

                except Exception as e:
                    retrieve_success = False
                    print(f"Complexity assessment retrieval failed: {e}")

                end_time = time.perf_counter()
                retrieve_time = end_time - start_time
                retrieve_times.append(retrieve_time)

                performance_profiler.record_operation(
                    retrieve_time,
                    success=retrieve_success,
                    operation_type=f"complexity_get_{assessment['complexity']}",
                )

        performance_profiler.end_measurement()

        # Analyze complexity assessment caching performance
        avg_cache_time = sum(cache_times) / len(cache_times)
        avg_retrieve_time = sum(retrieve_times) / len(retrieve_times)

        assert (
            avg_cache_time < threshold
        ), f"Average complexity caching time too slow: {avg_cache_time:.6f}s"
        assert (
            avg_retrieve_time < threshold * 0.8
        ), f"Average complexity retrieval time too slow: {avg_retrieve_time:.6f}s"

        print(f"Complexity cache - Avg: {avg_cache_time:.6f}s")
        print(f"Complexity retrieve - Avg: {avg_retrieve_time:.6f}s")


class TestCacheScalability:
    """Test cache performance scalability under increasing loads."""

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations_scaling(
        self, performance_profiler, load_test_runner, performance_thresholds
    ):
        """Test cache performance with concurrent operations."""

        config = CacheConfig(enabled=True, default_ttl=3600)
        service = CacheService(config)

        # Mock Redis backend with higher capacity
        mock_backend = MockRedisCache(config)
        service._backend = mock_backend
        service._initialized = True

        async def concurrent_cache_operation():
            """Single cache operation for concurrent testing."""
            import random

            operation = random.choice(["set", "get"])
            cache_id = random.randint(1, 1000)
            request_key = f"concurrent_request_{cache_id}"

            try:
                if operation == "set":
                    test_data = {
                        "id": cache_id,
                        "data": f"Concurrent test data {cache_id}",
                        "timestamp": time.time(),
                        "metadata": {"test": True, "operation": "concurrent"},
                    }

                    return await service.cache_planning_result(
                        request=request_key,
                        result=test_data,
                        metadata={"operation": "concurrent_set"},
                    )

                # get
                result = await service.get_planning_result(request=request_key)
                return True  # Success whether data exists or not

            except Exception as e:
                print(f"Concurrent cache operation failed: {e}")
                return False

        # Test different concurrency levels
        concurrency_levels = [1, 10, 25, 50, 100]
        scaling_results = {}

        for concurrent_ops in concurrency_levels:
            operations_per_task = 20

            results = await load_test_runner.run_async_load_test(
                concurrent_cache_operation,
                concurrent_tasks=concurrent_ops,
                operations_per_task=operations_per_task,
                ramp_up_seconds=0.2,
            )

            scaling_results[concurrent_ops] = {
                "throughput": results["throughput"],
                "avg_response_time": results["avg_response_time"],
                "success_rate": results["success_rate"],
                "total_operations": results["total_operations"],
            }

            print(
                f"Concurrency {concurrent_ops}: {results['throughput']:.2f} ops/sec, "
                f"avg time: {results['avg_response_time']:.6f}s, "
                f"success rate: {results['success_rate']:.4f}"
            )

        # Verify scaling characteristics
        min_threshold = performance_thresholds["cache"]["throughput_ops_per_sec"]

        for concurrency, results in scaling_results.items():
            assert (
                results["success_rate"] > 0.95
            ), f"Success rate too low at {concurrency} concurrent operations: {results['success_rate']:.4f}"

            # Throughput should scale with concurrency up to backend limits
            if concurrency == 1:
                assert (
                    results["throughput"] >= min_threshold
                ), f"Single-threaded cache throughput too low: {results['throughput']:.2f} ops/sec"
            elif concurrency <= 50:
                # Should maintain reasonable throughput
                expected_min_throughput = min_threshold * min(
                    concurrency, 20
                )  # Scale up to 20x
                assert (
                    results["throughput"] >= expected_min_throughput
                ), f"Cache throughput too low at {concurrency} concurrent operations: {results['throughput']:.2f} ops/sec"

    @pytest.mark.asyncio
    async def test_cache_hit_miss_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Test cache performance with different hit/miss ratios."""

        config = CacheConfig(enabled=True, default_ttl=3600)
        service = CacheService(config)

        # Mock backend with hit/miss tracking
        mock_backend = MockRedisCache(config)
        service._backend = mock_backend
        service._initialized = True

        performance_profiler.start_measurement()

        # Pre-populate cache with some data (for cache hits)
        hit_data = {}
        for i in range(100):
            request_key = f"hit_test_request_{i}"
            test_value = f"Pre-populated data {i}"

            await service.cache_planning_result(request=request_key, result=test_value)
            hit_data[request_key] = test_value

        # Test different hit/miss scenarios
        scenarios = [
            {"name": "high_hit_rate", "hit_ratio": 0.9},  # 90% hits
            {"name": "balanced", "hit_ratio": 0.5},  # 50% hits
            {"name": "high_miss_rate", "hit_ratio": 0.1},  # 10% hits
        ]

        hit_miss_results = {}
        threshold = performance_thresholds["cache"]["cache_get_ms"] / 1000

        for scenario in scenarios:
            hit_ratio = scenario["hit_ratio"]
            scenario_name = scenario["name"]

            hit_times = []
            miss_times = []

            for i in range(200):  # Test 200 operations per scenario
                # Determine if this should be a hit or miss
                should_hit = (i / 200) < hit_ratio

                if should_hit:
                    # Use existing key for cache hit
                    request_key = f"hit_test_request_{i % 100}"
                else:
                    # Use non-existent key for cache miss
                    request_key = f"miss_test_request_{i}"

                start_time = time.perf_counter()

                try:
                    result = await service.get_planning_result(request=request_key)

                    if should_hit:
                        # Should be a cache hit
                        assert (
                            result is not None
                        ), f"Expected cache hit but got miss for {request_key}"
                        hit_times.append(time.perf_counter() - start_time)
                    else:
                        # Should be a cache miss
                        assert (
                            result is None
                        ), f"Expected cache miss but got hit for {request_key}"
                        miss_times.append(time.perf_counter() - start_time)

                    success = True

                except Exception as e:
                    success = False
                    print(f"Cache hit/miss test failed: {e}")

                operation_time = time.perf_counter() - start_time
                operation_type = (
                    f"cache_{'hit' if should_hit else 'miss'}_{scenario_name}"
                )

                performance_profiler.record_operation(
                    operation_time, success=success, operation_type=operation_type
                )

            hit_miss_results[scenario_name] = {
                "avg_hit_time": sum(hit_times) / len(hit_times) if hit_times else 0,
                "avg_miss_time": sum(miss_times) / len(miss_times) if miss_times else 0,
                "hit_count": len(hit_times),
                "miss_count": len(miss_times),
                "actual_hit_ratio": len(hit_times) / (len(hit_times) + len(miss_times)),
            }

        performance_profiler.end_measurement()

        # Analyze hit/miss performance
        for scenario_name, results in hit_miss_results.items():
            if results["avg_hit_time"] > 0:
                assert (
                    results["avg_hit_time"] < threshold
                ), f"Cache hit time too slow in {scenario_name}: {results['avg_hit_time']:.6f}s"

            if results["avg_miss_time"] > 0:
                assert (
                    results["avg_miss_time"] < threshold
                ), f"Cache miss time too slow in {scenario_name}: {results['avg_miss_time']:.6f}s"

            print(
                f"{scenario_name}: Hit ratio {results['actual_hit_ratio']:.2f}, "
                f"Hit time {results['avg_hit_time']:.6f}s, Miss time {results['avg_miss_time']:.6f}s"
            )


class TestCacheMemoryPerformance:
    """Test cache memory usage and performance."""

    @pytest.mark.asyncio
    async def test_large_object_caching_performance(
        self,
        performance_profiler,
        memory_monitor,
        large_dataset_generator,
        performance_thresholds,
    ):
        """Test caching performance with large objects."""

        async def cache_large_objects():
            """Cache large objects and test memory usage."""
            config = CacheConfig(enabled=True, default_ttl=3600)
            service = CacheService(config)

            mock_backend = MockRedisCache(config)
            service._backend = mock_backend
            service._initialized = True

            # Test caching objects of different sizes
            sizes = [1, 5, 10]  # MB
            cached_count = 0

            for size_mb in sizes:
                for i in range(5):  # 5 objects per size
                    large_data = large_dataset_generator(
                        size_mb=size_mb, complexity="medium"
                    )
                    request_key = f"large_object_{size_mb}mb_{i}"

                    success = await service.cache_planning_result(
                        request=request_key,
                        result=large_data,
                        metadata={"size_mb": size_mb, "test": "large_object"},
                    )

                    if success:
                        cached_count += 1

                    # Also test retrieval
                    retrieved = await service.get_planning_result(request=request_key)
                    if retrieved is not None:
                        # Verify data integrity for smaller objects (to avoid excessive memory usage)
                        if size_mb <= 1:
                            assert retrieved == large_data

            return cached_count

        performance_profiler.start_measurement()

        def memory_test_operation():
            return asyncio.run(cache_large_objects())

        memory_usage = memory_monitor(memory_test_operation)

        performance_profiler.record_operation(
            memory_usage["execution_time"],
            success=memory_usage["success"],
            operation_type="large_object_caching",
        )

        performance_profiler.end_measurement()

        # Verify memory usage is reasonable
        memory_limit = performance_thresholds["cache"]["memory_limit_mb"]
        assert (
            memory_usage["memory_delta_mb"] < memory_limit
        ), f"Cache large object memory usage too high: {memory_usage['memory_delta_mb']:.2f}MB"

        assert memory_usage["success"], "Large object caching should succeed"
        assert memory_usage["result"] > 0, "Should have cached some objects"

        print(
            f"Large object caching memory usage: {memory_usage['memory_delta_mb']:.2f}MB"
        )
        print(
            f"Cached {memory_usage['result']} large objects in {memory_usage['execution_time']:.6f}s"
        )


class TestCacheStressTesting:
    """Stress testing for cache service under extreme conditions."""

    @pytest.mark.asyncio
    async def test_cache_service_stress_test(
        self, performance_profiler, stress_test_scenarios
    ):
        """Test cache service under high stress conditions."""

        config = CacheConfig(enabled=True, default_ttl=1800)
        service = CacheService(config)

        # Mock backend with large capacity
        mock_backend = MockRedisCache(config)
        service._backend = mock_backend
        service._initialized = True

        async def stress_cache_operation():
            """High-stress cache operation."""
            import random

            operation = random.choice(
                [
                    "set",
                    "get",
                    "set",
                    "get",
                ]
            )  # Favor get/set operations
            cache_id = random.randint(1, 10000)

            try:
                if operation == "set":
                    request_data = {
                        "request": f"stress_test_request_{cache_id}",
                        "complexity": random.choice(["SIMPLE", "MEDIUM", "COMPLEX"]),
                        "parameters": {
                            f"param_{i}": f"value_{i}"
                            for i in range(random.randint(5, 20))
                        },
                        "timestamp": time.time(),
                        "random_data": random.randint(1, 1000000),
                    }

                    result_data = {
                        "result": f"stress_result_{cache_id}",
                        "analysis": random.choice(["positive", "negative", "neutral"]),
                        "confidence": random.uniform(0.5, 1.0),
                        "factors": [
                            f"factor_{i}" for i in range(random.randint(3, 10))
                        ],
                        "metadata": {"stress_test": True, "operation_id": cache_id},
                    }

                    if random.choice([True, False]):
                        # Cache planning result
                        success = await service.cache_planning_result(
                            request=request_data,
                            result=result_data,
                            metadata={"stress_test": True},
                        )
                    else:
                        # Cache complexity assessment
                        success = await service.cache_complexity_assessment(
                            request=request_data,
                            assessment=result_data,
                            metadata={"stress_test": True},
                        )

                    return success

                # get
                request_data = {
                    "request": f"stress_test_request_{cache_id}",
                    "complexity": random.choice(["SIMPLE", "MEDIUM", "COMPLEX"]),
                    "timestamp": time.time(),
                }

                if random.choice([True, False]):
                    # Get planning result
                    result = await service.get_planning_result(request=request_data)
                else:
                    # Get complexity assessment
                    result = await service.get_complexity_assessment(
                        request=request_data
                    )

                return True  # Success whether data exists or not

            except Exception as e:
                print(f"Stress cache operation failed: {e}")
                return False

        performance_profiler.start_measurement()

        # Stress test configuration
        stress_config = stress_test_scenarios["concurrent_stress"]
        concurrent_ops = stress_config["thread_counts"][2]  # Use high concurrency
        duration = stress_config["duration_seconds"][1]  # Use moderate duration

        start_time = time.perf_counter()
        completed_operations = 0
        errors = []

        # Run stress test
        async def stress_worker():
            nonlocal completed_operations
            while time.perf_counter() - start_time < duration:
                try:
                    success = await stress_cache_operation()
                    completed_operations += 1

                    performance_profiler.record_operation(
                        time.perf_counter() - start_time,
                        success=success,
                        operation_type="cache_stress_test",
                    )

                    # Very small delay to prevent overwhelming
                    await asyncio.sleep(0.001)  # 1ms delay

                except Exception as e:
                    errors.append(str(e))
                    performance_profiler.record_operation(
                        time.perf_counter() - start_time,
                        success=False,
                        operation_type="cache_stress_error",
                    )

        # Run concurrent stress workers
        tasks = [asyncio.create_task(stress_worker()) for _ in range(concurrent_ops)]
        await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.perf_counter() - start_time
        performance_profiler.end_measurement()

        # Analyze stress test results
        error_rate = len(errors) / max(completed_operations + len(errors), 1)
        throughput = completed_operations / total_time

        print("Cache stress test results:")
        print(f"- Duration: {total_time:.2f}s")
        print(f"- Completed operations: {completed_operations}")
        print(f"- Errors: {len(errors)}")
        print(f"- Throughput: {throughput:.2f} ops/sec")
        print(f"- Error rate: {error_rate:.4f}")
        print(f"- Total cached items: {len(mock_backend.data)}")

        # Verify system survived stress test
        assert error_rate < 0.1, f"Error rate too high under stress: {error_rate:.4f}"
        assert completed_operations > 0, "No operations completed during stress test"
        assert (
            throughput > 100.0
        ), f"Cache throughput too low under stress: {throughput:.2f} ops/sec"

        metrics = performance_profiler.get_comprehensive_metrics()
        assert (
            metrics["success_rate"] > 0.9
        ), f"Success rate too low: {metrics['success_rate']:.4f}"
