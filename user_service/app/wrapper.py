"""
Request Wrapper/Proxy Service

Listens on a separate port and intercepts all incoming requests.
Allows modification of requests before forwarding to the main service or other destinations.
"""

import os
import logging
import httpx
from typing import Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

# Logging setup
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"time":"%(asctime)s","level":"%(levelname)s",'
           '"message":"%(message)s","name":"%(name)s"}',
)
logger = logging.getLogger(__name__)

# Configuration
WRAPPER_PORT = int(os.getenv("WRAPPER_PORT", "8002"))
TARGET_HOST = os.getenv("TARGET_HOST", "http://localhost:8000")  # Main FastAPI service
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30.0"))

app = FastAPI(
    title="User Service Wrapper",
    description="Request interceptor/proxy for user service",
    version="1.0.0",
)


async def modify_request(
    method: str,
    path: str,
    headers: dict,
    query_params: dict,
    body: Optional[bytes]
) -> tuple[str, str, dict, dict, Optional[bytes]]:
    """
    Modify the incoming request before forwarding.
    
    Override this function to implement custom request transformation logic.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        path: Request path
        headers: Request headers (mutable)
        query_params: Query parameters (mutable)
        body: Request body (can be modified)
    
    Returns:
        Tuple of (method, path, headers, query_params, body)
    """
    # Example modifications (customize as needed):
    
    # 1. Add custom headers
    headers["X-Forwarded-By"] = "user-service-wrapper"
    headers["X-Original-Path"] = path
    
    # 2. Log the request
    logger.info(f"📥 Intercepted: {method} {path}")
    
    # 3. You can modify the path
    # if path.startswith("/api/v1"):
    #     path = path.replace("/api/v1", "/api/v2")
    
    # 4. You can modify query params
    # query_params["wrapper_processed"] = "true"
    
    # 5. You can modify the body (for POST/PUT/PATCH)
    # if body and method in ["POST", "PUT", "PATCH"]:
    #     import json
    #     try:
    #         data = json.loads(body)
    #         data["modified_by_wrapper"] = True
    #         body = json.dumps(data).encode()
    #     except json.JSONDecodeError:
    #         pass
    
    return method, path, headers, query_params, body


async def modify_response(
    status_code: int,
    headers: dict,
    body: bytes
) -> tuple[int, dict, bytes]:
    """
    Modify the response before returning to client.
    
    Override this function to implement custom response transformation logic.
    
    Args:
        status_code: HTTP status code
        headers: Response headers (mutable)
        body: Response body
    
    Returns:
        Tuple of (status_code, headers, body)
    """
    # Example: Add wrapper header to response
    headers["X-Processed-By"] = "user-service-wrapper"
    
    return status_code, headers, body


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def catch_all(request: Request, path: str):
    """
    Catch-all route that intercepts all requests.
    
    1. Captures the incoming request
    2. Allows modification via modify_request()
    3. Forwards to the target service
    4. Allows modification of response via modify_response()
    5. Returns the response to the client
    """
    try:
        # Extract request details
        method = request.method
        
        # Get headers (convert to mutable dict, exclude hop-by-hop headers)
        excluded_headers = {"host", "content-length", "transfer-encoding", "connection"}
        headers = {
            k: v for k, v in request.headers.items() 
            if k.lower() not in excluded_headers
        }
        
        # Get query parameters
        query_params = dict(request.query_params)
        
        # Get body
        body = await request.body() if method in ["POST", "PUT", "PATCH"] else None
        
        # Modify request
        method, path, headers, query_params, body = await modify_request(
            method, path, headers, query_params, body
        )
        
        # Build target URL
        target_url = f"{TARGET_HOST}/{path}"
        
        logger.info(f"🔄 Forwarding to: {method} {target_url}")
        
        # Forward the request
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                params=query_params,
                content=body,
            )
        
        # Get response details
        response_headers = dict(response.headers)
        response_body = response.content
        
        # Remove hop-by-hop headers from response
        for header in ["content-encoding", "transfer-encoding", "content-length"]:
            response_headers.pop(header, None)
        
        # Modify response
        status_code, response_headers, response_body = await modify_response(
            response.status_code, response_headers, response_body
        )
        
        logger.info(f"📤 Response: {status_code}")
        
        return Response(
            content=response_body,
            status_code=status_code,
            headers=response_headers,
            media_type=response_headers.get("content-type", "application/json"),
        )
        
    except httpx.ConnectError as e:
        logger.error(f"❌ Connection error to {TARGET_HOST}: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "error": "Service Unavailable",
                "message": f"Could not connect to target service: {TARGET_HOST}",
            }
        )
    except httpx.TimeoutException as e:
        logger.error(f"⏱️ Timeout connecting to {TARGET_HOST}: {e}")
        return JSONResponse(
            status_code=504,
            content={
                "error": "Gateway Timeout",
                "message": "Target service did not respond in time",
            }
        )
    except Exception as e:
        logger.error(f"❌ Error processing request: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": str(e),
            }
        )


@app.get("/")
async def root_catch_all(request: Request):
    """Handle root path separately"""
    return await catch_all(request, "")


# Health check endpoint (not forwarded)
@app.get("/_wrapper/health")
async def health_check():
    """Health check for the wrapper service itself"""
    return {
        "status": "healthy",
        "service": "user_service_wrapper",
        "target": TARGET_HOST,
        "port": WRAPPER_PORT,
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"🚀 Starting Wrapper Service on port {WRAPPER_PORT}")
    logger.info(f"📡 Forwarding requests to: {TARGET_HOST}")
    
    uvicorn.run(app, host="0.0.0.0", port=WRAPPER_PORT)
