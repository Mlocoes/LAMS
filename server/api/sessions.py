"""
API endpoints for session management (Phase 3.1)

Endpoints:
- GET /sessions - List user's active sessions
- GET /sessions/stats - Get session statistics
- DELETE /sessions/{session_id} - Terminate specific session
- DELETE /sessions - Terminate all sessions except current
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime

from database.models import User, UserSession
from api.dependencies import get_db, get_current_user
from services.session_service import SessionService

router = APIRouter()


# Response models
from pydantic import BaseModel

class SessionResponse(BaseModel):
    id: int
    device_name: str | None
    device_type: str | None
    browser: str | None
    os: str | None
    ip_address: str | None
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    is_current: bool
    
    class Config:
        from_attributes = True


class SessionStatsResponse(BaseModel):
    active_sessions: int
    total_sessions: int
    max_sessions: int
    device_breakdown: dict
    can_create_session: bool


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists all active sessions for the current user.
    
    Returns device information and indicates which is the current session.
    Useful for security: users can see where they're logged in.
    """
    sessions = await SessionService.get_active_sessions(db, current_user.id)
    
    # Get current session token from cookie
    current_session_token = request.cookies.get("session_token")
    
    return [
        SessionResponse(
            id=s.id,
            device_name=s.device_name,
            device_type=s.device_type,
            browser=s.browser,
            os=s.os,
            ip_address=s.ip_address,
            created_at=s.created_at,
            last_activity=s.last_activity,
            expires_at=s.expires_at,
            is_current=s.session_token == current_session_token
        )
        for s in sessions
    ]


@router.get("/sessions/stats", response_model=SessionStatsResponse)
async def get_session_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Gets session statistics for the current user.
    
    Returns:
    - Active session count
    - Max allowed sessions
    - Device breakdown
    - Whether new sessions can be created
    """
    stats = await SessionService.get_session_stats(db, current_user.id)
    return SessionStatsResponse(**stats)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
async def terminate_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Terminates a specific session by ID.
    
    Security: Can only terminate own sessions.
    Useful for: "I don't recognize this device, sign it out".
    """
    # Verify session belongs to current user
    stmt = select(UserSession).where(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or does not belong to you"
        )
    
    success = await SessionService.terminate_session(db, session_id)
    
    if success:
        return {
            "message": "Session terminated successfully",
            "session_id": session_id
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to terminate session"
        )


@router.delete("/sessions", status_code=status.HTTP_200_OK)
async def terminate_all_sessions(
    request: Request,
    keep_current: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Terminates all sessions for the current user.
    
    Args:
        keep_current: If True (default), keeps current session active.
                     If False, terminates all including current (full logout).
    
    Returns:
        Number of sessions terminated
    
    Useful for:
    - "Sign out all devices"
    - Security response to compromised account
    """
    current_session_token = request.cookies.get("session_token") if keep_current else None
    
    count = await SessionService.terminate_all_sessions(
        db,
        current_user.id,
        except_session_token=current_session_token
    )
    
    return {
        "message": f"{count} session(s) terminated successfully",
        "count": count,
        "kept_current": keep_current
    }
