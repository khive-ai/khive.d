"""
Comprehensive tests for GitService.

Tests the core git service functionality including intent detection,
workflow handling, and service coordination.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from khive.services.git.git_service import GitService, PatternAnalyzer, QualityAnalyzer, CollaborationOptimizer
from khive.services.git.parts import (
    GitRequest,
    GitResponse,
    GitSession,
    WorkIntent,
    RepositoryUnderstanding,
    CodeInsight,
    FileUnderstanding,
    CollaborationContext,
    Recommendation,
    GitError,
    ImplementationFlow,
    ReleaseFlow,
    CollaborationFlow,
    PatternRecognition,
    QualityAssessment,
    QualityIssue,
)


class TestGitService:
    """Test the GitService class."""

    @pytest.fixture
    def git_service(self):
        """Create a GitService instance for testing."""
        return GitService()

    @pytest.fixture
    def sample_request(self):
        """Create a sample GitRequest for testing."""
        return GitRequest(
            request="save my progress",
            agent_id="test-agent",
            conversation_id="test-conv-123"
        )

    @pytest.fixture
    def sample_session(self):
        """Create a sample GitSession for testing."""
        return GitSession(
            id="test-session",
            agent_id="test-agent",
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
        )

    @pytest.fixture
    def sample_repo_state(self):
        """Create a sample repository state for testing."""
        return RepositoryUnderstanding(
            current_branch="feature/test",
            branch_purpose="Feature development",
            work_phase="implementing",
            files_changed=[
                FileUnderstanding(
                    path=Path("src/test.py"),
                    role="core",
                    change_summary="Added new feature functionality",
                    change_magnitude="significant"
                )
            ],
            code_insights=CodeInsight(
                primary_changes=["Added OAuth authentication"],
                side_effects=["Updated configuration"],
                change_type="feature",
                complexity="moderate",
                risk_level="low",
                affects_public_api=False,
                adds_tests=True,
                updates_docs=False,
                follows_patterns=True,
                introduces_tech_debt=False,
                requires_migration=False,
                breaks_compatibility=False,
            ),
            collaboration=CollaborationContext(),
            can_build=True,
            tests_passing=True,
            lint_clean=True,
            recommended_actions=["commit", "test"],
            potential_issues=[],
        )

    async def test_initialization(self, git_service):
        """Test GitService initialization."""
        assert git_service._sessions == {}
        assert git_service._llm_endpoint is None
        assert git_service._git_ops is not None
        assert git_service._file_analyzer is not None
        assert git_service._code_analyzer is not None
        assert git_service._pr_manager is not None
        assert git_service._commit_generator is not None
        assert git_service._intent_detector is not None
        assert git_service._response_generator is not None

    async def test_session_management(self, git_service):
        """Test session creation and management."""
        # Test session creation
        session1 = git_service._get_or_create_session("agent1", "conv1")
        assert session1.id == "conv1"
        assert session1.agent_id == "agent1"
        assert "conv1" in git_service._sessions

        # Test session retrieval
        session2 = git_service._get_or_create_session("agent1", "conv1")
        assert session1 is session2

        # Test auto-generated conversation ID
        session3 = git_service._get_or_create_session("agent2", None)
        assert session3.id.startswith("git-agent2-")
        assert session3.agent_id == "agent2"

    async def test_session_cleanup(self, git_service):
        """Test cleanup of old sessions."""
        # Create old session
        old_session = GitSession(
            id="old-session",
            agent_id="test-agent",
            started_at=datetime.utcnow() - timedelta(hours=3),
            last_activity=datetime.utcnow() - timedelta(hours=3),
        )
        git_service._sessions["old-session"] = old_session

        # Create recent session
        recent_session = GitSession(
            id="recent-session",
            agent_id="test-agent",
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
        )
        git_service._sessions["recent-session"] = recent_session

        # Trigger cleanup
        git_service._cleanup_old_sessions()

        # Old session should be removed
        assert "old-session" not in git_service._sessions
        assert "recent-session" in git_service._sessions

    @patch('khive.services.git.git_service.GitService._get_repository_state')
    @patch('khive.services.git.git_service.GitService._intent_detector')
    async def test_handle_request_explore(self, mock_intent_detector, mock_get_repo_state, git_service, sample_request, sample_repo_state):
        """Test handling explore requests."""
        # Setup mocks
        mock_intent_detector.detect_intent.return_value = (WorkIntent.EXPLORE, 0.9)
        mock_get_repo_state.return_value = sample_repo_state

        # Mock the _handle_explore method
        with patch.object(git_service, '_handle_explore') as mock_handle_explore:
            expected_response = GitResponse(
                understood_as="Exploring repository state",
                actions_taken=["Analyzed current state"],
                repository_state=sample_repo_state,
                conversation_id="test-conv-123"
            )
            mock_handle_explore.return_value = expected_response

            # Execute
            response = await git_service.handle_request(sample_request)

            # Verify
            assert response == expected_response
            mock_handle_explore.assert_called_once()

    @patch('khive.services.git.git_service.GitService._get_repository_state')
    @patch('khive.services.git.git_service.GitService._intent_detector')
    async def test_handle_request_implement(self, mock_intent_detector, mock_get_repo_state, git_service, sample_request, sample_repo_state):
        """Test handling implement requests."""
        # Setup mocks
        mock_intent_detector.detect_intent.return_value = (WorkIntent.IMPLEMENT, 0.95)
        mock_get_repo_state.return_value = sample_repo_state

        # Mock the _handle_implement method
        with patch.object(git_service, '_handle_implement') as mock_handle_implement:
            expected_response = GitResponse(
                understood_as="Saving implementation progress",
                actions_taken=["Staged files", "Created commit"],
                repository_state=sample_repo_state,
                conversation_id="test-conv-123"
            )
            mock_handle_implement.return_value = expected_response

            # Execute
            response = await git_service.handle_request(sample_request)

            # Verify
            assert response == expected_response
            mock_handle_implement.assert_called_once()

    async def test_handle_request_error(self, git_service, sample_request):
        """Test error handling in handle_request."""
        # Mock intent detector to raise an exception
        with patch.object(git_service, '_intent_detector') as mock_intent_detector:
            mock_intent_detector.detect_intent.side_effect = Exception("Test error")

            # Mock _handle_error
            with patch.object(git_service, '_handle_error') as mock_handle_error:
                expected_response = GitResponse(
                    understood_as="Attempted to save my progress but encountered an error",
                    actions_taken=["Analyzed error"],
                    success=False,
                    conversation_id="test-conv-123",
                    repository_state=sample_repo_state,
                    recommendations=[],
                    follow_up_prompts=["Should I try again?"]
                )
                mock_handle_error.return_value = expected_response

                # Execute
                response = await git_service.handle_request(sample_request)

                # Verify
                assert response == expected_response
                mock_handle_error.assert_called_once()

    async def test_error_analysis(self, git_service):
        """Test error analysis and suggestion generation."""
        test_cases = [
            {
                "error_msg": "permission denied",
                "expected_failure": "File or directory permissions",
                "expected_reason": "Insufficient permissions to access file or directory",
                "expected_retryable": False,
            },
            {
                "error_msg": "not a git repository",
                "expected_failure": "Git repository initialization",
                "expected_reason": "Current directory is not a git repository",
                "expected_retryable": False,
            },
            {
                "error_msg": "remote rejected push",
                "expected_failure": "Remote repository communication",
                "expected_reason": "Remote repository rejected the push (likely due to conflicts)",
                "expected_retryable": False,
            },
            {
                "error_msg": "merge conflict detected",
                "expected_failure": "Merge operation",
                "expected_reason": "Conflicting changes need manual resolution",
                "expected_retryable": False,
            },
            {
                "error_msg": "authentication failed",
                "expected_failure": "Authentication",
                "expected_reason": "Git credentials are invalid or expired",
                "expected_retryable": False,
            },
        ]

        for case in test_cases:
            failure_point = git_service._identify_failure_point(case["error_msg"])
            failure_reason = git_service._explain_failure_reason(case["error_msg"])
            is_retryable = git_service._is_retryable("TestError")

            assert failure_point == case["expected_failure"]
            assert failure_reason == case["expected_reason"]
            assert is_retryable == case["expected_retryable"]

    async def test_fix_suggestions(self, git_service):
        """Test fix suggestion generation."""
        # Test permission error fixes
        fixes = git_service._suggest_fixes("PermissionError", "permission denied")
        assert any("permission" in fix.lower() for fix in fixes)
        assert len(fixes) <= 3

        # Test git repository error fixes
        fixes = git_service._suggest_fixes("GitError", "not a git repository")
        assert any("git init" in fix for fix in fixes)
        assert len(fixes) <= 3

        # Test merge conflict fixes
        fixes = git_service._suggest_fixes("MergeError", "merge conflict")
        assert any("conflict" in fix.lower() for fix in fixes)
        assert len(fixes) <= 3

    async def test_work_phase_determination(self, git_service):
        async def test_work_phase_determination(self, git_service):
            """Test work phase determination logic."""
            # Test with no files - should be exploring
            empty_insight = CodeInsight(
                primary_changes=[],
                side_effects=[],
                change_type="feature",
                complexity="trivial",
                risk_level="safe",
                affects_public_api=False,
                adds_tests=False,
                updates_docs=False,
                follows_patterns=True,
                introduces_tech_debt=False,
                requires_migration=False,
                breaks_compatibility=False,
            )
            phase = git_service._determine_work_phase([], empty_insight)
            assert phase == "exploring"
    
            # Test with mostly test files - should be testing
            test_files = [
                FileUnderstanding(path=Path("test_1.py"), role="test", change_summary="Added tests", change_magnitude="minor"),
                FileUnderstanding(path=Path("test_2.py"), role="test", change_summary="Added tests", change_magnitude="minor"),
                FileUnderstanding(path=Path("src.py"), role="core", change_summary="Updated code", change_magnitude="minor"),
            ]
            phase = git_service._determine_work_phase(test_files, empty_insight)
            assert phase == "testing"
    
            # Test with mostly doc files - should be polishing
            doc_files = [
                FileUnderstanding(path=Path("README.md"), role="docs", change_summary="Updated docs", change_magnitude="minor"),
                FileUnderstanding(path=Path("docs.md"), role="docs", change_summary="Updated docs", change_magnitude="minor"),
                FileUnderstanding(path=Path("src.py"), role="core", change_summary="Updated code", change_magnitude="minor"),
            ]
            phase = git_service._determine_work_phase(doc_files, empty_insight)
            assert phase == "polishing"
    
            # Test with complex code - should be implementing
            code_files = [
                FileUnderstanding(path=Path("src.py"), role="core", change_summary="Complex changes", change_magnitude="major"),
            ]
            complex_insight = CodeInsight(
                primary_changes=["Major refactoring"],
                side_effects=["Updated dependencies"],
                change_type="refactor",
                complexity="complex",
                risk_level="medium",
                affects_public_api=True,
                adds_tests=False,
                updates_docs=False,
                follows_patterns=True,
                introduces_tech_debt=False,
                requires_migration=False,
                breaks_compatibility=False,
            )
            phase = git_service._determine_work_phase(code_files, complex_insight)
            assert phase == "implementing"
    async def test_branch_purpose_inference(self, git_service):
        """Test branch purpose inference."""
        test_cases = [
            ("feature/auth", [], "Feature development"),
            ("fix/bug-123", [], "Bug fix"),
            ("refactor/cleanup", [], "Code refactoring"),
            ("test/coverage", [], "Testing improvements"),
            ("docs/update", [], "Documentation updates"),
            ("main", [], "Main development branch"),
            ("develop", [], "Main development branch"),
            ("custom-branch", [FileUnderstanding(path=Path("test_auth.py"), role="test", change_summary="Added tests", change_magnitude="minor")], "Testing work"),
            ("custom-branch", [FileUnderstanding(path=Path("auth.py"), role="core", change_summary="Updated auth", change_magnitude="minor")], "Authentication feature"),
            ("custom-branch", [FileUnderstanding(path=Path("api.py"), role="core", change_summary="Updated API", change_magnitude="minor")], "API development"),
        ]

        for branch, files, expected in test_cases:
            purpose = git_service._infer_branch_purpose(branch, files)
            assert purpose == expected

    async def test_file_staging_logic(self, git_service, sample_repo_state):
        """Test intelligent file staging logic."""
        test_cases = [
            (Path("test_file.py"), True),  # Test files should be staged
            (Path("README.md"), True),     # Documentation should be staged
            (Path("src/main.py"), True),   # Code files should be staged
            (Path("src/main.js"), True),   # JS files should be staged
            (Path("src/main.ts"), True),   # TS files should be staged
            (Path(".temp_file"), False),   # Hidden files should not be staged
            (Path("backup.bak"), False),   # Backup files should not be staged
            (Path("temp.tmp"), False),     # Temp files should not be staged
        ]

        request = GitRequest(request="test", agent_id="test")
        
        for path, should_stage in test_cases:
            result = git_service._should_auto_stage(path, sample_repo_state, request)
            assert result == should_stage

    async def test_recommendation_generation(self, git_service, sample_repo_state, sample_session):
        """Test recommendation generation for different scenarios."""
        # Test explore recommendations
        recommendations = git_service._build_explore_recommendations(sample_repo_state, sample_session)
        assert isinstance(recommendations, list)
        assert all(isinstance(rec, Recommendation) for rec in recommendations)
        assert len(recommendations) <= 3

        # Test implement recommendations
        commit_result = {"success": True, "sha": "abc123"}
        recommendations = git_service._build_implement_recommendations(
            sample_repo_state, sample_session, commit_result
        )
        assert isinstance(recommendations, list)
        assert len(recommendations) >= 0

        # Test collaborate recommendations
        pr_result = {"success": True, "number": 123, "url": "https://github.com/test/repo/pull/123"}
        recommendations = git_service._build_collaborate_recommendations(
            sample_repo_state, sample_session, pr_result
        )
        assert isinstance(recommendations, list)

    @patch('khive.services.git.git_service.GitService._get_repository_state')
    async def test_close_cleanup(self, mock_get_repo_state, git_service):
        """Test proper cleanup when closing the service."""
        # Mock the git operations executor
        mock_executor = AsyncMock()
        git_service._git_ops._executor = mock_executor
        mock_executor.shutdown = AsyncMock()

        # Call close
        await git_service.close()

        # Verify cleanup was called
        mock_executor.shutdown.assert_called_once()


class TestPatternAnalyzer:
    """Test the PatternAnalyzer class."""

    @pytest.fixture
    def pattern_analyzer(self):
        """Create a PatternAnalyzer instance for testing."""
        return PatternAnalyzer()

    @pytest.fixture
    def sample_knowledge(self):
        """Create sample repository knowledge for testing."""
        return {
            "commits": [
                {"type": "feat", "size": 100},
                {"type": "fix", "size": 50},
                {"type": "refactor", "size": 200},
            ],
            "files": ["src/auth.py", "src/api.py", "tests/test_auth.py"],
            "team": ["alice", "bob", "charlie"],
        }

    async def test_pattern_analysis(self, pattern_analyzer, sample_knowledge):
        """Test pattern analysis functionality."""
        result = await pattern_analyzer.analyze(sample_knowledge)
        
        assert isinstance(result, PatternRecognition)
        assert isinstance(result.common_patterns, list)
        assert isinstance(result.anti_patterns, list)
        assert isinstance(result.typical_pr_size, (int, float))
        assert isinstance(result.typical_review_time, str)
        assert isinstance(result.typical_iteration_count, int)
        assert isinstance(result.expertise_map, dict)
        assert isinstance(result.collaboration_graph, dict)

    async def test_commit_pattern_analysis(self, pattern_analyzer, sample_knowledge):
        """Test commit pattern analysis."""
        patterns = pattern_analyzer._analyze_commit_patterns(sample_knowledge)
        
        assert isinstance(patterns, dict)
        assert "avg_pr_size" in patterns
        assert "common_types" in patterns
        assert "commit_frequency" in patterns

    async def test_code_pattern_analysis(self, pattern_analyzer, sample_knowledge):
        """Test code pattern analysis."""
        patterns = pattern_analyzer._analyze_code_patterns(sample_knowledge)
        
        assert isinstance(patterns, dict)
        assert "common" in patterns
        assert "anti" in patterns
        assert isinstance(patterns["common"], list)
        assert isinstance(patterns["anti"], list)

    async def test_team_pattern_analysis(self, pattern_analyzer, sample_knowledge):
        """Test team collaboration pattern analysis."""
        patterns = pattern_analyzer._analyze_team_patterns(sample_knowledge)
        
        assert isinstance(patterns, dict)
        assert "avg_review_time" in patterns
        assert "avg_iterations" in patterns
        assert "expertise_map" in patterns
        assert "collaboration_graph" in patterns


class TestQualityAnalyzer:
    """Test the QualityAnalyzer class."""

    @pytest.fixture
    def quality_analyzer(self):
        """Create a QualityAnalyzer instance for testing."""
        return QualityAnalyzer()

    @pytest.fixture
    def sample_repo_state(self):
        """Create a sample repository state for testing."""
        return RepositoryUnderstanding(
            current_branch="feature/test",
            branch_purpose="Feature development",
            work_phase="implementing",
            files_changed=[
                FileUnderstanding(path=Path("src/test.py"), role="core", change_summary="Updated core logic", change_magnitude="significant"),
                FileUnderstanding(path=Path("tests/test_test.py"), role="test", change_summary="Added tests", change_magnitude="minor"),
                FileUnderstanding(path=Path("README.md"), role="docs", change_summary="Updated docs", change_magnitude="minor"),
            ],
            code_insights=CodeInsight(
                primary_changes=["Updated core functionality"],
                side_effects=["Modified configuration"],
                change_type="feature",
                complexity="moderate",
                risk_level="medium",
                affects_public_api=True,
                adds_tests=False,
                updates_docs=True,
                follows_patterns=True,
                introduces_tech_debt=True,
                requires_migration=False,
                breaks_compatibility=False,
            ),
            collaboration=CollaborationContext(),
            can_build=True,
            tests_passing=True,
            lint_clean=True,
            recommended_actions=["Add tests", "Review code"],
            potential_issues=["Missing test coverage"],
        )

    async def test_quality_assessment(self, quality_analyzer, sample_repo_state):
        """Test comprehensive quality assessment."""
        assessment = await quality_analyzer.assess(sample_repo_state)
        
        assert isinstance(assessment, QualityAssessment)
        assert isinstance(assessment.test_coverage, float)
        assert isinstance(assessment.documentation_coverage, float)
        assert isinstance(assessment.complexity_score, float)
        assert assessment.readability in ["poor", "fair", "good", "excellent"]
        assert assessment.maintainability in ["poor", "fair", "good", "excellent"]
        assert assessment.consistency in ["poor", "fair", "good", "excellent"]
        assert isinstance(assessment.issues, list)
        assert isinstance(assessment.quick_wins, list)
        assert isinstance(assessment.long_term_improvements, list)

    async def test_test_coverage_calculation(self, quality_analyzer, sample_repo_state):
        """Test test coverage calculation."""
        # Mock changes_summary
        sample_repo_state.changes_summary = MagicMock()
        sample_repo_state.changes_summary.code_files = ["file1.py", "file2.py"]
        sample_repo_state.changes_summary.test_files = ["test1.py"]
        
        coverage = await quality_analyzer._calculate_test_coverage(sample_repo_state)
        
        assert isinstance(coverage, float)
        assert 0.0 <= coverage <= 1.0

    async def test_quality_issue_detection(self, quality_analyzer, sample_repo_state):
        """Test quality issue detection."""
        issues = await quality_analyzer._find_quality_issues(sample_repo_state)
        
        assert isinstance(issues, list)
        for issue in issues:
            assert isinstance(issue, QualityIssue)
            assert issue.type in ["maintainability", "reliability", "security", "performance"]
            assert issue.severity in ["info", "warning", "error", "critical"]
            assert isinstance(issue.location, str)
            assert isinstance(issue.description, str)
            assert isinstance(issue.suggestion, str)

    async def test_quick_wins_identification(self, quality_analyzer):
        """Test quick wins identification."""
        sample_issues = [
            QualityIssue(
                type="maintainability",
                severity="warning",
                location="test.py",
                description="Missing docstrings",
                suggestion="Add docstrings to public methods"
            ),
            QualityIssue(
                type="maintainability",
                severity="critical",
                location="core.py",
                description="Critical security issue",
                suggestion="Fix security vulnerability"
            ),
        ]
        
        quick_wins = quality_analyzer._identify_quick_wins(sample_issues)
        
        assert isinstance(quick_wins, list)
        assert len(quick_wins) <= 3
        # Should not include critical issues in quick wins
        assert not any("critical" in win.lower() for win in quick_wins)


class TestCollaborationOptimizer:
    """Test the CollaborationOptimizer class."""

    @pytest.fixture
    def collaboration_optimizer(self):
        """Create a CollaborationOptimizer instance for testing."""
        return CollaborationOptimizer()

    @pytest.fixture
    def sample_repo_state(self):
        """Create a sample repository state for testing."""
        return RepositoryUnderstanding(
            current_branch="feature/auth",
            branch_purpose="Authentication feature",
            work_phase="implementing",
            files_changed=[
                FileUnderstanding(path=Path("src/auth/login.py"), role="core", change_summary="Updated login logic", change_magnitude="significant"),
                FileUnderstanding(path=Path("src/api/users.py"), role="core", change_summary="Updated user API", change_magnitude="minor"),
                FileUnderstanding(path=Path("tests/test_auth.py"), role="test", change_summary="Added auth tests", change_magnitude="minor"),
            ],
            code_insights=CodeInsight(
                primary_changes=["Authentication improvements"],
                side_effects=["API updates"],
                change_type="feature",
                complexity="moderate",
                risk_level="medium",
                affects_public_api=True,
                adds_tests=True,
                updates_docs=False,
                follows_patterns=True,
                introduces_tech_debt=False,
                requires_migration=False,
                breaks_compatibility=False,
            ),
            collaboration=CollaborationContext(),
            can_build=True,
            tests_passing=True,
            lint_clean=True,
            recommended_actions=["Review changes"],
            potential_issues=[],
        )

    @pytest.fixture
    def sample_session_with_patterns(self):
        """Create a sample session with learned patterns."""
        session = GitSession(
            id="test-session",
            agent_id="test-agent",
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
        )
        session.learned_patterns = PatternRecognition(
            expertise_map={
                "auth": ["alice", "bob"],
                "api": ["charlie", "diana"],
                "tests": ["eve"],
            }
        )
        return session

    async def test_reviewer_suggestion(self, collaboration_optimizer, sample_repo_state, sample_session_with_patterns):
        """Test reviewer suggestion based on expertise."""
        reviewers = await collaboration_optimizer.suggest_reviewers(
            sample_repo_state, sample_session_with_patterns
        )
        
        assert isinstance(reviewers, list)
        assert len(reviewers) <= 3
        # Should suggest reviewers based on affected areas
        expected_reviewers = {"alice", "bob", "charlie", "diana", "eve"}
        assert all(reviewer in expected_reviewers for reviewer in reviewers)

    async def test_affected_areas_identification(self, collaboration_optimizer, sample_repo_state):
        """Test identification of affected code areas."""
        areas = collaboration_optimizer._identify_affected_areas(sample_repo_state.files_changed)
        
        assert isinstance(areas, list)
        # Should identify auth and api areas based on file paths
        assert "auth" in areas or "src" in areas
        assert len(areas) > 0

    async def test_reviewer_suggestion_no_patterns(self, collaboration_optimizer, sample_repo_state):
        """Test reviewer suggestion when no patterns are learned."""
        session_no_patterns = GitSession(
            id="test-session",
            agent_id="test-agent",
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
        )
        
        reviewers = await collaboration_optimizer.suggest_reviewers(
            sample_repo_state, session_no_patterns
        )
        
        # Should return empty list when no patterns are available
        assert isinstance(reviewers, list)
        assert len(reviewers) == 0


class TestGitServiceIntegration:
    """Integration tests for GitService workflows."""

    @pytest.fixture
    def git_service(self):
        """Create a GitService instance for integration testing."""
        return GitService()

    @pytest.fixture
    async def mock_git_operations(self, git_service):
        """Mock git operations for integration tests."""
        with patch.multiple(
            git_service._git_ops,
            get_current_branch=AsyncMock(return_value="feature/test"),
            get_changed_files=AsyncMock(return_value=[
                {"path": "src/test.py", "staged": False, "status": "modified"}
            ]),
            get_file_diff=AsyncMock(return_value="+ added line\n- removed line"),
            stage_files=AsyncMock(return_value=True),
            create_commit=AsyncMock(return_value={"success": True, "sha": "abc123def456"}),
        ):
            yield

    @pytest.mark.asyncio
    async def test_end_to_end_implement_workflow(self, git_service, mock_git_operations):
        """Test end-to-end implementation workflow."""
        # Mock additional dependencies
        with patch.multiple(
            git_service,
            _file_analyzer=MagicMock(),
            _code_analyzer=MagicMock(),
            _commit_generator=MagicMock(),
            _intent_detector=MagicMock(),
        ):
            # Setup mock returns
            git_service._file_analyzer.understand_file.return_value = FileUnderstanding(
                path=Path("src/test.py"),
                role="core",
                change_summary="Added new functionality",
                change_magnitude="significant"
            )
            
            git_service._code_analyzer.analyze_changes.return_value = CodeInsight(
                primary_changes=["Added new feature"],
                side_effects=["Updated configuration"],
                change_type="feature",
                complexity="moderate",
                risk_level="low",
                affects_public_api=False,
                adds_tests=True,
                updates_docs=False,
                follows_patterns=True,
                introduces_tech_debt=False,
                requires_migration=False,
                breaks_compatibility=False,
            )
            
            git_service._commit_generator.generate.return_value = "feat: add new functionality\n\nImplemented feature X with tests"
            git_service._intent_detector.detect_intent.return_value = (WorkIntent.IMPLEMENT, 0.95)

            # Create request
            request = GitRequest(
                request="save my implementation progress",
                agent_id="test-agent",
                conversation_id="test-conv"
            )

            # Execute workflow
            response = await git_service.handle_request(request)

            # Verify response
            assert isinstance(response, GitResponse)
            assert response.success is True
            assert "implementation progress" in response.understood_as.lower()
            assert len(response.actions_taken) > 0
            assert response.conversation_id == "test-conv"
            assert response.repository_state is not None

            # Verify git operations were called
            git_service._git_ops.stage_files.assert_called()
            git_service._git_ops.create_commit.assert_called()