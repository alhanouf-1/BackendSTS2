import os
from typing import Dict, Any, Optional
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    # General App Config
    APP_NAME: str = "STS Gateway"
    APP_ENV: str = "development"
    API_V1_STR: str = "/api/v1"
    LOGO_URL: str = "https://cdn.sts-platform.com/logo.png"
    DEFAULT_LANG: str = "en"
    
    # Database Configuration (MySQL)
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "password"
    MYSQL_DATABASE: str = "sts_db"
    MYSQL_SSL_CA: Optional[str] = None
    MYSQL_SSL_VERIFY: bool = False

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        # Returns async-compatible mysql connection URI
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    @computed_field
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        # Async engine uses aiomysql, but wait, the prompt says pymysql==1.1.1 is in requirements!
        # Wait, if we use pymysql with async, wait! pymysql is sync.
        # Wait, how does Async SQLAlchemy run with MySQL?
        # Typically it uses `asyncmy` or `aiomysql`. But since only `pymysql` is required,
        # can we run Async SQLAlchemy on top of pymysql? No, pymysql is blocking.
        # Wait! Is there a way to do async with SQLAlchemy 2.0 without a custom driver, or should we use `asyncmy` or run async using a thread pool, or do we define the async engine utilizing the standard async driver?
        # Let's check: sqlalchemy async driver for mysql is `asyncmy` or `aiomysql`.
        # Wait, is `asyncmy` or `aiomysql` installed or should we use `aiomysql`?
        # Let's check requirements: `pymysql` is specified, but let's check if we can run async using `aiomysql` or if we can run it with `asyncmy`.
        # Let's see: `aiomysql` is standard. Let's make sure we specify `mysql+aiomysql://` for ASYNC_DATABASE_URL or `mysql+asyncmy://`.
        # Let's import pymysql and see if we can use standard SQLAlchemy.
        # Wait! The requirement says: pymysql==1.1.1. Let's install it or let's use `asyncmy` or `aiomysql` if we can.
        # Wait, can we use standard `aiomysql`? Let's check if we should add it, or if SQLAlchemy 2.0 can run async on pymysql? SQLAlchemy 2.0 async engine REQUIRES an async driver (like `aiomysql` or `asyncmy`).
        # Let's use `mysql+aiomysql` as the default async URL scheme, but let's make it configurable in settings.
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    # Redis Configuration
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        password_str = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password_str}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # JWT Authentication Config
    JWT_SECRET_KEY: str = "supersecretjwtkeythatshouldbechangedinproduction"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Storage (S3 or Local)
    USE_LOCAL_STORAGE: bool = True
    LOCAL_STORAGE_DIR: str = "storage"
    S3_BUCKET: str = "sts-assets"
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None

    # OpenAI configuration
    OPENAI_API_KEY: Optional[str] = None

    # Email server SMTP Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "noreply@sts-platform.com"

settings = Settings()
