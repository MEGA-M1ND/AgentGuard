"""Agent and AgentKey models"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Agent(Base):
    """Agent model - represents an AI agent identity"""

    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    owner_team = Column(String(255), nullable=False)
    environment = Column(String(50), nullable=False, index=True)  # dev, stage, prod
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    keys = relationship("AgentKey", back_populates="agent", cascade="all, delete-orphan")
    policy = relationship("Policy", back_populates="agent", uselist=False, cascade="all, delete-orphan")
    logs = relationship("AuditLog", back_populates="agent", cascade="all, delete-orphan")


class AgentKey(Base):
    """AgentKey model - stores hashed API keys for agents"""

    __tablename__ = "agent_keys"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(50), ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False, index=True)
    key_hash = Column(String(255), unique=True, nullable=False)  # SHA256 hash
    key_prefix = Column(String(20), nullable=False, index=True)  # First 8 chars for identification
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="keys")
