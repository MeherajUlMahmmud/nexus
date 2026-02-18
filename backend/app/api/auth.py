import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import Register, Login, RefreshTokenRequest
from app.schemas.response import APIResponse
from app.schemas.user import UserResponse
from app.services.auth import AuthService
from app.utils.dependencies import get_current_user
from app.utils.response import success_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def get_auth_service() -> AuthService:
    """Dependency that returns the auth service instance."""
    return AuthService()


@router.post("/register", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def register(
        user_data: Register,
        db: AsyncSession = Depends(get_db),
        auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user."""
    logger.info(f"Registration attempt for username: {user_data.username}, email: {user_data.email}")
    try:
        user = await auth_service.register_user(db, user_data)
        logger.info(
            f"User registered successfully - user_id: {user.id}, username: {user.username}, email: {user.email}")
        return success_response(
            message="User registered successfully",
        )
    except Exception as e:
        logger.error(
            f"Registration failed for username: {user_data.username}, email: {user_data.email} - Error: {str(e)}")
        raise


@router.post("/login", response_model=APIResponse)
async def login(
        login_data: Login,
        db: AsyncSession = Depends(get_db),
        auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate user and get JWT token."""
    identifier = login_data.username or login_data.email
    logger.info(f"Login attempt for: {identifier}")
    try:
        token_data = await auth_service.login_user(db, login_data)
        user_id = token_data.user.get("id")
        logger.info(f"Login successful for: {identifier}, user_id: {user_id}")
        return success_response(
            message="Login successful",
            data=token_data.model_dump()
        )
    except Exception as e:
        logger.warning(f"Login failed for: {identifier} - Error: {str(e)}")
        raise


@router.post("/refresh", response_model=APIResponse)
async def refresh(
        refresh_data: RefreshTokenRequest,
        db: AsyncSession = Depends(get_db),
        auth_service: AuthService = Depends(get_auth_service),
):
    """Refresh access token using refresh token."""
    logger.info(f"Token refresh requested")
    try:
        token_data = await auth_service.refresh_access_token(db, refresh_data.refresh_token)
        logger.info(f"Token refreshed successfully")
        return success_response(
            message="Token refreshed successfully",
            data=token_data.model_dump()
        )
    except Exception as e:
        logger.warning(f"Token refresh failed - Error: {str(e)}")
        raise


@router.post("/logout", response_model=APIResponse)
async def logout(
        refresh_data: RefreshTokenRequest,
        db: AsyncSession = Depends(get_db),
        auth_service: AuthService = Depends(get_auth_service),
):
    """Revoke refresh token (logout)."""
    logger.info(f"Logout requested")
    try:
        await auth_service.revoke_refresh_token(db, refresh_data.refresh_token)
        logger.info(f"Refresh token revoked successfully")
        return success_response(
            message="Logged out successfully"
        )
    except Exception as e:
        logger.error(f"Logout failed - Error: {str(e)}")
        raise


@router.get("/me", response_model=APIResponse)
async def get_current_user_info(
        current_user: User = Depends(get_current_user)
):
    """Get current user profile."""
    logger.info(f"Get current user info requested for user_id: {current_user.id}, username: {current_user.username}")
    try:
        user_data = UserResponse.model_validate(current_user)
        logger.info(f"User profile retrieved successfully for user_id: {current_user.id}")
        return success_response(
            message="User profile retrieved successfully",
            data=user_data.model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to retrieve user profile for user_id: {current_user.id} - Error: {str(e)}")
        raise
