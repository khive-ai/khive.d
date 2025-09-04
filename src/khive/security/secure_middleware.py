"""
Comprehensive Security Middleware - Phase 5.3 Production Hardening
Implements all critical security measures for production deployment.

Features:
- Authentication and authorization 
- Input validation with enhanced security patterns
- Rate limiting and DDoS protection
- Security headers (CSP, HSTS, X-Frame-Options)
- Error handling that prevents information disclosure
- Audit logging for security events
"""

import hashlib
import hmac
import json
import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from functools import wraps

from fastapi import HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .enhanced_validation import validate_enhanced_security, SecurityValidationError

logger = logging.getLogger(__name__)

# Security configuration
SECURITY_CONFIG = {
    # Authentication
    "AUTH_ENABLED": True,
    "API_KEY_LENGTH": 32,
    "SESSION_TIMEOUT_HOURS": 24,
    "MAX_LOGIN_ATTEMPTS": 5,
    "LOCKOUT_DURATION_MINUTES": 30,
    
    # Rate limiting
    "RATE_LIMIT_REQUESTS": 100,
    "RATE_LIMIT_WINDOW_SECONDS": 60,
    "RATE_LIMIT_BURST": 10,
    
    # Input validation
    "MAX_REQUEST_SIZE": 1024 * 1024,  # 1MB
    "MAX_JSON_DEPTH": 10,
    "STRICT_VALIDATION": True,
    
    # Security headers
    "CONTENT_SECURITY_POLICY": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
    
    # CORS settings
    "ALLOWED_ORIGINS": [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://khive.ai",
        "https://app.khive.ai"
    ],
}

