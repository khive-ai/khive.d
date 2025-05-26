# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Natural language understanding components for Git Service.

This module handles intent detection, context extraction, and
intelligent response generation for agent interactions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from khive.services.git.parts import (
    GitSession,
    Recommendation,
    RepositoryUnderstanding,
    WorkContext,
    WorkIntent,
)


@dataclass
class IntentSignal:
    """A signal that indicates a particular intent."""

    pattern: str
    weight: float = 1.0
    requires_context: list[str] = None  # Required context keys

    def matches(self, text: str, context: WorkContext | None = None) -> float:
        """Check if this signal matches the input."""
        if re.search(self.pattern, text, re.IGNORECASE):
            # Check context requirements
            if self.requires_context and context:
                for key in self.requires_context:
                    if not getattr(context, key, None):
                        return 0.0
            return self.weight
        return 0.0


class IntentDetector:
    """Sophisticated intent detection for git operations."""

    def __init__(self):
        self.intent_signals = {
            WorkIntent.EXPLORE: [
                IntentSignal(r"\b(what|show|tell).*(status|state|chang)", 1.5),
                IntentSignal(r"\b(current|latest|recent)\s+\w+", 1.2),
                IntentSignal(r"\bexplor", 2.0),
                IntentSignal(r"\bcheck\s+(repo|code|status)", 1.8),
                IntentSignal(r"what('s|\s+is)\s+(new|different|changed)", 1.6),
                IntentSignal(r"anything\s+to\s+commit", 1.4),
            ],
            WorkIntent.IMPLEMENT: [
                IntentSignal(r"\b(save|commit|checkpoint)", 2.0),
                IntentSignal(r"\b(done|finish|complet).*(implement|code|feature)", 1.8),
                IntentSignal(r"ready\s+to\s+commit", 2.0),
                IntentSignal(r"implemented\s+\w+", 1.6),
                IntentSignal(r"save\s+(my\s+)?progress", 2.0),
                IntentSignal(r"record\s+(these\s+)?changes", 1.5),
                # Context-aware signals
                IntentSignal(
                    r"that's\s+working", 1.2, requires_context=["task_description"]
                ),
                IntentSignal(r"tests\s+are\s+passing", 1.4),
            ],
            WorkIntent.COLLABORATE: [
                IntentSignal(r"\b(create|open|make)\s+(a\s+)?pr", 2.0),
                IntentSignal(r"pull\s+request", 2.0),
                IntentSignal(r"(ready|share)\s+(for\s+)?review", 1.8),
                IntentSignal(r"get\s+feedback", 1.6),
                IntentSignal(r"submit\s+(for\s+)?review", 1.8),
                IntentSignal(r"push\s+(to\s+)?remote", 1.4),
                IntentSignal(r"share\s+(my\s+)?changes", 1.6),
                IntentSignal(r"collaborate", 1.5),
            ],
            WorkIntent.INTEGRATE: [
                IntentSignal(r"\bmerge\b", 2.0),
                IntentSignal(r"pull\s+(latest\s+)?changes", 1.8),
                IntentSignal(r"sync\s+(with\s+)?upstream", 1.8),
                IntentSignal(r"update\s+(my\s+)?branch", 1.6),
                IntentSignal(r"incorporate\s+feedback", 1.8),
                IntentSignal(r"apply\s+suggestions", 1.6),
                IntentSignal(r"address\s+comments", 1.6),
                IntentSignal(r"resolve\s+conflicts?", 2.0),
            ],
            WorkIntent.UNDERSTAND: [
                IntentSignal(r"what\s+happened", 1.8),
                IntentSignal(r"explain\s+(the\s+)?changes", 1.6),
                IntentSignal(r"understand\s+\w+", 1.6),
                IntentSignal(r"analyze\s+(commit|history|code)", 1.8),
                IntentSignal(r"show\s+me\s+(the\s+)?history", 1.6),
                IntentSignal(r"quality\s+(check|assessment|analysis)", 1.8),
                IntentSignal(r"find\s+patterns", 1.6),
                IntentSignal(r"(how|why)\s+did", 1.4),
            ],
            WorkIntent.RELEASE: [
                IntentSignal(r"\brelease\b", 2.0),
                IntentSignal(r"publish\s+(new\s+)?version", 1.8),
                IntentSignal(r"tag\s+(for\s+)?release", 1.8),
                IntentSignal(r"deploy", 1.6),
                IntentSignal(r"ship\s+it", 1.8),
                IntentSignal(r"version\s+\d+\.\d+", 1.6),
                IntentSignal(r"create\s+release", 1.8),
            ],
            WorkIntent.UNDO: [
                IntentSignal(r"\bundo\b", 2.0),
                IntentSignal(r"\brevert\b", 2.0),
                IntentSignal(r"roll\s*back", 1.8),
                IntentSignal(r"fix\s+(my\s+)?mistake", 1.6),
                IntentSignal(r"go\s+back\s+to", 1.6),
                IntentSignal(r"restore\s+previous", 1.6),
                IntentSignal(r"cancel\s+(that\s+)?commit", 1.8),
            ],
            WorkIntent.ORGANIZE: [
                IntentSignal(r"clean\s+(up\s+)?branch", 1.8),
                IntentSignal(r"organize\s+repo", 1.6),
                IntentSignal(r"tidy\s+up", 1.6),
                IntentSignal(r"archive\s+old", 1.6),
                IntentSignal(r"delete\s+merged", 1.8),
                IntentSignal(r"prune\s+branches", 1.8),
            ],
        }

        # Contextual modifiers
        self.context_modifiers = {
            "has_uncommitted_changes": {
                WorkIntent.IMPLEMENT: 1.5,
                WorkIntent.EXPLORE: 0.8,
            },
            "has_unpushed_commits": {
                WorkIntent.COLLABORATE: 1.5,
                WorkIntent.IMPLEMENT: 0.7,
            },
            "has_active_pr": {
                WorkIntent.INTEGRATE: 1.3,
                WorkIntent.COLLABORATE: 0.8,
            },
            "on_main_branch": {
                WorkIntent.EXPLORE: 1.2,
                WorkIntent.IMPLEMENT: 0.6,
            },
        }

    def detect_intent(
        self,
        text: str,
        context: WorkContext | None = None,
        state: RepositoryUnderstanding | None = None,
        session: GitSession | None = None,
    ) -> tuple[WorkIntent, float]:
        """
        Detect intent with confidence score.

        Returns:
            Tuple of (intent, confidence) where confidence is 0-1
        """
        scores = {}

        # Calculate base scores from signals
        for intent, signals in self.intent_signals.items():
            score = 0.0
            for signal in signals:
                score += signal.matches(text, context)
            scores[intent] = score

        # Apply contextual modifiers
        if state:
            for condition, modifiers in self.context_modifiers.items():
                if self._check_condition(condition, state):
                    for intent, modifier in modifiers.items():
                        if intent in scores:
                            scores[intent] *= modifier

        # Consider session history
        if session and session.request_history:
            scores = self._adjust_for_history(scores, session)

        # Find best match
        if not scores or max(scores.values()) == 0:
            return WorkIntent.EXPLORE, 0.3  # Default with low confidence

        best_intent = max(scores, key=scores.get)
        total_score = sum(scores.values())
        confidence = scores[best_intent] / total_score if total_score > 0 else 0

        return best_intent, min(confidence, 1.0)

    def _check_condition(self, condition: str, state: RepositoryUnderstanding) -> bool:
        """Check if a contextual condition is met."""
        if condition == "has_uncommitted_changes":
            return state.has_uncommitted_changes
        elif condition == "has_unpushed_commits":
            return state.current_branch != "main" and not state.has_remote_branch
        elif condition == "has_active_pr":
            return state.existing_pr is not None
        elif condition == "on_main_branch":
            return state.current_branch == "main"
        return False

    def _adjust_for_history(
        self, scores: dict[WorkIntent, float], session: GitSession
    ) -> dict[WorkIntent, float]:
        """Adjust scores based on conversation history."""
        recent_requests = session.request_history[-3:]  # Last 3 requests

        # Boost intents that follow logical flow
        if any("implement" in req.lower() for req in recent_requests):
            # After implementing, likely to share
            scores[WorkIntent.COLLABORATE] *= 1.3

        if any("review" in req.lower() for req in recent_requests):
            # After review, likely to integrate
            scores[WorkIntent.INTEGRATE] *= 1.3

        return scores


