"""Pydantic schemas for Product Service."""

from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from enum import Enum


class ProductCategory(str, Enum):
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    FOOD = "food"
    BOOKS = "books"
    HOME = "home"
    SPORTS = "sports"
    BEAUTY = "beauty"
    TOYS = "toys"
    OTHER = "other"


class ProductStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


# ─────────────────────────── Request Schemas ───────────────────────

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    price: float = Field(..., gt=0, description="Price in USD")
    category: ProductCategory
    stock_quantity: int = Field(..., ge=0)
    sku: str = Field(..., min_length=1, max_length=100, description="Stock Keeping Unit")
    brand: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = []
    weight_kg: Optional[float] = Field(None, gt=0)
    dimensions: Optional[dict] = None  # {"length": ..., "width": ..., "height": ...}

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Premium Wireless Headphones",
                "description": "High-quality noise-cancelling wireless headphones with 30-hour battery life.",
                "price": 299.99,
                "category": "electronics",
                "stock_quantity": 150,
                "sku": "WH-PREMIUM-001",
                "brand": "SoundMaster",
                "tags": ["wireless", "noise-cancelling", "premium"],
                "weight_kg": 0.35,
                "dimensions": {"length": 20, "width": 18, "height": 8}
            }
        }


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    price: Optional[float] = Field(None, gt=0)
    category: Optional[ProductCategory] = None
    stock_quantity: Optional[int] = Field(None, ge=0)
    brand: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[ProductStatus] = None
    weight_kg: Optional[float] = None
    dimensions: Optional[dict] = None


# ─────────────────────────── Response Schemas ──────────────────────

class ProductResponse(BaseModel):
    product_id: str
    name: str
    description: str
    price: float
    category: str
    stock_quantity: int
    sku: str
    brand: Optional[str] = None
    tags: List[str] = []
    status: str
    image_urls: List[str] = []
    weight_kg: Optional[float] = None
    dimensions: Optional[dict] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    count: int
    last_evaluated_key: Optional[str] = None


class PresignedUrlResponse(BaseModel):
    upload_url: str
    image_key: str
    expires_in: int
    message: str


class MessageResponse(BaseModel):
    message: str
    success: bool = True
