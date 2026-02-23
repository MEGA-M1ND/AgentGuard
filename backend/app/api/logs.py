"""Audit log endpoints"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin_or_agent, require_agent
from app.database import get_db
from app.models.agent import Agent
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate, AuditLogResponse
from app.utils.logger import logger

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post("", response_model=AuditLogResponse, status_code=201)
def create_log(
    log_data: AuditLogCreate,
    agent: Agent = Depends(require_agent),
    db: Session = Depends(get_db)
):
    """
    Submit an audit log entry (Agent auth)

    Logs are append-only and cannot be modified or deleted
    """
    # Create audit log
    audit_log = AuditLog(
        agent_id=agent.agent_id,
        action=log_data.action,
        resource=log_data.resource,
        context=log_data.context,
        allowed=log_data.allowed,
        result=log_data.result,
        log_metadata=log_data.metadata,
        request_id=log_data.request_id
    )
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)

    logger.info(
        f"Audit log created: {audit_log.log_id}",
        extra={
            "agent_id": agent.agent_id,
            "log_id": str(audit_log.log_id),
            "action": log_data.action
        }
    )

    return audit_log


@router.get("", response_model=List[AuditLogResponse])
def query_logs(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    allowed: Optional[bool] = Query(None, description="Filter by allowed status"),
    start_time: Optional[datetime] = Query(None, description="Filter by start time (ISO 8601)"),
    end_time: Optional[datetime] = Query(None, description="Filter by end time (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    db: Session = Depends(get_db),
    auth: tuple = Depends(require_admin_or_agent)
):
    """
    Query audit logs with filters (Admin or Agent auth)

    - Admin can query all logs
    - Agent can only query their own logs

    Query parameters:
    - agent_id: Filter by agent ID (ignored for agent auth)
    - action: Filter by action
    - allowed: Filter by allowed status (true/false)
    - start_time: Filter logs after this time
    - end_time: Filter logs before this time
    - limit: Maximum number of results (1-1000)
    - offset: Skip this many results
    """
    admin_key, agent = auth

    # Build query
    query = db.query(AuditLog)

    # If authenticated as agent, only show their logs
    if agent:
        query = query.filter(AuditLog.agent_id == agent.agent_id)
    elif agent_id:
        # Admin can filter by agent_id
        query = query.filter(AuditLog.agent_id == agent_id)

    # Apply filters
    if action:
        query = query.filter(AuditLog.action == action)
    if allowed is not None:
        query = query.filter(AuditLog.allowed == allowed)
    if start_time:
        query = query.filter(AuditLog.timestamp >= start_time)
    if end_time:
        query = query.filter(AuditLog.timestamp <= end_time)

    # Order by timestamp descending (most recent first)
    query = query.order_by(AuditLog.timestamp.desc())

    # Apply pagination
    logs = query.offset(offset).limit(limit).all()

    return logs
