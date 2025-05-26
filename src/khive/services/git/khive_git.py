#!/usr/bin/env python3
# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_git.py - Natural language git operations for humans and AI agents.

This CLI provides an intuitive interface to the agent-centric Git Service,
allowing users to express git operations in natural language.

Examples:
    # Basic operations
    khive git "save my progress"
    khive git "what changed?"
    khive git "create a PR"

    # With context
    khive git "I finished the OAuth feature" --context "Implemented PKCE flow"
    khive git "ready for review" --issues 123,456

    # Interactive mode
    khive git --interactive

    # Continue a session
    khive git "push the changes" --session abc123

    # JSON output for agents
    khive git "analyze code quality" --json
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import questionary
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from khive.services.git import GitRequest, GitService, WorkContext

# Initialize Rich console for beautiful output
console = Console()


class GitCLI:
    """Command-line interface for the Git Service."""

    def __init__(self):
        self.service = GitService()
        self.session_file = Path.home() / ".khive" / "git_session.json"
        self.history_file = Path.home() / ".khive" / "git_history.json"
        self.current_session_id = None

        # Ensure config directory exists
        self.session_file.parent.mkdir(parents=True, exist_ok=True)

    async def run(self, args: argparse.Namespace) -> int:
        """Run the CLI with the given arguments."""
        try:
            if args.interactive:
                return await self.interactive_mode()
            elif args.status:
                return await self.show_status()
            elif args.history:
                return await self.show_history()
            elif args.continue_session:
                return await self.continue_session()
            else:
                # Single command mode
                return await self.execute_request(args)

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
            return 130
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return 1
        finally:
            await self.service.close()

    async def execute_request(self, args: argparse.Namespace) -> int:
        """Execute a single git request."""
        # Build context from arguments
        context = None
        if any([args.context, args.issues, args.requirements, args.decisions]):
            context = WorkContext(
                task_description=args.context,
                related_issues=args.issues.split(",") if args.issues else [],
                requirements=args.requirements.split("|") if args.requirements else [],
                design_decisions=args.decisions.split("|") if args.decisions else [],
            )

        # Load or use session
        session_id = args.session or self.load_session_id()

        # Create request
        request = GitRequest(
            request=args.request,
            context=context,
            agent_id=args.agent_id or os.environ.get("KHIVE_AGENT_ID", "human-cli"),
            conversation_id=session_id,
            preferences={"commit_style": args.commit_style, "verbose": args.verbose},
        )

        # Execute request
        with console.status("[bold green]Processing request...[/bold green]"):
            response = await self.service.handle_request(request)

        # Save session ID
        if response.conversation_id:
            self.save_session_id(response.conversation_id)
            self.current_session_id = response.conversation_id

        # Add to history
        self.add_to_history(args.request, response)

        # Display response
        if args.json:
            self.display_json_response(response)
        else:
            self.display_response(response)

        return 0 if response.success else 1

    async def interactive_mode(self) -> int:
        """Run in interactive mode."""
        console.print(
            Panel.fit(
                "[bold green]Git Service Interactive Mode[/bold green]\n"
                "Express what you want to do in natural language.\n"
                "Type 'help' for examples, 'exit' to quit.",
                title="Welcome",
            )
        )

        # Load session if exists
        session_id = self.load_session_id()
        if session_id:
            console.print(f"[dim]Continuing session: {session_id}[/dim]\n")

        while True:
            try:
                # Get input
                request_text = await self.get_interactive_input()

                if request_text.lower() in ["exit", "quit", "q"]:
                    break
                elif request_text.lower() == "help":
                    self.show_help()
                    continue
                elif request_text.lower() == "status":
                    await self.show_status()
                    continue
                elif request_text.lower() == "history":
                    await self.show_history()
                    continue

                # Build context interactively if needed
                context = await self.build_interactive_context(request_text)

                # Create and execute request
                request = GitRequest(
                    request=request_text,
                    context=context,
                    agent_id="human-interactive",
                    conversation_id=session_id,
                )

                with console.status("[bold green]Processing...[/bold green]"):
                    response = await self.service.handle_request(request)

                # Update session
                if response.conversation_id:
                    session_id = response.conversation_id
                    self.save_session_id(session_id)

                # Display response
                self.display_response(response)

                # Show follow-up prompts
                if response.follow_up_prompts:
                    console.print("\n[bold]Suggestions:[/bold]")
                    for i, prompt in enumerate(response.follow_up_prompts, 1):
                        console.print(f"  {i}. {prompt}")

            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
                continue

        console.print("\n[green]Thanks for using Git Service![/green]")
        return 0

    async def get_interactive_input(self) -> str:
        """Get input in interactive mode."""
        # Show current branch in prompt
        try:
            from khive.utils import CommandResult, git_run

            result = git_run(["branch", "--show-current"], capture=True, check=False)
            branch = "unknown"
            if isinstance(result, CommandResult) and result.stdout:
                branch = result.stdout.strip()

            prompt = f"[{branch}]> "
        except:
            prompt = "> "

        return questionary.text(
            prompt, multiline=False, instruction="(What would you like to do?)"
        ).ask()

    async def build_interactive_context(self, request_text: str) -> WorkContext | None:
        """Build context interactively if needed."""
        # Check if request might benefit from context
        context_keywords = ["implement", "feature", "fix", "working on", "task"]
        needs_context = any(
            keyword in request_text.lower() for keyword in context_keywords
        )

        if not needs_context:
            return None

        # Ask if user wants to add context
        add_context = questionary.confirm(
            "Would you like to add more context?", default=False
        ).ask()

        if not add_context:
            return None

        context = WorkContext()

        # Task description
        task = questionary.text(
            "What are you working on?", instruction="(Brief description)"
        ).ask()
        if task:
            context.task_description = task

        # Related issues
        issues = questionary.text(
            "Related issue numbers?", instruction="(Comma-separated, e.g., 123,456)"
        ).ask()
        if issues:
            context.related_issues = [i.strip() for i in issues.split(",")]

        # Requirements
        if questionary.confirm("Add requirements?", default=False).ask():
            reqs = []
            while True:
                req = questionary.text("Requirement (empty to finish):").ask()
                if not req:
                    break
                reqs.append(req)
            context.requirements = reqs

        return context

    async def show_status(self) -> int:
        """Show repository status."""
        request = GitRequest(
            request="What's the current status?", agent_id="status-check"
        )

        with console.status("[bold green]Checking repository status...[/bold green]"):
            response = await self.service.handle_request(request)

        if not response.repository_state:
            console.print("[red]Could not get repository status[/red]")
            return 1

        state = response.repository_state

        # Create status table
        table = Table(title="Repository Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Branch", state.current_branch)
        table.add_row("Branch Purpose", state.branch_purpose)
        table.add_row("Work Phase", state.work_phase)
        table.add_row("Has Changes", "Yes" if state.has_uncommitted_changes else "No")
        table.add_row("Has Staged", "Yes" if state.has_staged_changes else "No")
        table.add_row("Commits Ahead", str(state.commits_ahead))
        table.add_row("Commits Behind", str(state.commits_behind))

        if state.existing_pr:
            table.add_row(
                "Pull Request",
                f"#{state.existing_pr.number} ({state.existing_pr.state})",
            )

        console.print(table)

        # Show file changes
        if state.changes_summary and state.changes_summary.total_files > 0:
            console.print("\n[bold]Changes:[/bold]")
            tree = Tree("📁 Modified Files")

            if state.changes_summary.code_files:
                code_branch = tree.add("💻 Code")
                for file in state.changes_summary.code_files[:5]:
                    code_branch.add(f"{file.path}")

            if state.changes_summary.test_files:
                test_branch = tree.add("🧪 Tests")
                for file in state.changes_summary.test_files[:5]:
                    test_branch.add(f"{file.path}")

            if state.changes_summary.doc_files:
                doc_branch = tree.add("📚 Docs")
                for file in state.changes_summary.doc_files[:5]:
                    doc_branch.add(f"{file.path}")

            console.print(tree)

        # Show recommendations
        if response.recommendations:
            console.print("\n[bold]Recommended Actions:[/bold]")
            for i, rec in enumerate(response.recommendations[:3], 1):
                console.print(f"\n{i}. [yellow]{rec.action}[/yellow]")
                console.print(f"   [dim]Why: {rec.reason}[/dim]")
                console.print(f"   [dim]How: {rec.example_request}[/dim]")

        return 0

    async def show_history(self) -> int:
        """Show command history."""
        history = self.load_history()

        if not history:
            console.print("[yellow]No command history found[/yellow]")
            return 0

        table = Table(title="Command History")
        table.add_column("Time", style="cyan")
        table.add_column("Request", style="green")
        table.add_column("Result", style="yellow")
        table.add_column("Session", style="dim")

        for entry in history[-10:]:  # Last 10 entries
            time_str = datetime.fromisoformat(entry["timestamp"]).strftime(
                "%Y-%m-%d %H:%M"
            )
            request = (
                entry["request"][:50] + "..."
                if len(entry["request"]) > 50
                else entry["request"]
            )
            result = "✓" if entry["success"] else "✗"
            session = entry.get("session_id", "")[:8]

            table.add_row(time_str, request, result, session)

        console.print(table)
        return 0

    async def continue_session(self) -> int:
        """Continue the last session interactively."""
        session_id = self.load_session_id()

        if not session_id:
            console.print("[yellow]No previous session found[/yellow]")
            return 1

        console.print(f"[green]Continuing session: {session_id}[/green]")

        # Get the last state
        request = GitRequest(
            request="What's the current state?",
            conversation_id=session_id,
            agent_id="session-continue",
        )

        response = await self.service.handle_request(request)
        self.display_response(response)

        # Continue interactively
        return await self.interactive_mode()

    def display_response(self, response):
        """Display response in a user-friendly format."""
        # Header
        status_emoji = "✅" if response.success else "❌"
        console.print(f"\n{status_emoji} [bold]{response.understood_as}[/bold]")

        # Actions taken
        if response.actions_taken:
            console.print("\n[bold]Actions:[/bold]")
            for action in response.actions_taken:
                console.print(f"  • {action}")

        # Current state summary
        if response.repository_state:
            state = response.repository_state
            status_line = f"\n📍 {state.current_branch}"
            if state.work_phase:
                status_line += f" ({state.work_phase})"
            console.print(status_line)

        # Key learnings
        if response.learned:
            console.print("\n[bold]Details:[/bold]")
            for key, value in response.learned.items():
                if key == "commit_sha" and isinstance(value, str):
                    console.print(f"  • Commit: {value[:8]}")
                elif key == "pr_url" and isinstance(value, str):
                    console.print(f"  • PR: [link={value}]{value}[/link]")
                elif key == "commit_message" and isinstance(value, str):
                    # Show commit message in a box
                    console.print("\n[bold]Commit Message:[/bold]")
                    console.print(Panel(value, border_style="green"))
                elif key == "key_insights" and isinstance(value, list):
                    console.print("  • Insights:")
                    for insight in value[:3]:
                        console.print(f"    - {insight}")
                elif not isinstance(value, (dict, list)) and key not in ["error"]:
                    console.print(f"  • {key.replace('_', ' ').title()}: {value}")

        # Recommendations
        if response.recommendations:
            console.print("\n[bold]Next Steps:[/bold]")
            for i, rec in enumerate(response.recommendations[:3], 1):
                urgency_color = {
                    "urgent": "red",
                    "required": "red",
                    "recommended": "yellow",
                    "optional": "green",
                    "whenever": "dim",
                }.get(rec.urgency, "white")

                console.print(
                    f"\n  {i}. [{urgency_color}]{rec.action}[/{urgency_color}]"
                )
                console.print(f"     [dim]{rec.reason}[/dim]")
                if rec.prerequisites:
                    console.print(
                        f"     [dim]Requires: {', '.join(rec.prerequisites)}[/dim]"
                    )

        # Summary message
        if response.summary:
            console.print(f"\n💡 [italic]{response.summary}[/italic]")

        # Session info
        if (
            response.conversation_id
            and self.current_session_id != response.conversation_id
        ):
            console.print(f"\n[dim]Session: {response.conversation_id}[/dim]")

    def display_json_response(self, response):
        """Display response as JSON."""
        output = {
            "success": response.success,
            "understood_as": response.understood_as,
            "actions_taken": response.actions_taken,
            "summary": response.summary,
            "session_id": response.conversation_id,
        }

        if response.repository_state:
            output["state"] = {
                "branch": response.repository_state.current_branch,
                "has_changes": response.repository_state.has_uncommitted_changes,
                "work_phase": response.repository_state.work_phase,
            }

        if response.recommendations:
            output["recommendations"] = [
                {
                    "action": rec.action,
                    "urgency": rec.urgency,
                    "how": rec.example_request,
                }
                for rec in response.recommendations[:3]
            ]

        if response.learned:
            output["details"] = response.learned

        print(json.dumps(output, indent=2))

    def show_help(self):
        """Show help information."""
        help_text = """
# Git Service Help

## Example Commands:

### Basic Operations
- "save my progress" - Commit current changes
- "what changed?" - Show repository status
- "create a PR" - Create pull request
- "push my changes" - Push to remote

### Working with Features
- "I'm starting work on the payment feature"
- "I finished implementing OAuth"
- "Ready to share this for review"

### Analysis
- "analyze code quality"
- "what's the commit history?"
- "find patterns in the codebase"

### Collaboration
- "check PR status"
- "incorporate feedback"
- "who should review this?"

### Maintenance
- "clean up old branches"
- "undo the last commit"
- "organize the repository"

## Interactive Commands:
- help - Show this help
- status - Show repository status
- history - Show command history
- exit - Exit interactive mode

## Tips:
- Provide context for better results
- Use natural language - no git commands needed
- Sessions maintain context across commands
"""
        console.print(Markdown(help_text))

    def save_session_id(self, session_id: str):
        """Save session ID for later use."""
        try:
            self.session_file.write_text(
                json.dumps({
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                })
            )
        except Exception:
            pass

    def load_session_id(self) -> str | None:
        """Load saved session ID."""
        try:
            if self.session_file.exists():
                data = json.loads(self.session_file.read_text())
                # Check if session is recent (within 2 hours)
                timestamp = datetime.fromisoformat(data["timestamp"])
                age = datetime.utcnow() - timestamp
                if age.total_seconds() < 7200:  # 2 hours
                    return data["session_id"]
        except Exception:
            pass
        return None

    def add_to_history(self, request: str, response):
        """Add command to history."""
        try:
            history = self.load_history()
            history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "request": request,
                "success": response.success,
                "session_id": response.conversation_id,
                "understood_as": response.understood_as,
            })

            # Keep last 100 entries
            history = history[-100:]

            self.history_file.write_text(json.dumps(history, indent=2))
        except Exception:
            pass

    def load_history(self) -> list[dict[str, Any]]:
        """Load command history."""
        try:
            if self.history_file.exists():
                return json.loads(self.history_file.read_text())
        except Exception:
            pass
        return []


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Natural language git operations",
        epilog="Examples:\n"
        '  khive git "save my progress"\n'
        '  khive git "create a PR" --issues 123\n'
        "  khive git --interactive\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Main argument
    parser.add_argument(
        "request", nargs="?", help="What you want to do (in natural language)"
    )

    # Mode options
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )
    mode_group.add_argument(
        "--status", "-s", action="store_true", help="Show repository status"
    )
    mode_group.add_argument(
        "--history", action="store_true", help="Show command history"
    )
    mode_group.add_argument(
        "--continue-session", "-c", action="store_true", help="Continue last session"
    )

    # Context options
    context_group = parser.add_argument_group("context options")
    context_group.add_argument(
        "--context", help="Additional context about what you're working on"
    )
    context_group.add_argument(
        "--issues", help="Related issue numbers (comma-separated)"
    )
    context_group.add_argument("--requirements", help="Requirements (pipe-separated)")
    context_group.add_argument("--decisions", help="Design decisions (pipe-separated)")

    # Session options
    session_group = parser.add_argument_group("session options")
    session_group.add_argument("--session", help="Continue specific session")
    session_group.add_argument("--agent-id", help="Agent identifier (for tracking)")

    # Output options
    output_group = parser.add_argument_group("output options")
    output_group.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )
    output_group.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )

    # Style options
    parser.add_argument(
        "--commit-style",
        choices=["conventional", "detailed", "simple"],
        default="conventional",
        help="Commit message style",
    )

    args = parser.parse_args()

    # Validate arguments
    if not any([
        args.request,
        args.interactive,
        args.status,
        args.history,
        args.continue_session,
    ]):
        parser.error("No request provided. Use --interactive for interactive mode.")

    # Run CLI
    cli = GitCLI()
    exit_code = asyncio.run(cli.run(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
