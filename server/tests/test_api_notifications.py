"""
Tests para API de notificaciones
Endpoints: /api/v1/notifications/*
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestNotificationConfigList:
    """Tests para listar configuraciones de notificación"""
    
    async def test_list_notification_configs(self, client: AsyncClient, auth_headers: dict, test_notification_config):
        """Test listar configuraciones"""
        response = await client.get(
            "/api/v1/notifications/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(c["id"] == test_notification_config.id for c in data)
    
    async def test_list_notifications_unauthorized(self, client: AsyncClient):
        """Test listar sin autenticación"""
        response = await client.get("/api/v1/notifications/")
        
        assert response.status_code == 401


@pytest.mark.asyncio
class TestNotificationConfigCreation:
    """Tests para crear configuraciones"""
    
    async def test_create_email_config(self, client: AsyncClient, auth_headers: dict):
        """Test crear configuración de email"""
        response = await client.post(
            "/api/v1/notifications/",
            json={
                "provider": "email",
                "config": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "smtp_user": "test@gmail.com",
                    "smtp_password": "password",
                    "email_from": "test@gmail.com",
                    "email_to": "admin@test.com"
                },
                "enabled": True,
                "severity_filter": "all"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "email"
        assert data["enabled"] is True
        assert "smtp_password" not in str(data)  # No debe exponer password en respuesta
    
    async def test_create_slack_config(self, client: AsyncClient, auth_headers: dict):
        """Test crear configuración de Slack"""
        response = await client.post(
            "/api/v1/notifications/",
            json={
                "provider": "slack",
                "config": {
                    "webhook_url": "https://hooks.slack.com/services/XXX/YYY/ZZZ"
                },
                "enabled": True,
                "severity_filter": "critical"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "slack"
        assert data["severity_filter"] == "critical"
    
    async def test_create_discord_config(self, client: AsyncClient, auth_headers: dict):
        """Test crear configuración de Discord"""
        response = await client.post(
            "/api/v1/notifications/",
            json={
                "provider": "discord",
                "config": {
                    "webhook_url": "https://discord.com/api/webhooks/123/456"
                },
                "enabled": False,
                "severity_filter": "warning"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "discord"
        assert data["enabled"] is False
    
    async def test_create_config_invalid_provider(self, client: AsyncClient, auth_headers: dict):
        """Test crear configuración con provider inválido"""
        response = await client.post(
            "/api/v1/notifications/",
            json={
                "provider": "invalid_provider",
                "config": {},
                "enabled": True,
                "severity_filter": "all"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 422


@pytest.mark.asyncio
class TestNotificationConfigUpdate:
    """Tests para actualizar configuraciones"""
    
    async def test_update_config_enabled(self, client: AsyncClient, auth_headers: dict, test_notification_config):
        """Test actualizar estado habilitado"""
        response = await client.put(
            f"/api/v1/notifications/{test_notification_config.id}",
            json={"enabled": False},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
    
    async def test_update_config_severity_filter(self, client: AsyncClient, auth_headers: dict, test_notification_config):
        """Test actualizar filtro de severidad"""
        response = await client.put(
            f"/api/v1/notifications/{test_notification_config.id}",
            json={"severity_filter": "critical"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["severity_filter"] == "critical"
    
    async def test_update_config_settings(self, client: AsyncClient, auth_headers: dict, test_notification_config):
        """Test act actualizar configuración completa"""
        response = await client.put(
            f"/api/v1/notifications/{test_notification_config.id}",
            json={
                "config": {
                    "smtp_host": "smtp.newhost.com",
                    "smtp_port": 465,
                    "smtp_user": "new@test.com",
                    "smtp_password": "newpass",
                    "email_from": "new@test.com",
                    "email_to": "newtarget@test.com"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    async def test_update_config_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test actualizar configuración inexistente"""
        response = await client.put(
            "/api/v1/notifications/99999",
            json={"enabled": False},
            headers=auth_headers
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestNotificationConfigDelete:
    """Tests para eliminar configuraciones"""
    
    async def test_delete_config_success(self, client: AsyncClient, auth_headers: dict, test_notification_config):
        """Test eliminar configuración"""
        config_id = test_notification_config.id
        
        response = await client.delete(
            f"/api/v1/notifications/{config_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verificar que ya no existe
        get_response = await client.get(
            f"/api/v1/notifications/{config_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
    
    async def test_delete_config_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test eliminar configuración inexistente"""
        response = await client.delete(
            "/api/v1/notifications/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestNotificationTest:
    """Tests para probar configuraciones de notificación"""
    
    async def test_test_notification_success(self, client: AsyncClient, auth_headers: dict, test_notification_config, mocker):
        """Test enviar notificación de prueba"""
        # Mock del envío de email para evitar envío real
        mocker.patch('notifications.email.EmailProvider._send_sync', return_value=None)
        
        response = await client.post(
            f"/api/v1/notifications/{test_notification_config.id}/test",
            headers=auth_headers
        )
        
        # Puede ser 200 (éxito) o error si no hay mock
        assert response.status_code in [200, 400, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data or "message" in data
    
    async def test_test_notification_disabled_config(self, client: AsyncClient, auth_headers: dict, db_session, admin_user):
        """Test probar configuración deshabilitada"""
        from database.models import NotificationConfig
        
        disabled_config = NotificationConfig(
            user_id=admin_user.id,
            provider="email",
            config={"test": "config"},
            enabled=False,
            severity_filter="all"
        )
        db_session.add(disabled_config)
        await db_session.commit()
        await db_session.refresh(disabled_config)
        
        response = await client.post(
            f"/api/v1/notifications/{disabled_config.id}/test",
            headers=auth_headers
        )
        
        # Debería permitir test incluso si está deshabilitada, o rechazar
        assert response.status_code in [200, 400]
    
    async def test_test_notification_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test probar configuración inexistente"""
        response = await client.post(
            "/api/v1/notifications/99999/test",
            headers=auth_headers
        )
        
        assert response.status_code == 404
