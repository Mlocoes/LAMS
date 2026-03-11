"""
Session Management Service (Phase 3.1)

Handles user session tracking, limits, and device management:
- Creates and validates sessions
- Enforces max concurrent sessions per user
- Tracks device information for security
- Provides session cleanup and management
"""

import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from user_agents import parse
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from database.models import UserSession
from core.config import settings

logger = logging.getLogger("security")


class SessionService:
    """Service for managing user sessions with device tracking"""
    
    @staticmethod
    def _detect_device_type(user_agent) -> str:
        """
        Detects device type from user agent.
        
        Returns: 'mobile', 'tablet', 'desktop', or 'other'
        """
        if user_agent.is_mobile:
            return "mobile"
        elif user_agent.is_tablet:
            return "tablet"
        elif user_agent.is_pc:
            return "desktop"
        else:
            return "other"
    
    @staticmethod
    async def create_session(
        db: AsyncSession,
        user_id: int,
        request: Request,
        refresh_token_id: Optional[int] = None
    ) -> UserSession:
        """
        Creates a new session for a user.
        
        - Parses device information from User-Agent
        - Enforces max sessions per user limit
        - Terminates oldest session if limit exceeded
        
        Args:
            db: Database session
            user_id: ID of the user
            request: FastAPI Request object (for headers and IP)
            refresh_token_id: Optional associated refresh token ID
            
        Returns:
            Created UserSession object
        """
        # Parse user agent
        user_agent_string = request.headers.get("user-agent", "")
        user_agent = parse(user_agent_string)
        
        # Check active sessions count
        active_sessions = await SessionService.get_active_sessions(db, user_id)
        
        # Enforce session limit
        if len(active_sessions) >= settings.MAX_SESSIONS_PER_USER:
            # Terminate oldest session (by last_activity)
            oldest_session = min(active_sessions, key=lambda s: s.last_activity or s.created_at)
            await SessionService.terminate_session(db, oldest_session.id)
            
            logger.info(
                "session_limit_enforced",
                extra={
                    "user_id": user_id,
                    "terminated_session_id": oldest_session.id,
                    "max_sessions": settings.MAX_SESSIONS_PER_USER
                }
            )
        
        # Create new session
        session = UserSession(
            user_id=user_id,
            session_token=secrets.token_urlsafe(32),
            refresh_token_id=refresh_token_id,
            device_name=user_agent.device.family,
            device_type=SessionService._detect_device_type(user_agent),
            browser=f"{user_agent.browser.family} {user_agent.browser.version_string}",
            os=f"{user_agent.os.family} {user_agent.os.version_string}",
            ip_address=request.client.host if request.client else None,
            user_agent=user_agent_string,
            expires_at=datetime.now(timezone.utc) + timedelta(
                days=settings.SESSION_ABSOLUTE_TIMEOUT_DAYS
            ),
            is_active=True
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        logger.info(
            "session_created",
            extra={
                "user_id": user_id,
                "session_id": session.id,
                "device_type": session.device_type,
                "ip_address": session.ip_address
            }
        )
        
        return session
    
    @staticmethod
    async def get_active_sessions(
        db: AsyncSession,
        user_id: int
    ) -> List[UserSession]:
        """
        Gets all active sessions for a user.
        
        Active sessions are:
        - is_active = True
        - expires_at > now
        - last_activity within idle timeout
        
        Args:
            db: Database session
            user_id: ID of the user
            
        Returns:
            List of active UserSession objects
        """
        now = datetime.now(timezone.utc)
        idle_threshold = now - timedelta(minutes=settings.SESSION_IDLE_TIMEOUT_MINUTES)
        
        stmt = select(UserSession).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.expires_at > now,
                UserSession.last_activity > idle_threshold
            )
        ).order_by(UserSession.last_activity.desc())
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def get_session_by_token(
        db: AsyncSession,
        session_token: str
    ) -> Optional[UserSession]:
        """
        Gets a session by its token.
        
        Args:
            db: Database session
            session_token: Session token to look up
            
        Returns:
            UserSession object or None if not found
        """
        stmt = select(UserSession).where(
            UserSession.session_token == session_token
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_activity(
        db: AsyncSession,
        session_token: str
    ) -> bool:
        """
        Updates the last_activity timestamp for a session.
        
        Should be called on every authenticated API request.
        
        Args:
            db: Database session
            session_token: Session token to update
            
        Returns:
            True if updated, False if session not found
        """
        session = await SessionService.get_session_by_token(db, session_token)
        
        if session and session.is_active:
            session.last_activity = datetime.now(timezone.utc)
            await db.commit()
            return True
        
        return False
    
    @staticmethod
    async def terminate_session(
        db: AsyncSession,
        session_id: int
    ) -> bool:
        """
        Terminates a specific session.
        
        Sets is_active = False.
        
        Args:
            db: Database session
            session_id: ID of the session to terminate
            
        Returns:
            True if terminated, False if session not found
        """
        stmt = select(UserSession).where(UserSession.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if session:
            session.is_active = False
            await db.commit()
            
            logger.info(
                "session_terminated",
                extra={
                    "session_id": session_id,
                    "user_id": session.user_id
                }
            )
            
            return True
        
        return False
    
    @staticmethod
    async def terminate_all_sessions(
        db: AsyncSession,
        user_id: int,
        except_session_token: Optional[str] = None
    ) -> int:
        """
        Terminates all sessions for a user.
        
        Optionally excludes current session (for "logout other devices").
        
        Args:
            db: Database session
            user_id: ID of the user
            except_session_token: Optional session token to preserve
            
        Returns:
            Number of sessions terminated
        """
        stmt = select(UserSession).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        )
        
        result = await db.execute(stmt)
        sessions = result.scalars().all()
        
        count = 0
        for session in sessions:
            if except_session_token and session.session_token == except_session_token:
                continue  # Skip current session
            
            session.is_active = False
            count += 1
        
        await db.commit()
        
        logger.info(
            "sessions_bulk_terminated",
            extra={
                "user_id": user_id,
                "count": count,
                "preserved_session": except_session_token is not None
            }
        )
        
        return count
    
    @staticmethod
    async def cleanup_expired_sessions(db: AsyncSession) -> int:
        """
        Cleanup job: Deactivates expired and idle sessions.
        
        Should be run periodically (e.g., daily cron job).
        
        Deactivates sessions that:
        - Have passed expires_at timestamp
        - Have been idle beyond SESSION_IDLE_TIMEOUT_MINUTES
        
        Args:
            db: Database session
            
        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now(timezone.utc)
        idle_threshold = now - timedelta(minutes=settings.SESSION_IDLE_TIMEOUT_MINUTES)
        
        # Find expired sessions
        stmt = select(UserSession).where(
            and_(
                UserSession.is_active == True,
                (
                    (UserSession.expires_at < now) |
                    (UserSession.last_activity < idle_threshold)
                )
            )
        )
        
        result = await db.execute(stmt)
        expired_sessions = result.scalars().all()
        
        count = 0
        for session in expired_sessions:
            session.is_active = False
            count += 1
        
        await db.commit()
        
        if count > 0:
            logger.info(
                "sessions_cleaned_up",
                extra={
                    "count": count,
                    "reason": "expired_or_idle"
                }
            )
        
        return count
    
    @staticmethod
    async def get_session_stats(db: AsyncSession, user_id: int) -> dict:
        """
        Gets session statistics for a user.
        
        Returns:
            Dict with session counts and info
        """
        # Active sessions
        active_sessions = await SessionService.get_active_sessions(db, user_id)
        
        # All sessions (including inactive)
        stmt = select(UserSession).where(UserSession.user_id == user_id)
        result = await db.execute(stmt)
        all_sessions = result.scalars().all()
        
        # Device breakdown
        device_counts = {}
        for session in active_sessions:
            device_type = session.device_type or "unknown"
            device_counts[device_type] = device_counts.get(device_type, 0) + 1
        
        return {
            "active_sessions": len(active_sessions),
            "total_sessions": len(all_sessions),
            "max_sessions": settings.MAX_SESSIONS_PER_USER,
            "device_breakdown": device_counts,
            "can_create_session": len(active_sessions) < settings.MAX_SESSIONS_PER_USER
        }
