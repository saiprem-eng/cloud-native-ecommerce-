"""Order Service configuration."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    SERVICE_NAME: str = "order-service"
    PORT: int = 8003

    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # DynamoDB
    DYNAMODB_ORDERS_TABLE: str = "orders"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    # Inter-service URLs (Kubernetes service names in EKS)
    USER_SERVICE_URL: str = "http://user-service:8001"
    PRODUCT_SERVICE_URL: str = "http://product-service:8002"

    # HTTP client timeout (seconds)
    SERVICE_CALL_TIMEOUT: float = 10.0

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
