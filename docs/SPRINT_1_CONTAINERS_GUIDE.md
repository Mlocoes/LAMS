# Sprint 1: Gestión Completa de Contenedores - Guía de Implementación

## 🎯 Objetivo del Sprint

Completar todas las operaciones sobre contenedores Docker, añadiendo:
1. ✅ Logs de contenedores (con streaming)
2. ✅ Inspect de contenedores (vista JSON completa)
3. ✅ Eliminar contenedores (con opciones)
4. ✅ Consola interactiva (terminal en navegador)

**Duración estimada:** 2-3 semanas  
**Prioridad:** 🔴 Alta

---

## 📋 Checklist de Tareas

### Fase 1.1: Logs de Contenedores (Días 1-5)

#### Backend
- [ ] Crear endpoint `GET /api/v1/containers/{host_id}/{container_id}/logs`
  - Parámetros: `tail` (int), `since` (timestamp), `follow` (bool)
  - Response: JSON con array de líneas o Stream
- [ ] Crear WebSocket endpoint `/ws/containers/{host_id}/{container_id}/logs`
  - Streaming en tiempo real
  - Manejo de conexión/desconexión
- [ ] Implementar sistema de pub/sub para logs
  - Redis (opcional) o almacenamiento en memoria
- [ ] Tests unitarios (≥80% cobertura)

#### Agente (Go)
- [ ] Implementar `GetContainerLogs(containerID, tail, follow)`
  - Usar `docker.ContainerLogs()` de SDK
  - Soporte para streaming
- [ ] Crear goroutine para streaming continuo
  - Push periódico a servidor (cada 1s con batch)
- [ ] Manejo de errores y reconexión
- [ ] Tests con contenedor de prueba

#### Frontend
- [ ] Componente `ContainerLogs.tsx`
  - Conexión WebSocket
  - Renderizado de logs con virtualización (para miles de líneas)
  - Auto-scroll configurable
  - Búsqueda/filtrado en cliente
  - Botón de descarga (`logs.txt`)
  - Botón de limpiar
- [ ] Integración en `HostDetailPage`
  - Botón "View Logs" en cada contenedor
  - Modal/Sidebar para logs viewer
- [ ] Tests E2E con Playwright

**Archivos a crear:**
```
server/api/containers_logs.py
server/api/websockets.py
agent/docker/logs.go
frontend/src/components/docker/ContainerLogs.tsx
frontend/src/components/docker/ContainerLogs.module.css
tests/test_container_logs.py
tests/e2e/container_logs.spec.ts
```

**Criterios de aceptación:**
- ✅ Logs se muestran en tiempo real con latencia <500ms
- ✅ Soporte para al menos 10,000 líneas sin lag
- ✅ Descarga de logs funciona correctamente
- ✅ WebSocket se reconecta automáticamente si falla

---

### Fase 1.2: Inspect de Contenedores (Días 6-7)

#### Backend
- [ ] Crear endpoint `GET /api/v1/containers/{host_id}/{container_id}/inspect`
  - Response: JSON completo del contenedor
  - Incluir: Config, State, NetworkSettings, Mounts, etc.
- [ ] Tests unitarios

#### Agente (Go)
- [ ] Implementar `InspectContainer(containerID)`
  - Usar `docker.ContainerInspect()`
  - Serializar a JSON
- [ ] Tests

#### Frontend
- [ ] Componente `ContainerInspect.tsx`
  - JSON viewer con syntax highlighting
  - Árbol colapsable por secciones
  - Búsqueda en JSON
  - Botón de copiar
  - Botón de descarga
- [ ] Usar librería: `react-json-view` o similar
- [ ] Integración en `HostDetailPage`
  - Botón "Inspect" en cada contenedor
- [ ] Tests E2E

**Archivos a crear:**
```
server/api/containers_inspect.py
agent/docker/inspect.go
frontend/src/components/docker/ContainerInspect.tsx
tests/test_container_inspect.py
tests/e2e/container_inspect.spec.ts
```

**Criterios de aceptación:**
- ✅ JSON completo se muestra correctamente
- ✅ Todas las secciones son navegables
- ✅ Búsqueda funciona en todo el JSON
- ✅ Performance fluida con JSONs grandes (>100KB)

---

### Fase 1.3: Eliminar Contenedores (Días 8-10)

#### Backend
- [ ] Crear endpoint `DELETE /api/v1/containers/{host_id}/{container_id}`
  - Query params: `force` (bool), `volumes` (bool)
  - Response: command_id para tracking
- [ ] Validaciones:
  - Contenedor existe
  - Permisos de usuario
- [ ] Audit log automático
- [ ] Tests

