"""
Redis cache keys used throughout the application.
All cache keys should be defined here for consistency and maintainability.
"""

# Models cache
MODELS_CACHE_KEY = "groq:models"

# IP blocking cache keys
def get_sensitive_url_attempts_key(ip_address: str) -> str:
    """Get Redis key for tracking sensitive URL attempts for an IP address."""
    return f"sensitive_url_attempts:{ip_address}"


def get_sensitive_url_user_agent_key(ip_address: str) -> str:
    """Get Redis key for storing user agent for sensitive URL attempts."""
    return f"sensitive_url_attempts:{ip_address}:user_agent"
