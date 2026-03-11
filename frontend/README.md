# LAMS Frontend

Dashboard web para el sistema de monitorización LAMS.

## Desarrollo Local

### Prerequisitos
- Node.js 18+ / npm 9+
- Backend LAMS corriendo en `http://192.168.0.8:8080` (o modificar `.env.local`)

### Instalación

```bash
# Instalar dependencias
npm install

# Configurar variables de entorno
# El archivo .env.local ya está configurado con la URL del API
cat .env.local
# NEXT_PUBLIC_API_URL=http://192.168.0.8:8080

# Iniciar servidor de desarrollo
npm run dev
```

El dashboard estará disponible en `http://localhost:3000`

### Credenciales por defecto

```
Email: admin@lams.io
Password: lams2024
```

## Solución de Problemas

### Error "Invalid credentials" en login

**Causa:** La contraseña ingresada no coincide con la del backend.

**Solución:**
1. Verifica que estés usando `admin@lams.io` / `lams2024`
2. Usa el botón "✨ Autocompletar credenciales" en la página de login
3. Verifica que el backend esté corriendo:
   ```bash
   curl -X POST "http://192.168.0.8:8080/api/v1/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin@lams.io&password=lams2024"
   # Debe retornar: {"access_token":"...","token_type":"bearer"}
   ```

### Backend no responde

**Verificar:**
```bash
# Ver estado de contenedores
docker ps | grep lams

# Verificar logs del servidor
docker logs lams-server --tail 50

# Probar endpoint de health
curl http://192.168.0.8:8080/health
# Debe retornar: {"status":"healthy","service":"LAMS Central Server"}
```

### CORS errors

El backend está configurado para aceptar todas las origins durante desarrollo (`allow_origins=["*"]`).

Si aún tienes problemas de CORS:
1. Verifica que `NEXT_PUBLIC_API_URL` esté correctamente configurado en `.env.local`
2. Reinicia el servidor de desarrollo: `npm run dev`
3. Limpia caché del navegador o prueba en modo incógnito

## Estructura del Proyecto

```
frontend/
├── src/
│   ├── app/
│   │   └── page.tsx          # Página principal con login y dashboard
│   ├── components/
│   │   └── MetricChart.tsx   # Componente de gráficos
│   ├── context/
│   │   └── AuthContext.tsx   # Contexto de autenticación
│   └── lib/
│       └── api.ts            # Cliente API HTTP
├── .env.local                # Variables de entorno local
├── next.config.ts            # Configuración Next.js
├── package.json
└── tsconfig.json
```

## Scripts Disponibles

```bash
npm run dev      # Servidor de desarrollo (puerto 3000)
npm run build    # Build para producción
npm run start    # Servidor de producción
npm run lint     # Linter TypeScript/ESLint
```

## Tecnologías

- **Next.js 15** - Framework React
- **TypeScript** - Tipado estático
- **Apache ECharts** - Gráficos de métricas
- **CSS Modules** - Estilos componentes

## API Endpoints Utilizados

- `POST /api/v1/auth/login` - Autenticación
- `GET /api/v1/auth/me` - Usuario actual
- `GET /api/v1/hosts/` - Lista de hosts
- `GET /api/v1/metrics/{host_id}` - Métricas de host
- `GET /api/v1/alerts/` - Alertas
- `GET /api/v1/notifications` - Configuraciones de notificaciones
- `GET /api/v1/users/` - Usuarios (solo admin)

## Páginas del Dashboard

1. **Dashboard** - Vista general con resumen de hosts y alertas
2. **Hosts** - Lista de máquinas monitorizadas
3. **Alertas** - Gestión de alertas del sistema
4. **Docker** - Monitoreo de contenedores (mock)
5. **Reglas** - Configuración de reglas de alertas
6. **Notificaciones** - Configuración de notificaciones (email, Slack, Discord)
7. **Usuarios** - Gestión de usuarios (solo admin)

## Notas de Desarrollo

- El token JWT se guarda en `localStorage` con la key `lams_token`
- El token expira en 8 días (configurable en backend)
- La página de login muestra un panel con las credenciales por defecto
- Los logs de las peticiones API se muestran en la consola del navegador

## Contacto

Para issues o preguntas sobre el frontend, consulta el [repositorio principal](../README.md).
