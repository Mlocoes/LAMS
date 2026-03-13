# Plan de Implementación: Funcionalidades Portainer en LAMS

## 📋 Resumen Ejecutivo

Este documento describe la implementación de funcionalidades similares a **Portainer** en el sistema **LAMS** (Linux Autonomous Monitoring System), transformándolo en una plataforma completa de gestión de contenedores distribuidos con capacidades de monitoreo avanzado.

### 🎯 Objetivo
Convertir LAMS en una solución que combine:
- **Monitoreo de infraestructura** (funcionalidad actual)
- **Gestión completa de Docker** (inspirada en Portainer)
- **Control remoto multi-host** de contenedores, imágenes, volúmenes y redes

### 📊 Estado Actual de LAMS

**✅ Funcionalidades Implementadas:**
- Gestión básica de contenedores (start/stop/restart)
- Visualización de contenedores activos
- Métricas de contenedores (CPU, memoria)
- Sistema de autenticación y autorización
- API REST con FastAPI
- Agente Go distribuido
- Dashboard Next.js

**❌ Funcionalidades Faltantes (vs Portainer):**
- Gestión completa de imágenes Docker
- Gestión de volúmenes y redes
- Gestión de stacks (docker-compose)
- Logs y consola interactiva de contenedores
- Inspección detallada de recursos Docker
- Templates/plantillas de aplicaciones
- Registry management
- Control de acceso granular por recursos

---

## 🔍 Análisis de Portainer: Funcionalidades Core

### 1. **Dashboard Global**
- Vista general de todos los nodos/endpoints
- Estadísticas agregadas: contenedores, imágenes, volúmenes, redes
- Estado de salud de cada endpoint
- Gráficos de recursos agregados

### 2. **Gestión de Contenedores**
- **Listado:** Filtros (estado, nombre, imagen), búsqueda, ordenamiento
- **Acciones:**
  - Start, Stop, Restart, Pause, Resume, Kill
  - Remove (con opciones: volumes, links)
  - Rename
  - Duplicate/Clone
  - Recreate (recrear con misma configuración)
- **Logs:** Live streaming, filtros, descarga
- **Inspect:** Todos los detalles del contenedor en JSON
- **Stats:** Gráficos en tiempo real de CPU, RAM, I/O
- **Console:** Terminal interactiva (exec)
- **Attach:** Conexión a STDOUT/STDERR

### 3. **Gestión de Imágenes**
- **Listado:** Todas las imágenes locales con tamaño, edad
- **Acciones:**
  - Pull (desde registry)
  - Push (a registry)
  - Remove (forzado, sin tag)
  - Build (desde Dockerfile)
  - Import/Export (tar)
  - Tag
- **Inspect:** Detalles completos (layers, history)
- **Registry Management:** Conexión a registries privados

### 4. **Gestión de Volúmenes**
- **Listado:** Todos los volúmenes con driver, mount point
- **Acciones:**
  - Create (con opciones personalizadas)
  - Remove (con advertencia de contenedores afectados)
  - Browse (explorar archivos)
- **Inspect:** Detalles y contenedores que lo usan

### 5. **Gestión de Redes**
- **Listado:** Todas las redes con driver, scope
- **Acciones:**
  - Create (bridge, host, overlay, macvlan)
  - Remove
  - Connect container
  - Disconnect container
- **Inspect:** Contenedores conectados, configuración

### 6. **Stacks (Docker Compose)**
- **Listado:** Todos los stacks desplegados
- **Acciones:**
  - Deploy (desde docker-compose.yml)
  - Update (redeploy con nuevos cambios)
  - Stop/Start stack completo
  - Remove
  - Editor de compose file
- **Logs:** Logs agregados de todos los servicios
- **Services:** Detalle por servicio del stack

### 7. **Templates/Plantillas**
- Biblioteca de aplicaciones pre-configuradas
- Deploy rápido (WordPress, MySQL, Nginx, etc.)
- Templates personalizados
- Variables de entorno configurables

### 8. **Usuarios y Control de Acceso**
- Roles: Admin, User, Read-only
- Permisos por endpoint
- Permisos por recurso (contenedores, volúmenes)
- Teams/Equipos con permisos compartidos
- Audit logs

