from typing import Optional, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """Standardized API response format."""
    status: str  # "SUCCESS" or "FAIL"
    message: str
    data: Optional[T] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "SUCCESS",
                "message": "Operation completed successfully",
                "data": None
            }
        }
