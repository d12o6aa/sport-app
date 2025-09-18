# في ملف جديد مثل app/models/goal_progress_log.py
from app.extensions import db
from datetime import datetime

class GoalProgressLog(db.Model):
    __tablename__ = "goal_progress_logs"

    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("athlete_goals.id"), nullable=False)
    progress = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_value = db.Column(db.Float, nullable=False)
    

    goal = db.relationship("AthleteGoal", back_populates="progress_logs")