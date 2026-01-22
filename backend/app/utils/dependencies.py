import uuid
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.utils.security import verify_token
from app.schemas.auth import TokenData

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency to get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    user_id_value = payload.get("user_id")
    
    if username is None or user_id_value is None:
        raise credentials_exception
    
    # Convert user_id to UUID (handle both string and UUID formats)
    try:
        if isinstance(user_id_value, str):
            user_id = uuid.UUID(user_id_value)
        elif isinstance(user_id_value, uuid.UUID):
            user_id = user_id_value
        else:
            # Legacy support: if it's an int, we can't convert it
            # This would only happen with old tokens
            raise ValueError("Invalid user_id format")
    except (ValueError, AttributeError):
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user

