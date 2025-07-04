from sqlalchemy import Column, String, Integer, Boolean, Enum, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum

from infrastructure.db.base import Base  # لو انتِ مستخدمة base.py لتعريف Base

class UserRole(enum.Enum):
    admin = "admin"
    coach = "coach"
    athlete = "athlete"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.athlete)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
