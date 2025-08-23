"""Comprehensive integration validation tests for all khive services.

This module provides:
- Integration test runner for all service validation tests
- Cross-service validation patterns
- Complete validation test suite orchestration
- Performance and stress testing for validation patterns
- Comprehensive reporting of validation results
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List

import pytest

from tests.validation.test_artifacts_validation import TestArtifactsValidation
from tests.validation.test_cache_validation import TestCacheValidation
from tests.validation.test_composition_validation import TestCompositionValidation
from tests.validation.test_orchestration_validation import TestOrchestrationValidation
from tests.validation.test_session_validation import TestSessionValidation


@dataclass
class ValidationResult:
    """Result of a validation test run."""

    service_name: str
    test_name: str
    success: bool
    duration: float
    error_message: str | None = None


@dataclass
class ServiceValidationSummary:
    """Summary of validation results for a service."""

    service_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    total_duration: float
    errors: List[str]

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100


class ComprehensiveValidationRunner:
    """Runner for comprehensive validation testing across all services."""

    def __init__(self):
        self.results: List[ValidationResult] = []
        self.service_summaries: Dict[str, ServiceValidationSummary] = {}

    def run_service_validation(
        self, service_name: str, test_class: type
    ) -> ServiceValidationSummary:
        """Run validation tests for a specific service."""
        print(f"\n🔍 Running {service_name} validation tests...")

        test_instance = test_class()
        test_methods = [
            method for method in dir(test_instance) if method.startswith("test_")
        ]

        results = []
        errors = []
        total_duration = 0.0

        for method_name in test_methods:
            test_method = getattr(test_instance, method_name)
            start_time = time.time()

            try:
                test_method()
                duration = time.time() - start_time
                total_duration += duration

                result = ValidationResult(
                    service_name=service_name,
                    test_name=method_name,
                    success=True,
                    duration=duration,
                )
                results.append(result)
                print(f"  ✅ {method_name} ({duration:.3f}s)")

            except Exception as e:
                duration = time.time() - start_time
                total_duration += duration
                error_msg = str(e)
                errors.append(f"{method_name}: {error_msg}")

                result = ValidationResult(
                    service_name=service_name,
                    test_name=method_name,
                    success=False,
                    duration=duration,
                    error_message=error_msg,
                )
                results.append(result)
                print(f"  ❌ {method_name} ({duration:.3f}s): {error_msg}")

        passed_tests = sum(1 for r in results if r.success)
        failed_tests = len(results) - passed_tests

        summary = ServiceValidationSummary(
            service_name=service_name,
            total_tests=len(results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            total_duration=total_duration,
            errors=errors,
        )

        self.results.extend(results)
        self.service_summaries[service_name] = summary

        print(
            f"  📊 {service_name}: {passed_tests}/{len(results)} tests passed ({summary.pass_rate:.1f}%)"
        )

        return summary

    def run_all_validations(self) -> Dict[str, ServiceValidationSummary]:
        """Run validation tests for all services."""
        print("🚀 Starting comprehensive khive validation testing...")
        print("=" * 60)

        services = [
            ("Artifacts Service", TestArtifactsValidation),
            ("Cache Service", TestCacheValidation),
            ("Session Service", TestSessionValidation),
            ("Composition Service", TestCompositionValidation),
            ("Orchestration Service", TestOrchestrationValidation),
        ]

        for service_name, test_class in services:
            try:
                self.run_service_validation(service_name, test_class)
            except Exception as e:
                print(f"  💥 Failed to run {service_name} validation: {e}")
                # Create error summary
                self.service_summaries[service_name] = ServiceValidationSummary(
                    service_name=service_name,
                    total_tests=0,
                    passed_tests=0,
                    failed_tests=1,
                    total_duration=0.0,
                    errors=[f"Service validation setup failed: {e}"],
                )

        return self.service_summaries

    def run_parallel_validations(self) -> Dict[str, ServiceValidationSummary]:
        """Run validation tests in parallel for better performance."""
        print("🚀 Starting parallel comprehensive validation testing...")
        print("=" * 60)

        services = [
            ("Artifacts Service", TestArtifactsValidation),
            ("Cache Service", TestCacheValidation),
            ("Session Service", TestSessionValidation),
            ("Composition Service", TestCompositionValidation),
            ("Orchestration Service", TestOrchestrationValidation),
        ]

        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all service validations
            futures = {
                executor.submit(
                    self.run_service_validation, service_name, test_class
                ): service_name
                for service_name, test_class in services
            }

            # Collect results as they complete
            for future in as_completed(futures):
                service_name = futures[future]
                try:
                    future.result()  # Summary already stored in run_service_validation
                except Exception as e:
                    print(f"  💥 Parallel validation failed for {service_name}: {e}")
                    self.service_summaries[service_name] = ServiceValidationSummary(
                        service_name=service_name,
                        total_tests=0,
                        passed_tests=0,
                        failed_tests=1,
                        total_duration=0.0,
                        errors=[f"Parallel execution failed: {e}"],
                    )

        return self.service_summaries

    def generate_report(self) -> str:
        """Generate comprehensive validation report."""
        if not self.service_summaries:
            return "No validation results to report."

        report_lines = ["📋 COMPREHENSIVE KHIVE VALIDATION REPORT", "=" * 60, ""]

        # Overall statistics
        total_tests = sum(s.total_tests for s in self.service_summaries.values())
        total_passed = sum(s.passed_tests for s in self.service_summaries.values())
        total_failed = sum(s.failed_tests for s in self.service_summaries.values())
        total_duration = sum(s.total_duration for s in self.service_summaries.values())
        overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        report_lines.extend(
            [
                "📊 OVERALL STATISTICS:",
                f"  Total Tests: {total_tests}",
                f"  Passed: {total_passed} ({overall_pass_rate:.1f}%)",
                f"  Failed: {total_failed}",
                f"  Total Duration: {total_duration:.2f}s",
                (
                    f"  Average Test Duration: {total_duration / total_tests:.3f}s"
                    if total_tests > 0
                    else "  Average Test Duration: N/A"
                ),
                "",
            ]
        )

        # Service-by-service breakdown
        report_lines.append("🔍 SERVICE VALIDATION BREAKDOWN:")

        for service_name, summary in self.service_summaries.items():
            status_emoji = "✅" if summary.failed_tests == 0 else "❌"
            report_lines.extend(
                [
                    f"{status_emoji} {service_name}:",
                    f"    Tests: {summary.passed_tests}/{summary.total_tests} passed ({summary.pass_rate:.1f}%)",
                    f"    Duration: {summary.total_duration:.2f}s",
                ]
            )

            if summary.errors:
                report_lines.append("    Errors:")
                for error in summary.errors[:3]:  # Show first 3 errors
                    report_lines.append(f"      • {error}")
                if len(summary.errors) > 3:
                    report_lines.append(
                        f"      ... and {len(summary.errors) - 3} more errors"
                    )

            report_lines.append("")

        # Performance insights
        if total_tests > 0:
            report_lines.extend(
                [
                    "⚡ PERFORMANCE INSIGHTS:",
                    f"  Fastest Service: {min(self.service_summaries.values(), key=lambda s: s.total_duration / max(s.total_tests, 1)).service_name}",
                    f"  Slowest Service: {max(self.service_summaries.values(), key=lambda s: s.total_duration / max(s.total_tests, 1)).service_name}",
                    "",
                ]
            )

        # Recommendations
        report_lines.extend(
            [
                "💡 RECOMMENDATIONS:",
            ]
        )

        failing_services = [
            s.service_name
            for s in self.service_summaries.values()
            if s.failed_tests > 0
        ]
        if failing_services:
            report_lines.append(
                f"  • Fix failing tests in: {', '.join(failing_services)}"
            )

        slow_services = [
            s.service_name
            for s in self.service_summaries.values()
            if s.total_tests > 0 and (s.total_duration / s.total_tests) > 0.1
        ]
        if slow_services:
            report_lines.append(
                f"  • Optimize slow tests in: {', '.join(slow_services)}"
            )

        if overall_pass_rate == 100:
            report_lines.append("  • Excellent! All validation tests are passing.")
        elif overall_pass_rate >= 90:
            report_lines.append("  • Good coverage. Address remaining test failures.")
        else:
            report_lines.append(
                "  • Significant issues detected. Priority fix required."
            )

        report_lines.extend(["", "=" * 60, "🎯 VALIDATION COMPLETE"])

        return "\n".join(report_lines)

    def save_report(self, filename: str) -> None:
        """Save validation report to file."""
        report = self.generate_report()
        with open(filename, "w") as f:
            f.write(report)
        print(f"📄 Validation report saved to: {filename}")


class TestComprehensiveValidation:
    """Pytest test class for comprehensive validation testing."""

    def test_all_service_validations_sequential(self):
        """Test all service validations sequentially."""
        runner = ComprehensiveValidationRunner()
        summaries = runner.run_all_validations()

        print(runner.generate_report())

        # Assert that all critical services pass
        critical_services = ["Artifacts Service", "Cache Service", "Session Service"]
        for service_name in critical_services:
            if service_name in summaries:
                summary = summaries[service_name]
                assert (
                    summary.pass_rate >= 90
                ), f"{service_name} has low pass rate: {summary.pass_rate:.1f}%"

    def test_all_service_validations_parallel(self):
        """Test all service validations in parallel."""
        runner = ComprehensiveValidationRunner()
        summaries = runner.run_parallel_validations()

        print(runner.generate_report())

        # Assert overall quality standards
        total_tests = sum(s.total_tests for s in summaries.values())
        total_passed = sum(s.passed_tests for s in summaries.values())
        overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        assert (
            overall_pass_rate >= 85
        ), f"Overall pass rate too low: {overall_pass_rate:.1f}%"
        assert total_tests >= 50, f"Too few tests: {total_tests}"

    def test_validation_performance(self):
        """Test that validation tests complete within reasonable time."""
        runner = ComprehensiveValidationRunner()

        start_time = time.time()
        runner.run_all_validations()
        total_time = time.time() - start_time

        # All validation tests should complete within 30 seconds
        assert total_time < 30, f"Validation tests too slow: {total_time:.2f}s"

        # Average test time should be reasonable
        total_tests = sum(s.total_tests for s in runner.service_summaries.values())
        if total_tests > 0:
            avg_test_time = total_time / total_tests
            assert (
                avg_test_time < 0.5
            ), f"Average test time too slow: {avg_test_time:.3f}s"

    def test_validation_coverage_completeness(self):
        """Test that validation coverage is comprehensive."""
        runner = ComprehensiveValidationRunner()
        summaries = runner.run_all_validations()

        # Ensure all expected services are tested
        expected_services = {
            "Artifacts Service",
            "Cache Service",
            "Session Service",
            "Composition Service",
            "Orchestration Service",
        }

        tested_services = set(summaries.keys())
        missing_services = expected_services - tested_services

        assert (
            not missing_services
        ), f"Missing validation for services: {missing_services}"

        # Ensure reasonable test coverage per service
        for service_name, summary in summaries.items():
            assert (
                summary.total_tests >= 5
            ), f"{service_name} has too few tests: {summary.total_tests}"

    def test_cross_service_integration_patterns(self):
        """Test validation patterns that span multiple services."""
        # This would test integration scenarios where multiple services interact

        # Example: Artifacts service storing documents about cache service operations
        # Example: Session service coordinating composition and orchestration services
        # Example: Cross-service validation consistency

        # For now, verify that individual service validations are comprehensive
        runner = ComprehensiveValidationRunner()
        summaries = runner.run_all_validations()

        # Verify that services with interdependencies have good coverage
        interdependent_services = ["Composition Service", "Orchestration Service"]
        for service_name in interdependent_services:
            if service_name in summaries:
                summary = summaries[service_name]
                # Services with interdependencies need higher coverage
                assert (
                    summary.pass_rate >= 95
                ), f"Interdependent service {service_name} needs higher pass rate"


def run_comprehensive_validation_suite():
    """Standalone function to run comprehensive validation suite."""
    print("🎯 KHIVE COMPREHENSIVE VALIDATION SUITE")
    print("=" * 60)

    runner = ComprehensiveValidationRunner()

    # Run validations
    start_time = time.time()
    summaries = runner.run_all_validations()
    total_time = time.time() - start_time

    # Generate and display report
    report = runner.generate_report()
    print("\n" + report)

    # Save report to file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_filename = f"validation_report_{timestamp}.txt"
    runner.save_report(report_filename)

    # Return summary for programmatic use
    return {
        "summaries": summaries,
        "total_time": total_time,
        "report": report,
        "report_file": report_filename,
    }


if __name__ == "__main__":
    # Run the comprehensive validation suite
    result = run_comprehensive_validation_suite()

    # Exit with appropriate code
    total_tests = sum(s.total_tests for s in result["summaries"].values())
    total_passed = sum(s.passed_tests for s in result["summaries"].values())

    if total_passed == total_tests:
        print("\n🎉 All validation tests passed!")
        exit(0)
    else:
        print(f"\n⚠️  {total_tests - total_passed} validation tests failed!")
        exit(1)
