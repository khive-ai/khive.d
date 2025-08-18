from __future__ import annotations

from khive.services.plan.khive_plan import main as original_main


def cli_entry() -> None:
    original_main()


if __name__ == "__main__":
    cli_entry()
