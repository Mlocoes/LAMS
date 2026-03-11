from fastapi import APIRouter
from api import auth, hosts, metrics, alerts, docker, alert_rules, notifications, commands, users, maintenance, agents, sessions, mfa, keys

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])  # Phase 3.1: Session management
api_router.include_router(mfa.router, prefix="/mfa", tags=["mfa"])  # Phase 3.2: MFA/2FA
api_router.include_router(keys.router, prefix="/keys", tags=["keys"])  # Phase 3.5: Key rotation
api_router.include_router(hosts.router, prefix="/hosts", tags=["hosts"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(docker.router, prefix="/docker", tags=["docker"])
api_router.include_router(alert_rules.router, prefix="/alert-rules", tags=["alert-rules"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(commands.router, prefix="/commands", tags=["commands"])
api_router.include_router(maintenance.router, prefix="/maintenance", tags=["maintenance"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
