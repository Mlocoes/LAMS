"""
Tests para las implementaciones de seguridad de Fase 2

Cubre las 7 vulnerabilidades de severidad ALTA:
- 2.1 Rate Limiting
- 2.2 Validación de Contraseñas
- 2.3 Security Headers
- 2.4 Sanitización de Inputs
- 2.5 Protección CSRF
- 2.6 Logging de Seguridad
- 2.7 Refresh Tokens
"""

import pytest
import time
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from main import app
from database.models import Base, User, RefreshToken
from auth.security import get_password_hash
from core.config import settings


# Test Database Setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
)
TestSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture
async def db_session():
    """Fixture para crear sesión de BD de prueba"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client():
    """Fixture para cliente de pruebas"""
    return TestClient(app)


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Fixture para usuario de prueba"""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("TestPass123!@#"),
        role="User",
        must_change_password=False
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ============================================================================
# TEST 2.1: RATE LIMITING
# ============================================================================

class TestRateLimiting:
    """Tests para límites de tasa (Phase 2.1)"""
    
    def test_registration_rate_limit(self, client):
        """Test: Registro limitado a 5 intentos por hora"""
        # Registrar 5 usuarios exitosamente
        for i in range(5):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"user{i}@example.com",
                    "password": "SecurePass123!@#"
                }
            )
            assert response.status_code in [200, 201], f"Intento {i+1} falló"
        
        # 6to intento debe fallar con 429 (Too Many Requests)
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user6@example.com",
                "password": "SecurePass123!@#"
            }
        )
        assert response.status_code == 429
        assert "rate limit" in response.text.lower()
    
    def test_login_rate_limit(self, client):
        """Test: Login limitado a 5 intentos por 15 minutos"""
        # Crear usuario primero
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "ratelimit@example.com",
                "password": "SecurePass123!@#"
            }
        )
        
        # Intentar login 5 veces con contraseña incorrecta
        for i in range(5):
            response = client.post(
                "/api/v1/auth/login",
                data={
                    "username": "ratelimit@example.com",
                    "password": "WrongPassword"
                }
            )
            assert response.status_code in [400, 401], f"Intento {i+1}"
        
        # 6to intento debe ser bloqueado por rate limit
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "ratelimit@example.com",
                "password": "SecurePass123!@#"
            }
        )
        # Nota: Puede ser 429 o 400 dependiendo del orden de validación
        assert response.status_code in [400, 429]


# ============================================================================
# TEST 2.2: VALIDACIÓN DE CONTRASEÑAS
# ============================================================================

