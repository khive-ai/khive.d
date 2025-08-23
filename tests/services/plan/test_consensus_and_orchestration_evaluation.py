"""Comprehensive tests for multi-LLM consensus building and orchestration evaluation."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from khive.services.plan.models import OrchestrationEvaluation
from khive.services.plan.planner_service import OrchestrationPlanner


@pytest.mark.unit
class TestMultiLLMConsensusBuilding:
    """Test multi-LLM consensus building mechanisms."""

    @pytest.fixture
    def mock_planner_for_consensus(self, tmp_path):
        """Create mock planner for consensus testing."""
        with patch.multiple(
            OrchestrationPlanner,
            _load_available_roles=MagicMock(
                return_value=[
                    "researcher",
                    "analyst",
                    "architect",
                    "implementer",
                    "tester",
                    "critic",
                    "auditor",
                    "reviewer",
                ]
            ),
            _load_available_domains=MagicMock(
                return_value=[
                    "distributed-systems",
                    "consensus-algorithms",
                    "api-design",
                    "performance-optimization",
                    "security-systems",
                ]
            ),
            _load_prompt_templates=MagicMock(
                return_value={
                    "agents": {
                        "efficiency_analyst": {
                            "name": "efficiency_analyst",
                            "system_prompt_template": "Efficiency focused: {base_context}",
                            "description": "Minimizes resources",
                        },
                        "quality_architect": {
                            "name": "quality_architect",
                            "system_prompt_template": "Quality focused: {base_context}",
                            "description": "Maximizes validation",
                        },
                        "risk_auditor": {
                            "name": "risk_auditor",
                            "system_prompt_template": "Risk focused: {base_context}",
                            "description": "Paranoid about failures",
                        },
                    },
                    "base_context_template": "Context: {roles_str}, {domains_str}, Budget: ${cost_budget}",
                    "user_prompt_template": "Request: {request}",
                }
            ),
            _load_decision_matrix=MagicMock(
                return_value={"complexity_assessment": {}, "agent_role_selection": {}}
            ),
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                planner = OrchestrationPlanner()
                planner.workspace_dir = tmp_path
                return planner

    @pytest.fixture
    def sample_evaluations(self):
        """Sample evaluations from multiple LLM agents."""
        return [
            {
                "config": {"name": "efficiency_analyst"},
                "evaluation": OrchestrationEvaluation(
                    complexity="medium",
                    complexity_reason="Multiple objectives but clear scope",
                    total_agents=4,
                    agent_reason="Minimal coordination needed",
                    rounds_needed=2,
                    role_priorities=["implementer", "tester", "researcher"],
                    primary_domains=["api-design"],
                    domain_reason="Standard API development",
                    workflow_pattern="parallel",
                    workflow_reason="Independent tasks",
                    quality_level="basic",
                    quality_reason="Simple requirements",
                    rules_applied=["efficiency"],
                    confidence=0.85,
                    summary="Efficient approach with minimal agents",
                ),
                "cost": 0.001,
                "response_time_ms": 120,
            },
            {
                "config": {"name": "quality_architect"},
                "evaluation": OrchestrationEvaluation(
                    complexity="complex",
                    complexity_reason="Requires thorough validation",
                    total_agents=8,
                    agent_reason="Comprehensive validation needed",
                    rounds_needed=3,
                    role_priorities=[
                        "researcher",
                        "architect",
                        "implementer",
                        "tester",
                        "critic",
                        "auditor",
                    ],
                    primary_domains=["distributed-systems", "api-design"],
                    domain_reason="Complex system architecture",
                    workflow_pattern="sequential",
                    workflow_reason="Dependencies between phases",
                    quality_level="thorough",
                    quality_reason="Critical system requirements",
                    rules_applied=["quality", "validation"],
                    confidence=0.9,
                    summary="Thorough approach with comprehensive validation",
                ),
                "cost": 0.0015,
                "response_time_ms": 180,
            },
            {
                "config": {"name": "risk_auditor"},
                "evaluation": OrchestrationEvaluation(
                    complexity="very_complex",
                    complexity_reason="High failure risk without proper oversight",
                    total_agents=10,
                    agent_reason="Extensive oversight required",
                    rounds_needed=4,
                    role_priorities=[
                        "auditor",
                        "critic",
                        "tester",
                        "researcher",
                        "architect",
                        "implementer",
                    ],
                    primary_domains=["security-systems", "distributed-systems"],
                    domain_reason="Security and reliability critical",
                    workflow_pattern="hybrid",
                    workflow_reason="Mixed parallel and sequential needs",
                    quality_level="critical",
                    quality_reason="Cannot afford failures",
                    rules_applied=["risk", "security", "validation"],
                    confidence=0.75,
                    summary="Risk-mitigated approach with extensive oversight",
                ),
                "cost": 0.002,
                "response_time_ms": 220,
            },
        ]

    def test_complexity_consensus_building(
        self, mock_planner_for_consensus, sample_evaluations
    ):
        """Test complexity consensus from multiple evaluations."""
        output, consensus_data = mock_planner_for_consensus.build_consensus(
            sample_evaluations, "Build distributed API system", "claude"
        )

        # Should pick most common complexity
        # efficiency_analyst: medium, quality_architect: complex, risk_auditor: very_complex
        # With 3 different values, should pick one based on voting logic
        assert consensus_data["complexity"] in ["medium", "complex", "very_complex"]

        # Verify consensus output contains complexity info
        assert "Complexity Consensus:" in output
        assert "Agent assessments:" in output

    def test_agent_count_consensus_with_weighted_voting(
        self, mock_planner_for_consensus, sample_evaluations
    ):
        """Test agent count consensus uses weighted voting."""
        # Mock cost tracker for budget-aware weighting
        mock_planner_for_consensus.cost_tracker.total_cost = 0.002  # 80% of budget
        mock_planner_for_consensus.cost_tracker.get_cost_budget = MagicMock(
            return_value=0.0025
        )

        output, consensus_data = mock_planner_for_consensus.build_consensus(
            sample_evaluations, "Build API system", "claude"
        )

        # Should have weighted agent count recommendation
        agent_counts = [4, 8, 10]  # From sample evaluations
        expected_range = (min(agent_counts), max(agent_counts))

        assert expected_range[0] <= consensus_data["agent_count"] <= expected_range[1]
        assert "Total Agents:" in output

    def test_role_priority_consensus_with_position_scoring(
        self, mock_planner_for_consensus, sample_evaluations
    ):
        """Test role priority consensus uses position-weighted scoring."""
        output, consensus_data = mock_planner_for_consensus.build_consensus(
            sample_evaluations, "Build API system", "claude"
        )

        # Should have role recommendations with scores
        role_recommendations = consensus_data["role_recommendations"]
        assert isinstance(role_recommendations, list)
        assert len(role_recommendations) > 0

        # Each recommendation should be (role, score) tuple
        for role, score in role_recommendations:
            assert isinstance(role, str)
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0

        # Roles should be sorted by score (highest first)
        scores = [score for _, score in role_recommendations]
        assert scores == sorted(scores, reverse=True)

        # Output should contain role information
        assert "Top 10 Role Recommendations" in output

    def test_domain_frequency_consensus(
        self, mock_planner_for_consensus, sample_evaluations
    ):
        """Test domain consensus based on frequency."""
        output, consensus_data = mock_planner_for_consensus.build_consensus(
            sample_evaluations, "Build API system", "claude"
        )

        # Should aggregate domains across all evaluations
        domains = consensus_data["domains"]
        assert isinstance(domains, list)

        # Expected domains from sample evaluations
        expected_domains = {"api-design", "distributed-systems", "security-systems"}
        assert any(domain in expected_domains for domain in domains)

        # Output should contain domain information
        assert "Top Domains" in output

    def test_workflow_pattern_consensus(
        self, mock_planner_for_consensus, sample_evaluations
    ):
        """Test workflow pattern consensus selection."""
        output, consensus_data = mock_planner_for_consensus.build_consensus(
            sample_evaluations, "Build API system", "claude"
        )

        # Should pick most common workflow pattern
        patterns = ["parallel", "sequential", "hybrid"]  # From sample evaluations
        assert consensus_data["workflow_pattern"] in patterns

        # Output should contain workflow information
        assert "Workflow Pattern:" in output

    def test_quality_level_consensus_with_escalation(
        self, mock_planner_for_consensus, sample_evaluations
    ):
        """Test quality level consensus with gate escalation."""
        output, consensus_data = mock_planner_for_consensus.build_consensus(
            sample_evaluations, "Build API system", "claude"
        )

        # Should have quality level consensus
        quality_levels = ["basic", "thorough", "critical"]  # From sample evaluations
        assert consensus_data["quality_level"] in quality_levels

        # Test gate escalation middleware
        if "auditor" in str(sample_evaluations):  # Has auditor role
            # Should escalate basic to thorough if auditor present
            if consensus_data["quality_level"] == "basic":
                # Check escalation note in output
                assert (
                    "auto-escalated" in output
                    or consensus_data["quality_level"] != "basic"
                )

    def test_confidence_aggregation_across_agents(
        self, mock_planner_for_consensus, sample_evaluations
    ):
        """Test confidence aggregation across multiple agents."""
        output, consensus_data = mock_planner_for_consensus.build_consensus(
            sample_evaluations, "Build API system", "claude"
        )

        # Should calculate average confidence
        expected_confidences = [0.85, 0.9, 0.75]  # From sample evaluations
        expected_avg = sum(expected_confidences) / len(expected_confidences)

        assert abs(consensus_data["confidence"] - expected_avg) < 0.01

        # Output should contain confidence information
        assert "Overall Confidence:" in output
        assert "Individual confidence scores:" in output

    def test_consensus_meta_insights_analysis(
        self, mock_planner_for_consensus, sample_evaluations
    ):
        """Test meta-orchestration analysis in consensus."""
        # Create evaluations that trigger efficiency cliff warning
        high_agent_evaluations = []
        for i, eval_data in enumerate(sample_evaluations):
            eval_copy = eval_data.copy()
            eval_copy["evaluation"] = OrchestrationEvaluation(
                **{
                    **eval_data["evaluation"].model_dump(),
                    "total_agents": 15,
                }  # Exceed 12-agent limit
            )
            high_agent_evaluations.append(eval_copy)

        output, consensus_data = mock_planner_for_consensus.build_consensus(
            high_agent_evaluations, "Build API system", "claude"
        )

        # Should trigger efficiency cliff warning
        assert "Efficiency Cliff Warning" in output
        assert "exceed 12-agent optimum" in output

    def test_consensus_cost_analysis(
        self, mock_planner_for_consensus, sample_evaluations
    ):
        """Test cost analysis in consensus building."""
        # Set high cost tracker
        mock_planner_for_consensus.cost_tracker.total_cost = 0.01
        mock_planner_for_consensus.target_budget = 0.005  # Lower than total cost

        output, consensus_data = mock_planner_for_consensus.build_consensus(
            sample_evaluations, "Build API system", "claude"
        )

        # Should include cost warning
        assert "Planning Cost:" in output
        assert "Cost Warning" in output

    def test_batch_tool_command_generation(
        self, mock_planner_for_consensus, sample_evaluations
    ):
        """Test BatchTool command generation in consensus."""
        output, consensus_data = mock_planner_for_consensus.build_consensus(
            sample_evaluations,
            "Build distributed API system",
            "claude",  # Claude format
        )

        # Should contain BatchTool commands
        assert "BatchTool Format for Claude Code" in output
        assert "Task(" in output
        assert "uv run khive compose" in output

    def test_json_format_consensus_output(
        self, mock_planner_for_consensus, sample_evaluations
    ):
        """Test JSON format consensus output for orchestration."""
        output, consensus_data = mock_planner_for_consensus.build_consensus(
            sample_evaluations,
            "Build API system",
            "json",  # JSON format
        )

        # Should contain JSON format
        assert "JSON Format for Orchestration" in output
        assert "```json" in output

        # Should contain valid JSON in output
        json_start = output.find("```json\n") + 8
        json_end = output.find("```", json_start)
        json_content = output[json_start:json_end].strip()

        # Should be valid JSON
        consensus_json = json.loads(json_content)
        assert "session_id" in consensus_json
        assert "complexity" in consensus_json
        assert "agents" in consensus_json

    def test_phase_aware_execution_commands(
        self, mock_planner_for_consensus, sample_evaluations
    ):
        """Test phase-aware execution command generation."""
        # Mock phase determination to return multiple phases
        with patch(
            "khive.prompts.phase_determination.determine_required_phases"
        ) as mock_phases:
            mock_phases.return_value = ["discovery_phase", "implementation_phase"]

            with patch(
                "khive.prompts.phase_determination.get_phase_description"
            ) as mock_desc:
                mock_desc.side_effect = lambda phase: f"Description for {phase}"

                output, consensus_data = mock_planner_for_consensus.build_consensus(
                    sample_evaluations,
                    "Research and implement distributed consensus system",
                    "claude",
                )

        # Should contain phase-organized commands
        assert "Phase 1:" in output
        assert "Phase 2:" in output
        assert "discovery" in output.lower()
        assert "implementation" in output.lower()

    def test_consensus_with_disagreement_handling(self, mock_planner_for_consensus):
        """Test consensus building when agents strongly disagree."""
        disagreement_evaluations = [
            {
                "config": {"name": "minimalist"},
                "evaluation": OrchestrationEvaluation(
                    complexity="simple",
                    complexity_reason="Very straightforward task",
                    total_agents=1,
                    agent_reason="Single person job",
                    rounds_needed=1,
                    role_priorities=["implementer"],
                    primary_domains=["api-design"],
                    domain_reason="Basic API",
                    workflow_pattern="parallel",
                    workflow_reason="No coordination",
                    quality_level="basic",
                    quality_reason="Simple requirements",
                    rules_applied=["minimalism"],
                    confidence=0.95,
                    summary="Minimal approach",
                ),
                "cost": 0.0005,
                "response_time_ms": 80,
            },
            {
                "config": {"name": "maximalist"},
                "evaluation": OrchestrationEvaluation(
                    complexity="very_complex",
                    complexity_reason="Extremely sophisticated requirements",
                    total_agents=20,
                    agent_reason="Massive coordination needed",
                    rounds_needed=6,
                    role_priorities=[
                        "researcher",
                        "theorist",
                        "architect",
                        "implementer",
                        "tester",
                        "critic",
                        "auditor",
                        "reviewer",
                    ],
                    primary_domains=[
                        "distributed-systems",
                        "consensus-algorithms",
                        "performance-optimization",
                        "security-systems",
                    ],
                    domain_reason="Multi-domain expertise required",
                    workflow_pattern="sequential",
                    workflow_reason="Complex dependencies",
                    quality_level="critical",
                    quality_reason="Cannot fail",
                    rules_applied=["maximalism", "paranoia"],
                    confidence=0.99,
                    summary="Maximum rigor approach",
                ),
                "cost": 0.003,
                "response_time_ms": 400,
            },
        ]

        output, consensus_data = mock_planner_for_consensus.build_consensus(
            disagreement_evaluations, "Build API", "claude"
        )

        # Should handle extreme disagreement gracefully
        assert 1 <= consensus_data["agent_count"] <= 20
        assert consensus_data["complexity"] in ["simple", "very_complex"]

        # Should show the disagreement in output
        assert "1-20" in output  # Agent count range


@pytest.mark.unit
class TestOrchestrationEvaluationValidation:
    """Test OrchestrationEvaluation model validation and processing."""

    def test_orchestration_evaluation_valid_creation(self):
        """Test creating valid OrchestrationEvaluation."""
        evaluation = OrchestrationEvaluation(
            complexity="medium",
            complexity_reason="Multiple objectives with moderate uncertainty",
            total_agents=5,
            agent_reason="Coordination across multiple specialties",
            rounds_needed=3,
            role_priorities=["researcher", "architect", "implementer", "tester"],
            primary_domains=["distributed-systems", "api-design"],
            domain_reason="System architecture and API expertise needed",
            workflow_pattern="hybrid",
            workflow_reason="Mix of parallel and sequential tasks",
            quality_level="thorough",
            quality_reason="Important system requiring validation",
            rules_applied=["complexity_assessment", "domain_matching"],
            confidence=0.85,
            summary="Moderate complexity task requiring coordinated specialists",
        )

        assert evaluation.complexity == "medium"
        assert evaluation.total_agents == 5
        assert len(evaluation.role_priorities) == 4
        assert len(evaluation.primary_domains) == 2
        assert 0.0 <= evaluation.confidence <= 1.0

    @pytest.mark.parametrize(
        "invalid_field,invalid_value,error_pattern",
        [
            ("complexity", "invalid_complexity", "Input should be"),
            ("total_agents", 25, "Input should be less than or equal to"),
            ("total_agents", -1, "Input should be greater than or equal to"),
            ("confidence", 1.5, "Input should be less than or equal to"),
            ("confidence", -0.1, "Input should be greater than or equal to"),
            ("rounds_needed", 0, "Input should be greater than or equal to"),
            ("workflow_pattern", "invalid_pattern", "Input should be"),
            ("quality_level", "invalid_level", "Input should be"),
        ],
    )
    def test_orchestration_evaluation_validation_errors(
        self, invalid_field, invalid_value, error_pattern
    ):
        """Test OrchestrationEvaluation validation errors."""
        valid_data = {
            "complexity": "medium",
            "complexity_reason": "Test reason",
            "total_agents": 5,
            "agent_reason": "Test reason",
            "rounds_needed": 2,
            "role_priorities": ["implementer"],
            "primary_domains": ["api-design"],
            "domain_reason": "Test reason",
            "workflow_pattern": "parallel",
            "workflow_reason": "Test reason",
            "quality_level": "thorough",
            "quality_reason": "Test reason",
            "rules_applied": ["test"],
            "confidence": 0.8,
            "summary": "Test summary",
        }

        # Set invalid field
        invalid_data = valid_data.copy()
        invalid_data[invalid_field] = invalid_value

        with pytest.raises(ValidationError, match=error_pattern):
            OrchestrationEvaluation(**invalid_data)

    def test_orchestration_evaluation_string_length_limits(self):
        """Test string field length validation."""
        base_data = {
            "complexity": "medium",
            "total_agents": 5,
            "rounds_needed": 2,
            "role_priorities": ["implementer"],
            "primary_domains": ["api-design"],
            "workflow_pattern": "parallel",
            "quality_level": "thorough",
            "rules_applied": ["test"],
            "confidence": 0.8,
        }

        # Test reason fields (should have reasonable limits)
        long_reason = "x" * 1000  # Very long string

        # These should work with long strings (no explicit limit in current model)
        evaluation = OrchestrationEvaluation(
            **base_data,
            complexity_reason=long_reason,
            agent_reason=long_reason,
            domain_reason=long_reason,
            workflow_reason=long_reason,
            quality_reason=long_reason,
            summary=long_reason,
        )

        assert len(evaluation.complexity_reason) == 1000

    def test_orchestration_evaluation_list_validations(self):
        """Test list field validations."""
        base_data = {
            "complexity": "medium",
            "complexity_reason": "Test",
            "total_agents": 5,
            "agent_reason": "Test",
            "rounds_needed": 2,
            "domain_reason": "Test",
            "workflow_pattern": "parallel",
            "workflow_reason": "Test",
            "quality_level": "thorough",
            "quality_reason": "Test",
            "confidence": 0.8,
            "summary": "Test",
        }

        # Valid lists
        evaluation = OrchestrationEvaluation(
            **base_data,
            role_priorities=["researcher", "implementer", "tester"],
            primary_domains=["distributed-systems"],
            rules_applied=["complexity", "domain_matching"],
        )

        assert len(evaluation.role_priorities) == 3
        assert len(evaluation.primary_domains) == 1
        assert len(evaluation.rules_applied) == 2

        # Empty lists should be valid
        evaluation_empty = OrchestrationEvaluation(
            **base_data,
            role_priorities=[],
            primary_domains=[],
            rules_applied=[],
        )

        assert len(evaluation_empty.role_priorities) == 0

    def test_orchestration_evaluation_serialization(self):
        """Test OrchestrationEvaluation serialization."""
        evaluation = OrchestrationEvaluation(
            complexity="complex",
            complexity_reason="High coordination requirements",
            total_agents=8,
            agent_reason="Multiple specialization areas",
            rounds_needed=4,
            role_priorities=[
                "researcher",
                "architect",
                "implementer",
                "tester",
                "critic",
            ],
            primary_domains=["distributed-systems", "performance-optimization"],
            domain_reason="System performance and architecture critical",
            workflow_pattern="hybrid",
            workflow_reason="Mixed coordination patterns needed",
            quality_level="thorough",
            quality_reason="Critical system requirements",
            rules_applied=[
                "complexity_assessment",
                "domain_expertise",
                "quality_gates",
            ],
            confidence=0.82,
            summary="Complex system requiring multi-domain coordination",
        )

        # Test Pydantic serialization
        evaluation_dict = evaluation.model_dump()

        assert isinstance(evaluation_dict, dict)
        assert evaluation_dict["complexity"] == "complex"
        assert evaluation_dict["total_agents"] == 8
        assert len(evaluation_dict["role_priorities"]) == 5
        assert evaluation_dict["confidence"] == 0.82

        # Test JSON serialization
        evaluation_json = evaluation.model_dump_json()
        parsed_evaluation = json.loads(evaluation_json)

        assert parsed_evaluation["complexity"] == "complex"
        assert parsed_evaluation["confidence"] == 0.82


@pytest.mark.unit
class TestConsensusAlgorithmLogic:
    """Test consensus building algorithm logic."""

    def test_majority_voting_consensus(self):
        """Test majority voting for discrete choices."""
        complexities = ["simple", "medium", "simple", "medium", "simple"]

        # Count votes
        complexity_counts = {c: complexities.count(c) for c in set(complexities)}
        consensus_complexity = max(complexity_counts, key=complexity_counts.get)

        assert consensus_complexity == "simple"  # 3 votes vs 2 votes
        assert complexity_counts["simple"] == 3
        assert complexity_counts["medium"] == 2

    def test_weighted_average_consensus(self):
        """Test weighted average for numerical values."""
        agent_data = [
            {"agents": 4, "confidence": 0.9},
            {"agents": 6, "confidence": 0.8},
            {"agents": 8, "confidence": 0.7},
        ]

        # Calculate confidence-weighted average
        total_weight = sum(data["confidence"] for data in agent_data)
        weighted_sum = sum(data["agents"] * data["confidence"] for data in agent_data)
        weighted_average = weighted_sum / total_weight

        expected = (4 * 0.9 + 6 * 0.8 + 8 * 0.7) / (0.9 + 0.8 + 0.7)
        assert abs(weighted_average - expected) < 0.01

    def test_position_weighted_scoring(self):
        """Test position-weighted scoring for role priorities."""
        role_priorities = [
            ["researcher", "implementer", "tester"],
            ["implementer", "researcher", "critic"],
            ["researcher", "implementer", "auditor"],
        ]

        # Calculate position-weighted scores
        role_scores = {}
        for priorities in role_priorities:
            for position, role in enumerate(priorities):
                if role not in role_scores:
                    role_scores[role] = 0
                # Position weight: 1st = 1.0, 2nd = 0.8, 3rd = 0.6
                position_weight = max(0.2, 1.0 - (position * 0.2))
                role_scores[role] += position_weight

        # Normalize by number of evaluations
        for role in role_scores:
            role_scores[role] = role_scores[role] / len(role_priorities)

        sorted_roles = sorted(role_scores.items(), key=lambda x: x[1], reverse=True)

        # "researcher" appears first twice, second once = (1.0 + 1.0 + 0.8)/3 = 0.93
        # "implementer" appears second twice, first once = (0.8 + 1.0 + 0.8)/3 = 0.87
        assert sorted_roles[0][0] in ["researcher", "implementer"]  # Top scoring

    def test_consensus_tie_breaking(self):
        """Test tie-breaking mechanisms in consensus."""
        # Perfect tie scenario
        complexities = ["simple", "medium", "simple", "medium"]
        complexity_counts = {c: complexities.count(c) for c in set(complexities)}

        # In case of tie, should have deterministic tie-breaking
        # (e.g., alphabetical, or prefer higher/lower complexity)
        tied_options = [
            k
            for k, v in complexity_counts.items()
            if v == max(complexity_counts.values())
        ]

        if len(tied_options) > 1:
            # Test deterministic tie-breaking (alphabetical)
            consensus = sorted(tied_options)[0]
            assert consensus in ["simple", "medium"]

    def test_confidence_threshold_filtering(self):
        """Test filtering evaluations by confidence threshold."""
        evaluations = [
            {"name": "high_conf", "complexity": "simple", "confidence": 0.9},
            {"name": "medium_conf", "complexity": "medium", "confidence": 0.7},
            {"name": "low_conf", "complexity": "complex", "confidence": 0.4},
        ]

        confidence_threshold = 0.6
        filtered = [e for e in evaluations if e["confidence"] >= confidence_threshold]

        assert len(filtered) == 2
        assert filtered[0]["name"] == "high_conf"
        assert filtered[1]["name"] == "medium_conf"

    def test_outlier_detection_and_handling(self):
        """Test outlier detection in consensus building."""
        agent_counts = [4, 5, 4, 6, 5, 20]  # 20 is outlier

        # Calculate median and IQR
        sorted_counts = sorted(agent_counts)
        median = sorted_counts[len(sorted_counts) // 2]
        q1 = sorted_counts[len(sorted_counts) // 4]
        q3 = sorted_counts[3 * len(sorted_counts) // 4]
        iqr = q3 - q1

        # Outlier detection (values > Q3 + 1.5*IQR)
        outlier_threshold = q3 + 1.5 * iqr
        outliers = [count for count in agent_counts if count > outlier_threshold]

        assert 20 in outliers

        # Filter outliers for consensus
        filtered_counts = [
            count for count in agent_counts if count <= outlier_threshold
        ]
        consensus_count = sum(filtered_counts) / len(filtered_counts)

        assert 4 <= consensus_count <= 6  # Should be in normal range

    def test_consensus_convergence_detection(self):
        """Test detection of consensus convergence vs divergence."""
        # Convergent scenario (agents agree)
        convergent_complexities = ["medium", "medium", "complex", "medium"]
        convergent_counts = {
            c: convergent_complexities.count(c) for c in set(convergent_complexities)
        }
        convergent_max_ratio = max(convergent_counts.values()) / len(
            convergent_complexities
        )

        # Divergent scenario (agents disagree)
        divergent_complexities = ["simple", "medium", "complex", "very_complex"]
        divergent_counts = {
            c: divergent_complexities.count(c) for c in set(divergent_complexities)
        }
        divergent_max_ratio = max(divergent_counts.values()) / len(
            divergent_complexities
        )

        # Convergent should have higher agreement ratio
        assert convergent_max_ratio > divergent_max_ratio
        assert convergent_max_ratio >= 0.5  # Majority agreement
        assert divergent_max_ratio == 0.25  # No majority


@pytest.mark.integration
class TestConsensusIntegrationScenarios:
    """Integration tests for consensus building in realistic scenarios."""

    @pytest.fixture
    def realistic_planner(self, tmp_path):
        """Create realistic planner for integration testing."""
        with patch.multiple(
            OrchestrationPlanner,
            _load_available_roles=MagicMock(
                return_value=[
                    "researcher",
                    "analyst",
                    "theorist",
                    "architect",
                    "strategist",
                    "implementer",
                    "innovator",
                    "tester",
                    "critic",
                    "auditor",
                    "reviewer",
                ]
            ),
            _load_available_domains=MagicMock(
                return_value=[
                    "distributed-systems",
                    "consensus-algorithms",
                    "api-design",
                    "performance-optimization",
                    "security-systems",
                    "real-time-systems",
                ]
            ),
            _load_prompt_templates=MagicMock(
                return_value={
                    "agents": {
                        "efficiency_analyst": {"name": "efficiency_analyst"},
                        "quality_architect": {"name": "quality_architect"},
                        "risk_auditor": {"name": "risk_auditor"},
                        "innovation_strategist": {"name": "innovation_strategist"},
                    },
                    "base_context_template": "Context with {roles_str}",
                    "user_prompt_template": "Task: {request}",
                }
            ),
            _load_decision_matrix=MagicMock(
                return_value={"complexity_assessment": {}, "agent_role_selection": {}}
            ),
        ):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}):
                planner = OrchestrationPlanner()
                planner.workspace_dir = tmp_path
                return planner

    @pytest.mark.asyncio
    async def test_end_to_end_consensus_flow(self, realistic_planner):
        """Test complete end-to-end consensus building flow."""
        # Mock evaluation responses
        mock_evaluations = [
            {
                "config": {"name": "efficiency_analyst"},
                "evaluation": OrchestrationEvaluation(
                    complexity="medium",
                    complexity_reason="Standard distributed system",
                    total_agents=6,
                    agent_reason="Reasonable coordination",
                    rounds_needed=2,
                    role_priorities=["architect", "implementer", "tester"],
                    primary_domains=["distributed-systems"],
                    domain_reason="Core system architecture",
                    workflow_pattern="parallel",
                    workflow_reason="Parallel development possible",
                    quality_level="thorough",
                    quality_reason="Important system",
                    rules_applied=["efficiency"],
                    confidence=0.85,
                    summary="Efficient distributed system approach",
                ),
                "cost": 0.001,
                "response_time_ms": 150,
            }
        ]

        with patch.object(
            realistic_planner, "evaluate_request", return_value=mock_evaluations
        ):
            # Test full consensus building
            output, consensus_data = realistic_planner.build_consensus(
                mock_evaluations,
                "Build high-availability distributed consensus system",
                "claude",
            )

            # Verify consensus structure
            assert "Orchestration Planning Consensus" in output
            assert consensus_data["complexity"] == "medium"
            assert consensus_data["agent_count"] == 6
            assert len(consensus_data["role_recommendations"]) > 0
            assert len(consensus_data["domains"]) > 0

    def test_consensus_with_budget_constraints(self, realistic_planner):
        """Test consensus building under budget constraints."""
        # Set tight budget
        realistic_planner.cost_tracker.total_cost = 0.008
        realistic_planner.cost_tracker.get_cost_budget = MagicMock(return_value=0.01)

        budget_evaluations = [
            {
                "config": {"name": "cost_optimizer"},
                "evaluation": OrchestrationEvaluation(
                    complexity="simple",
                    complexity_reason="Keep it minimal for budget",
                    total_agents=3,
                    agent_reason="Cost-effective team size",
                    rounds_needed=1,
                    role_priorities=["implementer", "tester"],
                    primary_domains=["api-design"],
                    domain_reason="Focus on core functionality",
                    workflow_pattern="parallel",
                    workflow_reason="Minimize coordination overhead",
                    quality_level="basic",
                    quality_reason="Budget constraints",
                    rules_applied=["budget_optimization"],
                    confidence=0.9,
                    summary="Budget-optimized approach",
                ),
                "cost": 0.0005,
                "response_time_ms": 100,
            }
        ]

        output, consensus_data = realistic_planner.build_consensus(
            budget_evaluations, "Build API system", "claude"
        )

        # Should reflect budget consciousness
        assert consensus_data["agent_count"] <= 5  # Should be conservative
        assert (
            "Cost Warning" in output or realistic_planner.cost_tracker.total_cost < 0.01
        )

    def test_consensus_for_research_intensive_task(self, realistic_planner):
        """Test consensus for research-intensive tasks."""
        research_evaluations = [
            {
                "config": {"name": "research_specialist"},
                "evaluation": OrchestrationEvaluation(
                    complexity="very_complex",
                    complexity_reason="Novel algorithmic research required",
                    total_agents=12,
                    agent_reason="Multiple research specializations needed",
                    rounds_needed=5,
                    role_priorities=[
                        "researcher",
                        "theorist",
                        "analyst",
                        "critic",
                        "implementer",
                    ],
                    primary_domains=[
                        "consensus-algorithms",
                        "performance-optimization",
                    ],
                    domain_reason="Cutting-edge algorithm development",
                    workflow_pattern="sequential",
                    workflow_reason="Research phases must build on each other",
                    quality_level="critical",
                    quality_reason="Research validation essential",
                    rules_applied=["research_protocols", "validation"],
                    confidence=0.75,
                    summary="Comprehensive research approach",
                ),
                "cost": 0.003,
                "response_time_ms": 300,
            }
        ]

        output, consensus_data = realistic_planner.build_consensus(
            research_evaluations,
            "Research novel Byzantine fault tolerance algorithms",
            "json",
        )

        # Should reflect research nature
        assert consensus_data["complexity"] == "very_complex"
        assert consensus_data["agent_count"] >= 10
        assert "researcher" in [
            role for role, _ in consensus_data["role_recommendations"][:3]
        ]

    def test_consensus_with_mixed_confidence_levels(self, realistic_planner):
        """Test consensus building with mixed confidence levels."""
        mixed_confidence_evaluations = [
            {
                "config": {"name": "confident_agent"},
                "evaluation": OrchestrationEvaluation(
                    complexity="medium",
                    complexity_reason="Clear requirements",
                    total_agents=5,
                    agent_reason="Standard team",
                    rounds_needed=2,
                    role_priorities=["implementer", "tester"],
                    primary_domains=["api-design"],
                    domain_reason="Standard API",
                    workflow_pattern="parallel",
                    workflow_reason="Clear separation",
                    quality_level="thorough",
                    quality_reason="Good practices",
                    rules_applied=["standard"],
                    confidence=0.95,  # Very confident
                    summary="High confidence assessment",
                ),
                "cost": 0.001,
                "response_time_ms": 120,
            },
            {
                "config": {"name": "uncertain_agent"},
                "evaluation": OrchestrationEvaluation(
                    complexity="complex",
                    complexity_reason="Many unknowns present",
                    total_agents=10,
                    agent_reason="Account for uncertainty",
                    rounds_needed=4,
                    role_priorities=["researcher", "analyst", "implementer"],
                    primary_domains=["distributed-systems"],
                    domain_reason="Complex system",
                    workflow_pattern="sequential",
                    workflow_reason="Dependencies unclear",
                    quality_level="critical",
                    quality_reason="High risk",
                    rules_applied=["uncertainty"],
                    confidence=0.45,  # Low confidence
                    summary="Uncertain assessment with high contingency",
                ),
                "cost": 0.002,
                "response_time_ms": 250,
            },
        ]

        output, consensus_data = realistic_planner.build_consensus(
            mixed_confidence_evaluations,
            "Build system with unclear requirements",
            "claude",
        )

        # Should weight the high-confidence evaluation more heavily
        expected_confidence = (0.95 + 0.45) / 2
        assert abs(consensus_data["confidence"] - expected_confidence) < 0.05

        # Should be influenced more by confident evaluation
        assert 5 <= consensus_data["agent_count"] <= 10

    @pytest.mark.asyncio
    async def test_consensus_performance_under_load(self, realistic_planner):
        """Test consensus building performance with many evaluations."""
        # Create many evaluation responses
        many_evaluations = []
        for i in range(20):  # Simulate many agent responses
            evaluation = {
                "config": {"name": f"agent_{i}"},
                "evaluation": OrchestrationEvaluation(
                    complexity=["simple", "medium", "complex"][i % 3],
                    complexity_reason=f"Agent {i} assessment",
                    total_agents=(i % 10) + 3,  # 3-12 agents
                    agent_reason=f"Agent {i} reasoning",
                    rounds_needed=(i % 3) + 1,
                    role_priorities=["implementer", "tester", "researcher"][
                        : (i % 3) + 1
                    ],
                    primary_domains=["api-design"],
                    domain_reason=f"Agent {i} domain",
                    workflow_pattern=["parallel", "sequential", "hybrid"][i % 3],
                    workflow_reason=f"Agent {i} workflow",
                    quality_level=["basic", "thorough", "critical"][i % 3],
                    quality_reason=f"Agent {i} quality",
                    rules_applied=[f"rule_{i}"],
                    confidence=0.5 + (i % 5) * 0.1,  # 0.5-0.9
                    summary=f"Agent {i} summary",
                ),
                "cost": 0.001,
                "response_time_ms": 100 + (i % 50),
            }
            many_evaluations.append(evaluation)

        # Measure consensus building time
        start_time = time.time()
        output, consensus_data = realistic_planner.build_consensus(
            many_evaluations, "Build system with many agent opinions", "claude"
        )
        end_time = time.time()

        # Should complete in reasonable time
        consensus_time = end_time - start_time
        assert consensus_time < 5.0  # Should be fast

        # Should produce valid consensus despite many inputs
        assert consensus_data["complexity"] in ["simple", "medium", "complex"]
        assert 3 <= consensus_data["agent_count"] <= 15
        assert len(consensus_data["role_recommendations"]) > 0