#### Agente (Go)
- [ ] Implementar `RemoveContainer(containerID, force, volumes)`
  - Usar `docker.ContainerRemove()`
  - Opciones: RemoveVolumes, Force
- [ ] Manejo de errores:
  - Contenedor en ejecución (sin force)
  - Permisos
- [ ] Tests

#### Frontend
- [ ] Modal de confirmación
  - Checkbox "Force remove"
  - Checkbox "Remove volumes"
  - Advertencia si contenedor está running
- [ ] Actualización de lista tras eliminar
- [ ] Loading state durante eliminación
- [ ] Toast de confirmación/error
- [ ] Tests E2E

**Archivos a modificar/crear:**
```
server/api/containers.py (añadir DELETE)
agent/docker/containers.go (añadir RemoveContainer)
frontend/src/app/hosts/[id]/page.tsx (añadir botón Delete)
frontend/src/components/docker/DeleteContainerModal.tsx
tests/test_container_delete.py
tests/e2e/container_delete.spec.ts
```

**Criterios de aceptación:**
- ✅ No permite eliminar contenedor running sin force
- ✅ Advertencia clara si tiene volúmenes
- ✅ Lista se actualiza inmediatamente tras eliminar
- ✅ Audit log registra quién eliminó qué y cuándo

---

### Fase 1.4: Consola Interactiva (Días 11-17) 🔴 **COMPLEJO**

#### Backend
- [ ] Crear WebSocket endpoint `/ws/containers/{host_id}/{container_id}/exec`
  - Bidireccional: enviar comandos, recibir output
  - Soporte para PTY (pseudo-terminal)
  - Manejo de redimensionamiento de terminal
- [ ] Sistema de sesiones exec
  - Crear exec instance
  - Attach a stdin/stdout/stderr
  - Resize terminal
  - Detach y cleanup
- [ ] Seguridad:
  - Validar permisos de usuario
  - Rate limiting (max 100 comandos/minuto)
  - Timeout de inactividad (5 minutos)
- [ ] Tests con simulación de comandos

#### Agente (Go)
- [ ] Implementar `ExecCreate(containerID, cmd, tty)`
  - Usar `docker.ContainerExecCreate()`
  - Opciones: AttachStdin, AttachStdout, Tty
- [ ] Implementar `ExecAttach(execID, stdin, stdout, stderr)`
  - Streaming bidireccional
  - Manejo de señales (Ctrl+C, Ctrl+D)
- [ ] Implementar `ExecResize(execID, height, width)`
  - Ajustar tamaño de PTY
- [ ] Goroutine para mantener conexión
- [ ] Tests

#### Frontend
- [ ] Componente `ContainerConsole.tsx`
  - **Librería:** `xterm` + `xterm-addon-fit`
  - Terminal completa en navegador
  - Soporte para colores ANSI
  - Historial de comandos (↑/↓)
  - Copy/Paste
  - Redimensionable
- [ ] WebSocket bidireccional
  - Enviar input del usuario
  - Recibir output y renderizar en xterm
  - Enviar resize events
- [ ] Manejo de estados:
  - Connecting
  - Connected
  - Disconnected
  - Error
- [ ] Botón "Disconnect" y cleanup
- [ ] Tests E2E (comandos básicos: echo, ls, pwd)

**Archivos a crear:**
```
server/api/containers_exec.py
server/websockets/exec.py
agent/docker/exec.go
frontend/src/components/docker/ContainerConsole.tsx
frontend/src/hooks/useTerminal.ts
frontend/package.json (añadir xterm dependencies)
tests/test_container_exec.py
tests/e2e/container_console.spec.ts
```

**Dependencias Frontend:**
```bash
npm install xterm xterm-addon-fit xterm-addon-web-links @types/xterm
```

**Criterios de aceptación:**
- ✅ Terminal interactiva funciona con bash/sh
- ✅ Comandos básicos funcionan (ls, cat, echo, cd)
- ✅ Copy/paste funciona correctamente
- ✅ Resize de terminal ajusta correctamente
- ✅ Se desconecta limpiamente sin memory leaks
- ✅ Timeout de inactividad funciona (5 min)

---

## 🛠️ Configuración del Entorno

### 1. Instalar Dependencias

**Backend:**
```bash
cd server
pip install redis  # Para pub/sub de logs (opcional)
pip install pytest pytest-asyncio pytest-cov
```

**Agente:**
```bash
cd agent
go get github.com/docker/docker/api/types
go get github.com/docker/docker/client
go get github.com/gorilla/websocket
```

