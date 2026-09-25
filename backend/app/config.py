from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    # App
    APP_NAME: str = 'PharmaPredict API'
    APP_VERSION: str = '0.1.0'
    ENVIRONMENT: Literal['development', 'staging', 'production'] = 'development'
    DEBUG: bool = True
    LOG_LEVEL: str = 'INFO'
    LOG_FORMAT: Literal['json', 'console'] = 'console'

    # API
    API_PREFIX: str = '/api/v1'
    HOST: str = '0.0.0.0'
    PORT: int = 8000
    WORKERS: int = 1

    # Database
    POSTGRES_HOST: str = 'localhost'
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = 'pharmapredict'
    POSTGRES_PASSWORD: str = 'pharmapredict_dev'
    POSTGRES_DB: str = 'pharmapredict'
    POSTGRES_SCHEMA: str = 'public'
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    @computed_field
    @property
    def DATABASE_URL(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme='postgresql+asyncpg',
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @computed_field
    @property
    def DATABASE_URL_SYNC(self) -> str:
        return f'postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}'

    # Redis
    REDIS_HOST: str = 'localhost'
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_TLS: bool = False

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        scheme = 'rediss' if self.REDIS_TLS else 'redis'
        auth = f':{self.REDIS_PASSWORD}@' if self.REDIS_PASSWORD else ''
        return f'{scheme}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}'

    # Auth
    SECRET_KEY: str = 'dev-secret-key-change-in-production-min-32-chars'
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    # CORS
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ['http://localhost:3000', 'http://localhost:3001']
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = Field(default_factory=lambda: ['*'])
    CORS_ALLOW_HEADERS: list[str] = Field(default_factory=lambda: ['*'])

    # MLflow
    MLFLOW_TRACKING_URI: str = 'http://localhost:5001'
    MLFLOW_S3_ENDPOINT_URL: str = 'http://localhost:9000'
    MLFLOW_ARTIFACT_BUCKET: str = 'mlflow-artifacts'
    AWS_ACCESS_KEY_ID: str = 'minioadmin'
    AWS_SECRET_ACCESS_KEY: str = 'minioadmin'
    AWS_DEFAULT_REGION: str = 'us-east-1'

    # Celery
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 30 * 60
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1
    CELERY_BEAT_SCHEDULE: dict = Field(default_factory=dict)

    @computed_field
    @property
    def CELERY_BROKER_URL_COMPUTED(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @computed_field
    @property
    def CELERY_RESULT_BACKEND_COMPUTED(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set[str] = Field(default_factory=lambda: {'.csv', '.xlsx', '.xls', '.pdf'})

    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    SENTRY_DSN: str | None = None

    # Feature Flags
    ENABLE_SWAGGER: bool = True
    ENABLE_REDOC: bool = True
    ENABLE_DOCS_IN_PROD: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
