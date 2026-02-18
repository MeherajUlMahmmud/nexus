import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.exceptions import BadRequestError
from app.prompts import SESSION_TITLE_SYSTEM_PROMPT, get_session_title_prompt
from app.utils.cache_keys import MODELS_CACHE_KEY
from app.utils.redis_client import get_redis_client
from groq import Groq
import httpx

logger = logging.getLogger(__name__)

# Initialize Groq client
groq_client = Groq(
    api_key=settings.groq_api_key
) if settings.groq_api_key else None

# Audio transcription configuration
SUPPORTED_FORMATS = {'.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm'}
MAX_DURATION_SECONDS = 300  # 5 minutes (adjust based on your needs)
# or "whisper-large-v3-turbo" for faster processing
WHISPER_MODEL = "whisper-large-v3"


def _get_audio_duration(audio_file_path: str) -> float:
    """
    Get audio file duration in seconds.

    Note: This requires ffprobe to be installed.
    Alternative: use librosa or pydub if available.
    """
    try:
        import subprocess

        result = subprocess.run(
            [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_file_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return float(result.stdout.strip())
        else:
            logger.warning(
                f"Could not determine audio duration: {result.stderr}")
            return 0.0
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError) as e:
        logger.warning(f"Could not determine audio duration: {e}")
        # Return 0 if we can't determine duration (validation will be skipped)
        return 0.0


async def get_available_models() -> List[Dict[str, Any]]:
    """Get list of available Groq models from the API, with Redis caching."""
    redis_client = await get_redis_client()

    # Try to get from Redis cache first
    if redis_client:
        try:
            cached_models = await redis_client.get(MODELS_CACHE_KEY)
            if cached_models:
                models = json.loads(cached_models)
                logger.debug(
                    f"Retrieved {len(models)} models from Redis cache")
                return models
        except Exception as e:
            logger.warning(f"Error reading from Redis cache: {str(e)}")

    if not settings.groq_api_key:
        logger.warning(
            "Groq API key not configured, returning empty model list")
        return []

    try:
        url = "https://api.groq.com/openai/v1/models"
        headers = {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        # Transform the response to match our expected format
        models = []

        if isinstance(data, dict) and "data" in data:
            for model in data["data"]:
                models.append({
                    "id": model.get("id", ""),
                    "name": model.get("id", "").replace("/", " ").replace("-", " ").title(),
                    "context_length": model.get("context_window", 8192) if "context_window" in model else 8192,
                    "description": f"Model ID: {model.get('id', '')}"
                })
        elif isinstance(data, list):
            # Handle case where API returns a list directly
            for model in data:
                models.append({
                    "id": model.get("id", ""),
                    "name": model.get("id", "").replace("/", " ").replace("-", " ").title(),
                    "context_length": model.get("context_window", 8192) if "context_window" in model else 8192,
                    "description": f"Model ID: {model.get('id', '')}"
                })

        # Cache the models in Redis
        if redis_client and models:
            try:
                models_json = json.dumps(models)
                await redis_client.setex(
                    MODELS_CACHE_KEY,
                    settings.models_cache_ttl,
                    models_json
                )
                logger.info(
                    f"Cached {len(models)} models in Redis for {settings.models_cache_ttl} seconds")
            except Exception as e:
                logger.warning(f"Error caching models in Redis: {str(e)}")

        return models

    except httpx.HTTPError as e:
        logger.error(f"Error fetching models from Groq API: {str(e)}")
        # Return empty list on error, but don't cache it
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching models: {str(e)}")
        return []


async def clear_models_cache():
    """Clear the models cache in Redis (useful for testing or forcing refresh)."""
    redis_client = await get_redis_client()
    if redis_client:
        try:
            await redis_client.delete(MODELS_CACHE_KEY)
            logger.info("Cleared models cache from Redis")
        except Exception as e:
            logger.warning(f"Error clearing models cache from Redis: {str(e)}")


async def get_chat_completion(
        messages: List[Dict[str, str]],
        model: str = "llama-3.1-8b-instant",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get chat completion from Groq API with optional function calling support.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        tools: Optional list of tools in Groq function calling format
        tool_choice: Control when tools are called. Options:
            - "none": Don't call any tools (even if tools are provided)
            - "auto": Let the model decide (default behavior)
            - "required": Force the model to call at least one tool
            - {"type": "function", "function": {"name": "tool_name"}}: Force specific tool

    Returns:
        Dict with 'content', 'tool_calls' (if any), and 'metadata'
    """
    if not groq_client:
        raise BadRequestError("Groq API key not configured")

    # Validate model against available models
    available_models = await get_available_models()
    model_ids = [m["id"] for m in available_models]

    # If we couldn't fetch models, skip validation (API will handle it)
    if model_ids and model not in model_ids:
        raise BadRequestError(
            f"Invalid model: {model}. Available models: {', '.join(model_ids[:5])}...")

    try:
        import time
        api_start = time.time()

        # Prepare messages for Groq API
        groq_messages = []
        for msg in messages:
            message_dict = {"role": msg["role"]}

            # Add content if it exists and is not None
            if "content" in msg and msg["content"] is not None:
                message_dict["content"] = msg["content"]

            # Add tool_calls if present (for assistant messages)
            if "tool_calls" in msg:
                message_dict["tool_calls"] = msg["tool_calls"]

            # Add name if present (for tool messages)
            if "name" in msg:
                message_dict["name"] = msg["name"]

            # Add tool_call_id if present (for tool messages)
            if "tool_call_id" in msg:
                message_dict["tool_call_id"] = msg["tool_call_id"]

            groq_messages.append(message_dict)

        # Prepare API call parameters
        api_params = {
            "model": model,
            "messages": groq_messages,
            "temperature": temperature,
        }

        if max_tokens:
            api_params["max_tokens"] = max_tokens

        # Add tools if provided
        if tools:
            api_params["tools"] = tools
            logger.debug(f"[GROQ_API] Tools provided: {len(tools)} tool(s)")
            # Set tool_choice if provided (gives control over when tools are called)
            # Options: "none" (disable), "auto" (let model decide), "required" (force call)
            if tool_choice is not None:
                try:
                    api_params["tool_choice"] = tool_choice
                    logger.debug(
                        f"[GROQ_API] Setting tool_choice to: {tool_choice}")
                except Exception as e:
                    # Some models may not support tool_choice parameter
                    logger.warning(
                        f"[GROQ_API] Model {model} may not support tool_choice parameter: {e}")

        logger.info(f"[GROQ_API] Calling Groq API - model: {model}, messages: {len(groq_messages)}, "
                    f"temperature: {temperature}, max_tokens: {max_tokens}")

        # Call Groq API
        response = groq_client.chat.completions.create(**api_params)

        api_time = time.time() - api_start
        logger.info(
            f"[GROQ_API] Response received in {api_time:.2f}s - model: {model}")

        # Extract response
        message = response.choices[0].message
        assistant_message = message.content if hasattr(
            message, 'content') and message.content else None

        # Extract tool calls if present
        tool_calls = None
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_calls = []
            for tool_call in message.tool_calls:
                tool_calls.append({
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                })

        # Extract metadata
        metadata = {
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if hasattr(response, 'usage') and response.usage else None,
            "finish_reason": response.choices[0].finish_reason if response.choices else None,
        }

        result = {
            "metadata": metadata
        }

        # Only include content if it's not None
        if assistant_message is not None:
            result["content"] = assistant_message

        if tool_calls:
            result["tool_calls"] = tool_calls

        return result

    except Exception as e:
        raise BadRequestError(f"Error calling Groq API: {str(e)}")


async def generate_session_title(message: str, model: str = "llama-3.1-8b-instant") -> str:
    """Generate a session title from the user's initial message using LLM."""
    if not groq_client:
        # Fallback to a simple title if Groq is not configured
        return message[:50] + "..." if len(message) > 50 else message

    try:
        response = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SESSION_TITLE_SYSTEM_PROMPT},
                {"role": "user", "content": get_session_title_prompt(message)}
            ],
            temperature=0.3,
            max_tokens=50,
        )

        title = response.choices[0].message.content.strip()
        # Remove any quotes or extra formatting
        title = title.strip('"\'')
        # Limit to 200 characters (database constraint)
        title = title[:200]

        # Fallback if title is empty or too short
        if not title or len(title) < 3:
            title = message[:50] + "..." if len(message) > 50 else message

        return title

    except Exception as e:
        logger.warning(
            f"Error generating title from LLM: {str(e)}, using fallback")
        # Fallback to a simple title
        return message[:50] + "..." if len(message) > 50 else message


