from datetime import datetime
from app.extensions import db
from app.models.training_plan import TrainingPlan

class AthletePlan(db.Model):
    __tablename__ = "athlete_plan"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("training_plans.id"), nullable=False, index=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(
        db.String(20),
        db.CheckConstraint("status IN ('assigned','completed','cancelled')"),
        default="assigned",
    )
    image_url = db.Column(db.String(255), nullable=True)

    athlete = db.relationship("User", back_populates="plan_assignments")
    plan = db.relationship("app.models.training_plan.TrainingPlan", back_populates="athlete_assignments")

    __table_args__ = (
        db.UniqueConstraint("athlete_id", "plan_id", name="uq_athlete_plan_unique"),
        db.Index("idx_athlete_plan_athlete_id", "athlete_id"),
        db.Index("idx_athlete_plan_plan_id", "plan_id"),
    )
