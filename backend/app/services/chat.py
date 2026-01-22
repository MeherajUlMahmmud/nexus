"""
Chat service functions for handling chat operations.
"""
import json
import logging
import os
import re
import time
import uuid
from typing import List, Optional, Tuple, Dict, Any

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.tool_orchestrator import ToolOrchestrator
from app.config import settings
from app.exceptions import NotFoundError, ForbiddenError
from app.models.message import File, Message
from app.models.session import ChatSession
from app.models.user import User
from app.schemas.message import MessageResponse, FileResponse
from app.services.groq import get_chat_completion

logger = logging.getLogger(__name__)

# Constants
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILES = 2


async def validate_session(
        db: AsyncSession,
        session_id: uuid.UUID,
        user: User
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
        logger.warning(
            f"Session not found - session_id: {session_id}, user_id: {user.id}"
        )
        raise NotFoundError("Session not found")

    if session.user_id != user.id:
        logger.warning(
            f"Access denied - session_id: {session_id}, user_id: {user.id}, "
            f"session_owner: {session.user_id}"
        )
        raise ForbiddenError("You don't have access to this session")

    return session


async def validate_and_process_file(
        file: UploadFile,
        session_id: uuid.UUID,
        user_id: uuid.UUID
) -> Tuple[Optional[File], Optional[str], Optional[str], Optional[str]]:
    """
    Validate and process a single uploaded file.

    Args:
        file: Uploaded file
        session_id: Current session ID
        user_id: Current user ID

    Returns:
        Tuple of (File object, file content, file path, error_message)
        On error, returns (None, None, None, error_message)
    """
    file_name = file.filename
    file_type = file.content_type or "application/octet-stream"

    # Validate file type
    if file_type != "text/plain":
        logger.warning(
            f"Unsupported file type: {file_type} - session_id: {session_id}, "
            f"user_id: {user_id}, filename: {file_name}"
        )
        return None, None, None, "Only text files (.txt) are supported"

    try:
        # Read file content
        file_bytes = await file.read()

        # Validate file size
        file_size = len(file_bytes)
        if file_size > MAX_FILE_SIZE:
            logger.warning(
                f"File too large: {file_name} ({file_size} bytes) - "
                f"session_id: {session_id}, user_id: {user_id}"
            )
            return None, None, None, f"File {file_name} exceeds maximum size of {MAX_FILE_SIZE / (1024 * 1024):.0f}MB"

        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}_{file_name}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        # Save to disk
        try:
            with open(file_path, "wb") as f:
                f.write(file_bytes)
            logger.info(
                f"File saved to disk: {unique_filename} - session_id: {session_id}, "
                f"user_id: {user_id}, size: {file_size} bytes"
            )
        except Exception as write_error:
            logger.error(
                f"Failed to save file to disk: {file_name} - session_id: {session_id}, "
                f"user_id: {user_id}, error: {write_error}"
            )
            return None, None, None, f"Failed to save file {file_name}"

        # Decode content
        try:
            file_content = file_bytes.decode("utf-8")
        except UnicodeDecodeError as decode_error:
            logger.error(
                f"Failed to decode file as UTF-8: {file_name} - session_id: {session_id}, "
                f"user_id: {user_id}, error: {decode_error}"
            )
            # Cleanup saved file
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as cleanup_error:
                logger.error(
                    f"Failed to cleanup file {file_path}: {cleanup_error}")
            return None, None, None, f"File {file_name} is not valid UTF-8 text"

        # Create file record
        file_item = File(
            filename=file_name,
            file_type=file_type,
            file_size=file_size,
            file_content=file_content,
            file_url=f'/uploads/{unique_filename}'
        )

        logger.info(
            f"File processed successfully: {file_name} - session_id: {session_id}, "
            f"user_id: {user_id}, size: {file_size} bytes"
        )

        return file_item, file_content, file_path, None

    except Exception as e:
        logger.error(
            f"File processing error: {file_name} - session_id: {session_id}, "
            f"user_id: {user_id}, error: {str(e)}"
        )
        return None, None, None, f"Failed to process file {file_name}"


