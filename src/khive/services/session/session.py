"""
Session management for lion orchestrator
Handles session initialization and completion workflows
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from khive.core import TimePolicy

# ANSI color codes
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RED = "\033[91m"
RESET = "\033[0m"


class SessionInitializer:
    """Streamlined session initialization for orchestrator"""

    def __init__(
        self,
        issue: int | None = None,
        resume: bool = False,
        depth: int = 7,
        continue_session: bool = False,
    ):
        self.issue = issue
        self.resume = resume
        self.continue_session = continue_session
        self.memory_depth = depth
        self.context = {
            "date": TimePolicy.now_utc().strftime("%Y-%m-%d %H:%M:%S"),
            "priorities": [],
            "recent_work": [],
            "patterns": [],
            "pending_tasks": [],
            "unprocessed_summaries": 0,
            "db_reset": False,
        }

    def run_command(self, cmd: list[str]) -> tuple[bool, str]:
        """Execute command and return success status and output"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False)  # noqa: S603
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip()

    def get_pending_tasks(self) -> list[dict]:
        """Get pending tasks from GitHub issues"""
        # Get open issues with specific labels
        issues = self.get_open_issues(limit=10)
        tasks = []

        for issue in issues:
            priority = "low"
            labels = [l.get("name", "") for l in issue.get("labels", [])]

            if "priority:high" in labels:
                priority = "high"
            elif "priority:medium" in labels:
                priority = "medium"

            # Check for task-related labels
            if any(label in labels for label in ["todo", "task", "enhancement", "bug"]):
                tasks.append({
                    "description": f"Issue #{issue['number']}: {issue['title']}",
                    "priority": priority,
                })

        return tasks

    def count_unprocessed_summaries(self) -> int:
        """Count conversation summaries that need diary processing"""
        summary_dir = Path(".khive/notes/summaries")
        if not summary_dir.exists():
            return 0

        count = 0
        for summary_file in summary_dir.glob("summary_*.md"):
            try:
                content = summary_file.read_text()
                # Check if not processed
                if "processed: true" not in content:
                    count += 1
            except (OSError, UnicodeDecodeError) as e:
                self.logger.warning(f"Failed to read summary file {summary_file}: {e}")

        return count

    def get_recent_diaries(self, limit: int = 3) -> list[str]:
        """Get most recent session diaries"""
        diary_dir = Path(".khive/notes/diaries")
        if not diary_dir.exists():
            return []

        diaries = sorted(
            diary_dir.glob("diary_*.md"), key=lambda p: p.stat().st_mtime, reverse=True
        )[:limit]

        results = []
        for diary in diaries:
            try:
                content = diary.read_text()
                lines = content.split("\n")

                # Extract key sections from diary
                in_section = None
                for line in lines:
                    line = line.strip()

                    # Look for accomplishments
                    if "Key Accomplishments" in line:
                        in_section = "accomplishments"
                        continue
                    if "Critical Insights" in line:
                        in_section = "insights"
                        continue
                    if "Tomorrow's Priorities" in line:
                        in_section = "priorities"
                        continue
                    if line.startswith("#"):
                        in_section = None
                        continue

                    # Extract content based on section
                    if in_section and line and not line.startswith("{{"):
                        if in_section == "accomplishments" and "**Impact**:" in line:
                            impact = line.split("**Impact**:")[1].strip()
                            if impact:
                                results.append(f"[ACCOMPLISHED] {impact}")
                        elif in_section == "insights" and line.startswith("1."):
                            insight = line[3:].strip()
                            if insight:
                                results.append(f"[INSIGHT] {insight}")
                        elif in_section == "priorities" and line.startswith("1."):
                            priority = line[3:].strip()
                            if priority:
                                results.append(f"[PRIORITY] {priority}")

                    if len(results) >= 5:
                        break

            except (OSError, UnicodeDecodeError, ValueError) as e:
                self.logger.warning(f"Failed to process diary file {diary}: {e}")

        return results[:5]

    def load_orchestrator_docs(self) -> str | None:
        """Load complete orchestrator documentation (no truncation)"""
        doc_paths = [
            Path(
                "khive.md"
            ),  # Primary orchestrator guidance - COMPLETE CONTENT REQUIRED
            Path("CLAUDE.md"),  # Project instructions
            Path("libs/khive/CLAUDE.md"),  # Khive-specific guidance
            Path(".claude/QUICK_START.md"),  # Quick reference
        ]

        for path in doc_paths:
            if path.exists():
                try:
                    content = path.read_text()
                    return f"# Documentation: {path.name}\n\n" + content
                except (OSError, UnicodeDecodeError) as e:
                    self.logger.warning(f"Failed to read documentation file {path}: {e}")
                    continue

        return "# No orchestrator documentation found - using memory patterns only"

    def get_recent_summaries(self, limit: int = 3) -> list[str]:
        """Get most recent session summaries with intelligent extraction"""
        summary_dir = Path(".khive/notes/summaries")
        if not summary_dir.exists():
            return []

        summaries = sorted(
            summary_dir.glob("summary_*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]

        results = []
        for summary in summaries:
            try:
                content = summary.read_text()

                # Extract key patterns
                patterns = {
                    "outcome": r"(?:outcome|completed|achieved|delivered):\s*(.+)",
                    "learning": r"(?:learned|discovered|insight):\s*(.+)",
                    "challenge": r"(?:challenge|issue|problem):\s*(.+)",
                    "next": r"(?:next|todo|pending):\s*(.+)",
                }

                for pattern_type, regex in patterns.items():
                    matches = re.findall(regex, content, re.IGNORECASE | re.MULTILINE)
                    for match in matches[:1]:  # Take first match of each type
                        clean_match = match.strip()
                        if len(clean_match) > 20 and len(clean_match) < 200:
                            results.append(f"[{pattern_type.upper()}] {clean_match}")

                # If we don't have enough, look for bullet points
                if len(results) < 3:
                    lines = content.split("\n")
                    for line in lines:
                        line = line.strip()
                        if (line.startswith(("•", "-", "*"))) and len(line) > 20:
                            results.append(line[1:].strip())
                            if len(results) >= 5:
                                break

            except (OSError, UnicodeDecodeError, ValueError) as e:
                self.logger.warning(f"Failed to process summary file {summary}: {e}")

        # Deduplicate and limit
        seen = set()
        unique_results = []
        for r in results:
            if r not in seen and len(unique_results) < 5:
                seen.add(r)
                unique_results.append(r)

        return unique_results

    def get_git_status(self) -> dict[str, any]:
        """Get current git status"""
        status = {}

        # Current branch
        success, branch = self.run_command(["git", "branch", "--show-current"])
        status["branch"] = branch if success else "unknown"

        # Modified files count
        success, modified = self.run_command(["git", "status", "--porcelain"])
        if success:
            status["modified_files"] = len([
                l for l in modified.split("\n") if l.strip()
            ])
        else:
            status["modified_files"] = 0

        # Recent commits
        success, commits = self.run_command(["git", "log", "--oneline", "-3"])
        status["recent_commits"] = commits.split("\n")[:3] if success else []

        return status

    def get_open_issues(self, limit: int = 5) -> list[dict]:
        """Get open GitHub issues"""
        success, output = self.run_command([
            "gh",
            "issue",
            "list",
            "--state",
            "open",
            "--limit",
            str(limit),
            "--json",
            "number,title,labels",
        ])

        if success and output:
            try:
                return json.loads(output)
            except (json.JSONDecodeError, TypeError) as e:
                self.logger.warning(f"Failed to parse JSON output: {e}")
        return []

    def generate_memory_queries(self) -> list[str]:
        """Generate focused, proven memory search queries"""
        # Core queries that always provide value
        queries = [
            ("search_by_type", "preference", 10),  # Ocean's preferences
            ("search", "orchestration successful patterns", 5),
            ("search", "session outcome recent", 5),
        ]

        # Add context-specific queries
        if self.issue:
            queries.append(("search", f"issue {self.issue}", 3))
        if self.resume:
            queries.append(("search", "incomplete tasks", 3))

        return queries[:5]  # Respect batch limit

    def format_output(self) -> str:
        """Streamlined initialization output focusing on actionable next steps"""
        git = self.context.get("git_status", {})
        task_count = len(self.context["pending_tasks"])

        output = [
            f"🦁 Lion Orchestrator Session Initialized ({self.context['date']})",
            f"📊 Status: {git.get('branch', 'unknown')} branch, {git.get('modified_files', 0)} modified files, {task_count} pending tasks",
            "",
            "🚨 CRITICAL: Always use 'uv run khive plan [task]' for orchestration tasks",
            "",
        ]

        # Show high priority tasks only
        high_priority_tasks = [
            t for t in self.context["pending_tasks"] if t.get("priority") == "high"
        ][:2]
        if high_priority_tasks:
            output.append("🔥 High Priority Tasks:")
            output.extend(f"  • {task.get('description', 'Unknown task')}" for task in high_priority_tasks)
            output.append("")

        # Recent insights (condensed)
        if self.context.get("recent_diaries"):
            output.append("💡 Recent Key Insights:")
            for insight in self.context["recent_diaries"][:2]:
                truncated = insight[:60] + "..." if len(insight) > 60 else insight
                output.append(f"  • {truncated}")
            output.append("")

        # Unprocessed summaries alert
        if self.context.get("unprocessed_summaries", 0) > 0:
            output.append(
                f"📝 {self.context['unprocessed_summaries']} unprocessed summaries - run 'uv run khive session end' when ready"
            )
            output.append("")

        # Load orchestrator documentation (CRITICAL IDENTITY)
        if self.context.get("orchestrator_docs"):
            output.append("📚 Orchestrator Documentation (khive.md):")
            output.append("```markdown")
            output.append(self.context["orchestrator_docs"])
            output.append("```")
            output.append("")

        # Common pitfalls and critical reminders
        output.append("⚠️  CRITICAL ORCHESTRATION PITFALLS TO AVOID:")
        output.append(
            "❌ Never skip 'uv run khive plan' - causes inefficient agent selection"
        )
        output.append(
            "❌ Never use sequential calls for parallel tasks - use BatchTool instead"
        )
        output.append(
            "❌ Never let Task agents use Memory/Knowledge MCPs - orchestrator only"
        )
        output.append(
            "❌ Never start orchestration without loading memory context first"
        )
        output.append("❌ Never spawn >5 agents without quality gates (critic agents)")
        output.append(
            "❌ Never forget to save successful patterns to memory for learning"
        )
        output.append("✅ Always: plan → memory context → orchestrate → save learnings")
        output.append("")

        # Next actions
        output.append("🎯 Next Actions:")
        output.append("1. Execute memory queries above (batch)")
        output.append(
            "2. Run 'uv run khive plan [your task]' for orchestration guidance"
        )
        output.append("3. Begin orchestration work with proven patterns")

        return "\n".join(output)

    def initialize(self):
        """Run the initialization process"""
        print(f"{CYAN}Initializing orchestrator session...{RESET}")

        # Count unprocessed summaries
        self.context["unprocessed_summaries"] = self.count_unprocessed_summaries()

        # Get pending tasks
        self.context["pending_tasks"] = self.get_pending_tasks()

        # Get recent diaries
        self.context["recent_diaries"] = self.get_recent_diaries()

        # Get recent summaries
        self.context["recent_work"] = self.get_recent_summaries()

        # Load orchestrator documentation
        self.context["orchestrator_docs"] = self.load_orchestrator_docs()

        # Get git status
        self.context["git_status"] = self.get_git_status()

        # Get open issues
        issues = self.get_open_issues()
        if issues:
            self.context["open_issues"] = len(issues)
            self.context["priority_issues"] = [
                i
                for i in issues
                if any(l.get("name") == "priority:high" for l in i.get("labels", []))
            ]

        # Generate output for response
        formatted_output = self.format_output()

        # If resuming, show additional context
        resume_output = ""

        # Return the complete output for server response
        return formatted_output + resume_output


class DiaryWritingAssistant:
    """Assistant for manual diary writing process"""

    def __init__(self, dry_run: bool = False, target_date: str | None = None):
        self.dry_run = dry_run
        self.target_date = target_date
        self.summaries_dir = Path(".khive/notes/summaries")
        self.diaries_dir = Path(".khive/notes/diaries")
        self.diaries_dir.mkdir(parents=True, exist_ok=True)

    def find_unprocessed_summaries(self) -> dict[str, list[Path]]:
        """Find summaries that haven't been processed into diaries, grouped by date"""
        summaries_by_date = {}

        if not self.summaries_dir.exists():
            return summaries_by_date

        for summary_file in self.summaries_dir.glob("summary_*.md"):
            try:
                content = summary_file.read_text()

                # Check if already processed
                if "processed: true" in content and not self.dry_run:
                    continue

                # Extract date from filename (summary_YYYYMMDD_HHMMSS.md)
                match = re.search(r"summary_(\d{8})_\d{6}\.md", summary_file.name)
                if match:
                    date_str = match.group(1)
                    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

                    if self.target_date and formatted_date != self.target_date:
                        continue

                    if formatted_date not in summaries_by_date:
                        summaries_by_date[formatted_date] = []
                    summaries_by_date[formatted_date].append(summary_file)

            except Exception as e:
                print(f"{RED}Error reading {summary_file}: {e}{RESET}")

        # Sort summaries within each date
        for date in summaries_by_date:
            summaries_by_date[date].sort(key=lambda p: p.stat().st_mtime)

        return summaries_by_date

    def extract_summary_overview(self, summary_path: Path) -> dict[str, Any]:
        """Extract basic overview from a conversation summary for context"""
        content = summary_path.read_text()
        overview = {
            "main_topic": "Unknown",
            "duration": "Unknown",
            "key_points": [],
            "file_path": str(summary_path),
        }

        # Extract main topic
        match = re.search(r"main_topic:\s*(.+)", content)
        if match:
            overview["main_topic"] = match.group(1).strip()

        # Extract duration
        match = re.search(r"duration:\s*(.+)", content)
        if match:
            overview["duration"] = match.group(1).strip()

        # Find first few bullet points for context
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if (line.startswith(("- ", "* "))) and len(line) > 10:
                point = line[2:].strip()
                if len(point) < 100:  # Keep it concise
                    overview["key_points"].append(point)
                    if len(overview["key_points"]) >= 3:
                        break

        return overview

    def prompt_diary_writing(
        self, date: str, summaries: list[Path], existing_diary: Path | None = None
    ) -> str:
        """Streamlined diary writing prompt"""
        diary_file = self.diaries_dir / f"diary_{date.replace('-', '')}.md"
        action_type = "Appending to" if existing_diary else "Writing New"

        print(f"\n📔 {action_type} Diary Entry for {date}")
        print(f"Sessions: {len(summaries)} to process")
        print()

        # Show session contexts concisely
        print("Session Context:")
        for i, summary_path in enumerate(summaries, 1):
            overview = self.extract_summary_overview(summary_path)
            topic = (
                overview["main_topic"][:50] + "..."
                if len(overview["main_topic"]) > 50
                else overview["main_topic"]
            )
            print(f"  {i}. {topic} ({overview['duration']})")
        print()

        print("🎯 Diary Writing Task:")
        if existing_diary:
            print(f"1. Read existing diary: {existing_diary}")
            print("2. Use Edit tool to append reflections on new sessions above")
        else:
            print(f"1. Write new diary: {diary_file}")
        print(
            "2. Focus on: orchestration learnings, Ocean's guidance, technical insights"
        )
        print("3. Target: 100-200 lines of honest reflection")
        print("4. Run this command again to mark summaries as processed")

        return f"diary_{date.replace('-', '')}.md"

    def check_diary_exists(self, date: str) -> Path | None:
        """Check if diary already exists for this date, return path if exists"""
        diary_file = self.diaries_dir / f"diary_{date.replace('-', '')}.md"
        return diary_file if diary_file.exists() else None

    def mark_summaries_processed(self, summaries: list[Path]) -> None:
        """Mark summaries as processed by adding processed: true flag"""
        for summary_path in summaries:
            try:
                content = summary_path.read_text()

                # Add processed flag at the end if not already present
                if "processed: true" not in content:
                    content += f"\n\n---\nprocessed: true\nprocessed_date: {TimePolicy.now_utc().isoformat()}\n"

                    if not self.dry_run:
                        summary_path.write_text(content)
                        print(
                            f"  {GREEN}✓ Marked {summary_path.name} as processed{RESET}"
                        )
                    else:
                        print(
                            f"  {YELLOW}[DRY RUN] Would mark {summary_path.name} as processed{RESET}"
                        )

            except Exception as e:
                print(f"  {RED}✗ Error marking {summary_path.name}: {e}{RESET}")

    def process_diaries(self):
        """Main process for diary writing assistance"""
        print(f"{BOLD}📔 Diary Writing Assistant{RESET}")
        print(f"{CYAN}Helping you write thoughtful diary entries...{RESET}")
        print()

        summaries_by_date = self.find_unprocessed_summaries()

        if not summaries_by_date:
            print(f"{GREEN}✓ No unprocessed summaries found.{RESET}")
            return

        print(
            f"{BOLD}{YELLOW}Found {sum(len(s) for s in summaries_by_date.values())} unprocessed summaries across {len(summaries_by_date)} dates{RESET}"
        )

        for date in sorted(summaries_by_date.keys()):
            summaries = summaries_by_date[date]

            # Check if diary already exists
            existing_diary = self.check_diary_exists(date)

            if existing_diary and not summaries:
                # Diary exists and no unprocessed summaries for this date
                print(f"\n{GREEN}✓ Diary for {date} already complete{RESET}")
                continue

            if existing_diary:
                # Diary exists but there are new unprocessed summaries
                print(
                    f"\n{YELLOW}📔 Diary for {date} exists, but {len(summaries)} new summaries need to be added{RESET}"
                )
                self.prompt_diary_writing(date, summaries, existing_diary)
            else:
                # No diary exists, create new one
                self.prompt_diary_writing(date, summaries)

            # Check if diary was created/updated after prompting
            if self.check_diary_exists(date):
                print(f"\n{GREEN}✓ Diary for {date} found!{RESET}")
                print(f"  Marking {len(summaries)} summaries as processed...")
                self.mark_summaries_processed(summaries)
            else:
                print(f"\n{YELLOW}⏸  Waiting for diary to be written for {date}{RESET}")
                print("  Summaries remain unprocessed until diary is created.")
                break  # Stop processing until this diary is written

        print(f"\n{GREEN}✓ Diary processing session complete!{RESET}")
