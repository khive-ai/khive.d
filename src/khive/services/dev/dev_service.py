# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Khive Development Service - Intelligent development operations.

This service provides unified development capabilities that intelligently
route to the appropriate tools based on intent, not forcing agents to
choose specific commands.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from khive.cli.khive_ci import CICommand
from khive.cli.khive_fmt import FormatCommand
from khive.cli.khive_init import InitCommand
from khive.services.dev.parts import (
    DevInsight,
    DevIssue,
    DevMode,
    DevRequest,
    DevResponse,
    IssueSeverity,
    IssueType,
    ProjectHealth,
    StackType,
    TestResult,
)
from khive.types import Service
from khive.utils import get_project_root


class DevServiceGroup(Service):
    """
    Unified development service that intelligently handles all dev operations.

    Instead of making agents choose between init/format/test commands,
    this service understands intent and executes the right operations.
    """

    def __init__(self):
        """Initialize the development service."""
        self._init_cmd = None
        self._fmt_cmd = None
        self._ci_cmd = None
        self._project_cache = {}

    async def handle_request(self, request: DevRequest) -> DevResponse:
        """
        Handle development request with intelligent routing.

        Analyzes intent and context to determine the best approach.
        """
        start_time = time.time()

        try:
            # Parse request if needed
            if isinstance(request, str):
                request = DevRequest.model_validate_json(request)
            elif isinstance(request, dict):
                request = DevRequest.model_validate(request)

            # Determine project root
            project_root = (
                Path(request.project_root)
                if request.project_root
                else get_project_root()
            )

            # Detect mode if not specified
            mode = request.mode or await self._detect_mode(request.intent, project_root)

            # Route to appropriate handler
            if mode == DevMode.SETUP:
                response = await self._handle_setup(request, project_root)
            elif mode == DevMode.QUICK_FIX:
                response = await self._handle_quick_fix(request, project_root)
            elif mode == DevMode.FULL_CHECK:
                response = await self._handle_full_check(request, project_root)
            elif mode == DevMode.DIAGNOSTIC:
                response = await self._handle_diagnostic(request, project_root)
            elif mode == DevMode.MAINTENANCE:
                response = await self._handle_maintenance(request, project_root)
            else:
                response = await self._handle_full_check(request, project_root)

            # Add duration
            response.duration = time.time() - start_time

            # Generate project health if we have enough data
            if response.issues_found or response.test_results:
                response.project_health = self._assess_project_health(response)

            return response

        except Exception as e:
            return DevResponse(
                success=False,
                summary=f"Development operation failed: {e!s}",
                mode_used=request.mode or DevMode.FULL_CHECK,
                error=str(e),
                duration=time.time() - start_time,
            )

    async def _detect_mode(self, intent: str, project_root: Path) -> DevMode:
        """Intelligently detect the best mode based on intent and project state."""
        intent_lower = intent.lower()

        # Setup patterns
        setup_patterns = [
            r"set\s*up",
            r"init",
            r"create",
            r"new project",
            r"bootstrap",
            r"scaffold",
            r"start",
        ]
        if any(re.search(pattern, intent_lower) for pattern in setup_patterns):
            return DevMode.SETUP

        # Quick fix patterns
        fix_patterns = [
            r"fix",
            r"format",
            r"lint",
            r"clean.*code",
            r"style",
            r"prettier",
            r"black",
        ]
        if any(re.search(pattern, intent_lower) for pattern in fix_patterns):
            return DevMode.QUICK_FIX

        # Diagnostic patterns
        diagnostic_patterns = [
            r"diagnos",
            r"analyz",
            r"what.*wrong",
            r"debug",
            r"investig",
            r"why.*fail",
            r"understand",
        ]
        if any(re.search(pattern, intent_lower) for pattern in diagnostic_patterns):
            return DevMode.DIAGNOSTIC

        # Maintenance patterns
        maintenance_patterns = [
            r"clean",
            r"optimiz",
            r"maintain",
            r"upgrade",
            r"update.*dep",
            r"refactor",
        ]
        if any(re.search(pattern, intent_lower) for pattern in maintenance_patterns):
            return DevMode.MAINTENANCE

        # Check project state for context
        has_tests = (project_root / "tests").exists() or (project_root / "src").exists()
        has_ci_config = (project_root / ".khive" / "ci.toml").exists()

        # Default to full check for established projects
        if has_tests or has_ci_config:
            return DevMode.FULL_CHECK

        # Default to setup for new projects
        return DevMode.SETUP

    async def _handle_setup(
        self, request: DevRequest, project_root: Path
    ) -> DevResponse:
        """Handle project setup and initialization."""
        actions_taken = []
        insights = []
        issues = []

        # Detect what needs to be set up
        detected_stacks = self._detect_project_stacks(project_root)

        if not detected_stacks and request.stack == StackType.AUTO:
            return DevResponse(
                success=False,
                summary="No project configuration found. Please specify a stack type.",
                mode_used=DevMode.SETUP,
                insights=[
                    DevInsight(
                        category="setup",
                        summary="Empty project detected",
                        details="No pyproject.toml, package.json, or Cargo.toml found",
                        impact="Cannot auto-detect project type",
                    )
                ],
                next_steps=[
                    "Create a project configuration file (pyproject.toml for Python, package.json for Node, etc.)",
                    "Or specify the stack explicitly in your request",
                ],
            )

        # Initialize the init command
        if self._init_cmd is None:
            self._init_cmd = InitCommand()

        # Prepare arguments
        args = ["--project-root", str(project_root), "--json-output"]

        if request.stack != StackType.AUTO:
            # Map to init command's expected values
            stack_map = {
                StackType.PYTHON: "uv",
                StackType.NODE: "pnpm",
                StackType.RUST: "cargo",
            }
            if request.stack in stack_map:
                args.extend(["--stack", stack_map[request.stack]])

        # Execute initialization
        try:
            parsed_args = self._init_cmd.parser.parse_args(args)
            config = self._init_cmd._create_config(parsed_args)
            result = self._init_cmd._execute(parsed_args, config)

            # Parse the result
            if result.status == "success":
                actions_taken.append("Project dependencies initialized")

                # Extract insights from initialization
                for step in result.data.get("steps", []):
                    if step["status"] == "OK":
                        actions_taken.append(
                            f"✓ {step['name']}: {step.get('message', 'completed')}"
                        )
                    elif step["status"] == "SKIPPED":
                        insights.append(
                            DevInsight(
                                category="setup",
                                summary=f"{step['name']} was skipped",
                                details=step.get("message"),
                                confidence=1.0,
                            )
                        )

                # Add setup insights
                insights.append(
                    DevInsight(
                        category="setup",
                        summary="Project successfully initialized",
                        details=f"Set up {len(detected_stacks)} stack(s): {', '.join(detected_stacks)}",
                        impact="Ready for development",
                        confidence=1.0,
                    )
                )

                return DevResponse(
                    success=True,
                    summary="Project initialized successfully",
                    mode_used=DevMode.SETUP,
                    actions_taken=actions_taken,
                    insights=insights,
                    next_steps=[
                        "Run tests to verify setup",
                        "Configure your IDE/editor",
                        "Set up pre-commit hooks if needed",
                    ],
                )
            else:
                return DevResponse(
                    success=False,
                    summary=f"Initialization failed: {result.message}",
                    mode_used=DevMode.SETUP,
                    error=result.message,
                )

        except Exception as e:
            return DevResponse(
                success=False,
                summary=f"Setup failed: {e!s}",
                mode_used=DevMode.SETUP,
                error=str(e),
            )

    async def _handle_quick_fix(
        self, request: DevRequest, project_root: Path
    ) -> DevResponse:
        """Handle quick fixes like formatting and linting."""
        if self._fmt_cmd is None:
            self._fmt_cmd = FormatCommand()

        actions_taken = []
        issues_found = []
        issues_fixed = 0

        # First check formatting
        check_args = ["--project-root", str(project_root), "--check", "--json-output"]

        try:
            parsed_args = self._fmt_cmd.parser.parse_args(check_args)
            config = self._fmt_cmd._create_config(parsed_args)
            check_result = self._fmt_cmd._execute(parsed_args, config)

            # Analyze what needs fixing
            if (
                check_result.status == "failure"
                or check_result.status == "check_failed"
            ):
                for stack in check_result.data.get("stacks_processed", []):
                    if stack["status"] in ["check_failed", "error"]:
                        issues_found.append(
                            DevIssue(
                                type=IssueType.FORMATTING,
                                severity=IssueSeverity.MEDIUM,
                                summary=f"Formatting issues in {stack['stack_name']} code",
                                details=stack.get("message"),
                                fix_available=True,
                                recommendation="Run formatter to fix",
                            )
                        )

                if request.fix_issues:
                    # Apply fixes
                    fix_args = ["--project-root", str(project_root), "--json-output"]
                    parsed_args = self._fmt_cmd.parser.parse_args(fix_args)
                    config = self._fmt_cmd._create_config(parsed_args)
                    fix_result = self._fmt_cmd._execute(parsed_args, config)

                    if fix_result.status == "success":
                        for stack in fix_result.data.get("stacks_processed", []):
                            if stack["status"] == "success":
                                files_fixed = stack.get("files_processed", 0)
                                issues_fixed += 1
                                actions_taken.append(
                                    f"Fixed formatting in {files_fixed} {stack['stack_name']} files"
                                )

                                # Mark issues as fixed
                                for issue in issues_found:
                                    if stack["stack_name"] in issue.summary:
                                        issue.fix_applied = True
            else:
                actions_taken.append("Code formatting check passed - no issues found")

            # Generate response
            summary = self._generate_fix_summary(issues_found, issues_fixed)

            return DevResponse(
                success=True,
                summary=summary,
                mode_used=DevMode.QUICK_FIX,
                issues_found=issues_found,
                issues_fixed=issues_fixed,
                actions_taken=actions_taken,
                insights=[
                    DevInsight(
                        category="quality",
                        summary="Code style consistency",
                        details=f"Found {len(issues_found)} formatting issues, fixed {issues_fixed}",
                        impact="Consistent code style improves readability and reduces conflicts",
                        confidence=1.0,
                    )
                ],
                next_steps=self._generate_next_steps_for_fixes(
                    issues_found, issues_fixed
                ),
            )

        except Exception as e:
            return DevResponse(
                success=False,
                summary=f"Quick fix failed: {e!s}",
                mode_used=DevMode.QUICK_FIX,
                error=str(e),
            )

    async def _handle_full_check(
        self, request: DevRequest, project_root: Path
    ) -> DevResponse:
        """Handle comprehensive checks including tests and formatting."""
        actions_taken = []
        all_issues = []
        test_results = []
        insights = []

        # Run formatting check
        fmt_response = await self._handle_quick_fix(
            DevRequest(
                intent="check formatting",
                fix_issues=False,
                project_root=str(project_root),
            ),
            project_root,
        )

        if fmt_response.issues_found:
            all_issues.extend(fmt_response.issues_found)
            actions_taken.append("Checked code formatting")

        # Run tests
        if self._ci_cmd is None:
            self._ci_cmd = CICommand()

        test_args = ["--project-root", str(project_root), "--json-output"]

        try:
            parsed_args = self._ci_cmd.parser.parse_args(test_args)
            config = self._ci_cmd._create_config(parsed_args)
            ci_result = await self._ci_cmd._execute_async(parsed_args, config)

            # Parse test results
            for test_run in ci_result.data.get("test_results", []):
                test_result = TestResult(
                    stack=StackType(test_run["test_type"]),
                    duration=test_run["duration"],
                )

                if test_run.get("summary"):
                    summary = test_run["summary"]
                    test_result.total_tests = summary.get("total", 0)
                    test_result.passed = summary.get("passed", 0)
                    test_result.failed = summary.get("failed", 0)
                    test_result.skipped = summary.get("skipped", 0)
                    test_result.coverage = summary.get("coverage_percent")

                    if summary.get("failures"):
                        test_result.failures = summary["failures"]

                test_results.append(test_result)

                # Create issues for test failures
                if test_result.failed > 0:
                    all_issues.append(
                        DevIssue(
                            type=IssueType.TEST_FAILURE,
                            severity=IssueSeverity.HIGH,
                            summary=f"{test_result.failed} {test_result.stack} tests failing",
                            details="\n".join(test_result.failures[:5]),
                            fix_available=False,
                            recommendation="Review test failures and fix the underlying issues",
                        )
                    )

                # Add insight about test coverage
                if test_result.coverage is not None:
                    coverage_status = (
                        "good" if test_result.coverage >= 80 else "needs improvement"
                    )
                    insights.append(
                        DevInsight(
                            category="testing",
                            summary=f"{test_result.stack} test coverage: {test_result.coverage:.1f}%",
                            details=f"Coverage is {coverage_status}",
                            impact="Higher coverage reduces bugs in production",
                            confidence=1.0,
                        )
                    )

            actions_taken.append(f"Ran tests for {len(test_results)} stack(s)")

        except Exception as e:
            all_issues.append(
                DevIssue(
                    type=IssueType.CONFIGURATION,
                    severity=IssueSeverity.HIGH,
                    summary="Failed to run tests",
                    details=str(e),
                    fix_available=False,
                    recommendation="Check test configuration and dependencies",
                )
            )

        # Generate comprehensive summary
        summary = self._generate_comprehensive_summary(all_issues, test_results)

        return DevResponse(
            success=len([i for i in all_issues if i.severity == IssueSeverity.CRITICAL])
            == 0,
            summary=summary,
            mode_used=DevMode.FULL_CHECK,
            issues_found=all_issues,
            test_results=test_results,
            actions_taken=actions_taken,
            insights=insights,
            next_steps=self._generate_comprehensive_next_steps(
                all_issues, test_results
            ),
        )

    async def _handle_diagnostic(
        self, request: DevRequest, project_root: Path
    ) -> DevResponse:
        """Handle deep diagnostic analysis of project issues."""
        # Run full check first
        full_check = await self._handle_full_check(request, project_root)

        # Enhance with detailed analysis
        insights = full_check.insights.copy()

        # Analyze patterns in issues
        if full_check.issues_found:
            issue_patterns = self._analyze_issue_patterns(full_check.issues_found)

            for pattern, details in issue_patterns.items():
                insights.append(
                    DevInsight(
                        category="quality",
                        summary=f"Pattern detected: {pattern}",
                        details=details["description"],
                        impact=details["impact"],
                        confidence=0.8,
                    )
                )

        # Analyze test patterns
        if full_check.test_results:
            test_insights = self._analyze_test_patterns(full_check.test_results)
            insights.extend(test_insights)

        # Add root cause analysis
        root_causes = self._identify_root_causes(
            full_check.issues_found, full_check.test_results
        )

        return DevResponse(
            success=full_check.success,
            summary=f"Diagnostic complete: {root_causes['summary']}",
            mode_used=DevMode.DIAGNOSTIC,
            issues_found=full_check.issues_found,
            test_results=full_check.test_results,
            insights=insights,
            actions_taken=full_check.actions_taken + ["Performed root cause analysis"],
            next_steps=root_causes["recommendations"],
        )

    async def _handle_maintenance(
        self, request: DevRequest, project_root: Path
    ) -> DevResponse:
        """Handle maintenance operations like cleanup and optimization."""
        actions_taken = []
        insights = []

        # For now, run formatting with fixes
        fmt_response = await self._handle_quick_fix(
            DevRequest(
                intent="fix all formatting",
                fix_issues=True,
                project_root=str(project_root),
            ),
            project_root,
        )

        actions_taken.extend(fmt_response.actions_taken)

        # Add maintenance-specific insights
        insights.append(
            DevInsight(
                category="quality",
                summary="Code maintenance completed",
                details="Formatting standardized across the project",
                impact="Reduces technical debt and improves consistency",
                confidence=1.0,
            )
        )

        # Suggest additional maintenance
        next_steps = [
            "Update dependencies to latest compatible versions",
            "Review and update documentation",
            "Check for deprecated API usage",
            "Run security audit on dependencies",
        ]

        return DevResponse(
            success=True,
            summary="Maintenance operations completed successfully",
            mode_used=DevMode.MAINTENANCE,
            issues_found=fmt_response.issues_found,
            issues_fixed=fmt_response.issues_fixed,
            actions_taken=actions_taken,
            insights=insights,
            next_steps=next_steps,
        )

    # Helper methods

    def _detect_project_stacks(self, project_root: Path) -> list[str]:
        """Detect which stacks are present in the project."""
        stacks = []

        if (project_root / "pyproject.toml").exists() or (
            project_root / "setup.py"
        ).exists():
            stacks.append("python")

        if (project_root / "package.json").exists():
            stacks.append("node")

        if (project_root / "Cargo.toml").exists():
            stacks.append("rust")

        if any(project_root.glob("*.ts")) or any(project_root.glob("*.tsx")):
            if "node" not in stacks:
                stacks.append("typescript")

        return stacks

    def _assess_project_health(self, response: DevResponse) -> ProjectHealth:
        """Calculate overall project health score."""
        score = 100.0
        strengths = []
        concerns = []

        # Deduct for issues
        for issue in response.issues_found:
            if issue.severity == IssueSeverity.CRITICAL:
                score -= 20
                concerns.append(f"Critical: {issue.summary}")
            elif issue.severity == IssueSeverity.HIGH:
                score -= 10
                concerns.append(f"High priority: {issue.summary}")
            elif issue.severity == IssueSeverity.MEDIUM:
                score -= 5
            else:
                score -= 2

        # Evaluate test results
        total_tests = 0
        total_passed = 0

        for test_result in response.test_results:
            total_tests += test_result.total_tests
            total_passed += test_result.passed

            if test_result.coverage and test_result.coverage >= 80:
                strengths.append(
                    f"Good test coverage in {test_result.stack} ({test_result.coverage:.0f}%)"
                )
            elif test_result.coverage and test_result.coverage < 60:
                score -= 10
                concerns.append(
                    f"Low test coverage in {test_result.stack} ({test_result.coverage:.0f}%)"
                )

        if total_tests > 0:
            pass_rate = total_passed / total_tests
            if pass_rate == 1.0:
                strengths.append("All tests passing")
            elif pass_rate < 0.8:
                score -= 15

        # Determine status
        if score >= 80:
            status = "healthy"
        elif score >= 60:
            status = "needs_attention"
        else:
            status = "unhealthy"

        # Generate next steps based on concerns
        next_steps = []
        if any("test" in c.lower() for c in concerns):
            next_steps.append("Fix failing tests")
        if any("coverage" in c.lower() for c in concerns):
            next_steps.append("Improve test coverage")
        if response.issues_found:
            next_steps.append("Address code quality issues")

        return ProjectHealth(
            score=max(0, min(100, score)),
            status=status,
            strengths=strengths,
            concerns=concerns,
            next_steps=next_steps,
        )

    def _generate_fix_summary(self, issues: list[DevIssue], fixed: int) -> str:
        """Generate a summary for fix operations."""
        if not issues:
            return "Code quality check passed - no issues found"

        if fixed == len(issues):
            return f"Fixed all {fixed} code quality issues"
        elif fixed > 0:
            return f"Fixed {fixed} of {len(issues)} code quality issues"
        else:
            return f"Found {len(issues)} code quality issues that need attention"

    def _generate_comprehensive_summary(
        self, issues: list[DevIssue], test_results: list[TestResult]
    ) -> str:
        """Generate a comprehensive check summary."""
        parts = []

        # Test summary
        total_tests = sum(tr.total_tests for tr in test_results)
        failed_tests = sum(tr.failed for tr in test_results)

        if total_tests > 0:
            if failed_tests == 0:
                parts.append(f"All {total_tests} tests passed")
            else:
                parts.append(f"{failed_tests} of {total_tests} tests failed")

        # Issue summary
        if issues:
            critical = len([i for i in issues if i.severity == IssueSeverity.CRITICAL])
            high = len([i for i in issues if i.severity == IssueSeverity.HIGH])

            if critical > 0:
                parts.append(f"{critical} critical issues")
            if high > 0:
                parts.append(f"{high} high priority issues")
        else:
            parts.append("no quality issues")

        return "Project check complete: " + ", ".join(parts)

    def _generate_next_steps_for_fixes(
        self, issues: list[DevIssue], fixed: int
    ) -> list[str]:
        """Generate next steps after fix operations."""
        next_steps = []

        unfixed = len(issues) - fixed
        if unfixed > 0:
            next_steps.append(f"Manually fix {unfixed} remaining issues")

        if fixed > 0:
            next_steps.append("Run tests to ensure fixes didn't break anything")
            next_steps.append("Commit the formatting changes")

        next_steps.append("Set up pre-commit hooks to prevent future issues")

        return next_steps

    def _generate_comprehensive_next_steps(
        self, issues: list[DevIssue], test_results: list[TestResult]
    ) -> list[str]:
        """Generate next steps for comprehensive checks."""
        next_steps = []

        # Priority 1: Fix critical issues
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        if critical_issues:
            next_steps.append(f"Fix {len(critical_issues)} critical issues immediately")

        # Priority 2: Fix failing tests
        failing_stacks = [tr.stack for tr in test_results if tr.failed > 0]
        if failing_stacks:
            next_steps.append(f"Fix failing tests in: {', '.join(failing_stacks)}")

        # Priority 3: Improve coverage
        low_coverage = [tr for tr in test_results if tr.coverage and tr.coverage < 60]
        if low_coverage:
            next_steps.append("Improve test coverage to at least 60%")

        # Always useful
        if not next_steps:
            next_steps.append("Continue regular development")

        return next_steps[:3]  # Top 3 priorities

    def _analyze_issue_patterns(
        self, issues: list[DevIssue]
    ) -> dict[str, dict[str, str]]:
        """Identify patterns in issues."""
        patterns = {}

        # Count issue types
        type_counts = {}
        for issue in issues:
            type_counts[issue.type] = type_counts.get(issue.type, 0) + 1

        # Identify patterns
        if type_counts.get(IssueType.FORMATTING, 0) > 5:
            patterns["inconsistent_formatting"] = {
                "description": "Multiple formatting inconsistencies detected",
                "impact": "Makes code reviews harder and increases merge conflicts",
            }

        if type_counts.get(IssueType.TEST_FAILURE, 0) > 0:
            patterns["test_failures"] = {
                "description": "Tests are failing, indicating potential bugs",
                "impact": "Cannot safely deploy code with failing tests",
            }

        return patterns

    def _analyze_test_patterns(
        self, test_results: list[TestResult]
    ) -> list[DevInsight]:
        """Analyze patterns in test results."""
        insights = []

        # Check for consistent test coverage
        coverages = [tr.coverage for tr in test_results if tr.coverage is not None]
        if coverages:
            avg_coverage = sum(coverages) / len(coverages)
            if avg_coverage < 60:
                insights.append(
                    DevInsight(
                        category="testing",
                        summary="Low overall test coverage",
                        details=f"Average coverage is {avg_coverage:.1f}%, should be at least 80%",
                        impact="Increases risk of undetected bugs",
                        confidence=1.0,
                    )
                )

        # Check for slow tests
        slow_stacks = [tr.stack for tr in test_results if tr.duration > 60]
        if slow_stacks:
            insights.append(
                DevInsight(
                    category="performance",
                    summary="Slow test suites detected",
                    details=f"Tests taking too long in: {', '.join(slow_stacks)}",
                    impact="Slows down development velocity",
                    confidence=0.9,
                )
            )

        return insights

    def _identify_root_causes(
        self, issues: list[DevIssue], test_results: list[TestResult]
    ) -> dict[str, Any]:
        """Identify root causes of problems."""
        root_causes = {
            "summary": "No major root causes identified",
            "recommendations": [],
        }

        # Check for missing tools
        if any("not found" in issue.details for issue in issues if issue.details):
            root_causes["summary"] = "Missing development tools"
            root_causes["recommendations"].append(
                "Install all required development tools"
            )

        # Check for configuration issues
        elif any(issue.type == IssueType.CONFIGURATION for issue in issues):
            root_causes["summary"] = "Configuration issues detected"
            root_causes["recommendations"].append(
                "Review and fix project configuration"
            )

        # Check for systematic test failures
        elif sum(tr.failed for tr in test_results) > 5:
            root_causes["summary"] = (
                "Systematic test failures suggest recent breaking changes"
            )
            root_causes["recommendations"].append(
                "Review recent commits for breaking changes"
            )

        return root_causes

    async def close(self) -> None:
        """Clean up resources."""
        # Commands don't need explicit cleanup
