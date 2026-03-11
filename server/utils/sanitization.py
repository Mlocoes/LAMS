"""
Input Sanitization Utilities (Phase 2.4)

Provides utilities for sanitizing and validating user inputs to prevent:
- XSS attacks
- SQL injection (additional layer on top of SQLAlchemy)
- Command injection
- Path traversal
- HTML injection
"""

import bleach
import re
from typing import List, Optional


def sanitize_string(text: str, max_length: int = 255) -> str:
    """
    Sanitize a string input by removing HTML tags and limiting length.
    
    Args:
        text: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not text:
        return ""
    
    # Remove all HTML tags
    clean = bleach.clean(text, tags=[], strip=True)
    
    # Trim whitespace
    clean = clean.strip()
    
    # Limit length
    return clean[:max_length]


def sanitize_tags(tags: List[str], max_tags: int = 10, max_tag_length: int = 50) -> List[str]:
    """
    Sanitize a list of tags.
    
    Args:
        tags: List of tag strings
        max_tags: Maximum number of tags allowed
        max_tag_length: Maximum length of each tag
        
    Returns:
        List of sanitized tags
    """
    if not tags:
        return []
    
    cleaned = []
    for tag in tags[:max_tags]:  # Limit number of tags
        # Sanitize each tag
        clean = sanitize_string(tag, max_length=max_tag_length)
        
        # Only allow alphanumeric, hyphens, underscores, and spaces
        if clean and all(c.isalnum() or c in ['-', '_', ' '] for c in clean):
            cleaned.append(clean)
    
    return cleaned


def sanitize_html(html: str, allowed_tags: Optional[List[str]] = None) -> str:
    """
    Sanitize HTML content, allowing only specific safe tags.
    
    Args:
        html: HTML string to sanitize
        allowed_tags: List of allowed HTML tags. If None, uses default safe set.
        
    Returns:
        Sanitized HTML string
    """
    if not html:
        return ""
    
    # Default safe tags for rich text
    if allowed_tags is None:
        allowed_tags = ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li', 'code', 'pre']
    
    # Allowed attributes
    allowed_attrs = {
        'a': ['href', 'title'],
        '*': ['class']
    }
    
    # Sanitize
    clean = bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True
    )
    
    return clean


def sanitize_email(email: str) -> str:
    """
    Sanitize and validate email address format.
    
    Args:
        email: Email address to sanitize
        
    Returns:
        Sanitized email address
        
    Raises:
        ValueError: If email format is invalid
    """
    if not email:
        raise ValueError("Email cannot be empty")
    
    # Remove whitespace
    email = email.strip().lower()
    
    # Basic email regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        raise ValueError("Invalid email format")
    
    return email


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename to prevent path traversal and other attacks.
    
    Args:
        filename: Filename to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized filename
        
    Raises:
        ValueError: If filename is invalid
    """
    if not filename:
        raise ValueError("Filename cannot be empty")
    
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    
    # Limit length
    filename = filename[:max_length]
    
    if not filename:
        raise ValueError("Invalid filename after sanitization")
    
    return filename


def sanitize_url(url: str, allowed_schemes: Optional[List[str]] = None) -> str:
    """
    Sanitize and validate URL.
    
    Args:
        url: URL to sanitize
        allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])
        
    Returns:
        Sanitized URL
        
    Raises:
        ValueError: If URL is invalid or uses disallowed scheme
    """
    if not url:
        raise ValueError("URL cannot be empty")
    
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']
    
    # Remove whitespace
    url = url.strip()
    
    # Check scheme
    scheme = url.split('://')[0].lower() if '://' in url else ''
    
    if scheme and scheme not in allowed_schemes:
        raise ValueError(f"URL scheme must be one of: {', '.join(allowed_schemes)}")
    
    # Basic URL validation
    url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    
    if not re.match(url_pattern, url):
        raise ValueError("Invalid URL format")
    
    return url


def sanitize_hostname(hostname: str) -> str:
    """
    Sanitize a hostname.
    
    Args:
        hostname: Hostname to sanitize
        
    Returns:
        Sanitized hostname
        
    Raises:
        ValueError: If hostname is invalid
    """
    if not hostname:
        raise ValueError("Hostname cannot be empty")
    
    # Remove whitespace
    hostname = hostname.strip().lower()
    
    # Only allow alphanumeric, hyphens, dots, and underscores
    if not re.match(r'^[a-z0-9._-]+$', hostname):
        raise ValueError("Hostname contains invalid characters")
    
    # Limit length (DNS hostname limit)
    if len(hostname) > 253:
        raise ValueError("Hostname too long")
    
    return hostname


def validate_host_id(host_id: str) -> str:
    """
    Validate and sanitize host ID.
    
    Args:
        host_id: Host ID to validate
        
    Returns:
        Sanitized host ID
        
    Raises:
        ValueError: If host ID is invalid
    """
    if not host_id:
        raise ValueError("Host ID cannot be empty")
    
    # Remove whitespace
    host_id = host_id.strip()
    
    # Only allow alphanumeric, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', host_id):
        raise ValueError("Host ID contains invalid characters")
    
    # Limit length
    if len(host_id) > 100:
        raise ValueError("Host ID too long")
    
    return host_id
