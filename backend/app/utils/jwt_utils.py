"""JWT utilities — RS256 keypair management, token signing, verification, and JWKS"""
import base64
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.utils.logger import logger

# ---------------------------------------------------------------------------
# Keypair management
# ---------------------------------------------------------------------------

_private_key: Any = None   # cryptography RSAPrivateKey object
_public_key: Any = None    # cryptography RSAPublicKey object


def _load_keypair() -> None:
    """Load or auto-generate the RSA keypair.

    Reads JWT_PRIVATE_KEY from settings (PEM string).
    If absent, generates a fresh RSA-2048 keypair, logs the private key PEM
    so the operator can paste it into .env to make it persistent across restarts.
    """
    global _private_key, _public_key

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend

    if settings.JWT_PRIVATE_KEY:
        pem = settings.JWT_PRIVATE_KEY.encode()
        _private_key = serialization.load_pem_private_key(pem, password=None, backend=default_backend())
        _public_key = _private_key.public_key()
        logger.info("JWT keypair loaded from JWT_PRIVATE_KEY setting")
    else:
        _private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )
        _public_key = _private_key.public_key()

        pem_str = _private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

        logger.warning(
            "JWT_PRIVATE_KEY not set — auto-generated RSA-2048 keypair for this session. "
            "All tokens will be invalidated on restart. "
            "Set the following in backend/.env to persist the key:\n"
            f"JWT_PRIVATE_KEY=\"{pem_str.strip()}\""
        )


def get_private_key() -> Any:
    """Return the loaded private key, initialising on first call."""
    if _private_key is None:
        _load_keypair()
    return _private_key


def get_public_key() -> Any:
    """Return the loaded public key, initialising on first call."""
    if _public_key is None:
        _load_keypair()
    return _public_key


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------

def create_access_token(subject: str, token_type: str, extra_claims: Dict[str, Any]) -> str:
    """Sign and return a JWT access token.

    Args:
        subject:      Value for the 'sub' claim (agent_id or 'admin').
        token_type:   'agent' or 'admin' — stored as 'type' claim and used
                      by deps.py to gate access.
        extra_claims: Additional claims to embed (env, team, etc.).

    Returns:
        Signed JWT string.
    """
    expire_seconds = (
        settings.JWT_AGENT_EXPIRE_SECONDS
        if token_type == "agent"
        else settings.JWT_ADMIN_EXPIRE_SECONDS
    )

    now = int(datetime.now(timezone.utc).timestamp())

    payload: Dict[str, Any] = {
        "sub": subject,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + expire_seconds,
        "type": token_type,
        **extra_claims,
    }

    if settings.JWT_KEY_ID:
        payload["kid"] = settings.JWT_KEY_ID

    private_key = get_private_key()
    token = jwt.encode(payload, private_key, algorithm=settings.JWT_ALGORITHM)
    return token


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------

def decode_access_token(token: str, db: Session) -> Dict[str, Any]:
    """Verify a JWT and return its payload.

    Checks:
    1. Signature validity (RS256 with our public key)
    2. Token not expired (jose handles 'exp')
    3. jti not in the revoked_tokens table

    Raises:
        HTTPException 401: on any verification failure.

    Returns:
        Decoded payload dict.
    """
    from app.models.revoked_token import RevokedToken

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        public_key = get_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        logger.debug(f"JWT decode failed: {exc}")
        raise credentials_exception

    jti = payload.get("jti")
    if not jti:
        raise credentials_exception

    # Check revocation blocklist
    revoked = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
    if revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


# ---------------------------------------------------------------------------
# JWKS
# ---------------------------------------------------------------------------

def get_jwks() -> Dict[str, Any]:
    """Return the public key in JWKS format for third-party token verification."""
    public_key = get_public_key()

    # Only RSA keys are supported; the key is already the public half
    try:
        pub_numbers = public_key.public_numbers()
    except AttributeError:
        raise NotImplementedError("JWKS export is only implemented for RSA public keys")

    def _to_base64url(n: int) -> str:
        byte_length = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(byte_length, "big")).rstrip(b"=").decode()

    key_entry: Dict[str, Any] = {
        "kty": "RSA",
        "use": "sig",
        "alg": settings.JWT_ALGORITHM,
        "n": _to_base64url(pub_numbers.n),
        "e": _to_base64url(pub_numbers.e),
    }

    if settings.JWT_KEY_ID:
        key_entry["kid"] = settings.JWT_KEY_ID

    return {"keys": [key_entry]}
