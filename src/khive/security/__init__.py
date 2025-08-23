"""Khive Security Module - Emergency Security Fixes

This module provides immediate security validation and protection
against critical vulnerabilities identified in the security assessment.
"""

from .error_handler import SecureErrorHandler, sanitize_error_message
from .secure_models import SecureAgentRequestMixin, SecureComposerRequestMixin
from .validation import (
    SecurityValidationError,
    validate_context_security,
    validate_domains_security,
    validate_input_security,
    validate_role_security,
)

__all__ = [
    # Validation functions
    "validate_input_security",
    "validate_role_security",
    "validate_domains_security",
    "validate_context_security",
    "SecurityValidationError",
    # Model mixins
    "SecureComposerRequestMixin",
    "SecureAgentRequestMixin",
    # Error handling
    "sanitize_error_message",
    "SecureErrorHandler",
]
