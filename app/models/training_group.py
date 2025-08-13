from datetime import datetime
from app.extensions import db

class TrainingGroup(db.Model):
    __tablename__ = "training_groups"

    id = db.Column(db.Integer, primary_key=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    trainer = db.relationship("User", back_populates="training_groups")
    athlete_assignments = db.relationship(
        "AthleteGroup",
        back_populates="group",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.Index("idx_training_groups_trainer_id", "trainer_id"),
    )
