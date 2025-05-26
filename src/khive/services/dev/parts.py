# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Data models for Khive Development Service.

Provides structured request/response models for development operations,
focusing on actionable insights rather than raw command output.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class DevMode(str, Enum):
    """Development operation modes - auto-selected based on context."""

    QUICK_FIX = "quick_fix"  # Fast formatting/linting fixes
    FULL_CHECK = "full_check"  # Comprehensive CI/CD pipeline
    SETUP = "setup"  # Project initialization
    DIAGNOSTIC = "diagnostic"  # Deep analysis of issues
    MAINTENANCE = "maintenance"  # Cleanup and optimization


class StackType(str, Enum):
    """Supported development stacks."""

    PYTHON = "python"
    RUST = "rust"
    NODE = "node"
    DENO = "deno"
    ALL = "all"
    AUTO = "auto"  # Auto-detect from project


class DevRequest(BaseModel):
    """
    Unified request for development operations.

    Agents describe what they want to achieve, not which tool to use.
    """

    intent: str = Field(
        ...,
        description="What you want to achieve (e.g., 'fix code issues', 'run tests', 'setup project')",
    )

    context: str | None = Field(
        None, description="Additional context about the project or specific needs"
    )

    mode: DevMode | None = Field(
        None, description="Preferred operation mode (auto-detected if not provided)"
    )

    stack: StackType = Field(
        StackType.AUTO, description="Target stack (auto-detected by default)"
    )

    project_root: str | None = Field(
        None, description="Project directory (defaults to current/git root)"
    )

    time_budget: float = Field(
        30.0, description="Maximum seconds to spend on operation", ge=1.0, le=600.0
    )

    fix_issues: bool = Field(True, description="Automatically fix issues when possible")

    detailed_analysis: bool = Field(
        False, description="Provide detailed analysis of issues found"
    )


class IssueType(str, Enum):
    """Types of development issues."""

    FORMATTING = "formatting"
    LINTING = "linting"
    TYPE_ERROR = "type_error"
    TEST_FAILURE = "test_failure"
    MISSING_DEPENDENCY = "missing_dependency"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    PERFORMANCE = "performance"


class IssueSeverity(str, Enum):
    """Severity levels for issues."""

    CRITICAL = "critical"  # Blocks development/deployment
    HIGH = "high"  # Should fix soon
    MEDIUM = "medium"  # Should fix eventually
    LOW = "low"  # Nice to fix
    INFO = "info"  # Informational only


class DevIssue(BaseModel):
    """A single development issue found."""

    type: IssueType = Field(..., description="Type of issue")

    severity: IssueSeverity = Field(..., description="How serious this is")

    summary: str = Field(..., description="Brief description of the issue")

    details: str | None = Field(None, description="Detailed explanation with examples")

    location: str | None = Field(None, description="File and line number if applicable")

    fix_available: bool = Field(
        False, description="Whether this can be automatically fixed"
    )

    fix_applied: bool = Field(False, description="Whether a fix was applied")

    recommendation: str | None = Field(None, description="How to fix this manually")


class TestResult(BaseModel):
    """Results from test execution."""

    stack: StackType = Field(..., description="Which stack was tested")

    total_tests: int = Field(0, description="Total number of tests")

    passed: int = Field(0, description="Tests that passed")

    failed: int = Field(0, description="Tests that failed")

    skipped: int = Field(0, description="Tests that were skipped")

    duration: float = Field(0.0, description="Time taken in seconds")

    coverage: float | None = Field(
        None, description="Code coverage percentage if available"
    )

    failures: list[str] = Field(
        default_factory=list, description="List of failed test names"
    )


class ProjectHealth(BaseModel):
    """Overall project health assessment."""

    score: float = Field(..., description="Health score 0-100", ge=0.0, le=100.0)

    status: Literal["healthy", "needs_attention", "unhealthy"] = Field(
        ..., description="Overall status"
    )

    strengths: list[str] = Field(
        default_factory=list, description="What's working well"
    )

    concerns: list[str] = Field(
        default_factory=list, description="Areas needing attention"
    )

    next_steps: list[str] = Field(
        default_factory=list, description="Recommended actions"
    )


class DevInsight(BaseModel):
    """A development insight or finding."""

    category: Literal["setup", "quality", "testing", "performance", "security"] = Field(
        ..., description="Category of insight"
    )

    summary: str = Field(..., description="Brief insight")

    details: str | None = Field(None, description="Detailed explanation")

    impact: str | None = Field(None, description="Why this matters")

    confidence: float = Field(
        1.0, description="Confidence in this insight", ge=0.0, le=1.0
    )


class DevResponse(BaseModel):
    """
    Response providing actionable development insights.

    Focuses on what was achieved and what to do next,
    not raw command output.
    """

    success: bool = Field(..., description="Whether the operation succeeded")

    summary: str = Field(..., description="What was done in 1-2 sentences")

    mode_used: DevMode = Field(..., description="Which operation mode was used")

    issues_found: list[DevIssue] = Field(
        default_factory=list, description="Issues discovered during operation"
    )

    issues_fixed: int = Field(0, description="Number of issues automatically fixed")

    test_results: list[TestResult] = Field(
        default_factory=list, description="Test execution results if tests were run"
    )

    insights: list[DevInsight] = Field(
        default_factory=list, description="Key insights about the project"
    )

    project_health: ProjectHealth | None = Field(
        None, description="Overall project health assessment"
    )

    actions_taken: list[str] = Field(
        default_factory=list, description="What was actually done"
    )

    next_steps: list[str] = Field(
        default_factory=list, description="Recommended follow-up actions"
    )

    duration: float = Field(0.0, description="Total time taken in seconds")

    error: str | None = Field(None, description="Error message if success is False")


# Configuration models for specific operations
class InitConfig(BaseModel):
    """Configuration for project initialization."""

    stack: StackType = Field(StackType.AUTO)
    extra_dependencies: list[str] = Field(default_factory=list)
    setup_ci: bool = Field(True)
    setup_pre_commit: bool = Field(True)
    create_structure: bool = Field(True)


class FormatConfig(BaseModel):
    """Configuration for code formatting."""

    fix: bool = Field(True, description="Apply fixes vs just check")
    stacks: list[StackType] = Field(default_factory=list)
    strict: bool = Field(False, description="Use strict formatting rules")


class TestConfig(BaseModel):
    """Configuration for test execution."""

    coverage: bool = Field(True)
    parallel: bool = Field(True)
    fail_fast: bool = Field(False)
    verbose: bool = Field(False)
    timeout_per_test: float = Field(60.0)
