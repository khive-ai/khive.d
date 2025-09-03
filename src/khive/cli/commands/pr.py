"""
Khive PR management commands - Create or view GitHub Pull Requests for the current branch.

Modern service-based implementation with backward compatibility.
"""

import sys

import click

from khive.utils import get_logger

logger = get_logger("KhivePRCLI", "🔀 [PR-CLI]")


@click.command()
@click.option("--title", "-t", help="Pull request title")
@click.option("--body", "-b", help="Pull request body")
@click.option("--base", help="Base branch for the pull request")
@click.option("--head", help="Head branch for the pull request")
@click.option("--draft", "-d", is_flag=True, help="Create as draft pull request")
@click.option("--reviewers", "-r", help="Comma-separated list of reviewers")
@click.option("--assignees", "-a", help="Comma-separated list of assignees")
@click.option("--labels", "-l", help="Comma-separated list of labels")
@click.option("--milestone", "-m", help="Milestone for the pull request")
@click.option("--web", "-w", is_flag=True, help="Open pull request in browser")
@click.option("--push", "-p", is_flag=True, help="Push branch before creating PR")
@click.option("--auto-merge", is_flag=True, help="Enable auto-merge for PR")
@click.option("--template", help="Use PR template")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be done")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option(
    "--json", "json_output", is_flag=True, help="Output results in JSON format"
)
def pr(
    title: str,
    body: str,
    base: str,
    head: str,
    draft: bool,
    reviewers: str,
    assignees: str,
    labels: str,
    milestone: str,
    web: bool,
    push: bool,
    auto_merge: bool,
    template: str,
    dry_run: bool,
    verbose: bool,
    json_output: bool,
):
    """Create or view GitHub Pull Requests for the current branch."""
    try:
        # Import the original implementation
        from khive.cli.khive_pr import main as original_main

        # Reconstruct argv for the original implementation
        argv = []

        # Handle options
        if title:
            argv.extend(["--title", title])
        if body:
            argv.extend(["--body", body])
        if base:
            argv.extend(["--base", base])
        if head:
            argv.extend(["--head", head])
        if reviewers:
            argv.extend(["--reviewers", reviewers])
        if assignees:
            argv.extend(["--assignees", assignees])
        if labels:
            argv.extend(["--labels", labels])
        if milestone:
            argv.extend(["--milestone", milestone])
        if template:
            argv.extend(["--template", template])

        # Handle flags
        if draft:
            argv.append("--draft")
        if web:
            argv.append("--web")
        if push:
            argv.append("--push")
        if auto_merge:
            argv.append("--auto-merge")
        if dry_run:
            argv.append("--dry-run")
        if verbose:
            argv.append("--verbose")
        if json_output:
            argv.append("--json-output")

        # Temporarily replace sys.argv to pass arguments to original implementation
        original_argv = sys.argv
        sys.argv = ["khive pr"] + argv

        try:
            original_main()
        finally:
            sys.argv = original_argv

    except SystemExit as e:
        # Preserve exit codes from the original implementation
        sys.exit(e.code if e.code is not None else 0)
    except Exception as e:
        logger.error(f"PR operation failed: {e}")
        if json_output:
            import json

            click.echo(json.dumps({"status": "failure", "message": str(e)}, indent=2))
        else:
            click.echo(f"❌ Error with pull request: {e}", err=True)
        sys.exit(1)


def cli_entry() -> None:
    """Entry point for the pr command."""
    pr()


if __name__ == "__main__":
    cli_entry()
