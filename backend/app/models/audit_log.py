"""Audit log model"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid_string():
    """Generate UUID as string for SQLite compatibility"""
    return str(uuid.uuid4())


class AuditLog(Base):
    """AuditLog model - append-only logs of agent actions"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(String(36), default=generate_uuid_string, unique=True, nullable=False, index=True)
    agent_id = Column(String(50), ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    action = Column(String(255), nullable=False, index=True)
    resource = Column(Text, nullable=True)
    context = Column(JSON, nullable=True)
    allowed = Column(Boolean, nullable=False, index=True)
    result = Column(String(50), nullable=False)  # success, error
    log_metadata = Column("metadata", JSON, nullable=True)  # Column name is 'metadata', attribute is 'log_metadata'
    request_id = Column(String(36), nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="logs")
