"""
Tests para API de autenticación
Endpoints: /api/v1/auth/login, /api/v1/auth/me
"""
import pytest
from httpx import AsyncClient
from auth.security import get_password_hash


@pytest.mark.asyncio
class TestAuthLogin:
    """Tests para endpoint de login"""
    
    async def test_login_success(self, client: AsyncClient, admin_user):
        """Test login exitoso con credenciales correctas"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "admin@test.com",
                "password": "admin123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 50  # JWT tiene longitud considerable
    
    async def test_login_wrong_password(self, client: AsyncClient, admin_user):
        """Test login con contraseña incorrecta"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "admin@test.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "detail" in response.json()
    
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login con usuario inexistente"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@test.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 401
        assert "detail" in response.json()
    
    async def test_login_missing_fields(self, client: AsyncClient):
        """Test login sin campos requeridos"""
        # Sin username
        response = await client.post(
            "/api/v1/auth/login",
            data={"password": "password123"}
        )
        assert response.status_code == 422
        
        # Sin password
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@test.com"}
        )
        assert response.status_code == 422
    
    async def test_login_empty_credentials(self, client: AsyncClient):
        """Test login con credenciales vacías"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "",
                "password": ""
            }
        )
        
        assert response.status_code in [401, 422]


@pytest.mark.asyncio
class TestAuthMe:
    """Tests para endpoint /auth/me"""
    
    async def test_get_current_user_success(self, client: AsyncClient, admin_token: str, admin_user):
        """Test obtener usuario actual con token válido"""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == admin_user.email
        assert data["role"] == admin_user.role
        assert "id" in data
        assert "created_at" in data
        assert "password_hash" not in data  # No debe exponer hash
    
    async def test_get_current_user_no_token(self, client: AsyncClient):
        """Test acceder sin token de autenticación"""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test acceder con token inválido"""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        
        assert response.status_code == 401
    
    async def test_get_current_user_malformed_header(self, client: AsyncClient, admin_token: str):
        """Test con header de autorización malformado"""
        # Sin "Bearer"
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": admin_token}
        )
        assert response.status_code == 401
        
        # Formato incorrecto
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Token {admin_token}"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestAuthRoles:
    """Tests para autorización basada en roles"""
    
    async def test_admin_can_access_admin_endpoints(self, client: AsyncClient, admin_token: str):
        """Test que admin puede acceder a endpoints de admin"""
        response = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Debería permitir acceso (200) o no encontrar endpoint (404), pero no 403 Forbidden
        assert response.status_code in [200, 404]
        assert response.status_code != 403
    
    async def test_regular_user_token_works(self, client: AsyncClient, user_token: str):
        """Test que token de usuario regular funciona para endpoints públicos"""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "user"


@pytest.mark.asyncio
class TestTokenSecurity:
    """Tests de seguridad para tokens"""
    
    async def test_token_is_different_for_different_users(self, client: AsyncClient, admin_token: str, user_token: str):
        """Test que cada usuario tiene token único"""
        assert admin_token != user_token
    
    async def test_token_contains_user_info(self, client: AsyncClient, admin_token: str, admin_user):
        """Test que endpoint /me devuelve info correcta del usuario del token"""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == admin_user.email
