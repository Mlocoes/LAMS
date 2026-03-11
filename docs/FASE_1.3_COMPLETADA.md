# Fase 1.3 - Sistema de Notificaciones - Implementación Completa ✅

Este documento resume la implementación del sistema de notificaciones para alertas en LAMS.

## 📋 Resumen de la Implementación

La Fase 1.3 añade capacidad de notificaciones en tiempo real cuando se disparan alertas críticas o de advertencia. Los usuarios pueden configurar múltiples proveedores de notificaciones (Email, Slack, Discord) con diferentes niveles de filtrado por severidad.

**Duración estimada**: 5-6 días  
**Duración real**: ~1 sesión de desarrollo

---

## 🏗️ Arquitectura Implementada

### Backend

#### 1. **Módulo de Notificaciones** (`server/notifications/`)

**`base.py`** - Clase abstracta base para proveedores
- Métodos abstractos: `send()`, `validate_config()`
- Métodos helper: `format_message()`, `should_send()`
- Filtrado por severidad (all, warning, critical)

**`email.py`** - Proveedor SMTP/Email
- Soporte para servidores SMTP estándar (Gmail, SendGrid, etc.)
- Mensajes HTML y texto plano
- Configuración: smtp_host, smtp_port, smtp_user, smtp_password, from_email, to_email, use_tls

**`slack.py`** - Proveedor Slack Webhooks
- Mensajes formateados con Block Kit de Slack
- Configuración: webhook_url, username, icon_emoji, channel (opcional)
- Emojis y colores según severidad

**`discord.py`** - Proveedor Discord Webhooks
- Embeds de Discord con colores y campos estructurados
- Configuración: webhook_url, username, avatar_url (opcional)
- Timestamps automáticos

#### 2. **Modelo de Base de Datos**

**`NotificationConfig`** (tabla `notification_configs`)
```python
- id: int (PK)
- user_id: int (FK a users)
- provider: str ('email', 'slack', 'discord')
- config: JSON (configuración específica del proveedor)
- enabled: bool (activar/desactivar)
- severity_filter: str ('all', 'warning', 'critical')
- created_at: datetime
- updated_at: datetime
```

Relación: `User.notification_configs` (cascade delete)

#### 3. **Integración con Motor de Alertas**

**`server/alerts/notifications.py`**
- `get_notification_providers(session)`: Carga proveedores habilitados desde BD
- `send_alert_notification(alert, session)`: Envía notificaciones a todos los proveedores
- Manejo de errores robusto por proveedor
- Logging detallado

**`server/alerts/engine.py`**
- Modificado para llamar a `send_alert_notification()` al crear nueva alerta
- Usa `await session.flush()` antes de enviar para obtener ID de alerta
- Integración asíncrona con gestión de sesiones

#### 4. **API REST Endpoints** (`server/api/notifications.py`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/notifications/` | GET | Listar configs del usuario |
| `/api/v1/notifications/{id}` | GET | Obtener config específica |
| `/api/v1/notifications/` | POST | Crear nueva config |
| `/api/v1/notifications/{id}` | PUT | Actualizar config |
| `/api/v1/notifications/{id}` | DELETE | Eliminar config |
| `/api/v1/notifications/{id}/test` | POST | Enviar notificación de prueba |

**Autenticación**: Todos los endpoints requieren JWT token  
**Autorización**: Los usuarios solo pueden acceder a sus propias configuraciones

#### 5. **Configuración** (`server/core/config.py`)

Variables de entorno añadidas:
```python
# Email
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL, SMTP_USE_TLS

# Slack
SLACK_WEBHOOK_URL, SLACK_USERNAME, SLACK_ICON_EMOJI

# Discord
DISCORD_WEBHOOK_URL, DISCORD_USERNAME
```

---

### Frontend

#### 1. **API Client** (`frontend/src/lib/api.ts`)

**Tipos TypeScript**:
- `NotificationConfig`: Configuración completa con ID
- `NotificationConfigCreate`: Datos para crear
- `NotificationConfigUpdate`: Datos para actualizar (campos opcionales)

