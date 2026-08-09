"""Application settings managed via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for Dev Crew Backend."""
    
    # General
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # LLM Settings
    LLM_PROVIDER: str = "mock"  # "openai", "gemini", "mock"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    
    # Limits
    DEFAULT_MAX_RETRIES: int = 3
    DEFAULT_MAX_BUDGET_USD: float = 2.0
    DEFAULT_MAX_EXECUTION_SECONDS: float = 300.0
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/devcrew"
    
    # Docker Sandbox Settings
    SANDBOX_DOCKER_IMAGE: str = "python:3.11-slim"
    SANDBOX_MEMORY_LIMIT: str = "512m"
    SANDBOX_CPU_QUOTA: int = 50000  # 0.5 CPU
    SANDBOX_TIMEOUT_SECONDS: float = 30.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
