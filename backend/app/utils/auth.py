"""Authentication utilities"""
import hashlib
import secrets
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent import AgentKey


def generate_api_key() -> str:
    """Generate a secure random API key"""
    random_part = secrets.token_urlsafe(32)
    return f"{settings.API_KEY_PREFIX}{random_part}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA256"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_key_prefix(api_key: str) -> str:
    """Extract prefix from API key for identification"""
    return api_key[:12] if len(api_key) >= 12 else api_key


def verify_api_key(db: Session, api_key: str) -> Optional[str]:
    """
    Verify API key and return agent_id if valid

    Args:
        db: Database session
        api_key: Raw API key to verify

    Returns:
        agent_id if valid, None otherwise
    """
    key_hash = hash_api_key(api_key)

    agent_key = db.query(AgentKey).filter(
        AgentKey.key_hash == key_hash,
        AgentKey.is_active == True
    ).first()

    if agent_key:
        return agent_key.agent_id
    return None


def generate_agent_id() -> str:
    """Generate a unique agent ID"""
    random_part = secrets.token_urlsafe(12)
    return f"{settings.AGENT_ID_PREFIX}{random_part}"
