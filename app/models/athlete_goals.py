from datetime import datetime
from app.extensions import db

class AthleteGoal(db.Model):
    __tablename__ = "athlete_goals"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("athlete_profiles.user_id"), nullable=True)

    title = db.Column(db.String(150), nullable=False)
    target_value = db.Column(db.String(150), nullable=False)
    current_value = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(20), default="")   # kg, km, reps
    deadline = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    athlete = db.relationship("User", back_populates="goals")
    athlete_profile = db.relationship("AthleteProfile", back_populates="goals")
    
    __table_args__ = (
        db.Index("idx_goals_athlete_id", "athlete_id"),
    )
