# Checklist de Testing - Instalación de Agente LAMS

Este documento contiene las pruebas que deben realizarse en diferentes distribuciones Linux para validar la instalación automatizada del agente LAMS con systemd.

## Distribuciones Objetivo

Según el plan de desarrollo (PLAN_DESARROLLO.md), se deben probar las siguientes distribuciones:

- ✅ **Ubuntu 22.04 LTS** (Jammy Jellyfish)
- ✅ **Debian 12** (Bookworm)  
- ✅ **Rocky Linux 9** (Blue Onyx)

### Distribuciones Adicionales Recomendadas (Opcional)
- Ubuntu 20.04 LTS (Focal Fossa)
- CentOS Stream 9
- Fedora 39+
- openSUSE Leap 15.5

---

## Pre-requisitos de Testing

Antes de comenzar las pruebas, asegúrate de tener:

1. **Máquinas de prueba**:
   - Instancias VM o contenedores con cada distribución
   - Acceso root/sudo
   - Conexión a internet

2. **Servidor LAMS central**:
   - Servidor LAMS ejecutándose y accesible
   - URL del servidor (ej: `http://192.168.1.100:8000`)
   - Token de autenticación configurado

3. **Archivos necesarios**:
   - `agent/install-agent.sh`
   - `agent/uninstall-agent.sh`
   - `agent/main.go` (código fuente del agente)
   - `agent/lams-agent.service.template`
   - `agent/agent.conf.example`

---

## Suite de Pruebas por Distribución

### Test Suite 1: Instalación Interactiva Básica

**Objetivo**: Verificar instalación interactiva funcional

**Pasos**:
```bash
# 1. Copiar archivos al sistema de prueba
scp -r agent/ user@test-system:/tmp/

# 2. Conectar al sistema
ssh user@test-system

# 3. Verificar prerrequisitos
systemctl --version           # Debe mostrar versión de systemd
go version                    # Debe mostrar Go 1.21+

# Si Go no está instalado:
# Ubuntu/Debian: sudo apt update && sudo apt install golang-go
# Rocky/CentOS: sudo dnf install golang

# 4. Ejecutar instalación interactiva
cd /tmp/agent
sudo ./install-agent.sh

# Ingresar cuando se solicite:
# - Server URL: http://<IP_SERVIDOR>:8000
# - Token: <TU_TOKEN>
# - Host ID: test-<distro>-01
# - Interval: 15
```

**Validaciones**:
- [ ] Script ejecuta sin errores
- [ ] Compilación de Go exitosa
- [ ] Binario instalado en `/usr/local/bin/lams-agent`
- [ ] Configuración creada en `/etc/lams/agent.conf` con permisos 600
- [ ] Servicio systemd creado en `/etc/systemd/system/lams-agent.service`
- [ ] Servicio habilitado: `systemctl is-enabled lams-agent` → "enabled"
- [ ] Servicio activo: `systemctl is-active lams-agent` → "active"
- [ ] Logs sin errores: `journalctl -u lams-agent -n 20`
- [ ] Métricas llegando al servidor (verificar en dashboard)

---

### Test Suite 2: Instalación No Interactiva (CLI Args)

**Objetivo**: Verificar instalación desatendida para automatización

**Pasos**:
```bash
# Limpiar instalación previa si existe
sudo ./uninstall-agent.sh --force

# Instalación con argumentos CLI
sudo ./install-agent.sh \
  --server "http://192.168.1.100:8000" \
  --token "test-token-123" \
  --host-id "cli-test-$(hostname)" \
  --interval 10
```

**Validaciones**:
- [ ] No solicita input interactivo
- [ ] Instalación completa sin intervención
- [ ] Configuración correcta según parámetros CLI
- [ ] Servicio ejecutándose correctamente
- [ ] Intervalo de 10 segundos aplicado (verificar en logs)

---

### Test Suite 3: Persistencia y Arranque Automático

**Objetivo**: Validar que el servicio sobrevive reinicios

