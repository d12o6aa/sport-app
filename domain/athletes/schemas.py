from pydantic import BaseModel
from typing import Optional

class AthleteProfileBase(BaseModel):
    age: Optional[int]
    gender: Optional[str]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    training_experience_years: Optional[float]
    injury_history: Optional[str]

class AthleteProfileCreate(AthleteProfileBase):
    user_id: int

class AthleteProfileOut(AthleteProfileBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True
