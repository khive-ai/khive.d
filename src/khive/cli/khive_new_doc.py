"""
khive_new_doc.py - AI-enhanced document scaffolder with template support.

Features
========
* Create structured documents from templates (prompts, conversations, reports)
* AI-specific templates for system prompts, RAG contexts, evaluation reports
* Flexible placeholder substitution with AI context awareness
* Template discovery across multiple locations
* Natural language template descriptions
* JSON output for programmatic use

CLI
---
    khive new-doc <type> <identifier> [--var KEY=VALUE] [--force] [--dry-run]
    khive new-doc --list-templates
    khive new-doc --create-template <name> [--description TEXT]

Exit codes: 0 success · 1 error.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from khive.cli.base import CLIResult, ConfigurableCLICommand, cli_command
from khive.core import TimePolicy
from khive.utils import BaseConfig, ensure_directory, log_msg, safe_write_file, warn_msg


# --- Template Data Classes ---
@dataclass
class Template:
    """Represents a document template."""

    path: Path
    doc_type: str  # e.g., "prompt", "conversation", "report"
    title: str
    description: str
    output_subdir: str
    filename_prefix: str
    meta: dict[str, str]
    body_template: str

    # AI-specific fields
    ai_context: str | None = None  # Context for AI to understand template purpose
    variables: list[str] = field(default_factory=list)  # Expected variables
    tags: list[str] = field(default_factory=list)  # For categorization


@dataclass
class NewDocConfig(BaseConfig):
    """Configuration for document creation."""

    default_destination_base_dir: str = ".khive/docs"
    custom_template_dirs: list[str] = field(default_factory=list)
    default_search_paths: list[str] = field(
        default_factory=lambda: [
            ".khive/templates",
            ".khive/prompts/templates",
            "docs/templates",
        ]
    )
    default_vars: dict[str, str] = field(default_factory=dict)
    ai_mode: bool = True  # Enable AI-specific features

    # Template creation
    template_author: str = "khive"
    template_version: str = "1.0.0"


@cli_command("new-doc")
class NewDocCommand(ConfigurableCLICommand):
    """Create documents from templates with AI enhancements."""

    def __init__(self):
        super().__init__(
            command_name="new-doc",
            description="Create structured documents from templates",
        )

    @property
    def config_filename(self) -> str:
        return "new_doc.toml"

    @property
    def default_config(self) -> dict[str, Any]:
        return {
            "default_destination_base_dir": ".khive/docs",
            "custom_template_dirs": [],
            "default_search_paths": [
                ".khive/templates",
                ".khive/prompts/templates",
                "docs/templates",
            ],
            "default_vars": {
                "author": "AI Assistant",
                "project": "{{PROJECT_NAME}}",
            },
            "ai_mode": True,
        }

    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add new-doc specific arguments."""
        # Main actions
        action_group = parser.add_mutually_exclusive_group()

        # Document creation (positional args)
        parser.add_argument(
            "type_or_template",
            nargs="?",
            help="Document type (e.g., 'prompt', 'report') or template filename",
        )
        parser.add_argument(
            "identifier",
            nargs="?",
            help="Identifier for the new document (e.g., 'chat-001', 'eval-results')",
        )

        # Alternative actions
        action_group.add_argument(
            "--list-templates", action="store_true", help="List all available templates"
        )
        action_group.add_argument(
            "--create-template",
            metavar="NAME",
            help="Create a new template with given name",
        )

        # Options
        parser.add_argument(
            "--dest", type=Path, help="Output directory (overrides default)"
        )
        parser.add_argument(
            "--template-dir", type=Path, help="Additional template directory to search"
        )
        parser.add_argument(
            "--var",
            action="append",
            metavar="KEY=VALUE",
            help="Set template variables (can be repeated)",
        )
        parser.add_argument(
            "--force", action="store_true", help="Overwrite existing files"
        )
        parser.add_argument(
            "--description",
            help="Description for new template (with --create-template)",
        )
        parser.add_argument(
            "--ai-enhance",
            action="store_true",
            help="Use AI to enhance template with better structure",
        )

    def _create_config(self, args: argparse.Namespace) -> NewDocConfig:
        """Create config from arguments and files."""
        config = NewDocConfig(project_root=args.project_root)
        config.update_from_cli_args(args)

        # Load configuration
        loaded_config = self._load_command_config(args.project_root)

        # Apply configuration
        config.default_destination_base_dir = loaded_config.get(
            "default_destination_base_dir", config.default_destination_base_dir
        )
        config.custom_template_dirs = loaded_config.get(
            "custom_template_dirs", config.custom_template_dirs
        )
        config.default_vars = loaded_config.get("default_vars", config.default_vars)
        config.ai_mode = loaded_config.get("ai_mode", config.ai_mode)

        return config

    def _execute(self, args: argparse.Namespace, config: NewDocConfig) -> CLIResult:
        """Execute the document creation command."""
        # List templates
        if args.list_templates:
            return self._list_templates(config, args.template_dir)

        # Create new template
        if args.create_template:
            return self._create_template(
                args.create_template, args.description, config, args.ai_enhance
            )

        # Create document
        if not args.type_or_template or not args.identifier:
            return CLIResult(
                status="failure",
                message="Both template/type and identifier required",
                exit_code=1,
            )

        # Parse variables
        custom_vars = {}
        if args.var:
            for var_spec in args.var:
                if "=" not in var_spec:
                    warn_msg(
                        f"Ignoring malformed --var '{var_spec}' (expected KEY=VALUE)"
                    )
                    continue
                key, value = var_spec.split("=", 1)
                custom_vars[key.strip()] = value.strip()

        return self._create_document(
            args.type_or_template,
            args.identifier,
            config,
            args.dest,
            custom_vars,
            args.force,
            args.template_dir,
        )

    def _list_templates(
        self, config: NewDocConfig, additional_dir: Path | None = None
    ) -> CLIResult:
        """List all available templates."""
        templates = self._discover_templates(config, additional_dir)

        if not templates:
            return CLIResult(
                status="success", message="No templates found", data={"templates": []}
            )

        # Group templates by category
        categorized = {}
        for tpl in templates:
            category = tpl.tags[0] if tpl.tags else "general"
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(tpl)

        # Format output
        template_data = []
        for category, tpls in sorted(categorized.items()):
            for tpl in sorted(tpls, key=lambda t: t.doc_type):
                template_data.append({
                    "category": category,
                    "type": tpl.doc_type,
                    "title": tpl.title,
                    "description": tpl.description,
                    "filename": tpl.path.name,
                    "variables": tpl.variables,
                    "tags": tpl.tags,
                })

        return CLIResult(
            status="success",
            message=f"Found {len(templates)} templates",
            data={"templates": template_data},
        )

    def _create_template(
        self,
        name: str,
        description: str | None,
        config: NewDocConfig,
        ai_enhance: bool,
    ) -> CLIResult:
        """Create a new template."""
        # Determine template type and path
        template_dir = config.project_root / config.default_search_paths[0]
        ensure_directory(template_dir)

        # Sanitize name
        safe_name = re.sub(r"[^\w\-]", "_", name.lower())
        template_path = template_dir / f"{safe_name}_template.md"

        if template_path.exists():
            return CLIResult(
                status="failure",
                message=f"Template already exists: {template_path.name}",
                exit_code=1,
            )

        # Create template content
        template_content = self._generate_template_content(
            name, description, ai_enhance
        )

        if config.dry_run:
            return CLIResult(
                status="success",
                message=f"Would create template: {template_path.name}",
                data={"path": str(template_path), "content": template_content},
            )

        # Write template
        if safe_write_file(template_path, template_content):
            return CLIResult(
                status="success",
                message=f"Created template: {template_path.name}",
                data={"path": str(template_path)},
            )
        return CLIResult(
            status="failure", message="Failed to write template file", exit_code=1
        )

    def _create_document(
        self,
        type_or_template: str,
        identifier: str,
        config: NewDocConfig,
        dest_override: Path | None,
        custom_vars: dict[str, str],
        force: bool,
        additional_template_dir: Path | None,
    ) -> CLIResult:
        """Create a document from a template."""
        # Find template
        templates = self._discover_templates(config, additional_template_dir)
        template = self._find_template(type_or_template, templates)

        if not template:
            available = sorted({t.doc_type for t in templates})
            return CLIResult(
                status="failure",
                message=f"Template '{type_or_template}' not found",
                data={"available_types": available},
                exit_code=1,
            )

        # Prepare output path
        base_dir = dest_override or (
            config.project_root / config.default_destination_base_dir
        )
        output_dir = base_dir / template.output_subdir

        # Sanitize identifier
        safe_id = re.sub(r"[^\w\-.]", "_", identifier)
        filename = f"{template.filename_prefix}-{safe_id}.md"
        output_path = output_dir / filename

        # Check existing file
        if output_path.exists() and not force:
            return CLIResult(
                status="failure",
                message=f"File exists: {output_path.name} (use --force to overwrite)",
                exit_code=1,
            )

        # Prepare variables
        all_vars = {
            **config.default_vars,
            **custom_vars,
            "DATE": dt.date.today().isoformat(),
            "DATETIME": TimePolicy.now_local().isoformat(),
            "IDENTIFIER": identifier,
            "PROJECT_ROOT": str(config.project_root),
            "USER": self._get_user_info(),
        }

        # Render content
        content = self._render_template(template, all_vars)

        if config.dry_run:
            return CLIResult(
                status="success",
                message=f"Would create: {output_path.relative_to(config.project_root)}",
                data={
                    "path": str(output_path),
                    "template": template.doc_type,
                    "content_preview": (
                        content[:500] + "..." if len(content) > 500 else content
                    ),
                },
            )

        # Write file
        ensure_directory(output_dir)
        if safe_write_file(output_path, content):
            return CLIResult(
                status="success",
                message=f"Created: {output_path.relative_to(config.project_root)}",
                data={
                    "path": str(output_path),
                    "template": template.doc_type,
                    "variables_used": list(all_vars.keys()),
                },
            )
        return CLIResult(
            status="failure", message="Failed to write document", exit_code=1
        )

    def _discover_templates(
        self, config: NewDocConfig, additional_dir: Path | None = None
    ) -> list[Template]:
        """Discover all available templates."""
        search_dirs = []

        # Add directories in priority order
        if additional_dir:
            search_dirs.append(additional_dir)

        for custom_dir in config.custom_template_dirs:
            path = Path(custom_dir)
            if path.is_absolute():
                search_dirs.append(path)
            else:
                search_dirs.append(config.project_root / path)

        for default_path in config.default_search_paths:
            search_dirs.append(config.project_root / default_path)

        # Also check package templates
        package_templates = Path(__file__).parent / "templates"
        if package_templates.exists():
            search_dirs.append(package_templates)

        # Find templates
        templates = []
        seen_paths = set()

        for search_dir in search_dirs:
            if not search_dir.is_dir():
                log_msg(f"Template directory not found: {search_dir}")
                continue

            log_msg(f"Searching templates in: {search_dir}")

            for template_path in search_dir.glob("*_template.md"):
                if template_path in seen_paths:
                    continue
                seen_paths.add(template_path)

                try:
                    template = self._parse_template(template_path)
                    templates.append(template)
                    log_msg(f"Found template: {template.doc_type}")
                except Exception as e:
                    warn_msg(f"Error parsing template {template_path.name}: {e}")

        # Add built-in AI templates if none found
        if not templates and config.ai_mode:
            templates.extend(self._get_builtin_ai_templates())

        return templates

    def _parse_template(self, path: Path) -> Template:
        """Parse a template file."""
        content = path.read_text(encoding="utf-8")

        # Parse front matter
        front_matter_match = re.match(
            r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL
        )

        if front_matter_match:
            front_matter_text, body = front_matter_match.groups()
            meta = {}

            for line in front_matter_text.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip().strip("\"'")
        else:
            meta = {}
            body = content

        # Extract template info
        doc_type = meta.get("doc_type", path.stem.replace("_template", ""))
        title = meta.get("title", doc_type.replace("_", " ").title())
        description = meta.get("description", f"{title} template")
        output_subdir = meta.get("output_subdir", f"{doc_type}s")
        filename_prefix = meta.get("filename_prefix", doc_type.upper())

        # AI-specific metadata
        ai_context = meta.get("ai_context", "")
        variables = [
            v.strip() for v in meta.get("variables", "").split(",") if v.strip()
        ]
        tags = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]

        # Find variables in body
        found_vars = set(re.findall(r"\{\{(\w+)\}\}", body))
        variables = list(set(variables) | found_vars)

        return Template(
            path=path,
            doc_type=doc_type,
            title=title,
            description=description,
            output_subdir=output_subdir,
            filename_prefix=filename_prefix,
            meta=meta,
            body_template=body,
            ai_context=ai_context,
            variables=variables,
            tags=tags or ["general"],
        )

    def _find_template(
        self, type_or_name: str, templates: list[Template]
    ) -> Template | None:
        """Find a template by type or filename."""
        # Try exact filename match
        for tpl in templates:
            if tpl.path.name == type_or_name or tpl.path.stem == type_or_name:
                return tpl

        # Try doc_type match (case-insensitive)
        for tpl in templates:
            if tpl.doc_type.lower() == type_or_name.lower():
                return tpl

        # Try fuzzy match on title/description
        search_lower = type_or_name.lower()
        for tpl in templates:
            if (
                search_lower in tpl.title.lower()
                or search_lower in tpl.description.lower()
            ):
                return tpl

        return None

    def _render_template(self, template: Template, variables: dict[str, str]) -> str:
        """Render a template with variables."""
        # Render body
        content = template.body_template

        # Simple variable substitution
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
            content = content.replace(f"{{{key}}}", str(value))

        # Create front matter for output
        output_meta = {
            "title": template.title.replace(
                "{{IDENTIFIER}}", variables.get("IDENTIFIER", "")
            ),
            "date": variables.get("DATE", dt.date.today().isoformat()),
            "type": template.doc_type,
            "identifier": variables.get("IDENTIFIER", ""),
        }

        # Add custom metadata
        for key, value in template.meta.items():
            if key not in [
                "doc_type",
                "output_subdir",
                "filename_prefix",
                "variables",
                "tags",
            ]:
                output_meta[key] = self._substitute_vars(value, variables)

        # Build final document
        lines = ["---"]
        for key, value in output_meta.items():
            lines.append(f"{key}: {json.dumps(value) if ' ' in str(value) else value}")
        lines.extend(["---", "", content])

        return "\n".join(lines)

    def _substitute_vars(self, text: str, variables: dict[str, str]) -> str:
        """Substitute variables in text."""
        for key, value in variables.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
            text = text.replace(f"{{{key}}}", str(value))
        return text

    def _get_user_info(self) -> str:
        """Get current user information."""
        import os
        import pwd

        try:
            return pwd.getpwuid(os.getuid()).pw_gecos.split(",")[0] or os.getlogin()
        except (KeyError, OSError, AttributeError, IndexError) as e:
            # Expected user info retrieval failure - fallback to environment
            import logging
            logging.getLogger(__name__).debug(
                f"User info retrieval failed (using fallback): {e}"
            )
            return os.environ.get("USER", "Unknown")

    def _generate_template_content(
        self, name: str, description: str | None, ai_enhance: bool
    ) -> str:
        """Generate content for a new template."""
        if ai_enhance:
            # Enhanced AI-aware template
            return f"""---
doc_type: {name.lower().replace(" ", "_")}
title: {{{{IDENTIFIER}}}} - {name}
description: {description or f"Template for {name} documents"}
output_subdir: {name.lower().replace(" ", "_")}s
filename_prefix: {name.upper().replace(" ", "_")}
variables: IDENTIFIER, DATE, AUTHOR, PROJECT
tags: ai, documentation
ai_context: |
  This template is used for creating {name} documents.
  It should help structure information in a clear, AI-friendly format.
---

# {{{{title}}}}

**Date**: {{{{DATE}}}}
**Author**: {{{{AUTHOR}}}}
**Project**: {{{{PROJECT}}}}
**Identifier**: {{{{IDENTIFIER}}}}

## Overview

<!-- Brief description of this {name} -->

## Context

<!-- Relevant background information -->

## Content

<!-- Main content goes here -->

### Key Points

1.
2.
3.

## Metadata

- **Created**: {{{{DATE}}}}
- **Last Modified**: {{{{DATE}}}}
- **Status**: Draft
- **Version**: 1.0.0

## References

<!-- Links to related documents, code, or resources -->

---
*Generated with khive document scaffolder*
"""
        # Basic template
        return f"""---
doc_type: {name.lower().replace(" ", "_")}
title: {name} - {{{{IDENTIFIER}}}}
---

# {{{{title}}}}

**Date**: {{{{DATE}}}}
**Identifier**: {{{{IDENTIFIER}}}}

## Content

<!-- Add your content here -->

"""

    def _get_builtin_ai_templates(self) -> list[Template]:
        """Get built-in AI-specific templates."""
        builtin = []

        # System Prompt Template
        builtin.append(
            Template(
                path=Path("builtin://system_prompt"),
                doc_type="system_prompt",
                title="System Prompt",
                description="AI system prompt configuration",
                output_subdir="prompts/system",
                filename_prefix="PROMPT",
                meta={},
                body_template="""# System Prompt: {{IDENTIFIER}}

## Purpose
{{PURPOSE}}

## Core Instructions
You are an AI assistant with the following capabilities and constraints:

### Capabilities
- {{CAPABILITY_1}}
- {{CAPABILITY_2}}
- {{CAPABILITY_3}}

### Constraints
- {{CONSTRAINT_1}}
- {{CONSTRAINT_2}}

## Response Guidelines
1. Always maintain a {{TONE}} tone
2. Prioritize {{PRIORITY}}
3. Format responses as {{FORMAT}}

## Context
{{CONTEXT}}

## Examples
### Good Response
```
{{GOOD_EXAMPLE}}
```

### Avoid
```
{{BAD_EXAMPLE}}
```
""",
                ai_context="System prompt for configuring AI behavior",
                variables=["IDENTIFIER", "PURPOSE", "CAPABILITY_1", "TONE", "PRIORITY"],
                tags=["ai", "prompts", "system"],
            )
        )

        # Conversation Log Template
        builtin.append(
            Template(
                path=Path("builtin://conversation"),
                doc_type="conversation",
                title="AI Conversation Log",
                description="Record of AI conversation for analysis",
                output_subdir="conversations",
                filename_prefix="CONV",
                meta={},
                body_template="""# Conversation: {{IDENTIFIER}}

## Metadata
- **Date**: {{DATE}}
- **Participants**: {{PARTICIPANTS}}
- **Model**: {{MODEL}}
- **Purpose**: {{PURPOSE}}
- **Duration**: {{DURATION}}

## Settings
- Temperature: {{TEMPERATURE}}
- Max Tokens: {{MAX_TOKENS}}
- System Prompt: {{SYSTEM_PROMPT_REF}}

## Conversation

### Turn 1 - User
{{USER_1}}

### Turn 1 - Assistant
{{ASSISTANT_1}}

### Turn 2 - User
{{USER_2}}

### Turn 2 - Assistant
{{ASSISTANT_2}}

## Analysis
### Key Topics
- {{TOPIC_1}}
- {{TOPIC_2}}

### Outcomes
{{OUTCOMES}}

### Follow-up Actions
1. {{ACTION_1}}
2. {{ACTION_2}}
""",
                ai_context="Log AI conversations for review and analysis",
                variables=["IDENTIFIER", "MODEL", "PURPOSE", "PARTICIPANTS"],
                tags=["ai", "conversations", "logs"],
            )
        )

        # Evaluation Report Template
        builtin.append(
            Template(
                path=Path("builtin://evaluation"),
                doc_type="evaluation",
                title="AI Evaluation Report",
                description="Evaluation results for AI models or prompts",
                output_subdir="evaluations",
                filename_prefix="EVAL",
                meta={},
                body_template="""# Evaluation Report: {{IDENTIFIER}}

## Summary
- **Date**: {{DATE}}
- **Evaluator**: {{EVALUATOR}}
- **Subject**: {{SUBJECT}}
- **Overall Score**: {{SCORE}}/10

## Test Configuration
- **Model**: {{MODEL}}
- **Dataset**: {{DATASET}}
- **Metrics**: {{METRICS}}
- **Test Cases**: {{NUM_CASES}}

## Results

### Quantitative Metrics
| Metric | Value | Baseline | Delta |
|--------|-------|----------|-------|
| {{METRIC_1}} | {{VALUE_1}} | {{BASELINE_1}} | {{DELTA_1}} |
| {{METRIC_2}} | {{VALUE_2}} | {{BASELINE_2}} | {{DELTA_2}} |

### Qualitative Assessment
#### Strengths
- {{STRENGTH_1}}
- {{STRENGTH_2}}

#### Weaknesses
- {{WEAKNESS_1}}
- {{WEAKNESS_2}}

## Recommendations
1. {{RECOMMENDATION_1}}
2. {{RECOMMENDATION_2}}

## Appendix
### Test Case Examples
{{TEST_EXAMPLES}}

### Raw Data
{{RAW_DATA_REF}}
""",
                ai_context="Document AI model or prompt evaluation results",
                variables=["IDENTIFIER", "MODEL", "DATASET", "SCORE", "EVALUATOR"],
                tags=["ai", "evaluation", "testing"],
            )
        )

        return builtin


def main(argv: list[str] | None = None) -> None:
    """Entry point for khive CLI integration."""
    cmd = NewDocCommand()
    cmd.run(argv)


if __name__ == "__main__":
    main()
