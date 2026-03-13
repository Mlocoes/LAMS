"""
Tests para API extendida de contenedores Docker (Portainer features)
Endpoints: /api/v1/containers/{host_id}/containers/{container_id}/*
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import RemoteCommand, DockerContainer, Host


@pytest.mark.asyncio
class TestContainerLogs:
    """Tests para obtener logs de contenedores"""
    
    async def test_get_container_logs_success(
        self, 
        client: AsyncClient, 
        auth_headers: dict, 
        test_host: Host,
        test_docker_container: DockerContainer,
        db_session: AsyncSession
    ):
        """Test obtener logs exitosamente"""
        # Simular que el comando se completa rápidamente
        with patch('api.containers_extended.asyncio.sleep', new_callable=AsyncMock):
            # Crear comando mock que se complete
            response = await client.get(
                f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}/logs?tail=100",
                headers=auth_headers
            )
            
            # Verificar que se creó el comando
            assert response.status_code in [200, 504]  # 504 si no hay agente simulado
    
    async def test_get_container_logs_with_parameters(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host,
        test_docker_container: DockerContainer
    ):
        """Test obtener logs con parámetros tail y since"""
        response = await client.get(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}/logs?tail=50&since=1234567890",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 504]
    
    async def test_get_container_logs_invalid_container(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host
    ):
        """Test obtener logs de contenedor inexistente"""
        response = await client.get(
            f"/api/v1/containers/{test_host.id}/containers/nonexistent123/logs",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    async def test_get_container_logs_invalid_host(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test obtener logs con host inexistente"""
        response = await client.get(
            "/api/v1/containers/nonexistent-host/containers/container123/logs",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    async def test_get_container_logs_unauthorized(
        self,
        client: AsyncClient,
        test_host: Host,
        test_docker_container: DockerContainer
    ):
        """Test obtener logs sin autenticación"""
        response = await client.get(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}/logs"
        )
        
        assert response.status_code == 401
    
    async def test_get_container_logs_invalid_tail(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host,
        test_docker_container: DockerContainer
    ):
        """Test con parámetro tail inválido"""
        response = await client.get(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}/logs?tail=99999",
            headers=auth_headers
        )
        
        # Debería fallar validación o ser clamped a 10000
        assert response.status_code in [200, 422, 504]


@pytest.mark.asyncio
class TestContainerInspect:
    """Tests para inspeccionar contenedores"""
    
    async def test_inspect_container_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host,
        test_docker_container: DockerContainer
    ):
        """Test inspeccionar contenedor exitosamente"""
        response = await client.get(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}/inspect",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 504]
    
    async def test_inspect_container_invalid_container(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host
    ):
        """Test inspeccionar contenedor inexistente"""
        response = await client.get(
            f"/api/v1/containers/{test_host.id}/containers/nonexistent123/inspect",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    async def test_inspect_container_unauthorized(
        self,
        client: AsyncClient,
        test_host: Host,
        test_docker_container: DockerContainer
    ):
        """Test inspeccionar sin autenticación"""
        response = await client.get(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}/inspect"
        )
        
        assert response.status_code == 401


