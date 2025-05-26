# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
MCP (Model Context Protocol) server for the Git Service.

Exposes git operations as tools that AI agents can use naturally.
"""

from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from khive.services.git import GitService, GitRequest, WorkContext

# Initialize MCP server
mcp = FastMCP(
    name="khive_git",
    instructions="""
    Natural language git operations designed for AI agents.
    
    You don't need to understand git commands - just express what you want to do:
    - "Save my progress" 
    - "Share this for review"
    - "What changed recently?"
    - "Help me understand the codebase"
    
    The service maintains context across operations and provides intelligent recommendations.
    """,
    tags=["git", "development", "collaboration", "version-control"],
)

# Global service instance (could be made per-session later)
git_service = GitService()


# Tool parameter models
class GitOperationParams(BaseModel):
    """Parameters for git operations."""

    request: str = Field(
        ...,
        description="What you want to do, in natural language",
        examples=[
            "Save my progress on the OAuth implementation",
            "I'm ready to share this for review",
            "What's the current state of the repository?",
        ],
    )

    # Optional context
    task_description: Optional[str] = Field(None, description="What you're working on")

    related_issues: Optional[List[str]] = Field(
        None, description="Issue numbers this relates to"
    )

    requirements: Optional[List[str]] = Field(
        None, description="Requirements or constraints for your work"
    )

    design_decisions: Optional[List[str]] = Field(
        None, description="Key decisions you've made"
    )

    # Session management
    session_id: Optional[str] = Field(
        None, description="Continue a previous git session"
    )


class GitAnalysisParams(BaseModel):
    """Parameters for analysis operations."""

    query: str = Field(
        ...,
        description="What you want to understand",
        examples=[
            "What changed in the auth module?",
            "Is the code ready for release?",
            "Show me the recent commit history",
        ],
    )

    focus: Optional[List[str]] = Field(
        None,
        description="Specific areas to analyze",
        examples=["quality", "security", "performance", "patterns"],
    )

    time_range: Optional[str] = Field(
        None,
        description="Time period to analyze",
        examples=["last week", "since yesterday", "past month"],
    )


# Main git operation tool
@mcp.tool(
    name="git_operation",
    description="Perform git operations using natural language",
    tags=["git", "save", "commit", "share", "collaborate"],
)
async def git_operation(params: GitOperationParams) -> Dict[str, Any]:
    """
    Perform git operations by expressing what you want to do.

    This tool handles the complete workflow - you don't need to worry about
    individual git commands like add, commit, push, etc.

    Returns:
        Complete information about what was done, current state, and recommendations
    """
    # Build context if provided
    context = None
    if any([
        params.task_description,
        params.related_issues,
        params.requirements,
        params.design_decisions,
    ]):
        context = WorkContext(
            task_description=params.task_description,
            related_issues=params.related_issues or [],
            requirements=params.requirements or [],
            design_decisions=params.design_decisions or [],
        )

    # Create request
    request = GitRequest(
        request=params.request,
        context=context,
        conversation_id=params.session_id,
        agent_id="mcp-agent",  # Could be customized
    )

    # Execute
    response = await git_service.handle_request(request)

    # Format response for MCP
    result = {
        "understood_as": response.understood_as,
        "actions_taken": response.actions_taken,
        "current_state": {
            "branch": response.repository_state.current_branch,
            "has_changes": response.repository_state.has_uncommitted_changes,
            "work_phase": response.repository_state.work_phase,
        },
        "recommendations": [
            {"action": rec.action, "reason": rec.reason, "how": rec.example_request}
            for rec in response.recommendations[:3]  # Top 3
        ],
        "session_id": response.conversation_id,
        "next_steps": response.follow_up_prompts[:3],
    }

    # Add any specific learned information
    if response.learned:
        result["details"] = response.learned

    return result


# Analysis tool
@mcp.tool(
    name="git_analyze",
    description="Analyze repository history, code quality, or patterns",
    tags=["git", "analysis", "history", "quality"],
)
async def git_analyze(params: GitAnalysisParams) -> Dict[str, Any]:
    """
    Understand what's happening in the repository.

    This tool provides insights about code changes, quality, patterns,
    and history to help you make informed decisions.

    Returns:
        Analysis results with actionable insights
    """
    # Build analysis request
    request_text = params.query
    if params.focus:
        request_text += f" focusing on {', '.join(params.focus)}"
    if params.time_range:
        request_text += f" in the {params.time_range}"

    request = GitRequest(request=request_text, agent_id="mcp-analyzer")

    # Execute
    response = await git_service.handle_request(request)

    # Extract analysis results
    result = {
        "analysis_type": response.understood_as,
        "findings": response.learned,
        "insights": [],
        "action_items": [],
    }

    # Add recommendations as action items
    for rec in response.recommendations:
        if rec.urgency in ["required", "urgent"]:
            result["action_items"].append({
                "action": rec.action,
                "priority": rec.urgency,
                "reason": rec.reason,
            })

    # Extract key insights
    if "quality" in response.learned:
        quality = response.learned["quality"]
        result["insights"].append(
            f"Code quality is {quality.get('readability', 'unknown')} "
            f"with {quality.get('test_coverage', 0):.0%} test coverage"
        )

    if "patterns" in response.learned:
        patterns = response.learned["patterns"]
        result["insights"].append(
            f"Common patterns: {', '.join(patterns.get('common_patterns', []))}"
        )

    return result


# Workflow status tool
@mcp.tool(
    name="git_status",
    description="Get current git repository status and workflow state",
    tags=["git", "status", "state"],
)
async def git_status() -> Dict[str, Any]:
    """
    Get a quick overview of the current repository state.

    Returns:
        Current branch, changes, work phase, and suggestions
    """
    request = GitRequest(request="What's the current state?", agent_id="mcp-status")

    response = await git_service.handle_request(request)

    return {
        "branch": response.repository_state.current_branch,
        "branch_purpose": response.repository_state.branch_purpose,
        "has_changes": response.repository_state.has_uncommitted_changes,
        "work_phase": response.repository_state.work_phase,
        "summary": response.repository_state.get_status_summary(),
        "suggested_action": response.recommendations[0].action
        if response.recommendations
        else None,
    }


# Collaboration helper
@mcp.tool(
    name="git_collaborate",
    description="Get help with collaboration workflows (PRs, reviews, etc)",
    tags=["git", "collaboration", "review", "pr"],
)
async def git_collaborate(
    action: str = Field(
        ...,
        description="What collaboration action to take",
        examples=[
            "create pr",
            "check review status",
            "address feedback",
            "find reviewers",
        ],
    ),
    context: Optional[str] = Field(
        None, description="Additional context for the action"
    ),
) -> Dict[str, Any]:
    """
    Help with collaboration workflows like creating PRs and handling reviews.

    Returns:
        Action results and next steps for collaboration
    """
    request_text = action
    if context:
        request_text += f" - {context}"

    request = GitRequest(request=request_text, agent_id="mcp-collaborator")

    response = await git_service.handle_request(request)

    result = {
        "action_taken": response.understood_as,
        "results": response.actions_taken,
        "collaboration_state": {
            "has_pr": response.repository_state.existing_pr is not None,
            "reviewers": response.repository_state.collaboration.active_reviewers,
            "feedback_items": len(
                response.repository_state.collaboration.feedback_received
            ),
            "next_steps": response.follow_up_prompts[:2],
        },
    }

    # Add PR details if created/updated
    if "pr_url" in response.learned:
        result["pr_details"] = {
            "url": response.learned["pr_url"],
            "number": response.learned.get("pr_number"),
            "reviewers": response.learned.get("reviewers", []),
        }

    return result


# Resource: Current git session
@mcp.resource(
    name="git_session", description="Current git workflow session information"
)
async def get_git_session() -> str:
    """
    Get information about the current git session.

    Sessions maintain context across multiple operations.
    """
    # This would retrieve session info from the service
    # For now, return a helpful message
    return """
    Git sessions maintain context across operations.
    
    When you perform a git operation, you receive a session_id.
    Use this session_id in subsequent operations to maintain context.
    
    This allows the service to:
    - Remember what you're working on
    - Generate better commit messages
    - Provide contextual recommendations
    - Track workflow progress
    """


# Prompt: Git workflow guide
@mcp.prompt(
    name="git_workflow", description="Guide for using git operations effectively"
)
async def git_workflow_prompt() -> str:
    """
    Get guidance on git workflows and best practices.
    """
    return """
    # Git Workflow Guide
    
    ## Basic Development Flow
    
    1. **Start Work**: "I'm starting work on [feature description]"
       - Creates/switches to appropriate branch
       - Sets up context for future operations
    
    2. **Save Progress**: "Save my progress" or "I've implemented [what you did]"
       - Intelligently stages relevant files
       - Creates semantic commit with context
    
    3. **Share for Review**: "Ready to share this for review"
       - Ensures changes are committed
       - Pushes to remote
       - Creates pull request
       - Assigns reviewers
    
    4. **Address Feedback**: "The reviewers suggested [feedback]"
       - Helps implement changes
       - Creates appropriate commits
       - Updates PR
    
    5. **Complete**: "All feedback addressed"
       - Ensures everything is ready
       - Helps with merge
    
    ## Best Practices
    
    - Provide context early (what you're working on, related issues)
    - Use the session_id to maintain context
    - Follow the recommendations provided
    - Be specific about what you've accomplished
    
    ## Examples
    
    - "I'm implementing OAuth authentication for issue #123"
    - "Added token refresh with 24-hour expiry"
    - "Fixed the security issues the reviewer mentioned"
    - "What's the status of my pull request?"
    - "Help me understand what changed in the auth module"
    """


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
