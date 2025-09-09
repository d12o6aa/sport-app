from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB

class AthleteProfile(db.Model):
    __tablename__ = "athlete_profiles"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    team = db.Column(db.String(100))
    position = db.Column(db.String(100))
    pending_updates = db.Column(JSONB, server_default="{}", default=dict)

    user = db.relationship("User", back_populates="athlete_profile")
    goals = db.relationship("AthleteGoal", back_populates="athlete_profile")
