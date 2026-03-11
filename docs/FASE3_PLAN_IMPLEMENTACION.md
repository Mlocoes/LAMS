# FASE 3: PLAN DE IMPLEMENTACIÓN - Vulnerabilidades de Severidad Media

**Fecha de Inicio:** 9 de marzo de 2026  
**Estado:** Planificación  
**Prerrequisito:** Fase 2 Completada (7/7) ✅  
**CVSS Actual:** 3.8 (Low-Medium)  
**CVSS Objetivo:** < 3.0 (Low)

---

## 📋 Resumen Ejecutivo

La Fase 3 del plan de remediación de seguridad aborda **6 vulnerabilidades de severidad MEDIA** identificadas en el análisis inicial. Estas vulnerabilidades, aunque menos críticas que las de Fase 1 y 2, son importantes para alcanzar un nivel de seguridad enterprise y cumplir con estándares de compliance.

### Objetivos de Fase 3

- ✅ Reducir CVSS Score de 3.8 a < 3.0
- ✅ Implementar controles de acceso avanzados
- ✅ Mejorar gestión de sesiones
- ✅ Proteger datos sensibles en reposo
- ✅ Preparar sistema para auditorías de seguridad

---

## 🎯 Vulnerabilidades a Abordar

| ID | Vulnerabilidad | Severidad | CVSS | Complejidad | Tiempo Estimado |
|---|---|---|---|---|---|
| 3.1 | Múltiples sesiones simultáneas sin límite | Media | 5.0 | Media | 4-6 horas |
| 3.2 | Sin autenticación de múltiples factores (MFA) | Media | 5.5 | Alta | 8-12 horas |
| 3.3 | Tokens en URL query params (documentación) | Media | 4.0 | Baja | 2-3 horas |
| 3.4 | Sin cifrado de datos sensibles en BD | Media | 5.8 | Alta | 6-8 horas |
| 3.5 | Sin rotación automática de secrets | Media | 4.5 | Media | 4-6 horas |
| 3.6 | Logs sin cifrado en almacenamiento | Media | 4.2 | Media | 4-6 horas |

**Tiempo Total Estimado:** 28-41 horas (~4-5 días de desarrollo)

---

## 🛡️ 3.1 Límite de Sesiones Simultáneas

### Problema
Un usuario puede tener sesiones ilimitadas activas simultáneamente desde diferentes dispositivos. Esto aumenta el riesgo si las credenciales son comprometidas, ya que el atacante puede mantener acceso incluso después de que el usuario legítimo cambie su contraseña.

**CVSS Score:** 5.0 (Medium)  
**CWE:** CWE-384: Session Fixation  
**OWASP:** A07:2021 - Identification and Authentication Failures

### Solución Propuesta

**Enfoque:** Sistema de gestión de sesiones con límite configurable por usuario.

#### Componentes a Implementar

1. **Base de Datos: Tabla `user_sessions`**
   ```sql
   CREATE TABLE user_sessions (
       id SERIAL PRIMARY KEY,
       user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
       session_token VARCHAR(64) UNIQUE NOT NULL,
       refresh_token_id INTEGER REFERENCES refresh_tokens(id),
       device_name VARCHAR(255),
       device_type VARCHAR(50),  -- desktop, mobile, tablet
       browser VARCHAR(100),
       os VARCHAR(100),
       ip_address VARCHAR(45),
       user_agent TEXT,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       expires_at TIMESTAMP WITH TIME ZONE,
       is_active BOOLEAN DEFAULT TRUE
   );
   
   CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
   CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
   CREATE INDEX idx_user_sessions_active ON user_sessions(is_active);
   ```

2. **Modelo SQLAlchemy**
   ```python
   # server/database/models.py
   class UserSession(Base):
       __tablename__ = "user_sessions"
       
       id = Column(Integer, primary_key=True, index=True)
       user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
       session_token = Column(String(64), unique=True, nullable=False)
       refresh_token_id = Column(Integer, ForeignKey("refresh_tokens.id"))
       device_name = Column(String(255))
       device_type = Column(String(50))
       browser = Column(String(100))
       os = Column(String(100))
       ip_address = Column(String(45))
       user_agent = Column(Text)
       created_at = Column(DateTime(timezone=True), server_default=func.now())
       last_activity = Column(DateTime(timezone=True), server_default=func.now())
       expires_at = Column(DateTime(timezone=True))
       is_active = Column(Boolean, default=True)
       
       user = relationship("User", back_populates="sessions")
       refresh_token = relationship("RefreshToken")
   ```

