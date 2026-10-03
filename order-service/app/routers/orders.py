"""Orders router — full order lifecycle management."""

from fastapi import APIRouter, Query, status
from typing import Optional
from app.schemas import (
    OrderCreate, OrderStatusUpdate, OrderResponse,
    OrderListResponse, MessageResponse,
)
from app.services.order_service import order_service

router = APIRouter()


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order",
)
async def create_order(payload: OrderCreate):
    """
    Place a new order.

    **Process:**
    1. Validates all products exist (calls Product Service)
    2. Checks stock availability for each item
    3. Calculates total amount based on current prices
    4. Creates order record in DynamoDB
    5. Returns created order with enriched product details

    **Status:** starts as `pending`, moves to `confirmed` if payment transaction_id is provided.
    """
    result = await order_service.create_order(payload.model_dump())
    return OrderResponse(**result)


@router.get(
    "/",
    response_model=OrderListResponse,
    summary="List all orders (Admin)",
)
async def list_all_orders(
    limit: int = Query(20, ge=1, le=100),
    last_key: Optional[str] = Query(None, description="Pagination cursor"),
):
    """List all orders across all users — Admin endpoint."""
    result = order_service.list_all_orders(limit=limit, last_evaluated_key=last_key)
    return OrderListResponse(**result)


@router.get(
    "/user/{user_id}",
    response_model=OrderListResponse,
    summary="List orders for a specific user",
)
async def list_user_orders(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    last_key: Optional[str] = Query(None),
):
    """Get all orders placed by a specific user, sorted newest first."""
    result = order_service.list_orders_by_user(
        user_id=user_id,
        limit=limit,
        last_evaluated_key=last_key,
    )
    return OrderListResponse(**result)


@router.get(
    "/user/{user_id}/summary",
    response_model=dict,
    summary="Get order summary/statistics for a user",
)
async def get_user_order_summary(user_id: str):
    """
    Get aggregated order statistics for a user:
    - Total orders count
    - Total amount spent
    - Breakdown by order status
    """
    return order_service.get_order_summary(user_id=user_id)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order by ID",
)
async def get_order(order_id: str):
    """Retrieve a single order by its order_id."""
    result = order_service.get_order(order_id=order_id)
    return OrderResponse(**result)


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Update order status",
)
async def update_order_status(order_id: str, payload: OrderStatusUpdate):
    """
    Update order status following valid transition rules:

    ```
    pending → confirmed → processing → shipped → delivered
    pending/confirmed/processing → cancelled
    delivered → refunded
    ```

    Invalid transitions return HTTP 400.
    """
    result = order_service.update_order_status(
        order_id=order_id,
        new_status=payload.status.value,
        notes=payload.notes,
        tracking_number=payload.tracking_number,
    )
    return OrderResponse(**result)
