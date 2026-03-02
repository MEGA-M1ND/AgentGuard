"""Approval request management endpoints"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import AdminContext, get_admin_context, require_admin, require_role
from app.database import get_db
from app.models.approval import ApprovalRequest
from app.models.agent import Agent
from app.schemas.approval import ApprovalDecisionRequest, ApprovalListResponse, ApprovalRequestResponse
from app.utils.logger import logger
from app.utils.webhook import send_webhook

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _to_response(approval: ApprovalRequest, agent_name: Optional[str] = None) -> ApprovalRequestResponse:
    """Convert ORM model to response schema"""
    return ApprovalRequestResponse(
        approval_id=approval.approval_id,
        agent_id=approval.agent_id,
        agent_name=agent_name,
        status=approval.status,
        action=approval.action,
        resource=approval.resource,
        context=approval.context,
        created_at=approval.created_at,
        decision_at=approval.decision_at,
        decision_by=approval.decision_by,
        decision_reason=approval.decision_reason,
    )


@router.get("", response_model=ApprovalListResponse)
def list_approvals(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: pending, approved, denied"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    ctx: AdminContext = Depends(get_admin_context),
):
    """
    List approval requests (approver+ role).

    Filter by status=pending to see what needs action.
    Team-scoped callers only see requests belonging to agents in their team.
    """
    query = db.query(ApprovalRequest)

    # Team scoping: join through Agent to filter by owner_team
    if ctx.team:
        query = query.join(Agent, Agent.agent_id == ApprovalRequest.agent_id).filter(
            Agent.owner_team == ctx.team
        )

    if status_filter:
        if status_filter not in ("pending", "approved", "denied"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="status must be one of: pending, approved, denied"
            )
        query = query.filter(ApprovalRequest.status == status_filter)

    if agent_id:
        query = query.filter(ApprovalRequest.agent_id == agent_id)

    total = query.count()
    pending_count = db.query(ApprovalRequest).filter(ApprovalRequest.status == "pending").count()

    approvals = query.order_by(ApprovalRequest.created_at.desc()).offset(offset).limit(limit).all()

    # Join agent names for display
    agent_names: dict = {}
    agent_ids = list({a.agent_id for a in approvals})
    if agent_ids:
        agents = db.query(Agent).filter(Agent.agent_id.in_(agent_ids)).all()
        agent_names = {a.agent_id: a.name for a in agents}

    items = [_to_response(a, agent_names.get(a.agent_id)) for a in approvals]

    return ApprovalListResponse(items=items, total=total, pending_count=pending_count)


@router.get("/{approval_id}", response_model=ApprovalRequestResponse)
def get_approval(
    approval_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Get a single approval request by ID (Admin only)"""
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.approval_id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval {approval_id} not found")

    agent = db.query(Agent).filter(Agent.agent_id == approval.agent_id).first()
    return _to_response(approval, agent.name if agent else None)


@router.post("/{approval_id}/approve", response_model=ApprovalRequestResponse)
def approve_request(
    approval_id: str,
    decision: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    ctx: AdminContext = Depends(require_role("approver")),
):
    """
    Approve a pending approval request (approver+ role).

    The agent that created this request will receive 'approved' when it next polls.
    """
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.approval_id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval {approval_id} not found")

    if approval.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Approval is already {approval.status}"
        )

    approval.status = "approved"
    approval.decision_at = datetime.utcnow()
    approval.decision_by = ctx.sub
    approval.decision_reason = decision.reason or "Approved by admin"

    db.commit()
    db.refresh(approval)

    logger.info(
        f"Approval approved: {approval_id}",
        extra={"approval_id": approval_id, "agent_id": approval.agent_id, "action": approval.action}
    )

    agent = db.query(Agent).filter(Agent.agent_id == approval.agent_id).first()
    send_webhook("approval.approved", {
        "approval_id": approval_id,
        "agent_id": approval.agent_id,
        "agent_name": agent.name if agent else None,
        "action": approval.action,
        "resource": approval.resource,
        "decision_reason": approval.decision_reason,
        "decision_by": approval.decision_by,
    })
    return _to_response(approval, agent.name if agent else None)


@router.post("/{approval_id}/deny", response_model=ApprovalRequestResponse)
def deny_request(
    approval_id: str,
    decision: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    ctx: AdminContext = Depends(require_role("approver")),
):
    """
    Deny a pending approval request (approver+ role).

    The agent that created this request will receive 'denied' when it next polls.
    """
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.approval_id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval {approval_id} not found")

    if approval.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Approval is already {approval.status}"
        )

    approval.status = "denied"
    approval.decision_at = datetime.utcnow()
    approval.decision_by = ctx.sub
    approval.decision_reason = decision.reason or "Denied by admin"

    db.commit()
    db.refresh(approval)

    logger.info(
        f"Approval denied: {approval_id}",
        extra={"approval_id": approval_id, "agent_id": approval.agent_id, "action": approval.action}
    )

    agent = db.query(Agent).filter(Agent.agent_id == approval.agent_id).first()
    send_webhook("approval.denied", {
        "approval_id": approval_id,
        "agent_id": approval.agent_id,
        "agent_name": agent.name if agent else None,
        "action": approval.action,
        "resource": approval.resource,
        "decision_reason": approval.decision_reason,
        "decision_by": approval.decision_by,
    })
    return _to_response(approval, agent.name if agent else None)


@router.delete("/{approval_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_approval(
    approval_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """
    Cancel and delete a pending approval request (Admin only)

    Only pending requests can be cancelled.
    """
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.approval_id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval {approval_id} not found")

    if approval.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only pending approvals can be cancelled (current status: {approval.status})"
        )

    db.delete(approval)
    db.commit()

    logger.info(f"Approval cancelled: {approval_id}")
