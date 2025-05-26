# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Agent-centric Git Service for Khive.

A complete reimagining of git operations for AI agents, focusing on
natural language understanding, workflow continuity, and intelligent assistance.

Example usage:
    ```python
    from khive.services.git import GitService, GitRequest

    service = GitService()

    # Natural language interface
    response = await service.handle_request(
        GitRequest(
            request="I've finished implementing OAuth and want to share it for review",
            context=WorkContext(
                task_description="Add OAuth2 authentication",
                related_issues=["123"],
                design_decisions=["Use PKCE flow", "Session-based tokens"]
            ),
            agent_id="implementer-1"
        )
    )

    # Response includes:
    # - What was understood and done
    # - Current repository state with semantic understanding
    # - Intelligent recommendations for next steps
    # - Session ID for continuity
    ```

Key Features:
    - **Natural Language First**: Express intent, not git commands
    - **Workflow Awareness**: Understands development phases and patterns
    - **Context Preservation**: Maintains state across operations
    - **Intelligent Assistance**: Proactive suggestions and error recovery
    - **Agent Optimization**: Designed for autonomous operation

Architecture:
    - GitService: Main service handling all requests
    - Intent Detection: Natural language understanding
    - Workflow Management: Orchestrates multi-step operations
    - State Analysis: Deep understanding of repository state
    - Response Generation: Agent-friendly responses with guidance
"""

from khive.services.git.git_service import GitService
from khive.services.git.parts import (
    # Core request/response
    GitRequest,
    GitResponse,
    # Context and state
    WorkContext,
    WorkIntent,
    RepositoryUnderstanding,
    GitSession,
    # Insights and recommendations
    CodeInsight,
    FileUnderstanding,
    Recommendation,
    # Collaboration
    CollaborationContext,
    # Quality and patterns
    QualityAssessment,
    PatternRecognition,
    # Errors
    GitError,
)

# Version info
__version__ = "2.0.0"
__author__ = "HaiyangLi"

# Public API
__all__ = [
    # Main service
    "GitService",
    # Request/Response
    "GitRequest",
    "GitResponse",
    # Context types
    "WorkContext",
    "WorkIntent",
    "RepositoryUnderstanding",
    "GitSession",
    # Analysis types
    "CodeInsight",
    "FileUnderstanding",
    "Recommendation",
    # Collaboration
    "CollaborationContext",
    # Quality
    "QualityAssessment",
    "PatternRecognition",
    # Errors
    "GitError",
]


# Convenience function for quick usage
async def git(request: str, **kwargs) -> GitResponse:
    """
    Convenience function for simple git operations.

    Args:
        request: Natural language request
        **kwargs: Additional arguments for GitRequest

    Returns:
        GitResponse with results and recommendations

    Example:
        ```python
        response = await git("save my progress")
        print(response.summary)
        ```
    """
    service = GitService()
    git_request = GitRequest(request=request, **kwargs)
    return await service.handle_request(git_request)
