from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from app.extensions import db

class WorkoutLog(db.Model):
    __tablename__ = "workout_logs"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    workout_details = db.Column(JSONB, server_default="{}", default=dict)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    athlete = db.relationship("User", back_populates="workout_logs")

    __table_args__ = (
        db.Index("idx_workout_logs_athlete_id", "athlete_id"),
    )
