from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.schemas.user import UserUpdate, UserResponse, PasswordChange
from app.utils.security import verify_password, get_password_hash
from app.exceptions import NotFoundError, ConflictError, UnauthorizedError, BadRequestError


async def get_user_by_id(db: AsyncSession, user_id: int) -> User:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User not found")
    return user


async def update_user_profile(
    db: AsyncSession,
    user: User,
    user_update: UserUpdate
) -> UserResponse:
    """Update user profile."""
    # Check if username is being changed and if it's already taken
    if user_update.username and user_update.username != user.username:
        result = await db.execute(select(User).where(User.username == user_update.username))
        if result.scalar_one_or_none():
            raise ConflictError("Username already taken")
        user.username = user_update.username
    
    # Check if email is being changed and if it's already taken
    if user_update.email and user_update.email != user.email:
        result = await db.execute(select(User).where(User.email == user_update.email))
        if result.scalar_one_or_none():
            raise ConflictError("Email already taken")
        user.email = user_update.email
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


async def change_user_password(
    db: AsyncSession,
    user: User,
    password_change: PasswordChange
) -> dict:
    """Change user password."""
    # Verify current password
    if not verify_password(password_change.current_password, user.password_hash):
        raise UnauthorizedError("Current password is incorrect")
    
    # Update password
    user.password_hash = get_password_hash(password_change.new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}


async def delete_user_account(
    db: AsyncSession,
    user: User,
    password: str
) -> dict:
    """Delete user account."""
    # Verify password
    if not verify_password(password, user.password_hash):
        raise UnauthorizedError("Password is incorrect")
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "Account deleted successfully"}

