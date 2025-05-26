# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Data models for the agent-centric Git Service.

Designed from scratch for AI agents - no legacy constraints.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set

from pydantic import BaseModel, Field


# --- Core Concepts ---


class WorkIntent(str, Enum):
    """What the agent wants to accomplish."""

    # Development flow
    EXPLORE = "explore"  # Understand codebase state
    IMPLEMENT = "implement"  # Save implementation work
    COLLABORATE = "collaborate"  # Share work for feedback
    INTEGRATE = "integrate"  # Merge changes from others
    RELEASE = "release"  # Publish a version

    # Meta operations
    UNDERSTAND = "understand"  # Analyze what happened
    UNDO = "undo"  # Revert/fix mistakes
    ORGANIZE = "organize"  # Clean up branches/commits


class WorkContext(BaseModel):
    """Rich context about what the agent is working on."""

    # Current focus
    task_description: Optional[str] = None
    related_issues: List[str] = Field(default_factory=list)

    # Knowledge sources
    research_findings: Dict[str, Any] = Field(default_factory=dict)
    design_decisions: List[str] = Field(default_factory=list)

    # Constraints
    requirements: List[str] = Field(default_factory=list)
    avoid: List[str] = Field(default_factory=list)

    # Progress tracking
    completed_steps: List[str] = Field(default_factory=list)
    next_todos: List[str] = Field(default_factory=list)

    # Evidence trail
    search_ids: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)


class CodeInsight(BaseModel):
    """Semantic understanding of code changes."""

    # What changed
    primary_changes: List[str]  # Main modifications in plain language
    side_effects: List[str]  # Indirect impacts

    # Quality indicators
    adds_tests: bool
    updates_docs: bool
    follows_patterns: bool
    introduces_tech_debt: bool

    # Semantic classification
    change_type: Literal["feature", "fix", "refactor", "perf", "style", "docs"]
    complexity: Literal["trivial", "simple", "moderate", "complex"]
    risk_level: Literal["safe", "low", "medium", "high"]

    # Dependencies
    affects_public_api: bool
    requires_migration: bool
    breaks_compatibility: bool


class CollaborationContext(BaseModel):
    """Information about collaboration state."""

    # Team awareness
    active_reviewers: List[str] = Field(default_factory=list)
    blocked_by: List[str] = Field(default_factory=list)
    blocking: List[str] = Field(default_factory=list)

    # Review state
    feedback_received: List[Dict[str, str]] = Field(default_factory=list)
    feedback_addressed: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)

    # Social signals
    reviewer_expertise: Dict[str, List[str]] = Field(default_factory=dict)
    optimal_review_time: Optional[str] = None
    team_availability: Dict[str, str] = Field(default_factory=dict)


# --- Request Model ---


class GitRequest(BaseModel):
    """Single, unified request model for all git operations."""

    # Natural language is primary
    request: str = Field(
        ...,
        description="What you want to do, in your own words",
        examples=[
            "I've implemented the OAuth feature and need feedback",
            "What changed while I was working on this?",
            "Help me understand the recent commits in the auth module",
        ],
    )

    # Rich context
    context: Optional[WorkContext] = None

    # Identity & continuity
    agent_id: Optional[str] = None
    conversation_id: Optional[str] = None

    # Preferences
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific preferences",
        examples=[
            {
                "commit_style": "detailed",
                "auto_stage_tests": True,
                "require_test_coverage": True,
            }
        ],
    )


# --- State Understanding ---


class FileUnderstanding(BaseModel):
    """Deep understanding of a file's role and changes."""

    path: Path
    role: Literal["core", "test", "config", "docs", "example", "generated"]

    # Change analysis
    change_summary: str  # What changed in plain language
    change_magnitude: Literal["cosmetic", "minor", "significant", "major"]

    # Relationships
    tests_this: List[Path] = Field(default_factory=list)
    tested_by: List[Path] = Field(default_factory=list)
    depends_on: List[Path] = Field(default_factory=list)

    # Quality signals
    has_todo_comments: bool = False
    has_fixme_comments: bool = False
    follows_conventions: bool = True


class RepositoryUnderstanding(BaseModel):
    """Complete understanding of repository state."""

    # Work context
    current_branch: str
    branch_purpose: str  # Inferred or declared purpose
    work_phase: Literal[
        "exploring", "implementing", "testing", "polishing", "reviewing"
    ]

    # Change analysis
    files_changed: List[FileUnderstanding]
    code_insights: CodeInsight

    # Collaboration state
    collaboration: CollaborationContext

    # Health indicators
    can_build: bool
    tests_passing: bool
    lint_clean: bool

    # Recommendations
    recommended_actions: List[str]
    potential_issues: List[str]


# --- Response Model ---


