from datetime import datetime
from app.extensions import db

class AthleteProgress(db.Model):
    __tablename__ = "athlete_progress"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    date = db.Column(db.Date, default=datetime.utcnow, index=True)
    weight = db.Column(db.Float, nullable=True)
    calories_burned = db.Column(db.Float, nullable=True)
    workouts_done = db.Column(db.Integer, default=0)

    athlete = db.relationship("User", back_populates="progress")

    __table_args__ = (
        db.Index("idx_progress_athlete_id", "athlete_id"),
    )
