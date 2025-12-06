from typing import Optional, Any
from fastapi.responses import JSONResponse
from app.schemas.response import APIResponse


def success_response(
    message: str = "Operation completed successfully",
    data: Optional[Any] = None
) -> APIResponse:
    """Create a standardized success response."""
    return APIResponse(
        status="SUCCESS",
        message=message,
        data=data
    )


def fail_response(
    message: str = "Operation failed",
    data: Optional[Any] = None,
    status_code: int = 400
) -> JSONResponse:
    """Create a standardized fail response for exception handlers."""
    response = APIResponse(
        status="FAIL",
        message=message,
        data=data
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(exclude_none=True)
    )
