"""
Message service for handling message operations.
"""
from typing import List
import uuid

from app.exceptions import ForbiddenError, NotFoundError
from app.models.message import Message
from app.models.session import ChatSession
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class MessageService:
    """
    Service for message operations: retrieving messages,
    creating messages, and session validation.
    """

    async def _validate_session_access(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        user: User,
    ) -> ChatSession:
        """
        Validate that session exists and belongs to the user.

        Args:
            db: Database session
            session_id: Session ID to validate
            user: Current user

        Returns:
            ChatSession: The validated session

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

        return session

    async def get_session_messages(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        user: User,
    ) -> List[MessageResponse]:
        """
        Get all messages in a chat session.

        Args:
            db: Database session
            session_id: Session ID to get messages for
            user: User requesting the messages

        Returns:
            List of MessageResponse objects

        Raises:
            NotFoundError: If session doesn't exist
            ForbiddenError: If user doesn't have access to session
        """
        # Verify session exists and belongs to user
        await self._validate_session_access(db, session_id, user)

        # Get messages with files eagerly loaded
        result = await db.execute(
            select(Message)
            .options(selectinload(Message.files))
            .where(Message.session_id == session_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()

        return [MessageResponse.model_validate(msg) for msg in messages]

    async def create_message(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        user: User,
        message_data: MessageCreate,
    ) -> MessageResponse:
        """
        Create a new message in a chat session.

        Args:
            db: Database session
            session_id: Session ID to create message in
            user: User creating the message
            message_data: Message creation data

        Returns:
            MessageResponse: Created message

        Raises:
            NotFoundError: If session doesn't exist
            ForbiddenError: If user doesn't have access to session
        """
        # Verify session exists and belongs to user
        await self._validate_session_access(db, session_id, user)

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


# Default instance for backward compatibility
_message_service = MessageService()


# Module-level wrappers (delegate to default MessageService)
async def get_session_messages(db, session_id, user):
    return await _message_service.get_session_messages(db, session_id, user)


async def create_message(db, session_id, user, message_data):
    return await _message_service.create_message(db, session_id, user, message_data)


__all__ = [
    "MessageService",
    "get_session_messages",
    "create_message",
]
