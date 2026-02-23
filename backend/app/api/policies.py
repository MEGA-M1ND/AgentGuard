"""Policy management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.database import get_db
from app.models.agent import Agent
from app.models.policy import Policy
from app.schemas.policy import PolicyRequest, PolicyResponse
from app.utils.logger import logger

router = APIRouter(prefix="/agents/{agent_id}/policy", tags=["policies"])


@router.put("", response_model=PolicyResponse)
def set_policy(
    agent_id: str,
    policy_data: PolicyRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin)
):
    """
    Set or update policy for an agent (Admin only)

    Replaces existing policy if present
    """
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.agent_id == agent_id, Agent.is_active == True).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found or inactive"
        )

    # Convert Pydantic models to dicts
    allow_rules = [rule.model_dump() for rule in policy_data.allow]
    deny_rules = [rule.model_dump() for rule in policy_data.deny]

    # Check if policy exists
    policy = db.query(Policy).filter(Policy.agent_id == agent_id).first()

    if policy:
        # Update existing policy
        policy.allow_rules = allow_rules
        policy.deny_rules = deny_rules
    else:
        # Create new policy
        policy = Policy(
            agent_id=agent_id,
            allow_rules=allow_rules,
            deny_rules=deny_rules
        )
        db.add(policy)

    db.commit()
    db.refresh(policy)

    logger.info(
        f"Set policy for agent: {agent_id}",
        extra={"agent_id": agent_id, "action": "set_policy"}
    )

    return PolicyResponse(
        agent_id=policy.agent_id,
        allow=policy.allow_rules,
        deny=policy.deny_rules,
        created_at=policy.created_at,
        updated_at=policy.updated_at
    )


@router.get("", response_model=PolicyResponse)
def get_policy(
    agent_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin)
):
    """
    Get policy for an agent (Admin only)
    """
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    # Get policy
    policy = db.query(Policy).filter(Policy.agent_id == agent_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No policy found for agent {agent_id}"
        )

    return PolicyResponse(
        agent_id=policy.agent_id,
        allow=policy.allow_rules,
        deny=policy.deny_rules,
        created_at=policy.created_at,
        updated_at=policy.updated_at
    )
