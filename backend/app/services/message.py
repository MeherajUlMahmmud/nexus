from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.message import Message
from app.models.session import ChatSession
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse
from app.exceptions import NotFoundError, ForbiddenError


async def get_session_messages(
    db: AsyncSession,
    session_id: int,
    user: User
) -> List[MessageResponse]:
    """Get all messages in a chat session."""
    # Verify session exists and belongs to user
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise NotFoundError("Session not found")
    
    if session.user_id != user.id:
        raise ForbiddenError("You don't have access to this session")
    
    # Get messages
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    return [MessageResponse.model_validate(msg) for msg in messages]


async def create_message(
    db: AsyncSession,
    session_id: int,
    user: User,
    message_data: MessageCreate
) -> MessageResponse:
    """Create a new message in a chat session."""
    # Verify session exists and belongs to user
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise NotFoundError("Session not found")
    
    if session.user_id != user.id:
        raise ForbiddenError("You don't have access to this session")
    
    # Create message
    new_message = Message(
        session_id=session_id,
        role=message_data.role,
        content=message_data.content,
    )
    
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    
    return MessageResponse.model_validate(new_message)

