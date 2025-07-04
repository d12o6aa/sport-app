from sqlalchemy.orm import Session
from .models import AthleteProfile
from .schemas import AthleteProfileCreate

def create_athlete_profile(db: Session, profile_data: AthleteProfileCreate):
    profile = AthleteProfile(**profile_data.dict())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile
