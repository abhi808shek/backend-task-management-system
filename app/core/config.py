import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Task Management API"
    VERSION: str = "1.0.0"

    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "taskdb")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret")
    REFRESH_SECRET_KEY: str = os.getenv("REFRESH_SECRET_KEY", "change-this-refresh-secret")

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


settings = Settings()