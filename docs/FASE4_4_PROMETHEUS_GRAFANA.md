# Fase 4.4: Integración con Prometheus/Grafana

**Duración estimada:** 4-5 días  
**Prioridad:** Alta  
**Estado:** 🔄 En planificación

## Objetivo

Integrar LAMS con el ecosistema de monitorización estándar de la industria (Prometheus + Grafana) para:
- Exportar métricas en formato Prometheus
- Permitir scraping automático de métricas
- Usar Grafana para visualizaciones avanzadas
- Mantener compatibilidad con herramientas existentes

---

## Arquitectura

```
┌─────────────┐
│ LAMS Agent  │ ──metrics──> ┌──────────────┐
└─────────────┘              │ LAMS Backend │
                             │   FastAPI    │
                             └──────┬───────┘
                                    │
                     ┌──────────────┼──────────────┐
                     │              │              │
                     ▼              ▼              ▼
              ┌──────────┐   ┌──────────┐   ┌──────────┐
              │ Frontend │   │Prometheus│   │ Grafana  │
              │ Next.js  │   │  Scraper │   │Dashboard │
              └──────────┘   └──────┬───┘   └─────┬────┘
                                    │             │
                                    └─────────────┘
                                   Query Metrics
```

---

## Fase 1: Exportador Prometheus (Backend)

### 1.1 Instalar Dependencias

```bash
cd server
pip install prometheus-client==0.19.0
```

Añadir a `requirements.txt`:
```
prometheus-client==0.19.0
```

### 1.2 Crear Módulo de Exportación

**Archivo:** `server/prometheus/exporter.py`

```python
from prometheus_client import (
    CollectorRegistry, Gauge, Counter, generate_latest, 
    CONTENT_TYPE_LATEST
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import Dict, List
from ..database.models import Host, Metric, DockerContainer

# Registry global para métricas
registry = CollectorRegistry()

# Definir métricas Prometheus
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

docker_container_cpu = Gauge(
    'lams_docker_container_cpu_percent',
    'Docker container CPU usage',
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
    Esta función se ejecuta antes de cada scrape de Prometheus.
    """
    # Obtener todos los hosts activos
    result = await db.execute(select(Host))
    hosts = result.scalars().all()
    
    for host in hosts:
        labels = {
            'host_id': host.id,
            'hostname': host.hostname,
            'ip': host.ip
        }
        
        # Host status
        is_online = (
            datetime.utcnow() - host.last_seen
        ).total_seconds() < 60 if host.last_seen else False
        
        host_up.labels(**labels).set(1 if is_online else 0)
        
        # Obtener última métrica del host (últimos 5 minutos)
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        metric_result = await db.execute(
            select(Metric)
            .where(Metric.host_id == host.id)
            .where(Metric.timestamp >= cutoff_time)
            .order_by(Metric.timestamp.desc())
            .limit(1)
        )
        metric = metric_result.scalar_one_or_none()
        
        if metric:
            # CPU, Memory, Temperature
            host_cpu_usage.labels(**labels).set(metric.cpu_usage)
            host_memory_usage.labels(**labels).set(metric.memory_usage)
            host_temperature.labels(**labels).set(metric.temperature or 0)
            
            # Memory en bytes (si tenemos total_memory en Host)
            if hasattr(host, 'total_memory_mb'):
                total_bytes = host.total_memory_mb * 1024 * 1024
                used_bytes = total_bytes * (metric.memory_usage / 100)
                host_memory_total.labels(**labels).set(total_bytes)
                host_memory_used.labels(**labels).set(used_bytes)
            
            # Disk usage (usando "/" como mount point por defecto)
            disk_labels = {**labels, 'mount_point': '/'}
            host_disk_usage.labels(**disk_labels).set(metric.disk_usage)
            
            # Network (counters acumulativos)
            host_network_rx_bytes.labels(**labels)._value.set(metric.network_rx)
            host_network_tx_bytes.labels(**labels)._value.set(metric.network_tx)
        
        # Obtener contenedores Docker del host
        docker_result = await db.execute(
            select(DockerContainer)
            .where(DockerContainer.host_id == host.id)
        )
        containers = docker_result.scalars().all()
        
        for container in containers:
            container_labels = {
                'host_id': host.id,
                'hostname': host.hostname,
                'container_id': container.container_id[:12],  # Short ID
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
                docker_container_memory.labels(**container_labels).set(
                    container.memory_usage * 1024 * 1024  # MB to bytes
                )


def generate_prometheus_metrics() -> bytes:
    """
    Genera las métricas en formato Prometheus.
    """
    return generate_latest(registry)
```

