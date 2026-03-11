# Análisis de Seguridad LAMS y Plan de Remediación

**Fecha de análisis:** 9 de marzo de 2026  
**Versión del sistema:** 1.0.0  
**Analista:** Security Review  
**Estado:** 🔴 CRÍTICO - Requiere atención inmediata

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Metodología de Análisis](#metodología-de-análisis)
3. [Vulnerabilidades Identificadas](#vulnerabilidades-identificadas)
4. [Plan de Remediación](#plan-de-remediación)
5. [Fases de Implementación](#fases-de-implementación)
6. [Checklist de Seguridad](#checklist-de-seguridad)
7. [Mejores Prácticas](#mejores-prácticas)

---

## 🎯 Resumen Ejecutivo

### Severidad General: 🔴 CRÍTICA

El análisis de seguridad del sistema LAMS ha identificado **27 vulnerabilidades** distribuidas de la siguiente manera:

| Severidad | Cantidad | Porcentaje |
|-----------|----------|------------|
| 🔴 Crítica | 8 | 30% |
| 🟠 Alta | 11 | 41% |
| 🟡 Media | 6 | 22% |
| 🟢 Baja | 2 | 7% |

### Áreas Más Afectadas

1. **Autenticación y Autorización** - 8 vulnerabilidades (5 críticas)
2. **Configuración y Secretos** - 6 vulnerabilidades (2 críticas)
3. **Validación de Entrada** - 5 vulnerabilidades (0 críticas, 4 altas)
4. **Comunicación de Red** - 4 vulnerabilidades (1 crítica)
5. **Frontend y XSS** - 4 vulnerabilidades (0 críticas, 3 altas)

### Recomendación Principal

**Se recomienda NO desplegar el sistema en producción hasta resolver todas las vulnerabilidades críticas (🔴) y de alta severidad (🟠).**

---

## 🔍 Metodología de Análisis

### Alcance del Análisis

- ✅ Código fuente del backend (FastAPI/Python)
- ✅ Código fuente del frontend (Next.js/React)
- ✅ Código fuente del agente (Go)
- ✅ Configuración de la base de datos (PostgreSQL)
- ✅ Configuración de comunicaciones (HTTP/REST)
- ✅ Gestión de secretos y configuración
- ✅ Manejo de sesiones y tokens

### Fuera del Alcance

- ❌ Infraestructura de deployment (pendiente)
- ❌ Configuración de red y firewall
- ❌ Auditoría de dependencias de terceros (pendiente)
- ❌ Pruebas de penetración activas

### Herramientas Utilizadas

- Revisión manual de código
- Análisis estático de patrones inseguros
- Revisión de configuraciones
- Verificación de OWASP Top 10

---

## 🚨 Vulnerabilidades Identificadas

### 1. Autenticación y Autorización

#### 🔴 CRÍTICA 1.1: Secret Key Hardcoded

**Ubicación:** `server/core/config.py:22`

```python
SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
```

**Riesgo:**
- La clave secreta está hardcoded en el código fuente
- Visible en repositorios Git
- Permite falsificación de tokens JWT si se compromete
- Facilita ataques de replay y session hijacking

**Impacto:** 
- Compromiso total de la autenticación
- Posibilidad de crear tokens para cualquier usuario
- Acceso no autorizado a todo el sistema

**CWE:** CWE-798 (Use of Hard-coded Credentials)  
**CVSS Score:** 9.8 (Critical)

---

#### 🔴 CRÍTICA 1.2: Password de Base de Datos Hardcoded

**Ubicación:** `server/core/config.py:9-11`

```python
POSTGRES_USER: str = "lams"
POSTGRES_PASSWORD: str = "secret"
POSTGRES_HOST: str = "postgres"
```

**Riesgo:**
- Credenciales de base de datos visibles en el código
- Password genérico y débil ("secret")
- Acceso directo a la base de datos si se compromete

**Impacto:**
- Acceso directo a todos los datos sensibles
- Modificación/eliminación de datos
- Exfiltración de información

**CWE:** CWE-259 (Use of Hard-coded Password)  
**CVSS Score:** 9.1 (Critical)

---

#### 🔴 CRÍTICA 1.3: Usuario Admin con Password por Defecto

**Ubicación:** `server/main.py:25-29`

```python
admin = User(
    email="admin@lams.io",
    password_hash=get_password_hash("lams2024"),
    role="Admin",
)
```

**Riesgo:**
- Credenciales por defecto conocidas públicamente
- Documentadas en el código fuente
- No se fuerza cambio de contraseña en primer login

**Impacto:**
- Acceso administrativo inmediato
- Control total del sistema
- Escalación de privilegios trivial

**CWE:** CWE-798 (Use of Hard-coded Credentials)  
**CVSS Score:** 9.8 (Critical)

---

#### 🔴 CRÍTICA 1.4: Tokens Almacenados en localStorage (XSS)

**Ubicación:** `frontend/src/lib/api.ts:4-6`, `frontend/src/context/AuthContext.tsx:28,45,52`

```typescript
function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('lams_token');
}
```

**Riesgo:**
- localStorage es vulnerable a ataques XSS
- Tokens accesibles desde cualquier JavaScript en el dominio
- No hay protección HttpOnly
- Persisten después de cerrar el navegador

**Impacto:**
- Robo de sesión mediante XSS
- Persistencia del ataque
- Acceso no autorizado prolongado

**CWE:** CWE-522 (Insufficiently Protected Credentials)  
**CVSS Score:** 8.1 (High)

---

#### 🟠 ALTA 1.5: Sin Rate Limiting en Login

**Ubicación:** `server/api/auth.py:34-49`

```python
@router.post("/login")
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    # No hay protección contra brute force
```

**Riesgo:**
- Ataques de fuerza bruta sin limitación
- Enumeración de usuarios
- Denegación de servicio (DoS)

**Impacto:**
- Compromiso de cuentas mediante fuerza bruta
- Sobrecarga del servidor
- Degradación del servicio

**CWE:** CWE-307 (Improper Restriction of Excessive Authentication Attempts)  
**CVSS Score:** 7.5 (High)

---

#### 🟠 ALTA 1.6: Tokens con Expiración Excesiva

**Ubicación:** `server/core/config.py:24`

```python
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 días
```

**Riesgo:**
- Ventana de ataque extendida si el token se compromete
- Tokens válidos por mucho tiempo después de logout
- Dificultad para revocar acceso

**Impacto:**
- Mayor exposición en caso de compromiso
- Sesiones "zombie" después de logout
- Dificultad en auditorías

**CWE:** CWE-613 (Insufficient Session Expiration)  
**CVSS Score:** 6.5 (Medium-High)

---

#### 🟠 ALTA 1.7: Sin Mecanismo de Revocación de Tokens

**Ubicación:** Todo el sistema

**Riesgo:**
- No hay blacklist de tokens
- No se pueden invalidar tokens comprometidos
- Logout no invalida el token, solo lo elimina del cliente

**Impacto:**
- Imposible revocar acceso antes de expiración
- Tokens robados siguen funcionando
- Sin protección post-compromiso

**CWE:** CWE-613 (Insufficient Session Expiration)  
**CVSS Score:** 7.2 (High)

---

#### 🟠 ALTA 1.8: Autorización Inconsistente en Endpoints

**Ubicación:** `server/api/hosts.py:34`, otros endpoints

```python
@router.post("/register", response_model=HostResponse)
async def register_host(
    host_data: HostRegister, 
    db: AsyncSession = Depends(get_db), 
    # Sin verificación de usuario actual
) -> Any:
```

**Riesgo:**
- Algunos endpoints no verifican roles
- Posible escalación de privilegios
- Acceso no autorizado a funciones administrativas

**Impacto:**
- Usuario normal puede registrar hosts
- Posible manipulación de configuración
- Escalación horizontal de privilegios

**CWE:** CWE-862 (Missing Authorization)  
**CVSS Score:** 7.1 (High)

---

### 2. Configuración y Secretos

#### 🔴 CRÍTICA 2.1: CORS Wildcard (allow_origins="*")

**Ubicación:** `server/main.py:70-76`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Should be restricted in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Riesgo:**
- Permite cualquier origen acceder a la API
- Facilita ataques CSRF
- Exponencia API públicamente sin restricciones
- El comentario indica consciencia pero no acción

**Impacto:**
- Sitios maliciosos pueden hacer requests a la API
- Robo de datos mediante CSRF
- Exfiltración de información

**CWE:** CWE-346 (Origin Validation Error)  
**CVSS Score:** 8.6 (High)

---

#### 🔴 CRÍTICA 2.2: Sin HTTPS Enforcement

**Ubicación:** Todo el sistema

**Riesgo:**
- Comunicación en texto plano
- Tokens y contraseñas transmitidos sin cifrado
- Susceptible a ataques Man-in-the-Middle (MITM)

**Impacto:**
- Interceptación de credenciales
- Robo de tokens de sesión
- Modificación de tráfico

**CWE:** CWE-319 (Cleartext Transmission of Sensitive Information)  
**CVSS Score:** 8.2 (High)

---

#### 🟠 ALTA 2.3: Sin Variables de Entorno para Secretos

**Ubicación:** `server/core/config.py`

**Riesgo:**
- Configuración sensible en código
- .env no está en .gitignore (potencialmente)
- Dificultad para rotar secretos

**Impacto:**
- Exposición de credenciales en repositorios
- Secretos compartidos entre entornos
- Dificultad en gestión de secrets

**CWE:** CWE-543 (Use of Singleton Pattern Without Synchronization)  
**CVSS Score:** 7.4 (High)

---

#### 🟡 MEDIA 2.4: Credenciales SMTP Vacías pero Definidas

**Ubicación:** `server/core/config.py:27-32`

```python
SMTP_HOST: str = ""
SMTP_PORT: int = 587
SMTP_USER: str = ""
SMTP_PASSWORD: str = ""
```

**Riesgo:**
- Configuración incompleta puede causar errores
- No hay validación de configuración necesaria
- Posible información disclosure en errores

**Impacto:**
- Funcionalidad de notificaciones no operativa
- Errores expuestos a usuarios
- Confusión en configuración

**CWE:** CWE-665 (Improper Initialization)  
**CVSS Score:** 4.3 (Medium)

---

#### 🟡 MEDIA 2.5: Sin Headers de Seguridad HTTP

**Ubicación:** `server/main.py`

**Riesgo:**
- No hay headers de seguridad configurados:
  - X-Content-Type-Options
  - X-Frame-Options
  - X-XSS-Protection
  - Strict-Transport-Security
  - Content-Security-Policy

**Impacto:**
- Mayor susceptibilidad a XSS
- Clickjacking posible
- Sin mitigaciones del navegador

**CWE:** CWE-693 (Protection Mechanism Failure)  
**CVSS Score:** 5.3 (Medium)

---

#### 🟡 MEDIA 2.6: Modo de Desarrollo en Producción

**Ubicación:** `server/main.py:90`

```python
uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

**Riesgo:**
- reload=True es para desarrollo
- Expone stack traces completos
- Mayor superficie de ataque

**Impacto:**
- Information disclosure
- Degradación de rendimiento
- Exposición de estructura interna

**CWE:** CWE-489 (Active Debug Code)  
**CVSS Score:** 5.0 (Medium)

---

### 3. Validación de Entrada

#### 🟠 ALTA 3.1: Sin Validación de Longitud de Passwords

**Ubicación:** `server/api/auth.py:13-14`

```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str  # Sin validación de complejidad
```

**Riesgo:**
- Acepta contraseñas débiles de 1 carácter
- Sin requisitos de complejidad
- Sin verificación de passwords comunes

**Impacto:**
- Cuentas fácilmente comprometibles
- Ataques de diccionario efectivos
- Debilidad en seguridad general

**CWE:** CWE-521 (Weak Password Requirements)  
**CVSS Score:** 7.3 (High)

---

#### 🟠 ALTA 3.2: Sin Sanitización de Inputs en Tags

**Ubicación:** `server/api/hosts.py:123`

```python
class HostTagsUpdate(BaseModel):
    tags: List[str]  # Sin validación de contenido
```

**Riesgo:**
- Posible inyección de código en tags
- Sin límite de longitud
- Posible XSS almacenado

**Impacto:**
- XSS en visualización de tags
- Inyección de HTML/JavaScript
- Corrupción de datos

**CWE:** CWE-79 (Improper Neutralization of Input)  
**CVSS Score:** 7.2 (High)

---

#### 🟠 ALTA 3.3: Sin Validación de hostId en Métricas

**Ubicación:** `server/api/metrics.py`

**Riesgo:**
- Acepta cualquier host_id sin validación
- Posible acceso a métricas de otros hosts
- Sin verificación de existencia del host

**Impacto:**
- Acceso no autorizado a datos
- Information disclosure
- Posible inyección

**CWE:** CWE-639 (Authorization Bypass Through User-Controlled Key)  
**CVSS Score:** 7.5 (High)

---

#### 🟡 MEDIA 3.4: Sin Límites de Rate en API

**Ubicación:** Todo el sistema

**Riesgo:**
- No hay limitación de requests
- Vulnerable a ataques de denegación de servicio
- Abuso de recursos

**Impacto:**
- DoS por abuso de API
- Costos excesivos de computación
- Degradación del servicio

**CWE:** CWE-770 (Allocation of Resources Without Limits)  
**CVSS Score:** 5.9 (Medium)

---

#### 🟡 MEDIA 3.5: Sin Validación de Tamaño de Payload

**Ubicación:** Todo el sistema

**Riesgo:**
- No hay límite en tamaño de requests
- Posible memory exhaustion
- DoS mediante payloads grandes

**Impacto:**
- Consumo excesivo de memoria
- Crash del servidor
- Denegación de servicio

**CWE:** CWE-400 (Uncontrolled Resource Consumption)  
**CVSS Score:** 5.3 (Medium)

---

### 4. Comunicación de Red

#### 🔴 CRÍTICA 4.1: Agente sin Autenticación Fuerte

**Ubicación:** `agent/main.go:69-70`

```go
agentToken := os.Getenv("LAMS_AGENT_TOKEN")
// Token opcional, no verificado consistentemente
```

**Riesgo:**
- Agentes pueden conectarse sin autenticación robusta
- Token opcional y no verificado en todos los endpoints
- Posible suplantación de agentes

**Impacto:**
- Inyección de métricas falsas
- Manipulación de datos del sistema
- DoS mediante sobrecarga de datos

**CWE:** CWE-306 (Missing Authentication for Critical Function)  
**CVSS Score:** 9.1 (Critical)

---

#### 🟠 ALTA 4.2: Sin Verificación de Certificados

**Ubicación:** `agent/main.go`

**Riesgo:**
- Cliente HTTP sin configuración de TLS
- No verifica certificados del servidor
- Vulnerable a MITM

**Impacto:**
- Intercepción de comunicaciones
- Modificación de comandos remotos
- Robo de datos sensibles

**CWE:** CWE-295 (Improper Certificate Validation)  
**CVSS Score:** 7.4 (High)

---

#### 🟠 ALTA 4.3: Comandos Remotos sin Firma Digital

**Ubicación:** `agent/main.go:100-117`

```go
func pollCommands(url, token, hostID string) []RemoteCommand {
    // Sin verificación de integridad de comandos
}
```

**Riesgo:**
- Comandos remotos sin verificación de origen
- Posible inyección de comandos maliciosos
- Sin audit trail robusto

**Impacto:**
- Ejecución de código arbitrario en hosts
- Compromiso total de sistemas monitoreados
- Movimiento lateral en infraestructura

**CWE:** CWE-494 (Download of Code Without Integrity Check)  
**CVSS Score:** 8.8 (High)

---

#### 🟡 MEDIA 4.4: Timeouts de Cliente No Configurados

**Ubicación:** `agent/main.go:138`

```go
client := &http.Client{Timeout: 10 * time.Second}
```

**Riesgo:**
- Timeout fijo puede no ser adecuado
- Sin configuración de retry
- Posible deadlock en red lenta

**Impacto:**
- Interrupciones de servicio
- Pérdida de datos de monitoreo
- Acumulación de conexiones

**CWE:** CWE-834 (Excessive Iteration)  
**CVSS Score:** 4.3 (Medium)

---

### 5. Base de Datos

#### 🟠 ALTA 5.1: Posible SQL Injection en Búsqueda

**Ubicación:** Potencial en queries dinámicas

**Riesgo:**
- Aunque se usa SQLAlchemy (protege contra SQLi)
- Queries dinámicas futuras podrían ser vulnerables
- Sin validación explícita de parámetros

**Impacto:**
- Acceso no autorizado a datos
- Modificación de base de datos
- Exfiltración de información

**CWE:** CWE-89 (SQL Injection)  
**CVSS Score:** 7.5 (High)

---

#### 🟠 ALTA 5.2: Sin Encriptación de Datos Sensibles en DB

**Ubicación:** `server/database/models.py`

**Riesgo:**
- Passwords hasheadas pero otros datos en texto plano
- Tokens de notificación sin cifrar
- Webhooks y URLs sensibles expuestas

**Impacto:**
- Exposición de secretos en backup de DB
- Information disclosure en caso de compromiso
- Cumplimiento regulatorio (GDPR, etc.)

**CWE:** CWE-311 (Missing Encryption of Sensitive Data)  
**CVSS Score:** 6.5 (Medium-High)

---

#### 🟡 MEDIA 5.3: Sin Auditoría de Cambios

**Ubicación:** Todo el sistema

**Riesgo:**
- No hay logging de quién cambió qué
- Sin timestamps de modificación
- Imposible rastrear acciones maliciosas

**Impacto:**
- Forense imposible después de incidente
- Sin accountability
- Dificultad en debugging

**CWE:** CWE-778 (Insufficient Logging)  
**CVSS Score:** 5.3 (Medium)

---

#### 🟢 BAJA 5.4: Sin Índices en Campos de Búsqueda Frecuente

**Ubicación:** `server/database/models.py`

**Riesgo:**
- Performance degradada en búsquedas
- Posible timeout en queries grandes
- DoS por queries lentas

**Impacto:**
- Degradación de rendimiento
- Experiencia de usuario pobre
- Costos aumentados de infraestructura

**CWE:** CWE-405 (Asymmetric Resource Consumption)  
**CVSS Score:** 3.7 (Low)

---

### 6. Frontend

#### 🟠 ALTA 6.1: Sin Protección CSRF

**Ubicación:** Frontend/Backend

**Riesgo:**
- No hay tokens CSRF
- Cualquier sitio puede hacer requests autenticados
- CORS wildcard agrava el problema

**Impacto:**
- Acciones no autorizadas en nombre del usuario
- Modificación de configuración
- Eliminación de datos

**CWE:** CWE-352 (Cross-Site Request Forgery)  
**CVSS Score:** 7.1 (High)

---

#### 🟠 ALTA 6.2: Posible XSS en Renderizado de Datos

**Ubicación:** `frontend/src/app/page.tsx` (múltiples ubicaciones)

**Riesgo:**
- Datos de API renderizados directamente
- Tags sin sanitización explícita
- Mensajes de alerta sin escape

**Impacto:**
- Ejecución de JavaScript malicioso
- Robo de tokens (agravado por localStorage)
- Defacement

**CWE:** CWE-79 (Cross-site Scripting)  
**CVSS Score:** 7.2 (High)

---

#### 🟠 ALTA 6.3: Sin Content Security Policy

**Ubicación:** Frontend

**Riesgo:**
- No hay CSP configurada
- Sin mitigación de XSS del navegador
- Puede cargar scripts de cualquier origen

**Impacto:**
- XSS más fácil de explotar
- Sin defensa en profundidad
- Mayor impacto de vulnerabilidades

**CWE:** CWE-1021 (Improper Restriction of Rendered UI Layers)  
**CVSS Score:** 6.1 (Medium-High)

---

#### 🟡 MEDIA 6.4: Credenciales Expuestas en Consola del Navegador

**Ubicación:** `frontend/src/lib/api.ts:28-30`

```typescript
console.log('📡 API Login - Credentials:', { email });
```

**Riesgo:**
- Logging de credenciales en consola
- Visible en herramientas de desarrollo
- Puede quedar en logs del navegador

**Impacto:**
- Information disclosure local
- Exposición en debugging
- Logs persistentes

**CWE:** CWE-532 (Information Exposure Through Log Files)  
**CVSS Score:** 4.3 (Medium)

---

### 7. Logging y Monitoreo

#### 🟠 ALTA 7.1: Sin Logging de Seguridad

**Ubicación:** Todo el sistema

**Riesgo:**
- No hay logs de intentos de login fallidos
- Sin registro de accesos a recursos sensibles
- Sin alertas de actividad sospechosa

**Impacto:**
- Imposible detectar ataques en curso
- Sin evidencia forense
- No cumplimiento regulatorio

**CWE:** CWE-778 (Insufficient Logging)  
**CVSS Score:** 6.5 (Medium-High)

---

#### 🟢 BAJA 7.2: Logs Potencialmente Con Información Sensible

**Ubicación:** `agent/main.go`, varios print statements

**Riesgo:**
- Logs pueden contener datos sensibles
- Sin sanitización de output
- Tokens y passwords pueden aparecer en logs

**Impacto:**
- Information disclosure en archivos de log
- Exposición de credenciales
- Problemas de privacidad

**CWE:** CWE-532 (Information Exposure Through Log Files)  
**CVSS Score:** 3.7 (Low)

---

## 🛡️ Plan de Remediación

### Fase 1: Mitigaciones Críticas (1-2 semanas)

**Objetivo:** Eliminar vulnerabilidades críticas que impiden deployment seguro.

#### 1.1 Gestión de Secretos

**Tareas:**
- [ ] Migrar SECRET_KEY a variable de entorno
- [ ] Implementar generación automática de SECRET_KEY si no está definida
- [ ] Migrar credenciales de BD a variables de entorno
- [ ] Crear archivo `.env.example` con valores de ejemplo
- [ ] Agregar `.env` a `.gitignore`
- [ ] Implementar validación de variables críticas al inicio
- [ ] Documentar proceso de configuración de secretos

**Archivos a modificar:**
- `server/core/config.py`
- `server/main.py`
- `.gitignore`
- `README.md`

**Código de ejemplo:**
```python
# server/core/config.py
from secrets import token_urlsafe

class Settings(BaseSettings):
    # SECRET_KEY debe venir de variable de entorno
    SECRET_KEY: str = None
    
    @validator('SECRET_KEY', pre=True)
    def validate_secret_key(cls, v):
        if v is None or v == "":
            # En desarrollo, generar una
            if os.getenv("ENV") == "development":
                return token_urlsafe(32)
            else:
                raise ValueError("SECRET_KEY must be set in production")
        return v
    
    # BD credentials desde env
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "lams"
```

**Estimación:** 2 días  
**Prioridad:** 🔴 CRÍTICA

---

#### 1.2 Cambio Forzado de Password Admin

**Tareas:**
- [ ] Agregar campo `must_change_password` al modelo User
- [ ] Marcar admin inicial con este flag
- [ ] Implementar endpoint para cambio forzado de password
- [ ] Agregar middleware que verifique este flag en cada request
- [ ] Crear interfaz de cambio de password en frontend
- [ ] Documentar proceso de primer login

**Archivos a modificar:**
- `server/database/models.py`
- `server/api/auth.py`
- `server/api/dependencies.py`
- `frontend/src/app/page.tsx`

**Código de ejemplo:**
```python
# server/database/models.py
class User(Base):
    # ... campos existentes
    must_change_password = Column(Boolean, default=False)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

# server/api/dependencies.py
async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    # ... validación existente
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required"
        )
    return user
```

**Estimación:** 3 días  
**Prioridad:** 🔴 CRÍTICA

---

#### 1.3 Restricción de CORS

**Tareas:**
- [ ] Configurar origins permitidos desde variables de entorno
- [ ] Implementar lista blanca de origins
- [ ] Agregar validación de origin en requests
- [ ] Configurar diferentes origins para dev/staging/prod
- [ ] Agregar headers de seguridad CORS

**Archivos a modificar:**
- `server/main.py`
- `server/core/config.py`

**Código de ejemplo:**
```python
# server/core/config.py
class Settings(BaseSettings):
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    
    @validator('ALLOWED_ORIGINS', pre=True)
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

# server/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Length", "X-Total-Count"],
    max_age=600,
)
```

**Estimación:** 1 día  
**Prioridad:** 🔴 CRÍTICA

---

#### 1.4 Migrar Tokens a HttpOnly Cookies

**Tareas:**
- [ ] Modificar endpoint de login para setear cookie HttpOnly
- [ ] Actualizar frontend para no usar localStorage
- [ ] Implementar CSRF protection
- [ ] Configurar SameSite=Strict en cookies
- [ ] Agregar Secure flag para producción
- [ ] Actualizar todas las requests para usar cookies

**Archivos a modificar:**
- `server/api/auth.py`
- `frontend/src/lib/api.ts`
- `frontend/src/context/AuthContext.tsx`

**Código de ejemplo:**
```python
# server/api/auth.py
from fastapi.responses import Response

@router.post("/login")
async def login_access_token(
    response: Response,
    db: AsyncSession = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    # ... validación existente
    
    access_token = create_access_token(user.id, expires_delta=access_token_expires)
    
    # Setear cookie HttpOnly
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return {"message": "Login successful"}
```

```typescript
// frontend/src/lib/api.ts
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  // No necesitamos obtener token, las cookies se envían automáticamente
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  const res = await fetch(`${API_URL}/api/v1${path}`, { 
    ...options, 
    headers,
    credentials: 'include' // Importante para enviar cookies
  });
  // ... resto del código
}
```

**Estimación:** 3 días  
**Prioridad:** 🔴 CRÍTICA

---

#### 1.5 Autenticación Robusta del Agente

**Tareas:**
- [ ] Implementar sistema de API keys únicas por agente
- [ ] Crear endpoint de generación de API keys
- [ ] Almacenar hash de API keys en base de datos
- [ ] Implementar verificación de API key en endpoints de agente
- [ ] Agregar rotación automática de API keys
- [ ] Documentar proceso de registro de agentes

**Archivos a modificar:**
- `server/database/models.py`
- `server/api/agents.py` (nuevo)
- `server/api/metrics.py`
- `agent/main.go`

**Código de ejemplo:**
```python
# server/database/models.py
class AgentAPIKey(Base):
    __tablename__ = "agent_api_keys"
    id = Column(Integer, primary_key=True)
    host_id = Column(String, ForeignKey("hosts.id"), unique=True)
    key_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

# server/api/dependencies.py
async def verify_agent_api_key(
    api_key: str = Header(..., alias="X-Agent-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> str:
    """Verify agent API key and return host_id"""
    key_hash = get_password_hash(api_key)
    
    stmt = select(AgentAPIKey).where(
        AgentAPIKey.key_hash == key_hash,
        AgentAPIKey.is_active == True
    )
    result = await db.execute(stmt)
    agent_key = result.scalar_one_or_none()
    
    if not agent_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if agent_key.expires_at and agent_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="API key expired")
    
    # Update last_used
    agent_key.last_used = datetime.now(timezone.utc)
    await db.commit()
    
    return agent_key.host_id
```

**Estimación:** 4 días  
**Prioridad:** 🔴 CRÍTICA

---

### Fase 2: Vulnerabilidades de Alta Severidad (2-3 semanas)

**Objetivo:** Mitigar riesgos significativos de seguridad.

#### 2.1 Rate Limiting

**Tareas:**
- [ ] Instalar slowapi o similar
- [ ] Configurar rate limiting global
- [ ] Implementar rate limiting específico para login (5 intentos/15min)
- [ ] Agregar rate limiting para endpoints de API
- [ ] Configurar rate limiting por IP y por usuario
- [ ] Implementar respuestas 429 Too Many Requests
- [ ] Agregar headers de rate limit en respuestas

**Dependencias:**
```bash
pip install slowapi
```

**Código de ejemplo:**
```python
# server/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# server/api/auth.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/15minutes")  # 5 intentos cada 15 minutos
async def login_access_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    # ... código existente
```

**Estimación:** 2 días  
**Prioridad:** 🟠 ALTA

---

#### 2.2 Validación de Passwords

**Tareas:**
- [ ] Instalar password-strength library
- [ ] Implementar validación de longitud mínima (12 caracteres)
- [ ] Verificar complejidad (mayúsculas, minúsculas, números, símbolos)
- [ ] Implementar check contra passwords comunes
- [ ] Agregar validación de password similar al email
- [ ] Implementar política de rotación de passwords
- [ ] Agregar indicador de fortaleza en frontend

**Dependencias:**
```bash
pip install password-strength
```

**Código de ejemplo:**
```python
# server/api/auth.py
from pydantic import validator
from password_strength import PasswordPolicy

policy = PasswordPolicy.from_names(
    length=12,  # min length: 12
    uppercase=1,  # need min. 1 uppercase letters
    numbers=1,  # need min. 1 digits
    special=1,  # need min. 1 special characters
)

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "User"
    
    @validator('password')
    def validate_password(cls, v):
        errors = policy.test(v)
        if errors:
            raise ValueError(
                "Password must be at least 12 characters and contain "
                "uppercase, lowercase, numbers, and special characters"
            )
        return v
```

**Estimación:** 2 días  
**Prioridad:** 🟠 ALTA

---

#### 2.3 Headers de Seguridad HTTP

**Tareas:**
- [ ] Instalar secure-headers middleware
- [ ] Configurar X-Content-Type-Options: nosniff
- [ ] Configurar X-Frame-Options: DENY
- [ ] Configurar X-XSS-Protection: 1; mode=block
- [ ] Configurar Strict-Transport-Security
- [ ] Implementar Content-Security-Policy
- [ ] Configurar Referrer-Policy

**Código de ejemplo:**
```python
# server/main.py
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' http://localhost:8000"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

**Estimación:** 1 día  
**Prioridad:** 🟠 ALTA

---

#### 2.4 Sanitización de Inputs

**Tareas:**
- [ ] Instalar bleach para sanitización HTML
- [ ] Implementar validación de tags (longitud, caracteres permitidos)
- [ ] Sanitizar todos los inputs de usuario
- [ ] Agregar validación de host_id en queries
- [ ] Implementar escape de HTML en frontend
- [ ] Agregar validación de tipos en todos los endpoints

**Dependencias:**
```bash
pip install bleach
```

**Código de ejemplo:**
```python
# server/utils/sanitization.py
import bleach
from typing import List

def sanitize_string(text: str, max_length: int = 255) -> str:
    """Sanitize a string input"""
    # Remove HTML tags
    clean = bleach.clean(text, tags=[], strip=True)
    # Trim whitespace
    clean = clean.strip()
    # Limit length
    return clean[:max_length]

def sanitize_tags(tags: List[str]) -> List[str]:
    """Sanitize a list of tags"""
    cleaned = []
    for tag in tags:
        # Sanitize each tag
        clean = sanitize_string(tag, max_length=50)
        # Only allow alphanumeric, hyphens, underscores
        if clean and all(c.isalnum() or c in ['-', '_', ' '] for c in clean):
            cleaned.append(clean)
    return cleaned[:10]  # Max 10 tags

# server/api/hosts.py
from utils.sanitization import sanitize_tags

class HostTagsUpdate(BaseModel):
    tags: List[str]
    
    @validator('tags')
    def validate_tags(cls, v):
        return sanitize_tags(v)
```

**Estimación:** 3 días  
**Prioridad:** 🟠 ALTA

---

#### 2.5 CSRF Protection

**Tareas:**
- [ ] Implementar generación de tokens CSRF
- [ ] Agregar token CSRF en cookies
- [ ] Validar token CSRF en requests mutantes
- [ ] Excluir endpoints de agente de CSRF
- [ ] Agregar CSRF token en formularios de frontend
- [ ] Implementar double-submit cookie pattern

**Código de ejemplo:**
```python
# server/middleware/csrf.py
from fastapi import Request, HTTPException
from secrets import token_urlsafe
import hmac
import hashlib

class CSRFProtection:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
    
    def generate_token(self, session_id: str) -> str:
        """Generate CSRF token"""
        message = f"{session_id}{token_urlsafe(32)}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{message}.{signature}"
    
    def validate_token(self, token: str, session_id: str) -> bool:
        """Validate CSRF token"""
        try:
            message, signature = token.rsplit('.', 1)
            expected = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected) and session_id in message
        except:
            return False

# server/api/dependencies.py
async def verify_csrf(
    request: Request,
    csrf_token: str = Header(..., alias="X-CSRF-Token")
):
    """Verify CSRF token for mutating requests"""
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        # Get session ID from cookie
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(status_code=403, detail="Missing session")
        
        csrf = CSRFProtection(settings.SECRET_KEY)
        if not csrf.validate_token(csrf_token, session_id):
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
```

**Estimación:** 3 días  
**Prioridad:** 🟠 ALTA

---

#### 2.6 Logging y Auditoría de Seguridad

**Tareas:**
- [ ] Implementar logging estructurado (JSON)
- [ ] Logging de intentos de login fallidos
- [ ] Logging de accesos a recursos sensibles
- [ ] Logging de cambios en configuración
- [ ] Implementar rotación de logs
- [ ] Agregar timestamps y user_id en todos los logs
- [ ] Configurar niveles de log apropiados
- [ ] Implementar envío de logs a servidor centralizado (opcional)

**Dependencias:**
```bash
pip install python-json-logger
```

**Código de ejemplo:**
```python
# server/core/logging_config.py
import logging
from pythonjsonlogger import jsonlogger

def setup_logging():
    logger = logging.getLogger()
    
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    return logger

# server/api/auth.py
import logging

security_logger = logging.getLogger('security')

@router.post("/login")
async def login_access_token(...) -> Any:
    # Log intento de login
    security_logger.info(
        "Login attempt",
        extra={
            "email": form_data.username,
            "ip": request.client.host,
            "user_agent": request.headers.get("user-agent")
        }
    )
    
    user = # ... validación
    
    if not user or not verify_password(...):
        security_logger.warning(
            "Failed login attempt",
            extra={
                "email": form_data.username,
                "ip": request.client.host,
                "reason": "invalid_credentials"
            }
        )
        raise HTTPException(...)
    
    security_logger.info(
        "Successful login",
        extra={
            "user_id": user.id,
            "email": user.email,
            "ip": request.client.host
        }
    )
    # ... resto del código
```

**Estimación:** 3 días  
**Prioridad:** 🟠 ALTA

---

#### 2.7 Reducir Expiración de Tokens

**Tareas:**
- [ ] Reducir ACCESS_TOKEN_EXPIRE_MINUTES a 1 hora
- [ ] Implementar refresh tokens
- [ ] Crear endpoint de refresh
- [ ] Implementar refresh automático en frontend
- [ ] Agregar revocación de refresh tokens
- [ ] Almacenar refresh tokens en base de datos
- [ ] Implementar sliding sessions

**Código de ejemplo:**
```python
# server/core/config.py
class Settings(BaseSettings):
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hora
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 días

# server/database/models.py
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)
    
    user = relationship("User")

# server/api/auth.py
@router.post("/refresh")
async def refresh_access_token(
    refresh_token: str = Cookie(...),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # Verify refresh token
    token_hash = get_password_hash(refresh_token)
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.now(timezone.utc)
    )
    result = await db.execute(stmt)
    refresh_token_obj = result.scalar_one_or_none()
    
    if not refresh_token_obj:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Generate new access token
    access_token = create_access_token(refresh_token_obj.user_id)
    
    return {"access_token": access_token, "token_type": "bearer"}
```

**Estimación:** 4 días  
**Prioridad:** 🟠 ALTA

---

### Fase 3: Hardening General (2-3 semanas)

**Objetivo:** Implementar mejores prácticas y defense-in-depth.

#### 3.1 HTTPS Enforcement

**Tareas:**
- [ ] Configurar Traefik/nginx con certificados SSL
- [ ] Implementar redirect HTTP → HTTPS
- [ ] Configurar HSTS headers
- [ ] Implementar certificate pinning (opcional)
- [ ] Configurar renovación automática de certificados (Let's Encrypt)
- [ ] Agregar verificación de certificados en agente

**Estimación:** 3 días  
**Prioridad:** 🟡 MEDIA

---

#### 3.2 Encriptación de Datos Sensibles

**Tareas:**
- [ ] Implementar encriptación de campos sensibles en BD
- [ ] Cifrar webhooks y API keys de notificaciones
- [ ] Implementar gestión de claves de cifrado
- [ ] Usar Fernet o similar para cifrado simétrico
- [ ] Documentar proceso de rotación de claves

**Dependencias:**
```bash
pip install cryptography
```

**Código de ejemplo:**
```python
# server/utils/encryption.py
from cryptography.fernet import Fernet
from core.config import settings

class FieldEncryption:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()

# server/database/models.py
from sqlalchemy.types import TypeDecorator, String

class EncryptedString(TypeDecorator):
    impl = String
    cache_ok = True
    
    def __init__(self, *args, **kwargs):
        self.encryptor = FieldEncryption(settings.ENCRYPTION_KEY.encode())
        super().__init__(*args, **kwargs)
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return self.encryptor.encrypt(value)
    
    def process_result_value(self, value, dialect):
        if value is not None:
            return self.encryptor.decrypt(value)

class NotificationConfig(Base):
    # ... otros campos
    webhook_url = Column(EncryptedString(500))  # Cifrado
```

**Estimación:** 4 días  
**Prioridad:** 🟡 MEDIA

---

#### 3.3 Verificación de Certificados en Agente

**Tareas:**
- [ ] Configurar cliente HTTP con verificación TLS
- [ ] Implementar certificate pinning
- [ ] Agregar manejo de errores de certificados
- [ ] Documentar configuración de certificados

**Código de ejemplo:**
```go
// agent/main.go
import (
    "crypto/tls"
    "crypto/x509"
    "io/ioutil"
)

func createSecureClient(caCertPath string) (*http.Client, error) {
    // Load CA cert
    caCert, err := ioutil.ReadFile(caCertPath)
    if err != nil {
        return nil, err
    }
    caCertPool := x509.NewCertPool()
    caCertPool.AppendCertsFromPEM(caCert)
    
    // Create TLS configuration
    tlsConfig := &tls.Config{
        RootCAs: caCertPool,
        MinVersion: tls.VersionTLS13,
    }
    
    // Create HTTP client
    client := &http.Client{
        Timeout: 10 * time.Second,
        Transport: &http.Transport{
            TLSClientConfig: tlsConfig,
        },
    }
    
    return client, nil
}
```

**Estimación:** 2 días  
**Prioridad:** 🟡 MEDIA

---

#### 3.4 Auditoría de Cambios en Base de Datos

**Tareas:**
- [ ] Crear tabla de auditoría
- [ ] Implementar triggers o event listeners
- [ ] Logging de INSERT/UPDATE/DELETE
- [ ] Almacenar usuario, timestamp, acción
- [ ] Implementar retention policy para logs de auditoría
- [ ] Crear endpoint de consulta de auditoría (admin only)

**Código de ejemplo:**
```python
# server/database/models.py
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)  # CREATE, UPDATE, DELETE
    table_name = Column(String, nullable=False)
    record_id = Column(String, nullable=False)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

# server/utils/audit.py
from sqlalchemy import event
from database.models import AuditLog

def log_change(session, action, instance, old_values=None, new_values=None):
    audit = AuditLog(
        user_id=get_current_user_id(),  # From context
        action=action,
        table_name=instance.__tablename__,
        record_id=str(instance.id),
        old_values=old_values,
        new_values=new_values
    )
    session.add(audit)

@event.listens_for(Host, 'after_insert')
def audit_host_insert(mapper, connection, target):
    # Log creation
    pass

@event.listens_for(Host, 'after_update')
def audit_host_update(mapper, connection, target):
    # Log update
    pass
```

**Estimación:** 4 días  
**Prioridad:** 🟡 MEDIA

---

#### 3.5 Validación de Tamaño de Payload

**Tareas:**
- [ ] Configurar límite de tamaño de request en FastAPI
- [ ] Implementar validación de tamaño de archivos (si aplica)
- [ ] Agregar límites específicos por endpoint
- [ ] Configurar timeout de requests

**Código de ejemplo:**
```python
# server/main.py
from fastapi.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_size:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request too large"}
                )
        return await call_next(request)

app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)
```

**Estimación:** 1 día  
**Prioridad:** 🟡 MEDIA

---

#### 3.6 XSS Prevention en Frontend

**Tareas:**
- [ ] Auditar todos los puntos de renderizado de datos
- [ ] Usar DOMPurify para sanitización
- [ ] Implementar CSP en Next.js
- [ ] Evitar dangerouslySetInnerHTML
- [ ] Validar inputs en formularios
- [ ] Implementar escaping automático

**Dependencias:**
```bash
npm install dompurify
npm install @types/dompurify --save-dev
```

**Código de ejemplo:**
```typescript
// frontend/src/utils/sanitize.ts
import DOMPurify from 'dompurify';

export function sanitizeHTML(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: [], // No HTML allowed
    KEEP_CONTENT: true
  });
}

export function sanitizeRichText(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br'],
    ALLOWED_ATTR: ['href']
  });
}

// Usage
import { sanitizeHTML } from '@/utils/sanitize';

function HostCard({ host }: { host: Host }) {
  return (
    <div>
      <h3>{sanitizeHTML(host.hostname)}</h3>
      <p>{sanitizeHTML(host.os)}</p>
    </div>
  );
}
```

**Estimación:** 2 días  
**Prioridad:** 🟡 MEDIA

---

### Fase 4: Monitoreo y Respuesta (1 semana)

**Objetivo:** Implementar detección y respuesta a incidentes.

#### 4.1 Sistema de Alertas de Seguridad

**Tareas:**
- [ ] Implementar detección de intentos de brute force
- [ ] Alertas por múltiples login fallidos
- [ ] Alertas por accesos no autorizados
- [ ] Alertas por cambios en configuración crítica
- [ ] Integración con sistema de notificaciones existente
- [ ] Dashboard de eventos de seguridad

**Estimación:** 5 días  
**Prioridad:** 🟢 BAJA

---

#### 4.2 Análisis de Vulnerabilidades Automatizado

**Tareas:**
- [ ] Integrar Bandit para análisis de código Python
- [ ] Integrar npm audit para dependencias JS
- [ ] Configurar GitHub Dependabot
- [ ] Implementar escaneo de secretos (trufflehog)
- [ ] Crear CI/CD pipeline con checks de seguridad

**Estimación:** 3 días  
**Prioridad:** 🟢 BAJA

---

#### 4.3 Plan de Respuesta a Incidentes

**Tareas:**
- [ ] Documentar procedimientos de respuesta
- [ ] Crear runbooks para diferentes tipos de incidentes
- [ ] Implementar proceso de backup y recuperación
- [ ] Documentar contactos de emergencia
- [ ] Crear checklist de post-mortem

**Estimación:** 2 días  
**Prioridad:** 🟢 BAJA

---

## 📅 Fases de Implementación

### Cronograma Recomendado

| Fase | Duración | Inicio | Fin | Esfuerzo |
|------|----------|--------|-----|----------|
| **Fase 1: Críticas** | 1-2 semanas | Inmediato | Semana 2 | 40-60 horas |
| **Fase 2: Alta** | 2-3 semanas | Semana 3 | Semana 5 | 60-80 horas |
| **Fase 3: Hardening** | 2-3 semanas | Semana 6 | Semana 8 | 50-70 horas |
| **Fase 4: Monitoreo** | 1 semana | Semana 9 | Semana 9 | 20-30 horas |
| **TOTAL** | **6-9 semanas** | | Semana 9 | **170-240 horas** |

### Hitos Importantes

- **Semana 2:** ✅ Sistema seguro para ambiente de staging
- **Semana 5:** ✅ Sistema seguro para producción limitada
- **Semana 8:** ✅ Sistema hardened con defense-in-depth
- **Semana 9:** ✅ Sistema con monitoreo completo de seguridad

---

## ✅ Checklist de Seguridad

### Pre-Deployment (Crítico)

- [ ] SECRET_KEY única y aleatoria configurada via env
- [ ] Credenciales de BD en variables de entorno
- [ ] Admin password cambiado del valor por defecto
- [ ] CORS configurado con origins específicos
- [ ] Tokens en HttpOnly cookies (no localStorage)
- [ ] Rate limiting implementado en login
- [ ] Autenticación robusta del agente con API keys

### Pre-Production (Alta Prioridad)

- [ ] Validación de passwords (12+ caracteres, complejidad)
- [ ] Headers de seguridad HTTP configurados
- [ ] Sanitización de inputs implementada
- [ ] CSRF protection habilitado
- [ ] Logging de seguridad funcional
- [ ] Tokens con expiración de 1 hora + refresh tokens
- [ ] Revocación de tokens implementada

### Post-Production (Hardening)

- [ ] HTTPS enforcement configurado
- [ ] Certificados SSL válidos y renovación automática
- [ ] Encriptación de datos sensibles en BD
- [ ] Auditoría de cambios activa
- [ ] Límites de payload configurados
- [ ] XSS prevention en todo el frontend
- [ ] Verificación de certificados en agente

### Monitoreo Continuo

- [ ] Alertas de seguridad configuradas
- [ ] Análisis de vulnerabilidades automatizado
- [ ] Plan de respuesta a incidentes documentado
- [ ] Backups automáticos configurados
- [ ] Logs de seguridad monitoreados
- [ ] Revisiones de seguridad periódicas programadas

---

## 🎯 Mejores Prácticas

### Desarrollo Seguro

1. **Principle of Least Privilege**: Dar solo los permisos necesarios
2. **Defense in Depth**: Múltiples capas de seguridad
3. **Fail Securely**: Fallar de manera segura, cerrar acceso por defecto
4. **Don't Trust User Input**: Validar y sanitizar siempre
5. **Keep Secrets Secret**: Nunca en código, siempre en env
6. **Logging Everything**: Pero sin información sensible
7. **Update Dependencies**: Mantener librerías actualizadas
8. **Review Code**: Peer reviews con enfoque en seguridad

### Testing de Seguridad

```bash
# Backend
bandit -r server/
pip-audit

# Frontend
npm audit
npm audit fix

# Secrets scanning
trufflehog filesystem . --only-verified

# SAST
sonarqube-scanner

# DAST (en staging)
zap-baseline.py -t http://staging.lams.io
```

### Deployment Seguro

```yaml
# docker-compose.yml
services:
  api:
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - ENVIRONMENT=production
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    networks:
      - internal
```

---

## 📚 Referencias

### Estándares y Frameworks

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **OWASP API Security**: https://owasp.org/www-project-api-security/
- **CWE/SANS Top 25**: https://cwe.mitre.org/top25/
- **NIST Cybersecurity Framework**: https://www.nist.gov/cyberframework

### Herramientas Recomendadas

- **Bandit**: https://bandit.readthedocs.io/ - SAST para Python
- **Safety**: https://pyup.io/safety/ - Análisis de dependencias Python
- **npm audit**: Built-in en npm - Análisis de dependencias JS
- **Snyk**: https://snyk.io/ - Análisis de vulnerabilidades
- **OWASP ZAP**: https://www.zaproxy.org/ - DAST scanner
- **Trivy**: https://trivy.dev/ - Scanner de containers

### Documentación de Bibliotecas

- **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/
- **Next.js Security**: https://nextjs.org/docs/advanced-features/security-headers
- **PostgreSQL Security**: https://www.postgresql.org/docs/current/security.html
- **Argon2**: https://github.com/P-H-C/phc-winner-argon2

---

## 📝 Conclusiones

### Resumen

El sistema LAMS presenta **vulnerabilidades críticas** que impiden su despliegue seguro en producción. Las áreas más problemáticas son:

1. **Gestión de secretos** - Hardcoded en código fuente
2. **Autenticación** - Débil y con credenciales por defecto
3. **Comunicación** - Sin cifrado ni autenticación robusta
4. **Validación** - Insuficiente en inputs de usuario
5. **Frontend** - Vulnerable a XSS y almacenamiento inseguro

### Recomendación Final

**NO DESPLEGAR EN PRODUCCIÓN** hasta completar al menos la **Fase 1 (Críticas)** y **Fase 2 (Alta Severidad)**.

**Tiempo estimado para producción segura: 5-6 semanas**

Una vez implementadas las fases 1 y 2, el sistema estará en condiciones de deployment en producción con un nivel de riesgo aceptable. Las fases 3 y 4 son altamente recomendadas para un sistema robusto y enterprise-grade.

### Próximos Pasos

1. **Inmediato**: Revisar y aprobar este plan con stakeholders
2. **Semana 1**: Comenzar implementación de Fase 1
3. **Semana 3**: Testing de seguridad de Fase 1
4. **Semana 4**: Iniciar Fase 2
5. **Semana 6**: Penetration testing externo (recomendado)
6. **Semana 7**: Deployment en staging
7. **Semana 9**: Go-live en producción

---

**Documento preparado por:** Security Review Team  
**Fecha:** 9 de marzo de 2026  
**Versión:** 1.0  
**Próxima revisión:** Después de implementar Fase 1
