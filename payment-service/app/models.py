from pydantic import BaseModel, Field

class PaymentRequest(BaseModel):
    """Represents the request body for a debit payment.

    Attributes:
        user_id: The unique identifier for the user.
        amount: The positive integer amount to be debited.
    """
    user_id: str
    amount: int = Field(..., gt=0, description="Amount to debit")

class PaymentResponse(BaseModel):
    """Represents the successful response for a debit payment.

    Attributes:
        user_id: The unique identifier for the user.
        new_balance: The user's balance after the debit was applied.
    """
    user_id: str
    new_balance: int