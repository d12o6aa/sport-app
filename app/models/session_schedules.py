from datetime import datetime, timedelta
from app.extensions import db

class SessionSchedule(db.Model):
    __tablename__ = "session_schedules"

    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(20), db.CheckConstraint("type IN ('virtual','in_person')"), nullable=True)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer)  # minutes
    location = db.Column(db.String(255))  # For in-person sessions
    meeting_link = db.Column(db.String(255))  # For virtual sessions
    status = db.Column(db.String(20), db.CheckConstraint("status IN ('scheduled','completed','cancelled')"), default="scheduled")

    coach = db.relationship("User", foreign_keys=[coach_id], back_populates="scheduled_sessions_as_coach")
    athlete = db.relationship("User", foreign_keys=[athlete_id], back_populates="scheduled_sessions_as_athlete")

    @property
    def end_time(self):
        return self.scheduled_at + timedelta(minutes=self.duration)

    @property
    def duration_minutes(self):
        return self.duration
    
    __table_args__ = (
        db.Index("idx_session_schedules_coach_athlete", "coach_id", "athlete_id"),
    )