**Frontend:**
```bash
cd frontend
npm install xterm xterm-addon-fit xterm-addon-web-links
npm install @types/xterm --save-dev
npm install react-json-view  # Para inspect viewer
```

### 2. Variables de Entorno

Añadir a `.env`:
```bash
# WebSocket Configuration
WS_HOST=0.0.0.0
WS_PORT=8080
WS_MAX_CONNECTIONS=100

# Logs Configuration
LOGS_BUFFER_SIZE=1000
LOGS_STREAM_INTERVAL=1  # seconds

# Exec Configuration
EXEC_TIMEOUT=300  # 5 minutes
EXEC_RATE_LIMIT=100  # commands per minute
```

### 3. Base de Datos Migrations

```bash
cd server
alembic revision -m "add_extended_container_fields"
alembic upgrade head
```

---

## 📝 Código de Ejemplo: Inicio Rápido

### Backend: Logs Endpoint

```python
# server/api/containers_logs.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

router = APIRouter()

@router.get("/{host_id}/containers/{container_id}/logs")
async def get_container_logs(
    host_id: str,
    container_id: str,
    tail: int = 100,
    since: Optional[int] = None,
    db = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Get logs from a container.
    
    Args:
        tail: Number of lines from end (default 100)
        since: Unix timestamp to show logs since
    """
    # Create command for agent
    command = RemoteCommand(
        host_id=host_id,
        command_type="container.logs",
        parameters={
            "container_id": container_id,
            "tail": tail,
            "since": since
        },
        status="pending"
    )
    db.add(command)
    await db.commit()
    
    # Wait for result (with timeout)
    import asyncio
    for _ in range(30):  # 30 seconds timeout
        await asyncio.sleep(1)
        await db.refresh(command)
        
        if command.status == "completed":
            return {"logs": command.result["logs"]}
        elif command.status == "failed":
            raise HTTPException(500, detail=command.error_message)
    
    raise HTTPException(504, detail="Timeout waiting for logs")
```

### Agente: Logs Implementation

```go
// agent/docker/logs.go
package docker

import (
    "context"
    "io"
    "bufio"
    
    "github.com/docker/docker/api/types"
    "github.com/docker/docker/client"
)

func GetContainerLogs(containerID string, tail int) ([]string, error) {
    cli, err := client.NewClientWithOpts(client.FromEnv)
    if err != nil {
        return nil, err
    }
    defer cli.Close()

    ctx := context.Background()
    options := types.ContainerLogsOptions{
        ShowStdout: true,
        ShowStderr: true,
        Tail:       fmt.Sprintf("%d", tail),
    }
    
    reader, err := cli.ContainerLogs(ctx, containerID, options)
    if err != nil {
        return nil, err
    }
    defer reader.Close()

    var logs []string
    scanner := bufio.NewScanner(reader)
    for scanner.Scan() {
        logs = append(logs, scanner.Text())
    }
    
    return logs, scanner.Err()
}
```

### Frontend: Logs Viewer Básico

```typescript
// frontend/src/components/docker/ContainerLogs.tsx
'use client';

import { useEffect, useState } from 'react';

export function ContainerLogs({ hostId, containerId }) {
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchLogs() {
      try {
        const response = await fetch(
          `/api/v1/containers/${hostId}/${containerId}/logs?tail=100`
        );
        const data = await response.json();
        setLogs(data.logs);
      } catch (error) {
        console.error('Failed to fetch logs:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchLogs();
  }, [hostId, containerId]);

  if (loading) return <div>Loading logs...</div>;

  return (
    <div className="logs-container">
      {logs.map((line, index) => (
        <div key={index} className="log-line">
          {line}
        </div>
      ))}
    </div>
  );
}
```

---

## 🧪 Testing Strategy

### Tests Unitarios (Backend)

```python
# tests/test_container_logs.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_logs_success(client: AsyncClient, auth_headers):
    response = await client.get(
        "/api/v1/containers/host1/container1/logs?tail=10",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert isinstance(data["logs"], list)

@pytest.mark.asyncio
async def test_get_logs_invalid_container(client: AsyncClient, auth_headers):
    response = await client.get(
        "/api/v1/containers/host1/invalid/logs",
        headers=auth_headers
    )
    assert response.status_code == 404
```

### Tests E2E (Frontend)