3. **Configuración**
   ```python
   # server/core/config.py
   class Settings(BaseSettings):
       # ... existing settings
       
       # Phase 3.1: Session management
       MAX_SESSIONS_PER_USER: int = Field(default=5, env="MAX_SESSIONS_PER_USER")
       SESSION_IDLE_TIMEOUT_MINUTES: int = Field(default=30, env="SESSION_IDLE_TIMEOUT_MINUTES")
       SESSION_ABSOLUTE_TIMEOUT_DAYS: int = Field(default=7, env="SESSION_ABSOLUTE_TIMEOUT_DAYS")
   ```

4. **Servicio de Gestión de Sesiones**
   ```python
   # server/services/session_service.py
   from user_agents import parse
   
   class SessionService:
       @staticmethod
       async def create_session(
           db: AsyncSession,
           user_id: int,
           request: Request,
           refresh_token_id: int
       ) -> UserSession:
           """Crea nueva sesión y limpia sesiones excedidas"""
           
           # Parse user agent
           user_agent = parse(request.headers.get("user-agent", ""))
           
           # Verificar límite de sesiones activas
           active_sessions = await SessionService.get_active_sessions(db, user_id)
           
           if len(active_sessions) >= settings.MAX_SESSIONS_PER_USER:
               # Cerrar sesión más antigua
               oldest_session = min(active_sessions, key=lambda s: s.last_activity)
               await SessionService.terminate_session(db, oldest_session.id)
           
           # Crear nueva sesión
           session = UserSession(
               user_id=user_id,
               session_token=secrets.token_urlsafe(32),
               refresh_token_id=refresh_token_id,
               device_name=user_agent.device.family,
               device_type=SessionService._detect_device_type(user_agent),
               browser=f"{user_agent.browser.family} {user_agent.browser.version_string}",
               os=f"{user_agent.os.family} {user_agent.os.version_string}",
               ip_address=request.client.host if request.client else None,
               user_agent=request.headers.get("user-agent"),
               expires_at=datetime.now(timezone.utc) + timedelta(
                   days=settings.SESSION_ABSOLUTE_TIMEOUT_DAYS
               )
           )
           
           db.add(session)
           await db.commit()
           await db.refresh(session)
           
           return session
       
       @staticmethod
       async def get_active_sessions(
           db: AsyncSession,
           user_id: int
       ) -> List[UserSession]:
           """Obtiene sesiones activas de un usuario"""
           stmt = select(UserSession).where(
               UserSession.user_id == user_id,
               UserSession.is_active == True,
               UserSession.expires_at > datetime.now(timezone.utc)
           )
           result = await db.execute(stmt)
           return result.scalars().all()
       
       @staticmethod
       async def update_activity(
           db: AsyncSession,
           session_token: str
       ):
           """Actualiza timestamp de última actividad"""
           stmt = select(UserSession).where(
               UserSession.session_token == session_token
           )
           result = await db.execute(stmt)
           session = result.scalar_one_or_none()
           
           if session:
               session.last_activity = datetime.now(timezone.utc)
               await db.commit()
       
       @staticmethod
       async def terminate_session(
           db: AsyncSession,
           session_id: int
       ):
           """Termina una sesión específica"""
           stmt = select(UserSession).where(UserSession.id == session_id)
           result = await db.execute(stmt)
           session = result.scalar_one_or_none()
           
           if session:
               session.is_active = False
               await db.commit()
       
       @staticmethod
       async def cleanup_expired_sessions(db: AsyncSession):
           """Job: Limpia sesiones expiradas o inactivas"""
           # Sesiones absolutamente expiradas
           stmt = select(UserSession).where(
               UserSession.expires_at < datetime.now(timezone.utc)
           )
           result = await db.execute(stmt)
           expired = result.scalars().all()
           
           for session in expired:
               session.is_active = False
           
           # Sesiones inactivas por timeout
           idle_threshold = datetime.now(timezone.utc) - timedelta(
               minutes=settings.SESSION_IDLE_TIMEOUT_MINUTES
           )
           stmt = select(UserSession).where(
               UserSession.last_activity < idle_threshold,
               UserSession.is_active == True
           )
           result = await db.execute(stmt)
           idle = result.scalars().all()
           
           for session in idle:
               session.is_active = False
           
           await db.commit()
   ```

