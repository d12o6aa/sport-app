from datetime import datetime
from app.extensions import db

class CoachAthlete(db.Model):
    __tablename__ = "coach_athlete"

    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(
        db.String(20),
        db.CheckConstraint("status IN ('pending','approved','rejected')"),
        default="pending",
        index=True,
    )
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    coach = db.relationship("User", foreign_keys=[coach_id], back_populates="athlete_links")
    athlete = db.relationship("User", foreign_keys=[athlete_id], back_populates="coach_links")
    approver = db.relationship("User", foreign_keys=[approved_by])

    __table_args__ = (
        db.UniqueConstraint("coach_id", "athlete_id", name="uq_coach_athlete_unique"),
        db.Index("idx_coach_athlete_coach_id", "coach_id"),
        db.Index("idx_coach_athlete_athlete_id", "athlete_id"),
    )
