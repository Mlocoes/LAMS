# 🚀 Guía de Instalación del Agente LAMS - Versión Mejorada

El script de instalación ahora incluye **modo interactivo** y **descubrimiento automático** de servidores LAMS en la red.

---

## 📋 Modos de Instalación

### 🎯 Modo 1: Interactivo (Recomendado)

El modo más fácil y amigable. El script te guiará paso a paso.

```bash
cd /tmp/lams-agent
sudo ./install-agent.sh
```

**Características:**
- ✅ Menús interactivos con navegación
- ✅ Detección automática de información del sistema
- ✅ Búsqueda automática de servidores LAMS en la red
- ✅ Validación de conectividad antes de instalar
- ✅ Valores por defecto inteligentes
- ✅ Confirmación antes de instalar

---

### 🔍 Modo 2: Auto-Descubrimiento

Para instalaciones rápidas con detección automática del servidor.

```bash
sudo ./install-agent.sh --auto
```

**Qué hace:**
1. 🔍 Escanea la red local buscando servidores LAMS
2. 🎯 Detecta puertos comunes (8080, 8000, 3000, 80, 443)
3. ✅ Valida la conectividad con los servidores encontrados
4. 🚀 Instala automáticamente con el mejor servidor encontrado

**Ideal para:**
- Instalaciones rápidas en múltiples servidores
- Scripts de automatización
- Cuando el servidor LAMS está en la misma red

---

### ⚙️ Modo 3: CLI Clásico

Para máximo control o automatización con scripts.

```bash
sudo ./install-agent.sh \
  --server "http://192.168.0.8:8080" \
  --token "K25uxTH_dDcLHpsYPQAqV_Jfy0DhzJuh7YG8niPxfBU" \
  --host-id "mi-servidor-web" \
  --build-local
```

**Opciones disponibles:**

| Opción | Descripción | Ejemplo |
|--------|-------------|---------|
| `--server URL` | URL del servidor LAMS | `http://192.168.0.8:8080` |
| `--token TOKEN` | Token de autenticación | `K25uxTH_d...` |
| `--host-id ID` | ID único del host | `web-server-01` |
| `--build-local` | Compilar con Go local | - |
| `--skip-systemd` | No instalar como servicio | - |
| `--non-interactive` | Sin confirmaciones | - |
| `--help` | Ver ayuda completa | - |

---

## 🔧 Requisitos del Sistema

### Obligatorios
- ✅ Sistema Linux (Ubuntu, Debian, RHEL, CentOS, etc.)
- ✅ `curl` instalado
- ✅ Permisos de root/sudo

### Opcionales
- ⚙️ `systemd` (recomendado para servicio automático)
- 🔨 `go` >= 1.20 (solo si usas `--build-local`)

### Instalar dependencias:

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install curl
```

**RHEL/CentOS/Rocky:**
```bash
sudo yum install curl
```

---

## 📡 Proceso de Descubrimiento Automático

El script busca servidores LAMS de forma inteligente:

### 1️⃣ **Escaneo Prioritario**
Primero verifica hosts comunes:
- `127.0.0.1` (localhost)
- IP local del servidor
- `x.x.x.1` (gateway)
- `x.x.x.8`, `x.x.x.10` (IPs comunes de servidores)

### 2️⃣ **Escaneo de Puertos**
Para cada host, prueba puertos comunes de LAMS:
- `8080` (puerto por defecto LAMS)
- `8000` (FastAPI default)
- `3000` (Next.js frontend)
- `80`, `443` (HTTP/HTTPS estándar)

### 3️⃣ **Validación**
Verifica que realmente es un servidor LAMS comprobando:
- ✅ `/docs` (Swagger UI)
- ✅ `/api/v1/health` (Health check)
- ✅ Respuesta contiene "LAMS"

### 4️⃣ **Escaneo Completo** (si no encuentra nada)
Si no encuentra nada en hosts prioritarios, escanea toda la red /24
- Muestra barra de progreso
- Escaneo paralelo (hasta 20 hosts simultáneos)
- Timeout de 2 segundos por host

---

## 🎨 Características de la UI Mejorada

### Interfaz Visual
- ✅ Banner ASCII colorido
- ✅ Iconos para cada tipo de mensaje
- ✅ Códigos de color consistentes
- ✅ Barras de progreso animadas
- ✅ Spinners para operaciones largas

### Feedback Claro
```
[✓] Operación exitosa
[⚠] Advertencia
[✗] Error
[→] Paso en progreso
```

### Detección Automática del Sistema
El script detecta automáticamente:
- 🖥️ Sistema operativo y versión
- 💻 Número de núcleos CPU
- 🧠 Memoria RAM total
- 💾 Espacio en disco disponible
- 🌐 IP local y red

---

## 📦 Ejemplo Completo de Instalación

### Preparación

1. **Copiar los archivos al servidor:**
```bash
# Desde tu máquina con LAMS
cd /home/mloco/Escritorio/LAMS/agent
scp -r * usuario@servidor-remoto:/tmp/lams-agent/
```

2. **Conectar al servidor remoto:**
```bash
ssh usuario@servidor-remoto
cd /tmp/lams-agent
```

### Instalación Interactiva Paso a Paso

```bash
sudo ./install-agent.sh
```

**El script te preguntará:**

1. **¿Buscar servidores automáticamente?**
   - ✅ Sí → Escanea la red y muestra servidores encontrados
   - ❌ No → Te pide la URL manualmente

2. **Selecciona el servidor** (si se encontraron varios)
   - Muestra lista numerada
   - Usa las flechas ↑↓ y Enter para seleccionar

3. **Token de autenticación** (opcional)
   - Presiona Enter para omitir o ingresa el token

4. **Host ID**
   - Presiona Enter para usar el hostname
   - O ingresa un ID personalizado

5. **¿Compilar localmente?** (si Go está instalado)
   - S/n → Decide si compilar con Go local o usar binario

6. **Confirmación final**
   - Muestra resumen de configuración
   - S/n → Procede con la instalación

---

## 🚦 Verificación Post-Instalación

### Ver estado del servicio
```bash
systemctl status lams-agent
```

**Salida esperada:**
```
● lams-agent.service - LAMS Monitoring Agent
   Loaded: loaded (/etc/systemd/system/lams-agent.service)
   Active: active (running) since...