5. **Endpoints de API**
   ```python
   # server/api/sessions.py
   router = APIRouter()
   
   @router.get("/sessions")
   async def list_sessions(
       current_user: User = Depends(get_current_user),
       db: AsyncSession = Depends(get_db)
   ):
       """Lista todas las sesiones activas del usuario"""
       sessions = await SessionService.get_active_sessions(db, current_user.id)
       
       return [{
           "id": s.id,
           "device_name": s.device_name,
           "device_type": s.device_type,
           "browser": s.browser,
           "os": s.os,
           "ip_address": s.ip_address,
           "created_at": s.created_at,
           "last_activity": s.last_activity,
           "is_current": s.session_token == request.cookies.get("session_token")
       } for s in sessions]
   
   @router.delete("/sessions/{session_id}")
   async def terminate_session(
       session_id: int,
       current_user: User = Depends(get_current_user),
       db: AsyncSession = Depends(get_db)
   ):
       """Termina una sesión específica"""
       # Verificar que la sesión pertenece al usuario
       stmt = select(UserSession).where(
           UserSession.id == session_id,
           UserSession.user_id == current_user.id
       )
       result = await db.execute(stmt)
       session = result.scalar_one_or_none()
       
       if not session:
           raise HTTPException(status_code=404, detail="Sesión no encontrada")
       
       await SessionService.terminate_session(db, session_id)
       
       return {"message": "Sesión terminada exitosamente"}
   
   @router.delete("/sessions")
   async def terminate_all_sessions(
       current_user: User = Depends(get_current_user),
       db: AsyncSession = Depends(get_db)
   ):
       """Termina todas las sesiones excepto la actual"""
       current_session_token = request.cookies.get("session_token")
       
       sessions = await SessionService.get_active_sessions(db, current_user.id)
       
       for session in sessions:
           if session.session_token != current_session_token:
               await SessionService.terminate_session(db, session.id)
       
       return {"message": f"{len(sessions) - 1} sesiones terminadas"}
   ```

#### Testing

```bash
# Test 1: Crear 5 sesiones y verificar límite
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/auth/login \
    -d "username=test@example.com&password=TestPass123!@#" \
    -c "cookies_$i.txt"
done

# Test 2: Listar sesiones activas
curl http://localhost:8000/api/sessions \
  -b cookies_1.txt

# Test 3: Terminar sesión específica
curl -X DELETE http://localhost:8000/api/sessions/123 \
  -b cookies_1.txt

# Test 4: Terminar todas las sesiones
curl -X DELETE http://localhost:8000/api/sessions \
  -b cookies_1.txt
```

**Impacto en Seguridad:**
- ✅ Limita superficie de ataque (máximo 5 sesiones)
- ✅ Permite al usuario ver y gestionar sesiones activas
- ✅ Detecta accesos desde dispositivos desconocidos
- ✅ Cumple con OWASP ASVS 3.2.1 - 3.2.3
- 🔒 CVSS Reducido: 5.0 → 3.2

---

## 🔐 3.2 Autenticación de Múltiples Factores (MFA/2FA)

### Problema
El sistema solo utiliza autenticación de un factor (contraseña). Si una contraseña es comprometida (phishing, keylogger, filtración), el atacante obtiene acceso completo a la cuenta.

**CVSS Score:** 5.5 (Medium)  
**CWE:** CWE-308: Use of Single-factor Authentication  
**OWASP:** A07:2021 - Identification and Authentication Failures

### Solución Propuesta

**Enfoque:** TOTP (Time-based One-Time Password) usando estándar RFC 6238, compatible con Google Authenticator, Microsoft Authenticator, Authy, etc.

#### Componentes a Implementar

1. **Dependencias**
   ```txt
   # server/requirements.txt
   pyotp==2.9.0              # TOTP implementation
   qrcode[pil]==7.4.2        # QR code generation
   ```

2. **Base de Datos: Tabla `user_mfa`**
   ```sql
   CREATE TABLE user_mfa (
       id SERIAL PRIMARY KEY,
       user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
       mfa_enabled BOOLEAN DEFAULT FALSE NOT NULL,
       mfa_secret VARCHAR(32) NOT NULL,  -- Base32-encoded secret
       mfa_method VARCHAR(20) DEFAULT 'totp',  -- totp, sms, email (future)
       backup_codes TEXT[],  -- Array of backup codes
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       enabled_at TIMESTAMP WITH TIME ZONE,
       last_used TIMESTAMP WITH TIME ZONE
   );
   
   CREATE INDEX idx_user_mfa_user_id ON user_mfa(user_id);
   CREATE INDEX idx_user_mfa_enabled ON user_mfa(mfa_enabled);
   ```

