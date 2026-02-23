"""Agent management endpoints"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.database import get_db
from app.models.agent import Agent, AgentKey
from app.schemas.agent import AgentCreate, AgentResponse, AgentWithKey
from app.utils.auth import generate_agent_id, generate_api_key, get_key_prefix, hash_api_key
from app.utils.logger import logger

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentWithKey, status_code=status.HTTP_201_CREATED)
def create_agent(
    agent_data: AgentCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin)
):
    """
    Create a new agent with API key (Admin only)

    Returns agent details including API key (only shown once!)
    """
    # Generate agent ID
    agent_id = generate_agent_id()

    # Check if agent_id already exists (very unlikely but check anyway)
    existing = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent ID collision, please retry"
        )

    # Create agent
    agent = Agent(
        agent_id=agent_id,
        name=agent_data.name,
        owner_team=agent_data.owner_team,
        environment=agent_data.environment,
        is_active=True
    )
    db.add(agent)
    db.flush()  # Flush to get agent in DB before creating key

    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    key_prefix = get_key_prefix(api_key)

    # Create agent key
    agent_key = AgentKey(
        agent_id=agent_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        is_active=True
    )
    db.add(agent_key)
    db.commit()

    logger.info(f"Created agent: {agent_id}", extra={"agent_id": agent_id, "action": "create_agent"})

    return AgentWithKey(
        agent_id=agent.agent_id,
        name=agent.name,
        owner_team=agent.owner_team,
        environment=agent.environment,
        is_active=agent.is_active,
        created_at=agent.created_at,
        api_key=api_key  # Only shown once!
    )


@router.get("", response_model=List[AgentResponse])
def list_agents(
    skip: int = 0,
    limit: int = 100,
    environment: str = None,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin)
):
    """
    List all agents (Admin only)

    Query parameters:
    - skip: Number of records to skip
    - limit: Maximum number of records to return
    - environment: Filter by environment (dev/stage/prod)
    """
    query = db.query(Agent).filter(Agent.is_active == True)

    if environment:
        query = query.filter(Agent.environment == environment)

    agents = query.offset(skip).limit(limit).all()
    return agents


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin)
):
    """
    Get agent by ID (Admin only)
    """
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin)
):
    """
    Delete an agent permanently (Admin only)

    Removes agent, keys, policies, and logs from database
    """
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    # Delete related keys
    db.query(AgentKey).filter(AgentKey.agent_id == agent_id).delete()
    # Delete the agent (cascades will handle other relations if configured)
    db.delete(agent)
    db.commit()

    logger.info(f"Deleted agent: {agent_id}", extra={"agent_id": agent_id, "action": "delete_agent"})
    return None
