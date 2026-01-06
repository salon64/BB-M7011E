# item_service/app/main.py
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, validator
from typing import Optional
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CollectorRegistry,
)
import logging
import time
import os
import json
import uuid
from contextlib import asynccontextmanager
import aio_pika
from aio_pika import Message, DeliveryMode

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

rabbitmq_publish_total = Counter(
    "rabbitmq_publish_total",
    "Total messages published to RabbitMQ",
    ["operation", "status"],
    registry=registry,
)

rabbitmq_publish_duration = Histogram(
    "rabbitmq_publish_duration_seconds",
    "Duration of RabbitMQ publish operations",
    ["operation"],
    registry=registry,
)

# Global RabbitMQ connection
rabbitmq_connection = None
rabbitmq_channel = None


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


class MessageResponse(BaseModel):
    message_id: str
    status: str
    operation: str
    message: str


# RabbitMQ functions
async def get_rabbitmq_connection():
    """Get or create RabbitMQ connection"""
    global rabbitmq_connection, rabbitmq_channel
    
    if rabbitmq_connection is None or rabbitmq_connection.is_closed:
        rabbitmq_url = os.getenv(
            "RABBITMQ_URL", 
            "amqp://guest:guest@rabbitmq-service:5672/"
        )
        logger.info(f"Connecting to RabbitMQ: {rabbitmq_url}")
        
        rabbitmq_connection = await aio_pika.connect_robust(
            rabbitmq_url,
            timeout=30,
        )
        rabbitmq_channel = await rabbitmq_connection.channel()
        
        # Declare exchange
        exchange = await rabbitmq_channel.declare_exchange(
            "items_exchange",
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        
        # Declare queues
        queues = [
            "items.create",
            "items.update",
            "items.delete",
            "items.get",
            "items.list"
        ]
        
        for queue_name in queues:
            queue = await rabbitmq_channel.declare_queue(queue_name, durable=True)
            await queue.bind(exchange, routing_key=queue_name)
        
        logger.info("RabbitMQ connection established and queues declared")
    
    return rabbitmq_channel


async def publish_message(routing_key: str, message_body: dict):
    """Publish a message to RabbitMQ"""
    start_time = time.time()
    operation = message_body.get("operation", "unknown")
    
    try:
        channel = await get_rabbitmq_connection()
        exchange = await channel.get_exchange("items_exchange")
        
        message = Message(
            body=json.dumps(message_body).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
            message_id=message_body.get("message_id"),
            timestamp=int(time.time()),
        )
        
        await exchange.publish(message, routing_key=routing_key)
        
        rabbitmq_publish_total.labels(operation=operation, status="success").inc()
        logger.info(
            f"Published message - ID: {message_body.get('message_id')}, "
            f"Operation: {operation}, Routing: {routing_key}"
        )
        
    except Exception as e:
        rabbitmq_publish_total.labels(operation=operation, status="error").inc()
        logger.error(f"Error publishing message: {str(e)}")
        raise
    finally:
        duration = time.time() - start_time
        rabbitmq_publish_duration.labels(operation=operation).observe(duration)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Item Service")
    try:
        await get_rabbitmq_connection()
        logger.info("Item Service startup complete")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise
    
    yield
    
    # Cleanup
    if rabbitmq_connection and not rabbitmq_connection.is_closed:
        await rabbitmq_connection.close()
        logger.info("RabbitMQ connection closed")
    logger.info("Shutting down Item Service")


# FastAPI app
app = FastAPI(
    title="Item Service",
    description="Item Management Service with RabbitMQ Integration",
    version="2.0.0",
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
    return {"status": "healthy", "service": "item_service", "timestamp": time.time()}


# Readiness check endpoint
@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint - verifies RabbitMQ connection"""
    try:
        await get_rabbitmq_connection()
        return {"status": "ready", "service": "item_service", "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"RabbitMQ connection failed: {str(e)}")


# Metrics endpoint
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(registry)


# Create item
@app.post("/items", response_model=MessageResponse, status_code=202)
async def create_item(item: ItemCreate):
    """Create a new item (async via RabbitMQ)"""
    try:
        message_id = str(uuid.uuid4())
        message_body = {
            "message_id": message_id,
            "operation": "create",
            "data": {
                "name": item.name,
                "price": item.price,
                "barcode_id": item.barcode_id,
            },
            "timestamp": time.time(),
        }

        await publish_message("items.create", message_body)

        return MessageResponse(
            message_id=message_id,
            status="accepted",
            operation="create",
            message="Item creation request queued successfully",
        )
    except Exception as e:
        logger.error(f"Error creating item: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to queue item creation: {str(e)}")


# Get all items
@app.get("/items", response_model=MessageResponse, status_code=202)
async def get_items(active: Optional[bool] = Query(None, description="Filter by active status")):
    """Get all items (async via RabbitMQ)"""
    try:
        message_id = str(uuid.uuid4())
        message_body = {
            "message_id": message_id,
            "operation": "list",
            "filters": {"active": active} if active is not None else {},
            "timestamp": time.time(),
        }

        await publish_message("items.list", message_body)

        return MessageResponse(
            message_id=message_id,
            status="accepted",
            operation="list",
            message="Item list request queued successfully",
        )
    except Exception as e:
        logger.error(f"Error fetching items: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to queue item list request: {str(e)}")


# Get item by ID
@app.get("/items/{item_id}", response_model=MessageResponse, status_code=202)
async def get_item(item_id: str):
    """Get a specific item by ID (async via RabbitMQ)"""
    try:
        message_id = str(uuid.uuid4())
        message_body = {
            "message_id": message_id,
            "operation": "get",
            "item_id": item_id,
            "timestamp": time.time(),
        }

        await publish_message("items.get", message_body)

        return MessageResponse(
            message_id=message_id,
            status="accepted",
            operation="get",
            message=f"Item retrieval request queued for ID: {item_id}",
        )
    except Exception as e:
        logger.error(f"Error fetching item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to queue item retrieval: {str(e)}")


# Update item
@app.put("/items/{item_id}", response_model=MessageResponse, status_code=202)
async def update_item(item_id: str, item_update: ItemUpdate):
    """Update an existing item (async via RabbitMQ)"""
    try:
        update_data = item_update.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        message_id = str(uuid.uuid4())
        message_body = {
            "message_id": message_id,
            "operation": "update",
            "item_id": item_id,
            "data": update_data,
            "timestamp": time.time(),
        }

        await publish_message("items.update", message_body)

        return MessageResponse(
            message_id=message_id,
            status="accepted",
            operation="update",
            message=f"Item update request queued for ID: {item_id}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to queue item update: {str(e)}")


# Delete item
@app.delete("/items/{item_id}", response_model=MessageResponse, status_code=202)
async def delete_item(
    item_id: str,
    hard_delete: bool = Query(False, description="Permanently delete the item")
):
    """Delete an item (async via RabbitMQ)"""
    try:
        message_id = str(uuid.uuid4())
        message_body = {
            "message_id": message_id,
            "operation": "delete",
            "item_id": item_id,
            "hard_delete": hard_delete,
            "timestamp": time.time(),
        }

        await publish_message("items.delete", message_body)

        delete_type = "permanent" if hard_delete else "soft"
        return MessageResponse(
            message_id=message_id,
            status="accepted",
            operation="delete",
            message=f"Item {delete_type} deletion request queued for ID: {item_id}",
        )
    except Exception as e:
        logger.error(f"Error deleting item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to queue item deletion: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))