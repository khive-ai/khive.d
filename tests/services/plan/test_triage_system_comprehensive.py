"""Comprehensive tests for the two-tier triage system and consensus mechanisms."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from khive.services.plan.models import OrchestrationEvaluation
from khive.services.plan.planner_service import PlannerService
from khive.services.plan.triage.complexity_triage import (
    ComplexityTriageService, TriageConsensus, TriageRecord)


@pytest.mark.unit
class TestComplexityTriageService:
    """Test the ComplexityTriageService two-tier system."""

    @pytest.fixture
    def mock_triage_service(self):
        """Create mock triage service."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = "test_api_key"
            service = ComplexityTriageService()
            service.client = MagicMock()
            return service

    @pytest.mark.asyncio
    async def test_triage_simple_task_proceeds(self, mock_triage_service):
        """Test that simple tasks proceed without escalation."""
        # Mock 3 agents voting to proceed
        mock_votes = [
            MagicMock(
                decision="proceed",
                confidence=0.9,
                reasoning="Simple CRUD task",
                recommended_agents=2,
                suggested_roles=["implementer"],
                suggested_domains=["backend-development"],
            ),
            MagicMock(
                decision="proceed",
                confidence=0.8,
                reasoning="Well-defined scope",
                recommended_agents=3,
                suggested_roles=["implementer", "tester"],
                suggested_domains=["api-design"],
            ),
            MagicMock(
                decision="proceed",
                confidence=0.85,
                reasoning="Standard pattern",
                recommended_agents=2,
                suggested_roles=["implementer"],
                suggested_domains=["backend-development"],
            ),
        ]

        with patch.object(
            mock_triage_service, "_single_triage", side_effect=mock_votes
        ):
            with patch.object(
                mock_triage_service, "_record_triage", new_callable=AsyncMock
            ):
                should_escalate, consensus = await mock_triage_service.triage(
                    "Create a simple REST API endpoint"
                )

        assert should_escalate is False
        assert consensus.decision_votes == {"proceed": 3, "escalate": 0}
        assert abs(consensus.average_confidence - 0.85) < 0.01  # (0.9 + 0.8 + 0.85) / 3
        assert consensus.final_agent_count == 3  # Max of [2, 3, 2]
        assert "implementer" in consensus.final_roles
        assert len(consensus.final_domains) <= 2

    @pytest.mark.asyncio
    async def test_triage_complex_task_escalates(self, mock_triage_service):
        """Test that complex tasks escalate to full consensus."""
        # Mock 2+ agents voting to escalate
        mock_votes = [
            MagicMock(
                decision="escalate",
                confidence=0.7,
                reasoning="Research required",
                recommended_agents=0,
                suggested_roles=[],
                suggested_domains=[],
            ),
            MagicMock(
                decision="escalate",
                confidence=0.8,
                reasoning="Novel algorithms",
                recommended_agents=0,
                suggested_roles=[],
                suggested_domains=[],
            ),
            MagicMock(
                decision="proceed",
                confidence=0.6,
                reasoning="Might be simple",
                recommended_agents=4,
                suggested_roles=["researcher"],
                suggested_domains=["distributed-systems"],
            ),
        ]

        with patch.object(
            mock_triage_service, "_single_triage", side_effect=mock_votes
        ):
            with patch.object(
                mock_triage_service, "_record_triage", new_callable=AsyncMock
            ):
                should_escalate, consensus = await mock_triage_service.triage(
                    "Research novel Byzantine fault tolerance algorithms"
                )

        assert should_escalate is True
        assert consensus.decision_votes == {"proceed": 1, "escalate": 2}
        assert consensus.average_confidence == 0.7  # (0.7 + 0.8 + 0.6) / 3
        assert consensus.final_agent_count is None  # No recommendations when escalating
        assert consensus.final_roles is None

    @pytest.mark.asyncio
    async def test_single_triage_agent_perspectives(self, mock_triage_service):
        """Test that different perspectives give expected results."""
        mock_response_proceed = MagicMock()
        mock_response_proceed.choices = [MagicMock()]
        mock_response_proceed.choices[0].message.content = json.dumps({
            "decision": "proceed",
            "confidence": 0.9,
            "reasoning": "Simple implementation task",
            "recommended_agents": 2,
            "suggested_roles": ["implementer", "tester"],
            "suggested_domains": ["api-design"],
        })

        mock_response_escalate = MagicMock()
        mock_response_escalate.choices = [MagicMock()]
        mock_response_escalate.choices[0].message.content = json.dumps({
            "decision": "escalate",
            "confidence": 0.8,
            "reasoning": "Requires research and analysis",
            "recommended_agents": 0,
            "suggested_roles": [],
            "suggested_domains": [],
        })

        # Test efficiency perspective (tends to proceed on simple tasks)
        mock_triage_service.client.chat.completions.create = AsyncMock(
            return_value=mock_response_proceed
        )
        result = await mock_triage_service._single_triage(
            "Build simple API", "efficiency"
        )
        assert result.decision == "proceed"
        assert result.recommended_agents == 2

        # Test risk perspective (tends to escalate on complex tasks)
        mock_triage_service.client.chat.completions.create = AsyncMock(
            return_value=mock_response_escalate
        )
        result = await mock_triage_service._single_triage(
            "Design distributed consensus", "risk"
        )
        assert result.decision == "escalate"
        assert result.recommended_agents == 0

    @pytest.mark.asyncio
    async def test_role_domain_correction(self, mock_triage_service):
        """Test role and domain correction for LLM mistakes."""
        mock_triage_service.available_roles = ["researcher", "implementer", "tester"]
        mock_triage_service.available_domains = ["api-design", "backend-development"]

        # Test with invalid role/domain that needs correction
        vote_data = {
            "decision": "proceed",
            "confidence": 0.8,
            "reasoning": "Test task",
            "recommended_agents": 2,
            "suggested_roles": [
                "developer",
                "researcher",
            ],  # 'developer' needs correction
            "suggested_domains": [
                "web-development"
            ],  # 'web-development' needs correction
        }

        corrected = mock_triage_service._correct_vote_data(vote_data)

        # Should have corrected invalid values
        assert "developer" not in corrected["suggested_roles"]
        assert "researcher" in corrected["suggested_roles"]
        assert (
            corrected["suggested_domains"][0] in mock_triage_service.available_domains
        )

    def test_string_correction_fallback(self, mock_triage_service):
        """Test string correction fallback when lionagi is unavailable."""
        mock_triage_service.available_roles = ["researcher", "analyst", "implementer"]

        # Test with lionagi unavailable (ImportError)
        with patch(
            "khive.services.plan.triage.complexity_triage.string_similarity",
            side_effect=ImportError,
        ):
            result = mock_triage_service._correct_string_value(
                "invalid_role", mock_triage_service.available_roles
            )
            # Should return first valid option as fallback
            assert result == "researcher"

    def test_consensus_building_edge_cases(self, mock_triage_service):
        """Test consensus building with edge cases."""
        # Test with all proceed votes
        votes_proceed = [
            MagicMock(
                decision="proceed",
                confidence=0.8,
                reasoning="Simple",
                recommended_agents=2,
                suggested_roles=["implementer"],
                suggested_domains=["api-design"],
            ),
            MagicMock(
                decision="proceed",
                confidence=0.9,
                reasoning="Clear scope",
                recommended_agents=3,
                suggested_roles=["implementer", "tester"],
                suggested_domains=["backend-development"],
            ),
            MagicMock(
                decision="proceed",
                confidence=0.7,
                reasoning="Standard task",
                recommended_agents=1,
                suggested_roles=["implementer"],
                suggested_domains=["api-design"],
            ),
        ]

        consensus = mock_triage_service._build_consensus(votes_proceed)
        assert consensus.should_escalate is False
        assert consensus.final_agent_count == 3  # Max of [2, 3, 1]
        assert "implementer" in consensus.final_roles
        assert len(consensus.final_domains) <= 2

        # Test with mixed votes where escalate wins
        votes_mixed = [
            MagicMock(decision="escalate", confidence=0.8),
            MagicMock(decision="escalate", confidence=0.9),
            MagicMock(decision="proceed", confidence=0.7),
        ]

        consensus = mock_triage_service._build_consensus(votes_mixed)
        assert consensus.should_escalate is True
        assert consensus.decision_votes == {"proceed": 1, "escalate": 2}

    @pytest.mark.asyncio
    async def test_triage_data_recording(self, mock_triage_service, tmp_path):
        """Test that triage decisions are recorded for training."""
        # Setup temporary data directory
        mock_triage_service.data_dir = tmp_path / "triage"
        mock_triage_service.data_dir.mkdir()
        mock_triage_service.data_file = (
            mock_triage_service.data_dir / "test_triage.jsonl"
        )

        # Mock votes
        mock_votes = [
            MagicMock(
                decision="proceed",
                confidence=0.9,
                model_dump=MagicMock(
                    return_value={"decision": "proceed", "confidence": 0.9}
                ),
            )
        ]
        mock_consensus = TriageConsensus(
            should_escalate=False,
            decision_votes={"proceed": 3, "escalate": 0},
            average_confidence=0.9,
        )

        await mock_triage_service._record_triage(
            "test prompt", mock_votes, mock_consensus
        )

        # Verify file was created and contains data
        assert mock_triage_service.data_file.exists()
        content = mock_triage_service.data_file.read_text()
        record = json.loads(content.strip())

        assert record["prompt"] == "test prompt"
        assert record["escalated"] is False
        assert record["final_decision"] == "proceed"
        assert len(record["votes"]) == 1

    @pytest.mark.parametrize(
        "prompt,expected_escalation",
        [
            ("Create simple CRUD endpoint", False),
            ("Fix bug in authentication", False),
            ("Update documentation", False),
            ("Research Byzantine consensus algorithms", True),
            ("Design distributed architecture", True),
            ("Analyze performance bottlenecks", True),
            ("Build entire microservices platform", True),
            ("Implement and test user management", True),  # Multiple phases
        ],
    )
    @pytest.mark.asyncio
    async def test_triage_decision_patterns(
        self, mock_triage_service, prompt, expected_escalation
    ):
        """Test triage decisions for various task patterns."""
        # Mock responses based on expected escalation
        if expected_escalation:
            mock_votes = [
                MagicMock(decision="escalate", confidence=0.8),
                MagicMock(decision="escalate", confidence=0.9),
                MagicMock(decision="escalate", confidence=0.7),
            ]
        else:
            mock_votes = [
                MagicMock(
                    decision="proceed",
                    confidence=0.9,
                    suggested_roles=["implementer"],
                    suggested_domains=["api-design"],
                    recommended_agents=2,
                ),
                MagicMock(
                    decision="proceed",
                    confidence=0.8,
                    suggested_roles=["implementer"],
                    suggested_domains=["backend-development"],
                    recommended_agents=2,
                ),
                MagicMock(
                    decision="proceed",
                    confidence=0.85,
                    suggested_roles=["implementer"],
                    suggested_domains=["api-design"],
                    recommended_agents=1,
                ),
            ]

        with patch.object(
            mock_triage_service, "_single_triage", side_effect=mock_votes
        ):
            with patch.object(
                mock_triage_service, "_record_triage", new_callable=AsyncMock
            ):
                should_escalate, consensus = await mock_triage_service.triage(prompt)

        assert should_escalate == expected_escalation

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_triage_service):
        """Test handling of API errors during triage."""
        # Mock API failure
        mock_triage_service.client.chat.completions.create = AsyncMock(
            side_effect=Exception("OpenAI API Error")
        )

        with pytest.raises(Exception):
            await mock_triage_service._single_triage("test prompt", "efficiency")

    def test_triage_vote_validation(self, mock_triage_service):
        """Test TriageVote model validation."""
        # Valid vote data
        valid_vote_data = {
            "decision": "proceed",
            "confidence": 0.8,
            "reasoning": "Simple task",
            "recommended_agents": 2,
            "suggested_roles": ["implementer"],
            "suggested_domains": ["api-design"],
        }

        vote = mock_triage_service.TriageVote(**valid_vote_data)
        assert vote.decision == "proceed"
        assert vote.confidence == 0.8

        # Invalid decision
        with pytest.raises(ValidationError):
            mock_triage_service.TriageVote(**{
                **valid_vote_data,
                "decision": "invalid_decision",
            })

        # Invalid confidence range
        with pytest.raises(ValidationError):
            mock_triage_service.TriageVote(**{**valid_vote_data, "confidence": 1.5})

        # Invalid agent count
        with pytest.raises(ValidationError):
            mock_triage_service.TriageVote(**{
                **valid_vote_data,
                "recommended_agents": 15,
            })


