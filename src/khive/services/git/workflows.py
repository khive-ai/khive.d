# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Workflow implementations for Git Service.

This module contains the concrete implementations of git workflows,
handling the actual git operations in an agent-friendly manner.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from khive.clients.executor import AsyncExecutor
from khive.connections.match_endpoint import match_endpoint
from khive.services.git.parts import (
    CodeInsight,
    FileUnderstanding,
)
from khive.utils import CommandResult, git_run, run_command


class GitOperations:
    """Low-level git operations with agent-friendly error handling."""

    def __init__(self):
        self._executor = AsyncExecutor(max_concurrency=5)

    async def get_current_branch(self) -> str:
        """Get the current branch name."""
        result = git_run(["branch", "--show-current"], capture=True, check=False)

        if isinstance(result, CommandResult) and result.success:
            return result.stdout.strip()

        # Fallback for detached HEAD
        result = git_run(["rev-parse", "--short", "HEAD"], capture=True, check=True)

        if isinstance(result, CommandResult):
            return f"detached-{result.stdout.strip()}"

        return "unknown"

    async def get_changed_files(self) -> List[Dict[str, Any]]:
        """Get list of changed files with details."""
        changed_files = []

        # Get staged files
        staged_result = git_run(
            ["diff", "--cached", "--name-status"], capture=True, check=False
        )

        if isinstance(staged_result, CommandResult) and staged_result.stdout:
            for line in staged_result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        changed_files.append({
                            "path": Path(parts[1]),
                            "status": self._parse_status(parts[0]),
                            "staged": True,
                        })

        # Get unstaged files
        unstaged_result = git_run(["diff", "--name-status"], capture=True, check=False)

        if isinstance(unstaged_result, CommandResult) and unstaged_result.stdout:
            for line in unstaged_result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        path = Path(parts[1])
                        # Check if already in staged
                        if not any(f["path"] == path for f in changed_files):
                            changed_files.append({
                                "path": path,
                                "status": self._parse_status(parts[0]),
                                "staged": False,
                            })

        # Get untracked files
        untracked_result = git_run(
            ["ls-files", "--others", "--exclude-standard"], capture=True, check=False
        )

        if isinstance(untracked_result, CommandResult) and untracked_result.stdout:
            for line in untracked_result.stdout.strip().split("\n"):
                if line:
                    changed_files.append({
                        "path": Path(line),
                        "status": "added",
                        "staged": False,
                    })

        return changed_files

    async def get_file_diff(self, file_path: Path, staged: bool = False) -> str:
        """Get diff for a specific file."""
        cmd = ["diff"]
        if staged:
            cmd.append("--cached")
        cmd.append(str(file_path))

        result = git_run(cmd, capture=True, check=False)

        if isinstance(result, CommandResult):
            return result.stdout
        return ""

    async def stage_files(self, files: List[Path]) -> bool:
        """Stage specific files."""
        if not files:
            return True

        result = git_run(["add"] + [str(f) for f in files], check=False)

        return result == 0 or (isinstance(result, CommandResult) and result.success)

    async def create_commit(self, message: str) -> Dict[str, str]:
        """Create a commit with the given message."""
        # Write message to temp file to handle multi-line messages
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(message)
            msg_file = f.name

        try:
            result = git_run(["commit", "-F", msg_file], capture=True, check=False)

            if isinstance(result, CommandResult) and result.success:
                # Get commit SHA
                sha_result = git_run(["rev-parse", "HEAD"], capture=True, check=True)

                sha = "unknown"
                if isinstance(sha_result, CommandResult):
                    sha = sha_result.stdout.strip()

                return {"success": True, "sha": sha, "message": message}
            else:
                return {
                    "success": False,
                    "error": result.stderr
                    if isinstance(result, CommandResult)
                    else "Unknown error",
                }
        finally:
            import os

            os.unlink(msg_file)

    async def push_branch(
        self, branch: str, set_upstream: bool = True
    ) -> Dict[str, Any]:
        """Push branch to remote."""
        cmd = ["push"]

        if set_upstream:
            # Check if upstream is already set
            upstream_result = git_run(
                ["config", f"branch.{branch}.remote"], capture=True, check=False
            )

            if not (
                isinstance(upstream_result, CommandResult)
                and upstream_result.stdout.strip()
            ):
                cmd.extend(["--set-upstream", "origin", branch])
            else:
                cmd.extend(["origin", branch])
        else:
            cmd.extend(["origin", branch])

        result = git_run(cmd, capture=True, check=False)

        if isinstance(result, CommandResult):
            return {
                "success": result.success,
                "output": result.stdout,
                "error": result.stderr if not result.success else None,
            }

        return {"success": result == 0}

    async def fetch_remote(self, remote: str = "origin") -> bool:
        """Fetch from remote."""
        result = git_run(["fetch", remote], check=False)
        return result == 0 or (isinstance(result, CommandResult) and result.success)

    async def merge_branch(self, branch: str) -> Dict[str, Any]:
        """Merge a branch into current branch."""
        result = git_run(["merge", branch], capture=True, check=False)

        if isinstance(result, CommandResult):
            # Check for conflicts
            if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
                # Get conflict details
                conflicts = await self._get_conflict_details()
                return {
                    "success": False,
                    "conflicts": conflicts,
                    "error": "Merge conflicts detected",
                }

            return {"success": result.success, "output": result.stdout}

        return {"success": result == 0}

    async def get_commits_between(
        self, base: str, head: str = "HEAD", limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get commits between two refs."""
        result = git_run(
            [
                "log",
                f"{base}..{head}",
                f"--max-count={limit}",
                "--pretty=format:%H|%s|%an|%ae|%ai|%b",
            ],
            capture=True,
            check=False,
        )

        commits = []
        if isinstance(result, CommandResult) and result.stdout:
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|", 5)
                    if len(parts) >= 5:
                        commits.append({
                            "sha": parts[0],
                            "subject": parts[1],
                            "author": parts[2],
                            "email": parts[3],
                            "date": parts[4],
                            "body": parts[5] if len(parts) > 5 else "",
                        })

        return commits

    async def checkout_branch(self, branch: str, create: bool = False) -> bool:
        """Checkout a branch."""
        cmd = ["checkout"]
        if create:
            cmd.append("-b")
        cmd.append(branch)

        result = git_run(cmd, check=False)
        return result == 0 or (isinstance(result, CommandResult) and result.success)

    async def pull_latest(
        self, remote: str = "origin", branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pull latest changes."""
        cmd = ["pull", remote]
        if branch:
            cmd.append(branch)

        result = git_run(cmd, capture=True, check=False)

        if isinstance(result, CommandResult):
            return {
                "success": result.success,
                "output": result.stdout,
                "error": result.stderr if not result.success else None,
            }

        return {"success": result == 0}

    async def create_tag(self, tag_name: str, message: str, ref: str = "HEAD") -> bool:
        """Create an annotated tag."""
        result = git_run(["tag", "-a", tag_name, "-m", message, ref], check=False)
        return result == 0 or (isinstance(result, CommandResult) and result.success)

    async def push_tag(self, tag_name: str) -> bool:
        """Push a tag to remote."""
        result = git_run(["push", "origin", tag_name], check=False)
        return result == 0 or (isinstance(result, CommandResult) and result.success)

    async def reset_to_commit(
        self, ref: str, soft: bool = False, hard: bool = False
    ) -> bool:
        """Reset to a specific commit."""
        cmd = ["reset"]
        if soft:
            cmd.append("--soft")
        elif hard:
            cmd.append("--hard")
        else:
            cmd.append("--mixed")
        cmd.append(ref)

        result = git_run(cmd, check=False)
        return result == 0 or (isinstance(result, CommandResult) and result.success)

    async def revert_commit(self, sha: str) -> Dict[str, Any]:
        """Create a revert commit."""
        result = git_run(["revert", sha, "--no-edit"], capture=True, check=False)

        if isinstance(result, CommandResult):
            return {
                "success": result.success,
                "output": result.stdout,
                "error": result.stderr if not result.success else None,
            }

        return {"success": result == 0}

    async def stash_changes(self, message: Optional[str] = None) -> Dict[str, Any]:
        """Stash current changes."""
        cmd = ["stash", "push"]
        if message:
            cmd.extend(["-m", message])

        result = git_run(cmd, capture=True, check=False)

        if isinstance(result, CommandResult):
            return {
                "success": result.success,
                "stash_ref": self._extract_stash_ref(result.stdout),
                "output": result.stdout,
            }

        return {"success": result == 0}

    async def list_stashes(self) -> List[Dict[str, Any]]:
        """List all stashes."""
        result = git_run(["stash", "list"], capture=True, check=False)

        stashes = []
        if isinstance(result, CommandResult) and result.stdout:
            for line in result.stdout.strip().split("\n"):
                if line:
                    # Parse stash line: stash@{0}: WIP on main: abc123 commit message
                    match = re.match(r"(stash@\{(\d+)\}): (.+)", line)
                    if match:
                        stashes.append({
                            "ref": match.group(1),
                            "index": int(match.group(2)),
                            "message": match.group(3),
                        })

        return stashes

    async def drop_stash(self, index: int) -> bool:
        """Drop a specific stash."""
        result = git_run(["stash", "drop", f"stash@{{{index}}}"], check=False)
        return result == 0 or (isinstance(result, CommandResult) and result.success)

    async def clean_working_directory(self) -> bool:
        """Clean working directory (remove untracked files)."""
        # First do a dry run to show what would be removed
        dry_run = git_run(["clean", "-n", "-d"], capture=True, check=False)

        # Actually clean
        result = git_run(["clean", "-f", "-d"], check=False)
        return result == 0 or (isinstance(result, CommandResult) and result.success)

    async def get_merged_branches(self, base: str = "main") -> List[str]:
        """Get list of branches merged into base."""
        result = git_run(
            ["branch", "--merged", base, "--format=%(refname:short)"],
            capture=True,
            check=False,
        )

        branches = []
        if isinstance(result, CommandResult) and result.stdout:
            for line in result.stdout.strip().split("\n"):
                if line and line != base:
                    branches.append(line)

        return branches

    async def delete_branch(self, branch: str, force: bool = False) -> bool:
        """Delete a local branch."""
        cmd = ["branch", "-d" if not force else "-D", branch]
        result = git_run(cmd, check=False)
        return result == 0 or (isinstance(result, CommandResult) and result.success)

    async def delete_remote_branch(self, branch: str, remote: str = "origin") -> bool:
        """Delete a remote branch."""
        result = git_run(["push", remote, "--delete", branch], check=False)
        return result == 0 or (isinstance(result, CommandResult) and result.success)

    async def remote_branch_exists(self, branch: str, remote: str = "origin") -> bool:
        """Check if a remote branch exists."""
        result = git_run(
            ["ls-remote", "--heads", remote, branch], capture=True, check=False
        )

        if isinstance(result, CommandResult):
            return bool(result.stdout.strip())
        return False

    async def remove_files_by_pattern(
        self, pattern: str, track: bool = True
    ) -> List[str]:
        """Remove files matching a pattern."""
        import glob

        removed = []

        for file_path in glob.glob(pattern, recursive=True):
            if os.path.isfile(file_path):
                os.remove(file_path)
                removed.append(file_path)

                if track:
                    # Stage the removal
                    git_run(["rm", "--cached", file_path], check=False)

        return removed

    def _parse_status(self, status_code: str) -> str:
        """Parse git status code to human-readable status."""
        status_map = {
            "A": "added",
            "M": "modified",
            "D": "deleted",
            "R": "renamed",
            "C": "copied",
            "U": "updated",
            "?": "untracked",
        }
        return status_map.get(status_code[0], "unknown")

    async def _get_conflict_details(self) -> List[Dict[str, str]]:
        """Get details about merge conflicts."""
        result = git_run(
            ["diff", "--name-only", "--diff-filter=U"], capture=True, check=False
        )

        conflicts = []
        if isinstance(result, CommandResult) and result.stdout:
            for file in result.stdout.strip().split("\n"):
                if file:
                    conflicts.append({"file": file, "type": "merge_conflict"})

        return conflicts

    def _extract_stash_ref(self, output: str) -> Optional[str]:
        """Extract stash reference from stash output."""
        match = re.search(r"(stash@\{\d+\})", output)
        return match.group(1) if match else None


class FileAnalyzer:
    """Analyze files for semantic understanding."""

    def __init__(self):
        self._extension_roles = {
            # Code files
            ".py": "core",
            ".js": "core",
            ".ts": "core",
            ".java": "core",
            ".cpp": "core",
            ".c": "core",
            ".go": "core",
            ".rs": "core",
            ".rb": "core",
            # Test files (override by path)
            "_test.py": "test",
            ".test.js": "test",
            ".spec.ts": "test",
            # Documentation
            ".md": "docs",
            ".rst": "docs",
            ".txt": "docs",
            # Configuration
            ".json": "config",
            ".yaml": "config",
            ".yml": "config",
            ".toml": "config",
            ".ini": "config",
            # Build
            "Makefile": "build",
            ".dockerfile": "build",
            "Dockerfile": "build",
        }

    async def understand_file(
        self, file_info: Dict[str, Any], diff: Optional[str] = None
    ) -> FileUnderstanding:
        """Create deep understanding of a file."""
        path = file_info["path"]

        # Determine role
        role = self._determine_role(path)

        # Analyze changes
        change_summary = (
            "File created" if file_info["status"] == "added" else "File modified"
        )
        change_magnitude = self._assess_change_magnitude(diff) if diff else "minor"

        # Check for TODOs and FIXMEs
        has_todos = False
        has_fixmes = False
        if diff:
            has_todos = bool(re.search(r"\+.*TODO", diff))
            has_fixmes = bool(re.search(r"\+.*FIXME", diff))

        # Find relationships
        tests_this = []
        tested_by = []

        if role == "core":
            # Look for test files
            test_patterns = [
                path.stem + "_test" + path.suffix,
                "test_" + path.name,
                path.stem + ".test" + path.suffix,
                path.stem + ".spec" + path.suffix,
            ]
            # In real implementation, would check if these files exist

        elif role == "test":
            # Find what this tests
            if path.stem.startswith("test_"):
                tests_this.append(Path(path.stem[5:] + path.suffix))
            elif path.stem.endswith("_test"):
                tests_this.append(Path(path.stem[:-5] + path.suffix))

        return FileUnderstanding(
            path=path,
            role=role,
            change_summary=change_summary,
            change_magnitude=change_magnitude,
            tests_this=tests_this,
            tested_by=tested_by,
            has_todo_comments=has_todos,
            has_fixme_comments=has_fixmes,
            follows_conventions=True,  # Would implement convention checking
        )

    def _determine_role(self, path: Path) -> str:
        """Determine the role of a file."""
        # Check path patterns first
        path_str = str(path).lower()

        if "test" in path_str or "spec" in path_str:
            return "test"
        elif "example" in path_str or "sample" in path_str:
            return "example"
        elif "generated" in path_str or "auto" in path_str:
            return "generated"

        # Check by extension
        for pattern, role in self._extension_roles.items():
            if path.name.endswith(pattern):
                return role

        return "core"  # Default

    def _assess_change_magnitude(self, diff: str) -> str:
        """Assess how significant a change is."""
        if not diff:
            return "minor"

        lines = diff.split("\n")
        additions = sum(
            1 for line in lines if line.startswith("+") and not line.startswith("+++")
        )
        deletions = sum(
            1 for line in lines if line.startswith("-") and not line.startswith("---")
        )

        total_changes = additions + deletions

        if total_changes < 10:
            return "cosmetic"
        elif total_changes < 50:
            return "minor"
        elif total_changes < 200:
            return "significant"
        else:
            return "major"


class CodeAnalyzer:
    """Analyze code changes for insights."""

    async def analyze_changes(
        self, files: List[FileUnderstanding], diffs: Optional[Dict[Path, str]] = None
    ) -> CodeInsight:
        """Analyze code changes to produce insights."""
        primary_changes = []
        side_effects = []

        # Categorize files
        has_core_changes = any(f.role == "core" for f in files)
        has_test_changes = any(f.role == "test" for f in files)
        has_doc_changes = any(f.role == "docs" for f in files)

        # Analyze primary changes
        if has_core_changes:
            core_files = [f for f in files if f.role == "core"]
            if len(core_files) == 1:
                primary_changes.append(f"Modified {core_files[0].path.name}")
            else:
                primary_changes.append(f"Modified {len(core_files)} core files")

        if has_test_changes:
            test_files = [f for f in files if f.role == "test"]
            primary_changes.append(f"Updated {len(test_files)} test files")

        # Determine change type
        change_type = self._determine_change_type(files, diffs)

        # Assess complexity
        complexity = self._assess_complexity(files)

        # Check for patterns
        adds_tests = has_test_changes
        updates_docs = has_doc_changes
        follows_patterns = True  # Would implement pattern checking

        # Check for tech debt indicators
        introduces_tech_debt = any(
            f.has_todo_comments or f.has_fixme_comments for f in files
        )

        # Assess risk
        risk_level = self._assess_risk(files, change_type, complexity)

        # Check API changes
        affects_public_api = self._check_api_changes(files, diffs)

        return CodeInsight(
            primary_changes=primary_changes,
            side_effects=side_effects,
            adds_tests=adds_tests,
            updates_docs=updates_docs,
            follows_patterns=follows_patterns,
            introduces_tech_debt=introduces_tech_debt,
            change_type=change_type,
            complexity=complexity,
            risk_level=risk_level,
            affects_public_api=affects_public_api,
            requires_migration=False,  # Would implement migration detection
            breaks_compatibility=False,  # Would implement compatibility checking
        )

    def _determine_change_type(
        self, files: List[FileUnderstanding], diffs: Optional[Dict[Path, str]] = None
    ) -> str:
        """Determine the type of change."""
        # Simple heuristics - would be more sophisticated
        if any(f.path.name.lower().startswith("fix") for f in files):
            return "fix"

        if any(f.role == "test" for f in files) and not any(
            f.role == "core" for f in files
        ):
            return "test"

        if any(f.role == "docs" for f in files) and not any(
            f.role == "core" for f in files
        ):
            return "docs"

        # Check if it's a refactor (changes but no new functionality)
        # Would analyze diffs for this

        return "feature"  # Default

    def _assess_complexity(self, files: List[FileUnderstanding]) -> str:
        """Assess the complexity of changes."""
        total_magnitude_score = 0
        magnitude_map = {"cosmetic": 1, "minor": 2, "significant": 3, "major": 4}

        for file in files:
            total_magnitude_score += magnitude_map.get(file.change_magnitude, 2)

        avg_score = total_magnitude_score / len(files) if files else 0

        if avg_score <= 1.5:
            return "trivial"
        elif avg_score <= 2.5:
            return "simple"
        elif avg_score <= 3.5:
            return "moderate"
        else:
            return "complex"

    def _assess_risk(
        self, files: List[FileUnderstanding], change_type: str, complexity: str
    ) -> str:
        """Assess risk level of changes."""
        # High risk indicators
        high_risk_patterns = ["auth", "security", "payment", "database"]

        for file in files:
            file_str = str(file.path).lower()
            if any(pattern in file_str for pattern in high_risk_patterns):
                return "high"

        # Risk based on complexity
        if complexity == "complex":
            return "medium" if change_type == "fix" else "high"
        elif complexity == "moderate":
            return "medium"

        return "low" if change_type in ["docs", "test"] else "safe"

    def _check_api_changes(
        self, files: List[FileUnderstanding], diffs: Optional[Dict[Path, str]] = None
    ) -> bool:
        """Check if changes affect public APIs."""
        api_indicators = ["api", "public", "export", "interface"]

        for file in files:
            if any(indicator in str(file.path).lower() for indicator in api_indicators):
                return True

        # Would also check diffs for function signature changes
        return False


class PRManager:
    """Manage pull request operations."""

    def __init__(self):
        self._gh_available = None

    async def create_pr(
        self,
        title: str,
        body: str,
        base: str = "main",
        head: Optional[str] = None,
        draft: bool = False,
        reviewers: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a pull request."""
        if not await self._check_gh():
            return {"success": False, "error": "GitHub CLI not available"}

        cmd = ["gh", "pr", "create", "--title", title, "--body", body, "--base", base]

        if head:
            cmd.extend(["--head", head])

        if draft:
            cmd.append("--draft")

        if reviewers:
            for reviewer in reviewers:
                cmd.extend(["--reviewer", reviewer])

        if labels:
            for label in labels:
                cmd.extend(["--label", label])

        result = run_command(cmd, capture=True, check=False)

        if isinstance(result, CommandResult) and result.success:
            # Extract PR number from output
            pr_url = result.stdout.strip()
            pr_number = pr_url.split("/")[-1] if "/" in pr_url else "unknown"

            return {
                "success": True,
                "url": pr_url,
                "number": pr_number,
                "title": title,
                "body": body,
                "reviewers": reviewers or [],
            }

        return {
            "success": False,
            "error": result.stderr
            if isinstance(result, CommandResult)
            else "Unknown error",
        }

    async def update_pr(
        self,
        pr_number: str,
        title: Optional[str] = None,
        body: Optional[str] = None,
        add_reviewers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update an existing pull request."""
        if not await self._check_gh():
            return {"success": False, "error": "GitHub CLI not available"}

        cmd = ["gh", "pr", "edit", pr_number]

        if title:
            cmd.extend(["--title", title])

        if body:
            cmd.extend(["--body", body])

        if add_reviewers:
            for reviewer in add_reviewers:
                cmd.extend(["--add-reviewer", reviewer])

        result = run_command(cmd, capture=True, check=False)

        return {
            "success": isinstance(result, CommandResult) and result.success,
            "number": pr_number,
        }

    async def get_pr_status(self, pr_number: str) -> Optional[Dict[str, Any]]:
        """Get status of a pull request."""
        if not await self._check_gh():
            return None

        result = run_command(
            [
                "gh",
                "pr",
                "view",
                pr_number,
                "--json",
                "state,reviews,statusCheckRollup",
            ],
            capture=True,
            check=False,
        )

        if isinstance(result, CommandResult) and result.success:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                pass

        return None

    async def _check_gh(self) -> bool:
        """Check if GitHub CLI is available."""
        if self._gh_available is None:
            result = run_command(["which", "gh"], capture=True, check=False)
            self._gh_available = isinstance(result, CommandResult) and result.success

        return self._gh_available


class CommitMessageGenerator:
    """Generate intelligent commit messages."""

    def __init__(self):
        self._llm_endpoint = None

    async def generate(
        self,
        files: List[FileUnderstanding],
        insights: CodeInsight,
        context: Optional[Dict[str, Any]] = None,
        style: str = "conventional",
    ) -> str:
        """Generate a commit message."""
        # Try LLM first
        llm_message = await self._generate_with_llm(files, insights, context, style)
        if llm_message:
            return llm_message

        # Fallback to rule-based
        return self._generate_rule_based(files, insights, context, style)

    async def _generate_with_llm(
        self,
        files: List[FileUnderstanding],
        insights: CodeInsight,
        context: Optional[Dict[str, Any]] = None,
        style: str = "conventional",
    ) -> Optional[str]:
        """Generate commit message using LLM."""
        try:
            if not self._llm_endpoint:
                self._llm_endpoint = match_endpoint("openai", "chat")

            # Build prompt
            prompt = self._build_llm_prompt(files, insights, context, style)

            response = await self._llm_endpoint.call({
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a git commit message generator. Generate clear, concise commit messages.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 500,
            })

            if hasattr(response, "choices") and response.choices:
                return response.choices[0].message.content.strip()

        except Exception as e:
            # Log error and fall back
            pass

        return None

    def _build_llm_prompt(
        self,
        files: List[FileUnderstanding],
        insights: CodeInsight,
        context: Optional[Dict[str, Any]] = None,
        style: str = "conventional",
    ) -> str:
        """Build prompt for LLM."""
        prompt_parts = []

        if style == "conventional":
            prompt_parts.append(
                "Generate a conventional commit message with format: type(scope): subject"
            )
            prompt_parts.append(
                "Valid types: feat, fix, docs, style, refactor, perf, test, build, ci, chore"
            )

        prompt_parts.append(f"\nChange type: {insights.change_type}")
        prompt_parts.append(f"Files changed: {len(files)}")

        # List key files
        key_files = [f for f in files if f.role == "core"][:3]
        if key_files:
            prompt_parts.append(
                f"Key files: {', '.join(str(f.path) for f in key_files)}"
            )

        # Add context
        if context:
            if "task_description" in context:
                prompt_parts.append(f"\nTask: {context['task_description']}")
            if "issue_id" in context:
                prompt_parts.append(f"Related to issue #{context['issue_id']}")

        # Add insights
        if insights.primary_changes:
            prompt_parts.append(f"\nChanges: {'; '.join(insights.primary_changes[:3])}")

        prompt_parts.append("\nGenerate a clear, specific commit message:")

        return "\n".join(prompt_parts)

    def _generate_rule_based(
        self,
        files: List[FileUnderstanding],
        insights: CodeInsight,
        context: Optional[Dict[str, Any]] = None,
        style: str = "conventional",
    ) -> str:
        """Generate commit message using rules."""
        # Determine scope
        scope = self._determine_scope(files)

        # Generate subject
        subject = self._generate_subject(files, insights)

        # Build message
        if style == "conventional":
            header = f"{insights.change_type}"
            if scope:
                header += f"({scope})"
            header += f": {subject}"
        else:
            header = subject.capitalize()

        # Add body if needed
        body_parts = []
        if len(files) > 3:
            body_parts.append(f"Modified {len(files)} files")

        if insights.adds_tests:
            body_parts.append("Added tests")

        if insights.introduces_tech_debt:
            body_parts.append("Contains TODOs")

        # Add context
        if context and "issue_id" in context:
            body_parts.append(f"\nRelates to #{context['issue_id']}")

        if body_parts:
            return header + "\n\n" + "\n".join(body_parts)

        return header

    def _determine_scope(self, files: List[FileUnderstanding]) -> Optional[str]:
        """Determine commit scope from files."""
        # Get common directory
        if not files:
            return None

        paths = [f.path for f in files]
        if len(paths) == 1:
            return paths[0].stem

        # Find common parent
        common_parts = []
        for parts in zip(*[p.parts for p in paths]):
            if len(set(parts)) == 1:
                common_parts.append(parts[0])
            else:
                break

        if common_parts and common_parts[-1] not in [".", "src", "lib"]:
            return common_parts[-1]

        return None

    def _generate_subject(
        self, files: List[FileUnderstanding], insights: CodeInsight
    ) -> str:
        """Generate commit subject."""
        if insights.primary_changes:
            return insights.primary_changes[0].lower()

        if len(files) == 1:
            action = "add" if files[0].change_summary == "File created" else "update"
            return f"{action} {files[0].path.name}"

        return f"update {len(files)} files"
