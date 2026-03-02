"""Audit log endpoints"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin_or_agent, require_agent
from app.database import get_db
from app.models.agent import Agent
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate, AuditLogResponse, ChainVerifyResponse
from app.utils import chain as chain_utils
from app.utils.logger import logger

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post("", response_model=AuditLogResponse, status_code=201)
def create_log(
    log_data: AuditLogCreate,
    agent: Agent = Depends(require_agent),
    db: Session = Depends(get_db)
):
    """
    Submit an audit log entry (Agent auth).

    Logs are append-only and cannot be modified or deleted.
    Each entry is linked to the previous one via a SHA-256 hash stored in
    ``previous_hash``, forming a tamper-evident chain verifiable at GET /logs/verify.
    """
    # ------------------------------------------------------------------
    # Compute chain hash before inserting
    # ------------------------------------------------------------------
    # Lock the latest row for this agent to prevent a concurrent insert
    # from computing the same previous_hash (PostgreSQL FOR UPDATE;
    # SQLite serialises writes via its WAL transaction lock).
    prev_log = (
        db.query(AuditLog)
        .filter(AuditLog.agent_id == agent.agent_id)
        .order_by(AuditLog.id.desc())
        .with_for_update()
        .first()
    )

    # We need the new log_id before we can compute the hash, so generate it now
    import uuid
    new_log_id = str(uuid.uuid4())

    if prev_log is None:
        previous_hash = chain_utils.genesis_hash()
    else:
        previous_hash = chain_utils.compute_hash(
            prev_log_id=prev_log.log_id,
            prev_timestamp=prev_log.timestamp,
            current_log_id=new_log_id,
            current_action=log_data.action,
        )

    audit_log = AuditLog(
        log_id=new_log_id,
        agent_id=agent.agent_id,
        action=log_data.action,
        resource=log_data.resource,
        context=log_data.context,
        allowed=log_data.allowed,
        result=log_data.result,
        log_metadata=log_data.metadata,
        request_id=log_data.request_id,
        previous_hash=previous_hash,
    )
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)

    logger.info(
        f"Audit log created: {audit_log.log_id}",
        extra={
            "agent_id": agent.agent_id,
            "log_id": str(audit_log.log_id),
            "action": log_data.action,
        }
    )

    return audit_log


@router.get("/verify", response_model=ChainVerifyResponse)
def verify_chain(
    agent_id: Optional[str] = Query(None, description="Agent ID to verify (required for agent auth)"),
    db: Session = Depends(get_db),
    auth: tuple = Depends(require_admin_or_agent),
):
    """
    Verify the cryptographic audit log chain for an agent (Admin or Agent auth).

    Walks all log entries in insertion order and recomputes each SHA-256 hash.
    Returns whether the chain is intact and, if not, the log_id of the first
    broken link.

    - Admin: pass ``agent_id`` query parameter to specify which agent to verify.
    - Agent: always verifies their own chain (``agent_id`` param ignored).
    """
    admin_key, agent_obj = auth

    if agent_obj:
        target_agent_id = agent_obj.agent_id
    else:
        if not agent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="agent_id query parameter is required for admin auth",
            )
        target_agent_id = agent_id

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.agent_id == target_agent_id)
        .order_by(AuditLog.id.asc())
        .all()
    )

    if not logs:
        return ChainVerifyResponse(
            agent_id=target_agent_id,
            valid=True,
            total_entries=0,
            broken_at=None,
        )

    # Walk the chain — first entry must have genesis_hash as its previous_hash
    for i, entry in enumerate(logs):
        if i == 0:
            expected = chain_utils.genesis_hash()
        else:
            prev = logs[i - 1]
            expected = chain_utils.compute_hash(
                prev_log_id=prev.log_id,
                prev_timestamp=prev.timestamp,
                current_log_id=entry.log_id,
                current_action=entry.action,
            )

        if entry.previous_hash != expected:
            return ChainVerifyResponse(
                agent_id=target_agent_id,
                valid=False,
                total_entries=len(logs),
                broken_at=entry.log_id,
            )

    return ChainVerifyResponse(
        agent_id=target_agent_id,
        valid=True,
        total_entries=len(logs),
        broken_at=None,
    )


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
    Query audit logs with filters (Admin or Agent auth).

    - Admin can query all logs
    - Agent can only query their own logs
    """
    admin_key, agent = auth

    query = db.query(AuditLog)

    if agent:
        query = query.filter(AuditLog.agent_id == agent.agent_id)
    elif agent_id:
        query = query.filter(AuditLog.agent_id == agent_id)

    if action:
        query = query.filter(AuditLog.action == action)
    if allowed is not None:
        query = query.filter(AuditLog.allowed == allowed)
    if start_time:
        query = query.filter(AuditLog.timestamp >= start_time)
    if end_time:
        query = query.filter(AuditLog.timestamp <= end_time)

    query = query.order_by(AuditLog.timestamp.desc())
    logs = query.offset(offset).limit(limit).all()

    return logs
