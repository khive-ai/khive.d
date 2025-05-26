from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class FileOperation(str, Enum):
    """Natural file system operations."""

    # Basic operations
    READ = "read"  # Read file content
    WRITE = "write"  # Write/create file
    APPEND = "append"  # Append to file
    DELETE = "delete"  # Delete file/directory

    # Navigation
    LIST = "list"  # List directory contents
    TREE = "tree"  # Show directory tree
    FIND = "find"  # Find files by pattern

    # File management
    COPY = "copy"  # Copy file/directory
    MOVE = "move"  # Move/rename file/directory
    MKDIR = "mkdir"  # Create directory

    # Metadata
    INFO = "info"  # Get file/directory info
    EXISTS = "exists"  # Check if path exists

    # Advanced
    WATCH = "watch"  # Watch for changes
    COMPRESS = "compress"  # Create archive
    EXTRACT = "extract"  # Extract archive


class FileType(str, Enum):
    """Common file type categories."""

    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    UNKNOWN = "unknown"


class FileInfo(BaseModel):
    """Comprehensive file/directory information."""

    path: str = Field(..., description="Full path to the file/directory")
    name: str = Field(..., description="Filename or directory name")
    type: FileType = Field(..., description="Type of file system entry")
    size: int = Field(..., description="Size in bytes")
    size_human: str = Field(..., description="Human-readable size")

    # Timestamps
    created: datetime | None = Field(None, description="Creation time")
    modified: datetime = Field(..., description="Last modification time")
    accessed: datetime | None = Field(None, description="Last access time")

    # Permissions
    readable: bool = Field(True, description="Can read")
    writable: bool = Field(True, description="Can write")
    executable: bool = Field(False, description="Can execute")

    # Additional metadata
    mime_type: str | None = Field(None, description="MIME type if file")
    encoding: str | None = Field(None, description="Text encoding if applicable")
    line_count: int | None = Field(None, description="Number of lines if text file")

    # For directories
    item_count: int | None = Field(None, description="Number of items in directory")
    total_size: int | None = Field(None, description="Total size of directory contents")


class FileContent(BaseModel):
    """File content with metadata."""

    path: str = Field(..., description="Path to the file")
    content: str | bytes = Field(..., description="File content")
    encoding: str = Field("utf-8", description="Text encoding")
    mime_type: str | None = Field(None, description="Detected MIME type")
    size: int = Field(..., description="Content size in bytes")
    line_count: int | None = Field(None, description="Number of lines if text")
    preview: str | None = Field(None, description="Preview of content if large")


class DirectoryListing(BaseModel):
    """Directory listing with rich information."""

    path: str = Field(..., description="Directory path")
    entries: list[FileInfo] = Field(..., description="Files and subdirectories")
    total_items: int = Field(..., description="Total number of items")
    total_size: int = Field(..., description="Total size in bytes")

    # Filtering results
    pattern: str | None = Field(None, description="Filter pattern applied")
    include_hidden: bool = Field(False, description="Whether hidden files included")
    recursive: bool = Field(False, description="Whether listing is recursive")


class FileOperation(BaseModel):
    """Result of a file operation."""

    operation: str = Field(..., description="Operation performed")
    success: bool = Field(..., description="Whether operation succeeded")

    # Affected paths
    source: str | None = Field(None, description="Source path")
    destination: str | None = Field(None, description="Destination path")

    # Results
    message: str = Field(..., description="Human-readable result message")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Operation-specific details"
    )

    # For multi-file operations
    processed: int = Field(0, description="Number of items processed")
    failed: int = Field(0, description="Number of failures")
    errors: list[str] = Field(default_factory=list, description="Error messages if any")


class FileRequest(BaseModel):
    """Unified file service request."""

    operation: FileOperation = Field(..., description="File operation to perform")
    path: str = Field(..., description="Primary path for the operation")

    # Optional parameters based on operation
    destination: str | None = Field(None, description="Destination path for copy/move")
    content: str | bytes | None = Field(None, description="Content for write/append")
    encoding: str = Field("utf-8", description="Text encoding")

    # Listing options
    pattern: str | None = Field(None, description="Filter pattern (glob or regex)")
    recursive: bool = Field(False, description="Recursive operation")
    include_hidden: bool = Field(False, description="Include hidden files")

    # Advanced options
    force: bool = Field(False, description="Force operation (overwrite, etc)")
    follow_symlinks: bool = Field(True, description="Follow symbolic links")
    preserve_metadata: bool = Field(True, description="Preserve timestamps/permissions")

    # Safety options
    dry_run: bool = Field(False, description="Simulate operation without changes")
    backup: bool = Field(
        False, description="Create backup before destructive operations"
    )

    @field_validator("path")
    def validate_path(cls, v: str) -> str:
        """Basic path validation."""
        if not v or v.strip() == "":
            raise ValueError("Path cannot be empty")
        # Prevent obvious path traversal
        if ".." in Path(v).parts:
            raise ValueError("Path traversal (..) not allowed")
        return v


class FileResponse(BaseModel):
    """Unified file service response."""

    success: bool = Field(..., description="Whether operation succeeded")
    operation: FileOperation = Field(..., description="Operation that was performed")

    # Results based on operation type
    file_info: FileInfo | None = Field(
        None, description="File information (for info/exists)"
    )
    content: FileContent | None = Field(None, description="File content (for read)")
    listing: DirectoryListing | None = Field(
        None, description="Directory listing (for list/tree/find)"
    )
    operation_result: FileOperation | None = Field(
        None, description="Operation details (for write/copy/etc)"
    )

    # Timing
    duration_ms: float = Field(..., description="Operation duration in milliseconds")

    # Errors
    error: str | None = Field(None, description="Error message if failed")
    error_details: dict[str, Any] | None = Field(
        None, description="Detailed error information"
    )

    # Suggestions
    suggestions: list[str] = Field(
        default_factory=list, description="Helpful suggestions"
    )


class WatchEvent(BaseModel):
    """File system watch event."""

    event_type: Literal["created", "modified", "deleted", "moved"] = Field(
        ..., description="Type of change"
    )
    path: str = Field(..., description="Path that changed")
    is_directory: bool = Field(..., description="Whether path is a directory")
    timestamp: datetime = Field(..., description="When the event occurred")
    old_path: str | None = Field(None, description="Previous path (for moves)")


class ArchiveOptions(BaseModel):
    """Options for compress/extract operations."""

    format: Literal["zip", "tar", "tar.gz", "tar.bz2"] = Field(
        "zip", description="Archive format"
    )
    compression_level: int = Field(6, ge=0, le=9, description="Compression level (0-9)")
    include_patterns: list[str] = Field(
        default_factory=list, description="Patterns to include"
    )
    exclude_patterns: list[str] = Field(
        default_factory=list, description="Patterns to exclude"
    )
    preserve_permissions: bool = Field(True, description="Preserve file permissions")
    follow_symlinks: bool = Field(False, description="Follow symbolic links")
