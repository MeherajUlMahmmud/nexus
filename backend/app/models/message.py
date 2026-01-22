from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class File(BaseModel):
    __tablename__ = "files"

    message_id = Column(
        GUID(),
        ForeignKey("messages.id"),
        nullable=False,
        index=True
    )
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # File size in bytes
    file_content = Column(Text, nullable=False)
    file_url = Column(String, nullable=False)

    # Relationships
    message = relationship("Message", back_populates="files")


class Message(BaseModel):
    __tablename__ = "messages"

    session_id = Column(GUID(), ForeignKey(
        "chat_sessions.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    # For storing token counts, etc.
    extra_metadata = Column(JSON, nullable=True)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    files = relationship("File", back_populates="message")
