from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.config import settings
import logging
from contextlib import asynccontextmanager

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=" * 80)
    logger.info("ITEM SERVICE STARTUP")
    logger.info("=" * 80)
    logger.info(f"Service Name: {settings.service_name}")
    logger.info(f"Service Version: 1.0.0")
    logger.info(f"Host: {settings.host}:{settings.service_port}")
    logger.info(f"Log Level: {settings.log_level}")
    
    # Log all registered routes
    logger.info("Registered Routes:")
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            logger.info(f"  {route.methods} {route.path}")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("Item Service shutting down...")

app = FastAPI(
    title="Item Service API",
    description="API for managing items in the BBosch system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)

@app.get("/")
async def root():
    return {
        "service": settings.service_name,
        "status": "running",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting {settings.service_name} on {settings.host}:{settings.service_port}")
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.service_port,
        log_level=settings.log_level.lower()
    )