from app import db
from datetime import datetime

class LoginLog(db.Model):
    __tablename__ = 'login_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    ip_address = db.Column(db.String(45), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # e.g., 'success', 'failed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_suspicious = db.Column(db.Boolean, default=False)
    details = db.Column(db.Text, nullable=True)

    user = db.relationship("User", back_populates="login_logs")