### 9. **Endpoints/Nodos**
- Gestión de múltiples Docker hosts
- Conexión: Local socket, TCP, SSH
- Estado de salud de cada endpoint
- Snapshots de estado

### 10. **Registries**
- Gestión de registries (Docker Hub, privados)
- Autenticación
- Browse de imágenes disponibles

---

## 🗺️ Mapeo: Portainer → LAMS

| Funcionalidad Portainer | Estado en LAMS | Prioridad | Esfuerzo |
|-------------------------|----------------|-----------|----------|
| Dashboard global | ✅ Parcial (solo hosts) | 🔴 Alta | 3 días |
| Contenedores: start/stop/restart | ✅ Implementado | - | - |
| Contenedores: logs | ❌ No implementado | 🔴 Alta | 5 días |
| Contenedores: console/exec | ❌ No implementado | 🟡 Media | 7 días |
| Contenedores: inspect | ❌ No implementado | 🟢 Baja | 2 días |
| Contenedores: stats en tiempo real | ✅ Parcial (agent) | 🟡 Media | 3 días |
| Contenedores: remove/recreate | ❌ No implementado | 🟡 Media | 3 días |
| Imágenes: listado | ❌ No implementado | 🔴 Alta | 2 días |
| Imágenes: pull/remove | ❌ No implementado | 🔴 Alta | 4 días |
| Imágenes: build | ❌ No implementado | 🟢 Baja | 5 días |
| Imágenes: push a registry | ❌ No implementado | 🟢 Baja | 3 días |
| Volúmenes: CRUD | ❌ No implementado | 🟡 Media | 4 días |
| Volúmenes: browse files | ❌ No implementado | 🟢 Baja | 5 días |
| Redes: CRUD | ❌ No implementado | 🟡 Media | 4 días |
| Redes: connect/disconnect | ❌ No implementado | 🟡 Media | 3 días |
| Stacks: deploy/manage | ❌ No implementado | 🟡 Media | 10 días |
| Templates | ❌ No implementado | 🟢 Baja | 5 días |
| Control de acceso por recursos | ❌ No implementado | 🟢 Baja | 7 días |
| Registries management | ❌ No implementado | 🟢 Baja | 4 días |
| Audit logs sistema | ❌ No implementado | 🟡 Media | 4 días |
| Múltiples endpoints | ✅ Implementado (hosts) | - | - |

**Resumen:**
- **Alta prioridad:** 6 funcionalidades (19 días estimados)
- **Media prioridad:** 9 funcionalidades (52 días estimados)
- **Baja prioridad:** 6 funcionalidades (31 días estimados)
- **TOTAL:** ~102 días de desarrollo (estimación conservadora)

---

## 🏗️ Arquitectura de Implementación

### Cambios en el Backend (FastAPI)

#### 1. Nuevos Modelos de Base de Datos

```python
# server/database/models.py

class DockerImage(Base):
    __tablename__ = "docker_images"
    id = Column(String, primary_key=True)  # Image ID
    host_id = Column(String, ForeignKey("hosts.id"))
    repository = Column(String)
    tag = Column(String)
    size = Column(BigInteger)
    created_at = Column(DateTime)
    last_seen = Column(DateTime)
    
    host = relationship("Host")

class DockerVolume(Base):
    __tablename__ = "docker_volumes"
    name = Column(String, primary_key=True)
    host_id = Column(String, ForeignKey("hosts.id"))
    driver = Column(String)
    mountpoint = Column(String)
    created_at = Column(DateTime)
    last_seen = Column(DateTime)
    
    host = relationship("Host")

class DockerNetwork(Base):
    __tablename__ = "docker_networks"
    id = Column(String, primary_key=True)
    host_id = Column(String, ForeignKey("hosts.id"))
    name = Column(String)
    driver = Column(String)
    scope = Column(String)
    created_at = Column(DateTime)
    last_seen = Column(DateTime)
    
    host = relationship("Host")

class DockerStack(Base):
    __tablename__ = "docker_stacks"
    id = Column(Integer, primary_key=True)
    host_id = Column(String, ForeignKey("hosts.id"))
    name = Column(String)
    compose_content = Column(Text)
    status = Column(String)  # running, stopped, error
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    host = relationship("Host")
    user = relationship("User")

class DockerRegistry(Base):
    __tablename__ = "docker_registries"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    url = Column(String)
    username = Column(String, nullable=True)
    password_encrypted = Column(String, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime)
    
class ContainerTemplate(Base):
    __tablename__ = "container_templates"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(Text)
    icon = Column(String)
    compose_content = Column(Text)
    variables = Column(JSON)  # Environment variables to configure
    category = Column(String)
    created_at = Column(DateTime)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)  # container.start, image.pull, etc.
    resource_type = Column(String)  # container, image, volume, network
    resource_id = Column(String)
    host_id = Column(String, ForeignKey("hosts.id"))
    details = Column(JSON)
    success = Column(Boolean)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime)
    ip_address = Column(String)
    
    user = relationship("User")
    host = relationship("Host")
```