### 1.3 Crear Endpoint de Métricas

**Archivo:** `server/api/prometheus.py`

```python
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_client import CONTENT_TYPE_LATEST

from ..database.database import get_db
from ..prometheus.exporter import (
    update_prometheus_metrics,
    generate_prometheus_metrics
)

router = APIRouter(prefix="/metrics", tags=["prometheus"])


@router.get("", response_class=Response)
async def prometheus_metrics(db: AsyncSession = Depends(get_db)):
    """
    Endpoint compatible con Prometheus para scraping de métricas.
    
    Este endpoint:
    - NO requiere autenticación (Prometheus scraper no soporta JWT)
    - Actualiza métricas desde la BD
    - Retorna formato texto plano compatible con Prometheus
    
    Ejemplo de scrape config:
    ```yaml
    scrape_configs:
      - job_name: 'lams'
        static_configs:
          - targets: ['lams-backend:8080']
    ```
    """
    # Actualizar métricas en tiempo real desde BD
    await update_prometheus_metrics(db)
    
    # Generar salida en formato Prometheus
    metrics_output = generate_prometheus_metrics()
    
    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST
    )
```

### 1.4 Registrar Router en Main

**Archivo:** `server/main.py`

```python
from api import prometheus as prometheus_api

# ... código existente ...

# Registrar router de Prometheus
app.include_router(prometheus_api.router, prefix="/api/v1")
```

### 1.5 Actualizar Middleware CSRF

**Archivo:** `server/middleware/csrf.py`

Añadir `/api/v1/metrics` a `CSRF_EXEMPT_PATHS`:

```python
CSRF_EXEMPT_PATHS = [
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/hosts/register",
    "/api/v1/metrics/",          # Agente
    "/api/v1/metrics",           # Prometheus ← NUEVO
    "/api/v1/commands/",
    "/api/v1/docker/sync",
    "/api/v1/agents/generate",
]
```

---

## Fase 2: Configuración Prometheus

### 2.1 Crear Configuración Prometheus

**Archivo:** `prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'lams'
    environment: 'production'

scrape_configs:
  # LAMS Backend metrics
  - job_name: 'lams-backend'
    static_configs:
      - targets: ['lams-server:8080']
        labels:
          service: 'lams-api'
    metrics_path: '/api/v1/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### 2.2 Actualizar Docker Compose

**Archivo:** `docker-compose.yml`

Añadir servicio Prometheus:

```yaml
services:
  # ... servicios existentes ...

  prometheus:
    image: prom/prometheus:v2.48.0
    container_name: lams-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'
    networks:
      - lams-network
    depends_on:
      - lams-server

volumes:
  postgres-data:
  prometheus-data:

networks:
  lams-network:
    driver: bridge
```

---

## Fase 3: Integración Grafana

### 3.1 Añadir Grafana al Docker Compose

**Archivo:** `docker-compose.yml`

```yaml
  grafana:
    image: grafana/grafana:10.2.2
    container_name: lams-grafana
    restart: unless-stopped
    ports:
      - "3002:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-lams2024}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=http://localhost:3002
      - GF_AUTH_ANONYMOUS_ENABLED=false
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
    networks:
      - lams-network
    depends_on:
      - prometheus

