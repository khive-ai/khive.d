import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .parts import FanoutConfig, FanoutPatterns, IssuePlan, RefinementConfig


@dataclass
class ParsedIssue:
    """Parsed issue data from markdown"""

    # Metadata
    issue_num: int
    flow_name: str
    pattern: str
    project_phase: str
    is_critical_path: bool
    is_experimental: bool
    blocks_issues: list[int]
    enables_issues: list[int]
    dependencies: list[int]
    workspace_path: str

    # Content sections
    system_prompt: str
    description: str
    planning_instructions: str
    synthesis_instructions: str
    context: str

    # Refinement (optional)
    refinement_enabled: bool = False
    refinement_desc: str | None = None
    critic_domain: str | None = None
    gate_instruction: str | None = None
    gates: list[str] | None = None
    skip_refinement: bool = False


class IssueMarkdownParser:
    """Parser for markdown-based issue definitions"""

    def __init__(self, issues_dir: Path):
        self.issues_dir = Path(issues_dir)

    def parse_file(self, file_path: Path) -> ParsedIssue:
        """Parse a single markdown issue file"""
        content = file_path.read_text()

        # Split frontmatter and content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                markdown_content = parts[2].strip()
            else:
                raise ValueError(f"Invalid frontmatter in {file_path}")
        else:
            raise ValueError(f"No frontmatter found in {file_path}")

        # Parse markdown sections
        sections = self._parse_markdown_sections(markdown_content)

        # Create ParsedIssue
        return ParsedIssue(
            # Metadata from frontmatter
            issue_num=frontmatter["issue_num"],
            flow_name=frontmatter["flow_name"],
            pattern=frontmatter["pattern"],
            project_phase=frontmatter["project_phase"],
            is_critical_path=frontmatter["is_critical_path"],
            is_experimental=frontmatter["is_experimental"],
            blocks_issues=frontmatter.get("blocks_issues", []),
            enables_issues=frontmatter.get("enables_issues", []),
            dependencies=frontmatter.get("dependencies", []),
            workspace_path=frontmatter.get(
                "workspace_path", f".khive/workspaces/{frontmatter['flow_name']}"
            ),
            # Content from markdown
            system_prompt=sections.get("system_prompt", ""),
            description=sections.get("description", ""),
            planning_instructions=sections.get("planning_instructions", ""),
            synthesis_instructions=sections.get("synthesis_instructions", ""),
            context=sections.get("context", ""),
            # Refinement config
            refinement_enabled=frontmatter.get("refinement_enabled", False),
            refinement_desc=frontmatter.get("refinement_desc"),
            critic_domain=frontmatter.get("critic_domain"),
            gate_instruction=frontmatter.get("gate_instruction"),
            gates=frontmatter.get("gates"),
            skip_refinement=frontmatter.get("skip_refinement", False),
        )

    def _parse_markdown_sections(self, content: str) -> dict[str, str]:
        """Parse markdown content into sections"""
        sections = {}

        # Define section patterns
        patterns = {
            "system_prompt": r"## System Prompt\s*\n(.*?)(?=\n## |\n# |$)",
            "description": r"## Description\s*\n(.*?)(?=\n## |\n# |$)",
            "planning_instructions": r"## Planning Instructions\s*\n(.*?)(?=\n## |\n# |$)",
            "synthesis_instructions": r"## Synthesis Instructions\s*\n(.*?)(?=\n## |\n# |$)",
            "context": r"## Context\s*\n(.*?)(?=\n## |\n# |$)",
        }

        for section_name, pattern in patterns.items():
            match = re.search(pattern, content, re.DOTALL)
            if match:
                sections[section_name] = match.group(1).strip()
            else:
                sections[section_name] = ""

        return sections

    def parse_all_issues(self) -> dict[str, ParsedIssue]:
        """Parse all markdown issues in the directory"""
        issues = {}

        for md_file in self.issues_dir.glob("*.md"):
            try:
                parsed = self.parse_file(md_file)
                issues[str(parsed.issue_num)] = parsed
            except Exception as e:
                print(f"Error parsing {md_file}: {e}")

        return issues

    def to_issue_plan(self, parsed: ParsedIssue) -> IssuePlan:
        """Convert ParsedIssue to IssuePlan for compatibility"""

        # Map pattern string to enum
        pattern_map = {
            "FANOUT": FanoutPatterns.FANOUT,
            "W_REFINEMENT": FanoutPatterns.W_REFINEMENT,
            "COMPOSITE": FanoutPatterns.COMPOSITE,
        }
        pattern = pattern_map.get(parsed.pattern, FanoutPatterns.FANOUT)

        # Create fanout config
        fanout_config = FanoutConfig(
            initial_desc=parsed.description,
            synth_instruction=parsed.synthesis_instructions,
            planning_instruction=parsed.planning_instructions,
            context=parsed.context,
        )

        # Create refinement config if enabled
        refinement_config = None
        if parsed.refinement_enabled and not parsed.skip_refinement:
            refinement_config = RefinementConfig(
                refinement_desc=parsed.refinement_desc or "Refine implementation",
                critic_domain=parsed.critic_domain or "general",
                gate_instruction=parsed.gate_instruction
                or "Evaluate quality and completeness",
                gates=parsed.gates or ["design"],
            )

        return IssuePlan(
            issue_num=parsed.issue_num,
            flow_name=parsed.flow_name,
            system=parsed.system_prompt,
            pattern=pattern,
            project_phase=parsed.project_phase,
            is_critical_path=parsed.is_critical_path,
            is_experimental=parsed.is_experimental,
            fanout_config=fanout_config,
            refinement_config=refinement_config,
            blocks_issues=parsed.blocks_issues,
            enables_issues=parsed.enables_issues,
            dependencies=parsed.dependencies,
            skip_refinement=parsed.skip_refinement,
        )

    def load_all_issue_plans(self) -> dict[str, IssuePlan]:
        """Load all issues as IssuePlan objects for compatibility"""
        parsed_issues = self.parse_all_issues()
        issue_plans = {}

        for issue_id, parsed in parsed_issues.items():
            issue_plans[issue_id] = self.to_issue_plan(parsed)

        return issue_plans


def load_all_issues(issues_dir: Path) -> dict[str, IssuePlan]:
    """
    Load all issues from markdown files
    """
    issues_dir = Path(issues_dir) if not isinstance(issues_dir, Path) else issues_dir
    if not issues_dir.exists() or not issues_dir.is_dir():
        raise NotADirectoryError(f"{issues_dir} does not exist")

    parser = IssueMarkdownParser(issues_dir)
    return parser.load_all_issue_plans()
