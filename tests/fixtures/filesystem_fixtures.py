"""Simple filesystem testing fixtures."""

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_file(temp_dir: Path) -> Path:
    """Create a temporary file for testing."""
    temp_file = temp_dir / "test_file.txt"
    temp_file.write_text("test content")
    return temp_file


@pytest.fixture
def mock_file_operations():
    """Mock file operations for testing."""
    with (
        patch("pathlib.Path.read_text") as mock_read,
        patch("pathlib.Path.write_text") as mock_write,
        patch("pathlib.Path.exists") as mock_exists,
    ):
        mock_read.return_value = "mock file content"
        mock_write.return_value = None
        mock_exists.return_value = True

        yield {
            "read_text": mock_read,
            "write_text": mock_write,
            "exists": mock_exists,
        }