async def transcribe_audio(
        audio_file_path: str,
        language: Optional[str] = None,
        temperature: float = 0.0,
        response_format: str = "verbose_json"
) -> Dict[str, Any]:
    """
    Transcribe audio file to text using Groq's Whisper API.

    Args:
        audio_file_path: Path to audio file
        language: Language code (e.g., 'bn' for Bangla, 'en' for English)
                 If None, will auto-detect
        temperature: Temperature for sampling (0-1, default: 0 for deterministic)
        response_format: Response format (json, verbose_json, or text)

    Returns:
        Dict containing:
            - text: Transcribed text
            - language: Detected/specified language
            - duration: Audio duration in seconds
            - segments: Word-level segments (if verbose_json)
            - success: Boolean indicating success

    Raises:
        BadRequestError: If Groq client not configured
        ValueError: If file format not supported or file too large
        FileNotFoundError: If audio file doesn't exist
    """
    if not groq_client:
        raise BadRequestError("Groq API key not configured")

    # Validate file exists
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

    # Validate file format
    file_ext = Path(audio_file_path).suffix.lower()
    if file_ext not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported audio format: {file_ext}. "
            f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )

    try:
        # Validate audio duration (optional - skip if ffprobe not available)
        duration = _get_audio_duration(audio_file_path)
        if duration > 0 and duration > MAX_DURATION_SECONDS:
            raise ValueError(
                f"Audio too long: {duration:.2f}s "
                f"(max: {MAX_DURATION_SECONDS}s)"
            )

        # Read audio file
        logger.info(f"Transcribing audio with Groq API: {audio_file_path}")

        with open(audio_file_path, "rb") as file:
            # Prepare transcription parameters
            transcribe_params = {
                "file": (os.path.basename(audio_file_path), file),
                "model": WHISPER_MODEL,
                "temperature": temperature,
                "response_format": response_format
            }

            # Add language if specified
            if language:
                transcribe_params["language"] = language

            # Call Groq API
            transcription = groq_client.audio.transcriptions.create(
                **transcribe_params)

        # Parse response based on format
        if response_format == "text":
            transcribed_text = transcription
            detected_language = language or "unknown"
            segments = []
        else:
            # For json or verbose_json
            transcribed_text = transcription.text if hasattr(
                transcription, 'text') else str(transcription)
            detected_language = getattr(
                transcription, 'language', language or "unknown")
            segments = getattr(transcription, 'segments', [])

        logger.info(
            f"Transcription complete: language={detected_language}, "
            f"duration={duration:.2f}s, text_length={len(transcribed_text)}"
        )

        return {
            "text": transcribed_text,
            "language": detected_language,
            "duration": duration if duration > 0 else None,
            "segments": segments,
            "success": True
        }

    except ValueError:
        # Re-raise validation errors
        raise

    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        return {
            "text": "",
            "language": language or "unknown",
            "duration": None,
            "segments": [],
            "error": str(e),
            "success": False
        }
