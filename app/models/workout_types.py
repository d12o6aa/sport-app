from app.extensions import db
from datetime import datetime

class WorkoutType(db.Model):
    __tablename__ = "workout_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.Index("idx_workout_types_name", "name"),)
    # Relationships
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    creator = db.relationship("User", back_populates="workout_types")
    training_plans = db.relationship("TrainingPlan", back_populates="workout_type", cascade="all, delete-orphan")