3. **Modelo SQLAlchemy**
   ```python
   # server/database/models.py
   from sqlalchemy.dialects.postgresql import ARRAY
   
   class UserMFA(Base):
       __tablename__ = "user_mfa"
       
       id = Column(Integer, primary_key=True, index=True)
       user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
       mfa_enabled = Column(Boolean, default=False, nullable=False)
       mfa_secret = Column(String(32), nullable=False)
       mfa_method = Column(String(20), default="totp")
       backup_codes = Column(ARRAY(String))
       created_at = Column(DateTime(timezone=True), server_default=func.now())
       enabled_at = Column(DateTime(timezone=True))
       last_used = Column(DateTime(timezone=True))
       
       user = relationship("User", back_populates="mfa")
   ```

4. **Servicio MFA**
   ```python
   # server/services/mfa_service.py
   import pyotp
   import qrcode
   from io import BytesIO
   import base64
   import secrets
   
   class MFAService:
       @staticmethod
       def generate_secret() -> str:
           """Genera secret TOTP de 32 caracteres base32"""
           return pyotp.random_base32()
       
       @staticmethod
       def generate_qr_code(
           email: str,
           secret: str,
           issuer: str = "LAMS"
       ) -> str:
           """Genera código QR para configurar authenticator app"""
           totp = pyotp.TOTP(secret)
           provisioning_uri = totp.provisioning_uri(
               name=email,
               issuer_name=issuer
           )
           
           # Generar QR
           qr = qrcode.QRCode(version=1, box_size=10, border=5)
           qr.add_data(provisioning_uri)
           qr.make(fit=True)
           
           img = qr.make_image(fill_color="black", back_color="white")
           
           # Convertir a base64
           buffer = BytesIO()
           img.save(buffer, format="PNG")
           img_str = base64.b64encode(buffer.getvalue()).decode()
           
           return f"data:image/png;base64,{img_str}"
       
       @staticmethod
       def verify_totp(secret: str, code: str) -> bool:
           """Verifica código TOTP (6 dígitos)"""
           totp = pyotp.TOTP(secret)
           return totp.verify(code, valid_window=1)  # ±30 segundos
       
       @staticmethod
       def generate_backup_codes(count: int = 10) -> List[str]:
           """Genera códigos de backup (8 caracteres alfanuméricos)"""
           codes = []
           for _ in range(count):
               code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') 
                             for _ in range(8))
               codes.append(code)
           return codes
       
       @staticmethod
       async def enable_mfa(
           db: AsyncSession,
           user_id: int,
           secret: str,
           backup_codes: List[str]
       ):
           """Habilita MFA para un usuario"""
           stmt = select(UserMFA).where(UserMFA.user_id == user_id)
           result = await db.execute(stmt)
           mfa = result.scalar_one_or_none()
           
           if mfa:
               mfa.mfa_enabled = True
               mfa.mfa_secret = secret
               mfa.backup_codes = backup_codes
               mfa.enabled_at = datetime.now(timezone.utc)
           else:
               mfa = UserMFA(
                   user_id=user_id,
                   mfa_enabled=True,
                   mfa_secret=secret,
                   backup_codes=backup_codes,
                   enabled_at=datetime.now(timezone.utc)
               )
               db.add(mfa)
           
           await db.commit()
           await db.refresh(mfa)
           return mfa
       
       @staticmethod
       async def verify_code(
           db: AsyncSession,
           user_id: int,
           code: str
       ) -> bool:
           """Verifica código TOTP o código de backup"""
           stmt = select(UserMFA).where(
               UserMFA.user_id == user_id,
               UserMFA.mfa_enabled == True
           )
           result = await db.execute(stmt)
           mfa = result.scalar_one_or_none()
           
           if not mfa:
               return False
           
           # Verificar TOTP
           if MFAService.verify_totp(mfa.mfa_secret, code):
               mfa.last_used = datetime.now(timezone.utc)
               await db.commit()
               return True
           
           # Verificar backup code
           if code in mfa.backup_codes:
               # Remover código usado
               mfa.backup_codes.remove(code)
               mfa.last_used = datetime.now(timezone.utc)
               await db.commit()
               return True
           
           return False
   ```

5. **Endpoints de API**
   ```python
   # server/api/mfa.py
   router = APIRouter()
   
   @router.post("/mfa/setup")
   async def setup_mfa(
       current_user: User = Depends(get_current_user),
       db: AsyncSession = Depends(get_db)
   ):
       """Inicia proceso de configuración MFA"""
       # Generar nuevo secret
       secret = MFAService.generate_secret()
       
       # Generar QR code
       qr_code = MFAService.generate_qr_code(current_user.email, secret)
       
       # Generar backup codes
       backup_codes = MFAService.generate_backup_codes()
       
       # Almacenar temporalmente (no habilitar aún)
       # Usuario debe verificar primero
       
       return {
           "secret": secret,
           "qr_code": qr_code,
           "backup_codes": backup_codes,
           "message": "Escanea el código QR con tu app de autenticación y verifica con un código"
       }
   
   @router.post("/mfa/enable")
   async def enable_mfa(
       verification_code: str,
       secret: str,
       backup_codes: List[str],
       current_user: User = Depends(get_current_user),
       db: AsyncSession = Depends(get_db)
   ):
       """Habilita MFA después de verificar código"""
       # Verificar código TOTP
       if not MFAService.verify_totp(secret, verification_code):
           raise HTTPException(
               status_code=400,
               detail="Código de verificación inválido"
           )
       
       # Habilitar MFA
       await MFAService.enable_mfa(db, current_user.id, secret, backup_codes)
       
       return {
           "message": "MFA habilitado exitosamente",
           "backup_codes": backup_codes
       }
   
   @router.post("/mfa/verify")
   async def verify_mfa(
       code: str,
       user_id: int,
       db: AsyncSession = Depends(get_db)
   ):
       """Verifica código MFA durante login"""
       is_valid = await MFAService.verify_code(db, user_id, code)
       
       if not is_valid:
           raise HTTPException(
               status_code=400,
               detail="Código MFA inválido o expirado"
           )
       
       return {"message": "Código verificado"}
   
   @router.delete("/mfa")
   async def disable_mfa(
       password: str,
       current_user: User = Depends(get_current_user),
       db: AsyncSession = Depends(get_db)
   ):
       """Deshabilita MFA (requiere contraseña)"""
       # Verificar contraseña
       if not verify_password(password, current_user.password_hash):
           raise HTTPException(status_code=400, detail="Contraseña incorrecta")
       
       # Deshabilitar MFA
       stmt = select(UserMFA).where(UserMFA.user_id == current_user.id)
       result = await db.execute(stmt)
       mfa = result.scalar_one_or_none()
       
       if mfa:
           mfa.mfa_enabled = False
           await db.commit()
       
       return {"message": "MFA deshabilitado"}
   ```

6. **Modificar Login para MFA**
   ```python
   # server/api/auth.py
   @router.post("/login")
   async def login_access_token(...):
       # ... verificación de contraseña ...
       
       # Verificar si MFA está habilitado
       stmt = select(UserMFA).where(
           UserMFA.user_id == user.id,
           UserMFA.mfa_enabled == True
       )
       result = await db.execute(stmt)
       mfa = result.scalar_one_or_none()
       
       if mfa:
           # MFA requerido - devolver token temporal
           temp_token = create_access_token(
               user.id,
               expires_delta=timedelta(minutes=5),
               data={"mfa_required": True}
           )
           
           return {
               "mfa_required": True,
               "temp_token": temp_token,
               "message": "Ingresa tu código de autenticación de dos factores"
           }
       
       # ... resto del flujo normal ...
   
   @router.post("/login/mfa")
   async def complete_mfa_login(
       temp_token: str,
       code: str,
       response: Response,
       db: AsyncSession = Depends(get_db)
   ):
       """Completa login después de verificar código MFA"""
       # Verificar temp_token
       payload = jwt.decode(temp_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
       
       if not payload.get("mfa_required"):
           raise HTTPException(status_code=400, detail="Token inválido")
       
       user_id = payload.get("sub")
       
       # Verificar código MFA
       is_valid = await MFAService.verify_code(db, user_id, code)
       
       if not is_valid:
           raise HTTPException(status_code=400, detail="Código MFA inválido")
       
       # Crear tokens finales (igual que login normal)
       # ... crear access_token, refresh_token, csrf_token ...
       
       return {
           "access_token": access_token,
           "token_type": "bearer",
           # ... resto de respuesta
       }
   ```

#### Frontend Integration

```javascript
// 1. Configurar MFA
const setupMFA = async () => {
  const response = await fetch('/api/mfa/setup', {
    method: 'POST',
    credentials: 'include'
  });
  
  const data = await response.json();
  
  // Mostrar QR code
  document.getElementById('qr-code').src = data.qr_code;
  
  // Mostrar backup codes
  showBackupCodes(data.backup_codes);
  
  // Guardar secret temporalmente
  localStorage.setItem('mfa_secret_temp', data.secret);
  localStorage.setItem('backup_codes_temp', JSON.stringify(data.backup_codes));
};

// 2. Verificar y habilitar
const enableMFA = async (code) => {
  const secret = localStorage.getItem('mfa_secret_temp');
  const backupCodes = JSON.parse(localStorage.getItem('backup_codes_temp'));
  
  const response = await fetch('/api/mfa/enable', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      verification_code: code,
      secret: secret,
      backup_codes: backupCodes
    })
  });
  
  if (response.ok) {
    alert('MFA habilitado exitosamente');
    // Limpiar storage temporal
    localStorage.removeItem('mfa_secret_temp');
    localStorage.removeItem('backup_codes_temp');
  }
};

// 3. Login con MFA
const login = async (email, password) => {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    body: new URLSearchParams({ username: email, password }),
    credentials: 'include'
  });
  
  const data = await response.json();
  
  if (data.mfa_required) {
    // Mostrar input para código MFA
    const mfaCode = prompt('Ingresa tu código MFA:');
    
    // Completar login con MFA
    const mfaResponse = await fetch('/api/auth/login/mfa', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        temp_token: data.temp_token,
        code: mfaCode
      })
    });
    
    if (mfaResponse.ok) {
      window.location.href = '/dashboard';
    }
  } else {
    // Login normal sin MFA
    window.location.href = '/dashboard';
  }
};
```

#### Testing

```bash
# Test 1: Configurar MFA
curl -X POST http://localhost:8000/api/mfa/setup \
  -b cookies.txt

# Test 2: Habilitar MFA con código
curl -X POST http://localhost:8000/api/mfa/enable \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"verification_code":"123456","secret":"ABCD...","backup_codes":[...]}'

# Test 3: Login con MFA
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=test@example.com&password=TestPass123!@#"

# Test 4: Completar login con código MFA
curl -X POST http://localhost:8000/api/auth/login/mfa \
  -H "Content-Type: application/json" \
  -d '{"temp_token":"eyJ...","code":"123456"}'
```

**Impacto en Seguridad:**
- ✅ Protege contra phishing de contraseñas
- ✅ Protege contra keyloggers
- ✅ Protege contra credential stuffing
- ✅ Compatible con apps de autenticación estándar
- ✅ Códigos de backup para recuperación
- ✅ Cumple con OWASP ASVS 2.8.1 - 2.8.5
- 🔒 CVSS Reducido: 5.5 → 2.8

---

## 📄 3.3 Eliminar Tokens de URL Query Params

### Problema
La documentación interactiva de FastAPI (/docs, /redoc) permite incluir tokens JWT en query parameters para testing. Esto es inseguro porque los tokens pueden ser registrados en logs del servidor, historial del navegador, y referrer headers.

**CVSS Score:** 4.0 (Medium)  
**CWE:** CWE-598: Use of GET Request Method With Sensitive Query Strings  
**OWASP:** A01:2021 - Broken Access Control

### Solución Propuesta

**Enfoque:** Deshabilitar documentación interactiva en producción y forzar uso de cookies/headers.

#### Implementación

```python
# server/main.py
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    # Phase 3.3: Deshabilitar docs en producción
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
)

# Middleware para bloquear acceso a /docs en producción
@app.middleware("http")
async def block_docs_in_production(request: Request, call_next):
    if settings.ENVIRONMENT == "production":
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            raise HTTPException(
                status_code=404,
                detail="Documentación no disponible en producción"
            )
    
    response = await call_next(request)
    return response
```

**Configuración:**
```bash
# .env (producción)
ENVIRONMENT=production  # Deshabilita /docs automáticamente
```

**Testing:**
```bash
# Development (docs disponibles)
curl http://localhost:8000/docs
# Esperado: HTML de Swagger UI

# Production (docs bloqueados)
ENVIRONMENT=production curl http://localhost:8000/docs
# Esperado: HTTP 404
```

**Impacto en Seguridad:**
- ✅ Previene fuga de tokens en logs
- ✅ Previene fuga de tokens en historial de navegador
- ✅ Reduce superficie de ataque en producción
- 🔒 CVSS Reducido: 4.0 → 2.5

---

## 🔒 3.4 Cifrado de Datos Sensibles en BD

### Problema
Datos sensibles como tokens de API del agente, contraseñas de BD en logs, etc. se almacenan en texto plano en la base de datos. Si la BD es comprometida, toda la información queda expuesta.

**CVSS Score:** 5.8 (Medium)  
**CWE:** CWE-311: Missing Encryption of Sensitive Data  
**OWASP:** A02:2021 - Cryptographic Failures

