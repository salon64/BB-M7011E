from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    Lastname: str
    password: str

class addBalance(BaseModel):
    card_id: int
    amount: int
