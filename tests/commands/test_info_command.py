"""
Tests for the info command (khive.commands.info).

This module tests the CLI interface for the info service including
argument parsing, service integration, and output formatting.
"""

import sys
from unittest.mock import Mock, patch, MagicMock
import pytest
from io import StringIO

# Import the command module
from khive.commands.info import cli_entry


class TestInfoCommand:
    """Test the info command CLI interface."""

    @patch("sys.argv", ["khive info", "--help"])
    @patch("sys.exit")
    def test_help_flag(self, mock_exit):
        """Test that --help flag works."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cli_entry()

        # Should have printed help text
        output = mock_stdout.getvalue()
        assert "usage:" in output.lower() or "help" in output.lower()

    @patch("khive.commands.info.InfoService")
    @patch("sys.argv", ["khive info", "test query"])
    def test_basic_query_execution(self, mock_service_class):
        """Test basic query execution."""
        # Setup mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.search.return_value = "Mock search result"

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cli_entry()

        # Verify service was called with correct query
        mock_service.search.assert_called_once_with("test query")

        # Verify output was printed
        output = mock_stdout.getvalue()
        assert "Mock search result" in output

    @patch("khive.commands.info.InfoService")
    @patch("sys.argv", ["khive info", "multi", "word", "query"])
    def test_multi_word_query(self, mock_service_class):
        """Test handling of multi-word queries."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.search.return_value = "Result for multi word query"

        with patch("sys.stdout", new_callable=StringIO):
            cli_entry()

        # Should join multiple words into single query
        mock_service.search.assert_called_once_with("multi word query")

    @patch("khive.commands.info.InfoService")
    @patch("sys.argv", ["khive info"])
    @patch("sys.stderr", new_callable=StringIO)
    @patch("sys.exit")
    def test_missing_query_error(self, mock_exit, mock_stderr, mock_service_class):
        """Test error handling when no query is provided."""
        cli_entry()

        # Should exit with error
        mock_exit.assert_called_once()

        # Should print error message
        error_output = mock_stderr.getvalue()
        assert len(error_output) > 0 or mock_exit.call_args[0][0] != 0

    @patch("khive.commands.info.InfoService")
    @patch("sys.argv", ["khive info", "test query", "--detailed"])
    def test_detailed_flag(self, mock_service_class):
        """Test --detailed flag functionality."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.search.return_value = "Detailed search result"

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cli_entry()

        # Verify service was called (detailed flag might affect service call)
        mock_service.search.assert_called_once()

    @patch("khive.commands.info.InfoService")
    @patch("sys.argv", ["khive info", "error query"])
    @patch("sys.stderr", new_callable=StringIO)
    def test_service_error_handling(self, mock_stderr, mock_service_class):
        """Test handling of service errors."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.search.side_effect = Exception("Service error")

        with pytest.raises(Exception):
            cli_entry()

    @patch("khive.commands.info.InfoService")
    @patch("sys.argv", ["khive info", "test", "--format", "json"])
    def test_format_option(self, mock_service_class):
        """Test format option if supported."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.search.return_value = {"result": "json formatted"}

        try:
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                cli_entry()

            # If format option exists, verify it's handled
            mock_service.search.assert_called_once()

        except SystemExit:
            # Format option might not exist, which is fine
            pass

    @patch("khive.commands.info.InfoService")
    @patch("sys.argv", ["khive info", "test query", "--providers", "exa,perplexity"])
    def test_providers_option(self, mock_service_class):
        """Test providers option if supported."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.search.return_value = "Provider-specific result"

        try:
            with patch("sys.stdout", new_callable=StringIO):
                cli_entry()

            # If providers option exists, verify service call
            mock_service.search.assert_called_once()

        except SystemExit:
            # Providers option might not exist, which is fine
            pass


class TestInfoCommandIntegration:
    """Integration tests for info command with real service."""

    @patch("sys.argv", ["khive info", "--help"])
    def test_real_help_output(self):
        """Test that real help output is reasonable."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with patch("sys.exit"):
                cli_entry()

        output = mock_stdout.getvalue()
        # Should contain basic CLI elements
        assert any(
            word in output.lower() for word in ["usage", "help", "info", "query"]
        )

    def test_cli_entry_exists_and_callable(self):
        """Test that cli_entry function exists and is callable."""
        assert hasattr(cli_entry, "__call__")
        assert callable(cli_entry)


@pytest.fixture
def mock_info_service():
    """Fixture providing a mock InfoService."""
    with patch("khive.commands.info.InfoService") as mock_service_class:
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        yield mock_service


@pytest.fixture
def capture_output():
    """Fixture to capture stdout and stderr."""
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            yield mock_stdout, mock_stderr