@pytest.mark.unit
class TestTriageIntegration:
    """Test integration between triage service and planner service."""

    @pytest.fixture
    def mock_planner_service(self):
        """Create mock planner service."""
        return PlannerService()

    @pytest.mark.asyncio
    async def test_planner_service_uses_triage(self, mock_planner_service):
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

        # Mock planner creation
        mock_planner = MagicMock()
        mock_planner.create_session.return_value = "test_session_123"

        with patch.object(
            mock_planner_service,
            "_get_triage_service",
            return_value=mock_triage_service,
        ):
            with patch.object(
                mock_planner_service, "_get_planner", return_value=mock_planner
            ):
                from khive.services.plan.parts import PlannerRequest

                request = PlannerRequest(task_description="Create simple CRUD API")
                response = await mock_planner_service.handle_request(request)

        # Verify triage was called
        mock_triage_service.triage.assert_called_once_with("Create simple CRUD API")

        # Verify response structure
        assert response.success is True
        assert "simple" in response.session_id or "simple" in response.summary.lower()

    @pytest.mark.asyncio
    async def test_escalation_to_full_consensus(self, mock_planner_service):
        """Test escalation from triage to full consensus."""
        # Mock triage service to escalate
        mock_triage_service = MagicMock()
        mock_consensus = TriageConsensus(
            should_escalate=True,
            decision_votes={"proceed": 1, "escalate": 2},
            average_confidence=0.7,
        )
        mock_triage_service.triage = AsyncMock(return_value=(True, mock_consensus))

        # Mock full planner for consensus
        mock_planner = MagicMock()
        mock_planner.create_session.return_value = "test_session_complex_456"
        mock_planner.evaluate_request = AsyncMock(
            return_value=[
                {
                    "config": {"name": "test_agent"},
                    "evaluation": OrchestrationEvaluation(
                        complexity="complex",
                        complexity_reason="Distributed system",
                        total_agents=8,
                        agent_reason="Multiple coordination points",
                        rounds_needed=3,
                        role_priorities=["researcher", "architect", "implementer"],
                        primary_domains=["distributed-systems"],
                        domain_reason="Consensus expertise needed",
                        workflow_pattern="hybrid",
                        workflow_reason="Mixed dependencies",
                        quality_level="thorough",
                        quality_reason="Critical system",
                        rules_applied=["complexity"],
                        confidence=0.85,
                        summary="Complex distributed task",
                    ),
                    "cost": 0.001,
                    "response_time_ms": 150,
                }
            ]
        )
        mock_planner.build_consensus.return_value = (
            "Full consensus output",
            {
                "complexity": "complex",
                "agent_count": 8,
                "role_recommendations": [("researcher", 0.9), ("architect", 0.8)],
                "domains": ["distributed-systems"],
                "confidence": 0.85,
                "quality_level": "thorough",
                "workflow_pattern": "hybrid",
            },
        )

        with patch.object(
            mock_planner_service,
            "_get_triage_service",
            return_value=mock_triage_service,
        ):
            with patch.object(
                mock_planner_service, "_get_planner", return_value=mock_planner
            ):
                from khive.services.plan.parts import PlannerRequest

                request = PlannerRequest(
                    task_description="Design distributed consensus system"
                )
                response = await mock_planner_service.handle_request(request)

        # Verify escalation occurred
        mock_triage_service.triage.assert_called_once()
        mock_planner.evaluate_request.assert_called_once()
        mock_planner.build_consensus.assert_called_once()

        assert response.success is True
        assert response.summary == "Full consensus output"
        assert "complex" in response.session_id

    @pytest.mark.asyncio
    async def test_triage_metrics_tracking(self, mock_planner_service):
        """Test that triage metrics are properly tracked."""
        initial_metrics = mock_planner_service.get_metrics()
        assert initial_metrics["total_requests"] == 0
        assert initial_metrics["triage_simple"] == 0
        assert initial_metrics["triage_complex"] == 0

        # Mock simple path
        mock_triage_service = MagicMock()
        mock_consensus = TriageConsensus(
            should_escalate=False,
            decision_votes={"proceed": 3, "escalate": 0},
            average_confidence=0.9,
            final_agent_count=2,
            final_roles=["implementer"],
        )
        mock_triage_service.triage = AsyncMock(return_value=(False, mock_consensus))

        mock_planner = MagicMock()
        mock_planner.create_session.return_value = "test_session"

        with patch.object(
            mock_planner_service,
            "_get_triage_service",
            return_value=mock_triage_service,
        ):
            with patch.object(
                mock_planner_service, "_get_planner", return_value=mock_planner
            ):
                from khive.services.plan.parts import PlannerRequest

                request = PlannerRequest(task_description="Simple task")
                await mock_planner_service.handle_request(request)

        # Check metrics updated
        updated_metrics = mock_planner_service.get_metrics()
        assert updated_metrics["total_requests"] == 1
        assert updated_metrics["triage_simple"] == 1
        assert updated_metrics["triage_complex"] == 0
        assert updated_metrics["total_llm_calls"] == 3  # 3 triage calls
        assert updated_metrics["escalation_rate"] == 0.0


