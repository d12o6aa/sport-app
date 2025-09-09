# models/settings.py
from app.extensions import db

class UserSettings(db.Model):
    __tablename__ = "user_settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    notifications = db.Column(db.Boolean, default=True)
    pin_lock = db.Column(db.Boolean, default=False)
    apple_health = db.Column(db.Boolean, default=False)
    dark_mode = db.Column(db.Boolean, default=False)

    user = db.relationship("User", back_populates="settings")
