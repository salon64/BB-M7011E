from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class ItemCreate(BaseModel):
    """Model for creating a new item"""

    name: str = Field(..., min_length=1, description="Item name")
    price: int = Field(..., ge=0, description="Item price in smallest currency unit")
    barcode_id: Optional[int] = Field(None, description="Optional barcode ID")


class ItemUpdate(BaseModel):
    """Model for updating an existing item"""

    name: Optional[str] = Field(None, min_length=1, description="Item name")
    price: Optional[int] = Field(None, ge=0, description="Item price")
    barcode_id: Optional[int] = Field(None, description="Barcode ID")


class ItemSetStatus(BaseModel):
    """Model for setting item active status"""

    item_id: UUID = Field(..., description="Item UUID")
    item_status: bool = Field(..., description="Active status")


class ItemSetStatusResponse(BaseModel):
    """Response model for set status operation"""

    response: str


class FetchItemInfo(BaseModel):
    """Model for fetching item info by ID"""

    item_id: UUID = Field(..., description="Item UUID")


class FetchItemByBarcode(BaseModel):
    """Model for fetching item info by barcode"""

    barcode_id: int = Field(..., description="Barcode ID")


class ItemInfoResponse(BaseModel):
    """Response model for item information"""

    id: UUID
    name: str
    price: int
    barcode_id: Optional[int]
    active: bool


class ListItemsRequest(BaseModel):
    """Model for listing items"""

    active_only: bool = Field(True, description="Only return active items")


class DeleteItemRequest(BaseModel):
    """Model for deleting (deactivating) an item"""

    item_id: UUID = Field(..., description="Item UUID to delete")
