"""Basic performance tests for khive components."""

import time
from pathlib import Path

import pytest


class TestBasicPerformance:
    """Basic performance validation tests."""

    def test_cli_import_performance(self):
        """Test that CLI imports don't take too long."""
        start_time = time.time()
        from khive.cli import khive_cli

        import_time = time.time() - start_time

        # Import should be reasonably fast (under 1 second)
        assert import_time < 1.0, f"CLI import took {import_time:.2f}s, expected < 1.0s"

    @pytest.mark.slow
    def test_file_operations_performance(self, temp_dir):
        """Test basic file operations performance."""
        test_file = temp_dir / "performance_test.txt"
        content = "test content " * 1000  # ~13KB of content

        start_time = time.time()
        test_file.write_text(content)
        read_content = test_file.read_text()
        operation_time = time.time() - start_time

        assert read_content == content
        assert (
            operation_time < 0.1
        ), f"File operations took {operation_time:.3f}s, expected < 0.1s"
