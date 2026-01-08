import traceback
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from supabase import Client
from postgrest.exceptions import APIError
from app.models import PaymentResponse, PaymentRequest
from common.database import get_supabase
from common.auth import require_auth
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.get("/auth/jwt")
async def get_decoded_jwt(token_data: dict = Depends(require_auth)):
    """Return the decoded JWT payload for the current request."""
    return token_data

@router.get("/transactions/history", response_model=dict)
async def get_transaction_history(
    user_id: int = None,
    limit: int = 100,
    offset: int = 0,
    supabase: Client = Depends(get_supabase),
    user_data: dict = Depends(require_auth),
):
    """
    Get transaction history. 
    - Regular users can only see their own transactions
    - Admins and service accounts can see all transactions or filter by user_id
    """
    logger = logging.getLogger("routes")
    logger.info("/transactions/history endpoint called")
    
    # Check if user is admin or service account
    is_admin = "bb_admin" in user_data.get("realm_access", {}).get("roles", [])
    is_service_account = user_data.get("preferred_username", "").startswith("service-account-")
    
    # Try to get numeric user ID from preferred_username
    try:
        current_user_id = int(user_data.get("preferred_username", -1))
    except (ValueError, TypeError):
        current_user_id = -1
    
    logger.info("USER DATA: %s", user_data)

    # Authorization logic
    if is_admin or is_service_account:
        # Admins and service accounts can query any user or all users
        if user_id is None:
            # Return all transactions
            logger.info("Admin/service account requesting all transactions")
            query_user_id = None
        else:
            # Return specific user's transactions
            logger.info("Admin/service account requesting transactions for user %s", user_id)
            query_user_id = user_id
    else:
        # Regular users can only see their own transactions
        if user_id is not None and user_id != current_user_id:
            logger.warning("User %s attempted to access transactions for user %s", current_user_id, user_id)
            raise HTTPException(status_code=403, detail="Cannot access another user's transaction history")
        query_user_id = current_user_id
        logger.info("Regular user %s requesting own transactions", current_user_id)
    
    try:
        # Build query
        query = supabase.table("Transaction_History").select("*")
        
        # Apply user filter if specified
        if query_user_id is not None:
            query = query.eq("user", query_user_id)
        
        # Apply ordering, limit, and offset
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        
        result = query.execute()
        
        logger.info("Retrieved %s transactions", len(result.data))
        
        return {
            "status": "success",
            "transactions": result.data,
            "count": len(result.data),
            "limit": limit,
            "offset": offset,
            "user_id": query_user_id
        }
        
    except APIError as e:
        logger.error("Database error: %s", e)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.get("/transactions/history/{transaction_id}", response_model=dict)
