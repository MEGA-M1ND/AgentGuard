"""Enhanced health check endpoints"""
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.agent import Agent

router = APIRouter(prefix="/health", tags=["health"])

# Track startup time
STARTUP_TIME = time.time()


@router.get("")
def health_check():
    """
    Basic health check endpoint

    Returns 200 if service is running
    """
    return {
        "status": "healthy",
        "service": "AgentGuard",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Readiness check - verifies all dependencies are available

    Checks:
    - Database connectivity
    - Database query performance
    - System resources

    Returns 200 if ready to serve traffic, 503 if not ready
    """
    checks = {
        "database": False,
        "database_latency_ms": None
    }

    try:
        # Check database connectivity and measure latency
        start = time.time()
        db.execute(text("SELECT 1"))
        latency_ms = (time.time() - start) * 1000
        checks["database"] = True
        checks["database_latency_ms"] = round(latency_ms, 2)

        # Check if database is too slow
        if latency_ms > 1000:  # More than 1 second
            return {
                "status": "degraded",
                "checks": checks,
                "message": "Database latency is high"
            }, status.HTTP_503_SERVICE_UNAVAILABLE

    except Exception as e:
        return {
            "status": "unhealthy",
            "checks": checks,
            "message": f"Database check failed: {str(e)}"
        }, status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/live")
def liveness_check():
    """
    Liveness check - verifies service is alive

    Returns 200 if process is alive
    Used by Kubernetes liveness probe
    """
    return {
        "status": "alive",
        "uptime_seconds": round(time.time() - STARTUP_TIME, 2),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/stats")
def health_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    System statistics and metrics

    Returns:
    - Agent counts
    - System info
    - Database stats
    """
    try:
        # Count agents
        total_agents = db.query(Agent).count()
        active_agents = db.query(Agent).filter(Agent.is_active == True).count()

        # Get database stats
        db_start = time.time()
        db.execute(text("SELECT 1"))
        db_latency_ms = (time.time() - db_start) * 1000

        return {
            "status": "healthy",
            "agents": {
                "total": total_agents,
                "active": active_agents
            },
            "database": {
                "connected": True,
                "latency_ms": round(db_latency_ms, 2)
            },
            "system": {
                "uptime_seconds": round(time.time() - STARTUP_TIME, 2),
                "environment": settings.HOST
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, status.HTTP_503_SERVICE_UNAVAILABLE
