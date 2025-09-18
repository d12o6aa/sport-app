from datetime import datetime
from app.extensions import db


class HealthIntegration(db.Model):
    __tablename__ = "health_integrations"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    provider = db.Column(db.String(50), db.CheckConstraint("provider IN ('apple_health','google_fit')"), nullable=False)
    steps = db.Column(db.Integer)
    calories = db.Column(db.Integer)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    athlete = db.relationship("User", foreign_keys=[athlete_id])

    __table_args__ = (
        db.Index("idx_health_integrations_athlete", "athlete_id"),
    )