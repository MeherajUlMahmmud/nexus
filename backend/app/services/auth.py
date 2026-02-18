"""
Authentication service for handling user registration, login,
token management, and refresh token operations.
"""
from datetime import datetime, timedelta

from app.config import settings
from app.exceptions import BadRequestError, ConflictError, UnauthorizedError
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import Login, Register, Token
from app.schemas.user import UserResponse
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class AuthService:
    """
    Service for authentication operations: user registration,
    login, token refresh, and logout.
    """

    async def register_user(
        self,
        db: AsyncSession,
        user_data: Register,
    ) -> UserResponse:
        """
        Register a new user.

        Args:
            db: Database session
            user_data: User registration data

        Returns:
            UserResponse: Created user

        Raises:
            ConflictError: If username or email already exists
        """
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

    async def login_user(
        self,
        db: AsyncSession,
        login_data: Login,
    ) -> Token:
        """
        Authenticate user and return JWT token with refresh token.

        Args:
            db: Database session
            login_data: Login credentials

        Returns:
            Token: Access token, refresh token, and user info

        Raises:
            BadRequestError: If neither username nor email provided
            UnauthorizedError: If credentials are invalid or user is inactive
        """
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

        # Create access token (2 hours)
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id},
            expires_delta=access_token_expires
        )

        # Create and store refresh token (30 days)
        refresh_token_value = create_refresh_token()
        refresh_token_expires = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        
        refresh_token = RefreshToken(
            token=refresh_token_value,
            user_id=user.id,
            expires_at=refresh_token_expires,
            is_revoked=False
        )
        db.add(refresh_token)
        await db.commit()

        return Token(
            access_token=access_token,
            refresh_token=refresh_token_value,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserResponse.model_validate(user).model_dump()
        )

    async def refresh_access_token(
        self,
        db: AsyncSession,
        refresh_token_value: str,
    ) -> Token:
        """
        Refresh access token using refresh token.

        Args:
            db: Database session
            refresh_token_value: Refresh token string

        Returns:
            Token: New access token and user info

        Raises:
            UnauthorizedError: If refresh token is invalid, revoked, or expired
        """
        # Find the refresh token with user relationship loaded
        result = await db.execute(
            select(RefreshToken)
            .options(selectinload(RefreshToken.user))
            .where(
                and_(
                    RefreshToken.token == refresh_token_value,
                    RefreshToken.is_revoked == False
                )
            )
        )
        refresh_token = result.scalar_one_or_none()

        if not refresh_token:
            raise UnauthorizedError("Invalid or revoked refresh token")

        # Check if refresh token is expired
        if refresh_token.expires_at < datetime.utcnow():
            # Mark as revoked
            refresh_token.is_revoked = True
            await db.commit()
            raise UnauthorizedError("Refresh token has expired")

        # Get the user (already loaded via selectinload)
        user = refresh_token.user
        if not user or not user.is_active:
            raise UnauthorizedError("User account is inactive")

        # Create new access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id},
            expires_delta=access_token_expires
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token_value,  # Return the same refresh token
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserResponse.model_validate(user).model_dump()
        )

    async def revoke_refresh_token(
        self,
        db: AsyncSession,
        refresh_token_value: str,
    ) -> None:
        """
        Revoke a refresh token (logout).

        Args:
            db: Database session
            refresh_token_value: Refresh token string to revoke
        """
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token == refresh_token_value)
        )
        refresh_token = result.scalar_one_or_none()

        if refresh_token:
            refresh_token.is_revoked = True
            await db.commit()


# Default instance for backward compatibility
_auth_service = AuthService()
