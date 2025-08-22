"""Simple CLI testing fixtures."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner():
    """CLI runner for testing Click commands."""
    return CliRunner()


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for CLI command testing."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="mock output", stderr="")
        yield mock_run
