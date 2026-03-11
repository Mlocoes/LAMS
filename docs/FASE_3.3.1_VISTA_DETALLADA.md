# Fase 3.3.1: Vista Detallada por Host

**Estado:** ✅ COMPLETADO  
**Fecha:** 9 de marzo de 2026  
**Duración:** 1 día

## Resumen

Se ha implementado una vista detallada completa para cada host registrado en el sistema LAMS. Esta vista muestra información exhaustiva del host, gráficos históricos de métricas con diferentes rangos temporales, contenedores Docker con controles de acción, y alertas específicas filtradas por host.

## Objetivos Cumplidos

✅ Página de vista detallada accesible vía ruta dinámica `/hosts/[id]`  
✅ Información completa del sistema (OS, kernel, CPU cores, memoria, host ID, última conexión)  
✅ Métricas actuales con indicadores visuales (CPU, Memoria, Disco, Temperatura)  
✅ Seis gráficos históricos usando ECharts (CPU, Memoria, Disco, Temperatura, Red RX/TX)  
✅ Selector de rango temporal (1h, 6h, 24h, 7d) con recarga automática  
✅ Lista de contenedores Docker con botones de control (Start/Stop/Restart)  
✅ Alertas activas filtradas por host  
✅ Navegación breadcrumb para volver al dashboard  
✅ Auto-refresh cada 15 segundos  
✅ Botón "Ver Detalles" en tabla de hosts del dashboard principal  

## Implementación Técnica

### 1. Estructura de Archivos

**Nuevo archivo creado:**
- `frontend/src/app/hosts/[id]/page.tsx` (~800 líneas)

**Archivos modificados:**
- `frontend/src/app/page.tsx`:
  - Añadido `import { useRouter } from 'next/navigation'`
  - Hook `useRouter()` en componente `HostsPage`
  - Nueva columna "Acciones" en tabla de hosts
  - Botón "Ver Detalles" con navegación a `/hosts/[id]`

### 2. Componentes Implementados

#### Componente Principal: `HostDetailPage`

```typescript
export default function HostDetailPage() {
  // Estado
  const [host, setHost] = useState<Host | null>(null);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [containers, setContainers] = useState<DockerContainer[]>([]);
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('6h');
  
  // Fetch con Promise.all paralelo
  // Auto-refresh cada 15 segundos
  // Filtrado de alertas por host_id en cliente
}
```

#### Componentes Auxiliares

1. **InfoItem**: Muestra información del host con icono y etiqueta
2. **MetricOverviewCard**: Card con métrica actual, barra de progreso y porcentaje
3. **ActionButton**: Botón de acción para contenedores Docker
4. **MetricChart**: Componente reutilizado de `@/components/MetricChart`

### 3. Funcionalidades Clave

#### a) Selector de Rango Temporal

```typescript
const limits: Record<typeof timeRange, number> = {
  '1h': 60,      // Último minuto durante 1 hora
  '6h': 360,     // Cada minuto durante 6 horas
  '24h': 1440,   // Cada minuto durante 24 horas
  '7d': 672      // Cada hora durante 7 días
};
```

Al cambiar el rango, se recarga la vista con más o menos puntos de datos según corresponda.

#### b) Control de Contenedores Docker

Los botones Start/Stop/Restart envían comandos remotos al agente:

```typescript
const handleDockerAction = async (containerId: string, action: 'start' | 'stop' | 'restart') => {
  await dockerAction(hostId, containerId, action);
  // Actualizar después de 3 segundos
  setTimeout(fetchData, 3000);
};
```

#### c) Gráficos Históricos

Se muestran 6 gráficos usando el componente `MetricChart`:

1. **CPU Usage** (%)
2. **Memory Used** (GB)
3. **Disk Usage** (%)
4. **CPU Temperature** (°C) - solo si disponible
5. **Network Received** (MB/s)
6. **Network Transmitted** (MB/s)

Cada gráfico tiene:
- Título con número de puntos de datos
- Tooltip con timestamp y valor
- Color temático según métrica
- Altura fija de 350px

#### d) Información del Host

