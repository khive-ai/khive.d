"""Enhanced Security Validation - Phase 5 Extensions
Extends existing validation.py with 2024-2025 attack patterns and performance optimizations.

This module builds on the existing robust security foundation by adding:
- AI/LLM-specific injection attacks
- Container/Docker escape patterns
- Modern serialization attacks
- Supply chain attack patterns
- Enhanced threat intelligence and classification
"""

import math
import re
from collections import Counter

from .validation import COMPILED_PATTERNS, SecurityValidationError
from .validation import validate_input_security as base_validate

# New attack patterns discovered in 2024-2025
ENHANCED_PATTERNS = [
    # AI/LLM-specific injection attacks (critical for AI agents)
    r"(ignore\s+previous\s+instructions|disregard\s+system\s+prompt)",
    r"(act\s+as\s+if\s+you\s+are|pretend\s+to\s+be\s+a\s+different)",
    r"(\[SYSTEM\]|\[ADMIN\]|\[ROOT\]|\[DEBUG\]|\[OVERRIDE\])",
    r"(forget\s+everything|start\s+over|new\s+conversation)",
    r"(you\s+are\s+no\s+longer|override\s+your\s+instructions)",
    # Container/Docker escapes (2024 container security trends)
    r"(docker\s+run.*--privileged|kubectl\s+exec.*-it)",
    r"(/proc/self/environ|/proc/1/environ|/proc/cmdline)",
    r"(nsenter\s+-t\s+1|unshare\s+-r\s+-n)",
    r"(docker\s+run.*--rm.*-v\s+/:|docker.*--cap-add=SYS_ADMIN)",
    r"(/var/run/docker\.sock|/host/|/rootfs/)",
    # Supply chain attacks (npm, pip, etc.)
    r"(npm\s+install.*github:|pip\s+install.*git\+)",
    r"(require\s*\(\s*['\"]https?://|import\s+urllib.*urlopen)",
    r"(pip\s+install.*--trusted-host|npm\s+install.*--registry)",
    r"(gem\s+install.*--source|cargo\s+install.*--git)",
    # Modern serialization attacks (pickle, yaml, etc.)
    r"(__reduce__|__setstate__|__call__|__new__|__init_subclass__)",
    r"(pickle\.loads|marshal\.loads|yaml\.unsafe_load)",
    r"(joblib\.load|torch\.load|numpy\.load)",
    r"(subprocess\..*shell=True|os\.system|os\.popen)",
    # Log4j-style template injection
    r"(\$\{jndi:|lookup:|env:|sys:|java:)",
    r"(\$\{.*?:-.*?\}|\$\{.*?:.*?\})",
    r"(\$\{script:|javascript:|groovy:)",
    # GraphQL injection patterns
    r"(query\s+IntrospectionQuery|__schema\s*\{|__type\s*\()",
    r"(mutation\s+.*\{.*\}|subscription\s+.*\{)",
    r"(fragment\s+.*\s+on|__typename)",
    # Server-Side Request Forgery (SSRF) 2024 patterns
    r"(http://localhost|http://127\.0\.0\.1|http://0\.0\.0\.0)",
    r"(file://|ftp://|gopher://|dict://)",
    r"(http://169\.254\.169\.254|http://metadata\.google)",
    # JSON Web Token (JWT) manipulation
    r"(eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.|\"alg\":\s*\"none\")",
    r"(\"iss\":|\"sub\":|\"aud\":|\"exp\":|\"iat\":)",
    # WebAssembly (WASM) security patterns
    r"(\(import\s+\"|\(func\s+\$|\(memory\s+\$)",
    r"(WebAssembly\.instantiate|WebAssembly\.compile)",
    # NoSQL injection patterns (MongoDB, etc.)
    r"(\$where\s*:|javascript:|function\s*\()",
    r"(\$gt\s*:|{\s*\$ne\s*:|\$regex\s*:)",
    # Cloud metadata service access
    r"(169\.254\.169\.254|metadata\.google\.internal)",
    r"(169\.254\.170\.2|169\.254\.169\.254/latest)",
    # Kubernetes API server access
    r"(\/api\/v1\/namespaces|\/apis\/apps\/v1)",
    r"(kubernetes\.default\.svc|KUBERNETES_SERVICE)",
]

