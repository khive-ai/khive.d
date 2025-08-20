"""Unit tests for khive base models and types."""

import pytest
from pydantic import ValidationError

from khive._types import BaseModel


class SampleModel(BaseModel):
    """Sample model for testing."""

    name: str
    value: int = 42
    tags: list[str] = []


@pytest.mark.unit
class TestBaseModel:
    """Test the base model functionality."""

    def test_model_creation(self):
        """Test basic model creation."""
        model = SampleModel(name="test")

        assert model.name == "test"
        assert model.value == 42
        assert model.tags == []

    def test_model_with_values(self):
        """Test model creation with custom values."""
        model = SampleModel(name="custom", value=100, tags=["tag1", "tag2"])

        assert model.name == "custom"
        assert model.value == 100
        assert model.tags == ["tag1", "tag2"]

    def test_model_validation_error(self):
        """Test model validation with invalid data."""
        with pytest.raises(ValidationError) as exc_info:
            SampleModel(name="test", value="invalid")

        assert "value" in str(exc_info.value)

    def test_model_hashability(self):
        """Test that model instances are hashable."""
        model1 = SampleModel(name="test", value=42)
        model2 = SampleModel(name="test", value=42)
        model3 = SampleModel(name="different", value=42)

        # Same data should have same hash
        assert hash(model1) == hash(model2)

        # Different data should (likely) have different hash
        assert hash(model1) != hash(model3)

        # Should be usable in sets
        model_set = {model1, model2, model3}
        assert len(model_set) == 2  # model1 and model2 are the same

    def test_model_config(self):
        """Test model configuration settings."""
        model = SampleModel(name="test")

        # Test that extra fields are forbidden
        with pytest.raises(ValidationError):
            SampleModel(name="test", extra_field="should_fail")

    def test_model_json_serialization(self):
        """Test JSON serialization and deserialization."""
        model = SampleModel(
            name="json_test", value=123, tags=["serialize", "deserialize"]
        )

        # Serialize to JSON
        json_data = model.model_dump()
        expected_data = {
            "name": "json_test",
            "value": 123,
            "tags": ["serialize", "deserialize"],
        }
        assert json_data == expected_data

        # Deserialize from JSON
        restored_model = SampleModel.model_validate(json_data)
        assert restored_model == model