#### 2. Nuevos Endpoints API

```python
# server/api/images.py
@router.get("/{host_id}/images")
async def list_images(host_id: str) -> List[DockerImage]:
    """Listar todas las imágenes en un host"""

@router.post("/{host_id}/images/pull")
async def pull_image(host_id: str, image: str, tag: str = "latest"):
    """Hacer pull de una imagen desde registry"""

@router.delete("/{host_id}/images/{image_id}")
async def remove_image(host_id: str, image_id: str, force: bool = False):
    """Eliminar una imagen"""

@router.post("/{host_id}/images/build")
async def build_image(host_id: str, dockerfile: str, tag: str):
    """Construir imagen desde Dockerfile"""

# server/api/volumes.py
@router.get("/{host_id}/volumes")
async def list_volumes(host_id: str) -> List[DockerVolume]:
    """Listar todos los volúmenes"""

@router.post("/{host_id}/volumes")
async def create_volume(host_id: str, name: str, driver: str = "local"):
    """Crear un volumen"""

@router.delete("/{host_id}/volumes/{volume_name}")
async def remove_volume(host_id: str, volume_name: str):
    """Eliminar un volumen"""

# server/api/networks.py
@router.get("/{host_id}/networks")
async def list_networks(host_id: str) -> List[DockerNetwork]:
    """Listar todas las redes"""

@router.post("/{host_id}/networks")
async def create_network(host_id: str, name: str, driver: str = "bridge"):
    """Crear una red"""

@router.delete("/{host_id}/networks/{network_id}")
async def remove_network(host_id: str, network_id: str):
    """Eliminar una red"""

# server/api/stacks.py
@router.post("/{host_id}/stacks")
async def deploy_stack(host_id: str, name: str, compose_content: str):
    """Desplegar un stack desde docker-compose.yml"""

@router.get("/{host_id}/stacks")
async def list_stacks(host_id: str) -> List[DockerStack]:
    """Listar todos los stacks"""

@router.put("/{host_id}/stacks/{stack_id}")
async def update_stack(host_id: str, stack_id: int, compose_content: str):
    """Actualizar un stack"""

@router.delete("/{host_id}/stacks/{stack_id}")
async def remove_stack(host_id: str, stack_id: int):
    """Eliminar un stack"""

# server/api/containers_extended.py
@router.get("/{host_id}/containers/{container_id}/logs")
async def get_container_logs(
    host_id: str, 
    container_id: str,
    tail: int = 100,
    follow: bool = False
):
    """Obtener logs de contenedor (con streaming si follow=true)"""

@router.post("/{host_id}/containers/{container_id}/exec")
async def exec_command(host_id: str, container_id: str, cmd: List[str]):
    """Ejecutar comando en contenedor (retorna exec_id)"""

@router.get("/{host_id}/containers/{container_id}/inspect")
async def inspect_container(host_id: str, container_id: str):
    """Inspeccionar configuración completa del contenedor"""

@router.delete("/{host_id}/containers/{container_id}")
async def remove_container(
    host_id: str, 
    container_id: str,
    force: bool = False,
    volumes: bool = False
):
    """Eliminar contenedor"""

# server/api/templates.py
@router.get("/templates")
async def list_templates() -> List[ContainerTemplate]:
    """Listar todas las plantillas disponibles"""

@router.post("/templates/{template_id}/deploy")
async def deploy_from_template(
    template_id: int,
    host_id: str,
    variables: dict
):
    """Desplegar contenedor/stack desde plantilla"""

# server/api/registries.py
@router.get("/registries")
async def list_registries() -> List[DockerRegistry]:
    """Listar registries configurados"""

@router.post("/registries")
async def add_registry(name: str, url: str, username: str = None, password: str = None):
    """Añadir registry"""

# server/api/audit.py
@router.get("/audit")
async def get_audit_logs(
    user_id: int = None,
    action: str = None,
    start_date: datetime = None,
    limit: int = 100
):
    """Obtener logs de auditoría"""
```

