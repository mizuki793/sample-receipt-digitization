from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    CHROMA_DATA_DIR: str = "./chroma_data"
    GEMINI_API_KEY: str = ""
    EMBEDDING_MODEL_NAME: str = "models/gemini-embedding-001"
    CHROMA_COLLECTION_NAME: str = "receipt_items"

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
    )

settings = Settings()
