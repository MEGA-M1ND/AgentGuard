"""AdminUser model — named admin accounts with RBAC roles"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base


class AdminUser(Base):
    """An admin user with a specific role and optional team scope.

    The legacy ``ADMIN_API_KEY`` env var is implicitly treated as a ``super-admin``
    (role="super-admin", team=None) without a database row.  This table is for
    named human operators who need role-gated access (admin / auditor / approver).
    """

    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    admin_id = Column(String(50), unique=True, nullable=False, index=True)   # "adm_xxx"
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)              # SHA-256 of raw key
    key_prefix = Column(String(20), nullable=False, index=True)              # first 8 chars
    role = Column(String(20), nullable=False)                                # super-admin|admin|auditor|approver
    team = Column(String(255), nullable=True)                                # null = all teams
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
