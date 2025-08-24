"""Focused triage system tests with essential validation.

This module tests core triage system functionality:
- Basic triage decision making (proceed vs escalate)
- Consensus building from multiple agent votes
- Role and domain correction mechanisms
- Integration with planner service
- Essential error handling and validation

Maintains practical coverage while removing over-engineering.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from khive.services.plan.models import OrchestrationEvaluation
from khive.services.plan.planner_service import PlannerService
from khive.services.plan.triage.complexity_triage import (
    ComplexityTriageService,
    TriageConsensus,
    TriageRecord,
)


@pytest.mark.unit
class TestTriageDecisions:
    """Test core triage decision making functionality."""

    @pytest.fixture
    def mock_triage_service(self):
        """Create mock triage service."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = "test_api_key"
            service = ComplexityTriageService()
            service.client = MagicMock()
            return service

    @pytest.mark.asyncio
    async def test_simple_task_proceeds(self, mock_triage_service):
        """Test that simple tasks proceed without escalation."""
        # Mock votes for simple task - all proceed
        mock_votes = [
            MagicMock(
                decision="proceed", confidence=0.9, reasoning="Simple CRUD task",
                recommended_agents=2, suggested_roles=["implementer"],
                suggested_domains=["backend-development"]
            ),
            MagicMock(
                decision="proceed", confidence=0.8, reasoning="Well-defined scope", 
                recommended_agents=2, suggested_roles=["implementer"],
                suggested_domains=["api-design"]
            ),
            MagicMock(
                decision="proceed", confidence=0.85, reasoning="Standard pattern",
                recommended_agents=2, suggested_roles=["implementer"], 
                suggested_domains=["backend-development"]
            ),
        ]

        with patch.object(mock_triage_service, "_single_triage", side_effect=mock_votes):
            with patch.object(mock_triage_service, "_record_triage", new_callable=AsyncMock):
                should_escalate, consensus = await mock_triage_service.triage(
                    "Create a simple REST API endpoint"
                )

        # Verify simple task proceeds
        assert should_escalate is False
        assert consensus.decision_votes == {"proceed": 3, "escalate": 0}
        assert consensus.average_confidence >= 0.8
        assert "implementer" in consensus.final_roles

    @pytest.mark.asyncio
    async def test_complex_task_escalates(self, mock_triage_service):
        """Test that complex tasks escalate to full consensus."""
        # Mock votes for complex task - majority escalate
        mock_votes = [
            MagicMock(decision="escalate", confidence=0.8, reasoning="Research required"),
            MagicMock(decision="escalate", confidence=0.7, reasoning="Novel algorithms"),
            MagicMock(decision="proceed", confidence=0.6, reasoning="Might be simple"),
        ]

        with patch.object(mock_triage_service, "_single_triage", side_effect=mock_votes):
            with patch.object(mock_triage_service, "_record_triage", new_callable=AsyncMock):
                should_escalate, consensus = await mock_triage_service.triage(
                    "Research novel Byzantine fault tolerance algorithms"
                )

        # Verify complex task escalates
        assert should_escalate is True
        assert consensus.decision_votes == {"proceed": 1, "escalate": 2}
        assert consensus.average_confidence >= 0.6

    @pytest.mark.parametrize("task,expected_escalation", [
        ("Create simple CRUD endpoint", False),
        ("Fix authentication bug", False), 
        ("Research Byzantine consensus algorithms", True),
        ("Design distributed microservices architecture", True),
        ("Build entire e-commerce platform", True),
    ])
    @pytest.mark.asyncio
    async def test_triage_decision_patterns(self, mock_triage_service, task, expected_escalation):
        """Test triage decisions for various task complexity patterns."""
        # Mock votes based on expected escalation
        if expected_escalation:
            mock_votes = [
                MagicMock(decision="escalate", confidence=0.8),
                MagicMock(decision="escalate", confidence=0.9),
                MagicMock(decision="escalate", confidence=0.7),
            ]
        else:
            mock_votes = [
                MagicMock(decision="proceed", confidence=0.9, recommended_agents=2, 
                         suggested_roles=["implementer"], suggested_domains=["api-design"]),
                MagicMock(decision="proceed", confidence=0.8, recommended_agents=2,
                         suggested_roles=["implementer"], suggested_domains=["backend-development"]),
                MagicMock(decision="proceed", confidence=0.85, recommended_agents=2,
                         suggested_roles=["implementer"], suggested_domains=["api-design"]),
            ]

        with patch.object(mock_triage_service, "_single_triage", side_effect=mock_votes):
            with patch.object(mock_triage_service, "_record_triage", new_callable=AsyncMock):
                should_escalate, consensus = await mock_triage_service.triage(task)

        assert should_escalate == expected_escalation


