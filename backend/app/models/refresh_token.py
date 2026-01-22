from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class RefreshToken(BaseModel):
    __tablename__ = "refresh_tokens"

    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_revoked = Column(Boolean, default=False, nullable=False)
    
    # Relationship
    user = relationship("User", back_populates="refresh_tokens")

