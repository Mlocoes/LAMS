"""
Security Middleware (Phase 2)

Implements:
- HTTP Security Headers (HSTS, CSP, X-Frame-Options, etc.)
- Request size limiting
- Security logging
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from core.config import settings
import logging

security_logger = logging.getLogger('security')


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses (Phase 2.3)
    
    Headers added:
    - X-Content-Type-Options: Prevent MIME type sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable XSS filtering (legacy browsers)
    - Strict-Transport-Security: Force HTTPS (production only)
    - Content-Security-Policy: Prevent XSS and injection attacks
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Control browser features
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # X-Content-Type-Options: Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options: Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection: Enable XSS filtering (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Strict-Transport-Security: Force HTTPS (only in production)
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Content-Security-Policy: Prevent XSS and injection attacks
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # TODO: Remove unsafe-* in future
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # Referrer-Policy: Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy: Control browser features
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Limit request payload size to prevent DoS attacks (Phase 2.4)
    
    Default limit: 10MB
    Configurable per environment
    """
    
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        # Check Content-Length header
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            
            if content_length:
                try:
                    content_length = int(content_length)
                    if content_length > self.max_size:
                        security_logger.warning(
                            "Request size limit exceeded",
                            extra={
                                "client_ip": request.client.host if request.client else "unknown",
                                "path": request.url.path,
                                "content_length": content_length,
                                "max_size": self.max_size
                            }
                        )
                        return JSONResponse(
                            status_code=413,
                            content={
                                "detail": f"Request too large. Maximum size: {self.max_size} bytes"
                            }
                        )
                except ValueError:
                    pass
        
        return await call_next(request)


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log security-relevant events (Phase 2.6)
    
    Logs:
    - Failed authentication attempts
    - Suspicious requests
    - Rate limit violations
    - Access to sensitive endpoints
    """
    
    SENSITIVE_ENDPOINTS = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/change-password",
        "/api/v1/users",
        "/api/v1/agents",
        "/api/v1/alert-rules"
    ]
    
    async def dispatch(self, request: Request, call_next):
        # Log requests to sensitive endpoints
        if any(request.url.path.startswith(endpoint) for endpoint in self.SENSITIVE_ENDPOINTS):
            security_logger.info(
                "Sensitive endpoint accessed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else "unknown",
                    "user_agent": request.headers.get("user-agent", "unknown")
                }
            )
        
        # Execute request
        response = await call_next(request)
        
        # Log authentication failures
        if request.url.path.startswith("/api/v1/auth/login") and response.status_code in [400, 401]:
            security_logger.warning(
                "Failed login attempt",
                extra={
                    "client_ip": request.client.host if request.client else "unknown",
                    "user_agent": request.headers.get("user-agent", "unknown"),
                    "status_code": response.status_code
                }
            )
        
        # Log unauthorized access attempts
        if response.status_code == 403:
            security_logger.warning(
                "Unauthorized access attempt",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else "unknown",
                    "user_agent": request.headers.get("user-agent", "unknown")
                }
            )
        
        return response
