"""
Prometheus metrics exporter for LAMS.

Exports host and Docker container metrics in Prometheus format.
"""

from prometheus_client import (
    CollectorRegistry, Gauge, Counter, generate_latest,
    CONTENT_TYPE_LATEST
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import logging

from database.models import Host, Metric, DockerContainer

logger = logging.getLogger(__name__)

# Registry global para métricas
registry = CollectorRegistry()

# ============================================================================
# HOST METRICS
# ============================================================================

host_cpu_usage = Gauge(
    'lams_host_cpu_usage_percent',
    'CPU usage percentage',
    ['host_id', 'hostname', 'ip'],
    registry=registry
)

host_memory_usage = Gauge(
    'lams_host_memory_usage_percent',
    'Memory usage percentage',
    ['host_id', 'hostname', 'ip'],
    registry=registry
)

host_memory_total = Gauge(
    'lams_host_memory_total_bytes',
    'Total memory in bytes',
    ['host_id', 'hostname', 'ip'],
    registry=registry
)

host_memory_used = Gauge(
    'lams_host_memory_used_bytes',
    'Used memory in bytes',
    ['host_id', 'hostname', 'ip'],
    registry=registry
)

host_disk_usage = Gauge(
    'lams_host_disk_usage_percent',
    'Disk usage percentage',
    ['host_id', 'hostname', 'ip', 'mount_point'],
    registry=registry
)

host_temperature = Gauge(
    'lams_host_temperature_celsius',
    'CPU temperature in Celsius',
    ['host_id', 'hostname', 'ip'],
    registry=registry
)

host_network_rx_bytes = Counter(
    'lams_host_network_receive_bytes_total',
    'Total network bytes received',
    ['host_id', 'hostname', 'ip'],
    registry=registry
)

host_network_tx_bytes = Counter(
    'lams_host_network_transmit_bytes_total',
    'Total network bytes transmitted',
    ['host_id', 'hostname', 'ip'],
    registry=registry
)

host_up = Gauge(
    'lams_host_up',
    'Host status (1=online, 0=offline)',
    ['host_id', 'hostname', 'ip'],
    registry=registry
)

host_info = Gauge(
    'lams_host_info',
    'Host information',
    ['host_id', 'hostname', 'ip', 'os', 'os_version', 'kernel'],
    registry=registry
)

# ============================================================================
# DOCKER CONTAINER METRICS
# ============================================================================

docker_container_cpu = Gauge(
    'lams_docker_container_cpu_percent',
    'Docker container CPU usage percentage',
    ['host_id', 'hostname', 'container_id', 'container_name', 'image'],
    registry=registry
)

docker_container_memory = Gauge(
    'lams_docker_container_memory_bytes',
    'Docker container memory usage in bytes',
    ['host_id', 'hostname', 'container_id', 'container_name', 'image'],
    registry=registry
)

docker_container_up = Gauge(
    'lams_docker_container_up',
    'Docker container status (1=running, 0=stopped)',
    ['host_id', 'hostname', 'container_id', 'container_name', 'image'],
    registry=registry
)


async def update_prometheus_metrics(db: AsyncSession) -> None:
    """
    Actualiza las métricas Prometheus con los últimos valores de la BD.
    
    Esta función se ejecuta antes de cada scrape de Prometheus para
    asegurar que las métricas están actualizadas.
    
    Args:
        db: Sesión de base de datos async
    """
    try:
        # Obtener todos los hosts
        result = await db.execute(select(Host))
        hosts = result.scalars().all()
        
        logger.info(f"Updating Prometheus metrics for {len(hosts)} hosts")
        
        for host in hosts:
            labels = {
                'host_id': host.id,
                'hostname': host.hostname,
                'ip': host.ip
            }
            
            # Host status (online si last_seen < 60 segundos)
            is_online = False
            if host.last_seen:
                seconds_since_seen = (
                    datetime.now(timezone.utc) - host.last_seen
                ).total_seconds()
                is_online = seconds_since_seen < 60
            
            host_up.labels(**labels).set(1 if is_online else 0)
            
            # Host info (siempre en 1, los labels contienen la info)
            info_labels = {
                **labels,
                'os': host.os or 'unknown',
                'os_version': 'unknown',  # No disponible en modelo actual
                'kernel': host.kernel_version or 'unknown'
            }
            host_info.labels(**info_labels).set(1)
            
            # Obtener última métrica del host (últimos 5 minutos)
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
            metric_result = await db.execute(
                select(Metric)
                .where(Metric.host_id == host.id)
                .where(Metric.timestamp >= cutoff_time)
                .order_by(Metric.timestamp.desc())
                .limit(1)
            )
            metric = metric_result.scalar_one_or_none()
            
            if metric:
                # CPU
                host_cpu_usage.labels(**labels).set(metric.cpu_usage)
                
                # Memory (calcular porcentaje desde used y free)
                if metric.memory_used is not None and metric.memory_free is not None:
                    total_mem = metric.memory_used + metric.memory_free
                    if total_mem > 0:
                        memory_pct = (metric.memory_used / total_mem) * 100.0
                        host_memory_usage.labels(**labels).set(memory_pct)
                        # Memory en bytes
                        host_memory_total.labels(**labels).set(total_mem * 1024 * 1024)  # MB to bytes
                        host_memory_used.labels(**labels).set(metric.memory_used * 1024 * 1024)
                
                # Temperature
                if metric.temp_cpu is not None:
                    host_temperature.labels(**labels).set(metric.temp_cpu)
                
                # Disk usage
                disk_labels = {**labels, 'mount_point': '/'}
                if metric.disk_usage_percent is not None:
                    host_disk_usage.labels(**disk_labels).set(metric.disk_usage_percent)
                
                # Network (counters acumulativos)
                # Usamos _value.set() para setear el valor interno del Counter
                if metric.net_rx is not None:
                    host_network_rx_bytes.labels(**labels)._value.set(metric.net_rx)
                if metric.net_tx is not None:
                    host_network_tx_bytes.labels(**labels)._value.set(metric.net_tx)
            else:
                logger.debug(
                    f"No recent metrics for host {host.hostname} "
                    f"(last_seen: {host.last_seen})"
                )
            
            # Obtener contenedores Docker del host
            docker_result = await db.execute(
                select(DockerContainer)
                .where(DockerContainer.host_id == host.id)
            )
            containers = docker_result.scalars().all()
            
            for container in containers:
                # Short ID (primeros 12 caracteres) - el ID completo está en container.id
                short_id = container.id[:12] if container.id else container.id
                
                container_labels = {
                    'host_id': host.id,
                    'hostname': host.hostname,
                    'container_id': short_id,
                    'container_name': container.name,
                    'image': container.image
                }
                
                # Container status
                is_running = container.state.lower() == 'running'
                docker_container_up.labels(**container_labels).set(
                    1 if is_running else 0
                )
                
                # Container resources (solo si está running)
                if is_running:
                    docker_container_cpu.labels(**container_labels).set(
                        container.cpu_percent
                    )
                    # Convertir MB a bytes
                    memory_bytes = container.memory_usage * 1024 * 1024
                    docker_container_memory.labels(**container_labels).set(
                        memory_bytes
                    )
        
        logger.info("Prometheus metrics updated successfully")
        
    except Exception as e:
        logger.error(f"Error updating Prometheus metrics: {e}", exc_info=True)
        raise


def generate_prometheus_metrics() -> bytes:
    """
    Genera las métricas en formato Prometheus.
    
    Returns:
        bytes: Métricas en formato texto plano Prometheus
    """
    return generate_latest(registry)
