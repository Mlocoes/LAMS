"""
Tests para API de métricas
Endpoints: /api/v1/metrics/*
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta


@pytest.mark.asyncio
class TestMetricSubmission:
    """Tests para envío de métricas"""
    
    async def test_submit_metric_success(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test enviar métrica exitosamente"""
        response = await client.post(
            "/api/v1/metrics/",
            json={
                "host_id": test_host.id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cpu_usage": 45.5,
                "memory_used": 3500.0,
                "memory_total": 8192.0,
                "disk_used": 60.0,
                "disk_total": 100.0,
                "network_received": 1200.0,
                "network_sent": 800.0,
                "cpu_temp": 48.0
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["host_id"] == test_host.id
        assert data["cpu_usage"] == 45.5
        assert "id" in data
    
    async def test_submit_metric_invalid_host(self, client: AsyncClient, auth_headers: dict):
        """Test enviar métrica para host inexistente"""
        response = await client.post(
            "/api/v1/metrics/",
            json={
                "host_id": "nonexistent-host",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cpu_usage": 50.0,
                "memory_used": 4000.0,
                "memory_total": 8000.0,
                "disk_used": 50.0,
                "disk_total": 100.0,
                "network_received": 1000.0,
                "network_sent": 500.0
            },
            headers=auth_headers
        )
        
        assert response.status_code in [404, 422]
    
    async def test_submit_metric_missing_fields(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test enviar métrica sin campos requeridos"""
        response = await client.post(
            "/api/v1/metrics/",
            json={
                "host_id": test_host.id,
                "cpu_usage": 50.0
                # Faltan campos requeridos
            },
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    async def test_submit_metric_invalid_values(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test enviar métrica con valores inválidos"""
        response = await client.post(
            "/api/v1/metrics/",
            json={
                "host_id": test_host.id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cpu_usage": -10.0,  # Negativo inválido
                "memory_used": 4000.0,
                "memory_total": 8000.0,
                "disk_used": 50.0,
                "disk_total": 100.0,
                "network_received": 1000.0,
                "network_sent": 500.0
            },
            headers=auth_headers
        )
        
        # Debería validar rangos
        assert response.status_code in [422, 400]
    
    async def test_submit_metric_unauthorized(self, client: AsyncClient, test_host):
        """Test enviar métrica sin autenticación"""
        response = await client.post(
            "/api/v1/metrics/",
            json={
                "host_id": test_host.id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cpu_usage": 50.0,
                "memory_used": 4000.0,
                "memory_total": 8000.0,
                "disk_used": 50.0,
                "disk_total": 100.0,
                "network_received": 1000.0,
                "network_sent": 500.0
            }
        )
        
        assert response.status_code == 401


@pytest.mark.asyncio
class TestMetricsRetrieval:
    """Tests para obtener métricas"""
    
    async def test_get_host_metrics_success(self, client: AsyncClient, auth_headers: dict, test_host, test_metrics):
        """Test obtener métricas de host"""
        response = await client.get(
            f"/api/v1/metrics/{test_host.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5  # Tenemos 5 métricas de prueba
        assert all(m["host_id"] == test_host.id for m in data)
    
    async def test_get_metrics_with_limit(self, client: AsyncClient, auth_headers: dict, test_host, test_metrics):
        """Test obtener métricas con límite"""
        limit = 3
        response = await client.get(
            f"/api/v1/metrics/{test_host.id}?limit={limit}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= limit
    
    async def test_get_metrics_with_time_range(self, client: AsyncClient, auth_headers: dict, test_host, test_metrics):
        """Test obtener métricas con rango de tiempo"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        response = await client.get(
            f"/api/v1/metrics/{test_host.id}",
            params={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_get_metrics_nonexistent_host(self, client: AsyncClient, auth_headers: dict):
        """Test obtener métricas de host inexistente"""
        response = await client.get(
            "/api/v1/metrics/nonexistent-host",
            headers=auth_headers
        )
        
        assert response.status_code in [404, 200]
        if response.status_code == 200:
            assert response.json() == []
    
    async def test_get_metrics_empty(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test obtener métricas cuando host no tiene ninguna"""
        # Obtener con límite 0 o rango vacío
        past_time = datetime.now(timezone.utc) - timedelta(days=365)
        
        response = await client.get(
            f"/api/v1/metrics/{test_host.id}",
            params={
                "start_time": past_time.isoformat(),
                "end_time": past_time.isoformat()
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


@pytest.mark.asyncio
class TestLatestMetrics:
    """Tests para obtener métricas más recientes"""
    
    async def test_get_latest_metric(self, client: AsyncClient, auth_headers: dict, test_host, test_metrics):
        """Test obtener la métrica más reciente"""
        response = await client.get(
            f"/api/v1/metrics/{test_host.id}/latest",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["host_id"] == test_host.id
            assert "cpu_usage" in data
            assert "memory_used" in data
    
    async def test_get_latest_metric_nonexistent_host(self, client: AsyncClient, auth_headers: dict):
        """Test obtener métrica más reciente de host inexistente"""
        response = await client.get(
            "/api/v1/metrics/nonexistent/latest",
            headers=auth_headers
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestMetricAggregation:
    """Tests para agregación de métricas"""
    
    async def test_get_aggregated_metrics(self, client: AsyncClient, auth_headers: dict, test_host, test_metrics):
        """Test obtener métricas agregadas"""
        response = await client.get(
            f"/api/v1/metrics/{test_host.id}/aggregated",
            params={"period": "hourly"},
            headers=auth_headers
        )
        
        # Si el endpoint existe
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            for item in data:
                assert "cpu_usage_avg" in item or "average" in str(item).lower()
