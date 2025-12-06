import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status

from app.exceptions import BadRequestError
from app.models.user import User
from app.schemas.response import APIResponse
from app.services.groq import transcribe_audio
from app.utils.dependencies import get_current_user
from app.utils.response import success_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Transcription"])

# Configuration
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB limit (Groq's limit)
SUPPORTED_FORMATS = {'.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm'}


@router.post("/transcribe", response_model=APIResponse)
async def transcribe_audio_endpoint(
        audio_file: UploadFile = File(..., description="Audio file to transcribe"),
        temperature: float = 0.0,
        response_format: str = "verbose_json",
        current_user: User = Depends(get_current_user),
):
    """
    Transcribe audio file to text using Groq's Whisper API.

    Supported formats: mp3, mp4, mpeg, mpga, m4a, wav, webm
    Max file size: 25MB
    """
    logger.info(
        f"Transcription requested - user_id: {current_user.id}, filename: {audio_file.filename}")

    temp_path = None

    try:
        # Validate file format
        file_ext = Path(audio_file.filename).suffix.lower()
        logger.info(f"File extension: {file_ext}")
        if file_ext not in SUPPORTED_FORMATS:
            raise BadRequestError(
                f"Unsupported audio format: {file_ext}. "
                f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
            )

        # Read file content and check size
        audio_content = await audio_file.read()
        file_size = len(audio_content)

        if file_size > MAX_AUDIO_SIZE:
            raise BadRequestError(
                f"File too large: {file_size / (1024 * 1024):.2f}MB. "
                f"Maximum size: {MAX_AUDIO_SIZE / (1024 * 1024):.0f}MB"
            )

        if file_size == 0:
            raise BadRequestError("Empty audio file")

        # Save to temporary file
        with tempfile.NamedTemporaryFile(
                suffix=file_ext,
                delete=False
        ) as temp_file:
            temp_path = temp_file.name
            temp_file.write(audio_content)

        logger.info(
            f"Audio saved to temp file: {temp_path}, size: {file_size / 1024:.2f}KB")

        # Call Groq transcription service
        result = await transcribe_audio(
            audio_file_path=temp_path,
            temperature=temperature,
            response_format=response_format
        )

        # Check if transcription was successful
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown transcription error")
            logger.error(
                f"Transcription failed - user_id: {current_user.id} - Error: {error_msg}")
            raise BadRequestError(f"Transcription failed: {error_msg}")

        logger.info(
            f"Transcription successful - user_id: {current_user.id}, "
            f"language: {result.get('language')}, duration: {result.get('duration', 0):.2f}s"
        )

        # Prepare response data
        response_data = {
            "text": result.get("text", ""),
            "language": result.get("language"),
            "duration": result.get("duration"),
        }

        # Include segments if available (verbose_json format)
        if result.get("segments"):
            response_data["segments"] = result["segments"]

        return success_response(
            message="Transcription successful",
            data=response_data
        )

    except BadRequestError:
        raise
    except Exception as e:
        logger.error(
            f"Failed to transcribe audio - user_id: {current_user.id}, "
            f"filename: {audio_file.filename} - Error: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.debug(f"Cleaned up temp file: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_path}: {e}")
