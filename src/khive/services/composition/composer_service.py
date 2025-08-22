# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from khive.prompts import ALL_AGENT_ROLES
from khive.utils import get_logger

from .agent_composer import AgentComposer
from .parts import ComposerRequest, ComposerResponse, DomainExpertise

logger = get_logger("khive.services.composition")


__all__ = (
    "ComposerService",
    "composer_service",
)


class ComposerService:
    """
    Agent Composition Service.

    Wraps the AgentComposer to provide intelligent agent composition
    from role + domain specifications.
    """

    def __init__(self):
        """Initialize the composer service."""
        self._composer = None
        self._composer_lock = asyncio.Lock()

    async def _get_composer(self) -> AgentComposer:
        """Get or create the agent composer."""
        if self._composer is None:
            async with self._composer_lock:
                if self._composer is None:
                    from khive.utils import KHIVE_CONFIG_DIR

                    source_prompts = Path(__file__).parent.parent.parent / "prompts"
                    khive_prompts = KHIVE_CONFIG_DIR / "prompts"

                    # copy entire roles folder
                    if not (khive_prompts / "roles").exists():
                        shutil.copytree(
                            source_prompts / "roles",
                            khive_prompts / "roles",
                            dirs_exist_ok=True,
                        )

                    # copy entire domains folder
                    if not (khive_prompts / "domains").exists():
                        shutil.copytree(
                            source_prompts / "domains",
                            khive_prompts / "domains",
                            dirs_exist_ok=True,
                        )

                    # check for specific files
                    files = {
                        "name_mapper.yaml",
                        "decision_matrix.yaml",
                        "agent_prompts.yaml",
                    }
                    for f in files:
                        if not (khive_prompts / f).exists():
                            shutil.copy(source_prompts / f, khive_prompts / f)

                    # ensure all roles are present
                    from lionagi.libs.file.file_ops import list_files

                    fps = list_files(khive_prompts / "roles", ".md")
                    all_existing_roles = {fp.stem for fp in fps if fp.is_file()}
                    if not ALL_AGENT_ROLES.issubset(all_existing_roles):
                        for role in ALL_AGENT_ROLES:
                            if role not in all_existing_roles:
                                role_prompt_fp = source_prompts / "roles" / f"{role}.md"
                                shutil.copy(
                                    role_prompt_fp,
                                    khive_prompts / "roles" / f"{role}.md",
                                )

                    self._composer = AgentComposer(
                        base_path=str(KHIVE_CONFIG_DIR / "prompts")
                    )
        return self._composer

    async def handle_request(self, request: ComposerRequest) -> ComposerResponse:
        """
        Handle an agent composition request.

        Args:
            request: The composition request

        Returns:
            Composition response with agent specification
        """
        try:
            # Parse request if needed
            if isinstance(request, str):
                request = ComposerRequest.model_validate_json(request)
            elif isinstance(request, dict):
                request = ComposerRequest.model_validate(request)

            # Get composer
            composer = await self._get_composer()

            # Compose agent
            agent_spec = composer.compose_agent(
                role=request.role, domains=request.domains, context=request.context
            )

            # Generate unique agent ID
            agent_id = composer.get_unique_agent_id(
                request.role,
                request.domains.split(",")[0] if request.domains else "general",
            )

            # Generate system prompt
            system_prompt = composer.generate_prompt(
                agent_spec, include_coordination=True
            )

            # Extract capabilities
            capabilities = []
            if "capabilities" in agent_spec:
                capabilities = (
                    agent_spec["capabilities"].split("\n")
                    if isinstance(agent_spec["capabilities"], str)
                    else []
                )

            # Extract tools
            tools = []
            identity = agent_spec.get("identity", {})
            if "tools" in identity:
                tools = identity["tools"]

            # Process domain expertise
            domain_expertise = []
            if "domains" in agent_spec:
                domain_expertise.extend(
                    DomainExpertise(
                        domain_id=domain_data.get("id", "unknown"),
                        knowledge_patterns=agent_spec.get("domain_patterns", {}),
                        decision_rules=agent_spec.get("domain_rules", {}),
                        specialized_tools=agent_spec.get("domain_tools", {}).get(
                            "specialized", []
                        ),
                        confidence_thresholds=agent_spec.get("domain_thresholds", {}),
                    )
                    for domain_data in agent_spec["domains"]
                    if isinstance(domain_data, dict)
                )

            # Extract domain names
            domain_names = []
            if request.domains:
                domain_names = [d.strip() for d in request.domains.split(",")]

            return ComposerResponse(
                success=True,
                summary=f"Composed {request.role} agent with {len(domain_names)} domain(s)",
                agent_id=agent_id,
                role=request.role,
                domains=domain_names,
                system_prompt=system_prompt,
                capabilities=capabilities,
                tools=tools,
                domain_expertise=domain_expertise,
                confidence=0.9,  # High confidence for successful composition
            )

        except Exception as e:
            logger.error(f"Error in handle_request: {e}", exc_info=True)
            return ComposerResponse(
                success=False,
                summary=f"Composition failed: {e!s}",
                agent_id="",
                role=request.role,
                system_prompt="",
                confidence=0.0,
                error=str(e),
            )

    async def compose(self, request: ComposerRequest) -> ComposerResponse:
        """
        Compose an agent (alias for handle_request).

        Args:
            request: The composition request

        Returns:
            Composition response
        """
        return await self.handle_request(request)

    async def close(self) -> None:
        """Clean up resources."""
        try:
            if self._composer is not None:
                # AgentComposer doesn't have async cleanup
                pass
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)


composer_service = ComposerService()
