"""API dependencies for authentication and authorization.

Dual-mode auth: every dependency accepts EITHER
  - Authorization: Bearer <JWT>   (new, preferred path)
  - X-Admin-Key / X-Agent-Key     (legacy header path, backward-compatible)

JWT path is checked first; legacy path is used if no Bearer token is present.

RBAC
----
Admin tokens carry ``role`` and (optionally) ``team`` JWT claims.
Use :func:`require_role` for role-gated endpoints and :func:`get_admin_context`
when you need the role/team values inside a handler.

Role hierarchy (higher level → more permissions):
    super-admin (4) > admin (3) > auditor (2) > approver (1)
"""
from typing import Callable, NamedTuple, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.agent import Agent
from app.utils.auth import verify_api_key
from app.utils.jwt_utils import decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Role hierarchy
# ---------------------------------------------------------------------------

_ROLE_HIERARCHY: dict[str, int] = {
    "super-admin": 4,
    "admin": 3,
    "auditor": 2,
    "approver": 1,
}


class AdminContext(NamedTuple):
    """Resolved admin identity, populated by :func:`get_admin_context`."""
    sub: str                  # admin_id (from DB) or "admin" (legacy super-admin)
    role: str                 # super-admin | admin | auditor | approver
    team: Optional[str]       # None = access to all teams


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_admin_context(
    credentials: Optional[HTTPAuthorizationCredentials],
    x_admin_key: Optional[str],
    db: Session,
) -> AdminContext:
    """Extract AdminContext from JWT or legacy header. Raises 401/403 on failure."""
    # JWT path
    if credentials:
        payload = decode_access_token(credentials.credentials, db)
        if payload.get("type") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin token required",
            )
        # Tokens issued before RBAC have no 'role' claim → treat as super-admin
        role = payload.get("role", "super-admin")
        team = payload.get("team")
        return AdminContext(sub=payload["sub"], role=role, team=team)

    # Legacy header path
    if x_admin_key:
        if x_admin_key == settings.ADMIN_API_KEY:
            return AdminContext(sub="admin", role="super-admin", team=None)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide Authorization: Bearer <token> or X-Admin-Key header.",
    )


# ---------------------------------------------------------------------------
# require_admin (legacy — returns str for backward compatibility)
# ---------------------------------------------------------------------------

def require_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    x_admin_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> str:
    """Require admin authentication (any admin role accepted).

    Accepts (in priority order):
    - ``Authorization: Bearer <JWT>`` where the token carries ``type == "admin"``
    - ``X-Admin-Key: <static-key>`` (legacy, backward-compatible)

    Returns the admin subject string for backward compatibility with existing callers.
    For role-aware code, use :func:`get_admin_context` or :func:`require_role` instead.
    """
    ctx = _resolve_admin_context(credentials, x_admin_key, db)
    return ctx.sub


# ---------------------------------------------------------------------------
# get_admin_context — returns full AdminContext (role + team)
# ---------------------------------------------------------------------------

def get_admin_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    x_admin_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> AdminContext:
    """Resolve and return the full admin context (role + team scope).

    Use this dependency when a handler needs the caller's role or team to apply
    fine-grained access control (e.g. filtering by team).
    """
    return _resolve_admin_context(credentials, x_admin_key, db)


# ---------------------------------------------------------------------------
# require_role factory — role-gated dependency
# ---------------------------------------------------------------------------

def require_role(min_role: str) -> Callable:
    """Return a FastAPI dependency that enforces a minimum admin role.

    Usage::

        @router.post("/sensitive")
        def endpoint(ctx: AdminContext = Depends(require_role("admin"))):
            ...

    Args:
        min_role: Minimum required role (``super-admin`` | ``admin`` | ``auditor`` | ``approver``).

    Returns:
        A FastAPI-injectable callable that resolves to :class:`AdminContext` or raises 403.
    """
    min_level = _ROLE_HIERARCHY.get(min_role, 0)

    def _role_dep(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
        x_admin_key: Optional[str] = Header(None),
        db: Session = Depends(get_db),
    ) -> AdminContext:
        ctx = _resolve_admin_context(credentials, x_admin_key, db)
        role_level = _ROLE_HIERARCHY.get(ctx.role, 0)
        if role_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{min_role}' or higher required (your role: '{ctx.role}')",
            )
        return ctx

    # Give FastAPI a unique name so it doesn't collapse distinct dependencies
    _role_dep.__name__ = f"require_role_{min_role.replace('-', '_')}"
    return _role_dep


# ---------------------------------------------------------------------------
# require_agent
# ---------------------------------------------------------------------------

def require_agent(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    x_agent_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Agent:
    """Require agent authentication.

    Accepts (in priority order):
    - ``Authorization: Bearer <JWT>`` where the token carries ``type == "agent"``
    - ``X-Agent-Key: <agk_xxx>`` (legacy, backward-compatible)

    Returns the Agent ORM object.
    """
    # JWT path
    if credentials:
        payload = decode_access_token(credentials.credentials, db)
        if payload.get("type") != "agent":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agent token required",
            )

        agent = db.query(Agent).filter(
            Agent.agent_id == payload["sub"],
            Agent.is_active == True,
        ).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found or inactive",
            )
        return agent

    # Legacy header path
    if not x_agent_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Authorization: Bearer <token> or X-Agent-Key header.",
        )

    agent_id = verify_api_key(db, x_agent_key)
    if not agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or inactive agent key",
        )

    agent = db.query(Agent).filter(Agent.agent_id == agent_id, Agent.is_active == True).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or inactive",
        )
    return agent


# ---------------------------------------------------------------------------
# require_admin_or_agent
# ---------------------------------------------------------------------------

def require_admin_or_agent(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    x_admin_key: Optional[str] = Header(None),
    x_agent_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> tuple[Optional[str], Optional[Agent]]:
    """Accept either admin or agent authentication.

    Returns ``(admin_identifier, None)`` for admins,
    or ``(None, Agent)`` for agents.
    """
    # JWT path — dispatch by 'type' claim
    if credentials:
        payload = decode_access_token(credentials.credentials, db)
        token_type = payload.get("type")

        if token_type == "admin":
            return (payload["sub"], None)

        if token_type == "agent":
            agent = db.query(Agent).filter(
                Agent.agent_id == payload["sub"],
                Agent.is_active == True,
            ).first()
            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found or inactive",
                )
            return (None, agent)

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token must have type 'admin' or 'agent'",
        )

    # Legacy header path
    if x_admin_key and x_admin_key == settings.ADMIN_API_KEY:
        return (x_admin_key, None)

    if x_agent_key:
        agent_id = verify_api_key(db, x_agent_key)
        if agent_id:
            agent = db.query(Agent).filter(Agent.agent_id == agent_id, Agent.is_active == True).first()
            if agent:
                return (None, agent)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide Authorization: Bearer <token>, X-Admin-Key, or X-Agent-Key header.",
    )
