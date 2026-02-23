"""FastAPI application entry point"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator

from app.api import agents, enforce, logs, policies, health
from app.config import settings
from app.utils.logger import logger, setup_logging

# Setup logging
setup_logging(settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("AgentGuard backend starting up", extra={
        "version": "0.1.0",
        "environment": settings.HOST,
        "log_level": settings.LOG_LEVEL,
        "rate_limiting": settings.RATE_LIMIT_ENABLED,
        "monitoring": settings.METRICS_ENABLED
    })
    yield
    # Shutdown
    logger.info("AgentGuard backend shutting down")


# Create FastAPI app
app = FastAPI(
    title="AgentGuard",
    description="Identity + Permissions + Audit Logs control plane for AI agents",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ===== Middleware Setup =====

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monitoring middleware
if settings.METRICS_ENABLED:
    from app.middleware.monitoring import MonitoringMiddleware
    app.add_middleware(MonitoringMiddleware)

    # Prometheus metrics
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health", "/health/ready", "/health/live"],
        inprogress_name="agentguard_requests_inprogress",
        inprogress_labels=True
    )
    instrumentator.instrument(app)
    instrumentator.expose(app, endpoint=settings.METRICS_PATH, include_in_schema=False)

# Rate limiting
if settings.RATE_LIMIT_ENABLED:
    from app.middleware.rate_limit import limiter, _rate_limit_exceeded_handler
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        """Handle rate limit exceeded errors"""
        logger.warning(
            "Rate limit exceeded",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client": request.client.host if request.client else "unknown"
            }
        )
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Please try again later.",
                "detail": str(exc.detail)
            }
        )

# ===== Route Setup =====

# Include routers
app.include_router(health.router)
app.include_router(agents.router)
app.include_router(policies.router)
app.include_router(enforce.router)
app.include_router(logs.router)


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "service": "AgentGuard",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
        "metrics": settings.METRICS_PATH if settings.METRICS_ENABLED else None
    }


# ===== Error Handlers =====

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for uncaught errors"""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please contact support."
        }
    )
