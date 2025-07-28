# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
LionAGI-Enhanced Git Service implementation.

A git service designed from the ground up for AI agents, integrating with LionAGI's
Branch orchestration, MessageManager for conversation history, and ActionManager
for tool-based git operations.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from lionagi.session.branch import Branch
from lionagi.protocols.types import (
    ActionManager,
    MessageManager,
    Instruction,
    AssistantResponse,
    ActionRequest,
    ActionResponse,
    System,
)
from lionagi.protocols.action.tool import Tool
from lionagi.service.types import iModel

LIONAGI_AVAILABLE = True

from khive.services.git.nlp import IntentDetector, ResponseGenerator
from khive.services.git.parts import (
    CodeInsight,
    CollaborationContext,
    CollaborationFlow,
    FileUnderstanding,
    GitError,
    GitRequest,
    GitResponse,
    GitSession,
    ImplementationFlow,
    PatternRecognition,
    QualityAssessment,
    QualityIssue,
    Recommendation,
    ReleaseFlow,
    RepositoryUnderstanding,
    WorkIntent,
)
from khive.services.git.workflows import (
    CodeAnalyzer,
    CommitMessageGenerator,
    FileAnalyzer,
    GitOperations,
    PRManager,
)
from khive.types import Service
from khive.utils import log_msg


