# Fase 3.1: Reverse Proxy con Traefik - COMPLETADA ✅

## Resumen

Esta fase implementa un reverse proxy con Traefik v2.10 que proporciona:
- SSL/TLS automático con Let's Encrypt
- Routing automático basado en Docker labels
- Rate limiting por servicio
- Headers de seguridad (HSTS, XSS Protection, etc.)
- Compresión HTTP
- Health checks automáticos
- Dashboard de monitorización

## 📦 Componentes Implementados

### 1. Traefik Configuration

**Archivos creados:**

#### `traefik/traefik.yml` (Configuración estática)
- **Entry Points**: HTTP (80) → redirect HTTPS (443)
- **SSL/TLS**: Let's Encrypt con ACME HTTP Challenge
- **Providers**: Docker auto-discovery + file provider
- **Dashboard**: Traefik UI para monitoring
- **Logs**: JSON format para parsing automático
- **Metrics**: Prometheus endpoint

**Características clave:**
```yaml
entryPoints:
  web:
    address: ":80"
    # Auto-redirect HTTP → HTTPS
  websecure:
    address: ":443"
    # TLS with Let's Encrypt

certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web
```

#### `traefik/dynamic/middlewares.yml` (Middlewares)
- **security-headers**: HSTS, XSS Protection, Content-Type nosniff
- **rate-limit**: 100 req/s general
- **api-rate-limit**: 500 req/s para API
- **auth-rate-limit**: 10 req/min para endpoints de autenticación
- **compress**: GZIP compression
- **cors-headers**: CORS automatizado
- **admin-whitelist**: IP whitelist para dashboard

#### `traefik/dynamic/tls.yml` (Configuración TLS)
- **TLS 1.2+**: Versión mínima
- **Cipher Suites**: Solo algoritmos seguros (AES-GCM, ChaCha20)
- **HTTP/2**: ALPN protocol negotiation
- **Curve Preferences**: P-521, P-384

### 2. Docker Compose Production

**Archivo:** `docker-compose.production.yml`

#### Servicio Traefik
```yaml
traefik:
  image: traefik:v2.10
  ports:
    - "80:80"    # HTTP
    - "443:443"  # HTTPS
    - "8888:8080" # Dashboard
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./traefik/traefik.yml:/etc/traefik/traefik.yml:ro
    - ./traefik/dynamic:/etc/traefik/dynamic:ro
    - ./traefik/letsencrypt:/letsencrypt
    - ./traefik/logs:/var/log/traefik
```

#### Backend Server (con labels Traefik)
```yaml
server:
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.lams-api.rule=Host(`api.lams.local`)"
    - "traefik.http.routers.lams-api.entrypoints=websecure"
    - "traefik.http.routers.lams-api.tls.certresolver=letsencrypt"
    - "traefik.http.services.lams-api.loadbalancer.server.port=8000"
    - "traefik.http.routers.lams-api.middlewares=api-rate-limit,security-headers"
```

#### Frontend Dashboard (con labels Traefik)
```yaml
frontend:
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.lams-frontend.rule=Host(`lams.local`)"
    - "traefik.http.routers.lams-frontend.entrypoints=websecure"
    - "traefik.http.services.lams-frontend.loadbalancer.server.port=3000"
```

### 3. Variables de Entorno

**Archivo:** `.env.example`

Variables configurables:
- `DOMAIN`: Dominio principal (lams.example.com)
- `API_DOMAIN`: Subdominio API (api.lams.example.com)
- `ACME_EMAIL`: Email para Let's Encrypt
- `POSTGRES_PASSWORD`: Contraseña segura de DB
- `SECRET_KEY`: Clave secreta JWT (64 char hex)
- `ADMIN_PASSWORD`: Contraseña administrador
- Rate limiting settings
- Backup configuration

### 4. Script de Instalación

**Archivo:** `setup-production.sh`

Automatiza el deployment completo:
1. ✅ Verifica Docker y Docker Compose instalados
2. ✅ Crea directorios necesarios (`traefik/letsencrypt`, `traefik/logs`)
3. ✅ Copia `.env.example` → `.env` si no existe
4. ✅ Valida variables críticas (passwords, secrets)
5. ✅ Actualiza configuración de Traefik con dominio real
6. ✅ Crea `acme.json` con permisos correctos (600)
7. ✅ Construye imágenes Docker
8. ✅ Inicia servicios con `docker-compose up -d`
9. ✅ Muestra estado y próximos pasos

**Uso:**
```bash
sudo ./setup-production.sh
```

## 🔒 Seguridad Implementada

### SSL/TLS
- ✅ Certificados automáticos con Let's Encrypt
- ✅ Renovación automática (60 días antes de expiración)
- ✅ TLS 1.2+ only
- ✅ Cipher suites modernos (AES-GCM, ChaCha20)
- ✅ HTTP/2 enabled
- ✅ HSTS con preload

### Headers de Seguridad
```yaml
security-headers:
  browserXssFilter: true
  contentTypeNosniff: true
  forceSTSHeader: true
  frameDeny: true
  sslRedirect: true
  stsIncludeSubdomains: true
  stsPreload: true
  stsSeconds: 31536000  # 1 año
  customFrameOptionsValue: "SAMEORIGIN"
```

### Rate Limiting
- **General**: 100 req/s, burst 50
- **API**: 500 req/s, burst 200
- **Auth**: 10 req/min, burst 20

