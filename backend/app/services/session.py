"""
Session service for handling chat session operations.
"""
import logging
from typing import List
import uuid

from app.exceptions import ForbiddenError, NotFoundError
from app.models.message import Message
from app.models.session import ChatSession
from app.models.user import User
from app.schemas.session import (
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)
from app.services.groq import generate_session_title
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


class SessionService:
    """
    Service for chat session operations: CRUD operations,
    session validation, and title generation.
    """

    def __init__(self, default_limit: int = 100):
        """
        Initialize SessionService.

        Args:
            default_limit: Default limit for listing sessions
        """
        self.default_limit = default_limit

    async def get_user_sessions(
        self,
        db: AsyncSession,
        user: User,
        skip: int = 0,
        limit: int = None,
    ) -> List[SessionListResponse]:
        """
        Get all chat sessions for a user.

        Args:
            db: Database session
            user: User to get sessions for
            skip: Number of sessions to skip
            limit: Maximum number of sessions to return (uses default if None)

        Returns:
            List of SessionListResponse objects
        """
        if limit is None:
            limit = self.default_limit

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
        self,
        db: AsyncSession,
        user: User,
        session_data: SessionCreate,
    ) -> SessionResponse:
        """
        Create a new chat session.

        Args:
            db: Database session
            user: User creating the session
            session_data: Session creation data

        Returns:
            SessionResponse: Created session
        """
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
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        user: User,
    ) -> SessionResponse:
        """
        Get a specific chat session with messages and their files.

        Args:
            db: Database session
            session_id: Session ID to retrieve
            user: User requesting the session

        Returns:
            SessionResponse: Session with messages and files

        Raises:
            NotFoundError: If session doesn't exist
            ForbiddenError: If user doesn't have access to session
        """
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
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        user: User,
        session_update: SessionUpdate,
    ) -> SessionResponse:
        """
        Update a chat session.

        Args:
            db: Database session
            session_id: Session ID to update
            user: User updating the session
            session_update: Update data

        Returns:
            SessionResponse: Updated session

        Raises:
            NotFoundError: If session doesn't exist
            ForbiddenError: If user doesn't have access to session
        """
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
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        user: User,
    ) -> dict:
        """
        Delete a chat session.

        Args:
            db: Database session
            session_id: Session ID to delete
            user: User deleting the session

        Returns:
            dict: Success message

        Raises:
            NotFoundError: If session doesn't exist
            ForbiddenError: If user doesn't have access to session
        """
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


# Default instance for backward compatibility
_session_service = SessionService()
