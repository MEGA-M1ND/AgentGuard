"""Monitoring and observability middleware"""
import time
from typing import Callable
from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logger import logger


# ===== Prometheus Metrics =====

# Request metrics
http_requests_total = Counter(
    "agentguard_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "agentguard_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)

# Agent-specific metrics
agent_enforcement_total = Counter(
    "agentguard_enforcement_total",
    "Total enforcement checks",
    ["agent_id", "action", "allowed"]
)

agent_logs_total = Counter(
    "agentguard_logs_total",
    "Total audit logs submitted",
    ["agent_id", "action", "result"]
)

policy_evaluations_total = Counter(
    "agentguard_policy_evaluations_total",
    "Total policy evaluations",
    ["outcome"]  # allowed, denied_by_rule, denied_no_policy, denied_default
)

# System metrics
active_agents_gauge = Gauge(
    "agentguard_active_agents",
    "Number of active agents"
)

database_connections_gauge = Gauge(
    "agentguard_database_connections",
    "Number of active database connections"
)

# Error metrics
http_errors_total = Counter(
    "agentguard_http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "status"]
)

authentication_failures_total = Counter(
    "agentguard_authentication_failures_total",
    "Total authentication failures",
    ["type"]  # admin, agent
)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring and metrics collection"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics"""
        start_time = time.time()

        # Extract request details
        method = request.method
        endpoint = request.url.path

        # Add request ID for tracing
        request_id = request.headers.get("x-request-id", f"req_{int(time.time() * 1000)}")
        request.state.request_id = request_id

        try:
            # Process request
            response = await call_next(request)
            status = response.status_code

            # Record metrics
            duration = time.time() - start_time
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            # Log slow requests
            if duration > 1.0:  # More than 1 second
                logger.warning(
                    f"Slow request detected: {method} {endpoint}",
                    extra={
                        "request_id": request_id,
                        "method": method,
                        "endpoint": endpoint,
                        "duration": duration,
                        "status": status
                    }
                )

            # Track errors
            if status >= 400:
                http_errors_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status=status
                ).inc()

            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"

            return response

        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            http_errors_total.labels(
                method=method,
                endpoint=endpoint,
                status=500
            ).inc()

            logger.error(
                f"Request failed: {method} {endpoint}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "endpoint": endpoint,
                    "duration": duration,
                    "error": str(e)
                },
                exc_info=True
            )
            raise


def record_enforcement_metric(agent_id: str, action: str, allowed: bool):
    """Record enforcement check metric"""
    agent_enforcement_total.labels(
        agent_id=agent_id,
        action=action,
        allowed=str(allowed)
    ).inc()


def record_log_metric(agent_id: str, action: str, result: str):
    """Record audit log submission metric"""
    agent_logs_total.labels(
        agent_id=agent_id,
        action=action,
        result=result
    ).inc()


def record_policy_evaluation(outcome: str):
    """Record policy evaluation outcome"""
    policy_evaluations_total.labels(outcome=outcome).inc()


def record_auth_failure(auth_type: str):
    """Record authentication failure"""
    authentication_failures_total.labels(type=auth_type).inc()
