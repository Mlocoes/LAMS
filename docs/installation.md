# Guía de Instalación de LAMS

## Prerrequisitos
- Servidor central con **Docker** y **Docker Compose** instalados (Ubuntu 20.04+, Debian 11+, Rocky Linux 9+).
- Máquinas a monitorizar con conectividad saliente HTTP (Puerto `8000`) hacia la IP del servidor central.

## Instalación del Servidor Central
1. Clona temporalmente el repositorio o descarga los archivos fuentes en `/home/usuario/LAMS`.
2. Opcional: Configura tus credenciales o token JWT en `./server/.env` (no incluido, usará defaults).
3. Levanta el ecosistema de la plataforma en demonio:
   ```bash
   cd /home/usuario/LAMS
   docker-compose up -d --build
   ```
4. El servidor mapeará:
   - Dashboard UI: `http://localhost:3000`
   - FastAPI REST API: `http://localhost:8000/docs`
   - PostgreSQL: Puerto `5432`

## Instalación de Agentes Remotos (Monitor Agent)

### Método 1: Instalación Automatizada con Systemd (Recomendado)

El método recomendado para producción utiliza systemd para gestionar el agente como un servicio persistente.

#### Prerrequisitos
- Sistema Linux con **systemd** (Ubuntu 20.04+, Debian 11+, Rocky Linux 9+, CentOS 8+)
- Compilador **Go 1.21+** instalado
- Permisos de **root/sudo**
- Conectividad HTTP hacia el servidor LAMS

#### Instalación Interactiva

1. Copia el script de instalación al servidor destino:
   ```bash
   scp agent/install-agent.sh user@host.remoto:/tmp/
   ssh user@host.remoto
   ```

2. Ejecuta el script con modo interactivo:
   ```bash
   sudo /tmp/install-agent.sh
   ```

3. Responde a los prompts:
   - **URL del servidor LAMS**: `http://IP_SERVIDOR_CENTRAL:8000`
   - **Token de autenticación**: Tu token secreto configurado en el servidor
   - **Host ID**: Identificador único (por defecto: hostname del sistema)
   - **Intervalo de métricas**: Segundos entre recolecciones (por defecto: 15)

El script realizará:
- Compilación del binario Go desde `agent/main.go`
- Instalación del binario en `/usr/local/bin/lams-agent`
- Creación de configuración en `/etc/lams/agent.conf`
- Configuración del servicio systemd en `/etc/systemd/system/lams-agent.service`
- Habilitación y arranque automático del servicio

#### Instalación No Interactiva (CI/CD, Ansible)

Para automatización o despliegues masivos:
```bash
sudo ./install-agent.sh \
  --server "http://10.0.1.100:8000" \
  --token "MY_SECRET_KEY" \
  --host-id "web-server-01" \
  --interval 15
```

#### Gestión del Servicio

Una vez instalado, puedes gestionar el agente como cualquier servicio systemd:

```bash
# Ver estado del servicio
sudo systemctl status lams-agent

# Ver logs en tiempo real
sudo journalctl -u lams-agent -f

# Reiniciar el servicio
sudo systemctl restart lams-agent

# Detener el servicio
sudo systemctl stop lams-agent

# Deshabilitar inicio automático
sudo systemctl disable lams-agent
```

#### Desinstalación

Para remover completamente el agente:
```bash
# Desinstalación completa
sudo ./uninstall-agent.sh

# Mantener configuración (para reinstalación)
sudo ./uninstall-agent.sh --keep-config

# Desinstalar sin confirmación
sudo ./uninstall-agent.sh --force
```

#### Archivos de Configuración

El agente instalado utiliza:
- **Binario**: `/usr/local/bin/lams-agent`
- **Configuración**: `/etc/lams/agent.conf`
- **Servicio systemd**: `/etc/systemd/system/lams-agent.service`
- **Logs**: `journalctl -u lams-agent`

Para modificar la configuración después de instalar:
```bash
sudo nano /etc/lams/agent.conf
sudo systemctl restart lams-agent
```

### Método 2: Instalación Manual (Desarrollo/Testing)

Para entornos de desarrollo o testing sin systemd:

1. Compila e instala el binario:
   ```bash
   cd /home/usuario/LAMS/agent
   go build -o lams-agent main.go
   sudo mv lams-agent /usr/local/bin/
   ```

2. Ejecuta manualmente con variables de entorno:
   ```bash
   LAMS_SERVER_URL="http://IP_SERVIDOR_CENTRAL:8000" \
   LAMS_HOST_ID="server-web-01" \
   LAMS_AGENT_TOKEN="MY_SECRET_KEY" \
   LAMS_METRICS_INTERVAL=15 \
   lams-agent
   ```

> **Nota**: Este método NO proporciona persistencia ni arranque automático. Usa el Método 1 para producción.

### Troubleshooting

#### Error: "systemd not found"
- Verifica que systemd esté instalado: `systemctl --version`
- Para sistemas sin systemd (Alpine, algunos contenedores), usa Método 2

#### Error: "Go compiler not found"
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install golang-go

# Rocky Linux/CentOS
sudo dnf install golang

# Verificar instalación
go version
```

#### Error: "Permission denied"
- Asegúrate de ejecutar el script con `sudo`
- Verifica permisos: `chmod +x install-agent.sh`

#### El servicio no arranca
```bash
# Ver errores detallados
sudo journalctl -u lams-agent -n 50

# Verificar configuración
cat /etc/lams/agent.conf

# Probar manualmente
sudo /usr/local/bin/lams-agent
```

#### Conectividad con el servidor
```bash
# Test de conectividad
curl -v http://IP_SERVIDOR_CENTRAL:8000/health

# Verificar firewall
sudo ufw status
sudo firewall-cmd --list-all
```