volumes:
  postgres-data:
  prometheus-data:
  grafana-data:
```

### 3.2 Configurar Datasource Automático

**Archivo:** `grafana/provisioning/datasources/prometheus.yml`

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
    jsonData:
      timeInterval: "15s"
      queryTimeout: "60s"
```

### 3.3 Crear Dashboard LAMS

**Archivo:** `grafana/provisioning/dashboards/dashboard.yml`

```yaml
apiVersion: 1

providers:
  - name: 'LAMS Dashboards'
    orgId: 1
    folder: 'LAMS'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: true
```

### 3.4 Dashboard JSON: Host Overview

**Archivo:** `grafana/dashboards/lams-host-overview.json`

```json
{
  "dashboard": {
    "title": "LAMS - Host Overview",
    "uid": "lams-host-overview",
    "tags": ["lams", "hosts"],
    "timezone": "browser",
    "schemaVersion": 38,
    "version": 1,
    "refresh": "30s",
    
    "templating": {
      "list": [
        {
          "name": "host",
          "type": "query",
          "datasource": "Prometheus",
          "query": "label_values(lams_host_cpu_usage_percent, hostname)",
          "refresh": 1,
          "includeAll": false,
          "multi": false
        }
      ]
    },
    
    "panels": [
      {
        "title": "CPU Usage",
        "type": "timeseries",
        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "lams_host_cpu_usage_percent{hostname=\"$host\"}",
            "legendFormat": "CPU {{hostname}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "min": 0,
            "max": 100
          }
        }
      },
      
      {
        "title": "Memory Usage",
        "type": "timeseries",
        "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "lams_host_memory_usage_percent{hostname=\"$host\"}",
            "legendFormat": "Memory {{hostname}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "min": 0,
            "max": 100
          }
        }
      },
      
      {
        "title": "Disk Usage",
        "type": "gauge",
        "gridPos": {"x": 0, "y": 8, "w": 6, "h": 6},
        "targets": [
          {
            "expr": "lams_host_disk_usage_percent{hostname=\"$host\"}",
            "legendFormat": "Disk"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "min": 0,
            "max": 100,
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {"value": 0, "color": "green"},
                {"value": 70, "color": "yellow"},
                {"value": 85, "color": "red"}
              ]
            }
          }
        }
      },
      
      {
        "title": "Temperature",
        "type": "gauge",
        "gridPos": {"x": 6, "y": 8, "w": 6, "h": 6},
        "targets": [
          {
            "expr": "lams_host_temperature_celsius{hostname=\"$host\"}",
            "legendFormat": "CPU Temp"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "celsius",
            "min": 0,
            "max": 100,
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {"value": 0, "color": "green"},
                {"value": 70, "color": "yellow"},
                {"value": 85, "color": "red"}
              ]
            }
          }
        }
      },
      
      {
        "title": "Network Traffic",
        "type": "timeseries",
        "gridPos": {"x": 12, "y": 8, "w": 12, "h": 6},
        "targets": [
          {
            "expr": "rate(lams_host_network_receive_bytes_total{hostname=\"$host\"}[5m])",
            "legendFormat": "RX"
          },
          {
            "expr": "rate(lams_host_network_transmit_bytes_total{hostname=\"$host\"}[5m])",
            "legendFormat": "TX"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "Bps"
          }
        }
      },
      
      {
        "title": "Docker Containers",
        "type": "table",
        "gridPos": {"x": 0, "y": 14, "w": 24, "h": 8},
        "targets": [
          {
            "expr": "lams_docker_container_up{hostname=\"$host\"}",
            "format": "table",
            "instant": true
          }
        ],
        "transformations": [
          {
            "id": "organize",
            "options": {
              "excludeByName": {
                "Time": true,
                "job": true,
                "instance": true
              },
              "renameByName": {
                "container_name": "Container",
                "image": "Image",
                "Value": "Status"
              }
            }
          }
        ]
      }
    ]
  }
}
```