### Cambios en el Agente (Go)

#### 1. Nuevas Funcionalidades Docker

```go
// agent/docker/images.go
func ListImages() ([]DockerImage, error)
func PullImage(image, tag string) error
func RemoveImage(imageID string, force bool) error
func BuildImage(dockerfile, tag string) error

// agent/docker/volumes.go
func ListVolumes() ([]DockerVolume, error)
func CreateVolume(name, driver string) error
func RemoveVolume(name string) error

// agent/docker/networks.go
func ListNetworks() ([]DockerNetwork, error)
func CreateNetwork(name, driver string) error
func RemoveNetwork(networkID string) error

// agent/docker/containers_extended.go
func GetContainerLogs(containerID string, tail int) (string, error)
func ExecCommand(containerID string, cmd []string) (string, error)
func InspectContainer(containerID string) (interface{}, error)
func RemoveContainer(containerID string, force, volumes bool) error

// agent/docker/compose.go
func DeployStack(name, composeContent string) error
func RemoveStack(name string) error
func GetStackStatus(name string) (string, error)
```

#### 2. Modificar Sync Periódico

```go
// agent/sync.go
func SyncAllResources() {
    // Sync existente
    SyncContainers()
    
    // Nuevos syncs
    SyncImages()
    SyncVolumes()
    SyncNetworks()
    SyncStacks()
}
```

### Cambios en el Frontend (Next.js)

#### 1. Nuevas Páginas

```
frontend/src/app/
├── hosts/
│   └── [id]/
│       ├── containers/      # Vista existente (mejorar)
│       ├── images/          # NUEVO
│       ├── volumes/         # NUEVO
│       ├── networks/        # NUEVO
│       └── stacks/          # NUEVO
├── templates/               # NUEVO
├── registries/              # NUEVO
└── audit/                   # NUEVO
```

#### 2. Nuevos Componentes

```typescript
// frontend/src/components/docker/
- ImagesList.tsx           // Listado de imágenes con acciones
- ImagePullDialog.tsx      // Modal para pull de imágenes
- VolumesList.tsx          // Listado de volúmenes
- NetworksList.tsx         // Listado de redes
- StackEditor.tsx          // Editor de docker-compose
- ContainerLogs.tsx        // Visor de logs con streaming
- ContainerConsole.tsx     // Terminal interactiva
- ContainerInspect.tsx     // Visor JSON de inspect
- TemplateGallery.tsx      // Galería de templates
- RegistryConfig.tsx       // Configuración de registries
- AuditLogViewer.tsx       // Visor de logs de auditoría
```

#### 3. Servicios API

```typescript
// frontend/src/lib/api.ts
export async function getImages(hostId: string): Promise<DockerImage[]>
export async function pullImage(hostId: string, image: string, tag: string)
export async function removeImage(hostId: string, imageId: string, force: boolean)

export async function getVolumes(hostId: string): Promise<DockerVolume[]>
export async function createVolume(hostId: string, name: string, driver: string)

export async function getNetworks(hostId: string): Promise<DockerNetwork[]>
export async function createNetwork(hostId: string, name: string, driver: string)

export async function getStacks(hostId: string): Promise<DockerStack[]>
export async function deployStack(hostId: string, name: string, composeContent: string)

export async function getContainerLogs(hostId: string, containerId: string, tail: number): Promise<string>
export async function execCommand(hostId: string, containerId: string, cmd: string[])

export async function getTemplates(): Promise<ContainerTemplate[]>
export async function deployTemplate(templateId: number, hostId: string, variables: Record<string, string>)

export async function getAuditLogs(filters: AuditFilters): Promise<AuditLog[]>
```

---

## 📅 Plan de Implementación por Fases

### **FASE 1: Gestión Completa de Contenedores** (2-3 semanas)

**Objetivo:** Completar todas las operaciones sobre contenedores existentes.

