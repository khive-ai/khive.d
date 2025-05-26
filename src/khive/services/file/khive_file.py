# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Natural file operations CLI for Khive.

Examples:
    # Read a file
    khive file read README.md
    khive file read config.json --encoding utf-8

    # Write content
    khive file write output.txt "Hello, World!"
    echo "Content" | khive file write output.txt -

    # List directory
    khive file list .
    khive file list src --recursive --pattern "*.py"

    # Copy/Move files
    khive file copy source.txt destination.txt
    khive file move old.txt new.txt --force

    # Get file info
    khive file info package.json

    # Create directory
    khive file mkdir new_project/src/components --parents
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from khive.services.file.parts import FileOperation, FileRequest
from khive.services.file.service import FileServiceGroup


async def execute_operation(args: argparse.Namespace) -> None:
    """Execute file operation based on parsed arguments."""
    service = FileServiceGroup()

    try:
        # Build request based on operation
        request_data = {
            "operation": FileOperation(args.operation),
            "path": args.path,
            "encoding": getattr(args, "encoding", "utf-8"),
            "recursive": getattr(args, "recursive", False),
            "include_hidden": getattr(args, "include_hidden", False),
            "force": getattr(args, "force", False),
            "dry_run": getattr(args, "dry_run", False),
            "backup": getattr(args, "backup", False),
        }

        # Add operation-specific fields
        if hasattr(args, "destination"):
            request_data["destination"] = args.destination

        if hasattr(args, "content"):
            if args.content == "-":
                # Read from stdin
                request_data["content"] = sys.stdin.read()
            else:
                request_data["content"] = args.content

        if hasattr(args, "pattern"):
            request_data["pattern"] = args.pattern

        # Create request
        request = FileRequest(**request_data)

        # Execute
        response = await service.handle_request(request)

        # Format output
        if args.json:
            print(json.dumps(response.model_dump(exclude_none=True), indent=2))
        else:
            format_output(response, args.operation)

        # Exit code
        sys.exit(0 if response.success else 1)

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await service.close()


def format_output(response, operation: str) -> None:
    """Format response for human consumption."""
    if not response.success:
        print(f"❌ {response.error}")
        if response.suggestions:
            print("\n💡 Suggestions:")
            for suggestion in response.suggestions:
                print(f"   • {suggestion}")
        return

    # Format based on operation
    if operation == "read":
        if response.content:
            if response.content.preview:
                print(response.content.preview)
                print(f"\n[File truncated - {response.content.size} bytes total]")
            else:
                content = response.content.content
                if isinstance(content, bytes):
                    print(f"[Binary file - {response.content.size} bytes]")
                else:
                    print(content)

    elif operation == "list":
        if response.listing:
            print(f"📁 {response.listing.path}")
            print(
                f"Total: {response.listing.total_items} items, {_format_size(response.listing.total_size)}\n"
            )

            for entry in response.listing.entries:
                icon = "📁" if entry.type == "directory" else "📄"
                print(f"{icon} {entry.name:<40} {entry.size_human:>10}")

    elif operation == "info":
        if response.file_info:
            info = response.file_info
            print("📋 File Information")
            print(f"Path:     {info.path}")
            print(f"Type:     {info.type}")
            print(f"Size:     {info.size_human} ({info.size:,} bytes)")
            print(f"Modified: {info.modified}")
            if info.mime_type:
                print(f"MIME:     {info.mime_type}")
            if info.line_count:
                print(f"Lines:    {info.line_count:,}")

    else:
        # Operation result
        if response.operation_result:
            print(f"✅ {response.operation_result.message}")
            if response.operation_result.details:
                for key, value in response.operation_result.details.items():
                    if value is not None:
                        print(f"   {key}: {value}")


