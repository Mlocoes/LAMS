# Corrección de Falla de Seguridad - Autenticación al Reload

**Fecha:** 11 de marzo de 2026  
**Severidad:** MEDIA  
**Estado:** ✅ CORREGIDO

## 📋 Resumen Ejecutivo

Se identificó y corrigió una falla de seguridad en el flujo de autenticación del frontend de LAMS. Al hacer reload (F5) de la página, el sistema no validaba correctamente la sesión del usuario antes de mostrar contenido, permaneciendo en estado "cargando" indefinidamente en caso de problemas de conectividad o tokens inválidos.

## 🔍 Problema Identificado

### Comportamiento Anterior (Vulnerable)

Al hacer reload de la página:

1. **Estado inicial:** `loading = true`
2. **Verificación de token:** Busca token en `localStorage`
3. **Validación retardada:** Si existe token, intenta llamar a `/api/v1/users/me`
4. **Sin timeout:** Sin límite de tiempo para la validación
5. **Exposición de estado:** Muestra "Iniciando LAMS..." indefinidamente

### Vectores de Ataque / Problemas

- **Token expirado:** Usuario con token inválido podría ver estados intermedios
- **Backend caído:** Sistema bloqueado en "cargando" sin fallback
- **Sin timeout:** Validación podría tardar indefinidamente
- **Experiencia degradada:** Usuario no sabe si cerrar sesión o esperar

## ✅ Solución Implementada

### Cambios en `AuthContext.tsx`

```typescript
useEffect(() => {
  const validateAuth = async () => {
    const stored = localStorage.getItem('lams_token');
    
    // ✅ NUEVO: Si no hay token, ir directo al login
    if (!stored) {
      setLoading(false);
      return;
    }

    // ✅ NUEVO: Timeout de seguridad de 5 segundos
    const timeoutId = setTimeout(() => {
      console.warn('⏱️ Timeout de validación alcanzado. Redirigiendo al login...');
      localStorage.removeItem('lams_token');
      setToken(null);
      setUser(null);
      setLoading(false);
    }, 5000);

    try {
      setToken(stored);
      const userData = await getMe();
      clearTimeout(timeoutId);
      setUser(userData);
    } catch (error) {
      clearTimeout(timeoutId);
      console.warn('🔒 Token inválido o sesión expirada. Redirigiendo al login...');
      localStorage.removeItem('lams_token');
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  validateAuth();
}, []);
```

### Mejoras de Seguridad

#### 1. **Validación Inmediata de Token**
- Si no hay token en localStorage → Login inmediato (sin "cargando")
- Elimina el estado ambiguo inicial

#### 2. **Timeout de Seguridad (5 segundos)**
- Protección contra backend lento o caído
- Fuerza logout y limpia el token expirado
- Usuario ve el login en lugar de pantalla congelada

#### 3. **Limpieza Automática de Tokens Inválidos**
- Cualquier error en validación limpia el token
- Previene loops de validación fallida
- Logs claros en consola para debugging

#### 4. **Estados Explícitos**
```
Sin token → Login (0ms)
Token válido → Dashboard (100-500ms)
Token inválido → Login + limpieza (100-500ms)
Timeout → Login + limpieza (5000ms)
```

## 🧪 Casos de Prueba

### Test 1: Usuario sin sesión (primera carga)
```
ANTES: loading → (validación innecesaria) → login
AHORA: login (inmediato)
```

### Test 2: Usuario con sesión válida (F5)
```
ANTES: loading → validando → dashboard
AHORA: loading → validando → dashboard (mismo flujo, pero con timeout)
```

### Test 3: Usuario con token expirado (F5)
```
ANTES: loading → error → (posible loop) → login
AHORA: loading → error → limpieza → login (garantizado < 5s)
```

### Test 4: Backend caído (F5)
```
ANTES: loading → (infinito)
AHORA: loading → timeout (5s) → login
```

## 📊 Impacto en Seguridad

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Tiempo máximo de validación** | ∞ (sin límite) | 5 segundos |
| **Limpieza de tokens inválidos** | Manual | Automática |
| **Estado sin token** | Valida innecesariamente | Login inmediato |
| **Feedback al usuario** | "Cargando..." | Login o Dashboard |
| **Logs de debugging** | Limitados | Explícitos |

## 🔐 Recomendaciones Adicionales

### Para Producción

1. **Reducir timeout a 3 segundos**
   ```typescript
   const timeoutId = setTimeout(() => { ... }, 3000);
   ```

2. **Implementar refresh tokens**
   - Token de acceso: 15 minutos
   - Refresh token: 7 días
   - Renovación automática transparente

3. **Agregar rate limiting en backend**
   - Limitar intentos de validación por IP
   - Prevenir ataques de fuerza bruta

4. **Logging centralizado**
   - Registrar intentos de validación fallidos
   - Alertas por tokens expirados masivos

5. **Header de expiración en tokens**
   - Validar expiración en frontend antes de llamar al backend
   - Evitar llamadas innecesarias

### Para Mejorar UX

1. **Mensaje de timeout personalizado**
   ```tsx
   if (!user && !loading) {
     return (
       <LoginScreen 
         message="Tu sesión expiró. Por favor, inicia sesión nuevamente." 
       />
     );
   }
   ```

2. **Botón de "Reintentar" en caso de error**
   - Permitir al usuario reintentar validación
   - Útil si fue un error temporal de red

3. **Persistencia opcional de sesión**
   - Checkbox "Mantener sesión iniciada"
   - Usar `localStorage` vs `sessionStorage` según elección

## 📝 Commits Relacionados

- **Fecha:** 2026-03-11
- **Archivos modificados:**
  - `frontend/src/context/AuthContext.tsx`
- **Líneas cambiadas:** ~35 líneas (27-61)

## 🎯 Conclusiones

✅ **Problema corregido:** Sistema ahora redirige correctamente al login al hacer reload  
✅ **Timeout implementado:** Máximo 5 segundos de validación  
✅ **Limpieza automática:** Tokens inválidos eliminados automáticamente  
✅ **Mejor UX:** Usuario ve estado definitivo en lugar de "cargando" indefinido  
✅ **Logs mejorados:** Debugging más fácil con mensajes explícitos  

## 📚 Referencias

- [OWASP: Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [React Security Best Practices](https://react.dev/learn/thinking-in-react#step-5-add-inverse-data-flow)

---

**Actualizado por:** GitHub Copilot  
**Revisado por:** Pendiente  
**Aprobado por:** Pendiente
