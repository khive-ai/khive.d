"""Secure Pydantic model validators for immediate deployment"""

from pydantic import field_validator

from .validation import (
    validate_context_security,
    validate_domains_security,
    validate_role_security,
)


class SecureComposerRequestMixin:
    """Security validation mixin for ComposerRequest"""

    @field_validator("role", mode="before")
    def validate_role_secure(cls, v):
        if v is None:
            return v
        return validate_role_security(str(v))

    @field_validator("domains", mode="before")
    def validate_domains_secure(cls, v):
        if v is None:
            return v
        return validate_domains_security(str(v))

    @field_validator("context", mode="before")
    def validate_context_secure(cls, v):
        if v is None:
            return v
        return validate_context_security(str(v))


class SecureAgentRequestMixin:
    """Security validation mixin for AgentRequest"""

    @field_validator("instruct", mode="before")
    def validate_instruct_secure(cls, v):
        if v is None:
            return v

        # Handle different instruct formats
        if hasattr(v, "model_dump"):
            instruct_dict = v.model_dump()
        elif hasattr(v, "__dict__"):
            instruct_dict = v.__dict__
        else:
            try:
                instruct_dict = dict(v) if v else {}
            except (TypeError, ValueError):
                # If we can't parse it, validate as string
                validate_context_security(str(v))
                return v

        # Validate task field if present
        if instruct_dict.get("task"):
            validate_context_security(str(instruct_dict["task"]))

        # Validate context field if present
        if instruct_dict.get("context"):
            if isinstance(instruct_dict["context"], str):
                validate_context_security(instruct_dict["context"])
            else:
                # Handle nested context
                context_str = str(instruct_dict["context"])
                validate_context_security(context_str)

        return v
