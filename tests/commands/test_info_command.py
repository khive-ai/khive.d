"""
Tests for the info command (khive.commands.info).

This module tests the CLI interface for the info service including
argument parsing, service integration, and output formatting.
"""


from unittest.mock import Mock, patch, AsyncMock
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

    @patch("khive.services.info.khive_info.InfoServiceGroup")
    @patch("sys.argv", ["khive info", "test query"])
    def test_basic_query_execution(self, mock_service_class):
        """Test basic query execution."""
        # Setup mock service
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # Mock successful response
        mock_response = Mock()
        mock_response.success = True
        mock_response.summary = "Mock search result"
        mock_response.synthesis = None
        mock_response.insights = []
        mock_response.suggestions = []
        mock_service.handle_request.return_value = mock_response

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cli_entry()

        # Verify service was called
        mock_service.handle_request.assert_called_once()
        
        # Verify the request had the correct query
        call_args = mock_service.handle_request.call_args[0][0]
        assert call_args.query == "test query"

        # Verify output was printed
        output = mock_stdout.getvalue()
        assert "Mock search result" in output

    @patch("khive.services.info.khive_info.InfoServiceGroup")
    @patch("sys.argv", ["khive info", "multi word query"])
    def test_multi_word_query(self, mock_service_class):
        """Test handling of multi-word queries."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # Mock successful response
        mock_response = Mock()
        mock_response.success = True
        mock_response.summary = "Result for multi word query"
        mock_response.synthesis = None
        mock_response.insights = []
        mock_response.suggestions = []
        mock_service.handle_request.return_value = mock_response

        with patch("sys.stdout", new_callable=StringIO):
            cli_entry()

        # Should handle multi-word query as single argument
        call_args = mock_service.handle_request.call_args[0][0]
        assert call_args.query == "multi word query"

    @patch("sys.argv", ["khive info"])
    @patch("sys.stderr", new_callable=StringIO)
    @patch("sys.exit")
    def test_missing_query_error(self, mock_exit, mock_stderr):
        """Test error handling when no query is provided."""
        cli_entry()

        # Should exit with error (argparse exits with code 2 for missing required args)
        assert mock_exit.call_count >= 1
        # Check that at least one exit was with error code
        exit_calls = [call.args[0] for call in mock_exit.call_args_list if call.args]
        assert any(code != 0 for code in exit_calls)

        # Should print error message
        error_output = mock_stderr.getvalue()
        assert len(error_output) > 0

    @patch("khive.services.info.khive_info.InfoServiceGroup")
    @patch("sys.argv", ["khive info", "test query", "--context", "test context"])
    def test_context_option(self, mock_service_class):
        """Test --context flag functionality."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # Mock successful response
        mock_response = Mock()
        mock_response.success = True
        mock_response.summary = "Contextual search result"
        mock_response.synthesis = None
        mock_response.insights = []
        mock_response.suggestions = []
        mock_service.handle_request.return_value = mock_response

        with patch("sys.stdout", new_callable=StringIO):
            cli_entry()

        # Verify service was called with context
        call_args = mock_service.handle_request.call_args[0][0]
        assert call_args.query == "test query"
        assert call_args.context == "test context"

    @patch("khive.services.info.khive_info.InfoServiceGroup")
    @patch("sys.argv", ["khive info", "error query"])
    @patch("sys.stderr", new_callable=StringIO)
    def test_service_error_handling(self, mock_stderr, mock_service_class):
        """Test handling of service errors."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.handle_request.side_effect = Exception("Service error")

        with pytest.raises(SystemExit):
            cli_entry()

    @patch("khive.services.info.khive_info.InfoServiceGroup")
    @patch("sys.argv", ["khive info", "test", "--mode", "quick"])
    def test_mode_option(self, mock_service_class):
        """Test mode option."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # Mock successful response
        mock_response = Mock()
        mock_response.success = True
        mock_response.summary = "Quick mode result"
        mock_response.synthesis = None
        mock_response.insights = []
        mock_response.suggestions = []
        mock_service.handle_request.return_value = mock_response

        with patch("sys.stdout", new_callable=StringIO):
            cli_entry()

        # Verify service was called with mode
        call_args = mock_service.handle_request.call_args[0][0]
        assert call_args.query == "test"
        assert call_args.mode.value == "quick"

    @patch("khive.services.info.khive_info.InfoServiceGroup")
    @patch("sys.argv", ["khive info", "test query", "--time-budget", "30"])
    def test_time_budget_option(self, mock_service_class):
        """Test time budget option."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # Mock successful response
        mock_response = Mock()
        mock_response.success = True
        mock_response.summary = "Time-budgeted result"
        mock_response.synthesis = None
        mock_response.insights = []
        mock_response.suggestions = []
        mock_service.handle_request.return_value = mock_response

        with patch("sys.stdout", new_callable=StringIO):
            cli_entry()

        # Verify service was called with time budget
        call_args = mock_service.handle_request.call_args[0][0]
        assert call_args.query == "test query"
        assert call_args.time_budget_seconds == 30.0


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
    """Fixture providing a mock InfoServiceGroup."""
    with patch("khive.services.info.khive_info.InfoServiceGroup") as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        # Default successful response
        mock_response = Mock()
        mock_response.success = True
        mock_response.summary = "Mock response"
        mock_response.synthesis = None
        mock_response.insights = []
        mock_response.suggestions = []
        mock_service.handle_request.return_value = mock_response
        
        yield mock_service


@pytest.fixture
def capture_output():
    """Fixture to capture stdout and stderr."""
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            yield mock_stdout, mock_stderr
