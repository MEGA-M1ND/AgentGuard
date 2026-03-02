"""Compliance reporting endpoints"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import AdminContext, require_role
from app.database import get_db
from app.models.agent import Agent
from app.models.approval import ApprovalRequest
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
def get_summary(
    days: int = Query(30, ge=1, le=365, description="Look-back window in days"),
    db: Session = Depends(get_db),
    ctx: AdminContext = Depends(require_role("auditor")),
):
    """
    Generate a compliance summary report (auditor+ role).

    Team-scoped callers only see data for agents in their team.

    Returns:
      - overview: total actions, allow/deny counts and rates
      - approvals: total, pending, approved, denied counts and approval rate
      - top_agents: top 10 agents by activity with allow/deny breakdown
      - top_denied_actions: top 10 most-blocked actions
      - daily_breakdown: per-day totals for the last min(days, 14) days
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Build a subquery of in-scope agent_ids for team-scoped callers
    if ctx.team:
        scoped_agent_ids = [
            row[0] for row in db.query(Agent.agent_id).filter(Agent.owner_team == ctx.team).all()
        ]
    else:
        scoped_agent_ids = None  # no filter

    def _log_q():
        q = db.query(AuditLog).filter(AuditLog.timestamp >= cutoff)
        if scoped_agent_ids is not None:
            q = q.filter(AuditLog.agent_id.in_(scoped_agent_ids))
        return q

    def _approval_q():
        q = db.query(ApprovalRequest)
        if scoped_agent_ids is not None:
            q = q.filter(ApprovalRequest.agent_id.in_(scoped_agent_ids))
        return q

    # ── Overall log stats ─────────────────────────────────────────────────────
    total_logs = _log_q().count()
    allowed_logs = _log_q().filter(AuditLog.allowed == True).count()  # noqa: E712
    denied_logs = total_logs - allowed_logs

    # ── Approval stats ────────────────────────────────────────────────────────
    total_approvals = _approval_q().filter(ApprovalRequest.created_at >= cutoff).count()
    pending_approvals = _approval_q().filter(ApprovalRequest.status == "pending").count()
    approved_count = _approval_q().filter(
        ApprovalRequest.created_at >= cutoff,
        ApprovalRequest.status == "approved",
    ).count()
    denied_approvals_count = _approval_q().filter(
        ApprovalRequest.created_at >= cutoff,
        ApprovalRequest.status == "denied",
    ).count()
    decided = approved_count + denied_approvals_count
    approval_rate = round(approved_count / decided * 100, 1) if decided > 0 else 0

    # ── Top agents by activity ────────────────────────────────────────────────
    top_agents_rows = (
        _log_q()
        .with_entities(AuditLog.agent_id, func.count(AuditLog.id).label("total"))
        .group_by(AuditLog.agent_id)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
        .all()
    )
    agent_ids = [row[0] for row in top_agents_rows]
    agents_map = {}
    if agent_ids:
        agents = db.query(Agent).filter(Agent.agent_id.in_(agent_ids)).all()
        agents_map = {a.agent_id: a.name for a in agents}

    top_agents = []
    for agent_id, total in top_agents_rows:
        agent_allowed = _log_q().filter(
            AuditLog.agent_id == agent_id,
            AuditLog.allowed == True,  # noqa: E712
        ).count()
        top_agents.append({
            "agent_id": agent_id,
            "agent_name": agents_map.get(agent_id, "Unknown"),
            "total_actions": total,
            "allowed": agent_allowed,
            "denied": total - agent_allowed,
        })

    # ── Top denied actions ────────────────────────────────────────────────────
    top_denied_rows = (
        _log_q()
        .with_entities(AuditLog.action, func.count(AuditLog.id).label("count"))
        .filter(AuditLog.allowed == False)  # noqa: E712
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
        .all()
    )
    top_denied_actions = [{"action": row[0], "count": row[1]} for row in top_denied_rows]

    # ── Daily breakdown (capped at 14 days for chart readability) ─────────────
    chart_days = min(days, 14)
    daily_breakdown = []
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(chart_days - 1, -1, -1):
        day_start = today_start - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_total = _log_q().filter(
            AuditLog.timestamp >= day_start,
            AuditLog.timestamp < day_end,
        ).count()
        day_allowed = _log_q().filter(
            AuditLog.timestamp >= day_start,
            AuditLog.timestamp < day_end,
            AuditLog.allowed == True,  # noqa: E712
        ).count()
        daily_breakdown.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "total": day_total,
            "allowed": day_allowed,
            "denied": day_total - day_allowed,
        })

    return {
        "period_days": days,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "overview": {
            "total_actions": total_logs,
            "allowed": allowed_logs,
            "denied": denied_logs,
            "allow_rate": round(allowed_logs / total_logs * 100, 1) if total_logs > 0 else 0,
            "deny_rate": round(denied_logs / total_logs * 100, 1) if total_logs > 0 else 0,
        },
        "approvals": {
            "total": total_approvals,
            "pending": pending_approvals,
            "approved": approved_count,
            "denied": denied_approvals_count,
            "approval_rate": approval_rate,
        },
        "top_agents": top_agents,
        "top_denied_actions": top_denied_actions,
        "daily_breakdown": daily_breakdown,
    }
