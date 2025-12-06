from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.session import ChatSession
from app.models.message import Message
from app.models.user import User
from app.schemas.session import SessionCreate, SessionUpdate, SessionResponse, SessionListResponse
from app.exceptions import NotFoundError, ForbiddenError
from app.services.groq import generate_session_title
import logging

logger = logging.getLogger(__name__)


async def get_user_sessions(
    db: AsyncSession,
    user: User,
    skip: int = 0,
    limit: int = 100
) -> List[SessionListResponse]:
    """Get all chat sessions for a user."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    sessions = result.scalars().all()
    return [SessionListResponse.model_validate(session) for session in sessions]


async def create_session(
    db: AsyncSession,
    user: User,
    session_data: SessionCreate
) -> SessionResponse:
    """Create a new chat session."""
    # Generate title if not provided
    title = session_data.title
    if not title and session_data.message:
        logger.info(f"Generating title from message for user_id: {user.id}")
        title = await generate_session_title(session_data.message, session_data.model_name)
        logger.info(f"Generated title: {title}")
    elif not title:
        # Fallback title if no message provided
        title = "New Chat"
    
    new_session = ChatSession(
        user_id=user.id,
        title=title,
        model_name=session_data.model_name,
    )
    
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    
    # Manually construct SessionResponse to avoid lazy loading messages relationship
    # A new session won't have messages, so we set it to None
    return SessionResponse(
        id=new_session.id,
        user_id=new_session.user_id,
        title=new_session.title,
        model_name=new_session.model_name,
        created_at=new_session.created_at,
        updated_at=new_session.updated_at,
        messages=None
    )


async def get_session_by_id(
    db: AsyncSession,
    session_id: int,
    user: User
) -> SessionResponse:
    """Get a specific chat session with messages and their files."""
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages).selectinload(Message.files))
        .where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise NotFoundError("Session not found")
    
    if session.user_id != user.id:
        raise ForbiddenError("You don't have access to this session")
    
    return SessionResponse.model_validate(session)


async def update_session(
    db: AsyncSession,
    session_id: int,
    user: User,
    session_update: SessionUpdate
) -> SessionResponse:
    """Update a chat session."""
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise NotFoundError("Session not found")
    
    if session.user_id != user.id:
        raise ForbiddenError("You don't have access to this session")
    
    if session_update.title is not None:
        session.title = session_update.title
    if session_update.model_name is not None:
        session.model_name = session_update.model_name
    
    await db.commit()
    
    # Return without messages to avoid lazy loading issues
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        model_name=session.model_name,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=None
    )


async def delete_session(
    db: AsyncSession,
    session_id: int,
    user: User
) -> dict:
    """Delete a chat session."""
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise NotFoundError("Session not found")
    
    if session.user_id != user.id:
        raise ForbiddenError("You don't have access to this session")
    
    await db.delete(session)
    await db.commit()
    
    return {"message": "Session deleted successfully"}