### Solución Propuesta

**Enfoque:** Cifrado a nivel de aplicación usando Fernet (AES128 en modo CBC con HMAC).

#### Componentes a Implementar

1. **Dependencias**
   ```txt
   # server/requirements.txt
   cryptography==42.0.0  # Ya instalado
   ```

2. **Servicio de Cifrado**
   ```python
   # server/services/encryption_service.py
   from cryptography.fernet import Fernet
   from core.config import settings
   import base64
   
   class EncryptionService:
       @staticmethod
       def _get_fernet():
           """Obtiene instancia Fernet con clave de settings"""
           # ENCRYPTION_KEY debe ser una clave Fernet de 32 bytes base64
           return Fernet(settings.ENCRYPTION_KEY)
       
       @staticmethod
       def encrypt(plaintext: str) -> str:
           """Cifra texto plano"""
           if not plaintext:
               return plaintext
           
           f = EncryptionService._get_fernet()
           encrypted = f.encrypt(plaintext.encode())
           return encrypted.decode()
       
       @staticmethod
       def decrypt(ciphertext: str) -> str:
           """Descifra texto cifrado"""
           if not ciphertext:
               return ciphertext
           
           f = EncryptionService._get_fernet()
           decrypted = f.decrypt(ciphertext.encode())
           return decrypted.decode()
       
       @staticmethod
       def generate_key() -> str:
           """Genera nueva clave de cifrado"""
           return Fernet.generate_key().decode()
   ```

3. **Campos Cifrados en Modelos**
   ```python
   # server/database/models.py
   from sqlalchemy.ext.hybrid import hybrid_property
   from services.encryption_service import EncryptionService
   
   class AgentAPIKey(Base):
       __tablename__ = "agent_api_keys"
       
       id = Column(Integer, primary_key=True, index=True)
       key_name = Column(String(255), nullable=False)
       _key_hash = Column("key_hash", String(255), unique=True, nullable=False)
       
       # Hybrid property para cifrado automático
       @hybrid_property
       def key_hash(self):
           """Descifra al leer"""
           return EncryptionService.decrypt(self._key_hash)
       
       @key_hash.setter
       def key_hash(self, value):
           """Cifra al escribir"""
           self._key_hash = EncryptionService.encrypt(value)
   ```

4. **Configuración**
   ```python
   # server/core/config.py
   class Settings(BaseSettings):
       # ... existing settings
       
       # Phase 3.4: Field-level encryption
       ENCRYPTION_KEY: str = Field(..., env="ENCRYPTION_KEY")
       
       @validator("ENCRYPTION_KEY")
       def validate_encryption_key(cls, v):
           if v == "CHANGE_THIS_ENCRYPTION_KEY":
               raise ValueError("ENCRYPTION_KEY must be changed from default")
           
           # Verificar que es una clave Fernet válida
           try:
               Fernet(v.encode())
           except Exception:
               raise ValueError("ENCRYPTION_KEY must be a valid Fernet key")
           
           return v
   ```

5. **Script de Generación de Clave**
   ```python
   # server/scripts/generate_encryption_key.py
   from cryptography.fernet import Fernet
   
   if __name__ == "__main__":
       key = Fernet.generate_key()
       print("Generated Encryption Key:")
       print(key.decode())
       print("\nAdd this to your .env file:")
       print(f"ENCRYPTION_KEY={key.decode()}")
   ```

6. **Migración de Datos Existentes**
   ```python
   # server/migrations/encrypt_existing_data.py
   async def encrypt_existing_agent_keys():
       """Cifra claves de agente existentes"""
       async with async_session_maker() as db:
           stmt = select(AgentAPIKey)
           result = await db.execute(stmt)
           keys = result.scalars().all()
           
           for key in keys:
               # Leer valor sin cifrar
               plaintext = key._key_hash
               
               # Verificar si ya está cifrado
               try:
                   EncryptionService.decrypt(plaintext)
                   continue  # Ya cifrado
               except:
                   # Cifrar
                   key._key_hash = EncryptionService.encrypt(plaintext)
           
           await db.commit()
           print(f"Encrypted {len(keys)} agent keys")
   ```

**Testing:**
```python
# Test cifrado/descifrado
plaintext = "my_secret_api_key_12345"
encrypted = EncryptionService.encrypt(plaintext)
decrypted = EncryptionService.decrypt(encrypted)

assert plaintext != encrypted  # Debe estar cifrado
assert plaintext == decrypted  # Debe descifrar correctamente
```

