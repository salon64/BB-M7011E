from fastapi import APIRouter, HTTPException, Depends
from supabase import Client
from postgrest.exceptions import APIError
from app.models import (
    ItemCreate,
    ItemUpdate,
    ItemSetStatus,
    ItemSetStatusResponse,
    FetchItemInfo,
    FetchItemByBarcode,
    ItemInfoResponse,
    ListItemsRequest,
    DeleteItemRequest
)
from common.database import get_supabase
from common.auth import require_auth
import logging
import traceback
from uuid import UUID

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')


router = APIRouter()


@router.get("/auth/jwt")
async def get_decoded_jwt(token_data: dict = Depends(require_auth)):
    """Return the decoded JWT payload for the current request."""
    return token_data


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.post("/items", response_model=dict)
async def create_item(
    request: ItemCreate,
    supabase: Client = Depends(get_supabase),
    user_data: dict = Depends(require_auth),
):
    """
    Create a new item in the database. Requires bb_admin role.
    """
    logger = logging.getLogger("routes")
    logger.info("/items endpoint called with: %s", request.dict())
    
    # Check if user has admin privileges
    is_admin = "bb_admin" in user_data.get("realm_access", {}).get("roles", [])
    if not is_admin:
        logger.warning("Non-admin user attempted to create item")
        raise HTTPException(status_code=403, detail="BB Admin privileges required to create items")
    
    try:
        logger.info("Calling Supabase RPC create_item...")
        result = supabase.rpc(
            "create_item",
            {
                "name_input": request.name,
                "price_input": request.price,
                "barcode_id_input": request.barcode_id,
            },
        ).execute()
        logger.info("Supabase RPC result: %s", result)
        
        item_id = result.data
        return {
            "status": "success",
            "item_id": str(item_id),
            "name": request.name,
            "price": request.price,
            "barcode_id": request.barcode_id
        }
    except Exception as e:
        logger.error("Supabase error: %s", e)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.post("/items/fetch_info", response_model=ItemInfoResponse)
async def fetch_item_info(
    request: FetchItemInfo,
    supabase: Client = Depends(get_supabase),
    user_data: dict = Depends(require_auth),
):
    """
    Fetch item information by item ID. Requires authentication.
    """
    logger = logging.getLogger("routes")
    
    try:
        result = supabase.rpc(
            "fetch_item_info",
            {
                "item_id_input": str(request.item_id),
            },
        ).execute()
        
        item_info = result.data
        
        # Handle empty result
        if not item_info:
            logger.warning("Item not found for item_id=%s", request.item_id)
            raise HTTPException(status_code=404, detail="Item not found")
        
        return ItemInfoResponse(
            id=UUID(item_info['id']),
            name=item_info['name'],
            price=item_info['price'],
            barcode_id=item_info.get('barcode_id'),
            active=item_info['active']
        )
    except APIError as e:
        logger.error("APIError in fetch_item_info: %s", e, exc_info=True)
        error_msg = e.message.lower()
        if "item not found" in error_msg:
            raise HTTPException(status_code=404, detail="Item not found")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {e.message}")
    except Exception as e:
        logger.error("Unexpected error in fetch_item_info: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/items/fetch_by_barcode", response_model=ItemInfoResponse)
async def fetch_item_by_barcode(
    request: FetchItemByBarcode,
    supabase: Client = Depends(get_supabase),
    user_data: dict = Depends(require_auth),
):
    """
    Fetch item information by barcode ID. Only returns active items.
    """
    logger = logging.getLogger("routes")
    
    try:
        result = supabase.rpc(
            "fetch_item_by_barcode",
            {
                "barcode_id_input": request.barcode_id,
            },
        ).execute()
        
        item_info = result.data
        
        if not item_info:
            logger.warning("Item not found for barcode_id=%s", request.barcode_id)
            raise HTTPException(status_code=404, detail="Item not found or inactive")
        
        return ItemInfoResponse(
            id=UUID(item_info['id']),
            name=item_info['name'],
            price=item_info['price'],
            barcode_id=item_info.get('barcode_id'),
            active=item_info['active']
        )
    except APIError as e:
        logger.error("APIError in fetch_item_by_barcode: %s", e, exc_info=True)
        error_msg = e.message.lower()
        if "item not found" in error_msg:
            raise HTTPException(status_code=404, detail="Item not found or inactive")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {e.message}")
    except Exception as e:
        logger.error("Unexpected error in fetch_item_by_barcode: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/items/list")
