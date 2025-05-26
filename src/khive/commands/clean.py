"""clean.py - Delete local and remote Git branches"""

from __future__ import annotations

from khive.services.dev.khive_clean import main as original_main


def cli_entry() -> None:
    """
    Entry point for the clean command.

    This function delegates to the original implementation.
    """
    original_main()


if __name__ == "__main__":
    cli_entry()