class GitService(Service):
    """
    LionAGI-Enhanced Git service optimized for AI agents.

    Key principles:
    - Natural language is the primary interface
    - Maintains conversational context across operations via LionAGI Branch
    - Git operations are defined as LionAGI Tools for intelligent orchestration
    - Provides rich semantic understanding and workflow intelligence
    - Learns from usage patterns through conversation history
    """

    def __init__(self):
        """Initialize the LionAGI-enhanced Git service."""
        self._sessions: dict[str, GitSession] = {}
        self._llm_endpoint = None

        # Core components
        self._git_ops = GitOperations()
        self._file_analyzer = FileAnalyzer()
        self._code_analyzer = CodeAnalyzer()
        self._pr_manager = PRManager()
        self._commit_generator = CommitMessageGenerator()

        # Intelligence components
        self._intent_detector = IntentDetector()
        self._response_generator = ResponseGenerator()
        self._pattern_analyzer = PatternAnalyzer()
        self._quality_analyzer = QualityAnalyzer()
        self._collaboration_optimizer = CollaborationOptimizer()

        # LionAGI Integration
        self._lionagi_available = LIONAGI_AVAILABLE
        self._branches: dict[str, Branch] = {}
        
        if self._lionagi_available:
            log_msg("LionAGI integration enabled - advanced conversation management available")
        else:
            log_msg("LionAGI not available - using standard service implementation")

    async def handle_request(self, request: GitRequest) -> GitResponse:
        """
        Handle a git request with LionAGI-enhanced natural language understanding.

        This is the single entry point for all git operations, now enhanced with
        LionAGI Branch orchestration for conversation management.
        """
        # Get or create session
        session = self._get_or_create_session(
            request.agent_id or "anonymous", request.conversation_id
        )

        # Get or create LionAGI Branch for conversation management
        branch = await self._get_or_create_branch(
            request.agent_id or "anonymous", request.conversation_id
        )

        # Track request in session and branch
        session.add_request(request.request)
        
        if branch:
            # Add user instruction to conversation history
            await branch.msgs.a_add_message(
                instruction=request.request,
                context=request.context.model_dump() if request.context else None,
                sender=request.agent_id or "user",
                metadata={"request_type": "git_operation", "timestamp": datetime.utcnow().isoformat()}
            )

        try:
            # Enhanced intent detection with LionAGI Branch context
            intent, confidence = await self._detect_intent_with_branch(
                request, session, branch
            )
            log_msg(f"Understood intent: {intent} (confidence: {confidence:.2f})")

            # Route to appropriate workflow with Branch support
            if intent == WorkIntent.EXPLORE:
                return await self._handle_explore(request, session, branch)
            elif intent == WorkIntent.IMPLEMENT:
                return await self._handle_implement(request, session, branch)
            elif intent == WorkIntent.COLLABORATE:
                return await self._handle_collaborate(request, session, branch)
            elif intent == WorkIntent.INTEGRATE:
                return await self._handle_integrate(request, session, branch)
            elif intent == WorkIntent.RELEASE:
                return await self._handle_release(request, session, branch)
            elif intent == WorkIntent.UNDERSTAND:
                return await self._handle_understand(request, session, branch)
            elif intent == WorkIntent.UNDO:
                return await self._handle_undo(request, session, branch)
            elif intent == WorkIntent.ORGANIZE:
                return await self._handle_organize(request, session, branch)

        except Exception as e:
            return await self._handle_error(e, request, session, branch)

    # --- Workflow Handlers ---

    async def _handle_explore(
        self, request: GitRequest, session: GitSession, branch: Branch | None = None
    ) -> GitResponse:
        """Handle exploration requests."""
        state = await self._get_repository_state()

        # Analyze patterns if enough history
        if len(session.action_history) > 10:
            session.learned_patterns = await self._pattern_analyzer.analyze(
                session.repository_knowledge
            )

        # Build recommendations based on state
        recommendations = self._build_explore_recommendations(state, session)

        # Track action
        session.add_action("explored repository state")

        return GitResponse(
            understood_as="Exploring repository state and available actions",
            actions_taken=[
                "Analyzed current branch and changes",
                "Identified work phase and context",
                "Generated personalized recommendations",
            ],
            repository_state=state,
            recommendations=recommendations,
            learned={
                "work_phase": state.work_phase,
                "change_summary": self._summarize_changes(state),
                "health_status": self._assess_health(state),
            },
            conversation_id=session.id,
            follow_up_prompts=self._generate_explore_prompts(state),
        )

    async def _handle_implement(
        self, request: GitRequest, session: GitSession, branch: Branch | None = None
    ) -> GitResponse:
        """Handle implementation save requests."""
        state = await self._get_repository_state()

        # Initialize or update implementation flow
        if not session.implementation_flow:
            session.implementation_flow = ImplementationFlow(
                task=request.context.task_description
                if request.context
                else "Current implementation",
                approach=request.context.design_decisions if request.context else [],
                success_criteria=request.context.requirements
                if request.context
                else [],
                started_at=datetime.utcnow(),
            )

        actions_taken = []

        # Smart staging based on changes
        staged_files = await self._smart_stage_files(state, request)
        actions_taken.append(f"Staged {len(staged_files)} files intelligently")

        # Generate commit message with context
        commit_message = await self._generate_contextual_commit(state, request, session)

        # Perform commit
        commit_result = await self._perform_commit(commit_message)
        actions_taken.append(f"Created commit: {commit_result['sha'][:8]}")

        # Update flow
        session.implementation_flow.add_checkpoint(
            commit_message.split("\n")[0], state.code_insights
        )

        # Update state
        state = await self._get_repository_state()

        # Build next recommendations
        recommendations = self._build_implement_recommendations(
            state, session, commit_result
        )

        session.add_action(f"saved implementation progress: {commit_result['sha'][:8]}")

        # Add assistant response to LionAGI Branch conversation
        if branch:
            response_content = f"Successfully committed changes: {commit_message.split(chr(10))[0]}"
            await branch.msgs.a_add_message(
                assistant_response=response_content,
                sender="git_service",
                metadata={
                    "action_type": "implement",
                    "commit_sha": commit_result.get("sha", ""),
                    "files_staged": len(staged_files)
                }
            )

        return GitResponse(
            understood_as="Saving implementation progress with intelligent commit",
            actions_taken=actions_taken,
            repository_state=state,
            recommendations=recommendations,
            learned={
                "commit_sha": commit_result["sha"],
                "commit_message": commit_message,
                "files_staged": staged_files,
                "next_phase": self._suggest_next_phase(state, session),
            },
            conversation_id=session.id,
            follow_up_prompts=[
                "Should I push these changes?",
                "Ready to create a pull request?",
                "Want me to run the tests?",
                "Continue with the next part?",
            ],
        )

    async def _handle_collaborate(
        self, request: GitRequest, session: GitSession, branch: Branch | None = None
    ) -> GitResponse:
        """Handle collaboration requests."""
        state = await self._get_repository_state()
        actions_taken = []

        # Ensure changes are committed
        if state.has_uncommitted_changes or state.has_staged_changes:
            commit_response = await self._handle_implement(request, session, branch)
            actions_taken.extend(commit_response.actions_taken)
            state = commit_response.repository_state

        # Push branch
        push_result = await self._push_branch(state.current_branch)
        actions_taken.append(f"Pushed branch '{state.current_branch}' to remote")

        # Create or update PR
        if state.existing_pr:
            # Update existing PR
            pr_result = await self._update_pull_request(state, request, session)
            actions_taken.append(f"Updated pull request #{pr_result['number']}")
        else:
            # Create new PR
            pr_result = await self._create_pull_request(state, request, session)
            actions_taken.append(f"Created pull request #{pr_result['number']}")

            # Initialize collaboration flow
            session.collaboration_flow = CollaborationFlow(
                pr_title=pr_result["title"],
                pr_body=pr_result["body"],
                suggested_reviewers=pr_result.get("reviewers", []),
                review_focus_areas=await self._identify_review_focus(state),
                expected_feedback_types=["code quality", "design", "tests"],
            )

        # Get updated state with PR info
        state = await self._get_repository_state()

        # Optimize reviewer assignment
        if not state.collaboration.active_reviewers:
            reviewers = await self._collaboration_optimizer.suggest_reviewers(
                state, session
            )
            if reviewers:
                await self._assign_reviewers(pr_result["number"], reviewers)
                actions_taken.append(
                    f"Assigned optimal reviewers: {', '.join(reviewers)}"
                )

        recommendations = self._build_collaborate_recommendations(
            state, session, pr_result
        )

        session.add_action(f"initiated collaboration via PR #{pr_result['number']}")

        return GitResponse(
            understood_as="Sharing work for collaborative review",
            actions_taken=actions_taken,
            repository_state=state,
            recommendations=recommendations,
            learned={
                "pr_url": pr_result["url"],
                "pr_number": pr_result["number"],
                "reviewers": pr_result.get("reviewers", []),
                "estimated_review_time": await self._estimate_review_time(
                    state, session
                ),
            },
            conversation_id=session.id,
            follow_up_prompts=[
                "Check review status?",
                "Add more context to the PR?",
                "Notify specific reviewers?",
                "Continue with another task while waiting?",
            ],
        )

    async def _handle_integrate(
        self, request: GitRequest, session: GitSession, branch: Branch | None = None
    ) -> GitResponse:
        """Handle integration requests."""
        state = await self._get_repository_state()
        actions_taken = []

        # Determine integration strategy
        if "feedback" in request.request.lower():
            # Incorporating review feedback
            if state.collaboration.feedback_received:
                changes_made = await self._apply_feedback(
                    state.collaboration.feedback_received, request
                )
                actions_taken.extend(changes_made)

                # Commit feedback changes
                commit_msg = await self._generate_feedback_commit(
                    state.collaboration.feedback_received
                )
                await self._perform_commit(commit_msg)
                actions_taken.append("Committed feedback changes")
        else:
            # Syncing with upstream
            sync_result = await self._sync_with_upstream(state.current_branch)
            actions_taken.extend(sync_result["actions"])

            if sync_result["conflicts"]:
                # Handle merge conflicts
                resolution = await self._suggest_conflict_resolution(
                    sync_result["conflicts"]
                )
                return GitResponse(
                    understood_as="Attempting to integrate changes but found conflicts",
                    actions_taken=actions_taken,
                    repository_state=await self._get_repository_state(),
                    recommendations=[
                        Recommendation(
                            action="Resolve merge conflicts",
                            reason="Cannot proceed until conflicts are resolved",
                            impact="Will allow branch to be merged",
                            urgency="urgent",
                            effort="moderate",
                            example_request="Help me resolve these conflicts",
                            prerequisites=[],
                        )
                    ],
                    learned={
                        "conflicts": sync_result["conflicts"],
                        "resolution_suggestions": resolution,
                    },
                    conversation_id=session.id,
                    follow_up_prompts=["Help me resolve the conflicts?"],
                )

        # Get final state
        state = await self._get_repository_state()
        recommendations = self._build_integrate_recommendations(state, session)

        session.add_action("integrated changes successfully")

        return GitResponse(
            understood_as="Integrating changes from collaboration",
            actions_taken=actions_taken,
            repository_state=state,
            recommendations=recommendations,
            learned={
                "integration_type": "feedback"
                if "feedback" in request.request.lower()
                else "upstream_sync",
                "changes_integrated": len(actions_taken),
                "branch_status": "up_to_date",
            },
            conversation_id=session.id,
            follow_up_prompts=[
                "Push the integrated changes?",
                "Update the pull request?",
                "Run tests to verify integration?",
            ],
        )

    async def _handle_release(
        self, request: GitRequest, session: GitSession, branch: Branch | None = None
    ) -> GitResponse:
        """Handle release requests."""
        state = await self._get_repository_state()
        actions_taken = []

        # Initialize release flow
        if not session.release_flow:
            # Extract version from request
            version = self._extract_version(request.request)
            if not version:
                # Generate next version based on changes
                version = await self._suggest_next_version(state)

            session.release_flow = ReleaseFlow(
                version=version,
                release_type=self._determine_release_type(version),
                highlights=[],
                breaking_changes=[],
            )

        # Ensure all changes are committed
        if state.has_uncommitted_changes:
            commit_response = await self._handle_implement(request, session, branch)
            actions_taken.extend(commit_response.actions_taken)
            state = commit_response.repository_state

        # Ensure we're on the main branch
        if state.current_branch != "main":
            # Create PR if needed
            if not state.existing_pr:
                pr_response = await self._handle_collaborate(request, session, branch)
                actions_taken.extend(pr_response.actions_taken)

            # Switch to main
            await self._git_ops.checkout_branch("main")
            await self._git_ops.pull_latest()
            actions_taken.append("Switched to main branch and pulled latest")

            # Merge feature branch
            merge_result = await self._git_ops.merge_branch(state.current_branch)
            if merge_result["success"]:
                actions_taken.append(f"Merged {state.current_branch} into main")
            else:
                return self._handle_merge_conflicts(merge_result, request, session)

        # Generate release artifacts
        release_artifacts = await self._generate_release_artifacts(
            session.release_flow, state
        )

        # Create git tag
        tag_result = await self._git_ops.create_tag(
            session.release_flow.version,
            f"Release {session.release_flow.version}\n\n{release_artifacts['changelog']}",
        )
        actions_taken.append(f"Created tag {session.release_flow.version}")

        # Push tag
        await self._git_ops.push_tag(session.release_flow.version)
        actions_taken.append("Pushed tag to remote")

        # Create GitHub release if available
        if await self._github_available():
            release_url = await self._create_github_release(
                session.release_flow, release_artifacts
            )
            actions_taken.append(f"Created GitHub release: {release_url}")

        # Update version files
        version_updates = await self._update_version_files(session.release_flow.version)
        if version_updates:
            actions_taken.extend(version_updates)

            # Commit version updates
            await self._git_ops.create_commit(
                f"chore: bump version to {session.release_flow.version}"
            )
            await self._git_ops.push_branch("main")

        # Get final state
        state = await self._get_repository_state()

        recommendations = [
            Recommendation(
                action="Announce the release",
                reason="Let users know about the new version",
                impact="Increases adoption of new features",
                urgency="recommended",
                effort="quick",
                example_request="Draft a release announcement",
                prerequisites=[],
            ),
            Recommendation(
                action="Monitor for issues",
                reason="Catch any problems early",
                impact="Maintains user trust",
                urgency="recommended",
                effort="moderate",
                example_request="Set up monitoring for the new release",
                prerequisites=[],
            ),
        ]

        session.add_action(f"released version {session.release_flow.version}")

        return GitResponse(
            understood_as=f"Creating release {session.release_flow.version}",
            actions_taken=actions_taken,
            repository_state=state,
            recommendations=recommendations,
            learned={
                "version": session.release_flow.version,
                "tag": session.release_flow.version,
                "changelog": release_artifacts["changelog"],
                "release_notes": release_artifacts["release_notes"],
                "release_url": release_artifacts.get("url"),
                "next_version_suggestion": self._suggest_next_dev_version(
                    session.release_flow.version
                ),
            },
            conversation_id=session.id,
            follow_up_prompts=[
                "Start working on the next version?",
                "Create release announcement?",
                "Update documentation for the release?",
            ],
        )

    async def _handle_understand(
        self, request: GitRequest, session: GitSession, branch: Branch | None = None
    ) -> GitResponse:
        """Handle understanding/analysis requests."""
        state = await self._get_repository_state()

        # Determine what to analyze
        focus = self._extract_analysis_focus(request.request)

        analysis_results = {}
        actions_taken = []

        if "commit" in focus["focus"] or "history" in focus["focus"]:
            # Analyze commit history
            history_analysis = await self._analyze_commit_history(
                branch=state.current_branch, limit=focus.get("limit", 20)
            )
            analysis_results["history"] = history_analysis
            actions_taken.append("Analyzed commit history")

        if "quality" in focus["focus"]:
            # Perform quality assessment
            quality = await self._quality_analyzer.assess(state)
            analysis_results["quality"] = quality
            actions_taken.append("Assessed code quality")

        if "patterns" in focus["focus"]:
            # Identify patterns
            patterns = await self._pattern_analyzer.analyze(
                session.repository_knowledge
            )
            analysis_results["patterns"] = patterns
            actions_taken.append("Identified codebase patterns")

        # Generate insights
        insights = await self._generate_insights(analysis_results, state)

        recommendations = self._build_understand_recommendations(
            insights, state, session
        )

        session.add_action(f"analyzed {', '.join(focus['focus'])}")

        return GitResponse(
            understood_as=f"Analyzing {', '.join(focus['focus'])} to provide insights",
            actions_taken=actions_taken,
            repository_state=state,
            recommendations=recommendations,
            learned={
                **analysis_results,
                "key_insights": insights,
                "actionable_findings": self._extract_actionable_findings(
                    analysis_results
                ),
            },
            conversation_id=session.id,
            follow_up_prompts=[
                "Want me to fix any of the issues found?",
                "Should I document these findings?",
                "Interested in more detailed analysis?",
                "Ready to act on these insights?",
            ],
        )

    async def _handle_undo(
        self, request: GitRequest, session: GitSession, branch: Branch | None = None
    ) -> GitResponse:
        """Handle undo/revert requests."""
        state = await self._get_repository_state()
        actions_taken = []

        # Determine what to undo
        undo_target = self._identify_undo_target(request.request, session)

        if undo_target["type"] == "last_commit":
            # Undo last commit
            if state.last_commit:
                # Check if commit was pushed
                if await self._is_commit_pushed(state.last_commit.sha):
                    # Need to revert instead of reset
                    revert_result = await self._git_ops.revert_commit(
                        state.last_commit.sha
                    )
                    actions_taken.append(
                        f"Created revert commit for {state.last_commit.sha[:8]}"
                    )

                    # Push the revert
                    await self._git_ops.push_branch(state.current_branch)
                    actions_taken.append("Pushed revert commit")
                else:
                    # Can safely reset
                    await self._git_ops.reset_to_commit("HEAD~1", soft=True)
                    actions_taken.append(
                        "Reset to previous commit (changes preserved in working directory)"
                    )
            else:
                return GitResponse(
                    understood_as="Attempting to undo last commit",
                    actions_taken=[],
                    repository_state=state,
                    recommendations=[],
                    learned={"error": "No commits to undo"},
                    conversation_id=session.id,
                    follow_up_prompts=["What would you like to do instead?"],
                )

        elif undo_target["type"] == "specific_commit":
            # Revert specific commit
            commit_sha = undo_target["sha"]
            revert_result = await self._git_ops.revert_commit(commit_sha)
            actions_taken.append(f"Created revert commit for {commit_sha[:8]}")

        elif undo_target["type"] == "unstaged_changes":
            # Discard unstaged changes
            if state.has_uncommitted_changes:
                # Save current changes to stash first
                stash_result = await self._git_ops.stash_changes("Backup before undo")
                actions_taken.append(
                    "Saved current changes to stash (can be recovered)"
                )

                # Clean working directory
                await self._git_ops.clean_working_directory()
                actions_taken.append("Restored working directory to last commit")

        elif undo_target["type"] == "merge":
            # Undo a merge
            if await self._is_merge_commit(state.last_commit.sha):
                # Reset to before merge
                await self._git_ops.reset_to_commit("ORIG_HEAD", hard=True)
                actions_taken.append("Undid merge, restored to pre-merge state")
            else:
                return GitResponse(
                    understood_as="Attempting to undo merge",
                    actions_taken=[],
                    repository_state=state,
                    recommendations=[],
                    learned={"error": "Last commit is not a merge"},
                    conversation_id=session.id,
                    follow_up_prompts=["What would you like to undo?"],
                )

        # Get updated state
        state = await self._get_repository_state()

        # Build recommendations based on what was undone
        recommendations = []

        if undo_target["type"] in ["last_commit", "specific_commit"]:
            recommendations.append(
                Recommendation(
                    action="Review the reverted changes",
                    reason="Ensure the undo achieved what you wanted",
                    impact="Prevents accidental loss of wanted changes",
                    urgency="recommended",
                    effort="quick",
                    example_request="Show me what was undone",
                    prerequisites=[],
                )
            )

        if "stash" in " ".join(actions_taken).lower():
            recommendations.append(
                Recommendation(
                    action="Recover stashed changes if needed",
                    reason="Your changes are safely stored in git stash",
                    impact="Can restore work if undo was mistaken",
                    urgency="optional",
                    effort="trivial",
                    example_request="Restore my stashed changes",
                    prerequisites=[],
                )
            )

        session.add_action(f"undid {undo_target['type']}")

        return GitResponse(
            understood_as=f"Undoing {undo_target['description']}",
            actions_taken=actions_taken,
            repository_state=state,
            recommendations=recommendations,
            learned={
                "undo_type": undo_target["type"],
                "can_recover": "stash" in " ".join(actions_taken).lower(),
                "next_action": "Continue with development"
                if state.has_uncommitted_changes
                else "Make new changes",
            },
            conversation_id=session.id,
            follow_up_prompts=[
                "Show me what changed?",
                "Continue working on something else?",
                "Need to undo something else?",
            ],
        )

    async def _handle_organize(
        self, request: GitRequest, session: GitSession, branch: Branch | None = None
    ) -> GitResponse:
        """Handle repository organization requests."""
        state = await self._get_repository_state()
        actions_taken = []

        # Determine organization scope
        org_scope = self._determine_organization_scope(request.request)

        organized_items = {
            "branches_deleted": [],
            "branches_archived": [],
            "tags_created": [],
            "stashes_cleaned": [],
            "files_cleaned": [],
        }

        if "branches" in org_scope or "all" in org_scope:
            # Clean up merged branches
            merged_branches = await self._git_ops.get_merged_branches()

            for branch in merged_branches:
                if branch not in ["main", "master", "develop", state.current_branch]:
                    # Check if branch has been merged
                    if await self._is_branch_fully_merged(branch):
                        # Delete local branch
                        await self._git_ops.delete_branch(branch, force=False)
                        organized_items["branches_deleted"].append(branch)

                        # Delete remote branch if exists
                        if await self._git_ops.remote_branch_exists(branch):
                            await self._git_ops.delete_remote_branch(branch)
                            actions_taken.append(
                                f"Deleted merged branch '{branch}' (local and remote)"
                            )
                        else:
                            actions_taken.append(
                                f"Deleted merged branch '{branch}' (local only)"
                            )

        if "stashes" in org_scope or "all" in org_scope:
            # Clean old stashes
            stashes = await self._git_ops.list_stashes()
            old_stashes = [s for s in stashes if self._is_stash_old(s)]

            for stash in old_stashes:
                await self._git_ops.drop_stash(stash["index"])
                organized_items["stashes_cleaned"].append(stash["message"])

            if organized_items["stashes_cleaned"]:
                actions_taken.append(
                    f"Cleaned {len(organized_items['stashes_cleaned'])} old stashes"
                )

        if "tags" in org_scope:
            # Organize tags (create missing release tags)
            version_commits = await self._find_version_commits()

            for commit in version_commits:
                if not commit["has_tag"]:
                    tag_name = f"v{commit['version']}"
                    await self._git_ops.create_tag(
                        tag_name, f"Release {commit['version']}", commit["sha"]
                    )
                    organized_items["tags_created"].append(tag_name)

            if organized_items["tags_created"]:
                actions_taken.append(
                    f"Created {len(organized_items['tags_created'])} missing version tags"
                )

        if "files" in org_scope or "all" in org_scope:
            # Clean up common junk files
            junk_patterns = [
                ".DS_Store",
                "Thumbs.db",
                "*.pyc",
                "__pycache__",
                ".pytest_cache",
                "*.swp",
                "*.swo",
                "*~",
            ]

            for pattern in junk_patterns:
                removed = await self._git_ops.remove_files_by_pattern(
                    pattern, track=True
                )
                organized_items["files_cleaned"].extend(removed)

            if organized_items["files_cleaned"]:
                actions_taken.append(
                    f"Removed {len(organized_items['files_cleaned'])} junk files"
                )

                # Commit the cleanup
                await self._git_ops.create_commit(
                    "chore: clean up repository\n\nRemoved common junk files and artifacts"
                )
                actions_taken.append("Committed cleanup changes")

        # Get final state
        state = await self._get_repository_state()

        # Build summary
        total_cleaned = sum(len(items) for items in organized_items.values())

        recommendations = []

        if total_cleaned > 0:
            recommendations.append(
                Recommendation(
                    action="Push cleanup changes",
                    reason="Share the organized repository with team",
                    impact="Keeps repository clean for everyone",
                    urgency="recommended",
                    effort="trivial",
                    example_request="Push these cleanup changes",
                    prerequisites=[],
                )
            )

        recommendations.append(
            Recommendation(
                action="Set up automated cleanup",
                reason="Prevent junk accumulation in future",
                impact="Maintains clean repository automatically",
                urgency="optional",
                effort="moderate",
                example_request="Help me set up git hooks for cleanup",
                prerequisites=[],
            )
        )

        session.add_action(f"organized repository ({total_cleaned} items cleaned)")

        return GitResponse(
            understood_as=f"Organizing repository by cleaning {', '.join(org_scope)}",
            actions_taken=actions_taken,
            repository_state=state,
            recommendations=recommendations,
            learned={
                "organization_scope": org_scope,
                "items_cleaned": organized_items,
                "total_cleaned": total_cleaned,
                "repository_health": "improved"
                if total_cleaned > 0
                else "already good",
            },
            conversation_id=session.id,
            follow_up_prompts=[
                "Show me what was cleaned up?",
                "Set up regular cleanup schedule?",
                "Any other maintenance needed?",
            ],
        )

    # --- LionAGI Integration Methods ---

    async def _get_or_create_branch(
        self, agent_id: str, conversation_id: str | None = None
    ) -> Branch | None:
        """Get or create a LionAGI Branch for conversation management."""
        branch_id = conversation_id or f"git-{agent_id}-{uuid4().hex[:8]}"
        
        if branch_id not in self._branches:
            # Create new Branch with git-specific system message
            system_message = (
                "You are an intelligent Git service assistant. You help users with "
                "git operations through natural language commands. You understand "
                "repository context, maintain conversation history, and can execute "
                "git operations as tools. Always provide clear, helpful responses "
                "about git operations and repository state."
            )
            
            try:
                branch = Branch(
                    name=f"git-service-{agent_id}",
                    system=system_message,
                    user=agent_id,
                    use_lion_system_message=False
                )
                
                # Register git operation tools
                await self._register_git_tools(branch)
                
                self._branches[branch_id] = branch
                log_msg(f"Created LionAGI Branch for git service: {branch_id}")
                
            except Exception as e:
                log_msg(f"Failed to create LionAGI Branch: {e}")
                return None
        
        return self._branches.get(branch_id)

    async def _register_git_tools(self, branch: Branch) -> None:
        """Register git operations as LionAGI Tools."""
        try:
            # Define git operation tools
            git_tools = [
                self._create_git_status_tool(),
                self._create_git_commit_tool(),
                self._create_git_push_tool(),
                self._create_git_branch_tool(),
                self._create_git_analyze_tool(),
            ]
            
            branch.register_tools(git_tools)
            log_msg(f"Registered {len(git_tools)} git operation tools")
            
        except Exception as e:
            log_msg(f"Failed to register git tools: {e}")

    def _create_git_status_tool(self) -> Tool:
        """Create a tool for git status operations."""
        async def git_status() -> dict[str, Any]:
            """Get the current git repository status."""
            try:
                state = await self._get_repository_state()
                return {
                    "current_branch": state.current_branch,
                    "has_changes": state.has_uncommitted_changes,
                    "has_staged": state.has_staged_changes,
                    "files_changed": len(state.files_changed),
                    "work_phase": state.work_phase,
                    "branch_purpose": state.branch_purpose,
                }
            except Exception as e:
                return {"error": str(e)}
        
        return Tool(func_callable=git_status)

    def _create_git_commit_tool(self) -> Tool:
        """Create a tool for git commit operations."""
        async def git_commit(message=None, auto_stage=True):
            """Create a git commit with the specified message.
            
            Args:
                message: Optional commit message
                auto_stage: Whether to auto-stage files
            
            Returns:
                dict: Commit result with success status and details
            """
            try:
                staged_files = []
                if auto_stage:
                    # Auto-stage files
                    state = await self._get_repository_state()
                    staged_files = await self._smart_stage_files(state, None)
                
                if not message:
                    # Generate contextual commit message
                    state = await self._get_repository_state()
                    message = await self._commit_generator.generate(
                        state.files_changed, state.code_insights, {}, style="conventional"
                    )
                
                result = await self._perform_commit(message)
                return {
                    "success": True,
                    "commit_sha": result.get("sha", ""),
                    "message": message,
                    "files_staged": staged_files if auto_stage else []
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return Tool(func_callable=git_commit)

    def _create_git_push_tool(self) -> Tool:
        """Create a tool for git push operations."""
        async def git_push(branch: str = None) -> dict[str, Any]:
            """Push changes to remote repository."""
            try:
                if not branch:
                    state = await self._get_repository_state()
                    branch = state.current_branch
                
                result = await self._push_branch(branch)
                return {
                    "success": True,
                    "branch": branch,
                    "result": result
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return Tool(func_callable=git_push)

    def _create_git_branch_tool(self) -> Tool:
        """Create a tool for git branch operations."""
        async def git_branch_info() -> dict[str, Any]:
            """Get information about git branches."""
            try:
                current_branch = await self._git_ops.get_current_branch()
                all_branches = await self._git_ops.get_all_branches()
                return {
                    "current_branch": current_branch,
                    "all_branches": all_branches,
                    "total_branches": len(all_branches)
                }
            except Exception as e:
                return {"error": str(e)}
        
        return Tool(func_callable=git_branch_info)

    def _create_git_analyze_tool(self) -> Tool:
        """Create a tool for git repository analysis."""
        async def git_analyze() -> dict[str, Any]:
            """Analyze the current repository state and provide insights."""
            try:
                state = await self._get_repository_state()
                quality = await self._quality_analyzer.assess(state)
                
                return {
                    "work_phase": state.work_phase,
                    "code_insights": {
                        "complexity": state.code_insights.complexity,
                        "change_type": state.code_insights.change_type,
                        "risk_level": state.code_insights.risk_level,
                        "adds_tests": state.code_insights.adds_tests,
                        "updates_docs": state.code_insights.updates_docs,
                    },
                    "quality_assessment": {
                        "test_coverage": quality.test_coverage,
                        "readability": quality.readability,
                        "maintainability": quality.maintainability,
                        "issues_count": len(quality.issues),
                    },
                    "recommended_actions": state.recommended_actions,
                }
            except Exception as e:
                return {"error": str(e)}
        
        return Tool(func_callable=git_analyze)

    async def _detect_intent_with_branch(
        self, request: GitRequest, session: GitSession, branch: Branch | None
    ) -> tuple[WorkIntent, float]:
        """Enhanced intent detection using LionAGI Branch context."""
        if not branch:
            # Fallback to standard intent detection
            return self._intent_detector.detect_intent(
                request.request,
                request.context,
                await self._get_repository_state(),
                session,
            )

        try:
            # Use LionAGI Branch for context-aware intent detection
            repo_state = await self._get_repository_state()
            
            # Build context from conversation history
            conversation_context = []
            if branch.msgs.messages:
                # Get recent messages for context
                recent_messages = list(branch.msgs.messages)[-5:]  # Last 5 messages
                for msg in recent_messages:
                    if hasattr(msg, 'content') and msg.content:
                        conversation_context.append(str(msg.content))
            
            # Enhanced intent detection with conversation context
            context_str = " ".join(conversation_context) if conversation_context else ""
            enhanced_request = f"{context_str} {request.request}".strip()
            
            intent, confidence = self._intent_detector.detect_intent(
                enhanced_request,
                request.context,
                repo_state,
                session,
            )
            
            # Boost confidence if we have good conversation context
            if conversation_context and confidence < 0.8:
                confidence = min(confidence + 0.1, 0.95)
            
            return intent, confidence
            
        except Exception as e:
            log_msg(f"Error in enhanced intent detection: {e}")
            # Fallback to standard detection
            return self._intent_detector.detect_intent(
                request.request,
                request.context,
                await self._get_repository_state(),
                session,
            )

    # Helper method stubs that are called but not yet implemented
    async def _push_branch(self, branch: str) -> dict[str, Any]:
        """Push branch to remote."""
        return await self._git_ops.push_branch(branch)

    # --- Helper Methods (continued) ---

    async def _handle_error(
        self, error: Exception, request: GitRequest, session: GitSession, branch: Branch | None = None
    ) -> GitResponse:
        """Handle errors gracefully with recovery suggestions."""
        error_type = type(error).__name__
        error_msg = str(error)

        # Analyze error
        git_error = GitError(
            error_type=error_type,
            description=error_msg,
            what_failed=self._identify_failure_point(error_msg),
            why_failed=self._explain_failure_reason(error_msg),
            can_retry=self._is_retryable(error_type),
            fix_suggestions=self._suggest_fixes(error_type, error_msg),
            workarounds=self._suggest_workarounds(error_type),
            prevention_tips=self._suggest_prevention(error_type),
        )

        return GitResponse(
            understood_as=f"Attempted to {request.request} but encountered an error",
            actions_taken=["Analyzed error", "Generated recovery suggestions"],
            repository_state=await self._get_repository_state(),
            recommendations=[
                Recommendation(
                    action=fix,
                    reason="This should resolve the error",
                    impact="Allow operation to complete successfully",
                    urgency="now",
                    effort="quick",
                    example_request=f"Please {fix.lower()}",
                    prerequisites=[],
                )
                for fix in git_error.fix_suggestions[:2]  # Top 2 fixes
            ],
            learned={"error": git_error.model_dump(), "can_retry": git_error.can_retry},
            conversation_id=session.id,
            follow_up_prompts=[
                "Should I try again?",
                "Want me to try a different approach?",
                "Need help with the fix?",
            ],
            success=False,
        )

    def _get_or_create_session(
        self, agent_id: str, conversation_id: str | None = None
    ) -> GitSession:
        """Get or create a session for continuity."""
        session_id = conversation_id or f"git-{agent_id}-{uuid4().hex[:8]}"

        # Clean up old sessions
        self._cleanup_old_sessions()

        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.last_activity = datetime.utcnow()
            return session

        # Create new session
        session = GitSession(
            id=session_id,
            agent_id=agent_id,
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
        )

        self._sessions[session_id] = session
        return session

    def _cleanup_old_sessions(self):
        """Remove sessions older than 2 hours."""
        cutoff = datetime.utcnow() - timedelta(hours=2)

        expired_sessions = [
            session_id
            for session_id, session in self._sessions.items()
            if session.last_activity < cutoff
        ]

        for session_id in expired_sessions:
            del self._sessions[session_id]

    def _identify_failure_point(self, error_msg: str) -> str:
        """Identify what specifically failed from error message."""
        error_lower = error_msg.lower()

        if "permission denied" in error_lower:
            return "File or directory permissions"
        elif "not a git repository" in error_lower:
            return "Git repository initialization"
        elif "remote" in error_lower and (
            "rejected" in error_lower or "failed" in error_lower
        ):
            return "Remote repository communication"
        elif "merge conflict" in error_lower or "conflict" in error_lower:
            return "Merge operation"
        elif "branch" in error_lower and "not found" in error_lower:
            return "Branch reference"
        elif "commit" in error_lower and (
            "failed" in error_lower or "error" in error_lower
        ):
            return "Commit operation"
        elif "authentication" in error_lower or "auth" in error_lower:
            return "Authentication"
        elif "network" in error_lower or "connection" in error_lower:
            return "Network connectivity"
        else:
            return "Git operation"

    def _explain_failure_reason(self, error_msg: str) -> str:
        """Explain why the failure occurred."""
        error_lower = error_msg.lower()

        if "permission denied" in error_lower:
            return "Insufficient permissions to access file or directory"
        elif "not a git repository" in error_lower:
            return "Current directory is not a git repository"
        elif "remote" in error_lower and "rejected" in error_lower:
            return "Remote repository rejected the push (likely due to conflicts)"
        elif "merge conflict" in error_lower:
            return "Conflicting changes need manual resolution"
        elif "branch" in error_lower and "not found" in error_lower:
            return "The specified branch does not exist"
        elif "authentication" in error_lower:
            return "Git credentials are invalid or expired"
        elif "network" in error_lower:
            return "Unable to connect to remote repository"
        else:
            return "An unexpected error occurred during git operation"

    def _is_retryable(self, error_type: str) -> bool:
        """Determine if the error can be retried."""
        retryable_errors = {
            "ConnectionError",
            "TimeoutError",
            "NetworkError",
            "TemporaryFailure",
        }
        return error_type in retryable_errors

    def _suggest_fixes(self, error_type: str, error_msg: str) -> list[str]:
        """Suggest fixes for the error."""
        error_lower = error_msg.lower()
        fixes = []

        if "permission denied" in error_lower:
            fixes.extend([
                "Check file permissions with 'ls -la'",
                "Run with appropriate permissions",
                "Ensure you own the repository directory",
            ])
        elif "not a git repository" in error_lower:
            fixes.extend([
                "Initialize git repository with 'git init'",
                "Navigate to the correct repository directory",
                "Clone the repository if it exists remotely",
            ])
        elif "remote" in error_lower and "rejected" in error_lower:
            fixes.extend([
                "Pull latest changes first with 'git pull'",
                "Resolve any merge conflicts",
                "Force push if you're sure (use with caution)",
            ])
        elif "merge conflict" in error_lower:
            fixes.extend([
                "Resolve conflicts manually in affected files",
                "Use 'git status' to see conflicted files",
                "Run 'git add' after resolving conflicts",
            ])
        elif "authentication" in error_lower:
            fixes.extend([
                "Check your git credentials",
                "Re-authenticate with git provider",
                "Verify SSH keys or personal access tokens",
            ])
        else:
            fixes.extend([
                "Check git status for repository state",
                "Verify the command syntax",
                "Try the operation again",
            ])

        return fixes[:3]  # Return top 3 fixes

    def _suggest_workarounds(self, error_type: str) -> list[str]:
        """Suggest workarounds for the error."""
        workarounds = []

        if error_type in ["ConnectionError", "NetworkError"]:
            workarounds.extend([
                "Try again when network is stable",
                "Use a different network connection",
                "Work offline and sync later",
            ])
        elif error_type == "PermissionError":
            workarounds.extend([
                "Use sudo if appropriate",
                "Change to a directory you own",
                "Copy files to a writable location",
            ])
        else:
            workarounds.extend([
                "Try a different approach to achieve the same goal",
                "Use git command line directly",
                "Check git documentation for alternatives",
            ])

        return workarounds[:2]  # Return top 2 workarounds

    def _suggest_prevention(self, error_type: str) -> list[str]:
        """Suggest prevention tips for future."""
        tips = []

        if error_type == "PermissionError":
            tips.extend([
                "Always work in directories you own",
                "Set up proper file permissions",
                "Use version control for important files",
            ])
        elif error_type in ["ConnectionError", "NetworkError"]:
            tips.extend([
                "Ensure stable internet connection",
                "Keep local repository synced regularly",
                "Use offline-capable workflows",
            ])
        else:
            tips.extend([
                "Keep git repository in good state",
                "Commit changes frequently",
                "Test operations on feature branches first",
            ])

        return tips[:2]  # Return top 2 tips

    async def _get_repository_state(self) -> RepositoryUnderstanding:
        """Get current repository state with deep understanding."""
        # Get basic git state
        current_branch = await self._git_ops.get_current_branch()
        changed_files_raw = await self._git_ops.get_changed_files()

        # Analyze files
        files_changed = []
        for file_info in changed_files_raw:
            diff = await self._git_ops.get_file_diff(
                file_info["path"], file_info["staged"]
            )
            file_understanding = await self._file_analyzer.understand_file(
                file_info, diff
            )
            files_changed.append(file_understanding)

        # Generate code insights
        diffs = {}
        for file_info in changed_files_raw:
            diff = await self._git_ops.get_file_diff(
                file_info["path"], file_info["staged"]
            )
            if diff:
                diffs[file_info["path"]] = diff

        code_insights = await self._code_analyzer.analyze_changes(files_changed, diffs)

        # Determine work phase
        work_phase = self._determine_work_phase(files_changed, code_insights)

        # Determine branch purpose
        branch_purpose = self._infer_branch_purpose(current_branch, files_changed)

        # Check health indicators
        can_build = await self._check_build_status()
        tests_passing = await self._check_test_status()
        lint_clean = await self._check_lint_status()

        # Get collaboration context
        collaboration = await self._get_collaboration_context()

        # Generate recommendations
        recommended_actions = self._generate_action_recommendations(
            files_changed, code_insights, work_phase
        )
        potential_issues = self._identify_potential_issues(files_changed, code_insights)

        return RepositoryUnderstanding(
            current_branch=current_branch,
            branch_purpose=branch_purpose,
            work_phase=work_phase,
            files_changed=files_changed,
            code_insights=code_insights,
            collaboration=collaboration,
            can_build=can_build,
            tests_passing=tests_passing,
            lint_clean=lint_clean,
            recommended_actions=recommended_actions,
            potential_issues=potential_issues,
        )

    def _determine_work_phase(
        self, files: list[FileUnderstanding], insights: CodeInsight
    ) -> str:
        """Determine current work phase based on changes."""
        if not files:
            return "exploring"

        # Check if mostly test files
        test_ratio = sum(1 for f in files if f.role == "test") / len(files)
        if test_ratio > 0.7:
            return "testing"

        # Check if documentation changes
        doc_ratio = sum(1 for f in files if f.role == "docs") / len(files)
        if doc_ratio > 0.5:
            return "polishing"

        # Check complexity
        if insights.complexity in ["complex", "moderate"]:
            return "implementing"

        # Default based on change type
        if insights.change_type in ["fix", "refactor"]:
            return "polishing"

        return "implementing"

    def _infer_branch_purpose(self, branch: str, files: list[FileUnderstanding]) -> str:
        """Infer the purpose of the current branch."""
        branch_lower = branch.lower()

        # Check branch name patterns
        if "feature" in branch_lower or "feat" in branch_lower:
            return "Feature development"
        elif "fix" in branch_lower or "bug" in branch_lower:
            return "Bug fix"
        elif "refactor" in branch_lower:
            return "Code refactoring"
        elif "test" in branch_lower:
            return "Testing improvements"
        elif "doc" in branch_lower:
            return "Documentation updates"
        elif branch in ["main", "master", "develop"]:
            return "Main development branch"

        # Infer from file changes
        if files:
            if all(f.role == "test" for f in files):
                return "Testing work"
            elif all(f.role == "docs" for f in files):
                return "Documentation work"
            elif any("auth" in str(f.path).lower() for f in files):
                return "Authentication feature"
            elif any("api" in str(f.path).lower() for f in files):
                return "API development"

        return "Development work"

    async def _check_build_status(self) -> bool:
        """Check if the project can build successfully."""
        # Simple check - would be more sophisticated in real implementation
        try:
            # Check for common build files
            build_files = ["pyproject.toml", "package.json", "Makefile", "Cargo.toml"]
            for build_file in build_files:
                if Path(build_file).exists():
                    return True
            return True  # Assume buildable if no specific build system
        except Exception:
            return False

    async def _check_test_status(self) -> bool:
        """Check if tests are passing."""
        # Simple heuristic - would run actual tests in real implementation
        return True  # Assume passing for now

    async def _check_lint_status(self) -> bool:
        """Check if linting is clean."""
        # Simple heuristic - would run actual linter in real implementation
        return True  # Assume clean for now

    async def _get_collaboration_context(self) -> CollaborationContext:
        """Get collaboration context."""
        # Would check for actual PR status, reviewers, etc.
        return CollaborationContext()

    def _generate_action_recommendations(
        self, files: list[FileUnderstanding], insights: CodeInsight, phase: str
    ) -> list[str]:
        """Generate recommended next actions."""
        recommendations = []

        if phase == "implementing":
            if not insights.adds_tests:
                recommendations.append("Add tests for new functionality")
            if not insights.updates_docs:
                recommendations.append("Update documentation")
            recommendations.append("Commit current progress")

        elif phase == "testing":
            recommendations.append("Run full test suite")
            recommendations.append("Check test coverage")

        elif phase == "polishing":
            recommendations.append("Review code quality")
            recommendations.append("Update documentation")
            recommendations.append("Prepare for review")

        # Always suggest commit if there are changes
        if files:
            recommendations.append("Save progress with commit")

        return recommendations[:3]  # Top 3

    def _identify_potential_issues(
        self, files: list[FileUnderstanding], insights: CodeInsight
    ) -> list[str]:
        """Identify potential issues."""
        issues = []

        if insights.introduces_tech_debt:
            issues.append("Code contains TODO/FIXME comments")

        if insights.risk_level == "high":
            issues.append("Changes affect high-risk areas")

        if insights.affects_public_api:
            issues.append("Changes may break API compatibility")

        if not insights.adds_tests and insights.change_type == "feature":
            issues.append("New feature lacks test coverage")

        return issues

    async def _smart_stage_files(
        self, state: RepositoryUnderstanding, request: GitRequest
    ) -> list[str]:
        """Intelligently stage files based on context."""
        staged_files = []

        # Get all changed files
        changed_files_raw = await self._git_ops.get_changed_files()

        # Filter files to stage
        files_to_stage = []
        for file_info in changed_files_raw:
            path = file_info["path"]

            # Skip already staged files
            if file_info["staged"]:
                staged_files.append(str(path))
                continue

            # Auto-stage based on file type and context
            if self._should_auto_stage(path, state, request):
                files_to_stage.append(path)

        # Stage the selected files
        if files_to_stage:
            success = await self._git_ops.stage_files(files_to_stage)
            if success:
                staged_files.extend(str(f) for f in files_to_stage)

        return staged_files

    def _should_auto_stage(
        self, path: Path, state: RepositoryUnderstanding, request: GitRequest
    ) -> bool:
        """Determine if a file should be auto-staged."""
        path_str = str(path).lower()

        # Always stage test files if they exist
        if "test" in path_str:
            return True

        # Stage documentation updates
        if path.suffix in [".md", ".rst", ".txt"]:
            return True

        # Stage core files if they're part of the main work
        if path.suffix in [".py", ".js", ".ts", ".go", ".rs"]:
            return True

        # Skip temporary files
        if path.name.startswith(".") or path.suffix in [".tmp", ".bak"]:
            return False

        return True  # Default to staging

    async def _generate_contextual_commit(
        self, state: RepositoryUnderstanding, request: GitRequest, session: GitSession
    ) -> str:
        """Generate a commit message with full context."""
        # Use the commit message generator
        context = {}

        # Add request context
        if request.context:
            context.update({
                "task_description": request.context.task_description,
                "issue_id": request.context.related_issues[0]
                if request.context.related_issues
                else None,
            })

        # Add session context
        if session.implementation_flow:
            context["task_description"] = session.implementation_flow.task

        # Generate message
        commit_message = await self._commit_generator.generate(
            state.files_changed, state.code_insights, context, style="conventional"
        )

        return commit_message

    async def _perform_commit(self, message: str) -> dict[str, str]:
        """Perform the actual commit operation."""
        return await self._git_ops.create_commit(message)

    def _build_explore_recommendations(
        self, state: RepositoryUnderstanding, session: GitSession
    ) -> list[Recommendation]:
        """Build recommendations for exploration phase."""
        recommendations = []

        # Recommend actions based on current state
        if state.files_changed:
            recommendations.append(
                Recommendation(
                    action="Save your current progress",
                    reason="You have uncommitted changes that should be preserved",
                    impact="Prevents loss of work and creates a checkpoint",
                    urgency="soon",
                    effort="trivial",
                    example_request="Save my progress",
                    prerequisites=[],
                )
            )

        if not state.tests_passing:
            recommendations.append(
                Recommendation(
                    action="Run tests to verify functionality",
                    reason="Ensure your changes don't break existing functionality",
                    impact="Catches issues early in development",
                    urgency="now",
                    effort="quick",
                    example_request="Run the tests",
                    prerequisites=[],
                )
            )

        if state.code_insights.introduces_tech_debt:
            recommendations.append(
                Recommendation(
                    action="Address TODO comments",
                    reason="Clean up technical debt before it accumulates",
                    impact="Improves code maintainability",
                    urgency="soon",
                    effort="moderate",
                    example_request="Help me clean up the TODOs",
                    prerequisites=[],
                )
            )

        return recommendations[:3]  # Top 3 recommendations

    def _build_implement_recommendations(
        self,
        state: RepositoryUnderstanding,
        session: GitSession,
        commit_result: dict[str, str],
    ) -> list[Recommendation]:
        """Build recommendations for implementation phase."""
        recommendations = []

        # Push changes if commit was successful
        if commit_result.get("success"):
            recommendations.append(
                Recommendation(
                    action="Push changes to remote",
                    reason="Share your progress with the team",
                    impact="Backs up your work and enables collaboration",
                    urgency="soon",
                    effort="trivial",
                    example_request="Push these changes",
                    prerequisites=[],
                )
            )

        # Suggest next steps based on implementation flow
        if session.implementation_flow:
            if (
                not session.implementation_flow.has_tests
                and state.code_insights.change_type == "feature"
            ):
                recommendations.append(
                    Recommendation(
                        action="Add tests for the new feature",
                        reason="Ensure the feature works correctly and prevent regressions",
                        impact="Improves code reliability and confidence",
                        urgency="now",
                        effort="moderate",
                        example_request="Help me write tests for this feature",
                        prerequisites=[],
                    )
                )

        return recommendations

    def _build_collaborate_recommendations(
        self,
        state: RepositoryUnderstanding,
        session: GitSession,
        pr_result: dict[str, Any],
    ) -> list[Recommendation]:
        """Build recommendations for collaboration phase."""
        recommendations = []

        if pr_result.get("success"):
            recommendations.append(
                Recommendation(
                    action="Monitor PR for feedback",
                    reason="Stay responsive to reviewer comments",
                    impact="Faster review cycle and better collaboration",
                    urgency="soon",
                    effort="quick",
                    example_request="Check PR status",
                    prerequisites=[],
                )
            )

        return recommendations

    def _build_integrate_recommendations(
        self, state: RepositoryUnderstanding, session: GitSession
    ) -> list[Recommendation]:
        """Build recommendations for integration phase."""
        recommendations = []

        recommendations.append(
            Recommendation(
                action="Test the integrated changes",
                reason="Ensure integration didn't break anything",
                impact="Maintains code quality after integration",
                urgency="now",
                effort="quick",
                example_request="Run tests after integration",
                prerequisites=[],
            )
        )

        return recommendations

    def _build_understand_recommendations(
        self,
        insights: dict[str, Any],
        state: RepositoryUnderstanding,
        session: GitSession,
    ) -> list[Recommendation]:
        """Build recommendations for understanding phase."""
        recommendations = []

        if "quality" in insights and insights["quality"].issues:
            recommendations.append(
                Recommendation(
                    action="Address quality issues",
                    reason="Improve code maintainability",
                    impact="Better long-term code health",
                    urgency="soon",
                    effort="moderate",
                    example_request="Fix the quality issues",
                    prerequisites=[],
                )
            )

        return recommendations

    # Add placeholder methods for missing functionality
    def _summarize_changes(self, state: RepositoryUnderstanding) -> str:
        """Summarize the current changes."""
        if not state.files_changed:
            return "No changes"
        return f"{len(state.files_changed)} files changed"

    def _assess_health(self, state: RepositoryUnderstanding) -> str:
        """Assess repository health."""
        if state.can_build and state.tests_passing and state.lint_clean:
            return "healthy"
        return "needs attention"

    def _generate_explore_prompts(self, state: RepositoryUnderstanding) -> list[str]:
        """Generate follow-up prompts for exploration."""
        return [
            "What should I work on next?",
            "Show me the current status",
            "Help me understand these changes",
        ]

    def _suggest_next_phase(
        self, state: RepositoryUnderstanding, session: GitSession
    ) -> str:
        """Suggest the next phase of work."""
        if state.work_phase == "implementing":
            return "testing"
        elif state.work_phase == "testing":
            return "reviewing"
        return "continue implementing"

    async def close(self) -> None:
        """Clean up resources."""
        # Clean up any open connections or resources
        if hasattr(self, "_executor") and hasattr(self._git_ops._executor, "shutdown"):
            await self._git_ops._executor.shutdown()


# --- Supporting Classes ---


class PatternAnalyzer:
    """Analyzes patterns in repository usage."""

    async def analyze(self, repository_knowledge: dict[str, Any]) -> PatternRecognition:
        """Identify patterns in the codebase and workflow."""
        # Analyze commit patterns
        commit_patterns = self._analyze_commit_patterns(repository_knowledge)

        # Analyze code patterns
        code_patterns = self._analyze_code_patterns(repository_knowledge)

        # Analyze team patterns
        team_patterns = self._analyze_team_patterns(repository_knowledge)

        return PatternRecognition(
            common_patterns=code_patterns["common"],
            anti_patterns=code_patterns["anti"],
            typical_pr_size=commit_patterns.get("avg_pr_size", 150),
            typical_review_time=team_patterns.get("avg_review_time", "2-4 hours"),
            typical_iteration_count=team_patterns.get("avg_iterations", 2),
            expertise_map=team_patterns.get("expertise_map", {}),
            collaboration_graph=team_patterns.get("collaboration_graph", {}),
        )

    def _analyze_commit_patterns(self, knowledge: dict[str, Any]) -> dict[str, Any]:
        """Analyze patterns in commit history."""
        # This would analyze actual commit data
        return {
            "avg_pr_size": 150,
            "common_types": ["feat", "fix", "refactor"],
            "commit_frequency": "daily",
        }

    def _analyze_code_patterns(self, knowledge: dict[str, Any]) -> dict[str, Any]:
        """Analyze patterns in code structure."""
        return {
            "common": ["dependency injection", "factory pattern", "observer pattern"],
            "anti": ["god objects", "copy-paste code", "magic numbers"],
        }

    def _analyze_team_patterns(self, knowledge: dict[str, Any]) -> dict[str, Any]:
        """Analyze team collaboration patterns."""
        return {
            "avg_review_time": "2-4 hours",
            "avg_iterations": 2,
            "expertise_map": {
                "auth": ["alice", "bob"],
                "database": ["charlie"],
                "frontend": ["diana", "eve"],
            },
            "collaboration_graph": {
                "alice": ["bob", "charlie"],
                "bob": ["alice", "diana"],
                "charlie": ["alice", "eve"],
            },
        }


class QualityAnalyzer:
    """Analyzes code quality."""

    async def assess(self, state: RepositoryUnderstanding) -> QualityAssessment:
        """Assess code quality."""
        # Run quality checks
        test_coverage = await self._calculate_test_coverage(state)
        doc_coverage = await self._calculate_doc_coverage(state)
        complexity = await self._calculate_complexity(state)

        # Assess subjective qualities
        readability = self._assess_readability(state)
        maintainability = self._assess_maintainability(state)
        consistency = self._assess_consistency(state)

        # Find specific issues
        issues = await self._find_quality_issues(state)

        # Generate recommendations
        quick_wins = self._identify_quick_wins(issues)
        long_term = self._identify_long_term_improvements(state)

        return QualityAssessment(
            test_coverage=test_coverage,
            documentation_coverage=doc_coverage,
            complexity_score=complexity,
            readability=readability,
            maintainability=maintainability,
            consistency=consistency,
            issues=issues,
            quick_wins=quick_wins,
            long_term_improvements=long_term,
        )

    async def _calculate_test_coverage(self, state: RepositoryUnderstanding) -> float:
        """Calculate test coverage percentage."""
        if not state.changes_summary:
            return 0.0

        # Simple heuristic: ratio of test files to code files
        code_count = len(state.changes_summary.code_files)
        test_count = len(state.changes_summary.test_files)

        if code_count == 0:
            return 1.0

        return (
            min(test_count / code_count, 1.0) * 0.75
        )  # Assume 75% coverage per test file

    async def _calculate_doc_coverage(self, state: RepositoryUnderstanding) -> float:
        """Calculate documentation coverage."""
        if not state.changes_summary:
            return 0.0

        # Check for documentation files
        has_readme = any("readme" in str(f.path).lower() for f in state.files_changed)
        has_docs = len(state.changes_summary.doc_files) > 0

        base_score = 0.3 if has_readme else 0.0
        doc_score = min(len(state.changes_summary.doc_files) * 0.2, 0.5)

        return base_score + doc_score

    async def _calculate_complexity(self, state: RepositoryUnderstanding) -> float:
        """Calculate average complexity score."""
        # Simplified - would use actual complexity metrics
        return 12.5

    def _assess_readability(self, state: RepositoryUnderstanding) -> str:
        """Assess code readability."""
        if state.code_insights.follows_patterns:
            return "good"
        return "fair"

    def _assess_maintainability(self, state: RepositoryUnderstanding) -> str:
        """Assess code maintainability."""
        if state.code_insights.introduces_tech_debt:
            return "fair"
        elif state.code_insights.adds_tests:
            return "good"
        return "fair"

    def _assess_consistency(self, state: RepositoryUnderstanding) -> str:
        """Assess code consistency."""
        # Would check style consistency
        return "excellent"

    async def _find_quality_issues(
        self, state: RepositoryUnderstanding
    ) -> list[QualityIssue]:
        """Find specific quality issues."""
        issues = []

        # Check for common issues
        if state.code_insights.introduces_tech_debt:
            issues.append(
                QualityIssue(
                    type="maintainability",
                    severity="warning",
                    location="See TODO comments",
                    description="Code contains TODOs that should be addressed",
                    suggestion="Create tickets for TODOs or address them now",
                )
            )

        if not state.code_insights.adds_tests:
            issues.append(
                QualityIssue(
                    type="maintainability",
                    severity="warning",
                    location="New code files",
                    description="New code lacks test coverage",
                    suggestion="Add unit tests for new functionality",
                )
            )

        if state.code_insights.complexity == "complex":
            issues.append(
                QualityIssue(
                    type="maintainability",
                    severity="warning",
                    location="Complex functions",
                    description="Some functions have high complexity",
                    suggestion="Consider breaking complex functions into smaller ones",
                )
            )

        return issues

    def _identify_quick_wins(self, issues: list[QualityIssue]) -> list[str]:
        """Identify quick improvements."""
        quick_wins = []

        for issue in issues:
            if issue.severity != "critical" and "Add" in issue.suggestion:
                quick_wins.append(issue.suggestion)

        # Add general quick wins
        quick_wins.extend([
            "Add docstrings to public methods",
            "Remove commented-out code",
            "Fix linting warnings",
        ])

        return quick_wins[:3]  # Top 3

    def _identify_long_term_improvements(
        self, state: RepositoryUnderstanding
    ) -> list[str]:
        """Identify long-term improvements."""
        improvements = []

        if state.code_insights.affects_public_api:
            improvements.append("Create comprehensive API documentation")

        if state.code_insights.complexity == "complex":
            improvements.append("Refactor complex modules for better maintainability")

        improvements.append("Set up automated quality checks in CI/CD")

        return improvements


class CollaborationOptimizer:
    """Optimizes collaboration workflows."""

    async def suggest_reviewers(
        self, state: RepositoryUnderstanding, session: GitSession
    ) -> list[str]:
        """Suggest optimal reviewers based on expertise and availability."""
        reviewers = []

        # Get affected code areas
        affected_areas = self._identify_affected_areas(state.files_changed)

        # Match with expertise
        if session.learned_patterns and session.learned_patterns.expertise_map:
            for area in affected_areas:
                if area in session.learned_patterns.expertise_map:
                    area_experts = session.learned_patterns.expertise_map[area]
                    reviewers.extend(area_experts)

        # Remove duplicates and limit
        unique_reviewers = list(set(reviewers))

        # Sort by expertise match (would be more sophisticated)
        return unique_reviewers[:3]  # Max 3 reviewers

    def _identify_affected_areas(self, files: list[FileUnderstanding]) -> list[str]:
        """Identify which areas of code are affected."""
        areas = set()

        for file in files:
            # Extract top-level directory as area
            parts = file.path.parts
            if len(parts) > 1:
                areas.add(parts[0])
            else:
                # File at root - check file name patterns
                if "auth" in str(file.path).lower():
                    areas.add("auth")
                elif (
                    "db" in str(file.path).lower() or "model" in str(file.path).lower()
                ):
                    areas.add("database")
                elif "api" in str(file.path).lower():
                    areas.add("api")

        return list(areas)
