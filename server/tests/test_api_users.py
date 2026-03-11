"""
Tests para API de usuarios
Endpoints: /api/v1/users/*
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestUsersList:
    """Tests para listar usuarios"""
    
    async def test_list_users_as_admin(self, client: AsyncClient, auth_headers: dict, admin_user, regular_user):
        """Test listar usuarios como admin"""
        response = await client.get(
            "/api/v1/users/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        assert any(u["email"] == admin_user.email for u in data)
        assert any(u["email"] == regular_user.email for u in data)
    
    async def test_list_users_as_regular_user(self, client: AsyncClient, user_token: str):
        """Test listar usuarios como usuario regular (debería fallar)"""
        response = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        # Usuario regular no debería tener acceso
        assert response.status_code == 403
    
    async def test_list_users_unauthorized(self, client: AsyncClient):
        """Test listar usuarios sin autenticación"""
        response = await client.get("/api/v1/users/")
        
        assert response.status_code == 401
    
    async def test_users_do_not_expose_password_hash(self, client: AsyncClient, auth_headers: dict):
        """Test que respuesta no expone password_hash"""
        response = await client.get(
            "/api/v1/users/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        for user in data:
            assert "password_hash" not in user
            assert "password" not in user


@pytest.mark.asyncio
class TestUserCreation:
    """Tests para crear usuarios"""
    
    async def test_create_user_as_admin(self, client: AsyncClient, auth_headers: dict):
        """Test crear usuario como admin"""
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "newuser@test.com",
                "password": "securepass123",
                "role": "user"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["role"] == "user"
        assert "password" not in data
        assert "id" in data
    
    async def test_create_user_duplicate_email(self, client: AsyncClient, auth_headers: dict, admin_user):
        """Test crear usuario con email duplicado"""
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": admin_user.email,  # Ya existe
                "password": "password123",
                "role": "user"
            },
            headers=auth_headers
        )
        
        assert response.status_code in [400, 409]
    
    async def test_create_user_invalid_email(self, client: AsyncClient, auth_headers: dict):
        """Test crear usuario con email inválido"""
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "not-an-email",
                "password": "password123",
                "role": "user"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    async def test_create_user_missing_fields(self, client: AsyncClient, auth_headers: dict):
        """Test crear usuario sin campos requeridos"""
        response = await client.post(
            "/api/v1/users/",
            json={"email": "test@test.com"},
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    async def test_create_user_as_regular_user(self, client: AsyncClient, user_token: str):
        """Test crear usuario como usuario regular (debería fallar)"""
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "another@test.com",
                "password": "password123",
                "role": "user"
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 403


@pytest.mark.asyncio
class TestUserUpdate:
    """Tests para actualizar usuarios"""
    
    async def test_update_user_email(self, client: AsyncClient, auth_headers: dict, regular_user):
        """Test actualizar email de usuario"""
        response = await client.put(
            f"/api/v1/users/{regular_user.id}",
            json={
                "email": "updated@test.com",
                "role": regular_user.role
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "updated@test.com"
    
    async def test_update_user_password(self, client: AsyncClient, auth_headers: dict, regular_user):
        """Test actualizar contraseña de usuario"""
        response = await client.put(
            f"/api/v1/users/{regular_user.id}",
            json={
                "email": regular_user.email,
                "password": "newpassword456",
                "role": regular_user.role
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verificar que puede hacer login con nueva contraseña
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": regular_user.email,
                "password": "newpassword456"
            }
        )
        assert login_response.status_code == 200
    
    async def test_update_user_role(self, client: AsyncClient, auth_headers: dict, regular_user):
        """Test actualizar rol de usuario"""
        response = await client.put(
            f"/api/v1/users/{regular_user.id}",
            json={
                "email": regular_user.email,
                "role": "admin"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
    
    async def test_update_user_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test actualizar usuario inexistente"""
        response = await client.put(
            "/api/v1/users/99999",
            json={
                "email": "test@test.com",
                "role": "user"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestUserDelete:
    """Tests para eliminar usuarios"""
    
    async def test_delete_user_success(self, client: AsyncClient, auth_headers: dict, regular_user):
        """Test eliminar usuario exitosamente"""
        user_id = regular_user.id
        
        response = await client.delete(
            f"/api/v1/users/{user_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verificar que ya no existe
        get_response = await client.get(
            "/api/v1/users/",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        users = get_response.json()
        assert not any(u["id"] == user_id for u in users)
    
    async def test_delete_self(self, client: AsyncClient, admin_token: str, admin_user):
        """Test que admin no puede eliminarse a sí mismo"""
        response = await client.delete(
            f"/api/v1/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Debería prevenir auto-eliminación
        assert response.status_code in [400, 403]
    
    async def test_delete_user_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test eliminar usuario inexistente"""
        response = await client.delete(
            "/api/v1/users/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
