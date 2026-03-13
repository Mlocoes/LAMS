# 🐳 Guía de Funcionalidades Docker - LAMS Sprint 1

## 📍 Acceso a las Funcionalidades

Las nuevas funcionalidades de gestión avanzada de contenedores Docker están disponibles en:

### Navegación:
1. **Abrir LAMS Dashboard**: http://localhost:3001
2. **Clic en "Docker"** en el menú lateral izquierdo (icono ⊡)
3. **Seleccionar el host** desde el selector en la parte superior derecha

## ✨ Funcionalidades Disponibles

### 1. 📋 **LOGS** - Logs del Contenedor
- **¿Qué hace?**: Muestra los logs en tiempo real del contenedor
- **Disponible para**: Todos los contenedores (running y stopped)
- **Características**:
  - Vista en tiempo real con auto-scroll
  - Búsqueda y filtrado de logs
  - Descarga de logs en archivo .txt
  - Selector de cantidad de líneas (50, 100, 500, 1000, todas)

### 2. 🔍 **INSPECT** - Inspección Detallada
- **¿Qué hace?**: Muestra la configuración completa del contenedor en formato JSON
- **Disponible para**: Todos los contenedores
- **Información incluida**:
  - Configuración de red (puertos, IPs, networks)
  - Variables de entorno
  - Volúmenes montados
  - Labels y metadatos
  - Políticas de restart
  - Exit code (si aplica)

### 3. 💻 **CONSOLE** - Terminal Interactiva
- **¿Qué hace?**: Abre una terminal bash interactiva dentro del contenedor
- **Disponible para**: Solo contenedores en estado **running**
- **Características**:
  - Ejecución de comandos en tiempo real
  - Shell bash completo (/bin/bash)
  - Historial de comandos
  - Output formateado con colores

### 4. 🗑️ **DELETE** - Eliminar Contenedor
- **¿Qué hace?**: Elimina un contenedor de forma permanente
- **Disponible para**: Todos los contenedores
- **Seguridad**:
  - Advertencia especial si el contenedor está running
  - Confirmación requerida
  - Opción de forzar eliminación (-f)
  - Refresh automático de la lista tras eliminación

## 🎯 Controles Básicos (Ya Existentes)

### ▶️ START
- Inicia un contenedor detenido

### ⏸️ STOP
- Detiene un contenedor en ejecución

### 🔄 RESTART
- Reinicia un contenedor

## 📊 Vista de Tabla

La tabla de Docker muestra:
| Columna | Descripción |
|---------|-------------|
| **Estado** | 🟢 RUN (running) o ⚪ STOP (stopped) |
| **Nombre** | Nombre del contenedor |
| **Imagen** | Imagen Docker usada |
| **CPU** | Porcentaje de uso de CPU |
| **Memoria** | MB de RAM consumidos |
| **Creado** | Fecha y hora de creación |
| **Acciones** | Botones de control |

## 🎨 Códigos de Color

- **Verde** (#10b981): Acciones seguras (START, CONSOLE)
- **Naranja** (#f59e0b): Acciones de pausa (STOP)
- **Azul** (#3b82f6): Acciones de reinicio (RESTART)
- **Morado** (#667eea): Información (LOGS)
- **Cyan** (#06b6d4): Inspección (INSPECT)
- **Rojo** (#ef4444): Acciones destructivas (DELETE)

## 🚀 Flujo de Trabajo Típico

### Monitorear un contenedor:
1. Clic en **LOGS** para ver actividad en tiempo real
2. Clic en **INSPECT** para revisar configuración
3. Si necesitas depurar: **CONSOLE** para ejecutar comandos

### Gestionar contenedor problemático:
1. **LOGS** para identificar el error
2. **RESTART** para reiniciar
3. Si persiste: **STOP** → **START**
4. Como último recurso: **DELETE** (y recrear)

## 💡 Consejos

- **Logs**: Usa la búsqueda para filtrar errores específicos
- **Inspect**: Busca información de networks y volumes antes de eliminar
- **Console**: Ideal para verificar archivos internos o ejecutar scripts
- **Delete**: Siempre verifica que no necesitas los datos antes de eliminar

## 🔒 Seguridad

- Solo usuarios autenticados pueden acceder
- Todas las acciones destructivas requieren confirmación
- Los comandos se ejecutan con los permisos del agente LAMS
- Los logs se filtran para no mostrar información sensible

## 📈 Estadísticas

En la parte superior verás:
- **Total de contenedores** en el host seleccionado
- **Contenedores activos** (running)
- **Contenedores detenidos** (stopped)
- **Host actual** seleccionado

## 🆘 Solución de Problemas

### "No veo los botones Sprint 1"
- Refresca el navegador (Ctrl + Shift + R)
- Verifica que el host tenga contenedores
- Comprueba que estás en la página Docker (menú ⊡)

### "Console no aparece"
- Console solo está disponible para contenedores **running**
- Inicia el contenedor primero con **START**

### "Error al ejecutar comando"
- Verifica la conexión con el host
- Revisa los logs del backend: `docker logs lams-server`
- Comprueba que el agente LAMS está corriendo en el host

## 📚 Arquitectura Técnica

```
Frontend (Next.js) → API LAMS → PostgreSQL
                          ↓
                    LAMS Agent (Go)
                          ↓
                    Docker Engine
```

## 🔗 Enlaces Útiles

- Dashboard principal: http://localhost:3001
- Página Docker: http://localhost:3001 (menú ⊡)
- Backend API: http://localhost:8080/docs
- Logs del servidor: `docker logs lams-server -f`

---

**Versión**: LAMS Sprint 1  
**Fecha**: Marzo 2026  
**Documentación**: /docs/DOCKER_FEATURES_GUIDE.md
