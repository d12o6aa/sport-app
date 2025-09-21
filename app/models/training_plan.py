from datetime import datetime
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB

class TrainingPlan(db.Model):
    __tablename__ = "training_plans"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    coach_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    status = db.Column(
        db.String(20),
        db.CheckConstraint("status IN ('active','completed','archived')"),
        default="active"
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    duration_weeks = db.Column(db.Integer, nullable=False, default=4)
    image_url = db.Column(db.String(255), nullable=True)
    exercises = db.Column(JSONB, server_default="{}", default=dict)  # New field
    # relationships
    coach = db.relationship("User", foreign_keys=[coach_id], back_populates="training_plans")
    athlete = db.relationship("User", foreign_keys=[athlete_id])
    assignments = db.relationship("WorkoutSession", back_populates="plan", cascade="all, delete-orphan")
    nutrition = db.relationship("NutritionPlan", back_populates="plan", cascade="all, delete-orphan")

    # 🆕 العلاقة مع AthletePlan
    athlete_assignments = db.relationship(
        "AthletePlan",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    __table_args__ = (
        db.CheckConstraint("status IN ('active','completed','archived')", name="check_status"),
    )
