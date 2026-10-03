"""Product Service configuration."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    SERVICE_NAME: str = "product-service"
    PORT: int = 8002

    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # DynamoDB
    DYNAMODB_TABLE_NAME: str = "products"

    # S3
    S3_BUCKET_NAME: str = "ecommerce-product-images"
    S3_PRESIGNED_URL_EXPIRY: int = 3600  # 1 hour

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    # Internal service URLs (for inter-service calls)
    USER_SERVICE_URL: str = "http://user-service:8001"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
