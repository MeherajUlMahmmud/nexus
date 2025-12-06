from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from app.database import get_db
from app.models.user import User
from app.models.session import ChatSession
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageResponse, ChatRequest
from app.schemas.response import APIResponse
from app.services.message import get_session_messages, create_message
from app.services.groq import get_chat_completion
from app.utils.dependencies import get_current_user
from app.utils.response import success_response
from app.exceptions import NotFoundError, ForbiddenError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions/{session_id}/messages", tags=["Messages"])


@router.get("/list", response_model=APIResponse)
async def get_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all messages in a chat session."""
    logger.info(f"Get messages requested - session_id: {session_id}, user_id: {current_user.id}")
    try:
        messages = await get_session_messages(db, session_id, current_user)
        logger.info(f"Messages retrieved successfully - session_id: {session_id}, user_id: {current_user.id}, count: {len(messages)}")
        return success_response(
            message="Messages retrieved successfully",
            data=[msg.model_dump() for msg in messages]
        )
    except Exception as e:
        logger.error(f"Failed to retrieve messages - session_id: {session_id}, user_id: {current_user.id} - Error: {str(e)}")
        raise


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_new_message(
    session_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a new message to a chat session."""
    content_preview = message_data.content[:50] + "..." if len(message_data.content) > 50 else message_data.content
    logger.info(f"Create message requested - session_id: {session_id}, user_id: {current_user.id}, role: {message_data.role}, content_preview: {content_preview}")
    try:
        message = await create_message(db, session_id, current_user, message_data)
        logger.info(f"Message created successfully - message_id: {message.id}, session_id: {session_id}, user_id: {current_user.id}, role: {message.role}")
        return success_response(
            message="Message created successfully",
            data=message.model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to create message - session_id: {session_id}, user_id: {current_user.id} - Error: {str(e)}")
        raise


@router.post("/chat", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def chat(
    session_id: int,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a message and get AI response."""
    content_preview = chat_request.content[:50] + "..." if len(chat_request.content) > 50 else chat_request.content
    logger.info(f"Chat request - session_id: {session_id}, user_id: {current_user.id}, content_preview: {content_preview}")
    
    try:
        # Verify session exists and belongs to user
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            logger.warning(f"Chat request failed - session not found: session_id: {session_id}, user_id: {current_user.id}")
            raise NotFoundError("Session not found")
        
        if session.user_id != current_user.id:
            logger.warning(f"Chat request failed - access denied: session_id: {session_id}, user_id: {current_user.id}, session_owner: {session.user_id}")
            raise ForbiddenError("You don't have access to this session")
        
        # Get existing messages for context
        existing_messages = await get_session_messages(db, session_id, current_user)
        logger.info(f"Chat context - session_id: {session_id}, existing_messages: {len(existing_messages)}, model: {session.model_name}")
        
        # Create user message
        user_message = Message(
            session_id=session_id,
            role="user",
            content=chat_request.content,
        )
        db.add(user_message)
        await db.commit()
        await db.refresh(user_message)
        logger.info(f"User message created - message_id: {user_message.id}, session_id: {session_id}")
        
        # Prepare messages for Groq API
        groq_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in existing_messages
        ]
        # Add the new user message
        groq_messages.append({
            "role": user_message.role,
            "content": user_message.content
        })
        
        # Get AI response from Groq
        logger.info(f"Requesting AI response from Groq - session_id: {session_id}, model: {session.model_name}, total_messages: {len(groq_messages)}")
        groq_response = await get_chat_completion(
            messages=groq_messages,
            model=session.model_name
        )
        logger.info(f"AI response received from Groq - session_id: {session_id}, response_length: {len(groq_response.get('content', ''))}")
        
        # Create assistant message with metadata
        assistant_message = Message(
            session_id=session_id,
            role="assistant",
            content=groq_response["content"],
            extra_metadata=groq_response.get("metadata"),
        )
        db.add(assistant_message)
        await db.commit()
        await db.refresh(assistant_message)
        logger.info(f"Assistant message created - message_id: {assistant_message.id}, session_id: {session_id}")
        
        return success_response(
            message="Chat response generated successfully",
            data=MessageResponse.model_validate(assistant_message).model_dump()
        )
    except (NotFoundError, ForbiddenError):
        raise
    except Exception as e:
        logger.error(f"Chat request failed - session_id: {session_id}, user_id: {current_user.id} - Error: {str(e)}")
        raise

