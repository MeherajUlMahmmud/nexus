import json
import logging
import os
import re
import uuid
from typing import List

import aiofiles
from fastapi import APIRouter, Depends, status, Form, File as FastAPIFile, UploadFile, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.tool_orchestrator import ToolOrchestrator
from app.config import settings
from app.database import get_db
from app.exceptions import NotFoundError, ForbiddenError
from app.models.message import File, Message
from app.models.session import ChatSession
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse
from app.schemas.response import APIResponse
from app.services.groq import get_chat_completion
from app.services.message import get_session_messages, create_message
from app.tools.location import get_client_ip
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
    import time
    start_time = time.time()
    content_preview = content[:50] + "..." if len(
        content) > 50 else content

    logger.info(
        f"[CHAT_REQUEST_START] session_id: {session_id}, user_id: {current_user.id}, "
        f"content_length: {len(content)}, files_count: {len(files)}, content_preview: {content_preview}")

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
        logger.debug(f"[CHAT_CONTEXT] Loading conversation history - session_id: {session_id}")
        existing_messages = await get_session_messages(db, session_id, current_user)
        logger.info(
            f"[CHAT_CONTEXT] Loaded {len(existing_messages)} messages - session_id: {session_id}, model: {session.model_name}")

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

        # Get client IP for tools that need location
        client_ip = get_client_ip(request) if request else None

        tools_enabled_for_request = settings.tools_enabled

        # Use agent-based tool orchestration (works with any model)
        final_response_content = None
        tools_used_count = 0
        tool_results = None

        if tools_enabled_for_request:
            logger.info(
                f"[TOOL_ORCHESTRATION] Starting tool orchestration - session_id: {session_id}, model: {session.model_name}")
            # Initialize Tool Orchestrator Agent
            tool_orchestrator = ToolOrchestrator(model=session.model_name)

            # Prepare conversation history for tool_orchestrator
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in existing_messages
            ]

            # Step 1: Tool Orchestrator Agent decides which tools to use
            logger.info(
                f"[TOOL_DECISION] Agent analyzing query for tools - session_id: {session_id}, query_length: {len(content)}")
            tool_decision_start = time.time()
            tool_decisions = await tool_orchestrator.decide_tools(
                user_query=content,
                conversation_history=conversation_history,
            )
            tool_decision_time = time.time() - tool_decision_start
            logger.info(
                f"[TOOL_DECISION] Completed in {tool_decision_time:.2f}s - session_id: {session_id}, decisions: {len(tool_decisions)}")

            if tool_decisions:
                tools_used_count = len(tool_decisions)
                tool_names = [td.tool_name for td in tool_decisions]
                logger.info(
                    f"[TOOL_DECISION] Agent selected {tools_used_count} tool(s): {tool_names} - session_id: {session_id}")

                # Step 2: Execute tools programmatically
                request_context = {
                    "session_id": session_id
                }
                if client_ip:
                    request_context["ip_address"] = client_ip
                    logger.debug(
                        f"[TOOL_EXECUTION] Request context prepared with IP: {client_ip} - session_id: {session_id}")
                else:
                    logger.debug(
                        f"[TOOL_EXECUTION] Request context prepared with session_id: {session_id}")

                logger.info(
                    f"[TOOL_EXECUTION] Starting execution of {tools_used_count} tool(s) - session_id: {session_id}")
                tool_execution_start = time.time()
                tool_results = await tool_orchestrator.execute_tools(
                    tool_decisions=tool_decisions,
                    request_context=request_context
                )
                tool_execution_time = time.time() - tool_execution_start
                successful_tools = sum(1 for r in tool_results if r.get("success", False))
                logger.info(f"[TOOL_EXECUTION] Completed in {tool_execution_time:.2f}s - session_id: {session_id}, "
                            f"successful: {successful_tools}/{tools_used_count}")

                # Step 3: Format final response using tool results
                logger.info(
                    f"[RESPONSE_FORMATTING] Formatting response with {len(tool_results)} tool result(s) - session_id: {session_id}")
                formatting_start = time.time()
                final_response_content = await tool_orchestrator.format_response(
                    user_query=content,
                    tool_results=tool_results,
                    conversation_history=conversation_history
                )
                formatting_time = time.time() - formatting_start
                logger.info(f"[RESPONSE_FORMATTING] Completed in {formatting_time:.2f}s - session_id: {session_id}, "
                            f"response_length: {len(final_response_content)}")
            else:
                logger.info(f"[TOOL_DECISION] Agent decided no tools needed - session_id: {session_id}")

        # If no tools were used or tools disabled, get direct LLM response
        if final_response_content is None:
            logger.info(
                f"[LLM_DIRECT] Getting direct LLM response - session_id: {session_id}, model: {session.model_name}")
            llm_start = time.time()
            groq_response = await get_chat_completion(
                messages=groq_messages,
                model=session.model_name
            )
            llm_time = time.time() - llm_start
            final_response_content = groq_response.get("content", "")
            logger.info(f"[LLM_DIRECT] Completed in {llm_time:.2f}s - session_id: {session_id}, "
                        f"response_length: {len(final_response_content)}")
            # Extract metadata from groq response if available
            groq_metadata = groq_response.get("metadata", {})
        else:
            groq_metadata = {}

        # Create final response dict
        final_response = {
            "content": final_response_content,
            "metadata": {
                "model": session.model_name,
                "tools_used": tools_used_count,
                **groq_metadata  # Include any metadata from groq response
            }
        }

        # Parse tool results to extract created files
        created_files = []
        if tool_results:  # tool_results will be None if tools weren't used or disabled
            for tool_result in tool_results:
                if tool_result.get("success") and tool_result.get("tool_name") == "create_file":
                    result_text = tool_result.get("result", "")
                    # Extract file metadata from the result
                    metadata_match = re.search(r'<!--FILE_METADATA:({.*?})-->', result_text, re.DOTALL)
                    if metadata_match:
                        try:
                            file_metadata = json.loads(metadata_match.group(1))
                            if file_metadata.get("file_created"):
                                created_files.append(file_metadata)
                                logger.info(
                                    f"[FILE_ATTACHMENT] Found created file: {file_metadata.get('filename')} - session_id: {session_id}")
                        except json.JSONDecodeError as e:
                            logger.warning(
                                f"[FILE_ATTACHMENT] Failed to parse file metadata: {e} - session_id: {session_id}")

        # Create File records for generated files
        file_list = []
        if created_files:
            for file_meta in created_files:
                file_path = file_meta.get("file_path")
                if file_path and os.path.exists(file_path):
                    try:
                        # Read file content
                        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                            file_content = await f.read()
                        
                        file_size = file_meta.get("file_size", len(file_content.encode('utf-8')))
                        filename = file_meta.get("filename", os.path.basename(file_path))
                        # Map file extension to MIME type
                        file_ext = file_meta.get("file_type", "txt")
                        mime_type_map = {
                            "txt": "text/plain",
                            "md": "text/markdown"
                        }
                        file_type = mime_type_map.get(file_ext, "text/plain")
                        
                        # Create relative URL path
                        # Convert absolute path to relative path from uploads/
                        if "uploads/generated" in file_path:
                            # Extract the relative path from uploads/
                            rel_path = file_path.split("uploads/", 1)[1] if "uploads/" in file_path else filename
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
                            f"[FILE_ATTACHMENT] Created file record: {filename} - session_id: {session_id}, "
                            f"size: {file_size} bytes")
                    except Exception as e:
                        logger.error(
                            f"[FILE_ATTACHMENT] Failed to read/create file record for {file_path}: {e} - session_id: {session_id}")

        # Create assistant message with metadata and files
        logger.debug(f"[DB_SAVE] Saving assistant message - session_id: {session_id}, files_count: {len(file_list)}")
        assistant_message = Message(
            session_id=session_id,
            role="assistant",
            content=final_response.get("content", ""),
            extra_metadata=final_response.get("metadata"),
            files=file_list,  # Attach created files
        )
        db.add(assistant_message)
        await db.commit()
        
        # Refresh message and load files relationship to get file IDs
        result = await db.execute(
            select(Message)
            .options(selectinload(Message.files))
            .where(Message.id == assistant_message.id)
        )
        assistant_message = result.scalar_one()
        
        logger.info(
            f"[DB_SAVE] Assistant message saved - message_id: {assistant_message.id}, session_id: {session_id}, "
            f"content_length: {len(assistant_message.content)}, files_count: {len(file_list)}")

        # Construct FileResponse objects from the loaded files
        from app.schemas.message import FileResponse
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
        
        # Manually construct response to avoid lazy loading files relationship
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

        total_time = time.time() - start_time
        logger.info(
            f"[CHAT_REQUEST_END] Completed successfully - session_id: {session_id}, user_id: {current_user.id}, "
            f"total_time: {total_time:.2f}s, tools_used: {tools_used_count}, response_length: {len(final_response_content)}")

        return success_response(
            message="Chat response generated successfully",
            data=response_data.model_dump()
        )
    except (NotFoundError, ForbiddenError) as e:
        total_time = time.time() - start_time
        logger.warning(
            f"[CHAT_REQUEST_END] Failed with expected error - session_id: {session_id}, user_id: {current_user.id}, "
            f"total_time: {total_time:.2f}s, error: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(
            f"[CHAT_REQUEST_END] Failed with unexpected error - session_id: {session_id}, user_id: {current_user.id}, "
            f"total_time: {total_time:.2f}s, error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise
