"""Comprehensive validation tests for Composition Service models.

This module provides systematic validation testing for:
- ComposerRequest model validation and role/domain combinations
- ComposerResponse model validation and confidence ranges
- DomainExpertise model validation and expertise structure
- AgentCompositionRequest model validation and security constraints
- Cross-model composition consistency validation
"""

from typing import Any

import pytest
from pydantic import ValidationError

from khive.services.composition.parts import (
    AgentCompositionRequest,
    ComposerRequest,
    ComposerResponse,
    DomainExpertise,
)
from tests.validation.pydantic_validators import BaseValidationPattern

# ============================================================================
# ComposerRequest Model Validation
# ============================================================================


class ComposerRequestValidator(BaseValidationPattern):
    """Validation patterns for ComposerRequest model."""

    # Common roles and domains for testing
    VALID_ROLES = [
        "researcher",
        "analyst",
        "architect",
        "implementer",
        "tester",
        "reviewer",
        "critic",
        "innovator",
    ]

    VALID_DOMAINS = [
        "distributed-systems",
        "software-architecture",
        "async-programming",
        "memory-systems",
        "agentic-systems",
        "graph-theory",
    ]

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid ComposerRequest data."""
        data = {
            "role": "researcher",
            "domains": "distributed-systems,async-programming",
            "context": "Research distributed system patterns for high-throughput data processing",
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        # Role is required
        cls.assert_invalid_model(
            ComposerRequest,
            {"domains": "test-domain", "context": "test context"},
            "role",
        )

        # Minimal valid request (only role)
        minimal_request = {"role": "researcher"}
        cls.assert_valid_model(ComposerRequest, minimal_request)

    @classmethod
    def test_field_defaults(cls):
        """Test field default values."""
        minimal_request = ComposerRequest(role="architect")

        assert minimal_request.role == "architect"  # AgentRole is a string literal
        assert minimal_request.domains is None
        assert minimal_request.context is None

    @classmethod
    def test_role_validation(cls):
        """Test role field validation."""
        # Valid roles (AgentRole enum values)
        for role in cls.VALID_ROLES:
            data = cls.create_valid_data(role=role)
            cls.assert_valid_model(ComposerRequest, data)

        # Invalid role should fail enum validation
        cls.assert_invalid_model(
            ComposerRequest, cls.create_valid_data(role="invalid_role"), "role"
        )

        # Empty role should fail
        cls.assert_invalid_model(
            ComposerRequest, cls.create_valid_data(role=""), "role"
        )

    @classmethod
    def test_domains_validation(cls):
        """Test domains field validation."""
        # Valid domain formats
        valid_domain_strings = [
            None,  # optional field
            "",  # empty string
            "single-domain",
            "domain1,domain2",
            "distributed-systems,async-programming,memory-systems",
            "domain-with-dashes",
            "domain_with_underscores",
        ]

        for domains in valid_domain_strings:
            data = cls.create_valid_data(domains=domains)
            cls.assert_valid_model(ComposerRequest, data)

        # Very long domain string
        long_domains = ",".join([f"domain{i}" for i in range(50)])
        data = cls.create_valid_data(domains=long_domains)
        cls.assert_valid_model(ComposerRequest, data)

    @classmethod
    def test_context_validation(cls):
        """Test context field validation."""
        # Valid context formats
        valid_contexts = [
            None,  # optional field
            "",  # empty string
            "Simple context",
            "Complex context with detailed requirements and specifications",
            "Multi-line\ncontext\nwith\nbreaks",
            "Context with special chars: @#$%^&*()[]{}",
            "Very long context " * 100,  # stress test
        ]

        for context in valid_contexts:
            data = cls.create_valid_data(context=context)
            cls.assert_valid_model(ComposerRequest, data)

    @classmethod
    def test_role_domain_combinations(cls):
        """Test common role-domain combinations."""
        # Realistic combinations
        combinations = [
            ("researcher", "distributed-systems"),
            ("architect", "software-architecture,microkernel-architecture"),
            ("implementer", "async-programming,rust-performance"),
            ("tester", "software-architecture,testing-frameworks"),
            ("analyst", "graph-theory,category-theory"),
            ("critic", "security-analysis,code-review"),
        ]

        for role, domains in combinations:
            data = cls.create_valid_data(role=role, domains=domains)
            cls.assert_valid_model(ComposerRequest, data)


# ============================================================================
# DomainExpertise Model Validation
# ============================================================================


class DomainExpertiseValidator(BaseValidationPattern):
    """Validation patterns for DomainExpertise model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid DomainExpertise data."""
        data = {
            "domain_id": "distributed-systems",
            "knowledge_patterns": {
                "consensus_algorithms": ["raft", "paxos", "pbft"],
                "consistency_models": ["strong", "eventual", "causal"],
            },
            "decision_rules": {
                "performance_threshold": 0.95,
                "availability_requirement": "99.9%",
                "scalability_target": "horizontal",
            },
            "specialized_tools": ["etcd", "consul", "zookeeper", "kubernetes"],
            "confidence_thresholds": {
                "pattern_recognition": 0.8,
                "solution_recommendation": 0.7,
                "risk_assessment": 0.9,
            },
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        # Only domain_id is required
        minimal_expertise = {"domain_id": "test-domain"}
        cls.assert_valid_model(DomainExpertise, minimal_expertise)

        # Missing domain_id should fail
        cls.assert_invalid_model(DomainExpertise, {}, "domain_id")

    @classmethod
    def test_field_defaults(cls):
        """Test field default values."""
        minimal_expertise = DomainExpertise(domain_id="test-domain")

        assert minimal_expertise.domain_id == "test-domain"
        assert minimal_expertise.knowledge_patterns == {}
        assert minimal_expertise.decision_rules == {}
        assert minimal_expertise.specialized_tools == []
        assert minimal_expertise.confidence_thresholds == {}

    @classmethod
    def test_domain_id_validation(cls):
        """Test domain_id field validation."""
        # Valid domain IDs
        valid_domain_ids = [
            "simple-domain",
            "distributed-systems",
            "software_architecture",
            "async_programming",
            "domain123",
            "very-long-domain-name-with-many-parts",
        ]

        for domain_id in valid_domain_ids:
            data = cls.create_valid_data(domain_id=domain_id)
            cls.assert_valid_model(DomainExpertise, data)

        # Empty domain_id should be invalid
        cls.assert_invalid_model(
            DomainExpertise, cls.create_valid_data(domain_id=""), "domain_id"
        )

    @classmethod
    def test_knowledge_patterns_validation(cls):
        """Test knowledge_patterns field validation."""
        # Various knowledge pattern structures
        valid_patterns = [
            {},  # empty
            {"simple": "pattern"},
            {"algorithms": ["algo1", "algo2"], "principles": {"principle1": "value1"}},
            {"complex": {"nested": {"structure": ["with", "multiple", "levels"]}}},
        ]

        for patterns in valid_patterns:
            data = cls.create_valid_data(knowledge_patterns=patterns)
            cls.assert_valid_model(DomainExpertise, data)

    @classmethod
    def test_decision_rules_validation(cls):
        """Test decision_rules field validation."""
        # Various decision rule structures
        valid_rules = [
            {},  # empty
            {"threshold": 0.5},
            {"performance": 0.95, "reliability": "high", "cost": "medium"},
            {
                "complex_rules": {
                    "conditions": ["condition1", "condition2"],
                    "actions": {"action1": "value1"},
                }
            },
        ]

        for rules in valid_rules:
            data = cls.create_valid_data(decision_rules=rules)
            cls.assert_valid_model(DomainExpertise, data)

    @classmethod
    def test_specialized_tools_validation(cls):
        """Test specialized_tools field validation."""
        # Various tool list structures
        valid_tool_lists = [
            [],  # empty
            ["tool1"],
            ["tool1", "tool2", "tool3"],
            ["very-long-tool-name-with-version-info-v1.2.3"],
        ]

        for tools in valid_tool_lists:
            data = cls.create_valid_data(specialized_tools=tools)
            cls.assert_valid_model(DomainExpertise, data)

    @classmethod
    def test_confidence_thresholds_validation(cls):
        """Test confidence_thresholds field validation."""
        # Various threshold structures
        valid_thresholds = [
            {},  # empty
            {"general": 0.8},
            {
                "pattern_recognition": 0.7,
                "solution_generation": 0.8,
                "risk_assessment": 0.9,
            },
            {"category1": {"subcategory": 0.75}, "category2": 0.85},
        ]

        for thresholds in valid_thresholds:
            data = cls.create_valid_data(confidence_thresholds=thresholds)
            cls.assert_valid_model(DomainExpertise, data)


# ============================================================================
# ComposerResponse Model Validation
# ============================================================================


class ComposerResponseValidator(BaseValidationPattern):
    """Validation patterns for ComposerResponse model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid ComposerResponse data."""
        data = {
            "success": True,
            "summary": "Successfully composed distributed systems researcher agent",
            "agent_id": "researcher_distributed_systems_001",
            "role": "researcher",
            "domains": ["distributed-systems", "consensus-algorithms"],
            "system_prompt": "You are a specialized researcher agent with expertise in distributed systems...",
            "capabilities": [
                "distributed_system_analysis",
                "consensus_algorithm_research",
                "scalability_assessment",
            ],
            "tools": ["Read", "Grep", "WebSearch", "mcp__knowledge__query"],
            "domain_expertise": [
                {
                    "domain_id": "distributed-systems",
                    "knowledge_patterns": {"consensus": ["raft", "paxos"]},
                    "decision_rules": {"reliability": "high"},
                    "specialized_tools": ["etcd"],
                    "confidence_thresholds": {"analysis": 0.8},
                }
            ],
            "confidence": 0.85,
            "error": None,
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        required_fields = [
            "success",
            "summary",
            "agent_id",
            "role",
            "system_prompt",
            "confidence",
        ]

        for field in required_fields:
            incomplete_data = cls.create_valid_data()
            del incomplete_data[field]
            cls.assert_invalid_model(ComposerResponse, incomplete_data, field)

    @classmethod
    def test_field_defaults(cls):
        """Test field default values."""
        minimal_response = ComposerResponse(
            success=True,
            summary="Test summary",
            agent_id="test_agent_001",
            role="researcher",
            system_prompt="Test system prompt",
            confidence=0.8,
        )

        assert minimal_response.domains == []
        assert minimal_response.capabilities == []
        assert minimal_response.tools == []
        assert minimal_response.domain_expertise == []
        assert minimal_response.error is None

    @classmethod
    def test_success_validation(cls):
        """Test success field validation."""
        # Valid boolean values
        for success in [True, False]:
            data = cls.create_valid_data(success=success)
            cls.assert_valid_model(ComposerResponse, data)

    @classmethod
    def test_summary_validation(cls):
        """Test summary field validation."""
        # Valid summaries
        valid_summaries = [
            "Short summary",
            "Detailed summary with comprehensive information about the agent composition",
            "Summary with special chars: @#$%^&*()",
        ]

        for summary in valid_summaries:
            data = cls.create_valid_data(summary=summary)
            cls.assert_valid_model(ComposerResponse, data)

        # Empty summary should be invalid
        cls.assert_invalid_model(
            ComposerResponse, cls.create_valid_data(summary=""), "summary"
        )

    @classmethod
    def test_agent_id_validation(cls):
        """Test agent_id field validation."""
        # Valid agent IDs
        valid_agent_ids = [
            "researcher_001",
            "architect_distributed_systems_002",
            "agent-with-dashes",
            "agent_with_underscores_123",
        ]

        for agent_id in valid_agent_ids:
            data = cls.create_valid_data(agent_id=agent_id)
            cls.assert_valid_model(ComposerResponse, data)

        # Empty agent_id should be invalid
        cls.assert_invalid_model(
            ComposerResponse, cls.create_valid_data(agent_id=""), "agent_id"
        )

    @classmethod
    def test_role_validation(cls):
        """Test role field validation."""
        # Valid roles (string format in response)
        valid_roles = [
            "researcher",
            "architect",
            "implementer",
            "tester",
            "analyst",
            "critic",
            "reviewer",
            "innovator",
        ]

        for role in valid_roles:
            data = cls.create_valid_data(role=role)
            cls.assert_valid_model(ComposerResponse, data)

        # Empty role should be invalid
        cls.assert_invalid_model(
            ComposerResponse, cls.create_valid_data(role=""), "role"
        )

    @classmethod
    def test_domains_list_validation(cls):
        """Test domains list validation."""
        # Valid domain lists
        valid_domain_lists = [
            [],  # empty
            ["single-domain"],
            ["distributed-systems", "async-programming"],
            ["domain1", "domain2", "domain3", "domain4", "domain5"],
        ]

        for domains in valid_domain_lists:
            data = cls.create_valid_data(domains=domains)
            cls.assert_valid_model(ComposerResponse, data)

    @classmethod
    def test_system_prompt_validation(cls):
        """Test system_prompt field validation."""
        # Valid system prompts
        valid_prompts = [
            "Simple prompt",
            "Detailed system prompt with comprehensive instructions and context",
            "Multi-line\nprompt\nwith\nbreaks",
            "Prompt with special characters: <>{}[]()!@#$%^&*",
            "Very long prompt " * 50,
        ]

        for prompt in valid_prompts:
            data = cls.create_valid_data(system_prompt=prompt)
            cls.assert_valid_model(ComposerResponse, data)

        # Empty system_prompt should be invalid
        cls.assert_invalid_model(
            ComposerResponse, cls.create_valid_data(system_prompt=""), "system_prompt"
        )

    @classmethod
    def test_capabilities_validation(cls):
        """Test capabilities list validation."""
        # Valid capability lists
        valid_capabilities = [
            [],  # empty
            ["capability1"],
            ["analysis", "research", "implementation"],
            ["very_specific_capability_with_long_name"],
        ]

        for capabilities in valid_capabilities:
            data = cls.create_valid_data(capabilities=capabilities)
            cls.assert_valid_model(ComposerResponse, data)

    @classmethod
    def test_tools_validation(cls):
        """Test tools list validation."""
        # Valid tool lists
        valid_tool_lists = [
            [],  # empty
            ["Read"],
            ["Read", "Write", "Bash", "Grep"],
            ["mcp__knowledge__query", "mcp__memory__search"],
        ]

        for tools in valid_tool_lists:
            data = cls.create_valid_data(tools=tools)
            cls.assert_valid_model(ComposerResponse, data)

    @classmethod
    def test_confidence_validation(cls):
        """Test confidence field validation."""
        # Valid confidence values (0.0 to 1.0)
        valid_confidences = [0.0, 0.25, 0.5, 0.75, 1.0]

        for confidence in valid_confidences:
            data = cls.create_valid_data(confidence=confidence)
            cls.assert_valid_model(ComposerResponse, data)

        # Invalid confidence values
        invalid_confidences = [-0.1, -1.0, 1.1, 2.0]

        for confidence in invalid_confidences:
            data = cls.create_valid_data(confidence=confidence)
            cls.assert_invalid_model(ComposerResponse, data, "confidence")

    @classmethod
    def test_domain_expertise_validation(cls):
        """Test domain_expertise list validation."""
        # Valid domain expertise lists (list of DomainExpertise)
        valid_expertise_lists = [
            [],  # empty
            [
                {
                    "domain_id": "test-domain",
                    "knowledge_patterns": {},
                    "decision_rules": {},
                    "specialized_tools": [],
                    "confidence_thresholds": {},
                }
            ],
        ]

        for expertise_list in valid_expertise_lists:
            data = cls.create_valid_data(domain_expertise=expertise_list)
            cls.assert_valid_model(ComposerResponse, data)

    @classmethod
    def test_error_validation(cls):
        """Test error field validation."""
        # Valid error values
        valid_errors = [
            None,  # no error
            "",  # empty error
            "Simple error message",
            "Detailed error with context and troubleshooting information",
        ]

        for error in valid_errors:
            data = cls.create_valid_data(error=error)
            cls.assert_valid_model(ComposerResponse, data)

    @classmethod
    def test_extra_fields_allowed(cls):
        """Test that extra fields are allowed."""
        # ComposerResponse has extra="allow" configuration
        data_with_extra = cls.create_valid_data(
            custom_field="custom_value", metadata={"key": "value"}
        )

        response = cls.assert_valid_model(ComposerResponse, data_with_extra)

        # Extra fields should be accessible
        assert hasattr(response, "custom_field")
        assert response.custom_field == "custom_value"


# ============================================================================
# AgentCompositionRequest Model Validation
# ============================================================================


class AgentCompositionRequestValidator(BaseValidationPattern):
    """Validation patterns for AgentCompositionRequest model."""

    @classmethod
    def create_valid_data(cls, **overrides) -> dict[str, Any]:
        """Create valid AgentCompositionRequest data."""
        data = {
            "role": "researcher",
            "domains": "distributed-systems,async-programming",
            "context": "Research scalable system architectures for high-throughput processing",
        }
        data.update(overrides)
        return data

    @classmethod
    def test_required_fields(cls):
        """Test required field validation."""
        # Role is required
        cls.assert_invalid_model(
            AgentCompositionRequest, {"domains": "test", "context": "test"}, "role"
        )

        # Minimal valid request
        minimal_request = {"role": "researcher"}
        cls.assert_valid_model(AgentCompositionRequest, minimal_request)

    @classmethod
    def test_field_defaults(cls):
        """Test field default values."""
        minimal_request = AgentCompositionRequest(role="architect")

        assert minimal_request.role == "architect"
        assert minimal_request.domains is None
        assert minimal_request.context is None

    @classmethod
    def test_role_validation_constraints(cls):
        """Test role field validation with constraints."""
        # Valid roles (length constraints)
        valid_roles = [
            "r",  # min_length=1
            "researcher",
            "a" * 100,  # max_length=100
        ]

        for role in valid_roles:
            data = cls.create_valid_data(role=role)
            cls.assert_valid_model(AgentCompositionRequest, data)

        # Invalid roles
        invalid_roles = [
            "",  # below min_length
            "a" * 101,  # above max_length
        ]

        for role in invalid_roles:
            data = cls.create_valid_data(role=role)
            cls.assert_invalid_model(AgentCompositionRequest, data, "role")

    @classmethod
    def test_role_security_validation(cls):
        """Test role field security validation."""
        # Path traversal attempts should be rejected by validator
        malicious_roles = [
            "../../../sensitive",
            "role/../../../etc",
            "role\\..\\..\\windows",
            "role/../../bin",
        ]

        for role in malicious_roles:
            data = cls.create_valid_data(role=role)
            cls.assert_invalid_model(AgentCompositionRequest, data, "role")

    @classmethod
    def test_role_sanitization(cls):
        """Test role field sanitization."""
        # Whitespace should be stripped
        roles_with_whitespace = [
            "  researcher  ",
            "\narchitect\n",
            "\ttester\t",
        ]

        for role in roles_with_whitespace:
            data = cls.create_valid_data(role=role)
            request = cls.assert_valid_model(AgentCompositionRequest, data)
            assert request.role.strip() == request.role  # Should be stripped

    @classmethod
    def test_domains_validation_constraints(cls):
        """Test domains field validation with constraints."""
        # Valid domains (length constraints)
        valid_domains = [
            None,  # optional
            "",  # empty
            "d",  # short
            "domain1,domain2,domain3",
            "x" * 500,  # max_length=500
        ]

        for domains in valid_domains:
            data = cls.create_valid_data(domains=domains)
            cls.assert_valid_model(AgentCompositionRequest, data)

        # Invalid domains (too long)
        invalid_domains = [
            "x" * 501,  # above max_length
        ]

        for domains in invalid_domains:
            data = cls.create_valid_data(domains=domains)
            cls.assert_invalid_model(AgentCompositionRequest, data, "domains")

    @classmethod
    def test_context_validation_constraints(cls):
        """Test context field validation with constraints."""
        # Valid contexts (length constraints)
        valid_contexts = [
            None,  # optional
            "",  # empty
            "c",  # short
            "Detailed context with requirements",
            "x" * 10000,  # max_length=10000
        ]

        for context in valid_contexts:
            data = cls.create_valid_data(context=context)
            cls.assert_valid_model(AgentCompositionRequest, data)

        # Invalid contexts (too long)
        invalid_contexts = [
            "x" * 10001,  # above max_length
        ]

        for context in invalid_contexts:
            data = cls.create_valid_data(context=context)
            cls.assert_invalid_model(AgentCompositionRequest, data, "context")

    @classmethod
    def test_extra_fields_forbidden(cls):
        """Test that extra fields are forbidden."""
        # AgentCompositionRequest has extra="forbid" configuration
        data_with_extra = cls.create_valid_data(extra_field="should_be_rejected")

        cls.assert_invalid_model(AgentCompositionRequest, data_with_extra)


# ============================================================================
# Cross-Model Composition Validation Patterns
# ============================================================================


class CompositionServiceCrossValidator:
    """Cross-model validation patterns for Composition Service."""

    @staticmethod
    def validate_request_response_consistency(
        request: ComposerRequest, response: ComposerResponse
    ) -> list[str]:
        """Validate consistency between ComposerRequest and ComposerResponse."""
        issues = []

        # Role consistency
        if request.role != response.role:
            issues.append(
                f"Request role '{request.role}' doesn't match "
                f"response role '{response.role}'"
            )

        # Domain consistency
        if request.domains:
            request_domains = [d.strip() for d in request.domains.split(",")]
            # Response domains should include at least some request domains
            if response.domains:
                missing_domains = set(request_domains) - set(response.domains)
                if missing_domains:
                    issues.append(
                        f"Response missing requested domains: {missing_domains}"
                    )

        # Success/error consistency
        if response.success and response.error:
            issues.append("Successful response contains error message")

        if not response.success and not response.error:
            issues.append("Failed response missing error message")

        # Confidence validation
        if response.success and response.confidence < 0.3:
            issues.append("Successful composition has very low confidence")

        return issues

    @staticmethod
    def validate_domain_expertise_consistency(response: ComposerResponse) -> list[str]:
        """Validate consistency of domain expertise in response."""
        issues = []

        # Domain expertise should match response domains
        if response.domain_expertise and response.domains:
            expertise_domains = {exp.domain_id for exp in response.domain_expertise}
            response_domains = set(response.domains)

            missing_expertise = response_domains - expertise_domains
            if missing_expertise:
                issues.append(
                    f"Missing domain expertise for domains: {missing_expertise}"
                )

            extra_expertise = expertise_domains - response_domains
            if extra_expertise:
                issues.append(
                    f"Extra domain expertise for unlisted domains: {extra_expertise}"
                )

        # Validate individual domain expertise
        for expertise in response.domain_expertise:
            # Domain expertise should have reasonable content
            if not any(
                [
                    expertise.knowledge_patterns,
                    expertise.decision_rules,
                    expertise.specialized_tools,
                    expertise.confidence_thresholds,
                ]
            ):
                issues.append(f"Domain expertise for '{expertise.domain_id}' is empty")

        return issues

    @staticmethod
    def validate_agent_composition_security(
        request: AgentCompositionRequest,
    ) -> list[str]:
        """Validate security aspects of agent composition."""
        issues = []

        # Role security validation
        if any(char in request.role for char in ["..", "/", "\\"]):
            issues.append("Role contains path traversal characters")

        # Context security validation (basic)
        if request.context:
            # Check for potentially malicious patterns
            suspicious_patterns = [
                "script>",
                "<script",
                "javascript:",
                "eval(",
                "exec(",
                "system(",
                "rm -rf",
                "del /",
                "format c:",
            ]

            for pattern in suspicious_patterns:
                if pattern.lower() in request.context.lower():
                    issues.append(f"Context contains suspicious pattern: {pattern}")

        # Domain security validation
        if request.domains:
            if any(char in request.domains for char in ["..", "/", "\\"]):
                issues.append("Domains contain path traversal characters")

        return issues

    @staticmethod
    def validate_composition_completeness(response: ComposerResponse) -> list[str]:
        """Validate completeness of composition response."""
        issues = []

        if not response.success:
            return issues  # Skip completeness check for failed responses

        # Essential components should be present
        if not response.system_prompt.strip():
            issues.append("Empty system prompt in successful response")

        if not response.capabilities:
            issues.append("No capabilities listed in successful response")

        if not response.tools:
            issues.append("No tools listed in successful response")

        # Agent ID should follow naming conventions
        if not any(char in response.agent_id for char in ["_", "-"]):
            issues.append("Agent ID doesn't follow naming conventions")

        # Confidence should be reasonable for successful composition
        if response.confidence < 0.5:
            issues.append("Low confidence for successful composition")

        return issues


# ============================================================================
# Comprehensive Test Suite
# ============================================================================


class TestCompositionValidation:
    """Test class to run all Composition Service validation tests."""

    def test_composer_request_validation(self):
        """Test ComposerRequest model validation."""
        ComposerRequestValidator.test_required_fields()
        ComposerRequestValidator.test_field_defaults()
        ComposerRequestValidator.test_role_validation()
        ComposerRequestValidator.test_domains_validation()
        ComposerRequestValidator.test_context_validation()
        ComposerRequestValidator.test_role_domain_combinations()

    def test_domain_expertise_validation(self):
        """Test DomainExpertise model validation."""
        DomainExpertiseValidator.test_required_fields()
        DomainExpertiseValidator.test_field_defaults()
        DomainExpertiseValidator.test_domain_id_validation()
        DomainExpertiseValidator.test_knowledge_patterns_validation()
        DomainExpertiseValidator.test_decision_rules_validation()
        DomainExpertiseValidator.test_specialized_tools_validation()
        DomainExpertiseValidator.test_confidence_thresholds_validation()

    def test_composer_response_validation(self):
        """Test ComposerResponse model validation."""
        ComposerResponseValidator.test_required_fields()
        ComposerResponseValidator.test_field_defaults()
        ComposerResponseValidator.test_success_validation()
        ComposerResponseValidator.test_summary_validation()
        ComposerResponseValidator.test_agent_id_validation()
        ComposerResponseValidator.test_role_validation()
        ComposerResponseValidator.test_domains_list_validation()
        ComposerResponseValidator.test_system_prompt_validation()
        ComposerResponseValidator.test_capabilities_validation()
        ComposerResponseValidator.test_tools_validation()
        ComposerResponseValidator.test_confidence_validation()
        ComposerResponseValidator.test_domain_expertise_validation()
        ComposerResponseValidator.test_error_validation()
        ComposerResponseValidator.test_extra_fields_allowed()

    def test_agent_composition_request_validation(self):
        """Test AgentCompositionRequest model validation."""
        AgentCompositionRequestValidator.test_required_fields()
        AgentCompositionRequestValidator.test_field_defaults()
        AgentCompositionRequestValidator.test_role_validation_constraints()
        AgentCompositionRequestValidator.test_role_security_validation()
        AgentCompositionRequestValidator.test_role_sanitization()
        AgentCompositionRequestValidator.test_domains_validation_constraints()
        AgentCompositionRequestValidator.test_context_validation_constraints()
        AgentCompositionRequestValidator.test_extra_fields_forbidden()

    def test_cross_model_validation(self):
        """Test cross-model validation patterns."""
        # Create test models

        request = ComposerRequest(
            role="researcher",
            domains="distributed-systems,async-programming",
            context="Research distributed system patterns",
        )

        response = ComposerResponse(
            success=True,
            summary="Successfully composed researcher agent",
            agent_id="researcher_distributed_001",
            role="researcher",
            domains=["distributed-systems", "async-programming"],
            system_prompt="You are a distributed systems researcher...",
            capabilities=["system_analysis", "pattern_research"],
            tools=["Read", "Grep", "WebSearch"],
            domain_expertise=[
                DomainExpertise(
                    domain_id="distributed-systems",
                    specialized_tools=["etcd", "consul"],
                ),
                DomainExpertise(
                    domain_id="async-programming",
                    specialized_tools=["asyncio", "aiohttp"],
                ),
            ],
            confidence=0.85,
        )

        composition_request = AgentCompositionRequest(
            role="researcher",
            domains="distributed-systems",
            context="Valid research context",
        )

        # Run cross-model validations
        request_response_issues = (
            CompositionServiceCrossValidator.validate_request_response_consistency(
                request, response
            )
        )

        expertise_issues = (
            CompositionServiceCrossValidator.validate_domain_expertise_consistency(
                response
            )
        )

        security_issues = (
            CompositionServiceCrossValidator.validate_agent_composition_security(
                composition_request
            )
        )

        completeness_issues = (
            CompositionServiceCrossValidator.validate_composition_completeness(response)
        )

        # Should have no issues for valid models
        assert len(request_response_issues) == 0
        assert len(expertise_issues) == 0
        assert len(security_issues) == 0
        assert len(completeness_issues) == 0


if __name__ == "__main__":
    # Manual test runner
    test_suite = TestCompositionValidation()

    try:
        test_suite.test_composer_request_validation()
        test_suite.test_domain_expertise_validation()
        test_suite.test_composer_response_validation()
        test_suite.test_agent_composition_request_validation()
        test_suite.test_cross_model_validation()

        print("✅ All Composition Service validation tests passed!")

    except Exception as e:
        print(f"❌ Composition validation test failed: {e}")
        raise
