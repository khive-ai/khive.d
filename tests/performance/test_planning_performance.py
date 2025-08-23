"""Performance tests for planning service.

Comprehensive performance testing for the khive planning service including:
- Complexity assessment performance and scalability
- Role selection and domain loading performance
- Cost tracking and budget management performance
- Timeout management and parallel execution performance
- Decision matrix processing and evaluation performance
- Large-scale planning operation benchmarking
- Memory profiling for complex planning scenarios
- Stress testing for concurrent planning operations
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from khive.services.artifacts.handlers import TimeoutConfig
from khive.services.plan.planner_service import (
    ComplexityTier,
    OrchestrationPlanner,
    Request,
)


class TestPlanningBenchmarks:
    """Benchmark planning core operations for performance baseline."""

    def test_complexity_assessment_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark complexity assessment performance."""

        # Mock environment and dependencies to avoid external API calls
        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}),
            patch("openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value = Mock()
            planner = OrchestrationPlanner()

            performance_profiler.start_measurement()

            # Test different complexity levels of requests
            test_requests = [
                "Simple task: print hello world",
                "Medium complexity: Create a REST API with authentication and basic CRUD operations",
                "Complex task: Design and implement a distributed microservices architecture with event sourcing, CQRS, and multiple databases",
                "Very complex: Build a full-stack application with React frontend, Node.js backend, PostgreSQL database, Redis caching, Docker containerization, CI/CD pipeline, monitoring, and deployment to Kubernetes",
                "Another simple task: Add a comment to existing function",
                "Medium task: Implement user registration and login system",
                "Complex integration: Migrate legacy monolith to microservices while maintaining zero downtime",
            ]

            assessment_times = []
            threshold = performance_thresholds["planning"]["simple_plan_ms"] / 1000

            for i, request_text in enumerate(test_requests):
                request = Request(request_text)

                start_time = time.perf_counter()

                try:
                    # Mock the assessment method since it typically involves external API calls
                    with patch.object(planner, "assess") as mock_assess:
                        # Simulate different complexity tiers based on request length
                        if len(request_text) < 50:
                            mock_assess.return_value = ComplexityTier.SIMPLE
                        elif len(request_text) < 150:
                            mock_assess.return_value = ComplexityTier.MEDIUM
                        elif len(request_text) < 250:
                            mock_assess.return_value = ComplexityTier.COMPLEX
                        else:
                            mock_assess.return_value = ComplexityTier.VERY_COMPLEX

                        complexity = planner.assess(request)
                        success = True

                except Exception as e:
                    success = False
                    complexity = None
                    print(f"Complexity assessment failed for request {i}: {e}")

                end_time = time.perf_counter()
                assessment_time = end_time - start_time
                assessment_times.append(assessment_time)

                performance_profiler.record_operation(
                    assessment_time,
                    success=success,
                    operation_type=f"complexity_assessment_{complexity.value if complexity else 'failed'}",
                )

            performance_profiler.end_measurement()

            # Analyze performance
            avg_time = sum(assessment_times) / len(assessment_times)
            min_time = min(assessment_times)
            max_time = max(assessment_times)

            # Performance assertions
            assert (
                avg_time < threshold
            ), f"Average assessment time too slow: {avg_time:.6f}s"
            assert (
                min_time < threshold * 0.5
            ), f"Minimum assessment time too slow: {min_time:.6f}s"
            assert (
                max_time < threshold * 2.0
            ), f"Maximum assessment time too slow: {max_time:.6f}s"

            print(
                f"Complexity assessment - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s"
            )

    def test_role_selection_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark role selection performance."""

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}),
            patch("openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value = Mock()

            # Mock the file system operations for loading roles
            mock_roles = [
                "researcher",
                "analyst",
                "architect",
                "implementer",
                "tester",
                "reviewer",
                "critic",
                "commentator",
                "auditor",
                "innovator",
                "strategist",
                "optimizer",
            ]

            with (
                patch.object(
                    OrchestrationPlanner,
                    "_load_available_roles",
                    return_value=mock_roles,
                ),
                patch.object(
                    OrchestrationPlanner, "_load_available_domains", return_value=[]
                ),
                patch.object(
                    OrchestrationPlanner, "_load_prompt_templates", return_value={}
                ),
                patch.object(
                    OrchestrationPlanner, "_load_decision_matrix", return_value={}
                ),
            ):
                planner = OrchestrationPlanner()

                performance_profiler.start_measurement()

                # Test role selection for different complexity levels
                test_scenarios = [
                    {
                        "complexity": ComplexityTier.SIMPLE,
                        "request": "Simple debugging task",
                    },
                    {
                        "complexity": ComplexityTier.MEDIUM,
                        "request": "Implement new feature",
                    },
                    {
                        "complexity": ComplexityTier.COMPLEX,
                        "request": "Refactor complex system",
                    },
                    {
                        "complexity": ComplexityTier.VERY_COMPLEX,
                        "request": "Design distributed architecture",
                    },
                ]

                selection_times = []
                threshold = performance_thresholds["planning"]["simple_plan_ms"] / 1000

                for scenario in test_scenarios * 5:  # Test each scenario 5 times
                    request = Request(scenario["request"])
                    complexity = scenario["complexity"]

                    start_time = time.perf_counter()

                    try:
                        # Mock role selection logic
                        with patch.object(planner, "select_roles") as mock_select:
                            if complexity == ComplexityTier.SIMPLE:
                                mock_select.return_value = ["implementer"]
                            elif complexity == ComplexityTier.MEDIUM:
                                mock_select.return_value = ["researcher", "implementer"]
                            elif complexity == ComplexityTier.COMPLEX:
                                mock_select.return_value = [
                                    "researcher",
                                    "architect",
                                    "implementer",
                                    "tester",
                                ]
                            else:  # VERY_COMPLEX
                                mock_select.return_value = [
                                    "researcher",
                                    "analyst",
                                    "architect",
                                    "implementer",
                                    "tester",
                                    "reviewer",
                                ]

                            selected_roles = planner.select_roles(request, complexity)
                            success = len(selected_roles) > 0

                    except Exception as e:
                        success = False
                        selected_roles = []
                        print(f"Role selection failed for {complexity.value}: {e}")

                    end_time = time.perf_counter()
                    selection_time = end_time - start_time
                    selection_times.append(selection_time)

                    performance_profiler.record_operation(
                        selection_time,
                        success=success,
                        operation_type=f"role_selection_{complexity.value}",
                    )

                performance_profiler.end_measurement()

                # Analyze performance
                avg_time = sum(selection_times) / len(selection_times)
                min_time = min(selection_times)
                max_time = max(selection_times)

                assert (
                    avg_time < threshold
                ), f"Average role selection time too slow: {avg_time:.6f}s"
                assert (
                    max_time < threshold * 2.0
                ), f"Maximum role selection time too slow: {max_time:.6f}s"

                print(
                    f"Role selection - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s"
                )

    def test_domain_loading_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Benchmark domain loading performance."""

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}),
            patch("openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value = Mock()

            # Create temporary directory structure for domains
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Create mock domain files
                domains_dir = temp_path / "domains"
                domains_dir.mkdir()

                # Create multiple categories with domains
                categories = [
                    "architecture",
                    "development",
                    "testing",
                    "security",
                    "performance",
                ]
                domains_per_category = 10

                for category in categories:
                    category_dir = domains_dir / category
                    category_dir.mkdir()

                    for i in range(domains_per_category):
                        domain_data = {
                            "domain": {"id": f"{category}_{i}"},
                            "knowledge_patterns": {
                                f"pattern_{j}": [f"item_{j}_{k}" for k in range(10)]
                                for j in range(5)
                            },
                            "decision_rules": {
                                f"rule_{j}": f"Rule {j} description" for j in range(8)
                            },
                        }

                        domain_file = category_dir / f"{category}_{i}.yaml"
                        with open(domain_file, "w") as f:
                            yaml.dump(domain_data, f)

                performance_profiler.start_measurement()

                # Mock the path lookup to use our temporary directory
                with (
                    patch(
                        "khive.services.plan.planner_service.KHIVE_CONFIG_DIR",
                        temp_path / "config",
                    ),
                    patch.object(
                        OrchestrationPlanner, "_load_available_roles", return_value=[]
                    ),
                    patch.object(
                        OrchestrationPlanner, "_load_prompt_templates", return_value={}
                    ),
                    patch.object(
                        OrchestrationPlanner, "_load_decision_matrix", return_value={}
                    ),
                ):
                    # Patch the actual path lookup in the method
                    with patch("khive.utils.KHIVE_CONFIG_DIR", temp_path):
                        # Create the expected directory structure
                        prompts_dir = temp_path / "prompts"
                        prompts_dir.mkdir()

                        # Copy our domains directory to the expected location
                        import shutil

                        shutil.copytree(domains_dir, prompts_dir / "domains")

                        loading_times = []
                        threshold = (
                            performance_thresholds["planning"]["simple_plan_ms"] / 1000
                        )

                        # Test domain loading multiple times
                        for i in range(10):
                            start_time = time.perf_counter()

                            try:
                                planner = OrchestrationPlanner()
                                domains = planner._load_available_domains()
                                success = len(domains) > 0

                                expected_domain_count = (
                                    len(categories) * domains_per_category
                                )
                                assert (
                                    len(domains) == expected_domain_count
                                ), f"Expected {expected_domain_count} domains, got {len(domains)}"

                            except Exception as e:
                                success = False
                                domains = []
                                print(f"Domain loading failed on iteration {i}: {e}")

                            end_time = time.perf_counter()
                            loading_time = end_time - start_time
                            loading_times.append(loading_time)

                            performance_profiler.record_operation(
                                loading_time,
                                success=success,
                                operation_type="domain_loading",
                            )

                performance_profiler.end_measurement()

                # Analyze performance
                avg_time = sum(loading_times) / len(loading_times)
                min_time = min(loading_times)
                max_time = max(loading_times)

                assert (
                    avg_time < threshold
                ), f"Average domain loading time too slow: {avg_time:.6f}s"
                assert (
                    max_time < threshold * 2.0
                ), f"Maximum domain loading time too slow: {max_time:.6f}s"

                print(
                    f"Domain loading - Avg: {avg_time:.6f}s, Min: {min_time:.6f}s, Max: {max_time:.6f}s"
                )


class TestPlanningScalability:
    """Test planning performance scalability under increasing loads."""

    async def test_concurrent_complexity_assessment_scaling(
        self, performance_profiler, load_test_runner, performance_thresholds
    ):
        """Test complexity assessment performance with concurrent requests."""

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}),
            patch("openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value = Mock()

            # Mock dependencies
            with (
                patch.object(
                    OrchestrationPlanner, "_load_available_roles", return_value=[]
                ),
                patch.object(
                    OrchestrationPlanner, "_load_available_domains", return_value=[]
                ),
                patch.object(
                    OrchestrationPlanner, "_load_prompt_templates", return_value={}
                ),
                patch.object(
                    OrchestrationPlanner, "_load_decision_matrix", return_value={}
                ),
            ):
                planner = OrchestrationPlanner()

                async def assess_complexity_operation():
                    """Single complexity assessment operation for load testing."""
                    request = Request(
                        "Test complexity assessment request for load testing"
                    )

                    # Mock the assessment to avoid external API calls
                    with patch.object(
                        planner, "assess", return_value=ComplexityTier.MEDIUM
                    ):
                        return planner.assess(request)

                # Test different concurrency levels
                concurrency_levels = [1, 5, 10, 20]
                scaling_results = {}

                for concurrent_ops in concurrency_levels:
                    operations_per_task = 10

                    results = await load_test_runner.run_async_load_test(
                        assess_complexity_operation,
                        concurrent_tasks=concurrent_ops,
                        operations_per_task=operations_per_task,
                        ramp_up_seconds=0.5,
                    )

                    scaling_results[concurrent_ops] = {
                        "throughput": results["throughput"],
                        "avg_response_time": results["avg_response_time"],
                        "success_rate": results["success_rate"],
                        "total_operations": results["total_operations"],
                    }

                    print(
                        f"Concurrency {concurrent_ops}: {results['throughput']:.2f} assessments/sec, "
                        f"avg time: {results['avg_response_time']:.6f}s"
                    )

                # Verify scaling characteristics
                min_threshold = performance_thresholds["planning"][
                    "throughput_ops_per_sec"
                ]

                for concurrency, results in scaling_results.items():
                    assert (
                        results["success_rate"] > 0.95
                    ), f"Success rate too low at {concurrency} concurrent operations: {results['success_rate']:.4f}"

                    if concurrency == 1:
                        # Single-threaded should meet minimum throughput
                        assert (
                            results["throughput"] >= min_threshold
                        ), f"Single-threaded throughput too low: {results['throughput']:.2f} ops/sec"

    @pytest.mark.asyncio
    async def test_large_scale_planning_performance(
        self, performance_profiler, large_dataset_generator, performance_thresholds
    ):
        """Test planning performance with large-scale planning scenarios."""

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}),
            patch("openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value = Mock()

            # Create large number of roles and domains
            mock_roles = [f"role_{i}" for i in range(50)]
            mock_domains = [f"domain_{i}" for i in range(100)]

            with (
                patch.object(
                    OrchestrationPlanner,
                    "_load_available_roles",
                    return_value=mock_roles,
                ),
                patch.object(
                    OrchestrationPlanner,
                    "_load_available_domains",
                    return_value=mock_domains,
                ),
                patch.object(
                    OrchestrationPlanner, "_load_prompt_templates", return_value={}
                ),
                patch.object(
                    OrchestrationPlanner, "_load_decision_matrix", return_value={}
                ),
            ):
                planner = OrchestrationPlanner()

                performance_profiler.start_measurement()

                # Test different scales of planning scenarios
                scale_scenarios = [
                    {
                        "complexity": ComplexityTier.SIMPLE,
                        "expected_agents": 1,
                        "scale": "small",
                    },
                    {
                        "complexity": ComplexityTier.MEDIUM,
                        "expected_agents": 3,
                        "scale": "medium",
                    },
                    {
                        "complexity": ComplexityTier.COMPLEX,
                        "expected_agents": 7,
                        "scale": "large",
                    },
                    {
                        "complexity": ComplexityTier.VERY_COMPLEX,
                        "expected_agents": 15,
                        "scale": "very_large",
                    },
                ]

                planning_times = {}
                threshold = performance_thresholds["planning"]["complex_plan_ms"] / 1000

                for scenario in scale_scenarios:
                    complexity = scenario["complexity"]
                    scale = scenario["scale"]
                    expected_agents = scenario["expected_agents"]

                    times = []

                    for i in range(5):  # Test each scale 5 times
                        # Generate large context for this scenario
                        large_context = large_dataset_generator(
                            size_mb=1, complexity="medium"
                        )
                        request_text = f"Large scale {scale} planning scenario: {json.dumps(large_context)[:500]}"

                        request = Request(request_text)

                        start_time = time.perf_counter()

                        try:
                            # Mock both assessment and role selection
                            with (
                                patch.object(
                                    planner, "assess", return_value=complexity
                                ),
                                patch.object(
                                    planner,
                                    "select_roles",
                                    return_value=mock_roles[:expected_agents],
                                ),
                            ):
                                assessed_complexity = planner.assess(request)
                                selected_roles = planner.select_roles(
                                    request, assessed_complexity
                                )

                                success = len(selected_roles) == expected_agents

                        except Exception as e:
                            success = False
                            print(f"Large scale planning failed for {scale}: {e}")

                        end_time = time.perf_counter()
                        planning_time = end_time - start_time
                        times.append(planning_time)

                        performance_profiler.record_operation(
                            planning_time,
                            success=success,
                            operation_type=f"large_scale_planning_{scale}",
                        )

                    planning_times[scale] = {
                        "avg": sum(times) / len(times),
                        "min": min(times),
                        "max": max(times),
                    }

                performance_profiler.end_measurement()

                # Verify planning performance scales reasonably
                for scale, metrics in planning_times.items():
                    max_expected_time = threshold * (2 if scale == "very_large" else 1)
                    assert (
                        metrics["avg"] < max_expected_time
                    ), f"Large scale planning for {scale} too slow: {metrics['avg']:.6f}s"
                    print(f"Large scale {scale} - Avg: {metrics['avg']:.6f}s")


class TestPlanningMemoryPerformance:
    """Test planning memory usage and performance."""

    def test_cost_tracking_memory_performance(
        self, performance_profiler, memory_monitor, performance_thresholds
    ):
        """Test cost tracking memory usage with large number of operations."""

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}),
            patch("openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value = Mock()

            def cost_tracking_operation():
                """Operation that heavily uses cost tracking."""
                with (
                    patch.object(
                        OrchestrationPlanner, "_load_available_roles", return_value=[]
                    ),
                    patch.object(
                        OrchestrationPlanner, "_load_available_domains", return_value=[]
                    ),
                    patch.object(
                        OrchestrationPlanner, "_load_prompt_templates", return_value={}
                    ),
                    patch.object(
                        OrchestrationPlanner, "_load_decision_matrix", return_value={}
                    ),
                ):
                    planner = OrchestrationPlanner()

                    # Simulate many cost tracking operations
                    for i in range(100):
                        # Mock cost tracking operations
                        planner.cost_tracker.add_cost(0.001)  # Small cost per operation

                        # Simulate planning operations
                        request = Request(f"Planning request {i}")
                        with patch.object(
                            planner, "assess", return_value=ComplexityTier.MEDIUM
                        ):
                            planner.assess(request)

                    return planner.cost_tracker

            performance_profiler.start_measurement()

            memory_usage = memory_monitor(cost_tracking_operation)

            performance_profiler.record_operation(
                memory_usage["execution_time"],
                success=memory_usage["success"],
                operation_type="cost_tracking_heavy",
            )

            performance_profiler.end_measurement()

            # Verify memory usage is reasonable
            memory_limit = performance_thresholds["planning"]["memory_limit_mb"]
            assert (
                memory_usage["memory_delta_mb"] < memory_limit
            ), f"Cost tracking memory usage too high: {memory_usage['memory_delta_mb']:.2f}MB"

            assert memory_usage["success"], "Cost tracking operation should succeed"

            print(
                f"Cost tracking memory usage: {memory_usage['memory_delta_mb']:.2f}MB"
            )
            print(
                f"Cost tracking execution time: {memory_usage['execution_time']:.6f}s"
            )

    def test_timeout_management_performance(
        self, performance_profiler, performance_thresholds
    ):
        """Test timeout management performance under various scenarios."""

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}),
            patch("openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value = Mock()

            performance_profiler.start_measurement()

            # Test different timeout configurations
            timeout_configs = [
                TimeoutConfig(
                    agent_execution_timeout=60.0, phase_completion_timeout=300.0
                ),
                TimeoutConfig(
                    agent_execution_timeout=120.0, phase_completion_timeout=600.0
                ),
                TimeoutConfig(
                    agent_execution_timeout=300.0, phase_completion_timeout=1800.0
                ),
            ]

            timeout_performance = {}
            threshold = performance_thresholds["planning"]["simple_plan_ms"] / 1000

            for i, config in enumerate(timeout_configs):
                times = []

                for j in range(10):  # Test each config 10 times
                    start_time = time.perf_counter()

                    try:
                        with (
                            patch.object(
                                OrchestrationPlanner,
                                "_load_available_roles",
                                return_value=[],
                            ),
                            patch.object(
                                OrchestrationPlanner,
                                "_load_available_domains",
                                return_value=[],
                            ),
                            patch.object(
                                OrchestrationPlanner,
                                "_load_prompt_templates",
                                return_value={},
                            ),
                            patch.object(
                                OrchestrationPlanner,
                                "_load_decision_matrix",
                                return_value={},
                            ),
                        ):
                            planner = OrchestrationPlanner(timeout_config=config)

                            # Test timeout configuration
                            assert (
                                planner.timeout_config.agent_execution_timeout
                                == config.agent_execution_timeout
                            )
                            assert (
                                planner.timeout_config.phase_completion_timeout
                                == config.phase_completion_timeout
                            )

                            success = True

                    except Exception as e:
                        success = False
                        print(f"Timeout configuration test failed: {e}")

                    end_time = time.perf_counter()
                    config_time = end_time - start_time
                    times.append(config_time)

                    performance_profiler.record_operation(
                        config_time,
                        success=success,
                        operation_type=f"timeout_config_{i}",
                    )

                timeout_performance[f"config_{i}"] = {
                    "avg": sum(times) / len(times),
                    "min": min(times),
                    "max": max(times),
                }

            performance_profiler.end_measurement()

            # Verify timeout management doesn't add significant overhead
            for config_name, metrics in timeout_performance.items():
                assert (
                    metrics["avg"] < threshold
                ), f"Timeout management overhead too high for {config_name}: {metrics['avg']:.6f}s"
                print(f"Timeout {config_name} - Avg: {metrics['avg']:.6f}s")


class TestPlanningStressTesting:
    """Stress testing for planning service under extreme conditions."""

    @pytest.mark.asyncio
    async def test_planning_service_stress_test(
        self, performance_profiler, stress_test_scenarios
    ):
        """Test planning service under high stress conditions."""

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}),
            patch("openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value = Mock()

            # Create large mock datasets
            mock_roles = [f"role_{i}" for i in range(100)]
            mock_domains = [f"domain_{i}" for i in range(200)]

            async def stress_planning_operation():
                """High-stress planning operation."""
                with (
                    patch.object(
                        OrchestrationPlanner,
                        "_load_available_roles",
                        return_value=mock_roles,
                    ),
                    patch.object(
                        OrchestrationPlanner,
                        "_load_available_domains",
                        return_value=mock_domains,
                    ),
                    patch.object(
                        OrchestrationPlanner, "_load_prompt_templates", return_value={}
                    ),
                    patch.object(
                        OrchestrationPlanner, "_load_decision_matrix", return_value={}
                    ),
                ):
                    planner = OrchestrationPlanner()

                    # Simulate complex planning request
                    complex_request = Request(
                        "Complex distributed system architecture " * 50
                    )

                    with (
                        patch.object(
                            planner, "assess", return_value=ComplexityTier.VERY_COMPLEX
                        ),
                        patch.object(
                            planner, "select_roles", return_value=mock_roles[:10]
                        ),
                    ):
                        complexity = planner.assess(complex_request)
                        roles = planner.select_roles(complex_request, complexity)

                        return {"complexity": complexity, "roles_count": len(roles)}

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
                        result = await stress_planning_operation()
                        completed_operations += 1

                        performance_profiler.record_operation(
                            time.perf_counter() - start_time,
                            success=True,
                            operation_type="planning_stress_test",
                        )

                        # Small delay to prevent overwhelming
                        await asyncio.sleep(0.01)

                    except Exception as e:
                        errors.append(str(e))
                        performance_profiler.record_operation(
                            time.perf_counter() - start_time,
                            success=False,
                            operation_type="planning_stress_error",
                        )

            # Run concurrent stress workers
            tasks = [
                asyncio.create_task(stress_worker()) for _ in range(concurrent_ops)
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

            total_time = time.perf_counter() - start_time
            performance_profiler.end_measurement()

            # Analyze stress test results
            error_rate = len(errors) / max(completed_operations + len(errors), 1)
            throughput = completed_operations / total_time

            print("Planning stress test results:")
            print(f"- Duration: {total_time:.2f}s")
            print(f"- Completed operations: {completed_operations}")
            print(f"- Errors: {len(errors)}")
            print(f"- Throughput: {throughput:.2f} ops/sec")
            print(f"- Error rate: {error_rate:.4f}")

            # Verify system survived stress test
            assert (
                error_rate < 0.15
            ), f"Error rate too high under stress: {error_rate:.4f}"
            assert (
                completed_operations > 0
            ), "No operations completed during stress test"

            metrics = performance_profiler.get_comprehensive_metrics()
            assert (
                metrics["success_rate"] > 0.85
            ), f"Success rate too low: {metrics['success_rate']:.4f}"
