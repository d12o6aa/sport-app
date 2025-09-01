from datetime import datetime
from app.extensions import db

class AthleteSchedule(db.Model):
    __tablename__ = "athlete_schedule"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    athlete = db.relationship("User", back_populates="schedule")

    __table_args__ = (
        db.Index("idx_schedule_athlete_id", "athlete_id"),
    )
