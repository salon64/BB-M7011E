# worker/app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import httpx
import logging
import time
import os
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST
from fastapi.responses import PlainTextResponse
import asyncio

# Logging setup
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s","name":"%(name)s"}'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
registry = CollectorRegistry()

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'Duration of HTTP requests in seconds',
    ['method', 'endpoint', 'status_code'],
    registry=registry
)

http_request_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=registry
)

worker_task_duration = Histogram(
    'worker_task_duration_seconds',
    'Duration of worker tasks',
    ['task_type'],
    registry=registry
)

worker_task_total = Counter(
    'worker_tasks_total',
    'Total number of worker tasks processed',
    ['task_type', 'status'],
    registry=registry
)

product_service_calls = Counter(
    'product_service_calls_total',
    'Total calls to product service',
    ['endpoint', 'status'],
    registry=registry
)

# Configuration
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service")
WORKER_INTERVAL = int(os.getenv("WORKER_INTERVAL", "30"))

# Pydantic models
class WorkerTask(BaseModel):
    task_type: str
    description: str

class WorkerStatus(BaseModel):
    status: str
    tasks_processed: int
    product_service_url: str
    last_run: Optional[str] = None

class ItemSummary(BaseModel):
    total_items: int
    active_items: int
    inactive_items: int
    total_value: int
    average_price: float

# Background task state
background_task_running = False
tasks_processed = 0
last_run_time = None

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    global background_task_running
    logger.info("Starting up Worker Service")
    
    # Start background worker
    background_task_running = True
    asyncio.create_task(background_worker())
    
    yield
    
    # Cleanup
    background_task_running = False
    logger.info("Shutting down Worker Service")

# FastAPI app
app = FastAPI(
    title="Worker Microservice",
    description="Worker service that processes items from Product Microservice",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware for metrics
@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    endpoint = request.url.path
    method = request.method
    status_code = response.status_code
    
    http_request_duration.labels(method=method, endpoint=endpoint, status_code=status_code).observe(duration)
    http_request_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    
    return response

# Background worker function
async def background_worker():
    global tasks_processed, last_run_time
    
    logger.info("Background worker started")
    
    while background_task_running:
        try:
            start_time = time.time()
            
            # Fetch items from product service
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{PRODUCT_SERVICE_URL}/items", timeout=10.0)
                
                if response.status_code == 200:
                    items = response.json()
                    
                    # Process items (example: calculate statistics)
                    active_count = sum(1 for item in items if item.get('active', False))
                    inactive_count = len(items) - active_count
                    total_value = sum(item.get('price', 0) for item in items)
                    avg_price = total_value / len(items) if items else 0
                    
                    logger.info(f"Processed {len(items)} items: {active_count} active, {inactive_count} inactive")
                    logger.info(f"Total value: {total_value}, Average price: {avg_price:.2f}")
                    
                    tasks_processed += 1
                    last_run_time = time.strftime("%Y-%m-%d %H:%M:%S")
                    
                    product_service_calls.labels(endpoint='/items', status='success').inc()
                    worker_task_total.labels(task_type='item_processing', status='success').inc()
                else:
                    logger.error(f"Failed to fetch items: HTTP {response.status_code}")
                    product_service_calls.labels(endpoint='/items', status='error').inc()
                    worker_task_total.labels(task_type='item_processing', status='error').inc()
            
            duration = time.time() - start_time
            worker_task_duration.labels(task_type='item_processing').observe(duration)
            
        except Exception as e:
            logger.error(f"Error in background worker: {str(e)}")
            worker_task_total.labels(task_type='item_processing', status='error').inc()
        
        # Wait before next iteration
        await asyncio.sleep(WORKER_INTERVAL)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

# Readiness check endpoint
@app.get("/ready")
async def readiness_check():
    """Readiness check - verifies connection to product service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PRODUCT_SERVICE_URL}/health", timeout=5.0)
            
            if response.status_code == 200:
                return {
                    "status": "ready",
                    "timestamp": time.time(),
                    "product_service": "connected"
                }
            else:
                raise HTTPException(status_code=503, detail="Product service not available")
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Product service connection failed: {str(e)}")

# Metrics endpoint
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(registry)

# Worker status endpoint
@app.get("/status", response_model=WorkerStatus)
async def get_worker_status():
    """Get worker service status"""
    return WorkerStatus(
        status="running" if background_task_running else "stopped",
        tasks_processed=tasks_processed,
        product_service_url=PRODUCT_SERVICE_URL,
        last_run=last_run_time
    )

# Get item summary from product service
@app.get("/items/summary", response_model=ItemSummary)
async def get_item_summary():
    """Get summary statistics of items from product service"""
    start_time = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PRODUCT_SERVICE_URL}/items", timeout=10.0)
            
            if response.status_code != 200:
                product_service_calls.labels(endpoint='/items', status='error').inc()
                raise HTTPException(status_code=502, detail="Failed to fetch items from product service")
            
            items = response.json()
            
            active_count = sum(1 for item in items if item.get('active', False))
            inactive_count = len(items) - active_count
            total_value = sum(item.get('price', 0) for item in items)
            avg_price = total_value / len(items) if items else 0
            
            product_service_calls.labels(endpoint='/items', status='success').inc()
            
            return ItemSummary(
                total_items=len(items),
                active_items=active_count,
                inactive_items=inactive_count,
                total_value=total_value,
                average_price=round(avg_price, 2)
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting item summary: {str(e)}")
        product_service_calls.labels(endpoint='/items', status='error').inc()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        duration = time.time() - start_time
        worker_task_duration.labels(task_type='item_summary').observe(duration)

# Manually trigger a worker task
@app.post("/tasks/trigger")
async def trigger_task():
    """Manually trigger a worker task"""
    start_time = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PRODUCT_SERVICE_URL}/items", timeout=10.0)
            
            if response.status_code == 200:
                items = response.json()
                
                active_count = sum(1 for item in items if item.get('active', False))
                inactive_count = len(items) - active_count
                
                logger.info(f"Manual task triggered: Processed {len(items)} items")
                
                product_service_calls.labels(endpoint='/items', status='success').inc()
                worker_task_total.labels(task_type='manual_trigger', status='success').inc()
                
                return {
                    "status": "success",
                    "items_processed": len(items),
                    "active": active_count,
                    "inactive": inactive_count
                }
            else:
                product_service_calls.labels(endpoint='/items', status='error').inc()
                worker_task_total.labels(task_type='manual_trigger', status='error').inc()
                raise HTTPException(status_code=502, detail="Failed to fetch items")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manual task: {str(e)}")
        worker_task_total.labels(task_type='manual_trigger', status='error').inc()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        duration = time.time() - start_time
        worker_task_duration.labels(task_type='manual_trigger').observe(duration)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")))