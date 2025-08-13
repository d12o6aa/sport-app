from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from app.extensions import db

class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(JSONB, server_default="{}", default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User", back_populates="activity_logs")