### 3.5 Dashboard JSON: Docker Containers

**Archivo:** `grafana/dashboards/lams-docker-containers.json`

```json
{
  "dashboard": {
    "title": "LAMS - Docker Containers",
    "uid": "lams-docker-containers",
    "tags": ["lams", "docker"],
    "timezone": "browser",
    "schemaVersion": 38,
    "version": 1,
    "refresh": "30s",
    
    "templating": {
      "list": [
        {
          "name": "host",
          "type": "query",
          "datasource": "Prometheus",
          "query": "label_values(lams_docker_container_up, hostname)",
          "refresh": 1,
          "includeAll": false,
          "multi": false
        },
        {
          "name": "container",
          "type": "query",
          "datasource": "Prometheus",
          "query": "label_values(lams_docker_container_up{hostname=\"$host\"}, container_name)",
          "refresh": 1,
          "includeAll": true,
          "multi": true
        }
      ]
    },
    
    "panels": [
      {
        "title": "Container CPU Usage",
        "type": "timeseries",
        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 10},
        "targets": [
          {
            "expr": "lams_docker_container_cpu_percent{hostname=\"$host\", container_name=~\"$container\"}",
            "legendFormat": "{{container_name}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent"
          }
        }
      },
      
      {
        "title": "Container Memory Usage",
        "type": "timeseries",
        "gridPos": {"x": 12, "y": 0, "w": 12, "h": 10},
        "targets": [
          {
            "expr": "lams_docker_container_memory_bytes{hostname=\"$host\", container_name=~\"$container\"}",
            "legendFormat": "{{container_name}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "bytes"
          }
        }
      },
      
      {
        "title": "Container Status",
        "type": "stat",
        "gridPos": {"x": 0, "y": 10, "w": 24, "h": 4},
        "targets": [
          {
            "expr": "lams_docker_container_up{hostname=\"$host\", container_name=~\"$container\"}",
            "legendFormat": "{{container_name}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "mappings": [
              {"type": "value", "options": {"0": {"text": "Stopped", "color": "red"}}},
              {"type": "value", "options": {"1": {"text": "Running", "color": "green"}}}
            ]
          }
        }
      }
    ]
  }
}
```

---

## Fase 4: Testing y Verificación

### 4.1 Levantar Stack Completo

```bash
cd /home/mloco/Escritorio/LAMS
docker-compose up -d
```

### 4.2 Verificar Endpoint Prometheus

```bash
# Verificar que el endpoint retorna métricas
curl http://localhost:8080/api/v1/metrics

# Debería retornar algo como:
# HELP lams_host_cpu_usage_percent CPU usage percentage
# TYPE lams_host_cpu_usage_percent gauge
# lams_host_cpu_usage_percent{host_id="zeus2",hostname="zeus2",ip="192.168.0.8"} 12.5
# lams_host_memory_usage_percent{host_id="zeus2",hostname="zeus2",ip="192.168.0.8"} 45.2
# ...
```

### 4.3 Verificar Prometheus UI

```bash
# Abrir navegador
xdg-open http://localhost:9090

# Verificar:
# 1. Status > Targets: lams-backend debe estar UP (1/1 up)
# 2. Graph: ejecutar query: lams_host_cpu_usage_percent
# 3. Ver gráfico con métricas reales
```

### 4.4 Verificar Grafana

```bash
# Abrir Grafana
xdg-open http://localhost:3002

# Login: admin / lams2024 (o contraseña de .env)

# Verificar:
# 1. Configuration > Data sources: Prometheus debe estar configurado
# 2. Dashboards > LAMS: debe haber 2 dashboards
# 3. Abrir "LAMS - Host Overview"
# 4. Seleccionar host en dropdown
# 5. Ver métricas en tiempo real
```

