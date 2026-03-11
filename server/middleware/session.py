"""
Session activity tracking middleware (Phase 3.1)

Updates last_activity timestamp on every authenticated request.
This enables idle timeout detection and user activity monitoring.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from database.database import async_session_maker
from services.session_service import SessionService
import logging

logger = logging.getLogger("security")


class SessionActivityMiddleware(BaseHTTPMiddleware):
    """
    Updates session activity timestamp on every request.
    
    Flow:
    1. Check if request has session_token cookie
    2. If yes, update last_activity timestamp
    3. Logs errors but doesn't block requests
    
    Purpose: Enable idle timeout detection for security.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Get session token from cookie
        session_token = request.cookies.get("session_token")
        
        if session_token:
            # Update activity in background (non-blocking)
            try:
                async with async_session_maker() as db:
                    await SessionService.update_activity(db, session_token)
            except Exception as e:
                # Log error but don't block request
                logger.error(
                    "Failed to update session activity",
                    extra={
                        "error": str(e),
                        "session_token": session_token[:10] + "...",  # Truncate for security
                        "path": request.url.path
                    }
                )
        
        response = await call_next(request)
        return response
