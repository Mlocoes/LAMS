"""
Tests para modelos de base de datos
Valida: campos, validaciones, relaciones y cascadas
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Host, Metric, Alert, AlertRule, DockerContainer, RemoteCommand, NotificationConfig
from auth.security import get_password_hash


@pytest.mark.asyncio
class TestUserModel:
    """Tests para modelo User"""
    
    async def test_create_user(self, db_session: AsyncSession):
        """Test crear usuario básico"""
        user = User(
            email="test@example.com",
            password_hash=get_password_hash("password123"),
            role="user"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.role == "user"
        assert user.created_at is not None
    
    async def test_user_email_unique(self, db_session: AsyncSession, admin_user: User):
        """Test que email es único"""
        duplicate_user = User(
            email=admin_user.email,
            password_hash=get_password_hash("password"),
            role="user"
        )
        db_session.add(duplicate_user)
        
        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()
    
    async def test_user_notification_relationship(self, db_session: AsyncSession, admin_user: User, test_notification_config: NotificationConfig):
        """Test relación User <-> NotificationConfig"""
        await db_session.refresh(admin_user, ["notification_configs"])
        assert len(admin_user.notification_configs) == 1
        assert admin_user.notification_configs[0].provider == "email"


@pytest.mark.asyncio
class TestHostModel:
    """Tests para modelo Host"""
    
    async def test_create_host(self, db_session: AsyncSession):
        """Test crear host básico"""
        host = Host(
            id="server-01",
            hostname="web-server",
            ip="10.0.0.5",
            os="Debian 12",
            kernel_version="6.1.0",
            cpu_cores=8,
            total_memory=16384.0,
            tags=["production", "web"],
            status="online"
        )
        db_session.add(host)
        await db_session.commit()
        await db_session.refresh(host)
        
        assert host.id == "server-01"
        assert host.hostname == "web-server"
        assert host.cpu_cores == 8
        assert "production" in host.tags
    
    async def test_host_id_unique(self, db_session: AsyncSession, test_host: Host):
        """Test que host_id es único"""
        duplicate_host = Host(
            id=test_host.id,
            hostname="another-server",
            ip="10.0.0.6",
            os="Ubuntu",
            kernel_version="5.15",
            cpu_cores=4,
            total_memory=8192.0
        )
        db_session.add(duplicate_host)
        
        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()
    
    async def test_host_metrics_relationship(self, db_session: AsyncSession, test_host: Host, test_metrics: list[Metric]):
        """Test relación Host <-> Metrics"""
        await db_session.refresh(test_host, ["metrics"])
        assert len(test_host.metrics) == 5
    
    async def test_host_cascade_delete_metrics(self, db_session: AsyncSession, test_host: Host, test_metrics: list[Metric]):
        """Test que eliminar host elimina sus métricas en cascada"""
        host_id = test_host.id
        await db_session.delete(test_host)
        await db_session.commit()
        
        # Verificar que métricas fueron eliminadas
        result = await db_session.execute(
            select(Metric).where(Metric.host_id == host_id)
        )
        metrics = result.scalars().all()
        assert len(metrics) == 0


@pytest.mark.asyncio
class TestMetricModel:
    """Tests para modelo Metric"""
    
    async def test_create_metric(self, db_session: AsyncSession, test_host: Host):
        """Test crear métrica básica"""
        metric = Metric(
            host_id=test_host.id,
            timestamp=datetime.now(timezone.utc),
            cpu_usage=65.3,
            memory_used=4500.0,
            memory_total=8192.0,
            disk_used=75.0,
            disk_total=200.0,
            network_received=1500.0,
            network_sent=800.0,
            cpu_temp=52.0
        )
        db_session.add(metric)
        await db_session.commit()
        await db_session.refresh(metric)
        
        assert metric.id is not None
        assert metric.cpu_usage == 65.3
        assert metric.timestamp is not None
    
    async def test_metric_requires_host(self, db_session: AsyncSession):
        """Test que métrica requiere host válido"""
        metric = Metric(
            host_id="nonexistent-host",
            timestamp=datetime.now(timezone.utc),
            cpu_usage=50.0,
            memory_used=4000.0,
            memory_total=8000.0,
            disk_used=50.0,
            disk_total=100.0,
            network_received=1000.0,
            network_sent=500.0
        )
        db_session.add(metric)
        
        with pytest.raises(Exception):  # ForeignKeyError
            await db_session.commit()


@pytest.mark.asyncio
class TestAlertRuleModel:
    """Tests para modelo AlertRule"""
    
    async def test_create_alert_rule(self, db_session: AsyncSession, test_host: Host):
        """Test crear regla de alerta"""
        rule = AlertRule(
            name="High Memory Usage",
            description="Alert when memory > 90%",
            host_id=test_host.id,
            metric_name="memory_used",
            operator=">",
            threshold=7372.8,  # 90% of 8192
            severity="critical",
            enabled=True
        )
        db_session.add(rule)
        await db_session.commit()
        await db_session.refresh(rule)
        
        assert rule.id is not None
        assert rule.name == "High Memory Usage"
        assert rule.metric_name == "memory_used"
        assert rule.operator == ">"
        assert rule.threshold == 7372.8
        assert rule.severity == "critical"
    
    async def test_alert_rule_operators(self, db_session: AsyncSession, test_host: Host):
        """Test diferentes operadores de reglas"""
        operators = [">", "<", ">=", "<=", "=="]
        
        for op in operators:
            rule = AlertRule(
                name=f"Test {op}",
                host_id=test_host.id,
                metric_name="cpu_usage",
                operator=op,
                threshold=50.0,
                severity="warning",
                enabled=True
            )
            db_session.add(rule)
        
        await db_session.commit()
        
        result = await db_session.execute(select(AlertRule))
        rules = result.scalars().all()
        assert len(rules) == len(operators)


@pytest.mark.asyncio
class TestAlertModel:
    """Tests para modelo Alert"""
    
    async def test_create_alert(self, db_session: AsyncSession, test_host: Host, test_alert_rule: AlertRule):
        """Test crear alerta"""
        alert = Alert(
            host_id=test_host.id,
            rule_id=test_alert_rule.id,
            message="CPU usage exceeded threshold: 92.5%",
            severity="critical",
            metric_value=92.5,
            status="active"
        )
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)
        
        assert alert.id is not None
        assert alert.message is not None
        assert alert.severity == "critical"
        assert alert.metric_value == 92.5
        assert alert.status == "active"
        assert alert.created_at is not None


@pytest.mark.asyncio
class TestDockerContainerModel:
    """Tests para modelo DockerContainer"""
    
    async def test_create_docker_container(self, db_session: AsyncSession, test_host: Host):
        """Test crear contenedor Docker"""
        container = DockerContainer(
            container_id="1a2b3c4d5e6f",
            host_id=test_host.id,
            name="webapp",
            image="python:3.11-alpine",
            status="running",
            ports={"8000/tcp": "8000", "443/tcp": "8443"}
        )
        db_session.add(container)
        await db_session.commit()
        await db_session.refresh(container)
        
        assert container.id is not None
        assert container.container_id == "1a2b3c4d5e6f"
        assert container.name == "webapp"
        assert container.image == "python:3.11-alpine"
        assert container.status == "running"
        assert "8000/tcp" in container.ports


@pytest.mark.asyncio
class TestRemoteCommandModel:
    """Tests para modelo RemoteCommand"""
    
    async def test_create_remote_command(self, db_session: AsyncSession, test_host: Host):
        """Test crear comando remoto"""
        command = RemoteCommand(
            host_id=test_host.id,
            command_type="docker_start",
            target_id="container123",
            status="pending"
        )
        db_session.add(command)
        await db_session.commit()
        await db_session.refresh(command)
        
        assert command.id is not None
        assert command.command_type == "docker_start"
        assert command.status == "pending"
        assert command.created_at is not None
        assert command.executed_at is None
        assert command.result is None
    
    async def test_command_status_transitions(self, db_session: AsyncSession, test_host: Host):
        """Test transiciones de estado de comando"""
        command = RemoteCommand(
            host_id=test_host.id,
            command_type="docker_restart",
            target_id="container456",
            status="pending"
        )
        db_session.add(command)
        await db_session.commit()
        
        # Simular ejecución
        command.status = "executing"
        await db_session.commit()
        
        # Simular completado
        command.status = "completed"
        command.executed_at = datetime.now(timezone.utc)
        command.result = "success"
        await db_session.commit()
        await db_session.refresh(command)
        
        assert command.status == "completed"
        assert command.executed_at is not None
        assert command.result == "success"


@pytest.mark.asyncio
class TestNotificationConfigModel:
    """Tests para modelo NotificationConfig"""
    
    async def test_create_notification_config(self, db_session: AsyncSession, admin_user: User):
        """Test crear configuración de notificación"""
        config = NotificationConfig(
            user_id=admin_user.id,
            provider="slack",
            config={"webhook_url": "https://hooks.slack.com/services/XXX"},
            enabled=True,
            severity_filter="critical"
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)
        
        assert config.id is not None
        assert config.provider == "slack"
        assert "webhook_url" in config.config
        assert config.enabled is True
        assert config.severity_filter == "critical"
    
    async def test_notification_providers(self, db_session: AsyncSession, admin_user: User):
        """Test diferentes providers de notificación"""
        providers = ["email", "slack", "discord"]
        
        for provider in providers:
            config = NotificationConfig(
                user_id=admin_user.id,
                provider=provider,
                config={"test": "config"},
                enabled=True,
                severity_filter="all"
            )
            db_session.add(config)
        
        await db_session.commit()
        
        result = await db_session.execute(
            select(NotificationConfig).where(NotificationConfig.user_id == admin_user.id)
        )
        configs = result.scalars().all()
        assert len(configs) == len(providers)
