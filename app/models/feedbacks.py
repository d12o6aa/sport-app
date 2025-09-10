from app.extensions import db
from datetime import datetime


class Feedback(db.Model):
    __tablename__ = "feedbacks"

    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("workout_logs.id"), nullable=True)
    content = db.Column(db.Text, nullable=False, server_default="")
    type = db.Column(db.String(50), nullable=True, default="general")  # e.g., performance, nutrition
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    coach = db.relationship("User", foreign_keys=[coach_id])
    athlete = db.relationship("User", foreign_keys=[athlete_id])
    workout = db.relationship("WorkoutLog", backref="feedbacks")

    __table_args__ = (
        db.Index("idx_feedback_coach_athlete", "coach_id", "athlete_id"),
    )