"""Khive Security Module - Emergency Security Fixes

This module provides immediate security validation and protection
against critical vulnerabilities identified in the security assessment.
"""

from .validation import (
    validate_input_security,
    validate_role_security, 
    validate_domains_security,
    validate_context_security,
    SecurityValidationError,
)

from .secure_models import (
    SecureComposerRequestMixin,
    SecureAgentRequestMixin,
)

from .error_handler import (
    sanitize_error_message,
    SecureErrorHandler,
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