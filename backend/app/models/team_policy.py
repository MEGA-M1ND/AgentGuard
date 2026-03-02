"""TeamPolicy model — base-level policy rules shared across an entire team"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String

from app.database import Base


class TeamPolicy(Base):
    """Team-level base policy that is merged with each agent's own policy at enforcement time.

    Merge semantics:
    - ``deny_rules``             → team deny rules go **first** (team can override agent allow)
    - ``allow_rules``            → agent allow rules go **first** (agent can be more specific)
    - ``require_approval_rules`` → team approval rules appended after agent approval rules
    """

    __tablename__ = "team_policies"

    id = Column(Integer, primary_key=True)
    team = Column(String(255), unique=True, nullable=False, index=True)
    allow_rules = Column(JSON, default=list, nullable=False)
    deny_rules = Column(JSON, default=list, nullable=False)
    require_approval_rules = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