```typescript
// tests/e2e/container_logs.spec.ts
import { test, expect } from '@playwright/test';

test('view container logs', async ({ page }) => {
  await page.goto('/hosts/host1');
  
  // Click on "View Logs" button
  await page.click('button:has-text("View Logs")');
  
  // Wait for logs modal to appear
  await expect(page.locator('.logs-container')).toBeVisible();
  
  // Verify logs are displayed
  await expect(page.locator('.log-line')).toHaveCount(10, { timeout: 5000 });
  
  // Test download button
  const downloadPromise = page.waitForEvent('download');
  await page.click('button:has-text("Download")');
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain('.txt');
});
```

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] Todos los tests pasan (unitarios + E2E)
- [ ] Cobertura de tests ≥80%
- [ ] Code review completado
- [ ] Documentación actualizada
- [ ] Changelog actualizado

### Database Migration
- [ ] Backup de base de datos realizado
- [ ] Migration testeada en staging
- [ ] Rollback plan documentado

### Deployment
- [ ] Backend desplegado
- [ ] Agente actualizado en todos los hosts
- [ ] Frontend desplegado
- [ ] Health checks pasando
- [ ] Monitoreo de errores activo

### Post-Deployment
- [ ] Tests de smoke en producción
- [ ] Verificar logs de errores
- [ ] Monitorear performance (latencia, uso de recursos)
- [ ] Comunicar nuevas features a usuarios

---

## 📊 Métricas de Éxito

### Performance
- API response time (logs endpoint): < 2s para 100 líneas
- WebSocket latency: < 200ms
- Terminal interactiva: < 100ms input delay

### Cobertura
- Backend: ≥80% cobertura de tests
- Agente: ≥70% cobertura de tests
- E2E: 100% de flujos críticos cubiertos

### Usabilidad
- Usuarios pueden ver logs de cualquier contenedor en <3 clicks
- Terminal interactiva funciona en ≥95% de contenedores
- Tasa de errores < 1%

---

## 🐛 Troubleshooting

### Problema: Logs no se actualizan en tiempo real

**Síntomas:** Logs solo aparecen al refrescar página

**Solución:**
1. Verificar WebSocket está conectado:
   ```javascript
   console.log(ws.readyState); // Debe ser 1 (OPEN)
   ```
2. Verificar agente está enviando logs:
   ```bash
   journalctl -u lams-agent -f | grep logs
   ```
3. Verificar backend está recibiendo logs:
   ```bash
   docker logs lams-server | grep "log line received"
   ```

### Problema: Terminal interactiva no responde

**Síntomas:** Input en terminal no hace nada

**Solución:**
1. Verificar PTY está habilitado en exec:
   ```python
   exec_options = types.ExecConfig(
       Tty=True,  # ← Debe estar en True
       AttachStdin=True
   )
   ```
2. Verificar WebSocket bidireccional:
   ```javascript
   ws.send(JSON.stringify({ type: 'input', data: 'ls\n' }));
   ```
3. Logs del agente:
   ```bash
   tail -f /var/log/lams-agent.log | grep exec
   ```

---

## 📚 Recursos

### Documentación
- [Docker API - Container Logs](https://docs.docker.com/engine/api/v1.41/#operation/ContainerLogs)
- [Docker API - Container Exec](https://docs.docker.com/engine/api/v1.41/#operation/ContainerExec)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [xterm.js Documentation](https://xtermjs.org/)

### Librerías
- [Docker SDK for Go](https://pkg.go.dev/github.com/docker/docker)
- [xterm.js](https://github.com/xtermjs/xterm.js)
- [react-json-view](https://github.com/mac-s-g/react-json-view)

---

## ✅ Definition of Done

Sprint 1 está completado cuando:

1. ✅ **Logs de Contenedores:**
   - Endpoint funcional con ≥80% cobertura
   - WebSocket streaming en tiempo real
   - UI con auto-scroll, búsqueda y descarga

2. ✅ **Inspect de Contenedores:**
   - Endpoint retorna JSON completo
   - UI muestra árbol navegable
   - Tests E2E pasando

3. ✅ **Eliminar Contenedores:**
   - Endpoint con opciones force/volumes
   - Validaciones correctas
   - Audit log registrado
   - UI con confirmación clara

4. ✅ **Consola Interactiva:**
   - WebSocket bidireccional funcional
   - Terminal xterm.js integrada
   - Comandos básicos funcionan (ls, cat, echo)
   - Timeout y cleanup correctos

5. ✅ **Calidad:**
   - Todos los tests pasan (unitarios + E2E)
   - Cobertura ≥80% backend, ≥70% agente
   - Code review aprobado
   - Documentación actualizada

6. ✅ **Deployment:**
   - Desplegado en staging y validado
   - Desplegado en producción
   - Health checks OK

---

**Última actualización:** 13 de Marzo de 2026  
**Versión:** 1.0  
**Responsable:** LAMS Development Team

**Próximo Sprint:** [Sprint 2 - Gestión de Imágenes](./SPRINT_2_IMAGES.md)
