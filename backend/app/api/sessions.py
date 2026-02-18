import logging
import uuid

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.response import APIResponse
from app.schemas.session import SessionCreate, SessionUpdate
from app.services.session import SessionService
from app.utils.dependencies import get_current_user
from app.utils.response import success_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["Chat Sessions"])


def get_session_service() -> SessionService:
    """Dependency that returns the session service instance."""
    return SessionService()


@router.get("/list", response_model=APIResponse)
async def get_sessions(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        session_service: SessionService = Depends(get_session_service),
):
    """Get all chat sessions for the authenticated user."""
    logger.info(f"Get sessions requested for user_id: {current_user.id}, skip: {skip}, limit: {limit}")
    try:
        sessions = await session_service.get_user_sessions(db, current_user, skip, limit)
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
        db: AsyncSession = Depends(get_db),
        session_service: SessionService = Depends(get_session_service),
):
    """Create a new chat session."""
    logger.info(
        f"Create session requested for user_id: {current_user.id}, title: {session_data.title}, model: {session_data.model_name}")
    try:
        session = await session_service.create_session(db, current_user, session_data)
        logger.info(
            f"Session created successfully - session_id: {session.id}, user_id: {current_user.id}, model: {session.model_name}")
        return success_response(
            message="Session created successfully",
            data=session.model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to create session for user_id: {current_user.id} - Error: {str(e)}")
        raise


@router.get("/{session_id}/details", response_model=APIResponse)
async def get_session(
        session_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        session_service: SessionService = Depends(get_session_service),
):
    """Get details of a specific chat session."""
    logger.info(f"Get session requested - session_id: {session_id}, user_id: {current_user.id}")
    try:
        session = await session_service.get_session_by_id(db, session_id, current_user)
        logger.info(f"Session retrieved successfully - session_id: {session_id}, user_id: {current_user.id}")
        return success_response(
            message="Session retrieved successfully",
            data=session.model_dump()
        )
    except Exception as e:
        logger.warning(
            f"Failed to retrieve session - session_id: {session_id}, user_id: {current_user.id} - Error: {str(e)}")
        raise


@router.put("/{session_id}/update", response_model=APIResponse)
async def update_session_endpoint(
        session_id: uuid.UUID,
        session_update: SessionUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        session_service: SessionService = Depends(get_session_service),
):
    """Update a chat session."""
    logger.info(f"Update session requested - session_id: {session_id}, user_id: {current_user.id}")
    try:
        session = await session_service.update_session(db, session_id, current_user, session_update)
        logger.info(f"Session updated successfully - session_id: {session_id}, user_id: {current_user.id}")
        return success_response(
            message="Session updated successfully",
            data=session.model_dump()
        )
    except Exception as e:
        logger.warning(
            f"Failed to update session - session_id: {session_id}, user_id: {current_user.id} - Error: {str(e)}")
        raise


@router.delete("/{session_id}/delete", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def delete_session_endpoint(
        session_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        session_service: SessionService = Depends(get_session_service),
):
    """Delete a chat session."""
    logger.info(f"Delete session requested - session_id: {session_id}, user_id: {current_user.id}")
    try:
        await session_service.delete_session(db, session_id, current_user)
        logger.info(f"Session deleted successfully - session_id: {session_id}, user_id: {current_user.id}")
        return success_response(
            message="Session deleted successfully",
            data=None
        )
    except Exception as e:
        logger.warning(
            f"Failed to delete session - session_id: {session_id}, user_id: {current_user.id} - Error: {str(e)}")
        raise
