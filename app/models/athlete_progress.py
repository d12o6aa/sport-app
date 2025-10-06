from app.extensions import db
from datetime import datetime

class AthleteProgress(db.Model):
    __tablename__ = "athlete_progress"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    progress = db.Column(db.Text, nullable=True)
    weight = db.Column(db.Float, nullable=True)
    weight_goal = db.Column(db.Float, nullable=True)
    calories_burned = db.Column(db.Float, nullable=True)
    workouts_done = db.Column(db.Integer, default=0)
    heart_rate = db.Column(db.Float, nullable=True)
    bmi = db.Column(db.Float, nullable=True)
    body_fat = db.Column(db.Float, nullable=True)
    muscle_mass = db.Column(db.Float, nullable=True)
    protein = db.Column(db.Float, nullable=True)
    carbs = db.Column(db.Float, nullable=True)
    fats = db.Column(db.Float, nullable=True)

    athlete = db.relationship("User", back_populates="progress")

    __table_args__ = (
        db.Index("idx_progress_athlete_id", "athlete_id"),
    )