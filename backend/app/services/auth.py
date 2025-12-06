from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import UnauthorizedError, ConflictError, BadRequestError
from app.models.user import User
from app.schemas.auth import Register, Login, Token
from app.schemas.user import UserResponse
from app.utils.security import verify_password, get_password_hash, create_access_token


async def register_user(db: AsyncSession, user_data: Register) -> UserResponse:
    """Register a new user."""
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise ConflictError("Username already registered")

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise ConflictError("Email already registered")

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserResponse.model_validate(new_user)


async def login_user(db: AsyncSession, login_data: Login) -> Token:
    """Authenticate user and return JWT token."""
    # Find user by username or email
    if login_data.username:
        result = await db.execute(select(User).where(User.username == login_data.username))
    elif login_data.email:
        result = await db.execute(select(User).where(User.email == login_data.email))
    else:
        raise BadRequestError("Username or email is required")

    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedError("Invalid username/email or password")

    if not verify_password(login_data.password, user.password_hash):
        raise UnauthorizedError("Invalid username/email or password")

    if not user.is_active:
        raise UnauthorizedError("User account is inactive")

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user).model_dump()
    )


async def refresh_token(db: AsyncSession, user: User) -> Token:
    """Refresh JWT token for a user."""
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user).model_dump()
    )
