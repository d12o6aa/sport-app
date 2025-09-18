from datetime import datetime
from app.extensions import db

class PointsLog(db.Model):
    __tablename__ = "points_logs"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    points = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=False)  # e.g., "Completed workout"
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow)

    athlete = db.relationship("User", foreign_keys=[athlete_id])

    __table_args__ = (
        db.Index("idx_points_logs_athlete", "athlete_id"),
    )
