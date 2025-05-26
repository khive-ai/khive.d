from __future__ import annotations

"""
khive_roo.py - Manage Roo AI mode configurations.

Features
========
* Initialize .khive/prompts structure with default templates
* Synchronize roo_rules to .roo directory for Roo/Cursor integration
* Generate .roomodes JSON file from mode definitions
* Support custom AI modes and templates
* Validate mode configurations

CLI
---
    khive roo                    # Full synchronization
    khive roo --init            # Initialize templates only
    khive roo --sync            # Sync to .roo only
    khive roo --generate        # Generate .roomodes only
    khive roo --validate        # Validate modes without changes

Exit codes: 0 success · 1 error.
"""


import importlib.resources
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from khive.cli.base import BaseCLICommand, CLIResult, cli_command
from khive.utils import (
    BaseConfig,
    ensure_directory,
    error_msg,
    info_msg,
    log_msg,
    safe_write_file,
    warn_msg,
)

# Try to import YAML support
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    yaml = None
    YAML_AVAILABLE = False


# Constants
KHIVE_DIR_NAME = ".khive"
PROMPTS_DIR_NAME = "services/roo/prompts"
ROO_RULES_DIR_NAME = "roo_rules"
TEMPLATES_DIR_NAME = "templates"
TARGET_ROO_DIR_NAME = ".roo"
OUTPUT_JSON_NAME = ".roomodes"


@dataclass
class RooMode:
    """Represents a Roo AI mode configuration."""

    slug: str
    name: str
    groups: List[str] = field(default_factory=list)
    source: str = "project"
    role_definition: str = ""
    custom_instructions: str = ""
    file_path: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "slug": self.slug,
            "name": self.name,
            "groups": self.groups,
            "source": self.source,
            "roleDefinition": self.role_definition,
            "customInstructions": self.custom_instructions,
        }

    def validate(self) -> List[str]:
        """Validate the mode configuration."""
        issues = []

        if not self.slug:
            issues.append("Missing required field: slug")
        if not self.name:
            issues.append("Missing required field: name")
        if not self.role_definition:
            issues.append("Missing or empty Role Definition section")
        if not self.custom_instructions:
            issues.append("Missing or empty Custom Instructions section")

        return issues


@dataclass
class RooConfig(BaseConfig):
    """Configuration for Roo command."""

    # Paths
    khive_prompts_dir: Path = field(init=False)
    source_roo_rules_dir: Path = field(init=False)
    source_templates_dir: Path = field(init=False)
    target_roo_dir: Path = field(init=False)
    output_json_path: Path = field(init=False)

    # Options
    validate_only: bool = False
    init_only: bool = False
    sync_only: bool = False
    generate_only: bool = False

    def __post_init__(self):
        """Initialize computed paths."""
        super().__post_init__()
        self.khive_prompts_dir = self.khive_config_dir / PROMPTS_DIR_NAME
        self.source_roo_rules_dir = self.khive_prompts_dir / ROO_RULES_DIR_NAME
        self.source_templates_dir = self.khive_prompts_dir / TEMPLATES_DIR_NAME
        self.target_roo_dir = self.project_root / TARGET_ROO_DIR_NAME
        self.output_json_path = self.project_root / OUTPUT_JSON_NAME


