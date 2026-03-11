# Fase 3.3.7: Página de Configuración Administrativa

**Fecha de implementación:** 2025-01-XX  
**Duración:** 2 días  
**Estado:** ✅ COMPLETADO

## Resumen

Implementación de una página de configuración administrativa completa que permite gestionar módulos, parámetros de seguridad, configuración del sistema y notificaciones. La página incluye control de acceso exclusivo para administradores y persistencia de configuración en localStorage.

## Objetivos

1. ✅ Proporcionar interfaz centralizada para administración del sistema
2. ✅ Permitir activar/desactivar módulos dinámicamente
3. ✅ Configurar parámetros de seguridad (timeout de sesión, auto-refresh)
4. ✅ Gestionar retención de métricas y agregación de datos
5. ✅ Configurar preferencias de notificaciones
6. ✅ Control de acceso exclusivo para usuarios administradores
7. ✅ Persistencia de configuración en cliente (localStorage)

## Componentes Implementados

### 1. SettingsPage Component

**Ubicación:** Integrado en `frontend/src/app/page.tsx`

**Características:**
- **4 pestañas organizadas:**
  - 📦 **Modules:** Control de visibilidad de módulos del dashboard
  - 🔒 **Security:** Parámetros de seguridad y autenticación
  - ⚙️ **System:** Configuración del sistema y rendimiento
  - 🔔 **Notifications:** Preferencias de notificaciones

- **Control de acceso:**
  - Verificación de rol de administrador
  - Componente AccessDenied para usuarios no autorizados
  - Redirección automática si no hay acceso

- **Persistencia:**
  - Almacenamiento en localStorage con clave `lams_settings`
  - Carga automática de configuración al montar componente
  - Guardado automático al cambiar cualquier configuración

### 2. Configuración por Pestaña

#### Pestaña Modules (📦)

Control de visibilidad de los módulos del dashboard:

| Módulo | Descripción | Control |
|--------|-------------|---------|
| Dashboard | Vista general del sistema | Toggle |
| Hosts | Gestión de hosts monitoreados | Toggle |
| Alerts | Sistema de alertas | Toggle |
| Docker | Gestión de contenedores | Toggle |
| Rules | Reglas de alertas | Toggle |
| Notifications | Centro de notificaciones | Toggle |
| Users | Gestión de usuarios | Toggle |

**Funcionalidades:**
- Lista visual con iconos por módulo
- Descripción clara de cada módulo
- Toggle switch para activar/desactivar
- Estado guardado automáticamente

#### Pestaña Security (🔒)

Parámetros de seguridad del sistema:

| Parámetro | Tipo | Rango | Valor Defecto | Descripción |
|-----------|------|-------|---------------|-------------|
| Session Timeout | Slider | 5-1440 min | 30 min | Tiempo de inactividad antes de logout |
| Auto Refresh | Slider | 5-300 seg | 30 seg | Intervalo de actualización automática |
| Password Policy | Toggle | - | Enabled | Política de contraseñas fuertes |
| Two-Factor Auth | Toggle | - | Disabled | Autenticación de dos factores (2FA) |

**Características:**
- Slider con valores en tiempo real
- Indicadores de unidad (minutos/segundos)
- Rangos validados para evitar configuraciones problemáticas
- Notificación de cambios aplicados

#### Pestaña System (⚙️)

Configuración del sistema y rendimiento:

| Parámetro | Tipo | Rango | Valor Defecto | Descripción |
|-----------|------|-------|---------------|-------------|
| Metrics Retention | Slider | 7-365 días | 30 días | Tiempo de retención de métricas detalladas |
| Data Aggregation | Slider | 1-30 días | 7 días | Días antes de agregar métricas |
| Cleanup Hour | Slider | 0-23 h | 2 h | Hora para tareas de limpieza |
| Max Hosts Per User | Slider | 1-100 | 10 | Máximo de hosts por usuario |
| Enable Docker | Toggle | - | Enabled | Habilitar monitoreo de Docker |

**Características:**
- Parámetros de optimización de rendimiento
- Control de crecimiento de base de datos
- Configuración de tareas programadas
- Límites de recursos por usuario

#### Pestaña Notifications (🔔)

Preferencias de notificaciones:

| Canal | Estado | Configuración adicional |
|-------|--------|------------------------|
| Email | Toggle | Dirección de email |
| Slack | Toggle | Webhook URL |
| Discord | Toggle | Webhook URL |

**Configuración adicional:**
- **Default Severity:** Severidad mínima para notificaciones
  - Options: low, medium, high, critical
  - Default: medium

**Características:**
- Activación/desactivación por canal
- Configuración de webhooks para integraciones
- Filtrado por severidad de alertas
- Validación de configuración guardada

## Estructura de Datos

### Formato de localStorage

