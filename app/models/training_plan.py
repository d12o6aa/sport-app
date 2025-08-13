from datetime import datetime
from app.extensions import db

class TrainingPlan(db.Model):
    __tablename__ = "training_plans"

    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    coach = db.relationship("User", back_populates="training_plans")
    athlete_assignments = db.relationship(
        "AthletePlan",
        back_populates="plan",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
