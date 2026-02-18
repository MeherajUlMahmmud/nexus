import redis.asyncio as aioredis
from typing import Optional
from app.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None
_redis_connection_failed = False  # Track if connection failed to avoid repeated attempts


async def get_redis_client() -> Optional[aioredis.Redis]:
    """Get or create Redis client."""
    global _redis_client, _redis_connection_failed
    
    if not settings.redis_enabled:
        return None
    
    # If connection previously failed, don't retry immediately
    if _redis_connection_failed:
        return None
    
    if _redis_client is None:
        try:
            # Create client with connection timeout
            _redis_client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,  # 2 second connection timeout
                socket_timeout=2,  # 2 second socket timeout
                retry_on_timeout=False,
                health_check_interval=30
            )
            # Test connection with timeout
            try:
                await asyncio.wait_for(_redis_client.ping(), timeout=2)
                logger.info("Redis connection established")
                _redis_connection_failed = False
            except asyncio.TimeoutError:
                logger.warning("Redis connection timeout - Redis may not be running")
                _redis_client = None
                _redis_connection_failed = True
                return None
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            _redis_client = None
            _redis_connection_failed = True
            return None
    
    return _redis_client


async def close_redis():
    """Close Redis connection."""
    global _redis_client, _redis_connection_failed
    if _redis_client:
        try:
            await _redis_client.close()
        except Exception as e:
            logger.error(f"Error closing Redis connection: {str(e)}")
        finally:
            _redis_client = None
            _redis_connection_failed = False
            logger.info("Redis connection closed")

