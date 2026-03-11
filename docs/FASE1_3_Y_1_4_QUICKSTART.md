# Fase 1.3 y 1.4 - Guía Rápida de Instalación

## 🚀 Instalación Rápida

### 1. Aplicar Migraciones de Base de Datos

```bash
cd /home/mloco/Escritorio/LAMS/server
sudo ./apply_phase_1_3_1_4_migrations.sh
```

### 2. Reiniciar Servicios

```bash
# Backend (si usa Docker)
cd /home/mloco/Escritorio/LAMS
docker-compose restart server

# Agente en cada host monitoreado
sudo systemctl restart lams-agent
```

### 3. Verificar Funcionamiento

**Backend:**
```bash
# Verificar que endpoints de notificaciones responden
curl http://localhost:8000/api/v1/notifications/ \
  -H "Authorization: Bearer $TOKEN"

# Verificar que endpoints de comandos responden
curl http://localhost:8000/api/v1/commands/server01/pending \
  -H "Authorization: Bearer $TOKEN"
```

**Frontend:**
- Accede a http://localhost:3000
- Ve a **Notificaciones** en el sidebar
- Deberías ver el formulario para crear configuraciones

**Agente:**
```bash
# Ver logs del agente
sudo journalctl -u lams-agent -f

# Deberías ver líneas como:
#   Starting command polling (30s interval)...
```

---

## 📧 Configurar Notificaciones por Email

### 1. Obtener Credenciales SMTP

**Gmail:** Usa "App Passwords"
1. Ve a https://myaccount.google.com/security
2. Habilita verificación en 2 pasos
3. Genera una "App Password" para "Mail"
4. Usa esa contraseña (no tu contraseña de Gmail)

**SendGrid:** Crea una API Key en https://sendgrid.com

### 2. Crear Configuración en Dashboard

1. Ve a **Notificaciones** → `➕ Nuevo Canal de Notificación`
2. Selecciona **Proveedor:** Email (SMTP)
3. Rellena:
   - `smtp_host`: smtp.gmail.com (o smtp.sendgrid.net)
   - `smtp_port`: 587
   - `smtp_user`: tu-email@gmail.com
   - `smtp_password`: tu-app-password
   - `from_email`: tu-email@gmail.com
   - `to_email`: destinatario@ejemplo.com
4. Selecciona **Severidad:** (todas, warning+, o solo critical)
5. Click **✓ Crear**
6. Click **🧪 Probar** → deberías recibir un email de prueba

---

## 💬 Configurar Notificaciones por Slack

### 1. Crear Webhook en Slack

