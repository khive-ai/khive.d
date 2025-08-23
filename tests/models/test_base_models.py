"""Comprehensive tests for khive base models and types."""

import json
from typing import Any

import pytest
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ValidationError

from khive._types import BaseModel


class TestBaseModelCore:
    """Core functionality tests for the khive BaseModel."""

    def test_base_model_inheritance(self):
        """Test BaseModel inherits from HashableModel correctly."""
        from lionagi.models import HashableModel

        assert issubclass(BaseModel, HashableModel)
        assert issubclass(BaseModel, PydanticBaseModel)

    def test_model_config_properties(self):
        """Test BaseModel configuration is set correctly."""
        config = BaseModel.model_config

        assert config["arbitrary_types_allowed"] is True
        assert config["extra"] == "forbid"
        assert config["use_enum_values"] is True
        assert config["populate_by_name"] is True

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden by default."""

        class TestModel(BaseModel):
            name: str
            value: int = 42

        # Valid creation should work
        model = TestModel(name="test", value=100)
        assert model.name == "test"
        assert model.value == 100

        # Extra fields should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            TestModel(name="test", value=100, extra_field="forbidden")

        error_msg = str(exc_info.value)
        assert "extra_field" in error_msg
        assert "Extra inputs are not permitted" in error_msg

    def test_use_enum_values_behavior(self):
        """Test enum values are used properly."""
        from enum import Enum

        class Status(str, Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        class TestModel(BaseModel):
            status: Status

        model = TestModel(status=Status.ACTIVE)
        serialized = model.model_dump()
        assert serialized["status"] == "active"  # String value, not enum

    def test_hashability(self):
        """Test model instances are hashable."""

        class TestModel(BaseModel):
            name: str
            value: int = 42

        model1 = TestModel(name="test", value=100)
        model2 = TestModel(name="test", value=100)
        model3 = TestModel(name="different", value=100)

        # Should be hashable
        hash1 = hash(model1)
        hash2 = hash(model2)
        hash3 = hash(model3)

        assert isinstance(hash1, int)
        assert isinstance(hash2, int)
        assert isinstance(hash3, int)

        # Same data should have same hash
        assert hash1 == hash2

        # Different data should (likely) have different hash
        assert hash1 != hash3

        # Should work in sets
        model_set = {model1, model2, model3}
        assert len(model_set) == 2  # model1 and model2 are equivalent

    def test_populate_by_name_behavior(self):
        """Test populate_by_name configuration works."""

        class TestModel(BaseModel):
            user_name: str

            class Config:
                alias_generator = lambda field_name: field_name.replace("_", "-")

        # Should work with field name
        model1 = TestModel(user_name="test")
        assert model1.user_name == "test"
        
        # Should also work with generated alias (underscore to dash)
        model2 = TestModel(**{"user-name": "test_alias"})
        assert model2.user_name == "test_alias"

        # Should also work with alias (if defined)
        # This tests the populate_by_name=True configuration


class TestBaseModelValidation:
    """Test validation behavior of BaseModel."""

    def test_type_validation(self):
        """Test basic type validation."""

        class TestModel(BaseModel):
            name: str
            count: int
            score: float
            active: bool
            tags: list[str]
            metadata: dict[str, Any]

        # Valid data
        valid_data = {
            "name": "test",
            "count": 42,
            "score": 95.5,
            "active": True,
            "tags": ["tag1", "tag2"],
            "metadata": {"key": "value"},
        }

        model = TestModel(**valid_data)
        assert model.name == "test"
        assert model.count == 42
        assert model.score == 95.5
        assert model.active is True
        assert model.tags == ["tag1", "tag2"]
        assert model.metadata == {"key": "value"}

    def test_type_coercion(self):
        """Test type coercion behavior."""

        class TestModel(BaseModel):
            count: int
            score: float
            active: bool

        # Test coercion
        model = TestModel(
            count="42",  # String to int
            score="95.5",  # String to float
            active="true",  # String to bool
        )

        assert model.count == 42
        assert model.score == 95.5
        assert model.active is True

    def test_validation_errors(self):
        """Test validation error messages are clear."""

        class TestModel(BaseModel):
            name: str
            count: int

        # Missing required field
        with pytest.raises(ValidationError) as exc_info:
            TestModel(count=42)

        error = exc_info.value
        assert "name" in str(error)
        assert "Field required" in str(error)

        # Wrong type
        with pytest.raises(ValidationError) as exc_info:
            TestModel(name="test", count="not_a_number")

        error = exc_info.value
        assert "count" in str(error)
        assert "Input should be a valid integer" in str(error)

    def test_nested_model_validation(self):
        """Test nested model validation."""

        class InnerModel(BaseModel):
            value: int

        class OuterModel(BaseModel):
            inner: InnerModel
            inners: list[InnerModel]

        # Valid nested data
        valid_data = {"inner": {"value": 42}, "inners": [{"value": 1}, {"value": 2}]}

        model = OuterModel(**valid_data)
        assert isinstance(model.inner, InnerModel)
        assert model.inner.value == 42
        assert len(model.inners) == 2
        assert all(isinstance(inner, InnerModel) for inner in model.inners)

        # Invalid nested data
        with pytest.raises(ValidationError) as exc_info:
            OuterModel(inner={"value": "not_int"}, inners=[{"value": 1}])

        error_msg = str(exc_info.value)
        assert "inner" in error_msg
        assert "value" in error_msg


class TestBaseModelSerialization:
    """Test serialization and deserialization behavior."""

    def test_model_dump(self):
        """Test model_dump produces correct output."""

        class TestModel(BaseModel):
            name: str
            count: int = 42
            tags: list[str] = []

        model = TestModel(name="test", count=100, tags=["a", "b"])
        data = model.model_dump()

        expected = {"name": "test", "count": 100, "tags": ["a", "b"]}
        assert data == expected

    def test_model_dump_json(self):
        """Test model_dump_json produces valid JSON."""

        class TestModel(BaseModel):
            name: str
            count: int = 42

        model = TestModel(name="test", count=100)
        json_str = model.model_dump_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed == {"name": "test", "count": 100}

    def test_model_validate(self):
        """Test model_validate creates instances from data."""

        class TestModel(BaseModel):
            name: str
            count: int = 42

        data = {"name": "test", "count": 100}
        model = TestModel.model_validate(data)

        assert isinstance(model, TestModel)
        assert model.name == "test"
        assert model.count == 100

    def test_model_validate_json(self):
        """Test model_validate_json creates instances from JSON."""

        class TestModel(BaseModel):
            name: str
            count: int = 42

        json_str = '{"name": "test", "count": 100}'
        model = TestModel.model_validate_json(json_str)

        assert isinstance(model, TestModel)
        assert model.name == "test"
        assert model.count == 100

    def test_serialization_roundtrip(self):
        """Test serialization and deserialization roundtrip."""

        class TestModel(BaseModel):
            name: str
            count: int
            tags: list[str]
            metadata: dict[str, Any]

        original = TestModel(
            name="test",
            count=42,
            tags=["a", "b", "c"],
            metadata={"key": "value", "nested": {"inner": "data"}},
        )

        # JSON roundtrip
        json_data = original.model_dump_json()
        restored = TestModel.model_validate_json(json_data)

        assert restored == original
        assert restored.name == original.name
        assert restored.count == original.count
        assert restored.tags == original.tags
        assert restored.metadata == original.metadata

    def test_arbitrary_types_allowed(self):
        """Test arbitrary_types_allowed configuration works."""
        from pathlib import Path

        class TestModel(BaseModel):
            path: Path
            name: str

        path = Path("/test/path")
        model = TestModel(path=path, name="test")

        assert model.path == path
        assert isinstance(model.path, Path)

    def test_model_copy(self):
        """Test model copying functionality."""

        class TestModel(BaseModel):
            name: str
            count: int = 42
            tags: list[str] = []

        original = TestModel(name="test", count=100, tags=["a", "b"])

        # Copy without changes
        copy1 = original.model_copy()
        assert copy1 == original
        assert copy1 is not original

        # Copy with updates
        copy2 = original.model_copy(update={"count": 200})
        assert copy2.name == "test"
        assert copy2.count == 200
        assert copy2.tags == ["a", "b"]


class TestBaseModelPerformance:
    """Performance tests for BaseModel operations."""

    def test_large_model_creation_performance(self):
        """Test performance with large models."""
        import time

        class LargeModel(BaseModel):
            data: dict[str, Any]

        # Create large data structure
        large_data = {f"key_{i}": f"value_{i}" for i in range(1000)}

        start_time = time.time()
        model = LargeModel(data=large_data)
        creation_time = time.time() - start_time

        # Should create reasonably quickly (under 1 second)
        assert creation_time < 1.0
        assert len(model.data) == 1000

    def test_serialization_performance(self):
        """Test serialization performance."""
        import time

        class TestModel(BaseModel):
            items: list[dict[str, Any]]

        # Create model with many items
        items = [{"id": i, "value": f"item_{i}"} for i in range(100)]
        model = TestModel(items=items)

        # Test JSON serialization performance
        start_time = time.time()
        json_data = model.model_dump_json()
        serialization_time = time.time() - start_time

        assert serialization_time < 0.1  # Should be fast
        assert len(json_data) > 1000  # Should have substantial content

        # Test deserialization performance
        start_time = time.time()
        restored = TestModel.model_validate_json(json_data)
        deserialization_time = time.time() - start_time

        assert deserialization_time < 0.1  # Should be fast
        assert restored == model

    def test_validation_performance(self):
        """Test validation performance with complex data."""
        import time

        class NestedModel(BaseModel):
            id: int
            data: dict[str, str]

        class ContainerModel(BaseModel):
            nested_items: list[NestedModel]

        # Create complex nested structure
        nested_data = []
        for i in range(50):
            nested_data.append({
                "id": i,
                "data": {f"key_{j}": f"value_{i}_{j}" for j in range(10)},
            })

        start_time = time.time()
        model = ContainerModel(nested_items=nested_data)
        validation_time = time.time() - start_time

        assert validation_time < 0.5  # Should validate reasonably quickly
        assert len(model.nested_items) == 50
