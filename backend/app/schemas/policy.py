"""Policy schemas"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PolicyRule(BaseModel):
    """Schema for a single policy rule"""

    action: str = Field(..., description="Action pattern (e.g., 'read:file', 'delete:*')")
    resource: Optional[str] = Field(None, description="Resource pattern (e.g., 's3://bucket/*', '*')")
    conditions: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Optional conditions that must ALL pass for this rule to apply. "
            "Supported keys: env (list), time_range ({start, end, tz}), day_of_week (list). "
            "Missing keys are ignored (always pass). Example: "
            '{\"env\": [\"production\"], \"time_range\": {\"start\": \"09:00\", \"end\": \"17:00\", \"tz\": \"UTC\"}}'
        ),
    )


class PolicyRequest(BaseModel):
    """Schema for setting agent policy"""

    allow: List[PolicyRule] = Field(default_factory=list, description="Allow rules")
    deny: List[PolicyRule] = Field(default_factory=list, description="Deny rules")
    require_approval: List[PolicyRule] = Field(default_factory=list, description="Rules that require human approval")


class PolicyResponse(BaseModel):
    """Schema for policy response"""

    agent_id: str
    allow: List[Dict[str, Any]]
    deny: List[Dict[str, Any]]
    require_approval: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PolicyGenerateRequest(BaseModel):
    """Schema for AI-assisted policy generation"""

    description: str = Field(..., description="Natural language description of what the agent should/shouldn't do", min_length=10)


class PolicyGenerateResponse(BaseModel):
    """Schema for AI-generated policy proposal"""

    allow: List[Dict[str, Any]]
    deny: List[Dict[str, Any]]
    explanation: str


class EnforceRequest(BaseModel):
    """Schema for enforcement request"""

    action: str = Field(..., description="Action to check (e.g., 'read:file')")
    resource: Optional[str] = Field(None, description="Resource to check (e.g., 'invoice.pdf')")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class EnforceResponse(BaseModel):
    """Schema for enforcement response"""

    allowed: bool = Field(..., description="Whether action is allowed (True only when status='allowed')")
    status: str = Field(..., description="Outcome: 'allowed', 'denied', or 'pending'")
    reason: str = Field(..., description="Explanation of decision")
    approval_id: Optional[str] = Field(None, description="Approval request ID (set only when status='pending')")
