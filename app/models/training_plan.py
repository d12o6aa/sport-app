from datetime import datetime
from app.extensions import db

class TrainingPlan(db.Model):
    __tablename__ = "training_plans"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    coach_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), db.CheckConstraint("status IN ('active','completed','archived')"), default="active")


    coach = db.relationship("User",foreign_keys=[coach_id], back_populates="training_plans")
    athlete = db.relationship("User",foreign_keys=[athlete_id])
    athlete_assignments = db.relationship(
        "AthletePlan",
        back_populates="plan",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