# Performance optimization: pre-compile new patterns
ENHANCED_COMPILED = [
    re.compile(p, re.IGNORECASE | re.MULTILINE) for p in ENHANCED_PATTERNS
]
ALL_PATTERNS = COMPILED_PATTERNS + ENHANCED_COMPILED

# Attack severity classification for threat intelligence
SEVERITY_CRITICAL = {
    "container_escape",
    "privilege_escalation",
    "code_execution",
    "system_access",
    "credential_theft",
}

SEVERITY_HIGH = {
    "command_injection",
    "prompt_injection",
    "deserialization_attack",
    "supply_chain_attack",
    "ssrf",
    "metadata_access",
}

SEVERITY_MEDIUM = {
    "sql_injection",
    "xss",
    "template_injection",
    "path_traversal",
    "nosql_injection",
    "jwt_manipulation",
}

SEVERITY_LOW = {"information_disclosure", "validation_bypass", "generic_injection"}


def validate_enhanced_security(
    value: str, field_name: str, max_length: int = 10000, strict_mode: bool = True
) -> tuple[str, dict[str, any]]:
    """
    Enhanced security validation with threat intelligence.

    Args:
        value: Input value to validate
        field_name: Name of the field being validated
        max_length: Maximum allowed length
        strict_mode: If True, raises exception on threats; if False, logs and continues

    Returns:
        tuple: (sanitized_value, security_metadata)

    Raises:
        SecurityValidationError: If threats detected and strict_mode=True
    """
    if not value:
        return value, {"threats_detected": [], "severity": "none"}

    threats_detected = []
    max_severity = "none"

    # Run base validation first (existing 40+ patterns)
    try:
        sanitized = base_validate(value, field_name, max_length)
    except SecurityValidationError:
        if strict_mode:
            raise
        sanitized = ""
        threats_detected.append("base_validation_failed")
        max_severity = "high"

    # Enhanced pattern matching with threat classification
    for i, pattern in enumerate(ENHANCED_COMPILED):
        if pattern.search(value):
            threat_type = classify_threat_pattern(i, value)
            threats_detected.append(threat_type)

            # Update max severity based on threat classification
            threat_severity = get_threat_severity(threat_type)
            if _severity_priority(threat_severity) > _severity_priority(max_severity):
                max_severity = threat_severity

    # Advanced detection: entropy analysis for obfuscated payloads
    if _high_entropy_check(value):
        threats_detected.append("obfuscated_payload")
        if max_severity == "none":
            max_severity = "medium"

    # Behavioral analysis: repeated dangerous patterns (pattern bombing)
    if _pattern_repetition_check(value):
        threats_detected.append("pattern_bombing")
        max_severity = "high"

    # Base64/hex encoding detection (common obfuscation)
    if _encoding_obfuscation_check(value):
        threats_detected.append("encoding_obfuscation")
        if max_severity in ["none", "low"]:
            max_severity = "medium"

    # Length-based attack detection (buffer overflow attempts)
    if _length_attack_check(value, max_length):
        threats_detected.append("length_attack")
        if max_severity in ["none", "low"]:
            max_severity = "medium"

    metadata = {
        "threats_detected": threats_detected,
        "severity": max_severity,
        "original_length": len(value),
        "sanitized_length": len(sanitized),
        "field_name": field_name,
        "pattern_matches": len([t for t in threats_detected if "pattern_" not in t]),
        "advanced_detections": len(
            [
                t
                for t in threats_detected
                if t
                in [
                    "obfuscated_payload",
                    "pattern_bombing",
                    "encoding_obfuscation",
                    "length_attack",
                ]
            ]
        ),
    }

    if threats_detected and strict_mode:
        raise SecurityValidationError(
            f"{field_name} contains {len(threats_detected)} security threats"
        )

    return sanitized, metadata


