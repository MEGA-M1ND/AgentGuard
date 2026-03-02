"""Admin user management + team policy endpoints"""
import hashlib
import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.database import get_db
from app.models.admin_user import AdminUser
from app.models.team_policy import TeamPolicy
from app.schemas.admin_user import (
    AdminUserCreate,
    AdminUserResponse,
    AdminUserWithKey,
    TeamPolicyResponse,
    TeamPolicySet,
)
from app.utils.logger import logger

router = APIRouter(tags=["admin"])

_ADMIN_ID_PREFIX = "adm_"


def _generate_admin_key() -> str:
    return f"adk_{secrets.token_urlsafe(32)}"


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _generate_admin_id() -> str:
    return f"{_ADMIN_ID_PREFIX}{secrets.token_urlsafe(10)}"


# ---------------------------------------------------------------------------
# Admin user CRUD (super-admin only)
# ---------------------------------------------------------------------------

@router.post("/admin/users", response_model=AdminUserWithKey, status_code=201)
def create_admin_user(
    data: AdminUserCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """
    Create a named admin user (super-admin only).

    The raw ``api_key`` is returned **once** at creation and never stored.
    Use this key with ``POST /token`` to obtain a role-scoped JWT.
    """
    api_key = _generate_admin_key()
    key_hash = _hash_key(api_key)
    key_prefix = api_key[:12]
    admin_id = _generate_admin_id()

    user = AdminUser(
        admin_id=admin_id,
        name=data.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        role=data.role,
        team=data.team,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"Created admin user: {admin_id}", extra={"admin_id": admin_id, "role": data.role})

    return AdminUserWithKey(
        admin_id=user.admin_id,
        name=user.name,
        role=user.role,
        team=user.team,
        is_active=user.is_active,
        created_at=user.created_at,
        api_key=api_key,
    )


@router.get("/admin/users", response_model=List[AdminUserResponse])
def list_admin_users(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """List all admin users (super-admin only)."""
    return db.query(AdminUser).order_by(AdminUser.created_at.desc()).all()


@router.delete("/admin/users/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_admin_user(
    admin_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Deactivate (soft-delete) an admin user (super-admin only)."""
    user = db.query(AdminUser).filter(AdminUser.admin_id == admin_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"Admin user {admin_id} not found")

    user.is_active = False
    db.commit()

    logger.info(f"Deactivated admin user: {admin_id}")
    return None


# ---------------------------------------------------------------------------
# Team policy management
# ---------------------------------------------------------------------------

@router.put("/teams/{team}/policy", response_model=TeamPolicyResponse)
def set_team_policy(
    team: str,
    data: TeamPolicySet,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """
    Create or replace the base policy for a team (admin+).

    Team deny rules take precedence over individual agent allow rules at enforcement time.
    """
    policy = db.query(TeamPolicy).filter(TeamPolicy.team == team).first()

    if policy:
        policy.allow_rules = data.allow_rules
        policy.deny_rules = data.deny_rules
        policy.require_approval_rules = data.require_approval_rules
    else:
        policy = TeamPolicy(
            team=team,
            allow_rules=data.allow_rules,
            deny_rules=data.deny_rules,
            require_approval_rules=data.require_approval_rules,
        )
        db.add(policy)

    db.commit()
    db.refresh(policy)

    logger.info(f"Team policy set for: {team}")
    return policy


@router.get("/teams/{team}/policy", response_model=TeamPolicyResponse)
def get_team_policy(
    team: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Get the base policy for a team (auditor+)."""
    policy = db.query(TeamPolicy).filter(TeamPolicy.team == team).first()
    if not policy:
        raise HTTPException(status_code=404, detail=f"No policy set for team '{team}'")
    return policy
