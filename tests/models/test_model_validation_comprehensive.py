"""Comprehensive validation tests focusing on edge cases, error messages, and boundary conditions."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from khive.prompts import AgentRole
from khive.services.artifacts.models import (
    Author,
    ContributionMetadata,
    Document,
    DocumentType,
)
from khive.services.composition.parts import (
    AgentCompositionRequest,
    ComposerRequest,
    ComposerResponse,
    DomainExpertise,
)
from khive.services.orchestration.parts import OrchestrationPlan
from khive.services.plan.parts import ComplexityLevel, PlannerRequest, PlannerResponse


class TestFieldConstraintValidation:
    """Test field constraint validation and boundary conditions."""

    @pytest.mark.parametrize(
        "field_name,invalid_value,expected_error",
        [
            ("id", "", "String should have at least 1 character"),
            ("role", "", "String should have at least 1 character"),
        ],
    )
    def test_author_field_constraints(self, field_name, invalid_value, expected_error):
        """Test Author field constraints with various invalid values."""
        valid_data = {"id": "test_id", "role": "test_role"}
        valid_data[field_name] = invalid_value

        with pytest.raises(ValidationError) as exc_info:
            Author(**valid_data)

        error_msg = str(exc_info.value)
        assert field_name in error_msg
        assert expected_error in error_msg

    @pytest.mark.parametrize(
        "confidence,should_pass",
        [
            (0.0, True),
            (0.1, True),
            (0.5, True),
            (0.9, True),
            (1.0, True),  # Valid values
            (-0.1, False),
            (1.1, False),
            (2.0, False),
            (-1.0, False),  # Invalid values
        ],
    )
    def test_confidence_boundary_validation(self, confidence, should_pass):
        """Test confidence field boundary validation across models."""
        base_data = {
            "success": True,
            "summary": "Test summary",
            "agent_id": "test_agent",
            "role": "researcher",
            "system_prompt": "Test prompt",
        }

        if should_pass:
            response = ComposerResponse(confidence=confidence, **base_data)
            assert response.confidence == confidence
        else:
            with pytest.raises(ValidationError) as exc_info:
                ComposerResponse(confidence=confidence, **base_data)

            error_msg = str(exc_info.value)
            assert "confidence" in error_msg

    @pytest.mark.parametrize(
        "content_length,should_pass",
        [
            (0, True),
            (1, True),
            (100, True),
            (10000, True),  # Valid values
            (-1, False),
            (-10, False),
            (-100, False),  # Invalid values
        ],
    )
    def test_content_length_validation(self, content_length, should_pass):
        """Test content_length field validation (must be >= 0)."""
        author = Author(id="test", role="test")
        timestamp = datetime.now(timezone.utc)

        if should_pass:
            contribution = ContributionMetadata(
                author=author, timestamp=timestamp, content_length=content_length
            )
            assert contribution.content_length == content_length
        else:
            with pytest.raises(ValidationError) as exc_info:
                ContributionMetadata(
                    author=author, timestamp=timestamp, content_length=content_length
                )

            error_msg = str(exc_info.value)
            assert "content_length" in error_msg
            assert "Input should be greater than or equal to 0" in error_msg

    def test_agent_composition_request_field_length_constraints(self):
        """Test AgentCompositionRequest field length constraints."""
        # Test role field constraints (min_length=1, max_length=100)
        with pytest.raises(ValidationError):
            AgentCompositionRequest(role="")  # Too short

        with pytest.raises(ValidationError):
            AgentCompositionRequest(role="a" * 101)  # Too long

        # Valid role lengths
        valid_role = AgentCompositionRequest(role="a" * 100)  # Max length
        assert len(valid_role.role) == 100

        # Test domains field constraints (max_length=500)
        with pytest.raises(ValidationError):
            AgentCompositionRequest(role="test", domains="a" * 501)  # Too long

        # Valid domains length
        valid_domains = AgentCompositionRequest(
            role="test", domains="a" * 500
        )  # Max length
        assert len(valid_domains.domains) == 500

        # Test context field constraints (max_length=10000)
        with pytest.raises(ValidationError):
            AgentCompositionRequest(role="test", context="a" * 10001)  # Too long

        # Valid context length
        valid_context = AgentCompositionRequest(
            role="test", context="a" * 10000
        )  # Max length
        assert len(valid_context.context) == 10000


class TestTypeValidationErrors:
    """Test type validation and error message clarity."""

    @pytest.mark.parametrize(
        "field_name,invalid_value,expected_type",
        [
            ("success", "not_boolean", "boolean"),
            ("confidence", "not_number", "number"),
            ("recommended_agents", "not_integer", "integer"),
            ("version", "not_integer", "integer"),
            ("content_length", "not_integer", "integer"),
        ],
    )
    def test_type_validation_error_messages(
        self, field_name, invalid_value, expected_type
    ):
        """Test that type validation errors provide clear messages."""
        # Use different models depending on the field
        if field_name in ["success", "confidence"]:
            model_class = ComposerResponse
            valid_data = {
                "summary": "Test",
                "agent_id": "test",
                "role": "test",
                "system_prompt": "test",
            }
        elif field_name == "recommended_agents":
            model_class = PlannerResponse
            valid_data = {
                "success": True,
                "summary": "Test",
                "complexity": ComplexityLevel.SIMPLE,
                "confidence": 0.8,
            }
        elif field_name == "version":
            model_class = Document
            valid_data = {
                "session_id": "test",
                "name": "test",
                "type": DocumentType.DELIVERABLE,
                "content": "test",
                "last_modified": datetime.now(timezone.utc),
            }
        elif field_name == "content_length":
            model_class = ContributionMetadata
            valid_data = {
                "author": Author(id="test", role="test"),
                "timestamp": datetime.now(timezone.utc),
            }

        valid_data[field_name] = invalid_value

        with pytest.raises(ValidationError) as exc_info:
            model_class(**valid_data)

        error_msg = str(exc_info.value)
        assert field_name in error_msg
        assert f"Input should be a valid {expected_type}" in error_msg

    def test_required_field_validation_messages(self):
        """Test that missing required fields generate clear error messages."""
        required_fields_tests = [
            (Author, ["id", "role"]),
            (
                ComposerResponse,
                [
                    "success",
                    "summary",
                    "agent_id",
                    "role",
                    "system_prompt",
                    "confidence",
                ],
            ),
            (Document, ["session_id", "name", "type", "content", "last_modified"]),
            (PlannerRequest, ["task_description"]),
        ]

        for model_class, required_fields in required_fields_tests:
            for field_name in required_fields:
                with pytest.raises(ValidationError) as exc_info:
                    if model_class == Author:
                        data = {"id": "test", "role": "test"}
                    elif model_class == ComposerResponse:
                        data = {
                            "success": True,
                            "summary": "test",
                            "agent_id": "test",
                            "role": "test",
                            "system_prompt": "test",
                            "confidence": 0.8,
                        }
                    elif model_class == Document:
                        data = {
                            "session_id": "test",
                            "name": "test",
                            "type": DocumentType.DELIVERABLE,
                            "content": "test",
                            "last_modified": datetime.now(timezone.utc),
                        }
                    elif model_class == PlannerRequest:
                        data = {"task_description": "test"}

                    del data[field_name]  # Remove required field
                    model_class(**data)

                error_msg = str(exc_info.value)
                assert field_name in error_msg
                assert "Field required" in error_msg

    def test_enum_validation_error_messages(self):
        """Test enum validation provides clear error messages."""
        timestamp = datetime.now(timezone.utc)

        # Test invalid DocumentType
        with pytest.raises(ValidationError) as exc_info:
            Document(
                session_id="test",
                name="test",
                type="invalid_type",  # Invalid enum value
                content="test",
                last_modified=timestamp,
            )

        error_msg = str(exc_info.value)
        assert "type" in error_msg
        # Should mention valid enum values
        assert any(doc_type.value in error_msg for doc_type in DocumentType)

    def test_nested_model_validation_error_messages(self):
        """Test nested model validation provides clear error paths."""
        timestamp = datetime.now(timezone.utc)

        # Test nested validation error (invalid Author within ContributionMetadata)
        with pytest.raises(ValidationError) as exc_info:
            ContributionMetadata(
                author={"id": "", "role": "test"},  # Invalid nested model (empty id)
                timestamp=timestamp,
                content_length=100,
            )

        error_msg = str(exc_info.value)
        assert "author" in error_msg
        assert "id" in error_msg
        assert "String should have at least 1 character" in error_msg


class TestCustomValidatorBehavior:
    """Test custom validator behavior and edge cases."""

    def test_agent_composition_request_role_validator(self):
        """Test custom role validator in AgentCompositionRequest."""
        # Test that role validation works correctly
        # (This would test custom validators if they exist)
        request = AgentCompositionRequest(role="researcher")
        assert request.role == "researcher"

        # Test role with special characters (if validator allows/disallows)
        request_with_underscore = AgentCompositionRequest(role="senior_researcher")
        assert request_with_underscore.role == "senior_researcher"

        request_with_numbers = AgentCompositionRequest(role="researcher_v2")
        assert request_with_numbers.role == "researcher_v2"

    def test_domain_expertise_field_defaults(self):
        """Test DomainExpertise field default factory behavior."""
        # Test that default factories work correctly
        expertise = DomainExpertise(domain_id="test_domain")

        assert expertise.knowledge_patterns == {}
        assert expertise.decision_rules == {}
        assert expertise.specialized_tools == []
        assert expertise.confidence_thresholds == {}

        # Test that different instances get separate default objects
        expertise1 = DomainExpertise(domain_id="domain1")
        expertise2 = DomainExpertise(domain_id="domain2")

        expertise1.knowledge_patterns["test"] = "value1"
        expertise2.knowledge_patterns["test"] = "value2"

        assert (
            expertise1.knowledge_patterns["test"]
            != expertise2.knowledge_patterns["test"]
        )

    def test_document_create_new_timestamp_behavior(self):
        """Test Document.create_new timestamp handling."""
        from unittest.mock import patch

        fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        with patch("khive.services.artifacts.models.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_time

            document = Document.create_new(
                session_id="timestamp_test",
                name="timestamp_document",
                doc_type=DocumentType.DELIVERABLE,
                content="Test content",
            )

            assert document.last_modified == fixed_time
            assert len(document.contributions) == 1
            assert document.contributions[0].timestamp == fixed_time


class TestEdgeCaseValidation:
    """Test edge cases and boundary conditions."""

    def test_empty_collections_handling(self):
        """Test handling of empty collections."""
        # Empty agent_requests list in OrchestrationPlan
        plan = OrchestrationPlan(common_background="Test background", agent_requests=[])
        assert plan.agent_requests == []

        # Empty domains list in ComposerResponse
        response = ComposerResponse(
            success=True,
            summary="Test summary",
            agent_id="test",
            role="test",
            system_prompt="test",
            domains=[],  # Empty list
            confidence=0.8,
        )
        assert response.domains == []

    def test_very_large_string_handling(self):
        """Test handling of very large strings within limits."""
        # Test large content in Document
        very_large_content = "x" * 100000  # 100KB content

        document = Document(
            session_id="large_content_test",
            name="large_document",
            type=DocumentType.DELIVERABLE,
            content=very_large_content,
            last_modified=datetime.now(timezone.utc),
        )

        assert len(document.content) == 100000

        # Test serialization still works
        serialized = document.model_dump_json()
        restored = Document.model_validate_json(serialized)
        assert restored.content == very_large_content

    def test_unicode_and_special_character_handling(self):
        """Test handling of Unicode and special characters."""
        # Test Unicode in various fields
        author = Author(id="测试用户", role="研究员")
        assert author.id == "测试用户"
        assert author.role == "研究员"

        # Test special characters in content
        special_content = "Content with émojis 🚀, symbols ♠️♣️♥️♦️, and newlines\n\ttabs"
        document = Document(
            session_id="unicode_test",
            name="special_chars_文档",
            type=DocumentType.SCRATCHPAD,
            content=special_content,
            last_modified=datetime.now(timezone.utc),
        )

        assert document.name == "special_chars_文档"
        assert document.content == special_content

        # Test serialization preserves Unicode
        serialized = document.model_dump_json()
        restored = Document.model_validate_json(serialized)
        assert restored.name == "special_chars_文档"
        assert restored.content == special_content

    def test_null_and_none_handling(self):
        """Test handling of null/None values in optional fields."""
        # Test None in optional fields
        request = ComposerRequest(
            role=AgentRole.RESEARCHER,
            domains=None,  # Explicitly None
            context=None,  # Explicitly None
        )

        assert request.domains is None
        assert request.context is None

        # Test serialization includes None values correctly
        serialized = request.model_dump()
        assert "domains" in serialized
        assert serialized["domains"] is None

    def test_model_equality_edge_cases(self):
        """Test model equality in edge cases."""
        timestamp = datetime.now(timezone.utc)

        # Test equality with identical timestamps
        doc1 = Document(
            session_id="equality_test",
            name="test_doc",
            type=DocumentType.DELIVERABLE,
            content="content",
            last_modified=timestamp,
        )

        doc2 = Document(
            session_id="equality_test",
            name="test_doc",
            type=DocumentType.DELIVERABLE,
            content="content",
            last_modified=timestamp,
        )

        assert doc1 == doc2

        # Test inequality with microsecond differences
        timestamp_diff = timestamp.replace(microsecond=timestamp.microsecond + 1)

        doc3 = Document(
            session_id="equality_test",
            name="test_doc",
            type=DocumentType.DELIVERABLE,
            content="content",
            last_modified=timestamp_diff,
        )

        assert doc1 != doc3  # Should be different due to timestamp difference

    def test_circular_reference_handling(self):
        """Test that models handle potential circular references gracefully."""
        # This tests the model design doesn't create circular references
        # For example, contributions referring back to documents

        author = Author(id="circular_test", role="test")
        timestamp = datetime.now(timezone.utc)

        # Create contribution
        contribution = ContributionMetadata(
            author=author, timestamp=timestamp, content_length=100
        )

        # Create document with contribution
        document = Document(
            session_id="circular_test",
            name="circular_doc",
            type=DocumentType.DELIVERABLE,
            content="content",
            contributions=[contribution],
            last_modified=timestamp,
        )

        # Should serialize without issues (no circular references)
        serialized = document.model_dump_json()
        restored = Document.model_validate_json(serialized)

        assert restored == document
        assert len(restored.contributions) == 1