async def get_transaction_by_id(
    transaction_id: UUID,
    supabase: Client = Depends(get_supabase),
    user_data: dict = Depends(require_auth),
):
    """
    Get a specific transaction by ID.
    - Regular users can only see their own transactions
    - Admins and service accounts can see any transaction
    """
    logger = logging.getLogger("routes")
    logger.info("/transactions/history/%s endpoint called", transaction_id)
    
    # Check if user is admin or service account
    is_admin = "bb_admin" in user_data.get("realm_access", {}).get("roles", [])
    is_service_account = user_data.get("preferred_username", "").startswith("service-account-")
    
    # Try to get numeric user ID from preferred_username
    try:
        current_user_id = int(user_data.get("preferred_username", -1))
    except (ValueError, TypeError):
        current_user_id = -1
    
    try:
        # Fetch the transaction
        result = supabase.table("Transaction_History").select("*").eq("id", str(transaction_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        transaction = result.data[0]
        
        # Authorization check - regular users can only see their own transactions
        if not (is_admin or is_service_account):
            if transaction["user"] != current_user_id:
                logger.warning("User %s attempted to access transaction for user %s", 
                             current_user_id, transaction["user"])
                raise HTTPException(status_code=403, detail="Cannot access another user's transaction")
        
        logger.info("Retrieved transaction %s", transaction_id)
        
        return {
            "status": "success",
            "transaction": transaction
        }
        
    except HTTPException:
        raise
    except APIError as e:
        logger.error("Database error: %s", e)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@router.post("/payments/debit", response_model=PaymentResponse)
async def debit_payment(
    request: PaymentRequest,
    user_data: dict = Depends(require_auth),
    supabase: Client = Depends(get_supabase),
):
    logger = logging.getLogger("routes")

    logger.debug(
        "Debit request received | user_id=%s item_id=%s caller=%s",
        request.user_id,
        request.item_id,
        user_data.get("preferred_username"),
    )

    if request.user_id != int(user_data.get("preferred_username", -1)) and \
       "bb_admin" not in user_data.get("realm_access", {}).get("roles", []):
        logger.warning(
            "Unauthorized debit attempt | target_user=%s caller=%s roles=%s",
            request.user_id,
            user_data.get("preferred_username"),
            user_data.get("realm_access", {}).get("roles", []),
        )
        raise HTTPException(status_code=403, detail="Cannot debit another user's account")

    try:
        logger.debug(
            "Calling debit_user RPC | user_id=%s item_id=%s",
            request.user_id,
            request.item_id,
        )

        result = supabase.rpc(
            "debit_user",
            {
                "user_id_input": request.user_id,
                "item_input": str(request.item_id),
            },
        ).execute()

        logger.info(
            "Debit successful | user_id=%s new_balance=%s",
            request.user_id,
            result.data,
        )

        return PaymentResponse(
            user_id=request.user_id,
            new_balance=int(result.data),
        )

    except APIError as e:
        error_msg = e.message.lower()
        logger.error(
            "Database error during debit | user_id=%s error=%s",
            request.user_id,
            e.message,
            exc_info=True,
        )

        if "insufficient funds" in error_msg:
            raise HTTPException(status_code=402, detail="Insufficient funds")
        elif "user is not active" in error_msg:
            raise HTTPException(status_code=403, detail="User is not active")
        elif "user not found" in error_msg:
            raise HTTPException(status_code=404, detail="User not found")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {e.message}")

    except Exception as e:
        logger.critical(
            "Unexpected error during debit | user_id=%s",
            request.user_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred",
        )


# @router.post("/payments/debit", response_model=PaymentResponse)
# async def debit_payment(
#     request: PaymentRequest,
#     user_data: dict = Depends(require_auth),
#     supabase: Client = Depends(get_supabase),
# ):
#     """Debits a specified amount from a user's account.

#     This endpoint processes a payment request by calling the `debit_user` RPC
#     function in the database.

#     Args:
#         request: A `PaymentRequest` object containing the user's ID and the item ID.
#         user_data: A dictionary containing authenticated user information.
#         supabase: An injected Supabase client for database communication.

#     Returns:
#         A `PaymentResponse` object with the user's ID and their new balance.

#     """

#     if request.user_id != int(user_data.get("preferred_username", -1)) and "bb_admin" not in user_data.get("realm_access", {}).get("roles", []):
#         raise HTTPException(status_code=403, detail="Cannot debit another user's account")
#     try:
#         result = supabase.rpc(
#             "debit_user",
#             {
#                 "user_id_input": request.user_id,
#                 "item_input": str(request.item_id),
#             },
#         ).execute()

#         return PaymentResponse(user_id=request.user_id, new_balance=int(result.data))

#     except APIError as e:
#         error_msg = e.message.lower()

#         if "insufficient funds" in error_msg:
#             raise HTTPException(status_code=402, detail="Insufficient funds")
#         elif "user is not active" in error_msg:
#             raise HTTPException(status_code=403, detail="User is not active")
#         elif "user not found" in error_msg:
#             raise HTTPException(status_code=404, detail="User not found")
#         else:
#             raise HTTPException(status_code=500, detail=f"Database error: {e.message}")
#     except Exception as e:
#         raise HTTPException(
#             status_code=500, detail=f"An unexpected error occurred: {str(e)}"
#         )
