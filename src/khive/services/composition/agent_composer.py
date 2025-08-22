# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
# SPDX-License-Identifier: Apache-2.0

import json
import sys
import threading
from pathlib import Path
from typing import Any

import yaml

from .parts import AgentCompositionRequest

__all__ = ("AgentComposer",)


class AgentComposer:
    """Compose agent persona from role + domain specifications"""

    # Class-level lock for file system access
    _file_lock = threading.Lock()

    def __init__(self, base_path: str | None = None):
        # Use khive's internal resources by default
        base_path = Path(__file__).parent if base_path is None else Path(base_path)

        # Set base path first so _is_safe_path can access it
        self.base_path = base_path.resolve()  # Resolve to absolute path

        # Validate base path is safe
        if not self._is_safe_path(self.base_path):
            raise ValueError(f"Unsafe base path: {self.base_path}")

        self.roles_path = self.base_path / "roles"
        self.domains_path = self.base_path / "domains"

        # Load agent prompts template for PromptFactory
        self._agent_prompts = self._load_agent_prompts()

        # Load domain name mapper for canonicalization
        self._domain_mapper = self._load_domain_mapper()

        # Track seen role-domain pairs to prevent duplicates
        self._seen_pairs: set = set()

    def load_yaml(self, file_path: Path) -> dict[str, Any]:
        """Load YAML file safely with validation"""
        try:
            # Validate file path to prevent directory traversal
            if not self._is_safe_path(file_path):
                raise ValueError(f"Unsafe file path detected: {file_path}")

            # Check file size limit (max 10MB)
            if file_path.stat().st_size > 10 * 1024 * 1024:
                print(f"Error: File {file_path} exceeds size limit", file=sys.stderr)
                return {}

            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                # Additional size check after reading
                if len(content) > 10 * 1024 * 1024:
                    print(
                        f"Error: Content in {file_path} exceeds size limit",
                        file=sys.stderr,
                    )
                    return {}
                return yaml.safe_load(content)
        except yaml.YAMLError as e:
            print(f"YAML parsing error in {file_path}: {e}", file=sys.stderr)
            return {}
        except ValueError as e:
            # Re-raise security-related errors (like unsafe file paths)
            if "Unsafe file path" in str(e):
                raise
            print(f"Error loading {file_path}: {e}", file=sys.stderr)
            return {}
        except Exception as e:
            print(f"Error loading {file_path}: {e}", file=sys.stderr)
            return {}

    def load_agent_role(self, role: str) -> dict[str, Any]:
        """Load base agent role specification with enhanced error handling"""
        if not role or not isinstance(role, str):
            raise ValueError("Role must be a non-empty string")

        # Sanitize role name
        safe_role = self._sanitize_input(role)

        # Try .md file first
        agent_file = self.roles_path / f"{safe_role}.md"

        if not agent_file.exists():
            # Try .yaml as fallback
            agent_file = self.roles_path / f"{safe_role}.yaml"
            if not agent_file.exists():
                available_roles = self.list_available_roles()
                raise ValueError(
                    f"Agent role '{role}' not found in {self.roles_path}. "
                    f"Available roles: {', '.join(available_roles[:10])}"
                )

        if agent_file.suffix == ".yaml":
            return self.load_yaml(agent_file)

        # Parse markdown to extract YAML blocks and content
        with open(agent_file) as f:
            content = f.read()

        # Extract identity block
        identity = {}
        if "```yaml" in content:
            yaml_start = content.find("```yaml") + 7
            yaml_end = content.find("```", yaml_start)
            yaml_content = content[yaml_start:yaml_end].strip()
            try:
                identity = yaml.safe_load(yaml_content)
            except yaml.YAMLError as e:
                # Malformed YAML - raise ValueError as expected by tests
                raise ValueError(f"Invalid YAML in role file: {e}")

        # Extract other sections and sanitize them
        return {
            "identity": identity,
            "role": self._sanitize_context(self._extract_section(content, "## Role")),
            "purpose": self._sanitize_context(
                self._extract_section(content, "## Purpose")
            ),
            "capabilities": self._sanitize_context(
                self._extract_section(content, "## Core Capabilities")
            ),
            "decision_logic": self._sanitize_context(
                self._extract_section(content, "## Decision Logic")
            ),
            "output_schema": self._extract_section(content, "## Output Schema"),
            "content": content,  # Full content for reference
        }

    def load_domain_expertise(self, domain: str) -> dict[str, Any]:
        """Load domain expertise module from hierarchical taxonomy with validation"""
        if not domain or not isinstance(domain, str):
            print(
                f"Warning: Invalid domain '{domain}', proceeding without domain expertise",
                file=sys.stderr,
            )
            return {}

        # Sanitize domain name
        safe_domain = self._sanitize_input(domain)

        # First try the old flat structure for backward compatibility
        domain_file = self.domains_path / f"{safe_domain}.yaml"

        if domain_file.exists():
            return self.load_yaml(domain_file)

        # Search recursively in taxonomy structure
        for yaml_file in self.domains_path.rglob(f"{safe_domain}.yaml"):
            return self.load_yaml(yaml_file)

        # Provide helpful error message with available domains
        available_domains = self.list_available_domains()
        print(
            f"Warning: Domain '{domain}' not found in taxonomy. "
            f"Available domains include: {', '.join(available_domains[:5])}... "
            f"(total: {len(available_domains)})",
            file=sys.stderr,
        )
        return {}

    def compose_agent(
        self, role: str, domains: str | None = None, context: str | None = None
    ) -> dict[str, Any]:
        """Compose complete agent persona from role + domain(s) + optional context"""
        # Use Pydantic validation for type safety
        try:
            request = AgentCompositionRequest(
                role=role, domains=domains, context=context
            )
        except Exception as e:
            raise ValueError(f"Invalid composition request: {e}") from e

        # Use validated and sanitized inputs
        role = request.role
        domains = request.domains
        context = request.context

        # Additional sanitization
        role = self._sanitize_input(role)
        if domains:
            domains = self._sanitize_input(domains)
        if context:
            context = self._sanitize_context(context)

        # Load base role
        agent_spec = self.load_agent_role(role)

        # Add optional context
        if context:
            agent_spec["task_context"] = context

        # If no domains specified, return base role
        if not domains:
            return agent_spec

        # Parse multiple domains (comma-separated)
        domain_list = [d.strip() for d in domains.split(",")]

        # Track all domains loaded
        agent_spec["domains"] = []
        agent_spec["domain_patterns"] = {}
        agent_spec["domain_rules"] = {}
        agent_spec["domain_tools"] = {}
        merged_thresholds = {}

        # Load and merge each domain's expertise
        for domain in domain_list:
            domain_spec = self.load_domain_expertise(domain)

            if domain_spec:
                # Track this domain
                agent_spec["domains"].append(domain_spec.get("domain", {}))

                # Merge knowledge patterns
                if "knowledge_patterns" in domain_spec:
                    for pattern_type, patterns in domain_spec[
                        "knowledge_patterns"
                    ].items():
                        if pattern_type not in agent_spec["domain_patterns"]:
                            agent_spec["domain_patterns"][pattern_type] = []
                        agent_spec["domain_patterns"][pattern_type].extend(patterns)

                # Merge decision rules
                if "decision_rules" in domain_spec:
                    for rule_type, rules in domain_spec["decision_rules"].items():
                        if rule_type not in agent_spec["domain_rules"]:
                            agent_spec["domain_rules"][rule_type] = []
                        if isinstance(rules, list):
                            agent_spec["domain_rules"][rule_type].extend(rules)
                        else:
                            agent_spec["domain_rules"][rule_type] = rules

                # Merge specialized tools
                if "specialized_tools" in domain_spec:
                    for category, tool_list in domain_spec["specialized_tools"].items():
                        if category not in agent_spec["domain_tools"]:
                            agent_spec["domain_tools"][category] = []
                        agent_spec["domain_tools"][category].extend(tool_list)

                # Merge thresholds (conservative - highest wins)
                if "confidence_thresholds" in domain_spec.get("decision_rules", {}):
                    for threshold_type, value in domain_spec["decision_rules"][
                        "confidence_thresholds"
                    ].items():
                        if threshold_type not in merged_thresholds:
                            merged_thresholds[threshold_type] = value
                        else:
                            # Conservative merge - take the higher threshold
                            merged_thresholds[threshold_type] = max(
                                merged_thresholds[threshold_type], value
                            )

        # Apply merged thresholds
        if merged_thresholds:
            agent_spec["domain_thresholds"] = merged_thresholds

        return agent_spec

    def _extract_section(self, content: str, section_header: str) -> str:
        """Extract content under a markdown section"""
        if section_header not in content:
            return ""

        start = content.find(section_header) + len(section_header)
        # Find next section or end
        next_section = content.find("\n## ", start)
        if next_section == -1:
            section_content = content[start:]
        else:
            section_content = content[start:next_section]

        return section_content.strip()

    def generate_prompt(
        self, agent_spec: dict[str, Any], include_coordination: bool = True
    ) -> str:
        """Generate agent execution prompt with full persona"""
        prompt_parts = []

        # Task context if provided
        if "task_context" in agent_spec:
            prompt_parts.append(f"TASK CONTEXT: {agent_spec['task_context']}\n")

        # Identity
        identity = agent_spec.get("identity", {})
        prompt_parts.append(
            f"You are executing as: {identity.get('id', 'unknown_agent')}"
        )
        prompt_parts.append(f"Type: {identity.get('type', 'general')}")
        prompt_parts.append(
            f"Capabilities: {', '.join(identity.get('capabilities', []))}"
        )
        prompt_parts.append(f"Tools: {', '.join(identity.get('tools', []))}")

        # Role and Purpose
        if agent_spec.get("role"):
            prompt_parts.append(f"\nRole: {agent_spec['role']}")
        if agent_spec.get("purpose"):
            prompt_parts.append(f"\nPurpose: {agent_spec['purpose']}")

        # Domain expertise if loaded
        if agent_spec.get("domains"):
            domain_names = [d.get("id", "unknown") for d in agent_spec["domains"]]
            prompt_parts.append(
                f"\n--- DOMAIN EXPERTISE: {', '.join(domain_names)} ---"
            )

            if agent_spec.get("domain_patterns"):
                prompt_parts.append("\nDomain Knowledge Patterns:")
                prompt_parts.append(json.dumps(agent_spec["domain_patterns"], indent=2))

            if agent_spec.get("domain_rules"):
                prompt_parts.append("\nDomain Decision Rules:")
                prompt_parts.append(json.dumps(agent_spec["domain_rules"], indent=2))

            if agent_spec.get("domain_tools"):
                prompt_parts.append("\nDomain-Specific Tools:")
                prompt_parts.append(json.dumps(agent_spec["domain_tools"], indent=2))

            if "domain_thresholds" in agent_spec:
                prompt_parts.append("\nDomain-Specific Thresholds:")
                prompt_parts.append(
                    json.dumps(agent_spec["domain_thresholds"], indent=2)
                )

        # Core capabilities
        if agent_spec.get("capabilities"):
            prompt_parts.append(f"\nCore Capabilities:\n{agent_spec['capabilities']}")

        # Decision logic
        if agent_spec.get("decision_logic"):
            prompt_parts.append(f"\nDecision Logic:\n{agent_spec['decision_logic']}")

        if include_coordination:
            prompt_parts.append("\n--- COORDINATION PROTOCOL ---")
            prompt_parts.append(
                "1. Respect other agents's findings and do not overwrite them"
            )
            prompt_parts.append("2. Write your opinions in your own artifacts")
            prompt_parts.append(
                "3. Collaborate and coordinate with other agents via artifact handoff"
            )

        prompt_parts.append("\n--- END PERSONA LOADING ---\n")
        prompt_parts.append(
            "Proceed with your assigned task using this complete persona."
        )

        return "\n".join(prompt_parts)

    def _load_agent_prompts(self) -> dict[str, Any]:
        """Load agent prompts template for PromptFactory trait"""
        prompts_path = self.base_path / "agent_prompts.yaml"

        if not prompts_path.exists():
            # Try fallback locations - bypass safety check for known config files
            fallback_paths = [
                Path(__file__).parent.parent.parent / "prompts" / "agent_prompts.yaml",
                Path(".khive/prompts/agent_prompts.yaml"),
                Path("src/khive/prompts/agent_prompts.yaml"),
            ]

            for fallback_path in fallback_paths:
                if fallback_path.exists():
                    # Load directly with yaml.safe_load to bypass path security for config files
                    try:
                        with open(fallback_path, encoding="utf-8") as f:
                            return yaml.safe_load(f) or {}
                    except Exception:
                        continue

            # Return basic default structure if no files found
            return {
                "templates": {
                    "base": "You are a helpful assistant with specialized knowledge.",
                    "role_prompt": "Role: {role}",
                    "domain_prompt": "Domain expertise: {domain}",
                }
            }

        return self.load_yaml(prompts_path)

    def _load_domain_mapper(self) -> dict[str, Any]:
        """Load domain name mapper for canonicalization"""
        mapper_path = self.base_path / "name_mapper.yaml"

        if not mapper_path.exists():
            # Try fallback locations - bypass safety check for known config files
            fallback_paths = [
                Path(__file__).parent.parent.parent / "prompts" / "name_mapper.yaml",
                Path(".khive/prompts/name_mapper.yaml"),
                Path("src/khive/prompts/name_mapper.yaml"),
            ]

            for fallback_path in fallback_paths:
                if fallback_path.exists():
                    # Load directly with yaml.safe_load to bypass path security for config files
                    try:
                        with open(fallback_path, encoding="utf-8") as f:
                            return yaml.safe_load(f) or {
                                "synonyms": {},
                                "canonical_domains": [],
                            }
                    except Exception:
                        continue

            # Return default structure if no files found
            return {"synonyms": {}, "canonical_domains": []}

        return self.load_yaml(mapper_path)

    def canonicalize_domain(self, domain: str) -> str:
        """Map domain synonyms to canonical domain names"""
        if not domain:
            return domain

        # Clean the domain name
        domain_clean = domain.strip().lower()

        # Check synonym mapping
        synonyms = self._domain_mapper.get("synonyms", {})
        if domain_clean in synonyms:
            return synonyms[domain_clean]

        # Return original if no mapping found
        return domain

    def _is_safe_path(self, file_path: Path) -> bool:
        """Validate file path to prevent directory traversal attacks"""
        try:
            # Convert to absolute path and resolve
            abs_path = file_path.resolve()

            # Check if path is within expected directories
            base_abs = (
                self.base_path.resolve()
                if hasattr(self, "base_path")
                else Path(__file__).parent.resolve()
            )

            # Allow access to shared prompts directory
            khive_src_path = Path(__file__).parent.parent.parent.parent.resolve()
            prompts_path = khive_src_path / "prompts"

            # Path must be within the base directory or the shared prompts directory
            try:
                abs_path.relative_to(base_abs)
                return True
            except ValueError:
                try:
                    abs_path.relative_to(prompts_path)
                    return True
                except ValueError:
                    # Path is outside allowed directories
                    return False

        except (OSError, ValueError):
            return False

    def _sanitize_cache_key(self, key: str) -> str:
        """Sanitize cache key to prevent injection attacks"""
        import re

        # First remove dangerous patterns
        sanitized = key
        # Remove path traversal patterns
        sanitized = re.sub(r"\.\.+", "", sanitized)
        # Remove dangerous shell characters (but not / which will be replaced with _)
        dangerous_chars = r"[\\;|&`$\x00\n\r]"
        sanitized = re.sub(dangerous_chars, "", sanitized)
        # Allow only alphanumeric, underscore, dash - replace everything else with _
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", sanitized)
        # Limit length to prevent memory exhaustion
        return sanitized[:100]

    def _sanitize_input(self, input_str: str) -> str:
        """Sanitize general input to prevent injection attacks"""
        import re

        # Remove potential path traversal sequences
        sanitized = input_str.replace("..", "").replace("/", "_").replace("\\\\", "_")
        # Remove shell metacharacters and dangerous characters
        dangerous_chars = r"[;|&`$\x00\n\r\t]"
        sanitized = re.sub(dangerous_chars, "", sanitized)
        # Remove other control characters
        sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", sanitized)
        # Limit length
        return sanitized.strip()[:255]

    def _sanitize_context(self, context: str) -> str:
        """Sanitize context input to prevent prompt injection"""
        import re

        # Remove potentially dangerous prompt injection patterns
        dangerous_patterns = [
            r"\bignore\s+(all\s+)?previous\s+instructions\b",
            r"\bforget\s+everything\b",
            r"\bforget\s+all\s+instructions\b",
            r"\bnew\s+instruction[s]?\s*:\s*be\s+malicious\b",
            r"\boverride\s+all\s+safety\b",
            r"\bdisregard\s+all\s+prior\s+instructions\b",
            r"\bsystem\s*:",
            r"\bassistant\s*:",
            r"\buser\s*:",
            r"<\s*/?s*system\s*>",
            r"```\s*system",
            # Command injection patterns
            r";\s*rm\s+-rf",
            r"DROP\s+TABLE",
            r"<script[^>]*>.*?</script>",
            # Markdown injection patterns
            r"\[.*?\]\(javascript:.*?\)",
            r"!\[.*?\]\(data:.*?malicious.*?\)",
            r"{{.*?}}",
            # Command substitution patterns
            r"\$\(.*?malicious.*?\)",
            r"`.*?malicious.*?`",
        ]

        sanitized = context
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)

        # Remove excessive newlines that could be used for injection
        sanitized = re.sub(r"\n{5,}", "\n\n", sanitized)

        # Prevent DoS attacks by limiting context size to reasonable amount (100KB)
        if len(sanitized) > 100000:
            sanitized = sanitized[:100000] + "...[TRUNCATED]"

        return sanitized.strip()

    def get_unique_agent_id(self, role: str, domain: str) -> str:
        """Generate unique agent identifier, appending version if duplicate"""
        # Canonicalize domain first
        canonical_domain = self.canonicalize_domain(domain)

        base_pair = f"{role}:{canonical_domain}"

        # If not seen before, add and return base
        if base_pair not in self._seen_pairs:
            self._seen_pairs.add(base_pair)
            return f"{role}_{canonical_domain}"

        # Find next available version
        version = 2
        while f"{base_pair}-v{version}" in self._seen_pairs:
            version += 1

        versioned_pair = f"{base_pair}-v{version}"
        self._seen_pairs.add(versioned_pair)
        return f"{role}_{canonical_domain}_v{version}"

    def list_available_roles(self) -> list[str]:
        """List all available agent roles"""
        roles = [
            file_path.stem
            for file_path in self.roles_path.glob("*")
            if file_path.suffix in [".md", ".yaml"]
        ]
        return sorted(roles)

    def list_available_domains(self) -> list[str]:
        """List all available domain expertise modules from hierarchical taxonomy"""
        domains = []

        # Include flat structure domains for backward compatibility
        domains.extend(
            file_path.stem
            for file_path in self.domains_path.glob("*.yaml")
            if file_path.stem not in ["TAXONOMY", "README"]
        )

        # Include hierarchical domains
        domains.extend(
            file_path.stem
            for file_path in self.domains_path.rglob("*.yaml")
            # Skip files in the root (already processed above)
            if (
                file_path.parent != self.domains_path
                and file_path.stem not in ["TAXONOMY", "README"]
            )
        )

        return sorted(set(domains))  # Remove duplicates

    def list_domains_by_taxonomy(self) -> dict[str, dict[str, list[str]]]:
        """List domains organized by taxonomy categories"""
        taxonomy = {}

        # Traverse the taxonomy structure
        for category_path in self.domains_path.iterdir():
            if category_path.is_dir():
                category_name = category_path.name
                taxonomy[category_name] = {}

                # Check for domains directly in category folder
                direct_domains = [
                    yaml_file.stem for yaml_file in category_path.glob("*.yaml")
                ]

                if direct_domains:
                    taxonomy[category_name]["_root"] = sorted(direct_domains)

                # Check for subcategories
                for subcategory_path in category_path.iterdir():
                    if subcategory_path.is_dir():
                        subcategory_name = subcategory_path.name
                        domains = [
                            yaml_file.stem
                            for yaml_file in subcategory_path.glob("*.yaml")
                        ]

                        if domains:  # Only include non-empty subcategories
                            taxonomy[category_name][subcategory_name] = sorted(domains)

                # Remove empty categories
                if not taxonomy[category_name]:
                    del taxonomy[category_name]

        return taxonomy
