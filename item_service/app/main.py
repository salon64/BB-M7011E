# app/main.py
from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, validator
from typing import Optional
from .database import get_supabase_client
from common.auth import require_auth, require_admin
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CollectorRegistry,
)
import logging
import time
import os
from contextlib import asynccontextmanager

# Logging setup
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"time":"%(asctime)s","level":"%(levelname)s",'
    '"message":"%(message)s","name":"%(name)s"}',
)
logger = logging.getLogger(__name__)

# Prometheus metrics
registry = CollectorRegistry()

http_request_duration = Histogram(
    "http_request_duration_seconds",
    "Duration of HTTP requests in seconds",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

http_request_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

db_operation_duration = Histogram(
    "db_operation_duration_seconds",
    "Duration of database operations",
    ["operation"],
    registry=registry,
)


# Pydantic models
class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Item name")
    price: int = Field(..., ge=0, description="Item price in cents")
    barcode_id: Optional[int] = Field(None, description="Barcode ID")

    @validator("name")
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[int] = Field(None, ge=0)
    barcode_id: Optional[int] = None
    active: Optional[bool] = None

    @validator("name")
    def name_must_not_be_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip() if v else v


class ItemResponse(BaseModel):
    id: str
    name: str
    price: int
    barcode_id: Optional[int]
    active: bool


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Product Microservice")
    yield
    logger.info("Shutting down Product Microservice")


# FastAPI app
app = FastAPI(
    title="Product Microservice",
    description="Microservice for managing product items",
    version="1.0.0",
    lifespan=lifespan,
)


# Middleware for metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    endpoint = request.url.path
    method = request.method
    status_code = response.status_code

    http_request_duration.labels(
        method=method, endpoint=endpoint, status_code=status_code
    ).observe(duration)
    http_request_total.labels(
        method=method, endpoint=endpoint, status_code=status_code
    ).inc()

    return response


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}


# Readiness check endpoint
@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint - verifies database connection"""
    try:
        get_supabase_client().table("Items").select("id").limit(1).execute()
        return {"status": "ready", "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Database connection failed")


# Metrics endpoint
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(registry)


# Create item
@app.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(item: ItemCreate, token_data: dict = Depends(require_admin)):
    """Create a new item - requires admin role"""
    start_time = time.time()
    try:
        item_data = {
            "name": item.name,
            "price": item.price,
            "barcode_id": item.barcode_id,
            "active": True,
        }

        response = get_supabase_client().table("Items").insert(item_data).execute()

        if not response.data:
            logger.error("Failed to create item: No data returned")
            raise HTTPException(status_code=500, detail="Failed to create item")

        created_item = response.data[0]
        logger.info(f"Item created successfully: {created_item['id']}")

        return ItemResponse(**created_item)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating item: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        duration = time.time() - start_time
        db_operation_duration.labels(operation="create").observe(duration)


# Get all items
@app.get("/items", response_model=list[ItemResponse])
async def get_items(
    active: Optional[bool] = Query(None, description="Filter by active status"),
    token_data: dict = Depends(require_auth),
):
    """Get all items, optionally filtered by active status - requires authentication"""
    start_time = time.time()
    try:
        query = get_supabase_client().table("Items").select("*")

        if active is not None:
            query = query.eq("active", active)

        response = query.order("name", desc=False).execute()

        return [ItemResponse(**item) for item in response.data]
    except Exception as e:
        logger.error(f"Error fetching items: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch items")
    finally:
        duration = time.time() - start_time
        db_operation_duration.labels(operation="read").observe(duration)


# Get item by ID
@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str, token_data: dict = Depends(require_auth)):
    """Get a specific item by ID - requires authentication"""
    start_time = time.time()
    try:
        response = (
            get_supabase_client().table("Items").select("*").eq("id", item_id).execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Item not found")

        return ItemResponse(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch item")
    finally:
        duration = time.time() - start_time
        db_operation_duration.labels(operation="read").observe(duration)


# Update item
@app.put("/items/{item_id}", response_model=ItemResponse)
async def update_item(item_id: str, item_update: ItemUpdate):
    """Update an existing item"""
    start_time = time.time()
    try:
        # Check if item exists
        check_response = (
            get_supabase_client()
            .table("Items")
            .select("id")
            .eq("id", item_id)
            .execute()
        )
        if not check_response.data:
            raise HTTPException(status_code=404, detail="Item not found")

        # Prepare update data (only include fields that are not None)
        update_data = item_update.dict(exclude_unset=True)

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        response = (
            get_supabase_client()
            .table("Items")
            .update(update_data)
            .eq("id", item_id)
            .execute()
        )

        if not response.data:
            logger.error(f"Failed to update item {item_id}")
            raise HTTPException(status_code=500, detail="Failed to update item")

        logger.info(f"Item updated successfully: {item_id}")
        return ItemResponse(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        duration = time.time() - start_time
        db_operation_duration.labels(operation="update").observe(duration)

# Delete item (soft delete by setting active=False)
@app.delete("/items/{item_id}", status_code=204)
async def delete_item(
    item_id: str,
    hard_delete: bool = Query(False, description="Permanently delete the item"),
    token_data: dict = Depends(require_admin),
):
    """Delete an item (soft delete by default, use hard_delete=true for permanent deletion) - requires admin role"""
    start_time = time.time()
    try:
        # Check if item exists
        check_response = (
            get_supabase_client()
            .table("Items")
            .select("id")
            .eq("id", item_id)
            .execute()
        )
        if not check_response.data:
            raise HTTPException(status_code=404, detail="Item not found")

        if hard_delete:
            # Hard delete
            get_supabase_client().table("Items").delete().eq("id", item_id).execute()
            logger.info(f"Item permanently deleted: {item_id}")
        else:
            # Soft delete
            get_supabase_client().table("Items").update({"active": False}).eq(
                "id", item_id
            ).execute()
            logger.info(f"Item soft deleted: {item_id}")

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        duration = time.time() - start_time
        db_operation_duration.labels(operation="delete").observe(duration)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