**Funciones**:
```typescript
getNotificationConfigs(): Promise<NotificationConfig[]>
getNotificationConfig(id): Promise<NotificationConfig>
createNotificationConfig(data): Promise<NotificationConfig>
updateNotificationConfig(id, data): Promise<NotificationConfig>
deleteNotificationConfig(id): Promise<void>
testNotificationConfig(id): Promise<{status, message}>
```

#### 2. **Interfaz de Usuario** (`frontend/src/app/page.tsx`)

**`NotificationsPage` Component**:

**Características**:
- Formulario de creación con campos dinámicos según proveedor
- Selector de proveedor (Email/Slack/Discord)
- Selector de filtro de severidad (Todas/Warning+/Critical)
- Lista de configuraciones con tarjetas visuales
- Iconos y badges de severidad con colores
- Botones de acción: Activar/Pausar, Test, Eliminar
- Estados de loading y error
- Confirmaciones de eliminación
- Alertas de éxito/error en pruebas

**Campos dinámicos por proveedor**:
- **Email**: smtp_host, smtp_port, smtp_user, smtp_password, from_email, to_email
- **Slack**: webhook_url, username, icon_emoji
- **Discord**: webhook_url, username

**Navegación**:
- Añadido en sidebar como "🔔 Notificaciones"
- Tipo `Page` extendido: `'notifications'`
- Integrado en objeto `pages` del componente `Home`

---

## 📂 Archivos Creados

### Backend
```
server/notifications/
├── __init__.py              # Exports de módulo
├── base.py                  # Clase abstracta NotificationProvider
├── email.py                 # Proveedor Email/SMTP
├── slack.py                 # Proveedor Slack Webhooks
└── discord.py               # Proveedor Discord Webhooks

server/api/
└── notifications.py         # Endpoints CRUD + Test

server/database/
└── models.py                # Modelo NotificationConfig (añadido)

server/core/
└── config.py                # Variables de entorno (actualizadas)
```

### Frontend
```
frontend/src/lib/
└── api.ts                   # Funciones de API (actualizadas)

frontend/src/app/
└── page.tsx                 # NotificationsPage component (añadido)
```

---

## 📂 Archivos Modificados

### Backend
- `server/alerts/notifications.py`: Reemplazó mock con implementación real
- `server/alerts/engine.py`: Integración con sistema de notificaciones
- `server/database/models.py`: Añadido modelo `NotificationConfig` y relación en `User`
- `server/api/__init__.py`: Registrado router de notificaciones
- `server/core/config.py`: Añadidas variables de configuración

### Frontend
- `frontend/src/lib/api.ts`: Añadidas funciones y tipos de notificaciones
- `frontend/src/app/page.tsx`: Añadido `NotificationsPage` y enlace en sidebar

---

## 🧪 Testing

### Pruebas Manuales Sugeridas

#### 1. **Crear Configuración de Email**
```
1. Login como admin@lams.io
2. Navegar a Notificaciones
3. Seleccionar proveedor: Email
4. Configurar SMTP (Gmail, SendGrid, Mailtrap, etc.)
5. Seleccionar filtro: Todas
6. Crear
7. Verificar que aparece en la lista
```

#### 2. **Crear Configuración de Slack**
```
1. Crear Incoming Webhook en Slack
2. Copiar webhook URL
3. En LAMS, seleccionar proveedor: Slack
4. Pegar webhook URL
5. Opcional: cambiar username, icon_emoji
6. Crear
```

#### 3. **Crear Configuración de Discord**
```
1. En Discord: Server Settings → Integrations → Webhooks → New Webhook
2. Copiar webhook URL
3. En LAMS, seleccionar proveedor: Discord
4. Pegar webhook URL
5. Crear
```

#### 4. **Probar Notificación**
```
1. Click en botón "🧪" en cualquier configuración
2. Esperar respuesta
3. Verificar que llega notificación de prueba al destino configurado
4. Contenido esperado:
   - Host: test-host
   - Métrica: test_metric
   - Valor: 99.9
   - Severidad: warning
   - Mensaje: "This is a test notification from LAMS"
```