#### Tareas:
1. **Logs de Contenedores** (5 días)
   - Backend: Endpoint GET `/containers/{id}/logs` con streaming
   - Agente: Función `GetContainerLogs()` con tail y follow
   - Frontend: Componente `ContainerLogs.tsx` con auto-scroll
   - Tests: Unitarios y E2E para logs

2. **Inspect de Contenedores** (2 días)
   - Backend: Endpoint GET `/containers/{id}/inspect`
   - Agente: Función `InspectContainer()`
   - Frontend: Componente `ContainerInspect.tsx` con JSON viewer
   - Tests: Validación de estructura JSON

3. **Eliminar Contenedores** (3 días)
   - Backend: Endpoint DELETE `/containers/{id}` con opciones
   - Agente: Función `RemoveContainer(force, volumes)`
   - Frontend: Modal de confirmación con checkboxes
   - Tests: Casos edge (contenedor en uso, con volúmenes)

4. **Consola Interactiva** (7 días) 🔴 **COMPLEJO**
   - Backend: WebSocket para `docker exec` interactivo
   - Agente: PTY allocation para shell interactivo
   - Frontend: Componente `ContainerConsole.tsx` con xterm.js
   - Manejo de redimensionamiento de terminal
   - Tests: Comandos básicos (echo, ls, cat)

**Entregables:**
- ✅ CRUD completo de contenedores
- ✅ Logs en tiempo real
- ✅ Terminal interactiva funcional
- ✅ 30+ tests nuevos

---

### **FASE 2: Gestión de Imágenes** (2 semanas)

**Objetivo:** Permitir Pull, Push, Build y Remove de imágenes Docker.

#### Tareas:
1. **Listado de Imágenes** (2 días)
   - Modelo: `DockerImage` con campos completos
   - Backend: Endpoint GET `/images` con filtros
   - Agente: Sync periódico de imágenes cada 60s
   - Frontend: `ImagesList.tsx` con tabla ordenable

2. **Pull de Imágenes** (4 días)
   - Backend: Endpoint POST `/images/pull` con progress tracking
   - Agente: `PullImage()` con gestión de layers
   - Frontend: `ImagePullDialog.tsx` con barra de progreso
   - Command queue para operaciones largas
   - Tests: Pull desde Docker Hub y registry privado

3. **Remove de Imágenes** (2 días)
   - Backend: Endpoint DELETE `/images/{id}` con forzado
   - Agente: `RemoveImage(force)` con validación de uso
   - Frontend: Confirmación con advertencia de contenedores afectados
   - Tests: Casos con/sin contenedores dependientes

4. **Build de Imágenes** (5 días) 🔴 **COMPLEJO**
   - Backend: Endpoint POST `/images/build` con upload de contexto
   - Agente: `BuildImage()` con streaming de logs
   - Frontend: Editor de Dockerfile + upload de archivos
   - Progress tracking de build steps
   - Tests: Build simple (nginx custom)

**Entregables:**
- ✅ Gestión completa de imágenes
- ✅ Registry integration básico
- ✅ 25+ tests nuevos

---

### **FASE 3: Volúmenes y Redes** (2 semanas)

**Objetivo:** CRUD completo de volúmenes y redes Docker.

#### Tareas:
1. **Gestión de Volúmenes** (4 días)
   - Modelo: `DockerVolume`
   - Backend: CRUD endpoints `/volumes`
   - Agente: Sync + Create/Remove de volúmenes
   - Frontend: `VolumesList.tsx` + Modal de creación
   - Validación: Impedir borrado si está en uso
   - Tests: CRUD completo

2. **Gestión de Redes** (4 días)
   - Modelo: `DockerNetwork`
   - Backend: CRUD endpoints `/networks`
   - Agente: Soporte para bridge, host, overlay
   - Frontend: `NetworksList.tsx` con detalle de contenedores conectados
   - Acciones: Connect/Disconnect contenedor a red
   - Tests: CRUD + connect/disconnect

3. **Explorador de Volúmenes** (5 días) 🟡 **OPCIONAL**
   - Backend: Endpoint `/volumes/{name}/browse`
   - Agente: Listar archivos en mountpoint
   - Frontend: File browser simple con permisos readonly
   - Solo para debugging (lectura únicamente)

**Entregables:**
- ✅ CRUD de volúmenes y redes
- ✅ Validaciones de uso
- ✅ 20+ tests nuevos

---

