"""Agent schemas"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    """Schema for creating a new agent"""

    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    owner_team: str = Field(..., min_length=1, max_length=255, description="Team that owns this agent")
    environment: Literal["development", "staging", "production"] = Field(..., description="Environment where agent runs")


class AgentResponse(BaseModel):
    """Schema for agent response (without API key)"""

    agent_id: str
    name: str
    owner_team: str
    environment: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentWithKey(BaseModel):
    """Schema for agent response with API key (only shown once at creation)"""

    agent_id: str
    name: str
    owner_team: str
    environment: str
    is_active: bool
    created_at: datetime
    api_key: str = Field(..., description="API key - only shown once, save securely!")

    class Config:
        from_attributes = True
