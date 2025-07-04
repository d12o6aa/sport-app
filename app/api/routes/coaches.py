from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from infrastructure.db.session import get_db
from domains.coaches import schemas, services

router = APIRouter(prefix="/coaches", tags=["Coaches"])

@router.post("/", response_model=schemas.CoachOut)
def register_coach(coach: schemas.CoachCreate, db: Session = Depends(get_db)):
    return services.create_coach(db, coach)
