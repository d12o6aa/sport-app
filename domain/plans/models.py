from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from infrastructure.db.base import Base

class TrainingLog(Base):
    __tablename__ = "training_logs"

    id = Column(Integer, primary_key=True, index=True)
    athlete_id = Column(Integer, ForeignKey("athlete_profiles.id"), nullable=False)
    coach_id = Column(Integer, ForeignKey("coach_profiles.id"), nullable=True)
    
    training_type = Column(String)      # e.g., Cardio, Strength
    intensity = Column(String)         # e.g., Low, Medium, High
    duration_min = Column(Float)
    notes = Column(String)
    log_date = Column(Date)

    athlete = relationship("AthleteProfile", backref="logs")
    coach = relationship("CoachProfile")



class TrainingProgram(Base):
    __tablename__ = "training_programs"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coach_profiles.id"))
    name = Column(String)
    description = Column(String)
    target_group = Column(String)  # e.g., Beginners, Advanced

    coach = relationship("CoachProfile", backref="programs")
