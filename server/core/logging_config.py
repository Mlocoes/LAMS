"""
Logging Configuration (Phase 2.6 + 3.6)

Implements structured JSON logging with:
- Security event logging
- Audit logging
- Performance logging
- Error logging
- Encrypted logging (Phase 3.6)

Log levels:
- DEBUG: Detailed information for debugging
- INFO: General informational messages
- WARNING: Warning messages (security alerts, etc.)
- ERROR: Error messages
- CRITICAL: Critical errors requiring immediate attention

Phase 3.6 adds optional encrypted logging for sensitive security logs.
"""

import logging
import logging.config
import sys
from pythonjsonlogger import jsonlogger
from core.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional fields
    """
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record['timestamp'] = record.created
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add environment
        log_record['environment'] = settings.ENVIRONMENT


def setup_logging():
    """
    Configure logging for the application (Phase 2.6)
    
    Creates multiple loggers:
    - root: General application logging
    - security: Security events
    - audit: Audit trail
    - performance: Performance metrics
    """
    
    # Determine log level from settings
    log_level = getattr(settings, 'LOG_LEVEL', 'INFO')
    
    # Create formatters
    json_formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    console_handler.setLevel(log_level)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Security logger
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)
    security_logger.addHandler(console_handler)
    security_logger.propagate = False
    
    # Audit logger
    audit_logger = logging.getLogger('audit')
    audit_logger.setLevel(logging.INFO)
    audit_logger.addHandler(console_handler)
    audit_logger.propagate = False
    
    # Performance logger
    performance_logger = logging.getLogger('performance')
    performance_logger.setLevel(logging.INFO)
    performance_logger.addHandler(console_handler)
    performance_logger.propagate = False
    
    # Suppress noisy loggers
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    root_logger.info("Logging configured", extra={
        "log_level": log_level,
        "environment": settings.ENVIRONMENT
    })


def get_logger(name: str = "lams") -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def get_security_logger() -> logging.Logger:
    """
    Get the security logger
    
    Returns:
        Security logger instance
    """
    return logging.getLogger('security')


def get_audit_logger() -> logging.Logger:
    """
    Get the audit logger
    
    Returns:
        Audit logger instance
    """
    return logging.getLogger('audit')


def get_performance_logger() -> logging.Logger:
    """
    Get the performance logger
    
    Returns:
        Performance logger instance
    """
    return logging.getLogger('performance')


def setup_encrypted_logging(enable: bool = True, log_dir: str = "/var/log/lams"):
    """
    Setup encrypted logging for sensitive logs (Phase 3.6).
    
    When enabled, security logs will be encrypted at rest using
    the EncryptedFileHandler. Logs can be decrypted using the
    decrypt_logs.py utility.
    
    Args:
        enable: Whether to enable encrypted logging
        log_dir: Directory for encrypted log files
    """
    if not enable:
        return
    
    try:
        from services.encrypted_logging_service import setup_encrypted_logging as setup_service
        
        # Configure encrypted logging
        setup_service(
            log_dir=log_dir,
            encrypt_security_logs=True,  # Always encrypt security logs
            encrypt_all_logs=False,  # Only encrypt sensitive records
            max_bytes=10485760,  # 10MB per file
            backup_count=10  # Keep 10 backup files
        )
        
        logging.getLogger('security').info(
            "Encrypted logging configured",
            extra={'log_dir': log_dir}
        )
    except Exception as e:
        logging.getLogger('security').error(
            f"Failed to configure encrypted logging: {e}",
            extra={'error': str(e)}
        )
