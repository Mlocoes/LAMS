# API Rest de LAMS Central Server

El backend LAMS, expuesto en el puerto `8000` proveé los siguientes Endpoints clave para la integración de agentes y tableros. Todo endpoint comienza con `/api/v1`.

### Autenticación (`/api/v1/auth`)
Para interfaces y tableros, usa Autenticación JWT y password hashing `Argon2`.
- `POST /auth/login` - Obtiene Bearer token (FormData: username, password).
- `GET /auth/me` - Retorna la identidad de la sesión.

### Hosts (`/api/v1/hosts`)
- `POST /hosts/register` - Endpoint para Agentes. Registra la metadata inicial del Hardware y levanta el estado general.
- `GET /hosts/` - Obtiene lista de máquinas con estado Actualizado / "Last Seen".
- `GET /hosts/{id}` - Detalles de una máquina.
- `DELETE /hosts/{id}` - Elimina un host y todos sus datos asociados (métricas, alertas, contenedores, reglas). Requiere autenticación. Retorna 204 si éxito, 404 si no existe.

### Métricas (`/api/v1/metrics`)
- `POST /metrics/` - Ingresa el frame JSON de telemetría (CPU, RAM, Disco, Red) al bloque TSDB de Postgres.
- `GET /metrics/{host_id}` - Obtiene los ultimos 100 fragmentos de telemetría del host ordenados para *ECharts*.

### Alertas (`/api/v1/alerts`)
- `GET /alerts/` - Recuperar alarmas con filtro (resolved=false/true).
- `POST /alerts/{id}/resolve` - Acuse de recibo de una alerta disparada por el Motor en Background (`APScheduler`).

### Docker (`/api/v1/docker`)
- `POST /docker/sync` - Endpoint para Agentes. Sincroniza y actualiza todos los `containers` hallados por el agente (estado, id, uso CPU).
- `GET /docker/{host_id}` - Obtiene los contenedores mapeados.
- `POST /docker/{host_id}/containers/{container_id}/action` (Mock) - Interfaz de mando para encender/apagar contenedores distribuidos.

### Mantenimiento (`/api/v1/maintenance`)
Endpoints administrativos para gestión de retención de datos. Requieren autenticación con rol Admin.
- `POST /maintenance/run` - Ejecuta el job completo de mantenimiento (agregación + limpieza).
- `POST /maintenance/aggregate` - Agrega métricas antiguas (>7 días) en resúmenes horarios.
- `POST /maintenance/cleanup` - Elimina métricas muy antiguas (>30 días).
