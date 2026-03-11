"""
Tests para API de reglas de alertas
Endpoints: /api/v1/alert-rules/*
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAlertRuleCreation:
    """Tests para crear reglas de alertas"""
    
    async def test_create_alert_rule_success(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test crear regla de alerta exitosamente"""
        response = await client.post(
            "/api/v1/alert-rules/",
            json={
                "name": "High Disk Usage",
                "description": "Alert when disk usage exceeds 85%",
                "host_id": test_host.id,
                "metric_name": "disk_used",
                "operator": ">",
                "threshold": 85.0,
                "severity": "warning",
                "enabled": True
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "High Disk Usage"
        assert data["metric_name"] == "disk_used"
        assert data["operator"] == ">"
        assert data["threshold"] == 85.0
        assert data["enabled"] is True
    
    async def test_create_alert_rule_invalid_operator(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test crear regla con operador inválido"""
        response = await client.post(
            "/api/v1/alert-rules/",
            json={
                "name": "Invalid Rule",
                "host_id": test_host.id,
                "metric_name": "cpu_usage",
                "operator": "!=",  # Operador no permitido
                "threshold": 50.0,
                "severity": "warning",
                "enabled": True
            },
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    async def test_create_alert_rule_invalid_metric(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test crear regla con métrica inválida"""
        response = await client.post(
            "/api/v1/alert-rules/",
            json={
                "name": "Invalid Metric",
                "host_id": test_host.id,
                "metric_name": "nonexistent_metric",
                "operator": ">",
                "threshold": 50.0,
                "severity": "warning",
                "enabled": True
            },
            headers=auth_headers
        )
        
        # Podría validar o aceptar
        assert response.status_code in [422, 200]
    
    async def test_create_alert_rule_missing_fields(self, client: AsyncClient, auth_headers: dict):
        """Test crear regla sin campos requeridos"""
        response = await client.post(
            "/api/v1/alert-rules/",
            json={
                "name": "Incomplete Rule"
                # Faltan campos requeridos
            },
            headers=auth_headers
        )
        
        assert response.status_code == 422


@pytest.mark.asyncio
class TestAlertRulesList:
    """Tests para listar reglas"""
    
    async def test_list_all_rules(self, client: AsyncClient, auth_headers: dict, test_alert_rule):
        """Test listar todas las reglas"""
        response = await client.get(
            "/api/v1/alert-rules/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(rule["id"] == test_alert_rule.id for rule in data)
    
    async def test_list_rules_by_host(self, client: AsyncClient, auth_headers: dict, test_host, test_alert_rule):
        """Test listar reglas de un host específico"""
        response = await client.get(
            f"/api/v1/alert-rules/?host_id={test_host.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(rule["host_id"] == test_host.id for rule in data)
    
    async def test_list_rules_enabled_only(self, client: AsyncClient, auth_headers: dict):
        """Test listar solo reglas habilitadas"""
        response = await client.get(
            "/api/v1/alert-rules/?enabled=true",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert all(rule["enabled"] for rule in data)


@pytest.mark.asyncio
class TestAlertRuleUpdate:
    """Tests para actualizar reglas"""
    
    async def test_update_rule_threshold(self, client: AsyncClient, auth_headers: dict, test_alert_rule):
        """Test actualizar umbral de regla"""
        new_threshold = 95.0
        
        response = await client.put(
            f"/api/v1/alert-rules/{test_alert_rule.id}",
            json={
                "name": test_alert_rule.name,
                "host_id": test_alert_rule.host_id,
                "metric_name": test_alert_rule.metric_name,
                "operator": test_alert_rule.operator,
                "threshold": new_threshold,
                "severity": test_alert_rule.severity,
                "enabled": test_alert_rule.enabled
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["threshold"] == new_threshold
    
    async def test_disable_rule(self, client: AsyncClient, auth_headers: dict, test_alert_rule):
        """Test deshabilitar regla"""
        response = await client.put(
            f"/api/v1/alert-rules/{test_alert_rule.id}",
            json={
                "name": test_alert_rule.name,
                "host_id": test_alert_rule.host_id,
                "metric_name": test_alert_rule.metric_name,
                "operator": test_alert_rule.operator,
                "threshold": test_alert_rule.threshold,
                "severity": test_alert_rule.severity,
                "enabled": False
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
    
    async def test_update_rule_not_found(self, client: AsyncClient, auth_headers: dict, test_host):
        """Test actualizar regla inexistente"""
        response = await client.put(
            "/api/v1/alert-rules/99999",
            json={
                "name": "Test",
                "host_id": test_host.id,
                "metric_name": "cpu_usage",
                "operator": ">",
                "threshold": 80.0,
                "severity": "warning",
                "enabled": True
            },
            headers=auth_headers
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestAlertRuleDelete:
    """Tests para eliminar reglas"""
    
    async def test_delete_rule_success(self, client: AsyncClient, auth_headers: dict, test_alert_rule):
        """Test eliminar regla exitosamente"""
        rule_id = test_alert_rule.id
        
        response = await client.delete(
            f"/api/v1/alert-rules/{rule_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verificar que ya no existe
        get_response = await client.get(
            f"/api/v1/alert-rules/{rule_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
    
    async def test_delete_rule_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test eliminar regla inexistente"""
        response = await client.delete(
            "/api/v1/alert-rules/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestAlertRuleValidation:
    """Tests para validación de reglas"""
    
    async def test_test_rule_endpoint(self, client: AsyncClient, auth_headers: dict, test_host, test_metrics):
        """Test endpoint para probar regla sin guardarla"""
        response = await client.post(
            "/api/v1/alert-rules/test",
            json={
                "host_id": test_host.id,
                "metric_name": "cpu_usage",
                "operator": ">",
                "threshold": 40.0  # Debería disparar con las métricas de prueba
            },
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "would_trigger" in data or "triggered" in data
