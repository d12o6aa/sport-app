from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from domains.users.schemas import UserCreate, UserOut
from domains.users.services import create_user
from infrastructure.db.session import get_db

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserOut)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user)
