from datetime import datetime
from app.extensions import db

class HealthRecord(db.Model):
    __tablename__ = "health_records"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    heart_rate = db.Column(db.Integer)
    calories_intake = db.Column(db.Integer)
    sleep_hours = db.Column(db.Float)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    protein = db.Column(db.Float)
    carbs = db.Column(db.Float)
    fats = db.Column(db.Float)
    calories_burned = db.Column(db.Integer)
    steps = db.Column(db.Integer)

    
    bp_dia = db.Column(db.Integer)   # diastolic
    bp_sys = db.Column(db.Integer)   # systolic
    hydration = db.Column(db.Float)  # liters of water
    mood = db.Column(db.Integer)     # 1-5 scale
    stress_level = db.Column(db.Integer) # 1-5
    spo2 = db.Column(db.Integer)     # oxygen saturation %
    hrv = db.Column(db.Float)        # HR variability
    
    athlete = db.relationship("User", back_populates="health_records")

    __table_args__ = (
        db.Index("idx_health_athlete_id", "athlete_id"),
        db.Index("idx_health_recorded_at", "recorded_at"),
    )