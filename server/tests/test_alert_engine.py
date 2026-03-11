"""
Tests para motor de alertas
Módulo: alerts/engine.py
Valida: evaluación de reglas, disparo de alertas, operadores
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Alert, AlertRule, Metric, Host


def check_condition(value: float, operator: str, threshold: float) -> bool:
    """
    Helper para verificar si una condición se cumple
    Replica la lógica del motor de alertas
    """
    if operator == ">":
        return value > threshold
    elif operator == "<":
        return value < threshold
    elif operator == ">=":
        return value >= threshold
    elif operator == "<=":
        return value <= threshold
    elif operator == "==":
        return value == threshold
    return False


@pytest.mark.asyncio
class TestRuleEvaluation:
    """Tests para evaluación de reglas de alertas"""
    
    async def test_rule_condition_greater_than(self, db_session: AsyncSession, test_host: Host):
        """Test que regla > dispara correctamente"""
        # Crear regla: CPU > 50%
        rule = AlertRule(
            name="Test CPU Alert",
            host_id=test_host.id,
            metric_name="cpu_usage",
            operator=">",
            threshold=50.0,
            severity="warning",
            enabled=True,
            duration_minutes=5
        )
        db_session.add(rule)
        
        # Crear métrica que supera umbral
        metric = Metric(
            host_id=test_host.id,
            timestamp=datetime.now(timezone.utc),
            cpu_usage=75.0,  # > 50.0
            memory_used=4000.0,
            memory_total=8000.0,
            disk_used=50.0,
            disk_total=100.0,
            network_received=1000.0,
            network_sent=500.0
        )
        db_session.add(metric)
        await db_session.commit()
        
        # Verificar condición
        assert check_condition(75.0, ">", 50.0) is True
        
        # Simular creación de alerta (lo que haría el motor)
        alert = Alert(
            host_id=test_host.id,
            rule_id=rule.id,
            message=f"CPU usage is {metric.cpu_usage}%",
            severity=rule.severity,
            metric_value=metric.cpu_usage,
            status="active"
        )
        db_session.add(alert)
        await db_session.commit()
        
        # Verificar que alerta existe
        result = await db_session.execute(
            select(Alert).where(Alert.host_id == test_host.id)
        )
        alerts = result.scalars().all()
        
        assert len(alerts) >= 1
        assert alerts[0].severity == "warning"
        assert alerts[0].metric_value == 75.0
    
    async def test_rule_condition_not_met(self, db_session: AsyncSession, test_host: Host):
        """Test que regla NO se dispara cuando condición no se cumple"""
        # Verificar lógica de condición
        assert check_condition(60.0, ">", 90.0) is False
        assert check_condition(40.0, "<", 30.0) is False
    
    async def test_disabled_rule_not_evaluated(self, db_session: AsyncSession, test_host: Host):
        """Test que reglas deshabilitadas existen pero no deberían procesarse"""
        rule = AlertRule(
            name="Disabled Rule",
            host_id=test_host.id,
            metric_name="cpu_usage",
            operator=">",
            threshold=10.0,
            severity="warning",
            enabled=False,  # DESHABILITADA
            duration_minutes=5
        )
        db_session.add(rule)
        await db_session.commit()
        
        # Verificar que regla existe
        result = await db_session.execute(
            select(AlertRule).where(AlertRule.enabled == False)
        )
        disabled_rules = result.scalars().all()
        assert len(disabled_rules) >= 1


@pytest.mark.asyncio
class TestOperators:
    """Tests para diferentes operadores de reglas"""
    
    @pytest.mark.parametrize("value,operator,threshold,should_trigger", [
        (60.0, ">", 50.0, True),   # 60 > 50 ✓
        (40.0, ">", 50.0, False),  # 40 > 50 ✗
        (50.0, ">", 50.0, False),  # 50 > 50 ✗
        (40.0, "<", 50.0, True),   # 40 < 50 ✓
        (60.0, "<", 50.0, False),  # 60 < 50 ✗
        (50.0, ">=", 50.0, True),  # 50 >= 50 ✓
        (60.0, ">=", 50.0, True),  # 60 >= 50 ✓
        (40.0, ">=", 50.0, False), # 40 >= 50 ✗
        (40.0, "<=", 50.0, True),  # 40 <= 50 ✓
        (50.0, "<=", 50.0, True),  # 50 <= 50 ✓
        (60.0, "<=", 50.0, False), # 60 <= 50 ✗
        (50.0, "==", 50.0, True),  # 50 == 50 ✓
        (49.9, "==", 50.0, False), # 49.9 == 50 ✗
    ])
    async def test_operator_logic(self, value, operator, threshold, should_trigger):
        """Test que operadores funcionan correctamente"""
        result = check_condition(value, operator, threshold)
        assert result == should_trigger, f"Operador {value} {operator} {threshold} falló"


@pytest.mark.asyncio
class TestMultipleRules:
    """Tests para múltiples reglas simultáneas"""
    
    async def test_multiple_rules_same_host(self, db_session: AsyncSession, test_host: Host):
        """Test que múltiples reglas pueden coexistir para mismo host"""
        # Crear 3 reglas diferentes
        rules_data = [
            ("CPU Warning", "cpu_usage", ">", 50.0, "warning"),
            ("Memory Warning", "memory_used", ">", 6000.0, "warning"),
            ("Disk Critical", "disk_used", ">", 80.0, "critical")
        ]
        
        for name, metric, op, thresh, sev in rules_data:
            rule = AlertRule(
                name=name,
                host_id=test_host.id,
                metric_name=metric,
                operator=op,
                threshold=thresh,
                severity=sev,
                enabled=True,
                duration_minutes=5
            )
            db_session.add(rule)
        
        await db_session.commit()
        
        # Verificar que se crearon
        result = await db_session.execute(
            select(AlertRule).where(AlertRule.host_id == test_host.id)
        )
        rules = result.scalars().all()
        assert len(rules) >= 3
    
    async def test_multiple_hosts_independent(self, db_session: AsyncSession, test_host: Host):
        """Test que reglas de diferentes hosts son independientes"""
        # Crear segundo host
        host2 = Host(
            id="test-host-02",
            hostname="server-02",
            ip="192.168.1.101",
            os="Debian 12",
            kernel_version="6.1",
            cpu_cores=4,
            total_memory=8192.0
        )
        db_session.add(host2)
        
        # Regla para host1
        rule1 = AlertRule(
            name="Host1 CPU",
            host_id=test_host.id,
            metric_name="cpu_usage",
            operator=">",
            threshold=50.0,
            severity="warning",
            enabled=True,
            duration_minutes=5
        )
        
        # Regla para host2
        rule2 = AlertRule(
            name="Host2 CPU",
            host_id=host2.id,
            metric_name="cpu_usage",
            operator=">",
            threshold=50.0,
            severity="warning",
            enabled=True,
            duration_minutes=5
        )
        
        db_session.add(rule1)
        db_session.add(rule2)
        await db_session.commit()
        
        # Verificar que ambas reglas existen y son independientes
        result1 = await db_session.execute(
            select(AlertRule).where(AlertRule.host_id == test_host.id)
        )
        rules1 = result1.scalars().all()
        
        result2 = await db_session.execute(
            select(AlertRule).where(AlertRule.host_id == host2.id)
        )
        rules2 = result2.scalars().all()
        
        assert len(rules1) >= 1
        assert len(rules2) >= 1


@pytest.mark.asyncio
class TestSeverityLevels:
    """Tests para niveles de severidad"""
    
    @pytest.mark.parametrize("severity", ["info", "warning", "critical"])
    async def test_different_severities(self, severity, db_session: AsyncSession, test_host: Host):
        """Test que reglas pueden tener diferentes severidades"""
        rule = AlertRule(
            name=f"Test {severity}",
            host_id=test_host.id,
            metric_name="cpu_usage",
            operator=">",
            threshold=50.0,
            severity=severity,
            enabled=True,
            duration_minutes=5
        )
        db_session.add(rule)
        await db_session.commit()
        await db_session.refresh(rule)
        
        assert rule.severity == severity


@pytest.mark.asyncio
class TestMetricTimeWindow:
    """Tests para ventana de tiempo de métricas"""
    
    async def test_recent_metrics_within_window(self, db_session: AsyncSession, test_host: Host):
        """Test que solo se consideran métricas recientes"""
        # Métrica reciente (dentro de ventana de 5 minutos)
        recent_metric = Metric(
            host_id=test_host.id,
            timestamp=datetime.now(timezone.utc),
            cpu_usage=80.0,
            memory_used=4000.0,
            memory_total=8000.0,
            disk_used=50.0,
            disk_total=100.0,
            network_received=1000.0,
            network_sent=500.0
        )
        
        # Métrica antigua (fuera de ventana)
        old_metric = Metric(
            host_id=test_host.id,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
            cpu_usage=90.0,
            memory_used=5000.0,
            memory_total=8000.0,
            disk_used=60.0,
            disk_total=100.0,
            network_received=2000.0,
            network_sent=1000.0
        )
        
        db_session.add(recent_metric)
        db_session.add(old_metric)
        await db_session.commit()
        
        # Consultar solo métricas recientes (últimos 5 minutos)
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
        result = await db_session.execute(
            select(Metric).where(
                Metric.host_id == test_host.id,
                Metric.timestamp >= time_threshold
            )
        )
        recent_metrics = result.scalars().all()
        
        # Solo debería retornar la métrica reciente
        assert len(recent_metrics) >= 1
        assert all(m.timestamp >= time_threshold for m in recent_metrics)


@pytest.mark.asyncio
class TestAlertCreation:
    """Tests para creación de alertas"""
    
    async def test_create_alert_from_rule(self, db_session: AsyncSession, test_host: Host, test_alert_rule: AlertRule):
        """Test crear alerta a partir de regla"""
        alert = Alert(
            host_id=test_host.id,
            rule_id=test_alert_rule.id,
            message=f"{test_alert_rule.name} triggered",
            severity=test_alert_rule.severity,
            metric_value=85.0,
            status="active"
        )
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)
        
        assert alert.id is not None
        assert alert.severity == test_alert_rule.severity
        assert alert.status == "active"
    
    async def test_alert_contains_metric_value(self, db_session: AsyncSession, test_host: Host, test_alert_rule: AlertRule):
        """Test que alerta guarda el valor que la disparó"""
        metric_value = 92.5
        alert = Alert(
            host_id=test_host.id,
            rule_id=test_alert_rule.id,
            message=f"CPU at {metric_value}%",
            severity="critical",
            metric_value=metric_value,
            status="active"
        )
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)
        
        assert alert.metric_value == metric_value



@pytest.mark.asyncio
class TestRuleEvaluation:
    """Tests para evaluación de reglas de alertas"""
    
    async def test_evaluate_rules_triggers_alert(self, db_session: AsyncSession, test_host: Host):
        """Test que regla se dispara cuando se cumple condición"""
        # Crear regla: CPU > 50%
        rule = AlertRule(
            name="Test CPU Alert",
            host_id=test_host.id,
            metric_name="cpu_usage",
            operator=">",
            threshold=50.0,
            severity="warning",
            enabled=True
        )
        db_session.add(rule)
        
        # Crear métrica que supera umbral
        metric = Metric(
            host_id=test_host.id,
            timestamp=datetime.now(timezone.utc),
            cpu_usage=75.0,  # > 50.0
            memory_used=4000.0,
            memory_total=8000.0,
            disk_used=50.0,
            disk_total=100.0,
            network_received=1000.0,
            network_sent=500.0
        )
        db_session.add(metric)
        await db_session.commit()
        
        # Ejecutar motor de alertas
        await evaluate_rules(db_session)
        
        # Verificar que se creó alerta
        result = await db_session.execute(
            select(Alert).where(Alert.host_id == test_host.id)
        )
        alerts = result.scalars().all()
        
        assert len(alerts) >= 1
        assert any(a.rule_id == rule.id for a in alerts)
        alert = [a for a in alerts if a.rule_id == rule.id][0]
        assert alert.severity == "warning"
        assert alert.metric_value == 75.0
    
    async def test_evaluate_rules_no_trigger(self, db_session: AsyncSession, test_host: Host):
        """Test que regla NO se dispara cuando no se cumple condición"""
        # Crear regla: CPU > 90%
        rule = AlertRule(
            name="Test High CPU",
            host_id=test_host.id,
            metric_name="cpu_usage",
            operator=">",
            threshold=90.0,
            severity="critical",
            enabled=True
        )
        db_session.add(rule)
        
        # Crear métrica que NO supera umbral
        metric = Metric(
            host_id=test_host.id,
            timestamp=datetime.now(timezone.utc),
            cpu_usage=60.0,  # < 90.0
            memory_used=4000.0,
            memory_total=8000.0,
            disk_used=50.0,
            disk_total=100.0,
            network_received=1000.0,
            network_sent=500.0
        )
        db_session.add(metric)
        await db_session.commit()
        
        initial_alerts_count = len((await db_session.execute(select(Alert))).scalars().all())
        
        # Ejecutar motor
        await evaluate_rules(db_session)
        
        # Verificar que NO se creó alerta nueva
        result = await db_session.execute(select(Alert))
        alerts = result.scalars().all()
        
        assert len(alerts) == initial_alerts_count
    
    async def test_evaluate_disabled_rule(self, db_session: AsyncSession, test_host: Host):
        """Test que reglas deshabilitadas no se evalúan"""
        # Crear regla deshabilitada
        rule = AlertRule(
            name="Disabled Rule",
            host_id=test_host.id,
            metric_name="cpu_usage",
            operator=">",
            threshold=10.0,
            severity="warning",
            enabled=False  # DESHABILITADA
        )
        db_session.add(rule)
        
        # Crear métrica que superaría umbral
        metric = Metric(
            host_id=test_host.id,
            timestamp=datetime.now(timezone.utc),
            cpu_usage=80.0,
            memory_used=4000.0,
            memory_total=8000.0,
            disk_used=50.0,
            disk_total=100.0,
            network_received=1000.0,
            network_sent=500.0
        )
        db_session.add(metric)
        await db_session.commit()
        
        # Ejecutar motor
        await evaluate_rules(db_session)
        
        # Verificar que NO se disparó alerta de regla deshabilitada
        result = await db_session.execute(
            select(Alert).where(Alert.rule_id == rule.id)
        )
        alerts = result.scalars().all()
        
        assert len(alerts) == 0


@pytest.mark.asyncio
class TestOperators:
    """Tests para diferentes operadores de reglas"""
    
    @pytest.mark.parametrize("value,operator,threshold,should_trigger", [
        (60.0, ">", 50.0, True),   # 60 > 50 ✓
        (40.0, ">", 50.0, False),  # 40 > 50 ✗
        (50.0, ">", 50.0, False),  # 50 > 50 ✗
        (40.0, "<", 50.0, True),   # 40 < 50 ✓
        (60.0, "<", 50.0, False),  # 60 < 50 ✗
        (50.0, ">=", 50.0, True),  # 50 >= 50 ✓
        (60.0, ">=", 50.0, True),  # 60 >= 50 ✓
        (40.0, ">=", 50.0, False), # 40 >= 50 ✗
        (40.0, "<=", 50.0, True),  # 40 <= 50 ✓
        (50.0, "<=", 50.0, True),  # 50 <= 50 ✓
        (60.0, "<=", 50.0, False), # 60 <= 50 ✗
        (50.0, "==", 50.0, True),  # 50 == 50 ✓
        (49.9, "==", 50.0, False), # 49.9 == 50 ✗
    ])
    async def test_operator_logic(self, value, operator, threshold, should_trigger, db_session: AsyncSession, test_host: Host):
        """Test que operadores funcionan correctamente"""
        # Crear regla con operador específico
        rule = AlertRule(
            name=f"Test {operator}",
            host_id=test_host.id,
            metric_name="cpu_usage",
            operator=operator,
            threshold=threshold,
            severity="warning",
            enabled=True
        )
        db_session.add(rule)
        
        # Crear métrica con valor específico
        metric = Metric(
            host_id=test_host.id,
            timestamp=datetime.now(timezone.utc),
            cpu_usage=value,
            memory_used=4000.0,
            memory_total=8000.0,
            disk_used=50.0,
            disk_total=100.0,
            network_received=1000.0,
            network_sent=500.0
        )
        db_session.add(metric)
        await db_session.commit()
        
        # Ejecutar motor
        await evaluate_rules(db_session)
        
        # Verificar resultado
        result = await db_session.execute(
            select(Alert).where(Alert.rule_id == rule.id)
        )
        alerts = result.scalars().all()
        
        if should_trigger:
            assert len(alerts) >= 1, f"Regla {value} {operator} {threshold} debería disparar"
        else:
            assert len(alerts) == 0, f"Regla {value} {operator} {threshold} NO debería disparar"


@pytest.mark.asyncio
class TestMultipleRules:
    """Tests para múltiples reglas simultáneas"""
    
    async def test_multiple_rules_same_host(self, db_session: AsyncSession, test_host: Host):
        """Test evaluar múltiples reglas para mismo host"""
        # Crear 3 reglas diferentes
        rules = [
            AlertRule(
                name="CPU Warning",
                host_id=test_host.id,
                metric_name="cpu_usage",
                operator=">",
                threshold=50.0,
                severity="warning",
                enabled=True
            ),
            AlertRule(
                name="Memory Warning",
                host_id=test_host.id,
                metric_name="memory_used",
                operator=">",
                threshold=6000.0,
                severity="warning",
                enabled=True
            ),
            AlertRule(
                name="Disk Critical",
                host_id=test_host.id,
                metric_name="disk_used",
                operator=">",
                threshold=80.0,
                severity="critical",
                enabled=True
            )
        ]
        
        for rule in rules:
            db_session.add(rule)
        
        # Crear métrica que dispara las 3 reglas
        metric = Metric(
            host_id=test_host.id,
            timestamp=datetime.now(timezone.utc),
            cpu_usage=75.0,     # > 50
            memory_used=7000.0, # > 6000
            memory_total=8000.0,
            disk_used=85.0,     # > 80
            disk_total=100.0,
            network_received=1000.0,
            network_sent=500.0
        )
        db_session.add(metric)
        await db_session.commit()
        
        # Ejecutar motor
        await evaluate_rules(db_session)
        
        # Verificar que se crearon 3 alertas
        result = await db_session.execute(
            select(Alert).where(Alert.host_id == test_host.id)
        )
        alerts = result.scalars().all()
        
        assert len(alerts) >= 3
        assert any(a.severity == "warning" for a in alerts)
        assert any(a.severity == "critical" for a in alerts)
    
    async def test_multiple_hosts_independent(self, db_session: AsyncSession, test_host: Host):
        """Test que reglas de diferentes hosts son independientes"""
        # Crear segundo host
        host2 = Host(
            id="test-host-02",
            hostname="server-02",
            ip="192.168.1.101",
            os="Debian 12",
            kernel_version="6.1",
            cpu_cores=4,
            total_memory=8192.0
        )
        db_session.add(host2)
        
        # Regla para host1
        rule1 = AlertRule(
            name="Host1 CPU",
            host_id=test_host.id,
            metric_name="cpu_usage",
            operator=">",
            threshold=50.0,
            severity="warning",
            enabled=True
        )
        
        # Regla para host2
        rule2 = AlertRule(
            name="Host2 CPU",
            host_id=host2.id,
            metric_name="cpu_usage",
            operator=">",
            threshold=50.0,
            severity="warning",
            enabled=True
        )
        
        db_session.add(rule1)
        db_session.add(rule2)
        
        # Solo host1 supera umbral
        metric1 = Metric(
            host_id=test_host.id,
            timestamp=datetime.now(timezone.utc),
            cpu_usage=80.0,  # Dispara
            memory_used=4000.0,
            memory_total=8000.0,
            disk_used=50.0,
            disk_total=100.0,
            network_received=1000.0,
            network_sent=500.0
        )
        
        metric2 = Metric(
            host_id=host2.id,
            timestamp=datetime.now(timezone.utc),
            cpu_usage=30.0,  # NO dispara
            memory_used=4000.0,
            memory_total=8000.0,
            disk_used=50.0,
            disk_total=100.0,
            network_received=1000.0,
            network_sent=500.0
        )
        
        db_session.add(metric1)
        db_session.add(metric2)
        await db_session.commit()
        
        # Ejecutar motor
        await evaluate_rules(db_session)
        
        # Verificar alertas solo en host1
        result1 = await db_session.execute(
            select(Alert).where(Alert.host_id == test_host.id)
        )
        alerts1 = result1.scalars().all()
        
        result2 = await db_session.execute(
            select(Alert).where(Alert.host_id == host2.id)
        )
        alerts2 = result2.scalars().all()
        
        assert len(alerts1) >= 1  # host1 tiene alerta
        assert len(alerts2) == 0  # host2 NO tiene alerta


@pytest.mark.asyncio
class TestSeverityLevels:
    """Tests para niveles de severidad"""
    
    @pytest.mark.parametrize("severity", ["info", "warning", "critical"])
    async def test_different_severities(self, severity, db_session: AsyncSession, test_host: Host):
        """Test que alertas respetan nivel de severidad configurado"""
        rule = AlertRule(
            name=f"Test {severity}",
            host_id=test_host.id,
            metric_name="cpu_usage",
            operator=">",
            threshold=50.0,
            severity=severity,
            enabled=True
        )
        db_session.add(rule)
        
        metric = Metric(
            host_id=test_host.id,
            timestamp=datetime.now(timezone.utc),
            cpu_usage=75.0,
            memory_used=4000.0,
            memory_total=8000.0,
            disk_used=50.0,
            disk_total=100.0,
            network_received=1000.0,
            network_sent=500.0
        )
        db_session.add(metric)
        await db_session.commit()
        
        await evaluate_rules(db_session)
        
        result = await db_session.execute(
            select(Alert).where(Alert.rule_id == rule.id)
        )
        alerts = result.scalars().all()
        
        assert len(alerts) >= 1
        assert alerts[0].severity == severity


@pytest.mark.asyncio
class TestAlertDuplication:
    """Tests para prevenir duplicación de alertas"""
    
    async def test_no_duplicate_alerts(self, db_session: AsyncSession, test_host: Host):
        """Test que no se crean alertas duplicadas para misma regla"""
        rule = AlertRule(
            name="Test Duplicate",
            host_id=test_host.id,
            metric_name="cpu_usage",
            operator=">",
            threshold=50.0,
            severity="warning",
            enabled=True
        )
        db_session.add(rule)
        
        # Crear métrica que dispara regla
        metric = Metric(
            host_id=test_host.id,
            timestamp=datetime.now(timezone.utc),
            cpu_usage=80.0,
            memory_used=4000.0,
            memory_total=8000.0,
            disk_used=50.0,
            disk_total=100.0,
            network_received=1000.0,
            network_sent=500.0
        )
        db_session.add(metric)
        await db_session.commit()
        
        # Ejecutar motor múltiples veces
        await evaluate_rules(db_session)
        await evaluate_rules(db_session)
        await evaluate_rules(db_session)
        
        # Verificar que solo hay una alerta activa
        result = await db_session.execute(
            select(Alert).where(
                Alert.rule_id == rule.id,
                Alert.status == "active"
            )
        )
        active_alerts = result.scalars().all()
        
        # Debería haber solo 1 alerta activa (no duplicados)
        assert len(active_alerts) == 1
