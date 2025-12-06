import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.blocked_ip import BlockedIP
from app.utils.cache_keys import (
    get_sensitive_url_attempts_key,
    get_sensitive_url_user_agent_key
)
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


async def track_sensitive_url_attempt(ip_address: str, user_agent: Optional[str] = None) -> bool:
    """
    Track a sensitive URL access attempt for an IP address.
    Returns True if IP should be blocked (reached threshold), False otherwise.
    """
    redis_client = await get_redis_client()

    if not redis_client:
        # If Redis is not available, we can't track attempts
        logger.warning("Redis not available, cannot track IP attempts")
        return False

    try:
        # Create a key for this IP
        key = get_sensitive_url_attempts_key(ip_address)

        # Increment the counter and set expiration
        attempts = await redis_client.incr(key)

        # Set expiration on first attempt (1 hour window)
        if attempts == 1:
            await redis_client.expire(key, settings.ip_block_window)

        # Store user agent if provided
        if user_agent:
            user_agent_key = get_sensitive_url_user_agent_key(ip_address)
            await redis_client.set(user_agent_key, user_agent, ex=settings.ip_block_window)

        # Check if threshold reached
        if attempts >= settings.ip_block_attempts:
            logger.warning(
                f"IP {ip_address} reached blocking threshold: {attempts} attempts "
                f"within {settings.ip_block_window} seconds"
            )
            return True

        return False

    except Exception as e:
        logger.error(f"Error tracking IP attempt in Redis: {str(e)}")
        return False


async def is_ip_blocked(db: AsyncSession, ip_address: str) -> Optional[BlockedIP]:
    """Check if an IP address is blocked."""
    result = await db.execute(
        select(BlockedIP).where(BlockedIP.ip_address == ip_address)
    )
    return result.scalar_one_or_none()


async def block_ip(
        db: AsyncSession,
        ip_address: str,
        user_agent: Optional[str] = None,
        reason: str = "Sensitive URL access attempts"
) -> BlockedIP:
    """Block an IP address and store it in the database."""
    # Check if already blocked
    existing = await is_ip_blocked(db, ip_address)
    if existing:
        # Update existing record
        existing.attempts_count += 1
        existing.last_attempt_at = datetime.utcnow()
        if user_agent:
            existing.user_agent = user_agent
        await db.commit()
        await db.refresh(existing)
        return existing

    # Create new blocked IP record
    blocked_ip = BlockedIP(
        ip_address=ip_address,
        blocked_at=datetime.utcnow(),
        attempts_count=1,
        last_attempt_at=datetime.utcnow(),
        reason=reason,
        user_agent=user_agent
    )

    db.add(blocked_ip)
    await db.commit()
    await db.refresh(blocked_ip)

    logger.warning(f"IP {ip_address} has been blocked: {reason}")
    return blocked_ip


async def unblock_ip(db: AsyncSession, ip_address: str) -> bool:
    """Unblock an IP address."""
    blocked_ip = await is_ip_blocked(db, ip_address)
    if blocked_ip:
        await db.delete(blocked_ip)
        await db.commit()

        # Also clear Redis tracking
        redis_client = await get_redis_client()
        if redis_client:
            try:
                await redis_client.delete(get_sensitive_url_attempts_key(ip_address))
                await redis_client.delete(get_sensitive_url_user_agent_key(ip_address))
            except Exception as e:
                logger.error(f"Error clearing Redis data for IP {ip_address}: {str(e)}")

        logger.info(f"IP {ip_address} has been unblocked")
        return True
    return False


async def get_blocked_ips(db: AsyncSession, skip: int = 0, limit: int = 100):
    """Get list of blocked IPs."""
    from sqlalchemy import select
    result = await db.execute(
        select(BlockedIP)
        .order_by(BlockedIP.blocked_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
