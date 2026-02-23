"""Policy model"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.database import Base


class Policy(Base):
    """Policy model - defines allow/deny rules for agents"""

    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(50), ForeignKey("agents.agent_id", ondelete="CASCADE"), unique=True, nullable=False)
    allow_rules = Column(JSON, default=list, nullable=False)  # List of {action, resource} dicts
    deny_rules = Column(JSON, default=list, nullable=False)   # List of {action, resource} dicts
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="policy")