```typescript
interface LAMSSettings {
  // Modules
  modules: {
    dashboard: boolean;
    hosts: boolean;
    alerts: boolean;
    docker: boolean;
    rules: boolean;
    notifications: boolean;
    users: boolean;
  };
  
  // Security
  security: {
    sessionTimeout: number; // minutes (5-1440)
    autoRefresh: number; // seconds (5-300)
    passwordPolicy: boolean;
    twoFactorAuth: boolean;
  };
  
  // System
  system: {
    metricsRetentionDays: number; // days (7-365)
    aggregationDays: number; // days (1-30)
    cleanupHour: number; // hour (0-23)
    maxHostsPerUser: number; // count (1-100)
    enableDocker: boolean;
  };
  
  // Notifications
  notifications: {
    email: {
      enabled: boolean;
      address: string;
    };
    slack: {
      enabled: boolean;
      webhook: string;
    };
    discord: {
      enabled: boolean;
      webhook: string;
    };
    defaultSeverity: 'low' | 'medium' | 'high' | 'critical';
  };
}
```

### Valores por defecto

```typescript
const DEFAULT_SETTINGS = {
  modules: {
    dashboard: true,
    hosts: true,
    alerts: true,
    docker: true,
    rules: true,
    notifications: true,
    users: true,
  },
  security: {
    sessionTimeout: 30, // 30 minutos
    autoRefresh: 30, // 30 segundos
    passwordPolicy: true,
    twoFactorAuth: false,
  },
  system: {
    metricsRetentionDays: 30,
    aggregationDays: 7,
    cleanupHour: 2, // 2 AM
    maxHostsPerUser: 10,
    enableDocker: true,
  },
  notifications: {
    email: { enabled: false, address: '' },
    slack: { enabled: false, webhook: '' },
    discord: { enabled: false, webhook: '' },
    defaultSeverity: 'medium',
  },
};
```

## Integración con Dashboard

### 1. Actualización del Type Page

```typescript
type Page = 'dashboard' | 'hosts' | 'alerts' | 'docker' | 'rules' | 'notifications' | 'users' | 'settings';
```

### 2. Sidebar Navigation

Nuevo link agregado al array de navegación:

```typescript
const sidebarLinks = [
  // ... otros links
  { id: 'settings', label: 'Configuración', icon: '⚙️' },
];
```

### 3. Pages Record

```typescript
const pages: Record<Page, React.ReactNode> = {
  // ... otras páginas
  settings: <SettingsPage />,
};
```

## Diseño y Estilos

### Glassmorphism Theme

La página mantiene el diseño glassmorphism del dashboard:
- Backdrop blur effects
- Semi-transparent backgrounds
- Border con gradiente sutil
- Box-shadow para profundidad

### Responsive Design

- **Tab navigation:** Horizontal en desktop, colapsa en móvil
- **Form layouts:** Grid adaptativo para inputs y controles
- **Sliders:** Width 100% para adaptarse al contenedor
- **Toggles:** Flex layout con wrap automático

### Theme Support

Compatibilidad total con modo claro/oscuro:
- Variables CSS adaptativas
- Colores dinámicos según tema activo
- Transiciones suaves al cambiar tema

## Funcionalidades Adicionales

### 1. Funciones Helper

```typescript
// Obtener icono del módulo
function getModuleIcon(module: string): string {
  const icons: Record<string, string> = {
    dashboard: '📊',
    hosts: '🖥️',
    alerts: '🚨',
    docker: '🐳',
    rules: '📋',
    notifications: '🔔',
    users: '👤',
  };
  return icons[module] || '📦';
}

// Obtener descripción del módulo
function getModuleDescription(module: string): string {
  const descriptions: Record<string, string> = {
    dashboard: 'Vista general del sistema',
    hosts: 'Gestión de hosts monitoreados',
    alerts: 'Sistema de alertas',
    docker: 'Gestión de contenedores Docker',
    rules: 'Reglas de alertas y automatización',
    notifications: 'Centro de notificaciones',
    users: 'Gestión de usuarios y permisos',
  };
  return descriptions[module] || 'Sin descripción';
}
```

### 2. Validaciones

- **Session Timeout:** Min 5 minutos, Max 24 horas (1440 min)
- **Auto Refresh:** Min 5 segundos, Max 5 minutos (300 seg)
- **Metrics Retention:** Min 7 días, Max 1 año (365 días)
- **Aggregation Days:** Min 1 día, Max 30 días
- **Cleanup Hour:** 0-23 (formato 24h)
- **Max Hosts:** Min 1, Max 100 hosts por usuario

### 3. Control de Acceso

```typescript
function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  
  if (!isAdmin) {
    return <AccessDenied />;
  }
  
  // ... resto del componente
}
```

## Mejoras Futuras