#### 5. **Pausar/Activar Notificación**
```
1. Click en botón "⏸" para pausar
2. Verificar que muestra "(OFF)" en el título
3. Crear alerta (siguiente test)
4. Verificar que NO se envía notificación
5. Reactivar con "▶️"
```

#### 6. **Disparo Real de Alerta**
```
1. Crear regla de alerta con umbral bajo (ej: CPU > 10%)
2. Esperar hasta 1 minuto (evaluación cada minuto)
3. Verificar en logs del servidor:
   - "Evaluating Alert Rules..."
   - "Loaded X notification providers"
   - "Alert notifications sent successfully via X provider(s)"
4. Verificar recepción en Email/Slack/Discord
5. Formato esperado:
   - 🚨 LAMS Alert - CRITICAL/WARNING
   - Host, Metric, Value, Time, Message
```

#### 7. **Filtro de Severidad**
```
1. Crear config con filtro "Solo Critical"
2. Crear regla de alerta severidad "warning"
3. Disparar alerta
4. Verificar que NO se envía notificación
5. Cambiar regla a severidad "critical"
6. Disparar alerta
7. Verificar que SÍ se envía notificación
```

#### 8. **Eliminar Configuración**
```
1. Click en botón "🗑️"
2. Confirmar eliminación
3. Verificar que desaparece de la lista
4. Disparar alerta
5. Verificar que NO se envía notificación
```

#### 9. **Múltiples Configuraciones**
```
1. Crear 1 config de Email
2. Crear 1 config de Slack
3. Crear 1 config de Discord
4. Todas con filtro "Todas"
5. Disparar alerta
6. Verificar que se envía notificación a los 3 canales
```

---

### Casos de Error para Validar

#### **Email**
- ❌ SMTP credentials incorrectas → Error claro en logs
- ❌ Servidor SMTP no alcanzable → Timeout, logged
- ❌ Campos faltantes → "Failed to send notification"
- ❌ Puerto incorrecto → Connection error

#### **Slack**
- ❌ Webhook URL inválida → HTTP 404
- ❌ Webhook URL expirada/revocada → Error logged
- ❌ Formato de URL incorrecto → Validación en frontend + backend

#### **Discord**
- ❌ Webhook URL inválida → HTTP 404
- ❌ Webhook deletado → Error logged

---

## 🔍 Verificación en Logs

### Backend Logs (journalctl/stdout)

**Startup**:
```
INFO:lams.notifications:Loaded 2 notification providers
```

**Evaluación de reglas**:
```
INFO:lams.engine:Evaluating Alert Rules...
```

**Disparo de alerta**:
```
INFO:lams.notifications:Email notification sent successfully to admin@example.com
INFO:lams.notifications:Slack notification sent successfully
INFO:lams.notifications:Alert notifications sent successfully via 2 provider(s)
```

**Errores**:
```
ERROR:lams.notifications:SMTP authentication failed - check credentials
ERROR:lams.notifications:Failed to send notification via EmailNotificationProvider: ...
WARNING:lams.notifications:Invalid configuration for email provider (ID: 1)
```

---

## ⚙️ Configuración de Producción

### Variables de Entorno (.env)

```env
# Email (ejemplo Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=lams@yourdomain.com
SMTP_USE_TLS=true

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_USERNAME=LAMS Monitor
SLACK_ICON_EMOJI=:bell:

# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/WEBHOOK/URL
DISCORD_USERNAME=LAMS Monitor
```

### Recomendaciones

