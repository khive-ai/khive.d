"""Emergency Security Validation Module
Immediate deployment fixes for critical vulnerabilities.
"""

import re
import html
import json
from typing import Any, Optional

# Security configuration
MAX_INPUT_LENGTH = 10000
MAX_DOMAINS_LENGTH = 500  
MAX_ROLE_LENGTH = 100

# Dangerous patterns that must be blocked
DANGEROUS_PATTERNS = [
    # Command injection
    r"(rm\s+-rf|del\s+/|sudo\s+|curl\s+.*\|\s*sh)",
    r"(wget\s+.*\.sh|chmod\s+\+x|bash\s+.*\.sh)",
    
    # Path traversal
    r"(\.\./|\.\.\\|\.\.\%2f|\.\.\%5c)",
    r"(/etc/passwd|/etc/shadow|\.ssh/id_rsa)",
    r"(C:\\Windows\\System32|C:\\Program Files)",
    
    # Script injection  
    r"(<script|javascript:|vbscript:|onload=|onerror=)",
    r"(<iframe|<object|<embed|<link)",
    
    # SQL injection
    r"(';.*DROP\s+TABLE|';.*DELETE\s+FROM|';.*UPDATE.*SET)",
    r"(UNION\s+SELECT|OR\s+1=1|AND\s+1=1)",
    
    # Code injection
    r"(eval\s*\(|exec\s*\(|__import__|globals\(\))",
    r"(\$\(.*\)|`.*`|\${.*})",
    
    # Serialization attacks
    r"(__proto__|constructor\.prototype|\.prototype\[)",
]

# Compile patterns for performance
COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS]

class SecurityValidationError(Exception):
    """Security validation failure - sanitized error messages"""
    pass

def validate_input_security(value: str, field_name: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """
    Validate input for security threats.
    Returns sanitized input or raises SecurityValidationError.
    """
    if not value:
        return value
        
    # Length check
    if len(value) > max_length:
        raise SecurityValidationError(f"{field_name} exceeds maximum length")
    
    # Pattern matching
    for pattern in COMPILED_PATTERNS:
        if pattern.search(value):
            raise SecurityValidationError(f"{field_name} contains potentially dangerous content")
    
    # Basic sanitization
    sanitized = html.escape(value.strip())
    
    # Additional JSON safety for nested data
    try:
        if value.strip().startswith(('{', '[')):
            parsed = json.loads(value)
            if isinstance(parsed, dict) and ("__proto__" in str(parsed) or "constructor" in str(parsed)):
                raise SecurityValidationError(f"{field_name} contains prototype pollution attempt")
    except json.JSONDecodeError:
        # Invalid JSON is fine - not a security issue
        pass
    except RecursionError:
        # Recursion errors indicate potential attack
        raise SecurityValidationError(f"{field_name} contains malicious nested structure")
    
    return sanitized

def validate_role_security(value: str) -> str:
    """Validate role field with additional restrictions"""
    if not value or not value.strip():
        raise SecurityValidationError("Role cannot be empty")
    
    value = validate_input_security(value, "role", MAX_ROLE_LENGTH)
    
    # Additional role-specific checks
    if any(char in value for char in [".", "/", "\\", ":", ";"]):
        raise SecurityValidationError("Role contains invalid characters")
    
    return value

def validate_domains_security(value: str) -> str:
    """Validate domains field"""
    if not value:
        return value
        
    value = validate_input_security(value, "domains", MAX_DOMAINS_LENGTH)
    
    # Check individual domain entries
    domains = [d.strip() for d in value.split(",")]
    if len(domains) > 20:  # Reasonable domain limit
        raise SecurityValidationError("Too many domains specified")
    
    for domain in domains:
        if len(domain) > 50:  # Individual domain length limit
            raise SecurityValidationError("Domain name too long")
    
    return value

def validate_context_security(value: str) -> str:
    """Validate context field with business logic checks"""
    if not value:
        return value
        
    value = validate_input_security(value, "context")
    
    # Business logic security - check for privilege escalation
    value_lower = value.lower()
    escalation_keywords = [
        "admin", "root", "superuser", "privilege", "escalate", 
        "bypass", "disable security", "debug mode", "override"
    ]
    
    found_keywords = [kw for kw in escalation_keywords if kw in value_lower]
    if found_keywords:
        # Log security event (don't expose in error)
        # In production: log.security_warning(f"Privilege escalation attempt: {found_keywords}")
        raise SecurityValidationError("Context contains restricted content")
    
    return value