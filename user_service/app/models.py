from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    Lastname: str
    password: str

class addBalance(BaseModel):
    card_id: int
    amount: int

class user_set_status(BaseModel):
    user_id_input: str
    user_status_input: bool

class user_set_status_response(BaseModel):
    response: str

class fetch_user_info(BaseModel):
    user_id: int

