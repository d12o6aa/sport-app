from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from infrastructure.db.base import Base

class CoachProfile(Base):
    __tablename__ = "coach_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    specialization = Column(String)
    experience_years = Column(Integer)

    user = relationship("User", backref="coach_profile")