class ContextExtractor:
    """Extract rich context from natural language requests."""

    def extract_context(
        self, text: str, existing_context: WorkContext | None = None
    ) -> WorkContext:
        """Extract work context from request text."""
        context = existing_context or WorkContext()

        # Extract issue references
        issue_pattern = r"#(\d+)|issue\s+(\d+)|ticket\s+(\d+)"
        for match in re.finditer(issue_pattern, text, re.IGNORECASE):
            issue_id = next(g for g in match.groups() if g)
            if issue_id not in context.related_issues:
                context.related_issues.append(issue_id)

        # Extract task description
        task_patterns = [
            r"implement(?:ing|ed)?\s+(.+?)(?:\.|$)",
            r"working\s+on\s+(.+?)(?:\.|$)",
            r"task\s+is\s+to\s+(.+?)(?:\.|$)",
            r"feature\s+for\s+(.+?)(?:\.|$)",
        ]
        for pattern in task_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and not context.task_description:
                context.task_description = match.group(1).strip()
                break

        # Extract requirements/constraints
        requirement_patterns = [
            r"must\s+(.+?)(?:\.|$)",
            r"should\s+(.+?)(?:\.|$)",
            r"need(?:s)?\s+to\s+(.+?)(?:\.|$)",
            r"require(?:s|ment)?\s+(.+?)(?:\.|$)",
        ]
        for pattern in requirement_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                requirement = match.group(1).strip()
                if requirement not in context.requirements:
                    context.requirements.append(requirement)

        # Extract things to avoid
        avoid_patterns = [
            r"don't\s+(.+?)(?:\.|$)",
            r"avoid\s+(.+?)(?:\.|$)",
            r"without\s+(.+?)(?:\.|$)",
            r"no\s+(.+?)(?:\.|$)",
        ]
        for pattern in avoid_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                avoid_item = match.group(1).strip()
                if avoid_item not in context.avoid:
                    context.avoid.append(avoid_item)

        # Extract search/evidence IDs
        search_pattern = r"(?:search|evidence|ref)[:\s]+([a-zA-Z0-9-]+)"
        for match in re.finditer(search_pattern, text, re.IGNORECASE):
            search_id = match.group(1)
            if search_id not in context.search_ids:
                context.search_ids.append(search_id)

        return context