---

## Fase 5: Documentación

### 5.1 Actualizar README.md

Añadir sección:

```markdown
## 📊 Prometheus & Grafana Integration

LAMS exposes metrics in Prometheus format for advanced monitoring and visualization.

### Quick Start

1. **Start services:**
   ```bash
   docker-compose up -d
   ```

2. **Access dashboards:**
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3002 (admin/lams2024)

### Available Metrics

- `lams_host_cpu_usage_percent` - CPU usage by host
- `lams_host_memory_usage_percent` - Memory usage by host
- `lams_host_disk_usage_percent` - Disk usage by host
- `lams_host_temperature_celsius` - CPU temperature
- `lams_host_network_receive_bytes_total` - Network RX counter
- `lams_host_network_transmit_bytes_total` - Network TX counter
- `lams_docker_container_cpu_percent` - Docker CPU usage
- `lams_docker_container_memory_bytes` - Docker memory usage
- `lams_docker_container_up` - Docker container status

### Example Queries

```promql
# Average CPU usage across all hosts
avg(lams_host_cpu_usage_percent)

# Hosts with high memory usage
lams_host_memory_usage_percent > 80

# Total network traffic
sum(rate(lams_host_network_receive_bytes_total[5m]))

# Running containers count
count(lams_docker_container_up == 1)
```

### Custom Dashboards

Import dashboards from `grafana/dashboards/` or create your own using the Grafana UI.
```

### 5.2 Crear Guía de Queries

**Archivo:** `docs/PROMETHEUS_QUERIES.md`

```markdown
# Prometheus Queries for LAMS

## Host Metrics

### CPU
```promql
# Current CPU usage per host
lams_host_cpu_usage_percent

# Average CPU over 5 minutes
avg_over_time(lams_host_cpu_usage_percent[5m])

# Hosts with CPU > 80%
lams_host_cpu_usage_percent > 80

# CPU usage trend (rate of change)
deriv(lams_host_cpu_usage_percent[5m])
```

### Memory
```promql
# Current memory usage
lams_host_memory_usage_percent

# Available memory (inverse)
100 - lams_host_memory_usage_percent

# Host with highest memory usage
topk(1, lams_host_memory_usage_percent)

# Memory used in bytes
lams_host_memory_used_bytes
```

### Network
```promql
# Network receive rate (bytes/sec)
rate(lams_host_network_receive_bytes_total[5m])

# Network transmit rate (bytes/sec)
rate(lams_host_network_transmit_bytes_total[5m])

# Total bandwidth usage
rate(lams_host_network_receive_bytes_total[5m]) + 
rate(lams_host_network_transmit_bytes_total[5m])

# Convert to MB/s
(rate(lams_host_network_receive_bytes_total[5m]) / 1024 / 1024)
```

### Disk
```promql
# Disk usage by host
lams_host_disk_usage_percent

# Hosts with low disk space (<20% free)
lams_host_disk_usage_percent > 80

# Average disk usage across all hosts
avg(lams_host_disk_usage_percent)
```

## Docker Metrics

### Container Resources
```promql
# CPU usage per container
lams_docker_container_cpu_percent

# Memory usage per container (MB)
lams_docker_container_memory_bytes / 1024 / 1024

# Top 5 containers by CPU
topk(5, lams_docker_container_cpu_percent)

# Top 5 containers by memory
topk(5, lams_docker_container_memory_bytes)
```

### Container Status
```promql
# Number of running containers
count(lams_docker_container_up == 1)

# Number of stopped containers
count(lams_docker_container_up == 0)

# Total containers per host
count by (hostname) (lams_docker_container_up)