### **FASE 4: Stacks (Docker Compose)** (2-3 semanas)

**Objetivo:** Deploy y gestión de aplicaciones multi-contenedor.

#### Tareas:
1. **Deploy de Stacks** (10 días) 🔴 **COMPLEJO**
   - Modelo: `DockerStack`
   - Backend: Endpoint POST `/stacks` con validación de YAML
   - Agente: Integración con `docker-compose` (binario o API)
   - Instalación automática de docker-compose en agente
   - Frontend: `StackEditor.tsx` con editor YAML + syntax highlight
   - Validación de compose file antes de deploy
   - Tests: Deploy de stack simple (nginx + redis)

2. **Gestión de Stacks** (5 días)
   - Backend: Endpoints para listar, update, remove stacks
   - Agente: `StopStack()`, `StartStack()`, `RemoveStack()`
   - Frontend: Lista de stacks con estado (running/stopped)
   - Logs agregados de todos los servicios del stack
   - Tests: Ciclo completo de stack lifecycle

**Entregables:**
- ✅ Deploy de stacks funcional
- ✅ Editor de compose
- ✅ Gestión de lifecycle
- ✅ 15+ tests nuevos

---

### **FASE 5: Templates y Registries** (1-2 semanas)

**Objetivo:** Simplificar deployment con templates pre-configurados.

#### Tareas:
1. **Sistema de Templates** (5 días)
   - Modelo: `ContainerTemplate`
   - Backend: CRUD de templates
   - Seed de templates populares (WordPress, MySQL, Nginx, Redis, MongoDB)
   - Frontend: `TemplateGallery.tsx` con cards visuales
   - Modal de configuración de variables
   - Deploy desde template → Stack
   - Tests: Deploy de 3 templates diferentes

2. **Gestión de Registries** (4 días)
   - Modelo: `DockerRegistry`
   - Backend: CRUD de registries con encriptación de passwords
   - Integración con pull/push de imágenes
   - Frontend: `RegistryConfig.tsx` para añadir/editar
   - Test de conexión a registry
   - Tests: Pull desde registry privado

**Entregables:**
- ✅ 10+ templates listos para usar
- ✅ Soporte para registries privados
- ✅ 12+ tests nuevos

---

### **FASE 6: Auditoría y Seguridad** (1 semana)

**Objetivo:** Trazabilidad completa de acciones y mejoras de seguridad.

#### Tareas:
1. **Sistema de Auditoría** (4 días)
   - Modelo: `AuditLog`
   - Middleware: Logging automático de todas las acciones de Docker
   - Backend: Endpoint GET `/audit` con filtros avanzados
   - Frontend: `AuditLogViewer.tsx` con timeline y filtros
   - Retención de logs: 90 días
   - Tests: Verificación de logging en acciones críticas

2. **Control de Acceso Granular** (7 días) 🟡 **OPCIONAL**
   - Modelo: `ResourcePermission`
   - Permisos por recurso: containers, images, volumes, networks
   - Roles: Admin (all), Operator (manage), Viewer (read-only)
   - Frontend: Gestión de permisos en Settings
   - Tests: Validación de permisos por role

**Entregables:**
- ✅ Audit trail completo
- ✅ Dashboard de auditoría
- ✅ 10+ tests nuevos

---

### **FASE 7: Dashboard Global Unificado** (1 semana)

**Objetivo:** Vista agregada estilo Portainer de todos los recursos.

#### Tareas:
1. **Dashboard Global** (3 días)
   - Backend: Endpoint GET `/dashboard/stats` con agregaciones
   - Estadísticas: Total containers/images/volumes/networks por host
   - Estado de salud: hosts online/offline, containers running/stopped
   - Frontend: Rediseño de página principal con cards de estadísticas
   - Gráficos: Distribución de recursos por host
   - Tests: Validación de agregaciones

2. **Endpoint Switcher** (2 días)
   - Frontend: Dropdown global para cambiar entre hosts
   - Persistencia de host seleccionado en localStorage
   - Navegación rápida entre hosts desde cualquier página

**Entregables:**
- ✅ Dashboard centralizado
- ✅ Navegación intuitiva multi-host

---

### **FASE 8: Optimización y Polish** (1 semana)

**Objetivo:** Mejoras de UX y performance.

