from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from infrastructure.db.base import Base

class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id = Column(Integer, primary_key=True, index=True)
    athlete_id = Column(Integer, ForeignKey("athlete_profiles.id"), nullable=False)
    performance_class = Column(Integer)
    injury_severity = Column(String)
    recovery_prediction = Column(Integer)
    periodization_phase = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    athlete = relationship("AthleteProfile", backref="predictions")
