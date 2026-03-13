# Arquitectura Técnica Detallada: Portainer Features en LAMS

## 📐 Índice

1. [Diagrama de Arquitectura](#diagrama-de-arquitectura)
2. [Flujo de Datos](#flujo-de-datos)
3. [Estructura de Base de Datos](#estructura-de-base-de-datos)
4. [Implementación por Componente](#implementación-por-componente)
5. [Ejemplos de Código](#ejemplos-de-código)
6. [WebSockets y Streaming](#websockets-y-streaming)
7. [Sistema de Comandos Remotos](#sistema-de-comandos-remotos)
8. [Seguridad y Autenticación](#seguridad-y-autenticación)

---

## 🏛️ Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Dashboard │  │Containers│  │  Images  │  │ Volumes  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │              │              │              │
│       └─────────────┴──────────────┴──────────────┘              │
│                         │                                        │
│                    REST API / WebSocket                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTPS/WSS
                         │
┌────────────────────────┴────────────────────────────────────────┐
│                   BACKEND (FastAPI)                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ API Layer                                                 │  │
│  │  /containers  /images  /volumes  /networks  /stacks      │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────┴───────────────────────────────┐  │
│  │ Business Logic                                            │  │
│  │  - Command Queue Manager                                 │  │
│  │  - Audit Logger                                           │  │
│  │  - Permission Validator                                   │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────┴───────────────────────────────┐  │
│  │ Database Layer (PostgreSQL)                               │  │
│  │  - Hosts, Containers, Images, Volumes, Networks          │  │
│  │  - Stacks, Templates, Registries, AuditLogs              │  │
│  └──────────────────────────┬───────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                         Command Queue
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Agent Host 1 │     │  Agent Host 2 │     │  Agent Host N │
│               │     │               │     │               │
│  ┌─────────┐  │     │  ┌─────────┐  │     │  ┌─────────┐  │
│  │Go Agent │  │     │  │Go Agent │  │     │  │Go Agent │  │
│  └────┬────┘  │     │  └────┬────┘  │     │  └────┬────┘  │
│       │       │     │       │       │     │       │       │
│       │       │     │       │       │     │       │       │
│  ┌────▼────┐  │     │  ┌────▼────┐  │     │  ┌────▼────┐  │
│  │ Docker  │  │     │  │ Docker  │  │     │  │ Docker  │  │
│  │ Daemon  │  │     │  │ Daemon  │  │     │  │ Daemon  │  │
│  └─────────┘  │     │  └─────────┘  │     │  └─────────┘  │
└───────────────┘     └───────────────┘     └───────────────┘
```

---

## 🔄 Flujo de Datos

### Flujo 1: Sincronización Periódica (Polling)

```
Agent (Go)                Server (FastAPI)              Database
    │                           │                           │
    │ ── GET /commands/pending ──>                         │
    │                           │                           │
    │ <── [commands array] ─────                            │
    │                           │                           │
    │ Execute Docker commands   │                           │
    │   (pull, start, stop...)  │                           │
    │                           │                           │
    │ ── POST /containers/sync ─>                           │
    │    [containers data]      │                           │
    │                           │ ── UPDATE containers ───> │
    │                           │                           │
    │ ── POST /images/sync ────>                            │
    │    [images data]          │                           │
    │                           │ ── UPDATE images ───────> │
    │                           │                           │
```

**Configuración de Polling:**
- Contenedores: cada 15 segundos
- Imágenes: cada 60 segundos
- Volúmenes: cada 60 segundos
- Redes: cada 60 segundos

### Flujo 2: Comandos Remotos (Command Queue)

```
Frontend                  Backend                     Agent
    │                         │                          │
    │ ── POST /containers/    │                          │
    │    {container}/action ─>│                          │
    │                         │                          │
    │                         │ ── INSERT command ───>   │
    │                         │    to queue (DB)         │
    │                         │                          │
    │ <── { command_id } ─────                           │
    │                         │                          │
    │                         │                          │
    │                         │ <── GET /commands/───────│
    │                         │     pending              │
    │                         │                          │
    │                         │ ─── [commands] ────────>│
    │                         │                          │
    │                         │                          │
    │                         │                          │ Execute
    │                         │ <── PUT /commands/───────│
    │                         │     {id}/result          │
    │                         │     { success, output }  │
    │                         │                          │
    │ ── GET /commands/{id} ─>│                          │
    │                         │                          │
    │ <── { status, result } ─                           │
    │                         │                          │
```

### Flujo 3: Logs Streaming (WebSocket)

```
Frontend                  Backend                     Agent
    │                         │                          │
    │ ── WS /containers/      │                          │
    │    {id}/logs ──────────>│                          │
    │                         │                          │
    │                         │ ── POST /commands ─────> │
    │                         │    (get logs)            │
    │                         │                          │
    │                         │ <── Stream logs ─────────│
    │                         │     (chunked)            │
    │                         │                          │
    │ <── WS message ─────────                           │
    │    (log line)           │                          │
    │                         │                          │
    │ <── WS message ─────────  ... more logs ...        │
    │    (log line)           │                          │
    │                         │                          │
```

---

## 🗄️ Estructura de Base de Datos

### Migraciones Necesarias

```sql
-- Migration 001: Docker Images
CREATE TABLE docker_images (
    id VARCHAR(64) PRIMARY KEY,
    host_id VARCHAR NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    repository VARCHAR(255) NOT NULL,
    tag VARCHAR(128) NOT NULL,
    size BIGINT NOT NULL,  -- bytes
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    digest VARCHAR(128),
    architecture VARCHAR(32),
    os VARCHAR(32),
    UNIQUE(host_id, repository, tag)
);
CREATE INDEX idx_docker_images_host ON docker_images(host_id);
CREATE INDEX idx_docker_images_last_seen ON docker_images(last_seen);

-- Migration 002: Docker Volumes
CREATE TABLE docker_volumes (
    name VARCHAR(255) NOT NULL,
    host_id VARCHAR NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    driver VARCHAR(64) NOT NULL DEFAULT 'local',
    mountpoint VARCHAR(512),
    scope VARCHAR(32),
    options JSONB,
    labels JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (name, host_id)
);
CREATE INDEX idx_docker_volumes_host ON docker_volumes(host_id);

-- Migration 003: Docker Networks
CREATE TABLE docker_networks (
    id VARCHAR(64) NOT NULL,
    host_id VARCHAR NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    driver VARCHAR(64) NOT NULL,
    scope VARCHAR(32),
    internal BOOLEAN DEFAULT FALSE,
    attachable BOOLEAN DEFAULT FALSE,
    ipam JSONB,
    options JSONB,
    labels JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, host_id)
);
CREATE INDEX idx_docker_networks_host ON docker_networks(host_id);

-- Migration 004: Docker Stacks
CREATE TABLE docker_stacks (
    id SERIAL PRIMARY KEY,
    host_id VARCHAR NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    compose_content TEXT NOT NULL,
    compose_version VARCHAR(16),
    status VARCHAR(32) DEFAULT 'stopped',  -- running, stopped, error, deploying
    services JSONB,  -- Array of service names
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deployed_at TIMESTAMP WITH TIME ZONE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(host_id, name)
);
CREATE INDEX idx_docker_stacks_host ON docker_stacks(host_id);
CREATE INDEX idx_docker_stacks_status ON docker_stacks(status);

-- Migration 005: Docker Registries
CREATE TABLE docker_registries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    url VARCHAR(512) NOT NULL,
    username VARCHAR(255),
    password_encrypted TEXT,  -- AES encrypted
    is_default BOOLEAN DEFAULT FALSE,
    auth_type VARCHAR(32) DEFAULT 'basic',  -- basic, token
    verify_ssl BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    last_verified TIMESTAMP WITH TIME ZONE
);

-- Migration 006: Container Templates
CREATE TABLE container_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(512),  -- URL or emoji
    category VARCHAR(64),  -- web, database, monitoring, etc.
    type VARCHAR(32) DEFAULT 'container',  -- container, stack
    compose_content TEXT,  -- For stacks
    image VARCHAR(512),  -- For single containers
    env_variables JSONB,  -- [{name, label, description, default}]
    ports JSONB,  -- [{container, host, protocol}]
    volumes JSONB,  -- [{container, host, type}]
    networks JSONB,
    is_official BOOLEAN DEFAULT FALSE,
    downloads INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_templates_category ON container_templates(category);

-- Migration 007: Audit Logs
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(255),  -- Denormalized for deleted users
    action VARCHAR(128) NOT NULL,  -- container.start, image.pull, etc.
    resource_type VARCHAR(64) NOT NULL,  -- container, image, volume, network, stack
    resource_id VARCHAR(255),
    resource_name VARCHAR(255),
    host_id VARCHAR REFERENCES hosts(id) ON DELETE SET NULL,
    details JSONB,  -- Additional context
    success BOOLEAN NOT NULL,
    error_message TEXT,
    duration_ms INTEGER,  -- Command execution time
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- Migration 008: Extended Remote Commands
ALTER TABLE remote_commands ADD COLUMN command_type VARCHAR(64) DEFAULT 'docker';
ALTER TABLE remote_commands ADD COLUMN parameters JSONB;
ALTER TABLE remote_commands ADD COLUMN result JSONB;
ALTER TABLE remote_commands ADD COLUMN duration_ms INTEGER;
ALTER TABLE remote_commands ADD COLUMN retry_count INTEGER DEFAULT 0;
ALTER TABLE remote_commands ADD COLUMN max_retries INTEGER DEFAULT 0;

-- Migration 009: Container Extended Info
ALTER TABLE docker_containers ADD COLUMN ports JSONB;
ALTER TABLE docker_containers ADD COLUMN volumes JSONB;
ALTER TABLE docker_containers ADD COLUMN networks JSONB;
ALTER TABLE docker_containers ADD COLUMN labels JSONB;
ALTER TABLE docker_containers ADD COLUMN restart_policy VARCHAR(64);
ALTER TABLE docker_containers ADD COLUMN exit_code INTEGER;
```

---

## 🛠️ Implementación por Componente

### 1. Backend: Gestión de Imágenes

```python
# server/api/images.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from datetime import datetime, timezone

from database.models import DockerImage, Host, User, RemoteCommand, AuditLog
from api.dependencies import get_db, get_current_user
from pydantic import BaseModel

router = APIRouter()

class ImageData(BaseModel):
    id: str
    repository: str
    tag: str
    size: int
    created_at: datetime
    digest: Optional[str] = None
    
class ImageSyncPayload(BaseModel):
    host_id: str
    images: List[ImageData]

class ImagePullRequest(BaseModel):
    image: str
    tag: str = "latest"
    registry_id: Optional[int] = None

@router.post("/sync")
async def sync_images(
    payload: ImageSyncPayload,
    db: AsyncSession = Depends(get_db)
):
    """
    Agent sends periodic updates of all images.
    Upsert strategy: update if exists, insert if new.
    """
    # Verify host exists
    stmt = select(Host).where(Host.id == payload.host_id)
    result = await db.execute(stmt)
    host = result.scalar_one_or_none()
    
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    # Track seen image IDs
    seen_ids = set()
    
    for img_data in payload.images:
        seen_ids.add(img_data.id)
        
        stmt = select(DockerImage).where(
            DockerImage.id == img_data.id,
            DockerImage.host_id == payload.host_id
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.last_seen = datetime.now(timezone.utc)
            existing.size = img_data.size
        else:
            # Create new
            new_image = DockerImage(
                id=img_data.id,
                host_id=payload.host_id,
                repository=img_data.repository,
                tag=img_data.tag,
                size=img_data.size,
                created_at=img_data.created_at,
                digest=img_data.digest
            )
            db.add(new_image)
    
    # Mark images not seen as potentially deleted (soft delete)
    # Delete images not seen in 5 minutes
    from datetime import timedelta
    threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
    
    stmt = select(DockerImage).where(
        DockerImage.host_id == payload.host_id,
        DockerImage.last_seen < threshold
    )
    result = await db.execute(stmt)
    stale_images = result.scalars().all()
    
    for img in stale_images:
        await db.delete(img)
    
    await db.commit()
    
    return {
        "status": "synced",
        "images": len(payload.images),
        "deleted": len(stale_images)
    }

@router.get("/{host_id}")
async def list_images(
    host_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[ImageData]:
    """List all images on a host."""
    stmt = select(DockerImage).where(
        DockerImage.host_id == host_id
    ).order_by(DockerImage.created_at.desc())
    
    result = await db.execute(stmt)
    images = result.scalars().all()
    
    return images

@router.post("/{host_id}/pull")
async def pull_image(
    host_id: str,
    request: ImagePullRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Queue a pull command for the agent.
    Returns immediately with command ID for tracking.
    """
    # Verify host
    stmt = select(Host).where(Host.id == host_id)
    result = await db.execute(stmt)
    host = result.scalar_one_or_none()
    
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    # Get registry credentials if specified
    registry_auth = None
    if request.registry_id:
        from database.models import DockerRegistry
        stmt = select(DockerRegistry).where(DockerRegistry.id == request.registry_id)
        result = await db.execute(stmt)
        registry = result.scalar_one_or_none()
        
        if registry:
            # Decrypt password and prepare auth
            from utils.encryption import decrypt_password
            password = decrypt_password(registry.password_encrypted) if registry.password_encrypted else None
            registry_auth = {
                "username": registry.username,
                "password": password,
                "registry": registry.url
            }
    
    # Create remote command
    command = RemoteCommand(
        host_id=host_id,
        command_type="image.pull",
        parameters={
            "image": request.image,
            "tag": request.tag,
            "auth": registry_auth
        },
        status="pending",
        created_at=datetime.now(timezone.utc)
    )
    db.add(command)
    await db.commit()
    await db.refresh(command)
    
    # Log audit trail
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.email,
        action="image.pull",
        resource_type="image",
        resource_name=f"{request.image}:{request.tag}",
        host_id=host_id,
        details={"command_id": command.id},
        success=True,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit)
    await db.commit()
    
    return {
        "command_id": command.id,
        "status": "queued",
        "message": f"Pull command queued for {request.image}:{request.tag}"
    }

@router.delete("/{host_id}/images/{image_id}")
async def remove_image(
    host_id: str,
    image_id: str,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Queue image removal command."""
    # Verify image exists
    stmt = select(DockerImage).where(
        DockerImage.id == image_id,
        DockerImage.host_id == host_id
    )
    result = await db.execute(stmt)
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Check if any containers use this image (only if not force)
    if not force:
        from database.models import DockerContainer
        stmt = select(DockerContainer).where(
            DockerContainer.host_id == host_id,
            DockerContainer.image.like(f"{image.repository}:{image.tag}%")
        )
        result = await db.execute(stmt)
        containers = result.scalars().all()
        
        if containers:
            return {
                "error": "Image in use",
                "containers": [c.id for c in containers],
                "message": "Use force=true to remove anyway"
            }
    
    # Create removal command
    command = RemoteCommand(
        host_id=host_id,
        command_type="image.remove",
        parameters={
            "image_id": image_id,
            "force": force
        },
        status="pending",
        created_at=datetime.now(timezone.utc)
    )
    db.add(command)
    await db.commit()
    await db.refresh(command)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.email,
        action="image.remove",
        resource_type="image",
        resource_id=image_id,
        resource_name=f"{image.repository}:{image.tag}",
        host_id=host_id,
        details={"force": force, "command_id": command.id},
        success=True,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit)
    await db.commit()
    
    return {
        "command_id": command.id,
        "status": "queued",
        "message": f"Image removal queued"
    }
```

### 2. Agente: Implementación Docker Images (Go)

```go
// agent/docker/images.go
package docker

import (
    "context"
    "encoding/base64"
    "encoding/json"
    "io"
    "time"

    "github.com/docker/docker/api/types"
    "github.com/docker/docker/api/types/registry"
    "github.com/docker/docker/client"
)

type DockerImage struct {
    ID         string    `json:"id"`
    Repository string    `json:"repository"`
    Tag        string    `json:"tag"`
    Size       int64     `json:"size"`
    CreatedAt  time.Time `json:"created_at"`
    Digest     string    `json:"digest"`
}

// ListImages fetches all images from local Docker daemon
func ListImages() ([]DockerImage, error) {
    cli, err := client.NewClientWithOpts(client.FromEnv)
    if err != nil {
        return nil, err
    }
    defer cli.Close()

    ctx := context.Background()
    images, err := cli.ImageList(ctx, types.ImageListOptions{All: false})
    if err != nil {
        return nil, err
    }

    var result []DockerImage
    for _, img := range images {
        // Each image may have multiple repo tags
        for _, repoTag := range img.RepoTags {
            repo, tag := parseRepoTag(repoTag)
            
            result = append(result, DockerImage{
                ID:         img.ID,
                Repository: repo,
                Tag:        tag,
                Size:       img.Size,
                CreatedAt:  time.Unix(img.Created, 0),
                Digest:     img.ID, // Short ID
            })
        }
    }

    return result, nil
}

// PullImage downloads an image from registry
func PullImage(image, tag string, auth *registry.AuthConfig) error {
    cli, err := client.NewClientWithOpts(client.FromEnv)
    if err != nil {
        return err
    }
    defer cli.Close()

    ctx := context.Background()
    
    // Prepare auth if provided
    var authStr string
    if auth != nil {
        authBytes, _ := json.Marshal(auth)
        authStr = base64.URLEncoding.EncodeToString(authBytes)
    }

    refStr := image + ":" + tag
    reader, err := cli.ImagePull(ctx, refStr, types.ImagePullOptions{
        RegistryAuth: authStr,
    })
    if err != nil {
        return err
    }
    defer reader.Close()

    // Stream progress (in real implementation, send to server)
    _, err = io.Copy(io.Discard, reader)
    return err
}

// RemoveImage deletes an image
func RemoveImage(imageID string, force bool) error {
    cli, err := client.NewClientWithOpts(client.FromEnv)
    if err != nil {
        return err
    }
    defer cli.Close()

    ctx := context.Background()
    _, err = cli.ImageRemove(ctx, imageID, types.ImageRemoveOptions{
        Force:         force,
        PruneChildren: true,
    })
    return err
}

// BuildImage builds from Dockerfile
func BuildImage(dockerfileContent, tag string) error {
    // Implementation requires tar context creation
    // Simplified version - in production, create tar with Dockerfile
    cli, err := client.NewClientWithOpts(client.FromEnv)
    if err != nil {
        return err
    }
    defer cli.Close()

    // Create build context tar (omitted for brevity)
    // reader := createBuildContext(dockerfileContent)

    // ctx := context.Background()
    // _, err = cli.ImageBuild(ctx, reader, types.ImageBuildOptions{
    //     Tags:       []string{tag},
    //     Dockerfile: "Dockerfile",
    // })
    
    return nil // Placeholder
}

// Helper function
func parseRepoTag(repoTag string) (repo, tag string) {
    // Split "nginx:latest" -> "nginx", "latest"
    parts := strings.Split(repoTag, ":")
    if len(parts) == 2 {
        return parts[0], parts[1]
    }
    return repoTag, "latest"
}

// SyncImages sends current images state to server
func SyncImages(hostID string) error {
    images, err := ListImages()
    if err != nil {
        return err
    }

    payload := map[string]interface{}{
        "host_id": hostID,
        "images":  images,
    }

    // POST to /api/v1/docker/sync
    return sendToServer("/api/v1/docker/images/sync", payload)
}
```

### 3. Frontend: Gestión de Imágenes

```typescript
// frontend/src/app/hosts/[id]/images/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import {
  getImages,
  pullImage,
  removeImage,
  getCommandStatus,
  type DockerImage
} from '@/lib/api';
import styles from './images.module.css';

export default function ImagesPage() {
  const params = useParams();
  const hostId = params.id as string;

  const [images, setImages] = useState<DockerImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [showPullDialog, setShowPullDialog] = useState(false);
  const [pullImage, setPullImage] = useState('');
  const [pullTag, setPullTag] = useState('latest');
  const [pullProgress, setPullProgress] = useState<string | null>(null);

  useEffect(() => {
    loadImages();
    const interval = setInterval(loadImages, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [hostId]);

  async function loadImages() {
    try {
      const data = await getImages(hostId);
      setImages(data);
    } catch (error) {
      console.error('Failed to load images:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handlePull() {
    if (!pullImage) return;

    try {
      setPullProgress('Queueing pull command...');
      const result = await pullImage(hostId, pullImage, pullTag);
      
      // Poll command status
      setPullProgress('Pulling image...');
      let completed = false;
      
      while (!completed) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        const status = await getCommandStatus(result.command_id);
        
        if (status.status === 'completed') {
          completed = true;
          setPullProgress(null);
          setShowPullDialog(false);
          setPullImage('');
          setPullTag('latest');
          loadImages(); // Refresh list
          alert('Image pulled successfully!');
        } else if (status.status === 'failed') {
          completed = true;
          setPullProgress(null);
          alert(`Pull failed: ${status.error}`);
        }
      }
    } catch (error) {
      console.error('Pull error:', error);
      setPullProgress(null);
      alert('Failed to pull image');
    }
  }

  async function handleRemove(imageId: string, imageName: string, force = false) {
    if (!confirm(`Remove image ${imageName}?${force ? ' (FORCE)' : ''}`)) {
      return;
    }

    try {
      const result = await removeImage(hostId, imageId, force);
      
      if (result.error === 'Image in use') {
        const retry = confirm(
          `Image is used by ${result.containers.length} container(s). Force remove?`
        );
        if (retry) {
          handleRemove(imageId, imageName, true);
        }
        return;
      }

      // Wait for command completion
      let completed = false;
      while (!completed) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        const status = await getCommandStatus(result.command_id);
        
        if (status.status === 'completed') {
          completed = true;
          loadImages();
          alert('Image removed successfully!');
        } else if (status.status === 'failed') {
          completed = true;
          alert(`Removal failed: ${status.error}`);
        }
      }
    } catch (error) {
      console.error('Remove error:', error);
      alert('Failed to remove image');
    }
  }

  function formatSize(bytes: number): string {
    const mb = bytes / (1024 * 1024);
    if (mb < 1024) {
      return `${mb.toFixed(1)} MB`;
    }
    return `${(mb / 1024).toFixed(2)} GB`;
  }

  if (loading) {
    return <div className={styles.loading}>Loading images...</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>🐳 Docker Images</h1>
        <button 
          className={styles.pullBtn}
          onClick={() => setShowPullDialog(true)}
        >
          + Pull Image
        </button>
      </div>

      {/* Pull Dialog */}
      {showPullDialog && (
        <div className={styles.modal}>
          <div className={styles.modalContent}>
            <h2>Pull Docker Image</h2>
            
            {pullProgress ? (
              <div className={styles.progress}>
                <div className={styles.spinner}></div>
                <p>{pullProgress}</p>
              </div>
            ) : (
              <>
                <div className={styles.formGroup}>
                  <label>Image:</label>
                  <input
                    type="text"
                    value={pullImage}
                    onChange={(e) => setPullImage(e.target.value)}
                    placeholder="nginx, postgres, redis..."
                  />
                </div>
                
                <div className={styles.formGroup}>
                  <label>Tag:</label>
                  <input
                    type="text"
                    value={pullTag}
                    onChange={(e) => setPullTag(e.target.value)}
                    placeholder="latest"
                  />
                </div>
                
                <div className={styles.modalActions}>
                  <button onClick={handlePull}>Pull</button>
                  <button onClick={() => setShowPullDialog(false)}>
                    Cancel
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Images Table */}
      <div className={styles.tableContainer}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Repository</th>
              <th>Tag</th>
              <th>Image ID</th>
              <th>Size</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {images.map((image) => (
              <tr key={`${image.id}-${image.tag}`}>
                <td>{image.repository}</td>
                <td><span className={styles.tag}>{image.tag}</span></td>
                <td className={styles.imageId}>{image.id.substring(7, 19)}</td>
                <td>{formatSize(image.size)}</td>
                <td>{new Date(image.created_at).toLocaleDateString()}</td>
                <td>
                  <button
                    className={styles.actionBtn}
                    onClick={() => handleRemove(
                      image.id,
                      `${image.repository}:${image.tag}`
                    )}
                  >
                    🗑️ Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {images.length === 0 && (
          <div className={styles.empty}>
            <p>No images found. Pull one to get started!</p>
          </div>
        )}
      </div>
    </div>
  );
}
```

```css
/* frontend/src/app/hosts/[id]/images/images.module.css */
.container {
  padding: 24px;
  height: 100vh;
  overflow-y: auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.pullBtn {
  padding: 10px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modalContent {
  background: #1a1a2e;
  padding: 32px;
  border-radius: 12px;
  width: 500px;
  max-width: 90%;
}

.formGroup {
  margin-bottom: 20px;
}

.formGroup label {
  display: block;
  margin-bottom: 8px;
  color: #a0a0a0;
}

.formGroup input {
  width: 100%;
  padding: 10px;
  background: #0f0f1e;
  border: 1px solid #333;
  border-radius: 6px;
  color: white;
}

.tableContainer {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  padding: 20px;
  backdrop-filter: blur(10px);
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th {
  text-align: left;
  padding: 12px;
  border-bottom: 2px solid #333;
  color: #00ff88;
  font-weight: 600;
}

.table td {
  padding: 12px;
  border-bottom: 1px solid #222;
}

.tag {
  background: #667eea;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.9em;
}

.imageId {
  font-family: 'Courier New', monospace;
  color: #888;
}

.actionBtn {
  padding: 6px 12px;
  background: #ff4444;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9em;
}

.actionBtn:hover {
  background: #cc0000;
}
```

---

## 🌐 WebSockets y Streaming

### Backend: Logs Streaming con WebSocket

```python
# server/api/containers_ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict
import asyncio
import json

from api.dependencies import get_current_user_ws

router = APIRouter()

# Active WebSocket connections
active_connections: Dict[str, WebSocket] = {}

@router.websocket("/ws/containers/{host_id}/{container_id}/logs")
async def container_logs_stream(
    websocket: WebSocket,
    host_id: str,
    container_id: str
):
    await websocket.accept()
    
    connection_id = f"{host_id}:{container_id}"
    active_connections[connection_id] = websocket
    
    try:
        # Create a command for agent to start streaming logs
        from database.models import RemoteCommand
        from database.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            command = RemoteCommand(
                host_id=host_id,
                command_type="container.logs.stream",
                parameters={
                    "container_id": container_id,
                    "follow": True,
                    "tail": 100
                },
                status="pending"
            )
            db.add(command)
            await db.commit()
        
        # Keep connection alive and forward logs
        while True:
            # In production, receive from Redis pub/sub or message queue
            # For now, simple polling simulation
            await asyncio.sleep(1)
            
            # Check for new log lines from agent
            # (Agent would POST logs to REST endpoint, stored in Redis)
            # Then we push to WebSocket
            
            # Placeholder: send heartbeat
            await websocket.send_json({"type": "heartbeat"})
            
    except WebSocketDisconnect:
        del active_connections[connection_id]
    except Exception as e:
        print(f"WebSocket error: {e}")
        del active_connections[connection_id]

# Endpoint for agent to push log lines
@router.post("/containers/{host_id}/{container_id}/logs/push")
async def push_log_lines(
    host_id: str,
    container_id: str,
    lines: List[str]
):
    """Agent calls this to push new log lines."""
    connection_id = f"{host_id}:{container_id}"
    
    if connection_id in active_connections:
        ws = active_connections[connection_id]
        for line in lines:
            try:
                await ws.send_json({
                    "type": "log",
                    "line": line,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            except:
                del active_connections[connection_id]
                break
    
    return {"status": "ok"}
```

### Frontend: Logs Viewer con WebSocket

```typescript
// frontend/src/components/docker/ContainerLogs.tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import styles from './ContainerLogs.module.css';

interface ContainerLogsProps {
  hostId: string;
  containerId: string;
  containerName: string;
  onClose: () => void;
}

export function ContainerLogs({
  hostId,
  containerId,
  containerName,
  onClose
}: ContainerLogsProps) {
  const [logs, setLogs] = useState<string[]>([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Connect to WebSocket
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws/containers/${hostId}/${containerId}/logs`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'log') {
        setLogs(prev => [...prev, data.line]);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
    };

    return () => {
      ws.close();
    };
  }, [hostId, containerId]);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  function downloadLogs() {
    const blob = new Blob([logs.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${containerName}-logs.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function clearLogs() {
    setLogs([]);
  }

  return (
    <div className={styles.modal}>
      <div className={styles.logsContainer}>
        <div className={styles.header}>
          <h2>📄 Logs: {containerName}</h2>
          <div className={styles.controls}>
            <label>
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
              />
              Auto-scroll
            </label>
            <button onClick={clearLogs}>🗑️ Clear</button>
            <button onClick={downloadLogs}>💾 Download</button>
            <button onClick={onClose}>✖️ Close</button>
          </div>
        </div>

        <div className={styles.logsContent}>
          {logs.map((line, index) => (
            <div key={index} className={styles.logLine}>
              <span className={styles.lineNumber}>{index + 1}</span>
              <span className={styles.lineContent}>{line}</span>
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
}
```

---

## 🔐 Seguridad y Autenticación

### Middleware de Auditoría Automática

```python
# server/middleware/audit.py
from fastapi import Request
from datetime import datetime, timezone
import time

from database.models import AuditLog
from database.database import AsyncSessionLocal

async def audit_middleware(request: Request, call_next):
    """
    Automatically log all Docker operations for audit trail.
    """
    start_time = time.time()
    
    # Execute request
    response = await call_next(request)
    
    # Only audit specific operations
    if should_audit(request):
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Extract user from JWT
        user = getattr(request.state, "user", None)
        
        # Determine action from path
        action = parse_action(request.method, request.url.path)
        
        if action:
            async with AsyncSessionLocal() as db:
                audit = AuditLog(
                    user_id=user.id if user else None,
                    username=user.email if user else "anonymous",
                    action=action,
                    resource_type=extract_resource_type(request.url.path),
                    resource_id=extract_resource_id(request.url.path),
                    host_id=extract_host_id(request.url.path),
                    details=await extract_details(request),
                    success=(200 <= response.status_code < 300),
                    duration_ms=duration_ms,
                    ip_address=request.client.host,
                    user_agent=request.headers.get("user-agent"),
                    timestamp=datetime.now(timezone.utc)
                )
                db.add(audit)
                await db.commit()
    
    return response

def should_audit(request: Request) -> bool:
    """Determine if request should be audited."""
    audit_paths = [
        "/api/v1/docker/",
        "/api/v1/containers/",
        "/api/v1/images/",
        "/api/v1/volumes/",
        "/api/v1/networks/",
        "/api/v1/stacks/"
    ]
    return any(request.url.path.startswith(path) for path in audit_paths)

def parse_action(method: str, path: str) -> str:
    """Parse action from HTTP method and path."""
    # Examples:
    # POST /containers/{id}/action -> container.action
    # DELETE /images/{id} -> image.remove
    # POST /stacks -> stack.deploy
    
    if "containers" in path:
        if method == "POST" and "action" in path:
            return "container.action"
        elif method == "DELETE":
            return "container.remove"
        elif method == "POST" and "exec" in path:
            return "container.exec"
    elif "images" in path:
        if method == "POST" and "pull" in path:
            return "image.pull"
        elif method == "DELETE":
            return "image.remove"
        elif method == "POST" and "build" in path:
            return "image.build"
    # ... more patterns
    
    return f"{method.lower()}.{path.split('/')[-1]}"
```

---

## 📚 Conclusión

Esta documentación técnica proporciona:

1. **Arquitectura clara** con diagramas de flujo
2. **Estructura de base de datos** completa con migraciones
3. **Ejemplos de código** de producción para Backend, Agente y Frontend
4. **Patrones de WebSocket** para streaming en tiempo real
5. **Sistema de auditoría** automático para trazabilidad

**Próximos pasos:**
1. Implementar migraciones de base de datos
2. Desarrollar endpoints de Backend (FastAPI)
3. Extender funcionalidades del Agente (Go)
4. Construir UI en Frontend (Next.js/React)
5. Tests E2E para cada funcionalidad

**Referencia rápida:**
- Backend API: [http://localhost:8080/docs](http://localhost:8080/docs)
- Frontend: [http://localhost:3000](http://localhost:3000)
- Agent config: `/etc/lams/agent.conf`

---

**Versión:** 1.0  
**Fecha:** 13 de Marzo de 2026  
**Complemento de:** PORTAINER_IMPLEMENTATION_PLAN.md
