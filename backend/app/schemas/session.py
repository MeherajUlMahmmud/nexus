from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.schemas.message import MessageResponse


class SessionBase(BaseModel):
    title: Optional[str] = Field(None, max_length=200, description="Session title")
    model_name: Optional[str] = Field(None, description="AI model name")


class SessionCreate(SessionBase):
    title: Optional[str] = Field(None, max_length=200, description="Session title (will be generated from message if not provided)")
    model_name: str = Field(default="llama-3.1-8b-instant", description="AI model name")
    message: Optional[str] = Field(None, min_length=1, description="Initial message to generate title from")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "My Chat Session",
                "model_name": "llama-3.1-8b-instant",
                "message": "What is the capital of France?"
            }
        }


class SessionUpdate(SessionBase):
    pass


class SessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    model_name: str
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[MessageResponse]] = None
    
    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    id: int
    user_id: int
    title: str
    model_name: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

