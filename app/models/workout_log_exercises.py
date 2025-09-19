from app.extensions import db
from sqlalchemy.orm import relationship

class WorkoutLogExercise(db.Model):
    __tablename__ = "workout_log_exercises"

    id = db.Column(db.Integer, primary_key=True)
    workout_log_id = db.Column(db.Integer, db.ForeignKey("workout_logs.id"), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False)
    
    # Performance details
    sets = db.Column(db.Integer)
    reps = db.Column(db.Integer)
    weight = db.Column(db.Float)
    duration_minutes = db.Column(db.Integer)
    distance = db.Column(db.Float)  # for cardio exercises
    pace = db.Column(db.String(20))  # for running/cycling
    rest_time = db.Column(db.Integer)  # rest between sets in seconds
    
    # Performance metrics
    calories_burned = db.Column(db.Integer)
    avg_heart_rate = db.Column(db.Integer)
    max_heart_rate = db.Column(db.Integer)
    
    # Notes and feedback
    notes = db.Column(db.Text)
    difficulty_rating = db.Column(db.Integer)  # 1-10 scale
    
    # Relationships
    workout_log = db.relationship("WorkoutLog", back_populates="exercises")
    exercise = db.relationship("Exercise", back_populates="workout_logs")

    __table_args__ = (
        db.Index("idx_workout_log_exercises_log_id", "workout_log_id"),
        db.Index("idx_workout_log_exercises_exercise_id", "exercise_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "workout_log_id": self.workout_log_id,
            "exercise_id": self.exercise_id,
            "sets": self.sets,
            "reps": self.reps,
            "weight": self.weight,
            "duration_minutes": self.duration_minutes,
            "distance": self.distance,
            "pace": self.pace,
            "rest_time": self.rest_time,
            "calories_burned": self.calories_burned,
            "avg_heart_rate": self.avg_heart_rate,
            "max_heart_rate": self.max_heart_rate,
            "notes": self.notes,
            "difficulty_rating": self.difficulty_rating,
            "exercise": self.exercise.to_dict() if self.exercise else None
        }

    def __repr__(self):
        return f"<WorkoutLogExercise {self.workout_log_id}-{self.exercise_id}>"

