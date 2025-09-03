"""
Khive commit management commands - Create Conventional Commits with staging and push options.

Modern service-based implementation with backward compatibility.
"""

import sys

import click

from khive.utils import get_logger

logger = get_logger("KhiveCommitCLI", "📝 [COMMIT-CLI]")


@click.command()
@click.argument("message", required=False)
@click.option("--type", "-t", help="Conventional commit type (e.g., feat, fix)")
@click.option("--scope", "-s", help="Optional scope of the change")
@click.option("--subject", help="Subject line of the commit")
@click.option("--body", "-b", help="Detailed body of the commit message")
@click.option("--breaking-change", "--bc", help="Description of the breaking change")
@click.option("--closes", "-c", help="Issue number this commit closes (e.g., 123)")
@click.option("--search-id", help="Search ID for evidence (e.g., pplx-abc)")
@click.option("--by", help="Committer persona (e.g., khive-implementer)")
@click.option(
    "--interactive", "-i", is_flag=True, help="Interactive commit message builder"
)
@click.option(
    "--patch", "-p", is_flag=True, help="Use 'git add -p' for interactive staging"
)
@click.option("--all", "-A", is_flag=True, help="Stage all changes")
@click.option("--amend", is_flag=True, help="Amend the previous commit")
@click.option(
    "--push/--no-push", default=None, help="Push after commit (overrides config)"
)
@click.option("--allow-empty", is_flag=True, help="Allow empty commits")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be done")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option(
    "--json", "json_output", is_flag=True, help="Output results in JSON format"
)
def commit(
    message: str,
    type: str,
    scope: str,
    subject: str,
    body: str,
    breaking_change: str,
    closes: str,
    search_id: str,
    by: str,
    interactive: bool,
    patch: bool,
    all: bool,
    amend: bool,
    push: bool,
    allow_empty: bool,
    dry_run: bool,
    verbose: bool,
    json_output: bool,
):
    """Create Conventional Commits with staging and push options."""
    try:
        # Import the original implementation
        from khive.cli.khive_commit import main as original_main

        # Reconstruct argv for the original implementation
        argv = []

        # Handle message argument
        if message:
            argv.append(message)

        # Handle structured arguments
        if type:
            argv.extend(["--type", type])
        if scope:
            argv.extend(["--scope", scope])
        if subject:
            argv.extend(["--subject", subject])
        if body:
            argv.extend(["--body", body])
        if breaking_change:
            argv.extend(["--breaking-change-description", breaking_change])
        if closes:
            argv.extend(["--closes", closes])
        if search_id:
            argv.extend(["--search-id", search_id])
        if by:
            argv.extend(["--by", by])

        # Handle flags
        if interactive:
            argv.append("--interactive")
        if patch:
            argv.append("--patch-stage")
        if all:
            argv.append("--all-stage")
        if amend:
            argv.append("--amend")
        if push is True:
            argv.append("--push")
        elif push is False:
            argv.append("--no-push")
        if allow_empty:
            argv.append("--allow-empty")
        if dry_run:
            argv.append("--dry-run")
        if verbose:
            argv.append("--verbose")
        if json_output:
            argv.append("--json-output")

        # Temporarily replace sys.argv to pass arguments to original implementation
        original_argv = sys.argv
        sys.argv = ["khive commit"] + argv

        try:
            original_main()
        finally:
            sys.argv = original_argv

    except SystemExit as e:
        # Preserve exit codes from the original implementation
        sys.exit(e.code if e.code is not None else 0)
    except Exception as e:
        logger.error(f"Commit operation failed: {e}")
        if json_output:
            import json

            click.echo(json.dumps({"status": "failure", "message": str(e)}, indent=2))
        else:
            click.echo(f"❌ Error creating commit: {e}", err=True)
        sys.exit(1)


def cli_entry() -> None:
    """Entry point for the commit command."""
    commit()


if __name__ == "__main__":
    cli_entry()
