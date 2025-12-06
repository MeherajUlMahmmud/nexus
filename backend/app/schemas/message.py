from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import UploadFile
from pydantic import BaseModel, Field


class MessageBase(BaseModel):
    content: str = Field(..., min_length=1, description="Message content")
    role: str = Field(..., pattern="^(user|assistant)$", description="Message role: user or assistant")


class MessageCreate(MessageBase):
    pass

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Hello, how are you?",
                "role": "user"
            }
        }


class FileResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    file_url: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    extra_metadata: Optional[Dict[str, Any]] = None
    files: List["FileResponse"] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    content: str = Field(..., min_length=1, description="User message content")
    files: Optional[List[UploadFile]] = Field(None, description="Optional files")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "What is the capital of France?"
            }
        }
