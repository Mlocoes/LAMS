"""
Middleware module for LAMS
"""

from middleware.security import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    SecurityLoggingMiddleware
)

from middleware.csrf import (
    CSRFProtectionMiddleware,
    generate_csrf_token,
    set_csrf_cookie
)

from middleware.session import (
    SessionActivityMiddleware
)

__all__ = [
    "SecurityHeadersMiddleware",
    "RequestSizeLimitMiddleware",
    "SecurityLoggingMiddleware",
    "CSRFProtectionMiddleware",
    "SessionActivityMiddleware"
]