1. Ve a https://api.slack.com/apps
2. Click **Create New App** → From scratch
3. Nombre: "LAMS Monitor" → Selecciona workspace
4. **Incoming Webhooks** → Activate
5. **Add New Webhook to Workspace** → Selecciona canal (ej. #devops-alerts)
6. Copia la Webhook URL (https://hooks.slack.com/services/...)

### 2. Crear Configuración en Dashboard

1. Ve a **Notificaciones** → `➕ Nuevo Canal de Notificación`
2. Selecciona **Proveedor:** Slack
3. Rellena:
   - `webhook_url`: (pega la URL copiada)
   - `username`: LAMS Monitor (opcional)
   - `icon_emoji`: :rotating_light: (opcional)
4. Selecciona **Severidad**
5. Click **✓ Crear**
6. Click **🧪 Probar** → deberías ver mensaje en canal de Slack

---

## 🎮 Configurar Notificaciones por Discord

### 1. Crear Webhook en Discord

1. Abre Discord → Ve al servidor donde quieres recibir alertas
2. Click derecho en canal → **Editar Canal**
3. **Integraciones** → **Webhooks** → **Crear Webhook**
4. Nombre: "LAMS Alerts"
5. Copia la **URL del Webhook**

### 2. Crear Configuración en Dashboard

1. Ve a **Notificaciones** → `➕ Nuevo Canal de Notificación`
2. Selecciona **Proveedor:** Discord
3. Rellena:
   - `webhook_url`: (pega la URL copiada)
   - `username`: LAMS Monitor (opcional)
4. Selecciona **Severidad**
5. Click **✓ Crear**
6. Click **🧪 Probar** → deberías ver mensaje en canal de Discord

---

## 🐳 Usar Control Remoto de Docker

### 1. Verificar que Agente Tiene Acceso a Docker

```bash
# En el host monitoreado
sudo docker ps  # Debe funcionar sin errores

# Ver logs del agente
sudo journalctl -u lams-agent -f
# Debe mostrar: "Starting command polling (30s interval)..."
```

### 2. Controlar Contenedores desde Dashboard

**Opción A: Vista Docker**
1. Dashboard → **Docker** en sidebar
2. Selecciona un host con contenedores
3. Verás lista de contenedores con botones:
   - 🟢 **Start** (si está stopped)
   - 🔴 **Stop** (si está running)
   - 🔄 **Restart** (siempre disponible)
4. Click en botón → acción se ejecuta en < 30 segundos

**Opción B: Vista Detallada del Host**
1. Dashboard → **Hosts** → Click en **Ver Detalles** de un host
2. Scroll a sección **Contenedores Docker**
3. Mismos botones de control disponibles

### 3. Verificar Ejecución

**En Dashboard:**
- Estado del contenedor se actualiza automáticamente
- Puedes ver botones cambiar según estado

**En Host Remoto:**
```bash
docker ps -a
# El contenedor debe reflejar la acción realizada
```

**En Logs del Agente:**
```bash
sudo journalctl -u lams-agent -n 50
# Busca líneas como:
#   Executing command: docker_start on target abc123
#   Container abc123 started successfully
```

---

## 🧪 Probar Sistema de Notificaciones

### 1. Crear Regla de Alerta de Prueba

```bash
# Crear regla con umbral bajo para que se dispare pronto
curl -X POST "http://localhost:8000/api/v1/alert-rules/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "metric_name": "cpu_usage",
    "operator": ">",
    "threshold": 5,
    "severity": "critical",
    "duration_minutes": 1
  }'
```

O desde el dashboard:
1. **Reglas** → `➕ Nueva Regla`
2. Métrica: `cpu_usage`
3. Operador: `>`
4. Umbral: `5` (bajo para que se dispare fácil)
5. Severidad: `critical`
6. Duración: `1` minuto
7. Click **✓ Crear**

### 2. Esperar a que se Dispare

- El motor de alertas evalúa cada 60 segundos
- Si CPU > 5%, creará una alerta
- Automáticamente enviará notificaciones a todos los canales configurados

### 3. Verificar Recepción

- **Email:** Revisa buzón de entrada
- **Slack:** Revisa canal configurado
- **Discord:** Revisa canal configurado

**Contenido del mensaje:**
```
🚨 LAMS Alert - CRITICAL

Host: server01
Metric: cpu_usage
Value: 12.45
Time: 2026-03-10 15:30:00 UTC
Message: cpu_usage exceeded threshold (12.45 > 5)
```

---

## 🔧 Troubleshooting

### Notificaciones No Llegan

**Email:**
```bash
# Ver logs del servidor
docker logs lams-server | grep -i smtp
docker logs lams-server | grep -i notification

# Errores comunes:
# - "SMTP authentication failed": Password incorrecta o no es App Password
# - "Connection refused": smtp_host o smtp_port incorrectos
# - "TLS error": Probar smtp_port 465 en lugar de 587
```

**Slack/Discord:**
```bash
# Ver logs
docker logs lams-server | grep -i webhook

# Errores comunes:
# - "Invalid webhook": URL copiada incorrectamente
# - "401 Unauthorized": Webhook eliminado o deshabilitado
# - "404 Not Found": URL no es de webhook de Slack/Discord
```

**Verificar configuración:**
```bash
# Ver todas las configuraciones de notificación
curl http://localhost:8000/api/v1/notifications/ \
  -H "Authorization: Bearer $TOKEN"

# Ver si enabled=true y severity_filter es correcto
```

### Comandos Docker No Se Ejecutan

**Agente no está polling:**
```bash
# Ver logs del agente
sudo journalctl -u lams-agent -f

# Debe mostrar cada 30 segundos:
#   (esperando comandos)

# Si no muestra nada, reiniciar:
sudo systemctl restart lams-agent
```

**Agente no tiene permisos para Docker:**
```bash
# Verificar acceso
sudo docker ps

# Si funciona con sudo pero no sin él:
sudo usermod -aG docker lams-agent-user
sudo systemctl restart lams-agent
```

**Comandos quedando en estado pending:**
```bash
# Ver comandos en BD
sudo -u postgres psql lams_db -c "SELECT * FROM remote_commands WHERE status='pending';"

# Si hay muchos en pending:
# 1. Verificar que agente está corriendo
# 2. Verificar que puede conectar al servidor
# 3. Ver logs del agente para errores
```

---

## 📖 Documentación Completa

Ver [FASE1_3_Y_1_4_COMPLETADA.md](./FASE1_3_Y_1_4_COMPLETADA.md) para:
- Arquitectura detallada
- Código de implementación
- Todos los endpoints API
- Casos de uso avanzados
- Consideraciones de seguridad

---

## 🎉 ¡Listo!

Ahora tienes:
- ✅ Notificaciones automáticas por Email, Slack y Discord
- ✅ Control remoto de contenedores Docker
- ✅ Latencia < 30 segundos para comandos remotos
- ✅ Sistema totalmente funcional

Para soporte o preguntas, revisa los logs del servidor y agente.
