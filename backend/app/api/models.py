import logging

from fastapi import APIRouter

from app.schemas.response import APIResponse
from app.services.groq import get_available_models
from app.utils.response import success_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/models", tags=["Models"])


@router.get("", response_model=APIResponse)
async def get_models():
    """Get available AI models."""
    logger.info("Get models requested")
    try:
        models = await get_available_models()
        logger.info(f"Models retrieved successfully - count: {len(models)}")
        return success_response(
            message="Models retrieved successfully",
            data=models
        )
    except Exception as e:
        logger.error(f"Failed to retrieve models - Error: {str(e)}")
        raise
