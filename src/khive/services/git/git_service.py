# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Git Service - AI-powered git operations and intelligence.

This service provides high-level git operations like commit message generation,
PR descriptions, changelog creation, and more.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from khive.clients.executor import AsyncExecutor
from khive.connections.match_endpoint import match_endpoint
from khive.services.git.parts import (
    AnalyzeDiffParams,
    ChangelogFormat,
    ChangelogParams,
    CommitMessageParams,
    GitAction,
    GitRequest,
    GitResponse,
    PRDescriptionParams,
    ReleaseNotesParams,
    ReviewCommentsParams,
    SemverBumpType,
    SuggestBranchParams,
)
from khive.types import Service
from khive.utils import CommandResult, git_run


class GitServiceGroup(Service):
    """
    AI-powered Git service for intelligent git operations.

    Provides:
    - Commit message generation
    - PR description creation
    - Changelog generation
    - Release notes
    - Code review comments
    - Branch name suggestions
    - Semantic version analysis
    """

    def __init__(self, default_provider: str = "openai"):
        """
        Initialize the Git Service.

        Args:
            default_provider: Default LLM provider for git operations
        """
        self._llm_endpoint = None
        self._default_provider = default_provider
        self._executor = AsyncExecutor(max_concurrency=5)

        # Commit message templates by type
        self._commit_types = {
            "feat": "A new feature",
            "fix": "A bug fix",
            "docs": "Documentation only changes",
            "style": "Changes that do not affect the meaning of the code",
            "refactor": "A code change that neither fixes a bug nor adds a feature",
            "perf": "A code change that improves performance",
            "test": "Adding missing tests or correcting existing tests",
            "build": "Changes that affect the build system or external dependencies",
            "ci": "Changes to our CI configuration files and scripts",
            "chore": "Other changes that don't modify src or test files",
            "revert": "Reverts a previous commit",
        }

    async def handle_request(self, request: GitRequest) -> GitResponse:
        """
        Handle a git service request.

        Args:
            request: The git request to handle

        Returns:
            GitResponse with the result or error
        """
        if isinstance(request, str):
            request = GitRequest.model_validate_json(request)
        if isinstance(request, dict):
            request = GitRequest.model_validate(request)

        try:
            if request.action == GitAction.GENERATE_COMMIT_MESSAGE:
                return await self._generate_commit_message(request.params)
            elif request.action == GitAction.GENERATE_PR_DESCRIPTION:
                return await self._generate_pr_description(request.params)
            elif request.action == GitAction.GENERATE_CHANGELOG:
                return await self._generate_changelog(request.params)
            elif request.action == GitAction.GENERATE_RELEASE_NOTES:
                return await self._generate_release_notes(request.params)
            elif request.action == GitAction.SUGGEST_REVIEWERS:
                return await self._suggest_reviewers(request.params)
            elif request.action == GitAction.ANALYZE_DIFF:
                return await self._analyze_diff(request.params)
            elif request.action == GitAction.SUGGEST_BRANCH_NAME:
                return await self._suggest_branch_name(request.params)
            elif request.action == GitAction.GENERATE_REVIEW_COMMENTS:
                return await self._generate_review_comments(request.params)
            else:
                return GitResponse(
                    success=False,
                    error=f"Unsupported action: {request.action}",
                )
        except Exception as e:
            return GitResponse(
                success=False,
                error=f"Git service error: {str(e)}",
                action_performed=request.action,
            )

    async def _get_llm_endpoint(self):
        """Get or initialize the LLM endpoint."""
        if self._llm_endpoint is None:
            if self._default_provider == "anthropic":
                self._llm_endpoint = match_endpoint("anthropic", "messages")
            elif self._default_provider == "openrouter":
                self._llm_endpoint = match_endpoint("openrouter", "chat")
            else:
                self._llm_endpoint = match_endpoint("openai", "chat")
        return self._llm_endpoint

    async def _generate_commit_message(
        self, params: CommitMessageParams
    ) -> GitResponse:
        """Generate a commit message based on diff or changes."""
        try:
            # Get diff if not provided
            if not params.diff and not params.file_changes:
                diff_result = git_run(
                    ["diff", "--cached", "--name-status"],
                    capture=True,
                    check=False,
                    cwd=params.repo_path,
                )

                if isinstance(diff_result, CommandResult) and diff_result.stdout:
                    params.file_changes = diff_result.stdout.strip()

                # Get detailed diff
                detailed_diff = git_run(
                    ["diff", "--cached"],
                    capture=True,
                    check=False,
                    cwd=params.repo_path,
                )

                if isinstance(detailed_diff, CommandResult) and detailed_diff.stdout:
                    params.diff = detailed_diff.stdout.strip()

            # Build prompt
            prompt = self._build_commit_prompt(params)

            # Call LLM
            llm = await self._get_llm_endpoint()
            response = await self._call_llm(llm, prompt, temperature=0.3)

            if not response:
                # Fallback to rule-based generation
                commit_message = self._generate_rule_based_commit(params)
            else:
                commit_message = response.strip()

                # Validate conventional commit format
                if params.conventional and not self._validate_conventional_commit(
                    commit_message
                ):
                    # Try to fix it
                    commit_message = self._fix_conventional_format(commit_message)

            # Add additional context if requested
            if params.include_stats and params.file_changes:
                stats = self._calculate_change_stats(params.file_changes)
                commit_message += f"\n\n{stats}"

            if params.closes_issues:
                footer = "\n".join(f"Closes #{issue}" for issue in params.closes_issues)
                commit_message += f"\n\n{footer}"

            if params.co_authors:
                co_author_lines = "\n".join(
                    f"Co-authored-by: {author}" for author in params.co_authors
                )
                commit_message += f"\n\n{co_author_lines}"

            return GitResponse(
                success=True,
                action_performed=GitAction.GENERATE_COMMIT_MESSAGE,
                content={
                    "message": commit_message,
                    "type": self._extract_commit_type(commit_message),
                    "scope": self._extract_commit_scope(commit_message),
                    "breaking_change": (
                        "!" in commit_message.split(":")[0]
                        if ":" in commit_message
                        else False
                    ),
                },
            )

        except Exception as e:
            return GitResponse(
                success=False,
                error=f"Failed to generate commit message: {str(e)}",
                action_performed=GitAction.GENERATE_COMMIT_MESSAGE,
            )

    async def _generate_pr_description(
        self, params: PRDescriptionParams
    ) -> GitResponse:
        """Generate a PR description."""
        try:
            # Get commits if not provided
            if not params.commits and params.source_branch and params.target_branch:
                commits_result = git_run(
                    [
                        "log",
                        f"{params.target_branch}..{params.source_branch}",
                        "--oneline",
                    ],
                    capture=True,
                    check=False,
                    cwd=params.repo_path,
                )

                if isinstance(commits_result, CommandResult) and commits_result.stdout:
                    params.commits = commits_result.stdout.strip().split("\n")

            # Get diff summary if not provided
            if (
                not params.diff_summary
                and params.source_branch
                and params.target_branch
            ):
                diff_result = git_run(
                    [
                        "diff",
                        f"{params.target_branch}...{params.source_branch}",
                        "--stat",
                    ],
                    capture=True,
                    check=False,
                    cwd=params.repo_path,
                )

                if isinstance(diff_result, CommandResult) and diff_result.stdout:
                    params.diff_summary = diff_result.stdout.strip()

            # Build prompt
            prompt = self._build_pr_prompt(params)

            # Call LLM
            llm = await self._get_llm_endpoint()
            response = await self._call_llm(llm, prompt, temperature=0.5)

            if not response:
                # Fallback generation
                pr_description = self._generate_basic_pr_description(params)
            else:
                pr_description = response.strip()

            # Parse sections
            sections = self._parse_pr_sections(pr_description)

            return GitResponse(
                success=True,
                action_performed=GitAction.GENERATE_PR_DESCRIPTION,
                content={
                    "description": pr_description,
                    "title": sections.get("title", params.title or "Update"),
                    "summary": sections.get("summary", ""),
                    "changes": sections.get("changes", []),
                    "testing": sections.get("testing", ""),
                    "checklist": sections.get("checklist", []),
                },
            )

        except Exception as e:
            return GitResponse(
                success=False,
                error=f"Failed to generate PR description: {str(e)}",
                action_performed=GitAction.GENERATE_PR_DESCRIPTION,
            )

    async def _generate_changelog(self, params: ChangelogParams) -> GitResponse:
        """Generate a changelog."""
        try:
            # Get commits between versions
            if params.from_ref and params.to_ref:
                commits_result = git_run(
                    [
                        "log",
                        f"{params.from_ref}..{params.to_ref}",
                        "--pretty=format:%H|%s|%b|%an|%ae|%ad",
                    ],
                    capture=True,
                    check=False,
                    cwd=params.repo_path,
                )

                commits = []
                if isinstance(commits_result, CommandResult) and commits_result.stdout:
                    for line in commits_result.stdout.strip().split("\n"):
                        if line:
                            parts = line.split("|", 5)
                            if len(parts) >= 6:
                                commits.append({
                                    "hash": parts[0],
                                    "subject": parts[1],
                                    "body": parts[2],
                                    "author_name": parts[3],
                                    "author_email": parts[4],
                                    "date": parts[5],
                                })
            else:
                commits = []

            # Group commits by type
            grouped_commits = self._group_commits_by_type(commits)

            # Generate changelog based on format
            if params.format == ChangelogFormat.MARKDOWN:
                changelog = self._generate_markdown_changelog(grouped_commits, params)
            elif params.format == ChangelogFormat.CONVENTIONAL:
                changelog = self._generate_conventional_changelog(
                    grouped_commits, params
                )
            else:  # KEEP_A_CHANGELOG
                changelog = self._generate_keep_changelog(grouped_commits, params)

            return GitResponse(
                success=True,
                action_performed=GitAction.GENERATE_CHANGELOG,
                content={
                    "changelog": changelog,
                    "version": params.version or "Unreleased",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "commit_count": len(commits),
                    "contributors": list(set(c["author_name"] for c in commits)),
                },
            )

        except Exception as e:
            return GitResponse(
                success=False,
                error=f"Failed to generate changelog: {str(e)}",
                action_performed=GitAction.GENERATE_CHANGELOG,
            )

    async def _analyze_diff(self, params: AnalyzeDiffParams) -> GitResponse:
        """Analyze a diff for various insights."""
        try:
            # Get diff if not provided
            if not params.diff:
                diff_cmd = ["diff"]
                if params.base_ref and params.head_ref:
                    diff_cmd.append(f"{params.base_ref}...{params.head_ref}")
                elif not params.staged:
                    diff_cmd.append("HEAD")

                diff_result = git_run(
                    diff_cmd,
                    capture=True,
                    check=False,
                    cwd=params.repo_path,
                )

                if isinstance(diff_result, CommandResult) and diff_result.stdout:
                    params.diff = diff_result.stdout.strip()

            # Analyze the diff
            analysis = {
                "files_changed": self._count_changed_files(params.diff),
                "insertions": self._count_insertions(params.diff),
                "deletions": self._count_deletions(params.diff),
                "languages": self._detect_languages(params.diff),
                "patterns": self._detect_patterns(params.diff),
            }

            # Get AI insights if requested
            if params.include_ai_summary:
                prompt = f"""Analyze this git diff and provide insights:
                
{params.diff[:3000]}  # Truncate for token limits

Provide:
1. Summary of changes
2. Potential impact
3. Suggested commit type (feat/fix/refactor/etc)
4. Any concerns or suggestions
"""

                llm = await self._get_llm_endpoint()
                ai_response = await self._call_llm(llm, prompt, temperature=0.3)

                if ai_response:
                    analysis["ai_summary"] = ai_response.strip()

            # Determine semantic version bump
            analysis["suggested_version_bump"] = self._suggest_version_bump(params.diff)

            return GitResponse(
                success=True,
                action_performed=GitAction.ANALYZE_DIFF,
                content=analysis,
            )

        except Exception as e:
            return GitResponse(
                success=False,
                error=f"Failed to analyze diff: {str(e)}",
                action_performed=GitAction.ANALYZE_DIFF,
            )

    # Helper methods
    def _build_commit_prompt(self, params: CommitMessageParams) -> str:
        """Build prompt for commit message generation."""
        prompt = f"""Generate a {"conventional " if params.conventional else ""}commit message for these changes:

"""

        if params.diff:
            prompt += f"Diff:\n{params.diff[:2000]}\n\n"  # Truncate for token limits

        if params.file_changes:
            prompt += f"Files changed:\n{params.file_changes}\n\n"

        if params.conventional:
            prompt += f"""Use conventional commit format: type(scope): subject

Valid types: {", ".join(self._commit_types.keys())}

Rules:
- Keep subject under 72 characters
- Use imperative mood
- Don't end with period
- Include body for complex changes
- Add 'BREAKING CHANGE:' footer if applicable
"""
        else:
            prompt += """Write a clear, concise commit message following best practices:
- First line: summary under 72 characters
- Blank line
- Detailed explanation if needed
- Use imperative mood
"""

        if params.context:
            prompt += f"\nAdditional context: {params.context}\n"

        prompt += "\nReturn ONLY the commit message, no explanation."

        return prompt

    def _build_pr_prompt(self, params: PRDescriptionParams) -> str:
        """Build prompt for PR description generation."""
        prompt = f"""Generate a pull request description for merging {params.source_branch or "feature branch"} into {params.target_branch or "main"}.

"""

        if params.commits:
            prompt += (
                f"Commits:\n{chr(10).join(params.commits[:20])}\n\n"  # Limit commits
            )

        if params.diff_summary:
            prompt += f"Changes summary:\n{params.diff_summary}\n\n"

        prompt += """Create a well-structured PR description with:
1. Clear title (if not provided)
2. Summary of changes
3. List of specific changes
4. Testing instructions
5. Checklist items

Use markdown formatting."""

        if params.template:
            prompt += f"\n\nUse this template as a guide:\n{params.template}"

        return prompt

    async def _call_llm(
        self, endpoint, prompt: str, temperature: float = 0.5
    ) -> Optional[str]:
        """Call LLM endpoint with error handling."""
        try:
            if self._default_provider == "anthropic":
                response = await endpoint.call({
                    "messages": [{"role": "user", "content": prompt}],
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1000,
                    "temperature": temperature,
                })
                if hasattr(response, "content") and response.content:
                    return response.content[0].text
            else:
                # OpenAI-compatible
                response = await endpoint.call({
                    "messages": [{"role": "user", "content": prompt}],
                    "model": "gpt-4o-mini",
                    "max_tokens": 1000,
                    "temperature": temperature,
                })
                if hasattr(response, "choices") and response.choices:
                    return response.choices[0].message.content

            return None
        except Exception as e:
            # Log error and return None for fallback
            print(f"LLM call failed: {e}")
            return None

    def _validate_conventional_commit(self, message: str) -> bool:
        """Validate if message follows conventional commit format."""
        lines = message.split("\n")
        if not lines:
            return False

        # Check header format
        header = lines[0]
        pattern = rf"^({'|'.join(self._commit_types.keys())})(\([^)]+\))?!?: .+"
        return bool(re.match(pattern, header))

    def _fix_conventional_format(self, message: str) -> str:
        """Try to fix a message to conventional format."""
        lines = message.split("\n", 1)
        header = lines[0]

        # Try to detect type from content
        header_lower = header.lower()
        detected_type = "chore"  # default

        for commit_type, description in self._commit_types.items():
            if commit_type in header_lower or description.lower() in header_lower:
                detected_type = commit_type
                break

        # Extract scope if present
        scope_match = re.search(r"\(([^)]+)\)", header)
        scope = f"({scope_match.group(1)})" if scope_match else ""

        # Clean subject
        subject = re.sub(
            r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)[:\s]*",
            "",
            header,
            flags=re.IGNORECASE,
        )
        subject = re.sub(r"^\([^)]+\)[:\s]*", "", subject)  # Remove scope
        subject = subject.strip()

        # Reconstruct
        new_header = f"{detected_type}{scope}: {subject}"

        if len(lines) > 1:
            return f"{new_header}\n{lines[1]}"
        return new_header

    def _extract_commit_type(self, message: str) -> Optional[str]:
        """Extract commit type from message."""
        match = re.match(r"^([a-z]+)(?:\([^)]+\))?!?:", message)
        return match.group(1) if match else None

    def _extract_commit_scope(self, message: str) -> Optional[str]:
        """Extract commit scope from message."""
        match = re.match(r"^[a-z]+\(([^)]+)\)!?:", message)
        return match.group(1) if match else None

    def _calculate_change_stats(self, file_changes: str) -> str:
        """Calculate statistics from file changes."""
        lines = file_changes.strip().split("\n")
        added = sum(1 for line in lines if line.startswith("A\t"))
        modified = sum(1 for line in lines if line.startswith("M\t"))
        deleted = sum(1 for line in lines if line.startswith("D\t"))

        parts = []
        if added:
            parts.append(f"{added} added")
        if modified:
            parts.append(f"{modified} modified")
        if deleted:
            parts.append(f"{deleted} deleted")

        return f"Files: {', '.join(parts)}" if parts else ""

    def _generate_rule_based_commit(self, params: CommitMessageParams) -> str:
        """Generate a simple rule-based commit message as fallback."""
        if not params.file_changes:
            return "chore: update project files"

        lines = params.file_changes.strip().split("\n")

        # Analyze changes
        added = [line[2:] for line in lines if line.startswith("A\t")]
        modified = [line[2:] for line in lines if line.startswith("M\t")]
        deleted = [line[2:] for line in lines if line.startswith("D\t")]

        # Determine type and message
        if added and not modified and not deleted:
            if any("test" in f for f in added):
                return f"test: add {Path(added[0]).stem if len(added) == 1 else f'{len(added)} test files'}"
            elif any("doc" in f.lower() or "readme" in f.lower() for f in added):
                return f"docs: add {Path(added[0]).name if len(added) == 1 else 'documentation'}"
            else:
                return f"feat: add {Path(added[0]).stem if len(added) == 1 else f'{len(added)} new files'}"

        elif deleted and not added and not modified:
            return f"chore: remove {Path(deleted[0]).name if len(deleted) == 1 else f'{len(deleted)} files'}"

        elif modified:
            if any("fix" in f or "bug" in f for f in modified):
                return f"fix: update {Path(modified[0]).stem if len(modified) == 1 else f'{len(modified)} files'}"
            elif any("test" in f for f in modified):
                return f"test: update {Path(modified[0]).stem if len(modified) == 1 else 'tests'}"
            else:
                return f"refactor: update {Path(modified[0]).stem if len(modified) == 1 else f'{len(modified)} files'}"

        return "chore: update project files"

    def _parse_pr_sections(self, description: str) -> Dict[str, Any]:
        """Parse PR description into sections."""
        sections = {
            "title": "",
            "summary": "",
            "changes": [],
            "testing": "",
            "checklist": [],
        }

        # Try to extract title (first line or # heading)
        lines = description.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("# "):
                sections["title"] = line[2:].strip()
                break
            elif i == 0 and line.strip():
                sections["title"] = line.strip()

        # Extract other sections using common patterns
        current_section = None
        current_content = []

        for line in lines:
            # Check for section headers
            if re.match(r"^#+\s*(summary|description|overview)", line, re.IGNORECASE):
                current_section = "summary"
                current_content = []
            elif re.match(
                r"^#+\s*(changes|what changed|modifications)", line, re.IGNORECASE
            ):
                current_section = "changes"
                current_content = []
            elif re.match(r"^#+\s*(testing|how to test|test)", line, re.IGNORECASE):
                current_section = "testing"
                current_content = []
            elif re.match(r"^#+\s*(checklist|tasks|todo)", line, re.IGNORECASE):
                current_section = "checklist"
                current_content = []
            elif current_section:
                if line.strip():
                    current_content.append(line)
                elif current_content:  # Empty line ends section
                    if current_section == "summary":
                        sections["summary"] = "\n".join(current_content).strip()
                    elif current_section == "testing":
                        sections["testing"] = "\n".join(current_content).strip()
                    elif current_section == "changes":
                        # Extract list items
                        for item in current_content:
                            if item.strip().startswith(("- ", "* ", "+ ")):
                                sections["changes"].append(item.strip()[2:])
                    elif current_section == "checklist":
                        # Extract checklist items
                        for item in current_content:
                            if "[ ]" in item or "[x]" in item:
                                sections["checklist"].append(item.strip())
                    current_section = None
                    current_content = []

        return sections

    def _group_commits_by_type(self, commits: List[Dict]) -> Dict[str, List[Dict]]:
        """Group commits by conventional commit type."""
        grouped = {
            "feat": [],
            "fix": [],
            "docs": [],
            "perf": [],
            "refactor": [],
            "test": [],
            "build": [],
            "ci": [],
            "chore": [],
            "other": [],
        }

        for commit in commits:
            subject = commit["subject"]
            commit_type = self._extract_commit_type(subject)

            if commit_type in grouped:
                grouped[commit_type].append(commit)
            else:
                grouped["other"].append(commit)

        # Remove empty groups
        return {k: v for k, v in grouped.items() if v}

    def _generate_markdown_changelog(
        self, grouped_commits: Dict[str, List[Dict]], params: ChangelogParams
    ) -> str:
        """Generate markdown format changelog."""
        lines = []

        # Header
        version = params.version or "Unreleased"
        date = datetime.now().strftime("%Y-%m-%d")
        lines.append(f"## [{version}] - {date}")
        lines.append("")

        # Sections
        type_labels = {
            "feat": "### 🚀 Features",
            "fix": "### 🐛 Bug Fixes",
            "docs": "### 📚 Documentation",
            "perf": "### ⚡ Performance",
            "refactor": "### ♻️ Refactoring",
            "test": "### ✅ Tests",
            "build": "### 📦 Build",
            "ci": "### 👷 CI",
            "chore": "### 🔧 Chores",
        }

        for commit_type, commits in grouped_commits.items():
            if commit_type in type_labels:
                lines.append(type_labels[commit_type])
                lines.append("")

                for commit in commits:
                    subject = commit["subject"]
                    # Remove type prefix
                    subject = re.sub(r"^[a-z]+(\([^)]+\))?!?:\s*", "", subject)

                    # Add commit link if URL template provided
                    if params.commit_url_template:
                        commit_link = params.commit_url_template.format(
                            hash=commit["hash"][:7]
                        )
                        lines.append(
                            f"- {subject} ([{commit['hash'][:7]}]({commit_link}))"
                        )
                    else:
                        lines.append(f"- {subject} ({commit['hash'][:7]})")

                lines.append("")

        return "\n".join(lines)

    def _count_changed_files(self, diff: str) -> int:
        """Count number of changed files in diff."""
        return len(re.findall(r"^diff --git", diff, re.MULTILINE))

    def _count_insertions(self, diff: str) -> int:
        """Count number of insertions in diff."""
        return len(re.findall(r"^\+[^+]", diff, re.MULTILINE))

    def _count_deletions(self, diff: str) -> int:
        """Count number of deletions in diff."""
        return len(re.findall(r"^-[^-]", diff, re.MULTILINE))

    def _detect_languages(self, diff: str) -> List[str]:
        """Detect programming languages from file extensions in diff."""
        extensions = re.findall(r"diff --git a/.*\.(\w+)", diff)

        language_map = {
            "py": "Python",
            "js": "JavaScript",
            "ts": "TypeScript",
            "java": "Java",
            "cpp": "C++",
            "c": "C",
            "go": "Go",
            "rs": "Rust",
            "rb": "Ruby",
            "php": "PHP",
            "swift": "Swift",
            "kt": "Kotlin",
            "scala": "Scala",
            "r": "R",
            "m": "MATLAB",
            "jl": "Julia",
            "sh": "Shell",
            "ps1": "PowerShell",
        }

        languages = set()
        for ext in extensions:
            if ext in language_map:
                languages.add(language_map[ext])
            elif ext in ["h", "hpp"]:
                languages.add("C/C++")
            elif ext in ["jsx", "tsx"]:
                languages.add("React")
            elif ext in ["vue"]:
                languages.add("Vue")
            elif ext in ["yaml", "yml"]:
                languages.add("YAML")
            elif ext in ["json"]:
                languages.add("JSON")
            elif ext in ["xml"]:
                languages.add("XML")
            elif ext in ["md", "markdown"]:
                languages.add("Markdown")

        return sorted(list(languages))

    def _detect_patterns(self, diff: str) -> Dict[str, bool]:
        """Detect common patterns in diff."""
        return {
            "has_tests": bool(re.search(r"test_|_test\.|\.test\.|/tests?/", diff)),
            "has_docs": bool(
                re.search(r"README|CHANGELOG|/docs?/|\.md", diff, re.IGNORECASE)
            ),
            "has_config": bool(
                re.search(
                    r"config|\.env|settings|\.ini|\.toml|\.yaml", diff, re.IGNORECASE
                )
            ),
            "has_dependencies": bool(
                re.search(
                    r"requirements\.txt|package\.json|Cargo\.toml|go\.mod|pom\.xml",
                    diff,
                )
            ),
            "has_migrations": bool(re.search(r"migrations?/|alembic/", diff)),
            "has_api_changes": bool(
                re.search(r"api/|endpoint|route|controller", diff, re.IGNORECASE)
            ),
            "has_ui_changes": bool(
                re.search(
                    r"\.css|\.scss|\.html|component|template|view", diff, re.IGNORECASE
                )
            ),
        }

    def _suggest_version_bump(self, diff: str) -> SemverBumpType:
        """Suggest semantic version bump based on diff."""
        # Check for breaking changes
        if re.search(r"BREAKING CHANGE|breaking:", diff, re.IGNORECASE):
            return SemverBumpType.MAJOR

        # Check commit messages in diff
        feat_count = len(re.findall(r"^feat(\([^)]+\))?:", diff, re.MULTILINE))
        fix_count = len(re.findall(r"^fix(\([^)]+\))?:", diff, re.MULTILINE))

        if feat_count > 0:
            return SemverBumpType.MINOR
        elif fix_count > 0:
            return SemverBumpType.PATCH

        # Check for API changes
        if re.search(
            r"api/|endpoint|route|interface|public\s+\w+", diff, re.IGNORECASE
        ):
            return SemverBumpType.MINOR

        # Default to patch
        return SemverBumpType.PATCH

    def _generate_basic_pr_description(self, params: PRDescriptionParams) -> str:
        """Generate basic PR description without AI."""
        lines = []

        # Title
        title = (
            params.title
            or f"Merge {params.source_branch or 'feature'} into {params.target_branch or 'main'}"
        )
        lines.append(f"# {title}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append("This PR includes the following changes:")
        lines.append("")

        # Changes from commits
        if params.commits:
            lines.append("## Changes")
            lines.append("")
            for commit in params.commits[:20]:  # Limit commits
                lines.append(f"- {commit}")
            if len(params.commits) > 20:
                lines.append(f"- ... and {len(params.commits) - 20} more commits")
            lines.append("")

        # File changes
        if params.diff_summary:
            lines.append("## Files Changed")
            lines.append("")
            lines.append("```")
            lines.append(params.diff_summary)
            lines.append("```")
            lines.append("")

        # Standard sections
        lines.append("## Testing")
        lines.append("")
        lines.append("- [ ] Tests pass locally")
        lines.append("- [ ] New tests added for changes")
        lines.append("")

        lines.append("## Checklist")
        lines.append("")
        lines.append("- [ ] Code follows project style guidelines")
        lines.append("- [ ] Self-review completed")
        lines.append("- [ ] Documentation updated")
        lines.append("- [ ] No new warnings")

        return "\n".join(lines)

    def _generate_conventional_changelog(
        self, grouped_commits: Dict[str, List[Dict]], params: ChangelogParams
    ) -> str:
        """Generate conventional changelog format."""
        # Similar to markdown but follows conventional changelog spec
        return self._generate_markdown_changelog(grouped_commits, params)

    def _generate_keep_changelog(
        self, grouped_commits: Dict[str, List[Dict]], params: ChangelogParams
    ) -> str:
        """Generate Keep a Changelog format."""
        lines = []

        # Header
        version = params.version or "Unreleased"
        date = datetime.now().strftime("%Y-%m-%d")
        lines.append(f"## [{version}] - {date}")
        lines.append("")

        # Keep a Changelog categories
        categories = {
            "feat": "Added",
            "fix": "Fixed",
            "docs": "Changed",  # Docs usually go under Changed
            "perf": "Changed",
            "refactor": "Changed",
            "test": "Changed",
            "build": "Changed",
            "ci": "Changed",
            "chore": "Changed",
        }

        # Group by Keep a Changelog categories
        keep_grouped = {
            "Added": [],
            "Changed": [],
            "Deprecated": [],
            "Removed": [],
            "Fixed": [],
            "Security": [],
        }

        for commit_type, commits in grouped_commits.items():
            category = categories.get(commit_type, "Changed")
            keep_grouped[category].extend(commits)

        # Write sections
        for category, commits in keep_grouped.items():
            if commits:
                lines.append(f"### {category}")
                for commit in commits:
                    subject = commit["subject"]
                    subject = re.sub(r"^[a-z]+(\([^)]+\))?!?:\s*", "", subject)
                    lines.append(f"- {subject}")
                lines.append("")

        return "\n".join(lines)

    async def _suggest_reviewers(self, params: Dict[str, Any]) -> GitResponse:
        """Suggest code reviewers based on file changes and history."""
        # This would analyze git blame, recent commits, and code ownership
        # Placeholder for now
        return GitResponse(
            success=False,
            error="Reviewer suggestion not yet implemented",
            action_performed=GitAction.SUGGEST_REVIEWERS,
        )

    async def _suggest_branch_name(self, params: SuggestBranchParams) -> GitResponse:
        """Suggest a branch name based on the work description."""
        try:
            # Build prompt
            prompt = f"""Suggest a git branch name for: {params.description}

Rules:
- Use lowercase and hyphens
- Keep it concise but descriptive
- Follow the pattern: {params.branch_prefix or "feature"}/description
- Max 50 characters total
- No special characters except hyphens

Return ONLY the branch name, no explanation."""

            # Call LLM
            llm = await self._get_llm_endpoint()
            response = await self._call_llm(llm, prompt, temperature=0.3)

            if response:
                branch_name = response.strip()
            else:
                # Fallback: create from description
                branch_name = self._create_branch_name_from_description(
                    params.description, params.branch_prefix
                )

            return GitResponse(
                success=True,
                action_performed=GitAction.SUGGEST_BRANCH_NAME,
                content={
                    "branch_name": branch_name,
                    "prefix": params.branch_prefix or "feature",
                },
            )

        except Exception as e:
            return GitResponse(
                success=False,
                error=f"Failed to suggest branch name: {str(e)}",
                action_performed=GitAction.SUGGEST_BRANCH_NAME,
            )

    async def _generate_review_comments(
        self, params: ReviewCommentsParams
    ) -> GitResponse:
        """Generate code review comments."""
        try:
            # Get diff
            if not params.diff and params.pr_number:
                # Would fetch from GitHub/GitLab API
                pass

            if not params.diff:
                return GitResponse(
                    success=False,
                    error="No diff provided for review",
                    action_performed=GitAction.GENERATE_REVIEW_COMMENTS,
                )

            # Build prompt
            prompt = f"""Review this code diff and provide constructive feedback:

{params.diff[:5000]}  # Truncate for token limits

Focus on:
{chr(10).join("- " + f for f in params.focus_areas) if params.focus_areas else "- Code quality, bugs, performance, security, maintainability"}

Provide specific, actionable comments with line numbers where applicable.
Be constructive and explain why changes would be beneficial.
Format as a list of comments."""

            # Call LLM
            llm = await self._get_llm_endpoint()
            response = await self._call_llm(llm, prompt, temperature=0.5)

            if response:
                comments = self._parse_review_comments(response)
            else:
                comments = []

            return GitResponse(
                success=True,
                action_performed=GitAction.GENERATE_REVIEW_COMMENTS,
                content={
                    "comments": comments,
                    "summary": f"Generated {len(comments)} review comments",
                    "severity_counts": self._count_comment_severities(comments),
                },
            )

        except Exception as e:
            return GitResponse(
                success=False,
                error=f"Failed to generate review comments: {str(e)}",
                action_performed=GitAction.GENERATE_REVIEW_COMMENTS,
            )

    async def _generate_release_notes(self, params: ReleaseNotesParams) -> GitResponse:
        """Generate release notes."""
        try:
            # Get commits/changelog
            changelog_params = ChangelogParams(
                from_ref=params.from_version,
                to_ref=params.to_version,
                version=params.version,
                format=ChangelogFormat.MARKDOWN,
                repo_path=params.repo_path,
            )

            changelog_response = await self._generate_changelog(changelog_params)

            if not changelog_response.success:
                return GitResponse(
                    success=False,
                    error="Failed to generate changelog for release notes",
                    action_performed=GitAction.GENERATE_RELEASE_NOTES,
                )

            # Build release notes
            lines = []

            # Title
            lines.append(f"# Release {params.version}")
            lines.append("")

            # Date
            lines.append(f"**Released:** {datetime.now().strftime('%B %d, %Y')}")
            lines.append("")

            # Summary (from highlights or generate)
            if params.highlights:
                lines.append("## Highlights")
                lines.append("")
                for highlight in params.highlights:
                    lines.append(f"- {highlight}")
                lines.append("")

            # Changelog
            lines.append("## What's Changed")
            lines.append("")
            lines.append(changelog_response.content["changelog"])

            # Contributors
            if changelog_response.content.get("contributors"):
                lines.append("## Contributors")
                lines.append("")
                lines.append("Thanks to all contributors:")
                for contributor in changelog_response.content["contributors"]:
                    lines.append(f"- {contributor}")
                lines.append("")

            # Breaking changes
            if params.breaking_changes:
                lines.append("## ⚠️ Breaking Changes")
                lines.append("")
                for change in params.breaking_changes:
                    lines.append(f"- {change}")
                lines.append("")

            # Upgrade instructions
            if params.include_upgrade_instructions:
                lines.append("## Upgrade Instructions")
                lines.append("")
                lines.append("To upgrade to this version:")
                lines.append("")
                lines.append("```bash")
                lines.append(f"pip install khive=={params.version}")
                lines.append("```")

            release_notes = "\n".join(lines)

            return GitResponse(
                success=True,
                action_performed=GitAction.GENERATE_RELEASE_NOTES,
                content={
                    "release_notes": release_notes,
                    "version": params.version,
                    "commit_count": changelog_response.content.get("commit_count", 0),
                },
            )

        except Exception as e:
            return GitResponse(
                success=False,
                error=f"Failed to generate release notes: {str(e)}",
                action_performed=GitAction.GENERATE_RELEASE_NOTES,
            )

    def _create_branch_name_from_description(
        self, description: str, prefix: Optional[str] = None
    ) -> str:
        """Create branch name from description without AI."""
        # Clean and format description
        words = re.findall(r"\w+", description.lower())[:5]  # Max 5 words
        branch_suffix = "-".join(words)

        # Add prefix
        prefix = prefix or "feature"
        branch_name = f"{prefix}/{branch_suffix}"

        # Ensure max length
        if len(branch_name) > 50:
            branch_name = branch_name[:50].rstrip("-")

        return branch_name

    def _parse_review_comments(self, response: str) -> List[Dict[str, Any]]:
        """Parse review comments from LLM response."""
        comments = []

        # Simple parsing - could be enhanced
        lines = response.strip().split("\n")
        current_comment = None

        for line in lines:
            if line.strip().startswith(("-", "*", "•", "1.", "2.", "3.")):
                if current_comment:
                    comments.append(current_comment)

                # Extract severity if present
                severity = "info"
                if any(word in line.lower() for word in ["critical", "severe", "bug"]):
                    severity = "critical"
                elif any(
                    word in line.lower() for word in ["warning", "issue", "problem"]
                ):
                    severity = "warning"
                elif any(
                    word in line.lower() for word in ["suggest", "consider", "optional"]
                ):
                    severity = "suggestion"

                current_comment = {
                    "comment": line.strip().lstrip("-*•0123456789. "),
                    "severity": severity,
                    "line": None,  # Would need to parse from comment
                }
            elif current_comment and line.strip():
                # Continue previous comment
                current_comment["comment"] += " " + line.strip()

        if current_comment:
            comments.append(current_comment)

        return comments

    def _count_comment_severities(
        self, comments: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Count comments by severity."""
        severities = {"critical": 0, "warning": 0, "suggestion": 0, "info": 0}

        for comment in comments:
            severity = comment.get("severity", "info")
            if severity in severities:
                severities[severity] += 1

        return severities

    async def close(self) -> None:
        """Close the service and release resources."""
        if hasattr(self, "_executor") and self._executor is not None:
            await self._executor.shutdown()

        if self._llm_endpoint and hasattr(self._llm_endpoint, "aclose"):
            await self._llm_endpoint.aclose()
