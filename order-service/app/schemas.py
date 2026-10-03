"""Pydantic schemas for Order Service."""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    UPI = "upi"
    NET_BANKING = "net_banking"
    WALLET = "wallet"
    COD = "cod"


# ─────────────────────────── Sub-schemas ───────────────────────────

class OrderItem(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)
    unit_price: Optional[float] = None  # Fetched from Product Service
    product_name: Optional[str] = None  # Fetched from Product Service

    class Config:
        json_schema_extra = {
            "example": {"product_id": "abc-123", "quantity": 2}
        }


class ShippingAddress(BaseModel):
    full_name: str
    street_address: str
    city: str
    state: str
    postal_code: str
    country: str = "India"
    phone: str


class PaymentInfo(BaseModel):
    method: PaymentMethod
    transaction_id: Optional[str] = None


# ─────────────────────────── Request Schemas ───────────────────────

class OrderCreate(BaseModel):
    user_id: str
    items: List[OrderItem] = Field(..., min_length=1)
    shipping_address: ShippingAddress
    payment: PaymentInfo
    notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user-uuid-123",
                "items": [
                    {"product_id": "prod-uuid-456", "quantity": 2},
                    {"product_id": "prod-uuid-789", "quantity": 1},
                ],
                "shipping_address": {
                    "full_name": "John Doe",
                    "street_address": "123 MG Road",
                    "city": "Bengaluru",
                    "state": "Karnataka",
                    "postal_code": "560001",
                    "country": "India",
                    "phone": "+919876543210",
                },
                "payment": {"method": "upi", "transaction_id": "txn_123456"},
                "notes": "Please leave at the door."
            }
        }


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    notes: Optional[str] = None
    tracking_number: Optional[str] = None


# ─────────────────────────── Response Schemas ──────────────────────

class OrderItemResponse(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float


class OrderResponse(BaseModel):
    order_id: str
    user_id: str
    items: List[OrderItemResponse]
    total_amount: float
    order_status: str
    payment_status: str
    payment_method: str
    shipping_address: dict
    tracking_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class OrderListResponse(BaseModel):
    orders: List[OrderResponse]
    count: int
    last_evaluated_key: Optional[str] = None


class MessageResponse(BaseModel):
    message: str
    success: bool = True