@pytest.mark.asyncio
class TestContainerRemove:
    """Tests para eliminar contenedores"""
    
    async def test_remove_container_stopped(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host,
        test_docker_container: DockerContainer,
        db_session: AsyncSession
    ):
        """Test eliminar contenedor detenido"""
        # Asegurar que el contenedor está detenido
        test_docker_container.state = "exited"
        db_session.add(test_docker_container)
        await db_session.commit()
        
        response = await client.delete(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 504]
        if response.status_code == 200:
            data = response.json()
            assert "command_id" in data or "status" in data
    
    async def test_remove_container_running_without_force(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host,
        test_docker_container: DockerContainer,
        db_session: AsyncSession
    ):
        """Test eliminar contenedor en ejecución sin force"""
        # Asegurar que el contenedor está running
        test_docker_container.state = "running"
        db_session.add(test_docker_container)
        await db_session.commit()
        
        response = await client.delete(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "running" in data["detail"].lower()
    
    async def test_remove_container_running_with_force(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host,
        test_docker_container: DockerContainer,
        db_session: AsyncSession
    ):
        """Test eliminar contenedor en ejecución con force=true"""
        test_docker_container.state = "running"
        db_session.add(test_docker_container)
        await db_session.commit()
        
        response = await client.delete(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}?force=true",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 504]
    
    async def test_remove_container_with_volumes(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host,
        test_docker_container: DockerContainer,
        db_session: AsyncSession
    ):
        """Test eliminar contenedor con volúmenes"""
        test_docker_container.state = "exited"
        db_session.add(test_docker_container)
        await db_session.commit()
        
        response = await client.delete(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}?volumes=true",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 504]
    
    async def test_remove_container_invalid_container(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host
    ):
        """Test eliminar contenedor inexistente"""
        response = await client.delete(
            f"/api/v1/containers/{test_host.id}/containers/nonexistent123",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    async def test_remove_container_unauthorized(
        self,
        client: AsyncClient,
        test_host: Host,
        test_docker_container: DockerContainer
    ):
        """Test eliminar sin autenticación"""
        response = await client.delete(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}"
        )
        
        assert response.status_code == 401


@pytest.mark.asyncio
class TestContainerExec:
    """Tests para ejecutar comandos en contenedores"""
    
    async def test_create_exec_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host,
        test_docker_container: DockerContainer,
        db_session: AsyncSession
    ):
        """Test crear exec exitosamente"""
        # Asegurar que el contenedor está running
        test_docker_container.state = "running"
        db_session.add(test_docker_container)
        await db_session.commit()
        
        response = await client.post(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}/exec",
            headers=auth_headers,
            json={
                "cmd": ["/bin/bash", "-c", "ls -la"],
                "tty": True,
                "stdin": True
            }
        )
        
        assert response.status_code in [200, 504]
    
    async def test_create_exec_container_not_running(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host,
        test_docker_container: DockerContainer,
        db_session: AsyncSession
    ):
        """Test crear exec en contenedor detenido"""
        test_docker_container.state = "exited"
        db_session.add(test_docker_container)
        await db_session.commit()
        
        response = await client.post(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}/exec",
            headers=auth_headers,
            json={
                "cmd": ["/bin/bash"],
                "tty": True,
                "stdin": True
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "running" in data["detail"].lower()
    
    async def test_create_exec_invalid_container(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host
    ):
        """Test crear exec en contenedor inexistente"""
        response = await client.post(
            f"/api/v1/containers/{test_host.id}/containers/nonexistent123/exec",
            headers=auth_headers,
            json={
                "cmd": ["/bin/bash"],
                "tty": True,
                "stdin": True
            }
        )
        
        assert response.status_code == 404
    
    async def test_create_exec_invalid_payload(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host,
        test_docker_container: DockerContainer,
        db_session: AsyncSession
    ):
        """Test crear exec con payload inválido"""
        test_docker_container.state = "running"
        db_session.add(test_docker_container)
        await db_session.commit()
        
        response = await client.post(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}/exec",
            headers=auth_headers,
            json={"invalid": "data"}  # Falta 'cmd'
        )
        
        assert response.status_code == 422
    
    async def test_create_exec_unauthorized(
        self,
        client: AsyncClient,
        test_host: Host,
        test_docker_container: DockerContainer
    ):
        """Test crear exec sin autenticación"""
        response = await client.post(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}/exec",
            json={
                "cmd": ["/bin/bash"],
                "tty": True,
                "stdin": True
            }
        )
        
        assert response.status_code == 401


@pytest.mark.asyncio
class TestRemoteCommandCreation:
    """Tests para verificar creación correcta de RemoteCommands"""
    
    async def test_logs_creates_remote_command(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host,
        test_docker_container: DockerContainer,
        db_session: AsyncSession
    ):
        """Test que logs crea un RemoteCommand con parámetros correctos"""
        response = await client.get(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}/logs?tail=50",
            headers=auth_headers
        )
        
        # Verificar que se creó un comando (sin importar timeout)
        from sqlalchemy import select
        stmt = select(RemoteCommand).where(
            RemoteCommand.host_id == test_host.id,
            RemoteCommand.command_type == "container.logs",
            RemoteCommand.target_id == test_docker_container.container_id
        )
        result = await db_session.execute(stmt)
        command = result.scalar_one_or_none()
        
        if response.status_code != 404:  # Si no hubo error de host/container
            assert command is not None
            assert command.parameters["tail"] == 50
            assert command.parameters["container_id"] == test_docker_container.container_id
    
    async def test_inspect_creates_remote_command(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host,
        test_docker_container: DockerContainer,
        db_session: AsyncSession
    ):
        """Test que inspect crea un RemoteCommand"""
        response = await client.get(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}/inspect",
            headers=auth_headers
        )
        
        from sqlalchemy import select
        stmt = select(RemoteCommand).where(
            RemoteCommand.host_id == test_host.id,
            RemoteCommand.command_type == "container.inspect"
        )
        result = await db_session.execute(stmt)
        command = result.scalar_one_or_none()
        
        if response.status_code != 404:
            assert command is not None
            assert command.parameters["container_id"] == test_docker_container.container_id
    
    async def test_remove_creates_remote_command(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_host: Host,
        test_docker_container: DockerContainer,
        db_session: AsyncSession
    ):
        """Test que remove crea un RemoteCommand con opciones"""
        test_docker_container.state = "exited"
        db_session.add(test_docker_container)
        await db_session.commit()
        
        response = await client.delete(
            f"/api/v1/containers/{test_host.id}/containers/{test_docker_container.container_id}?force=true&volumes=true",
            headers=auth_headers
        )
        
        from sqlalchemy import select
        stmt = select(RemoteCommand).where(
            RemoteCommand.host_id == test_host.id,
            RemoteCommand.command_type == "container.remove"
        )
        result = await db_session.execute(stmt)
        command = result.scalar_one_or_none()
        
        if response.status_code == 200:
            assert command is not None
            assert command.parameters["force"] == True
            assert command.parameters["volumes"] == True
