from app.extensions import db

class AthleteGroup(db.Model):
    __tablename__ = "athlete_group"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    group_id = db.Column(db.Integer, db.ForeignKey("training_groups.id"), nullable=False, index=True)

    athlete = db.relationship("User", back_populates="group_assignments")
    group = db.relationship("TrainingGroup", back_populates="athlete_assignments")

    __table_args__ = (
        db.UniqueConstraint("athlete_id", "group_id", name="uq_athlete_group_unique"),
        db.Index("idx_athlete_group_athlete_id", "athlete_id"),
        db.Index("idx_athlete_group_group_id", "group_id"),
    )