async def list_items(
    request: ListItemsRequest,
    supabase: Client = Depends(get_supabase),
    user_data: dict = Depends(require_auth),
):
    """
    List all items. Optionally filter by active status.
    """
    logger = logging.getLogger("routes")
    
    try:
        result = supabase.rpc(
            "list_items",
            {
                "active_only": request.active_only,
            },
        ).execute()
        
        items = result.data or []
        
        return {
            "items": items,
            "count": len(items),
            "active_only": request.active_only
        }
    except Exception as e:
        logger.error("Unexpected error in list_items: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.put("/items/update")
async def update_item(
    item_id: UUID,
    request: ItemUpdate,
    supabase: Client = Depends(get_supabase),
    user_data: dict = Depends(require_auth),
):
    """
    Update item information. Requires bb_admin role.
    """
    logger = logging.getLogger("routes")
    
    # Check if user has admin privileges
    is_admin = "bb_admin" in user_data.get("realm_access", {}).get("roles", [])
    if not is_admin:
        logger.warning("Non-admin user attempted to update item")
        raise HTTPException(status_code=403, detail="BB Admin privileges required to update items")
    
    try:
        result = supabase.rpc(
            "update_item",
            {
                "item_id_input": str(item_id),
                "name_input": request.name,
                "price_input": request.price,
                "barcode_id_input": request.barcode_id,
            },
        ).execute()
        
        item_info = result.data
        
        if not item_info:
            raise HTTPException(status_code=404, detail="Item not found")
        
        return {
            "status": "success",
            "item": item_info
        }
    except APIError as e:
        logger.error("APIError in update_item: %s", e, exc_info=True)
        error_msg = e.message.lower()
        if "item not found" in error_msg:
            raise HTTPException(status_code=404, detail="Item not found")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {e.message}")
    except Exception as e:
        logger.error("Unexpected error in update_item: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/items/set_status", response_model=ItemSetStatusResponse)
async def set_item_status(
    request: ItemSetStatus,
    supabase: Client = Depends(get_supabase),
    user_data: dict = Depends(require_auth),
):
    """
    Set an item's active status. Requires bb_admin role.
    """
    logger = logging.getLogger("routes")
    
    # Check if user has admin privileges
    is_admin = "bb_admin" in user_data.get("realm_access", {}).get("roles", [])
    if not is_admin:
        raise HTTPException(status_code=403, detail="BB Admin privileges required to set item status")
    
    try:
        result = supabase.rpc(
            "item_set_status",
            {
                "item_id_input": str(request.item_id),
                "item_status_input": request.item_status,
            },
        ).execute()
        return ItemSetStatusResponse(response=result.data)
    except APIError as e:
        error_msg = e.message.lower()
        if "item not found" in error_msg:
            raise HTTPException(status_code=404, detail="Item not found")
        elif "item status is already active=true" in error_msg:
            raise HTTPException(status_code=400, detail="Item status is already active=TRUE")
        elif "item status is already active=false" in error_msg:
            raise HTTPException(status_code=400, detail="Item status is already active=FALSE")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {e.message}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.delete("/items/delete")
async def delete_item(
    request: DeleteItemRequest,
    supabase: Client = Depends(get_supabase),
    user_data: dict = Depends(require_auth),
):
    """
    Delete (deactivate) an item. Requires bb_admin role.
    """
    logger = logging.getLogger("routes")
    
    # Check if user has admin privileges
    is_admin = "bb_admin" in user_data.get("realm_access", {}).get("roles", [])
    if not is_admin:
        raise HTTPException(status_code=403, detail="BB Admin privileges required to delete items")
    
    try:
        result = supabase.rpc(
            "delete_item",
            {
                "item_id_input": str(request.item_id),
            },
        ).execute()
        
        return {
            "status": "success",
            "message": result.data
        }
    except APIError as e:
        logger.error("APIError in delete_item: %s", e, exc_info=True)
        error_msg = e.message.lower()
        if "item not found" in error_msg:
            raise HTTPException(status_code=404, detail="Item not found")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {e.message}")
    except Exception as e:
        logger.error("Unexpected error in delete_item: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )