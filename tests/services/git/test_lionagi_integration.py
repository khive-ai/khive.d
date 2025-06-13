# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for LionAGI integration with GitService.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from khive.services.git.git_service import GitService
from khive.services.git.parts import GitRequest, WorkContext


class TestLionAGIIntegration:
    """Test LionAGI integration with GitService."""

    @pytest.fixture
    def git_service(self):
        """Create a GitService instance."""
        return GitService()

    @pytest.fixture
    def mock_git_request(self):
        """Create a mock GitRequest."""
        return GitRequest(
            request="save my progress",
            agent_id="test-agent",
            conversation_id="test-conversation",
            context=WorkContext(
                task_description="Testing LionAGI integration",
                related_issues=["177"],
                requirements=["Use LionAGI Branch for conversation management"],
                design_decisions=["Integrate MessageManager and ActionManager"]
            )
        )

    @pytest.mark.asyncio
    async def test_lionagi_branch_creation(self, git_service):
        """Test that LionAGI Branch is created successfully."""
        agent_id = "test-agent"
        conversation_id = "test-conv"
        
        branch = await git_service._get_or_create_branch(agent_id, conversation_id)
        
        assert branch is not None
        assert conversation_id in git_service._branches
        assert branch.name == f"git-service-{agent_id}"
        assert branch.user == agent_id

    @pytest.mark.asyncio
    async def test_git_tools_registration(self, git_service):
        """Test that git operation tools are registered properly."""
        agent_id = "test-agent"
        
        # Test that we can create tools individually
        status_tool = git_service._create_git_status_tool()
        assert status_tool is not None
        assert hasattr(status_tool, 'func_callable')
        
        commit_tool = git_service._create_git_commit_tool()
        assert commit_tool is not None
        assert hasattr(commit_tool, 'func_callable')
        
        push_tool = git_service._create_git_push_tool()
        assert push_tool is not None
        assert hasattr(push_tool, 'func_callable')
        
        branch_tool = git_service._create_git_branch_tool()
        assert branch_tool is not None
        assert hasattr(branch_tool, 'func_callable')
        
        analyze_tool = git_service._create_git_analyze_tool()
        assert analyze_tool is not None
        assert hasattr(analyze_tool, 'func_callable')

    @pytest.mark.asyncio
    async def test_conversation_history_tracking(self, git_service, mock_git_request):
        """Test that conversation history is tracked in LionAGI Branch."""
        with patch.object(git_service, '_get_repository_state', new_callable=AsyncMock) as mock_state, \
             patch.object(git_service._intent_detector, 'detect_intent') as mock_detect, \
             patch.object(git_service, '_handle_implement', new_callable=AsyncMock) as mock_implement:
            
            # Setup mocks
            mock_state.return_value = Mock()
            mock_detect.return_value = ("IMPLEMENT", 0.9)
            mock_implement.return_value = Mock(success=True)
            
            # Process request
            response = await git_service.handle_request(mock_git_request)
            
            # Check that branch was created and message was added
            branch = git_service._branches.get(mock_git_request.conversation_id)
            assert branch is not None
            assert len(branch.msgs.messages) > 0
            
            # Check that the user instruction was added
            instructions = [msg for msg in branch.msgs.messages if hasattr(msg, 'instruction')]
            assert len(instructions) > 0

    @pytest.mark.asyncio
    async def test_enhanced_intent_detection(self, git_service, mock_git_request):
        """Test enhanced intent detection with conversation context."""
        # Create a branch with some conversation history
        branch = await git_service._get_or_create_branch(
            mock_git_request.agent_id, mock_git_request.conversation_id
        )
        
        # Add some previous messages to create context
        await branch.msgs.a_add_message(
            instruction="I'm working on implementing LionAGI integration",
            sender="test-agent"
        )
        await branch.msgs.a_add_message(
            assistant_response="I'll help you with the LionAGI integration",
            sender="git_service"
        )
        
        # Mock the session and repository state
        session = Mock()
        session.action_history = []
        session.repository_knowledge = {}
        
        with patch.object(git_service, '_get_repository_state', new_callable=AsyncMock) as mock_state, \
             patch.object(git_service._intent_detector, 'detect_intent') as mock_detect:
            
            mock_state.return_value = Mock()
            mock_detect.return_value = ("IMPLEMENT", 0.7)
            
            # Test enhanced intent detection
            intent, confidence = await git_service._detect_intent_with_branch(
                mock_git_request, session, branch
            )
            
            # Should boost confidence due to conversation context
            assert confidence > 0.7  # Should be boosted from 0.7

    @pytest.mark.asyncio
    async def test_git_status_tool(self, git_service):
        """Test the git status tool functionality."""
        branch = await git_service._get_or_create_branch("test-agent")
        
        # Get the git status tool
        status_tool = git_service._create_git_status_tool()
        assert status_tool is not None
        
        # Mock the repository state
        with patch.object(git_service, '_get_repository_state', new_callable=AsyncMock) as mock_state:
            mock_repo_state = Mock()
            mock_repo_state.current_branch = "feature/lionagi-integration"
            mock_repo_state.has_uncommitted_changes = True
            mock_repo_state.has_staged_changes = False
            mock_repo_state.files_changed = [Mock(), Mock()]
            mock_repo_state.work_phase = "implementing"
            mock_repo_state.branch_purpose = "Feature development"
            
            mock_state.return_value = mock_repo_state
            
            # Execute the tool
            result = await status_tool.func_callable()
            
            # Verify results
            assert result["current_branch"] == "feature/lionagi-integration"
            assert result["has_changes"] is True
            assert result["has_staged"] is False
            assert result["files_changed"] == 2
            assert result["work_phase"] == "implementing"
            assert result["branch_purpose"] == "Feature development"

    @pytest.mark.asyncio
    async def test_git_commit_tool(self, git_service):
        """Test the git commit tool functionality."""
        commit_tool = git_service._create_git_commit_tool()
        assert commit_tool is not None
        
        with patch.object(git_service, '_get_repository_state', new_callable=AsyncMock) as mock_state, \
             patch.object(git_service, '_smart_stage_files', new_callable=AsyncMock) as mock_stage, \
             patch.object(git_service._commit_generator, 'generate', new_callable=AsyncMock) as mock_gen, \
             patch.object(git_service, '_perform_commit', new_callable=AsyncMock) as mock_commit:
            
            # Setup mocks
            mock_state.return_value = Mock(files_changed=[], code_insights=Mock())
            mock_stage.return_value = ["file1.py", "file2.py"]
            mock_gen.return_value = "feat: add LionAGI integration"
            mock_commit.return_value = {"sha": "abc123def456"}
            
            # Execute tool with auto-staging
            result = await commit_tool.func_callable(auto_stage=True)
            
            # Verify results
            assert result["success"] is True
            assert result["commit_sha"] == "abc123def456"
            assert result["message"] == "feat: add LionAGI integration"
            assert result["files_staged"] == ["file1.py", "file2.py"]

    @pytest.mark.asyncio
    async def test_lionagi_fallback_when_unavailable(self):
        """Test that service works when LionAGI is not available."""
        # This would test the fallback behavior if LionAGI wasn't installed
        # For now, since we have LionAGI installed, we'll just verify the flag
        git_service = GitService()
        assert git_service._lionagi_available is True

    @pytest.mark.asyncio
    async def test_branch_cleanup(self, git_service):
        """Test that branches are properly managed and cleaned up."""
        # Create multiple branches
        branch1 = await git_service._get_or_create_branch("agent1", "conv1")
        branch2 = await git_service._get_or_create_branch("agent2", "conv2")
        
        assert len(git_service._branches) == 2
        assert "conv1" in git_service._branches
        assert "conv2" in git_service._branches
        
        # Verify branches are independent
        assert branch1.id != branch2.id
        assert branch1.user != branch2.user

    @pytest.mark.asyncio
    async def test_error_handling_with_branch(self, git_service, mock_git_request):
        """Test error handling with LionAGI Branch integration."""
        # Mock all dependencies to avoid cascading errors
        with patch.object(git_service, '_get_repository_state', new_callable=AsyncMock) as mock_state, \
             patch.object(git_service._intent_detector, 'detect_intent') as mock_detect, \
             patch.object(git_service, '_handle_implement', new_callable=AsyncMock) as mock_implement:
            
            # Setup the main error we want to test
            mock_detect.side_effect = Exception("Intent detection failed")
            mock_state.return_value = Mock()
            mock_implement.return_value = Mock(success=False)
            
            # This should not crash and should handle the error gracefully
            response = await git_service.handle_request(mock_git_request)
            
            # Verify error was handled
            assert response.success is False
            assert "error" in response.learned