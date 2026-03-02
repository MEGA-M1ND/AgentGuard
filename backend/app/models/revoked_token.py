"""RevokedToken model — jti blocklist for JWT revocation"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class RevokedToken(Base):
    """Stores revoked JWT token IDs (jti claims).

    When a token is revoked via POST /token/revoke its jti is inserted here.
    decode_access_token() checks this table on every authenticated request.
    expires_at mirrors the token's original exp so old rows can be pruned safely.
    """

    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(36), unique=True, nullable=False, index=True)
    revoked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)  # original token exp — for TTL cleanup
