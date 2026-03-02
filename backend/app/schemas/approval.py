"""Approval request schemas"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApprovalRequestResponse(BaseModel):
    """Schema for an approval request"""

    approval_id: str
    agent_id: str
    agent_name: Optional[str] = None    # Joined from agents table for display
    status: str                          # pending | approved | denied
    action: str
    resource: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    created_at: datetime
    decision_at: Optional[datetime] = None
    decision_by: Optional[str] = None   # admin key prefix
    decision_reason: Optional[str] = None

    class Config:
        from_attributes = True


class ApprovalDecisionRequest(BaseModel):
    """Schema for approve/deny decision"""

    reason: str = Field(default="", description="Reason for this decision (required when denying)")


class ApprovalListResponse(BaseModel):
    """Schema for list of approval requests"""

    items: List[ApprovalRequestResponse]
    total: int
    pending_count: int