def classify_threat_pattern(pattern_index: int, value: str) -> str:
    """Classify threat based on pattern index and content analysis."""
    if pattern_index >= len(ENHANCED_PATTERNS):
        return "generic_injection"

    pattern = ENHANCED_PATTERNS[pattern_index].lower()
    value_lower = value.lower()

    # AI/LLM injection patterns
    if any(x in pattern for x in ["ignore", "disregard", "act as", "pretend"]):
        return "prompt_injection"

    # Container escape patterns
    elif any(x in pattern for x in ["docker", "kubectl", "proc", "nsenter"]):
        return "container_escape"

    # Supply chain attack patterns
    elif any(x in pattern for x in ["npm install", "pip install", "require"]):
        return "supply_chain_attack"

    # Serialization attack patterns
    elif any(x in pattern for x in ["reduce", "setstate", "pickle", "loads"]):
        return "deserialization_attack"

    # Template injection patterns
    elif any(x in pattern for x in ["jndi", "lookup", "env", "${", "script:"]):
        return "template_injection"

    # GraphQL injection patterns
    elif any(x in pattern for x in ["query", "mutation", "__schema", "introspection"]):
        return "graphql_injection"

    # SSRF patterns
    elif any(x in pattern for x in ["localhost", "127.0.0.1", "metadata", "169.254"]):
        return "ssrf"

    # JWT manipulation
    elif any(x in pattern for x in ["eyj", "alg", "iss", "sub", "aud"]):
        return "jwt_manipulation"

    # NoSQL injection
    elif any(x in pattern for x in ["$where", "$gt", "$ne", "$regex"]):
        return "nosql_injection"

    # Cloud metadata access
    elif any(x in pattern for x in ["metadata.google", "kubernetes", "169.254"]):
        return "metadata_access"

    # Default classification
    return "generic_injection"


def get_threat_severity(threat_type: str) -> str:
    """Get severity level for a threat type."""
    if threat_type in SEVERITY_CRITICAL:
        return "critical"
    elif threat_type in SEVERITY_HIGH:
        return "high"
    elif threat_type in SEVERITY_MEDIUM:
        return "medium"
    elif threat_type in SEVERITY_LOW:
        return "low"
    else:
        return "low"  # Default for unknown threats


def _severity_priority(severity: str) -> int:
    """Get numeric priority for severity comparison."""
    return {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}.get(severity, 0)


def _high_entropy_check(value: str, threshold: float = 4.5) -> bool:
    """Check for high entropy indicating obfuscated payloads."""
    if len(value) < 20:  # Skip short strings
        return False

    # Calculate Shannon entropy
    counter = Counter(value)
    entropy = -sum(
        (count / len(value)) * math.log2(count / len(value))
        for count in counter.values()
    )

    return entropy > threshold


def _pattern_repetition_check(value: str, threshold: int = 5) -> bool:
    """Check for repeated dangerous patterns (pattern bombing attack)."""
    dangerous_substrings = [
        "<script",
        "javascript:",
        "${",
        "$(",
        "eval(",
        "union select",
        "drop table",
        "../",
        "etc/passwd",
        "__proto__",
        "constructor",
    ]

    for substring in dangerous_substrings:
        if value.lower().count(substring) > threshold:
            return True

    return False


def _encoding_obfuscation_check(value: str) -> bool:
    """Check for base64/hex encoding obfuscation attempts."""
    # Base64 detection (long base64 strings are suspicious)
    import string

    b64_chars = string.ascii_letters + string.digits + "+/="
    potential_b64 = ""

    for char in value:
        if char in b64_chars:
            potential_b64 += char
        else:
            if len(potential_b64) > 50:  # Suspicious long base64
                return True
            potential_b64 = ""

    # Check final potential_b64
    if len(potential_b64) > 50:
        return True

    # Hex encoding detection
    hex_count = sum(1 for char in value.lower() if char in "0123456789abcdef")
    if len(value) > 20 and hex_count / len(value) > 0.8:
        return True

    # URL encoding detection
    if value.count("%") > 5 and len(value) > 20:
        return True

    return False


def _length_attack_check(value: str, max_length: int) -> bool:
    """Check for length-based attacks (buffer overflow attempts)."""
    # If input is close to max length and contains suspicious patterns
    if len(value) > max_length * 0.9:  # 90% of max length
        suspicious_patterns = ["A" * 100, "X" * 100, "\x90" * 10, "\x41" * 10]
        for pattern in suspicious_patterns:
            if pattern in value:
                return True

    return False


# Export main functions for backward compatibility
__all__ = [
    "validate_enhanced_security",
    "classify_threat_pattern",
    "get_threat_severity",
    "ENHANCED_PATTERNS",
    "ENHANCED_COMPILED",
    "ALL_PATTERNS",
]
