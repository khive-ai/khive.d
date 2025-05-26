from __future__ import annotations

import asyncio
import mimetypes
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles

from khive.services.file.parts import (
    DirectoryListing,
    FileContent,
    FileInfo,
    FileOperation,
    FileRequest,
    FileResponse,
    FileType,
)
from khive.types import Service


class FileServiceGroup(Service):
    """
    Natural file system operations for agents.

    Provides intuitive file operations that feel like enhanced Unix commands
    with built-in safety, validation, and rich metadata.
    """

    def __init__(self, base_path: str | None = None, sandbox_mode: bool = True):
        """
        Initialize file service.

        Args:
            base_path: Root directory for all operations (sandbox)
            sandbox_mode: Whether to restrict operations to base_path
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.sandbox_mode = sandbox_mode

        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Track open file handles for cleanup
        self._open_files: dict[str, Any] = {}

        # File type detection
        mimetypes.init()

    async def handle_request(self, request: FileRequest) -> FileResponse:
        """
        Handle file operation request.

        Routes to appropriate handler based on operation type.
        """
        start_time = time.time()

        try:
            # Validate and resolve paths
            path = self._resolve_path(request.path)
            destination = None
            if request.destination:
                destination = self._resolve_path(request.destination)

            # Route to appropriate handler
            if request.operation == FileOperation.READ:
                result = await self._read_file(path, request)
            elif request.operation == FileOperation.WRITE:
                result = await self._write_file(path, request)
            elif request.operation == FileOperation.APPEND:
                result = await self._append_file(path, request)
            elif request.operation == FileOperation.DELETE:
                result = await self._delete_path(path, request)
            elif request.operation == FileOperation.LIST:
                result = await self._list_directory(path, request)
            elif request.operation == FileOperation.TREE:
                result = await self._tree_directory(path, request)
            elif request.operation == FileOperation.FIND:
                result = await self._find_files(path, request)
            elif request.operation == FileOperation.COPY:
                result = await self._copy_path(path, destination, request)
            elif request.operation == FileOperation.MOVE:
                result = await self._move_path(path, destination, request)
            elif request.operation == FileOperation.MKDIR:
                result = await self._make_directory(path, request)
            elif request.operation == FileOperation.INFO:
                result = await self._get_info(path, request)
            elif request.operation == FileOperation.EXISTS:
                result = await self._check_exists(path, request)
            else:
                raise ValueError(f"Unsupported operation: {request.operation}")

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            return FileResponse(
                success=True,
                operation=request.operation,
                duration_ms=duration_ms,
                **result,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return FileResponse(
                success=False,
                operation=request.operation,
                duration_ms=duration_ms,
                error=str(e),
                error_details={"type": type(e).__name__},
                suggestions=self._get_error_suggestions(e),
            )

    # Path resolution and validation

    def _resolve_path(self, path_str: str) -> Path:
        """Resolve and validate path within sandbox."""
        path = Path(path_str)

        # Make absolute
        if not path.is_absolute():
            path = self.base_path / path

        # Resolve to real path
        try:
            path = path.resolve()
        except Exception:
            # Path doesn't exist yet, resolve parent
            path = path.parent.resolve() / path.name

        # Sandbox validation
        if self.sandbox_mode:
            try:
                path.relative_to(self.base_path)
            except ValueError:
                raise PermissionError(
                    f"Path '{path}' is outside sandbox '{self.base_path}'"
                )

        return path

    # File operations

    async def _read_file(self, path: Path, request: FileRequest) -> dict[str, Any]:
        """Read file content."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not path.is_file():
            raise IsADirectoryError(f"Path is a directory: {path}")

        # Detect file type
        mime_type, _ = mimetypes.guess_type(str(path))
        is_text = mime_type and mime_type.startswith("text")

        # Get file stats
        stat = path.stat()
        size = stat.st_size

        # Read content
        try:
            if is_text or request.encoding != "binary":
                async with aiofiles.open(path, "r", encoding=request.encoding) as f:
                    content = await f.read()
                    line_count = content.count("\n") + (
                        1 if content and not content.endswith("\n") else 0
                    )
            else:
                async with aiofiles.open(path, "rb") as f:
                    content = await f.read()
                    line_count = None

            # Create preview for large files
            preview = None
            if isinstance(content, str) and len(content) > 10000:
                preview = (
                    content[:1000] + f"\n... ({len(content) - 1000} more characters)"
                )

            return {
                "content": FileContent(
                    path=str(path),
                    content=content,
                    encoding=request.encoding if isinstance(content, str) else "binary",
                    mime_type=mime_type,
                    size=size,
                    line_count=line_count,
                    preview=preview,
                )
            }

        except UnicodeDecodeError:
            # Retry as binary
            async with aiofiles.open(path, "rb") as f:
                content = await f.read()

            return {
                "content": FileContent(
                    path=str(path),
                    content=content,
                    encoding="binary",
                    mime_type=mime_type or "application/octet-stream",
                    size=size,
                    line_count=None,
                    preview=None,
                )
            }

    async def _write_file(self, path: Path, request: FileRequest) -> dict[str, Any]:
        """Write file content."""
        if not request.content:
            raise ValueError("No content provided for write operation")

        # Check if file exists
        exists = path.exists()

        # Backup if requested
        backup_path = None
        if exists and request.backup:
            backup_path = path.with_suffix(path.suffix + ".bak")
            shutil.copy2(path, backup_path)

        # Dry run
        if request.dry_run:
            return {
                "operation_result": FileOperation(
                    operation="write",
                    success=True,
                    destination=str(path),
                    message=f"Would write {len(request.content)} bytes to {path}",
                    details={
                        "would_overwrite": exists,
                        "backup_created": backup_path is not None,
                    },
                )
            }

        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        if isinstance(request.content, str):
            async with aiofiles.open(path, "w", encoding=request.encoding) as f:
                await f.write(request.content)
                bytes_written = len(request.content.encode(request.encoding))
        else:
            async with aiofiles.open(path, "wb") as f:
                await f.write(request.content)
                bytes_written = len(request.content)

        return {
            "operation_result": FileOperation(
                operation="write",
                success=True,
                destination=str(path),
                message=f"Wrote {bytes_written} bytes to {path}",
                details={
                    "bytes_written": bytes_written,
                    "overwritten": exists,
                    "backup_path": str(backup_path) if backup_path else None,
                },
            )
        }

    async def _append_file(self, path: Path, request: FileRequest) -> dict[str, Any]:
        """Append to file."""
        if not request.content:
            raise ValueError("No content provided for append operation")

        # Create file if doesn't exist
        if not path.exists():
            return await self._write_file(path, request)

        # Append content
        if isinstance(request.content, str):
            async with aiofiles.open(path, "a", encoding=request.encoding) as f:
                await f.write(request.content)
                bytes_written = len(request.content.encode(request.encoding))
        else:
            async with aiofiles.open(path, "ab") as f:
                await f.write(request.content)
                bytes_written = len(request.content)

        return {
            "operation_result": FileOperation(
                operation="append",
                success=True,
                destination=str(path),
                message=f"Appended {bytes_written} bytes to {path}",
                details={"bytes_written": bytes_written},
            )
        }

    async def _delete_path(self, path: Path, request: FileRequest) -> dict[str, Any]:
        """Delete file or directory."""
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        # Dry run
        if request.dry_run:
            is_dir = path.is_dir()
            size = self._get_tree_size(path) if is_dir else path.stat().st_size
            return {
                "operation_result": FileOperation(
                    operation="delete",
                    success=True,
                    source=str(path),
                    message=f"Would delete {'directory' if is_dir else 'file'} {path}",
                    details={"size": size, "is_directory": is_dir},
                )
            }

        # Backup if requested
        backup_path = None
        if request.backup:
            backup_path = path.with_suffix(".deleted")
            if path.is_dir():
                shutil.copytree(path, backup_path)
            else:
                shutil.copy2(path, backup_path)

        # Delete
        if path.is_dir():
            shutil.rmtree(path)
            message = f"Deleted directory {path}"
        else:
            path.unlink()
            message = f"Deleted file {path}"

        return {
            "operation_result": FileOperation(
                operation="delete",
                success=True,
                source=str(path),
                message=message,
                details={"backup_path": str(backup_path) if backup_path else None},
            )
        }

    async def _list_directory(self, path: Path, request: FileRequest) -> dict[str, Any]:
        """List directory contents."""
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if not path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {path}")

        entries = []
        total_size = 0

        # Iterate directory
        for item in path.iterdir():
            # Skip hidden files if requested
            if not request.include_hidden and item.name.startswith("."):
                continue

            # Apply pattern filter
            if request.pattern and not self._match_pattern(item.name, request.pattern):
                continue

            # Get file info
            info = await self._get_file_info(item)
            entries.append(info)
            total_size += info.size

            # Recursive listing
            if request.recursive and item.is_dir():
                sub_result = await self._list_directory(item, request)
                entries.extend(sub_result["listing"].entries)
                total_size += sub_result["listing"].total_size

        # Sort entries
        entries.sort(key=lambda x: (x.type != FileType.DIRECTORY, x.name.lower()))

        return {
            "listing": DirectoryListing(
                path=str(path),
                entries=entries,
                total_items=len(entries),
                total_size=total_size,
                pattern=request.pattern,
                include_hidden=request.include_hidden,
                recursive=request.recursive,
            )
        }

    async def _tree_directory(self, path: Path, request: FileRequest) -> dict[str, Any]:
        """Show directory tree structure."""
        # Use list with recursive=True and format as tree
        request.recursive = True
        list_result = await self._list_directory(path, request)

        # Convert to tree structure (simplified for now)
        # In a full implementation, this would create an ASCII tree
        return list_result

    async def _find_files(self, path: Path, request: FileRequest) -> dict[str, Any]:
        """Find files matching pattern."""
        if not request.pattern:
            raise ValueError("Pattern required for find operation")

        # Use list with pattern
        return await self._list_directory(path, request)

    async def _copy_path(
        self, source: Path, destination: Path, request: FileRequest
    ) -> dict[str, Any]:
        """Copy file or directory."""
        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source}")

        if not destination:
            raise ValueError("Destination required for copy operation")

        # Handle directory destination
        if destination.exists() and destination.is_dir():
            destination = destination / source.name

        # Check overwrite
        if destination.exists() and not request.force:
            raise FileExistsError(f"Destination exists: {destination}")

        # Dry run
        if request.dry_run:
            return {
                "operation_result": FileOperation(
                    operation="copy",
                    success=True,
                    source=str(source),
                    destination=str(destination),
                    message=f"Would copy {source} to {destination}",
                    details={"would_overwrite": destination.exists()},
                )
            }

        # Create parent directories
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Copy
        if source.is_dir():
            shutil.copytree(
                source,
                destination,
                dirs_exist_ok=request.force,
                symlinks=request.follow_symlinks,
            )
            message = f"Copied directory {source} to {destination}"
        else:
            (
                shutil.copy2(source, destination)
                if request.preserve_metadata
                else shutil.copy(source, destination)
            )
            message = f"Copied file {source} to {destination}"

        return {
            "operation_result": FileOperation(
                operation="copy",
                success=True,
                source=str(source),
                destination=str(destination),
                message=message,
                details={"size": self._get_tree_size(destination)},
            )
        }

    async def _move_path(
        self, source: Path, destination: Path, request: FileRequest
    ) -> dict[str, Any]:
        """Move/rename file or directory."""
        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source}")

        if not destination:
            raise ValueError("Destination required for move operation")

        # Handle directory destination
        if destination.exists() and destination.is_dir():
            destination = destination / source.name

        # Check overwrite
        if destination.exists() and not request.force:
            raise FileExistsError(f"Destination exists: {destination}")

        # Dry run
        if request.dry_run:
            return {
                "operation_result": FileOperation(
                    operation="move",
                    success=True,
                    source=str(source),
                    destination=str(destination),
                    message=f"Would move {source} to {destination}",
                    details={"would_overwrite": destination.exists()},
                )
            }

        # Create parent directories
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Move
        shutil.move(str(source), str(destination))

        return {
            "operation_result": FileOperation(
                operation="move",
                success=True,
                source=str(source),
                destination=str(destination),
                message=f"Moved {source} to {destination}",
            )
        }

    async def _make_directory(self, path: Path, request: FileRequest) -> dict[str, Any]:
        """Create directory."""
        if path.exists():
            if not request.force:
                raise FileExistsError(f"Path exists: {path}")
            elif not path.is_dir():
                raise FileExistsError(f"Path exists and is not a directory: {path}")

        # Dry run
        if request.dry_run:
            return {
                "operation_result": FileOperation(
                    operation="mkdir",
                    success=True,
                    destination=str(path),
                    message=f"Would create directory {path}",
                    details={"exists": path.exists()},
                )
            }

        # Create directory
        path.mkdir(parents=True, exist_ok=True)

        return {
            "operation_result": FileOperation(
                operation="mkdir",
                success=True,
                destination=str(path),
                message=f"Created directory {path}",
            )
        }

    async def _get_info(self, path: Path, request: FileRequest) -> dict[str, Any]:
        """Get file/directory information."""
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        info = await self._get_file_info(path)
        return {"file_info": info}

    async def _check_exists(self, path: Path, request: FileRequest) -> dict[str, Any]:
        """Check if path exists."""
        exists = path.exists()
        info = None

        if exists:
            info = await self._get_file_info(path)

        return {
            "file_info": info,
            "operation_result": FileOperation(
                operation="exists",
                success=True,
                source=str(path),
                message=f"Path {'exists' if exists else 'does not exist'}: {path}",
                details={"exists": exists},
            ),
        }

    # Helper methods

    async def _get_file_info(self, path: Path) -> FileInfo:
        """Get comprehensive file information."""
        try:
            stat = path.stat()

            # Determine file type
            if path.is_symlink():
                file_type = FileType.SYMLINK
            elif path.is_dir():
                file_type = FileType.DIRECTORY
            elif path.is_file():
                file_type = FileType.FILE
            else:
                file_type = FileType.UNKNOWN

            # Get size
            if file_type == FileType.DIRECTORY:
                size = self._get_tree_size(path)
                item_count = len(list(path.iterdir()))
            else:
                size = stat.st_size
                item_count = None

            # MIME type
            mime_type = None
            if file_type == FileType.FILE:
                mime_type, _ = mimetypes.guess_type(str(path))

            # Line count for text files
            line_count = None
            encoding = None
            if (
                file_type == FileType.FILE
                and mime_type
                and mime_type.startswith("text")
            ):
                try:
                    with open(path, encoding="utf-8") as f:
                        line_count = sum(1 for _ in f)
                    encoding = "utf-8"
                except Exception:
                    pass

            return FileInfo(
                path=str(path),
                name=path.name,
                type=file_type,
                size=size,
                size_human=self._format_size(size),
                created=(
                    datetime.fromtimestamp(stat.st_ctime)
                    if hasattr(stat, "st_ctime")
                    else None
                ),
                modified=datetime.fromtimestamp(stat.st_mtime),
                accessed=(
                    datetime.fromtimestamp(stat.st_atime)
                    if hasattr(stat, "st_atime")
                    else None
                ),
                readable=os.access(path, os.R_OK),
                writable=os.access(path, os.W_OK),
                executable=os.access(path, os.X_OK),
                mime_type=mime_type,
                encoding=encoding,
                line_count=line_count,
                item_count=item_count,
                total_size=size if file_type == FileType.DIRECTORY else None,
            )
        except Exception:
            # Return minimal info on error
            return FileInfo(
                path=str(path),
                name=path.name,
                type=FileType.UNKNOWN,
                size=0,
                size_human="0 B",
                modified=datetime.now(),
            )

    def _get_tree_size(self, path: Path) -> int:
        """Get total size of directory tree."""
        total = 0
        try:
            if path.is_file():
                return path.stat().st_size
            elif path.is_dir():
                for item in path.rglob("*"):
                    if item.is_file():
                        total += item.stat().st_size
        except Exception:
            pass
        return total

    def _format_size(self, size: int) -> str:
        """Format size in human-readable form."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def _match_pattern(self, name: str, pattern: str) -> bool:
        """Match filename against pattern (glob or simple)."""
        from fnmatch import fnmatch

        return fnmatch(name, pattern)

    def _get_error_suggestions(self, error: Exception) -> list[str]:
        """Get helpful suggestions based on error."""
        suggestions = []

        if isinstance(error, FileNotFoundError):
            suggestions.append("Check if the path exists using 'exists' operation")
            suggestions.append("List parent directory to see available files")
        elif isinstance(error, PermissionError):
            suggestions.append("Check file permissions using 'info' operation")
            suggestions.append("Try operation with different permissions or location")
        elif isinstance(error, IsADirectoryError):
            suggestions.append("Use 'list' operation for directories")
            suggestions.append("Specify a file within the directory")
        elif isinstance(error, FileExistsError):
            suggestions.append("Use --force flag to overwrite existing files")
            suggestions.append("Choose a different destination path")

        return suggestions

    async def close(self) -> None:
        """Clean up resources."""
        # Close any open file handles
        for handle in self._open_files.values():
            if hasattr(handle, "close"):
                (
                    await handle.close()
                    if asyncio.iscoroutinefunction(handle.close)
                    else handle.close()
                )
        self._open_files.clear()
