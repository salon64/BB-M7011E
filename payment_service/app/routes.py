from fastapi import APIRouter, HTTPException, Depends
from supabase import Client
from postgrest.exceptions import APIError
from app.models import PaymentResponse, PaymentRequest
from app.database import get_supabase

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.post("/payments/debit", response_model=PaymentResponse)
async def debit_payment(
    request: PaymentRequest, supabase: Client = Depends(get_supabase)
):
    """Debits a specified amount from a user's account.

    This endpoint processes a payment request by calling the `debit_user` RPC
    function in the database.

    Args:
        request: A `PaymentRequest` object containing the user's ID and the item ID.
        supabase: An injected Supabase client for database communication.

    Returns:
        A `PaymentResponse` object with the user's ID and their new balance.

    """
    try:
        result = supabase.rpc(
            "debit_user",
            {
                "user_id_input": request.user_id,
                "item_input": str(request.item_id),
            },
        ).execute()

        return PaymentResponse(user_id=request.user_id, new_balance=int(result.data))

    except APIError as e:
        error_msg = e.message.lower()

        if "insufficient funds" in error_msg:
            raise HTTPException(status_code=402, detail="Insufficient funds")
        elif "user is not active" in error_msg:
            raise HTTPException(status_code=403, detail="User is not active")
        elif "user not found" in error_msg:
            raise HTTPException(status_code=404, detail="User not found")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {e.message}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )
