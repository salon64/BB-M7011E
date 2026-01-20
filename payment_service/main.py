from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import router
from contextlib import asynccontextmanager
import logging
from app.logging_config import setup_logging
from common.database import get_supabase_client

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to handle startup and shutdown events.
    """
    try:
        supabase_client = get_supabase_client()
        supabase_client.table("Users").select("card_id").limit(1).execute()
        logger.info("✓ Supabase connection established successfully")
    except Exception as e:
        logger.error(f"✗ Supabase connection failed: {e}")
    yield
    logger.info("Shutting down payment service.")


app = FastAPI(
    title="Payment Service",
    version="1.0.0",
    description="Handles all payment transactions for Bättre Bosh",
    lifespan=lifespan,
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins - can be restricted in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.host, port=settings.service_port, reload=True)