class SecurityManager:
    """Centralized security management"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.auth_manager = AuthManager()
        self.audit_logger = AuditLogger()
        self.blocked_ips = set()
        self.suspicious_patterns = defaultdict(int)
        
    def validate_request_security(self, request: Request) -> Tuple[bool, str]:
        """Comprehensive request security validation"""
        client_ip = self.get_client_ip(request)
        
        # Check blocked IPs
        if client_ip in self.blocked_ips:
            return False, "IP address blocked due to security violations"
            
        # Rate limiting
        if not self.rate_limiter.check_rate_limit(client_ip):
            self.audit_logger.log_security_event(
                "rate_limit_exceeded", client_ip, str(request.url)
            )
            return False, "Rate limit exceeded"
            
        # Request size validation
        content_length = int(request.headers.get("content-length", 0))
        if content_length > SECURITY_CONFIG["MAX_REQUEST_SIZE"]:
            return False, "Request too large"
            
        return True, "Valid"
        
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address with proxy support"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
        
    def add_security_headers(self, response: Response):
        """Add comprehensive security headers"""
        headers = {
            # Content Security Policy
            "Content-Security-Policy": SECURITY_CONFIG["CONTENT_SECURITY_POLICY"],
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            
            # XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # HSTS for HTTPS
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions policy
            "Permissions-Policy": (
                "camera=(), microphone=(), geolocation=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            ),
            
            # Remove server information
            "Server": "Khive-Secure",
            
            # Cache control for sensitive data
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        
        for header, value in headers.items():
            response.headers[header] = value

class RateLimiter:
    """Advanced rate limiting with burst protection"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.violations = defaultdict(int)
        
    def check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limits"""
        now = time.time()
        window_start = now - SECURITY_CONFIG["RATE_LIMIT_WINDOW_SECONDS"]
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id] 
            if req_time > window_start
        ]
        
        # Check rate limit
        current_requests = len(self.requests[client_id])
        if current_requests >= SECURITY_CONFIG["RATE_LIMIT_REQUESTS"]:
            self.violations[client_id] += 1
            return False
            
        # Add current request
        self.requests[client_id].append(now)
        return True
        
    def is_burst_attack(self, client_id: str) -> bool:
        """Detect burst attacks (too many requests in short time)"""
        now = time.time()
        recent_requests = [
            req_time for req_time in self.requests[client_id]
            if req_time > now - 5  # Last 5 seconds
        ]
        return len(recent_requests) > SECURITY_CONFIG["RATE_LIMIT_BURST"]

class AuthManager:
    """Authentication and authorization manager"""
    
    def __init__(self):
        self.active_sessions = {}
        self.api_keys = self._load_api_keys()
        self.failed_attempts = defaultdict(list)
        
    def _load_api_keys(self) -> Dict[str, Dict]:
        """Load API keys from secure storage"""
        # In production, load from encrypted key store
        # For now, generate a master API key
        master_key = self._generate_api_key()
        return {
            master_key: {
                "name": "master",
                "permissions": ["all"],
                "created_at": datetime.now().isoformat(),
                "last_used": None
            }
        }
        
    def _generate_api_key(self) -> str:
        """Generate secure API key"""
        return secrets.token_urlsafe(SECURITY_CONFIG["API_KEY_LENGTH"])
        
    def validate_api_key(self, api_key: str) -> Optional[Dict]:
        """Validate API key and return key info"""
        key_info = self.api_keys.get(api_key)
        if key_info:
            key_info["last_used"] = datetime.now().isoformat()
            return key_info
        return None
        
    def is_endpoint_protected(self, path: str) -> bool:
        """Check if endpoint requires authentication"""
        public_endpoints = [
            "/health",
            "/docs",
            "/openapi.json",
            "/api/config/roles",
            "/api/config/domains"
        ]
        
        return not any(path.startswith(endpoint) for endpoint in public_endpoints)
        
    def check_permission(self, key_info: Dict, endpoint: str, method: str) -> bool:
        """Check if API key has permission for endpoint"""
        permissions = key_info.get("permissions", [])
        
        # Master key has all permissions
        if "all" in permissions:
            return True
            
        # Check specific permissions
        if method.upper() == "GET" and "read" in permissions:
            return True
        if method.upper() in ["POST", "PUT", "DELETE"] and "write" in permissions:
            return True
            
        return False
        
    def record_failed_attempt(self, client_ip: str):
        """Record failed authentication attempt"""
        now = time.time()
        self.failed_attempts[client_ip].append(now)
        
        # Clean old attempts
        self.failed_attempts[client_ip] = [
            attempt for attempt in self.failed_attempts[client_ip]
            if attempt > now - SECURITY_CONFIG["LOCKOUT_DURATION_MINUTES"] * 60
        ]
        
    def is_locked_out(self, client_ip: str) -> bool:
        """Check if IP is locked out due to failed attempts"""
        recent_failures = len(self.failed_attempts[client_ip])
        return recent_failures >= SECURITY_CONFIG["MAX_LOGIN_ATTEMPTS"]

class AuditLogger:
    """Security audit logging"""
    
    def __init__(self):
        self.logger = logging.getLogger("khive.security.audit")
        
    def log_security_event(self, event_type: str, client_ip: str, 
                          details: str, severity: str = "warning"):
        """Log security event for monitoring"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "client_ip": client_ip,
            "details": details,
            "severity": severity
        }
        
        log_method = getattr(self.logger, severity, self.logger.warning)
        log_method(f"SECURITY_EVENT: {json.dumps(event)}")

