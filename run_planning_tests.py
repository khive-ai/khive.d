#!/usr/bin/env python3
"""
Comprehensive test runner for planning service unit tests.

This script demonstrates how to run the complete test suite for workflow pattern
determination, external model integration, and consistency validation.
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)

    start_time = time.time()
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, shell=False)  # noqa: S603
        duration = time.time() - start_time
        print(f"✅ SUCCESS ({duration:.2f}s)")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        print(f"❌ FAILED ({duration:.2f}s)")
        print(f"Return code: {e.returncode}")
        if e.stdout:
            print("STDOUT:")
            print(e.stdout)
        if e.stderr:
            print("STDERR:")
            print(e.stderr)
        return False


def main():
    """Run comprehensive planning service tests."""
    print("🧪 Khive Planning Service - Comprehensive Test Suite")
    print(
        "Testing workflow pattern determination, external model integration, and consistency validation"
    )

    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Ensure we have the required test dependencies
    print("\n📦 Installing test dependencies...")
    if not run_command(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-e",
            ".",
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
            "pytest-benchmark",
            "psutil",
        ],
        "Install test dependencies",
    ):
        return 1

    success_count = 0
    total_tests = 0

    # Test categories to run
    test_categories = [
        {
            "name": "Unit Tests - Core Algorithms",
            "cmd": [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_planning_service.py",
                "-m",
                "unit",
                "-v",
            ],
            "description": "Test complexity assessment, role selection, and workflow pattern determination",
        },
        {
            "name": "External Model Integration Tests",
            "cmd": [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_planning_service.py::TestExternalModelIntegration",
                "-v",
            ],
            "description": "Test OpenAI integration, cost tracking, and external model mocking",
        },
        {
            "name": "Consistency Validation Tests",
            "cmd": [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_planning_service.py::TestConsistencyValidation",
                "-v",
            ],
            "description": "Test deterministic behavior and identical input consistency",
        },
        {
            "name": "Performance Benchmarks",
            "cmd": [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_planning_service.py",
                "-m",
                "performance",
                "-v",
                "--benchmark-only",
            ],
            "description": "Performance benchmarks for critical paths",
        },
        {
            "name": "Integration Tests",
            "cmd": [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_planning_service.py",
                "-m",
                "integration",
                "-v",
            ],
            "description": "End-to-end integration testing",
        },
        {
            "name": "Pydantic Model Validation",
            "cmd": [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_planning_service.py::TestPydanticValidation",
                "-v",
            ],
            "description": "Validate Pydantic models and schemas",
        },
    ]

    # Run each test category
    for category in test_categories:
        total_tests += 1
        print(f"\n🔍 {category['name']}")
        print(f"Description: {category['description']}")

        if run_command(category["cmd"], category["name"]):
            success_count += 1
            print(f"✅ {category['name']} - PASSED")
        else:
            print(f"❌ {category['name']} - FAILED")

    # Generate comprehensive coverage report
    print("\n📊 Generating comprehensive coverage report...")
    if run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_planning_service.py",
            "--cov=khive.services.plan",
            "--cov-report=html:htmlcov/planning_service",
            "--cov-report=term-missing",
            "--cov-report=json:coverage.json",
            "--cov-fail-under=90",
        ],
        "Generate coverage report",
    ):
        success_count += 1
        print("📊 Coverage report generated in htmlcov/planning_service/")
    total_tests += 1

    # Run specific consistency validation scenarios
    print("\n🔄 Running consistency validation scenarios...")
    consistency_scenarios = [
        "tests/test_planning_service.py::TestConsistencyValidation::test_complexity_assessment_determinism",
        "tests/test_planning_service.py::TestConsistencyValidation::test_role_selection_determinism",
        "tests/test_planning_service.py::TestConsistencyValidation::test_heuristic_assessment_stability",
    ]

    for scenario in consistency_scenarios:
        total_tests += 1
        if run_command(
            [sys.executable, "-m", "pytest", scenario, "-v"],
            f"Consistency scenario: {scenario.split('::')[-1]}",
        ):
            success_count += 1

    # Performance benchmark summary
    print("\n⚡ Running performance benchmarks...")
    if run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_planning_service.py::TestPerformanceBenchmarks",
            "-v",
            "--tb=short",
        ],
        "Performance benchmarks",
    ):
        success_count += 1
    total_tests += 1

    # Summary
    print(f"\n{'=' * 60}")
    print("🏁 TEST SUITE SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total test categories: {total_tests}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_tests - success_count}")
    print(f"Success rate: {(success_count / total_tests) * 100:.1f}%")

    if success_count == total_tests:
        print("\n🎉 ALL TESTS PASSED! Planning service is ready for production.")
        print("Key achievements:")
        print("  ✅ Workflow pattern determination tested and validated")
        print("  ✅ External model integration (OpenAI) mocked and tested")
        print("  ✅ Consistency validation ensures deterministic behavior")
        print("  ✅ Performance benchmarks meet critical path requirements")
        print("  ✅ >90% test coverage achieved")
        return 0
    print("\n⚠️  Some tests failed. Please review the output above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
