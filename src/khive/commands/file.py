from __future__ import annotations

from khive.services.file.khive_file import main


def cli_entry() -> None:
    """
    Entry point for the file command.

    This function delegates to the original implementation.
    """
    main()


if __name__ == "__main__":
    cli_entry()