**Pasos**:
```bash
# 1. Verificar servicio está habilitado
sudo systemctl is-enabled lams-agent

# 2. Reiniciar sistema
sudo reboot

# 3. Después del reinicio, verificar servicio
sudo systemctl status lams-agent
journalctl -u lams-agent --since "5 minutes ago"

# 4. Verificar proceso activo
ps aux | grep lams-agent
```

**Validaciones**:
- [ ] Servicio arranca automáticamente tras reboot
- [ ] Proceso lams-agent ejecutándose
- [ ] Métricas continúan llegando al servidor
- [ ] No hay errores en logs post-reboot

---

### Test Suite 4: Gestión del Servicio

**Objetivo**: Verificar comandos de gestión systemd

**Pasos**:
```bash
# Stop
sudo systemctl stop lams-agent
sudo systemctl status lams-agent  # Debe mostrar "inactive"

# Start  
sudo systemctl start lams-agent
sudo systemctl status lams-agent  # Debe mostrar "active"

# Restart
sudo systemctl restart lams-agent
journalctl -u lams-agent -n 10    # Verificar logs de reinicio

# Disable
sudo systemctl disable lams-agent
systemctl is-enabled lams-agent   # Debe mostrar "disabled"

# Enable nuevamente
sudo systemctl enable lams-agent
```

**Validaciones**:
- [ ] Todos los comandos systemctl funcionan correctamente
- [ ] Stop detiene el proceso
- [ ] Start inicia el proceso
- [ ] Restart reinicia sin errores
- [ ] Enable/Disable cambian configuración de arranque

---

### Test Suite 5: Configuración y Modificación

**Objetivo**: Verificar cambios de configuración

**Pasos**:
```bash
# 1. Modificar configuración
sudo nano /etc/lams/agent.conf
# Cambiar LAMS_METRICS_INTERVAL=15 → LAMS_METRICS_INTERVAL=30

# 2. Aplicar cambios
sudo systemctl restart lams-agent

# 3. Verificar cambio aplicado
journalctl -u lams-agent -n 20 | grep -i interval
```

**Validaciones**:
- [ ] Archivo de configuración editable
- [ ] Cambios se aplican tras restart
- [ ] Nuevo intervalo reflejado en comportamiento

---

### Test Suite 6: Desinstalación

**Objetivo**: Validar limpieza completa del sistema

**Pasos**:
```bash
# 1. Desinstalación manteniendo configuración
sudo ./uninstall-agent.sh --keep-config

# Verificar
ls -la /usr/local/bin/lams-agent           # No debe existir
ls -la /etc/systemd/system/lams-agent.service  # No debe existir
ls -la /etc/lams/agent.conf                # Debe existir (keep-config)
sudo systemctl status lams-agent           # Service not found

# 2. Reinstalar usando config existente
sudo ./install-agent.sh --server "http://192.168.1.100:8000"
cat /etc/lams/agent.conf                   # Config debe estar intacta

# 3. Desinstalación completa
sudo ./uninstall-agent.sh --force

# Verificar limpieza total
ls -la /usr/local/bin/lams-agent           # No debe existir
ls -la /etc/lams/                          # Directorio no debe existir
ls -la /etc/systemd/system/lams-agent.service  # No debe existir
sudo systemctl daemon-reload
sudo systemctl status lams-agent           # Service not found
```

**Validaciones**:
- [ ] `--keep-config` mantiene configuración
- [ ] Desinstalación completa elimina todo
- [ ] No quedan archivos huérfanos
- [ ] Servicio completamente removido de systemd

---

### Test Suite 7: Casos de Error

**Objetivo**: Validar manejo de errores y edge cases

#### 7.1 Instalación sin Go
```bash
# Simular Go no disponible
sudo mv /usr/bin/go /usr/bin/go.backup 2>/dev/null || true
which go  # No debe encontrarse

# Intentar instalación
sudo ./install-agent.sh

# Restaurar
sudo mv /usr/bin/go.backup /usr/bin/go 2>/dev/null || true
```
**Validación**: 
- [ ] Error claro indicando Go no encontrado
- [ ] Script termina con código de error

