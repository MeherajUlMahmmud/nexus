import logging
import os
import time
from typing import List
import uuid

from app.agents.validation import ValidationAgent
from app.database import get_db
from app.exceptions import ForbiddenError, NotFoundError
from app.models.user import User
from app.schemas.response import APIResponse
from app.services.chat import ChatService
from app.services.message import MessageService
from app.tools.location import get_client_ip
from app.utils.dependencies import get_current_user
from app.utils.response import fail_response, success_response
from fastapi import (
    APIRouter,
    Depends,
    File as FastAPIFile,
    Form,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/sessions/{session_id}/messages", tags=["Messages"])

# Initialize validation agent and chat service
validation_agent = ValidationAgent()


def get_chat_service() -> ChatService:
    """Dependency that returns the chat service instance."""
    return ChatService()


def get_message_service() -> MessageService:
    """Dependency that returns the message service instance."""
    return MessageService()


# Create the upload directory if it doesn't exist
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


@router.get("/list", response_model=APIResponse)
async def get_messages(
        session_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        message_service: MessageService = Depends(get_message_service),
):
    """Get all messages in a chat session."""
    logger.info(
        f"Get messages requested - session_id: {session_id}, user_id: {current_user.id}")
    try:
        messages = await message_service.get_session_messages(db, session_id, current_user)
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


@router.post("/chat", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def chat(
        request: Request,
        session_id: uuid.UUID,
        content: str = Form(...),
        files: List[UploadFile] = FastAPIFile(default=[]),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        chat_service: ChatService = Depends(get_chat_service),
        message_service: MessageService = Depends(get_message_service),
):
    """
    Send a message and get AI response with optional tool execution.
    """
    start_time = time.time()
    content_preview = content[:50] + "..." if len(content) > 50 else content

    logger.info(
        f"[CHAT_REQUEST_START] session_id: {session_id}, user_id: {current_user.id}, "
        f"content_length: {len(content)}, files_count: {len(files)}, content_preview: {content_preview}"
    )

    try:
        # Validate session
        session = await chat_service.validate_session(db, session_id, current_user)

        # Validate user query for security threats
        validation_context = {
            "user_id": current_user.id,
            "session_id": session_id,
            "client_ip": get_client_ip(request) if request else None
        }
        query_validation = await validation_agent.validate_query(content, validation_context)

        if query_validation.status.value == "blocked":
            logger.warning(
                f"[QUERY_BLOCKED] Query validation failed - session_id: {session_id}, "
                f"user_id: {current_user.id}, severity: {query_validation.severity_score:.2f}, "
                f"issues: {query_validation.issues}"
            )
            raise ForbiddenError(
                detail=f"Query blocked: {query_validation.message}. "
                f"Issues: {', '.join(query_validation.issues[:3])}"
            )
        elif query_validation.status.value == "warning":
            logger.warning(
                f"[QUERY_WARNING] Query validation warning - session_id: {session_id}, "
                f"user_id: {current_user.id}, severity: {query_validation.severity_score:.2f}, "
                f"issues: {query_validation.issues}"
            )

        # Get existing messages for context
        logger.debug(
            f"[CHAT_CONTEXT] Loading conversation history - session_id: {session_id}")
        existing_messages = await message_service.get_session_messages(db, session_id, current_user)
        logger.info(
            f"[CHAT_CONTEXT] Loaded {len(existing_messages)} messages - "
            f"session_id: {session_id}, model: {session.model_name}"
        )

        # Process uploaded files
        file_list, file_contents, saved_file_paths, file_error = await chat_service.process_uploaded_files(
            files, session_id, current_user.id
        )

        if file_list is None:  # Error occurred during file processing
            error_message = file_error or "Failed to process files"
            return fail_response(message=error_message)

        # Create user message
        try:
            user_message = await chat_service.create_user_message(
                db, session_id, content, file_list
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
                    logger.error(
                        f"Failed to cleanup file {saved_path}: {cleanup_error}")
            return fail_response(message="Failed to save message and files")

        # Prepare messages for API
        groq_messages = chat_service.prepare_messages_for_api(
            existing_messages, user_message, file_contents
        )

        # Get client IP for tools
        client_ip = get_client_ip(request) if request else None

        # Prepare conversation history for tool orchestration
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in existing_messages
        ]

        # Execute tool orchestration or get direct LLM response
        final_response_content, tools_used_count, tool_results = await chat_service.execute_tool_orchestration(
            content, conversation_history, session_id, session.model_name, client_ip
        )

        # Get LLM response if tools weren't used
        if final_response_content is None:
            final_response_content, groq_metadata = await chat_service.get_llm_response(
                groq_messages, session.model_name, session_id
            )
        else:
            groq_metadata = {}

        # Validate AI response for safety and quality
        response_validation_context = {
            "user_id": current_user.id,
            "session_id": session_id,
            "client_ip": get_client_ip(request) if request else None
        }
        response_validation = await validation_agent.validate_response(
            final_response_content, content, response_validation_context
        )

        if response_validation.status.value == "blocked":
            logger.warning(
                f"[RESPONSE_BLOCKED] Response validation failed - session_id: {session_id}, "
                f"user_id: {current_user.id}, severity: {response_validation.severity_score:.2f}, "
                f"issues: {response_validation.issues}"
            )
            raise ForbiddenError(
                detail=f"Response blocked: {response_validation.message}. "
                f"Issues: {', '.join(response_validation.issues[:3])}"
            )
        elif response_validation.status.value == "warning":
            logger.warning(
                f"[RESPONSE_WARNING] Response validation warning - session_id: {session_id}, "
                f"user_id: {current_user.id}, severity: {response_validation.severity_score:.2f}, "
                f"issues: {response_validation.issues}"
            )

        # Create response metadata
        response_metadata = {
            "model": session.model_name,
            "tools_used": tools_used_count,
            **groq_metadata
        }

        # Parse and create file records for generated files
        created_files = chat_service.parse_created_files(tool_results)
        generated_file_list = await chat_service.create_file_records_for_generated_files(
            created_files, session_id
        )

        # Create assistant message
        response_data = await chat_service.create_assistant_message(
            db, session_id, final_response_content, response_metadata, generated_file_list
        )

        total_time = time.time() - start_time
        logger.info(
            f"[CHAT_REQUEST_END] Completed successfully - session_id: {session_id}, "
            f"user_id: {current_user.id}, total_time: {total_time:.2f}s, "
            f"tools_used: {tools_used_count}, response_length: {len(final_response_content)}"
        )

        return success_response(
            message="Chat response generated successfully",
            data=response_data.model_dump()
        )

    except (NotFoundError, ForbiddenError) as e:
        total_time = time.time() - start_time
        logger.warning(
            f"[CHAT_REQUEST_END] Failed with expected error - session_id: {session_id}, "
            f"user_id: {current_user.id}, total_time: {total_time:.2f}s, "
            f"error: {type(e).__name__}: {str(e)}"
        )
        raise
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(
            f"[CHAT_REQUEST_END] Failed with unexpected error - session_id: {session_id}, "
            f"user_id: {current_user.id}, total_time: {total_time:.2f}s, "
            f"error: {type(e).__name__}: {str(e)}", exc_info=True
        )
        raise
