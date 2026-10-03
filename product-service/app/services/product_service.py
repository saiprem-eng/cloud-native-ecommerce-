"""
DynamoDB + S3 service layer for Product Service.
Handles all CRUD operations for products.
"""

import boto3
import botocore.exceptions
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal
from fastapi import HTTPException, status
from boto3.dynamodb.conditions import Key, Attr

from app.config import settings

logger = logging.getLogger(__name__)


def get_dynamodb_resource():
    return boto3.resource(
        "dynamodb",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
    )


def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
    )


def float_to_decimal(obj):
    """Recursively convert floats to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [float_to_decimal(i) for i in obj]
    return obj


def decimal_to_float(obj):
    """Recursively convert Decimals back to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj


class ProductService:
    """Service class for product CRUD operations using DynamoDB + S3."""

    def __init__(self):
        self.dynamodb = get_dynamodb_resource()
        self.s3 = get_s3_client()
        self.table = self.dynamodb.Table(settings.DYNAMODB_TABLE_NAME)
        self.bucket = settings.S3_BUCKET_NAME

    def create_product(self, data: dict) -> dict:
        """Create a new product in DynamoDB."""
        try:
            product_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            item = {
                "product_id": product_id,
                "name": data["name"],
                "description": data["description"],
                "price": float_to_decimal(data["price"]),
                "category": data["category"],
                "stock_quantity": data["stock_quantity"],
                "sku": data["sku"],
                "brand": data.get("brand", ""),
                "tags": data.get("tags", []),
                "status": "active",
                "image_urls": [],
                "weight_kg": float_to_decimal(data["weight_kg"]) if data.get("weight_kg") else None,
                "dimensions": float_to_decimal(data.get("dimensions")) if data.get("dimensions") else None,
                "created_at": now,
                "updated_at": now,
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(product_id)",
            )

            logger.info(f"Product created: {product_id} - {data['name']}")
            return decimal_to_float(item)

        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product with this ID already exists.",
            )
        except botocore.exceptions.ClientError as e:
            logger.error(f"DynamoDB create error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create product.",
            )

    def get_product(self, product_id: str) -> dict:
        """Get a single product by ID."""
        try:
            response = self.table.get_item(Key={"product_id": product_id})
            item = response.get("Item")
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product '{product_id}' not found.",
                )
            return decimal_to_float(item)
        except HTTPException:
            raise
        except botocore.exceptions.ClientError as e:
            logger.error(f"DynamoDB get error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch product.",
            )

    def list_products(
        self,
        category: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 20,
        last_evaluated_key: Optional[str] = None,
    ) -> dict:
        """List products with optional filters."""
        try:
            kwargs = {"Limit": limit}

            # Build filter expression
            filters = []
            if category:
                filters.append(Attr("category").eq(category))
            if status_filter:
                filters.append(Attr("status").eq(status_filter))

            if filters:
                filter_expr = filters[0]
                for f in filters[1:]:
                    filter_expr = filter_expr & f
                kwargs["FilterExpression"] = filter_expr

            if last_evaluated_key:
                kwargs["ExclusiveStartKey"] = {"product_id": last_evaluated_key}

            response = self.table.scan(**kwargs)
            items = [decimal_to_float(item) for item in response.get("Items", [])]
            lek = response.get("LastEvaluatedKey", {}).get("product_id")

            return {
                "products": items,
                "count": len(items),
                "last_evaluated_key": lek,
            }
        except botocore.exceptions.ClientError as e:
            logger.error(f"DynamoDB list error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list products.",
            )

    def update_product(self, product_id: str, data: dict) -> dict:
        """Update a product's attributes."""
        try:
            # Verify product exists
            self.get_product(product_id)

            now = datetime.now(timezone.utc).isoformat()
            update_expression_parts = []
            expression_attribute_names = {}
            expression_attribute_values = {":updated_at": now}

            field_map = {
                "name": "#n",
                "description": "description",
                "price": "price",
                "category": "category",
                "stock_quantity": "stock_quantity",
                "brand": "brand",
                "tags": "tags",
                "status": "#s",
                "weight_kg": "weight_kg",
                "dimensions": "dimensions",
            }

            reserved_words = {"name": "#n", "status": "#s"}

            for field, value in data.items():
                if value is not None and field in field_map:
                    placeholder = field_map[field]
                    val_key = f":{field}"
                    update_expression_parts.append(f"{placeholder} = {val_key}")
                    if field in reserved_words:
                        expression_attribute_names[reserved_words[field]] = field
                    expression_attribute_values[val_key] = float_to_decimal(value)

            if not update_expression_parts:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields provided for update.",
                )

            update_expression_parts.append("updated_at = :updated_at")
            update_expression = "SET " + ", ".join(update_expression_parts)

            kwargs = {
                "Key": {"product_id": product_id},
                "UpdateExpression": update_expression,
                "ExpressionAttributeValues": expression_attribute_values,
                "ReturnValues": "ALL_NEW",
            }
            if expression_attribute_names:
                kwargs["ExpressionAttributeNames"] = expression_attribute_names

            response = self.table.update_item(**kwargs)
            updated_item = decimal_to_float(response["Attributes"])

            logger.info(f"Product updated: {product_id}")
            return updated_item

        except HTTPException:
            raise
        except botocore.exceptions.ClientError as e:
            logger.error(f"DynamoDB update error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update product.",
            )

    def delete_product(self, product_id: str) -> dict:
        """Soft delete a product by setting status to 'discontinued'."""
        try:
            self.get_product(product_id)
            self.table.update_item(
                Key={"product_id": product_id},
                UpdateExpression="SET #s = :status, updated_at = :updated_at",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":status": "discontinued",
                    ":updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            logger.info(f"Product soft-deleted: {product_id}")
            return {"message": f"Product {product_id} discontinued successfully.", "success": True}
        except HTTPException:
            raise
        except botocore.exceptions.ClientError as e:
            logger.error(f"DynamoDB delete error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete product.",
            )

    def generate_upload_url(self, product_id: str, filename: str, content_type: str) -> dict:
        """Generate a pre-signed S3 URL for image upload."""
        try:
            # Verify product exists
            self.get_product(product_id)

            extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
            image_key = f"products/{product_id}/{uuid.uuid4()}.{extension}"

            presigned_url = self.s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": image_key,
                    "ContentType": content_type,
                },
                ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRY,
            )

            # Add image URL to product record
            image_url = f"https://{self.bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{image_key}"
            self.table.update_item(
                Key={"product_id": product_id},
                UpdateExpression="SET image_urls = list_append(if_not_exists(image_urls, :empty), :url), updated_at = :now",
                ExpressionAttributeValues={
                    ":url": [image_url],
                    ":empty": [],
                    ":now": datetime.now(timezone.utc).isoformat(),
                },
            )

            return {
                "upload_url": presigned_url,
                "image_key": image_key,
                "expires_in": settings.S3_PRESIGNED_URL_EXPIRY,
                "message": "Upload the image using a PUT request to the upload_url.",
            }

        except HTTPException:
            raise
        except botocore.exceptions.ClientError as e:
            logger.error(f"S3 presigned URL error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate upload URL.",
            )

    def search_products(self, query: str, limit: int = 20) -> dict:
        """Basic product search by name (case-insensitive contains)."""
        try:
            response = self.table.scan(
                FilterExpression=Attr("name").contains(query) | Attr("description").contains(query),
                Limit=min(limit, 100),
            )
            items = [decimal_to_float(item) for item in response.get("Items", [])]
            return {"products": items, "count": len(items), "query": query}
        except botocore.exceptions.ClientError as e:
            logger.error(f"Search error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Search failed.",
            )


# Singleton
product_service = ProductService()
