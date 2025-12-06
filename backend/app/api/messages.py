import logging
import os
import time
from typing import List

from fastapi import APIRouter, Depends, status, Form, File as FastAPIFile, UploadFile, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import NotFoundError, ForbiddenError
from app.models.user import User
from app.schemas.response import APIResponse
from app.services.chat import (
    validate_session,
    process_uploaded_files,
    create_user_message,
    prepare_messages_for_api,
    execute_tool_orchestration,
    get_llm_response,
    parse_created_files,
    create_file_records_for_generated_files,
    create_assistant_message,
)
from app.services.message import get_session_messages
from app.tools.location import get_client_ip
from app.utils.dependencies import get_current_user
from app.utils.response import fail_response, success_response

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/sessions/{session_id}/messages", tags=["Messages"])

# Create the upload directory if it doesn't exist
UPLOAD_DIR = "uploads"
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


@router.post("/chat", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def chat(
        request: Request,
        session_id: int,
        content: str = Form(...),
        files: List[UploadFile] = FastAPIFile(default=[]),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
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
        session = await validate_session(db, session_id, current_user)

        # Get existing messages for context
        logger.debug(f"[CHAT_CONTEXT] Loading conversation history - session_id: {session_id}")
        existing_messages = await get_session_messages(db, session_id, current_user)
        logger.info(
            f"[CHAT_CONTEXT] Loaded {len(existing_messages)} messages - "
            f"session_id: {session_id}, model: {session.model_name}"
        )

        # Process uploaded files
        file_list, file_contents, saved_file_paths, file_error = await process_uploaded_files(
            files, session_id, current_user.id
        )

        if file_list is None:  # Error occurred during file processing
            error_message = file_error or "Failed to process files"
            return fail_response(message=error_message)

        # Create user message
        try:
            user_message = await create_user_message(
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
                    logger.error(f"Failed to cleanup file {saved_path}: {cleanup_error}")
            return fail_response(message="Failed to save message and files")

        # Prepare messages for API
        groq_messages = prepare_messages_for_api(
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
        final_response_content, tools_used_count, tool_results = await execute_tool_orchestration(
            content, conversation_history, session_id, session.model_name, client_ip
        )

        # Get LLM response if tools weren't used
        if final_response_content is None:
            final_response_content, groq_metadata = await get_llm_response(
                groq_messages, session.model_name, session_id
            )
        else:
            groq_metadata = {}

        # Create response metadata
        response_metadata = {
            "model": session.model_name,
            "tools_used": tools_used_count,
            **groq_metadata
        }

        # Parse and create file records for generated files
        created_files = parse_created_files(tool_results)
        generated_file_list = await create_file_records_for_generated_files(
            created_files, session_id
        )

        # Create assistant message
        response_data = await create_assistant_message(
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