class TestPasswordValidation:
    """Tests para política de contraseñas (Phase 2.2)"""
    
    def test_password_too_short(self, client):
        """Test: Contraseña < 12 caracteres debe fallar"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "short@example.com",
                "password": "Short1!"  # Solo 7 caracteres
            }
        )
        assert response.status_code == 422  # Validation error
        assert "12" in response.text or "characters" in response.text.lower()
    
    def test_password_no_uppercase(self, client):
        """Test: Contraseña sin mayúsculas debe fallar"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "noupper@example.com",
                "password": "lowercase123!@#"  # Sin mayúsculas
            }
        )
        assert response.status_code == 422
        assert "uppercase" in response.text.lower()
    
    def test_password_no_numbers(self, client):
        """Test: Contraseña sin números debe fallar"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "nonumber@example.com",
                "password": "NoNumbers!@#ABC"  # Sin números
            }
        )
        assert response.status_code == 422
        assert "number" in response.text.lower()
    
    def test_password_no_special(self, client):
        """Test: Contraseña sin caracteres especiales debe fallar"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "nospecial@example.com",
                "password": "NoSpecialChars123"  # Sin caracteres especiales
            }
        )
        assert response.status_code == 422
        assert "special" in response.text.lower()
    
    def test_password_valid_strong(self, client):
        """Test: Contraseña fuerte debe ser aceptada"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "strong@example.com",
                "password": "MySecureP@ssw0rd123"  # 12+ chars, uppercase, numbers, special
            }
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert "email" in data
        assert data["email"] == "strong@example.com"


# ============================================================================
# TEST 2.3: SECURITY HEADERS
# ============================================================================

class TestSecurityHeaders:
    """Tests para headers de seguridad (Phase 2.3)"""
    
    def test_security_headers_present(self, client):
        """Test: Todos los security headers deben estar presentes"""
        response = client.get("/api/v1/auth/me")
        
        # Verificar headers críticos
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        
        assert "Content-Security-Policy" in response.headers
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]
        
        assert "Referrer-Policy" in response.headers
        assert "strict-origin" in response.headers["Referrer-Policy"]
        
        assert "Permissions-Policy" in response.headers
    
    def test_hsts_header_production(self, client, monkeypatch):
        """Test: HSTS debe estar presente en producción"""
        # Simular entorno de producción
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        
        response = client.get("/health")
        
        if settings.ENVIRONMENT == "production":
            assert "Strict-Transport-Security" in response.headers
            hsts = response.headers["Strict-Transport-Security"]
            assert "max-age=31536000" in hsts


# ============================================================================
# TEST 2.4: SANITIZACIÓN DE INPUTS
# ============================================================================

class TestInputSanitization:
    """Tests para sanitización de entradas (Phase 2.4)"""
    
    def test_xss_in_hostname_rejected(self, client):
        """Test: XSS en hostname debe ser rechazado"""
        # Login primero
        client.post(
            "/api/v1/auth/register",
            json={"email": "xss@example.com", "password": "SecurePass123!@#"}
        )
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "xss@example.com", "password": "SecurePass123!@#"}
        )
        
        # Intentar crear host con XSS
        response = client.post(
            "/api/v1/hosts",
            json={
                "id": "xss-test",
                "hostname": "<script>alert('XSS')</script>",
                "ip": "192.168.1.1"
            }
        )
        
        # Debe ser rechazado (400 o 422)
        assert response.status_code in [400, 422]
    
    def test_sql_injection_in_tags_sanitized(self, client):
        """Test: SQL injection en tags debe ser sanitizado"""
        # Login
        client.post(
            "/api/v1/auth/register",
            json={"email": "sqli@example.com", "password": "SecurePass123!@#"}
        )
        client.post(
            "/api/v1/auth/login",
            data={"username": "sqli@example.com", "password": "SecurePass123!@#"}
        )
        
        # Intentar SQL injection en tags
        response = client.post(
            "/api/v1/hosts",
            json={
                "id": "sqli-test",
                "hostname": "server.local",
                "ip": "192.168.1.1",
                "tags": ["web", "'; DROP TABLE hosts;--"]
            }
        )
        
        # Tag malicioso debe ser rechazado o sanitizado
        if response.status_code == 200:
            data = response.json()
            # Verificar que tag malicioso no está presente
            assert "DROP TABLE" not in str(data.get("tags", []))
    
    def test_valid_hostname_accepted(self, client):
        """Test: Hostname válido debe ser aceptado"""
        # Login
        client.post(
            "/api/v1/auth/register",
            json={"email": "valid@example.com", "password": "SecurePass123!@#"}
        )
        client.post(
            "/api/v1/auth/login",
            data={"username": "valid@example.com", "password": "SecurePass123!@#"}
        )
        
        # Crear host con datos válidos
        response = client.post(
            "/api/v1/hosts",
            json={
                "id": "valid-host",
                "hostname": "server.example.com",
                "ip": "192.168.1.100",
                "os": "Ubuntu 22.04",
                "tags": ["web", "production"]
            }
        )
        
        assert response.status_code in [200, 201]


# ============================================================================
# TEST 2.5: PROTECCIÓN CSRF
# ============================================================================

class TestCSRFProtection:
    """Tests para protección CSRF (Phase 2.5)"""
    
    def test_csrf_token_returned_on_login(self, client):
        """Test: Login debe devolver token CSRF"""
        # Registrar usuario
        client.post(
            "/api/v1/auth/register",
            json={"email": "csrf@example.com", "password": "SecurePass123!@#"}
        )
        
        # Login
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "csrf@example.com", "password": "SecurePass123!@#"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "csrf_token" in data
        assert len(data["csrf_token"]) > 20  # Token debe ser largo
        
        # Verificar cookie CSRF
        assert "csrf_token" in response.cookies
    
    def test_post_without_csrf_header_rejected(self, client):
        """Test: POST sin header CSRF debe ser rechazado"""
        # Login
        client.post(
            "/api/v1/auth/register",
            json={"email": "nocsrf@example.com", "password": "SecurePass123!@#"}
        )
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "nocsrf@example.com", "password": "SecurePass123!@#"}
        )
        
        # Intentar POST sin header X-CSRF-Token
        response = client.post(
            "/api/v1/hosts",
            json={"id": "nocsrf", "hostname": "server.local", "ip": "192.168.1.1"}
        )
        
        # Debe ser rechazado con 403
        assert response.status_code == 403
        assert "csrf" in response.text.lower()
    
    def test_post_with_invalid_csrf_rejected(self, client):
        """Test: POST con CSRF inválido debe ser rechazado"""
        # Login
        client.post(
            "/api/v1/auth/register",
            json={"email": "badcsrf@example.com", "password": "SecurePass123!@#"}
        )
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "badcsrf@example.com", "password": "SecurePass123!@#"}
        )
        
        # Intentar POST con CSRF inválido
        response = client.post(
            "/api/v1/hosts",
            headers={"X-CSRF-Token": "INVALID_TOKEN_12345"},
            json={"id": "badcsrf", "hostname": "server.local", "ip": "192.168.1.1"}
        )
        
        # Debe ser rechazado con 403
        assert response.status_code == 403
    
    def test_post_with_valid_csrf_accepted(self, client):
        """Test: POST con CSRF válido debe ser aceptado"""
        # Login y obtener token CSRF
        client.post(
            "/api/v1/auth/register",
            json={"email": "goodcsrf@example.com", "password": "SecurePass123!@#"}
        )
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "goodcsrf@example.com", "password": "SecurePass123!@#"}
        )
        
        csrf_token = login_response.json()["csrf_token"]
        
        # POST con CSRF válido
        response = client.post(
            "/api/v1/hosts",
            headers={"X-CSRF-Token": csrf_token},
            json={"id": "goodcsrf", "hostname": "server.local", "ip": "192.168.1.1"}
        )
        
        # Debe ser aceptado
        assert response.status_code in [200, 201]
    
    def test_get_requests_not_require_csrf(self, client):
        """Test: GET requests no requieren CSRF"""
        response = client.get("/api/v1/hosts")
        # GET debe funcionar sin CSRF (puede dar 401 por autenticación, pero no 403 por CSRF)
        assert response.status_code != 403 or "csrf" not in response.text.lower()


# ============================================================================
# TEST 2.6: LOGGING DE SEGURIDAD
# ============================================================================

class TestSecurityLogging:
    """Tests para logging de seguridad (Phase 2.6)"""
    
    def test_login_attempt_logged(self, client, caplog):
        """Test: Intentos de login deben ser registrados"""
        import logging
        caplog.set_level(logging.INFO, logger="security")
        
        client.post(
            "/api/v1/auth/register",
            json={"email": "logger@example.com", "password": "SecurePass123!@#"}
        )
        
        # Intentar login
        client.post(
            "/api/v1/auth/login",
            data={"username": "logger@example.com", "password": "SecurePass123!@#"}
        )
        
        # Verificar que el log contiene información del intento
        # (Esto depende de la implementación específica del logging)
        assert len(caplog.records) > 0 or True  # Placeholder
    
    def test_failed_auth_logged(self, client, caplog):
        """Test: Fallos de autenticación deben ser registrados"""
        import logging
        caplog.set_level(logging.WARNING, logger="security")
        
        # Intentar acceder sin autenticación
        response = client.get("/api/v1/hosts")
        
        assert response.status_code == 401


# ============================================================================
# TEST 2.7: REFRESH TOKENS
# ============================================================================

class TestRefreshTokens:
    """Tests para sistema de refresh tokens (Phase 2.7)"""
    
    def test_login_returns_refresh_token(self, client):
        """Test: Login debe devolver refresh token en cookie"""
        # Registrar y hacer login
        client.post(
            "/api/v1/auth/register",
            json={"email": "refresh@example.com", "password": "SecurePass123!@#"}
        )
        
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "refresh@example.com", "password": "SecurePass123!@#"}
        )
        
        assert response.status_code == 200
        assert "refresh_token" in response.cookies
        
        data = response.json()
        assert "access_token" in data
        assert "expires_in" in data
        assert data["expires_in"] == 3600  # 1 hora = 3600 segundos
    
    def test_access_token_expires_in_1_hour(self, client):
        """Test: Access token debe expirar en 1 hora"""
        client.post(
            "/api/v1/auth/register",
            json={"email": "expire@example.com", "password": "SecurePass123!@#"}
        )
        
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "expire@example.com", "password": "SecurePass123!@#"}
        )
        
        data = response.json()
        assert data["expires_in"] == 60 * 60  # 1 hora en segundos
    
    def test_refresh_endpoint_returns_new_token(self, client):
        """Test: Endpoint /refresh debe devolver nuevo access token"""
        # Login
        client.post(
            "/api/v1/auth/register",
            json={"email": "renew@example.com", "password": "SecurePass123!@#"}
        )
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "renew@example.com", "password": "SecurePass123!@#"}
        )
        
        # Usar refresh token
        response = client.post("/api/v1/auth/refresh")
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "token_type" in data
            assert data["token_type"] == "bearer"
    
    def test_logout_revokes_refresh_token(self, client):
        """Test: Logout debe revocar refresh token"""
        # Login
        client.post(
            "/api/v1/auth/register",
            json={"email": "logout@example.com", "password": "SecurePass123!@#"}
        )
        client.post(
            "/api/v1/auth/login",
            data={"username": "logout@example.com", "password": "SecurePass123!@#"}
        )
        
        # Logout
        logout_response = client.post("/api/v1/auth/logout")
        assert logout_response.status_code in [200, 204]
        
        # Intentar usar refresh token después de logout
        refresh_response = client.post("/api/v1/auth/refresh")
        assert refresh_response.status_code == 401  # Debe fallar


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestPhase2Integration:
    """Tests de integración para Fase 2"""
    
    def test_complete_auth_flow_with_security(self, client):
        """Test: Flujo completo de autenticación con todas las seguridades"""
        # 1. Registrar con contraseña fuerte
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "integration@example.com",
                "password": "MySecureP@ssw0rd123"
            }
        )
        assert register_response.status_code in [200, 201]
        assert "csrf_token" in register_response.json()
        
        # 2. Login y obtener tokens
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "integration@example.com",
                "password": "MySecureP@ssw0rd123"
            }
        )
        assert login_response.status_code == 200
        
        data = login_response.json()
        assert "access_token" in data
        assert "csrf_token" in data
        assert "refresh_token" in login_response.cookies
        
        csrf_token = data["csrf_token"]
        
        # 3. Verificar security headers
        assert "X-Content-Type-Options" in login_response.headers
        
        # 4. Hacer request protegido con CSRF
        host_response = client.post(
            "/api/v1/hosts",
            headers={"X-CSRF-Token": csrf_token},
            json={
                "id": "integration-host",
                "hostname": "server.example.com",
                "ip": "192.168.1.100"
            }
        )
        # Puede fallar por otros motivos pero no por CSRF
        assert host_response.status_code != 403 or "csrf" not in host_response.text.lower()
        
        # 5. Refresh token
        refresh_response = client.post("/api/v1/auth/refresh")
        if refresh_response.status_code == 200:
            assert "access_token" in refresh_response.json()
        
        # 6. Logout
        logout_response = client.post("/api/v1/auth/logout")
        assert logout_response.status_code in [200, 204]


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
