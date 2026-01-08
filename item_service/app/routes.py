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
        logger.info("Inserting item into Items table...")
        result = supabase.table("Items").insert({
            "name": request.name,
            "price": request.price,
            "barcode_id": request.barcode_id,
        }).execute()
        logger.info("Insert result: %s", result)
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create item")
        
        item = result.data[0]
        return {
            "status": "success",
            "item_id": str(item["id"]),
            "name": item["name"],
            "price": item["price"],
            "barcode_id": item.get("barcode_id")
        }
    except Exception as e:
        logger.error("Database error: %s", e)
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
        result = supabase.table("Items").select("*").eq("id", str(request.item_id)).execute()
        
        if not result.data:
            logger.warning("Item not found for item_id=%s", request.item_id)
            raise HTTPException(status_code=404, detail="Item not found")
        
        item_info = result.data[0]
        
        return ItemInfoResponse(
            id=UUID(item_info['id']),
            name=item_info['name'],
            price=item_info['price'],
            barcode_id=item_info.get('barcode_id'),
            active=item_info['active']
        )
    except HTTPException:
        raise
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
        result = supabase.table("Items").select("*").eq("barcode_id", request.barcode_id).eq("active", True).execute()
        
        if not result.data:
            logger.warning("Item not found for barcode_id=%s", request.barcode_id)
            raise HTTPException(status_code=404, detail="Item not found or inactive")
        
        item_info = result.data[0]
        
        return ItemInfoResponse(
            id=UUID(item_info['id']),
            name=item_info['name'],
            price=item_info['price'],
            barcode_id=item_info.get('barcode_id'),
            active=item_info['active']
        )
    except HTTPException:
        raise
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
        query = supabase.table("Items").select("*")
        
        if request.active_only:
            query = query.eq("active", True)
        
        result = query.execute()
        
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
        # Build update data, only including non-None fields
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.price is not None:
            update_data["price"] = request.price
        if request.barcode_id is not None:
            update_data["barcode_id"] = request.barcode_id
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        result = supabase.table("Items").update(update_data).eq("id", str(item_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Item not found")
        
        return {
            "status": "success",
            "item": result.data[0]
        }
    except HTTPException:
        raise
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
        # First check current status
        check_result = supabase.table("Items").select("active").eq("id", str(request.item_id)).execute()
        
        if not check_result.data:
            raise HTTPException(status_code=404, detail="Item not found")
        
        current_status = check_result.data[0]["active"]
        if current_status == request.item_status:
            status_str = "TRUE" if request.item_status else "FALSE"
            raise HTTPException(status_code=400, detail=f"Item status is already active={status_str}")
        
        # Update the status
        result = supabase.table("Items").update({"active": request.item_status}).eq("id", str(request.item_id)).execute()
        
        return ItemSetStatusResponse(response=f"Item status updated to active={request.item_status}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in set_item_status: %s", e, exc_info=True)
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
        # Soft delete - set active to false
        result = supabase.table("Items").update({"active": False}).eq("id", str(request.item_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Item not found")
        
        return {
            "status": "success",
            "message": "Item deleted (deactivated) successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in delete_item: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )