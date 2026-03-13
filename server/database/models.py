from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, JSON, func
from sqlalchemy.orm import relationship
from database.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)  # True for Admin, False for regular User
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Security fields (Phase 1.2)
    must_change_password = Column(Boolean, default=False)  # Force password change on next login
    password_changed_at = Column(DateTime(timezone=True), nullable=True)  # Last password change timestamp
    
    # Relationships
    notification_configs = relationship("NotificationConfig", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")  # Phase 3.1
    mfa = relationship("UserMFA", back_populates="user", uselist=False, cascade="all, delete-orphan")  # Phase 3.2

class Host(Base):
    __tablename__ = "hosts"
    id = Column(String, primary_key=True, index=True) # Usually a unique HWID or UUID
    hostname = Column(String, index=True, nullable=False)
    ip = Column(String)
    os = Column(String)
    kernel_version = Column(String)
    cpu_cores = Column(Integer)
    total_memory = Column(Float)  # In MB or GB
    tags = Column(JSON, default=list)  # List of tags for categorization
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="online") # online, offline

    metrics = relationship("Metric", back_populates="host", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="host", cascade="all, delete-orphan")
    docker_containers = relationship("DockerContainer", back_populates="host", cascade="all, delete-orphan")
    remote_commands = relationship("RemoteCommand", back_populates="host", cascade="all, delete-orphan")

class AgentAPIKey(Base):
    """
    API Keys for agent authentication (Phase 1.5).
    Each host has a unique API key for secure agent-server communication.
    """
    __tablename__ = "agent_api_keys"
    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(String, ForeignKey("hosts.id"), unique=True, nullable=False)
    key_hash = Column(String, nullable=False)  # Hashed API key (never store plaintext)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    is_active = Column(Boolean, default=True)
    
    # Audit fields
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin who created the key
    
    host = relationship("Host")
    creator = relationship("User")

class RefreshToken(Base):
    """
    Refresh Tokens for JWT token refresh mechanism (Phase 2.7).
    Allows users to obtain new access tokens without re-authentication.
    """
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False, index=True)  # Hashed refresh token
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked = Column(Boolean, default=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    client_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User")


class UserSession(Base):
    """
    User session tracking with device information (Phase 3.1)
    
    Tracks active sessions per user with device details for:
    - Session limits (max 5 concurrent sessions)
    - Device management (view/terminate sessions)
    - Security auditing (detect unauthorized access)
    """
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_token = Column(String(64), unique=True, nullable=False, index=True)
    refresh_token_id = Column(Integer, ForeignKey("refresh_tokens.id"), nullable=True)
    
    # Device information
    device_name = Column(String(255), nullable=True)
    device_type = Column(String(50), nullable=True)  # desktop, mobile, tablet, other
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True), index=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    refresh_token = relationship("RefreshToken")


class UserMFA(Base):
    """
    Multi-Factor Authentication (MFA/TOTP) configuration per user (Phase 3.2)
    
    Implements TOTP (Time-based One-Time Password) authentication:
    - Generates QR code for authenticator apps (Google Authenticator, Authy, etc.)
    - Stores encrypted TOTP secret
    - Provides backup codes for account recovery
    - Tracks MFA usage for security auditing
    """
    __tablename__ = "user_mfa"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # MFA configuration
    mfa_enabled = Column(Boolean, default=False, nullable=False, index=True)
    mfa_secret = Column(String(32), nullable=True)  # Base32 encoded TOTP secret
    backup_codes = Column(Text, nullable=True)  # JSON array of hashed backup codes
    key_version = Column(Integer, default=1, nullable=False, index=True)  # Phase 3.5: Encryption key version
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    enabled_at = Column(DateTime(timezone=True), nullable=True)  # When MFA was enabled
    last_used_at = Column(DateTime(timezone=True), nullable=True)  # Last successful verification
    
    # Relationships
    user = relationship("User", back_populates="mfa")


class EncryptionKey(Base):
    """
    Encryption key versioning for key rotation (Phase 3.5)
    
    Supports graceful key rotation:
    - Multiple key versions can exist
    - Only one active key for new encryptions
    - Old keys kept for decrypting existing data
    - Keys stored encrypted with master key
    """
    __tablename__ = "encryption_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(Integer, nullable=False, unique=True, index=True)
    key_encrypted = Column(Text, nullable=False)  # Encrypted with master key
    algorithm = Column(String(50), default="fernet", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    rotated_at = Column(DateTime(timezone=True), nullable=True)  # When rotated/replaced
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Metadata
    created_by = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)


