from dataclasses import dataclass, field
import json
import sys
from typing import Any


# --- ANSI Colors and Logging ---
ANSI = {
    "G": "\033[32m" if sys.stdout.isatty() else "",
    "R": "\033[31m" if sys.stdout.isatty() else "",
    "Y": "\033[33m" if sys.stdout.isatty() else "",
    "B": "\033[34m" if sys.stdout.isatty() else "",
    "M": "\033[35m" if sys.stdout.isatty() else "",
    "C": "\033[36m" if sys.stdout.isatty() else "",
    "N": "\033[0m" if sys.stdout.isatty() else "",
    "BOLD": "\033[1m" if sys.stdout.isatty() else "",
}
verbose_mode = False


def log_msg(msg: str, *, kind: str = "B") -> None:
    if verbose_mode:
        print(f"{ANSI[kind]}▶{ANSI['N']} {msg}")


def format_message(prefix: str, msg: str, color_code: str) -> str:
    return f"{color_code}{prefix}{ANSI['N']} {msg}"


def info_msg(msg: str, *, console: bool = True) -> str:
    output = format_message("✔", msg, ANSI["G"])
    if console:
        print(output)
    return output


def warn_msg(msg: str, *, console: bool = True) -> str:
    output = format_message("⚠", msg, ANSI["Y"])
    if console:
        print(output, file=sys.stderr)
    return output


def error_msg(msg: str, *, console: bool = True) -> str:
    output = format_message("✖", msg, ANSI["R"])
    if console:
        print(output, file=sys.stderr)
    return output


def die(
    msg: str, json_data: dict[str, Any] | None = None, json_output_flag: bool = False
) -> None:
    error_msg(msg, console=not json_output_flag)
    if json_output_flag:
        base_data = {"status": "failure", "message": msg, "stacks_processed": []}
        if json_data and "stacks_processed" in json_data:
            base_data["stacks_processed"] = json_data["stacks_processed"]
        print(json.dumps(base_data, indent=2))
    sys.exit(1)


# --- Configuration ---
@dataclass
class StackConfig:
    name: str
    cmd: str
    check_cmd: str
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    enabled: bool = True