#### 7.2 Instalación sin permisos sudo
```bash
./install-agent.sh  # Sin sudo
```
**Validación**:
- [ ] Error claro: "debe ejecutarse como root"

#### 7.3 Servidor no accesible
```bash
sudo ./install-agent.sh \
  --server "http://192.168.255.255:9999" \
  --token "test"
```
**Validación**:
- [ ] Servicio se instala pero muestra errores de conexión en logs
- [ ] journalctl muestra intentos de reconexión

#### 7.4 Reinstalación sobre instalación existente
```bash
# Primer install
sudo ./install-agent.sh --server "..." --token "..."

# Segundo install sin desinstalar
sudo ./install-agent.sh --server "..." --token "..."
```
**Validación**:
- [ ] Script maneja instalación existente correctamente
- [ ] No genera conflictos

---

## Matriz de Resultados

Completa esta tabla con los resultados de las pruebas:

| Test Suite | Ubuntu 22.04 | Debian 12 | Rocky Linux 9 | Notas |
|-----------|--------------|-----------|---------------|-------|
| 1. Instalación Interactiva | ⬜ | ⬜ | ⬜ | |
| 2. CLI Args | ⬜ | ⬜ | ⬜ | |
| 3. Persistencia | ⬜ | ⬜ | ⬜ | |
| 4. Gestión systemd | ⬜ | ⬜ | ⬜ | |
| 5. Configuración | ⬜ | ⬜ | ⬜ | |
| 6. Desinstalación | ⬜ | ⬜ | ⬜ | |
| 7. Casos de Error | ⬜ | ⬜ | ⬜ | |

**Símbolos**:
- ✅ = Todos los tests pasaron
- ⚠️ = Pasó con warnings/issues menores
- ❌ = Falló
- ⬜ = No probado

---

## Información de Testing

### Versiones Probadas

| Distribución | Versión Kernel | Go Version | Systemd Version |
|-------------|----------------|------------|-----------------|
| Ubuntu 22.04 | | | |
| Debian 12 | | | |
| Rocky Linux 9 | | | |

### Issues Encontrados

Documenta cualquier problema encontrado durante las pruebas:

```
Issue #1:
- Distribución: 
- Test Suite:
- Descripción:
- Workaround/Solución:

Issue #2:
...
```

---

## Checklist Final

Antes de dar por completada la Fase 1.2, verifica:

- [ ] Los 3 scripts funcionan correctamente:
  - [ ] `install-agent.sh` (modo interactivo)
  - [ ] `install-agent.sh` (modo CLI)
  - [ ] `uninstall-agent.sh`

- [ ] Archivos de configuración validados:
  - [ ] `lams-agent.service.template`
  - [ ] `agent.conf.example`

- [ ] Documentación actualizada:
  - [ ] `docs/installation.md` con nuevo procedimiento
  - [ ] Troubleshooting incluido

- [ ] Testing completado en:
  - [ ] Ubuntu 22.04
  - [ ] Debian 12
  - [ ] Rocky Linux 9

- [ ] Funcionalidad verificada:
  - [ ] Instalación interactiva
  - [ ] Instalación CLI/automatizada
  - [ ] Arranque automático (reboot test)
  - [ ] Gestión con systemctl
  - [ ] Modificación de configuración
  - [ ] Desinstalación limpia
  - [ ] Manejo de errores

---

## Notas

- Usa VMs o contenedores con acceso a systemd (no Docker containers estándar)
- Para Rocky Linux: habilitar EPEL si es necesario para Go
- Documenta cualquier diferencia de comportamiento entre distribuciones
- Si encuentras bugs, reporta en el archivo correspondiente o crea issues

## Referencias

- [PLAN_DESARROLLO.md](PLAN_DESARROLLO.md) - Plan completo Fase 1.2
- [docs/installation.md](../docs/installation.md) - Documentación de instalación actualizada
- Systemd docs: `man systemd.service`, `man systemctl`