class GitResponse(BaseModel):
    """Single, unified response model focused on agent needs."""

    # What happened
    understood_as: str  # How we interpreted the request
    actions_taken: List[str]  # What we did in plain language

    # Current state
    repository_state: RepositoryUnderstanding

    # What's next
    recommendations: List[Recommendation]

    # Knowledge gained
    learned: Dict[str, Any] = Field(
        default_factory=dict, description="New information discovered during operations"
    )

    # Conversation continuity
    conversation_id: str
    follow_up_prompts: List[str]  # Suggested follow-up questions


class Recommendation(BaseModel):
    """A recommended next action with full context."""

    action: str  # What to do in plain language
    reason: str  # Why this makes sense now
    impact: str  # What this will accomplish

    urgency: Literal["whenever", "soon", "now", "urgent"]
    effort: Literal["trivial", "quick", "moderate", "substantial"]

    # How to do it
    example_request: str
    prerequisites: List[str] = Field(default_factory=list)

    # Consequences
    will_enable: List[str] = Field(default_factory=list)
    will_block: List[str] = Field(default_factory=list)


# --- Workflow Types ---


class ImplementationFlow(BaseModel):
    """Workflow for implementation tasks."""

    # Planning
    task: str
    approach: List[str]
    success_criteria: List[str]

    # Progress
    started_at: datetime
    checkpoints: List[Dict[str, Any]] = Field(default_factory=list)

    # Quality gates
    has_tests: bool = False
    has_docs: bool = False
    peer_reviewed: bool = False

    def add_checkpoint(self, description: str, code_insight: CodeInsight):
        """Record progress checkpoint."""
        self.checkpoints.append({
            "time": datetime.utcnow(),
            "description": description,
            "insight": code_insight,
            "cumulative_changes": len(self.checkpoints) + 1,
        })


class CollaborationFlow(BaseModel):
    """Workflow for collaboration."""

    # Sharing context
    pr_title: str
    pr_body: str

    # Review optimization
    suggested_reviewers: List[str]
    review_focus_areas: List[str]
    expected_feedback_types: List[str]

    # Iteration tracking
    review_rounds: int = 0
    total_comments: int = 0
    resolved_comments: int = 0


class ReleaseFlow(BaseModel):
    """Workflow for releases."""

    version: str
    release_type: Literal["major", "minor", "patch", "preview"]

    # Content
    highlights: List[str]
    breaking_changes: List[str]

    # Automation
    auto_generated_notes: str
    manual_notes: Optional[str] = None

    # Distribution
    publish_targets: List[str] = Field(default_factory=list)


# --- Intelligence Models ---


class PatternRecognition(BaseModel):
    """Recognized patterns in the codebase."""

    # Coding patterns
    common_patterns: List[str]
    anti_patterns: List[str]

    # Workflow patterns
    typical_pr_size: int
    typical_review_time: str
    typical_iteration_count: int

    # Team patterns
    expertise_map: Dict[str, List[str]]
    collaboration_graph: Dict[str, List[str]]


class QualityAssessment(BaseModel):
    """Assessment of code quality."""

    # Objective metrics
    test_coverage: float
    documentation_coverage: float
    complexity_score: float

    # Subjective assessments
    readability: Literal["excellent", "good", "fair", "poor"]
    maintainability: Literal["excellent", "good", "fair", "poor"]
    consistency: Literal["excellent", "good", "fair", "poor"]

    # Specific issues
    issues: List[QualityIssue]

    # Improvements
    quick_wins: List[str]
    long_term_improvements: List[str]


class QualityIssue(BaseModel):
    """A specific quality issue."""

    type: Literal["bug_risk", "security", "performance", "maintainability", "style"]
    severity: Literal["info", "warning", "error", "critical"]
    location: str
    description: str
    suggestion: str


# --- Session Model ---


class GitSession(BaseModel):
    """Stateful session maintaining context across operations."""

    id: str
    agent_id: str
    started_at: datetime
    last_activity: datetime

    # Accumulated understanding
    repository_knowledge: Dict[str, Any] = Field(default_factory=dict)
    learned_patterns: Optional[PatternRecognition] = None

    # Active workflows
    implementation_flow: Optional[ImplementationFlow] = None
    collaboration_flow: Optional[CollaborationFlow] = None
    release_flow: Optional[ReleaseFlow] = None

    # History
    request_history: List[str] = Field(default_factory=list)
    action_history: List[str] = Field(default_factory=list)

    # Preferences learned
    inferred_preferences: Dict[str, Any] = Field(default_factory=dict)

    def add_request(self, request: str):
        """Track request for context."""
        self.request_history.append(request)
        self.last_activity = datetime.utcnow()

    def add_action(self, action: str):
        """Track action taken."""
        self.action_history.append(action)
        self.last_activity = datetime.utcnow()


# --- Error Handling ---


class GitError(BaseModel):
    """Rich error information for agent understanding."""

    error_type: str
    description: str

    # Context
    what_failed: str
    why_failed: str

    # Recovery
    can_retry: bool
    fix_suggestions: List[str]
    workarounds: List[str]

    # Learning
    prevention_tips: List[str]
