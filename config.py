from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "Document Secure Sharing API"
    DATABASE_URL: str = "mysql+pymysql://root:change_me@127.0.0.1:3306/document_sharing_db"
    JWT_SECRET_KEY: str = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    STORAGE_DIR: str = "storage"
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: str = ".pdf,.txt,.png,.jpg,.jpeg,.docx,.xlsx,.csv"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_extensions_set(self):
        return {x.strip().lower() for x in self.ALLOWED_EXTENSIONS.split(",") if x.strip()}

settings = Settings()
