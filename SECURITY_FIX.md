# Corrección de Seguridad Crítica

**Fecha:** 10 de marzo de 2026  
**Severidad:** 🔴 CRÍTICA

## Vulnerabilidades Corregidas

### 1. Contraseñas Hardcodeadas Eliminadas

#### Archivos afectados:
- ✅ `docker-compose.yml` - Contraseñas de PostgreSQL y SECRET_KEY hardcodeadas
- ✅ `docker-compose.production.yml` - Mismas vulnerabilidades
- ✅ `server/main.py` - Contraseña de admin hardcodeada
- ✅ `server/reset_admin_password.py` - Contraseña de admin hardcodeada

### 2. Solución Implementada

#### Archivo `.env` creado con credenciales seguras:
```bash
# Credenciales generadas criptográficamente:
SECRET_KEY=1ba7de0401298bd6f951c8faeef86418e9cba9b0ca666e6d68b98e0e0a04e35b
POSTGRES_PASSWORD=R2YoREF53JW3Il3qMKTE71gZyr9rDply
ADMIN_PASSWORD=XrJCb2-3KQaZ6hZUf-t2fg
LAMS_AGENT_TOKEN=K25uxTH_dDcLHpsYPQAqV_Jfy0DhzJuh7YG8niPxfBU
```

#### Permisos seguros:
```bash
chmod 600 .env  # Solo lectura/escritura para propietario
```

#### Docker Compose actualizado:
```yaml
# Antes (❌ INSEGURO):
POSTGRES_PASSWORD: secret
SECRET_KEY: 09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7

# Después (✅ SEGURO):
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
SECRET_KEY: ${SECRET_KEY}
```

## Acciones Requeridas

### ⚠️ URGENTE - Pasos Inmediatos:

1. **Cambiar contraseña de admin:**
   ```bash
   # Iniciar sesión en http://192.168.0.8:3001
   # Usuario: admin@lams.io
   # Nueva contraseña temporal: XrJCb2-3KQaZ6hZUf-t2fg
   # ⚠️ DEBES CAMBIAR esta contraseña en tu primer login
   ```

2. **Reiniciar servicios:**
   ```bash
   cd /home/mloco/Escritorio/LAMS
   docker-compose down
   docker-compose up -d
   ```

3. **Verificar que .env NO esté en Git:**
   ```bash
   git status
   # .env NO debe aparecer en la lista
   # Si aparece, ejecutar:
   git rm --cached .env
   git commit -m "Remove .env from version control"
   ```

4. **Rotar credenciales en producción:**
   - Si este código ya está en producción, **ROTAR TODAS LAS CREDENCIALES INMEDIATAMENTE**
   - La SECRET_KEY antigua está comprometida
   - Todos los tokens JWT generados con la clave antigua deben invalidarse

### 🔍 Verificación de Seguridad

```bash
# 1. Verificar que .env tiene permisos correctos
ls -l .env
# Debe mostrar: -rw------- (600)

# 2. Verificar que .env está en .gitignore
grep "^\.env$" .gitignore
# Debe retornar: .env

# 3. Verificar que no hay secretos hardcodeados
grep -r "POSTGRES_PASSWORD.*secret" docker-compose*.yml
# No debe retornar resultados

# 4. Comprobar que las variables se cargan
docker-compose config | grep SECRET_KEY
# Debe mostrar la nueva SECRET_KEY
```

## Buenas Prácticas Implementadas

✅ Variables de entorno en `.env`  
✅ Template `.env.example` para documentación  
✅ Archivo `.env` añadido a `.gitignore`  
✅ Permisos restrictivos en `.env` (600)  
✅ Secrets generados con `secrets.token_urlsafe()` y `secrets.token_hex()`  
✅ Código actualizado para leer de `os.getenv()`  

## Medidas Preventivas Futuras

1. **Pre-commit hooks:**
   ```bash
   # Instalar git-secrets para prevenir commits de secretos
   brew install git-secrets  # o apt-get install git-secrets
   cd /home/mloco/Escritorio/LAMS
   git secrets --install
   git secrets --register-aws
   ```

2. **Escaneo de seguridad:**
   ```bash
   # Usar truffleHog para detectar secretos en el historial
   pip install truffleHog
   trufflehog --regex --entropy=True .
   ```

3. **Rotar credenciales periódicamente:**
   - SECRET_KEY: cada 90 días
   - POSTGRES_PASSWORD: cada 90 días
   - ADMIN_PASSWORD: cada 30 días
   - LAMS_AGENT_TOKEN: cada 60 días

## Checklist de Auditoría

- [x] Eliminar credenciales hardcodeadas de docker-compose.yml
- [x] Eliminar credenciales hardcodeadas de docker-compose.production.yml
- [x] Actualizar main.py para usar variables de entorno
- [x] Actualizar reset_admin_password.py
- [x] Crear archivo .env con credenciales seguras
- [x] Establecer permisos 600 en .env
- [x] Verificar .env en .gitignore
- [ ] Cambiar contraseña de admin en primer login
- [ ] Rotar credenciales en producción (si aplica)
- [ ] Escanear historial de Git con truffleHog
- [ ] Configurar alertas de seguridad en GitHub

## Recursos

- Generar nuevas SECRET_KEY:
  ```bash
  python3 -c "from secrets import token_hex; print(token_hex(32))"
  ```

- Generar contraseñas seguras:
  ```bash
  python3 -c "from secrets import token_urlsafe; print(token_urlsafe(24))"
  ```

## Contacto

Para reportar problemas de seguridad: **security@lams.io** (si aplica)

---
**⚠️ IMPORTANTE:** Este documento contiene información sensible sobre la corrección.  
**NO compartir** detalles de las credenciales actuales.