**Impacto en Seguridad:**
- ✅ Protege datos sensibles en BD
- ✅ Cumple con GDPR/PCI-DSS (encryption at rest)
- ✅ Usa algoritmo seguro (AES128 + HMAC)
- 🔒 CVSS Reducido: 5.8 → 3.5

---

## 🔄 3.5 Rotación Automática de Secrets

### Problema
Las claves secretas (SECRET_KEY, ENCRYPTION_KEY) nunca se rotan. Si son comprometidas, permanecen válidas indefinidamente.

**CVSS Score:** 4.5 (Medium)  
**CWE:** CWE-320: Key Management Errors  
**OWASP:** A02:2021 - Cryptographic Failures

### Solución Propuesta

**Enfoque:** Sistema de versionado de claves con rotación periódica (90 días).

#### Implementación

```python
# server/services/key_rotation_service.py
class KeyRotationService:
    @staticmethod
    async def rotate_secret_key(db: AsyncSession):
        """Rota SECRET_KEY cada 90 días"""
        # Generar nueva clave
        new_key = secrets.token_urlsafe(64)
        
        # Almacenar en BD con versión
        key_version = SecretKeyVersion(
            key_hash=get_password_hash(new_key),
            version=await KeyRotationService.get_next_version(db),
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=90)
        )
        
        db.add(key_version)
        await db.commit()
        
        # Actualizar variable de entorno
        # (requiere restart del servicio)
        logger.warning(f"SECRET_KEY rotated to version {key_version.version}")
        
        return new_key
    
    @staticmethod
    async def get_active_keys(db: AsyncSession) -> List[SecretKeyVersion]:
        """Obtiene claves activas (no expiradas)"""
        stmt = select(SecretKeyVersion).where(
            SecretKeyVersion.expires_at > datetime.now(timezone.utc)
        ).order_by(SecretKeyVersion.version.desc())
        
        result = await db.execute(stmt)
        return result.scalars().all()
```

**Impacto en Seguridad:**
- ✅ Limita ventana de compromiso
- ✅ Fuerza renovación periódica
- 🔒 CVSS Reducido: 4.5 → 3.0

---

## 📝 3.6 Cifrado de Logs

### Problema
Los logs pueden contener información sensible y se almacenan en texto plano.

**CVSS Score:** 4.2 (Medium)  
**CWE:** CWE-532: Insertion of Sensitive Information into Log File  
**OWASP:** A09:2021 - Security Logging and Monitoring Failures

### Solución Propuesta

**Enfoque:** Logs cifrados en disco, descifrados solo para análisis.

#### Implementación

```python
# server/core/logging_config.py
class EncryptedFileHandler(logging.FileHandler):
    """Handler que cifra logs antes de escribir"""
    
    def emit(self, record):
        try:
            msg = self.format(record)
            encrypted = EncryptionService.encrypt(msg)
            self.stream.write(encrypted + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)
```

**Impacto en Seguridad:**
- ✅ Protege logs sensibles
- ✅ Cumple con compliance
- 🔒 CVSS Reducido: 4.2 → 2.8

---

## 📊 Resumen de Impacto Fase 3

| Implementación | CVSS Antes | CVSS Después | Reducción |
|---|---|---|---|
| Límite de sesiones (3.1) | 5.0 | 3.2 | -36% |
| MFA/2FA (3.2) | 5.5 | 2.8 | -49% |
| Eliminar tokens URL (3.3) | 4.0 | 2.5 | -38% |
| Cifrado de datos (3.4) | 5.8 | 3.5 | -40% |
| Rotación de secrets (3.5) | 4.5 | 3.0 | -33% |
| Cifrado de logs (3.6) | 4.2 | 2.8 | -33% |

**Promedio de Reducción:** -38%  
**CVSS Final Esperado:** < 3.0 (Low)

---

## 🚀 Plan de Implementación

### Orden Recomendado

1. **3.3 Tokens en URL** (2-3h) - Rápido, bajo riesgo
2. **3.1 Límite de sesiones** (4-6h) - Media complejidad
3. **3.4 Cifrado de datos** (6-8h) - Alta prioridad compliance
4. **3.5 Rotación de secrets** (4-6h) - Complementa 3.4
5. **3.6 Cifrado de logs** (4-6h) - Complementa 3.4
6. **3.2 MFA/2FA** (8-12h) - Alta complejidad, alto impacto

**Total:** 28-41 horas (~4-5 días)

---

**Documento creado:** 9 de marzo de 2026  
**Estado:** Planificación  
**Próxima acción:** Implementar 3.3 (Tokens en URL)
