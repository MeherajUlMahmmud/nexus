import logging
import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, status, Form, File as FastAPIFile, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import NotFoundError, ForbiddenError
from app.models.message import File, Message
from app.models.session import ChatSession
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse
from app.schemas.response import APIResponse
from app.services.groq import get_chat_completion
from app.services.message import get_session_messages, create_message
from app.utils.dependencies import get_current_user
from app.utils.response import fail_response, success_response

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/sessions/{session_id}/messages", tags=["Messages"])

# Define the upload directory
UPLOAD_DIR = "uploads"

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Create the upload directory if it doesn't exist
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


@router.get("/list", response_model=APIResponse)
async def get_messages(
        session_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Get all messages in a chat session."""
    logger.info(
        f"Get messages requested - session_id: {session_id}, user_id: {current_user.id}")
    try:
        messages = await get_session_messages(db, session_id, current_user)
        logger.info(
            f"Messages retrieved successfully - session_id: {session_id}, user_id: {current_user.id}, count: {len(messages)}")
        return success_response(
            message="Messages retrieved successfully",
            data=[msg.model_dump() for msg in messages]
        )
    except Exception as e:
        logger.error(
            f"Failed to retrieve messages - session_id: {session_id}, user_id: {current_user.id} - Error: {str(e)}")
        raise


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_new_message(
        session_id: int,
        message_data: MessageCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Add a new message to a chat session."""
    content_preview = message_data.content[:50] + "..." if len(
        message_data.content) > 50 else message_data.content
    logger.info(
        f"Create message requested - session_id: {session_id}, user_id: {current_user.id}, role: {message_data.role}, content_preview: {content_preview}")
    try:
        message = await create_message(db, session_id, current_user, message_data)
        logger.info(
            f"Message created successfully - message_id: {message.id}, session_id: {session_id}, user_id: {current_user.id}, role: {message.role}")
        return success_response(
            message="Message created successfully",
            data=message.model_dump()
        )
    except Exception as e:
        logger.error(
            f"Failed to create message - session_id: {session_id}, user_id: {current_user.id} - Error: {str(e)}")
        raise


@router.post("/chat", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def chat(
        session_id: int,
        content: str = Form(...),
        files: List[UploadFile] = FastAPIFile(default=[]),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Send a message and get AI response."""
    content_preview = content[:50] + "..." if len(
        content) > 50 else content
    logger.info(
        f"Chat request - session_id: {session_id}, user_id: {current_user.id}, content_preview: {content_preview}")

    try:
        # Verify session exists and belongs to user
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            logger.warning(
                f"Chat request failed - session not found: session_id: {session_id}, user_id: {current_user.id}")
            raise NotFoundError("Session not found")

        if session.user_id != current_user.id:
            logger.warning(
                f"Chat request failed - access denied: session_id: {session_id}, user_id: {current_user.id}, session_owner: {session.user_id}")
            raise ForbiddenError("You don't have access to this session")

        # Get existing messages for context
        existing_messages = await get_session_messages(db, session_id, current_user)
        logger.info(
            f"Chat context - session_id: {session_id}, existing_messages: {len(existing_messages)}, model: {session.model_name}")

        # If a file was uploaded, save it to the database or file system
        file_list = []
        file_contents = []
        saved_file_paths = []  # Track saved files for cleanup on error

        if files:
            if len(files) > 2:
                logger.warning(f"Maximum 2 files are allowed - session_id: {session_id}, user_id: {current_user.id}")
                return fail_response(message="Maximum 2 files are allowed")

            for file in files:
                file_name = file.filename
                file_type = file.content_type or "application/octet-stream"

                # Validate file type BEFORE processing
                if file_type != "text/plain":
                    logger.warning(
                        f"Unsupported file type: {file_type} - session_id: {session_id}, "
                        f"user_id: {current_user.id}, filename: {file_name}"
                    )
                    # Cleanup any files already saved
                    for saved_path in saved_file_paths:
                        try:
                            if os.path.exists(saved_path):
                                os.remove(saved_path)
                        except Exception as cleanup_error:
                            logger.error(f"Failed to cleanup file {saved_path}: {cleanup_error}")
                    return fail_response(message="Only text files (.txt) are supported")

                try:
                    # Read file content once
                    file_bytes = await file.read()

                    # Validate file size
                    file_size = len(file_bytes)
                    if file_size > MAX_FILE_SIZE:
                        logger.warning(
                            f"File too large: {file_name} ({file_size} bytes) - session_id: {session_id}, "
                            f"user_id: {current_user.id}"
                        )
                        # Cleanup any files already saved
                        for saved_path in saved_file_paths:
                            try:
                                if os.path.exists(saved_path):
                                    os.remove(saved_path)
                            except Exception as cleanup_error:
                                logger.error(f"Failed to cleanup file {saved_path}: {cleanup_error}")
                        return fail_response(
                            message=f"File {file_name} exceeds maximum size of {MAX_FILE_SIZE / (1024 * 1024):.0f}MB"
                        )

                    # Generate unique filename to avoid race conditions
                    unique_filename = f"{uuid.uuid4()}_{file_name}"
                    file_path = os.path.join(UPLOAD_DIR, unique_filename)

                    # Save to disk
                    try:
                        with open(file_path, "wb") as f:
                            f.write(file_bytes)
                        saved_file_paths.append(file_path)
                        logger.info(
                            f"File saved to disk: {unique_filename} - session_id: {session_id}, "
                            f"user_id: {current_user.id}, size: {file_size} bytes"
                        )
                    except Exception as write_error:
                        logger.error(
                            f"Failed to save file to disk: {file_name} - session_id: {session_id}, "
                            f"user_id: {current_user.id}, error: {write_error}"
                        )
                        # Cleanup any files already saved
                        for saved_path in saved_file_paths:
                            try:
                                if os.path.exists(saved_path):
                                    os.remove(saved_path)
                            except Exception as cleanup_error:
                                logger.error(f"Failed to cleanup file {saved_path}: {cleanup_error}")
                        return fail_response(message=f"Failed to save file {file_name}")

                    # Decode content for database storage
                    try:
                        file_content = file_bytes.decode("utf-8")
                    except UnicodeDecodeError as decode_error:
                        logger.error(
                            f"Failed to decode file as UTF-8: {file_name} - session_id: {session_id}, "
                            f"user_id: {current_user.id}, error: {decode_error}"
                        )
                        # Cleanup saved file
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                saved_file_paths.remove(file_path)
                        except Exception as cleanup_error:
                            logger.error(f"Failed to cleanup file {file_path}: {cleanup_error}")
                        return fail_response(message=f"File {file_name} is not valid UTF-8 text")

                    # Create file record (message_id will be set after message creation)
                    file_item = File(
                        filename=file_name,
                        file_type=file_type,
                        file_size=file_size,
                        file_content=file_content,
                        file_url=f'/uploads/{unique_filename}'
                    )
                    file_contents.append(file_content)
                    file_list.append(file_item)

                    logger.info(
                        f"File processed successfully: {file_name} - session_id: {session_id}, "
                        f"user_id: {current_user.id}, size: {file_size} bytes"
                    )

                except Exception as e:
                    logger.error(
                        f"File processing error: {file_name} - session_id: {session_id}, "
                        f"user_id: {current_user.id}, error: {str(e)}"
                    )
                    # Cleanup any files already saved
                    for saved_path in saved_file_paths:
                        try:
                            if os.path.exists(saved_path):
                                os.remove(saved_path)
                        except Exception as cleanup_error:
                            logger.error(f"Failed to cleanup file {saved_path}: {cleanup_error}")
                    return fail_response(message=f"Failed to process file {file_name}")

        # Create user message with files (SQLAlchemy will handle message_id assignment via relationship)
        user_message = Message(
            session_id=session_id,
            role="user",
            content=content,
            files=file_list,  # Files will be associated when message is committed
        )

        try:
            db.add(user_message)
            # Commit message and files together (SQLAlchemy will set message_id automatically via relationship)
            await db.commit()
            await db.refresh(user_message)

            logger.info(
                f"User message created - message_id: {user_message.id}, session_id: {session_id}, "
                f"files_count: {len(file_list)}"
            )

            if file_list:
                logger.info(
                    f"Files associated with message - message_id: {user_message.id}, "
                    f"files_count: {len(file_list)} - session_id: {session_id}"
                )
        except Exception as db_error:
            logger.error(
                f"Failed to create message with files - session_id: {session_id}, "
                f"user_id: {current_user.id}, error: {db_error}"
            )
            # Cleanup saved files on disk
            for saved_path in saved_file_paths:
                try:
                    if os.path.exists(saved_path):
                        os.remove(saved_path)
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup file {saved_path}: {cleanup_error}")
            await db.rollback()
            return fail_response(message="Failed to save message and files")

        # Prepare messages for Groq API
        groq_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in existing_messages
        ]

        # Add the new user message
        new_message = {
            "role": user_message.role,
            "content": user_message.content
        }

        # Loop through files and add their contents to the message
        for file_content in file_contents:
            new_message["content"] += "\n\n\nFile Content:\n" + file_content

        # Add the new user message
        groq_messages.append(new_message)

        # Get AI response from Groq
        logger.info(
            f"Requesting AI response from Groq - session_id: {session_id}, model: {session.model_name}, total_messages: {len(groq_messages)}")
        groq_response = await get_chat_completion(
            messages=groq_messages,
            model=session.model_name
        )
        logger.info(
            f"AI response received from Groq - session_id: {session_id}, response_length: {len(groq_response.get('content', ''))}")

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
        logger.info(
            f"Assistant message created - message_id: {assistant_message.id}, session_id: {session_id}")

        # Manually construct response to avoid lazy loading files relationship
        response_data = MessageResponse(
            id=assistant_message.id,
            session_id=assistant_message.session_id,
            role=assistant_message.role,
            content=assistant_message.content,
            extra_metadata=assistant_message.extra_metadata,
            files=[],  # Assistant messages don't have files
            created_at=assistant_message.created_at,
            updated_at=assistant_message.updated_at,
        )

        return success_response(
            message="Chat response generated successfully",
            data=response_data.model_dump()
        )
    except (NotFoundError, ForbiddenError):
        raise
    except Exception as e:
        logger.error(
            f"Chat request failed - session_id: {session_id}, user_id: {current_user.id} - Error: {str(e)}")
        raise
