from fastapi import FastAPI
from app.config import settings
from app.routes import router
from contextlib import asynccontextmanager
import logging
from app.logging_config import setup_logging
from app.database import supabase_client


setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to handle startup and shutdown events.
    """
    try:
        supabase_client.table("payments").select("id").limit(1).execute()
        logger.info("✓ Supabase connection established successfully")
    except Exception as e:
        logger.error(f"✗ Supabase connection failed: {e}")
    yield
    logger.info("Shutting down payment service.")

app = FastAPI(
    title="Payment Service",
    version="1.0.0",
    description="Handles all payment transactions for Bättre Bosh",
    lifespan=lifespan
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        'main:app', 
        host=settings.host,
        port=settings.service_port,
        reload=True
    )