async def process_uploaded_files(
        files: List[UploadFile],
        session_id: uuid.UUID,
        user_id: uuid.UUID
) -> Tuple[Optional[List[File]], Optional[List[str]], Optional[List[str]], Optional[str]]:
    """
    Process all uploaded files with validation and cleanup on error.

    Args:
        files: List of uploaded files
        session_id: Current session ID
        user_id: Current user ID

    Returns:
        Tuple of (file_list, file_contents, saved_file_paths, error_message)
        If error occurs, returns (None, None, None, error_message)
    """
    if not files:
        return [], [], [], None

    if len(files) > MAX_FILES:
        logger.warning(
            f"Maximum {MAX_FILES} files allowed - session_id: {session_id}, "
            f"user_id: {user_id}, provided: {len(files)}"
        )
        return None, None, None, f"Maximum {MAX_FILES} files are allowed"

    file_list = []
    file_contents = []
    saved_file_paths = []

    for file in files:
        file_item, file_content, file_path, error_message = await validate_and_process_file(
            file, session_id, user_id
        )

        if file_item is None:
            # Cleanup any files already saved
            for saved_path in saved_file_paths:
                try:
                    if os.path.exists(saved_path):
                        os.remove(saved_path)
                except Exception as cleanup_error:
                    logger.error(
                        f"Failed to cleanup file {saved_path}: {cleanup_error}")
            return None, None, None, error_message or f"Failed to process file {file.filename}"

        file_list.append(file_item)
        file_contents.append(file_content)
        saved_file_paths.append(file_path)

    return file_list, file_contents, saved_file_paths, None


async def create_user_message(
        db: AsyncSession,
        session_id: uuid.UUID,
        content: str,
        file_list: List[File]
) -> Message:
    """
    Create and save user message with attached files.

    Args:
        db: Database session
        session_id: Session ID
        content: Message content
        file_list: List of File objects to attach

    Returns:
        Message: Created user message

    Raises:
        Returns fail_response dict on database errors
    """
    user_message = Message(
        session_id=session_id,
        role="user",
        content=content,
        files=file_list,
    )

    try:
        db.add(user_message)
        await db.commit()
        await db.refresh(user_message)

        logger.info(
            f"User message created - message_id: {user_message.id}, "
            f"session_id: {session_id}, files_count: {len(file_list)}"
        )

        return user_message

    except Exception as db_error:
        logger.error(
            f"Failed to create message with files - session_id: {session_id}, "
            f"error: {db_error}"
        )
        await db.rollback()
        raise


def prepare_messages_for_api(
        existing_messages: List[MessageResponse],
        user_message: Message,
        file_contents: List[str]
) -> List[Dict[str, str]]:
    """
    Prepare messages in format expected by Groq API.

    Args:
        existing_messages: Previous messages in conversation
        user_message: New user message
        file_contents: Contents of uploaded files

    Returns:
        List of message dicts for API
    """
    groq_messages = [
        {"role": msg.role, "content": msg.content}
        for msg in existing_messages
    ]

    # Add the new user message with file contents
    new_message = {
        "role": user_message.role,
        "content": user_message.content
    }

    # Append file contents to message
    for file_content in file_contents:
        new_message["content"] += "\n\n\nFile Content:\n" + file_content

    groq_messages.append(new_message)
    return groq_messages


