"""Comprehensive validation tests for Session Service models.

This module provides systematic validation testing for:
- SessionRequest model validation and action types
- SessionResponse model validation and response consistency
- Cross-model session workflow validation
- Session lifecycle validation patterns
"""

from typing import Any

import pytest
from pydantic import ValidationError

from khive.services.session.parts import SessionRequest, SessionResponse
from tests.validation.pydantic_validators import BaseValidationPattern

# ============================================================================
# SessionRequest Model Validation
# ============================================================================


class SessionRequestValidator(BaseValidationPattern):
    """Validation patterns for SessionRequest model."""

    VALID_ACTIONS = ["init", "end", "status", "resume", "continue"]

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid SessionRequest data."""
        data = {
            "action": "init",
            "issue": 123,
            "resume": False,
            "depth": 7,
            "continue_session": False,
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        # Only action is required
        minimal_request = {"action": "init"}
        cls.assert_valid_model(SessionRequest, minimal_request)

        # Missing action should fail
        cls.assert_invalid_model(SessionRequest, {}, "action")

    @classmethod
    def test_field_defaults(cls):
        """Test field default values."""
        minimal_request = SessionRequest(action="init")

        assert minimal_request.action == "init"
        assert minimal_request.issue is None
        assert minimal_request.resume is False
        assert minimal_request.depth == 7
        assert minimal_request.continue_session is False

    @classmethod
    def test_action_validation(cls):
        """Test action field validation."""
        # Valid actions
        for action in cls.VALID_ACTIONS:
            data = cls.create_valid_data(action=action)
            cls.assert_valid_model(SessionRequest, data)

        # Empty action should be invalid
        cls.assert_invalid_model(
            SessionRequest, cls.create_valid_data(action=""), "action"
        )

        # Action validation is mostly at service level, but basic string rules apply
        valid_actions_extended = [
            "init",
            "end",
            "status",
            "resume",
            "continue",
            "custom_action",  # Custom actions might be valid
        ]

        for action in valid_actions_extended:
            data = cls.create_valid_data(action=action)
            cls.assert_valid_model(SessionRequest, data)

    @classmethod
    def test_issue_validation(cls):
        """Test issue field validation."""
        # Valid issue numbers
        valid_issues = [None, 1, 123, 9999, 100000]

        for issue in valid_issues:
            data = cls.create_valid_data(issue=issue)
            cls.assert_valid_model(SessionRequest, data)

        # Invalid issue numbers
        invalid_issues = [0, -1, -123]

        for issue in invalid_issues:
            data = cls.create_valid_data(issue=issue)
            cls.assert_invalid_model(SessionRequest, data, "issue")

    @classmethod
    def test_boolean_fields(cls):
        """Test boolean field validation."""
        boolean_fields = ["resume", "continue_session"]

        for field in boolean_fields:
            # Valid boolean values
            for value in [True, False]:
                data = cls.create_valid_data(**{field: value})
                cls.assert_valid_model(SessionRequest, data)

    @classmethod
    def test_depth_validation(cls):
        """Test depth field validation."""
        # Valid depth values
        valid_depths = [1, 5, 7, 10, 20, 100]

        for depth in valid_depths:
            data = cls.create_valid_data(depth=depth)
            cls.assert_valid_model(SessionRequest, data)

        # Invalid depth values (negative or zero)
        invalid_depths = [0, -1, -10]

        for depth in invalid_depths:
            data = cls.create_valid_data(depth=depth)
            cls.assert_invalid_model(SessionRequest, data, "depth")

    @classmethod
    def test_extra_fields_forbidden(cls):
        """Test that extra fields are forbidden."""
        # SessionRequest has extra="forbid" configuration
        data_with_extra = cls.create_valid_data(extra_field="should_be_rejected")

        cls.assert_invalid_model(SessionRequest, data_with_extra)

    @classmethod
    def test_common_request_patterns(cls):
        """Test common session request patterns."""
        # Init request with issue
        init_request = {"action": "init", "issue": 456, "depth": 10}
        cls.assert_valid_model(SessionRequest, init_request)

        # Resume request
        resume_request = {"action": "resume", "resume": True, "depth": 7}
        cls.assert_valid_model(SessionRequest, resume_request)

        # Continue session request
        continue_request = {"action": "continue", "continue_session": True}
        cls.assert_valid_model(SessionRequest, continue_request)

        # Status request (minimal)
        status_request = {"action": "status"}
        cls.assert_valid_model(SessionRequest, status_request)

        # End request with issue
        end_request = {"action": "end", "issue": 789}
        cls.assert_valid_model(SessionRequest, end_request)


# ============================================================================
# SessionResponse Model Validation
# ============================================================================


class SessionResponseValidator(BaseValidationPattern):
    """Validation patterns for SessionResponse model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid SessionResponse data."""
        data = {
            "success": True,
            "summary": "Session initialized successfully",
            "session_output": "Session init output here...",
            "pending_tasks": [
                {"task_id": "1", "description": "Test task", "status": "pending"}
            ],
            "git_status": {"branch": "main", "modified_files": 3, "untracked_files": 1},
            "unprocessed_summaries": 2,
            "error": None,
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        required_fields = ["success", "summary"]

        for field in required_fields:
            incomplete_data = cls.create_valid_data()
            del incomplete_data[field]
            cls.assert_invalid_model(SessionResponse, incomplete_data, field)

    @classmethod
    def test_field_defaults(cls):
        """Test field default values."""
        minimal_response = SessionResponse(success=True, summary="Test summary")

        assert minimal_response.success is True
        assert minimal_response.summary == "Test summary"
        assert minimal_response.session_output is None
        assert minimal_response.pending_tasks == []
        assert minimal_response.git_status is None
        assert minimal_response.unprocessed_summaries == 0
        assert minimal_response.error is None

    @classmethod
    def test_success_field_validation(cls):
        """Test success field validation."""
        # Valid boolean values
        for success in [True, False]:
            data = cls.create_valid_data(success=success)
            cls.assert_valid_model(SessionResponse, data)

    @classmethod
    def test_summary_validation(cls):
        """Test summary field validation."""
        # Valid summaries
        valid_summaries = [
            "Short summary",
            "A longer summary with more details about the session operation",
            "Summary with special characters: @#$%^&*()",
            "Multi-line\nsummary\nwith\nbreaks",
        ]

        for summary in valid_summaries:
            data = cls.create_valid_data(summary=summary)
            cls.assert_valid_model(SessionResponse, data)

        # Empty summary should be invalid
        cls.assert_invalid_model(
            SessionResponse, cls.create_valid_data(summary=""), "summary"
        )

    @classmethod
    def test_session_output_validation(cls):
        """Test session_output field validation."""
        # Valid session outputs (including None)
        valid_outputs = [
            None,
            "",
            "Simple output",
            "Multi-line\noutput\nwith\nbreaks",
            "Very long output " * 100,
            "Output with special chars: <>{}[]()!@#$%^&*",
        ]

        for output in valid_outputs:
            data = cls.create_valid_data(session_output=output)
            cls.assert_valid_model(SessionResponse, data)

    @classmethod
    def test_pending_tasks_validation(cls):
        """Test pending_tasks field validation."""
        # Valid task lists
        valid_task_lists = [
            [],
            [{"id": "1", "name": "Task 1"}],
            [
                {"task_id": "1", "description": "First task"},
                {"task_id": "2", "description": "Second task", "priority": "high"},
            ],
            [{"complex": {"nested": "structure"}, "list": [1, 2, 3]}],
        ]

        for tasks in valid_task_lists:
            data = cls.create_valid_data(pending_tasks=tasks)
            cls.assert_valid_model(SessionResponse, data)

    @classmethod
    def test_git_status_validation(cls):
        """Test git_status field validation."""
        # Valid git status formats
        valid_git_statuses = [
            None,
            {},
            {"branch": "main"},
            {
                "branch": "main",
                "modified_files": 3,
                "untracked_files": 1,
                "ahead": 0,
                "behind": 0,
            },
            {
                "current_branch": "feature/new-feature",
                "status": "clean",
                "commits": {"ahead": 2, "behind": 0},
            },
        ]

        for git_status in valid_git_statuses:
            data = cls.create_valid_data(git_status=git_status)
            cls.assert_valid_model(SessionResponse, data)

    @classmethod
    def test_unprocessed_summaries_validation(cls):
        """Test unprocessed_summaries field validation."""
        # Valid counts
        valid_counts = [0, 1, 5, 10, 100]

        for count in valid_counts:
            data = cls.create_valid_data(unprocessed_summaries=count)
            cls.assert_valid_model(SessionResponse, data)

        # Invalid counts (negative)
        invalid_counts = [-1, -10]

        for count in invalid_counts:
            data = cls.create_valid_data(unprocessed_summaries=count)
            cls.assert_invalid_model(SessionResponse, data, "unprocessed_summaries")

    @classmethod
    def test_error_field_validation(cls):
        """Test error field validation."""
        # Valid error values (including None)
        valid_errors = [
            None,
            "",
            "Simple error message",
            "Detailed error message with context and stack trace information",
            "Error: Something went wrong\nStack trace follows...",
        ]

        for error in valid_errors:
            data = cls.create_valid_data(error=error)
            cls.assert_valid_model(SessionResponse, data)

    @classmethod
    def test_extra_fields_allowed(cls):
        """Test that extra fields are allowed."""
        # SessionResponse has extra="allow" configuration
        data_with_extra = cls.create_valid_data(
            extra_field="should_be_allowed", custom_metadata={"key": "value"}
        )

        response = cls.assert_valid_model(SessionResponse, data_with_extra)

        # Extra fields should be present
        assert hasattr(response, "extra_field")
        assert response.extra_field == "should_be_allowed"
        assert hasattr(response, "custom_metadata")

    @classmethod
    def test_common_response_patterns(cls):
        """Test common session response patterns."""
        # Successful init response
        success_init = {
            "success": True,
            "summary": "Session initialized successfully",
            "session_output": "Created workspace, loaded context",
            "git_status": {"branch": "main", "clean": True},
        }
        cls.assert_valid_model(SessionResponse, success_init)

        # Failed operation response
        failed_response = {
            "success": False,
            "summary": "Session operation failed",
            "error": "Unable to initialize workspace: Permission denied",
        }
        cls.assert_valid_model(SessionResponse, failed_response)

        # Status response with tasks
        status_response = {
            "success": True,
            "summary": "Session status retrieved",
            "pending_tasks": [
                {"id": "task1", "status": "in_progress"},
                {"id": "task2", "status": "pending"},
            ],
            "unprocessed_summaries": 3,
        }
        cls.assert_valid_model(SessionResponse, status_response)

        # End session response
        end_response = {
            "success": True,
            "summary": "Session ended successfully",
            "git_status": {"branch": "main", "modified": 2, "staged": 0},
        }
        cls.assert_valid_model(SessionResponse, end_response)


# ============================================================================
# Cross-Model Session Validation Patterns
# ============================================================================


class SessionServiceCrossValidator:
    """Cross-model validation patterns for Session Service."""

    @staticmethod
    def validate_request_response_consistency(
        request: SessionRequest, response: SessionResponse
    ) -> list[str]:
        """Validate consistency between SessionRequest and SessionResponse."""
        issues = []

        # Success responses shouldn't have errors
        if response.success and response.error:
            issues.append("Successful response contains error message")

        # Failed responses should have errors (recommended)
        if not response.success and not response.error:
            issues.append("Failed response missing error message")

        # Response should be relevant to request action
        action = request.action.lower()
        summary = response.summary.lower()

        # Check for action-specific response patterns
        if action == "init":
            if response.success and "init" not in summary:
                issues.append("Init request should mention initialization in summary")

        elif action == "end":
            if response.success and "end" not in summary:
                issues.append("End request should mention ending in summary")

        elif action == "status":
            if response.success and "status" not in summary:
                issues.append("Status request should mention status in summary")

        # Resume requests should handle resume flag
        if request.resume and response.success:
            if "resume" not in summary and "restored" not in summary:
                issues.append("Resume request should indicate resumption in summary")

        # Issue-based requests
        if request.issue is not None:
            # Response might include issue information (not required but common)
            pass  # Issue handling is service-level concern

        return issues

    @staticmethod
    def validate_session_lifecycle_consistency(
        requests: list[SessionRequest], responses: list[SessionResponse]
    ) -> list[str]:
        """Validate session lifecycle consistency."""
        issues = []

        if len(requests) != len(responses):
            issues.append(
                f"Request count ({len(requests)}) doesn't match "
                f"response count ({len(responses)})"
            )
            return issues

        # Check lifecycle patterns
        actions = [req.action for req in requests]

        # Should start with init or resume
        if actions and actions[0] not in ["init", "resume"]:
            issues.append(
                f"Session lifecycle should start with 'init' or 'resume', "
                f"but started with '{actions[0]}'"
            )

        # Should not have multiple init actions
        init_count = actions.count("init")
        if init_count > 1:
            issues.append(f"Multiple init actions found: {init_count}")

        # End should be last if present
        if "end" in actions and actions[-1] != "end":
            issues.append("End action should be last in session lifecycle")

        # Responses should generally match success patterns
        failed_responses = [i for i, resp in enumerate(responses) if not resp.success]

        # If there are failures, later operations might be affected
        if failed_responses:
            first_failure = failed_responses[0]
            # Subsequent operations after failure might also fail
            # This is business logic, but we can validate patterns
            pass

        return issues

    @staticmethod
    def validate_session_state_consistency(response: SessionResponse) -> list[str]:
        """Validate internal consistency of session state."""
        issues = []

        # Pending tasks and unprocessed summaries relationship
        if response.pending_tasks and response.unprocessed_summaries == 0:
            # This might be valid, but could indicate inconsistency
            if len(response.pending_tasks) > 5:  # Arbitrary threshold
                issues.append("Many pending tasks but no unprocessed summaries")

        # Git status consistency
        if response.git_status:
            git_status = response.git_status

            # Check for reasonable git status structure
            if isinstance(git_status, dict):
                # Common git status fields
                if "modified_files" in git_status and "untracked_files" in git_status:
                    modified = git_status.get("modified_files", 0)
                    untracked = git_status.get("untracked_files", 0)

                    if modified < 0 or untracked < 0:
                        issues.append("Git status contains negative file counts")

        # Session output consistency
        if response.session_output == "" and response.success:
            # Empty output might be valid, but could indicate issues
            pass

        return issues


# ============================================================================
# Comprehensive Test Suite
# ============================================================================


class TestSessionValidation:
    """Test class to run all Session Service validation tests."""

    def test_session_request_validation(self):
        """Test SessionRequest model validation."""
        SessionRequestValidator.test_required_fields()
        SessionRequestValidator.test_field_defaults()
        SessionRequestValidator.test_action_validation()
        SessionRequestValidator.test_issue_validation()
        SessionRequestValidator.test_boolean_fields()
        SessionRequestValidator.test_depth_validation()
        SessionRequestValidator.test_extra_fields_forbidden()
        SessionRequestValidator.test_common_request_patterns()

    def test_session_response_validation(self):
        """Test SessionResponse model validation."""
        SessionResponseValidator.test_required_fields()
        SessionResponseValidator.test_field_defaults()
        SessionResponseValidator.test_success_field_validation()
        SessionResponseValidator.test_summary_validation()
        SessionResponseValidator.test_session_output_validation()
        SessionResponseValidator.test_pending_tasks_validation()
        SessionResponseValidator.test_git_status_validation()
        SessionResponseValidator.test_unprocessed_summaries_validation()
        SessionResponseValidator.test_error_field_validation()
        SessionResponseValidator.test_extra_fields_allowed()
        SessionResponseValidator.test_common_response_patterns()

    def test_cross_model_validation(self):
        """Test cross-model validation patterns."""
        # Create test request-response pairs
        init_request = SessionRequest(action="init", issue=123, depth=7)
        init_response = SessionResponse(
            success=True, summary="Session initialized successfully for issue #123"
        )

        failed_request = SessionRequest(action="init")
        failed_response = SessionResponse(
            success=False,
            summary="Session initialization failed",
            error="Workspace permission denied",
        )

        # Test request-response consistency
        init_issues = (
            SessionServiceCrossValidator.validate_request_response_consistency(
                init_request, init_response
            )
        )

        failed_issues = (
            SessionServiceCrossValidator.validate_request_response_consistency(
                failed_request, failed_response
            )
        )

        # Test lifecycle consistency
        requests = [init_request]
        responses = [init_response]

        lifecycle_issues = (
            SessionServiceCrossValidator.validate_session_lifecycle_consistency(
                requests, responses
            )
        )

        # Test state consistency
        state_issues = SessionServiceCrossValidator.validate_session_state_consistency(
            init_response
        )

        # Should have no issues for valid models
        assert len(init_issues) == 0
        assert len(failed_issues) == 0
        assert len(lifecycle_issues) == 0
        assert len(state_issues) == 0

    def test_session_workflow_validation(self):
        """Test complete session workflow validation."""
        # Create a complete session workflow
        requests = [
            SessionRequest(action="init", issue=456),
            SessionRequest(action="status"),
            SessionRequest(action="end", issue=456),
        ]

        responses = [
            SessionResponse(
                success=True,
                summary="Session initialized for issue #456",
                session_output="Workspace created successfully",
            ),
            SessionResponse(
                success=True,
                summary="Session status retrieved",
                pending_tasks=[{"task": "test", "status": "pending"}],
                unprocessed_summaries=1,
            ),
            SessionResponse(
                success=True,
                summary="Session ended successfully",
                git_status={"branch": "main", "clean": True},
            ),
        ]

        # Validate entire workflow
        workflow_issues = (
            SessionServiceCrossValidator.validate_session_lifecycle_consistency(
                requests, responses
            )
        )

        # Each request-response pair should be consistent
        for req, resp in zip(requests, responses):
            pair_issues = (
                SessionServiceCrossValidator.validate_request_response_consistency(
                    req, resp
                )
            )
            assert len(pair_issues) == 0

        assert len(workflow_issues) == 0


if __name__ == "__main__":
    # Manual test runner
    test_suite = TestSessionValidation()

    try:
        test_suite.test_session_request_validation()
        test_suite.test_session_response_validation()
        test_suite.test_cross_model_validation()
        test_suite.test_session_workflow_validation()

        print("✅ All Session Service validation tests passed!")

    except Exception as e:
        print(f"❌ Session validation test failed: {e}")
        raise
