"""
khive_new_doc.py - Simple document creation for agents.

No auto-detection. No magic. Just explicit, simple document creation.

Usage:
    # For agent deliverables (agents use this)
    khive new-doc deliverable --agent AGENT_ID --coordination COORD_ID --phase PHASE
    
    # For simple documents
    khive new-doc artifact NAME --coordination COORD_ID
    
    # List templates
    khive new-doc --list-templates
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from khive.cli.base import CLIResult, ConfigurableCLICommand, cli_command
from khive.utils import ensure_directory, safe_write_file


@dataclass
class NewDocConfig:
    """Configuration for new-doc command."""
    project_root: Path = Path.cwd()
    templates_dir: Path = None
    
    def __post_init__(self):
        if self.templates_dir is None:
            # Look for templates in khive package
            import khive
            khive_path = Path(khive.__file__).parent
            self.templates_dir = khive_path / "prompts" / "templates"


@cli_command("new-doc")
class NewDocCommand(ConfigurableCLICommand):
    """Create documents from templates - simple and explicit."""
    
    name = "new-doc"
    help = "Create documents from templates"
    config_class = NewDocConfig
    config_filename = ".khive/new-doc.yaml"
    default_config = {}
    
    def _create_config(self, args: argparse.Namespace) -> NewDocConfig:
        """Create configuration from arguments."""
        return NewDocConfig(project_root=Path.cwd())
    
    def _add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add command arguments."""
        subparsers = parser.add_subparsers(dest="doc_type", help="Document type")
        
        # Deliverable subcommand (for agents)
        deliverable = subparsers.add_parser(
            "deliverable", 
            help="Create agent deliverable"
        )
        deliverable.add_argument(
            "--agent",
            required=True,
            help="Agent ID (e.g., researcher_memory-systems)"
        )
        deliverable.add_argument(
            "--coordination",
            required=True,
            help="Coordination ID from khive plan"
        )
        deliverable.add_argument(
            "--phase",
            required=True,
            help="Phase (discovery, design, implementation, validation)"
        )
        deliverable.add_argument(
            "--name",
            help="Document name (default: AGENT_PHASE_final)"
        )
        
        # Artifact subcommand (for general docs)
        artifact = subparsers.add_parser(
            "artifact",
            help="Create artifact document"
        )
        artifact.add_argument(
            "name",
            help="Document name"
        )
        artifact.add_argument(
            "--coordination",
            required=True,
            help="Coordination ID"
        )
        
        # List templates
        parser.add_argument(
            "--list-templates",
            action="store_true",
            help="List available templates"
        )
    
    async def _execute(self, args: argparse.Namespace, config: NewDocConfig) -> CLIResult:
        """Execute the command."""
        
        # List templates
        if args.list_templates:
            return self._list_templates(config)
        
        # Handle document creation
        if args.doc_type == "deliverable":
            return self._create_deliverable(args, config)
        elif args.doc_type == "artifact":
            return self._create_artifact(args, config)
        else:
            return CLIResult(
                status="error",
                message="Please specify 'deliverable' or 'artifact'",
                exit_code=1
            )
    
    def _list_templates(self, config: NewDocConfig) -> CLIResult:
        """List available templates."""
        templates = []
        
        if config.templates_dir.exists():
            for template_file in config.templates_dir.glob("*.md"):
                templates.append(template_file.stem)
        
        if templates:
            message = f"Available templates:\n" + "\n".join(f"  - {t}" for t in sorted(templates))
        else:
            message = f"No templates found in {config.templates_dir}"
        
        return CLIResult(
            status="success",
            message=message,
            data={"templates": templates}
        )
    
    def _create_deliverable(self, args: argparse.Namespace, config: NewDocConfig) -> CLIResult:
        """Create agent deliverable document."""
        
        # Parse agent ID to get role and domain
        agent_parts = args.agent.split("_", 1)
        if len(agent_parts) != 2:
            return CLIResult(
                status="error",
                message=f"Invalid agent ID format: {args.agent}. Expected: role_domain",
                exit_code=1
            )
        
        role, domain = agent_parts
        phase = args.phase
        coordination_id = args.coordination
        
        # Generate document name if not provided
        doc_name = args.name or f"{role}_{domain}_{phase}_final"
        
        # Create workspace directory structure
        workspace_dir = config.project_root / ".khive" / "workspace" / coordination_id
        phase_dir = workspace_dir / phase / "deliverables"
        ensure_directory(phase_dir)
        
        # Output file path
        output_file = phase_dir / f"{doc_name}.md"
        
        # Load template
        template_file = config.templates_dir / "agent_deliverable_template.md"
        if not template_file.exists():
            # Fallback to simple template
            template_content = self._get_simple_deliverable_template()
        else:
            template_content = template_file.read_text()
        
        # Replace placeholders
        replacements = {
            "{{AGENT_ROLE}}": role,
            "{{AGENT_DOMAIN}}": domain,
            "{{PHASE}}": phase,
            "{{SESSION_ID}}": coordination_id,  # Template uses SESSION_ID
            "{{COORDINATION_ID}}": coordination_id,
            "{{DATE}}": datetime.now().isoformat(),  # Template uses DATE
            "{{TIMESTAMP}}": datetime.now().isoformat(),
            "{{AGENT_ID}}": args.agent,
        }
        
        content = template_content
        for key, value in replacements.items():
            content = content.replace(key, value)
        
        # Write file
        if output_file.exists():
            return CLIResult(
                status="error",
                message=f"File already exists: {output_file}",
                exit_code=1
            )
        
        safe_write_file(output_file, content)
        
        # Update registry (simple JSON, no fancy logic)
        registry_file = workspace_dir / "registry.json"
        registry = {}
        if registry_file.exists():
            try:
                registry = json.loads(registry_file.read_text())
            except:
                registry = {}
        
        # Add entry
        if phase not in registry:
            registry[phase] = []
        
        registry[phase].append({
            "agent": args.agent,
            "role": role,
            "domain": domain,
            "deliverable": str(output_file.relative_to(workspace_dir)),
            "created": datetime.now().isoformat()
        })
        
        safe_write_file(registry_file, json.dumps(registry, indent=2))
        
        return CLIResult(
            status="success",
            message=f"Created deliverable: {output_file}",
            data={
                "file": str(output_file),
                "agent": args.agent,
                "phase": phase,
                "coordination": coordination_id
            }
        )
    
    def _create_artifact(self, args: argparse.Namespace, config: NewDocConfig) -> CLIResult:
        """Create artifact document."""
        
        # Create workspace directory
        workspace_dir = config.project_root / ".khive" / "workspace" / args.coordination / "artifacts"
        ensure_directory(workspace_dir)
        
        # Output file
        output_file = workspace_dir / f"{args.name}.md"
        
        # Simple artifact template
        content = f"""# Artifact: {args.name}

**Coordination ID**: {args.coordination}
**Created**: {datetime.now().isoformat()}

## Content

[Your artifact content here]

## Notes

[Additional notes]
"""
        
        # Write file
        if output_file.exists():
            return CLIResult(
                status="error",
                message=f"File already exists: {output_file}",
                exit_code=1
            )
        
        safe_write_file(output_file, content)
        
        return CLIResult(
            status="success",
            message=f"Created artifact: {output_file}",
            data={
                "file": str(output_file),
                "name": args.name,
                "coordination": args.coordination
            }
        )
    
    def _get_simple_deliverable_template(self) -> str:
        """Get a simple deliverable template if file not found."""
        return """# Agent Deliverable: {{AGENT_ROLE}} ({{AGENT_DOMAIN}})

**Agent ID**: {{AGENT_ID}}
**Phase**: {{PHASE}}
**Coordination ID**: {{COORDINATION_ID}}
**Created**: {{TIMESTAMP}}

## Executive Summary

[1-2 sentences summarizing your work]

## Key Findings

- Finding 1
- Finding 2
- Finding 3

## Analysis/Implementation

[Your detailed work here]

## Dependencies

[What artifacts/work you built upon]

## Recommendations

[Next steps for other agents]

## Artifacts Created

[List any files, code, or documents you created]

---
*Signed: {{AGENT_ID}} at {{TIMESTAMP}}*
"""