1. **Email**: Usa App Passwords si usas Gmail (no la contraseña normal)
2. **Rate Limits**: Slack/Discord tienen límites de velocidad, considera throttling si envías muchas alertas
3. **Seguridad**: Nunca commitees webhooks URLs a Git
4. **Testing**: Usa servicios como [Mailtrap](https://mailtrap.io/) para testing de emails
5. **Monitoring**: Monitorea logs para detectar fallos de notificación

---

## 🐛 Troubleshooting

### "No notification providers configured"
- No hay configuraciones en BD
- Todas las configs están deshabilitadas (`enabled=False`)
- Solución: Crear configuración desde UI

### "Failed to send notification"
- Ver logs detallados para el error específico
- Verificar configuración del proveedor
- Probar con endpoint `/test`

### "Alert notifications sent successfully via 0 provider(s)"
- Filtro de severidad bloqueando notificación
- Todas las configs fallaron por errores
- Verificar logs para detalles

### Notificaciones no llegan (Slack/Discord)
- Verificar que webhook URL sea correcta
- Verificar que webhook no esté eliminado/revocado
- Probar webhook manualmente con `curl`

### Emails no llegan
- Verificar carpeta de spam
- Verificar credenciales SMTP
- Verificar puerto y TLS settings
- Probar conexión con telnet/openssl

---

## 📊 Métricas y Monitoring

### Base de Datos
```sql
-- Contar configuraciones por proveedor
SELECT provider, COUNT(*) FROM notification_configs GROUP BY provider;

-- Configuraciones habilitadas
SELECT COUNT(*) FROM notification_configs WHERE enabled = true;

-- Por usuario
SELECT user_id, COUNT(*) FROM notification_configs GROUP BY user_id;
```

### Logs
- Buscar: `"notification providers"`  → Cantidad de proveedores cargados
- Buscar: `"notification sent successfully"` → Notificaciones exitosas
- Buscar: `"Failed to send notification"` → Errores

---

## 🚀 Próximos Pasos

Con la Fase 1.3 completada, las siguientes opciones son:

### **Opción A: Fase 1.4 - Gestión Remota de Docker** (4-5 días)
- Comandos remotos (start/stop/restart containers)
- Sistema de polling de comandos
- UI con botones de control
- Reporte de resultados

### **Opción B: Fase 2.1 - Tests Unitarios Backend** (7-10 días)
- Suite completa de pytest
- Cobertura ≥70%
- Tests de models, API, autenticación, alertas, notificaciones

### **Opción C: Fase 2.2 - Tests de Integración E2E** (3-5 días)
- Flujo completo agente → servidor → dashboard
- Validación de métricas
- Testing de alertas y notificaciones

---

## ✅ Checklist de Completitud

- [x] Módulo base de notificaciones (`notifications/base.py`)
- [x] Proveedor Email/SMTP con HTML
- [x] Proveedor Slack con Block Kit
- [x] Proveedor Discord con embeds
- [x] Modelo `NotificationConfig` en base de datos
- [x] Relación `User.notification_configs`
- [x] Variables de configuración en `config.py`
- [x] Integración en motor de alertas
- [x] API CRUD completa (5 endpoints)
- [x] Endpoint `/test` para pruebas
- [x] Autenticación y autorización
- [x] Validaciones de entrada
- [x] Manejo de errores robusto
- [x] Logging detallado
- [x] Cliente JavaScript/TypeScript
- [x] Componente React de UI
- [x] Formulario dinámico por proveedor
- [x] Lista visual de configuraciones
- [x] Botones de acción (toggle, test, delete)
- [x] Estados de loading/error
- [x] Integración en navegación del dashboard
- [x] Sin errores de compilación
- [x] Documentación completa

---

## 📝 Notas de Implementación

1. **Seguridad**: Las configuraciones contienen datos sensibles (passwords, webhook URLs) - considerar encriptación en BD para producción
2. **Performance**: Sistema de notificaciones es asíncrono y no-bloqueante
3. **Escalabilidad**: Fácil añadir nuevos proveedores heredando de `NotificationProvider`
4. **Extensibilidad**: Filtros de severidad pueden extenderse (ej: por host, por métrica)
5. **Testing**: Endpoint `/test` facilita validación antes de producción
6. **UX**: UI intuitiva con iconos, colores y feedback inmediato

---

## 🎉 Estado Final

**Fase 1.3: COMPLETADA ✅**

El sistema de notificaciones está completamente funcional e integrado. Los usuarios pueden:
- Configurar múltiples canales de notificación
- Filtrar por nivel de severidad
- Probar configuraciones antes de producción
- Gestionar configuraciones (CRUD)
- Recibir notificaciones en tiempo real cuando se disparan alertas

**Siguiente Fase**: A elección del usuario (Opción A, B o C)