```

### Ver logs en tiempo real
```bash
journalctl -u lams-agent -f
```

### Verificar en el dashboard
1. Abre el navegador en: `http://SERVIDOR_LAMS:8080`
2. Inicia sesión
3. Deberías ver el nuevo host en la lista

---

## 🔄 Gestión del Agente

### Comandos básicos
```bash
# Reiniciar agente
sudo systemctl restart lams-agent

# Detener agente
sudo systemctl stop lams-agent

# Iniciar agente
sudo systemctl start lams-agent

# Ver logs (últimas 50 líneas)
sudo journalctl -u lams-agent -n 50

# Seguir logs en tiempo real
sudo journalctl -u lams-agent -f
```

### Editar configuración
```bash
sudo nano /etc/lams/agent.conf
```

Después de editar, reiniciar:
```bash
sudo systemctl restart lams-agent
```

---

## 🛠️ Solución de Problemas

### El agente no encuentra el servidor

**Problema:** "No se encontraron servidores LAMS automáticamente"

**Soluciones:**
1. Verifica que el servidor LAMS está corriendo
2. Verifica que estás en la misma red
3. Usa modo manual: `sudo ./install-agent.sh --server http://IP:PUERTO`
4. Verifica firewall: `sudo ufw status` (si está bloqueando)

### El agente no inicia

**Problema:** `systemctl status lams-agent` muestra "failed"

**Soluciones:**
```bash
# Ver logs detallados
sudo journalctl -u lams-agent -n 100

# Verificar configuración
cat /etc/lams/agent.conf

# Probar ejecución manual
sudo /usr/local/bin/lams-agent
```

### Errores de compilación (con --build-local)

**Problema:** "failed to compile"

**Soluciones:**
1. Verifica versión de Go: `go version` (debe ser >= 1.20)
2. Instala dependencias: `cd /tmp/lams-agent && go mod download`
3. Usa binario pre-compilado (omite `--build-local`)

---

## 🔐 Seguridad

### Archivo de configuración
El archivo `/etc/lams/agent.conf` tiene permisos `600` (solo root puede leer):
```bash
-rw------- 1 root root agent.conf
```

### Token de autenticación
El token se guarda en `/etc/lams/agent.conf` y nunca se muestra en logs.

---

## 🗑️ Desinstalación

Para desinstalar completamente el agente:

```bash
cd /tmp/lams-agent
sudo ./uninstall-agent.sh
```

**Opciones:**
- `--keep-config` → Mantiene la configuración para reinstalar después
- `--force` → No pide confirmación

---

## 📞 Ayuda y Soporte

### Ver ayuda del script
```bash
./install-agent.sh --help
```

### Consultar documentación completa
```bash
cat /tmp/lams-agent/README.md
```

### Verificar versión y estado
```bash
/usr/local/bin/lams-agent --version
systemctl status lams-agent
```

---

## ✨ Nuevas Características vs Versión Anterior

| Característica | Antes | Ahora |
|----------------|-------|-------|
| **Modo de uso** | Solo CLI | CLI + Interactivo + Auto |
| **Descubrimiento** | Manual | Automático en red |
| **UI** | Texto plano | Colores + iconos + barras |
| **Validación** | Ninguna | Prueba conectividad |
| **Detección sistema** | Manual | Automática |
| **Confirmación** | No | Sí (con resumen) |
| **Feedback** | Básico | Detallado con spinners |

---

¡Listo! 🎉 El agente LAMS ahora es mucho más fácil de instalar con el modo interactivo y descubrimiento automático.
