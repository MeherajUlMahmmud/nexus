from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from app.database import get_db
from app.models.user import User
from app.schemas.auth import Register, Login, Token
from app.schemas.user import UserResponse
from app.schemas.response import APIResponse
from app.services.auth import register_user, login_user, refresh_token
from app.utils.dependencies import get_current_user
from app.utils.response import success_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: Register,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    logger.info(f"Registration attempt for username: {user_data.username}, email: {user_data.email}")
    try:
        user = await register_user(db, user_data)
        logger.info(f"User registered successfully - user_id: {user.id}, username: {user.username}, email: {user.email}")
        return success_response(
            message="User registered successfully",
        )
    except Exception as e:
        logger.error(f"Registration failed for username: {user_data.username}, email: {user_data.email} - Error: {str(e)}")
        raise


@router.post("/login", response_model=APIResponse)
async def login(
    login_data: Login,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and get JWT token."""
    identifier = login_data.username or login_data.email
    logger.info(f"Login attempt for: {identifier}")
    try:
        token_data = await login_user(db, login_data)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Refresh JWT token."""
    logger.info(f"Token refresh requested for user_id: {current_user.id}, username: {current_user.username}")
    try:
        token_data = await refresh_token(db, current_user)
        logger.info(f"Token refreshed successfully for user_id: {current_user.id}")
        return success_response(
            message="Token refreshed successfully",
            data=token_data.model_dump()
        )
    except Exception as e:
        logger.error(f"Token refresh failed for user_id: {current_user.id} - Error: {str(e)}")
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

