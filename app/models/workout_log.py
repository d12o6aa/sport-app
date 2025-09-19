from datetime import datetime, date
from sqlalchemy.dialects.postgresql import JSONB
from app.extensions import db
from sqlalchemy.orm import relationship

class WorkoutLog(db.Model):
    __tablename__ = "workout_logs"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    
    # Enhanced workout details
    title = db.Column(db.String(150), nullable=True)
    workout_type = db.Column(db.String(50), nullable=True)  # strength, cardio, mobility, etc.
    session_type = db.Column(db.String(50), nullable=False)  # workout, rest, active_recovery
    
    # Timing and metrics
    planned_duration = db.Column(db.Integer)  # planned minutes
    actual_duration = db.Column(db.Integer)   # actual minutes
    total_time = db.Column(db.Integer)        # total session time
    
    # Performance metrics
    calories_burned = db.Column(db.Integer, default=0)
    avg_heart_rate = db.Column(db.Integer)
    max_heart_rate = db.Column(db.Integer)
    
    # Heart rate zones (percentages)
    hr_zone_anaerobic = db.Column(db.Float, default=0.0)  # 90-100%
    hr_zone_aerobic = db.Column(db.Float, default=0.0)    # 70-85%
    hr_zone_intensive = db.Column(db.Float, default=0.0)   # 85-90%
    hr_zone_light = db.Column(db.Float, default=0.0)      # 60-70%
    hr_zone_relaxed = db.Column(db.Float, default=0.0)    # 50-60%
    
    # Training effect scores
    training_effect_aerobic = db.Column(db.Float, default=0.0)
    training_effect_anaerobic = db.Column(db.Float, default=0.0)
    recovery_time = db.Column(db.Integer, default=0)  # hours
    
    # Workout status and feedback
    completion_status = db.Column(
        db.String(20),
        db.CheckConstraint("completion_status IN ('completed','missed','partial','in_progress')"),
        default="completed"
    )
    difficulty_level = db.Column(
        db.String(20),
        db.CheckConstraint("difficulty_level IN ('beginner','intermediate','advanced')"),
        default="beginner"
    )
    
    # Notes and media
    feedback = db.Column(db.Text)
    notes = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    
    # Timestamps
    date = db.Column(db.Date, default=date.today, index=True)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # JSON fields for flexible data
    workout_details = db.Column(JSONB, server_default="{}", default=dict)
    metrics = db.Column(JSONB, default={})
    heart_rate_data = db.Column(JSONB, default={})  # detailed HR data points
    
    # Relationships
    athlete = db.relationship("User", back_populates="workout_logs")
    exercises = relationship(
        "WorkoutLogExercise",
        back_populates="workout_log",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.Index("idx_workout_logs_athlete_date", "athlete_id", "date"),
        db.Index("idx_workout_logs_type", "workout_type"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "workout_type": self.workout_type,
            "session_type": self.session_type,
            "planned_duration": self.planned_duration,
            "actual_duration": self.actual_duration,
            "total_time": self.total_time,
            "calories_burned": self.calories_burned,
            "avg_heart_rate": self.avg_heart_rate,
            "max_heart_rate": self.max_heart_rate,
            "hr_zones": {
                "anaerobic": self.hr_zone_anaerobic,
                "aerobic": self.hr_zone_aerobic,
                "intensive": self.hr_zone_intensive,
                "light": self.hr_zone_light,
                "relaxed": self.hr_zone_relaxed
            },
            "training_effect": {
                "aerobic": self.training_effect_aerobic,
                "anaerobic": self.training_effect_anaerobic
            },
            "recovery_time": self.recovery_time,
            "completion_status": self.completion_status,
            "difficulty_level": self.difficulty_level,
            "date": self.date.isoformat() if self.date else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "feedback": self.feedback,
            "notes": self.notes,
            "image_url": self.image_url,
            "workout_details": self.workout_details or {},
            "metrics": self.metrics or {},
            "heart_rate_data": self.heart_rate_data or {}
        }