Card con layout grid responsive mostrando:
- Sistema Operativo (con icono 💻)
- Kernel version (⚙️)
- CPU Cores (🔲)
- Memoria Total en GB (🧠)
- Host ID truncado (🔑)
- Última conexión formateada (🕐)

#### e) Métricas Actuales

Cards individuales con:
- Valor actual del recurso
- Porcentaje de uso
- Barra de progreso con colores semáforo:
  - Verde < 60%
  - Amarillo 60-80%
  - Rojo > 80%

### 4. Estilo Visual

El componente mantiene el diseño glassmorphic consistente con el resto del dashboard:

- Cards con `backdrop-filter: blur(10px)`
- Bordes con `rgba(255,255,255,0.1)`
- Gradientes de colores (#667eea, #10b981, #f59e0b, etc.)
- Animaciones suaves con `transition: all 0.3s ease`
- Hover effects en botones
- Badges con estados visuales (online/offline, severity)

### 5. Navegación

#### Desde el Dashboard Principal

En la tabla de hosts, nueva columna "Acciones" con botón:

```typescript
<button onClick={() => router.push(`/hosts/${h.id}`)}>
  Ver Detalles
</button>
```

#### Breadcrumb en Vista Detallada

Botón para volver al dashboard con efecto hover:

```typescript
<button onClick={() => router.push('/')}>
  ← Volver al Dashboard
</button>
```

### 6. Manejo de Estados

- **Loading inicial**: Spinner con mensaje "Cargando detalles del host..."
- **Error**: Mensaje de error con botón para volver
- **Sin datos**: Mensajes específicos según sección:
  - Métricas: "No hay datos históricos disponibles"
  - Docker: No se muestra sección si no hay contenedores
  - Alertas: "✅ No hay alertas activas para este host"

### 7. Performance

- **Fetch paralelo**: `Promise.all` para cargar host, métricas, alertas y contenedores simultáneamente
- **Auto-refresh inteligente**: Interval de 15s con cleanup automático
- **Lazy loading**: Componentes Docker solo si hay contenedores
- **Gráficos eficientes**: ECharts con renderizado optimizado

## Uso

### Acceso a la Vista Detallada

**Opción 1: Desde la tabla de hosts**
1. Ir a vista "Hosts" en el dashboard
2. Click en botón "Ver Detalles" de cualquier host
3. Se abre la vista detallada con URL `/hosts/{host_id}`

**Opción 2: URL directa**
```
https://lams.ejemplo.com/hosts/{host_id}
```

### Interacción

1. **Cambiar rango temporal**: Click en botones 1h / 6h / 24h / 7d
2. **Controlar Docker**: Botones Start/Stop/Restart en tabla de contenedores
3. **Volver al dashboard**: Click en "← Volver al Dashboard"
4. **Auto-refresh**: Datos se actualizan cada 15 segundos automáticamente

## Capturas de Pantalla (Ejemplo de Layout)

```
┌─────────────────────────────────────────────────────────┐
│ ← Volver al Dashboard          [1h] [6h] [24h] [7d]     │
│ hostname.local                                           │
│ ● Online | IP: 192.168.1.10                             │
├─────────────────────────────────────────────────────────┤
│ 📊 Información del Sistema                              │
│ [OS] [Kernel] [CPU Cores] [Memory] [Host ID] [Uptime]  │
├─────────────────────────────────────────────────────────┤
│ [CPU 45%] [Memory 8.5GB] [Disk 62%] [Temp 55°C]        │
├─────────────────────────────────────────────────────────┤
│ 📈 Métricas Históricas (360 puntos)                    │
│ ┌────────┐ ┌────────┐ ┌────────┐                      │
│ │CPU     │ │Memory  │ │Disk    │                      │
│ │Chart   │ │Chart   │ │Chart   │                      │
│ └────────┘ └────────┘ └────────┘                      │
│ ┌────────┐ ┌────────┐ ┌────────┐                      │
│ │Temp    │ │Net RX  │ │Net TX  │                      │
│ └────────┘ └────────┘ └────────┘                      │
├─────────────────────────────────────────────────────────┤
│ 🐳 Contenedores Docker (3)                             │
│ ┌───────────────────────────────────────────────────┐  │
│ │nginx-proxy | running | [Stop] [Restart]          │  │
│ │postgres-db | running | [Stop] [Restart]          │  │
│ │redis-cache | stopped | [Start]                   │  │
│ └───────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│ 🚨 Alertas Activas (2)                                 │
│ [CRITICAL] High CPU: 95% at 10:35                      │
│ [WARNING] Low Disk: 12% free at 10:42                  │
└─────────────────────────────────────────────────────────┘
```

## Testing

### Casos de Prueba

✅ **Test 1: Navegación desde dashboard**
- Click en "Ver Detalles" de un host online
- Verifica que se carga la página con datos correctos
- URL debe ser `/hosts/{id}`

✅ **Test 2: Cambio de rango temporal**
- Cambiar rango de 6h a 24h
- Verificar que gráficos se actualizan con más datos
- Contador de puntos debe cambiar (360 → 1440)

✅ **Test 3: Control de contenedores**
- Click en botón "Stop" de contenedor running
- Esperar 3 segundos
- Verificar que estado cambia a "stopped"
- Botón "Start" debe aparecer

✅ **Test 4: Host sin Docker**
- Navegar a host sin contenedores
- Verificar que sección Docker no se muestra

✅ **Test 5: Host sin alertas**
- Navegar a host sin alertas activas
- Verificar mensaje "✅ No hay alertas activas para este host"

✅ **Test 6: Auto-refresh**
- Dejar página abierta 15 segundos
- Verificar que datos se actualizan automáticamente
- Nuevo punto de datos debe aparecer en gráficos

✅ **Test 7: Host offline**
- Navegar a host con status = "offline"
- Badge debe mostrar "○ Offline" en gris
- Datos históricos deben mostrarse igual

✅ **Test 8: Responsive (manual)**
- Abrir en tablet (768px): Grid de gráficos se adapta
- Abrir en móvil (375px): Layout de una columna
- Tabla Docker con scroll horizontal

## Próximos Pasos Opcionales

**Mejoras futuras:**

1. **Comparación de métricas**: Vista para comparar dos hosts lado a lado
2. **Alertas in-line**: Marcar en gráficos cuándo se disparó cada alerta
3. **Logs de contenedor**: Ver logs en tiempo real del contenedor seleccionado
4. **Historial de comandos**: Tabla con comandos Docker ejecutados y su estado
5. **Exportar gráficos**: Botón para descargar gráficos como PNG
6. **Favoritos**: Marcar hosts como favoritos para acceso rápido
7. **Notas**: Campo de texto para añadir notas sobre el host

## Archivos Involucrados

### Nuevos
- `frontend/src/app/hosts/[id]/page.tsx` (800 líneas)

### Modificados
- `frontend/src/app/page.tsx` (+5 líneas import, +2 líneas hook, +35 líneas botón)

## Verificación Final

```bash
# 1. Verificar que no hay errores de compilación
cd /home/mloco/Escritorio/LAMS/frontend
npm run build

# 2. Iniciar en desarrollo
npm run dev

# 3. Acceder a
# http://localhost:3000 → Login → Hosts → Click "Ver Detalles"
# http://localhost:3000/hosts/{host_id} → Vista detallada

# 4. Verificar funcionalidades:
# - Gráficos se cargan correctamente
# - Selector de rango funciona
# - Auto-refresh cada 15s
# - Botones Docker responden
# - Navegación de vuelta funciona
```

## Conclusión

La **Fase 3.3.1** está completamente implementada y funcional. Los usuarios ahora pueden:

✅ Ver información exhaustiva de cada host  
✅ Analizar métricas históricas con gráficos interactivos  
✅ Controlar contenedores Docker remotamente  
✅ Monitorear alertas específicas del host  
✅ Navegar fluidamente entre dashboard y vista detallada  

Esta funcionalidad mejora significativamente la experiencia de usuario, permitiendo un análisis profundo de cada host sin necesidad de cambiar entre múltiples vistas o herramientas externas.

**Progreso Fase 3.3: 4/7 completados (57%)**

---

**Siguiente tarea recomendada:** Fase 3.3.4 - Modo claro/oscuro toggle (1 día)