### Backend Integration (Fase futura)

Para sincronización multi-dispositivo y persistencia robusta:

1. **API Endpoints:**
   - `GET /api/v1/settings` - Obtener configuración actual
   - `PUT /api/v1/settings` - Actualizar configuración completa
   - `PATCH /api/v1/settings/{section}` - Actualizar sección específica

2. **Database Schema:**
```sql
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    settings JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id)
);
```

3. **Migración de datos:**
   - Script para importar configuración de localStorage a DB
   - Sincronización bidireccional
   - Backup automático de configuración

### Funcionalidades Adicionales

1. **Export/Import de configuración:**
   - Exportar settings a JSON
   - Importar configuración desde archivo
   - Plantillas de configuración predefinidas

2. **Historial de cambios:**
   - Log de modificaciones con timestamp
   - Usuario que realizó cada cambio
   - Capacidad de revertir cambios

3. **Validación avanzada:**
   - Validación de webhooks antes de guardar
   - Test de conexión para integraciones
   - Advertencias de configuraciones problemáticas

4. **Permisos granulares:**
   - Control de qué configuraciones puede modificar cada admin
   - Solicitudes de aprobación para cambios críticos
   - Multi-tenancy con configuración por organización

## Testing

### Tests Recomendados

```typescript
describe('SettingsPage', () => {
  it('should show access denied for non-admin users', () => {
    // Test control de acceso
  });
  
  it('should load settings from localStorage', () => {
    // Test carga de configuración
  });
  
  it('should save settings on change', () => {
    // Test guardado automático
  });
  
  it('should validate slider ranges', () => {
    // Test validación de rangos
  });
  
  it('should toggle modules correctly', () => {
    // Test toggle de módulos
  });
  
  it('should switch between tabs', () => {
    // Test navegación de tabs
  });
});
```

### Casos de Uso

1. **Desactivar módulo Docker:**
   - Admin accede a Settings
   - Navega a pestaña Modules
   - Desactiva toggle de Docker
   - Configuración se guarda automáticamente
   - El módulo Docker desaparece del sidebar

2. **Configurar timeout de sesión:**
   - Admin accede a pestaña Security
   - Ajusta slider de Session Timeout a 60 minutos
   - Valor se actualiza en tiempo real
   - Settings se persisten en localStorage
   - Aplicación usa nuevo valor de timeout

3. **Configurar notificaciones por email:**
   - Admin accede a pestaña Notifications
   - Activa toggle de Email
   - Ingresa dirección de email
   - Selecciona severidad mínima (high)
   - Configuración se guarda automáticamente

## Documentación de Usuario

### Acceso a Configuración

1. Iniciar sesión como usuario administrador
2. Click en icono ⚙️ "Configuración" en sidebar
3. Seleccionar pestaña deseada
4. Modificar configuraciones según necesidad
5. Los cambios se guardan automáticamente

### Pestañas Disponibles

#### Modules (📦)
Control de visibilidad de módulos del dashboard. Desactivar un módulo lo oculta del sidebar y previene acceso a esa funcionalidad.

#### Security (🔒)
Parámetros de seguridad y autenticación:
- **Session Timeout:** Tiempo de inactividad antes de logout automático
- **Auto Refresh:** Frecuencia de actualización de datos en pantalla
- **Password Policy:** Requerir contraseñas fuertes
- **2FA:** Habilitar autenticación de dos factores

#### System (⚙️)
Configuración del sistema y optimización:
- **Metrics Retention:** Cuántos días mantener métricas detalladas
- **Data Aggregation:** Cuándo comenzar a agregar datos antiguos
- **Cleanup Hour:** Hora del día para ejecutar tareas de limpieza
- **Max Hosts Per User:** Límite de hosts que puede registrar cada usuario

#### Notifications (🔔)
Configurar canales de notificación y preferencias:
- Habilitar/deshabilitar cada canal (Email, Slack, Discord)
- Configurar webhooks para integraciones
- Establecer severidad mínima para recibir notificaciones

### Notas Importantes

- ⚠️ Solo usuarios administradores pueden acceder a configuración
- ⚠️ La configuración se guarda localmente en el navegador
- ⚠️ Limpiar datos del navegador eliminará la configuración
- ⚠️ Cambios en módulos son inmediatos pero requieren recarga de página

## Conclusión

La implementación de la página de configuración administrativa proporciona una interfaz centralizada y intuitiva para gestionar todos los aspectos del sistema LAMS. La persistencia en localStorage permite una configuración rápida y sin necesidad de backend adicional, mientras que la estructura modular facilita la futura migración a una solución basada en base de datos.

**Estado Final:** ✅ **COMPLETADO** - Fase 3.3.7
**Próximo paso:** Fase 3.3.5 - Responsive design para tablets/móviles
