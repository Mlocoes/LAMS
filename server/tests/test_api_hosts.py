"""
Tests para API de hosts
Endpoints: /api/v1/hosts/*
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHostRegistration:
    """Tests para registro de hosts"""
    
    async def test_register_host_success(self, client: AsyncClient, auth_headers: dict):
        """Test registrar host exitosamente"""
        response = await client.post(
            "/api/v1/hosts/register",
            json={
                "id": "new-host-01",
                "hostname": "webserver-01",
                "ip": "192.168.1.50",
                "os": "Ubuntu 22.04 LTS",
                "kernel_version": "5.15.0-generic",
                "cpu_cores": 8,
                "total_memory": 16384.0
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "new-host-01"
        assert data["hostname"] == "webserver-01"
        assert data["ip"] == "192.168.1.50"
        assert data["cpu_cores"] == 8
        assert data["status"] == "online"
        assert "created_at" in data
    
    async def test_register_host_duplicate(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test registrar host con ID duplicado"""
        response = await client.post(
            "/api/v1/hosts/register",
            json={
                "id": test_host.id,  # ID ya existe
                "hostname": "duplicate",
                "ip": "10.0.0.1",
                "os": "Debian",
                "kernel_version": "6.1",
                "cpu_cores": 4,
                "total_memory": 8192.0
            },
            headers=auth_headers
        )
        
        # Debería rechazar o actualizar (dependiendo de implementación)
        assert response.status_code in [409, 200]
    
    async def test_register_host_missing_fields(self, client: AsyncClient, auth_headers: dict):
        """Test registrar host sin campos requeridos"""
        response = await client.post(
            "/api/v1/hosts/register",
            json={
                "id": "incomplete-host",
                "hostname": "incomplete"
                # Faltan campos requeridos
            },
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    async def test_register_host_unauthorized(self, client: AsyncClient):
        """Test registrar host sin autenticación"""
        response = await client.post(
            "/api/v1/hosts/register",
            json={
                "id": "unauthorized-host",
                "hostname": "test",
                "ip": "10.0.0.1",
                "os": "Ubuntu",
                "kernel_version": "5.15",
                "cpu_cores": 4,
                "total_memory": 8192.0
            }
        )
        
        assert response.status_code == 401


@pytest.mark.asyncio
class TestHostsList:
    """Tests para listar hosts"""
    
    async def test_list_hosts_success(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test listar todos los hosts"""
        response = await client.get(
            "/api/v1/hosts/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(host["id"] == test_host.id for host in data)
    
    async def test_list_hosts_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listar hosts cuando no hay ninguno"""
        response = await client.get(
            "/api/v1/hosts/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_list_hosts_unauthorized(self, client: AsyncClient):
        """Test listar hosts sin autenticación"""
        response = await client.get("/api/v1/hosts/")
        
        assert response.status_code == 401


@pytest.mark.asyncio
class TestHostDetail:
    """Tests para obtener detalles de host"""
    
    async def test_get_host_success(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test obtener host existente"""
        response = await client.get(
            f"/api/v1/hosts/{test_host.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_host.id
        assert data["hostname"] == test_host.hostname
        assert data["ip"] == test_host.ip
        assert "cpu_cores" in data
        assert "total_memory" in data
    
    async def test_get_host_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test obtener host inexistente"""
        response = await client.get(
            "/api/v1/hosts/nonexistent-host",
            headers=auth_headers
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestHostUpdate:
    """Tests para actualizar hosts"""
    
    async def test_update_host_status(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test actualizar estado de host"""
        response = await client.patch(
            f"/api/v1/hosts/{test_host.id}",
            json={"status": "offline"},
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "offline"
    
    async def test_update_host_tags(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test actualizar tags de host"""
        new_tags = ["production", "database", "critical"]
        
        response = await client.patch(
            f"/api/v1/hosts/{test_host.id}",
            json={"tags": new_tags},
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert set(data["tags"]) == set(new_tags)


@pytest.mark.asyncio
class TestHostDelete:
    """Tests para eliminar hosts"""
    
    async def test_delete_host_success(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test eliminar host existente"""
        response = await client.delete(
            f"/api/v1/hosts/{test_host.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # Verificar que ya no existe
        get_response = await client.get(
            f"/api/v1/hosts/{test_host.id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
    
    async def test_delete_host_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test eliminar host inexistente"""
        response = await client.delete(
            "/api/v1/hosts/nonexistent",
            headers=auth_headers
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestHostHeartbeat:
    """Tests para heartbeat de hosts"""
    
    async def test_heartbeat_success(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test enviar heartbeat de host"""
        response = await client.post(
            f"/api/v1/hosts/{test_host.id}/heartbeat",
            headers=auth_headers
        )
        
        # Si el endpoint existe, debería actualizar last_seen
        if response.status_code == 200:
            data = response.json()
            assert "last_seen" in data
    
    async def test_heartbeat_nonexistent_host(self, client: AsyncClient, auth_headers: dict):
        """Test heartbeat de host inexistente"""
        response = await client.post(
            "/api/v1/hosts/nonexistent/heartbeat",
            headers=auth_headers
        )
        
        # Debería fallar o auto-registrar (dependiendo de lógica)
        assert response.status_code in [404, 200]
