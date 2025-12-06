from sqlalchemy import Column, String, DateTime, Integer, Text

from app.models.base import BaseModel


class BlockedIP(BaseModel):
    __tablename__ = "blocked_ips"

    ip_address = Column(String, unique=True, index=True, nullable=False)
    blocked_at = Column(DateTime, nullable=False)
    attempts_count = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=True)  # Reason for blocking (e.g., "Sensitive URL access attempts")
    user_agent = Column(Text, nullable=True)  # User agent from the last attempt