async def execute_tool_orchestration(
        content: str,
        conversation_history: List[Dict[str, str]],
        session_id: uuid.UUID,
        model_name: str,
        client_ip: Optional[str]
) -> Tuple[Optional[str], int, Optional[List[Dict[str, Any]]]]:
    """
    Execute tool orchestration if tools are enabled.

    Args:
        content: User query content
        conversation_history: Previous conversation messages
        session_id: Current session ID
        model_name: Model name to use
        client_ip: Client IP address for location-based tools

    Returns:
        Tuple of (final_response_content, tools_used_count, tool_results)
    """
    if not settings.tools_enabled:
        return None, 0, None

    logger.info(
        f"[TOOL_ORCHESTRATION] Starting tool orchestration - "
        f"session_id: {session_id}, model: {model_name}"
    )

    tool_orchestrator = ToolOrchestrator(model=model_name)

    # Step 1: Decide which tools to use
    logger.info(
        f"[TOOL_DECISION] Agent analyzing query for tools - "
        f"session_id: {session_id}, query_length: {len(content)}"
    )
    tool_decision_start = time.time()
    tool_decisions = await tool_orchestrator.decide_tools(
        user_query=content,
        conversation_history=conversation_history,
    )
    tool_decision_time = time.time() - tool_decision_start
    logger.info(
        f"[TOOL_DECISION] Completed in {tool_decision_time:.2f}s - "
        f"session_id: {session_id}, decisions: {len(tool_decisions)}"
    )

    if not tool_decisions:
        logger.info(
            f"[TOOL_DECISION] Agent decided no tools needed - session_id: {session_id}"
        )
        return None, 0, None

    tools_used_count = len(tool_decisions)
    tool_names = [td.tool_name for td in tool_decisions]
    logger.info(
        f"[TOOL_DECISION] Agent selected {tools_used_count} tool(s): {tool_names} - "
        f"session_id: {session_id}"
    )

    # Step 2: Execute tools
    request_context = {"session_id": session_id}
    if client_ip:
        request_context["ip_address"] = client_ip
        logger.debug(
            f"[TOOL_EXECUTION] Request context prepared with IP: {client_ip} - "
            f"session_id: {session_id}"
        )

    logger.info(
        f"[TOOL_EXECUTION] Starting execution of {tools_used_count} tool(s) - "
        f"session_id: {session_id}"
    )
    tool_execution_start = time.time()
    tool_results = await tool_orchestrator.execute_tools(
        tool_decisions=tool_decisions,
        request_context=request_context,
        user_query=content,
        conversation_history=conversation_history
    )
    tool_execution_time = time.time() - tool_execution_start
    successful_tools = sum(1 for r in tool_results if r.get("success", False))
    logger.info(
        f"[TOOL_EXECUTION] Completed in {tool_execution_time:.2f}s - "
        f"session_id: {session_id}, successful: {successful_tools}/{tools_used_count}"
    )

    # Step 3: Format final response
    logger.info(
        f"[RESPONSE_FORMATTING] Formatting response with {len(tool_results)} tool result(s) - "
        f"session_id: {session_id}"
    )
    formatting_start = time.time()
    final_response_content = await tool_orchestrator.format_response(
        user_query=content,
        tool_results=tool_results,
        conversation_history=conversation_history
    )
    formatting_time = time.time() - formatting_start
    logger.info(
        f"[RESPONSE_FORMATTING] Completed in {formatting_time:.2f}s - "
        f"session_id: {session_id}, response_length: {len(final_response_content)}"
    )

    return final_response_content, tools_used_count, tool_results


async def get_llm_response(
        groq_messages: List[Dict[str, str]],
        model_name: str,
        session_id: uuid.UUID
) -> Tuple[str, Dict[str, Any]]:
    """
    Get direct LLM response when tools are not used.

    Args:
        groq_messages: Messages formatted for API
        model_name: Model name to use
        session_id: Current session ID

    Returns:
        Tuple of (response_content, metadata)
    """
    logger.info(
        f"[LLM_DIRECT] Getting direct LLM response - "
        f"session_id: {session_id}, model: {model_name}"
    )
    llm_start = time.time()
    groq_response = await get_chat_completion(
        messages=groq_messages,
        model=model_name
    )
    llm_time = time.time() - llm_start
    final_response_content = groq_response.get("content", "")
    logger.info(
        f"[LLM_DIRECT] Completed in {llm_time:.2f}s - "
        f"session_id: {session_id}, response_length: {len(final_response_content)}"
    )
    groq_metadata = groq_response.get("metadata", {})
    return final_response_content, groq_metadata


