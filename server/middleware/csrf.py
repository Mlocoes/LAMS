"""
Middleware de protección CSRF (Cross-Site Request Forgery)

Implementa protección CSRF mediante tokens de doble envío:
- Token almacenado en cookie HttpOnly
- Token enviado en header X-CSRF-Token para requests mutantes
- Validación de coincidencia entre cookie y header

Excluye endpoints que usan autenticación por API key (agente).
"""

import secrets
import logging
from typing import Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("security")

# Métodos HTTP que requieren protección CSRF
CSRF_PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Endpoints excluidos de protección CSRF (autenticación por API key)
CSRF_EXEMPT_PATHS = {
    "/api/agent/metrics",
    "/api/agent/heartbeat",
    "/api/agent/register",
    "/api/health",
    "/docs",
    "/openapi.json",
    "/api/v1/auth/login",      # Login genera el token CSRF
    "/api/v1/auth/register",   # Registro genera el token CSRF
    "/api/v1/hosts/register",  # Agentes registrando hosts
    "/api/v1/metrics/",        # Agentes enviando métricas
    "/api/v1/metrics",         # Prometheus scraper (sin autenticación)
    "/api/v1/docker/sync",     # Agentes sincronizando Docker
    "/api/v1/commands/",       # Agentes consultando comandos pendientes
    "/api/v1/agents/generate", # Generación de API keys para agentes
}


def generate_csrf_token() -> str:
    """
    Genera un token CSRF criptográficamente seguro.
    
    Returns:
        Token CSRF de 32 bytes en formato URL-safe base64
    """
    return secrets.token_urlsafe(32)


def is_csrf_exempt(path: str) -> bool:
    """
    Verifica si un endpoint está exento de protección CSRF.
    
    Args:
        path: Ruta del endpoint
        
    Returns:
        True si el endpoint está exento, False en caso contrario
    """
    # Verificar paths exactos
    if path in CSRF_EXEMPT_PATHS:
        return True
    
    # Verificar prefijos (para endpoints del agente)
    if path.startswith("/api/agent/"):
        return True
    
    # Endpoints de comandos del agente (GET con parámetros)
    if path.startswith("/api/v1/commands/"):
        return True
    
    return False


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware de protección CSRF mediante tokens de doble envío.
    
    Funcionamiento:
    1. En login/register: Genera token CSRF y lo almacena en cookie
    2. En requests mutantes (POST/PUT/PATCH/DELETE): Valida token
    3. Compara token en cookie vs token en header X-CSRF-Token
    4. Rechaza requests sin token válido con HTTP 403
    
    Excepciones:
    - Endpoints del agente (autenticación por API key)
    - Métodos seguros (GET, HEAD, OPTIONS)
    - Endpoints en CSRF_EXEMPT_PATHS
    """
    
    async def dispatch(self, request: Request, call_next):
        # Permitir métodos seguros (no modifican estado)
        if request.method not in CSRF_PROTECTED_METHODS:
            response = await call_next(request)
            return response
        
        # Excluir endpoints específicos
        if is_csrf_exempt(request.url.path):
            response = await call_next(request)
            return response
        
        # Obtener token de la cookie
        csrf_cookie = request.cookies.get("csrf_token")
        
        # Obtener token del header
        csrf_header = request.headers.get("X-CSRF-Token")
        
        # Validar presencia de tokens
        if not csrf_cookie:
            logger.warning(
                "csrf_missing_cookie",
                extra={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "client_ip": request.client.host,
                }
            )
            raise HTTPException(
                status_code=403,
                detail="Token CSRF no encontrado. Por favor, inicia sesión nuevamente."
            )
        
        if not csrf_header:
            logger.warning(
                "csrf_missing_header",
                extra={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "client_ip": request.client.host,
                }
            )
            raise HTTPException(
                status_code=403,
                detail="Header X-CSRF-Token requerido para esta operación."
            )
        
        # Validar coincidencia de tokens (protección contra CSRF)
        if not secrets.compare_digest(csrf_cookie, csrf_header):
            logger.warning(
                "csrf_token_mismatch",
                extra={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "client_ip": request.client.host,
                }
            )
            raise HTTPException(
                status_code=403,
                detail="Token CSRF inválido. Posible ataque CSRF detectado."
            )
        
        # Token válido, procesar request
        logger.debug(
            "csrf_validated",
            extra={
                "endpoint": request.url.path,
                "method": request.method,
            }
        )
        
        response = await call_next(request)
        return response


def set_csrf_cookie(response: Response, csrf_token: str, secure: bool = False) -> None:
    """
    Establece la cookie CSRF en la respuesta.
    
    Args:
        response: Objeto Response de FastAPI/Starlette
        csrf_token: Token CSRF generado
        secure: Si True, cookie solo se envía por HTTPS (producción)
    """
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=True,           # No accesible desde JavaScript (previene XSS)
        secure=secure,           # Solo HTTPS en producción
        samesite="strict",       # Solo requests del mismo origen
        max_age=3600,            # 1 hora (igual que access token)
        path="/"                 # Disponible en toda la aplicación
    )
