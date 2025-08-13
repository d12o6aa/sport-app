from datetime import datetime
from app.extensions import db

class WorkoutFile(db.Model):
    __tablename__ = "workout_files"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(
        db.String(20),
        db.CheckConstraint("file_type IN ('image','video')"),
        nullable=False,
        index=True,
    )
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    athlete = db.relationship("User", back_populates="workout_files")

    __table_args__ = (
        db.Index("idx_workout_files_athlete_id", "athlete_id"),
    )
