from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .models import User
from .schemas import UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)

def create_user(db: Session, user_data: UserCreate):
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        password_hash=hashed_password,
        role=user_data.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
