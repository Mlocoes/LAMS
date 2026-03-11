from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

from core.config import settings
from core.logging_config import setup_logging, setup_encrypted_logging
from database.database import engine, Base
from api import api_router
from middleware import SecurityHeadersMiddleware, RequestSizeLimitMiddleware, SecurityLoggingMiddleware, CSRFProtectionMiddleware, SessionActivityMiddleware

# Phase 2.6: Setup structured logging
setup_logging()

# Phase 3.6: Setup encrypted logging (only in production)
if settings.ENVIRONMENT == "production":
    setup_encrypted_logging(enable=True, log_dir="/var/log/lams")

logger = logging.getLogger("lams")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Import all models to ensure they are registered with Base
    from database import models  # noqa: F401
    
    # Initialize DB (Create tables if they don't exist)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default admin user if DB is empty
    from sqlalchemy.future import select
    from database.database import async_session_maker
    from database.models import User
    from auth.security import get_password_hash
    import os
    
    # Get admin credentials from environment variables
    admin_email = os.getenv("ADMIN_EMAIL", "admin@lams.io")
    admin_password = os.getenv("ADMIN_PASSWORD", "lams2024")
    
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == admin_email))
        if not result.scalar_one_or_none():
            admin = User(
                email=admin_email,
                password_hash=get_password_hash(admin_password),
                is_admin=True,
                must_change_password=False,  # Allow direct access - user can change password from settings
            )
            session.add(admin)
            await session.commit()
            print(f"⚠️  Default admin user created: {admin_email}")
            print("⚠️  SECURITY: Password must be changed on first login!")

    # Start the Alert Engine Scheduler
    from alerts.engine import evaluate_rules
    from maintenance.cleanup import run_maintenance_job
    
    scheduler = AsyncIOScheduler()
    
    # Alert evaluation every minute
    scheduler.add_job(evaluate_rules, 'interval', minutes=1)
    
    # Data retention and cleanup job (daily at configured hour)
    scheduler.add_job(
        run_maintenance_job,
        'cron',
        hour=settings.CLEANUP_SCHEDULE_HOUR,
        minute=settings.CLEANUP_SCHEDULE_MINUTE,
        id='maintenance_job'
    )
    
    scheduler.start()

    yield

    # Cleanup on shutdown
    scheduler.shutdown()
    await engine.dispose()


# Phase 3.3: Disable interactive docs in production
# Prevents token exposure in URL query params and logs
app = FastAPI(
    title=settings.PROJECT_NAME, 
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
)

# Phase 2.1: Rate Limiting
# Configure rate limiter with slowapi
limiter = Limiter(key_func=get_remote_address, default_limits=["100/hour"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Phase 2.3: Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# Phase 2.4: Request Size Limit Middleware (10MB max)
app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)

# Phase 2.6: Security Logging Middleware
app.add_middleware(SecurityLoggingMiddleware)

# Phase 3.1: Session Activity Tracking Middleware
# Updates last_activity timestamp for idle timeout detection
app.add_middleware(SessionActivityMiddleware)

# Phase 2.5: CSRF Protection Middleware
# Double-submit cookie pattern for CSRF protection
app.add_middleware(CSRFProtectionMiddleware)

# CORS - Security hardened (Phase 1.3)
# Only allows specified origins from configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # From environment variable
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-CSRF-Token"],
    expose_headers=["Content-Length", "X-Total-Count"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Phase 3.3: Middleware to block docs access in production
@app.middleware("http")
async def block_docs_in_production(request: Request, call_next):
    """
    Blocks access to /docs, /redoc, and /openapi.json in production.
    Prevents token exposure in URL query params.
    """
    if settings.ENVIRONMENT == "production":
        docs_paths = ["/docs", "/redoc", "/openapi.json"]
        if request.url.path in docs_paths:
            security_logger = logging.getLogger("security")
            security_logger.warning(
                "docs_access_blocked",
                extra={
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent", "unknown")
                }
            )
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=404,
                content={"detail": "Not Found"}
            )
    
    response = await call_next(request)
    return response

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "LAMS Central Server is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "LAMS Central Server"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
