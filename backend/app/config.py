from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./chat_app.db"

    # JWT Settings
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Groq API
    groq_api_key: str = ""
    
    # Tools
    tools_enabled: bool = True
    openweathermap_api_key: str = ""
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = True
    models_cache_ttl: int = 3600  # Cache models for 1 hour (in seconds)

    # IP Blocking
    ip_block_attempts: int = 3  # Number of attempts before blocking
    ip_block_window: int = 3600  # Time window in seconds (1 hour)

    # Environment
    environment: str = "development"
    
    # Logging
    log_dir: str = "logs"
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
