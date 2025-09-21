from pydantic import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    secret_key: str = "your-secret-key-here"
    database_url: str = "sqlite:///./neologe.db"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"


settings = Settings()