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
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from khive.cli.base import CLIResult, ConfigurableCLICommand, cli_command
from khive.core import TimePolicy
from khive.services.artifacts import (
    ArtifactsConfig,
    Author,
    DocumentType,
    SessionAlreadyExists,
    create_artifacts_service,
)
from khive.utils import (
    KHIVE_CONFIG_DIR,
    BaseConfig,
    ensure_directory,
    log_msg,
    safe_write_file,
    warn_msg,
)


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
            help="Description for new template (with --create-template) or document (with --artifact/--doc)",
        )

        # Session-based document creation
        doc_group = parser.add_mutually_exclusive_group()
        doc_group.add_argument(
            "--artifact",
            metavar="NAME",
            help="Create artifact document in workspace/{session_id}/scratchpad/ with given name",
        )
        doc_group.add_argument(
            "--doc",
            choices=["CRR", "TDS", "RR", "IP", "TI"],
            help="Create official deliverable document in .khive/reports/{TYPE}/",
        )
        parser.add_argument(
            "--session-id",
            "-s",
            help="Session ID for workspace organization (required with --artifact)",
        )
        parser.add_argument(
            "--issue",
            "-i",
            type=int,
            help="GitHub issue number (required with --doc, will be padded to 5 digits)",
        )

        # Agent deliverable specific arguments (for agent_deliverable template)
        parser.add_argument(
            "--phase",
            help="Phase for agent deliverable (e.g., discovery_phase, design_phase)",
        )
        parser.add_argument(
            "--role",
            help="Agent role for deliverable (e.g., researcher, architect)",
        )
        parser.add_argument(
            "--domain",
            help="Agent domain for deliverable (e.g., api-design, backend-development)",
        )
        
        # Convenience shortcuts for common workflows
        parser.add_argument(
            "--quick",
            action="store_true",
            help="Quick mode: auto-detect context and use smart defaults",
        )
        parser.add_argument(
            "--agent-deliverable",
            metavar="NAME",
            help="Shortcut: create agent deliverable with auto-detected context",
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

    def _detect_session_context(self, config: NewDocConfig) -> str | None:
        """Auto-detect session ID from current workspace context."""
        # Check if we're in a workspace directory
        current_path = Path.cwd()
        workspace_base = config.project_root / ".khive" / "workspace"
        
        if workspace_base.exists() and current_path.is_relative_to(workspace_base):
            # We're inside a workspace, extract session ID
            try:
                relative_path = current_path.relative_to(workspace_base)
                session_id = str(relative_path).split('/')[0]
                return session_id
            except (IndexError, ValueError):
                pass
        
        # Check for recent sessions
        if workspace_base.exists():
            sessions = [d for d in workspace_base.iterdir() if d.is_dir()]
            if sessions:
                # Return the most recently modified session
                recent_session = max(sessions, key=lambda d: d.stat().st_mtime)
                return recent_session.name
        
        return None

    def _detect_agent_context(self, config: NewDocConfig) -> tuple[str | None, str | None]:
        """Auto-detect agent role and domain from environment or recent usage."""
        # Check environment variables (set by khive compose)
        role = os.environ.get('KHIVE_AGENT_ROLE')
        domain = os.environ.get('KHIVE_AGENT_DOMAIN')
        
        if role and domain:
            return role, domain
        
        # Check for recent compose usage in current session
        try:
            # Look for .khive/workspace/*/compose_context.json files
            workspace_base = config.project_root / ".khive" / "workspace"
            if workspace_base.exists():
                for session_dir in workspace_base.iterdir():
                    if session_dir.is_dir():
                        context_file = session_dir / "compose_context.json"
                        if context_file.exists():
                            try:
                                with open(context_file) as f:
                                    context = json.load(f)
                                    return context.get('role'), context.get('domain')
                            except (json.JSONDecodeError, KeyError):
                                continue
        except Exception:
            pass
        
        return None, None

    def _prompt_for_missing_info(self, missing_params: dict[str, str]) -> dict[str, str]:
        """Interactively prompt for missing required information."""
        results = {}
        
        # Check if we're in an interactive terminal
        if not os.isatty(0):  # stdin is not a terminal
            # Non-interactive mode - just provide helpful guidance
            param_list = list(missing_params.keys())
            param_descriptions = [missing_params[p] for p in param_list]
            print(f"⚠️  Missing required parameters: {', '.join(param_list)}")
            print(f"💡 In CLI, you can provide these as: khive new-doc <type> <identifier>")
            return {}
        
        for param, description in missing_params.items():
            try:
                value = input(f"Enter {description}: ").strip()
                if value:
                    results[param] = value
                else:
                    print(f"Skipping {param} (empty input)")
            except (KeyboardInterrupt, EOFError):
                print("\nOperation cancelled by user")
                return {}
        
        return results

    def _get_helpful_suggestions(self, config: NewDocConfig) -> str:
        """Generate helpful suggestions based on current context."""
        suggestions = []
        
        # Check available templates
        templates = self._discover_templates(config)
        if templates:
            common_types = [t.doc_type for t in templates[:3]]
            suggestions.append(f"Available templates: {', '.join(common_types)}")
        
        # Check workspace context
        session_id = self._detect_session_context(config)
        if session_id:
            suggestions.append(f"Detected session: {session_id}")
        
        # Check agent context
        role, domain = self._detect_agent_context(config)
        if role and domain:
            suggestions.append(f"Detected agent: {role} ({domain})")
        
        return "\n".join(f"  • {s}" for s in suggestions) if suggestions else ""

    def _show_usage_examples(self, config: NewDocConfig) -> str:
        """Show helpful usage examples based on current context."""
        examples = []
        
        # Detect context for smarter examples
        session_id = self._detect_session_context(config)
        role, domain = self._detect_agent_context(config)
        
        examples.append("📋 Common usage patterns:")
        examples.append("")
        
        # Quick artifact creation
        if session_id:
            examples.append(f"  Create artifact:     khive new-doc --artifact analysis-notes")
            examples.append(f"  Agent deliverable:   khive new-doc --agent-deliverable final-report")
        else:
            examples.append(f"  Create artifact:     khive new-doc --artifact analysis-notes -s session_id")
            examples.append(f"  Agent deliverable:   khive new-doc --agent-deliverable final-report --quick")
        
        examples.append(f"  Official report:     khive new-doc --doc CRR -i 123")
        examples.append(f"  Quick mode:          khive new-doc artifact my-notes --quick")
        examples.append("")
        examples.append("  List templates:      khive new-doc --list-templates")
        
        return "\n".join(examples)

    async def _execute(
        self, args: argparse.Namespace, config: NewDocConfig
    ) -> CLIResult:
        """Execute the document creation command."""
        # List templates
        if args.list_templates:
            return self._list_templates(config, args.template_dir)

        # Create new template
        if args.create_template:
            return self._create_template(args.create_template, args.description, config)

        # Parse variables first (needed for all document types)
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

        # Apply quick mode defaults
        if args.quick:
            # Auto-detect and apply all available context
            auto_role, auto_domain = self._detect_agent_context(config)
            auto_session = self._detect_session_context(config)
            
            if auto_role:
                custom_vars.setdefault("AGENT_ROLE", auto_role)
            if auto_domain:
                custom_vars.setdefault("AGENT_DOMAIN", auto_domain)
            if auto_session:
                custom_vars.setdefault("SESSION_ID", auto_session)
            
            log_msg("Quick mode: Using auto-detected context")

        # Handle convenience shortcuts
        if args.agent_deliverable:
            # Auto-detect context for agent deliverable
            auto_role, auto_domain = self._detect_agent_context(config)
            auto_session = self._detect_session_context(config)
            
            # Add auto-detected values to custom_vars
            if auto_role:
                custom_vars.setdefault("AGENT_ROLE", auto_role)
            if auto_domain:
                custom_vars.setdefault("AGENT_DOMAIN", auto_domain)
            if auto_session:
                custom_vars.setdefault("SESSION_ID", auto_session)
            
            # Add command line args to variables
            if args.role:
                custom_vars["AGENT_ROLE"] = args.role
            if args.domain:
                custom_vars["AGENT_DOMAIN"] = args.domain
            if args.phase:
                custom_vars["PHASE"] = args.phase
            
            # Create agent deliverable document
            return self._create_document(
                "agent_deliverable",
                args.agent_deliverable,
                config,
                args.dest,
                custom_vars,
                args.force,
                args.template_dir,
            )

        # Special handling for artifact documents (session-based)
        if args.artifact:
            session_id = args.session_id
            
            # Auto-detect session if not provided
            if not session_id:
                detected_session = self._detect_session_context(config)
                if detected_session:
                    session_id = detected_session
                    log_msg(f"Auto-detected session: {session_id}")
                else:
                    # Interactive prompting for session ID
                    print("🔍 No session ID provided. Let me help you:")
                    suggestions = self._get_helpful_suggestions(config)
                    if suggestions:
                        print("Context information:")
                        print(suggestions)
                    
                    missing_info = self._prompt_for_missing_info({
                        "session_id": "session ID (or press Enter to create a new one)"
                    })
                    
                    session_id = missing_info.get("session_id")
                    if not session_id:
                        # Generate a new session ID
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        session_id = f"{timestamp}_auto_session"
                        log_msg(f"Created new session: {session_id}")

            artifact_name = args.artifact
            return await self._create_artifact_document(
                "artifact",  # Always use "artifact" as the type
                artifact_name,
                session_id,
                config,
                args.dest,
                custom_vars,
                args.force,
                args.template_dir,
                args.description,
            )

        # Special handling for official deliverable documents (issue-based)
        if args.doc:
            issue_number = args.issue
            
            if not issue_number:
                # Interactive prompting for issue number
                print(f"🔍 Creating {args.doc} report. Let me help you:")
                suggestions = self._get_helpful_suggestions(config)
                if suggestions:
                    print("Context information:")
                    print(suggestions)
                
                missing_info = self._prompt_for_missing_info({
                    "issue": f"GitHub issue number for this {args.doc} report"
                })
                
                issue_str = missing_info.get("issue")
                if not issue_str:
                    return CLIResult(
                        status="failure",
                        message="Issue number is required for official reports. Operation cancelled.",
                        exit_code=1,
                    )
                
                try:
                    issue_number = int(issue_str)
                except ValueError:
                    return CLIResult(
                        status="failure",
                        message=f"Invalid issue number '{issue_str}'. Please enter a valid number.",
                        exit_code=1,
                    )

            return self._create_official_report(
                args.doc,
                issue_number,
                config,
                args.dest,  # dest_override
                custom_vars,
                args.force,
                args.template_dir,
                args.description,
            )

        # Agent deliverables should use regular template system
        # The agent-deliverable template file should be available in templates directory

        # Regular template-based document creation
        type_or_template = args.type_or_template
        identifier = args.identifier
        
        # Interactive prompting for missing required information
        if not type_or_template or not identifier:
            print("🔍 Let me help you create a document:")
            
            # Show context and examples
            suggestions = self._get_helpful_suggestions(config)
            if suggestions:
                print("Context information:")
                print(suggestions)
                print()
            
            print(self._show_usage_examples(config))
            print()
            
            missing_params = {}
            if not type_or_template:
                missing_params["type"] = "template/document type (e.g., 'artifact', 'agent_deliverable')"
            if not identifier:
                missing_params["identifier"] = "document identifier (e.g., 'analysis-001', 'final-report')"
            
            missing_info = self._prompt_for_missing_info(missing_params)
            
            if not missing_info:
                return CLIResult(
                    status="failure",
                    message="Document creation cancelled by user.",
                    exit_code=1,
                )
            
            type_or_template = missing_info.get("type") or type_or_template
            identifier = missing_info.get("identifier") or identifier
            
            if not type_or_template or not identifier:
                return CLIResult(
                    status="failure",
                    message="Both template type and identifier are required. Operation cancelled.",
                    exit_code=1,
                )

        return self._create_document(
            type_or_template,
            identifier,
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
        template_content = self._generate_template_content(name, description)

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
            suggestions = []
            
            # Find similar templates
            search_lower = type_or_template.lower()
            similar = [t.doc_type for t in templates if search_lower in t.doc_type.lower()]
            if similar:
                suggestions.append(f"Did you mean: {', '.join(similar[:3])}")
            
            suggestions.append(f"Available templates: {', '.join(available[:5])}")
            if len(available) > 5:
                suggestions.append(f"... and {len(available) - 5} more (use --list-templates to see all)")
            
            suggestion_text = "\n".join(f"  💡 {s}" for s in suggestions)
            
            return CLIResult(
                status="failure",
                message=f"Template '{type_or_template}' not found.\n\n{suggestion_text}",
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
            relative_path = output_path.relative_to(config.project_root) if config.project_root in output_path.parents else output_path
            return CLIResult(
                status="failure",
                message=f"Document already exists: {relative_path}\n\n  💡 Use --force to overwrite, or choose a different identifier",
                exit_code=1,
            )

        # Auto-detect agent context for agent-related templates
        auto_role, auto_domain = self._detect_agent_context(config)
        auto_session = self._detect_session_context(config)
        
        # Prepare variables with auto-detected context
        all_vars = {
            **config.default_vars,
            **custom_vars,
            "DATE": dt.date.today().isoformat(),
            "DATETIME": TimePolicy.now_local().isoformat(),
            "IDENTIFIER": identifier,
            "PROJECT_ROOT": str(config.project_root),
            "USER": self._get_user_info(),
        }
        
        # Add auto-detected agent context if available
        if auto_role and "AGENT_ROLE" not in all_vars:
            all_vars["AGENT_ROLE"] = auto_role
            log_msg(f"Auto-detected agent role: {auto_role}")
        
        if auto_domain and "AGENT_DOMAIN" not in all_vars:
            all_vars["AGENT_DOMAIN"] = auto_domain
            log_msg(f"Auto-detected agent domain: {auto_domain}")
        
        if auto_session and "SESSION_ID" not in all_vars:
            all_vars["SESSION_ID"] = auto_session
            log_msg(f"Auto-detected session: {auto_session}")
        
        # For agent_deliverable templates, ensure required variables are available
        if template.doc_type == "agent_deliverable":
            missing_agent_vars = {}
            if "AGENT_ROLE" not in all_vars:
                missing_agent_vars["role"] = "agent role (e.g., researcher, architect, implementer)"
            if "AGENT_DOMAIN" not in all_vars:
                missing_agent_vars["domain"] = "agent domain (e.g., api-design, backend-development)"
            if "PHASE" not in all_vars:
                missing_agent_vars["phase"] = "phase name (e.g., discovery_phase, design_phase)"
            
            if missing_agent_vars:
                print(f"🔍 Creating agent deliverable. Missing some context:")
                agent_info = self._prompt_for_missing_info(missing_agent_vars)
                
                if agent_info.get("role"):
                    all_vars["AGENT_ROLE"] = agent_info["role"]
                if agent_info.get("domain"):
                    all_vars["AGENT_DOMAIN"] = agent_info["domain"]
                if agent_info.get("phase"):
                    all_vars["PHASE"] = agent_info["phase"]

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
        """Discover all available templates with copy-from-package logic."""
        # Primary template directory in KHIVE_CONFIG_DIR
        primary_template_dir = KHIVE_CONFIG_DIR / "prompts" / "templates"

        # Package template directory (source for copying)
        package_template_dir = Path(__file__).parent.parent / "prompts" / "templates"

        # Ensure primary template directory exists and copy missing templates
        self._ensure_templates_available(primary_template_dir, package_template_dir)

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

        # Primary template directory from KHIVE_CONFIG_DIR
        search_dirs.append(primary_template_dir)

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

        return templates

    def _ensure_templates_available(self, target_dir: Path, source_dir: Path) -> None:
        """Ensure templates are available in target directory, copying from source if needed."""
        try:
            # Create target directory if it doesn't exist
            ensure_directory(target_dir)

            # Check if source directory exists
            if not source_dir.exists():
                log_msg(f"Package template directory not found: {source_dir}")
                return

            # Copy missing templates from package to KHIVE_CONFIG_DIR
            for source_template in source_dir.glob("*_template.md"):
                target_template = target_dir / source_template.name

                if not target_template.exists():
                    log_msg(f"Copying template: {source_template.name}")
                    try:
                        content = source_template.read_text(encoding="utf-8")
                        safe_write_file(target_template, content)
                    except Exception as e:
                        warn_msg(f"Failed to copy template {source_template.name}: {e}")

        except Exception as e:
            warn_msg(f"Failed to ensure templates available: {e}")

    def _parse_template(self, path: Path) -> Template:
        """Parse a template file."""
        content = path.read_text(encoding="utf-8")

        # Parse front matter using YAML
        front_matter_match = re.match(
            r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL
        )

        if front_matter_match:
            front_matter_text, body = front_matter_match.groups()
            try:
                import yaml

                meta = yaml.safe_load(front_matter_text) or {}
            except yaml.YAMLError:
                # Fallback to simple parsing if YAML fails
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

        # Handle variables - can be comma-separated string or list
        variables_raw = meta.get("variables", "")
        if isinstance(variables_raw, list):
            variables = variables_raw
        else:
            variables = [v.strip() for v in str(variables_raw).split(",") if v.strip()]

        # Handle tags - can be YAML list or comma-separated string
        tags_raw = meta.get("tags", "")
        if isinstance(tags_raw, list):
            tags = tags_raw
        else:
            tags = [t.strip() for t in str(tags_raw).split(",") if t.strip()]

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

        # Add custom metadata (ensure meta is a dict)
        if isinstance(template.meta, dict):
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

    def _substitute_vars(self, text: str | Any, variables: dict[str, str]) -> str | Any:
        """Substitute variables in text."""
        # Handle non-string values (lists, bools, etc.)
        if not isinstance(text, str):
            return text

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

    def _generate_template_content(self, name: str, description: str | None) -> str:
        """Generate minimal template metadata - actual templates should be files."""
        # Generate only minimal metadata, templates should be actual files
        return f"""---
doc_type: {name.lower().replace(" ", "_")}
title: {{{{IDENTIFIER}}}} - {name}
description: {description or f"Template for {name} documents"}
output_subdir: {name.lower().replace(" ", "_")}s
filename_prefix: {name.upper().replace(" ", "_")}
variables: IDENTIFIER, DATE
---

# {{{{IDENTIFIER}}}}

_Template content should be added here_
"""

    async def _create_artifact_document(
        self,
        type_or_template: str,
        identifier: str,
        session_id: str,
        config: NewDocConfig,
        dest_override: Path | None,
        custom_vars: dict[str, str],
        force: bool,
        additional_template_dir: Path | None,
        description: str | None = None,
    ) -> CLIResult:
        """Create an artifact document using the artifacts service."""
        try:
            # Initialize artifacts service
            workspace_dir = dest_override or (
                config.project_root / ".khive" / "workspace"
            )
            artifacts_config = ArtifactsConfig(workspace_root=workspace_dir)
            artifacts_service = create_artifacts_service(artifacts_config)

            # Create author from user info
            author = Author(id=f"cli_user_{session_id}", role="user")

            # Sanitize identifier for document name
            safe_id = re.sub(r"[^\w\-.]", "_", identifier)
            doc_name = f"{type_or_template}_{safe_id}"

            # Check if document already exists and handle accordingly
            doc_exists = await artifacts_service.document_exists(
                session_id, doc_name, DocumentType.SCRATCHPAD
            )

            if doc_exists and not force:
                return CLIResult(
                    status="failure",
                    message=f"Artifact already exists: {doc_name}.md\n\n  💡 Use --force to overwrite, or choose a different name",
                    exit_code=1,
                )

            # Prepare content with template variables
            all_vars = {
                **config.default_vars,
                **custom_vars,
                "DATE": TimePolicy.now_local().isoformat()[:10],
                "DATETIME": TimePolicy.now_local().isoformat(),
                "IDENTIFIER": identifier,
                "SESSION_ID": session_id,
                "TYPE": type_or_template,
                "PROJECT_ROOT": str(config.project_root),
                "USER": self._get_user_info(),
            }

            # Try to find a template for artifacts
            templates = self._discover_templates(config, additional_template_dir)
            artifact_template = None
            for tpl in templates:
                if tpl.doc_type == "artifact" or tpl.doc_type == "scratchpad":
                    artifact_template = tpl
                    break

            if artifact_template:
                # Use template if found
                content = self._render_template(artifact_template, all_vars)
            else:
                # Minimal fallback if no template
                content = f"# {identifier}\n\nSession: {session_id}\nDate: {all_vars['DATE']}\n\n"

            if config.dry_run:
                return CLIResult(
                    status="success",
                    message=f"Would create artifact: workspace/{session_id}/scratchpad/{doc_name}.md",
                    data={
                        "session_id": session_id,
                        "doc_name": doc_name,
                        "content_preview": content[:300] + "...",
                    },
                )

            # Create session if it doesn't exist
            try:
                await artifacts_service.create_session(session_id)
            except SessionAlreadyExists:
                # Session already exists, which is fine
                pass

            # Create or update the document using artifacts service
            if doc_exists and force:
                # Update existing document
                document = await artifacts_service.update_document(
                    session_id=session_id,
                    doc_name=doc_name,
                    doc_type=DocumentType.SCRATCHPAD,
                    new_content=content,
                    author=author,
                )
            else:
                # Create new document
                document = await artifacts_service.create_document(
                    session_id=session_id,
                    doc_name=doc_name,
                    doc_type=DocumentType.SCRATCHPAD,
                    content=content,
                    author=author,
                    description=description or custom_vars.get("description"),
                    agent_role=author.role,
                    agent_domain=None,  # No domain for CLI user
                    metadata={
                        "created_via": "cli",
                        "type_or_template": type_or_template,
                    },
                )

            # Get the actual file path for user feedback
            doc_path = workspace_dir / session_id / "scratchpad" / f"{doc_name}.md"
            relative_path = (
                doc_path.relative_to(config.project_root)
                if config.project_root in doc_path.parents
                else doc_path
            )

            return CLIResult(
                status="success",
                message=f"Created artifact: {relative_path}",
                data={
                    "path": str(doc_path),
                    "session_id": session_id,
                    "document_name": doc_name,
                    "type": "artifact",
                    "version": document.version,
                },
            )

        except Exception as e:
            return CLIResult(
                status="failure", message=f"Failed to create artifact: {e}", exit_code=1
            )

    def _create_official_report(
        self,
        doc_type: str,
        issue_number: int,
        config: NewDocConfig,
        dest_override: Path | None,
        custom_vars: dict[str, str],
        force: bool,
        additional_template_dir: Path | None,
        description: str | None = None,
    ) -> CLIResult:
        """Create official report document in .khive/reports/{TYPE}/ structure."""
        try:
            # Pad issue number to 5 digits
            issue_padded = str(issue_number).zfill(5)

            # Determine output path
            reports_dir = dest_override or (
                config.project_root / ".khive" / "reports" / doc_type
            )
            ensure_directory(reports_dir)

            # Create document name with padded issue number
            doc_name = f"{doc_type}_{issue_padded}"
            doc_path = reports_dir / f"{doc_name}.md"

            # Check if document already exists
            if doc_path.exists() and not force:
                relative_path = (
                    doc_path.relative_to(config.project_root)
                    if config.project_root in doc_path.parents
                    else doc_path
                )
                return CLIResult(
                    status="failure",
                    message=f"Report already exists: {relative_path}\n\n  💡 Use --force to overwrite the existing report",
                    exit_code=1,
                )

            # Find the appropriate template
            templates = self._discover_templates(config, additional_template_dir)

            template = None
            for tpl in templates:
                # Match by template file name pattern
                if tpl.path.stem.startswith(f"{doc_type}_"):
                    template = tpl
                    break

            if not template:
                available_templates = [t.doc_type for t in templates if t.doc_type.startswith(doc_type)]
                return CLIResult(
                    status="failure",
                    message=f"Template for {doc_type} report not found.\n\n  💡 Available report templates: {', '.join(available_templates) if available_templates else 'none'}\n  💡 Use --list-templates to see all available templates",
                    exit_code=1,
                )

            # Prepare variables
            all_vars = {
                **config.default_vars,
                **custom_vars,
                "DATE": TimePolicy.now_local().isoformat()[:10],
                "DATETIME": TimePolicy.now_local().isoformat(),
                "ISSUE_NUMBER": str(issue_number),
                "ISSUE_NUMBER_PADDED": issue_padded,
                "AGENT_ROLE": custom_vars.get("role", "user"),
                "PROJECT_ROOT": str(config.project_root),
                "USER": self._get_user_info(),
            }

            # Render content using existing template system
            content = self._render_template(template, all_vars)

            if config.dry_run:
                return CLIResult(
                    status="success",
                    message=f"Would create {doc_type} report: {doc_path.relative_to(config.project_root)}",
                    data={
                        "path": str(doc_path),
                        "issue": issue_number,
                        "template": doc_type,
                    },
                )

            # Write the report file
            if safe_write_file(doc_path, content):
                relative_path = (
                    doc_path.relative_to(config.project_root)
                    if config.project_root in doc_path.parents
                    else doc_path
                )

                return CLIResult(
                    status="success",
                    message=f"Created {doc_type} report: {relative_path}",
                    data={
                        "path": str(doc_path),
                        "template": doc_type,
                        "issue": issue_number,
                        "issue_padded": issue_padded,
                        "action": "created",
                    },
                )
            return CLIResult(
                status="failure",
                message=f"Failed to write {doc_type} report",
                exit_code=1,
            )

        except Exception as e:
            return CLIResult(
                status="failure",
                message=f"Failed to create {doc_type} document: {e}",
                exit_code=1,
            )


def main(argv: list[str] | None = None) -> None:
    """Entry point for khive CLI integration."""
    cmd = NewDocCommand()
    cmd.run(argv)


if __name__ == "__main__":
    main()
