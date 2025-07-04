from pydantic import BaseModel, EmailStr
from enum import Enum

class UserRole(str, Enum):
    admin = "admin"
    coach = "coach"
    athlete = "athlete"

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: UserRole

class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool

    class Config:
        orm_mode = True
