# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

# Import the original implementation
from khive.cli.khive_init import main as original_main


def cli_entry() -> None:
    original_main()


if __name__ == "__main__":
    cli_entry()