class ResponseGenerator:
    """Generate natural, helpful responses for agents."""

    def generate_prompts(
        self,
        intent: WorkIntent,
        state: RepositoryUnderstanding,
        session: GitSession | None = None,
    ) -> list[str]:
        """Generate contextual follow-up prompts."""
        prompts = []

        if intent == WorkIntent.EXPLORE:
            if state.has_uncommitted_changes:
                prompts.append("Should I save these changes?")
            if state.code_insights and not state.code_insights.adds_tests:
                prompts.append("Want me to help add tests?")
            if state.potential_issues:
                prompts.append("Should I fix the issues I found?")

        elif intent == WorkIntent.IMPLEMENT:
            if state.code_insights and state.code_insights.adds_tests:
                prompts.append("Ready to push for review?")
            else:
                prompts.append("Should we add tests before sharing?")
            prompts.append("Continue with the next part?")

        elif intent == WorkIntent.COLLABORATE:
            prompts.append("Want me to notify specific reviewers?")
            prompts.append("Should I add more context to the PR?")
            if session and session.implementation_flow:
                prompts.append("Continue working while waiting for review?")

        elif intent == WorkIntent.INTEGRATE:
            prompts.append("Run tests after integration?")
            prompts.append("Update the PR with these changes?")

        # Always include a general prompt
        prompts.append("What would you like to do next?")

        return prompts[:4]  # Max 4 prompts

    def generate_recommendations(
        self,
        intent: WorkIntent,
        state: RepositoryUnderstanding,
        context: dict[str, Any],
    ) -> list[Recommendation]:
        """Generate intelligent recommendations based on context."""
        recommendations = []

        # Universal recommendations
        if state.has_uncommitted_changes:
            recommendations.append(
                Recommendation(
                    action="Save your current progress",
                    reason="You have uncommitted changes that should be preserved",
                    impact="Creates a checkpoint you can return to",
                    urgency="recommended",
                    effort="trivial",
                    example_request="Save my progress",
                    prerequisites=[],
                )
            )

        # Intent-specific recommendations
        if intent == WorkIntent.IMPLEMENT:
            if not state.code_insights.adds_tests:
                recommendations.append(
                    Recommendation(
                        action="Add tests for your implementation",
                        reason="Code without tests is harder to maintain",
                        impact="Improves code reliability and review speed",
                        urgency="recommended",
                        effort="moderate",
                        example_request="Help me add tests for these changes",
                        prerequisites=["Save current progress"],
                    )
                )

        elif intent == WorkIntent.COLLABORATE:
            if state.code_insights.complexity == "complex":
                recommendations.append(
                    Recommendation(
                        action="Add detailed PR description",
                        reason="Complex changes need clear explanation",
                        impact="Speeds up review and reduces back-and-forth",
                        urgency="recommended",
                        effort="quick",
                        example_request="Help me write a comprehensive PR description",
                        prerequisites=[],
                    )
                )

        # Quality-based recommendations
        if state.code_insights.introduces_tech_debt:
            recommendations.append(
                Recommendation(
                    action="Address technical debt",
                    reason="New technical debt will slow future development",
                    impact="Maintains code quality and velocity",
                    urgency="soon",
                    effort="moderate",
                    example_request="Help me refactor to reduce technical debt",
                    prerequisites=[],
                )
            )

        return recommendations

    def summarize_changes(self, state: RepositoryUnderstanding) -> str:
        """Create a natural language summary of changes."""
        if not state.files_changed:
            return "No changes detected in the repository."

        # Count by category
        categories = {}
        for file in state.files_changed:
            categories[file.role] = categories.get(file.role, 0) + 1

        # Build summary
        parts = []
        if categories.get("core", 0) > 0:
            parts.append(f"{categories['core']} core files")
        if categories.get("test", 0) > 0:
            parts.append(f"{categories['test']} test files")
        if categories.get("docs", 0) > 0:
            parts.append(f"{categories['docs']} documentation files")

        summary = f"Modified {', '.join(parts)}"

        # Add insights
        if state.code_insights:
            summary += f" implementing {state.code_insights.change_type} changes"
            if state.code_insights.complexity != "simple":
                summary += f" with {state.code_insights.complexity} complexity"

        return summary