### IP Whitelisting
Dashboard de Traefik solo accesible desde:
- localhost (127.0.0.1/32)
- Redes privadas (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)

## 📊 Monitorización

### Traefik Dashboard
- **URL**: https://traefik.lams.local:8888
- **Autenticación**: IP whitelist
- **Información**:
  - Routers activos
  - Services y health status
  - Middlewares aplicados
  - Certificados SSL
  - Request rate en tiempo real

### Logs
```bash
# Logs combinados
docker-compose -f docker-compose.production.yml logs -f

# Solo Traefik
docker-compose -f docker-compose.production.yml logs -f traefik

# Access logs
tail -f traefik/logs/access.log | jq

# Error logs
tail -f traefik/logs/traefik.log | jq '.level="ERROR"'
```

### Métricas Prometheus
**Endpoint**: `http://traefik:8080/metrics`

Métricas disponibles:
- `traefik_entrypoint_requests_total`
- `traefik_entrypoint_request_duration_seconds`
- `traefik_service_requests_total`
- `traefik_service_request_duration_seconds`

## 🚀 Deployment en Producción

### Prerrequisitos

1. **Servidor con IP pública**
   - Ubuntu 20.04+ / Debian 11+ / Rocky Linux 9+
   - Al menos 2 GB RAM, 20 GB disco
   - Puertos 80, 443 abiertos en firewall

2. **Dominio configurado**
   ```
   A Record: lams.example.com → IP_SERVIDOR
   A Record: api.lams.example.com → IP_SERVIDOR
   A Record: traefik.lams.example.com → IP_SERVIDOR
   ```

3. **Docker & Docker Compose instalados**
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   
   # Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

### Pasos de Instalación

#### 1. Clonar repositorio
```bash
git clone https://github.com/TU_USUARIO/LAMS.git
cd LAMS
```

#### 2. Configurar variables de entorno
```bash
cp .env.example .env
nano .env  # o vim, vi, etc.
```

**Variables críticas a cambiar:**
```bash
DOMAIN=lams.tudominio.com
API_DOMAIN=api.lams.tudominio.com
ACME_EMAIL=tu-email@dominio.com
POSTGRES_PASSWORD=$(openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)
ADMIN_PASSWORD=$(openssl rand -base64 16)
```

#### 3. Ejecutar setup
```bash
sudo ./setup-production.sh
```

#### 4. Verificar certificados SSL
```bash
# Ver logs de ACME challenge
docker-compose -f docker-compose.production.yml logs traefik | grep -i acme

# Verificar acme.json
sudo ls -la traefik/letsencrypt/acme.json

# Test HTTPS
curl -I https://lams.tudominio.com
```

#### 5. Acceder al sistema
- **Dashboard**: https://lams.tudominio.com
- **API Docs**: https://api.lams.tudominio.com/docs
- **Traefik Dashboard**: https://traefik.lams.tudominio.com:8888

### Troubleshooting

#### Certificados SSL no se generan

**Problema**: Let's Encrypt ACME challenge falla

**Solución**:
```bash
# 1. Verificar DNS configurado correctamente
dig lams.tudominio.com +short

# 2. Verificar puertos abiertos
sudo netstat -tlnp | grep -E ':(80|443)'

# 3. Ver logs detallados
docker-compose -f docker-compose.production.yml logs traefik

# 4. Usar staging de Let's Encrypt para testing
# Editar traefik/traefik.yml: caServer staging URL
# Borrar acme.json y reiniciar
rm traefik/letsencrypt/acme.json
docker-compose -f docker-compose.production.yml restart traefik
```

#### Error 502 Bad Gateway

**Problema**: Traefik no puede conectar con backend

**Solución**:
```bash
# Verificar que servicios están corriendo
docker-compose -f docker-compose.production.yml ps

# Verificar logs de backend
docker-compose -f docker-compose.production.yml logs server

# Verificar red Docker
docker network inspect lams_network

# Reiniciar servicios
docker-compose -f docker-compose.production.yml restart
```

#### Rate Limit alcanzado

**Problema**: HTTP 429 Too Many Requests

**Solución**:
```bash
# Editar traefik/dynamic/middlewares.yml
# Aumentar average y burst según necesidades

# Recargar configuración (no requiere restart)
# Traefik detecta cambios automáticamente
```

## 🔄 Actualización del Sistema

```bash
# 1. Pull últimos cambios
git pull origin main

# 2. Rebuild imágenes
docker-compose -f docker-compose.production.yml build

# 3. Recrear servicios (con zero-downtime)
docker-compose -f docker-compose.production.yml up -d

# 4. Verificar estado
docker-compose -f docker-compose.production.yml ps
```

## 📈 Próximos Pasos

Con Fase 3.1 completada, el sistema tiene:
- ✅ Reverse proxy con Traefik
- ✅ SSL/TLS automático
- ✅ Rate limiting configurado
- ✅ Headers de seguridad
- ✅ Compresión HTTP
- ✅ Health checks
- ✅ Logs estructurados

**Siguiente fase**: Fase 3.2 - Política de Retención de Datos

## 📚 Referencias

- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [Let's Encrypt](https://letsencrypt.org/getting-started/)
- [Docker Compose Networking](https://docs.docker.com/compose/networking/)
- [Security Headers](https://securityheaders.com/)
- [OWASP Security Cheat Sheet](https://cheatsheetseries.owasp.org/)
