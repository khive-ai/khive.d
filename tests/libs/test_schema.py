"""
Tests for the schema utility module (khive._libs.schema).

This module tests the SchemaUtil class which dynamically generates
Pydantic models from JSON schemas using datamodel-code-generator.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from pydantic import BaseModel, PydanticUserError

from khive._libs.schema import SchemaUtil


class TestSchemaUtil:
    """Test the SchemaUtil class functionality."""

    @pytest.fixture
    def simple_schema_dict(self):
        """Simple schema as a dictionary."""
        return {
            "type": "object",
            "title": "TestModel",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0},
            },
            "required": ["name"],
        }

    @pytest.fixture
    def simple_schema_str(self, simple_schema_dict):
        """Simple schema as a JSON string."""
        return json.dumps(simple_schema_dict)

    @pytest.fixture
    def complex_schema_dict(self):
        """More complex schema with nested objects."""
        return {
            "type": "object",
            "title": "UserProfile",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                    },
                    "required": ["name", "email"],
                },
                "preferences": {
                    "type": "object",
                    "properties": {
                        "theme": {"type": "string", "enum": ["light", "dark"]},
                        "notifications": {"type": "boolean"},
                    },
                },
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["user"],
        }

    @pytest.fixture
    def schema_with_special_title(self):
        """Schema with title containing special characters."""
        return {
            "type": "object",
            "title": "User Profile Model-2024!",
            "properties": {"id": {"type": "integer"}},
        }

    def test_missing_datamodel_code_generator_dependency(self):
        """Test error when datamodel-code-generator is not installed."""
        with patch("khive._libs.schema._HAS_DATAMODEL_CODE_GENERATOR", False):
            with pytest.raises(
                ImportError, match="datamodel-code-generator.*not installed"
            ):
                SchemaUtil.load_pydantic_model_from_schema({"type": "object"})

    @patch("khive._libs.schema._HAS_DATAMODEL_CODE_GENERATOR", True)
    @patch("datamodel_code_generator.generate")
    @patch("khive._libs.schema.importlib.util.spec_from_file_location")
    @patch("khive._libs.schema.importlib.util.module_from_spec")
    def test_successful_model_generation_from_dict(
        self,
        mock_module_from_spec,
        mock_spec_from_file,
        mock_generate,
        simple_schema_dict,
    ):
        """Test successful model generation from dictionary schema."""
        # Setup mocks
        mock_spec = Mock()
        mock_loader = Mock()
        mock_spec.loader = mock_loader
        mock_spec_from_file.return_value = mock_spec

        mock_module = Mock()
        mock_module_from_spec.return_value = mock_module

        # Create a mock model class
        class MockTestModel(BaseModel):
            name: str
            age: int = 0

            @classmethod
            def model_rebuild(cls, **kwargs):
                pass

        mock_module.TestModel = MockTestModel
        mock_module.__dict__ = {"TestModel": MockTestModel}

        with patch("tempfile.TemporaryDirectory") as mock_temp_dir:
            mock_temp_path = Mock()
            mock_temp_path.__truediv__ = lambda self, other: Mock(
                stem="testmodel_model_123", exists=lambda: True
            )
            mock_temp_dir.return_value.__enter__.return_value = mock_temp_path

            result = SchemaUtil.load_pydantic_model_from_schema(simple_schema_dict)

            # Verify the result
            assert result == MockTestModel
            assert issubclass(result, BaseModel)

            # Verify generate was called
            mock_generate.assert_called_once()

    @patch("khive._libs.schema._HAS_DATAMODEL_CODE_GENERATOR", True)
    @patch("datamodel_code_generator.generate")
    @patch("khive._libs.schema.importlib.util.spec_from_file_location")
    @patch("khive._libs.schema.importlib.util.module_from_spec")
    def test_successful_model_generation_from_string(
        self,
        mock_module_from_spec,
        mock_spec_from_file,
        mock_generate,
        simple_schema_str,
    ):
        """Test successful model generation from JSON string schema."""
        # Setup similar to dict test
        mock_spec = Mock()
        mock_loader = Mock()
        mock_spec.loader = mock_loader
        mock_spec_from_file.return_value = mock_spec

        mock_module = Mock()
        mock_module_from_spec.return_value = mock_module

        class MockTestModel(BaseModel):
            name: str

            @classmethod
            def model_rebuild(cls, **kwargs):
                pass

        mock_module.TestModel = MockTestModel
        mock_module.__dict__ = {"TestModel": MockTestModel}

        with patch("tempfile.TemporaryDirectory") as mock_temp_dir:
            mock_temp_path = Mock()
            mock_temp_path.__truediv__ = lambda self, other: Mock(
                stem="testmodel_model_123", exists=lambda: True
            )
            mock_temp_dir.return_value.__enter__.return_value = mock_temp_path

            result = SchemaUtil.load_pydantic_model_from_schema(simple_schema_str)

            assert result == MockTestModel
            mock_generate.assert_called_once()

    def test_invalid_schema_dict(self):
        """Test error handling for invalid schema dictionary."""
        with patch("khive._libs.schema._HAS_DATAMODEL_CODE_GENERATOR", True):
            # Create a dict that can't be JSON serialized
            invalid_schema = {"type": "object", "invalid": object()}

            with pytest.raises(ValueError, match="Invalid dictionary provided"):
                SchemaUtil.load_pydantic_model_from_schema(invalid_schema)

    def test_invalid_schema_string(self):
        """Test error handling for invalid JSON string."""
        with patch("khive._libs.schema._HAS_DATAMODEL_CODE_GENERATOR", True):
            invalid_json = "{'invalid': json}"

            with pytest.raises(ValueError, match="Invalid JSON schema string"):
                SchemaUtil.load_pydantic_model_from_schema(invalid_json)

    def test_invalid_schema_type(self):
        """Test error handling for invalid schema type."""
        with patch("khive._libs.schema._HAS_DATAMODEL_CODE_GENERATOR", True):
            with pytest.raises(
                TypeError, match="Schema must be a JSON string or a dictionary"
            ):
                SchemaUtil.load_pydantic_model_from_schema(123)

    def test_title_sanitization(self, schema_with_special_title):
        """Test that schema titles with special characters are properly sanitized."""
        with patch("khive._libs.schema._HAS_DATAMODEL_CODE_GENERATOR", True):
            with patch("datamodel_code_generator.generate") as mock_generate:
                with patch(
                    "khive._libs.schema.importlib.util.spec_from_file_location"
                ) as mock_spec_from_file:
                    with patch(
                        "khive._libs.schema.importlib.util.module_from_spec"
                    ) as mock_module_from_spec:
                        mock_spec = Mock()
                        mock_loader = Mock()
                        mock_spec.loader = mock_loader
                        mock_spec_from_file.return_value = mock_spec

                        mock_module = Mock()
                        mock_module_from_spec.return_value = mock_module

                        class MockUserProfileModel2024(BaseModel):
                            id: int

                            @classmethod
                            def model_rebuild(cls, **kwargs):
                                pass

                        # The sanitized name should be "UserProfileModel2024"
                        mock_module.UserProfileModel2024 = MockUserProfileModel2024
                        mock_module.__dict__ = {
                            "UserProfileModel2024": MockUserProfileModel2024
                        }

                        with patch("tempfile.TemporaryDirectory") as mock_temp_dir:
                            mock_temp_path = Mock()
                            mock_temp_path.__truediv__ = lambda self, other: Mock(
                                stem="userprofilemodel2024_model_123",
                                exists=lambda: True,
                            )
                            mock_temp_dir.return_value.__enter__.return_value = (
                                mock_temp_path
                            )

                            result = SchemaUtil.load_pydantic_model_from_schema(
                                schema_with_special_title
                            )
                            assert result == MockUserProfileModel2024

    @patch("khive._libs.schema._HAS_DATAMODEL_CODE_GENERATOR", True)
    @patch("datamodel_code_generator.generate")
    def test_generation_failure(self, mock_generate, simple_schema_dict):
        """Test handling of code generation failures."""
        mock_generate.side_effect = Exception("Generation failed")

        with pytest.raises(RuntimeError, match="Failed to generate model code"):
            SchemaUtil.load_pydantic_model_from_schema(simple_schema_dict)

    @patch("khive._libs.schema._HAS_DATAMODEL_CODE_GENERATOR", True)
    @patch("datamodel_code_generator.generate")
    def test_missing_output_file(self, mock_generate, simple_schema_dict):
        """Test handling when generated file doesn't exist."""
        with patch("tempfile.TemporaryDirectory") as mock_temp_dir:
            mock_temp_path = Mock()
            mock_output_file = Mock()
            mock_output_file.exists.return_value = False
            mock_temp_path.__truediv__ = lambda self, other: mock_output_file
            mock_temp_dir.return_value.__enter__.return_value = mock_temp_path

            with pytest.raises(
                FileNotFoundError, match="Generated model file was not created"
            ):
                SchemaUtil.load_pydantic_model_from_schema(simple_schema_dict)

    @patch("khive._libs.schema._HAS_DATAMODEL_CODE_GENERATOR", True)
    @patch("datamodel_code_generator.generate")
    @patch("khive._libs.schema.importlib.util.spec_from_file_location")
    def test_module_import_failure(
        self, mock_spec_from_file, mock_generate, simple_schema_dict
    ):
        """Test handling of module import failures."""
        mock_spec_from_file.return_value = None

        with patch("tempfile.TemporaryDirectory") as mock_temp_dir:
            mock_temp_path = Mock()
            mock_temp_path.__truediv__ = lambda self, other: Mock(
                stem="testmodel_model_123", exists=lambda: True
            )
            mock_temp_dir.return_value.__enter__.return_value = mock_temp_path

            with pytest.raises(ImportError, match="Could not create module spec"):
                SchemaUtil.load_pydantic_model_from_schema(simple_schema_dict)

    @patch("khive._libs.schema._HAS_DATAMODEL_CODE_GENERATOR", True)
    @patch("datamodel_code_generator.generate")
    @patch("khive._libs.schema.importlib.util.spec_from_file_location")
    @patch("khive._libs.schema.importlib.util.module_from_spec")
    def test_missing_model_class(
        self,
        mock_module_from_spec,
        mock_spec_from_file,
        mock_generate,
        simple_schema_dict,
    ):
        """Test handling when expected model class is not found."""
        mock_spec = Mock()
        mock_loader = Mock()
        mock_spec.loader = mock_loader
        mock_spec_from_file.return_value = mock_spec

        mock_module = Mock()
        mock_module_from_spec.return_value = mock_module

        # Mock module without the expected TestModel attribute
        del mock_module.TestModel
        del mock_module.Model  # Also remove fallback
        mock_module.__dict__ = {}

        with patch("tempfile.TemporaryDirectory") as mock_temp_dir:
            mock_temp_path = Mock()
            mock_temp_path.__truediv__ = lambda self, other: Mock(
                stem="testmodel_model_123", exists=lambda: True
            )
            mock_temp_dir.return_value.__enter__.return_value = mock_temp_path

            with pytest.raises(
                AttributeError, match="Could not find expected model class"
            ):
                SchemaUtil.load_pydantic_model_from_schema(simple_schema_dict)

    @patch("khive._libs.schema._HAS_DATAMODEL_CODE_GENERATOR", True)
    @patch("datamodel_code_generator.generate")
    @patch("khive._libs.schema.importlib.util.spec_from_file_location")
    @patch("khive._libs.schema.importlib.util.module_from_spec")
    def test_model_rebuild_failure(
        self,
        mock_module_from_spec,
        mock_spec_from_file,
        mock_generate,
        simple_schema_dict,
    ):
        """Test handling of model rebuild failures."""
        mock_spec = Mock()
        mock_loader = Mock()
        mock_spec.loader = mock_loader
        mock_spec_from_file.return_value = mock_spec

        mock_module = Mock()
        mock_module_from_spec.return_value = mock_module

        class MockTestModel(BaseModel):
            name: str

            @classmethod
            def model_rebuild(cls, **kwargs):
                raise PydanticUserError("Rebuild failed")

        mock_module.TestModel = MockTestModel
        mock_module.__dict__ = {"TestModel": MockTestModel}

        with patch("tempfile.TemporaryDirectory") as mock_temp_dir:
            mock_temp_path = Mock()
            mock_temp_path.__truediv__ = lambda self, other: Mock(
                stem="testmodel_model_123", exists=lambda: True
            )
            mock_temp_dir.return_value.__enter__.return_value = mock_temp_path

            with pytest.raises(RuntimeError, match="Error during model_rebuild"):
                SchemaUtil.load_pydantic_model_from_schema(simple_schema_dict)

    def test_custom_model_name(self, simple_schema_dict):
        """Test using a custom model name."""
        # Remove title from schema
        schema_without_title = simple_schema_dict.copy()
        del schema_without_title["title"]

        with patch("khive._libs.schema._HAS_DATAMODEL_CODE_GENERATOR", True):
            with patch("datamodel_code_generator.generate") as mock_generate:
                with patch(
                    "khive._libs.schema.importlib.util.spec_from_file_location"
                ) as mock_spec_from_file:
                    with patch(
                        "khive._libs.schema.importlib.util.module_from_spec"
                    ) as mock_module_from_spec:
                        mock_spec = Mock()
                        mock_loader = Mock()
                        mock_spec.loader = mock_loader
                        mock_spec_from_file.return_value = mock_spec

                        mock_module = Mock()
                        mock_module_from_spec.return_value = mock_module

                        class MockCustomModel(BaseModel):
                            name: str

                            @classmethod
                            def model_rebuild(cls, **kwargs):
                                pass

                        mock_module.CustomModel = MockCustomModel
                        mock_module.__dict__ = {"CustomModel": MockCustomModel}

                        with patch("tempfile.TemporaryDirectory") as mock_temp_dir:
                            mock_temp_path = Mock()
                            mock_temp_path.__truediv__ = lambda self, other: Mock(
                                stem="custommodel_model_123", exists=lambda: True
                            )
                            mock_temp_dir.return_value.__enter__.return_value = (
                                mock_temp_path
                            )

                            result = SchemaUtil.load_pydantic_model_from_schema(
                                schema_without_title, model_name="CustomModel"
                            )
                            assert result == MockCustomModel

    def test_fallback_to_model_class(self, simple_schema_dict):
        """Test fallback to 'Model' class when expected name not found."""
        with patch("khive._libs.schema._HAS_DATAMODEL_CODE_GENERATOR", True):
            with patch("datamodel_code_generator.generate") as mock_generate:
                with patch(
                    "khive._libs.schema.importlib.util.spec_from_file_location"
                ) as mock_spec_from_file:
                    with patch(
                        "khive._libs.schema.importlib.util.module_from_spec"
                    ) as mock_module_from_spec:
                        with patch("builtins.print") as mock_print:
                            mock_spec = Mock()
                            mock_loader = Mock()
                            mock_spec.loader = mock_loader
                            mock_spec_from_file.return_value = mock_spec

                            mock_module = Mock()
                            mock_module_from_spec.return_value = mock_module

                            class MockModel(BaseModel):
                                name: str

                                @classmethod
                                def model_rebuild(cls, **kwargs):
                                    pass

                            # TestModel doesn't exist, but Model does
                            del mock_module.TestModel
                            mock_module.Model = MockModel
                            mock_module.__dict__ = {"Model": MockModel}

                            with patch("tempfile.TemporaryDirectory") as mock_temp_dir:
                                mock_temp_path = Mock()
                                mock_temp_path.__truediv__ = lambda self, other: Mock(
                                    stem="testmodel_model_123", exists=lambda: True
                                )
                                mock_temp_dir.return_value.__enter__.return_value = (
                                    mock_temp_path
                                )

                                result = SchemaUtil.load_pydantic_model_from_schema(
                                    simple_schema_dict
                                )
                                assert result == MockModel

                                # Should print warning about fallback
                                mock_print.assert_called_once()
                                assert "Warning" in mock_print.call_args[0][0]


class TestSchemaUtilIntegration:
    """Integration tests that might require the actual datamodel-code-generator package."""

    def test_package_availability_check(self):
        """Test that package availability is correctly detected."""
        # This test checks the actual package detection logic
        from khive._libs.schema import _HAS_DATAMODEL_CODE_GENERATOR

        # The result should be a boolean
        assert isinstance(_HAS_DATAMODEL_CODE_GENERATOR, bool)

        # If package is available, import should work
        if _HAS_DATAMODEL_CODE_GENERATOR:
            try:
                from datamodel_code_generator import generate

                assert callable(generate)
            except ImportError:
                pytest.fail("Package detection says available but import fails")
