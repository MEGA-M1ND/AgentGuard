"""AdminUser schemas"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

VALID_ROLES = {"super-admin", "admin", "auditor", "approver"}


class AdminUserCreate(BaseModel):
    name: str = Field(..., description="Display name for this admin user")
    role: str = Field(..., description="Role: admin | auditor | approver")
    team: Optional[str] = Field(None, description="Team scope (null = all teams)")

    def model_post_init(self, __context) -> None:
        if self.role not in ("admin", "auditor", "approver"):
            raise ValueError("role must be one of: admin, auditor, approver (super-admin is reserved for ADMIN_API_KEY)")


class AdminUserResponse(BaseModel):
    admin_id: str
    name: str
    role: str
    team: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUserWithKey(AdminUserResponse):
    """Returned once at creation — includes the raw API key (never stored)."""
    api_key: str


class TeamPolicySet(BaseModel):
    allow_rules: List[dict] = Field(default_factory=list)
    deny_rules: List[dict] = Field(default_factory=list)
    require_approval_rules: List[dict] = Field(default_factory=list)


class TeamPolicyResponse(BaseModel):
    team: str
    allow_rules: List[dict]
    deny_rules: List[dict]
    require_approval_rules: List[dict]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
