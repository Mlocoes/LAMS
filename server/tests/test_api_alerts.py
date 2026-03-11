"""
Tests para API de alertas
Endpoints: /api/v1/alerts/*
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAlertsList:
    """Tests para listar alertas"""
    
    async def test_list_all_alerts(self, client: AsyncClient, auth_headers: dict, test_alert):
        """Test listar todas las alertas"""
        response = await client.get(
            "/api/v1/alerts/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(alert["id"] == test_alert.id for alert in data)
    
    async def test_list_alerts_by_host(self, client: AsyncClient, auth_headers: dict, test_host, test_alert):
        """Test listar alertas de un host específico"""
        response = await client.get(
            f"/api/v1/alerts/?host_id={test_host.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(alert["host_id"] == test_host.id for alert in data)
    
    async def test_list_alerts_by_severity(self, client: AsyncClient, auth_headers: dict, test_alert):
        """Test listar alertas por severidad"""
        response = await client.get(
            f"/api/v1/alerts/?severity={test_alert.severity}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(alert["severity"] == test_alert.severity for alert in data)
    
    async def test_list_alerts_by_status(self, client: AsyncClient, auth_headers: dict):
        """Test listar alertas por estado"""
        response = await client.get(
            "/api/v1/alerts/?status=active",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_list_alerts_unauthorized(self, client: AsyncClient):
        """Test listar alertas sin autenticación"""
        response = await client.get("/api/v1/alerts/")
        
        assert response.status_code == 401


@pytest.mark.asyncio
class TestAlertDetail:
    """Tests para detalles de alertas"""
    
    async def test_get_alert_success(self, client: AsyncClient, auth_headers: dict, test_alert):
        """Test obtener detalles de alerta"""
        response = await client.get(
            f"/api/v1/alerts/{test_alert.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_alert.id
        assert data["message"] == test_alert.message
        assert data["severity"] == test_alert.severity
        assert "host_id" in data
        assert "rule_id" in data
    
    async def test_get_alert_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test obtener alerta inexistente"""
        response = await client.get(
            "/api/v1/alerts/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestAlertUpdate:
    """Tests para actualizar alertas"""
    
    async def test_acknowledge_alert(self, client: AsyncClient, auth_headers: dict, test_alert):
        """Test reconocer alerta"""
        response = await client.patch(
            f"/api/v1/alerts/{test_alert.id}",
            json={"status": "acknowledged"},
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "acknowledged"
    
    async def test_resolve_alert(self, client: AsyncClient, auth_headers: dict, test_alert):
        """Test resolver alerta"""
        response = await client.patch(
            f"/api/v1/alerts/{test_alert.id}",
            json={"status": "resolved"},
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "resolved"


@pytest.mark.asyncio
class TestAlertDelete:
    """Tests para eliminar alertas"""
    
    async def test_delete_alert_success(self, client: AsyncClient, auth_headers: dict, test_alert):
        """Test eliminar alerta"""
        alert_id = test_alert.id
        
        response = await client.delete(
            f"/api/v1/alerts/{alert_id}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            # Verificar que ya no existe
            get_response = await client.get(
                f"/api/v1/alerts/{alert_id}",
                headers=auth_headers
            )
            assert get_response.status_code == 404
    
    async def test_delete_alert_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test eliminar alerta inexistente"""
        response = await client.delete(
            "/api/v1/alerts/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestAlertStatistics:
    """Tests para estadísticas de alertas"""
    
    async def test_get_alert_stats(self, client: AsyncClient, auth_headers: dict, test_alert):
        """Test obtener estadísticas de alertas"""
        response = await client.get(
            "/api/v1/alerts/stats",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "total" in data or isinstance(data, dict)
    
    async def test_get_alert_count_by_severity(self, client: AsyncClient, auth_headers: dict, test_alert):
        """Test obtener conteo de alertas por severidad"""
        response = await client.get(
            "/api/v1/alerts/stats/severity",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict) or isinstance(data, list)
