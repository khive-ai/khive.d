"""commit.py - Create Conventional Commits with staging and push options."""

from __future__ import annotations

from khive.services.git.khive_git import main as original_main


def cli_entry() -> None:
    """
    Entry point for the commit command.

    This function delegates to the original implementation.
    """
    original_main()


if __name__ == "__main__":
    cli_entry()
