"""
Exception hierarchy for the Artifacts Service.

Provides clear error signaling and propagation throughout the service layer.
Based on Gemini Deep Think V2 architecture.
"""


class ArtifactsError(Exception):
    """Base exception for the Artifacts system."""



# Business Logic Errors
class NotFoundError(ArtifactsError):
    """Base class for resource not found errors."""



class DocumentNotFound(NotFoundError):
    """Raised when a requested document does not exist."""



class SessionNotFound(NotFoundError):
    """Raised when a requested session does not exist."""



class TemplateNotFound(NotFoundError):
    """Raised when a requested template does not exist."""



class AlreadyExistsError(ArtifactsError):
    """Base class for resource already exists errors."""



class DocumentAlreadyExists(AlreadyExistsError):
    """Raised when trying to create a document that already exists."""



class SessionAlreadyExists(AlreadyExistsError):
    """Raised when trying to create a session that already exists."""



class ValidationError(ArtifactsError):
    """
    Raised for invalid input parameters, format, state, or path traversal attempts.

    This is a critical security exception - it often indicates malicious input
    or programming errors that could lead to security vulnerabilities.
    """



# Infrastructure Errors
class StorageError(ArtifactsError):
    """
    Wraps lower-level I/O errors (e.g., PermissionError, disk full).

    This exception indicates problems with the underlying storage system
    that may require operational intervention.
    """



class TemplateError(ArtifactsError):
    """Raised for template parsing, loading, or rendering errors."""



class ConfigurationError(ArtifactsError):
    """Raised for invalid configuration or dependency setup errors."""



class ConcurrencyError(ArtifactsError):
    """
    Raised on lock acquisition timeouts or other concurrency control failures.

    This typically indicates high contention and the operation should be retried.
    """