@cli_command("roo")
class RooCommand(BaseCLICommand):
    """Manage Roo AI mode configurations."""

    def __init__(self):
        super().__init__(
            command_name="roo", description="Manage Roo AI mode configurations"
        )

    def _add_arguments(self, parser) -> None:
        """Add roo-specific arguments."""
        parser.add_argument(
            "--init",
            action="store_true",
            help="Initialize .khive/prompts structure only",
        )
        parser.add_argument(
            "--sync", action="store_true", help="Synchronize to .roo directory only"
        )
        parser.add_argument(
            "--generate", action="store_true", help="Generate .roomodes file only"
        )
        parser.add_argument(
            "--validate",
            action="store_true",
            help="Validate mode configurations without making changes",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Remove generated .roo and .roomodes files",
        )

    def _create_config(self, args) -> RooConfig:
        """Create RooConfig from arguments."""
        config = RooConfig(project_root=args.project_root)
        config.update_from_cli_args(args)

        # Set operation flags
        config.validate_only = args.validate
        config.init_only = args.init
        config.sync_only = args.sync
        config.generate_only = args.generate

        return config

    def _execute(self, args, config: RooConfig) -> CLIResult:
        """Execute the roo command."""
        # Handle clean operation
        if args.clean:
            return self._clean_generated_files(config)

        # Handle validate operation
        if config.validate_only:
            return self._validate_modes(config)

        # Handle specific operations
        if config.init_only:
            return self._initialize_structure(config)

        if config.sync_only:
            return self._sync_to_roo(config)

        if config.generate_only:
            return self._generate_roomodes(config)

        # Default: run full process
        return self._run_full_process(config)

    def _run_full_process(self, config: RooConfig) -> CLIResult:
        """Run the complete roo setup process."""
        steps = []

        # Step 1: Initialize structure
        log_msg("Step 1: Initializing .khive/prompts structure...")
        init_result = self._initialize_structure(config)
        steps.append({"step": "initialize", "result": init_result.status})

        if init_result.status != "success":
            return CLIResult(
                status="failure",
                message="Failed to initialize .khive structure",
                data={"steps": steps},
                exit_code=1,
            )

        # Step 2: Sync to .roo
        log_msg("Step 2: Synchronizing to .roo directory...")
        sync_result = self._sync_to_roo(config)
        steps.append({"step": "sync", "result": sync_result.status})

        if sync_result.status != "success":
            return CLIResult(
                status="failure",
                message="Failed to synchronize to .roo directory",
                data={"steps": steps},
                exit_code=1,
            )

        # Step 3: Generate .roomodes
        log_msg("Step 3: Generating .roomodes file...")
        generate_result = self._generate_roomodes(config)
        steps.append({"step": "generate", "result": generate_result.status})

        if generate_result.status != "success":
            return CLIResult(
                status="failure",
                message="Failed to generate .roomodes file",
                data={"steps": steps},
                exit_code=1,
            )

        return CLIResult(
            status="success",
            message="Roo configuration completed successfully",
            data={
                "steps": steps,
                "modes_count": generate_result.data.get("modes_count", 0),
            },
        )

    def _initialize_structure(self, config: RooConfig) -> CLIResult:
        """Initialize .khive/prompts structure with templates."""
        # Create directories
        ensure_directory(config.khive_config_dir)
        ensure_directory(config.khive_prompts_dir)

        # Get package source path
        source_path = self._get_package_source_path()
        if not source_path:
            return CLIResult(
                status="failure",
                message="Failed to locate source templates",
                exit_code=1,
            )

        copied_items = []

        # Copy roo_rules if needed
        if not config.source_roo_rules_dir.exists() or not any(
            config.source_roo_rules_dir.iterdir()
        ):
            source_roo_rules = source_path / ROO_RULES_DIR_NAME
            if source_roo_rules.exists():
                log_msg(f"Copying roo_rules from package...")
                try:
                    if config.source_roo_rules_dir.exists():
                        shutil.rmtree(config.source_roo_rules_dir)
                    shutil.copytree(source_roo_rules, config.source_roo_rules_dir)
                    copied_items.append("roo_rules")
                except Exception as e:
                    return CLIResult(
                        status="failure",
                        message=f"Failed to copy roo_rules: {e}",
                        exit_code=1,
                    )
            else:
                warn_msg(f"Source roo_rules not found at {source_roo_rules}")

        # Copy templates if needed
        if not config.source_templates_dir.exists() or not any(
            config.source_templates_dir.iterdir()
        ):
            source_templates = source_path / TEMPLATES_DIR_NAME
            if source_templates.exists():
                log_msg(f"Copying templates from package...")
                try:
                    if config.source_templates_dir.exists():
                        shutil.rmtree(config.source_templates_dir)
                    shutil.copytree(source_templates, config.source_templates_dir)
                    copied_items.append("templates")
                except Exception as e:
                    return CLIResult(
                        status="failure",
                        message=f"Failed to copy templates: {e}",
                        exit_code=1,
                    )
            else:
                warn_msg(f"Source templates not found at {source_templates}")

        if copied_items:
            return CLIResult(
                status="success",
                message=f"Initialized .khive/prompts with: {', '.join(copied_items)}",
                data={"copied": copied_items},
            )
        else:
            return CLIResult(
                status="success",
                message=".khive/prompts already initialized",
                data={"copied": []},
            )

    def _sync_to_roo(self, config: RooConfig) -> CLIResult:
        """Synchronize roo_rules to .roo directory."""
        if not config.source_roo_rules_dir.is_dir():
            return CLIResult(
                status="failure",
                message=f"Source rules directory not found: {config.source_roo_rules_dir}",
                exit_code=1,
            )

        # Remove existing .roo if it exists
        if config.target_roo_dir.exists():
            log_msg(f"Removing existing .roo directory...")
            try:
                shutil.rmtree(config.target_roo_dir)
            except Exception as e:
                return CLIResult(
                    status="failure",
                    message=f"Failed to remove existing .roo: {e}",
                    exit_code=1,
                )

        # Copy to .roo
        log_msg(f"Copying rules to .roo directory...")
        try:
            shutil.copytree(config.source_roo_rules_dir, config.target_roo_dir)

            # Count files copied
            file_count = sum(1 for _ in config.target_roo_dir.rglob("*") if _.is_file())

            return CLIResult(
                status="success",
                message=f"Synchronized {file_count} files to .roo directory",
                data={"files_copied": file_count},
            )
        except Exception as e:
            return CLIResult(
                status="failure", message=f"Failed to copy to .roo: {e}", exit_code=1
            )

    def _generate_roomodes(self, config: RooConfig) -> CLIResult:
        """Generate .roomodes JSON file from mode definitions."""
        if not YAML_AVAILABLE:
            return CLIResult(
                status="failure",
                message="PyYAML is required for parsing mode files. Install with: pip install PyYAML",
                exit_code=1,
            )

        if not config.target_roo_dir.is_dir():
            return CLIResult(
                status="failure",
                message=f"Target .roo directory not found. Run sync first.",
                exit_code=1,
            )

        # Parse all modes
        modes = self._discover_modes(config)

        # Validate modes
        validation_issues = []
        for mode in modes:
            issues = mode.validate()
            if issues:
                validation_issues.append({
                    "mode": mode.slug,
                    "file": str(mode.file_path) if mode.file_path else "unknown",
                    "issues": issues,
                })

        if validation_issues and not config.dry_run:
            for issue in validation_issues:
                warn_msg(
                    f"Mode '{issue['mode']}' has issues: {', '.join(issue['issues'])}"
                )

        # Generate JSON
        output_data = {"customModes": [mode.to_dict() for mode in modes]}

        if config.dry_run:
            return CLIResult(
                status="success",
                message=f"Would generate .roomodes with {len(modes)} modes",
                data={
                    "modes_count": len(modes),
                    "modes": [m.slug for m in modes],
                    "validation_issues": validation_issues,
                },
            )

        # Write JSON file
        try:
            json_content = json.dumps(output_data, indent=2, ensure_ascii=False)
            if safe_write_file(config.output_json_path, json_content):
                return CLIResult(
                    status="success",
                    message=f"Generated .roomodes with {len(modes)} modes",
                    data={
                        "modes_count": len(modes),
                        "modes": [m.slug for m in modes],
                        "validation_issues": validation_issues,
                    },
                )
            else:
                return CLIResult(
                    status="failure",
                    message="Failed to write .roomodes file",
                    exit_code=1,
                )
        except Exception as e:
            return CLIResult(
                status="failure",
                message=f"Error generating .roomodes: {e}",
                exit_code=1,
            )

    def _validate_modes(self, config: RooConfig) -> CLIResult:
        """Validate mode configurations without making changes."""
        if not YAML_AVAILABLE:
            return CLIResult(
                status="failure",
                message="PyYAML is required for validating mode files",
                exit_code=1,
            )

        if not config.target_roo_dir.is_dir():
            return CLIResult(
                status="failure",
                message=".roo directory not found. Run sync first.",
                exit_code=1,
            )

        modes = self._discover_modes(config)
        validation_results = []

        for mode in modes:
            issues = mode.validate()
            validation_results.append({
                "mode": mode.slug,
                "name": mode.name,
                "file": (
                    str(mode.file_path.relative_to(config.project_root))
                    if mode.file_path
                    else "unknown"
                ),
                "valid": len(issues) == 0,
                "issues": issues,
            })

        valid_count = sum(1 for r in validation_results if r["valid"])
        total_count = len(validation_results)

        return CLIResult(
            status="success" if valid_count == total_count else "warning",
            message=f"Validated {total_count} modes: {valid_count} valid, {total_count - valid_count} with issues",
            data={"validation_results": validation_results},
        )

    def _clean_generated_files(self, config: RooConfig) -> CLIResult:
        """Remove generated .roo and .roomodes files."""
        removed = []

        # Remove .roo directory
        if config.target_roo_dir.exists():
            try:
                shutil.rmtree(config.target_roo_dir)
                removed.append(".roo directory")
                info_msg("Removed .roo directory")
            except Exception as e:
                error_msg(f"Failed to remove .roo: {e}")

        # Remove .roomodes file
        if config.output_json_path.exists():
            try:
                config.output_json_path.unlink()
                removed.append(".roomodes file")
                info_msg("Removed .roomodes file")
            except Exception as e:
                error_msg(f"Failed to remove .roomodes: {e}")

        if removed:
            return CLIResult(
                status="success",
                message=f"Cleaned: {', '.join(removed)}",
                data={"removed": removed},
            )
        else:
            return CLIResult(
                status="success",
                message="No generated files to clean",
                data={"removed": []},
            )

    def _discover_modes(self, config: RooConfig) -> List[RooMode]:
        """Discover all mode definitions in .roo directory."""
        modes = []

        # Check mode directories
        for item in sorted(config.target_roo_dir.iterdir()):
            if item.is_dir():
                # Look for mode readme files
                for readme_name in ["_MODE_INSTRUCTION.md", "readme.md", "README.md"]:
                    readme_path = item / readme_name
                    if readme_path.exists():
                        log_msg(f"Found mode in directory: {item.name}")
                        mode = self._parse_mode_file(readme_path, item.name)
                        if mode:
                            modes.append(mode)
                        break

        # Check standalone mode files
        for item in sorted(config.target_roo_dir.iterdir()):
            if item.is_file() and item.suffix == ".md":
                # Skip non-mode files
                if item.name.lower() in [
                    "readme.md",
                    "index.md",
                    "contributing.md",
                    "license.md",
                ]:
                    continue

                log_msg(f"Found potential mode file: {item.name}")
                mode = self._parse_mode_file(item, None)
                if mode:
                    modes.append(mode)

        return modes

    def _parse_mode_file(
        self, filepath: Path, dir_name: Optional[str]
    ) -> Optional[RooMode]:
        """Parse a mode definition file."""
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception as e:
            error_msg(f"Error reading {filepath}: {e}")
            return None

        # Extract YAML front matter
        front_matter_match = re.match(
            r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL
        )
        if not front_matter_match:
            warn_msg(f"No YAML front matter found in {filepath.name}")
            return None

        front_matter_text, markdown_content = front_matter_match.groups()

        # Parse YAML
        try:
            front_matter = yaml.safe_load(front_matter_text)
            if not isinstance(front_matter, dict):
                warn_msg(f"Invalid YAML structure in {filepath.name}")
                return None
        except yaml.YAMLError as e:
            warn_msg(f"YAML parsing error in {filepath.name}: {e}")
            return None

        # Extract sections
        role_def = self._extract_section(markdown_content, "Role Definition")
        custom_inst = self._extract_section(markdown_content, "Custom Instructions")

        # Determine slug
        default_slug = dir_name or filepath.stem

        # Create mode
        mode = RooMode(
            slug=front_matter.get("slug", default_slug),
            name=front_matter.get("name", default_slug.replace("_", " ").title()),
            groups=front_matter.get("groups", []),
            source=front_matter.get("source", "project"),
            role_definition=role_def,
            custom_instructions=custom_inst,
            file_path=filepath,
        )

        return mode

    def _extract_section(self, content: str, heading: str) -> str:
        """Extract a section from markdown content."""
        pattern = re.compile(
            rf"^#{{{2, 3}}}\s+{re.escape(heading)}\s*\n(.*?)(?=\n^#{{{2, 3}}}\s+|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        match = pattern.search(content)
        return match.group(1).strip() if match else ""

    def _get_package_source_path(self) -> Optional[Path]:
        """Get path to bundled source templates."""
        try:
            # Try importlib.resources for installed package
            return importlib.resources.files("khive.prompts")
        except (ModuleNotFoundError, AttributeError):
            log_msg("Could not locate package templates via importlib.resources")

        # Fallback for development
        dev_path = Path(__file__).resolve().parent.parent / "prompts"
        if dev_path.is_dir():
            log_msg(f"Using development path: {dev_path}")
            return dev_path

        error_msg("Source templates directory not found")
        return None


def main(argv: Optional[List[str]] = None) -> None:
    """Entry point for khive CLI integration."""
    cmd = RooCommand()
    cmd.run(argv)


if __name__ == "__main__":
    main()