class ConversationManager:
    """Manage conversation flow and context."""

    def __init__(self):
        self.response_generator = ResponseGenerator()
        self.context_extractor = ContextExtractor()

    def get_conversation_state(self, session: GitSession) -> str:
        """Determine the current conversation state."""
        if not session.request_history:
            return "new_conversation"

        recent_actions = session.action_history[-3:] if session.action_history else []

        # Identify patterns
        if any("commit" in action for action in recent_actions):
            if any("push" in action for action in recent_actions):
                return "ready_for_review"
            return "post_commit"

        if any("pr" in action for action in recent_actions):
            return "awaiting_review"

        if any("merge" in action or "integrate" in action for action in recent_actions):
            return "post_integration"

        return "active_development"

    def suggest_next_action(
        self, current_state: str, repository_state: RepositoryUnderstanding
    ) -> str:
        """Suggest the next logical action based on conversation state."""
        suggestions = {
            "new_conversation": "explore the repository state",
            "post_commit": "push changes for review",
            "ready_for_review": "create a pull request",
            "awaiting_review": "check review status or continue with another task",
            "post_integration": "verify integration success and plan next steps",
            "active_development": "save progress or get feedback",
        }

        base_suggestion = suggestions.get(current_state, "explore current state")

        # Customize based on repository state
        if repository_state.potential_issues:
            return f"address the issues found, then {base_suggestion}"

        return base_suggestion