def _format_size(size: int) -> str:
    """Format size in human-readable form."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def main():
    parser = argparse.ArgumentParser(
        prog="khive file",
        description="Natural file operations",
        epilog="Use 'khive file OPERATION --help' for operation-specific help",
    )

    # Global options
    parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # Subcommands for each operation
    subparsers = parser.add_subparsers(
        dest="operation", help="File operation", required=True
    )

    # READ
    read_parser = subparsers.add_parser("read", help="Read file content")
    read_parser.add_argument("path", help="File to read")
    read_parser.add_argument("--encoding", default="utf-8", help="Text encoding")

    # WRITE
    write_parser = subparsers.add_parser("write", help="Write file content")
    write_parser.add_argument("path", help="File to write")
    write_parser.add_argument("content", help="Content to write (use '-' for stdin)")
    write_parser.add_argument("--encoding", default="utf-8", help="Text encoding")
    write_parser.add_argument("--force", action="store_true", help="Overwrite existing")
    write_parser.add_argument(
        "--backup", action="store_true", help="Backup existing file"
    )

    # APPEND
    append_parser = subparsers.add_parser("append", help="Append to file")
    append_parser.add_argument("path", help="File to append to")
    append_parser.add_argument("content", help="Content to append")
    append_parser.add_argument("--encoding", default="utf-8", help="Text encoding")

    # DELETE
    delete_parser = subparsers.add_parser(
        "delete", aliases=["rm"], help="Delete file/directory"
    )
    delete_parser.add_argument("path", help="Path to delete")
    delete_parser.add_argument("--force", action="store_true", help="Force deletion")
    delete_parser.add_argument(
        "--backup", action="store_true", help="Create backup before deletion"
    )

    # LIST
    list_parser = subparsers.add_parser("list", aliases=["ls"], help="List directory")
    list_parser.add_argument("path", nargs="?", default=".", help="Directory to list")
    list_parser.add_argument(
        "-r", "--recursive", action="store_true", help="List recursively"
    )
    list_parser.add_argument(
        "-a",
        "--all",
        dest="include_hidden",
        action="store_true",
        help="Include hidden files",
    )
    list_parser.add_argument("-p", "--pattern", help="Filter by pattern")

    # TREE
    tree_parser = subparsers.add_parser("tree", help="Show directory tree")
    tree_parser.add_argument("path", nargs="?", default=".", help="Directory root")
    tree_parser.add_argument("-p", "--pattern", help="Filter by pattern")

    # FIND
    find_parser = subparsers.add_parser("find", help="Find files")
    find_parser.add_argument("path", nargs="?", default=".", help="Search root")
    find_parser.add_argument("pattern", help="Search pattern")
    find_parser.add_argument(
        "-r", "--recursive", action="store_true", help="Search recursively"
    )

    # COPY
    copy_parser = subparsers.add_parser("copy", aliases=["cp"], help="Copy files")
    copy_parser.add_argument("path", help="Source path")
    copy_parser.add_argument("destination", help="Destination path")
    copy_parser.add_argument("--force", action="store_true", help="Overwrite existing")
    copy_parser.add_argument(
        "--no-preserve",
        dest="preserve_metadata",
        action="store_false",
        help="Don't preserve metadata",
    )

    # MOVE
    move_parser = subparsers.add_parser(
        "move", aliases=["mv"], help="Move/rename files"
    )
    move_parser.add_argument("path", help="Source path")
    move_parser.add_argument("destination", help="Destination path")
    move_parser.add_argument("--force", action="store_true", help="Overwrite existing")

    # MKDIR
    mkdir_parser = subparsers.add_parser("mkdir", help="Create directory")
    mkdir_parser.add_argument("path", help="Directory to create")
    mkdir_parser.add_argument(
        "-p",
        "--parents",
        dest="force",
        action="store_true",
        help="Create parent directories",
    )

    # INFO
    info_parser = subparsers.add_parser(
        "info", aliases=["stat"], help="Get file information"
    )
    info_parser.add_argument("path", help="Path to inspect")

    # EXISTS
    exists_parser = subparsers.add_parser("exists", help="Check if path exists")
    exists_parser.add_argument("path", help="Path to check")

    # Add common flags to all operation parsers
    for subparser in subparsers.choices.values():
        subparser.add_argument(
            "--dry-run", action="store_true", help="Show what would be done"
        )
        subparser.add_argument(
            "--json", action="store_true", help="Output in JSON format"
        )

    args = parser.parse_args()

    # Run the operation
    asyncio.run(execute_operation(args))


if __name__ == "__main__":
    main()
