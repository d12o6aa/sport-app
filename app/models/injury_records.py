from datetime import datetime
from app.extensions import db

class InjuryRecord(db.Model):
    __tablename__ = "injury_records"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    injury_type = db.Column(db.String(100))  # e.g., Muscle Strain, Sprained Ankle
    severity = db.Column(db.String(20), db.CheckConstraint("severity IN ('mild','moderate','severe')"))
    imaging_report = db.Column(db.String(100))  # e.g., MRI Moderate
    recovery_strategy = db.Column(db.String(100))  # e.g., Rest and Ice, Stretching
    reported_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    athlete = db.relationship("User", back_populates="injuries")