@pytest.mark.unit
class TestTriageConsensus:
    """Test consensus building and vote correction mechanisms."""

    @pytest.fixture
    def mock_triage_service(self):
        """Create mock triage service."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = "test_api_key"
            service = ComplexityTriageService()
            service.available_roles = ["researcher", "implementer", "tester"]
            service.available_domains = ["api-design", "backend-development"]
            return service

    def test_consensus_building(self, mock_triage_service):
        """Test consensus building from multiple votes."""
        # Test all proceed votes
        votes_proceed = [
            MagicMock(decision="proceed", confidence=0.8, recommended_agents=2,
                     suggested_roles=["implementer"], suggested_domains=["api-design"]),
            MagicMock(decision="proceed", confidence=0.9, recommended_agents=3, 
                     suggested_roles=["implementer", "tester"], suggested_domains=["backend-development"]),
            MagicMock(decision="proceed", confidence=0.7, recommended_agents=1,
                     suggested_roles=["implementer"], suggested_domains=["api-design"]),
        ]

        consensus = mock_triage_service._build_consensus(votes_proceed)
        assert consensus.should_escalate is False
        assert consensus.final_agent_count == 3  # Max agent count
        assert "implementer" in consensus.final_roles

        # Test mixed votes where escalate wins
        votes_mixed = [
            MagicMock(decision="escalate", confidence=0.8),
            MagicMock(decision="escalate", confidence=0.9),
            MagicMock(decision="proceed", confidence=0.7),
        ]

        consensus = mock_triage_service._build_consensus(votes_mixed)
        assert consensus.should_escalate is True
        assert consensus.decision_votes == {"proceed": 1, "escalate": 2}

    def test_role_domain_correction(self, mock_triage_service):
        """Test correction of invalid roles and domains from LLM responses."""
        # Test with invalid role/domain that needs correction
        vote_data = {
            "decision": "proceed",
            "confidence": 0.8,
            "reasoning": "Test task",
            "recommended_agents": 2,
            "suggested_roles": ["developer", "researcher"],  # 'developer' invalid
            "suggested_domains": ["web-development"],  # 'web-development' invalid
        }

        corrected = mock_triage_service._correct_vote_data(vote_data)

        # Verify corrections
        assert "developer" not in corrected["suggested_roles"]
        assert "researcher" in corrected["suggested_roles"]
        assert corrected["suggested_domains"][0] in mock_triage_service.available_domains

    def test_validation_errors(self, mock_triage_service):
        """Test validation of triage vote data."""
        # Valid vote data
        valid_vote_data = {
            "decision": "proceed",
            "confidence": 0.8,
            "reasoning": "Simple task",
            "recommended_agents": 2,
            "suggested_roles": ["implementer"],
            "suggested_domains": ["api-design"],
        }

        # Test valid vote
        vote = mock_triage_service.TriageVote(**valid_vote_data)
        assert vote.decision == "proceed"
        assert vote.confidence == 0.8

        # Test validation errors
        with pytest.raises(ValidationError):
            mock_triage_service.TriageVote(**{**valid_vote_data, "decision": "invalid"})
        
        with pytest.raises(ValidationError):
            mock_triage_service.TriageVote(**{**valid_vote_data, "confidence": 1.5})
            
        with pytest.raises(ValidationError):
            mock_triage_service.TriageVote(**{**valid_vote_data, "recommended_agents": 15})


@pytest.mark.integration
class TestTriageIntegration:
    """Test triage integration with planner service and error handling."""

    @pytest.mark.asyncio
    async def test_planner_triage_integration(self):
        """Test that planner service properly integrates triage system."""
        # Mock triage service
        mock_triage_service = MagicMock()
        mock_consensus = TriageConsensus(
            should_escalate=False,
            decision_votes={"proceed": 3, "escalate": 0},
            average_confidence=0.9,
            final_agent_count=2,
            final_roles=["implementer", "tester"],
            final_domains=["api-design"],
            consensus_reasoning="Simple CRUD task | Well-defined scope | Standard pattern",
        )
        mock_triage_service.triage = AsyncMock(return_value=(False, mock_consensus))

        # Mock planner service
        mock_planner_service = PlannerService()
        mock_planner = MagicMock()
        mock_planner.create_session.return_value = "test_session_123"

        with patch.object(mock_planner_service, "_get_triage_service", return_value=mock_triage_service):
            with patch.object(mock_planner_service, "_get_planner", return_value=mock_planner):
                from khive.services.plan.parts import PlannerRequest
                
                request = PlannerRequest(task_description="Create simple CRUD API")
                response = await mock_planner_service.handle_request(request)

        # Verify integration
        mock_triage_service.triage.assert_called_once_with("Create simple CRUD API")
        assert response.success is True

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test handling of API errors during triage."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = "test_api_key"
            service = ComplexityTriageService()
            service.client = MagicMock()

            # Mock API failure
            service.client.chat.completions.create = AsyncMock(
                side_effect=Exception("OpenAI API Error")
            )

            with pytest.raises(Exception, match="OpenAI API Error"):
                await service._single_triage("test prompt", "efficiency")

    @pytest.mark.asyncio
    async def test_data_recording(self, tmp_path):
        """Test that triage decisions are recorded correctly."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = "test_api_key"
            service = ComplexityTriageService()
            
            # Setup temporary data directory
            service.data_dir = tmp_path / "triage"
            service.data_dir.mkdir()
            service.data_file = service.data_dir / "test_triage.jsonl"

            # Mock votes and consensus
            mock_votes = [
                MagicMock(
                    decision="proceed", confidence=0.9,
                    model_dump=MagicMock(return_value={"decision": "proceed", "confidence": 0.9})
                )
            ]
            mock_consensus = TriageConsensus(
                should_escalate=False,
                decision_votes={"proceed": 3, "escalate": 0},
                average_confidence=0.9,
            )

            await service._record_triage("test prompt", mock_votes, mock_consensus)

            # Verify recording
            assert service.data_file.exists()
            content = service.data_file.read_text()
            record = json.loads(content.strip())
            
            assert record["prompt"] == "test prompt"
            assert record["escalated"] is False
            assert record["final_decision"] == "proceed"

    def test_triage_record_creation(self):
        """Test TriageRecord data structure creation."""
        record = TriageRecord(
            timestamp="2024-01-01T12:00:00Z",
            prompt="Test prompt",
            word_count=2,
            votes=[{"decision": "proceed", "confidence": 0.9}],
            consensus={"should_escalate": False, "average_confidence": 0.9},
            escalated=False,
            final_decision="proceed",
            actual_agents_used=2,
            execution_success=True,
        )

        # Test serialization
        jsonl_output = record.to_jsonl()
        parsed = json.loads(jsonl_output)
        
        assert parsed["prompt"] == "Test prompt"
        assert parsed["escalated"] is False
        assert parsed["execution_success"] is True
