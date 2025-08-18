from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from app.extensions import db

class WorkoutLog(db.Model):
    __tablename__ = "workout_logs"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    workout_details = db.Column(JSONB, server_default="{}", default=dict)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    date = db.Column(db.Date, default=datetime.utcnow, index=True)
    session_type = db.Column(db.String(50), nullable=False)  # e.g., strength, cardio
    duration = db.Column(db.Integer)  # minutes
    metrics = db.Column(JSONB, default={})  # sprint_time, jump_height, HRV...
    feedback = db.Column(db.Text, nullable=True)
    compliance_status = db.Column(
        db.String(20),
        db.CheckConstraint("compliance_status IN ('completed','missed','partial')"),
        default="completed"
    )
    athlete = db.relationship("User", back_populates="workout_logs")

    __table_args__ = (
        db.Index("idx_workout_logs_athlete_id", "athlete_id"),
    )
