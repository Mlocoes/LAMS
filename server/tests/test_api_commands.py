"""
Tests para API de comandos remotos
Endpoints: /api/v1/commands/*
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone


@pytest.mark.asyncio
class TestCommandCreation:
    """Tests para crear comandos remotos"""
    
    async def test_create_docker_command_success(self, client: AsyncClient, auth_headers: dict, test_host, test_docker_container):
        """Test crear comando Docker remoto"""
        response = await client.post(
            "/api/v1/commands/",
            json={
                "host_id": test_host.id,
                "command_type": "docker_start",
                "target_id": test_docker_container.container_id
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["host_id"] == test_host.id
        assert data["command_type"] == "docker_start"
        assert data["status"] == "pending"
        assert "id" in data
        assert "created_at" in data
    
    async def test_create_command_invalid_host(self, client: AsyncClient, auth_headers: dict):
        """Test crear comando para host inexistente"""
        response = await client.post(
            "/api/v1/commands/",
            json={
                "host_id": "nonexistent-host",
                "command_type": "docker_start",
                "target_id": "container123"
            },
            headers=auth_headers
        )
        
        assert response.status_code in [404, 422]
    
    async def test_create_command_invalid_type(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test crear comando con tipo inválido"""
        response = await client.post(
            "/api/v1/commands/",
            json={
                "host_id": test_host.id,
                "command_type": "invalid_command",
                "target_id": "target123"
            },
            headers=auth_headers
        )
        
        assert response.status_code in [400, 422]
    
    async def test_create_command_unauthorized(self, client: AsyncClient, test_host):
        """Test crear comando sin autenticación"""
        response = await client.post(
            "/api/v1/commands/",
            json={
                "host_id": test_host.id,
                "command_type": "docker_start",
                "target_id": "container123"
            }
        )
        
        assert response.status_code == 401


@pytest.mark.asyncio
class TestCommandPolling:
    """Tests para polling de comandos por agente"""
    
    async def test_get_pending_commands(self, client: AsyncClient, test_host, db_session):
        """Test obtener comandos pendientes para agente"""
        # Crear comando pendiente
        from database.models import RemoteCommand
        command = RemoteCommand(
            host_id=test_host.id,
            command_type="docker_restart",
            target_id="container123",
            status="pending"
        )
        db_session.add(command)
        await db_session.commit()
        await db_session.refresh(command)
        
        # Agente solicita comandos (sin auth - endpoint público para agentes)
        response = await client.get(f"/api/v1/commands/{test_host.id}/pending")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Verificar que comando cambió a "executing"
        await db_session.refresh(command)
        assert command.status == "executing"
    
    async def test_get_pending_commands_empty(self, client: AsyncClient, test_host):
        """Test obtener comandos cuando no hay pendientes"""
        response = await client.get(f"/api/v1/commands/{test_host.id}/pending")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
class TestCommandResult:
    """Tests para reportar resultados de comandos"""
    
    async def test_update_command_result_success(self, client: AsyncClient, test_host, db_session):
        """Test reportar resultado exitoso de comando"""
        from database.models import RemoteCommand
        
        # Crear comando en ejecución
        command = RemoteCommand(
            host_id=test_host.id,
            command_type="docker_start",
            target_id="container123",
            status="executing"
        )
        db_session.add(command)
        await db_session.commit()
        await db_session.refresh(command)
        
        # Agente reporta resultado
        response = await client.post(
            f"/api/v1/commands/{command.id}/result",
            json={
                "status": "completed",
                "result": "Container started successfully"
            }
        )
        
        assert response.status_code == 200
        
        # Verificar que comando se actualizó
        await db_session.refresh(command)
        assert command.status == "completed"
        assert command.result == "Container started successfully"
        assert command.executed_at is not None
    
    async def test_update_command_result_failed(self, client: AsyncClient, test_host, db_session):
        """Test reportar resultado fallido de comando"""
        from database.models import RemoteCommand
        
        command = RemoteCommand(
            host_id=test_host.id,
            command_type="docker_stop",
            target_id="container123",
            status="executing"
        )
        db_session.add(command)
        await db_session.commit()
        await db_session.refresh(command)
        
        response = await client.post(
            f"/api/v1/commands/{command.id}/result",
            json={
                "status": "failed",
                "result": "Container not found"
            }
        )
        
        assert response.status_code == 200
        
        await db_session.refresh(command)
        assert command.status == "failed"
        assert "not found" in command.result.lower()
    
    async def test_update_command_result_not_found(self, client: AsyncClient):
        """Test reportar resultado de comando inexistente"""
        response = await client.post(
            "/api/v1/commands/99999/result",
            json={
                "status": "completed",
                "result": "success"
            }
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestCommandStatus:
    """Tests para verificar estado de comandos"""
    
    async def test_get_command_status(self, client: AsyncClient, auth_headers: dict, test_host, db_session):
        """Test obtener estado de comando"""
        from database.models import RemoteCommand
        
        command = RemoteCommand(
            host_id=test_host.id,
            command_type="docker_restart",
            target_id="container123",
            status="pending"
        )
        db_session.add(command)
        await db_session.commit()
        await db_session.refresh(command)
        
        response = await client.get(
            f"/api/v1/commands/{command.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == command.id
        assert data["status"] == "pending"
        assert "host_id" in data
        assert "command_type" in data
    
    async def test_get_command_status_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test obtener estado de comando inexistente"""
        response = await client.get(
            "/api/v1/commands/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestCommandHistory:
    """Tests para historial de comandos"""
    
    async def test_get_host_commands(self, client: AsyncClient, auth_headers: dict, test_host, db_session):
        """Test obtener historial de comandos de host"""
        from database.models import RemoteCommand
        
        # Crear varios comandos
        for i in range(3):
            command = RemoteCommand(
                host_id=test_host.id,
                command_type="docker_start",
                target_id=f"container{i}",
                status="completed"
            )
            db_session.add(command)
        
        await db_session.commit()
        
        response = await client.get(
            f"/api/v1/commands/host/{test_host.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3
    
    async def test_get_host_commands_with_limit(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test obtener historial con límite"""
        response = await client.get(
            f"/api/v1/commands/host/{test_host.id}?limit=5",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5
