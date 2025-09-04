from datetime import datetime
from app.extensions import db

class WorkoutSession(db.Model):
    __tablename__ = "workout_sessions"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("training_plans.id"), nullable=True)
    name = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(50))  # e.g. cardio, strength
    duration = db.Column(db.Integer)  # minutes
    calories = db.Column(db.Integer)
    performed_at = db.Column(db.DateTime, default=datetime.utcnow)

    athlete = db.relationship("User", back_populates="workout_logs")
    plan = db.relationship("TrainingPlan", back_populates="assignments")
