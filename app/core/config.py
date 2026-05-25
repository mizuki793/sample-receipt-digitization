#設定読み込み
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"
    GEMINI_API_KEY: str = "mock-key-for-local-testing"
    LLM_MODEL_NAME: str ="gemini/gemini-2.5-flash"
    DUCKDB_PATH: str = "/app/data/ocr_few_shots.duckdb"
    STORAGE_TYPE: str = "LOCAL"
    LOCAL_DATA_SET_BASE_DIR: str = "/app/data"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
settings = Settings()
