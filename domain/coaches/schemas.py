from pydantic import BaseModel, EmailStr
from typing import Optional

class CoachCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    specialization: Optional[str]
    experience_years: Optional[int]

class CoachOut(BaseModel):
    id: int
    full_name: str
    email: str
    specialization: Optional[str]
    experience_years: Optional[int]

    class Config:
        orm_mode = True
