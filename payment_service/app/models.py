from pydantic import BaseModel, Field
from uuid import UUID


class PaymentRequest(BaseModel):
    """Represents the request body for a debit payment.

    Attributes:
        user_id: The unique identifier for the user.
        item_id: The unique identifier for the item being purchased.
    """

    user_id: int
    item_id: UUID = Field(
        ..., description="The unique identifier for the item being purchased"
    )


class PaymentResponse(BaseModel):
    """Represents the successful response for a debit payment.

    Attributes:
        user_id: The unique identifier for the user.
        new_balance: The user's balance after the debit was applied.
    """

    user_id: int
    new_balance: int
