"""
Tests for khive_new_doc.py - simplified tests for the actual class-based implementation
"""

import argparse
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from khive.cli.khive_new_doc import NewDocCommand, NewDocConfig, Template, main


class TestNewDocConfig:
    """Test NewDocConfig dataclass."""

    def test_new_doc_config_creation(self, tmp_path):
        config = NewDocConfig(project_root=tmp_path)
        assert config.project_root == tmp_path
        assert config.default_destination_base_dir == ".khive/docs"
        assert config.custom_template_dirs == []
        assert config.ai_mode is True

    def test_new_doc_config_with_custom_values(self, tmp_path):
        config = NewDocConfig(
            project_root=tmp_path,
            default_destination_base_dir="custom_docs",
            custom_template_dirs=["templates"],
            ai_mode=False,
        )
        assert config.default_destination_base_dir == "custom_docs"
        assert config.custom_template_dirs == ["templates"]
        assert config.ai_mode is False


class TestTemplate:
    """Test Template dataclass."""

    def test_template_creation(self):
        template = Template(
            path=Path("test_template.md"),
            doc_type="test",
            title="Test Template",
            description="A test template",
            output_subdir="tests",
            filename_prefix="TEST",
            meta={"test": "value"},
            body_template="Test content with {{IDENTIFIER}}",
        )

        assert template.path == Path("test_template.md")
        assert template.doc_type == "test"
        assert template.title == "Test Template"
        assert template.description == "A test template"
        assert template.output_subdir == "tests"
        assert template.filename_prefix == "TEST"
        assert template.meta == {"test": "value"}
        assert template.body_template == "Test content with {{IDENTIFIER}}"
        assert template.ai_context is None
        assert template.variables == []
        assert template.tags == []


class TestNewDocCommand:
    """Test NewDocCommand class."""

    def test_new_doc_command_creation(self):
        cmd = NewDocCommand()
        assert cmd.command_name == "new-doc"
        assert cmd.description == "Create structured documents from templates"
        assert cmd.config_filename == "new_doc.toml"

    def test_default_config(self):
        cmd = NewDocCommand()
        default = cmd.default_config
        assert default["default_destination_base_dir"] == ".khive/docs"
        assert default["custom_template_dirs"] == []
        assert default["ai_mode"] is True
        assert "default_vars" in default

    def test_create_config_basic(self, tmp_path):
        cmd = NewDocCommand()
        args = argparse.Namespace(
            project_root=tmp_path, json_output=False, dry_run=False, verbose=False
        )

        with patch.object(cmd, "_load_command_config", return_value={}):
            config = cmd._create_config(args)
            assert isinstance(config, NewDocConfig)
            assert config.project_root == tmp_path

    def test_parse_template_with_frontmatter(self, tmp_path):
        cmd = NewDocCommand()

        # Create a test template file
        template_content = """---
doc_type: test
title: Test Template
description: A test template
output_subdir: tests
filename_prefix: TEST
variables: IDENTIFIER, DATE
tags: test, sample
---

# Test Template

This is a test template with {{IDENTIFIER}} and {{DATE}}.
"""

        template_path = tmp_path / "test_template.md"
        template_path.write_text(template_content)

        template = cmd._parse_template(template_path)

        assert template.doc_type == "test"
        assert template.title == "Test Template"
        assert template.description == "A test template"
        assert template.output_subdir == "tests"
        assert template.filename_prefix == "TEST"
        assert "IDENTIFIER" in template.variables
        assert "DATE" in template.variables
        assert "test" in template.tags
        assert "sample" in template.tags

    def test_parse_template_without_frontmatter(self, tmp_path):
        cmd = NewDocCommand()

        # Create a test template file without frontmatter
        template_content = "# Simple Template\n\nContent with {{IDENTIFIER}}."

        template_path = tmp_path / "simple_template.md"
        template_path.write_text(template_content)

        template = cmd._parse_template(template_path)

        assert template.doc_type == "simple"  # Derived from filename
        assert template.title == "Simple"
        assert "IDENTIFIER" in template.variables  # Found in body

    def test_find_template_by_doc_type(self):
        cmd = NewDocCommand()

        templates = [
            Template(
                path=Path("test1.md"),
                doc_type="report",
                title="Report Template",
                description="Test",
                output_subdir="reports",
                filename_prefix="RPT",
                meta={},
                body_template="Content",
            ),
            Template(
                path=Path("test2.md"),
                doc_type="prompt",
                title="Prompt Template",
                description="Test",
                output_subdir="prompts",
                filename_prefix="PRM",
                meta={},
                body_template="Content",
            ),
        ]

        found = cmd._find_template("report", templates)
        assert found is not None
        assert found.doc_type == "report"

        found = cmd._find_template("prompt", templates)
        assert found is not None
        assert found.doc_type == "prompt"

        found = cmd._find_template("nonexistent", templates)
        assert found is None

    def test_find_template_by_filename(self):
        cmd = NewDocCommand()

        templates = [
            Template(
                path=Path("report_template.md"),
                doc_type="report",
                title="Report Template",
                description="Test",
                output_subdir="reports",
                filename_prefix="RPT",
                meta={},
                body_template="Content",
            )
        ]

        found = cmd._find_template("report_template.md", templates)
        assert found is not None
        assert found.path.name == "report_template.md"

    def test_render_template(self):
        cmd = NewDocCommand()

        template = Template(
            path=Path("test.md"),
            doc_type="test",
            title="Test Template - {{IDENTIFIER}}",
            description="Test",
            output_subdir="tests",
            filename_prefix="TEST",
            meta={"author": "{{AUTHOR}}"},
            body_template="Hello {{NAME}}, today is {{DATE}}. ID: {{IDENTIFIER}}.",
        )

        variables = {
            "IDENTIFIER": "test-123",
            "NAME": "John",
            "DATE": "2023-01-01",
            "AUTHOR": "Test Author",
        }

        content = cmd._render_template(template, variables)

        assert "test-123" in content
        assert "John" in content
        assert "2023-01-01" in content
        assert "Test Author" in content

    def test_substitute_vars(self):
        cmd = NewDocCommand()

        text = "Hello {{NAME}}, your ID is {{IDENTIFIER}}."
        variables = {"NAME": "John", "IDENTIFIER": "123"}

        result = cmd._substitute_vars(text, variables)
        assert result == "Hello John, your ID is 123."

    def test_get_builtin_ai_templates(self):
        cmd = NewDocCommand()

        templates = cmd._get_builtin_ai_templates()

        assert len(templates) > 0

        # Check that we have expected built-in templates
        template_types = [t.doc_type for t in templates]
        assert "system_prompt" in template_types
        assert "conversation" in template_types
        assert "evaluation" in template_types

        # Check template structure
        for template in templates:
            assert isinstance(template, Template)
            assert template.doc_type
            assert template.title
            assert template.body_template
            assert template.ai_context
            assert template.variables
            assert template.tags

    def test_generate_template_content_basic(self):
        cmd = NewDocCommand()

        content = cmd._generate_template_content("test", "A test template", False)

        assert "doc_type: test" in content
        assert "{{IDENTIFIER}}" in content
        assert "{{DATE}}" in content

    def test_generate_template_content_ai_enhanced(self):
        cmd = NewDocCommand()

        content = cmd._generate_template_content("test", "A test template", True)

        assert "doc_type: test" in content
        assert "ai_context:" in content
        assert "variables:" in content
        assert "tags: ai, documentation" in content


class TestMainFunction:
    """Test the main entry point."""

    def test_main_function_exists(self):
        assert callable(main)

    @patch("khive.cli.khive_new_doc.NewDocCommand")
    def test_main_calls_new_doc_command(self, mock_command_class):
        mock_command = MagicMock()
        mock_command_class.return_value = mock_command

        main(["--help"])

        mock_command_class.assert_called_once()
        mock_command.run.assert_called_once_with(["--help"])


class TestIntegration:
    """Integration tests for NewDocCommand."""

    def test_list_templates_empty(self, tmp_path):
        cmd = NewDocCommand()
        config = NewDocConfig(project_root=tmp_path)

        with patch.object(cmd, "_discover_templates", return_value=[]):
            result = cmd._list_templates(config)

            assert result.status == "success"
            assert result.message == "No templates found"
            assert result.data["templates"] == []

    def test_list_templates_with_templates(self, tmp_path):
        cmd = NewDocCommand()
        config = NewDocConfig(project_root=tmp_path)

        mock_templates = [
            Template(
                path=Path("test.md"),
                doc_type="test",
                title="Test Template",
                description="A test template",
                output_subdir="tests",
                filename_prefix="TEST",
                meta={},
                body_template="Content",
                variables=["IDENTIFIER"],
                tags=["test"],
            )
        ]

        with patch.object(cmd, "_discover_templates", return_value=mock_templates):
            result = cmd._list_templates(config)

            assert result.status == "success"
            assert "Found 1 templates" in result.message
            assert len(result.data["templates"]) == 1
            assert result.data["templates"][0]["type"] == "test"
