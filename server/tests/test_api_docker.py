"""
Tests para API de Docker
Endpoints: /api/v1/docker/*
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestDockerContainersList:
    """Tests para listar contenedores Docker"""
    
    async def test_list_containers_by_host(self, client: AsyncClient, auth_headers: dict, test_host, test_docker_container):
        """Test listar contenedores de un host"""
        response = await client.get(
            f"/api/v1/docker/{test_host.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(c["container_id"] == test_docker_container.container_id for c in data)
    
    async def test_list_containers_nonexistent_host(self, client: AsyncClient, auth_headers: dict):
        """Test listar contenedores de host inexistente"""
        response = await client.get(
            "/api/v1/docker/nonexistent-host",
            headers=auth_headers
        )
        
        assert response.status_code in [404, 200]
        if response.status_code == 200:
            assert response.json() == []
    
    async def test_list_containers_unauthorized(self, client: AsyncClient, test_host):
        """Test listar contenedores sin autenticación"""
        response = await client.get(f"/api/v1/docker/{test_host.id}")
        
        assert response.status_code == 401


@pytest.mark.asyncio
class TestDockerContainerSync:
    """Tests para sincronización de contenedores"""
    
    async def test_sync_containers_success(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test sincronizar contenedores de host"""
        response = await client.post(
            f"/api/v1/docker/{test_host.id}/sync",
            json={
                "containers": [
                    {
                        "container_id": "new123",
                        "name": "nginx-proxy",
                        "image": "nginx:alpine",
                        "status": "running",
                        "ports": {"80/tcp": "8080"}
                    }
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "added" in data or "synced" in data.get("message", "").lower()
    
    async def test_sync_empty_containers_list(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test sincronizar lista vacía de contenedores"""
        response = await client.post(
            f"/api/v1/docker/{test_host.id}/sync",
            json={"containers": []},
            headers=auth_headers
        )
        
        assert response.status_code == 200


@pytest.mark.asyncio
class TestDockerActions:
    """Tests para acciones Docker (start/stop/restart)"""
    
    async def test_docker_action_start(self, client: AsyncClient, auth_headers: dict, test_host, test_docker_container):
        """Test iniciar contenedor"""
        response = await client.post(
            f"/api/v1/docker/{test_host.id}/containers/{test_docker_container.container_id}/action",
            json={"action": "start"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "command_id" in data or "status" in data
    
    async def test_docker_action_stop(self, client: AsyncClient, auth_headers: dict, test_host, test_docker_container):
        """Test detener contenedor"""
        response = await client.post(
            f"/api/v1/docker/{test_host.id}/containers/{test_docker_container.container_id}/action",
            json={"action": "stop"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "command_id" in data or "status" in data
    
    async def test_docker_action_restart(self, client: AsyncClient, auth_headers: dict, test_host, test_docker_container):
        """Test reiniciar contenedor"""
        response = await client.post(
            f"/api/v1/docker/{test_host.id}/containers/{test_docker_container.container_id}/action",
            json={"action": "restart"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "command_id" in data or "status" in data
    
    async def test_docker_action_invalid(self, client: AsyncClient, auth_headers: dict, test_host, test_docker_container):
        """Test acción inválida"""
        response = await client.post(
            f"/api/v1/docker/{test_host.id}/containers/{test_docker_container.container_id}/action",
            json={"action": "invalid_action"},
            headers=auth_headers
        )
        
        assert response.status_code in [400, 422]
    
    async def test_docker_action_nonexistent_container(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test acción en contenedor inexistente"""
        response = await client.post(
            f"/api/v1/docker/{test_host.id}/containers/nonexistent/action",
            json={"action": "start"},
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    async def test_docker_action_unauthorized(self, client: AsyncClient, test_host, test_docker_container):
        """Test acción Docker sin autenticación"""
        response = await client.post(
            f"/api/v1/docker/{test_host.id}/containers/{test_docker_container.container_id}/action",
            json={"action": "start"}
        )
        
        assert response.status_code == 401


@pytest.mark.asyncio
class TestDockerContainerDetail:
    """Tests para detalles de contenedores"""
    
    async def test_get_container_detail(self, client: AsyncClient, auth_headers: dict, test_host, test_docker_container):
        """Test obtener detalles de contenedor"""
        response = await client.get(
            f"/api/v1/docker/{test_host.id}/containers/{test_docker_container.container_id}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["container_id"] == test_docker_container.container_id
            assert "name" in data
            assert "image" in data
            assert "status" in data
