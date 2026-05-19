#設定読み込み
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"
    GOOGLE_API_KEY: str = "mock-key-for-local-testing"

    model_config = SettingsConfigDict(
        env_file="app/.env", 
        env_file_encoding="utf-8",
    )
settings = Settings()