"""ApprovalRequest model"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid_string():
    """Generate UUID as string for SQLite compatibility"""
    return str(uuid.uuid4())


class ApprovalRequest(Base):
    """ApprovalRequest model - tracks agent actions pending human approval"""

    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    approval_id = Column(String(36), default=generate_uuid_string, unique=True, nullable=False, index=True)
    agent_id = Column(String(50), ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending | approved | denied
    action = Column(String(255), nullable=False)
    resource = Column(Text, nullable=True)
    context = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    decision_at = Column(DateTime, nullable=True)
    decision_by = Column(String(50), nullable=True)   # admin key prefix for audit trail
    decision_reason = Column(Text, nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="approval_requests")
