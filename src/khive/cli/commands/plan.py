from __future__ import annotations

from khive.services.plan.khive_plan import main as consensus_main


def cli_entry() -> None:
    """CLI entry point for multi-round consensus planning."""
    consensus_main()


if __name__ == "__main__":
    cli_entry()
