from datetime import datetime
from app.extensions import db

class Challenge(db.Model):
    __tablename__ = "challenges"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(
        db.String(20),
        db.CheckConstraint("status IN ('ongoing','completed')"),
        default="ongoing",
        index=True,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    athlete = db.relationship("User", back_populates="ml_insights")
    activities = db.relationship(
        "ChallengeActivity",
        back_populates="challenge",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    __table_args__ = (
        db.Index("idx_challenge_athlete_id", "athlete_id"),
        db.Index("idx_challenge_status", "status"),
    )