def parse_created_files(tool_results: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Parse tool results to extract created files metadata.

    Args:
        tool_results: Results from tool execution

    Returns:
        List of file metadata dicts
    """
    if not tool_results:
        return []

    created_files = []
    for tool_result in tool_results:
        if tool_result.get("success") and tool_result.get("tool_name") == "create_file":
            result_text = tool_result.get("result", "")
            # Extract file metadata from the result
            metadata_match = re.search(
                r'<!--FILE_METADATA:({.*?})-->', result_text, re.DOTALL
            )
            if metadata_match:
                try:
                    file_metadata = json.loads(metadata_match.group(1))
                    if file_metadata.get("file_created"):
                        created_files.append(file_metadata)
                        logger.info(
                            f"[FILE_ATTACHMENT] Found created file: "
                            f"{file_metadata.get('filename')}"
                        )
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"[FILE_ATTACHMENT] Failed to parse file metadata: {e}"
                    )

    return created_files


async def create_file_records_for_generated_files(
        created_files: List[Dict[str, Any]],
        session_id: uuid.UUID
) -> List[File]:
    """
    Create File database records for generated files.

    Args:
        created_files: List of file metadata dicts
        session_id: Current session ID

    Returns:
        List of File objects
    """
    if not created_files:
        return []

    file_list = []
    mime_type_map = {
        "txt": "text/plain",
        "md": "text/markdown"
    }

    for file_meta in created_files:
        file_path = file_meta.get("file_path")
        if not file_path or not os.path.exists(file_path):
            continue

        try:
            # Read file content
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                file_content = await f.read()

            file_size = file_meta.get(
                "file_size", len(file_content.encode('utf-8')))
            filename = file_meta.get("filename", os.path.basename(file_path))
            file_ext = file_meta.get("file_type", "txt")
            file_type = mime_type_map.get(file_ext, "text/plain")

            # Create relative URL path
            if "uploads/generated" in file_path:
                rel_path = file_path.split(
                    "uploads/", 1)[1] if "uploads/" in file_path else filename
                file_url = f'/uploads/{rel_path}'
            else:
                file_url = f'/uploads/{filename}'

            # Create file record
            file_item = File(
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                file_content=file_content,
                file_url=file_url
            )
            file_list.append(file_item)
            logger.info(
                f"[FILE_ATTACHMENT] Created file record: {filename} - "
                f"session_id: {session_id}, size: {file_size} bytes"
            )

        except Exception as e:
            logger.error(
                f"[FILE_ATTACHMENT] Failed to read/create file record for {file_path}: {e} - "
                f"session_id: {session_id}"
            )

    return file_list


async def create_assistant_message(
        db: AsyncSession,
        session_id: uuid.UUID,
        content: str,
        metadata: Dict[str, Any],
        file_list: List[File]
) -> MessageResponse:
    """
    Create and save assistant message with metadata and files.

    Args:
        db: Database session
        session_id: Session ID
        content: Message content
        metadata: Extra metadata
        file_list: List of File objects to attach

    Returns:
        MessageResponse: Created assistant message
    """
    logger.debug(
        f"[DB_SAVE] Saving assistant message - "
        f"session_id: {session_id}, files_count: {len(file_list)}"
    )

    assistant_message = Message(
        session_id=session_id,
        role="assistant",
        content=content,
        extra_metadata=metadata,
        files=file_list,
    )
    db.add(assistant_message)
    await db.commit()

    # Refresh message and load files relationship
    result = await db.execute(
        select(Message)
        .options(selectinload(Message.files))
        .where(Message.id == assistant_message.id)
    )
    assistant_message = result.scalar_one()

    logger.info(
        f"[DB_SAVE] Assistant message saved - message_id: {assistant_message.id}, "
        f"session_id: {session_id}, content_length: {len(assistant_message.content)}, "
        f"files_count: {len(file_list)}"
    )

    # Construct FileResponse objects
    file_responses = [
        FileResponse(
            id=file.id,
            filename=file.filename,
            file_type=file.file_type,
            file_size=file.file_size,
            file_url=file.file_url,
            created_at=file.created_at
        )
        for file in assistant_message.files
    ]

    # Construct response
    response_data = MessageResponse(
        id=assistant_message.id,
        session_id=assistant_message.session_id,
        role=assistant_message.role,
        content=assistant_message.content,
        extra_metadata=assistant_message.extra_metadata,
        files=file_responses,
        created_at=assistant_message.created_at,
        updated_at=assistant_message.updated_at,
    )

    return response_data
