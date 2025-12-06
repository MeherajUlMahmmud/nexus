import logging

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.response import APIResponse
from app.schemas.user import UserUpdate, UserResponse, PasswordChange
from app.services.user import update_user_profile, change_user_password, delete_user_account
from app.utils.dependencies import get_current_user
from app.utils.response import success_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


class PasswordConfirmation(BaseModel):
    password: str


@router.put("/profile", response_model=APIResponse)
async def update_profile(
        user_update: UserUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Update user profile."""
    logger.info(f"Profile update requested for user_id: {current_user.id}, username: {current_user.username}")
    try:
        user = await update_user_profile(db, current_user, user_update)
        logger.info(
            f"Profile updated successfully for user_id: {user.id}, updated fields: {list(user_update.model_dump(exclude_unset=True).keys())}")
        return success_response(
            message="Profile updated successfully",
            data=UserResponse.model_validate(user).model_dump()
        )
    except Exception as e:
        logger.error(f"Profile update failed for user_id: {current_user.id} - Error: {str(e)}")
        raise


@router.put("/password", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def change_password(
        password_change: PasswordChange,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Change user password."""
    logger.info(f"Password change requested for user_id: {current_user.id}, username: {current_user.username}")
    try:
        await change_user_password(db, current_user, password_change)
        logger.info(f"Password changed successfully for user_id: {current_user.id}")
        return success_response(
            message="Password changed successfully",
            data=None
        )
    except Exception as e:
        logger.warning(f"Password change failed for user_id: {current_user.id} - Error: {str(e)}")
        raise


@router.delete("/account", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def delete_account(
        password_confirmation: PasswordConfirmation,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Delete user account."""
    logger.info(f"Account deletion requested for user_id: {current_user.id}, username: {current_user.username}")
    try:
        await delete_user_account(db, current_user, password_confirmation.password)
        logger.info(f"Account deleted successfully for user_id: {current_user.id}, username: {current_user.username}")
        return success_response(
            message="Account deleted successfully",
            data=None
        )
    except Exception as e:
        logger.warning(f"Account deletion failed for user_id: {current_user.id} - Error: {str(e)}")
        raise
