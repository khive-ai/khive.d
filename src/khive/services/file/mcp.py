# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
MCP server for natural file operations.

Provides intuitive file system access for agents with built-in safety.
"""

from fastmcp import FastMCP

from khive.services.file.parts import FileOperation, FileRequest
from khive.services.file.service import FileServiceGroup

# Agent-friendly description
instruction = """
Khive File provides natural file system operations with built-in safety.

You can:
- Read and write files with automatic encoding detection
- Navigate directories and find files by pattern
- Copy, move, and manage files with transaction-like safety
- Get rich metadata about files and directories

All operations are sandboxed by default for safety. The service handles
encoding, binary files, and large files intelligently.
"""

mcp = FastMCP(
    name="khive_file",
    instructions=instruction,
    tags=["file", "filesystem", "storage", "io"],
)


@mcp.tool(
    name="file_read",
    description="Read file content with automatic encoding detection",
    tags=["read", "content", "text"],
)
async def file_read(
    path: str,
    encoding: str = "utf-8",
):
    """
    Read file content intelligently.

    Automatically detects text vs binary files and handles large files
    by providing previews.

    Args:
        path: File path to read
        encoding: Text encoding (default: utf-8, use 'binary' for raw bytes)

    Returns:
        File content with metadata including size, type, and encoding
    """
    service = FileServiceGroup()

    try:
        request = FileRequest(
            operation=FileOperation.READ, path=path, encoding=encoding
        )

        response = await service.handle_request(request)

        if response.success and response.content:
            return {
                "content": (
                    response.content.content
                    if isinstance(response.content.content, str)
                    else "[Binary content]"
                ),
                "size": response.content.size,
                "mime_type": response.content.mime_type,
                "encoding": response.content.encoding,
                "line_count": response.content.line_count,
                "preview_only": response.content.preview is not None,
            }
        else:
            return {"error": response.error, "suggestions": response.suggestions}

    except Exception as e:
        return {"error": str(e)}
    finally:
        await service.close()


@mcp.tool(
    name="file_write",
    description="Write or create a file with content",
    tags=["write", "create", "save"],
)
async def file_write(
    path: str,
    content: str,
    encoding: str = "utf-8",
    overwrite: bool = False,
    backup: bool = True,
):
    """
    Write content to a file.

    Creates parent directories automatically. Can backup existing files
    before overwriting.

    Args:
        path: File path to write
        content: Content to write
        encoding: Text encoding (default: utf-8)
        overwrite: Whether to overwrite existing files
        backup: Create backup of existing file before overwriting

    Returns:
        Operation result with bytes written and backup information
    """
    service = FileServiceGroup()

    try:
        request = FileRequest(
            operation=FileOperation.WRITE,
            path=path,
            content=content,
            encoding=encoding,
            force=overwrite,
            backup=backup,
        )

        response = await service.handle_request(request)

        if response.success and response.operation_result:
            return {
                "message": response.operation_result.message,
                "bytes_written": response.operation_result.details.get("bytes_written"),
                "backup_path": response.operation_result.details.get("backup_path"),
                "overwritten": response.operation_result.details.get(
                    "overwritten", False
                ),
            }
        else:
            return {"error": response.error, "suggestions": response.suggestions}

    except Exception as e:
        return {"error": str(e)}
    finally:
        await service.close()


@mcp.tool(
    name="file_list",
    description="List directory contents with rich metadata",
    tags=["list", "directory", "browse"],
)
async def file_list(
    path: str = ".",
    pattern: str | None = None,
    recursive: bool = False,
    include_hidden: bool = False,
):
    """
    List directory contents with filtering options.

    Returns rich metadata for each file including size, type, and timestamps.

    Args:
        path: Directory path (default: current directory)
        pattern: Filter pattern (glob syntax like *.py)
        recursive: List subdirectories recursively
        include_hidden: Include hidden files (starting with .)

    Returns:
        Directory listing with file information
    """
    service = FileServiceGroup()

    try:
        request = FileRequest(
            operation=FileOperation.LIST,
            path=path,
            pattern=pattern,
            recursive=recursive,
            include_hidden=include_hidden,
        )

        response = await service.handle_request(request)

        if response.success and response.listing:
            entries = []
            for entry in response.listing.entries[:50]:  # Limit for MCP response
                entries.append({
                    "name": entry.name,
                    "type": entry.type,
                    "size": entry.size_human,
                    "modified": (
                        entry.modified.isoformat() if entry.modified else None
                    ),
                    "path": entry.path,
                })

            return {
                "directory": response.listing.path,
                "total_items": response.listing.total_items,
                "total_size": _format_size(response.listing.total_size),
                "entries": entries,
                "truncated": len(response.listing.entries) > 50,
            }
        else:
            return {"error": response.error, "suggestions": response.suggestions}

    except Exception as e:
        return {"error": str(e)}
    finally:
        await service.close()


@mcp.tool(
    name="file_info",
    description="Get detailed information about a file or directory",
    tags=["info", "metadata", "stats"],
)
async def file_info(path: str):
    """
    Get comprehensive file or directory information.

    Returns size, timestamps, permissions, type, and more.

    Args:
        path: Path to inspect

    Returns:
        Detailed file information
    """
    service = FileServiceGroup()

    try:
        request = FileRequest(operation=FileOperation.INFO, path=path)

        response = await service.handle_request(request)

        if response.success and response.file_info:
            info = response.file_info
            return {
                "path": info.path,
                "name": info.name,
                "type": info.type,
                "size": info.size_human,
                "size_bytes": info.size,
                "created": info.created.isoformat() if info.created else None,
                "modified": info.modified.isoformat() if info.modified else None,
                "mime_type": info.mime_type,
                "encoding": info.encoding,
                "line_count": info.line_count,
                "permissions": {
                    "readable": info.readable,
                    "writable": info.writable,
                    "executable": info.executable,
                },
                "is_directory": info.type == "directory",
                "item_count": info.item_count,
            }
        else:
            return {"error": response.error, "suggestions": response.suggestions}

    except Exception as e:
        return {"error": str(e)}
    finally:
        await service.close()


@mcp.tool(
    name="file_copy",
    description="Copy files or directories",
    tags=["copy", "duplicate"],
)
async def file_copy(
    source: str,
    destination: str,
    overwrite: bool = False,
):
    """
    Copy a file or directory to a new location.

    Preserves metadata by default. Creates parent directories as needed.

    Args:
        source: Source file or directory
        destination: Destination path
        overwrite: Whether to overwrite existing destination

    Returns:
        Operation result with size copied
    """
    service = FileServiceGroup()

    try:
        request = FileRequest(
            operation=FileOperation.COPY,
            path=source,
            destination=destination,
            force=overwrite,
        )

        response = await service.handle_request(request)

        if response.success and response.operation_result:
            return {
                "message": response.operation_result.message,
                "source": response.operation_result.source,
                "destination": response.operation_result.destination,
                "size": response.operation_result.details.get("size"),
            }
        else:
            return {"error": response.error, "suggestions": response.suggestions}

    except Exception as e:
        return {"error": str(e)}
    finally:
        await service.close()


@mcp.tool(
    name="file_move",
    description="Move or rename files and directories",
    tags=["move", "rename"],
)
async def file_move(
    source: str,
    destination: str,
    overwrite: bool = False,
):
    """
    Move or rename a file or directory.

    Atomic operation when possible. Creates parent directories as needed.

    Args:
        source: Source file or directory
        destination: Destination path or new name
        overwrite: Whether to overwrite existing destination

    Returns:
        Operation result
    """
    service = FileServiceGroup()

    try:
        request = FileRequest(
            operation=FileOperation.MOVE,
            path=source,
            destination=destination,
            force=overwrite,
        )

        response = await service.handle_request(request)

        if response.success and response.operation_result:
            return {
                "message": response.operation_result.message,
                "source": response.operation_result.source,
                "destination": response.operation_result.destination,
            }
        else:
            return {"error": response.error, "suggestions": response.suggestions}

    except Exception as e:
        return {"error": str(e)}
    finally:
        await service.close()


@mcp.tool(
    name="file_delete",
    description="Delete files or directories",
    tags=["delete", "remove"],
)
async def file_delete(
    path: str,
    backup: bool = False,
):
    """
    Delete a file or directory.

    Can create a backup before deletion for safety.

    Args:
        path: Path to delete
        backup: Create backup before deletion

    Returns:
        Operation result with backup path if created
    """
    service = FileServiceGroup()

    try:
        request = FileRequest(operation=FileOperation.DELETE, path=path, backup=backup)

        response = await service.handle_request(request)

        if response.success and response.operation_result:
            return {
                "message": response.operation_result.message,
                "deleted": response.operation_result.source,
                "backup_path": response.operation_result.details.get("backup_path"),
            }
        else:
            return {"error": response.error, "suggestions": response.suggestions}

    except Exception as e:
        return {"error": str(e)}
    finally:
        await service.close()


@mcp.tool(
    name="file_find",
    description="Find files matching a pattern",
    tags=["find", "search", "locate"],
)
async def file_find(
    pattern: str,
    path: str = ".",
    recursive: bool = True,
):
    """
    Find files matching a pattern.

    Uses glob pattern matching (e.g., *.py, test_*, [0-9].txt).

    Args:
        pattern: Search pattern (glob syntax)
        path: Starting directory for search
        recursive: Search in subdirectories

    Returns:
        List of matching files with basic info
    """
    service = FileServiceGroup()

    try:
        request = FileRequest(
            operation=FileOperation.FIND,
            path=path,
            pattern=pattern,
            recursive=recursive,
        )

        response = await service.handle_request(request)

        if response.success and response.listing:
            matches = []
            for entry in response.listing.entries[:100]:  # Limit results
                matches.append({
                    "path": entry.path,
                    "name": entry.name,
                    "type": entry.type,
                    "size": entry.size_human,
                    "modified": (
                        entry.modified.isoformat() if entry.modified else None
                    ),
                })

            return {
                "pattern": pattern,
                "search_root": path,
                "matches_found": response.listing.total_items,
                "matches": matches,
                "truncated": len(response.listing.entries) > 100,
            }
        else:
            return {"error": response.error, "suggestions": response.suggestions}

    except Exception as e:
        return {"error": str(e)}
    finally:
        await service.close()


@mcp.tool(
    name="file_mkdir",
    description="Create a directory",
    tags=["mkdir", "create", "directory"],
)
async def file_mkdir(
    path: str,
    parents: bool = True,
):
    """
    Create a directory.

    Can create parent directories automatically.

    Args:
        path: Directory path to create
        parents: Create parent directories if needed

    Returns:
        Operation result
    """
    service = FileServiceGroup()

    try:
        request = FileRequest(
            operation=FileOperation.MKDIR,
            path=path,
            force=parents,  # force creates parents
        )

        response = await service.handle_request(request)

        if response.success and response.operation_result:
            return {
                "message": response.operation_result.message,
                "created": response.operation_result.destination,
            }
        else:
            return {"error": response.error, "suggestions": response.suggestions}

    except Exception as e:
        return {"error": str(e)}
    finally:
        await service.close()


def _format_size(size: int) -> str:
    """Format size in human-readable form."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


if __name__ == "__main__":
    mcp.run()
