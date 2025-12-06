from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from app.database import get_db
from app.models.user import User
from app.schemas.session import SessionCreate, SessionUpdate, SessionResponse, SessionListResponse
from app.schemas.response import APIResponse
from app.services.session import (
    get_user_sessions,
    create_session,
    get_session_by_id,
    update_session,
    delete_session
)
from app.utils.dependencies import get_current_user
from app.utils.response import success_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["Chat Sessions"])


@router.get("/list", response_model=APIResponse)
async def get_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all chat sessions for the authenticated user."""
    logger.info(f"Get sessions requested for user_id: {current_user.id}, skip: {skip}, limit: {limit}")
    try:
        sessions = await get_user_sessions(db, current_user, skip, limit)
        logger.info(f"Sessions retrieved successfully for user_id: {current_user.id}, count: {len(sessions)}")
        return success_response(
            message="Sessions retrieved successfully",
            data=[session.model_dump() for session in sessions]
        )
    except Exception as e:
        logger.error(f"Failed to retrieve sessions for user_id: {current_user.id} - Error: {str(e)}")
        raise


@router.post("/create", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_new_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat session."""
    logger.info(f"Create session requested for user_id: {current_user.id}, title: {session_data.title}, model: {session_data.model_name}")
    try:
        session = await create_session(db, current_user, session_data)
        logger.info(f"Session created successfully - session_id: {session.id}, user_id: {current_user.id}, model: {session.model_name}")
        return success_response(
            message="Session created successfully",
            data=session.model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to create session for user_id: {current_user.id} - Error: {str(e)}")
        raise


@router.get("/{session_id}/details", response_model=APIResponse)
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get details of a specific chat session."""
    logger.info(f"Get session requested - session_id: {session_id}, user_id: {current_user.id}")
    try:
        session = await get_session_by_id(db, session_id, current_user)
        logger.info(f"Session retrieved successfully - session_id: {session_id}, user_id: {current_user.id}")
        return success_response(
            message="Session retrieved successfully",
            data=session.model_dump()
        )
    except Exception as e:
        logger.warning(f"Failed to retrieve session - session_id: {session_id}, user_id: {current_user.id} - Error: {str(e)}")
        raise


@router.delete("/{session_id}/delete", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def delete_session_endpoint(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat session."""
    logger.info(f"Delete session requested - session_id: {session_id}, user_id: {current_user.id}")
    try:
        await delete_session(db, session_id, current_user)
        logger.info(f"Session deleted successfully - session_id: {session_id}, user_id: {current_user.id}")
        return success_response(
            message="Session deleted successfully",
            data=None
        )
    except Exception as e:
        logger.warning(f"Failed to delete session - session_id: {session_id}, user_id: {current_user.id} - Error: {str(e)}")
        raise

