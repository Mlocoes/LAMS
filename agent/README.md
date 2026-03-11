# LAMS Agent - Monitor de Sistema

Este directorio contiene el agente de monitoreo LAMS escrito en **Go**, que recolecta métricas del sistema y las envía al servidor central.

## Archivos

### Código Fuente
- **`main.go`**: Código fuente del agente en Go
  - Recolecta métricas: CPU, RAM, Disco, Temperatura, Contenedores Docker
  - Envía métricas cada 15 segundos (configurable)
  - Reconexión automática en caso de fallo

### Scripts de Instalación

#### `install-agent.sh` ⭐
Script automatizado para instalar el agente como servicio systemd.

**Uso Interactivo** (recomendado para instalaciones manuales):
```bash
sudo ./install-agent.sh
```
El script solicitará:
- URL del servidor LAMS
- Token de autenticación
- Host ID (opcional, usa hostname por defecto)
- Intervalo de métricas en segundos (opcional, 15 por defecto)

**Uso No Interactivo** (para automatización/Ansible):
```bash
sudo ./install-agent.sh \
  --server "http://192.168.1.100:8000" \
  --token "your-secret-token" \
  --host-id "web-server-01" \
  --interval 15
```

**Qué hace el script**:
1. ✅ Valida prerrequisitos (Go, systemd, permisos root)
2. ✅ Compila el binario desde `main.go`
3. ✅ Instala binario en `/usr/local/bin/lams-agent`
4. ✅ Crea configuración en `/etc/lams/agent.conf`
5. ✅ Configura servicio systemd
6. ✅ Habilita arranque automático
7. ✅ Inicia el servicio

#### `uninstall-agent.sh`
Script para desinstalar completamente el agente.

**Uso básico**:
```bash
sudo ./uninstall-agent.sh
```

**Opciones**:
```bash
# Mantener configuración para reinstalación futura
sudo ./uninstall-agent.sh --keep-config

# Desinstalar sin confirmación (para scripts)
sudo ./uninstall-agent.sh --force
```

**Qué hace el script**:
1. Detiene el servicio systemd
2. Deshabilita arranque automático
3. Elimina binario de `/usr/local/bin/`
4. Elimina servicio de `/etc/systemd/system/`
5. Elimina configuración de `/etc/lams/` (opcional)
6. Recarga systemd

#### `install-agent.sh.old`
Backup del script de instalación original (referencia histórica).

### Archivos de Configuración

#### `lams-agent.service.template`
Template del archivo de unidad systemd. El script `install-agent.sh` utiliza este template y sustituye las variables para generar el servicio final.

**Variables sustituidas**:
- `{{LAMS_SERVER_URL}}`: URL del servidor
- `{{LAMS_HOST_ID}}`: Identificador del host
- `{{LAMS_AGENT_TOKEN}}`: Token de autenticación
- `{{LAMS_METRICS_INTERVAL}}`: Intervalo en segundos

#### `agent.conf.example`
Ejemplo de archivo de configuración con todas las variables de entorno documentadas.

**Variables disponibles**:
- `LAMS_SERVER_URL`: URL del servidor LAMS (requerido)
- `LAMS_HOST_ID`: Identificador único del host (opcional, default: hostname)
- `LAMS_AGENT_TOKEN`: Token para autenticación (requerido)
- `LAMS_METRICS_INTERVAL`: Segundos entre recolecciones (opcional, default: 15)

### Documentación de Testing

#### `TESTING_CHECKLIST.md`
Checklist completo para validar la instalación en múltiples distribuciones Linux.

**Incluye**:
- 7 test suites detallados
- Validaciones por distribución (Ubuntu, Debian, Rocky Linux)
- Matriz de resultados
- Troubleshooting de casos de error

---

## Guía Rápida de Instalación

### Para Producción (con systemd)

1. **Copiar archivos al servidor**:
   ```bash
   scp -r agent/ user@remote-server:/tmp/
   ```

2. **Conectar y ejecutar instalación**:
   ```bash
   ssh user@remote-server
   cd /tmp/agent
   sudo ./install-agent.sh
   ```

3. **Verificar instalación**:
   ```bash
   sudo systemctl status lams-agent
   sudo journalctl -u lams-agent -f
   ```

### Para Desarrollo (ejecución manual)

1. **Compilar**:
   ```bash
   go build -o lams-agent main.go
   ```

2. **Ejecutar con variables de entorno**:
   ```bash
   LAMS_SERVER_URL="http://localhost:8000" \
   LAMS_HOST_ID="dev-machine" \
   LAMS_AGENT_TOKEN="dev-token" \
   ./lams-agent
   ```

---

## Gestión del Servicio (Producción)

Una vez instalado como servicio systemd:

```bash
# Ver estado
sudo systemctl status lams-agent

# Ver logs en tiempo real
sudo journalctl -u lams-agent -f

# Reiniciar servicio
sudo systemctl restart lams-agent

# Detener servicio
sudo systemctl stop lams-agent

# Arranque automático
sudo systemctl enable lams-agent   # Habilitar
sudo systemctl disable lams-agent  # Deshabilitar
```

---

## Modificar Configuración

Después de instalar, puedes modificar la configuración editando:

```bash
sudo nano /etc/lams/agent.conf
```

Aplicar cambios:
```bash
sudo systemctl restart lams-agent
```

---

## Desinstalación

```bash
# Desinstalación completa
sudo ./uninstall-agent.sh

# O mantener configuración para reinstalar después
sudo ./uninstall-agent.sh --keep-config
```

---

## Prerrequisitos

- **Sistema Operativo**: Linux con systemd (Ubuntu 20.04+, Debian 11+, Rocky Linux 9+)
- **Go**: Versión 1.21 o superior
- **Permisos**: root o sudo
- **Dependencias Go**: 
  - `github.com/shirou/gopsutil/v3`
  - Instaladas automáticamente con `go build`

### Instalar Go si no está disponible

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install golang-go
```

**Rocky Linux/CentOS**:
```bash
sudo dnf install golang
```

**Verificar instalación**:
```bash
go version  # Debe mostrar 1.21+
```

---

## Troubleshooting

### Error: "systemd not found"
- Verifica: `systemctl --version`
- Para sistemas sin systemd, usa ejecución manual

### Error: "Go compiler not found"
- Instala Go según las instrucciones de prerrequisitos arriba

### Error: "Permission denied"
- Usa `sudo` para ejecutar los scripts
- Verifica permisos: `chmod +x install-agent.sh`

### El agente no conecta al servidor
```bash
# Test manual de conectividad
curl http://<SERVER_IP>:8000/health

# Verificar logs
sudo journalctl -u lams-agent -n 50

# Verificar configuración
cat /etc/lams/agent.conf
```

### Métricas no llegan al dashboard
1. Verifica que el servicio esté activo: `systemctl status lams-agent`
2. Revisa logs por errores: `journalctl -u lams-agent -f`
3. Verifica conectividad de red al servidor
4. Confirma que el token sea correcto
5. Verifica que el Host ID esté registrado en el servidor

---

## Archivos Instalados (Producción)

Cuando instales con `install-agent.sh`, los archivos se ubicarán en:

- **Binario**: `/usr/local/bin/lams-agent`
- **Configuración**: `/etc/lams/agent.conf` (permisos 600)
- **Servicio systemd**: `/etc/systemd/system/lams-agent.service`
- **Logs**: Accesibles con `journalctl -u lams-agent`

---

## Próximos Pasos

Después de instalar el agente:

1. ✅ Verificar métricas en el dashboard web
2. ✅ Configurar reglas de alertas en el servidor
3. ✅ Probar persistencia con reboot del sistema
4. ✅ Consultar logs con `journalctl` para debugging

---

## Referencias

- **Documentación**: Ver [`../docs/installation.md`](../docs/installation.md) para guía completa
- **Testing**: Ver [`TESTING_CHECKLIST.md`](TESTING_CHECKLIST.md) para validación multi-distro
- **Plan de Desarrollo**: Ver [`../docs/PLAN_DESARROLLO.md`](../docs/PLAN_DESARROLLO.md) Fase 1.2

## Licencia

Parte del proyecto LAMS (Linux Autonomous Monitoring System).
