# app/models/readiness_score.py
from app.extensions import db
from datetime import datetime


class ReadinessScore(db.Model):
    __tablename__ = "readiness_scores"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow, index=True)
    score = db.Column(db.Integer, nullable=False)  # 0–100
    poms_score = db.Column(db.Integer, default=15)  # Psychological mood state
    confidence_score = db.Column(db.Float, default=0.8)

    injury_risk = db.Column(
        db.String(20),
        db.CheckConstraint("injury_risk IN ('low','medium','high')"),
        default="low"
    )
    recovery_prediction = db.Column(db.String(100))  # e.g., "72% recovery expected"

    athlete = db.relationship("User", back_populates="readiness_scores")
    
    def to_dict(self):
        return {
            "id": self.id,
            "athlete_id": self.athlete_id,
            "date": self.date.isoformat(),
            "score": self.score,
            "injury_risk": self.injury_risk,
            "recovery_prediction": self.recovery_prediction
        }