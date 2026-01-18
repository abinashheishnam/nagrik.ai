from pydantic import BaseModel, Field
from typing import Optional

class UserSignup(BaseModel):
    full_name: str = ""
    phone: str = Field(..., min_length=6, max_length=30)
    email: Optional[str] = None
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    identifier: str  # phone or email
    password: str

class AdminLogin(BaseModel):
    username: str
    password: str

class AdminSignup(BaseModel):
    username: str
    password: str
    secret_key: Optional[str] = "admin_secret"  # simple check for demo

class TokenOut(BaseModel):
    access_token: str
    role: str

class UserOut(BaseModel):
    id: int
    full_name: str
    phone: str
    email: Optional[str] = None

    class Config:
        from_attributes = True
