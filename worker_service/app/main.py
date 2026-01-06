# worker_service/app/main.py
import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager

import aio_pika
from aio_pika import IncomingMessage
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest, CollectorRegistry

# Logging setup
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"time":"%(asctime)s","level":"%(levelname)s",'
    '"message":"%(message)s","name":"%(name)s"}',
)
logger = logging.getLogger(__name__)

# Prometheus metrics
registry = CollectorRegistry()

messages_received_total = Counter(
    "messages_received_total",
    "Total messages received from RabbitMQ",
    ["operation", "status"],
    registry=registry,
)

message_processing_duration = Histogram(
    "message_processing_duration_seconds",
    "Duration of message processing",
    ["operation"],
    registry=registry,
)

queue_size = Histogram(
    "queue_processing_size",
    "Number of messages in queue",
    ["queue_name"],
    registry=registry,
)

# Global variables
worker_tasks = []
message_log = []  # In-memory log for the last 1000 messages





async def process_create_item(message_data: dict):
    """Process item creation - TEMP: Just logs the message"""
    logger.info("=" * 80)
    logger.info("📦 CREATE ITEM REQUEST")
    logger.info(f"Message ID: {message_data.get('message_id')}")
    logger.info(f"Item Data: {json.dumps(message_data.get('data'), indent=2)}")
    logger.info(f"Timestamp: {message_data.get('timestamp')}")
    logger.info("=" * 80)
    
    # TODO: Forward to Supabase
    # Example:
    # from database import get_supabase_client
    # item_data = message_data["data"]
    # item_data["active"] = True
    # response = get_supabase_client().table("Items").insert(item_data).execute()
    
    # For now, just simulate processing
    await asyncio.sleep(0.1)
    return True


async def process_get_item(message_data: dict):
    """Process single item retrieval - TEMP: Just logs the message"""
    logger.info("=" * 80)
    logger.info("🔍 GET ITEM REQUEST")
    logger.info(f"Message ID: {message_data.get('message_id')}")
    logger.info(f"Item ID: {message_data.get('item_id')}")
    logger.info(f"Timestamp: {message_data.get('timestamp')}")
    logger.info("=" * 80)
    
    # TODO: Forward to Supabase
    # Example:
    # from database import get_supabase_client
    # item_id = message_data["item_id"]
    # response = get_supabase_client().table("Items").select("*").eq("id", item_id).execute()
    
    await asyncio.sleep(0.05)
    return True


async def process_list_items(message_data: dict):
    """Process list items request - TEMP: Just logs the message"""
    logger.info("=" * 80)
    logger.info("📋 LIST ITEMS REQUEST")
    logger.info(f"Message ID: {message_data.get('message_id')}")
    logger.info(f"Filters: {json.dumps(message_data.get('filters', {}), indent=2)}")
    logger.info(f"Timestamp: {message_data.get('timestamp')}")
    logger.info("=" * 80)
    
    # TODO: Forward to Supabase
    # Example:
    # from database import get_supabase_client
    # filters = message_data.get("filters", {})
    # query = get_supabase_client().table("Items").select("*")
    # if "active" in filters:
    #     query = query.eq("active", filters["active"])
    # response = query.order("name", desc=False).execute()
    
    await asyncio.sleep(0.05)
    return True


async def process_update_item(message_data: dict):
    """Process item update - TEMP: Just logs the message"""
    logger.info("=" * 80)
    logger.info("✏️  UPDATE ITEM REQUEST")
    logger.info(f"Message ID: {message_data.get('message_id')}")
    logger.info(f"Item ID: {message_data.get('item_id')}")
    logger.info(f"Update Data: {json.dumps(message_data.get('data'), indent=2)}")
    logger.info(f"Timestamp: {message_data.get('timestamp')}")
    logger.info("=" * 80)
    
    # TODO: Forward to Supabase
    # Example:
    # from database import get_supabase_client
    # item_id = message_data["item_id"]
    # update_data = message_data["data"]
    # response = get_supabase_client().table("Items").update(update_data).eq("id", item_id).execute()
    
    await asyncio.sleep(0.1)
    return True


async def process_delete_item(message_data: dict):
    """Process item deletion - TEMP: Just logs the message"""
    delete_type = "HARD DELETE" if message_data.get('hard_delete') else "SOFT DELETE"
    logger.info("=" * 80)
    logger.info(f"🗑️  DELETE ITEM REQUEST ({delete_type})")
    logger.info(f"Message ID: {message_data.get('message_id')}")
    logger.info(f"Item ID: {message_data.get('item_id')}")
    logger.info(f"Hard Delete: {message_data.get('hard_delete')}")
    logger.info(f"Timestamp: {message_data.get('timestamp')}")
    logger.info("=" * 80)
    
    # TODO: Forward to Supabase
    # Example:
    # from database import get_supabase_client
    # item_id = message_data["item_id"]
    # hard_delete = message_data.get("hard_delete", False)
    # if hard_delete:
    #     get_supabase_client().table("Items").delete().eq("id", item_id).execute()
    # else:
    #     get_supabase_client().table("Items").update({"active": False}).eq("id", item_id).execute()
    
    await asyncio.sleep(0.1)
    return True


async def process_message(message: IncomingMessage):
    """Process incoming RabbitMQ message"""
    start_time = time.time()
    async with message.process():
        try:
            message_data = json.loads(message.body.decode())
            operation = message_data.get("operation", "unknown")
            message_id = message_data.get("message_id", "unknown")

            logger.info(
                f"⚡ Processing message - ID: {message_id}, "
                f"Operation: {operation}, Queue: {message.routing_key}"
            )

            # Store in memory log
            log_entry = {
                "message_id": message_id,
                "operation": operation,
                "routing_key": message.routing_key,
                "timestamp": time.time(),
                "data": message_data,
            }
            message_log.append(log_entry)
            if len(message_log) > 1000:
                message_log.pop(0)

            # Route to appropriate handler
            success = False
            if operation == "create":
                success = await process_create_item(message_data)
            elif operation == "get":
                success = await process_get_item(message_data)
            elif operation == "list":
                success = await process_list_items(message_data)
            elif operation == "update":
                success = await process_update_item(message_data)
            elif operation == "delete":
                success = await process_delete_item(message_data)
            else:
                logger.warning(f"⚠️  Unknown operation: {operation}")
                success = False

            status = "success" if success else "error"
            messages_received_total.labels(operation=operation, status=status).inc()
            
            if success:
                logger.info(f"✅ Message processed successfully: {message_id}")
            else:
                logger.error(f"❌ Message processing failed: {message_id}")

        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in message: {str(e)}")
            messages_received_total.labels(operation="unknown", status="error").inc()
        except Exception as e:
            logger.error(f"❌ Error processing message: {str(e)}")
            messages_received_total.labels(operation="unknown", status="error").inc()
        finally:
            duration = time.time() - start_time
            operation = message_data.get("operation", "unknown") if 'message_data' in locals() else "unknown"
            message_processing_duration.labels(operation=operation).observe(duration)


async def consume_from_queue(queue_name: str, channel):
    """Consume messages from a specific queue"""
    try:
        queue = await channel.get_queue(queue_name)
        
        logger.info(f"📡 Started consuming from queue: {queue_name}")
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await process_message(message)
                
    except Exception as e:
        logger.error(f"❌ Error consuming from queue {queue_name}: {str(e)}")
        raise


async def start_consumers():
    """Start all queue consumers"""
    rabbitmq_url = os.getenv(
        "RABBITMQ_URL",
        "amqp://guest:guest@rabbitmq-service:5672/"
    )
    
    while True:
        try:
            logger.info(f"🔌 Connecting to RabbitMQ: {rabbitmq_url}")
            connection = await aio_pika.connect_robust(
                rabbitmq_url,
                timeout=30,
            )
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=10)

            # Declare exchange and queues
            exchange = await channel.declare_exchange(
                "items_exchange",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )

            queues = [
                "items.create",
                "items.get",
                "items.list",
                "items.update",
                "items.delete",
            ]

            for queue_name in queues:
                queue = await channel.declare_queue(queue_name, durable=True)
                await queue.bind(exchange, routing_key=queue_name)
                
                # Create a consumer task for each queue
                task = asyncio.create_task(consume_from_queue(queue_name, channel))
                worker_tasks.append(task)

            logger.info("🚀 Worker service started - consuming messages from all queues")
            
            # Wait for all tasks
            await asyncio.gather(*worker_tasks)

        except aio_pika.exceptions.AMQPConnectionError as e:
            logger.error(f"❌ RabbitMQ connection error: {str(e)}")
            logger.info("⏳ Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"❌ Unexpected error in consumer: {str(e)}")
            logger.info("⏳ Retrying in 5 seconds...")
            await asyncio.sleep(5)


# FastAPI app for health checks and metrics
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Worker Service")
    consumer_task = asyncio.create_task(start_consumers())
    worker_tasks.append(consumer_task)
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down Worker Service")
    for task in worker_tasks:
        task.cancel()
    await asyncio.gather(*worker_tasks, return_exceptions=True)


app = FastAPI(
    title="Worker Service",
    description="Background worker for processing item operations from RabbitMQ",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "worker_service",
        "timestamp": time.time()
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    return {
        "status": "ready",
        "service": "worker_service",
        "active_tasks": len(worker_tasks),
        "timestamp": time.time()
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(registry)


@app.get("/messages")
async def get_messages(limit: int = 50):
    """Get recent messages processed"""
    return {
        "total_processed": len(message_log),
        "messages": message_log[-limit:]
    }


@app.get("/stats")
async def get_stats():
    """Get processing statistics"""
    stats = {
        "total_messages": len(message_log),
        "by_operation": {},
        "by_status": {"success": 0, "error": 0}
    }

    for msg in message_log:
        operation = msg.get("operation", "unknown")
        stats["by_operation"][operation] = stats["by_operation"].get(operation, 0) + 1

    return stats


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")))