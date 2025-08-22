from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RolePriority(BaseModel):
    """Simple role priority model"""

    model_config = ConfigDict(extra="forbid")

    roles: list[str] = Field(
        min_length=3,
        max_length=10,
        description="Priority-ordered list of recommended roles",
    )


class OrchestrationEvaluation(BaseModel):
    """Single flat evaluation model for GPT-5-nano"""

    model_config = ConfigDict(extra="forbid")

    # Core Assessment
    complexity: Literal["simple", "medium", "complex", "very_complex"]
    complexity_reason: str = Field(max_length=200)

    total_agents: int = Field(ge=1, le=20)
    agent_reason: str = Field(max_length=200)

    rounds_needed: int = Field(ge=1, le=6)

    # Role Priority List
    role_priorities: list[str] = Field(
        max_length=10,
        description="Priority-ordered list of recommended roles (most important first)",
    )

    # Domains (just lists)
    primary_domains: list[str] = Field(max_length=3)
    domain_reason: str = Field(max_length=200)
    
    @field_validator("role_priorities", mode="before")
    @classmethod
    def validate_roles(cls, v):
        """Validate and fix role names using string similarity."""
        from khive.prompts import ALL_AGENT_ROLES
        from khive.utils import get_logger
        
        logger = get_logger("khive.services.plan")
        
        if not v:
            return v
            
        validated_roles = []
        for role in v:
            if role in ALL_AGENT_ROLES:
                validated_roles.append(role)
            else:
                # Try to find the closest matching valid role
                from lionagi.libs.validate.string_similarity import (
                    string_similarity,
                )
                
                # Convert set to list for string_similarity
                valid_roles_list = list(ALL_AGENT_ROLES)
                
                best_match = string_similarity(
                    role,
                    valid_roles_list,
                    threshold=0.5,  # Lower threshold to catch domain->role mappings
                    case_sensitive=False,
                    return_most_similar=True,
                )
                
                if best_match:
                    logger.debug(f"Corrected role '{role}' to '{best_match}'")
                    validated_roles.append(best_match)
                else:
                    logger.warning(f"Could not match role '{role}' to any valid role")
                    # Skip if no good match found (don't add invalid roles)
                    
        return validated_roles
    
    @field_validator("primary_domains", mode="before")
    @classmethod  
    def validate_domains(cls, v):
        """Validate domain names - canonicalize them."""
        from khive.utils import KHIVE_CONFIG_DIR
        from khive.services.composition import AgentComposer
        
        if not v:
            return v
            
        # Initialize composer using the established config directory
        composer = AgentComposer(KHIVE_CONFIG_DIR / "prompts")
        
        validated_domains = []
        for domain in v:
            # Canonicalize the domain
            canonical = composer.canonicalize_domain(domain)
            validated_domains.append(canonical)
            
        return validated_domains

    # Workflow
    workflow_pattern: Literal["parallel", "sequential", "hybrid"]
    workflow_reason: str = Field(max_length=200)

    # Quality
    quality_level: Literal["basic", "thorough", "critical"]
    quality_reason: str = Field(max_length=200)

    # Decision Matrix
    rules_applied: list[str] = Field(max_length=3)

    # Summary
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(max_length=300)


# Lion-Task Coordination Models (legacy coordination models removed)
