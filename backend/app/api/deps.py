"""API dependencies for authentication and authorization"""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.agent import Agent
from app.utils.auth import verify_api_key


def require_admin(x_admin_key: Optional[str] = Header(None)) -> str:
    """
    Dependency to require admin authentication

    Args:
        x_admin_key: Admin API key from header

    Returns:
        Admin key if valid

    Raises:
        HTTPException: If admin key is missing or invalid
    """
    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required. Provide X-Admin-Key header."
        )

    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key"
        )

    return x_admin_key


def require_agent(
    x_agent_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Agent:
    """
    Dependency to require agent authentication

    Args:
        x_agent_key: Agent API key from header
        db: Database session

    Returns:
        Agent object if valid

    Raises:
        HTTPException: If agent key is missing or invalid
    """
    if not x_agent_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent authentication required. Provide X-Agent-Key header."
        )

    agent_id = verify_api_key(db, x_agent_key)
    if not agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or inactive agent key"
        )

    # Get agent
    agent = db.query(Agent).filter(Agent.agent_id == agent_id, Agent.is_active == True).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or inactive"
        )

    return agent


def require_admin_or_agent(
    x_admin_key: Optional[str] = Header(None),
    x_agent_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> tuple[Optional[str], Optional[Agent]]:
    """
    Dependency that accepts either admin or agent authentication

    Returns:
        Tuple of (admin_key or None, agent or None)
    """
    # Try admin first
    if x_admin_key and x_admin_key == settings.ADMIN_API_KEY:
        return (x_admin_key, None)

    # Try agent
    if x_agent_key:
        agent_id = verify_api_key(db, x_agent_key)
        if agent_id:
            agent = db.query(Agent).filter(Agent.agent_id == agent_id, Agent.is_active == True).first()
            if agent:
                return (None, agent)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide X-Admin-Key or X-Agent-Key header."
    )