class SecurityMiddleware(BaseHTTPMiddleware):
    """FastAPI security middleware"""
    
    def __init__(self, app, security_manager: SecurityManager):
        super().__init__(app)
        self.security = security_manager
        
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = self.security.get_client_ip(request)
        
        try:
            # Pre-request security validation
            is_valid, error_message = self.security.validate_request_security(request)
            if not is_valid:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Security validation failed", "message": error_message}
                )
                
            # Authentication for protected endpoints
            if self.security.auth_manager.is_endpoint_protected(str(request.url.path)):
                auth_result = await self._authenticate_request(request)
                if not auth_result["success"]:
                    self.security.auth_manager.record_failed_attempt(client_ip)
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Authentication required", "message": auth_result["message"]}
                    )
                    
            # Input validation for requests with body
            if request.method in ["POST", "PUT", "PATCH"]:
                validation_result = await self._validate_request_body(request)
                if not validation_result["success"]:
                    self.security.audit_logger.log_security_event(
                        "input_validation_failed", client_ip, 
                        validation_result["message"], "high"
                    )
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Input validation failed", "message": "Invalid request data"}
                    )
            
            # Process request
            response = await call_next(request)
            
            # Post-request processing
            self.security.add_security_headers(response)
            
            # Log successful request
            duration = time.time() - start_time
            self.security.audit_logger.log_security_event(
                "request_processed", client_ip,
                f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s",
                "info"
            )
            
            return response
            
        except Exception as e:
            # Secure error handling - don't expose internal details
            self.security.audit_logger.log_security_event(
                "internal_error", client_ip,
                f"Error processing {request.method} {request.url.path}: {type(e).__name__}",
                "error"
            )
            
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "message": "An error occurred processing your request"}
            )
            
    async def _authenticate_request(self, request: Request) -> Dict[str, Any]:
        """Authenticate request using API key"""
        # Check for API key in header
        auth_header = request.headers.get("Authorization")
        api_key = None
        
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
        elif "X-API-Key" in request.headers:
            api_key = request.headers["X-API-Key"]
            
        if not api_key:
            return {"success": False, "message": "API key required"}
            
        # Validate API key
        key_info = self.security.auth_manager.validate_api_key(api_key)
        if not key_info:
            return {"success": False, "message": "Invalid API key"}
            
        # Check permissions
        if not self.security.auth_manager.check_permission(
            key_info, str(request.url.path), request.method
        ):
            return {"success": False, "message": "Insufficient permissions"}
            
        return {"success": True, "key_info": key_info}
        
    async def _validate_request_body(self, request: Request) -> Dict[str, Any]:
        """Validate request body for security threats"""
        try:
            # Read request body
            body = await request.body()
            if not body:
                return {"success": True}
                
            # Parse JSON if content-type is application/json
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    data = json.loads(body.decode('utf-8'))
                    
                    # Validate JSON structure depth
                    if self._json_depth(data) > SECURITY_CONFIG["MAX_JSON_DEPTH"]:
                        return {"success": False, "message": "JSON structure too deep"}
                        
                    # Validate all string values in JSON
                    violations = self._validate_json_values(data)
                    if violations:
                        return {"success": False, "message": f"Security violations detected: {violations}"}
                        
                except json.JSONDecodeError:
                    return {"success": False, "message": "Invalid JSON format"}
            else:
                # Validate raw body content
                body_str = body.decode('utf-8', errors='ignore')
                try:
                    _, metadata = validate_enhanced_security(
                        body_str, "request_body", 
                        SECURITY_CONFIG["MAX_REQUEST_SIZE"],
                        SECURITY_CONFIG["STRICT_VALIDATION"]
                    )
                    
                    if metadata["severity"] in ["critical", "high"]:
                        return {"success": False, "message": f"Security threats detected: {metadata['threats_detected']}"}
                        
                except SecurityValidationError as e:
                    return {"success": False, "message": str(e)}
                    
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "message": f"Validation error: {type(e).__name__}"}
            
    def _json_depth(self, obj, depth=0) -> int:
        """Calculate JSON object depth"""
        if depth > SECURITY_CONFIG["MAX_JSON_DEPTH"]:
            return depth
            
        if isinstance(obj, dict):
            if not obj:
                return depth
            return max(self._json_depth(value, depth + 1) for value in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return depth
            return max(self._json_depth(item, depth + 1) for item in obj)
        else:
            return depth
            
    def _validate_json_values(self, obj, path="root") -> List[str]:
        """Recursively validate all string values in JSON"""
        violations = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                violations.extend(self._validate_json_values(value, f"{path}.{key}"))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                violations.extend(self._validate_json_values(item, f"{path}[{i}]"))
        elif isinstance(obj, str):
            try:
                _, metadata = validate_enhanced_security(
                    obj, path, len(obj) * 2,  # Allow reasonable length for JSON values
                    SECURITY_CONFIG["STRICT_VALIDATION"]
                )
                
                if metadata["severity"] in ["critical", "high"]:
                    violations.append(f"{path}: {metadata['threats_detected']}")
                    
            except SecurityValidationError:
                violations.append(f"{path}: security validation failed")
                
        return violations

def create_security_manager() -> SecurityManager:
    """Factory function to create security manager"""
    return SecurityManager()

# Export for use in server
__all__ = [
    "SecurityManager", 
    "SecurityMiddleware", 
    "create_security_manager",
    "SECURITY_CONFIG"
]