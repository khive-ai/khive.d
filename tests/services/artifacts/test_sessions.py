"""Tests for artifacts session management."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from khive.services.artifacts.exceptions import (SessionNotFound,
                                                 ValidationError)
from khive.services.artifacts.models import Author
from khive.services.artifacts.sessions import SessionManager


class TestSessionManager:
    """Test the SessionManager class."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def session_manager(self, temp_workspace):
        """Create a SessionManager instance."""
        return SessionManager(str(temp_workspace))

    @pytest.fixture
    def test_session_id(self):
        """Return a test session ID."""
        return "test_session_123"

    @pytest.fixture
    def sample_author(self):
        """Create a sample author."""
        return Author(
            author_id="test_user",
            author_role="user",
            timestamp=datetime.now(timezone.utc),
        )

    @pytest.mark.unit
    def test_session_manager_initialization(self, session_manager, temp_workspace):
        """Test that SessionManager initializes correctly."""
        assert session_manager is not None
        assert Path(session_manager.workspace_path) == temp_workspace

    @pytest.mark.unit
    def test_create_session(self, session_manager, test_session_id, sample_author):
        """Test creating a new session."""
        session = session_manager.create_session(test_session_id, sample_author)

        assert session is not None
        assert session.session_id == test_session_id
        assert session.created_by == sample_author
        assert session.created_at is not None

    @pytest.mark.unit
    def test_session_exists(self, session_manager, test_session_id, sample_author):
        """Test checking if a session exists."""
        # Initially should not exist
        assert not session_manager.session_exists(test_session_id)

        # Create session
        session_manager.create_session(test_session_id, sample_author)

        # Now should exist
        assert session_manager.session_exists(test_session_id)

    @pytest.mark.unit
    def test_get_session(self, session_manager, test_session_id, sample_author):
        """Test retrieving a session."""
        # Create session first
        original_session = session_manager.create_session(
            test_session_id, sample_author
        )

        # Retrieve session
        retrieved_session = session_manager.get_session(test_session_id)

        assert retrieved_session.session_id == original_session.session_id
        assert (
            retrieved_session.created_by.author_id
            == original_session.created_by.author_id
        )

    @pytest.mark.unit
    def test_get_nonexistent_session(self, session_manager):
        """Test retrieving a non-existent session raises error."""
        with pytest.raises(SessionNotFound):
            session_manager.get_session("nonexistent_session")

    @pytest.mark.unit
    def test_list_sessions(self, session_manager, sample_author):
        """Test listing all sessions."""
        # Create multiple sessions
        session_ids = ["session_1", "session_2", "session_3"]
        for session_id in session_ids:
            session_manager.create_session(session_id, sample_author)

        # List sessions
        sessions = session_manager.list_sessions()

        assert len(sessions) == len(session_ids)
        retrieved_ids = {session.session_id for session in sessions}
        expected_ids = set(session_ids)
        assert retrieved_ids == expected_ids

    @pytest.mark.unit
    def test_session_directory_creation(
        self, session_manager, test_session_id, sample_author
    ):
        """Test that session directories are created."""
        session_path = Path(session_manager.workspace_path) / test_session_id

        # Directory should not exist initially
        assert not session_path.exists()

        # Create session
        session_manager.create_session(test_session_id, sample_author)

        # Directory should now exist
        assert session_path.exists()
        assert session_path.is_dir()

    @pytest.mark.unit
    def test_session_metadata_persistence(
        self, session_manager, test_session_id, sample_author
    ):
        """Test that session metadata is properly persisted."""
        # Create session with metadata
        session = session_manager.create_session(test_session_id, sample_author)

        # Create new session manager instance (simulates restart)
        new_session_manager = SessionManager(session_manager.workspace_path)

        # Retrieve session metadata
        retrieved_session = new_session_manager.get_session(test_session_id)

        assert retrieved_session.session_id == session.session_id
        assert retrieved_session.created_by.author_id == session.created_by.author_id

    @pytest.mark.unit
    def test_invalid_session_id_validation(self, session_manager, sample_author):
        """Test validation of session IDs."""
        # Test with invalid characters
        invalid_ids = [
            "../malicious_session",
            "session/with/slashes",
            "session\x00with\x00nulls",
            "",  # Empty string
            "a" * 500,  # Too long
        ]

        for invalid_id in invalid_ids:
            with pytest.raises((ValidationError, ValueError)):
                session_manager.create_session(invalid_id, sample_author)

    @pytest.mark.unit
    def test_session_update_last_accessed(
        self, session_manager, test_session_id, sample_author
    ):
        """Test updating session last accessed time."""
        # Create session
        session = session_manager.create_session(test_session_id, sample_author)
        original_accessed = session.last_accessed_at

        # Simulate some delay
        import time

        time.sleep(0.1)

        # Update last accessed
        session_manager.update_session_access(test_session_id)

        # Retrieve updated session
        updated_session = session_manager.get_session(test_session_id)

        assert updated_session.last_accessed_at > original_accessed

    @pytest.mark.integration
    def test_concurrent_session_creation(self, session_manager, sample_author):
        """Test concurrent session creation."""
        import threading

        results = []
        errors = []

        def create_session(session_id):
            try:
                session = session_manager.create_session(
                    f"concurrent_{session_id}", sample_author
                )
                results.append(session.session_id)
            except Exception as e:
                errors.append(e)

        # Create multiple sessions concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_session, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0  # No errors should occur
        assert len(results) == 5  # All sessions should be created
        assert len(set(results)) == 5  # All session IDs should be unique

    @pytest.mark.unit
    def test_session_cleanup(self, session_manager, test_session_id, sample_author):
        """Test session cleanup functionality."""
        # Create session
        session_manager.create_session(test_session_id, sample_author)
        assert session_manager.session_exists(test_session_id)

        # Delete session
        session_manager.delete_session(test_session_id)

        # Verify deletion
        assert not session_manager.session_exists(test_session_id)

    @pytest.mark.performance
    def test_large_number_of_sessions(self, session_manager, sample_author):
        """Test handling of a large number of sessions."""
        # Create many sessions
        num_sessions = 100
        session_ids = [f"bulk_session_{i}" for i in range(num_sessions)]

        for session_id in session_ids:
            session_manager.create_session(session_id, sample_author)

        # Verify all sessions exist
        sessions = session_manager.list_sessions()
        assert len(sessions) == num_sessions

        retrieved_ids = {session.session_id for session in sessions}
        expected_ids = set(session_ids)
        assert retrieved_ids == expected_ids