#### Tareas:
1. **WebSockets para Actualizaciones** (3 días)
   - Backend: WebSocket server para push de actualizaciones
   - Eventos: container.started, container.stopped, image.pulled
   - Frontend: Cliente WebSocket para updates en tiempo real
   - Sin necesidad de polling constante

2. **Mejoras de UI** (2 días)
   - Loading states consistentes
   - Toasts de confirmación para acciones
   - Animaciones suaves
   - Dark mode optimizado

3. **Documentación** (2 días)
   - API docs actualizados
   - Guías de usuario para nuevas funcionalidades
   - Video demo de 5 minutos

**Entregables:**
- ✅ Sistema pulido y production-ready

---

## 📊 Resumen de Esfuerzo Estimado

| Fase | Duración | Complejidad | Dependencias |
|------|----------|-------------|--------------|
| Fase 1: Contenedores completos | 2-3 semanas | 🟡 Media-Alta | Ninguna |
| Fase 2: Imágenes | 2 semanas | 🟡 Media | Ninguna |
| Fase 3: Volúmenes/Redes | 2 semanas | 🟢 Baja-Media | Ninguna |
| Fase 4: Stacks | 2-3 semanas | 🔴 Alta | Fase 2 (imágenes) |
| Fase 5: Templates/Registries | 1-2 semanas | 🟢 Baja | Fase 2, 4 |
| Fase 6: Auditoría | 1 semana | 🟢 Baja | Ninguna |
| Fase 7: Dashboard Global | 1 semana | 🟢 Baja | Todas anteriores |
| Fase 8: Polish | 1 semana | 🟢 Baja | Todas anteriores |

**Total: 12-16 semanas** (3-4 meses para implementación completa)

**Enfoque MVP (Prioritario):**
- Fase 1 + Fase 2 + Fase 3 + Fase 7 = **7-9 semanas** para funcionalidad core

---

## 🎯 Priorización Recomendada

### **Sprint 1 (Semanas 1-3): Contenedores Completos**
1. Logs de contenedores ⭐⭐⭐⭐⭐
2. Inspect de contenedores ⭐⭐⭐⭐
3. Remove de contenedores ⭐⭐⭐⭐
4. Consola interactiva ⭐⭐⭐

### **Sprint 2 (Semanas 4-5): Imágenes**
1. Listado de imágenes ⭐⭐⭐⭐⭐
2. Pull de imágenes ⭐⭐⭐⭐⭐
3. Remove de imágenes ⭐⭐⭐⭐
4. Build de imágenes ⭐⭐⭐

### **Sprint 3 (Semanas 6-7): Volúmenes y Redes**
1. CRUD de volúmenes ⭐⭐⭐⭐
2. CRUD de redes ⭐⭐⭐⭐
3. Connect/Disconnect contenedores ⭐⭐⭐

### **Sprint 4 (Semanas 8-10): Stacks**
1. Deploy de stacks ⭐⭐⭐⭐
2. Gestión de stacks ⭐⭐⭐⭐

### **Sprint 5 (Semanas 11-12): Templates y Auditoría**
1. Sistema de templates ⭐⭐⭐
2. Audit logs ⭐⭐⭐
3. Dashboard global ⭐⭐⭐⭐

---

## 🔒 Consideraciones de Seguridad

1. **Autenticación:**
   - Todas las operaciones Docker requieren JWT válido
   - Validación de permisos por rol (admin/user)

2. **Validación de Inputs:**
   - Sanitización de nombres de imágenes/contenedores
   - Validación de docker-compose YAML (prevenir code injection)
   - Límites de tamaño para uploads

3. **Docker Socket Security:**
   - Agente accede a `/var/run/docker.sock` con permisos limitados
   - No exponer socket directamente al frontend
   - Todas las operaciones pasan por API backend

4. **Secrets Management:**
   - Passwords de registries encriptados en DB
   - Variables de entorno sensibles no almacenadas en plaintext
   - Usar sistema de secrets de Docker cuando esté disponible

5. **Rate Limiting:**
   - Límites en operaciones costosas (build, pull)
   - Queue de comandos para evitar sobrecarga

6. **Audit Trail:**
   - Registro de todas las operaciones críticas
   - Información de usuario, IP, timestamp

---

## 🧪 Estrategia de Testing

### Tests Unitarios
- Backend: 80%+ cobertura en nuevos endpoints
- Agente: Tests de funciones Docker con mock client
- Frontend: Tests de componentes con React Testing Library