# Containers that went down recently
changes(lams_docker_container_up[10m]) > 0
```

## Alerts (Para Prometheus Alertmanager)

```yaml
groups:
  - name: lams_hosts
    rules:
      - alert: HighCPUUsage
        expr: lams_host_cpu_usage_percent > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU on {{ $labels.hostname }}"
          description: "CPU usage is {{ $value }}%"
      
      - alert: HighMemoryUsage
        expr: lams_host_memory_usage_percent > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory on {{ $labels.hostname }}"
          description: "Memory usage is {{ $value }}%"
      
      - alert: HostDown
        expr: lams_host_up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Host {{ $labels.hostname }} is down"
          description: "Host has been unreachable for 2 minutes"
      
      - alert: DockerContainerDown
        expr: lams_docker_container_up == 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Container {{ $labels.container_name }} is down"
          description: "Container on {{ $labels.hostname }} has been stopped"
```

## Aggregations

```promql
# Total CPU cores across all hosts
sum(lams_host_cpu_cores)

# Average CPU usage across cluster
avg(lams_host_cpu_usage_percent)

# Standard deviation of CPU usage
stddev(lams_host_cpu_usage_percent)

# Percentiles
quantile(0.95, lams_host_cpu_usage_percent)  # 95th percentile
quantile(0.50, lams_host_cpu_usage_percent)  # Median
```
```

---

## Resumen de Archivos Nuevos

**Backend:**
- ✅ `server/prometheus/__init__.py`
- ✅ `server/prometheus/exporter.py` (200+ líneas)
- ✅ `server/api/prometheus.py` (40 líneas)

**Configuración:**
- ✅ `prometheus/prometheus.yml`
- ✅ `grafana/provisioning/datasources/prometheus.yml`
- ✅ `grafana/provisioning/dashboards/dashboard.yml`
- ✅ `grafana/dashboards/lams-host-overview.json`
- ✅ `grafana/dashboards/lams-docker-containers.json`

**Documentación:**
- ✅ `docs/FASE4_4_PROMETHEUS_GRAFANA.md` (este archivo)
- ✅ `docs/PROMETHEUS_QUERIES.md`

**Modificaciones:**
- ✅ `server/requirements.txt` - Añadir prometheus-client
- ✅ `server/main.py` - Registrar router Prometheus
- ✅ `server/middleware/csrf.py` - Exentar /metrics
- ✅ `docker-compose.yml` - Añadir servicios Prometheus y Grafana
- ✅ `README.md` - Sección de Prometheus/Grafana

---

## Ventajas de Esta Integración

1. **Compatibilidad Estándar:** LAMS ahora es compatible con el stack de monitoring más usado (Prometheus + Grafana).

2. **Visualizaciones Avanzadas:** Grafana ofrece dashboards mucho más potentes que el frontend Next.js actual.

3. **Alerting Robusto:** Prometheus Alertmanager es más maduro que el sistema de alertas actual de LAMS.

4. **Queries Avanzadas:** PromQL permite análisis sofisticados (percentiles, predicciones, correlaciones).

5. **Escalabilidad:** Prometheus escala mejor para múltiples hosts y millones de métricas.

6. **Ecosistema:** Integración con Alertmanager, Thanos, Cortex, etc.

7. **Sin Duplicación:** El dashboard Next.js puede convivir con Grafana. Los usuarios eligen su herramienta preferida.

---

## Próximos Pasos Después de Fase 4.4

1. **Alertmanager:** Configurar Prometheus Alertmanager para alertas avanzadas
2. **Thanos:** Para retención de métricas a largo plazo (> 30 días)
3. **Service Discovery:** Auto-descubrimiento de hosts sin configuración manual
4. **Métricas Business:** Añadir métricas de aplicación (errores HTTP, latencias, etc.)

---

## Tiempo Estimado de Implementación

- Fase 1 (Backend): **1-2 días**
- Fase 2 (Prometheus): **0.5 días**
- Fase 3 (Grafana): **1-1.5 días**
- Fase 4 (Testing): **0.5 días**
- Fase 5 (Documentación): **0.5 días**

**Total: 4-5 días** ✅
