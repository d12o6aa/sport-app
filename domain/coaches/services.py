from sqlalchemy.orm import Session
from domains.coaches import models, schemas
from domains.users.models import User, UserRole
from utils.security import hash_password

def create_coach(db: Session, coach_data: schemas.CoachCreate):
    user = User(
        full_name=coach_data.full_name,
        email=coach_data.email,
        hashed_password=hash_password(coach_data.password),
        role=UserRole.coach
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    coach_profile = models.CoachProfile(
        user_id=user.id,
        specialization=coach_data.specialization,
        experience_years=coach_data.experience_years
    )
    db.add(coach_profile)
    db.commit()
    db.refresh(coach_profile)

    return coach_profile
