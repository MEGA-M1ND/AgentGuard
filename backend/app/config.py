"""Application configuration"""
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Database
    DATABASE_URL: str = "postgresql://agentguard:agentguard_password@localhost:5432/agentguard"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600  # Recycle connections after 1 hour

    # Authentication
    ADMIN_API_KEY: str = "admin-secret-key-change-in-production"

    # AI Policy Generation
    ANTHROPIC_API_KEY: Optional[str] = None

    # Webhooks (fire-and-forget notifications for approval events)
    WEBHOOK_URL: Optional[str] = None          # Any HTTPS URL; Slack incoming webhooks auto-detected
    WEBHOOK_SECRET: Optional[str] = None       # If set, signs body with HMAC-SHA256

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # Agent ID prefix
    AGENT_ID_PREFIX: str = "agt_"
    API_KEY_PREFIX: str = "agk_"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: List[str] = ["100/minute", "1000/hour"]
    RATE_LIMIT_STORAGE_URI: str = "memory://"  # Use redis:// for production

    # Monitoring
    METRICS_ENABLED: bool = True
    METRICS_PATH: str = "/metrics"

    # Performance
    REQUEST_TIMEOUT: int = 30  # seconds
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Security
    ENABLE_HTTPS: bool = False
    TRUST_PROXY_HEADERS: bool = False  # Set True if behind reverse proxy

    # JWT Authentication
    JWT_PRIVATE_KEY: Optional[str] = None   # RSA-2048 PEM string; auto-generated on startup if absent
    JWT_ALGORITHM: str = "RS256"             # RS256 (RSA) or ES256 (ECDSA)
    JWT_AGENT_EXPIRE_SECONDS: int = 3600    # 1 hour for agent tokens
    JWT_ADMIN_EXPIRE_SECONDS: int = 28800   # 8 hours for admin tokens
    JWT_KEY_ID: Optional[str] = None        # kid claim for key rotation tracking

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.LOG_LEVEL == "WARNING" or self.LOG_LEVEL == "ERROR"


settings = Settings()
