# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Data models for the Git Service.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GitAction(str, Enum):
    """Available actions for the Git service."""

    GENERATE_COMMIT_MESSAGE = "generate_commit_message"
    GENERATE_PR_DESCRIPTION = "generate_pr_description"
    GENERATE_CHANGELOG = "generate_changelog"
    GENERATE_RELEASE_NOTES = "generate_release_notes"
    SUGGEST_REVIEWERS = "suggest_reviewers"
    ANALYZE_DIFF = "analyze_diff"
    SUGGEST_BRANCH_NAME = "suggest_branch_name"
    GENERATE_REVIEW_COMMENTS = "generate_review_comments"


class ChangelogFormat(str, Enum):
    """Changelog format options."""

    MARKDOWN = "markdown"
    CONVENTIONAL = "conventional"
    KEEP_A_CHANGELOG = "keep_a_changelog"


class SemverBumpType(str, Enum):
    """Semantic version bump types."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    NONE = "none"


# Request parameter models
class CommitMessageParams(BaseModel):
    """Parameters for generating a commit message."""

    diff: Optional[str] = Field(None, description="Git diff content")
    file_changes: Optional[str] = Field(
        None, description="File change summary from git"
    )
    conventional: bool = Field(True, description="Use conventional commit format")
    context: Optional[str] = Field(
        None, description="Additional context for the commit"
    )
    include_stats: bool = Field(False, description="Include file change statistics")
    closes_issues: Optional[List[str]] = Field(None, description="Issue IDs to close")
    co_authors: Optional[List[str]] = Field(None, description="Co-author emails")
    repo_path: Optional[Path] = Field(Path.cwd(), description="Repository path")


class PRDescriptionParams(BaseModel):
    """Parameters for generating a PR description."""

    title: Optional[str] = Field(None, description="PR title")
    source_branch: Optional[str] = Field(None, description="Source branch name")
    target_branch: Optional[str] = Field(None, description="Target branch name")
    commits: Optional[List[str]] = Field(None, description="List of commit messages")
    diff_summary: Optional[str] = Field(None, description="Summary of changes")
    template: Optional[str] = Field(None, description="PR template to follow")
    include_checklist: bool = Field(True, description="Include standard checklist")
    repo_path: Optional[Path] = Field(Path.cwd(), description="Repository path")


class ChangelogParams(BaseModel):
    """Parameters for generating a changelog."""

    from_ref: Optional[str] = Field(None, description="Starting git ref (tag/commit)")
    to_ref: Optional[str] = Field("HEAD", description="Ending git ref")
    version: Optional[str] = Field(None, description="Version number for changelog")
    format: ChangelogFormat = Field(
        ChangelogFormat.MARKDOWN, description="Output format"
    )
    include_author: bool = Field(False, description="Include commit authors")
    include_date: bool = Field(True, description="Include commit dates")
    group_by_type: bool = Field(True, description="Group commits by type")
    commit_url_template: Optional[str] = Field(
        None, description="URL template for commit links (use {hash} placeholder)"
    )
    repo_path: Optional[Path] = Field(Path.cwd(), description="Repository path")


class ReleaseNotesParams(BaseModel):
    """Parameters for generating release notes."""

    version: str = Field(..., description="Version being released")
    from_version: Optional[str] = Field(None, description="Previous version")
    to_version: Optional[str] = Field("HEAD", description="Current version ref")
    highlights: Optional[List[str]] = Field(
        None, description="Key highlights to feature"
    )
    breaking_changes: Optional[List[str]] = Field(None, description="Breaking changes")
    include_contributors: bool = Field(True, description="Include contributor list")
    include_stats: bool = Field(True, description="Include statistics")
    include_upgrade_instructions: bool = Field(
        True, description="Include upgrade guide"
    )
    repo_path: Optional[Path] = Field(Path.cwd(), description="Repository path")


class AnalyzeDiffParams(BaseModel):
    """Parameters for analyzing a diff."""

    diff: Optional[str] = Field(None, description="Git diff content")
    base_ref: Optional[str] = Field(None, description="Base reference")
    head_ref: Optional[str] = Field(None, description="Head reference")
    staged: bool = Field(True, description="Analyze staged changes")
    include_ai_summary: bool = Field(True, description="Include AI-generated summary")
    repo_path: Optional[Path] = Field(Path.cwd(), description="Repository path")


class SuggestBranchParams(BaseModel):
    """Parameters for suggesting a branch name."""

    description: str = Field(..., description="Description of the work")
    branch_prefix: Optional[str] = Field(
        "feature", description="Branch prefix (feature/fix/chore/etc)"
    )
    max_length: int = Field(50, description="Maximum branch name length")


class ReviewCommentsParams(BaseModel):
    """Parameters for generating review comments."""

    diff: Optional[str] = Field(None, description="Code diff to review")
    pr_number: Optional[int] = Field(None, description="PR number to fetch diff")
    focus_areas: Optional[List[str]] = Field(
        None, description="Specific areas to focus on (security, performance, etc)"
    )
    severity_threshold: Optional[str] = Field(
        None,
        description="Minimum severity to report (info/suggestion/warning/critical)",
    )
    repo_path: Optional[Path] = Field(Path.cwd(), description="Repository path")


# Request/Response models
class GitRequest(BaseModel):
    """Request to the Git service."""

    action: GitAction = Field(..., description="The action to perform")
    params: Any = Field(..., description="Parameters for the action")

    def model_post_init(self, __context):
        """Validate params match the action."""
        # Map actions to their parameter types
        param_types = {
            GitAction.GENERATE_COMMIT_MESSAGE: CommitMessageParams,
            GitAction.GENERATE_PR_DESCRIPTION: PRDescriptionParams,
            GitAction.GENERATE_CHANGELOG: ChangelogParams,
            GitAction.GENERATE_RELEASE_NOTES: ReleaseNotesParams,
            GitAction.ANALYZE_DIFF: AnalyzeDiffParams,
            GitAction.SUGGEST_BRANCH_NAME: SuggestBranchParams,
            GitAction.GENERATE_REVIEW_COMMENTS: ReviewCommentsParams,
        }

        # Validate and convert params if needed
        if self.action in param_types:
            expected_type = param_types[self.action]
            if not isinstance(self.params, expected_type):
                if isinstance(self.params, dict):
                    self.params = expected_type(**self.params)
                else:
                    self.params = expected_type.model_validate(self.params)


class GitResponse(BaseModel):
    """Response from the Git service."""

    success: bool = Field(..., description="Whether the operation succeeded")
    action_performed: Optional[GitAction] = Field(
        None, description="The action that was performed"
    )
    content: Optional[Dict[str, Any]] = Field(
        None, description="The response content (varies by action)"
    )
    error: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "action_performed": "generate_commit_message",
                    "content": {
                        "message": "feat(auth): add OAuth2 support",
                        "type": "feat",
                        "scope": "auth",
                        "breaking_change": False,
                    },
                },
                {
                    "success": True,
                    "action_performed": "analyze_diff",
                    "content": {
                        "files_changed": 5,
                        "insertions": 150,
                        "deletions": 30,
                        "languages": ["Python", "TypeScript"],
                        "suggested_version_bump": "minor",
                        "ai_summary": "Added new authentication module...",
                    },
                },
            ]
        }
