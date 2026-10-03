"""
Configuration settings for User Service using environment variables.
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App
    ENVIRONMENT: str = "development"
    SERVICE_NAME: str = "user-service"
    PORT: int = 8001

    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # AWS Cognito
    COGNITO_USER_POOL_ID: str = ""
    COGNITO_CLIENT_ID: str = ""
    COGNITO_CLIENT_SECRET: str = ""
    COGNITO_DOMAIN: str = ""

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    # JWT
    JWT_ALGORITHM: str = "RS256"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
