from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
from secrets import token_urlsafe
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "LAMS API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # ENVIRONMENT - development, staging, production
    ENVIRONMENT: str = "development"
    
    # DATABASE
    # Using asyncpg for async db operations
    # These MUST be provided via environment variables in production
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "lams"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # AUTHENTICATION
    # SECRET_KEY must be provided via environment variable in production
    # In development, a temporary key will be generated if not provided
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    
    # Phase 2.7: Reduced access token expiration to 1 hour (from 8 days)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    
    # Phase 2.7: Refresh token expiration
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days
    
    # Phase 3.1: Session management
    MAX_SESSIONS_PER_USER: int = Field(default=5, description="Maximum concurrent sessions per user")
    SESSION_IDLE_TIMEOUT_MINUTES: int = Field(default=30, description="Idle timeout for sessions")
    SESSION_ABSOLUTE_TIMEOUT_DAYS: int = Field(default=7, description="Absolute session timeout")
    
    # Encryption settings (Phase 3.4)
    ENCRYPTION_KEY: str = Field(default="", description="Fernet encryption key for field-level encryption")
    
    # Key Rotation settings (Phase 3.5)
    MASTER_ENCRYPTION_KEY: str = Field(default="", description="Master key for encrypting encryption keys")
    KEY_ROTATION_DAYS: int = Field(default=90, description="Days between key rotations")
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Validate SECRET_KEY - must be set in production, auto-generated in development"""
        environment = info.data.get('ENVIRONMENT', 'development')
        
        if not v or v == "":
            if environment == "production":
                raise ValueError(
                    "SECRET_KEY must be set in production environment. "
                    "Generate one with: python -c 'from secrets import token_urlsafe; print(token_urlsafe(32))'"
                )
            else:
                # Auto-generate for development
                generated_key = token_urlsafe(32)
                print(f"⚠️  WARNING: Using auto-generated SECRET_KEY for development: {generated_key}")
                print("⚠️  DO NOT use this in production! Set SECRET_KEY in .env file")
                return generated_key
        return v
    
    @field_validator('ENCRYPTION_KEY')
    @classmethod
    def validate_encryption_key(cls, v: str, info) -> str:
        """Validate ENCRYPTION_KEY - must be set for field-level encryption"""
        if not v or v == "":
            # Generate a Fernet key for development
            from cryptography.fernet import Fernet
            generated_key = Fernet.generate_key().decode()
            print(f"⚠️  WARNING: Using auto-generated ENCRYPTION_KEY for development")
            print(f"⚠️  Key: {generated_key}")
            print("⚠️  DO NOT use this in production! Set ENCRYPTION_KEY in .env file")
            print("⚠️  Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
            return generated_key
        
        # Validate key format (Fernet keys are 44 chars base64)
        if len(v) != 44:
            raise ValueError(
                "ENCRYPTION_KEY must be a valid Fernet key (44 characters base64). "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        # Try to create a Fernet instance to validate key
        try:
            from cryptography.fernet import Fernet
            Fernet(v.encode())
        except Exception as e:
            raise ValueError(f"Invalid ENCRYPTION_KEY format: {e}")
        
        return v
    
    # CORS CONFIGURATION
    # Comma-separated list of allowed origins
    # In development: defaults to localhost:3000
    # In production: MUST be explicitly set
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    @field_validator('ALLOWED_ORIGINS')
    @classmethod
    def validate_allowed_origins(cls, v: str, info) -> list[str]:
        """Parse comma-separated origins into a list"""
        environment = info.data.get('ENVIRONMENT', 'development')
        
        # Parse comma-separated values
        origins = [origin.strip() for origin in v.split(',') if origin.strip()]
        
        # Validate that wildcard is not used in production
        if environment == "production" and "*" in origins:
            raise ValueError(
                "CORS wildcard (*) is not allowed in production. "
                "Please specify exact origins in ALLOWED_ORIGINS"
            )
        
        if not origins:
            if environment == "production":
                raise ValueError("ALLOWED_ORIGINS must be set in production")
            # Default for development
            return ["http://localhost:3000"]
        
        return origins
    
    # NOTIFICATIONS - Email (SMTP)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True
    
    # NOTIFICATIONS - Slack
    SLACK_WEBHOOK_URL: str = ""
    SLACK_USERNAME: str = "LAMS Monitor"
    SLACK_ICON_EMOJI: str = ":bell:"
    
    # NOTIFICATIONS - Discord
    DISCORD_WEBHOOK_URL: str = ""
    DISCORD_USERNAME: str = "LAMS Monitor"
    
    # DATA RETENTION
    METRICS_RETENTION_DAYS: int = 30  # Delete metrics older than X days
    METRICS_AGGREGATION_DAYS: int = 7  # Aggregate metrics older than X days
    CLEANUP_SCHEDULE_HOUR: int = 2  # Hour to run cleanup (2 AM)
    CLEANUP_SCHEDULE_MINUTE: int = 0
    
    # LOGGING (Phase 2.6)
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
