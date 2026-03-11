# Prometheus Queries for LAMS

Esta guía contiene queries útiles de Prometheus para monitorizar tu infraestructura con LAMS.

## 📊 Métricas Disponibles

### Host Metrics
- `lams_host_cpu_usage_percent` - Uso de CPU por host (gauge)
- `lams_host_memory_usage_percent` - Uso de memoria por host (gauge)
- `lams_host_memory_total_bytes` - Memoria total en bytes (gauge)
- `lams_host_memory_used_bytes` - Memoria usada en bytes (gauge)
- `lams_host_disk_usage_percent` - Uso de disco por host (gauge)
- `lams_host_temperature_celsius` - Temperatura de CPU en Celsius (gauge)
- `lams_host_network_receive_bytes_total` - Total de bytes recibidos (counter)
- `lams_host_network_transmit_bytes_total` - Total de bytes transmitidos (counter)
- `lams_host_up` - Estado del host (1=online, 0=offline) (gauge)
- `lams_host_info` - Información del host (gauge)

### Docker Metrics
- `lams_docker_container_cpu_percent` - Uso de CPU por contenedor (gauge)
- `lams_docker_container_memory_bytes` - Uso de memoria por contenedor (gauge)
- `lams_docker_container_up` - Estado del contenedor (1=running, 0=stopped) (gauge)

## 🔍 Queries Básicas

### CPU

```promql
# Uso actual de CPU por host
lams_host_cpu_usage_percent

# Promedio de CPU en los últimos 5 minutos
avg_over_time(lams_host_cpu_usage_percent[5m])

# Hosts con CPU > 80%
lams_host_cpu_usage_percent > 80

# Host con mayor uso de CPU
topk(1, lams_host_cpu_usage_percent)

# Promedio de CPU en todos los hosts
avg(lams_host_cpu_usage_percent)

# Tendencia de CPU (derivada en 5m)
deriv(lams_host_cpu_usage_percent[5m])
```

### Memoria

```promql
# Uso actual de memoria por host
lams_host_memory_usage_percent

# Memoria disponible (inverso del uso)
100 - lams_host_memory_usage_percent

# Host con mayor uso de memoria
topk(1, lams_host_memory_usage_percent)

# Memoria usada en GB
lams_host_memory_used_bytes / 1024 / 1024 / 1024

# Memoria total disponible en GB
lams_host_memory_total_bytes / 1024 / 1024 / 1024

# Hosts con memoria crítica (>90%)
lams_host_memory_usage_percent > 90
```

### Disco

```promql
# Uso actual de disco por host
lams_host_disk_usage_percent

# Hosts con disco lleno (>85%)
lams_host_disk_usage_percent > 85

# Espacio libre en porcentaje
100 - lams_host_disk_usage_percent

# Host con menos espacio disponible
topk(1, lams_host_disk_usage_percent)
```

### Temperatura

```promql
# Temperatura actual de CPU por host
lams_host_temperature_celsius

# Hosts con temperatura alta (>70°C)
lams_host_temperature_celsius > 70

# Temperatura promedio en 10 minutos
avg_over_time(lams_host_temperature_celsius[10m])

# Host más caliente
topk(1, lams_host_temperature_celsius)
```

### Red

```promql
# Tasa de recepción (bytes/segundo) en últimos 5 minutos
rate(lams_host_network_receive_bytes_total[5m])

# Tasa de transmisión (bytes/segundo) en últimos 5 minutos
rate(lams_host_network_transmit_bytes_total[5m])

# Ancho de banda total (RX + TX) en Mbps
(rate(lams_host_network_receive_bytes_total[5m]) + 
 rate(lams_host_network_transmit_bytes_total[5m])) * 8 / 1000000

# Tráfico total recibido en GB desde el inicio
lams_host_network_receive_bytes_total / 1024 / 1024 / 1024

# Host con mayor tráfico de red
topk(1, rate(lams_host_network_receive_bytes_total[5m]) + 
         rate(lams_host_network_transmit_bytes_total[5m]))
```

## 🐳 Docker Queries

### Contenedores en Ejecución

```promql
# Número de contenedores running
count(lams_docker_container_up == 1)

# Número de contenedores stopped
count(lams_docker_container_up == 0)

# Contenedores por host
count by (hostname) (lams_docker_container_up)

# Lista de contenedores stopped
lams_docker_container_up == 0
```

### CPU de Contenedores

```promql
# Top 10 contenedores por uso de CPU
topk(10, lams_docker_container_cpu_percent)

# Contenedores con CPU > 50%
lams_docker_container_cpu_percent > 50

# Uso total de CPU de todos los contenedores
sum(lams_docker_container_cpu_percent)

# Uso promedio de CPU por contenedor
avg(lams_docker_container_cpu_percent)

# CPU por contenedor en un host específico
lams_docker_container_cpu_percent{hostname="zeus2"}
```

