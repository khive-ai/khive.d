"""Secure error handling to prevent information disclosure"""

import logging

from pydantic import ValidationError

# Configure security logging
security_logger = logging.getLogger("khive.security")

GENERIC_ERROR_MESSAGES = {
    "validation": "Input validation failed. Please check your input and try again.",
    "security": "Security validation failed. Request blocked for safety.",
    "system": "An internal error occurred. Please contact support if this persists.",
    "permission": "Access denied. Insufficient permissions for this operation.",
}


def sanitize_error_message(error: Exception, context: str = None) -> str:
    """
    Convert detailed error messages to safe, generic messages.
    Log detailed info for debugging without exposing to users.
    """
    error_type = type(error).__name__
    error_message = str(error)

    # Log detailed error for debugging (server-side only)
    security_logger.error(
        f"Security error in {context}: {error_type}: {error_message}",
        extra={"context": context, "error_type": error_type},
    )

    # Return generic message based on error type
    if isinstance(error, ValidationError):
        return GENERIC_ERROR_MESSAGES["validation"]
    elif "security" in error_message.lower() or "dangerous" in error_message.lower():
        return GENERIC_ERROR_MESSAGES["security"]
    elif any(
        keyword in error_message.lower()
        for keyword in ["path", "file", "directory", "system"]
    ):
        return GENERIC_ERROR_MESSAGES["system"]
    else:
        return GENERIC_ERROR_MESSAGES["validation"]


class SecureErrorHandler:
    """Context manager for secure error handling"""

    def __init__(self, operation_context: str):
        self.context = operation_context

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            # Convert to safe error message
            safe_message = sanitize_error_message(exc_val, self.context)
            # Re-raise with sanitized message
            raise type(exc_val)(safe_message) from None
        return False
