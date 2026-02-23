"""Rate limiting middleware for API protection"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from app.config import settings


def get_identifier(request: Request) -> str:
    """
    Get identifier for rate limiting based on authentication

    Priority:
    1. Agent ID (from agent key)
    2. Admin key
    3. IP address (for unauthenticated)
    """
    # Check for agent authentication
    agent_key = request.headers.get("x-agent-key")
    if agent_key and hasattr(request.state, "agent_id"):
        return f"agent:{request.state.agent_id}"

    # Check for admin authentication
    admin_key = request.headers.get("x-admin-key")
    if admin_key == settings.ADMIN_API_KEY:
        return "admin:authenticated"

    # Fall back to IP address for unauthenticated requests
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(
    key_func=get_identifier,
    default_limits=settings.RATE_LIMIT_DEFAULT,
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
    strategy="fixed-window"
)


# Rate limit configurations for different endpoints
RATE_LIMITS = {
    # Admin endpoints - more generous limits
    "admin_create": "50/hour",
    "admin_read": "200/hour",
    "admin_delete": "20/hour",

    # Agent endpoints - high volume expected
    "enforce": "1000/minute",
    "log_action": "1000/minute",
    "query_logs": "100/minute",

    # Public endpoints
    "health": "100/minute",
    "docs": "50/minute"
}


def get_rate_limit(endpoint: str) -> str:
    """Get rate limit for specific endpoint"""
    return RATE_LIMITS.get(endpoint, settings.RATE_LIMIT_DEFAULT[0])
