import os
from pathlib import Path

class Settings:
    HEARTBEAT_INTERVAL_SECONDS: float = float(os.getenv("HEARTBEAT_INTERVAL", "5.0"))
    HEARTBEAT_TIMEOUT_SECONDS: float = float(os.getenv("HEARTBEAT_TIMEOUT", "10.0"))
    NODE_OFFLINE_TIMEOUT_SECONDS: float = float(os.getenv("NODE_OFFLINE_TIMEOUT", "15.0"))
    MAX_TASK_RETRIES: int = int(os.getenv("MAX_TASK_RETRIES", "3"))
    RETRY_BACKOFF_BASE: float = float(os.getenv("RETRY_BACKOFF_BASE", "2.0"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "")
    CPU_HEALTH_THRESHOLD: float = float(os.getenv("CPU_HEALTH_THRESHOLD", "85.0"))
    RAM_HEALTH_THRESHOLD_MB: float = float(os.getenv("RAM_HEALTH_THRESHOLD_MB", "512.0"))
    CPU_CRITICAL_THRESHOLD: float = float(os.getenv("CPU_CRITICAL_THRESHOLD", "95.0"))
    RAM_CRITICAL_THRESHOLD_MB: float = float(os.getenv("RAM_CRITICAL_THRESHOLD_MB", "128.0"))

settings = Settings()


def get_default_database_path() -> str:
    """Return an absolute SQLite path inside the Track 4 project tree."""
    backend_dir = Path(__file__).resolve().parent
    default_path = backend_dir.parent / "node_registry.db"
    default_path.parent.mkdir(parents=True, exist_ok=True)
    return str(default_path)
