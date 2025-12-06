from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any


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


class MessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    extra_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    content: str = Field(..., min_length=1, description="User message content")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "What is the capital of France?"
            }
        }

