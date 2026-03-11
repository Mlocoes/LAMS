"""
Fixtures globales de pytest para tests de LAMS
Provee fixtures reutilizables para base de datos, cliente HTTP y datos de prueba
"""
import asyncio
from typing import AsyncGenerator, Dict
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from database.models import Base, User, Host, Metric, Alert, AlertRule, DockerContainer, RemoteCommand, NotificationConfig
from auth.security import get_password_hash
from core.config import settings
from main import app
from database.session import get_db


# URL de base de datos en memoria para tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """
    Fixture para proporcionar event loop para toda la sesión de tests
    Necesario para  pytest-asyncio
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    """
    Fixture para crear engine de base de datos en memoria
    Se crea uno nuevo para cada test para aislamiento completo
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # Crear todas las tablas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Limpiar
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture para proporcionar sesión de base de datos para tests
    Cada test obtiene una sesión limpia
    """
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture para cliente HTTP de pruebas
    Sobrescribe la dependencia de base de datos para usar session de test
    """
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """
    Fixture para crear usuario admin de prueba
    """
    user = User(
        email="admin@test.com",
        password_hash=get_password_hash("admin123"),
        role="admin"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def regular_user(db_session: AsyncSession) -> User:
    """
    Fixture para crear usuario regular de prueba
    """
    user = User(
        email="user@test.com",
        password_hash=get_password_hash("user123"),
        role="user"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, admin_user: User) -> str:
    """
    Fixture para obtener token JWT de admin
    """
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@test.com",
            "password": "admin123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]


@pytest_asyncio.fixture
async def user_token(client: AsyncClient, regular_user: User) -> str:
    """
    Fixture para obtener token JWT de usuario regular
    """
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "user@test.com",
            "password": "user123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]


@pytest_asyncio.fixture
async def auth_headers(admin_token: str) -> Dict[str, str]:
    """
    Fixture para headers de autenticación con token admin
    """
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def test_host(db_session: AsyncSession) -> Host:
    """
    Fixture para crear host de prueba
    """
    host = Host(
        id="test-host-01",
        hostname="test-server",
        ip="192.168.1.100",
        os="Ubuntu 22.04",
        kernel_version="5.15.0-generic",
        cpu_cores=4,
        total_memory=8192.0,
        tags=["test", "development"],
        status="online"
    )
    db_session.add(host)
    await db_session.commit()
    await db_session.refresh(host)
    return host


@pytest_asyncio.fixture
async def test_metrics(db_session: AsyncSession, test_host: Host) -> list[Metric]:
    """
    Fixture para crear métricas de prueba
    """
    metrics = []
    for i in range(5):
        metric = Metric(
            host_id=test_host.id,
            timestamp=datetime.now(timezone.utc),
            cpu_usage=50.0 + i * 5,
            memory_used=4096.0 + i * 100,
            memory_total=8192.0,
            disk_used=50.0 + i * 2,
            disk_total=100.0,
            network_received=1000.0 + i * 10,
            network_sent=500.0 + i * 5,
            cpu_temp=45.0 + i
        )
        metrics.append(metric)
        db_session.add(metric)
    
    await db_session.commit()
    for metric in metrics:
        await db_session.refresh(metric)
    return metrics


@pytest_asyncio.fixture
async def test_alert_rule(db_session: AsyncSession, test_host: Host) -> AlertRule:
    """
    Fixture para crear regla de alerta de prueba
    """
    rule = AlertRule(
        name="Test CPU Alert",
        description="Alert when CPU is high",
        host_id=test_host.id,
        metric_name="cpu_usage",
        operator=">",
        threshold=80.0,
        severity="warning",
        enabled=True
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    return rule


@pytest_asyncio.fixture
async def test_alert(db_session: AsyncSession, test_host: Host, test_alert_rule: AlertRule) -> Alert:
    """
    Fixture para crear alerta de prueba
    """
    alert = Alert(
        host_id=test_host.id,
        rule_id=test_alert_rule.id,
        message="CPU usage is 85.5%",
        severity="warning",
        metric_value=85.5,
        status="active"
    )
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)
    return alert


@pytest_asyncio.fixture
async def test_docker_container(db_session: AsyncSession, test_host: Host) -> DockerContainer:
    """
    Fixture para crear contenedor Docker de prueba
    """
    container = DockerContainer(
        container_id="abc123def456",
        host_id=test_host.id,
        name="test-container",
        image="nginx:latest",
        status="running",
        ports={"80/tcp": "8080"}
    )
    db_session.add(container)
    await db_session.commit()
    await db_session.refresh(container)
    return container


@pytest_asyncio.fixture
async def test_notification_config(db_session: AsyncSession, admin_user: User) -> NotificationConfig:
    """
    Fixture para crear configuración de notificación de prueba
    """
    config = NotificationConfig(
        user_id=admin_user.id,
        provider="email",
        config={
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "smtp_user": "test@test.com",
            "smtp_password": "password",
            "email_from": "test@test.com",
            "email_to": "admin@test.com"
        },
        enabled=True,
        severity_filter="all"
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config