### Tests de Integración
- E2E: Flujos completos por fase
  - Fase 1: Deploy contenedor → Ver logs → Exec comando → Remove
  - Fase 2: Pull imagen → Create container desde imagen → Remove
  - Fase 4: Deploy stack → Verificar servicios → Remove stack

### Tests de Performance
- Load testing de logs streaming (100+ líneas/segundo)
- Latencia de comandos remotos (<2 segundos)
- Rendering de listas grandes (1000+ contenedores)

### Tests de Seguridad
- Validación de permisos por endpoint
- Injection attacks en nombres/comandos
- Rate limiting funcional

---

## 📦 Dependencias Técnicas

### Backend (Python)
- `docker` (SDK de Python) - Validación local de compose
- `pyyaml` - Parsing de docker-compose files
- `aiofiles` - Upload asíncrono de archivos

### Agente (Go)
- `github.com/docker/docker` - API cliente Docker
- `github.com/docker/compose-go` - Parsing de compose
- Instalación de `docker-compose` CLI en hosts (fallback)

### Frontend (React/Next.js)
- `xterm` + `xterm-addon-fit` - Terminal interactiva
- `@monaco-editor/react` - Editor de YAML/Dockerfile
- `yaml` - Validación de sintaxis
- `react-json-view` - Visor de JSON para inspect

---

## 🚀 Métricas de Éxito

### Funcionales
- ✅ 100% de funcionalidades core de Portainer implementadas
- ✅ Paridad de features con Portainer Community Edition

### Técnicas
- ✅ API response time < 500ms (p95)
- ✅ Streaming de logs sin lag (<100ms latency)
- ✅ UI responsive en mobile/tablet
- ✅ 80%+ cobertura de tests

### Negocio/UX
- ✅ Reducción en tiempo de deployment (vs SSH manual)
- ✅ Usuarios pueden gestionar Docker sin CLI
- ✅ Trazabilidad completa (quien hizo qué y cuándo)

---

## 🎓 Recursos de Aprendizaje

### Portainer
- [Documentación Oficial](https://docs.portainer.io/)
- [Portainer GitHub](https://github.com/portainer/portainer)
- [API Reference](https://docs.portainer.io/api/api-reference)

### Docker Remote API
- [Docker Engine API](https://docs.docker.com/engine/api/)
- [Docker SDK for Go](https://pkg.go.dev/github.com/docker/docker)
- [Docker SDK for Python](https://docker-py.readthedocs.io/)

### WebSockets + Streaming
- [WebSockets en FastAPI](https://fastapi.tiangolo.com/advanced/websockets/)
- [Gorilla WebSocket](https://github.com/gorilla/websocket)
- [xterm.js Terminal](https://xtermjs.org/)

---

## 📝 Notas Finales

Este plan transforma LAMS en una solución completa de gestión de infraestructura containerizada, combinando:
- **Monitoreo avanzado** (capacidad actual de LAMS)
- **Gestión de contenedores** (similar a Portainer)
- **Multi-host management** (ventaja sobre Portainer standalone)

**Diferenciadores vs Portainer:**
1. ✅ Monitoreo de hosts no-Docker (CPU, RAM, disco)
2. ✅ Alertas proactivas de salud
3. ✅ Gestión unificada de infraestructura + contenedores
4. ✅ Agente ligero en Go (bajo overhead)

**Recomendación:**
Iniciar con **Sprint 1-3** (MVP de 7-9 semanas) para validar arquitectura y UX antes de invertir en funcionalidades avanzadas como Stacks y Templates.

---

## 📅 Cronograma Visual

```
Mes 1          Mes 2          Mes 3          Mes 4
|--------------|--------------|--------------|--------------|
[==== Sprint 1 ====]
  Contenedores
               [== Sprint 2 ==]
                 Imágenes
                              [== Sprint 3 ==]
                                Volúmenes/Redes
                                             [==== Sprint 4 ====]
                                               Stacks
                                                            [== Sprint 5 ==]
                                                              Templates/Audit
                                                                           [Polish]
```

---

**Documento creado el:** 13 de Marzo de 2026  
**Versión:** 1.0  
**Autor:** LAMS Development Team  
**Próxima revisión:** Tras completar Sprint 1
