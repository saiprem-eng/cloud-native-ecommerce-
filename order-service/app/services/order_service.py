"""
Order service layer — DynamoDB CRUD + inter-service calls to Product Service.
"""

import boto3
import botocore.exceptions
import httpx
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from boto3.dynamodb.conditions import Attr, Key

from app.config import settings

logger = logging.getLogger(__name__)


def float_to_decimal(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [float_to_decimal(i) for i in obj]
    return obj


def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj


class OrderService:
    """Service class for order lifecycle management."""

    def __init__(self):
        self.dynamodb = boto3.resource(
            "dynamodb",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        )
        self.table = self.dynamodb.Table(settings.DYNAMODB_ORDERS_TABLE)

    async def _fetch_product(self, product_id: str) -> Dict[str, Any]:
        """Fetch product details from Product Service."""
        try:
            async with httpx.AsyncClient(timeout=settings.SERVICE_CALL_TIMEOUT) as client:
                resp = await client.get(
                    f"{settings.PRODUCT_SERVICE_URL}/api/v1/products/{product_id}"
                )
                if resp.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Product '{product_id}' not found.",
                    )
                resp.raise_for_status()
                return resp.json()
        except HTTPException:
            raise
        except httpx.RequestError as e:
            logger.error(f"Product service call failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Product service is unavailable.",
            )

    async def _validate_stock(self, product_id: str, quantity: int, product: dict) -> None:
        """Validate that product has enough stock."""
        if product.get("status") != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{product_id}' is not available for purchase.",
            )
        if product.get("stock_quantity", 0) < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product '{product['name']}'. "
                       f"Available: {product['stock_quantity']}, Requested: {quantity}",
            )

    async def create_order(self, data: dict) -> dict:
        """Create a new order — validates products, calculates total, persists to DynamoDB."""
        order_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Validate all products and enrich order items
        enriched_items = []
        total_amount = 0.0

        for item in data["items"]:
            product = await self._fetch_product(item["product_id"])
            await self._validate_stock(item["product_id"], item["quantity"], product)

            unit_price = product["price"]
            subtotal = unit_price * item["quantity"]
            total_amount += subtotal

            enriched_items.append({
                "product_id": item["product_id"],
                "product_name": product["name"],
                "quantity": item["quantity"],
                "unit_price": unit_price,
                "subtotal": subtotal,
            })

        # Build order record
        order = {
            "order_id": order_id,
            "user_id": data["user_id"],
            "items": enriched_items,
            "total_amount": total_amount,
            "order_status": "pending",
            "payment_status": "pending",
            "payment_method": data["payment"]["method"],
            "transaction_id": data["payment"].get("transaction_id", ""),
            "shipping_address": data["shipping_address"],
            "notes": data.get("notes", ""),
            "tracking_number": "",
            "created_at": now,
            "updated_at": now,
        }

        # Mark as paid if transaction_id provided
        if data["payment"].get("transaction_id"):
            order["payment_status"] = "paid"
            order["order_status"] = "confirmed"

        try:
            self.table.put_item(Item=float_to_decimal(order))
            logger.info(f"Order created: {order_id} for user {data['user_id']}, total: ${total_amount:.2f}")
            return decimal_to_float(order)
        except botocore.exceptions.ClientError as e:
            logger.error(f"DynamoDB order create error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create order.",
            )

    def get_order(self, order_id: str) -> dict:
        """Get a single order by ID."""
        try:
            response = self.table.get_item(Key={"order_id": order_id})
            item = response.get("Item")
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Order '{order_id}' not found.",
                )
            return decimal_to_float(item)
        except HTTPException:
            raise
        except botocore.exceptions.ClientError as e:
            logger.error(f"DynamoDB get order error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch order.",
            )

    def list_orders_by_user(
        self,
        user_id: str,
        limit: int = 20,
        last_evaluated_key: Optional[str] = None,
    ) -> dict:
        """List all orders for a specific user."""
        try:
            kwargs = {
                "FilterExpression": Attr("user_id").eq(user_id),
                "Limit": limit,
            }
            if last_evaluated_key:
                kwargs["ExclusiveStartKey"] = {"order_id": last_evaluated_key}

            response = self.table.scan(**kwargs)
            items = [decimal_to_float(item) for item in response.get("Items", [])]
            # Sort by created_at desc
            items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            return {
                "orders": items,
                "count": len(items),
                "last_evaluated_key": response.get("LastEvaluatedKey", {}).get("order_id"),
            }
        except botocore.exceptions.ClientError as e:
            logger.error(f"DynamoDB list orders error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list orders.",
            )

    def list_all_orders(self, limit: int = 20, last_evaluated_key: Optional[str] = None) -> dict:
        """List all orders (admin view)."""
        try:
            kwargs = {"Limit": limit}
            if last_evaluated_key:
                kwargs["ExclusiveStartKey"] = {"order_id": last_evaluated_key}

            response = self.table.scan(**kwargs)
            items = [decimal_to_float(item) for item in response.get("Items", [])]
            items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            return {
                "orders": items,
                "count": len(items),
                "last_evaluated_key": response.get("LastEvaluatedKey", {}).get("order_id"),
            }
        except botocore.exceptions.ClientError as e:
            logger.error(f"DynamoDB list all orders error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list orders.",
            )

    def update_order_status(
        self,
        order_id: str,
        new_status: str,
        notes: Optional[str] = None,
        tracking_number: Optional[str] = None,
    ) -> dict:
        """Update order status (e.g., confirmed → processing → shipped → delivered)."""
        try:
            order = self.get_order(order_id)

            # Status transition validation
            valid_transitions = {
                "pending": ["confirmed", "cancelled"],
                "confirmed": ["processing", "cancelled"],
                "processing": ["shipped", "cancelled"],
                "shipped": ["delivered"],
                "delivered": ["refunded"],
                "cancelled": [],
                "refunded": [],
            }

            current_status = order["order_status"]
            if new_status not in valid_transitions.get(current_status, []):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status transition: '{current_status}' → '{new_status}'. "
                           f"Valid transitions: {valid_transitions.get(current_status, [])}",
                )

            now = datetime.now(timezone.utc).isoformat()
            update_parts = ["#s = :status", "updated_at = :now"]
            expr_values = {":status": new_status, ":now": now}
            expr_names = {"#s": "order_status"}

            if notes:
                update_parts.append("notes = :notes")
                expr_values[":notes"] = notes
            if tracking_number:
                update_parts.append("tracking_number = :tracking")
                expr_values[":tracking"] = tracking_number

            # Auto-update payment status on cancellation/refund
            if new_status in ("cancelled", "refunded"):
                update_parts.append("payment_status = :pstatus")
                expr_values[":pstatus"] = new_status

            response = self.table.update_item(
                Key={"order_id": order_id},
                UpdateExpression="SET " + ", ".join(update_parts),
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
                ReturnValues="ALL_NEW",
            )

            logger.info(f"Order {order_id} status: {current_status} → {new_status}")
            return decimal_to_float(response["Attributes"])

        except HTTPException:
            raise
        except botocore.exceptions.ClientError as e:
            logger.error(f"DynamoDB update order error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update order status.",
            )

    def get_order_summary(self, user_id: str) -> dict:
        """Get order statistics for a user."""
        try:
            response = self.table.scan(
                FilterExpression=Attr("user_id").eq(user_id)
            )
            orders = [decimal_to_float(item) for item in response.get("Items", [])]

            total_spent = sum(o.get("total_amount", 0) for o in orders if o.get("payment_status") == "paid")
            status_counts = {}
            for o in orders:
                s = o.get("order_status", "unknown")
                status_counts[s] = status_counts.get(s, 0) + 1

            return {
                "user_id": user_id,
                "total_orders": len(orders),
                "total_spent_usd": round(total_spent, 2),
                "status_breakdown": status_counts,
            }
        except botocore.exceptions.ClientError as e:
            logger.error(f"Order summary error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch order summary.",
            )


# Singleton
order_service = OrderService()
