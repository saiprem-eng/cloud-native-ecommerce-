"""Products router — full CRUD + image upload + search."""

from fastapi import APIRouter, Query, status
from typing import Optional
from app.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    ProductListResponse, PresignedUrlResponse, MessageResponse,
)
from app.services.product_service import product_service
from pydantic import BaseModel

router = APIRouter()


class ImageUploadRequest(BaseModel):
    filename: str
    content_type: str = "image/jpeg"


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
async def create_product(payload: ProductCreate):
    """
    Create a new product in the catalog.
    - Stores data in DynamoDB
    - Returns the created product with generated product_id
    """
    result = product_service.create_product(payload.model_dump())
    return ProductResponse(**result)


@router.get(
    "/search",
    response_model=dict,
    summary="Search products by name/description",
)
async def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search products by keyword in name or description."""
    return product_service.search_products(query=q, limit=limit)


@router.get(
    "/",
    response_model=ProductListResponse,
    summary="List all products",
)
async def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    last_key: Optional[str] = Query(None, description="Pagination cursor from previous response"),
):
    """
    List products with optional filtering by category and status.
    Uses DynamoDB pagination via last_key.
    """
    result = product_service.list_products(
        category=category,
        status_filter=status_filter,
        limit=limit,
        last_evaluated_key=last_key,
    )
    return ProductListResponse(**result)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
)
async def get_product(product_id: str):
    """Retrieve a single product by its product_id."""
    result = product_service.get_product(product_id=product_id)
    return ProductResponse(**result)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update product",
)
async def update_product(product_id: str, payload: ProductUpdate):
    """
    Update product attributes. Only provided fields are updated (partial update).
    """
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    result = product_service.update_product(product_id=product_id, data=update_data)
    return ProductResponse(**result)


@router.delete(
    "/{product_id}",
    response_model=MessageResponse,
    summary="Discontinue product (soft delete)",
)
async def delete_product(product_id: str):
    """
    Soft-delete a product by setting its status to 'discontinued'.
    The product remains in DynamoDB for order history integrity.
    """
    result = product_service.delete_product(product_id=product_id)
    return MessageResponse(**result)


@router.post(
    "/{product_id}/images/upload-url",
    response_model=PresignedUrlResponse,
    summary="Get pre-signed URL for image upload",
)
async def get_image_upload_url(product_id: str, payload: ImageUploadRequest):
    """
    Generate a pre-signed S3 URL to upload a product image directly from the client.

    **Workflow:**
    1. Call this endpoint to get an `upload_url`
    2. PUT the image binary to the `upload_url` (no auth needed, URL has signed credentials)
    3. The image URL is automatically saved to the product's `image_urls` list
    """
    result = product_service.generate_upload_url(
        product_id=product_id,
        filename=payload.filename,
        content_type=payload.content_type,
    )
    return PresignedUrlResponse(**result)
