"""Audit log schemas"""
from datetime import datetime
from typing import Any, Dict, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AuditLogCreate(BaseModel):
    """Schema for creating audit log"""

    action: str = Field(..., description="Action performed")
    resource: Optional[str] = Field(None, description="Resource accessed")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    allowed: bool = Field(..., description="Whether action was allowed")
    result: Literal["success", "error"] = Field(..., description="Result of action")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    request_id: Optional[Union[UUID, str]] = Field(None, description="Request ID for correlation")


class AuditLogResponse(BaseModel):
    """Schema for audit log response"""

    log_id: Union[UUID, str]
    agent_id: str
    timestamp: datetime
    action: str
    resource: Optional[str]
    context: Optional[Dict[str, Any]]
    allowed: bool
    result: str
    metadata: Optional[Dict[str, Any]] = None
    request_id: Optional[Union[UUID, str]]

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def map_log_metadata(cls, data):
        """Map log_metadata attribute to metadata field"""
        # Handle SQLAlchemy model objects
        if hasattr(data, '__dict__') and hasattr(data, 'log_metadata'):
            return {
                'log_id': data.log_id,
                'agent_id': data.agent_id,
                'timestamp': data.timestamp,
                'action': data.action,
                'resource': data.resource,
                'context': data.context,
                'allowed': data.allowed,
                'result': data.result,
                'metadata': data.log_metadata,
                'request_id': data.request_id
            }
        return data
