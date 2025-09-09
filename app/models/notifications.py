from datetime import datetime
from app.extensions import db

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), db.CheckConstraint("type IN ('message','video','alert')"), nullable=False)
    file_path = db.Column(db.String(255))  # For videos
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    coach = db.relationship("User", foreign_keys=[coach_id], back_populates="sent_notifications")
    athlete = db.relationship("User", foreign_keys=[athlete_id], back_populates="received_notifications")


    __table_args__ = (
        db.Index("idx_notifications_coach_athlete", "coach_id", "athlete_id"),
    )
   