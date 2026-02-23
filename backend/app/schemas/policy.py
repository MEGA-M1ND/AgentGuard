"""Policy schemas"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PolicyRule(BaseModel):
    """Schema for a single policy rule"""

    action: str = Field(..., description="Action pattern (e.g., 'read:file', 'delete:*')")
    resource: Optional[str] = Field(None, description="Resource pattern (e.g., 's3://bucket/*', '*')")


class PolicyRequest(BaseModel):
    """Schema for setting agent policy"""

    allow: List[PolicyRule] = Field(default_factory=list, description="Allow rules")
    deny: List[PolicyRule] = Field(default_factory=list, description="Deny rules")


class PolicyResponse(BaseModel):
    """Schema for policy response"""

    agent_id: str
    allow: List[Dict[str, Any]]
    deny: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EnforceRequest(BaseModel):
    """Schema for enforcement request"""

    action: str = Field(..., description="Action to check (e.g., 'read:file')")
    resource: Optional[str] = Field(None, description="Resource to check (e.g., 'invoice.pdf')")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class EnforceResponse(BaseModel):
    """Schema for enforcement response"""

    allowed: bool = Field(..., description="Whether action is allowed")
    reason: str = Field(..., description="Explanation of decision")