def main():
    """CLI entry point."""
    import asyncio
    
    parser = argparse.ArgumentParser(
        prog="khive new-doc",
        description="Create documents from templates - simple and explicit"
    )
    
    subparsers = parser.add_subparsers(dest="doc_type", help="Document type")
    
    # Deliverable subcommand (for agents)
    deliverable = subparsers.add_parser(
        "deliverable", 
        help="Create agent deliverable"
    )
    deliverable.add_argument(
        "--agent",
        required=True,
        help="Agent ID (e.g., researcher_memory-systems)"
    )
    deliverable.add_argument(
        "--coordination",
        required=True,
        help="Coordination ID from khive plan"
    )
    deliverable.add_argument(
        "--phase",
        required=True,
        help="Phase (discovery, design, implementation, validation)"
    )
    deliverable.add_argument(
        "--name",
        help="Document name (default: AGENT_PHASE_final)"
    )
    
    # Artifact subcommand (for general docs)
    artifact = subparsers.add_parser(
        "artifact",
        help="Create artifact document"
    )
    artifact.add_argument(
        "name",
        help="Document name"
    )
    artifact.add_argument(
        "--coordination",
        required=True,
        help="Coordination ID"
    )
    
    # List templates
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List available templates"
    )
    
    args = parser.parse_args()
    
    # Create command and execute
    command = NewDocCommand("new-doc", "Create documents from templates")
    config = NewDocConfig()
    
    # Run async execute
    result = asyncio.run(command._execute(args, config))
    
    print(result.message)
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()