### Memoria de Contenedores

```promql
# Top 10 contenedores por uso de memoria
topk(10, lams_docker_container_memory_bytes)

# Memoria total usada por contenedores en GB
sum(lams_docker_container_memory_bytes) / 1024 / 1024 / 1024

# Contenedores con más de 1GB de memoria
lams_docker_container_memory_bytes > 1073741824

# Memoria promedio por contenedor en MB
avg(lams_docker_container_memory_bytes) / 1024 / 1024

# Contenedores de un host específico
lams_docker_container_memory_bytes{hostname="kronos"}
```

## 🚨 Queries de Alerta

### Alertas de CPU

```promql
# CPU alta sostenida (>80% por 5 minutos)
avg_over_time(lams_host_cpu_usage_percent[5m]) > 80

# Pico de CPU repentino (incremento >30% en 1 minuto)
delta(lams_host_cpu_usage_percent[1m]) > 30
```

### Alertas de Memoria

```promql
# Memoria crítica (>90%)
lams_host_memory_usage_percent > 90

# Memoria creciendo rápidamente
deriv(lams_host_memory_usage_percent[5m]) > 2
```

### Alertas de Disco

```promql
# Disco casi lleno (>85%)
lams_host_disk_usage_percent > 85

# Disco crítico (>95%)
lams_host_disk_usage_percent > 95
```

### Alertas de Temperatura

```promql
# Temperatura alta (>75°C)
lams_host_temperature_celsius > 75

# Temperatura crítica (>85°C)
lams_host_temperature_celsius > 85
```

### Alertas de Contenedores

```promql
# Contenedor caído inesperadamente
changes(lams_docker_container_up[5m]) > 0 and lams_docker_container_up == 0

# Demasiados contenedores detenidos
count(lams_docker_container_up == 0) > 5

# Contenedor usando demasiada CPU
lams_docker_container_cpu_percent > 90
```

## 📈 Queries Avanzadas

### Análisis de Tendencias

```promql
# Predicción de llenado de disco (días hasta lleno)
predict_linear(lams_host_disk_usage_percent[24h], 86400 * 7) > 100

# Tasa de cambio de memoria en 1 hora
rate(lams_host_memory_used_bytes[1h])

# Variación de temperatura
stddev_over_time(lams_host_temperature_celsius[30m])
```

### Agregaciones

```promql
# CPU total del cluster
sum(lams_host_cpu_usage_percent) / count(lams_host_cpu_usage_percent)

# Memoria total usada en el cluster (GB)
sum(lams_host_memory_used_bytes) / 1024 / 1024 / 1024

# Capacidad total del cluster (GB)
sum(lams_host_memory_total_bytes) / 1024 / 1024 / 1024

# Contenedores por imagen
count by (image) (lams_docker_container_up == 1)
```

### Comparaciones

```promql
# Diferencia de CPU entre hosts
lams_host_cpu_usage_percent{hostname="zeus2"} - 
lams_host_cpu_usage_percent{hostname="kronos"}

# Ratio de memoria usada vs total
lams_host_memory_used_bytes / lams_host_memory_total_bytes * 100
```

## 🎯 Recording Rules

Para optimizar queries frecuentes, puedes crear recording rules:

```yaml
groups:
  - name: lams_aggregations
    interval: 30s
    rules:
      - record: lams:cluster_cpu_avg
        expr: avg(lams_host_cpu_usage_percent)
      
      - record: lams:cluster_memory_avg
        expr: avg(lams_host_memory_usage_percent)
      
      - record: lams:containers_running_total
        expr: count(lams_docker_container_up == 1)
      
      - record: lams:network_total_mbps
        expr: |
          sum(rate(lams_host_network_receive_bytes_total[5m]) + 
              rate(lams_host_network_transmit_bytes_total[5m])) * 8 / 1000000
```

## 📚 Funciones Útiles

- `rate()` - Tasa de cambio por segundo (para counters)
- `irate()` - Tasa instantánea (para counters)
- `increase()` - Incremento total en un rango
- `deriv()` - Derivada (pendiente de cambio)
- `predict_linear()` - Predicción lineal
- `avg_over_time()` - Promedio en un rango
- `max_over_time()` - Máximo en un rango
- `min_over_time()` - Mínimo en un rango
- `stddev_over_time()` - Desviación estándar
- `delta()` - Diferencia entre primer y último valor
- `changes()` - Número de cambios de valor
- `topk(n, ...)` - Top N valores
- `bottomk(n, ...)` - Bottom N valores
- `sum by (label)` - Suma agrupada por label
- `count by (label)` - Conteo agrupado por label

## 🔗 Referencias

- [Prometheus Query Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Prometheus Functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [PromQL Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
