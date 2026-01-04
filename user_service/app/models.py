from pydantic import BaseModel

class UserCreate(BaseModel):
    card_id: int
    first_name: str
    last_name: str
    email: str
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

class UserInfoResponse(BaseModel):
    first_name: str
    last_name: str
    balance: int
    active: bool
