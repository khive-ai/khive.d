# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Agent-centric Git Service implementation.

A git service designed from the ground up for AI agents, focusing on
natural language understanding, contextual awareness, and workflow intelligence.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from khive.services.git.nlp import IntentDetector, ResponseGenerator
from khive.services.git.parts import (
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
    Git service optimized for AI agents.

    Key principles:
    - Natural language is the primary interface
    - Maintains context across operations
    - Provides rich semantic understanding
    - Offers intelligent recommendations
    - Learns from usage patterns
    """

    def __init__(self):
        """Initialize the Git service."""
        self._sessions: Dict[str, GitSession] = {}
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

    async def handle_request(self, request: GitRequest) -> GitResponse:
        """
        Handle a git request with natural language understanding.

        This is the single entry point for all git operations.
        """
        # Get or create session
        session = self._get_or_create_session(
            request.agent_id or "anonymous", request.conversation_id
        )

        # Track request
        session.add_request(request.request)

        try:
            # Understand intent
            intent, confidence = self._intent_detector.detect_intent(
                request.request,
                request.context,
                await self._get_repository_state(),
                session,
            )
            log_msg(f"Understood intent: {intent} (confidence: {confidence:.2f})")

            # Route to appropriate workflow
            if intent == WorkIntent.EXPLORE:
                return await self._handle_explore(request, session)
            elif intent == WorkIntent.IMPLEMENT:
                return await self._handle_implement(request, session)
            elif intent == WorkIntent.COLLABORATE:
                return await self._handle_collaborate(request, session)
            elif intent == WorkIntent.INTEGRATE:
                return await self._handle_integrate(request, session)
            elif intent == WorkIntent.RELEASE:
                return await self._handle_release(request, session)
            elif intent == WorkIntent.UNDERSTAND:
                return await self._handle_understand(request, session)
            elif intent == WorkIntent.UNDO:
                return await self._handle_undo(request, session)
            elif intent == WorkIntent.ORGANIZE:
                return await self._handle_organize(request, session)

        except Exception as e:
            return await self._handle_error(e, request, session)

    # --- Workflow Handlers ---

    async def _handle_explore(
        self, request: GitRequest, session: GitSession
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
        self, request: GitRequest, session: GitSession
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
        self, request: GitRequest, session: GitSession
    ) -> GitResponse:
        """Handle collaboration requests."""
        state = await self._get_repository_state()
        actions_taken = []

        # Ensure changes are committed
        if state.has_uncommitted_changes or state.has_staged_changes:
            commit_response = await self._handle_implement(request, session)
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
        self, request: GitRequest, session: GitSession
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
        self, request: GitRequest, session: GitSession
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
            commit_response = await self._handle_implement(request, session)
            actions_taken.extend(commit_response.actions_taken)
            state = commit_response.repository_state

        # Ensure we're on the main branch
        if state.current_branch != "main":
            # Create PR if needed
            if not state.existing_pr:
                pr_response = await self._handle_collaborate(request, session)
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
        self, request: GitRequest, session: GitSession
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
        self, request: GitRequest, session: GitSession
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
        self, request: GitRequest, session: GitSession
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

    # --- Helper Methods (continued) ---

    async def _handle_error(
        self, error: Exception, request: GitRequest, session: GitSession
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
        )

    def _get_or_create_session(
        self, agent_id: str, conversation_id: Optional[str] = None
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

    async def close(self) -> None:
        """Clean up resources."""
        # Clean up any open connections or resources
        if hasattr(self, "_executor") and hasattr(self._git_ops._executor, "shutdown"):
            await self._git_ops._executor.shutdown()


# --- Supporting Classes ---


class PatternAnalyzer:
    """Analyzes patterns in repository usage."""

    async def analyze(self, repository_knowledge: Dict[str, Any]) -> PatternRecognition:
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

    def _analyze_commit_patterns(self, knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze patterns in commit history."""
        # This would analyze actual commit data
        return {
            "avg_pr_size": 150,
            "common_types": ["feat", "fix", "refactor"],
            "commit_frequency": "daily",
        }

    def _analyze_code_patterns(self, knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze patterns in code structure."""
        return {
            "common": ["dependency injection", "factory pattern", "observer pattern"],
            "anti": ["god objects", "copy-paste code", "magic numbers"],
        }

    def _analyze_team_patterns(self, knowledge: Dict[str, Any]) -> Dict[str, Any]:
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
    ) -> List[QualityIssue]:
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

    def _identify_quick_wins(self, issues: List[QualityIssue]) -> List[str]:
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
    ) -> List[str]:
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
    ) -> List[str]:
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

    def _identify_affected_areas(self, files: List[FileUnderstanding]) -> List[str]:
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
