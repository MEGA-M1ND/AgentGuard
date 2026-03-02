"""Token issuance, revocation, and JWKS endpoints"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.admin_user import AdminUser
from app.models.agent import Agent, AgentKey
from app.models.revoked_token import RevokedToken
from app.utils.auth import hash_api_key
from app.utils.jwt_utils import create_access_token, decode_access_token, get_jwks
from app.utils.logger import logger

router = APIRouter(tags=["authentication"])

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TokenRequest(BaseModel):
    agent_key: Optional[str] = None   # agk_xxx — for agent token exchange
    admin_key: Optional[str] = None   # static admin key — for admin token exchange


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int   # seconds until expiry


class RevokeResponse(BaseModel):
    revoked: bool


# ---------------------------------------------------------------------------
# POST /token
# ---------------------------------------------------------------------------

@router.post("/token", response_model=TokenResponse)
def issue_token(
    request: TokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange a static credential for a signed JWT access token.

    Provide exactly one of:
    - **agent_key**: an `agk_` prefixed key obtained when creating an agent.
    - **admin_key**: the `ADMIN_API_KEY` configured in the server environment.

    The returned JWT should be used as `Authorization: Bearer <token>` on all
    subsequent API calls. Agent tokens expire after 1 hour; admin tokens after 8 hours.
    Obtain a fresh token before expiry (or on a 401 response) by calling this endpoint again.
    """
    if request.agent_key:
        return _issue_agent_token(request.agent_key, db)

    if request.admin_key:
        return _issue_admin_token(request.admin_key, db)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide either 'agent_key' or 'admin_key'",
    )


def _issue_agent_token(agent_key: str, db: Session) -> TokenResponse:
    key_hash = hash_api_key(agent_key)
    agent_key_record = db.query(AgentKey).filter(
        AgentKey.key_hash == key_hash,
        AgentKey.is_active == True,
    ).first()

    if not agent_key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive agent key",
        )

    agent = db.query(Agent).filter(
        Agent.agent_id == agent_key_record.agent_id,
        Agent.is_active == True,
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent not found or inactive",
        )

    token = create_access_token(
        subject=agent.agent_id,
        token_type="agent",
        extra_claims={
            "env": agent.environment,
            "team": agent.owner_team,
        },
    )

    logger.info(
        f"Issued agent JWT for {agent.agent_id}",
        extra={"agent_id": agent.agent_id, "action": "issue_token"},
    )

    return TokenResponse(
        access_token=token,
        expires_in=settings.JWT_AGENT_EXPIRE_SECONDS,
    )


def _issue_admin_token(admin_key: str, db: Session) -> TokenResponse:
    """Exchange an admin key for a role-scoped JWT.

    Lookup order:
    1. ``AdminUser`` table — named users with specific roles (admin/auditor/approver).
    2. ``ADMIN_API_KEY`` env var — legacy bootstrap key → implicit super-admin.
    """
    import hashlib as _hl
    key_hash = _hl.sha256(admin_key.encode()).hexdigest()

    admin_user = db.query(AdminUser).filter(
        AdminUser.key_hash == key_hash,
        AdminUser.is_active == True,
    ).first()

    if admin_user:
        extra: dict = {"role": admin_user.role}
        if admin_user.team:
            extra["team"] = admin_user.team
        token = create_access_token(
            subject=admin_user.admin_id,
            token_type="admin",
            extra_claims=extra,
        )
        logger.info(
            f"Issued admin JWT for {admin_user.admin_id} (role={admin_user.role})",
            extra={"admin_id": admin_user.admin_id, "role": admin_user.role, "action": "issue_token"},
        )
        return TokenResponse(access_token=token, expires_in=settings.JWT_ADMIN_EXPIRE_SECONDS)

    # Fallback: legacy ADMIN_API_KEY → super-admin
    if admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
        )

    token = create_access_token(
        subject="admin",
        token_type="admin",
        extra_claims={"role": "super-admin"},
    )

    logger.info("Issued super-admin JWT (legacy ADMIN_API_KEY)", extra={"action": "issue_token"})

    return TokenResponse(
        access_token=token,
        expires_in=settings.JWT_ADMIN_EXPIRE_SECONDS,
    )


# ---------------------------------------------------------------------------
# POST /token/revoke
# ---------------------------------------------------------------------------

@router.post("/token/revoke", response_model=RevokeResponse)
def revoke_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> RevokeResponse:
    """Revoke a JWT token by adding its jti to the blocklist.

    Requires a valid `Authorization: Bearer <token>` header.
    The provided token (typically the caller's own current token) is immediately
    invalidated. Any subsequent request with the same token returns 401.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization: Bearer <token> header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials, db)

    jti = payload["jti"]
    exp_timestamp = payload["exp"]
    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc).replace(tzinfo=None)

    revoked = RevokedToken(jti=jti, expires_at=expires_at)
    db.add(revoked)
    db.commit()

    logger.info(
        f"Revoked JWT jti={jti}",
        extra={"jti": jti, "sub": payload.get("sub"), "action": "revoke_token"},
    )

    return RevokeResponse(revoked=True)


# ---------------------------------------------------------------------------
# GET /.well-known/jwks.json
# ---------------------------------------------------------------------------

@router.get("/.well-known/jwks.json", response_model=Dict[str, Any])
def jwks() -> Dict[str, Any]:
    """Return the public key set (JWKS) for verifying AgentGuard JWTs.

    This endpoint is unauthenticated and intended for third-party systems that
    need to verify tokens issued by this server. The public key corresponds to
    the RS256 private key used to sign all access tokens.
    """
    return get_jwks()