class Metric(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(String, ForeignKey("hosts.id"), index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
    
    # CPU
    cpu_usage = Column(Float)
    load_average = Column(String)
    
    # Memory
    memory_used = Column(Float)
    memory_free = Column(Float)
    swap_used = Column(Float)
    
    # Disk
    disk_total = Column(Float)
    disk_used = Column(Float)
    disk_usage_percent = Column(Float)
    
    # Temperatures
    temp_cpu = Column(Float, nullable=True)
    
    # Network
    net_rx = Column(Float) # Bytes received
    net_tx = Column(Float) # Bytes transmitted

    host = relationship("Host", back_populates="metrics")

class MetricAggregated(Base):
    """Aggregated metrics for long-term storage with reduced granularity"""
    __tablename__ = "metrics_aggregated"
    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(String, ForeignKey("hosts.id"), index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)  # Start of the period
    period = Column(String, nullable=False)  # "hourly" or "daily"
    
    # CPU metrics (avg, min, max)
    cpu_usage_avg = Column(Float)
    cpu_usage_min = Column(Float)
    cpu_usage_max = Column(Float)
    
    # Memory metrics
    memory_used_avg = Column(Float)
    memory_used_min = Column(Float)
    memory_used_max = Column(Float)
    
    # Disk metrics
    disk_usage_percent_avg = Column(Float)
    disk_usage_percent_min = Column(Float)
    disk_usage_percent_max = Column(Float)
    
    # Temperature metrics
    temp_cpu_avg = Column(Float, nullable=True)
    temp_cpu_min = Column(Float, nullable=True)
    temp_cpu_max = Column(Float, nullable=True)
    
    # Network metrics (total for the period)
    net_rx_total = Column(Float)
    net_tx_total = Column(Float)
    
    # Number of samples aggregated
    sample_count = Column(Integer)

class AlertRule(Base):
    __tablename__ = "alert_rules"
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String, nullable=False) # e.g. "cpu_usage"
    operator = Column(String, nullable=False) # ">", "<", "=="
    threshold = Column(Float, nullable=False)
    severity = Column(String, nullable=False) # "warning", "critical"
    duration_minutes = Column(Integer, default=1)
    
    # optional: apply only to a specific host
    host_id = Column(String, ForeignKey("hosts.id"), nullable=True)
    
class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(String, ForeignKey("hosts.id"), index=True, nullable=True) # Nullable for global rules (future)
    event_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    metric = Column(String, nullable=False) # e.g. "cpu_usage"
    value = Column(Float, nullable=False) # The threshold breached
    severity = Column(String, nullable=False) # "warning", "critical"
    message = Column(Text, nullable=False)
    resolved = Column(Boolean, default=False)

    host = relationship("Host", back_populates="alerts")

class DockerContainer(Base):
    __tablename__ = "docker_containers"
    id = Column(String, primary_key=True, index=True) # Container ID
    host_id = Column(String, ForeignKey("hosts.id"), index=True, nullable=False)
    name = Column(String, nullable=False)
    image = Column(String, nullable=False)
    state = Column(String, nullable=False) # running, exited, etc.
    cpu_percent = Column(Float)
    memory_usage = Column(Float)
    created_at = Column(DateTime(timezone=True))
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Extended fields for Portainer features
    ports = Column(JSON, nullable=True)  # Port mappings
    volumes = Column(JSON, nullable=True)  # Volume mounts
    networks = Column(JSON, nullable=True)  # Connected networks
    labels = Column(JSON, nullable=True)  # Container labels
    restart_policy = Column(String(64), nullable=True)  # Restart policy
    exit_code = Column(Integer, nullable=True)  # Exit code if stopped

    host = relationship("Host", back_populates="docker_containers")

class NotificationConfig(Base):
    __tablename__ = "notification_configs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    provider = Column(String, nullable=False)  # "email", "slack", "discord"
    config = Column(JSON, nullable=False)  # Provider-specific configuration (webhook_url, smtp settings, etc.)
    enabled = Column(Boolean, default=True)
    severity_filter = Column(String, default="all")  # "all", "warning", "critical"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="notification_configs")

class RemoteCommand(Base):
    __tablename__ = "remote_commands"
    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(String, ForeignKey("hosts.id"), index=True, nullable=False)
    command_type = Column(String, nullable=False)  # "docker_start", "docker_stop", "docker_restart", "container.logs", "container.inspect", etc.
    target_id = Column(String, nullable=False)  # container_id
    parameters = Column(JSON, nullable=True)  # Additional parameters for the command
    status = Column(String, default="pending", nullable=False)  # "pending", "executing", "completed", "failed"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    executed_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(JSON, nullable=True)  # Result data (was Text, now JSON for structured data)
    error_message = Column(Text, nullable=True)  # Error details if failed
    duration_ms = Column(Integer, nullable=True)  # Command execution time in milliseconds
    retry_count = Column(Integer, default=0, nullable=False)  # Number of retries attempted
    max_retries = Column(Integer, default=0, nullable=False)  # Maximum retries allowed
    
    host = relationship("Host", back_populates="remote_commands")
