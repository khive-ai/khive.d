"""
Comprehensive tests for DevService.

Tests the development service functionality including mode detection,
project setup, formatting, testing, and diagnostic analysis.
"""

import pytest
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from khive.services.dev.dev_service import DevServiceGroup
from khive.services.dev.parts import (
    DevRequest,
    DevResponse,
    DevMode,
    DevInsight,
    DevIssue,
    IssueType,
    IssueSeverity,
    StackType,
    TestResult,
    ProjectHealth,
)
from khive.cli.khive_init import InitCommand
from khive.cli.khive_fmt import FormatCommand
from khive.cli.khive_ci import CICommand


class TestDevServiceGroup:
    """Test the DevServiceGroup class."""

    @pytest.fixture
    def dev_service(self):
        """Create a DevServiceGroup instance for testing."""
        return DevServiceGroup()

    @pytest.fixture
    def sample_project_root(self, tmp_path):
        """Create a sample project root directory."""
        project_root = tmp_path / "test_project"
        project_root.mkdir()
        return project_root

    @pytest.fixture
    def python_project_root(self, tmp_path):
        """Create a Python project root directory with pyproject.toml."""
        project_root = tmp_path / "python_project"
        project_root.mkdir()
        
        # Create pyproject.toml
        pyproject = project_root / "pyproject.toml"
        pyproject.write_text("""
[tool.poetry]
name = "test-project"
version = "0.1.0"
description = "Test project"
""")
        
        # Create tests directory
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        
        return project_root

    async def test_initialization(self, dev_service):
        """Test DevServiceGroup initialization."""
        assert dev_service._init_cmd is None
        assert dev_service._fmt_cmd is None
        assert dev_service._ci_cmd is None
        assert dev_service._project_cache == {}

    async def test_handle_request_string_input(self, dev_service, sample_project_root):
        """Test handling request with string input."""
        request_str = '{"intent": "setup project", "project_root": "' + str(sample_project_root) + '"}'
        
        with patch.object(dev_service, '_detect_mode', return_value=DevMode.SETUP), \
             patch.object(dev_service, '_handle_setup') as mock_handle_setup:
            
            mock_response = DevResponse(
                success=True,
                summary="Project setup complete",
                mode_used=DevMode.SETUP
            )
            mock_handle_setup.return_value = mock_response
            
            response = await dev_service.handle_request(request_str)
            
            assert response == mock_response
            mock_handle_setup.assert_called_once()

    async def test_mode_detection_setup_patterns(self, dev_service, sample_project_root):
        """Test mode detection for setup patterns."""
        test_cases = [
            "set up the project",
            "init new project", 
            "create a new project",
            "bootstrap this",
            "scaffold the app",
            "start fresh",
        ]
        
        for intent in test_cases:
            mode = await dev_service._detect_mode(intent, sample_project_root)
            assert mode == DevMode.SETUP

    async def test_mode_detection_quick_fix_patterns(self, dev_service, python_project_root):
        """Test mode detection for quick fix patterns."""
        test_cases = [
            "fix the formatting",
            "format the code", 
            "lint everything",
            "clean up code style",
            "run prettier",
            "apply black formatting",
        ]
        
        for intent in test_cases:
            mode = await dev_service._detect_mode(intent, python_project_root)
            assert mode == DevMode.QUICK_FIX

    async def test_stack_detection(self, dev_service, python_project_root, tmp_path):
        """Test project stack detection."""
        # Python project
        stacks = dev_service._detect_project_stacks(python_project_root)
        assert "python" in stacks
        
        # Node project
        node_project = tmp_path / "node_project"
        node_project.mkdir()
        package_json = node_project / "package.json"
        package_json.write_text('{"name": "test"}')
        
        stacks = dev_service._detect_project_stacks(node_project)
        assert "node" in stacks

    @patch('khive.services.dev.dev_service.InitCommand')
    async def test_handle_setup_success(self, mock_init_class, dev_service, python_project_root):
        """Test successful project setup."""
        # Setup mocks
        mock_init = MagicMock()
        mock_init_class.return_value = mock_init
        
        mock_parser = MagicMock()
        mock_init.parser = mock_parser
        mock_parsed_args = MagicMock()
        mock_parser.parse_args.return_value = mock_parsed_args
        
        mock_config = MagicMock()
        mock_init._create_config.return_value = mock_config
        
        mock_result = MagicMock()
        mock_result.status = "success"
        mock_result.data = {
            "steps": [
                {"name": "Install dependencies", "status": "OK", "message": "Dependencies installed"},
                {"name": "Setup hooks", "status": "SKIPPED", "message": "Already configured"},
            ]
        }
        mock_init._execute.return_value = mock_result
        
        request = DevRequest(
            intent="setup project",
            stack=StackType.PYTHON,
            project_root=str(python_project_root)
        )
        
        response = await dev_service._handle_setup(request, python_project_root)
        
        assert response.success is True
        assert "successfully initialized" in response.summary
        assert response.mode_used == DevMode.SETUP
        assert len(response.actions_taken) > 0
        assert len(response.insights) > 0

    @patch('khive.services.dev.dev_service.FormatCommand')
    async def test_handle_quick_fix_with_issues(self, mock_fmt_class, dev_service, python_project_root):
        """Test quick fix when formatting issues are found."""
        # Setup mocks
        mock_fmt = MagicMock()
        mock_fmt_class.return_value = mock_fmt
        
        mock_parser = MagicMock()
        mock_fmt.parser = mock_parser
        mock_parsed_args = MagicMock()
        mock_parser.parse_args.return_value = mock_parsed_args
        
        mock_config = MagicMock()
        mock_fmt._create_config.return_value = mock_config
        
        # Mock check result with issues
        mock_check_result = MagicMock()
        mock_check_result.status = "check_failed"
        mock_check_result.data = {
            "stacks_processed": [
                {
                    "stack_name": "python",
                    "status": "check_failed",
                    "message": "Formatting issues found"
                }
            ]
        }
        
        # Mock fix result
        mock_fix_result = MagicMock()
        mock_fix_result.status = "success"
        mock_fix_result.data = {
            "stacks_processed": [
                {
                    "stack_name": "python", 
                    "status": "success",
                    "files_processed": 5
                }
            ]
        }
        
        mock_fmt._execute.side_effect = [mock_check_result, mock_fix_result]
        
        request = DevRequest(
            intent="fix formatting",
            fix_issues=True,
            project_root=str(python_project_root)
        )
        
        response = await dev_service._handle_quick_fix(request, python_project_root)
        
        assert response.success is True
        assert response.mode_used == DevMode.QUICK_FIX
        assert len(response.issues_found) > 0
        assert response.issues_fixed > 0

    async def test_project_health_assessment(self, dev_service):
        """Test project health assessment calculation."""
        # Create response with various issues and test results
        response = DevResponse(
            success=True,
            mode_used=DevMode.FULL_CHECK,
            issues_found=[
                DevIssue(type=IssueType.FORMATTING, severity=IssueSeverity.MEDIUM),
                DevIssue(type=IssueType.TEST_FAILURE, severity=IssueSeverity.HIGH),
                DevIssue(type=IssueType.CONFIGURATION, severity=IssueSeverity.CRITICAL),
            ],
            test_results=[
                TestResult(
                    stack=StackType.PYTHON,
                    total_tests=100,
                    passed=90,
                    failed=10,
                    coverage=85.0
                )
            ]
        )
        
        health = dev_service._assess_project_health(response)
        
        assert isinstance(health, ProjectHealth)
        assert 0 <= health.score <= 100
        assert health.status in ["healthy", "needs_attention", "unhealthy"]
        assert isinstance(health.strengths, list)
        assert isinstance(health.concerns, list)
        assert isinstance(health.next_steps, list)

    async def test_issue_pattern_analysis(self, dev_service):
        """Test issue pattern analysis."""
        issues = [
            DevIssue(type=IssueType.FORMATTING, severity=IssueSeverity.MEDIUM, summary="Format issue 1"),
            DevIssue(type=IssueType.FORMATTING, severity=IssueSeverity.MEDIUM, summary="Format issue 2"),
            DevIssue(type=IssueType.FORMATTING, severity=IssueSeverity.MEDIUM, summary="Format issue 3"),
            DevIssue(type=IssueType.FORMATTING, severity=IssueSeverity.MEDIUM, summary="Format issue 4"),
            DevIssue(type=IssueType.FORMATTING, severity=IssueSeverity.MEDIUM, summary="Format issue 5"),
            DevIssue(type=IssueType.FORMATTING, severity=IssueSeverity.MEDIUM, summary="Format issue 6"),
            DevIssue(type=IssueType.TEST_FAILURE, severity=IssueSeverity.HIGH, summary="Test failure"),
        ]
        
        patterns = dev_service._analyze_issue_patterns(issues)
        
        assert isinstance(patterns, dict)
        assert "inconsistent_formatting" in patterns
        assert "test_failures" in patterns

    async def test_summary_generation(self, dev_service):
        """Test various summary generation methods."""
        # Test fix summary
        issues = [
            DevIssue(type=IssueType.FORMATTING, severity=IssueSeverity.MEDIUM),
            DevIssue(type=IssueType.FORMATTING, severity=IssueSeverity.MEDIUM),
        ]
        
        summary = dev_service._generate_fix_summary(issues, 2)
        assert "Fixed all 2 code quality issues" in summary
        
        summary = dev_service._generate_fix_summary([], 0)
        assert "no issues found" in summary