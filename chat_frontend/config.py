from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BACKEND_URL:str = "http://search-rag-service:8001/v1"
    RECEIPT_URL:str = "http://receipt_fastapi_web:8000/api/v1/receipt"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore"
    )
settings = Settings()