@pytest.mark.unit
class TestTriageRecord:
    """Test TriageRecord data collection functionality."""

    def test_triage_record_creation(self):
        """Test TriageRecord creation and serialization."""
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

        # Test JSONL serialization
        jsonl_output = record.to_jsonl()
        parsed = json.loads(jsonl_output)

        assert parsed["prompt"] == "Test prompt"
        assert parsed["escalated"] is False
        assert parsed["execution_success"] is True
        assert len(parsed["votes"]) == 1

    def test_triage_record_defaults(self):
        """Test TriageRecord with minimal required fields."""
        record = TriageRecord(
            timestamp="2024-01-01T12:00:00Z",
            prompt="Test prompt",
            word_count=2,
            votes=[],
            consensus={},
            escalated=False,
        )

        assert record.final_decision is None
        assert record.actual_agents_used is None
        assert record.execution_success is None


@pytest.mark.integration
class TestTriageSystemEnd2End:
    """Integration tests for complete triage system."""

    @pytest.mark.asyncio
    async def test_end_to_end_simple_path(self):
        """Test complete end-to-end flow for simple task."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = "test_api_key"

            # Create real triage service but mock API calls
            triage_service = ComplexityTriageService()

            # Mock the OpenAI API calls to return proceed decisions
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "decision": "proceed",
                "confidence": 0.9,
                "reasoning": "Simple CRUD task",
                "recommended_agents": 2,
                "suggested_roles": ["implementer"],
                "suggested_domains": ["api-design"],
            })

            triage_service.client.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            # Test the complete flow
            with patch.object(triage_service, "_record_triage", new_callable=AsyncMock):
                should_escalate, consensus = await triage_service.triage(
                    "Create a simple REST API endpoint for user registration"
                )

            assert should_escalate is False
            assert consensus.decision_votes["proceed"] == 3
            assert consensus.final_agent_count is not None
            assert len(consensus.final_roles) > 0
            assert consensus.average_confidence > 0.8

    @pytest.mark.asyncio
    async def test_end_to_end_complex_path(self):
        """Test complete end-to-end flow for complex task."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = "test_api_key"

            # Create real triage service but mock API calls
            triage_service = ComplexityTriageService()

            # Mock the OpenAI API calls to return escalate decisions
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "decision": "escalate",
                "confidence": 0.8,
                "reasoning": "Research and novel algorithms required",
                "recommended_agents": 0,
                "suggested_roles": [],
                "suggested_domains": [],
            })

            triage_service.client.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            # Test the complete flow
            with patch.object(triage_service, "_record_triage", new_callable=AsyncMock):
                should_escalate, consensus = await triage_service.triage(
                    "Research and implement novel Byzantine fault tolerance algorithms for distributed consensus"
                )

            assert should_escalate is True
            assert consensus.decision_votes["escalate"] == 3
            assert consensus.final_agent_count is None
            assert consensus.final_roles is None
            assert consensus.average_confidence > 0.5

    @pytest.mark.asyncio
    async def test_mixed_voting_scenarios(self):
        """Test various mixed voting scenarios."""
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = "test_api_key"

            triage_service = ComplexityTriageService()

            # Test 2 escalate, 1 proceed -> should escalate
            votes = [
                json.dumps({
                    "decision": "escalate",
                    "confidence": 0.8,
                    "reasoning": "Complex scope",
                    "recommended_agents": 0,
                    "suggested_roles": [],
                    "suggested_domains": [],
                }),
                json.dumps({
                    "decision": "escalate",
                    "confidence": 0.7,
                    "reasoning": "Multiple unknowns",
                    "recommended_agents": 0,
                    "suggested_roles": [],
                    "suggested_domains": [],
                }),
                json.dumps({
                    "decision": "proceed",
                    "confidence": 0.9,
                    "reasoning": "Might be simple",
                    "recommended_agents": 3,
                    "suggested_roles": ["implementer"],
                    "suggested_domains": ["api-design"],
                }),
            ]

            responses = []
            for vote_content in votes:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = vote_content
                responses.append(mock_response)

            triage_service.client.chat.completions.create = AsyncMock(
                side_effect=responses
            )

            with patch.object(triage_service, "_record_triage", new_callable=AsyncMock):
                should_escalate, consensus = await triage_service.triage(
                    "Implement user authentication with role-based access control"
                )

            assert should_escalate is True
            assert consensus.decision_votes == {"proceed": 1, "escalate": 2}
            assert 0.7 <= consensus.average_confidence <= 0.9
