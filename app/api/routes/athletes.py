from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from domains.athletes.schemas import AthleteProfileCreate, AthleteProfileOut
from domains.athletes.services import create_athlete_profile
from infrastructure.db.session import get_db

router = APIRouter(prefix="/athletes", tags=["Athletes"])

@router.post("/", response_model=AthleteProfileOut)
def create_profile(profile: AthleteProfileCreate, db: Session = Depends(get_db)):
    return create_athlete_profile(db, profile)
